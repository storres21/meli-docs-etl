"""Funciones puras de la etapa qa: preguntas OpenAPI deterministas, filtros de calidad,
idioma, identificadores estables, formato chat (SFT), fuga y acuerdo juez-humano."""

from __future__ import annotations

import hashlib
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from meli_docs_etl.lang import EN_STOPWORDS, ES_STOPWORDS
from meli_docs_etl.split_utils import TRAIN, EndpointLeak, endpoint_leaks, group_hash

QA_TYPES = ("llm", "openapi", "unanswerable")
# Rúbrica del juez (1-5). En unanswerable no hay faithfulness: el juez decide `answered`.
CRITERIA = ("faithfulness", "clarity", "usefulness")
LANGS = ("es", "en")
# Nombre del idioma dentro de los prompts (escritos en inglés).
LANG_NAMES = {"es": "Spanish", "en": "English"}
UNANSWERABLE_ANSWER = {
    "es": "La documentación no lo especifica.",
    "en": "The documentation does not specify this.",
}
SYSTEM_RAG = {
    "es": "Responde la pregunta usando solo la documentación proporcionada. Si la "
    "documentación no contiene la respuesta, responde exactamente: «"
    + UNANSWERABLE_ANSWER["es"]
    + "»",
    "en": "Answer the question using only the documentation provided. If the documentation "
    'does not contain the answer, reply exactly: "' + UNANSWERABLE_ANSWER["en"] + '"',
}
SYSTEM_CLOSED_BOOK = {
    "es": "Eres un asistente que responde preguntas sobre la documentación técnica interna de "
    "los proyectos de software de la empresa. Si la documentación no especifica algo, "
    "responde exactamente: «" + UNANSWERABLE_ANSWER["es"] + "»",
    "en": "You are an assistant that answers questions about the company's internal software "
    "documentation. If the documentation does not specify something, reply exactly: "
    '"' + UNANSWERABLE_ANSWER["en"] + '"',
}
RAG_LABELS = {"es": ("Documentación", "Pregunta"), "en": ("Documentation", "Question")}

# Evidencia más corta que esto no ancla nada (una palabra suelta casi siempre aparece).
MIN_EVIDENCE_CHARS = 8

_WS = re.compile(r"\s+")
_WORD = re.compile(r"\w+")
_STRIP_CHARS = re.compile(r"[`*_\"'«»“”‘’]")
_QUESTION_WORDS = frozenset(
    """
    qué que cuál cuáles cuál cómo como cuándo cuando dónde donde cuánto cuánta cuántos
    cuántas quién quiénes por para es son se hay debe deben puede pueden
    what which how when where who whom whose why is are do does can should must
    a e y de en in on at to of me no
    """.split()
)  # palabras interrogativas y las ambiguas es/en que lang.py excluye a propósito
_STOP = ES_STOPWORDS | EN_STOPWORDS | _QUESTION_WORDS

# Referencias a un texto que quien lee la pregunta (sin la ficha) no tiene.
_AMBIGUOUS = re.compile(
    r"\b(?:this|the above|the following|the given|the mentioned|the provided|the previous)\s+"
    r"(?:document|documentation|section|text|passage|fragment|snippet|page|guide|file|"
    r"example|table|list|endpoint|service|api|operation|method|command|project)\b"
    r"|\baccording to the (?:text|document|documentation|fragment|section|passage)\b"
    r"|\b(?:este|esta|estos|estas|dicho|dicha|el presente|la presente)\s+"
    r"(?:documento|documentación|sección|texto|fragmento|apartado|página|guía|archivo|"
    r"ejemplo|tabla|lista|endpoint|servicio|api|operación|método|comando|proyecto)\b"
    r"|\bsegún (?:el|la|este|esta) (?:texto|documento|documentación|fragmento|sección)\b"
    r"|\b(?:anteriormente|arriba) mencionad[oa]s?\b|\bmencionad[oa]s? (?:anteriormente|arriba)\b",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- texto


def collapse_ws(text: str) -> str:
    return _WS.sub(" ", text).strip()


def normalize_answer(text: str) -> str:
    """Normalización del verificador `normalized`: NFKC, minúsculas, sin marcas de
    markdown ni comillas, espacios colapsados y sin puntuación en los extremos."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = _STRIP_CHARS.sub("", text)
    return collapse_ws(text).strip(" .,;:!?¿¡")


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def content_words(text: str) -> set[str]:
    return {w for w in words(text) if w not in _STOP}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def make_qa_id(chunk_id: str, qa_type: str, question: str) -> str:
    """Estable mientras no cambien la ficha (su chunk_id), el tipo ni la pregunta."""
    key = f"{chunk_id}|{qa_type}|{normalize_answer(question)}"
    return "qa-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- selección


def resolve_languages(
    chunks: Sequence[Mapping[str, Any]], default: str
) -> dict[str, tuple[str, str]]:
    """chunk_id → (idioma, origen). Origen: `ficha` si la ficha es es/en; si no (unknown,
    mixed), `proyecto` = idioma mayoritario (en tokens) entre las fichas es/en del proyecto;
    `default` si el proyecto no tiene ninguna."""
    by_project: dict[str, Counter] = defaultdict(Counter)
    for ch in chunks:
        if ch["language"] in LANGS:
            by_project[ch["project"]][ch["language"]] += ch["n_tokens"]
    out = {}
    for ch in chunks:
        if ch["language"] in LANGS:
            out[ch["chunk_id"]] = (ch["language"], "ficha")
        elif by_project[ch["project"]]:
            top = sorted(by_project[ch["project"]].items(), key=lambda kv: (-kv[1], kv[0]))
            out[ch["chunk_id"]] = (top[0][0], "proyecto")
        else:
            out[ch["chunk_id"]] = (default, "default")
    return out


def n_llm_questions(n_tokens: int, min_tokens: int, two_min_tokens: int) -> int:
    if n_tokens < min_tokens:
        return 0
    return 2 if n_tokens > two_min_tokens else 1


def selected_unanswerable(seed: int, chunk_id: str, ratio: float) -> bool:
    """Selección estable (no depende de las demás fichas): sha256(seed|unanswerable|id)."""
    return group_hash(seed, f"unanswerable|{chunk_id}") < ratio


def location(chunk: Mapping[str, Any]) -> str:
    """Primera línea del texto contextualizado: `proyecto › archivo › sección`."""
    return chunk["contextualized_text"].split("\n", 1)[0]


def lexical_neighbors(
    question: str, chunk: Mapping[str, Any], candidates: Iterable[Mapping[str, Any]], k: int
) -> list[Mapping[str, Any]]:
    """Las k fichas del mismo proyecto (sin la propia) que comparten más palabras de
    contenido con la pregunta. Para que el juez descarte preguntas "sin respuesta" que otra
    ficha sí responde."""
    q = content_words(question)
    scored = []
    for c in candidates:
        if c["chunk_id"] == chunk["chunk_id"] or c["project"] != chunk["project"]:
            continue
        score = len(q & set(words(c["text"])))
        if score:
            scored.append((-score, c["chunk_id"], c))
    return [c for _, _, c in sorted(scored, key=lambda t: t[:2])[:k]]


# --------------------------------------------------------------------------- respuestas del LLM


def parse_json(raw: str | None) -> dict[str, Any] | None:
    """JSON del modelo; tolera texto o cercas ``` alrededor del objeto."""
    if not raw:
        return None
    for candidate in (raw, raw[raw.find("{") : raw.rfind("}") + 1]):
        try:
            obj = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _str(v: Any) -> str | None:
    return v.strip() if isinstance(v, str) and v.strip() else None


def parse_questions(raw: str | None, n: int, fields: Sequence[str]) -> tuple[list[dict], int]:
    """Hasta n preguntas válidas (con todos los `fields` como texto no vacío) y la cantidad
    de las n pedidas que faltan o vinieron mal formadas."""
    obj = parse_json(raw)
    items = obj.get("questions") if obj else None
    if not isinstance(items, list):
        return [], n
    valid = []
    for it in items[:n]:
        if not isinstance(it, dict) or any(_str(it.get(f)) is None for f in fields):
            continue
        q = {f: _str(it[f]) for f in fields}
        if "short_answer" in it:
            q["short_answer"] = _str(it["short_answer"])
            if q["short_answer"] and q["short_answer"].lower() in ("null", "none"):
                q["short_answer"] = None
        if "missing_information" in it:
            q["missing_information"] = _str(it["missing_information"])
        valid.append(q)
    return valid, n - len(valid)


def _score(v: Any) -> int | None:
    try:
        s = int(round(float(v)))
    except (TypeError, ValueError):
        return None
    return s if 1 <= s <= 5 else None


def _bool(v: Any) -> bool | None:
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "false"):
        return v.strip().lower() == "true"
    return None


def parse_judge(raw: str | None, qa_type: str) -> dict[str, Any] | None:
    """Puntajes del juez o None si falta alguno. llm: faithfulness, clarity, usefulness;
    unanswerable: answered (bool), clarity, usefulness."""
    obj = parse_json(raw)
    if obj is None:
        return None
    criteria = ("clarity", "usefulness") if qa_type == "unanswerable" else CRITERIA
    out: dict[str, Any] = {c: _score(obj.get(c)) for c in criteria}
    if qa_type == "unanswerable":
        out["answered"] = _bool(obj.get("answered"))
    if any(v is None for v in out.values()):
        return None
    out["rationale"] = _str(obj.get("rationale")) or ""
    return out


def judge_pass(scores: Mapping[str, Any], min_score: int) -> bool:
    if scores.get("answered"):
        return False
    return all(scores[c] >= min_score for c in CRITERIA if c in scores)


# --------------------------------------------------------------------------- filtros


def evidence_match(evidence: str, text: str) -> str | None:
    """`literal` si la cita aparece tal cual; `espacios` si aparece solo colapsando
    espacios en blanco (único ajuste permitido); None si no aparece o es muy corta."""
    if len(evidence.strip()) < MIN_EVIDENCE_CHARS:
        return None
    if evidence in text:
        return "literal"
    if collapse_ws(evidence) in collapse_ws(text):
        return "espacios"
    return None


def is_trivial(
    question: str,
    answers: Iterable[str | None],
    titles: Iterable[str],
    project: str,
    min_words: int,
) -> bool:
    """Muy corta, contiene su propia respuesta, o es solo un título hecho pregunta."""
    if len(words(question)) < min_words:
        return True
    nq = normalize_answer(question)
    for a in answers:
        na = normalize_answer(a) if a else ""
        if len(na) >= 3 and na in nq:
            return True
    core = content_words(question) - set(words(project))
    return bool(core) and any(core == content_words(t) for t in titles)


def is_ambiguous(question: str) -> bool:
    return bool(_AMBIGUOUS.search(question))


def short_answer_ok(short: str | None, text: str, max_words: int) -> bool:
    """Respuesta corta verificable: pocas palabras y presente en la ficha."""
    if not short or not words(short) or len(words(short)) > max_words:
        return False
    return normalize_answer(short) in normalize_answer(text)


# --------------------------------------------------------------------------- OpenAPI

_PARAM = re.compile(r"^- `([^`]+)` \((path|query|header|cookie); ([^)]*)\)")
_CODE = re.compile(r"^- `(\d{3}|\dXX|default)`:")
_BLOCK = re.compile(r"^([A-Z][A-Za-z ]*(?: \([^)]*\))?):")


def openapi_facts(chunk: Mapping[str, Any]) -> dict[str, Any]:
    """Hechos verificables de una ficha de swagger, leídos del texto que renderiza
    `openapi.py` (formato fijo), con la línea literal que respalda cada uno."""
    op = chunk["operation"]
    lines = chunk["text"].splitlines()
    header = f"## {op['method']} {op['path']}"
    facts: dict[str, Any] = {
        "method": op["method"],
        "path": op["path"],
        "operation_id": op.get("operation_id"),
        "header": header if header in lines else None,
        "opid_line": None,
        "required": [],  # (nombre, ubicación, línea)
        "codes": [],  # (código, línea)
    }
    block = None
    for ln in lines:
        m = _BLOCK.match(ln)
        if m:
            block = m.group(1)
            if block == "Operation ID":
                facts["opid_line"] = ln
            continue
        if block == "Parameters" and (p := _PARAM.match(ln)):
            if "required" in [x.strip() for x in p.group(3).split(";")]:
                facts["required"].append((p.group(1), p.group(2), ln))
        elif block == "Responses" and (c := _CODE.match(ln)):
            facts["codes"].append((c.group(1), ln))
    return facts


def _enum(items: Sequence[str], lang: str) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + (" y " if lang == "es" else " and ") + items[-1]


def openapi_questions(chunk: Mapping[str, Any], lang: str) -> list[dict[str, Any]]:
    """Hasta 3 preguntas exactas por operación: método y path (verifier exact), parámetros
    obligatorios (set) y códigos de respuesta documentados (set)."""
    f = openapi_facts(chunk)
    project, endpoint = chunk["project"], f"{f['method']} {f['path']}"
    es = lang == "es"
    out = []
    if f["operation_id"] and f["header"] and f["opid_line"]:
        out.append(
            {
                "template": "metodo_path",
                "question": (
                    f"¿Qué método HTTP y qué path usa la operación `{f['operation_id']}` "
                    f"de la API {project}?"
                    if es
                    else f"Which HTTP method and path does the `{f['operation_id']}` operation "
                    f"of the {project} API use?"
                ),
                "answer": (
                    f"La operación `{f['operation_id']}` usa `{endpoint}`."
                    if es
                    else f"The `{f['operation_id']}` operation uses `{endpoint}`."
                ),
                "evidence": [f["header"], f["opid_line"]],
                "reference_answer": endpoint,
                "verifier": "exact",
            }
        )
    if f["required"]:
        names = [n for n, _, _ in f["required"]]
        listed = _enum([f"`{n}` ({loc})" for n, loc, _ in f["required"]], lang)
        out.append(
            {
                "template": "parametros_obligatorios",
                "question": (
                    f"¿Qué parámetros son obligatorios en `{endpoint}` de la API {project}?"
                    if es
                    else f"Which parameters are required by `{endpoint}` in the {project} API?"
                ),
                "answer": (
                    f"Los parámetros obligatorios son {listed}."
                    if es
                    else f"The required parameters are {listed}."
                ),
                "evidence": [ln for _, _, ln in f["required"]],
                "reference_answer": names,
                "verifier": "set",
            }
        )
    if f["codes"]:
        codes = [c for c, _ in f["codes"]]
        out.append(
            {
                "template": "codigos_respuesta",
                "question": (
                    f"¿Qué códigos de respuesta HTTP documenta `{endpoint}` de la API {project}?"
                    if es
                    else f"Which HTTP response codes are documented for `{endpoint}` in the "
                    f"{project} API?"
                ),
                "answer": (
                    f"Documenta {'el código' if len(codes) == 1 else 'los códigos'} "
                    f"{_enum(codes, lang)}."
                    if es
                    else f"It documents {'code' if len(codes) == 1 else 'codes'} "
                    f"{_enum(codes, lang)}."
                ),
                "evidence": [ln for _, ln in f["codes"]],
                "reference_answer": codes,
                "verifier": "set",
            }
        )
    return out


# --------------------------------------------------------------------------- salida


def chat_messages(
    question: str, answer: str, chunk: Mapping[str, Any], lang: str
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """(messages_rag, messages_closed_book): con la ficha como contexto (caso RAG,
    eval_project) y sin ella (conocimiento aprendido, eval_section)."""
    doc_label, q_label = RAG_LABELS[lang]
    rag = [
        {"role": "system", "content": SYSTEM_RAG[lang]},
        {
            "role": "user",
            "content": f"{doc_label}:\n{chunk['contextualized_text']}\n\n{q_label}: {question}",
        },
        {"role": "assistant", "content": answer},
    ]
    closed = [
        {"role": "system", "content": SYSTEM_CLOSED_BOOK[lang]},
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]
    return rag, closed


def leak_map(chunks: Sequence[Mapping[str, Any]]) -> dict[str, list[EndpointLeak]]:
    """chunk_id de eval → endpoints cuyo contenido también está en una ficha de train
    (swagger en eval mencionado en un .md de train, o al revés). Reusa la auditoría de
    split (§5.2), así la marca sigue al corpus y no a una lista fija de endpoints."""
    out: dict[str, list[EndpointLeak]] = defaultdict(list)
    for leak in endpoint_leaks(chunks):
        if leak.openapi_split != TRAIN and leak.markdown_split == TRAIN:
            out[leak.openapi_chunk].append(leak)
        elif leak.markdown_split != TRAIN and leak.openapi_split == TRAIN:
            out[leak.markdown_chunk].append(leak)
    return dict(out)


# --------------------------------------------------------------------------- acuerdo


def parse_accept(value: str | None) -> bool | None:
    v = (value or "").strip().lower()
    if v in ("si", "sí", "s", "yes", "y", "1", "true"):
        return True
    if v in ("no", "n", "0", "false"):
        return False
    return None


def cohen_kappa(pairs: Sequence[tuple[bool, bool]]) -> float | None:
    """κ de Cohen para dos anotadores binarios; None si no está definido."""
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def human_sample(items: Sequence[Mapping[str, Any]], size: int, seed: int) -> list[Mapping]:
    """Muestra estratificada por (qa_type, veredicto del juez), en round-robin: incluye
    preguntas rechazadas para medir el acuerdo en ambos sentidos."""
    strata: dict[tuple[str, bool], list[Mapping]] = defaultdict(list)
    for it in sorted(items, key=lambda x: x["qa_id"]):
        strata[(it["qa_type"], bool(it["judge_pass"]))].append(it)
    rng = random.Random(seed)
    queues = []
    for key in sorted(strata):
        q = list(strata[key])
        rng.shuffle(q)
        queues.append(q)
    out: list[Mapping] = []
    while len(out) < size and any(queues):
        for q in queues:
            if q and len(out) < size:
                out.append(q.pop(0))
    rng.shuffle(out)  # el orden round-robin delataría el veredicto del juez
    return out
