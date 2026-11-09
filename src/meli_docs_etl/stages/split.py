"""Etapa 5 — split train / eval_section / eval_project por split_group.

Lee `<outputs_dir>/corpus.jsonl` (chunk), asigna cada split_group a un split y escribe:
- el mismo corpus con el campo `split` (los chunk_id no cambian);
- `<splits_dir>/manifest.json` (versionado): congela la asignación. Las corridas siguientes
  conservan el split de los grupos existentes y solo asignan los nuevos;
- `<reports_dir>/split.md`: tamaños, estratificación, estabilidad y auditoría de fuga.

La etapa falla (sin escribir corpus ni manifiesto) si hay fuga dura, o si cambió algún
parámetro del split sin `--rebuild`.
"""

from __future__ import annotations

import json
import logging
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from meli_docs_etl.config import Config, display_path
from meli_docs_etl.split_utils import (
    EVAL_PROJECT,
    EVAL_SECTION,
    PARAM_KEYS,
    SPLITS,
    TRAIN,
    Assignment,
    Group,
    HardAudit,
    assign,
    audit_hard,
    build_groups,
    cross_split_similar,
    endpoint_leaks,
    files_across,
    group_hash,
    occurrence_keys,
)
from meli_docs_etl.stages.chunk import CORPUS_FILE

log = logging.getLogger(__name__)

MANIFEST_FILE = "manifest.json"
Chunk = dict[str, Any]


class SplitError(RuntimeError):
    pass


def params_of(cfg: Config) -> dict[str, Any]:
    s = cfg.split
    values = {
        "seed": cfg.seed,
        "eval_project": s.eval_project,
        "eval_section_fraction": s.eval_section_fraction,
        "tolerance": s.tolerance,
        "min_groups_per_stratum": s.min_groups_per_stratum,
    }
    return {k: values[k] for k in PARAM_KEYS}


def read_corpus(path: Path) -> list[Chunk]:
    if not path.exists():
        raise FileNotFoundError(f"{path} no existe: corré antes `meli-etl chunk`.")
    with open(path, encoding="utf-8") as fh:
        chunks = [json.loads(line) for line in fh]
    for ch in chunks:
        ch.pop("split", None)  # se recalcula siempre desde el manifiesto
    return chunks


def project_table(chunks: list[Chunk]) -> list[list[Any]]:
    total = sum(ch["n_tokens"] for ch in chunks) or 1
    by: dict[str, list[Chunk]] = defaultdict(list)
    for ch in chunks:
        by[ch["project"]].append(ch)
    rows = []
    for p, cs in sorted(by.items(), key=lambda x: (-sum(c["n_tokens"] for c in x[1]), x[0])):
        tok = sum(c["n_tokens"] for c in cs)
        lang: Counter = Counter()
        for c in cs:
            lang[c["language"]] += c["n_tokens"]
        top = ", ".join(f"{k} {v / tok:.0%}" for k, v in lang.most_common(2))
        rows.append(
            [
                p,
                len(cs),
                tok,
                f"{tok / total:.1%}",
                top,
                sum(c["source_type"] == "openapi" for c in cs),
                len({c["split_group"] for c in cs}),
            ]
        )
    return rows


def _manifest(
    groups: dict[str, Group],
    asg: Assignment,
    params: dict[str, Any],
    history: list[dict[str, Any]],
) -> dict:
    return {
        "_nota": "Generado por `meli-etl split`. NO editar a mano (README «Split y manifiesto»).",
        "params": params,
        # Historial versionado de cambios del conjunto de eval (sin fechas: determinista).
        "eval_changes": history,
        "groups": {
            gid: {
                "split": asg.split[gid],
                "projects": g.projects,
                "source_type": g.source_type,
                "tokens": g.tokens,
                "cluster_ids": g.cluster_ids,
                "chunk_ids": g.chunk_ids,
                "keys": g.keys,
            }
            for gid, g in sorted(groups.items())
        },
    }


def run(cfg: Config, rebuild: bool = False) -> Path:
    corpus_path = cfg.paths.outputs_dir / CORPUS_FILE
    chunks = read_corpus(corpus_path)
    held = cfg.split.eval_project
    projects = sorted({ch["project"] for ch in chunks})
    if not held or held not in projects:
        table = "\n".join("  " + " | ".join(str(v) for v in row) for row in project_table(chunks))
        raise SplitError(
            f"split.eval_project = {held!r} no es un proyecto del corpus. Elegí uno "
            f"(proyecto | fichas | tokens | % | idioma | OpenAPI | grupos):\n{table}"
        )

    params = params_of(cfg)
    manifest_path = cfg.paths.splits_dir / MANIFEST_FILE
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    )
    if manifest and not rebuild and manifest["params"] != params:
        diff = ", ".join(
            f"{k}: {manifest['params'].get(k)!r} → {params[k]!r}"
            for k in PARAM_KEYS
            if manifest["params"].get(k) != params[k]
        )
        raise SplitError(
            f"Cambiaron parámetros del split ({diff}). Esto genera un conjunto de eval nuevo y "
            "los resultados anteriores dejan de ser comparables: si es intencional, corré "
            "`meli-etl split --rebuild` (o `make split-rebuild`)."
        )

    groups = build_groups(chunks)
    previous = None if (rebuild or not manifest) else manifest["groups"]
    asg = assign(groups, params, previous)
    for ch in chunks:
        ch["split"] = asg.split[ch["split_group"]]

    hard = audit_hard(chunks, held)
    events: list[dict[str, Any]] = []
    for change in asg.changes:
        # Fichas actuales (ya en train) con contenido que antes estaba en eval.
        left = set(change.left_eval_keys)
        left_chunks = sorted(
            ch["chunk_id"]
            for ch in chunks
            if ch["split_group"] == change.group_id and occurrence_keys(ch) & left
        )
        log.warning(
            "Cambio del conjunto de eval: el grupo %s une contenido de splits distintos "
            "(%s) y va a train; pasan de eval a train %d fichas: %s (secciones: %s)",
            change.group_id,
            ", ".join(f"{g}={s}" for g, s in change.previous.items()),
            len(left_chunks),
            ", ".join(left_chunks),
            ", ".join(change.left_eval_keys),
        )
        events.append(
            {
                "tipo": "union_entre_splits",
                "grupo": change.group_id,
                "antes": change.previous,
                "fichas_que_salen": left_chunks,
                "secciones_que_salen": change.left_eval_keys,
            }
        )
    for g, sp in asg.removed.items():
        if sp == TRAIN:
            continue
        gone = manifest["groups"][g]["chunk_ids"]
        log.warning("Cambio del conjunto de eval: el grupo %s (%s) ya no existe", g, sp)
        events.append(
            {"tipo": "grupo_eliminado", "grupo": g, "split": sp, "fichas_que_salen": gone}
        )
    rebuilt_diff = None
    if rebuild and manifest:
        old = {
            c for g in manifest["groups"].values() if g["split"] != TRAIN for c in g["chunk_ids"]
        }
        new = {ch["chunk_id"] for ch in chunks if ch["split"] != TRAIN}
        rebuilt_diff = (len(old - new), len(new - old))
        if any(rebuilt_diff):
            log.warning(
                "--rebuild: conjunto de eval nuevo (%d fichas salieron, %d entraron); los "
                "resultados de evaluación anteriores dejan de ser comparables",
                *rebuilt_diff,
            )
            events.append(
                {"tipo": "rebuild", "salieron": rebuilt_diff[0], "entraron": rebuilt_diff[1]}
            )
        else:
            log.info("--rebuild: el conjunto de eval resultó idéntico al del manifiesto anterior")
    history = list(manifest.get("eval_changes", [])) if manifest else []
    for e in events:
        history.append({"n": len(history) + 1, **e})

    cfg.paths.reports_dir.mkdir(parents=True, exist_ok=True)
    report = cfg.paths.reports_dir / "split.md"
    report.write_text(
        render_report(
            chunks, groups, asg, hard, cfg, previous is not None, rebuilt_diff, events, history
        ),
        encoding="utf-8",
    )
    log.info("Reporte escrito en %s", display_path(report))
    if not hard.ok:
        raise SplitError(
            "Fuga dura en el split (ver reports/split.md §4); no se escribió el corpus: "
            f"grupos={hard.groups_split} clusters={hard.clusters_split} "
            f"sin_split={hard.unassigned} retenido_fuera={hard.held_out_outside}"
        )

    with open(corpus_path, "w", encoding="utf-8") as fh:
        for ch in chunks:
            fh.write(json.dumps(ch, ensure_ascii=False, sort_keys=True) + "\n")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            _manifest(groups, asg, params, history), ensure_ascii=False, indent=1, sort_keys=True
        )
        + "\n",
        encoding="utf-8",
    )
    counts = Counter(ch["split"] for ch in chunks)
    log.info(
        "Split: %s | manifiesto %s",
        ", ".join(f"{s}={counts[s]}" for s in SPLITS),
        display_path(manifest_path),
    )
    return corpus_path


# --------------------------------------------------------------------------- reporte


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    def cell(v: Any) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    return out + ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]


def _pct(a: float, b: float) -> str:
    return f"{a / b:.1%}" if b else "—"


def _breakdown(chunks: list[Chunk], key: str) -> list[list[Any]]:
    tok: dict[str, Counter] = defaultdict(Counter)
    for ch in chunks:
        tok[ch[key]][ch["split"]] += ch["n_tokens"]
    totals = Counter()
    for c in tok.values():
        totals.update(c)
    rows = []
    for k, c in sorted(tok.items(), key=lambda x: (-sum(x[1].values()), x[0])):
        row = [k]
        for s in SPLITS:
            row.append(f"{c[s]} ({_pct(c[s], totals[s])})")
        row.append(_pct(c[EVAL_SECTION], c[TRAIN] + c[EVAL_SECTION]))
        rows.append(row)
    return rows


def _preview(ch: Chunk, n: int = 12) -> list[str]:
    lines = ch["contextualized_text"].split("\n")
    body = "\n".join(lines[:n]) + (f"\n… ({len(lines) - n} líneas más)" if len(lines) > n else "")
    longest = max((len(x) for x in body.split() if set(x) == {"`"}), default=0)
    fence = "`" * max(4, longest + 1)
    return [
        f"`{ch['chunk_id']}` · **{ch['split']}** · {ch['n_tokens']} tokens · `{ch['split_group']}`",
        "",
        f"{fence}markdown",
        body,
        fence,
        "",
    ]


def _describe(e: dict[str, Any]) -> str:
    if e["tipo"] == "union_entre_splits":
        prev = ", ".join(f"`{g}` ({sp})" for g, sp in e["antes"].items())
        return (
            f"el grupo `{e['grupo']}` une contenido de splits distintos ({prev}) y va a "
            f"**train** para no filtrar; pasan de eval a train {len(e['fichas_que_salen'])} "
            "fichas: "
            + ", ".join(f"`{c}`" for c in e["fichas_que_salen"])
            # Entradas anteriores a este campo no lo tienen (el historial no se reescribe).
            + (
                " (secciones: " + ", ".join(f"`{s}`" for s in e["secciones_que_salen"]) + ")"
                if "secciones_que_salen" in e
                else ""
            )
        )
    if e["tipo"] == "grupo_eliminado":
        return (
            f"el grupo `{e['grupo']}` ({e['split']}) ya no existe en el corpus; salen del eval "
            + ", ".join(f"`{c}`" for c in e["fichas_que_salen"])
        )
    return (
        f"`--rebuild`: conjunto de eval nuevo ({e['salieron']} fichas salieron, "
        f"{e['entraron']} entraron)"
    )


def pure_hash_range(groups: dict[str, Group], held: str, frac: float, seeds: int = 200):
    """% de tokens en eval_section con hash puro (h < frac), sobre `seeds` semillas."""
    pool = [g for g in groups.values() if held not in g.projects]
    total = sum(g.tokens for g in pool) or 1
    shares = [
        sum(g.tokens for g in pool if group_hash(seed, g.id) < frac) / total
        for seed in range(seeds)
    ]
    return min(shares), max(shares), statistics.mean(shares), len(pool)


def render_report(
    chunks: list[Chunk],
    groups: dict[str, Group],
    asg: Assignment,
    hard: HardAudit,
    cfg: Config,
    from_manifest: bool,
    rebuilt_diff: tuple[int, int] | None,
    events: list[dict[str, Any]] = (),
    history: list[dict[str, Any]] = (),
) -> str:
    s = cfg.split
    held = s.eval_project
    by_id = {ch["chunk_id"]: ch for ch in chunks}
    tok = Counter()
    n = Counter()
    grp = defaultdict(set)
    for ch in chunks:
        tok[ch["split"]] += ch["n_tokens"]
        n[ch["split"]] += 1
        grp[ch["split"]].add(ch["split_group"])
    total = sum(tok.values())
    pool_tok = tok[TRAIN] + tok[EVAL_SECTION]
    lo, hi = s.eval_section_fraction - s.tolerance, s.eval_section_fraction + s.tolerance

    out = [
        "# Split train / eval",
        "",
        f"Generado por `meli-etl split`. Unidad: `split_group`. Proyecto retenido "
        f"(`eval_project`): **{held}**. eval_section: {s.eval_section_fraction:.1%} de los tokens "
        f"de cada estrato (proyecto × source_type), tolerancia ±{s.tolerance:.0%}, orden "
        f"`sha256(seed={cfg.seed}|split_group)`. Manifiesto: "
        f"`{display_path(cfg.paths.splits_dir / MANIFEST_FILE)}`.",
        "",
        "## 1. Tamaños por split",
        "",
    ]
    out += _table(
        ["Split", "Fichas", "Tokens", "% tokens", "split_groups", "Para qué"],
        [
            [
                f"`{TRAIN}`",
                n[TRAIN],
                tok[TRAIN],
                _pct(tok[TRAIN], total),
                len(grp[TRAIN]),
                "entrenamiento (CPT/SFT/RL)",
            ],
            [
                f"`{EVAL_SECTION}`",
                n[EVAL_SECTION],
                tok[EVAL_SECTION],
                _pct(tok[EVAL_SECTION], total),
                len(grp[EVAL_SECTION]),
                "¿aprendió el contenido de proyectos que vio?",
            ],
            [
                f"`{EVAL_PROJECT}`",
                n[EVAL_PROJECT],
                tok[EVAL_PROJECT],
                _pct(tok[EVAL_PROJECT], total),
                len(grp[EVAL_PROJECT]),
                "¿generaliza a documentación nueva? (caso RAG)",
            ],
            ["**Total**", len(chunks), total, "100%", len(groups), ""],
        ],
    )
    share = tok[EVAL_SECTION] / pool_tok if pool_tok else 0
    status = "✅ dentro" if lo <= share <= hi else "⚠️ fuera"
    out += [
        "",
        f"**eval_section sobre los proyectos no retenidos: {share:.1%}** de "
        f"{pool_tok} tokens (objetivo {s.eval_section_fraction:.1%}, rango "
        f"[{lo:.1%}, {hi:.1%}]: {status}).",
    ]

    # 2. Distribución
    out += ["", "## 2. Estratificación: objetivo vs logrado", ""]
    strata: dict[tuple[str, str], list[Group]] = defaultdict(list)
    for g in groups.values():
        if held not in g.projects:
            strata[g.stratum].append(g)
    rows = []
    for (proj, st), gs in sorted(strata.items()):
        st_tok = sum(g.tokens for g in gs)
        ev = sum(g.tokens for g in gs if asg.split[g.id] == EVAL_SECTION)
        notes = []
        if len(gs) < s.min_groups_per_stratum:
            word = "grupo" if len(gs) == 1 else "grupos"
            notes.append(f"estrato chico ({len(gs)} {word} < {s.min_groups_per_stratum}) → train")
        big = [g for g in gs if g.tokens > (s.eval_section_fraction + s.tolerance) * st_tok]
        if big and len(gs) >= s.min_groups_per_stratum:
            notes.append(
                "no entra en la cuota: " + ", ".join(f"`{g.id}` ({g.tokens} tok)" for g in big)
            )
        dev = ev / st_tok - s.eval_section_fraction if st_tok else 0
        rows.append(
            [proj, st, len(gs), st_tok, ev, _pct(ev, st_tok), f"{dev:+.1%}", "; ".join(notes)]
        )
    out += _table(
        ["Proyecto", "Tipo", "Grupos", "Tokens", "eval_section", "Logrado", "vs objetivo", "Nota"],
        rows,
    )
    zen = max(groups.values(), key=lambda g: (len(g.chunk_ids), g.id))
    out += [
        "",
        f"El grupo más grande (`{zen.id}`, {len(zen.chunk_ids)} fichas, {zen.tokens} tokens, "
        f"{zen.projects[0]}) quedó en **{asg.split[zen.id]}**: "
        + (
            "es el único grupo de su estrato, así que no hay nada que retener sin vaciarlo."
            if len(strata.get(zen.stratum, [])) < s.min_groups_per_stratum
            else "la cuota lo trata como cualquier grupo y lo saltea si no entra en la tolerancia."
        ),
        "",
        "**Por proyecto** (tokens y % dentro de cada split; última columna = eval_section / "
        "(train + eval_section)):",
        "",
    ]
    out += _table(["Proyecto", *SPLITS, "eval_section"], _breakdown(chunks, "project"))
    out += ["", "**Por idioma:**", ""]
    out += _table(["Idioma", *SPLITS, "eval_section"], _breakdown(chunks, "language"))
    out += ["", "**Por source_type:**", ""]
    out += _table(["Tipo", *SPLITS, "eval_section"], _breakdown(chunks, "source_type"))
    lang_tok: dict[str, Counter] = defaultdict(Counter)
    for ch in chunks:
        lang_tok[ch["project"]][ch["language"]] += ch["n_tokens"]
    spanish = sorted(p for p, c in lang_tok.items() if c["es"] > 0.5 * sum(c.values()))
    out += [
        "",
        "El idioma no es una dimensión de estratificación aparte: depende casi por completo del "
        f"proyecto (en español: {', '.join(spanish) or 'ninguno'}), así que estratificar por "
        "proyecto ya lo balancea; agregarlo crearía estratos de 1–2 fichas.",
    ]

    # 3. Estabilidad
    pmin, pmax, pmean, npool = pure_hash_range(groups, held, s.eval_section_fraction)
    origin = Counter(asg.origin.values())
    out += [
        "",
        "## 3. Estabilidad y manifiesto",
        "",
        "Origen de cada asignación en esta corrida: "
        + ", ".join(
            f"{k} {origin[k]}"
            for k in ("kept", "inherited", "new", "conflict", "held_out")
            if origin[k]
        )
        + (
            " (desde el manifiesto)."
            if from_manifest
            else " (construcción desde cero: primera corrida o `--rebuild`)."
        ),
    ]
    if rebuilt_diff == (0, 0):
        out.append(
            "\n`--rebuild`: el conjunto de eval resultó idéntico al del manifiesto anterior."
        )
    elif rebuilt_diff:
        out.append(
            f"\n⚠️ **`--rebuild`: conjunto de eval nuevo** — {rebuilt_diff[0]} fichas salieron "
            f"del eval y {rebuilt_diff[1]} entraron respecto del manifiesto anterior. Los "
            "resultados de evaluación anteriores dejan de ser comparables."
        )
    out += ["", "**Cambios del conjunto de eval en esta corrida:**", ""]
    out += [f"- ⚠️ **Cambio del conjunto de eval:** {_describe(e)}" for e in events] or ["Ninguno."]
    out += [
        "",
        "**Historial de cambios del conjunto de eval** (guardado en el manifiesto, versionado):",
        "",
    ]
    out += [f"{e['n']}. {_describe(e)}" for e in history] or ["Sin cambios desde la construcción."]
    out += [
        "",
        "**Por qué cuota en orden de hash + manifiesto, y no hash puro.** Con hash puro cada "
        "grupo decide solo (`h(grupo) < fracción`): es perfectamente estable y, con muchos "
        "grupos, la ley de los grandes números deja la proporción cerca del objetivo en cada "
        "estrato, así que a escala bastaría. Acá la muestra es chica "
        f"({npool} grupos de tamaños muy desiguales): simulando 200 semillas, el hash puro deja "
        f"eval_section entre **{pmin:.0%} y {pmax:.0%}** de los tokens (media {pmean:.0%}). La "
        "cuota por estrato fija la proporción; el manifiesto recupera la estabilidad (los grupos "
        "asignados no se mueven al llegar documentos nuevos).",
    ]

    # 4. Auditoría dura
    out += ["", "## 4. Auditoría de fuga dura", ""]
    out += _table(
        ["Chequeo", "Casos", "Resultado"],
        [
            [
                "split_group en más de un split",
                len(hard.groups_split),
                "✅" if not hard.groups_split else "❌ " + ", ".join(hard.groups_split[:10]),
            ],
            [
                "cluster_id en más de un split",
                len(hard.clusters_split),
                "✅" if not hard.clusters_split else "❌ " + ", ".join(hard.clusters_split[:10]),
            ],
            [
                "Fichas sin split",
                len(hard.unassigned),
                "✅" if not hard.unassigned else "❌ " + ", ".join(hard.unassigned[:10]),
            ],
            [
                f"Fichas de {held} fuera de eval_project",
                len(hard.held_out_outside),
                "✅"
                if not hard.held_out_outside
                else "❌ " + ", ".join(hard.held_out_outside[:10]),
            ],
        ],
    )
    out.append("")
    out.append(
        "**Resultado: ✅ sin fuga dura.**"
        if hard.ok
        else "**Resultado: ❌ fuga dura (la etapa falla).**"
    )

    # 5. Auditoría sutil
    thr = cfg.dedup.near_dup_threshold
    sim = cross_split_similar(chunks, s.audit_jaccard_min, cfg.dedup.shingle_size)
    high = [x for x in sim if x[0] >= thr]
    out += [
        "",
        "## 5. Auditoría de fuga sutil (para revisión, no falla)",
        "",
        f"### 5.1 Fichas parecidas en splits distintos (Jaccard ≥ {s.audit_jaccard_min})",
        "",
        f"- **≥ {thr} (umbral de dedup):** {len(high)} pares. Dedup agrupa secciones; una ficha "
        "fusionada podría combinarlas de forma que supere el umbral sin compartir cluster.",
        f"- **[{s.audit_jaccard_min}, {thr}):** {len(sim) - len(high)} pares — plantilla o "
        "contenido compartido que dedup no considera duplicado (la §8 de dedup.md valida esa "
        "zona con etiquetas humanas).",
        "",
    ]
    if sim:
        out += _table(
            ["Jaccard", "Ficha A", "Split A", "Ficha B", "Split B"],
            [
                [
                    f"{j:.3f}",
                    f"{by_id[a]['source_path']} › {' › '.join(by_id[a]['section_path'][-1:])}",
                    by_id[a]["split"],
                    f"{by_id[b]['source_path']} › {' › '.join(by_id[b]['section_path'][-1:])}",
                    by_id[b]["split"],
                ]
                for j, a, b in sim[:20]
            ],
        )
    eps = endpoint_leaks(chunks)
    out += [
        "",
        "### 5.2 Endpoints del swagger mencionados en un .md de otro split",
        "",
        f"{len(eps)} casos (mismo proyecto; el path del .md coincide con el del swagger o es un "
        "sufijo de ≥ 2 segmentos, con `{param}` normalizado). Una pregunta de eval sobre la "
        "operación puede responderse con lo visto en train.",
        "",
    ]
    if eps:
        out += _table(
            ["Proyecto", "Endpoint (swagger)", "Split", "Mención en .md", "Ficha .md", "Split"],
            [
                [
                    e.project,
                    e.endpoint,
                    e.openapi_split,
                    e.mentioned_as,
                    f"{by_id[e.markdown_chunk]['source_path']} (parte "
                    f"{by_id[e.markdown_chunk]['part']})",
                    e.markdown_split,
                ]
                for e in eps
            ],
        )
    across = files_across(chunks)
    n_eval_files = len({ch["source_path"] for ch in chunks if ch["split"] == EVAL_SECTION})
    out += [
        "",
        "### 5.3 Archivos con fichas en train y en eval_section",
        "",
        f"{len(across)} de {n_eval_files} archivos con fichas en eval_section también tienen "
        "fichas en train (permitido: son secciones distintas, pero comparten contexto).",
        "",
    ]
    if across:
        out += _table(
            ["Archivo", "train", "eval_section"],
            [[f, c.get(TRAIN, 0), c.get(EVAL_SECTION, 0)] for f, c in across.items()],
        )

    # 6. Ejemplos
    out += ["", "## 6. Ejemplos", ""]
    ev = sorted(
        (ch for ch in chunks if ch["split"] == EVAL_SECTION and ch["source_path"] in across),
        key=lambda c: (c["source_path"], c["chunk_id"]),
    )
    if ev:
        e = ev[0]
        neighbor = min(
            (c for c in chunks if c["source_path"] == e["source_path"] and c["split"] == TRAIN),
            key=lambda c: c["chunk_id"],
        )
        out += ["### eval_section y su vecina de train (mismo archivo)", ""]
        out += _preview(e) + _preview(neighbor)
    ep = sorted((c for c in chunks if c["split"] == EVAL_PROJECT), key=lambda c: c["chunk_id"])
    if ep:
        out += ["### eval_project", ""] + _preview(ep[len(ep) // 2])
    if sim:
        j, a, b = sim[0]
        out += [f"### Par sutil más alto (Jaccard {j:.3f})", ""]
        out += _preview(by_id[a]) + _preview(by_id[b])

    # 7. Validación
    out += [
        "",
        "## 7. Validación para entrenamiento (no se crea acá)",
        "",
        "Se saca de `train` con el mismo algoritmo y una sal distinta, así también respeta "
        "split_groups enteros: ordenar los grupos de train de cada estrato por "
        "`sha256(seed|val|split_group)` y tomar ~10% de los tokens. Las Q&A heredan el split de "
        "su ficha, así que la validación no comparte clusters con train ni con los eval.",
        "",
    ]
    return "\n".join(out)
