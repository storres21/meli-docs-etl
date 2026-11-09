"""Split train / eval_section / eval_project por split_group (lógica pura).

- La unidad es el split_group: un grupo entero va a un solo split.
- eval_project: todos los grupos del proyecto retenido.
- eval_section: en cada estrato (proyecto × source_type), los grupos se recorren en orden de
  `sha256(seed|split_group)` y se toman hasta llegar a la fracción objetivo de tokens; un grupo
  que dejaría el estrato por encima de fracción + tolerancia se saltea.
- Manifiesto congelado: los grupos ya asignados conservan su split; un grupo nuevo hereda el
  split de los grupos anteriores con los que comparte ocurrencias (si vienen de splits
  distintos, va a train y se registra como cambio del conjunto de eval); los realmente nuevos
  completan la cuota de su estrato en orden de hash.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from meli_docs_etl.dedup_utils import jaccard, shingles, tokenize

TRAIN, EVAL_SECTION, EVAL_PROJECT = "train", "eval_section", "eval_project"
SPLITS = (TRAIN, EVAL_SECTION, EVAL_PROJECT)
PARAM_KEYS = (
    "seed",
    "eval_project",
    "eval_section_fraction",
    "tolerance",
    "min_groups_per_stratum",
)


def group_hash(seed: int, group_id: str) -> float:
    """Posición estable del grupo en [0, 1): no depende de los demás grupos."""
    return int(hashlib.sha256(f"{seed}|{group_id}".encode()).hexdigest(), 16) / 2**256


def occurrence_keys(chunk: Mapping[str, Any]) -> set[str]:
    """Claves estables del contenido de una ficha: section_id de cada ocurrencia (incluidas
    las absorbidas) o `archivo|operación` en OpenAPI. No dependen de hashes de contenido."""
    keys = set()
    for o in chunk["occurrences"]:
        keys.add(o["section_id"] or f"{o['path']}|{o['section_path'][0]}")
    return keys


@dataclass
class Group:
    id: str
    projects: list[str]
    source_type: str
    tokens: int
    cluster_ids: list[str]
    chunk_ids: list[str]
    keys: list[str]

    @property
    def stratum(self) -> tuple[str, str]:
        return (self.projects[0], self.source_type)


def build_groups(chunks: Iterable[Mapping[str, Any]]) -> dict[str, Group]:
    acc: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "projects": defaultdict(int),
            "types": defaultdict(int),
            "tokens": 0,
            "clusters": set(),
            "chunks": [],
            "keys": set(),
        }
    )
    for ch in chunks:
        g = acc[ch["split_group"]]
        g["projects"][ch["project"]] += ch["n_tokens"]
        g["types"][ch["source_type"]] += ch["n_tokens"]
        g["tokens"] += ch["n_tokens"]
        g["clusters"].update(ch["cluster_ids"])
        g["chunks"].append(ch["chunk_id"])
        g["keys"] |= occurrence_keys(ch)
    return {
        gid: Group(
            id=gid,
            # Proyecto mayoritario primero (hoy ningún grupo mezcla proyectos).
            projects=sorted(g["projects"], key=lambda p: (-g["projects"][p], p)),
            source_type=max(sorted(g["types"]), key=lambda t: g["types"][t]),
            tokens=g["tokens"],
            cluster_ids=sorted(g["clusters"]),
            chunk_ids=sorted(g["chunks"]),
            keys=sorted(g["keys"]),
        )
        for gid, g in sorted(acc.items())
    }


@dataclass
class EvalChange:
    """Un grupo nuevo une contenido que estaba en splits distintos: va a train."""

    group_id: str
    previous: dict[str, str]  # grupo anterior → split
    # Claves de ocurrencia (section_id u `archivo|operación`) que estaban en un grupo de eval
    # y ahora quedan en train. Las fichas se derivan de estas claves sobre el corpus actual:
    # los chunk_id del manifiesto pueden no existir más si el chunking cambió.
    left_eval_keys: list[str]


@dataclass
class Assignment:
    split: dict[str, str]  # group_id → split
    origin: dict[str, str]  # group_id → kept | inherited | new | conflict
    changes: list[EvalChange] = field(default_factory=list)
    removed: dict[str, str] = field(default_factory=dict)  # grupos del manifiesto que ya no están
    skipped_big: list[str] = field(default_factory=list)  # nuevos que no entraban en la cuota
    small_strata: list[tuple[str, str]] = field(default_factory=list)


def assign(
    groups: Mapping[str, Group],
    params: Mapping[str, Any],
    manifest_groups: Mapping[str, Mapping[str, Any]] | None = None,
) -> Assignment:
    """Asigna cada grupo a un split, respetando el manifiesto si existe."""
    held_out = params["eval_project"]
    manifest_groups = manifest_groups or {}
    res = Assignment(split={}, origin={})

    # 1) Grupos del manifiesto y herencia por ocurrencias compartidas.
    owner: dict[str, str] = {}  # clave de ocurrencia → grupo anterior
    for old_id, old in sorted(manifest_groups.items()):
        for key in old["keys"]:
            owner.setdefault(key, old_id)
    used_old: set[str] = set()
    pending: list[Group] = []
    for gid, g in groups.items():
        if held_out in g.projects:
            res.split[gid], res.origin[gid] = EVAL_PROJECT, "held_out"
            used_old |= {owner[k] for k in g.keys if k in owner}
            continue
        # Se mira siempre de qué grupos anteriores viene el contenido, aunque el id ya esté
        # en el manifiesto: un must-link nuevo puede unir dos grupos y dejar el id de uno
        # de ellos (el del cluster canónico), y "conservar" ese split movería en silencio
        # contenido de train a eval.
        prev = {owner[k] for k in g.keys if k in owner}
        if gid in manifest_groups:
            prev.add(gid)
        used_old |= prev
        splits = {manifest_groups[o]["split"] for o in prev}
        if not prev:
            pending.append(g)
        elif len(splits) == 1:
            origin = "kept" if prev == {gid} else "inherited"
            res.split[gid], res.origin[gid] = splits.pop(), origin
        else:
            res.split[gid], res.origin[gid] = TRAIN, "conflict"
            res.changes.append(
                EvalChange(
                    group_id=gid,
                    previous={o: manifest_groups[o]["split"] for o in sorted(prev)},
                    left_eval_keys=sorted(
                        k
                        for o in prev
                        if manifest_groups[o]["split"] != TRAIN
                        for k in manifest_groups[o]["keys"]
                        if k in set(g.keys)
                    ),
                )
            )
    res.removed = {o: m["split"] for o, m in sorted(manifest_groups.items()) if o not in used_old}

    # 2) Cuota por estrato para los grupos realmente nuevos, en orden de hash.
    pending_ids = {g.id for g in pending}
    by_stratum: dict[tuple[str, str], list[Group]] = defaultdict(list)
    for g in groups.values():
        if held_out not in g.projects:
            by_stratum[g.stratum].append(g)
    frac, tol = params["eval_section_fraction"], params["tolerance"]
    for stratum, members in sorted(by_stratum.items()):
        new = [g for g in members if g.id in pending_ids]
        if not new:
            continue
        if len(members) < params["min_groups_per_stratum"]:
            res.small_strata.append(stratum)
            for g in new:
                res.split[g.id], res.origin[g.id] = TRAIN, "new"
            continue
        total = sum(g.tokens for g in members)
        acc = sum(g.tokens for g in members if res.split.get(g.id) == EVAL_SECTION)
        for g in sorted(new, key=lambda g: (group_hash(params["seed"], g.id), g.id)):
            fits = acc + g.tokens <= (frac + tol) * total
            if acc < frac * total and fits:
                res.split[g.id] = EVAL_SECTION
                acc += g.tokens
            else:
                res.split[g.id] = TRAIN
                if acc < frac * total and not fits:
                    res.skipped_big.append(g.id)
            res.origin[g.id] = "new"
    return res


# --------------------------------------------------------------------------- auditoría


@dataclass
class HardAudit:
    groups_split: list[str] = field(default_factory=list)  # split_group en > 1 split
    clusters_split: list[str] = field(default_factory=list)  # cluster_id en > 1 split
    unassigned: list[str] = field(default_factory=list)  # fichas sin split válido
    held_out_outside: list[str] = field(default_factory=list)  # proyecto retenido fuera

    @property
    def ok(self) -> bool:
        return not (
            self.groups_split or self.clusters_split or self.unassigned or self.held_out_outside
        )


def audit_hard(chunks: Sequence[Mapping[str, Any]], held_out: str) -> HardAudit:
    res = HardAudit()
    by_group: dict[str, set[str]] = defaultdict(set)
    by_cluster: dict[str, set[str]] = defaultdict(set)
    for ch in chunks:
        split = ch.get("split")
        if split not in SPLITS:
            res.unassigned.append(ch["chunk_id"])
            continue
        by_group[ch["split_group"]].add(split)
        for cid in ch["cluster_ids"]:
            by_cluster[cid].add(split)
        if ch["project"] == held_out and split != EVAL_PROJECT:
            res.held_out_outside.append(ch["chunk_id"])
    res.groups_split = sorted(g for g, s in by_group.items() if len(s) > 1)
    res.clusters_split = sorted(c for c, s in by_cluster.items() if len(s) > 1)
    return res


def cross_split_similar(
    chunks: Sequence[Mapping[str, Any]], min_j: float, shingle_size: int
) -> list[tuple[float, str, str]]:
    """Pares de fichas en splits distintos con Jaccard ≥ min_j: (j, chunk_a, chunk_b)."""
    sh = {ch["chunk_id"]: shingles(tokenize(ch["text"]), shingle_size) for ch in chunks}
    out = []
    ordered = sorted(chunks, key=lambda c: c["chunk_id"])
    for i, a in enumerate(ordered):
        for b in ordered[i + 1 :]:
            if a["split"] == b["split"]:
                continue
            j = jaccard(sh[a["chunk_id"]], sh[b["chunk_id"]])
            if j >= min_j:
                out.append((j, a["chunk_id"], b["chunk_id"]))
    return sorted(out, key=lambda x: (-x[0], x[1], x[2]))


_PATH_RE = re.compile(r"(?<![\w.:/])(/[A-Za-z0-9_{}\-]+(?:/[A-Za-z0-9_{}\-]+)*)")
_PARAM_RE = re.compile(r"\{[^}]*\}")


def _norm_path(path: str) -> str:
    return _PARAM_RE.sub("{}", path.rstrip("/")).lower()


@dataclass(frozen=True)
class EndpointLeak:
    project: str
    endpoint: str  # MÉTODO path del swagger
    mentioned_as: str  # path tal como aparece en el .md
    openapi_chunk: str
    openapi_split: str
    markdown_chunk: str
    markdown_split: str


def endpoint_leaks(chunks: Sequence[Mapping[str, Any]]) -> list[EndpointLeak]:
    """Endpoints del swagger mencionados en un .md del mismo proyecto en otro split.

    Coincide si el path del .md es igual al del swagger o un sufijo de al menos dos
    segmentos (los .md suelen omitir prefijos como `/api/v1`); los parámetros `{x}` se
    normalizan a `{}`.
    """
    ops = [c for c in chunks if c["source_type"] == "openapi" and c.get("operation")]
    docs = [c for c in chunks if c["source_type"] == "markdown"]
    out = set()
    for op in ops:
        target = _norm_path(op["operation"]["path"])
        for doc in docs:
            if doc["project"] != op["project"] or doc["split"] == op["split"]:
                continue
            for m in _PATH_RE.finditer(doc["text"]):
                mention = _norm_path(m.group(1))
                if mention == target or (mention.count("/") >= 2 and target.endswith(mention)):
                    out.add(
                        EndpointLeak(
                            op["project"],
                            f"{op['operation']['method']} {op['operation']['path']}",
                            m.group(1),
                            op["chunk_id"],
                            op["split"],
                            doc["chunk_id"],
                            doc["split"],
                        )
                    )
                    break
    return sorted(out, key=lambda e: (e.project, e.endpoint, e.markdown_chunk))


def files_across(
    chunks: Sequence[Mapping[str, Any]], a: str = TRAIN, b: str = EVAL_SECTION
) -> dict[str, dict[str, int]]:
    """Archivos con fichas en los splits a y b: {archivo: {split: n_fichas}}."""
    by_file: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for ch in chunks:
        by_file[ch["source_path"]][ch["split"]] += 1
    return {f: dict(sorted(c.items())) for f, c in sorted(by_file.items()) if c.get(a) and c.get(b)}
