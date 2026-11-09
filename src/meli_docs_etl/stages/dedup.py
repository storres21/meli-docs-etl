"""Etapa 3 — dedup a nivel de sección: exacto (sha256) + casi-duplicados (MinHash/LSH).

Lee `sections.jsonl` / `normalized_docs.jsonl` (etapa normalize) y escribe:
- `<processed_dir>/sections_dedup.jsonl`: secciones canónicas y variantes con sus ocurrencias.
- `<processed_dir>/versions.json`: versión declarada vs. versión efectiva por contenido.
- `<processed_dir>/near_dup_pairs.jsonl`: pares con Jaccard ≥ labels.review_min_jaccard.
- `<reports_dir>/dedup.md`.

`cluster_id` agrupa duplicados exactos y casi-duplicados: es la clave para el split
train/eval sin leakage.
"""

from __future__ import annotations

import difflib
import json
import logging
from collections import Counter, defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any

from meli_docs_etl.config import Config, display_path
from meli_docs_etl.dedup_utils import (
    UnionFind,
    body_lines,
    jaccard,
    lsh_candidates,
    merge_cluster,
    shingles,
    tokenize,
)
from meli_docs_etl.inventory import ALIAS_VERSIONS
from meli_docs_etl.stages.normalize import DOCS_FILE, SECTIONS_FILE, STATS_FILE, n_words
from meli_docs_etl.stages.validate_threshold import (
    LABELS_FILE,
    MANUAL_LINKS_FILE,
    PAIRS_FILE,
    THRESHOLD_KEY,
    VERSIONS_FILE,
    ManualLink,
    build_validation,
    checked_labels,
    read_manual_links,
)
from meli_docs_etl.stages.validate_threshold import render_section as render_threshold_section
from meli_docs_etl.threshold_validation import (
    ThresholdChoice,
    choose_threshold,
    pair_id,
    threshold_grid,
)

log = logging.getLogger(__name__)

DEDUP_FILE = "sections_dedup.jsonl"
Section = dict[str, Any]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"{path} no existe: corré antes `meli-etl normalize`.")
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def _is_alias(s: Section) -> bool:
    return s["version_dir"] in ALIAS_VERSIONS


def _canon_key(s: Section) -> tuple:
    """Preferencia determinista: versión concreta antes que alias; luego ruta y orden."""
    return (_is_alias(s), s["doc_path"], s["ordinal"])


# --------------------------------------------------------------------------- versiones


def resolve_versions(sections: list[Section]) -> dict[str, Any]:
    """Compara carpetas de un mismo proyecto por su conjunto de hashes de sección.

    Usa todas las secciones de contenido (también las descartadas) para que dos carpetas
    con los mismos archivos se reconozcan como iguales.
    """
    sigs: dict[tuple[str, str], set[str]] = defaultdict(set)
    declared: dict[tuple[str, str], str] = {}
    for s in sections:
        key = (s["project"], s["version_dir"])
        sigs[key].add(s["norm_hash"])
        declared[key] = s["declared_version"]

    folders: dict[str, Any] = {}
    for (project, vdir), sig in sorted(sigs.items()):
        siblings = [(v, sigs[(p, v)]) for (p, v) in sorted(sigs) if p == project and v != vdir]
        identical = [v for v, other in siblings if other == sig]
        best = max(siblings, key=lambda x: (jaccard(sig, x[1]), x[0]), default=None)
        decl = declared[(project, vdir)]
        decl_present = (project, decl) in sigs and decl != vdir
        is_alias = vdir in ALIAS_VERSIONS
        if is_alias and identical:
            effective = sorted(identical, key=lambda v: (v in ALIAS_VERSIONS, v))[0]
        elif is_alias:
            effective = decl
        else:
            effective = vdir

        issues = []
        if not is_alias and decl != vdir:
            issues.append(f"la carpeta `{vdir}` declara `{decl}`")
        if is_alias and identical and decl not in identical:
            where = "presente" if decl_present else "no presente en docs_raw"
            issues.append(
                f"declara `{decl}` ({where}) pero el contenido es idéntico a `{identical[0]}`"
            )
        if is_alias and decl_present and decl not in identical:
            issues.append(f"declara `{decl}`, que está en docs_raw, pero el contenido difiere")
        if is_alias and not identical and best is not None:
            other = sigs[(project, best[0])]
            rel = "⊇" if sig >= other else "≠"
            issues.append(
                f"sin carpeta idéntica; más parecida `{best[0]}` "
                f"(Jaccard de secciones {jaccard(sig, other):.2f}, contenido {rel} `{best[0]}`)"
            )
        folders[f"{project}/{vdir}"] = {
            "project": project,
            "version_dir": vdir,
            "is_alias": is_alias,
            "declared_version": decl,
            "declared_present": decl_present,
            "identical_to": identical,
            "most_similar": best[0] if best else None,
            "most_similar_jaccard": round(jaccard(sig, best[1]), 4) if best else None,
            "effective_version": effective,
            "n_sections": len(sig),
            "issues": issues,
        }
    return folders


# --------------------------------------------------------------------------- dedup


def _occurrence(s: Section, effective: dict[str, str], match: str, j: float | None) -> dict:
    return {
        "section_id": s["section_id"],
        "project": s["project"],
        "version_dir": s["version_dir"],
        "declared_version": s["declared_version"],
        "effective_version": effective[f"{s['project']}/{s['version_dir']}"],
        "path": s["doc_path"],
        "section_path": s["section_path"],
        "match": match,
        "jaccard": None if j is None else round(j, 4),
    }


def dedup_sections(
    kept: list[Section],
    versions: dict[str, Any],
    cfg: Config,
    must_link: Collection[str] = (),
    manual_links: Sequence[ManualLink] = (),
    labels: Mapping[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """`must_link`: pair_ids etiquetados `same` por una persona; se agrupan aunque su
    Jaccard quede bajo el umbral. `labels` (pair_id → same/diff/unsure) alimenta el umbral
    `auto` (ver `choose_threshold`). `manual_links`: must-links declarados por section_id para
    pares fuera de la muestra etiquetable (p. ej. hallados en la auditoría del split).
    Las etiquetas `diff` nunca separan pares."""
    d = cfg.dedup
    effective = {k: v["effective_version"] for k, v in versions.items()}

    # 1) Exacto: mismo texto normalizado (título + cuerpo).
    by_hash: dict[str, list[Section]] = defaultdict(list)
    for s in kept:
        by_hash[s["norm_hash"]].append(s)
    groups = {h: sorted(g, key=_canon_key) for h, g in by_hash.items()}
    reps = {g[0]["section_id"]: g[0] for g in groups.values()}
    members_of = {g[0]["section_id"]: g for g in groups.values()}

    # 2) Casi-duplicados entre representantes con suficiente texto.
    sh = {
        sid: shingles(tokenize(s["text"]), d.shingle_size)
        for sid, s in reps.items()
        if s["tokens"] >= d.near_dup_min_tokens
    }
    candidates = lsh_candidates(sh, d.lsh_threshold, d.num_perm, cfg.seed)
    # Diagnóstico exhaustivo (el corpus es chico): distribución y recall de LSH.
    all_pairs: dict[tuple[str, str], float] = {}
    for a, b in combinations(sorted(sh), 2):
        j = jaccard(sh[a], sh[b])
        if j > 0:
            all_pairs[(a, b)] = j
    by_pid = {pair_id(a, b): (a, b) for a, b in all_pairs}
    lc = cfg.labels
    choice = choose_threshold(
        d.near_dup_threshold,
        sorted(all_pairs.get(p, 0.0) for p in candidates),
        sorted(
            (all_pairs[by_pid[pid]], label)
            for pid, label in (labels or {}).items()
            if pid in by_pid and label
        ),
        fallback=d.threshold_fallback,
        bounds=d.threshold_bounds,
        min_valley_width=d.min_valley_width,
        grid=threshold_grid(lc.grid_start, lc.grid_stop, lc.grid_step),
        min_label_pairs=lc.min_same_pairs,
    )
    thr = choice.threshold
    edges = {p: all_pairs.get(p, 0.0) for p in candidates}
    edges = {p: j for p, j in edges.items() if j >= thr}
    truth = {p for p, j in all_pairs.items() if j >= thr}

    # Must-link: pares `same` (etiqueta humana) que el umbral no agrupa por sí solo.
    human = {by_pid[pid]: all_pairs[by_pid[pid]] for pid in must_link if pid in by_pid}
    human = {p: j for p, j in human.items() if p not in edges}
    missing_links = sorted(pid for pid in must_link if pid not in by_pid)

    # Must-links manuales: por section_id (puede ser una copia exacta) → su representante.
    rep_of = {s["section_id"]: g[0]["section_id"] for g in groups.values() for s in g}
    manual: dict[tuple[str, str], dict[str, Any]] = {}
    manual_report: list[dict[str, Any]] = []
    for m in manual_links:
        ra, rb = rep_of.get(m.section_a), rep_of.get(m.section_b)
        entry = {"link": m, "jaccard": None}
        if ra is None or rb is None:
            entry["status"] = "sección inexistente o filtrada"
        elif ra == rb:
            entry["status"] = "ya idénticas (dedup exacto)"
        else:
            x, y = sorted((ra, rb))
            entry["jaccard"] = jaccard(
                shingles(tokenize(reps[x]["text"]), d.shingle_size),
                shingles(tokenize(reps[y]["text"]), d.shingle_size),
            )
            if (x, y) in edges or (x, y) in human:
                entry["status"] = "ya agrupadas"
            else:
                entry["status"] = "unidas"
                manual[(x, y)] = entry
        manual_report.append(entry)

    uf: UnionFind[str] = UnionFind(sorted(reps))
    for a, b in sorted(edges) + sorted(human) + sorted(manual):
        uf.union(a, b)

    def link(a: str, b: str) -> str:
        """Cómo quedó unido un par dentro del cluster."""
        x, y = sorted((a, b))
        if (x, y) in edges:
            return "near_dup"
        if (x, y) in human:
            return "human_label"
        return "audit_link" if (x, y) in manual else "transitive"

    # 3) Regla de fusión sin pérdida dentro de cada cluster.
    records: list[dict[str, Any]] = []
    clusters_info: list[dict[str, Any]] = []
    cluster_of: dict[str, str] = {}
    for group in uf.groups():
        res = merge_cluster(
            [reps[sid] for sid in group],
            lines=lambda s: body_lines(s["body"]),
            sort_key=_canon_key,
        )
        canonical = res.kept[0]
        cluster_id = "cl-" + canonical["norm_hash"][:12]
        cluster_of.update(dict.fromkeys(group, cluster_id))
        canon_lines = body_lines(canonical["body"])
        for i, s in enumerate(res.kept):
            occ = [
                _occurrence(m, effective, "self" if m is s else "exact", None if m is s else 1.0)
                for m in members_of[s["section_id"]]
            ]
            for ab in res.absorbed_by.get(i, []):
                j = _pair_j(all_pairs, s["section_id"], ab["section_id"])
                match = link(s["section_id"], ab["section_id"])
                occ += [_occurrence(m, effective, match, j) for m in members_of[ab["section_id"]]]
            lines = body_lines(s["body"])
            shared = lines & canon_lines if i else frozenset()
            records.append(
                {
                    "section_id": s["section_id"],
                    "cluster_id": cluster_id,
                    "exact_group_id": "ex-" + s["norm_hash"][:12],
                    "role": "canonical" if i == 0 else "variant",
                    "variant_of": None if i == 0 else canonical["section_id"],
                    "jaccard_vs_canonical": (
                        None
                        if i == 0
                        else round(_pair_j(all_pairs, canonical["section_id"], s["section_id"]), 4)
                    ),
                    "match_to_canonical": (
                        None if i == 0 else link(canonical["section_id"], s["section_id"])
                    ),
                    "project": s["project"],
                    "version_dir": s["version_dir"],
                    "declared_version": s["declared_version"],
                    "effective_version": effective[f"{s['project']}/{s['version_dir']}"],
                    "path": s["doc_path"],
                    "title": s["title"],
                    "section_path": s["section_path"],
                    "level": s["level"],
                    "language": s["language"],
                    "language_source": s["language_source"],
                    "tokens": s["tokens"],
                    "norm_hash": s["norm_hash"],
                    "text": s["text"],
                    "body": s["body"],
                    "n_occurrences": len(occ),
                    "projects": sorted({o["project"] for o in occ}),
                    "versions": sorted({f"{o['project']}/{o['version_dir']}" for o in occ}),
                    "occurrences": occ,
                    "unique_lines_vs_canonical": sorted(lines - canon_lines) if i else [],
                    "redundant_tokens": n_words("\n".join(shared)),
                }
            )
        if len(group) > 1:
            pair_js = [_pair_j(all_pairs, a, b) for a, b in combinations(group, 2)]
            clusters_info.append(
                {
                    "cluster_id": cluster_id,
                    "n_reps": len(group),
                    "n_sections": sum(len(members_of[g]) for g in group),
                    "min_j": min(pair_js),
                    "canonical": canonical["section_id"],
                    "n_variants": len(res.kept) - 1,
                    "n_absorbed": sum(len(v) for v in res.absorbed_by.values()),
                    "projects": sorted({reps[g]["project"] for g in group}),
                }
            )

    records.sort(key=lambda r: r["section_id"])
    diag = {
        "groups": groups,
        "reps": reps,
        "eligible": sorted(sh),
        "all_pairs": all_pairs,
        "threshold": choice,
        "candidates": candidates,
        "edges": edges,
        "human_links": human,
        "missing_links": missing_links,
        "manual_links": manual_report,
        "cluster_of": cluster_of,
        "truth": truth,
        "clusters": clusters_info,
    }
    return records, diag


def _pair_j(all_pairs: dict[tuple[str, str], float], a: str, b: str) -> float:
    x, y = sorted((a, b))
    return all_pairs.get((x, y), 0.0)


# --------------------------------------------------------------------------- reporte


def _table(headers: list[str], rows: Iterable[Iterable[object]]) -> str:
    def cell(v: object) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(out)


def _bar(n: int, total: int, width: int = 30) -> str:
    return "█" * round(width * n / total) if total else ""


def _hist(values: list[float], edges: list[float]) -> list[tuple[str, int]]:
    rows = []
    for lo, hi in zip(edges, edges[1:], strict=False):
        last = hi == edges[-1]
        n = sum(lo <= v < hi or (last and v == hi) for v in values)
        rows.append((f"[{lo:.1f}, {hi:.1f}{']' if last else ')'}", n))
    return rows


def _short(s: Section) -> str:
    return f"{s['doc_path']} › {' › '.join(s['section_path'][1:]) or s['section_path'][0]}"


def _diff(a: Section, b: Section, max_lines: int = 30) -> str:
    diff = list(
        difflib.unified_diff(
            a["text"].splitlines(), b["text"].splitlines(), "A", "B", n=1, lineterm=""
        )
    )[2:]
    if len(diff) > max_lines:
        diff = diff[:max_lines] + [f"... ({len(diff) - max_lines} líneas más)"]
    return "\n".join(diff)


def render_report(
    docs: list[dict[str, Any]],
    sections: list[Section],
    records: list[dict[str, Any]],
    diag: dict[str, Any],
    versions: dict[str, Any],
    norm_stats: dict[str, Any],
    cfg: Config,
    threshold_section: str = "",
) -> str:
    d = cfg.dedup
    content_docs = [x for x in docs if x["file_type"] == "content"]
    kept_docs = [x for x in content_docs if x["kept"]]
    kept_doc_ids = {x["doc_id"] for x in kept_docs}
    secs_in_kept_docs = [s for s in sections if s["doc_path"] in kept_doc_ids]
    kept = [s for s in sections if s["kept"]]
    reps = diag["reps"]
    final_tokens = sum(r["tokens"] for r in records)

    out = ["# Normalización y deduplicación", ""]
    out.append(
        "Generado por `meli-etl normalize` + `meli-etl dedup` (determinista). Unidad de dedup: "
        "**sección** (header + cuerpo hasta el siguiente header). Tokens = palabras `\\w+`."
    )

    # 1. Embudo
    out += ["", "## 1. Embudo", ""]
    funnel = [
        (
            "0. Crudo (Markdown: contenido + navegación)",
            len(docs),
            len(sections),
            sum(x["tokens_raw"] for x in docs),
        ),
        ("1. Normalizado", len(docs), len(sections), sum(x["tokens"] for x in docs)),
        (
            "2. Filtro de archivos (nav, stub, todo_only)",
            len(kept_docs),
            len(secs_in_kept_docs),
            sum(s["tokens"] for s in secs_in_kept_docs),
        ),
        (
            "3. Filtro de secciones (cuerpo vacío, TO DO)",
            len({s["doc_path"] for s in kept}),
            len(kept),
            sum(s["tokens"] for s in kept),
        ),
        (
            "4. Dedup exacto",
            len({s["doc_path"] for s in reps.values()}),
            len(reps),
            sum(s["tokens"] for s in reps.values()),
        ),
        (
            "5. Dedup casi-duplicados (regla sin pérdida)",
            len({r["path"] for r in records}),
            len(records),
            final_tokens,
        ),
    ]
    out.append(_table(["Paso", "Archivos", "Secciones", "Tokens"], funnel))
    n_var = sum(r["role"] == "variant" for r in records)
    red = sum(r["redundant_tokens"] for r in records)
    out += [
        "",
        f"- Resultado: **{len(records)} secciones** = {len(records) - n_var} canónicas + "
        f"{n_var} variantes, en {len({r['cluster_id'] for r in records})} clusters.",
        "- En los pasos 0–1 los tokens incluyen navegación; desde el paso 2 se cuentan "
        "por sección.",
    ]

    # 2. Archivos excluidos
    out += ["", "## 2. Archivos excluidos del corpus", ""]
    excl = sorted((x for x in docs if not x["kept"]), key=lambda x: (x["drop_reason"], x["path"]))
    out.append(
        _table(
            ["Archivo", "Motivo", "Tokens de contenido"],
            [
                (x["path"], x["drop_reason"], x.get("content_tokens", "—"))
                for x in excl
                if x["drop_reason"] != "nav"
            ],
        )
    )
    n_nav = sum(x["drop_reason"] == "nav" for x in docs)
    out += [
        "",
        f"Además se excluyen **{n_nav} archivos de navegación** "
        f"(`{'`, `'.join(cfg.files.nav_filenames)}`); "
        "su orden, títulos y frase de portada quedan como metadata (`nav_title`, `nav_order`, "
        "`nav_parent`, `project_tagline`) y en `nav.jsonl`.",
        f"Criterio de stub: menos de {cfg.normalize.stub_min_tokens} tokens de contenido tras "
        "quitar headers e imágenes; **cuenta código, tablas y texto de links**.",
        "",
        "**Secciones descartadas dentro de archivos conservados**",
        "",
    ]
    drop = Counter(s["drop_reason"] for s in secs_in_kept_docs if not s["kept"])
    out.append(
        _table(
            ["Motivo", "Secciones", "Significado"],
            [
                (
                    "empty_body",
                    drop["empty_body"],
                    "header sin cuerpo propio (contenedor) o solo imágenes; "
                    "su título sigue en `section_path` de las hijas",
                ),
                ("todo", drop["todo"], "cuerpo con solo marcadores TO DO"),
            ],
        )
    )

    # 3. Normalización
    out += ["", "## 3. Efecto de la normalización", ""]
    tf = norm_stats.get("transformations", {})
    labels = {
        "entities_decoded": "Entidades HTML decodificadas (`&#39;` → `'`), código incluido",
        "tables_normalized": "Tablas re-escritas sin padding",
        "empty_table_rows_removed": "Filas de tabla vacías/rotas quitadas",
        "images_removed": "Imágenes quitadas del texto (→ metadata `images`)",
        "badges_removed": "Badges quitados (→ metadata `badges`)",
        "html_comments_removed": "Comentarios HTML/docsify quitados",
        "style_attrs_removed": "Atributos `style` quitados",
        "malformed_headers_fixed": "Headers mal formados reparados (`#Título` → `# Título`)",
        "h1_synthesized": "H1 sintetizado desde el nombre de archivo",
    }
    out.append(
        _table(
            ["Transformación", "Ocurrencias"], [(labels.get(k, k), tf.get(k, 0)) for k in labels]
        )
    )

    def groups_by(items: list[dict[str, Any]], key: str) -> list[list[dict[str, Any]]]:
        g: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for it in items:
            g[it[key]].append(it)
        return [v for v in g.values() if len(v) > 1]

    def dup_stats(items: list[dict[str, Any]], raw_key: str, norm_key: str) -> tuple:
        raw_g, norm_g = groups_by(items, raw_key), groups_by(items, norm_key)
        grown = [g for g in norm_g if len({x[raw_key] for x in g}) > 1]
        raw_red = sum(len(g) - 1 for g in raw_g)
        norm_red = sum(len(g) - 1 for g in norm_g)
        return (len(raw_g), raw_red, len(norm_g), norm_red, norm_red - raw_red, len(grown)), grown

    file_row, gained_files = dup_stats(content_docs, "raw_sha256", "norm_sha256")
    sec_row, gained_secs = dup_stats(kept, "raw_hash", "norm_hash")
    out += [
        "",
        "**Casi-duplicados que se volvieron exactos solo por normalizar**",
        "",
        _table(
            [
                "Nivel",
                "Grupos exactos (crudo)",
                "Copias redundantes (crudo)",
                "Grupos exactos (normalizado)",
                "Copias redundantes (normalizado)",
                "Copias detectadas solo por normalizar",
                "Grupos que crecieron o aparecieron",
            ],
            [("Archivo", *file_row), ("Sección (en corpus)", *sec_row)],
        ),
        "",
        "Copias redundantes = elementos de un grupo exacto además del primero.",
        "",
    ]
    if gained_files:
        out.append(
            "Archivos que pasaron a ser idénticos: "
            + "; ".join(" = ".join(f"`{x['path']}`" for x in g) for g in gained_files)
        )
        out.append("")
    if gained_secs:
        out += ["<details><summary>Secciones que pasaron a ser idénticas</summary>", ""]
        out.append(
            _table(
                ["Sección", "Copias", "Ubicaciones"],
                [
                    (
                        " › ".join(g[0]["section_path"]),
                        len(g),
                        "<br>".join(s["doc_path"] for s in g),
                    )
                    for g in sorted(gained_secs, key=lambda g: g[0]["section_id"])
                ],
            )
        )
        out += ["", "</details>"]

    # 4. Similitud y umbral
    all_pairs: dict[tuple[str, str], float] = diag["all_pairs"]
    eligible = diag["eligible"]
    out += ["", "## 4. Distribución de similitudes y umbral", ""]
    out.append(
        f"Shingles de {d.shingle_size} palabras; Jaccard **exacto** entre los {len(eligible)} "
        f"representantes (uno por grupo exacto) con ≥ {d.near_dup_min_tokens} tokens. "
        f"{len(reps) - len(eligible)} representantes más cortos solo participan del dedup exacto."
    )
    max_j: dict[str, float] = defaultdict(float)
    for (a, b), j in all_pairs.items():
        max_j[a] = max(max_j[a], j)
        max_j[b] = max(max_j[b], j)
    maxes = [max_j[s] for s in eligible]
    edges10 = [round(x * 0.1, 1) for x in range(11)]
    hist_max = _hist(maxes, edges10)
    hist_pairs = _hist([j for j in all_pairs.values() if j >= 0.1], edges10[1:])
    out += ["", f"**Similitud máxima de cada sección con cualquier otra** (n = {len(maxes)})", ""]
    out.append(
        _table(["Jaccard", "Secciones", ""], [(r, n, _bar(n, len(maxes))) for r, n in hist_max])
    )
    total_p = sum(n for _, n in hist_pairs)
    out += [
        "",
        f"**Pares con Jaccard ≥ 0.1** (n = {total_p} de "
        f"{len(eligible) * (len(eligible) - 1) // 2} pares posibles)",
        "",
    ]
    out.append(
        _table(
            ["Jaccard", "Pares", ""],
            [(r, n, _bar(n, max(n for _, n in hist_pairs) or 1)) for r, n in hist_pairs],
        )
    )

    choice: ThresholdChoice = diag["threshold"]
    thr = choice.threshold
    gap_lo = max((j for j in all_pairs.values() if j < thr), default=0.0)
    gap_hi = min((j for j in all_pairs.values() if j >= thr), default=1.0)
    lsh_found = len(diag["truth"] & set(diag["edges"]))
    recall = lsh_found / len(diag["truth"]) if diag["truth"] else 1.0
    cross = sum(1 for (a, b) in diag["truth"] if reps[a]["project"] != reps[b]["project"])
    out += [
        "",
        f"- Umbral: **Jaccard ≥ {thr}**. Par más similar por debajo: {gap_lo:.3f}; "
        f"par menos similar por encima: {gap_hi:.3f}.",
        *_threshold_choice_lines(choice, d),
        f"- Pares sobre el umbral: {len(diag['truth'])} ({cross} entre proyectos distintos).",
        f"- Recall de MinHash/LSH (umbral de banding {d.lsh_threshold}, "
        f"{d.num_perm} permutaciones) "
        f"frente al cálculo exhaustivo: **{recall:.0%}** ({lsh_found}/{len(diag['truth'])}); "
        f"{len(diag['candidates'])} candidatos verificados.",
    ]
    border = sorted(((j, p) for p, j in all_pairs.items() if 0.3 <= j < thr), reverse=True)
    out += [
        "",
        f"**Pares más similares bajo el umbral (0.3 ≤ Jaccard < {thr})** — no se agrupan",
        "",
    ]
    if border:
        out.append(
            _table(
                ["Jaccard", "A", "B"],
                [(f"{j:.3f}", _short(reps[a]), _short(reps[b])) for j, (a, b) in border[:15]],
            )
        )
    else:
        out.append("_Ninguno._")
    above = sorted(((j, p) for p, j in diag["edges"].items()), key=lambda x: x[0])
    out += ["", "**Pares fusionados más cercanos al umbral**", ""]
    out.append(
        _table(
            ["Jaccard", "A", "B"],
            [(f"{j:.3f}", _short(reps[a]), _short(reps[b])) for j, (a, b) in above[:10]],
        )
        if above
        else "_Ninguno._"
    )

    # 5. Clusters y regla de fusión
    out += ["", "## 5. Clusters de casi-duplicados y regla de fusión", ""]
    out.append(
        "Dentro de cada cluster, la canónica es la sección con más líneas. Otra sección se "
        "**absorbe** (pasa a `occurrences`) solo si todas sus líneas ya están en una sección "
        "conservada; si aporta al menos una línea nueva queda como **variante** (mismo "
        "`cluster_id`, `variant_of` → canónica). No se pierde contenido único."
    )
    out += [""]
    cl = sorted(diag["clusters"], key=lambda c: (-c["n_sections"], c["cluster_id"]))
    out.append(
        _table(
            [
                "Cluster",
                "Representantes",
                "Secciones",
                "Jaccard mín.",
                "Canónica",
                "Absorbidas",
                "Variantes",
                "Proyectos",
            ],
            [
                (
                    c["cluster_id"],
                    c["n_reps"],
                    c["n_sections"],
                    f"{c['min_j']:.2f}",
                    c["canonical"],
                    c["n_absorbed"],
                    c["n_variants"],
                    ", ".join(c["projects"]),
                )
                for c in cl
            ],
        )
        if cl
        else "_Sin clusters de casi-duplicados._"
    )
    human = diag["human_links"]
    out += [
        "",
        f"**Uniones por etiqueta humana (must-link, `match: human_label`):** {len(human)} pares "
        f"etiquetados `same` en `{display_path(cfg.paths.labels_dir / LABELS_FILE)}` que el "
        "umbral no agrupa por sí solo. Las etiquetas `diff` no separan pares: solo cuentan "
        "para las métricas de la §8.",
    ]
    if human:
        out += [""]
        out.append(
            _table(
                ["Jaccard", "A", "B"],
                [
                    (f"{j:.3f}", _short(diag["reps"][a]), _short(diag["reps"][b]))
                    for (a, b), j in sorted(human.items(), key=lambda x: (-x[1], x[0]))
                ],
            )
        )
    manual = diag["manual_links"]
    out += [
        "",
        f"**Must-links manuales (`match: audit_link`):** {len(manual)} pares declarados en "
        f"`{display_path(cfg.paths.labels_dir / MANUAL_LINKS_FILE)}` para casos fuera de la "
        "muestra etiquetable (Jaccard < "
        f"{cfg.labels.review_min_jaccard} o secciones con < {d.near_dup_min_tokens} tokens), "
        "por ejemplo los hallados en la auditoría sutil del split. Se reportan aparte de las "
        "etiquetas de la muestra.",
    ]
    if manual:
        out += [""]
        out.append(
            _table(
                ["Origen", "Jaccard", "A", "B", "Estado", "Nota"],
                [
                    (
                        e["link"].origen,
                        "—" if e["jaccard"] is None else f"{e['jaccard']:.3f}",
                        e["link"].section_a,
                        e["link"].section_b,
                        e["status"],
                        e["link"].nota or "—",
                    )
                    for e in manual
                ],
            )
        )
    variants = [r for r in records if r["role"] == "variant"]
    out += [
        "",
        f"**Redundancia que queda (costo de no perder contenido):** {len(variants)} variantes con "
        f"{sum(r['tokens'] for r in variants)} tokens; de ellos {red} tokens están en líneas "
        f"compartidas con su canónica = **{red / final_tokens:.1%}** del corpus final "
        f"({final_tokens} tokens).",
    ]
    if variants:
        out += ["", "<details><summary>Líneas únicas que justifican cada variante</summary>", ""]
        for r in variants:
            uniq = r["unique_lines_vs_canonical"]
            out += [
                f"- `{r['section_id']}` (variante de `{r['variant_of']}`, "
                f"J = {r['jaccard_vs_canonical']:.3f}, {r['match_to_canonical']}): "
                + "; ".join(f"`{u[:90]}`" for u in uniq[:4])
                + (f" … (+{len(uniq) - 4})" if len(uniq) > 4 else "")
            ]
        out += ["", "</details>"]

    # 6. Ejemplos
    out += ["", "## 6. Ejemplos de pares casi-duplicados", ""]
    merged = sorted(diag["edges"].items(), key=lambda x: x[1])
    picks: list[tuple[str, tuple[str, str], float]] = []
    if merged:
        idx = sorted({0, len(merged) // 3, (2 * len(merged)) // 3, len(merged) - 1})
        role = {r["section_id"]: r["role"] for r in records}
        picks += [
            (
                "mismo cluster → "
                + (
                    "variante (aporta líneas nuevas)"
                    if role.get(merged[i][0][1]) == "variant"
                    or role.get(merged[i][0][0]) == "variant"
                    else "absorbida en la canónica"
                ),
                merged[i][0],
                merged[i][1],
            )
            for i in idx
        ]
    if border:
        picks.append(("rechazado (bajo el umbral)", border[0][1], border[0][0]))
    seen: set[tuple[str, str]] = set()
    for label, (a, b), j in picks[: d.n_diff_examples]:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        out += [
            f"### Jaccard {j:.3f} — {label}",
            "",
            f"- A: `{_short(reps[a])}` ({reps[a]['version_dir']})",
            f"- B: `{_short(reps[b])}` ({reps[b]['version_dir']})",
            "",
            "````diff",
            _diff(reps[a], reps[b]),
            "````",
            "",
        ]

    # 7. Versiones
    out += ["## 7. Versiones: declarada vs. efectiva (por contenido)", ""]
    out.append(
        "La versión efectiva de una carpeta alias (`latest`) es la carpeta concreta con "
        "contenido idéntico (mismo conjunto de hashes de sección); si no existe, se usa la "
        "declarada en `documentationTypes.json`."
    )
    out += [""]
    out.append(
        _table(
            [
                "Carpeta",
                "Declarada",
                "Efectiva",
                "Idéntica a",
                "Más parecida (Jaccard)",
                "Observación",
            ],
            [
                (
                    k,
                    v["declared_version"],
                    v["effective_version"],
                    ", ".join(v["identical_to"]) or "—",
                    f"{v['most_similar']} ({v['most_similar_jaccard']:.2f})"
                    if v["most_similar"]
                    else "—",
                    "; ".join(v["issues"]) or "ok",
                )
                for k, v in versions.items()
            ],
        )
    )

    out += ["", threshold_section]

    out += [
        "",
        "## Salidas",
        "",
        "- `sections_dedup.jsonl`: secciones canónicas y variantes con `occurrences` "
        "(proyecto, versión declarada/efectiva, archivo, `section_path`, tipo de match).",
        "- `cluster_id` agrupa duplicados exactos y casi-duplicados: "
        "**es la clave del split train/eval**.",
        "- `versions.json`, `nav.jsonl`, `normalized_docs.jsonl`, `sections.jsonl` "
        "en `processed_dir`.",
        f"- `{PAIRS_FILE}`: pares de representantes con Jaccard ≥ "
        f"{cfg.labels.review_min_jaccard} (insumo de `label-pairs` y `validate-threshold`).",
        "",
    ]
    return "\n".join(out)


METHOD_TEXT = {
    "config": "fijo en la config (`dedup.near_dup_threshold`)",
    "labels": "etiquetas humanas: punto medio (en la grilla) del intervalo con mejor F1",
    "valley": "valle: punto medio del hueco sin pares más ancho en el Jaccard de los "
    "candidatos LSH",
    "fallback": "fallback (`dedup.threshold_fallback`): no hay etiquetas suficientes ni valle",
}


def _threshold_choice_lines(choice: ThresholdChoice, d: Any) -> list[str]:
    """Cómo se eligió el umbral (también en versions.json) e histograma de candidatos."""
    lo, hi = d.threshold_bounds
    valley = (
        f"[{choice.valley[0]:.3f}, {choice.valley[1]:.3f}] (ancho {choice.valley_width:.3f})"
        if choice.valley
        else "—"
    )
    out = [
        f"- Método: **{choice.method}**, {METHOD_TEXT[choice.method]}"
        + (f"; {choice.detail}" if choice.detail else "")
        + ".",
        f"- Valle más ancho en [{lo}, {hi}]: {valley}; se exige ancho ≥ {d.min_valley_width}.",
    ]
    if choice.method == "fallback":
        out.append(
            "- ⚠️ **Sin valle claro**: conviene etiquetar pares (`meli-etl label-pairs`) y "
            "recalibrar."
        )
    total = choice.n_candidates
    out += [
        "",
        f"**Jaccard de los {total} candidatos LSH** (insumo del valle)",
        "",
        _table(
            ["Jaccard", "Pares", ""],
            [
                (r, n, _bar(n, max([n for _, n in choice.histogram] + [1])))
                for r, n in choice.histogram
            ],
        ),
    ]
    return out


def write_pairs(
    all_pairs: dict[tuple[str, str], float],
    cluster_of: dict[str, str],
    min_j: float,
    path: Path,
) -> int:
    """Pares (a < b) con Jaccard ≥ min_j, ordenados por pair_id; `same_cluster` indica si
    el clustering final (umbral + must-link) los agrupa."""
    rows = sorted(
        (
            {
                "pair_id": pair_id(a, b),
                "a": a,
                "b": b,
                "jaccard": j,
                "same_cluster": cluster_of[a] == cluster_of[b],
            }
            for (a, b), j in all_pairs.items()
            if j >= min_j
        ),
        key=lambda r: r["pair_id"],
    )
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def _labels(cfg: Config) -> dict[str, str]:
    """pair_id → etiqueta humana (vacío si no hay etiquetas o son inválidas)."""
    path = cfg.paths.labels_dir / LABELS_FILE
    if not path.exists():
        return {}
    try:
        return {r["pair_id"]: r["label"] for r in checked_labels(path) if r["label"]}
    except ValueError as exc:
        log.warning("Etiquetas no utilizables, sin must-link: %s", exc)
        return {}


def _manual_links(cfg: Config) -> list[ManualLink]:
    try:
        return read_manual_links(cfg.paths.labels_dir / MANUAL_LINKS_FILE)
    except ValueError as exc:
        log.warning("Must-links manuales no utilizables: %s", exc)
        return []


def _threshold_section(cfg: Config) -> str:
    """§8: validación con etiquetas si existen; si no, instrucciones."""
    labels_rel = display_path(cfg.paths.labels_dir / LABELS_FILE)
    try:
        v = build_validation(cfg)
    except FileNotFoundError:
        return render_threshold_section(None, cfg, labels_rel)
    except ValueError as exc:
        log.warning("Etiquetas no utilizables: %s", exc)
        return render_threshold_section(None, cfg, labels_rel, f"Etiquetas no utilizables: {exc}")
    if not (v.counts["same"] + v.counts["diff"]):
        return render_threshold_section(None, cfg, labels_rel)
    return render_threshold_section(v, cfg, labels_rel)


def run(cfg: Config) -> Path:
    processed = cfg.paths.processed_dir
    docs = _read_jsonl(processed / DOCS_FILE)
    sections = _read_jsonl(processed / SECTIONS_FILE)
    stats_path = processed / STATS_FILE
    norm_stats = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.exists() else {}

    versions = resolve_versions(sections)
    kept = [s for s in sections if s["kept"]]
    log.info("Dedup de %d secciones", len(kept))
    labels = _labels(cfg)
    must_link = {pid for pid, label in labels.items() if label == "same"}
    manual_links = _manual_links(cfg)
    records, diag = dedup_sections(kept, versions, cfg, must_link, manual_links, labels)
    choice: ThresholdChoice = diag["threshold"]
    log.info(
        "Umbral de casi-duplicados: %s (método %s; valle %s, ancho %s)",
        choice.threshold,
        choice.method,
        choice.valley,
        choice.valley_width,
    )
    for e in diag["manual_links"]:
        if e["status"] != "unidas":
            log.warning(
                "Must-link manual %s ↔ %s: %s",
                e["link"].section_a,
                e["link"].section_b,
                e["status"],
            )
    for pid in diag["missing_links"]:
        log.warning("Etiqueta `same` de un par que ya no existe (se ignora): %s", pid)

    with open(processed / DEDUP_FILE, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    (processed / VERSIONS_FILE).write_text(
        json.dumps(
            {**versions, THRESHOLD_KEY: choice.to_json()},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    write_pairs(
        diag["all_pairs"], diag["cluster_of"], cfg.labels.review_min_jaccard, processed / PAIRS_FILE
    )
    log.info(
        "Secciones: %d → %d grupos exactos → %d finales (%d variantes); %d pares casi-dup",
        len(kept),
        len(diag["reps"]),
        len(records),
        sum(r["role"] == "variant" for r in records),
        len(diag["edges"]),
    )
    for k, v in versions.items():
        for issue in v["issues"]:
            log.warning("Versión %s: %s", k, issue)

    cfg.paths.reports_dir.mkdir(parents=True, exist_ok=True)
    report = cfg.paths.reports_dir / "dedup.md"
    report.write_text(
        render_report(
            docs, sections, records, diag, versions, norm_stats, cfg, _threshold_section(cfg)
        ),
        encoding="utf-8",
    )
    log.info("Reporte escrito en %s", display_path(report))
    return report
