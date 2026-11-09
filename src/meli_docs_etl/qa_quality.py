"""Calidad del dataset Q&A (sin LLM): cobertura, balance, diversidad, longitudes,
fundamentación, fuga y abstención. Lo usa `evaluate` para la sección final de su reporte.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from itertools import combinations
from typing import Any

from meli_docs_etl.qa_utils import QA_TYPES, collapse_ws, content_words, jaccard
from meli_docs_etl.split_utils import SPLITS

OPENAPI = "openapi"
QA = Mapping[str, Any]
Chunk = Mapping[str, Any]

# Primera(s) palabra(s) de la pregunta → tipo (es/en). Se prueban en orden.
QUESTION_KINDS: tuple[tuple[str, str], ...] = (
    (r"(how many|how much|cuántos|cuántas|cuánto|cuánta)\b", "cuánto"),
    (r"(what|qué|que)\b", "qué"),
    (r"(which|cuál|cuáles)\b", "cuál"),
    (r"(how|cómo)\b", "cómo"),
    (r"(when|cuándo)\b", "cuándo"),
    (r"(where|dónde|en qué)\b", "dónde"),
    (r"(why|por qué)\b", "por qué"),
    (r"(who|quién|quiénes)\b", "quién"),
    (r"(is|are|does|do|can|should|will|es|existe|hay|se puede|puede)\b", "sí/no"),
)


def question_kind(question: str) -> str:
    q = question.strip().lstrip("¿¡\"'`").lower()
    for pattern, kind in QUESTION_KINDS:
        if re.match(pattern, q):
            return kind
    return "otra"


def grounded(q: QA, chunk: Chunk) -> tuple[bool, bool]:
    """(literal exacta, literal con espacios normalizados) de todas las evidencias."""
    ev = [e for e in q["evidence"] if e.strip()]
    if not ev:
        return False, False
    text = chunk["text"]
    flat = collapse_ws(text)
    return all(e in text for e in ev), all(collapse_ws(e) in flat for e in ev)


def near_dup_share(questions: Sequence[QA], threshold: float) -> float:
    """Fracción de preguntas con al menos otra del mismo split a Jaccard ≥ threshold
    (palabras de contenido)."""
    if not questions:
        return 0.0
    words = [content_words(q["question"]) for q in questions]
    dup = set()
    for i, j in combinations(range(len(questions)), 2):
        if jaccard(words[i], words[j]) >= threshold:
            dup.update((i, j))
    return len(dup) / len(questions)


def _pct(n: int, d: int) -> str:
    return f"{n / d:.0%}" if d else "—"


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    def cell(v: Any) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")

    return [
        "| " + " | ".join(headers) + " |",
        "|" + "---|" * len(headers),
        *("| " + " | ".join(cell(v) for v in r) + " |" for r in rows),
        "",
    ]


def _short(text: str, n: int = 100) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _dist(values: Sequence[int]) -> list[Any]:
    if not values:
        return ["—"] * 6
    v = sorted(values)

    def pct(p: float) -> int:
        return v[min(len(v) - 1, int(round(p * (len(v) - 1))))]

    return [len(v), v[0], pct(0.25), int(statistics.median(v)), pct(0.95), v[-1]]


def render_quality(
    qa: Sequence[QA],
    chunks: Sequence[Chunk],
    count_tokens: Callable[[str], int],
    near_dup_threshold: float,
    min_tokens: int,
    discards: Mapping[str, Counter] | None = None,
    section: int = 8,
) -> list[str]:
    """Líneas markdown de la sección. `discards`: chunk_id → motivos de descarte de sus
    candidatas (de `qa_candidates.jsonl`, si existe) para explicar fichas sin preguntas."""
    by_id = {c["chunk_id"]: c for c in chunks}
    asked = Counter(q["chunk_id"] for q in qa)
    projects = sorted({c["project"] for c in chunks})
    n = section
    out = [
        f"## {n}. Calidad del dataset Q&A",
        "",
        f"Sobre `outputs/qa.jsonl` ({len(qa)} preguntas, todos los splits y tipos) y "
        f"`outputs/corpus.jsonl` ({len(chunks)} fichas). Sin LLM.",
        "",
    ]

    # Cobertura
    out += [f"### {n}.1 Cobertura: fichas con al menos una pregunta", ""]
    rows = []
    for p in projects:
        row: list[Any] = [p]
        for s in SPLITS:
            cs = [c for c in chunks if c["project"] == p and c["split"] == s]
            row.append(f"{sum(asked[c['chunk_id']] > 0 for c in cs)}/{len(cs)}" if cs else "—")
        cs = [c for c in chunks if c["project"] == p]
        row.append(_pct(sum(asked[c["chunk_id"]] > 0 for c in cs), len(cs)))
        rows.append(row)
    tot = [
        f"{sum(asked[c['chunk_id']] > 0 for c in chunks if c['split'] == s)}/"
        f"{sum(c['split'] == s for c in chunks)}"
        for s in SPLITS
    ]
    covered = sum(asked[c["chunk_id"]] > 0 for c in chunks)
    rows.append(["**Total**", *tot, _pct(covered, len(chunks))])
    out += _table(["Proyecto", *SPLITS, "% cubiertas"], rows)

    missing = sorted(
        (c for c in chunks if not asked[c["chunk_id"]]),
        key=lambda c: (c["project"], c["split"], c["chunk_id"]),
    )

    def reason(c: Chunk) -> str:
        if c["n_tokens"] < min_tokens:
            return f"corta ({c['n_tokens']} < {min_tokens} tokens): no se generan preguntas"
        d = (discards or {}).get(c["chunk_id"])
        if d:
            return "descartadas: " + ", ".join(f"{k} {v}" for k, v in sorted(d.items()))
        return "sin candidatas registradas"

    short = sum(c["n_tokens"] < min_tokens for c in missing)
    out += [
        f"**Fichas sin preguntas: {len(missing)}** ({short} por ser más cortas que "
        f"`qa.min_tokens`; el resto perdió todas sus candidatas en los filtros o el juez).",
        "",
        "<details><summary>Lista</summary>",
        "",
    ]
    out += _table(
        ["Ficha", "Proyecto", "Split", "Tokens", "Ubicación", "Motivo"],
        [
            [
                f"`{c['chunk_id']}`",
                c["project"],
                c["split"],
                c["n_tokens"],
                _short(c["contextualized_text"].split("\n", 1)[0].split(" › ", 1)[-1], 70),
                reason(c),
            ]
            for c in missing
        ],
    )
    out += ["</details>", ""]

    # Balance
    out += [f"### {n}.2 Balance", ""]
    by = Counter((q["split"], q["qa_type"]) for q in qa)
    out += ["**Por fuente y split:**", ""]
    out += _table(
        ["Split", *QA_TYPES, "Total"],
        [[s, *(by[(s, t)] for t in QA_TYPES), sum(by[(s, t)] for t in QA_TYPES)] for s in SPLITS],
    )
    by = Counter((q["project"], q["split"]) for q in qa)
    covered_by = Counter(c["project"] for c in chunks if asked[c["chunk_id"]])
    out += ["**Por proyecto y split** (y preguntas por ficha cubierta):", ""]
    out += _table(
        ["Proyecto", *SPLITS, "Total", "Preguntas / ficha"],
        [
            [
                p,
                *(by[(p, s)] for s in SPLITS),
                sum(by[(p, s)] for s in SPLITS),
                f"{sum(by[(p, s)] for s in SPLITS) / max(1, covered_by[p]):.1f}",
            ]
            for p in projects
        ],
    )
    by = Counter((q["language"], q["split"]) for q in qa)
    langs = sorted({q["language"] for q in qa})
    out += ["**Por idioma y split:**", ""]
    out += _table(["Idioma", *SPLITS], [[lg, *(by[(lg, s)] for s in SPLITS)] for lg in langs])

    # Diversidad
    out += [f"### {n}.3 Diversidad", ""]
    kinds = Counter((question_kind(q["question"]), q["split"]) for q in qa)
    kind_names = sorted({k for k, _ in kinds}, key=lambda k: -sum(kinds[(k, s)] for s in SPLITS))
    out += ["**Tipo de pregunta** (primera palabra; es/en unificados):", ""]
    out += _table(
        ["Tipo", *SPLITS, "Total", "%"],
        [
            [
                k,
                *(kinds[(k, s)] for s in SPLITS),
                sum(kinds[(k, s)] for s in SPLITS),
                _pct(sum(kinds[(k, s)] for s in SPLITS), len(qa)),
            ]
            for k in kind_names
        ],
    )
    loose = round(near_dup_threshold - 0.3, 2)
    in_split = {s: [q for q in qa if q["split"] == s] for s in SPLITS}
    out += [
        "**Casi-duplicadas dentro de cada split** (preguntas con otra del mismo split a "
        "Jaccard de palabras de contenido ≥ umbral). Sin `openapi` es lo que controla el "
        f"filtro de qa (≥ {near_dup_threshold}); con `openapi`, las plantillas deterministas "
        "comparten palabras a propósito (cambian el endpoint, no la redacción).",
        "",
    ]
    free = {s: [q for q in in_split[s] if q["qa_type"] != OPENAPI] for s in SPLITS}
    out += _table(
        [
            "Split",
            "Preguntas sin openapi",
            f"≥ {near_dup_threshold}",
            f"≥ {loose}",
            f"≥ {loose} con openapi",
        ],
        [
            [
                s,
                len(free[s]),
                f"{near_dup_share(free[s], near_dup_threshold):.1%}",
                f"{near_dup_share(free[s], loose):.1%}",
                f"{near_dup_share(in_split[s], loose):.1%}",
            ]
            for s in SPLITS
        ],
    )

    # Longitudes
    out += [f"### {n}.4 Longitudes (tokens, `o200k_base`)", ""]
    qlen = {q["qa_id"]: count_tokens(q["question"]) for q in qa}
    alen = {q["qa_id"]: count_tokens(q["answer"]) for q in qa}
    rows = []
    for t in QA_TYPES:
        sel = [q["qa_id"] for q in qa if q["qa_type"] == t]
        rows.append([f"pregunta · {t}", *_dist([qlen[i] for i in sel])])
        rows.append([f"respuesta · {t}", *_dist([alen[i] for i in sel])])
    out += _table(["", "n", "mín", "p25", "mediana", "p95", "máx"], rows)
    llm = [q for q in qa if q["qa_type"] == "llm"]
    extremes = (
        [
            (
                "Pregunta más corta",
                min(qa, key=lambda q: (qlen[q["qa_id"]], q["qa_id"])),
                "question",
                qlen,
            ),
            (
                "Pregunta más larga",
                max(qa, key=lambda q: (qlen[q["qa_id"]], q["qa_id"])),
                "question",
                qlen,
            ),
            (
                "Respuesta `llm` más corta",
                min(llm, key=lambda q: (alen[q["qa_id"]], q["qa_id"])),
                "answer",
                alen,
            ),
            (
                "Respuesta `llm` más larga",
                max(llm, key=lambda q: (alen[q["qa_id"]], q["qa_id"])),
                "answer",
                alen,
            ),
        ]
        if llm
        else []
    )
    out += ["**Casos extremos:**", ""]
    out += [
        f"- {label} ({lens[q['qa_id']]} tokens, `{q['qa_id']}`): {_short(q[field], 160)}"
        for label, q, field, lens in extremes
    ]
    out.append("")

    # Fundamentación
    answerable = [q for q in qa if q["qa_type"] != "unanswerable"]
    g = {q["qa_id"]: grounded(q, by_id[q["chunk_id"]]) for q in answerable}
    exact = sum(v[0] for v in g.values())
    norm = sum(v[1] for v in g.values())
    out += [f"### {n}.5 Fundamentación", ""]
    out += _table(
        ["Tipo", "Preguntas", "Evidencia literal exacta", "Literal con espacios normalizados"],
        [
            [
                t,
                sum(q["qa_type"] == t for q in answerable),
                _pct(
                    sum(g[q["qa_id"]][0] for q in answerable if q["qa_type"] == t),
                    sum(q["qa_type"] == t for q in answerable),
                ),
                _pct(
                    sum(g[q["qa_id"]][1] for q in answerable if q["qa_type"] == t),
                    sum(q["qa_type"] == t for q in answerable),
                ),
            ]
            for t in ("llm", "openapi")
        ]
        + [
            [
                "**Total**",
                len(answerable),
                _pct(exact, len(answerable)),
                _pct(norm, len(answerable)),
            ]
        ],
    )
    out += [
        f"{'✅' if norm == len(answerable) else '❌'} {norm}/{len(answerable)} respuestas tienen "
        "toda su evidencia literal en la ficha (con espacios normalizados): es invariante "
        "del pipeline y lo verifica `tests/test_dataset_integrity.py`. Las `unanswerable` "
        "no tienen evidencia por definición.",
        "",
    ]

    # Fuga y abstención
    out += [f"### {n}.6 Fuga y abstención", ""]
    out += _table(
        [
            "Split",
            "Preguntas",
            "`leak_risk`",
            "% `leak_risk`",
            "`unanswerable`",
            "% `unanswerable`",
        ],
        [
            [
                s,
                (m := sum(q["split"] == s for q in qa)),
                (lk := sum(q["split"] == s and q["leak_risk"] for q in qa)),
                _pct(lk, m),
                (un := sum(q["split"] == s and q["qa_type"] == "unanswerable" for q in qa)),
                _pct(un, m),
            ]
            for s in SPLITS
        ],
    )

    # Conclusión
    n_eval = sum(q["split"] != "train" for q in qa)
    un_proj = sum(q["split"] == "eval_project" and q["qa_type"] == "unanswerable" for q in qa)
    open_proj = sum(q["split"] == "eval_project" and q["qa_type"] == "openapi" for q in qa)
    top_kind, top_n = max(
        ((k, sum(kinds[(k, s)] for s in SPLITS)) for k in kind_names), key=lambda x: x[1]
    )
    es = sum(q["language"] == "es" for q in qa)
    reasons = Counter(r for c in missing for r in (discards or {}).get(c["chunk_id"], {}))
    top_reason, top_reason_n = reasons.most_common(1)[0] if reasons else ("", 0)
    out += [
        f"### {n}.7 Conclusión: qué le falta al dataset",
        "",
        f"- **Volumen:** {len(qa)} preguntas ({n_eval} de eval) alcanzan para medir retrieval "
        "y para una prueba de entrenabilidad, no para un SFT con conclusiones finas ni "
        "para comparar por proyecto o idioma.",
        f"- **Cobertura:** {len(missing)} de {len(chunks)} fichas no tienen preguntas "
        f"({short} por cortas"
        + (
            f"; el motivo de descarte más común es `{top_reason}`, en {top_reason_n} fichas"
            if top_reason
            else ""
        )
        + "). Con más tiempo: regenerar esas fichas con más preguntas por ficha o otro "
        "prompt, y revisar a mano una muestra de los rechazos del juez (puede ser demasiado "
        "estricto con fichas cortas o de listas).",
        f"- **Abstención:** solo {un_proj} `unanswerable` en eval_project; la tasa de "
        "abstención por split no es estimable. Subir `unanswerable_ratio` en eval y generar "
        'preguntas sin respuesta "cercanas" (sobre hechos ausentes de la propia ficha).',
        f"- **Verificabilidad:** eval_project tiene {open_proj} preguntas `openapi`; casi "
        "toda la señal con verificador exacto está en eval_section. Extraer más respuestas "
        "cortas verificables de las `llm` (valores, comandos, nombres).",
        f'- **Diversidad:** domina el tipo "{top_kind}" ({top_n / len(qa):.0%}). Pedir '
        "explícitamente preguntas de procedimiento (cómo), condición (cuándo/por qué) y "
        "multi-hop entre fichas del mismo archivo.",
        f"- **Idioma:** {es} preguntas en español de {len(qa)}: el idioma sigue al de la "
        "documentación. Si el uso real es en español, generar también preguntas en español "
        "sobre fichas en inglés.",
        "- **Calidad del juez:** sin etiquetas humanas todavía; completar `make label-qa` "
        "antes de usar sus puntajes como filtro o métrica.",
        "",
    ]
    return out
