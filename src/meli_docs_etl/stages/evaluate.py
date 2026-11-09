"""Etapa 7 — retrieval BM25 sobre las 3 estrategias de chunking → reports/evaluate.md.

Lee las preguntas de eval (`eval_section` y `eval_project`, sin `unanswerable`) de
`outputs/qa.jsonl` y, para cada estrategia, indexa el `contextualized_text` de
`<processed_dir>/corpus_<estrategia>.jsonl` (todo el corpus, todos los splits: el caso RAG
real busca en toda la documentación). El acierto no depende de la estrategia (`retrieval.is_hit`):
el chunk contiene literalmente la evidencia, o es el de la operación OpenAPI preguntada.

Métricas: Recall@k y MRR, para todas las preguntas y sin las `leak_risk`, más un baseline
aleatorio con semilla. También escribe `outputs/retrieval_metrics.json`. Sin LLM, determinista.
"""

from __future__ import annotations

import json
import logging
import random
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from meli_docs_etl.config import Config, display_path
from meli_docs_etl.qa_quality import render_quality
from meli_docs_etl.retrieval import (
    BM25,
    first_hit_rank,
    is_hit,
    metrics,
    operation_key,
    tokenize,
)
from meli_docs_etl.split_utils import EVAL_PROJECT, EVAL_SECTION
from meli_docs_etl.stages.chunk import CORPUS_FILE, STRATEGIES
from meli_docs_etl.stages.qa import CANDIDATES_FILE, QA_FILE
from meli_docs_etl.tokens import token_counter

log = logging.getLogger(__name__)

METRICS_FILE = "retrieval_metrics.json"
EVAL_SPLITS = (EVAL_SECTION, EVAL_PROJECT)
SUBSETS = ("todas", "sin_leak_risk")
METHODS = ("bm25", "aleatorio")


class EvaluateError(RuntimeError):
    pass


@dataclass
class Result:
    """Rango del primer acierto por pregunta (None = ningún chunk acierta en todo el ranking)."""

    strategy: str
    method: str
    ranks: dict[str, int | None]
    rankings: dict[str, list[str]]  # ranking completo, solo BM25 (diagnóstico de fallos)
    reachable: dict[str, bool]  # algún chunk de la estrategia cumple el criterio


def _read_jsonl(path: Path, hint: str) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"{path} no existe: corré antes `{hint}`.")
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def load_questions(cfg: Config) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Preguntas de eval sin `unanswerable` y la operación OpenAPI de cada una (gold)."""
    qa = _read_jsonl(cfg.paths.outputs_dir / QA_FILE, "meli-etl qa")
    corpus = {
        c["chunk_id"]: c
        for c in _read_jsonl(cfg.paths.outputs_dir / CORPUS_FILE, "meli-etl chunk && split")
    }
    questions = sorted(
        (q for q in qa if q["split"] in EVAL_SPLITS and q["qa_type"] != "unanswerable"),
        key=lambda q: q["qa_id"],
    )
    stale = sorted({q["chunk_id"] for q in questions} - set(corpus))
    if stale:
        raise EvaluateError(
            f"{len(stale)} preguntas apuntan a fichas que ya no están en "
            f"outputs/{CORPUS_FILE} (p. ej. {stale[0]}): `qa.jsonl` está desactualizado; "
            "corré `meli-etl qa`."
        )
    gold = {
        q["qa_id"]: operation_key(corpus[q["chunk_id"]])
        for q in questions
        if q["qa_type"] == "openapi"
    }
    return questions, gold


def evaluate_strategy(
    strategy: str,
    chunks: Sequence[Mapping[str, Any]],
    questions: Sequence[Mapping[str, Any]],
    gold: Mapping[str, Any],
    cfg: Config,
) -> list[Result]:
    ids = [c["chunk_id"] for c in chunks]
    e = cfg.evaluate
    bm25 = BM25(ids, [c["contextualized_text"] for c in chunks], e.k1, e.b)
    bm, rnd = Result(strategy, "bm25", {}, {}, {}), Result(strategy, "aleatorio", {}, {}, {})
    for q in questions:
        qid = q["qa_id"]
        relevant = {c["chunk_id"] for c in chunks if is_hit(q, c, gold.get(qid))}
        ranking = bm25.rank(q["question"])
        bm.ranks[qid] = first_hit_rank(ranking, relevant)
        bm.rankings[qid] = ranking
        shuffled = list(ids)
        random.Random(f"{cfg.seed}|{strategy}|{qid}").shuffle(shuffled)
        rnd.ranks[qid] = first_hit_rank(shuffled, relevant)
        bm.reachable[qid] = rnd.reachable[qid] = bool(relevant)
    return [bm, rnd]


def table_rows(
    results: Sequence[Result], questions: Sequence[Mapping[str, Any]], ks: Sequence[int]
) -> list[dict[str, Any]]:
    rows = []
    for subset in SUBSETS:
        qs = [q for q in questions if subset == "todas" or not q["leak_risk"]]
        for r in results:
            for split in (*EVAL_SPLITS, "total"):
                sel = [q["qa_id"] for q in qs if split == "total" or q["split"] == split]
                rows.append(
                    {
                        "subset": subset,
                        "strategy": r.strategy,
                        "method": r.method,
                        "split": split,
                        "n": len(sel),
                        **metrics([r.ranks[i] for i in sel], ks),
                    }
                )
    return rows


def run(cfg: Config) -> Path:
    questions, gold = load_questions(cfg)
    if not questions:
        raise EvaluateError("No hay preguntas de eval (sin `unanswerable`) en qa.jsonl.")
    corpora = {
        s: _read_jsonl(cfg.paths.processed_dir / f"corpus_{s}.jsonl", "meli-etl chunk")
        for s in STRATEGIES
    }
    log.info(
        "Evaluate: %d preguntas de eval × %d estrategias (%s)",
        len(questions),
        len(STRATEGIES),
        ", ".join(f"{s}={len(c)} chunks" for s, c in corpora.items()),
    )
    results = [
        r for s in STRATEGIES for r in evaluate_strategy(s, corpora[s], questions, gold, cfg)
    ]
    rows = table_rows(results, questions, cfg.evaluate.ks)
    for row in rows:
        if row["subset"] == "todas" and row["split"] == "total":
            log.info(
                "%-13s %-9s R@1=%.3f R@5=%.3f R@10=%.3f MRR=%.3f",
                row["strategy"],
                row["method"],
                *(row[f"R@{k}"] for k in cfg.evaluate.ks),
                row["MRR"],
            )

    out = cfg.paths.outputs_dir / METRICS_FILE
    out.write_text(
        json.dumps(
            {
                "bm25": {"k1": cfg.evaluate.k1, "b": cfg.evaluate.b},
                "seed": cfg.seed,
                "n_questions": len(questions),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    report = cfg.paths.reports_dir / "evaluate.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    text = render_report(rows, results, questions, gold, corpora, cfg)
    report.write_text(text + "\n" + "\n".join(quality_section(cfg)), encoding="utf-8")
    log.info("Escrito %s y reporte %s", display_path(out), display_path(report))
    return report


def quality_section(cfg: Config) -> list[str]:
    """§8: calidad del dataset Q&A completo (todos los splits y tipos)."""
    qa = _read_jsonl(cfg.paths.outputs_dir / QA_FILE, "meli-etl qa")
    chunks = _read_jsonl(cfg.paths.outputs_dir / CORPUS_FILE, "meli-etl chunk && split")
    discards: dict[str, Counter] = defaultdict(Counter)
    cands = cfg.paths.processed_dir / CANDIDATES_FILE
    if cands.exists():  # intermedio de qa: explica por qué una ficha quedó sin preguntas
        for c in _read_jsonl(cands, "meli-etl qa"):
            if c["discard"]:
                discards[c["chunk_id"]][c["discard"]] += 1
    return render_quality(
        qa,
        chunks,
        token_counter(cfg.chunk.tokenizer, cfg.paths.tiktoken_cache_dir),
        cfg.qa.near_dup_jaccard,
        cfg.qa.min_tokens,
        discards,
    )


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


def _f(x: float) -> str:
    return "—" if x != x else f"{x:.3f}"


def _short(text: str, n: int = 110) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _get(rows: Sequence[Mapping[str, Any]], **kw: Any) -> Mapping[str, Any]:
    (row,) = [r for r in rows if all(r[k] == v for k, v in kw.items())]
    return row


def diagnose(
    q: Mapping[str, Any],
    rank: int | None,
    top: Sequence[str],
    by_id: Mapping[str, Mapping[str, Any]],
    relevant: Sequence[Mapping[str, Any]],
) -> str:
    """Una línea: por qué BM25 no puso la ficha correcta arriba (heurística léxica; la
    primera causa que aplica, en este orden)."""
    where = f"queda en el puesto {rank}" if rank else "no aparece en el ranking"
    if not relevant:
        return (
            "ningún chunk de esta estrategia contiene la evidencia completa (quedó partida "
            "entre chunks): fallo del chunking, no del ranking."
        )
    gold, first = relevant[0], by_id[top[0]]
    qt = set(tokenize(q["question"]))
    overlap = len(qt & set(tokenize(gold["contextualized_text"]))) / len(qt) if qt else 0.0
    op_g, op_f = operation_key(gold), operation_key(first)
    if op_g and op_f and op_g[0] == op_f[0] and op_g[2] == op_f[2]:
        return (
            f"la top-1 es otra operación sobre el mismo path ({op_f[1]} {op_f[2]}): BM25 no "
            f"distingue el método; la correcta {where}."
        )
    if not set(tokenize(gold["project"])) <= qt:
        rival = (
            f"páginas parecidas de otros proyectos (top-1: {first['project']})"
            if first["project"] != gold["project"]
            else "otras páginas del proyecto sin un término que la distinga"
        )
        return (
            f"la pregunta no nombra el proyecto ({gold['project']}) y compite con {rival}; "
            f"la correcta {where}."
        )
    if q["language"] != gold.get("language", q["language"]) and gold["language"] in ("es", "en"):
        return (
            f"pregunta en `{q['language']}` sobre una ficha en `{gold['language']}`: comparten "
            f"pocas palabras ({overlap:.0%} de los términos); la correcta {where}."
        )
    if first["source_path"] == gold["source_path"]:
        return (
            "la top-1 es otra sección del mismo archivo, con vocabulario casi igual; la "
            f"correcta {where}."
        )
    if overlap < 0.5:
        return (
            f"poca superposición léxica: solo {overlap:.0%} de los términos de la pregunta "
            f"están en la ficha correcta (parafraseo); la correcta {where}."
        )
    return (
        f"otra página ({first['source_path'].split('/', 2)[-1]}) repite más veces los "
        f"términos de la pregunta; la correcta {where}."
    )


def _tie_note(best: str, ranked: Sequence[str], score: Any, n: int) -> str:
    """Si la segunda está a menos de una pregunta de MRR, es un empate técnico."""
    second = ranked[1] if ranked[0] == best else ranked[0]
    gap = score(best)["MRR"] - score(second)["MRR"]
    d_r5 = score(best)["R@5"] - score(second)["R@5"]
    if gap < 1 / n:
        return (
            f"- **Empate técnico** con `{second}` (ΔMRR {gap:+.3f}, menos de lo que mueve una "
            f"pregunta, {1 / n:.3f}): la elección se apoya en {d_r5:+.3f} de R@5 y en que "
            "es la estrategia del entregable (`outputs/corpus.jsonl`); no hay "
            "evidencia para preferir una sobre otra en calidad de retrieval."
        )
    return f"- **Margen:** ΔMRR {gap:+.3f} frente a `{second}`."


def _pick_failures(
    questions: Sequence[Mapping[str, Any]], result: Result, n: int
) -> list[Mapping[str, Any]]:
    """Los n peores fallos @1: primero los que no tienen acierto, luego por rango
    descendente (empate → qa_id)."""
    fails = [q for q in questions if (result.ranks[q["qa_id"]] or 10**9) > 1]
    return sorted(fails, key=lambda q: (-(result.ranks[q["qa_id"]] or 10**9), q["qa_id"]))[:n]


def render_report(
    rows: list[dict[str, Any]],
    results: list[Result],
    questions: list[dict[str, Any]],
    gold: Mapping[str, Any],
    corpora: Mapping[str, list[dict[str, Any]]],
    cfg: Config,
) -> str:
    e, ks = cfg.evaluate, cfg.evaluate.ks
    rk = [f"R@{k}" for k in ks]
    n_leak = sum(q["leak_risk"] for q in questions)
    by_split = {s: sum(q["split"] == s for q in questions) for s in EVAL_SPLITS}
    by_type = {t: sum(q["qa_type"] == t for q in questions) for t in ("llm", "openapi")}
    out = [
        "# Evaluación de retrieval (BM25)",
        "",
        f"Generado por `meli-etl evaluate` (sin LLM, determinista). BM25 Okapi implementado "
        f"a mano (k1 = {e.k1}, b = {e.b}, idf no negativo); tokenización: minúsculas y "
        "secuencias de letras/dígitos. Se indexa el `contextualized_text` de **todo** el "
        "corpus de cada estrategia (los tres splits), como en un RAG real.",
        "",
        f"- **Preguntas:** {len(questions)} de `outputs/qa.jsonl` con split eval y tipo "
        f"`llm` u `openapi` ({by_split[EVAL_SECTION]} eval_section, "
        f"{by_split[EVAL_PROJECT]} eval_project; {by_type['llm']} llm, "
        f"{by_type['openapi']} openapi). Las `unanswerable` no tienen ficha correcta. "
        f"{n_leak} tienen `leak_risk`.",
        "- **Acierto** (igual para cualquier estrategia): el chunk recuperado contiene "
        "literalmente la `evidence` de la pregunta (espacios normalizados); en `openapi`, "
        "el chunk es el de esa operación (proyecto + método + path). Más de un chunk puede "
        "acertar (p. ej. contenido repetido entre versiones).",
        f"- **Métricas:** Recall@k = fracción de preguntas con un acierto en el top k; MRR = "
        "media de 1/rango del primer acierto sobre el ranking completo (0 si ninguno). "
        f"Baseline aleatorio: permutación con semilla `{cfg.seed}|estrategia|qa_id`.",
        "",
        "## 1. Estrategias",
        "",
    ]
    bm = {r.strategy: r for r in results if r.method == "bm25"}
    tokens = {s: sum(c["n_tokens"] for c in corpora[s]) / len(corpora[s]) for s in STRATEGIES}
    unreach = {s: sum(not bm[s].reachable[q["qa_id"]] for q in questions) for s in STRATEGIES}
    out += _table(
        ["Estrategia", "Chunks", "Tokens medios", "Preguntas sin ningún chunk que acierte"],
        [[s, len(corpora[s]), round(tokens[s]), unreach[s]] for s in STRATEGIES],
    )

    titles = {"todas": "todas las preguntas", "sin_leak_risk": "sin las preguntas `leak_risk`"}
    for i, subset in enumerate(SUBSETS, 2):
        out += [f"## {i}. Resultados: {titles[subset]}", ""]
        out += _table(
            ["Estrategia", "Método", "Split", "n", *rk, "MRR"],
            [
                [
                    f"**{r['strategy']}**" if r["method"] == "bm25" else r["strategy"],
                    r["method"],
                    r["split"],
                    r["n"],
                    *(_f(r[m]) for m in rk),
                    _f(r["MRR"]),
                ]
                for r in rows
                if r["subset"] == subset
            ],
        )

    # 4. Conclusión
    def score(s: str, subset: str = "sin_leak_risk", split: str = "total") -> Mapping[str, Any]:
        return _get(rows, subset=subset, strategy=s, method="bm25", split=split)

    best = max(STRATEGIES, key=lambda s: (score(s)["MRR"], score(s)[rk[1]], -STRATEGIES.index(s)))
    ranked = sorted(STRATEGIES, key=lambda s: -score(s)["MRR"])
    rnd_row = _get(rows, subset="sin_leak_risk", strategy=best, method="aleatorio", split="total")
    out += ["## 4. Conclusión: qué estrategia conviene", ""]
    out += [
        f"**{best}** (MRR {_f(score(best)['MRR'])}, {rk[1]} {_f(score(best)[rk[1]])}, "
        f"{rk[2]} {_f(score(best)[rk[2]])} sin `leak_risk`; aleatorio: MRR "
        f"{_f(rnd_row['MRR'])}). Orden por MRR: "
        + " > ".join(f"{s} ({_f(score(s)['MRR'])})" for s in ranked)
        + ".",
        "",
        f"- **Tamaño de chunk:** {', '.join(f'{s} ≈ {tokens[s]:.0f} tokens' for s in STRATEGIES)}. "
        "Con BM25, un chunk más grande junta más términos de la pregunta (título, proyecto y "
        "cuerpo en el mismo documento) pero la normalización por largo (b) lo penaliza; un "
        "chunk chico es más preciso pero puede quedarse sin el contexto que nombra la "
        "pregunta.",
        "- **Chunks partidos:** preguntas sin ningún chunk que contenga su evidencia: "
        + ", ".join(f"{s} {unreach[s]}" for s in STRATEGIES)
        + ". Una evidencia cortada entre dos chunks es un fallo seguro, independiente del "
        "ranking.",
        _tie_note(best, ranked, score, len(questions)),
        "- **Sesgo a tener en cuenta:** las preguntas `llm` se generaron leyendo fichas "
        "`merged`, así que su vocabulario sigue esos límites de chunk (el criterio de acierto "
        "por evidencia sí es neutral entre estrategias).",
        f"- **Recomendación:** usar `{best}` como retriever de los brazos con RAG del plan de "
        "experimentos (`reports/experiment_plan.md`). Con "
        f"{len(questions)} preguntas, una sola pregunta mueve el Recall "
        f"{1 / len(questions):.1%}.",
        "",
    ]

    # 5. eval_section vs eval_project
    sec, proj = score(best, split=EVAL_SECTION), score(best, split=EVAL_PROJECT)
    n_open = {
        sp: sum(
            q["split"] == sp and q["qa_type"] == "openapi" and not q["leak_risk"] for q in questions
        )
        for sp in EVAL_SPLITS
    }
    out += ["## 5. eval_section vs eval_project", ""]
    out += _table(
        ["Split", "n", *rk, "MRR"],
        [
            [s, r["n"], *(_f(r[m]) for m in rk), _f(r["MRR"])]
            for s, r in ((EVAL_SECTION, sec), (EVAL_PROJECT, proj))
        ],
    )
    diff = proj["MRR"] - sec["MRR"]
    out += [
        f"Con `{best}` y sin `leak_risk`, eval_project tiene MRR {diff:+.3f} respecto de "
        "eval_section. Para un retriever léxico sin entrenamiento las dos son el mismo "
        "problema (buscar en todo el corpus, que incluye el proyecto retenido): BM25 no "
        'aprende de train, así que "proyecto nunca visto" no lo afecta. La diferencia '
        "viene de la composición: eval_project es un solo proyecto "
        f"({n_open[EVAL_PROJECT]} preguntas openapi de {proj['n']}); eval_section mezcla "
        f"secciones de los otros proyectos ({n_open[EVAL_SECTION]} openapi de {sec['n']}). "
        "La distinción importa para los modelos entrenados del plan de experimentos. Con "
        f"{proj['n']} preguntas en eval_project, el intervalo de confianza es amplio.",
        "",
    ]

    # 6. leak_risk
    out += ["## 6. Efecto de quitar `leak_risk`", ""]
    lr_rows = []
    for s in STRATEGIES:
        a = score(s, subset="todas", split=EVAL_SECTION)
        b = score(s, subset="sin_leak_risk", split=EVAL_SECTION)
        lr_rows.append(
            [s, a["n"], b["n"], _f(a["MRR"]), _f(b["MRR"]), f"{b['MRR'] - a['MRR']:+.3f}"]
        )
    out += _table(
        ["Estrategia", "n (todas)", "n (sin leak)", "MRR todas", "MRR sin leak", "Δ"], lr_rows
    )
    leak_ids = [q["qa_id"] for q in questions if q["leak_risk"]]
    bm_best = bm[best]
    leak_ranks = [bm_best.ranks[i] for i in leak_ids]
    out += [
        f"Las {len(leak_ids)} preguntas `leak_risk` son todas de eval_section (eval_project no "
        "tiene). Con `"
        f"{best}`, sus rangos del primer acierto: {', '.join(str(r) for r in leak_ranks) or '—'}. "
        "`leak_risk` señala riesgo de **memorización** (el endpoint aparece en una ficha de "
        "train): afecta a un modelo entrenado, no a BM25, que no aprende nada de train. Acá "
        "el efecto es solo de composición de la muestra; en el plan de experimentos se "
        "reportan aparte.",
        "",
    ]

    # 7. Fallos
    by_id = {c["chunk_id"]: c for c in corpora[best]}
    picks = _pick_failures(questions, bm_best, e.n_failure_examples)
    out += [
        f"## 7. Ejemplos de fallos (`{best}`, BM25)",
        "",
        f"Los {e.n_failure_examples} peores fallos en el top 1 (rango del primer acierto más "
        f"alto). Fallos en el top {ks[-1]}: "
        f"{sum((bm_best.ranks[q['qa_id']] or 10**9) > ks[-1] for q in questions)} de "
        f"{len(questions)}. El diagnóstico es una heurística léxica (primera causa que aplica).",
        "",
    ]
    for i, q in enumerate(picks, 1):
        qid = q["qa_id"]
        rank, top = bm_best.ranks[qid], bm_best.rankings[qid]
        # Ficha correcta mejor rankeada (o ninguna, si la evidencia quedó partida).
        relevant = [by_id[c] for c in top if is_hit(q, by_id[c], gold.get(qid))]
        first = by_id[top[0]]
        out += [
            f"**{i}. `{qid}`** · {q['split']} · {q['qa_type']} · rango del primer acierto: "
            f"{rank if rank else '—'}",
            "",
            f"- Pregunta: {q['question']}",
            "- Esperada: "
            + (_short(relevant[0]["contextualized_text"].splitlines()[0]) if relevant else "—"),
            f"- Top-1: {_short(first['contextualized_text'].splitlines()[0])}",
            f"- Diagnóstico: {diagnose(q, rank, top, by_id, relevant)}",
            "",
        ]
    return "\n".join(out)
