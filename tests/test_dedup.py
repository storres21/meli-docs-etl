"""Tests de deduplicación por sección, regla de fusión y resolución de versiones."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from meli_docs_etl.config import Config, load_config
from meli_docs_etl.dedup_utils import body_lines, merge_cluster
from meli_docs_etl.stages import dedup, label_pairs, normalize, validate_threshold
from meli_docs_etl.threshold_validation import choose_threshold, threshold_grid

INTRO = (
    "# Stock API\n\nThis service is responsible for the stock of the items sold by the "
    "vendors and keeps the warehouse in sync.\n"
)
ROWS = [
    "| POST | Feed Consumer | `/fp/inventory/operations/feed` |",
    "| POST | Restock Consumer | `/fp/inventory/operations/restock-new` |",
    "| GET | Get Detail | `/fp/inventory/item/detail/{identifierRegister}` |",
    "| GET | Internal Item Detail | `/internal/stock-operations/3pl/{identifierRegister}` |",
    "| GET | Operation Validation Consumer | `/stock-operations/3pl/validation/restock` |",
]


def services(rows: list[str], padded: bool = False) -> str:
    head = "| METHOD   | OPERATION   | PATH   |" if padded else "| METHOD | OPERATION | PATH |"
    return "## Services\n\n" + "\n".join([head, "|---|---|---|", *rows]) + "\n"


UNIQUE = (
    "## Operation Validation Consumer\n\nValidates each restock order against the stock "
    "reported by the items API before confirming it.\n"
)
FILES = {
    # Versión con la fila extra y una sección única.
    "stock/0.0.10/guide/api.md": (
        INTRO.replace("'", "&#39;") + "\n" + services(ROWS) + "\n" + UNIQUE
    ),
    # Alias: sin la fila extra, padding distinto; declara una versión que no existe.
    "stock/latest/guide/api.md": INTRO + "\n" + services(ROWS[:4], padded=True),
    "stock/latest/documentationTypes.json": json.dumps(
        {"guide": "https://d.s3.amazonaws.com/stock/0.41.0/guide/index.html"}
    ),
    # Proyecto cuyo alias es idéntico a una versión concreta.
    "pay/1.0/guide/README.md": "# Pay\n\nPayment promises are created by the gateway service.\n",
    "pay/latest/guide/README.md": "# Pay\n\nPayment promises are created by the gateway service.\n",
    "pay/latest/documentationTypes.json": json.dumps(
        {"guide": "https://d.s3.amazonaws.com/pay/3.7.0/guide/index.html"}
    ),
    # Mismo contenido en dos documentos de una versión: Jaccard bajo el umbral.
    "ops/1.0/guide/setup/README.md": (
        "# Setup\n\n## Prerequisites Summary\n\nInstall Java 17, Maven 3.9 and Docker before "
        "running the service locally on your machine. Ask the team for access to the staging "
        "database and to the message broker.\n"
    ),
    "ops/1.0/guide/setup/local-development.md": (
        "# Local Development\n\n## Prerequisites\n\nInstall Java 17, Maven 3.9 and Docker "
        "before running the service locally. Then clone the repository and run the bootstrap "
        "script that creates the local queues and the test topics.\n"
    ),
}


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    raw = tmp_path / "raw"
    for rel, content in FILES.items():
        (raw / rel).parent.mkdir(parents=True, exist_ok=True)
        (raw / rel).write_text(content, encoding="utf-8")
    return load_config(
        overrides={
            "raw_dir": raw,
            "processed_dir": tmp_path / "processed",
            "reports_dir": tmp_path / "reports",
            "labels_dir": tmp_path / "labels",
        }
    )


def _run(cfg: Config) -> list[dict]:
    normalize.run(cfg)
    dedup.run(cfg)
    path = cfg.paths.processed_dir / dedup.DEDUP_FILE
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_merge_rule_never_drops_unique_lines() -> None:
    big = {"id": "a", "body": "x\ny\nz"}
    subset = {"id": "b", "body": "x\ny"}
    other = {"id": "c", "body": "x\ny\nw"}
    res = merge_cluster([subset, other, big], lambda m: body_lines(m["body"]), lambda m: (m["id"],))
    assert [m["id"] for m in res.kept] == ["a", "c"]  # c aporta "w" → variante
    assert [m["id"] for m in res.absorbed_by[0]] == ["b"]


def test_dedup_end_to_end(cfg: Config) -> None:
    records = _run(cfg)
    by_title = {}
    for r in records:
        by_title.setdefault((r["project"], r["title"]), []).append(r)

    # Exacto tras normalizar (&#39; vs '): una sola sección con ocurrencias en ambas versiones.
    (intro,) = by_title[("stock", "Stock API")]
    assert {o["version_dir"] for o in intro["occurrences"]} == {"0.0.10", "latest"}

    # Casi-duplicado: la tabla con la fila extra es canónica y absorbe a la otra.
    (svc,) = by_title[("stock", "Services")]
    assert svc["version_dir"] == "0.0.10" and svc["role"] == "canonical"
    assert svc["jaccard_vs_canonical"] is None
    assert "Operation Validation Consumer" in svc["body"]
    matches = {o["version_dir"]: o["match"] for o in svc["occurrences"]}
    assert matches == {"0.0.10": "self", "latest": "near_dup"}

    # La sección única sobrevive.
    assert ("stock", "Operation Validation Consumer") in by_title

    # Versiones: alias idéntico → efectiva = carpeta concreta; alias distinto → declarada.
    versions = json.loads((cfg.paths.processed_dir / dedup.VERSIONS_FILE).read_text())
    assert versions["pay/latest"]["effective_version"] == "1.0"
    assert versions["pay/latest"]["issues"]
    assert versions["stock/latest"]["effective_version"] == "0.41.0"
    assert versions["stock/latest"]["identical_to"] == []
    (pay,) = by_title[("pay", "Pay")]
    assert {o["effective_version"] for o in pay["occurrences"]} == {"1.0"}

    report = (cfg.paths.reports_dir / "dedup.md").read_text(encoding="utf-8")
    for heading in ("## 1. Embudo", "## 4. Distribución", "## 6. Ejemplos", "## 7. Versiones"):
        assert heading in report


def test_dedup_is_deterministic(cfg: Config) -> None:
    first = _run(cfg)
    report = (cfg.paths.reports_dir / "dedup.md").read_text(encoding="utf-8")
    assert _run(cfg) == first
    assert (cfg.paths.reports_dir / "dedup.md").read_text(encoding="utf-8") == report


def test_label_pairs_blind_review_and_label_merge(cfg: Config) -> None:
    _run(cfg)
    label_pairs.run(cfg)
    pairs = validate_threshold.read_pairs(cfg.paths.processed_dir / validate_threshold.PAIRS_FILE)
    assert pairs  # al menos la tabla Services entre versiones

    labels_dir = cfg.paths.labels_dir
    review = (labels_dir / validate_threshold.REVIEW_FILE).read_text(encoding="utf-8")
    assert all(pid in review for pid in pairs)
    # Revisión ciega: ni la palabra ni los valores de Jaccard.
    assert "jaccard" not in review.lower()
    assert not any(f"{p['jaccard']:.2f}" in review for p in pairs.values())

    # Etiquetar y regenerar: la etiqueta se conserva.
    csv_path = labels_dir / validate_threshold.LABELS_FILE
    rows = validate_threshold.read_labels(csv_path)
    assert [r["pair_id"] for r in rows] and all(not r["label"] for r in rows)
    first = rows[0]["pair_id"]
    csv_path.write_text(
        csv_path.read_text(encoding="utf-8").replace(f"{first},,", f"{first},same,ok", 1),
        encoding="utf-8",
    )
    label_pairs.run(cfg)
    rows = {r["pair_id"]: r for r in validate_threshold.read_labels(csv_path)}
    assert (rows[first]["label"], rows[first]["nota"]) == ("same", "ok")

    # validate-threshold reemplaza la §8 del reporte; dedup la vuelve a generar igual.
    dedup.run(cfg)  # aplica los must-link nuevos
    report = validate_threshold.run(cfg)
    text = report.read_text(encoding="utf-8")
    assert "Umbral recomendado" in text and text.count(validate_threshold.MARK_START) == 1
    dedup.run(cfg)
    assert report.read_text(encoding="utf-8") == text


def _write_labels(cfg: Config, labels: dict[str, str]) -> None:
    cfg.paths.labels_dir.mkdir(parents=True, exist_ok=True)
    rows = "".join(f"{pid},{label},\n" for pid, label in labels.items())
    (cfg.paths.labels_dir / validate_threshold.LABELS_FILE).write_text(
        "pair_id,label,nota\n" + rows, encoding="utf-8"
    )


def test_same_labels_are_must_links_and_diff_never_splits(cfg: Config) -> None:
    _run(cfg)
    pairs_path = cfg.paths.processed_dir / validate_threshold.PAIRS_FILE
    pairs = validate_threshold.read_pairs(pairs_path)
    threshold = validate_threshold.near_dup_threshold(cfg)
    (low,) = [p for p in pairs.values() if p["jaccard"] < threshold]  # prerequisitos de ops
    (high,) = [p for p in pairs.values() if p["jaccard"] >= threshold]  # Services
    assert not low["same_cluster"] and high["same_cluster"]

    _write_labels(cfg, {low["pair_id"]: "same", high["pair_id"]: "diff"})
    records = _run(cfg)
    pairs = validate_threshold.read_pairs(pairs_path)
    # `same` bajo el umbral → agrupado por must-link; `diff` sobre el umbral → sigue agrupado.
    assert pairs[low["pair_id"]]["same_cluster"] and pairs[high["pair_id"]]["same_cluster"]
    by_id = {r["section_id"]: r for r in records}
    a, b = by_id[low["a"]], by_id[low["b"]]
    assert a["cluster_id"] == b["cluster_id"]
    # Ambas aportan líneas propias: ninguna se pierde, una queda como variante human_label.
    variant = a if a["role"] == "variant" else b
    assert variant["match_to_canonical"] == "human_label"
    assert variant["unique_lines_vs_canonical"]
    report = (cfg.paths.reports_dir / "dedup.md").read_text(encoding="utf-8")
    assert "Uniones por etiqueta humana (must-link, `match: human_label`):** 1 pares" in report
    assert "### Pares `diff` que quedan agrupados" in report


# --------------------------------------------------------------------------- umbral auto

AUTO = {
    "fallback": 0.6,
    "bounds": (0.3, 0.9),
    "min_valley_width": 0.1,
    "grid": threshold_grid(0.1, 0.9, 0.05),
    "min_label_pairs": 3,
}


def test_auto_threshold_takes_the_midpoint_of_a_clear_valley() -> None:
    js = [0.05, 0.12, 0.31, 0.35, 0.72, 0.8, 0.95]
    choice = choose_threshold("auto", js, [], **AUTO)
    assert (choice.method, choice.valley, choice.threshold) == ("valley", (0.35, 0.72), 0.535)
    assert choice.valley_width == 0.37
    assert dict(choice.histogram)["[0.3, 0.4)"] == 2
    assert choose_threshold("auto", list(reversed(js)), [], **AUTO) == choice  # determinista


def test_auto_threshold_without_valley_falls_back_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    js = [0.3 + 0.07 * i for i in range(10)]  # pares cada 0.07: ningún hueco ≥ 0.1
    with caplog.at_level("WARNING"):
        choice = choose_threshold("auto", js, [], **AUTO)
    assert (choice.method, choice.threshold) == ("fallback", 0.6)
    assert choice.valley_width is not None and choice.valley_width < 0.1
    assert any(
        r.levelname == "WARNING" and "threshold_fallback" in r.message for r in caplog.records
    )


def test_auto_threshold_prefers_labels_over_valley() -> None:
    js = [0.1, 0.2, 0.72, 0.8]  # valle [0.3, 0.72] → 0.51
    labeled = [(0.2, "diff"), (0.25, "diff"), (0.3, "diff"), (0.45, "same"), (0.5, "same")]
    labeled += [(0.8, "same"), (0.1, "unsure")]
    choice = choose_threshold("auto", js, labeled, **AUTO)
    # Mejor F1 (= 1) en [0.35, 0.45] → punto medio en la grilla.
    assert (choice.method, choice.threshold) == ("labels", 0.4)
    # Con menos pares que el mínimo, las etiquetas no deciden.
    few = choose_threshold("auto", js, labeled[2:], **AUTO)
    assert (few.method, few.threshold) == ("valley", 0.51)


def test_numeric_threshold_is_respected(cfg: Config) -> None:
    choice = choose_threshold(0.6, [0.1, 0.9], [(0.5, "same")] * 5 + [(0.1, "diff")] * 5, **AUTO)
    assert (choice.method, choice.threshold) == ("config", 0.6)

    auto_records = _run(cfg)
    auto = json.loads((cfg.paths.processed_dir / dedup.VERSIONS_FILE).read_text())
    assert auto[validate_threshold.THRESHOLD_KEY]["method"] in ("valley", "fallback")
    fixed = dataclasses.replace(cfg, dedup=dataclasses.replace(cfg.dedup, near_dup_threshold=0.6))
    fixed_records = _run(fixed)
    rec = json.loads((cfg.paths.processed_dir / dedup.VERSIONS_FILE).read_text())
    assert rec[validate_threshold.THRESHOLD_KEY]["method"] == "config"
    assert rec[validate_threshold.THRESHOLD_KEY]["threshold"] == 0.6
    assert validate_threshold.near_dup_threshold(fixed) == 0.6
    report = (cfg.paths.reports_dir / "dedup.md").read_text(encoding="utf-8")
    assert "Umbral: **Jaccard ≥ 0.6**" in report and "Método: **config**" in report
    # En este corpus no hay pares entre el valle y 0.6: mismos clusters.
    assert [r["cluster_id"] for r in fixed_records] == [r["cluster_id"] for r in auto_records]
