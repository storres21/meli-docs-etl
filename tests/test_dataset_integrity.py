"""Integridad de los entregables versionados (`outputs/`): invariantes que el pipeline debe
cumplir siempre. A diferencia del resto de los tests, lee los datos reales."""

from __future__ import annotations

import json

import pytest

from meli_docs_etl.config import load_config
from meli_docs_etl.qa_quality import grounded

CFG = load_config()
QA_PATH = CFG.paths.outputs_dir / "qa.jsonl"
CORPUS_PATH = CFG.paths.outputs_dir / "corpus.jsonl"

pytestmark = pytest.mark.skipif(
    not (QA_PATH.exists() and CORPUS_PATH.exists()), reason="faltan los entregables en outputs/"
)


def _read(path):  # noqa: ANN001, ANN202
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def test_every_answer_has_literal_evidence_in_its_chunk() -> None:
    chunks = {c["chunk_id"]: c for c in _read(CORPUS_PATH)}
    qa = _read(QA_PATH)
    assert qa
    bad = [
        q["qa_id"]
        for q in qa
        if q["qa_type"] != "unanswerable" and not grounded(q, chunks[q["chunk_id"]])[1]
    ]
    assert not bad, f"{len(bad)} respuestas sin evidencia literal en su ficha: {bad[:5]}"


def test_questions_inherit_the_split_of_an_existing_chunk() -> None:
    chunks = {c["chunk_id"]: c for c in _read(CORPUS_PATH)}
    for q in _read(QA_PATH):
        assert q["chunk_id"] in chunks, q["qa_id"]
        assert q["split"] == chunks[q["chunk_id"]]["split"], q["qa_id"]
