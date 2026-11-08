"""Tests del cálculo de precisión/recall por umbral y de la recomendación."""

from __future__ import annotations

import pytest

from meli_docs_etl.threshold_validation import (
    evaluate_threshold,
    pair_id,
    recommend,
    sweep,
    threshold_grid,
)

# (Jaccard, etiqueta): dos `same` altos, `diff` repartidos y dos `unsure`.
PAIRS = [
    (0.95, "same"),
    (0.70, "same"),
    (0.55, "diff"),
    (0.35, "diff"),
    (0.20, "diff"),
    (0.50, "unsure"),
    (0.15, "unsure"),
]


def test_confusion_and_metrics_by_hand() -> None:
    r = evaluate_threshold(PAIRS, 0.6)
    assert (r.tp, r.fp, r.fn, r.tn, r.unsure_above) == (2, 0, 0, 3, 0)
    assert (r.precision, r.recall, r.f1) == (1.0, 1.0, 1.0)

    # Umbral bajo: agrupa dos `diff` (FP) y un `unsure`, que no entra en las métricas.
    r = evaluate_threshold(PAIRS, 0.3)
    assert (r.tp, r.fp, r.fn, r.tn, r.unsure_above) == (2, 2, 0, 1, 1)
    assert r.precision == pytest.approx(0.5)
    assert r.recall == 1.0
    assert r.f1 == pytest.approx(2 / 3)

    # Umbral alto: pierde un `same` (FN).
    r = evaluate_threshold(PAIRS, 0.8)
    assert (r.tp, r.fp, r.fn, r.tn) == (1, 0, 1, 3)
    assert (r.precision, r.recall) == (1.0, 0.5)
    assert r.f1 == pytest.approx(2 / 3)

    # Sin predicciones positivas la precisión no está definida (no se inventa un 0).
    r = evaluate_threshold(PAIRS, 0.99)
    assert (r.precision, r.recall, r.f1) == (None, 0.0, None)

    # Los `unsure` se excluyen de TP/FP/FN/TN pero se cuentan.
    assert all(x.tp + x.fp + x.fn + x.tn == 5 for x in sweep(PAIRS, [0.1, 0.5, 0.9]))


def test_invalid_label_raises() -> None:
    with pytest.raises(ValueError, match="Etiqueta inválida"):
        evaluate_threshold([(0.5, "maybe")], 0.5)


def test_grid_and_pair_id() -> None:
    grid = threshold_grid(0.1, 0.9, 0.05)
    assert len(grid) == 17 and grid[0] == 0.1 and grid[-1] == 0.9 and 0.3 in grid
    assert pair_id("a#001", "b#002") == pair_id("b#002", "a#001")
    assert pair_id("a#001", "b#002").startswith("np-")


def test_recommendation_prioritizes_recall() -> None:
    rows = sweep(PAIRS, threshold_grid(0.1, 0.9, 0.05))
    rec = recommend(rows, recall_priority=True)
    # Recall 100% hasta 0.70; sin FP desde 0.60 → intervalo equivalente [0.60, 0.70],
    # se recomienda el punto medio.
    assert rec.equivalent == (0.6, 0.7)
    assert rec.row.threshold == 0.65
    assert (rec.row.recall, rec.row.precision) == (1.0, 1.0)

    # Con un `same` bajo, la prioridad a recall acepta falsos positivos; F1 no.
    noisy = [*PAIRS, (0.30, "same")]
    rows = sweep(noisy, threshold_grid(0.1, 0.9, 0.05))
    by_recall = recommend(rows, recall_priority=True)
    by_f1 = recommend(rows, recall_priority=False)
    assert by_recall.row.recall == 1.0 and by_recall.row.fp > 0
    assert by_f1.row.recall < 1.0 and by_f1.row.f1 > by_recall.row.f1
