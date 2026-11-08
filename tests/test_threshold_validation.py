"""Tests del cálculo de precisión/recall por umbral y de la recomendación."""

from __future__ import annotations

import pytest

from meli_docs_etl.threshold_validation import (
    evaluate_predictions,
    evaluate_threshold,
    fragility,
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


def test_final_clustering_metrics_from_predictions() -> None:
    # Must-link agrupa un `same` bajo el umbral; un `diff` agrupado cuenta como FP.
    r = evaluate_predictions([(True, "same"), (True, "same"), (True, "diff"), (False, "diff")], 0.6)
    assert (r.tp, r.fp, r.fn, r.tn) == (2, 1, 0, 1)
    assert (r.recall, r.precision) == (1.0, pytest.approx(2 / 3))


def test_fragility_flags() -> None:
    grid = threshold_grid(0.1, 0.9, 0.05)
    # PAIRS: recomendado 0.65 en [0.60, 0.70]. Con solo 2 `same`, sacar el de 0.70 o el
    # `diff` de 0.55 mueve el intervalo (pares críticos 1 y 2); los demás no lo cambian.
    robust = fragility(PAIRS, grid, recall_priority=True, min_same=2)
    assert not (robust.zero_width or robust.few_positives or robust.thin_margin)
    assert robust.margin == pytest.approx(0.05)
    assert robust.critical == [1, 2]

    # Forma de los datos reales: un `same` bajo (0.319) pegado a un `diff` (0.316) y otro
    # `diff` justo debajo (0.27). Recall 100% solo con 0.30, a 0.016 del `diff`.
    real_like = [(0.95, "same"), (0.319, "same"), (0.316, "diff"), (0.27, "diff"), (0.1, "diff")]
    f = fragility(real_like, grid, recall_priority=True, min_same=10)
    assert f.few_positives and f.n_same == 2
    assert f.zero_width
    assert f.thin_margin and f.margin == pytest.approx(0.016)
    assert 1 in f.critical  # sin el `same` de 0.319 la recomendación sube
    assert f.fragile
