"""Validación del umbral de casi-duplicados con etiquetas humanas.

Lee `<labels_dir>/near_dup_labels.csv` (etiquetas) y `<processed_dir>/near_dup_pairs.jsonl`
(Jaccard de cada par, escrito por dedup), barre la grilla de umbrales de la config y
reemplaza la sección §8 de `reports/dedup.md` (entre marcadores, para que `dedup` y este
comando produzcan el mismo bloque).
"""

from __future__ import annotations

import csv
import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from meli_docs_etl.config import Config, display_path
from meli_docs_etl.threshold_validation import (
    LABELS,
    Fragility,
    Recommendation,
    ThresholdRow,
    evaluate_predictions,
    fragility,
    recommend,
    sweep,
    threshold_grid,
)

log = logging.getLogger(__name__)

PAIRS_FILE = "near_dup_pairs.jsonl"
LABELS_FILE = "near_dup_labels.csv"
REVIEW_FILE = "near_dup_review.md"
LABEL_COLUMNS = ("pair_id", "label", "nota")
MARK_START = "<!-- threshold-validation:start -->"
MARK_END = "<!-- threshold-validation:end -->"


def read_pairs(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"{path} no existe: corré antes `meli-etl dedup`.")
    with open(path, encoding="utf-8") as fh:
        return {p["pair_id"]: p for p in map(json.loads, fh)}


def read_labels(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as fh:
        return [
            {k: (row.get(k) or "").strip() for k in LABEL_COLUMNS} for row in csv.DictReader(fh)
        ]


def checked_labels(path: Path) -> list[dict[str, str]]:
    """Etiquetas en minúsculas; ValueError si alguna no es same/diff/unsure."""
    rows = read_labels(path)
    invalid = [r["pair_id"] for r in rows if r["label"] and r["label"].lower() not in LABELS]
    if invalid:
        raise ValueError(
            f"Etiquetas inválidas en {len(invalid)} pares ({', '.join(invalid[:10])}); "
            f"valores permitidos: {', '.join(LABELS)}."
        )
    return [{**r, "label": r["label"].lower()} for r in rows]


def same_pair_ids(path: Path) -> set[str]:
    """pair_ids etiquetados `same`: dedup los usa como must-link."""
    return {r["pair_id"] for r in checked_labels(path) if r["label"] == "same"}


@dataclass
class Validation:
    n_pairs: int
    counts: Counter
    n_unlabeled: int
    missing: list[str]
    current: float
    same_js: list[float] = field(default_factory=list)
    diff_js: list[float] = field(default_factory=list)
    rows: list[ThresholdRow] = field(default_factory=list)
    rec: Recommendation | None = None
    frag: Fragility | None = None
    critical: list[dict[str, Any]] = field(default_factory=list)
    # Clustering final de dedup (umbral actual + must-link) evaluado contra las etiquetas.
    final: ThresholdRow | None = None
    # Pares etiquetados con su Jaccard, rutas y si el clustering final los agrupa.
    labeled: list[dict[str, Any]] = field(default_factory=list)


def build_validation(cfg: Config) -> Validation:
    """Cruza etiquetas con Jaccard. FileNotFoundError si faltan archivos; ValueError si
    hay etiquetas inválidas."""
    pairs = read_pairs(cfg.paths.processed_dir / PAIRS_FILE)
    labels_path = cfg.paths.labels_dir / LABELS_FILE
    if not labels_path.exists():
        raise FileNotFoundError(f"{labels_path} no existe: corré antes `meli-etl label-pairs`.")
    labeled: list[dict[str, Any]] = []
    missing, n_unlabeled = [], 0
    for r in checked_labels(labels_path):
        if not r["label"]:
            n_unlabeled += 1
        elif r["pair_id"] not in pairs:
            missing.append(r["pair_id"])
        else:
            labeled.append({**pairs[r["pair_id"]], **r})
    labeled.sort(key=lambda x: (-x["jaccard"], x["pair_id"]))
    js = [(x["jaccard"], x["label"]) for x in labeled]

    current = cfg.dedup.near_dup_threshold
    v = Validation(
        n_pairs=len(pairs),
        counts=Counter(label for _, label in js),
        n_unlabeled=n_unlabeled,
        missing=missing,
        current=current,
        same_js=sorted(j for j, label in js if label == "same"),
        diff_js=sorted(j for j, label in js if label == "diff"),
        labeled=labeled,
    )
    lc = cfg.labels
    grid = threshold_grid(lc.grid_start, lc.grid_stop, lc.grid_step)
    v.rows = sweep(js, grid)
    v.final = evaluate_predictions([(x["same_cluster"], x["label"]) for x in labeled], current)
    if v.same_js:
        v.rec = recommend(v.rows, lc.recall_priority)
        v.frag = fragility(js, grid, lc.recall_priority, lc.min_same_pairs)
        v.critical = [labeled[i] for i in v.frag.critical]
    return v


# --------------------------------------------------------------------------- reporte


def _nota(x: dict[str, Any]) -> str:
    return x["nota"].replace("|", "\\|") or "—"


def _fmt(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}"


def _render_body(v: Validation, labels_rel: str, cfg: Config) -> list[str]:
    c = v.counts
    n_eval = c["same"] + c["diff"]
    out = [
        f"Etiquetas humanas en `{labels_rel}` sobre los {v.n_pairs} pares de representantes con "
        f"Jaccard ≥ {cfg.labels.review_min_jaccard} (revisión ciega: el archivo de revisión no "
        "muestra el Jaccard y los pares están en orden aleatorio).",
        "",
        "| `same` | `diff` | `unsure` (excluidos) | Sin etiquetar | Sin par (ya no existe) |",
        "|---|---|---|---|---|",
        f"| {c['same']} | {c['diff']} | {c['unsure']} | {v.n_unlabeled} | {len(v.missing)} |",
        "",
    ]
    if not v.same_js:
        return out + [
            f"Sin pares `same` etiquetados ({n_eval} evaluables): el recall no está definido y "
            "no se puede recomendar un umbral."
        ]

    if v.diff_js:
        lo_same, hi_diff = v.same_js[0], v.diff_js[-1]
        sep = (
            f"las clases son **separables**: cualquier umbral en ({hi_diff:.3f}, {lo_same:.3f}] "
            "las divide sin errores"
            if hi_diff < lo_same
            else "las clases **se solapan**: ningún umbral las divide sin errores"
        )
        out.append(
            f"- `same` con menor Jaccard: **{lo_same:.3f}**; `diff` con mayor Jaccard: "
            f"**{hi_diff:.3f}** → {sep}."
        )
    else:
        out.append(f"- `same` con menor Jaccard: **{v.same_js[0]:.3f}**; no hay pares `diff`.")
    out += [
        "- Predicción: casi-duplicado si Jaccard ≥ umbral. Positivo real = `same`. "
        "`unsure ≥ t` = pares `unsure` que ese umbral agruparía.",
        "",
    ]

    rec_t = v.rec.row.threshold if v.rec else None
    table = [
        "| Umbral | TP | FP | FN | TN | Precisión | Recall | F1 | `unsure` ≥ t | |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in v.rows:
        tags = []
        if abs(r.threshold - v.current) < 1e-9:
            tags.append("actual")
        if rec_t is not None and abs(r.threshold - rec_t) < 1e-9:
            tags.append("**recomendado**")
        table.append(
            f"| {r.threshold:.2f} | {r.tp} | {r.fp} | {r.fn} | {r.tn} | {_fmt(r.precision)} | "
            f"{_fmt(r.recall)} | {_fmt(r.f1)} | {r.unsure_above} | {' · '.join(tags)} |"
        )
    out += table
    f = v.final
    out += [
        "",
        f"**Clustering final de `dedup`** (umbral {v.current:.2f} + must-link de los `same`): "
        f"TP {f.tp} · FP {f.fp} · FN {f.fn} · TN {f.tn} · precisión {_fmt(f.precision)} · "
        f"recall {_fmt(f.recall)} · F1 {_fmt(f.f1)}. La tabla de arriba mide solo el umbral; "
        "acá se mide lo que realmente usa el split.",
    ]

    if v.rec and v.frag:
        r, fr = v.rec.row, v.frag
        lo, hi = v.rec.equivalent
        current_in = lo - 1e-9 <= v.current <= hi + 1e-9
        criterion = (
            "el umbral más alto que mantiene el **recall máximo**"
            if cfg.labels.recall_priority
            else "el umbral con mejor F1"
        )
        out += [
            "",
            "### Recomendación",
            "",
            f"**Umbral recomendado: {r.threshold:.2f}** (recall {_fmt(r.recall)}, precisión "
            f"{_fmt(r.precision)}, F1 {_fmt(r.f1)}; n = {n_eval} pares evaluables, "
            f"{r.tp + r.fn} `same`)" + (" — **frágil, ver avisos**." if fr.fragile else "."),
            "",
            f"- **Criterio**: {criterion}; todos los umbrales en **[{lo:.2f}, {hi:.2f}]** dan "
            f"la misma matriz de confusión, así que con estas etiquetas son indistinguibles. "
            "Se recomienda el punto medio del intervalo (hacia abajo en la grilla) para dejar "
            "margen a ambos lados frente a pares que no están en el set etiquetado.",
            "- **Por qué priorizar recall**: un falso negativo (misma sección en otra versión "
            "que queda en otro cluster) permite que una versión caiga en train y la otra en "
            "eval: es **leakage**, y además deja contenido redundante. Un falso positivo solo "
            "pone dos secciones distintas en el mismo cluster: con la regla de fusión sin "
            "pérdida (§5) no se descarta contenido, solo el split queda un poco más grueso. "
            "El costo es asimétrico, así que se acepta perder precisión antes que recall.",
            "- **Must-link**: los pares etiquetados `same` se agrupan en `dedup` con cualquier "
            "umbral (`match: human_label`), así que el recall sobre el set etiquetado no depende "
            "del umbral. El umbral decide sobre los pares **no** etiquetados: por eso importa "
            "más que la recomendación sea robusta que exprimir el recall de este set.",
            f"- **Umbral actual ({v.current:.2f})**: "
            + (
                "está dentro del intervalo equivalente; con estas etiquetas da los mismos "
                "resultados que el recomendado."
                if current_in
                else "queda **fuera** del intervalo equivalente"
                + (
                    "; como la recomendación es frágil y los `same` ya se agrupan por must-link, "
                    "la config lo mantiene."
                    if fr.fragile
                    else "; ver la tabla para el costo."
                )
            ),
            f"- **Límites**: el recall se mide solo sobre pares con Jaccard ≥ "
            f"{cfg.labels.review_min_jaccard} entre representantes con ≥ "
            f"{cfg.dedup.near_dup_min_tokens} tokens; un `same` por debajo de eso no se ve "
            f"(con t = {cfg.labels.grid_start:.2f} el recall es 100% por construcción).",
            "",
            "### Robustez de la recomendación",
            "",
        ]
        warn = []
        if fr.few_positives:
            warn.append(
                f"⚠️ **Pocos positivos**: {fr.n_same} pares `same` (mínimo configurado "
                f"{cfg.labels.min_same_pairs}); cada uno vale {1 / fr.n_same:.0%} de recall."
            )
        if fr.zero_width:
            warn.append(
                f"⚠️ **Intervalo de ancho cero**: solo {r.threshold:.2f} da esta matriz de "
                "confusión; un paso de la grilla hacia cualquier lado cambia el resultado."
            )
        if fr.thin_margin:
            warn.append(
                f"⚠️ **Margen menor a un paso de la grilla**: hay un par etiquetado a "
                f"{fr.margin:.3f} del umbral recomendado."
            )
        if v.critical:
            crit = "; ".join(
                f"`{x['pair_id']}` ({x['label']}, J = {x['jaccard']:.3f})" for x in v.critical
            )
            warn.append(
                f"⚠️ **Depende de {len(v.critical)} etiqueta(s)**: quitando cualquiera de "
                f"estos pares cambia el umbral recomendado: {crit}."
            )
        out += [f"- {w}" for w in warn] or [
            f"- Sin avisos: {fr.n_same} `same`, intervalo [{lo:.2f}, {hi:.2f}], margen "
            f"{fr.margin:.3f}, ningún par decide la recomendación por sí solo."
        ]

    fn = [x for x in v.labeled if x["label"] == "same" and x["jaccard"] < v.current]
    out += ["", f"### `same` bajo el umbral actual ({v.current:.2f})", ""]
    if not fn:
        out.append("Ninguno.")
    else:
        out += [
            "| pair_id | Jaccard | Clustering final | A | B | Nota |",
            "|---|---|---|---|---|---|",
        ]
        out += [
            f"| {x['pair_id']} | {x['jaccard']:.3f} | "
            f"{'agrupado (must-link)' if x['same_cluster'] else '**separado**'} | "
            f"`{x['a']}` | `{x['b']}` | {_nota(x)} |"
            for x in fn
        ]

    grouped_diff = [x for x in v.labeled if x["label"] == "diff" and x["same_cluster"]]
    out += [
        "",
        "### Pares `diff` que quedan agrupados",
        "",
        "Las etiquetas `diff` **no separan** pares que el umbral agrupa: solo cuentan para las "
        "métricas. `diff` responde a «¿es el mismo contenido?»; el cluster responde a «¿deben ir "
        "al mismo lado del split?». Dos versiones que comparten la mayor parte del texto deben "
        "ir juntas aunque una tenga cambios relevantes: separarlas filtraría a eval lo que se vio "
        "en train. Ninguna se pierde: la regla sin pérdida conserva cada una como canónica o "
        "variante, con sus líneas propias en `unique_lines_vs_canonical`.",
        "",
    ]
    if not grouped_diff:
        out.append("Ninguno.")
    else:
        out += ["| pair_id | Jaccard | A | B | Nota |", "|---|---|---|---|---|"]
        out += [
            f"| {x['pair_id']} | {x['jaccard']:.3f} | `{x['a']}` | `{x['b']}` | {_nota(x)} |"
            for x in grouped_diff
        ]
    if v.missing:
        out += ["", f"Etiquetas de pares que ya no existen: {', '.join(v.missing)}."]
    return out


def render_section(v: Validation | None, cfg: Config, labels_rel: str, reason: str = "") -> str:
    out = [MARK_START, "## 8. Validación del umbral con etiquetas humanas", ""]
    if v is None:
        out.append(
            reason
            or f"Sin etiquetas todavía: `meli-etl label-pairs` genera `{labels_rel}`; "
            "completarlo y correr `meli-etl validate-threshold`."
        )
    else:
        out += _render_body(v, labels_rel, cfg)
    out.append(MARK_END)
    return "\n".join(out)


def replace_section(report: str, section: str) -> str:
    start, end = report.find(MARK_START), report.find(MARK_END)
    if start < 0 or end < 0:
        raise ValueError("El reporte no tiene la sección §8: corré antes `meli-etl dedup`.")
    return report[:start] + section + report[end + len(MARK_END) :]


def run(cfg: Config) -> Path:
    v = build_validation(cfg)
    labels_path = cfg.paths.labels_dir / LABELS_FILE
    pairs_path = cfg.paths.processed_dir / PAIRS_FILE
    if labels_path.stat().st_mtime > pairs_path.stat().st_mtime:
        log.warning(
            "Las etiquetas son más nuevas que la última corrida de dedup: los must-link nuevos "
            "no se reflejan en el clustering final. Corré `meli-etl dedup` (o "
            "`make validate-threshold`, que lo hace antes)."
        )
    if v.rec is None:
        raise ValueError(
            f"No hay pares `same` etiquetados ({v.counts['diff']} `diff`, "
            f"{v.counts['unsure']} `unsure`, {v.n_unlabeled} sin etiquetar): "
            "no se puede calcular recall."
        )
    if v.n_unlabeled:
        log.warning("%d pares sin etiquetar: quedan fuera de las métricas", v.n_unlabeled)
    for pid in v.missing:
        log.warning("Etiqueta de un par que ya no existe: %s", pid)
    log.info(
        "same=%d diff=%d unsure=%d | recomendado %.2f (intervalo equivalente %.2f–%.2f)",
        v.counts["same"],
        v.counts["diff"],
        v.counts["unsure"],
        v.rec.row.threshold,
        *v.rec.equivalent,
    )

    if v.frag and v.frag.fragile:
        log.warning("Recomendación frágil: ver «Robustez de la recomendación» en la §8")
    report = cfg.paths.reports_dir / "dedup.md"
    if not report.exists():
        raise FileNotFoundError(f"{report} no existe: corré antes `meli-etl dedup`.")
    section = render_section(v, cfg, display_path(cfg.paths.labels_dir / LABELS_FILE))
    report.write_text(replace_section(report.read_text(encoding="utf-8"), section), "utf-8")
    log.info("Sección §8 actualizada en %s", display_path(report))
    return report
