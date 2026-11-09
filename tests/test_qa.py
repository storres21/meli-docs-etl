"""Tests de la etapa qa con un proveedor LLM falso (sin red) y un corpus sintético."""

from __future__ import annotations

import csv
import dataclasses
import json
import re
from pathlib import Path

import pytest

from meli_docs_etl.config import Config, load_config
from meli_docs_etl.llm import CachedLLM, LLMError, load_prompt
from meli_docs_etl.qa_utils import (
    cohen_kappa,
    evidence_match,
    is_ambiguous,
    is_trivial,
    openapi_questions,
)
from meli_docs_etl.stages import label_qa
from meli_docs_etl.stages import qa as stage

OPENAPI_TEXT = """## PUT /v1/whitelist

Agrega una IP a la whitelist

Operation ID: whitelistIP
Tags: whitelist
Servers: http://traffic-gate.local

Parameters:
- `scope` (query; string; values: api, front): The scope to check.
- `ip` (path; string; required): IP a agregar.
- `X-Caller` (header; string; required): Servicio que llama.

Request body (required):
- `reason` (string): Motivo.

Responses:
- `201`: Successful operation
  Content (application/json): Result
    - `code` (string): Código
- `400`: Bad request
- `500`: Internal server error"""


def chunk(
    cid: str,
    project: str,
    split: str,
    text: str,
    language: str = "en",
    source_type: str = "markdown",
    operation: dict | None = None,
    title: str = "Sección",
) -> dict:
    path = f"{project}/1.0/guide/{cid}.md"
    head = f"{project} › guide/{cid}.md › {title}"
    return {
        "chunk_id": f"ck-{cid}",
        "project": project,
        "split": split,
        "split_group": f"sg-{cid}",
        "source_type": source_type,
        "language": language,
        "n_tokens": len(text.split()) * 2,
        "text": text,
        "contextualized_text": f"{head}\nVersions: 1.0\n\n{text}",
        "section_titles": [title],
        "section_path": [title],
        "source_path": path,
        "operation": operation,
        "occurrences": [{"section_id": f"{path}#000", "path": path, "section_path": [title]}],
    }


def body(topic: str, extra: str = "") -> str:
    return (
        f"# {topic.title()}\n\n"
        f"The {topic} worker retries failed jobs every 30 seconds before giving up.\n"
        f"Set `{topic.upper()}_LIMIT` to change the maximum batch size of the {topic} queue.\n"
        f"{extra}"
    )


def base_corpus() -> list[dict]:
    return [
        chunk("t1", "alpha", "train", body("billing")),
        chunk("t2", "alpha", "train", body("invoices")),
        chunk(
            "t3", "gate", "train", body("routing", "Use the /v1/whitelist endpoint to allow IPs.\n")
        ),
        chunk("e1", "alpha", "eval_section", body("refunds")),
        chunk(
            "e2",
            "gate",
            "eval_section",
            OPENAPI_TEXT,
            language="mixed",
            source_type="openapi",
            operation={"method": "PUT", "path": "/v1/whitelist", "operation_id": "whitelistIP"},
        ),
        chunk("p1", "omega", "eval_project", body("shipping")),
        # Idioma desconocido en un proyecto en español → preguntas en español.
        chunk(
            "s1", "sol", "train", "Los pagos se concilian cada noche con el banco central.", "es"
        ),
        chunk(
            "s2",
            "sol",
            "train",
            "```\nRECONCILE_CRON=0 3 * * *\nRECONCILE_TIMEOUT=900\n```",
            "unknown",
        ),
    ]


def _doc(user: str) -> str:
    return user.split("<doc>\n", 1)[1].split("\n</doc>", 1)[0]


class FakeLLM:
    """Responde según el tipo de prompt. `overrides`: `"<tipo>:<texto>"` → respuesta cruda
    cuando la ficha (primer <doc>) contiene <texto>; tipos: generate, unanswerable, judge,
    judge_un."""

    def __init__(self, overrides: dict[str, str] | None = None) -> None:
        self.overrides = overrides or {}
        self.n = 0

    def __call__(self, model: str, system: str, user: str) -> str:
        self.n += 1
        doc = _doc(user)
        project = re.search(r"Project: (\S+)", user).group(1)
        kind = (
            "judge_un"
            if "Other fragments" in user
            else "judge"
            if "Proposed answer:" in user
            else "unanswerable"
            if "NOT in the fragment" in user
            else "generate"
        )
        for key, raw in self.overrides.items():
            k, needle = key.split(":", 1)
            if k == kind and needle in doc:
                return raw
        if kind == "judge":
            return json.dumps({"rationale": "ok", "faithfulness": 5, "clarity": 4, "usefulness": 4})
        if kind == "judge_un":
            return json.dumps({"rationale": "no", "answered": False, "clarity": 4, "usefulness": 4})
        line = next(
            ln
            for ln in doc.splitlines()
            if not ln.startswith("#") and len(re.findall(r"\w+", ln)) > 1
        )
        topic = re.findall(r"\w+", line)[1]
        if kind == "unanswerable":
            q = f"Which TLS version does the {project} {topic} worker queue require?"
            return json.dumps({"questions": [{"question": q, "missing_information": "TLS"}]})
        q = f"How often does the {project} {topic} worker retry failed jobs?"
        return json.dumps(
            {
                "questions": [
                    {
                        "question": q,
                        "answer": "Every 30 seconds.",
                        "evidence": line,
                        "short_answer": "30 seconds",
                    }
                ]
            }
        )


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    base = load_config(
        overrides={
            "outputs_dir": tmp_path / "outputs",
            "reports_dir": tmp_path / "reports",
            "processed_dir": tmp_path / "processed",
            "llm_cache_dir": tmp_path / "cache",
            "labels_dir": tmp_path / "labels",
        }
    )
    cfg = dataclasses.replace(
        base,
        llm=dataclasses.replace(base.llm, cache_mode="record"),
        qa=dataclasses.replace(base.qa, min_tokens=8, unanswerable_ratio=1.0),
    )
    write_corpus(cfg, base_corpus())
    return cfg


def write_corpus(cfg: Config, chunks: list[dict]) -> None:
    path = cfg.paths.outputs_dir / "corpus.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(c) + "\n" for c in chunks), encoding="utf-8")


def read_qa(cfg: Config) -> list[dict]:
    text = (cfg.paths.outputs_dir / "qa.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def candidates(cfg: Config) -> list[dict]:
    text = (cfg.paths.processed_dir / "qa_candidates.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def replay(cfg: Config) -> Config:
    return dataclasses.replace(cfg, llm=dataclasses.replace(cfg.llm, cache_mode="replay"))


def no_provider(model: str, system: str, user: str) -> str:
    raise AssertionError("replay no debe llamar al proveedor")


# --------------------------------------------------------------------------- unitarios


def test_openapi_questions_are_exact_and_literal() -> None:
    ch = base_corpus()[4]
    qs = {q["template"]: q for q in openapi_questions(ch, "en")}
    assert qs["metodo_path"]["reference_answer"] == "PUT /v1/whitelist"
    assert qs["metodo_path"]["verifier"] == "exact"
    # `scope` no es obligatorio; el request body no es un parámetro.
    assert qs["parametros_obligatorios"]["reference_answer"] == ["ip", "X-Caller"]
    assert qs["parametros_obligatorios"]["verifier"] == "set"
    # Solo los códigos del bloque Responses (no los `code` anidados del esquema).
    assert qs["codigos_respuesta"]["reference_answer"] == ["201", "400", "500"]
    for q in qs.values():
        assert all(ev in ch["text"] for ev in q["evidence"])
    es = openapi_questions(ch, "es")
    assert es[0]["question"].startswith("¿Qué método HTTP")


def test_quality_filters() -> None:
    assert evidence_match("retries failed jobs", "The worker retries failed jobs.") == "literal"
    assert evidence_match("retries  failed\njobs", "The worker retries failed jobs.") == "espacios"
    assert evidence_match("retries jobs that failed", "The worker retries failed jobs.") is None
    assert evidence_match("jobs", "jobs") is None  # demasiado corta para anclar
    assert is_ambiguous("What does this section say about retries?")
    assert is_ambiguous("¿Qué devuelve este endpoint cuando falla?")
    assert not is_ambiguous("What does the billing worker of alpha do on failure?")
    assert is_trivial("What is X?", [], [], "alpha", 5)  # muy corta
    assert is_trivial(
        "Is the retry interval of the billing worker 30 seconds?", ["30 seconds"], [], "alpha", 5
    )
    assert is_trivial("What is the Billing Setup in alpha?", [], ["Billing Setup"], "alpha", 5)
    assert cohen_kappa([(True, True), (False, False)]) == 1.0
    assert cohen_kappa([(True, False), (False, True)]) == -1.0


def test_cache_key_changes_with_prompt_model_and_chunk(cfg: Config) -> None:
    llm = CachedLLM(cfg.llm, cfg.paths.llm_cache_dir, cfg.seed, call=lambda m, s, u: "{}")
    p = load_prompt(cfg.paths.prompts_dir, "qa_judge", "v1")
    vals = {"project": "a", "text": "uno", "question": "q", "answer": "r"}
    k = llm.key(p, "m1", *p.render(**vals))
    assert k != llm.key(p, "m2", *p.render(**vals))
    assert k != llm.key(p, "m1", *p.render(**{**vals, "text": "dos"}))
    # El texto insertado no se vuelve a reemplazar (las fichas traen `{{ ENV }}`).
    _, user = p.render(**{**vals, "text": "usa {{ ENV }} y {{question}}"})
    assert "usa {{ ENV }} y {{question}}" in user
    other = dataclasses.replace(p, sha="otro")
    assert k != llm.key(other, "m1", *p.render(**vals))


# --------------------------------------------------------------------------- etapa


def test_evidence_must_be_literal(cfg: Config) -> None:
    bad = json.dumps(
        {
            "questions": [
                {
                    "question": "How often does the alpha invoices worker retry jobs?",
                    "answer": "Every 30 s.",
                    "evidence": "It retries every half minute.",
                    "short_answer": None,
                }
            ]
        }
    )
    stage.run(cfg, call=FakeLLM({"generate:invoices worker": bad}))
    rows = read_qa(cfg)
    by_chunk = {c["chunk_id"] for c in candidates(cfg) if c["discard"] == "evidencia_no_literal"}
    assert by_chunk == {"ck-t2"}
    corpus = {c["chunk_id"]: c for c in base_corpus()}
    llm_rows = [r for r in rows if r["qa_type"] == "llm"]
    assert llm_rows and all(
        ev in corpus[r["chunk_id"]]["text"] for r in llm_rows for ev in r["evidence"]
    )
    report = (cfg.paths.reports_dir / "qa.md").read_text(encoding="utf-8")
    assert "evidencia_no_literal" in report


def test_replay_is_deterministic_without_provider(cfg: Config) -> None:
    fake = FakeLLM()
    stage.run(cfg, call=fake)
    assert fake.n > 0
    first = (cfg.paths.outputs_dir / "qa.jsonl").read_bytes()
    report = (cfg.paths.reports_dir / "qa.md").read_bytes()

    stage.run(replay(cfg), call=no_provider)
    assert (cfg.paths.outputs_dir / "qa.jsonl").read_bytes() == first
    assert (cfg.paths.reports_dir / "qa.md").read_bytes() == report

    # Falta una entrada: falla sin escribir nada y sin llamar al proveedor.
    next(cfg.paths.llm_cache_dir.rglob("*.json")).unlink()
    (cfg.paths.outputs_dir / "qa.jsonl").unlink()
    with pytest.raises(stage.QAError, match="Faltan 1 respuestas"):
        stage.run(replay(cfg), call=no_provider)
    assert not (cfg.paths.outputs_dir / "qa.jsonl").exists()

    # record reanuda: solo pide la que falta.
    resume = FakeLLM()
    stage.run(cfg, call=resume)
    assert resume.n == 1
    assert (cfg.paths.outputs_dir / "qa.jsonl").read_bytes() == first


def test_split_is_inherited_and_fields(cfg: Config) -> None:
    stage.run(cfg, call=FakeLLM())
    rows = read_qa(cfg)
    corpus = {c["chunk_id"]: c for c in base_corpus()}
    assert {r["qa_type"] for r in rows} == {"llm", "openapi", "unanswerable"}
    for r in rows:
        ch = corpus[r["chunk_id"]]
        assert r["split"] == ch["split"] and r["project"] == ch["project"]
        assert r["source_path"] == ch["source_path"]
        assert ch["contextualized_text"] in r["messages_rag"][1]["content"]
        assert r["messages_closed_book"][1]["content"] == r["question"]
        assert r["messages_rag"][-1]["content"] == r["answer"]
        assert (r["verifier"] is None) == (r["answer_type"] == "long")
    assert len({r["qa_id"] for r in rows}) == len(rows)
    # Idioma: s2 es `unknown` en un proyecto en español.
    s2 = [r for r in rows if r["chunk_id"] == "ck-s2"]
    assert s2 and all(r["language"] == "es" for r in s2)
    un = [r for r in s2 if r["qa_type"] == "unanswerable"]
    assert un and un[0]["answer"] == "La documentación no lo especifica."
    assert un[0]["verifier"] == "normalized"


def test_leak_risk_marks_eval_questions_on_endpoints_seen_in_train(cfg: Config) -> None:
    stage.run(cfg, call=FakeLLM())
    rows = read_qa(cfg)
    leaky = {r["chunk_id"] for r in rows if r["leak_risk"]}
    assert leaky == {"ck-e2"}  # swagger en eval, mencionado en ck-t3 (train)
    assert all(r["split"] != "train" for r in rows if r["leak_risk"])
    report = (cfg.paths.reports_dir / "qa.md").read_text(encoding="utf-8")
    section = report.split("## 4.")[1].split("## 5.")[0]
    assert "PUT /v1/whitelist" in section and "/v1/whitelist" in section


def test_near_duplicates_across_splits_drop_the_eval_one(cfg: Config) -> None:
    same = json.dumps(
        {
            "questions": [
                {
                    "question": "How often does the alpha billing worker retry failed jobs?",
                    "answer": "Every 30 seconds.",
                    "evidence": "retries failed jobs every 30 seconds",
                    "short_answer": None,
                }
            ]
        }
    )
    stage.run(cfg, call=FakeLLM({"generate:billing worker": same, "generate:refunds worker": same}))
    cands = {c["chunk_id"]: c for c in candidates(cfg) if c["qa_type"] == "llm"}
    assert cands["ck-t1"]["discard"] is None
    assert cands["ck-e1"]["discard"] == "casi_duplicada_entre_splits"
    assert cands["ck-e1"]["duplicate_of"] == cands["ck-t1"]["qa_id"]
    report = (cfg.paths.reports_dir / "qa.md").read_text(encoding="utf-8")
    assert "Casi-duplicadas entre splits" in report.split("## 4.")[0]


def test_unanswerable_answered_by_context_is_dropped(cfg: Config) -> None:
    answered = json.dumps({"rationale": "sí", "answered": True, "clarity": 5, "usefulness": 5})
    stage.run(cfg, call=FakeLLM({"judge_un:billing worker": answered}))
    un = {c["chunk_id"]: c for c in candidates(cfg) if c["qa_type"] == "unanswerable"}
    assert un["ck-t1"]["discard"] == "juez_respondible"
    assert un["ck-t2"]["discard"] is None
    assert un["ck-t2"]["judge_neighbors"]  # el juez vio vecinas del mismo proyecto


def test_label_qa_sample_is_blind_keeps_labels_and_feeds_agreement(cfg: Config) -> None:
    stage.run(cfg, call=FakeLLM())
    label_qa.run(cfg)
    review = (cfg.paths.labels_dir / "qa_review.md").read_text(encoding="utf-8")
    assert 'faithfulness": ' not in review and "judge" not in review.split("---", 1)[1]
    path = cfg.paths.labels_dir / "qa_judge_labels.csv"
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows and all(not r["accept"] for r in rows)
    rows[0]["accept"], rows[0]["nota"] = "si", "bien"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    label_qa.run(cfg)  # no pisa la etiqueta cargada
    with open(path, encoding="utf-8", newline="") as fh:
        again = {r["qa_id"]: r for r in csv.DictReader(fh)}
    assert again[rows[0]["qa_id"]]["accept"] == "si"
    stage.run(replay(cfg), call=no_provider)
    report = (cfg.paths.reports_dir / "qa.md").read_text(encoding="utf-8")
    assert "1 preguntas etiquetadas" in report


def test_provider_errors_are_explicit(cfg: Config) -> None:
    off = dataclasses.replace(
        cfg, llm=dataclasses.replace(cfg.llm, base_url="http://127.0.0.1:9", timeout_s=2)
    )
    with pytest.raises(LLMError, match="ollama serve"):
        stage.run(off)
