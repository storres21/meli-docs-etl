"""Etapa 6 — Q&A anclado a fichas → outputs/qa.jsonl + reports/qa.md.

Tres tipos de preguntas, cada una anclada a un chunk_id y con el split de su ficha:
- `llm`: generadas desde el `text` de la ficha; la `evidence` debe aparecer literal en ella.
- `openapi`: deterministas (sin LLM) desde las fichas de swagger: método y path, parámetros
  obligatorios y códigos de respuesta, con respuesta exacta y verificador.
- `unanswerable`: plausibles pero sin respuesta en la ficha ni en sus vecinas (lo decide el
  juez); la respuesta es "la documentación no lo especifica" en el idioma de la ficha.

Embudo (conteos en el reporte): JSON inválido → evidencia no literal → trivial → ambigua →
casi-duplicada (entre splits se descarta la de eval) → LLM-juez. Primero se generan todas
las preguntas y después se juzgan (con Ollama, un solo cambio de modelo).

El LLM pasa por la cache de `llm.py`. En `replay` (default) no hace falta red: si falta
alguna respuesta la etapa falla sin escribir nada y dice cómo grabarlas.

También escribe `<processed_dir>/qa_candidates.jsonl` (todas las candidatas con su motivo
de descarte y los puntajes del juez), que `label-qa` usa para la revisión humana.
"""

from __future__ import annotations

import csv
import json
import logging
import statistics
import time
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from meli_docs_etl.config import Config, display_path
from meli_docs_etl.llm import CachedLLM, CallFn, Prompt, load_prompt
from meli_docs_etl.qa_utils import (
    CRITERIA,
    LANG_NAMES,
    QA_TYPES,
    UNANSWERABLE_ANSWER,
    chat_messages,
    cohen_kappa,
    content_words,
    evidence_match,
    is_ambiguous,
    is_trivial,
    jaccard,
    judge_pass,
    leak_map,
    lexical_neighbors,
    location,
    make_qa_id,
    n_llm_questions,
    openapi_questions,
    parse_accept,
    parse_judge,
    parse_questions,
    resolve_languages,
    selected_unanswerable,
    short_answer_ok,
)
from meli_docs_etl.split_utils import EVAL_PROJECT, EVAL_SECTION, SPLITS, TRAIN
from meli_docs_etl.stages.chunk import CORPUS_FILE

log = logging.getLogger(__name__)

QA_FILE = "qa.jsonl"
CANDIDATES_FILE = "qa_candidates.jsonl"
HUMAN_LABELS_FILE = "qa_judge_labels.csv"
HUMAN_REVIEW_FILE = "qa_review.md"
PROMPTS = ("qa_generate", "qa_unanswerable", "qa_judge", "qa_judge_unanswerable")
SPLIT_ORDER = {TRAIN: 0, EVAL_SECTION: 1, EVAL_PROJECT: 2}
OPENAPI_TEMPLATE = "openapi_template.v1"

# Motivos de descarte, en el orden del embudo.
REASONS = (
    "json_invalido",
    "evidencia_no_literal",
    "trivial",
    "ambigua",
    "casi_duplicada",
    "casi_duplicada_entre_splits",
    "juez_json_invalido",
    "juez_respondible",
    "juez_puntaje_bajo",
)

Chunk = dict[str, Any]
Candidate = dict[str, Any]


class QAError(RuntimeError):
    pass


def read_corpus(path: Path) -> list[Chunk]:
    if not path.exists():
        raise FileNotFoundError(f"{path} no existe: corré antes `meli-etl chunk` y `split`.")
    with open(path, encoding="utf-8") as fh:
        chunks = [json.loads(line) for line in fh]
    if any("split" not in ch for ch in chunks):
        raise QAError(f"{display_path(path)} no tiene el campo `split`: corré `meli-etl split`.")
    return chunks


class Progress:
    """Log de avance con ETA; solo las llamadas reales al proveedor cuentan para el tiempo
    (los aciertos de cache son instantáneos y se informan cada 50)."""

    def __init__(self, phase: str, total: int, llm: CachedLLM) -> None:
        self.phase, self.total, self.llm = phase, total, llm
        self.i = 0
        self.times: list[float] = []

    def __call__(
        self, chunk_id: str, prompt: Prompt, model: str, chunk_text: str, **values: Any
    ) -> str | None:
        self.i += 1
        calls, t0 = self.llm.calls, time.perf_counter()
        out = self.llm.complete(prompt, model, chunk_id, chunk_text, **values)
        if self.llm.calls > calls:
            self.times.append(time.perf_counter() - t0)
            eta = statistics.mean(self.times) * (self.total - self.i)
            log.info(
                "[%s %d/%d] %s · %.1f s · ETA ~%d min",
                self.phase,
                self.i,
                self.total,
                chunk_id,
                self.times[-1],
                round(eta / 60),
            )
        elif self.i % 50 == 0 or self.i == self.total:
            log.info(
                "[%s %d/%d] (cache; faltan %d)", self.phase, self.i, self.total, self.llm.misses
            )
        return out


def _candidate(ch: Chunk, qa_type: str, lang: str, question: str, **extra: Any) -> Candidate:
    return {
        "qa_id": make_qa_id(ch["chunk_id"], qa_type, question),
        "qa_type": qa_type,
        "chunk_id": ch["chunk_id"],
        "split": ch["split"],
        "project": ch["project"],
        "language": lang,
        "question": question,
        "discard": None,
        "judge_scores": None,
        "judge_pass": None,
        **extra,
    }


def generate(
    chunks: list[Chunk],
    langs: Mapping[str, tuple[str, str]],
    llm: CachedLLM,
    prompts: Mapping[str, Prompt],
    cfg: Config,
    funnel: Counter,
) -> list[Candidate]:
    q, model = cfg.qa, cfg.llm.generator_model
    out: list[Candidate] = []
    for ch in chunks:
        if ch["source_type"] == "openapi":
            lang = langs[ch["chunk_id"]][0]
            for item in openapi_questions(ch, lang):
                funnel[("openapi", "generadas")] += 1
                out.append(
                    _candidate(
                        ch,
                        "openapi",
                        lang,
                        item.pop("question"),
                        generator={"prompt": OPENAPI_TEMPLATE, "template": item.pop("template")},
                        **item,
                    )
                )

    gen_jobs = [
        (ch, n)
        for ch in chunks
        if ch["source_type"] == "markdown"
        and (n := n_llm_questions(ch["n_tokens"], q.min_tokens, q.two_questions_min_tokens))
    ]
    un_jobs = [
        ch
        for ch in chunks
        if ch["n_tokens"] >= q.min_tokens
        and selected_unanswerable(cfg.seed, ch["chunk_id"], q.unanswerable_ratio)
    ]
    jobs = [("llm", ch, n) for ch, n in gen_jobs] + [("unanswerable", ch, 1) for ch in un_jobs]
    progress = Progress("generar", len(jobs), llm)
    for kind, ch, n in jobs:
        prompt = prompts["qa_generate" if kind == "llm" else "qa_unanswerable"]
        lang = langs[ch["chunk_id"]][0]
        values = {
            "project": ch["project"],
            "location": location(ch),
            "text": ch["text"],
            "n": n,
            "language_name": LANG_NAMES[lang],
        }
        if kind == "llm":
            values["short_max"] = q.short_answer_max_words
        raw = progress(ch["chunk_id"], prompt, model, ch["text"], **values)
        if raw is None:  # miss en replay: la etapa falla al final
            continue
        fields = ("question", "answer", "evidence") if kind == "llm" else ("question",)
        items, bad = parse_questions(raw, n, fields)
        funnel[(kind, "generadas")] += n
        funnel[(kind, "json_invalido")] += bad
        gen = {"model": model, "prompt": prompt.id}
        for it in items:
            if kind == "llm":
                extra = {
                    "answer": it["answer"],
                    "evidence": [it["evidence"]],
                    "short_answer": it.get("short_answer"),
                }
            else:
                extra = {
                    "answer": UNANSWERABLE_ANSWER[lang],
                    "evidence": [],
                    "missing_information": it.get("missing_information"),
                }
            out.append(_candidate(ch, kind, lang, it["question"], generator=gen, **extra))
    return out


def cheap_filters(
    cands: list[Candidate], by_id: Mapping[str, Chunk], cfg: Config
) -> list[dict[str, Any]]:
    """Evidencia literal, trivial, ambigua y casi-duplicadas (no aplican a openapi, que es
    determinista). Devuelve los pares casi-duplicados entre splits (registro)."""
    q = cfg.qa
    for c in cands:
        if c["qa_type"] == "openapi":
            continue
        ch = by_id[c["chunk_id"]]
        if c["qa_type"] == "llm":
            c["evidence_match"] = evidence_match(c["evidence"][0], ch["text"])
            if c["evidence_match"] is None:
                c["discard"] = "evidencia_no_literal"
                continue
        answers = [c.get("short_answer"), c["answer"]] if c["qa_type"] == "llm" else []
        if is_trivial(
            c["question"], answers, ch["section_titles"], ch["project"], q.min_question_words
        ):
            c["discard"] = "trivial"
        elif is_ambiguous(c["question"]):
            c["discard"] = "ambigua"

    # Casi-duplicadas: train primero, así entre splits se descarta siempre la de eval.
    alive = sorted(
        (c for c in cands if c["qa_type"] != "openapi" and c["discard"] is None),
        key=lambda c: (SPLIT_ORDER[c["split"]], c["chunk_id"], c["qa_type"], c["qa_id"]),
    )
    kept: list[tuple[set[str], Candidate]] = []
    cross = []
    for c in alive:
        words = content_words(c["question"])
        for other_words, other in kept:
            sim = jaccard(words, other_words)
            if sim >= q.near_dup_jaccard:
                if other["split"] == c["split"]:
                    c["discard"] = "casi_duplicada"
                else:
                    c["discard"] = "casi_duplicada_entre_splits"
                    cross.append({"descartada": c, "conservada": other, "jaccard": sim})
                c["duplicate_of"] = other["qa_id"]
                break
        else:
            kept.append((words, c))
    return cross


def judge(
    cands: list[Candidate],
    chunks: list[Chunk],
    by_id: Mapping[str, Chunk],
    llm: CachedLLM,
    prompts: Mapping[str, Prompt],
    cfg: Config,
) -> None:
    model, q = cfg.llm.judge_model, cfg.qa
    todo = sorted(
        (c for c in cands if c["qa_type"] != "openapi" and c["discard"] is None),
        key=lambda c: c["qa_id"],
    )
    progress = Progress("juzgar", len(todo), llm)
    for c in todo:
        ch = by_id[c["chunk_id"]]
        values = {"project": ch["project"], "text": ch["text"], "question": c["question"]}
        if c["qa_type"] == "unanswerable":
            prompt = prompts["qa_judge_unanswerable"]
            neigh = lexical_neighbors(c["question"], ch, chunks, q.neighbors)
            c["judge_neighbors"] = [n["chunk_id"] for n in neigh]
            values["neighbors"] = (
                "\n".join(
                    f"<doc>\n{location(n)}\n{n['text'][: q.neighbor_max_chars]}\n</doc>"
                    for n in neigh
                )
                or "(none)"
            )
        else:
            prompt = prompts["qa_judge"]
            values["answer"] = c["answer"]
        raw = progress(ch["chunk_id"], prompt, model, ch["text"], **values)
        if raw is None:
            continue
        c["judge"] = {"model": model, "prompt": prompt.id}
        scores = parse_judge(raw, c["qa_type"])
        if scores is None:
            c["discard"] = "juez_json_invalido"
            continue
        c["judge_scores"] = scores
        c["judge_pass"] = judge_pass(scores, q.judge_min_score)
        if not c["judge_pass"]:
            c["discard"] = "juez_respondible" if scores.get("answered") else "juez_puntaje_bajo"


def to_record(c: Candidate, ch: Chunk, leaks: Mapping[str, Any], cfg: Config) -> dict[str, Any]:
    lang = c["language"]
    if c["qa_type"] == "openapi":
        answer_type, ref, verifier = "short", c["reference_answer"], c["verifier"]
    elif c["qa_type"] == "unanswerable":
        answer_type, ref, verifier = "short", c["answer"], "normalized"
    elif short_answer_ok(c.get("short_answer"), ch["text"], cfg.qa.short_answer_max_words):
        answer_type, ref, verifier = "short", c["short_answer"], "normalized"
    else:
        answer_type, ref, verifier = "long", None, None
    rag, closed = chat_messages(c["question"], c["answer"], ch, lang)
    scores = None
    if c["judge_scores"]:
        scores = {k: v for k, v in c["judge_scores"].items() if k != "rationale"}
    return {
        "qa_id": c["qa_id"],
        "question": c["question"],
        "answer": c["answer"],
        "evidence": c["evidence"],
        "qa_type": c["qa_type"],
        "answer_type": answer_type,
        "reference_answer": ref,
        "verifier": verifier,
        "chunk_id": ch["chunk_id"],
        "split": ch["split"],
        "project": ch["project"],
        "source_path": ch["source_path"],
        "section_path": ch["section_path"],
        "language": lang,
        "leak_risk": ch["split"] != TRAIN and ch["chunk_id"] in leaks,
        "judge_scores": scores,
        "generator": c["generator"],
        "messages_rag": rag,
        "messages_closed_book": closed,
    }


def read_human_labels(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def agreement(cands: list[Candidate], labels: list[dict[str, str]]) -> dict[str, Any] | None:
    """Acuerdo juez-humano sobre la muestra etiquetada: aceptar/rechazar (% y κ) y error
    absoluto medio por criterio."""
    judged = {c["qa_id"]: c for c in cands if c["judge_pass"] is not None}
    pairs, diffs = [], defaultdict(list)
    by_type: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    for row in labels:
        c = judged.get(row.get("qa_id", ""))
        human = parse_accept(row.get("accept"))
        if c is None or human is None:
            continue
        pairs.append((human, c["judge_pass"]))
        by_type[c["qa_type"]].append((human, c["judge_pass"]))
        for crit in CRITERIA:
            h = (row.get(crit) or "").strip()
            if h.isdigit() and crit in c["judge_scores"]:
                diffs[crit].append(abs(int(h) - c["judge_scores"][crit]))
    if not pairs:
        return None
    return {
        "n": len(pairs),
        "agree": sum(a == b for a, b in pairs) / len(pairs),
        "kappa": cohen_kappa(pairs),
        "confusion": Counter(pairs),
        "by_type": {t: (len(p), sum(a == b for a, b in p) / len(p)) for t, p in by_type.items()},
        "mae": {k: (len(v), statistics.mean(v)) for k, v in diffs.items() if v},
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def run(cfg: Config, call: CallFn | None = None) -> Path:
    corpus_path = cfg.paths.outputs_dir / CORPUS_FILE
    chunks = sorted(read_corpus(corpus_path), key=lambda ch: ch["chunk_id"])
    by_id = {ch["chunk_id"]: ch for ch in chunks}
    langs = resolve_languages(chunks, cfg.qa.default_language)
    leaks = leak_map(chunks)
    prompts = {
        name: load_prompt(cfg.paths.prompts_dir, name, cfg.qa.prompt_version) for name in PROMPTS
    }
    llm = CachedLLM(cfg.llm, cfg.paths.llm_cache_dir, cfg.seed, call)
    log.info(
        "QA sobre %d fichas | proveedor=%s generador=%s juez=%s | cache=%s (%s)",
        len(chunks),
        cfg.llm.provider,
        cfg.llm.generator_model,
        cfg.llm.judge_model,
        cfg.llm.cache_mode,
        display_path(cfg.paths.llm_cache_dir),
    )

    funnel: Counter = Counter()
    cands = generate(chunks, langs, llm, prompts, cfg, funnel)
    cross = cheap_filters(cands, by_id, cfg)
    judge(cands, chunks, by_id, llm, prompts, cfg)
    if llm.misses:
        raise QAError(
            f"Faltan {llm.misses} respuestas del LLM en la cache "
            f"({display_path(cfg.paths.llm_cache_dir)}) y el modo es `replay`; no se escribió "
            "nada (puede faltar más: el juez solo corre sobre lo generado). Grabalas con "
            f"`uv run meli-etl qa --cache-mode record` (proveedor {cfg.llm.provider}; se "
            "reanuda si se corta)."
        )
    for c in cands:
        if c["discard"]:
            funnel[(c["qa_type"], c["discard"])] += 1

    kept = [c for c in cands if c["discard"] is None]
    records = sorted(
        (to_record(c, by_id[c["chunk_id"]], leaks, cfg) for c in kept),
        key=lambda r: (
            SPLIT_ORDER[r["split"]],
            r["project"],
            r["chunk_id"],
            QA_TYPES.index(r["qa_type"]),
            r["qa_id"],
        ),
    )
    out_path = cfg.paths.outputs_dir / QA_FILE
    _write_jsonl(out_path, records)
    _write_jsonl(cfg.paths.processed_dir / CANDIDATES_FILE, sorted(cands, key=lambda c: c["qa_id"]))
    labels = read_human_labels(cfg.paths.labels_dir / HUMAN_LABELS_FILE)
    report = cfg.paths.reports_dir / "qa.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        render_report(records, cands, chunks, langs, leaks, cross, funnel, labels, prompts, cfg),
        encoding="utf-8",
    )
    counts = Counter((r["split"], r["qa_type"]) for r in records)
    log.info(
        "QA: %d preguntas (%s) | cache: %d aciertos, %d llamadas",
        len(records),
        ", ".join(f"{s}={sum(v for (sp, _), v in counts.items() if sp == s)}" for s in SPLITS),
        llm.hits,
        llm.calls,
    )
    log.info("Escrito %s y reporte %s", display_path(out_path), display_path(report))
    return out_path


# --------------------------------------------------------------------------- reporte


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    def cell(v: Any) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")

    return [
        "| " + " | ".join(headers) + " |",
        "|" + "---|" * len(headers),
        *("| " + " | ".join(cell(v) for v in r) + " |" for r in rows),
        "",
    ]


def _short(text: str, n: int = 140) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _example(r: Mapping[str, Any]) -> list[str]:
    lines = [
        f"`{r['qa_id']}` · {r['qa_type']} · {r['split']} · {r['language']} · "
        f"`{r['chunk_id']}` ({r['source_path']})",
        "",
        f"- **Pregunta:** {r['question']}",
        f"- **Respuesta:** {r['answer']}",
    ]
    for ev in r["evidence"]:
        lines.append(f"- **Evidencia:** `{_short(ev, 200)}`")
    if r["verifier"]:
        lines.append(
            f"- **reference_answer** ({r['verifier']}): "
            f"`{json.dumps(r['reference_answer'], ensure_ascii=False)}`"
        )
    if r["judge_scores"]:
        lines.append(f"- **Juez:** {r['judge_scores']}")
    return [*lines, ""]


def render_report(
    records: list[dict[str, Any]],
    cands: list[Candidate],
    chunks: list[Chunk],
    langs: Mapping[str, tuple[str, str]],
    leaks: Mapping[str, Any],
    cross: list[dict[str, Any]],
    funnel: Counter,
    labels: list[dict[str, str]],
    prompts: Mapping[str, Prompt],
    cfg: Config,
) -> str:
    q = cfg.qa
    out = [
        "# QA: preguntas ancladas a fichas",
        "",
        f"Generado por `meli-etl qa` desde `outputs/{CORPUS_FILE}` ({len(chunks)} fichas). "
        f"Salida: `outputs/{QA_FILE}`. Proveedor `{cfg.llm.provider}`; generador "
        f"`{cfg.llm.generator_model}`, juez `{cfg.llm.judge_model}` (familias distintas para "
        f"reducir la auto-aprobación); temperatura {cfg.llm.temperature}. Respuestas del LLM "
        "cacheadas en `data/cache/llm/` (la etapa se reproduce sin red).",
        "",
        "Prompts: "
        + ", ".join(f"`{p.id}` (sha `{p.sha[:12]}`)" for p in prompts.values())
        + f"; OpenAPI: plantillas deterministas `{OPENAPI_TEMPLATE}`.",
        "",
        "## 1. Conteos",
        "",
    ]
    by = Counter((r["split"], r["qa_type"]) for r in records)
    out += _table(
        ["Split", *QA_TYPES, "Total"],
        [[s, *(by[(s, t)] for t in QA_TYPES), sum(by[(s, t)] for t in QA_TYPES)] for s in SPLITS]
        + [
            [
                "**Total**",
                *(sum(by[(s, t)] for s in SPLITS) for t in QA_TYPES),
                len(records),
            ]
        ],
    )
    proj = Counter((r["project"], r["split"]) for r in records)
    projects = sorted({r["project"] for r in records})
    out += ["**Por proyecto:**", ""]
    out += _table(
        ["Proyecto", *SPLITS, "Total"],
        [[p, *(proj[(p, s)] for s in SPLITS), sum(proj[(p, s)] for s in SPLITS)] for p in projects],
    )
    lang = Counter((r["language"], r["qa_type"]) for r in records)
    src = Counter(langs[r["chunk_id"]][1] for r in records)
    out += ["**Por idioma** (idioma de la pregunta = idioma de la ficha):", ""]
    out += _table(
        ["Idioma", *QA_TYPES, "Total"],
        [
            [lg, *(lang[(lg, t)] for t in QA_TYPES), sum(lang[(lg, t)] for t in QA_TYPES)]
            for lg in sorted({r["language"] for r in records})
        ],
    )
    out += [
        f"Origen del idioma: {src['ficha']} preguntas de fichas es/en, {src['proyecto']} de "
        f"fichas `unknown`/`mixed` resueltas con el idioma mayoritario de su proyecto, "
        f"{src['default']} con el default (`qa.default_language = {q.default_language}`).",
        "",
    ]
    vt = Counter((r["answer_type"], r["verifier"] or "—") for r in records)
    out += ["**Tipo de respuesta y verificador** (útil para RL con recompensa verificable):", ""]
    out += _table(
        ["answer_type", "verifier", "Preguntas"], [[a, v, n] for (a, v), n in sorted(vt.items())]
    )

    # 2. Embudo
    out += [
        "## 2. Embudo de descartes",
        "",
        "Orden de los filtros: JSON inválido → evidencia no literal (solo `llm`) → trivial → "
        "ambigua → casi-duplicada → juez. `openapi` es determinista: no pasa por los filtros "
        f"ni por el juez. Casi-duplicadas: Jaccard de palabras de contenido ≥ "
        f"{q.near_dup_jaccard}; el juez exige cada criterio ≥ {q.judge_min_score}.",
        "",
    ]
    rows = []
    for t in QA_TYPES:
        row = [t, funnel[(t, "generadas")]]
        row += [funnel[(t, r)] or "" for r in REASONS]
        row.append(sum(1 for r in records if r["qa_type"] == t))
        rows.append(row)
    out += _table(["Tipo", "Generadas", *REASONS, "Final"], rows)
    ws = sum(1 for c in cands if c.get("evidence_match") == "espacios" and c["discard"] is None)
    out += [
        f"Evidencia aceptada solo colapsando espacios en blanco: {ws} (el resto es literal "
        "exacta).",
        "",
    ]

    # 3. Casi-duplicadas entre splits
    out += [
        "## 3. Casi-duplicadas entre splits (descartadas de eval)",
        "",
        "Se conserva la de train (o la del split que va primero) y se descarta la de eval, "
        "para que eval no pregunte lo mismo que train.",
        "",
    ]
    if cross:
        out += _table(
            ["Jaccard", "Descartada", "Split", "Conservada", "Split"],
            [
                [
                    f"{x['jaccard']:.2f}",
                    _short(x["descartada"]["question"], 90),
                    x["descartada"]["split"],
                    _short(x["conservada"]["question"], 90),
                    x["conservada"]["split"],
                ]
                for x in sorted(cross, key=lambda x: x["descartada"]["qa_id"])
            ],
        )
    else:
        out += ["Ninguna.", ""]

    # 4. Fuga
    risky = [r for r in records if r["leak_risk"]]
    out += [
        "## 4. Riesgo de fuga (`leak_risk = true`)",
        "",
        "Preguntas de eval sobre fichas cuyo endpoint también aparece en una ficha de train "
        "(auditoría §5.2 de `reports/split.md`): un modelo entrenado en train puede responderlas "
        "sin haber aprendido la ficha. Se conservan, marcadas, para poder excluirlas o "
        f"reportarlas aparte en `evaluate`. Total: {len(risky)}.",
        "",
    ]
    if risky:
        out += _table(
            ["qa_id", "Split", "Tipo", "Endpoint", "Mención en train", "Pregunta"],
            [
                [
                    r["qa_id"],
                    r["split"],
                    r["qa_type"],
                    "; ".join(sorted({lk.endpoint for lk in leaks[r["chunk_id"]]})),
                    "; ".join(sorted({lk.mentioned_as for lk in leaks[r["chunk_id"]]})),
                    _short(r["question"], 90),
                ]
                for r in risky
            ],
        )

    # 5. Juez
    judged = [c for c in cands if c["judge_scores"]]
    out += ["## 5. LLM-juez", ""]
    if judged:
        rows = []
        for t in ("llm", "unanswerable"):
            js = [c for c in judged if c["qa_type"] == t]
            if not js:
                continue
            means = [
                f"{statistics.mean(c['judge_scores'][k] for c in js):.2f}"
                if k in js[0]["judge_scores"]
                else "—"
                for k in CRITERIA
            ]
            answered = sum(bool(c["judge_scores"].get("answered")) for c in js)
            ok = sum(c["judge_pass"] for c in js)
            rows.append(
                [
                    t,
                    len(js),
                    *means,
                    answered if t == "unanswerable" else "—",
                    f"{ok / len(js):.0%}",
                ]
            )
        out += _table(
            ["Tipo", "Juzgadas", *CRITERIA, "Respondible (descartada)", "Aprobadas"], rows
        )
    else:
        out += ["Sin preguntas juzgadas.", ""]

    # 6. Acuerdo
    out += ["## 6. Acuerdo juez-humano", ""]
    agr = agreement(cands, labels)
    if agr is None:
        out += [
            f"Sin etiquetas todavía. `meli-etl label-qa` exporta una muestra de "
            f"{q.human_sample_size} preguntas juzgadas (estratificada por tipo y veredicto del "
            f"juez, sin mostrar sus puntajes) a `data/labels/{HUMAN_REVIEW_FILE}`; completá "
            f"`data/labels/{HUMAN_LABELS_FILE}` y volvé a correr `meli-etl qa`.",
            "",
        ]
    else:
        conf = agr["confusion"]
        kappa = "—" if agr["kappa"] is None else f"{agr['kappa']:.2f}"
        out += [
            f"{agr['n']} preguntas etiquetadas. Acuerdo en aceptar/rechazar: "
            f"**{agr['agree']:.0%}**, κ de Cohen **{kappa}** (la muestra sobrerrepresenta las "
            "rechazadas a propósito, así que el κ mide acuerdo en ambos sentidos, no la tasa "
            "real de aprobación).",
            "",
        ]
        out += _table(
            ["", "Juez acepta", "Juez rechaza"],
            [
                ["**Humano acepta**", conf[(True, True)], conf[(True, False)]],
                ["**Humano rechaza**", conf[(False, True)], conf[(False, False)]],
            ],
        )
        out += _table(
            ["Tipo", "Etiquetadas", "Acuerdo"],
            [[t, n, f"{a:.0%}"] for t, (n, a) in sorted(agr["by_type"].items())],
        )
        if agr["mae"]:
            out += _table(
                ["Criterio", "Pares", "Error absoluto medio (1-5)"],
                [[k, n, f"{m:.2f}"] for k, (n, m) in sorted(agr["mae"].items())],
            )

    # 7. Ejemplos
    out += ["## 7. Ejemplos", ""]
    for t in QA_TYPES:
        rs = [r for r in records if r["qa_type"] == t]
        out += [f"### {t}", ""]
        if not rs:
            out += ["Sin preguntas.", ""]
            continue
        picks = sorted(rs, key=lambda r: r["qa_id"])[:2]
        for r in picks:
            out += _example(r)
    return "\n".join(out)
