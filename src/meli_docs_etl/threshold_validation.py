"""Validación del umbral de casi-duplicados contra etiquetas humanas (cálculo puro).

Cada par etiquetado aporta (Jaccard, label). Con un umbral t, el par se predice
"casi-duplicado" si Jaccard ≥ t; el positivo real es `same`. `unsure` no entra en las
métricas pero se cuenta.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

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
