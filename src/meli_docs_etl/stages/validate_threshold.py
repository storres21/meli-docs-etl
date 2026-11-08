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
    Recommendation,
    ThresholdRow,
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
    # Pares mal clasificados con el umbral actual de la config.
    errors: list[dict[str, Any]] = field(default_factory=list)


def build_validation(cfg: Config) -> Validation:
    """Cruza etiquetas con Jaccard. FileNotFoundError si faltan archivos; ValueError si
    hay etiquetas inválidas."""
    pairs = read_pairs(cfg.paths.processed_dir / PAIRS_FILE)
    labels_path = cfg.paths.labels_dir / LABELS_FILE
    if not labels_path.exists():
        raise FileNotFoundError(f"{labels_path} no existe: corré antes `meli-etl label-pairs`.")
    rows = read_labels(labels_path)

    invalid = [r["pair_id"] for r in rows if r["label"] and r["label"].lower() not in LABELS]
    if invalid:
        raise ValueError(
            f"Etiquetas inválidas en {len(invalid)} pares ({', '.join(invalid[:10])}); "
            f"valores permitidos: {', '.join(LABELS)}."
        )

    labeled: list[tuple[float, str, dict[str, str]]] = []
    missing, n_unlabeled = [], 0
    for r in rows:
        if not r["label"]:
            n_unlabeled += 1
        elif r["pair_id"] not in pairs:
            missing.append(r["pair_id"])
        else:
            labeled.append((pairs[r["pair_id"]]["jaccard"], r["label"].lower(), r))

    current = cfg.dedup.near_dup_threshold
    v = Validation(
        n_pairs=len(pairs),
        counts=Counter(label for _, label, _ in labeled),
        n_unlabeled=n_unlabeled,
        missing=missing,
        current=current,
        same_js=sorted(j for j, label, _ in labeled if label == "same"),
        diff_js=sorted(j for j, label, _ in labeled if label == "diff"),
    )
    lc = cfg.labels
    v.rows = sweep(
        [(j, label) for j, label, _ in labeled],
        threshold_grid(lc.grid_start, lc.grid_stop, lc.grid_step),
    )
    if v.same_js:
        v.rec = recommend(v.rows, lc.recall_priority)
    for j, label, r in sorted(labeled, key=lambda x: (-x[0], x[2]["pair_id"])):
        if (label == "same" and j < current) or (label == "diff" and j >= current):
            p = pairs[r["pair_id"]]
            v.errors.append({**r, "label": label, "jaccard": j, "a": p["a"], "b": p["b"]})
    return v


# --------------------------------------------------------------------------- reporte


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

    if v.rec:
        r = v.rec.row
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
            f"{r.tp + r.fn} `same`).",
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
            f"- **Umbral actual ({v.current:.2f})**: "
            + (
                "está dentro del intervalo equivalente; con estas etiquetas da los mismos "
                "resultados que el recomendado."
                if current_in
                else "queda **fuera** del intervalo equivalente; ver la tabla para el costo."
            ),
            f"- **Límites**: el recall se mide solo sobre pares con Jaccard ≥ "
            f"{cfg.labels.review_min_jaccard} entre representantes con ≥ "
            f"{cfg.dedup.near_dup_min_tokens} tokens; un `same` por debajo de eso no se ve "
            f"(con t = {cfg.labels.grid_start:.2f} el recall es 100% por construcción). Con "
            f"{r.tp + r.fn} pares `same`, cada uno vale "
            f"{1 / (r.tp + r.fn):.0%} de recall.",
        ]

    out += ["", f"**Pares mal clasificados con el umbral actual ({v.current:.2f})**", ""]
    if not v.errors:
        out.append("Ninguno.")
    else:
        out += [
            "| pair_id | Etiqueta | Jaccard | Error | A | B | Nota |",
            "|---|---|---|---|---|---|---|",
        ]
        for e in v.errors:
            kind = "FN" if e["label"] == "same" else "FP"
            nota = e["nota"].replace("|", "\\|") or "—"
            out.append(
                f"| {e['pair_id']} | {e['label']} | {e['jaccard']:.3f} | {kind} | "
                f"`{e['a']}` | `{e['b']}` | {nota} |"
            )
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

    report = cfg.paths.reports_dir / "dedup.md"
    if not report.exists():
        raise FileNotFoundError(f"{report} no existe: corré antes `meli-etl dedup`.")
    section = render_section(v, cfg, display_path(cfg.paths.labels_dir / LABELS_FILE))
    report.write_text(replace_section(report.read_text(encoding="utf-8"), section), "utf-8")
    log.info("Sección §8 actualizada en %s", display_path(report))
    return report
