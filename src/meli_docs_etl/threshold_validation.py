"""Validación del umbral de casi-duplicados contra etiquetas humanas (cálculo puro).

Cada par etiquetado aporta (Jaccard, label). Con un umbral t, el par se predice
"casi-duplicado" si Jaccard ≥ t; el positivo real es `same`. `unsure` no entra en las
métricas pero se cuenta.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence
from dataclasses import dataclass

log = logging.getLogger(__name__)

LABELS = ("same", "diff", "unsure")


def pair_id(a: str, b: str) -> str:
    """Id estable del par (independiente del orden y del corpus restante)."""
    x, y = sorted((a, b))
    return "np-" + hashlib.sha1(f"{x}|{y}".encode()).hexdigest()[:8]


def threshold_grid(start: float, stop: float, step: float) -> list[float]:
    """Grilla inclusiva calculada con enteros (evita 0.30000000000000004)."""
    n = int(round((stop - start) / step))
    return [round(start + i * step, 4) for i in range(n + 1)]


@dataclass(frozen=True)
class ThresholdRow:
    threshold: float
    tp: int
    fp: int
    fn: int
    tn: int
    unsure_above: int
    precision: float | None
    recall: float | None
    f1: float | None

    @property
    def confusion(self) -> tuple[int, int, int, int]:
        return (self.tp, self.fp, self.fn, self.tn)


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def evaluate_predictions(predicted: Sequence[tuple[bool, str]], threshold: float) -> ThresholdRow:
    """Matriz de confusión y métricas para predicciones ya tomadas (par agrupado o no)."""
    tp = fp = fn = tn = unsure_above = 0
    for pred, label in predicted:
        if label == "unsure":
            unsure_above += pred
        elif label == "same":
            tp += pred
            fn += not pred
        elif label == "diff":
            fp += pred
            tn += not pred
        else:
            raise ValueError(f"Etiqueta inválida: {label!r} (válidas: {', '.join(LABELS)})")
    precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall > 0
        else None
    )
    return ThresholdRow(threshold, tp, fp, fn, tn, unsure_above, precision, recall, f1)


def evaluate_threshold(pairs: Sequence[tuple[float, str]], threshold: float) -> ThresholdRow:
    return evaluate_predictions([(j >= threshold, label) for j, label in pairs], threshold)


def sweep(pairs: Sequence[tuple[float, str]], thresholds: Sequence[float]) -> list[ThresholdRow]:
    return [evaluate_threshold(pairs, t) for t in thresholds]


@dataclass(frozen=True)
class Recommendation:
    row: ThresholdRow
    # Intervalo de umbrales contiguos con la misma matriz de confusión que el óptimo.
    equivalent: tuple[float, float]


def recommend(rows: Sequence[ThresholdRow], recall_priority: bool = True) -> Recommendation:
    """Elige el umbral recomendado sobre una grilla ordenada de menor a mayor.

    1. Óptimo: con prioridad a recall, el umbral más alto que mantiene el recall máximo
       (entre umbrales con igual recall, subirlo solo quita falsos positivos, así que es
       también el de mejor precisión). Sin prioridad a recall, el de mejor F1.
    2. Todos los umbrales contiguos con la misma matriz de confusión son indistinguibles
       con estas etiquetas; se recomienda el punto medio de ese intervalo (redondeado
       hacia abajo en la grilla) para dejar margen a ambos lados frente a pares no vistos.
    """
    if not rows:
        raise ValueError("No hay umbrales para evaluar.")
    metric = (lambda r: r.recall) if recall_priority else (lambda r: r.f1)
    best = max((metric(r) for r in rows if metric(r) is not None), default=None)
    if best is None:
        raise ValueError("Ninguna métrica definida: hacen falta pares `same` etiquetados.")
    opt = max(i for i, r in enumerate(rows) if metric(r) == best)
    lo = hi = opt
    while lo > 0 and rows[lo - 1].confusion == rows[opt].confusion:
        lo -= 1
    while hi < len(rows) - 1 and rows[hi + 1].confusion == rows[opt].confusion:
        hi += 1
    return Recommendation(rows[(lo + hi) // 2], (rows[lo].threshold, rows[hi].threshold))


@dataclass(frozen=True)
class Fragility:
    n_same: int
    few_positives: bool  # menos pares `same` que el mínimo configurado
    zero_width: bool  # ningún otro umbral de la grilla da la misma matriz de confusión
    margin: float  # distancia del umbral recomendado al Jaccard etiquetado más cercano
    thin_margin: bool  # margen menor que un paso de la grilla
    critical: list[int]  # índices de pares cuya etiqueta, sola, decide la recomendación

    @property
    def fragile(self) -> bool:
        return self.few_positives or self.zero_width or self.thin_margin or bool(self.critical)


def fragility(
    pairs: Sequence[tuple[float, str]],
    thresholds: Sequence[float],
    recall_priority: bool,
    min_same: int,
) -> Fragility:
    """Qué tan frágil es la recomendación: tamaño de muestra, ancho del intervalo,
    margen y pares críticos (leave-one-out: quitar ese par cambia el umbral recomendado)."""
    rec = recommend(sweep(pairs, thresholds), recall_priority)
    t = rec.row.threshold
    step = thresholds[1] - thresholds[0] if len(thresholds) > 1 else 0.0
    labeled = [i for i, (_, label) in enumerate(pairs) if label != "unsure"]
    margin = min((abs(pairs[i][0] - t) for i in labeled), default=float("inf"))
    critical = []
    for i in labeled:
        rest = [p for k, p in enumerate(pairs) if k != i]
        if not any(label == "same" for _, label in rest):
            continue
        if recommend(sweep(rest, thresholds), recall_priority).row.threshold != t:
            critical.append(i)
    n_same = sum(label == "same" for _, label in pairs)
    return Fragility(
        n_same=n_same,
        few_positives=n_same < min_same,
        zero_width=rec.equivalent[0] == rec.equivalent[1],
        margin=margin,
        thin_margin=margin < step - 1e-9,
        critical=critical,
    )


# --------------------------------------------------------------------------- umbral auto

METHODS = ("config", "labels", "valley", "fallback")


@dataclass(frozen=True)
class ThresholdChoice:
    """Umbral de casi-duplicados usado por dedup y cómo se eligió (`METHODS`)."""

    threshold: float
    method: str
    # Hueco sin pares más ancho dentro de threshold_bounds (se calcula siempre, para registro).
    valley: tuple[float, float] | None
    histogram: list[tuple[str, int]]  # Jaccard de los candidatos LSH, en tramos de 0.1
    n_candidates: int
    detail: str = ""

    @property
    def valley_width(self) -> float | None:
        return None if self.valley is None else round(self.valley[1] - self.valley[0], 4)

    def to_json(self) -> dict[str, object]:
        return {
            "threshold": self.threshold,
            "method": self.method,
            "valley": list(self.valley) if self.valley else None,
            "valley_width": self.valley_width,
            "histogram": [{"jaccard": r, "pairs": n} for r, n in self.histogram],
            "n_candidates": self.n_candidates,
            "detail": self.detail,
        }


def jaccard_histogram(values: Sequence[float], step: float = 0.1) -> list[tuple[str, int]]:
    n = int(round(1 / step))
    counts = [0] * n
    for v in values:
        counts[min(int(v / step + 1e-9), n - 1)] += 1
    return [
        (f"[{i * step:.1f}, {(i + 1) * step:.1f}{']' if i == n - 1 else ')'}", c)
        for i, c in enumerate(counts)
    ]


def find_valley(values: Sequence[float], bounds: tuple[float, float]) -> tuple[float, float]:
    """Hueco sin pares más ancho dentro de `bounds` (los extremos cuentan como bordes).
    Empate → el más bajo, así el resultado es determinista."""
    lo, hi = bounds
    points = sorted({lo, hi, *(round(v, 6) for v in values if lo < v < hi)})
    gaps = [(b - a, -a, a, b) for a, b in zip(points[:-1], points[1:], strict=True)]
    _, _, a, b = max(gaps)
    return (round(a, 4), round(b, 4))


def choose_threshold(
    configured: float | str,
    candidate_js: Sequence[float],
    labeled: Sequence[tuple[float, str]],
    *,
    fallback: float,
    bounds: tuple[float, float],
    min_valley_width: float,
    grid: Sequence[float],
    min_label_pairs: int,
) -> ThresholdChoice:
    """Número en la config → ese umbral. `auto`: (a) etiquetas humanas con ≥ min_label_pairs
    `same` y `diff` → punto medio (en la grilla) del intervalo con mejor F1; (b) si no, punto
    medio del valle de `candidate_js`; (c) si el valle mide < min_valley_width, `fallback`."""
    valley = find_valley(candidate_js, bounds)
    common = {
        "valley": valley,
        "histogram": jaccard_histogram(candidate_js),
        "n_candidates": len(candidate_js),
    }
    if not isinstance(configured, str):
        return ThresholdChoice(float(configured), "config", **common)
    if configured != "auto":
        raise ValueError(f"dedup.near_dup_threshold debe ser un número o 'auto': {configured!r}")
    n_same = sum(label == "same" for _, label in labeled)
    n_diff = sum(label == "diff" for _, label in labeled)
    if n_same >= min_label_pairs and n_diff >= min_label_pairs:
        rec = recommend(sweep(labeled, grid), recall_priority=False)
        lo, hi = rec.equivalent
        detail = f"{n_same} same / {n_diff} diff; mejor F1 en [{lo:.2f}, {hi:.2f}]"
        return ThresholdChoice(rec.row.threshold, "labels", detail=detail, **common)
    labels_note = (
        f"etiquetas insuficientes ({n_same} same / {n_diff} diff; mínimo {min_label_pairs})"
    )
    if valley[1] - valley[0] >= min_valley_width:
        mid = round((valley[0] + valley[1]) / 2, 4)
        return ThresholdChoice(mid, "valley", detail=labels_note, **common)
    log.warning(
        "Umbral de casi-duplicados: sin valle de ancho ≥ %s en el Jaccard de los %d candidatos "
        "LSH (más ancho: %s) y %s; se usa threshold_fallback = %s. Conviene etiquetar pares "
        "(`meli-etl label-pairs`) y recalibrar.",
        min_valley_width,
        len(candidate_js),
        valley,
        labels_note,
        fallback,
    )
    return ThresholdChoice(fallback, "fallback", detail=labels_note, **common)
