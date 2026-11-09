"""Tests de evaluate: BM25, métricas, criterio de acierto y la etapa sobre datos sintéticos."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from meli_docs_etl.config import Config, load_config
from meli_docs_etl.retrieval import BM25, first_hit_rank, is_hit, metrics, tokenize
from meli_docs_etl.stages import evaluate as stage

# --------------------------------------------------------------------------- unitarios


def test_tokenize_lowercases_and_splits_words_and_numbers() -> None:
    assert tokenize("GET /v1/Items?id=42 BILLING_LIMIT año") == [
        "get", "v1", "items", "id", "42", "billing", "limit", "año"
    ]  # fmt: skip


def test_bm25_scores_match_hand_computation() -> None:
    bm = BM25(["d0", "d1", "d2"], ["apple banana", "apple cherry", "durian"], k1=1.5, b=0.75)
    # N = 3, df(banana) = 1 → idf = ln(1 + 2.5 / 1.5); avgdl = 5/3; d0: tf = 1, |d| = 2.
    idf = math.log(1 + 2.5 / 1.5)
    expected = idf * 1 * 2.5 / (1 + 1.5 * (1 - 0.75 + 0.75 * 2 / (5 / 3)))
    assert bm.scores("banana") == pytest.approx([expected, 0.0, 0.0])
    # `apple` está en 2 de 3 documentos: idf más bajo que `banana`.
    assert bm.idf["apple"] < bm.idf["banana"]
    assert bm.rank("banana apple") == ["d0", "d1", "d2"]
    assert bm.rank("cherry") == ["d1", "d0", "d2"]  # empate en 0 → orden original
    assert bm.rank("durian")[0] == "d2"
    assert bm.rank("unknown") == ["d0", "d1", "d2"]


def test_bm25_length_normalization_prefers_shorter_doc() -> None:
    bm = BM25(["long", "short"], ["kafka " + "filler " * 20, "kafka topic"])
    assert bm.rank("kafka") == ["short", "long"]


def test_recall_and_mrr_by_hand() -> None:
    ranks = [1, 3, None, 12]
    m = metrics(ranks, (1, 5, 10))
    assert m == pytest.approx(
        {"R@1": 1 / 4, "R@5": 2 / 4, "R@10": 2 / 4, "MRR": (1 + 1 / 3 + 1 / 12) / 4}
    )
    assert first_hit_rank(["a", "b", "c"], {"c", "b"}) == 2
    assert first_hit_rank(["a"], set()) is None


def test_hit_criterion_by_evidence_and_by_operation() -> None:
    q = {"qa_type": "llm", "evidence": ["The worker retries   every\n30 seconds."]}
    assert is_hit(q, {"text": "# Worker\n\nThe worker retries every 30 seconds. More."})
    assert not is_hit(q, {"text": "The worker retries every"})  # evidencia partida
    assert not is_hit({"qa_type": "llm", "evidence": []}, {"text": "x"})
    op = {"qa_type": "openapi", "evidence": ["Operation ID: listItems"]}
    gold = ("shop", "GET", "/items")
    chunk = {"project": "shop", "operation": {"method": "get", "path": "/items"}, "text": "…"}
    assert is_hit(op, chunk, gold)
    other = {**chunk, "operation": {"method": "POST", "path": "/items"}}
    assert not is_hit(op, other, gold)  # mismo path, otro método
    assert not is_hit(op, {**chunk, "project": "other"}, gold)


# --------------------------------------------------------------------------- etapa


def _chunk(cid: str, project: str, text: str, op: dict | None = None) -> dict:
    head = f"{project} › guide/{cid}.md › Sección"
    return {
        "chunk_id": cid,
        "project": project,
        "source_path": f"{project}/1.0/guide/{cid}.md",
        "language": "en",
        "n_tokens": len(text.split()),
        "text": text,
        "contextualized_text": f"{head}\n\n{text}",
        "operation": op,
        "source_type": "openapi" if op else "markdown",
    }


def _q(qid: str, cid: str, split: str, evidence: str, question: str, **kw: object) -> dict:
    return {
        "qa_id": qid,
        "chunk_id": cid,
        "split": split,
        "qa_type": "llm",
        "question": question,
        "evidence": [evidence],
        "language": "en",
        "leak_risk": False,
        **kw,
    }


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    cfg = load_config(
        overrides={
            "outputs_dir": tmp_path / "outputs",
            "reports_dir": tmp_path / "reports",
            "processed_dir": tmp_path / "processed",
        }
    )
    chunks = [
        _chunk("c-bill", "alpha", "The billing worker retries failed jobs every 30 seconds."),
        _chunk("c-ship", "alpha", "Shipping labels are printed by the label service at noon."),
        _chunk("c-auth", "beta", "Tokens expire after 15 minutes and are refreshed by the SDK."),
        _chunk(
            "c-op",
            "beta",
            "## GET /items\n\nOperation ID: listItems",
            {"method": "GET", "path": "/items", "operation_id": "listItems"},
        ),
    ]
    qa = [
        _q("q1", "c-bill", "eval_section", "retries failed jobs every 30 seconds", "How often "
           "does the alpha billing worker retry failed jobs?"),
        _q("q2", "c-auth", "eval_project", "Tokens expire after 15 minutes", "When do beta "
           "tokens expire?"),
        _q("q3", "c-op", "eval_section", "Operation ID: listItems", "Which method and path "
           "does listItems use in beta?", qa_type="openapi", leak_risk=True),
        _q("q4", "c-ship", "train", "Shipping labels", "Who prints alpha shipping labels?"),
        _q("q5", "c-ship", "eval_section", "", "Unanswerable?", qa_type="unanswerable"),
    ]  # fmt: skip
    for d in (cfg.paths.outputs_dir, cfg.paths.processed_dir):
        d.mkdir(parents=True)
    lines = "".join(json.dumps(c) + "\n" for c in chunks)
    (cfg.paths.outputs_dir / "corpus.jsonl").write_text(lines, encoding="utf-8")
    for s in ("section", "section_split", "merged"):
        (cfg.paths.processed_dir / f"corpus_{s}.jsonl").write_text(lines, encoding="utf-8")
    (cfg.paths.outputs_dir / "qa.jsonl").write_text(
        "".join(json.dumps(q) + "\n" for q in qa), encoding="utf-8"
    )
    return cfg


def test_stage_reports_eval_questions_with_and_without_leak_risk(cfg: Config) -> None:
    report = stage.run(cfg)
    data = json.loads((cfg.paths.outputs_dir / stage.METRICS_FILE).read_text(encoding="utf-8"))
    assert data["n_questions"] == 3  # sin train ni unanswerable

    def row(subset: str, method: str = "bm25", split: str = "total") -> dict:
        (r,) = [
            r
            for r in data["rows"]
            if (r["subset"], r["strategy"], r["method"], r["split"])
            == (subset, "merged", method, split)
        ]
        return r

    assert row("todas")["n"] == 3 and row("sin_leak_risk")["n"] == 2
    assert row("todas")["R@1"] == 1.0 and row("todas")["MRR"] == 1.0
    assert row("todas", split="eval_project")["n"] == 1
    assert 0 < row("todas", "aleatorio")["MRR"] <= 1
    text = report.read_text(encoding="utf-8")
    for heading in ("## 1.", "## 4. Conclusión", "## 5. eval_section", "## 6.", "## 7."):
        assert heading in text
    first = text
    stage.run(cfg)
    assert report.read_text(encoding="utf-8") == first  # determinista


def test_stale_qa_fails(cfg: Config) -> None:
    path = cfg.paths.outputs_dir / "qa.jsonl"
    stale = _q("q9", "ck-gone", "eval_section", "x" * 10, "Where did this chunk go?")
    path.write_text(path.read_text(encoding="utf-8") + json.dumps(stale) + "\n", encoding="utf-8")
    with pytest.raises(stage.EvaluateError, match="desactualizado"):
        stage.run(cfg)
