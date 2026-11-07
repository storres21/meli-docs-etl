"""Primitivas de deduplicación: shingles, Jaccard, MinHash/LSH, union-find y regla de fusión."""

from __future__ import annotations

import re
from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from datasketch import MinHash, MinHashLSH

K = TypeVar("K", bound=Hashable)
T = TypeVar("T")
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def shingles(tokens: Sequence[str], k: int) -> set[str]:
    if len(tokens) < k:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def body_lines(body: str) -> frozenset[str]:
    """Conjunto de líneas no vacías: la unidad para decidir si una sección aporta algo nuevo."""
    return frozenset(ln.strip() for ln in body.splitlines() if ln.strip())


def lsh_candidates(
    sets: dict[K, set[str]], threshold: float, num_perm: int, seed: int
) -> set[tuple[K, K]]:
    """Pares candidatos (ordenados) vía MinHash + LSH."""
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    hashes: dict[K, MinHash] = {}
    for key in sorted(sets, key=str):
        mh = MinHash(num_perm=num_perm, seed=seed)
        for sh in sorted(sets[key]):
            mh.update(sh.encode("utf-8"))
        hashes[key] = mh
        lsh.insert(key, mh)
    pairs: set[tuple[K, K]] = set()
    for key, mh in hashes.items():
        for other in lsh.query(mh):
            if other != key:
                a, b = sorted((key, other), key=str)
                pairs.add((a, b))
    return pairs


class UnionFind(Generic[K]):
    def __init__(self, items: Iterable[K]) -> None:
        self.parent: dict[K, K] = {x: x for x in items}

    def find(self, x: K) -> K:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: K, b: K) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            lo, hi = sorted((ra, rb), key=str)
            self.parent[hi] = lo

    def groups(self) -> list[list[K]]:
        out: dict[K, list[K]] = {}
        for x in self.parent:
            out.setdefault(self.find(x), []).append(x)
        return [
            sorted(g, key=str) for g in sorted(out.values(), key=lambda g: str(min(g, key=str)))
        ]


@dataclass
class MergeResult(Generic[T]):
    kept: list[T]  # kept[0] es la canónica del cluster; el resto son variantes
    absorbed_by: dict[int, list[T]] = field(default_factory=dict)  # índice en kept → absorbidos


def merge_cluster(
    members: Sequence[T], lines: Callable[[T], frozenset[str]], sort_key: Callable[[T], tuple]
) -> MergeResult[T]:
    """Regla de fusión sin pérdida.

    Se recorren los miembros de mayor a menor contenido. Un miembro se absorbe solo si
    TODAS sus líneas ya están en una sección conservada; si aporta al menos una línea
    nueva, se conserva como variante. Nunca se descarta contenido único.
    """
    ordered = sorted(members, key=lambda m: (-len(lines(m)), *sort_key(m)))
    result: MergeResult[T] = MergeResult(kept=[ordered[0]])
    for m in ordered[1:]:
        m_lines = lines(m)
        for i, k in enumerate(result.kept):
            if m_lines <= lines(k):
                result.absorbed_by.setdefault(i, []).append(m)
                break
        else:
            result.kept.append(m)
    return result
