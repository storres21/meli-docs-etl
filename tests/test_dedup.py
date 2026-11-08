"""Tests de deduplicación por sección, regla de fusión y resolución de versiones."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meli_docs_etl.config import Config, load_config
from meli_docs_etl.dedup_utils import body_lines, merge_cluster
from meli_docs_etl.stages import dedup, label_pairs, normalize, validate_threshold

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
    report = validate_threshold.run(cfg)
    text = report.read_text(encoding="utf-8")
    assert "Umbral recomendado" in text and text.count(validate_threshold.MARK_START) == 1
    dedup.run(cfg)
    assert report.read_text(encoding="utf-8") == text
