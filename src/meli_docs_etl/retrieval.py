"""Retrieval léxico para la etapa evaluate (cálculo puro, determinista, sin dependencias).

- `tokenize`: minúsculas y secuencias de letras/dígitos (`_` separa: `BILLING_LIMIT` →
  `billing`, `limit`).
- `BM25`: Okapi BM25 con idf no negativo (variante Lucene):
  idf(t) = ln(1 + (N - df + 0.5) / (df + 0.5)),
  score(q, d) = Σ_{t ∈ q} idf(t) · tf·(k1 + 1) / (tf + k1·(1 - b + b·|d| / avgdl)).
  Los términos repetidos de la consulta suman una vez por aparición (como rank-bm25).
  Empates: orden de `ids` (estable).
- `is_hit`: criterio de acierto independiente de la estrategia de chunking (evidencia literal
  con espacios normalizados, u operación OpenAPI).
- `first_hit_rank`, `metrics`: Recall@k y MRR.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

_TOKEN = re.compile(r"[^\W_]+")
_WS = re.compile(r"\s+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def collapse_ws(text: str) -> str:
    return _WS.sub(" ", text).strip()


class BM25:
    def __init__(
        self, ids: Sequence[str], docs: Sequence[str], k1: float = 1.5, b: float = 0.75
    ) -> None:
        if len(ids) != len(docs):
            raise ValueError("ids y docs deben tener el mismo largo")
        self.ids, self.k1, self.b = list(ids), k1, b
        self.tfs = [Counter(tokenize(d)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = sum(self.lens) / len(self.lens) if self.lens else 0.0
        df: Counter = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def scores(self, query: str) -> list[float]:
        terms = [t for t in tokenize(query) if t in self.idf]
        out = []
        for tf, dl in zip(self.tfs, self.lens, strict=True):
            norm = self.k1 * (1 - self.b + self.b * dl / self.avgdl) if self.avgdl else self.k1
            s = 0.0
            for t in terms:
                f = tf.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + norm)
            out.append(s)
        return out

    def rank(self, query: str) -> list[str]:
        """Todos los ids, de mayor a menor score (empate → orden original)."""
        sc = self.scores(query)
        order = sorted(range(len(self.ids)), key=lambda i: (-sc[i], i))
        return [self.ids[i] for i in order]


def operation_key(chunk: Mapping[str, Any]) -> tuple[str, str, str] | None:
    op = chunk.get("operation")
    if not op:
        return None
    return (chunk["project"], op["method"].upper(), op["path"])


def is_hit(question: Mapping[str, Any], chunk: Mapping[str, Any], gold_op: Any = None) -> bool:
    """`openapi`: el chunk es el de esa operación (proyecto + método + path; `gold_op`).
    Resto: el `text` del chunk contiene literalmente cada evidencia (espacios normalizados)."""
    if question["qa_type"] == "openapi":
        return gold_op is not None and operation_key(chunk) == gold_op
    evidence = [collapse_ws(e) for e in question["evidence"] if e.strip()]
    if not evidence:
        return False
    text = collapse_ws(chunk["text"])
    return all(e in text for e in evidence)


def first_hit_rank(ranking: Sequence[str], relevant: set[str]) -> int | None:
    """Posición (1-based) del primer id relevante; None si ninguno lo es."""
    for i, cid in enumerate(ranking, 1):
        if cid in relevant:
            return i
    return None


def metrics(ranks: Sequence[int | None], ks: Sequence[int]) -> dict[str, float]:
    """Recall@k (fracción con un acierto en el top k) y MRR (1/rango del primer acierto
    sobre el ranking completo; 0 si no hay ninguno)."""
    n = len(ranks)
    if not n:
        return {**{f"R@{k}": float("nan") for k in ks}, "MRR": float("nan")}
    out = {f"R@{k}": sum(r is not None and r <= k for r in ranks) / n for k in ks}
    out["MRR"] = sum(1 / r for r in ranks if r is not None) / n
    return out
