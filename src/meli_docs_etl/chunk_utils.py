"""Primitivas de chunking (puras): bloques Markdown atómicos, empaquetado y conservación.

Un texto se descompone en bloques contiguos que lo cubren por completo (las líneas en
blanco quedan pegadas al bloque anterior), así que cualquier secuencia de bloques
consecutivos es un slice exacto del texto original. Los cortes solo caen entre bloques;
código, tablas, listas y bloques HTML `<details>` son atómicos.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from meli_docs_etl.md_utils import ATX_RE, FENCE_RE

_TABLE_RE = re.compile(r"^\s*\|")
_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_INDENTED_RE = re.compile(r"^(?: {2,}|\t)\S")
_DETAILS_OPEN_RE = re.compile(r"<details\b", re.IGNORECASE)
_DETAILS_CLOSE_RE = re.compile(r"</details>", re.IGNORECASE)

ATOMIC_KINDS = frozenset({"code", "table", "list", "html"})


@dataclass(frozen=True)
class Block:
    start: int  # offset en el texto (inicio de línea)
    end: int  # offset exclusivo; el siguiente bloque empieza acá
    kind: str  # header | paragraph | code | table | list | html


def _line_kinds(lines: list[str]) -> tuple[list[str], list[bool]]:
    """Clasifica cada línea (blank | fence | header | table | list | text) y marca qué
    líneas cierran un bloque de código (misma regla que md_utils.iter_lines)."""
    kinds, closes = [], []
    fence: str | None = None
    for line in lines:
        m = FENCE_RE.match(line)
        if fence is None and m:
            fence = m.group(1)[0] * len(m.group(1))
            kinds.append("fence")
            closes.append(False)
            continue
        if fence is not None:
            closing = m is not None and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence)
            kinds.append("fence")
            closes.append(closing)
            if closing:
                fence = None
            continue
        closes.append(False)
        if not line.strip():
            kinds.append("blank")
        elif ATX_RE.match(line):
            kinds.append("header")
        elif _TABLE_RE.match(line):
            kinds.append("table")
        elif _LIST_RE.match(line):
            kinds.append("list")
        else:
            kinds.append("text")
    return kinds, closes


def parse_blocks(text: str) -> list[Block]:
    """Bloques contiguos que cubren `text` entero; un header se une al bloque que le sigue."""
    lines = text.split("\n")
    offsets, pos = [], 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1
    kinds, closes = _line_kinds(lines)
    n = len(lines)

    spans: list[tuple[int, int, str]] = []  # (línea inicio, línea fin exclusiva, tipo)
    i = 0
    while i < n:
        k = kinds[i]
        j = i + 1
        if k == "blank":
            # Líneas en blanco iniciales: bloque propio, se fusiona después.
            while j < n and kinds[j] == "blank":
                j += 1
            spans.append((i, j, "blank"))
            i = j
            continue
        if k == "fence":
            j = i
            while j < n and kinds[j] == "fence":
                j += 1
                if closes[j - 1]:
                    break
            kind = "code"
        elif _DETAILS_OPEN_RE.search(lines[i]) and k != "fence":
            depth = 0
            j = i
            while j < n:
                if kinds[j] != "fence":
                    depth += len(_DETAILS_OPEN_RE.findall(lines[j]))
                    depth -= len(_DETAILS_CLOSE_RE.findall(lines[j]))
                j += 1
                if depth <= 0:
                    break
            kind = "html"
        elif k == "table":
            while j < n and kinds[j] == "table":
                j += 1
            kind = "table"
        elif k == "list":
            while j < n:
                if kinds[j] == "blank":
                    nxt = next((t for t in range(j, n) if kinds[t] != "blank"), None)
                    if nxt is None or not (kinds[nxt] == "list" or _INDENTED_RE.match(lines[nxt])):
                        break
                    j = nxt
                elif kinds[j] in ("header", "table") and not _INDENTED_RE.match(lines[j]):
                    break
                elif (
                    kinds[j] == "fence"
                    and (kinds[j - 1] != "fence" or closes[j - 1])
                    and not lines[j][:1].isspace()
                ):
                    break  # un fence sin indentar interrumpe la lista (CommonMark)
                else:
                    j += 1  # ítems, continuación indentada o perezosa, fences anidados
            kind = "list"
        elif k == "header":
            kind = "header"
        else:
            while j < n and kinds[j] == "text" and not _DETAILS_OPEN_RE.search(lines[j]):
                j += 1
            kind = "paragraph"
        spans.append((i, j, kind))
        i = j

    # Blancos → al bloque anterior (o al siguiente si van primero); header → al siguiente.
    merged: list[list] = []
    for s, e, kind in spans:
        if kind == "blank" and merged:
            merged[-1][1] = e
        elif merged and merged[-1][2] in ("header", "blank"):
            merged[-1] = [merged[-1][0], e, kind]
        else:
            merged.append([s, e, kind])

    blocks: list[Block] = []
    for s, e, kind in merged:
        start = offsets[s]
        end = offsets[e] if e < n else len(text)
        b = Block(start, end, kind)
        # Un párrafo que presenta al bloque atómico siguiente viaja con él: termina en ":",
        # va pegado sin línea en blanco, o es una sola línea (título como "PUT /orders").
        if blocks and blocks[-1].kind == "paragraph" and kind in ATOMIC_KINDS:
            prev = text[blocks[-1].start : blocks[-1].end]
            body = prev.strip()
            if not prev.endswith("\n\n") or body.endswith(":") or "\n" not in body:
                b = Block(blocks.pop().start, end, kind)
        blocks.append(b)
    return blocks


def block_kinds(text: str) -> set[str]:
    return {b.kind for b in parse_blocks(text)}


def pack_blocks(
    sizes: Sequence[int], target: int, min_size: int, max_size: int
) -> list[tuple[int, int]]:
    """Agrupa bloques consecutivos en rangos [i, j) de ~target tokens.

    1. Greedy: se suman bloques mientras no pase target; un bloque más grande que target
       va solo (si supera max queda "oversize": nunca se corta por dentro).
    2. Sin huérfanos: un grupo bajo min se une al vecino con el que sume menos, siempre
       que no pase max o que el vecino ya sea oversize (así "El diagrama es:" queda junto
       a su diagrama y nunca se crea un oversize nuevo).
    """
    groups: list[list[int]] = []
    total = 0
    for i, size in enumerate(sizes):
        if groups and total + size <= target:
            groups[-1][1] = i + 1
            total += size
        else:
            groups.append([i, i + 1])
            total = size

    def size_of(g: list[int]) -> int:
        return sum(sizes[g[0] : g[1]])

    stuck: set[int] = set()  # inicio de grupos chicos que no pueden unirse a nadie
    while len(groups) > 1:
        small = [i for i, g in enumerate(groups) if size_of(g) < min_size and g[0] not in stuck]
        if not small:
            break
        i = small[0]
        options = []
        for j in (i - 1, i + 1):
            if 0 <= j < len(groups):
                sj = size_of(groups[j])
                if size_of(groups[i]) + sj <= max_size or sj > max_size:
                    options.append((sj, j))
        if not options:
            stuck.add(groups[i][0])
            continue
        _, j = min(options)
        a, b = sorted((i, j))
        groups[a] = [groups[a][0], groups[b][1]]
        del groups[b]
    return [(a, b) for a, b in groups]


def split_text(
    text: str, count: Callable[[str], int], target: int, min_size: int, max_size: int
) -> list[tuple[int, int]]:
    """Slices (inicio, fin) que cubren `text` exactamente, cortando solo entre bloques."""
    blocks = parse_blocks(text)
    sizes = [count(text[b.start : b.end]) for b in blocks]
    return [
        (blocks[a].start, blocks[b - 1].end)
        for a, b in pack_blocks(sizes, target, min_size, max_size)
    ]


@dataclass(frozen=True)
class MergeUnit:
    key: str
    parent: tuple[str, ...]
    tokens: int
    mergeable: bool  # False: variantes y secciones partidas
    adjacent: bool  # contigua a la unidad anterior en el archivo original


def merge_siblings(units: Sequence[MergeUnit], min_size: int, target: int) -> list[list[str]]:
    """Agrupa unidades hermanas consecutivas cuando alguna es corta (< min), hasta target."""
    groups: list[list[str]] = []
    total = 0
    prev: MergeUnit | None = None
    for u in units:
        if (
            prev is not None
            and u.adjacent
            and u.mergeable
            and prev.mergeable
            and u.parent == prev.parent
            and (total < min_size or u.tokens < min_size)
            and total + u.tokens <= target
        ):
            groups[-1].append(u.key)
            total += u.tokens
        else:
            groups.append([u.key])
            total = u.tokens
        prev = u
    return groups


@dataclass
class Conservation:
    n_sections: int = 0
    n_pieces: int = 0
    gaps: list[str] = field(default_factory=list)  # secciones con slices que no la cubren
    unassigned: list[str] = field(default_factory=list)  # pedazos sin chunk
    duplicated: list[str] = field(default_factory=list)  # pedazos en > 1 chunk
    not_verbatim: list[str] = field(default_factory=list)  # pedazo ausente del texto del chunk
    lines_missing: int = 0
    lines_extra: int = 0

    @property
    def ok(self) -> bool:
        return not (
            self.gaps
            or self.unassigned
            or self.duplicated
            or self.not_verbatim
            or self.lines_missing
            or self.lines_extra
        )


def _lines(text: str) -> Counter:
    return Counter(ln.strip() for ln in text.splitlines() if ln.strip())


def check_conservation(
    sections: Mapping[str, str],
    pieces: Mapping[str, Sequence[tuple[int, int]]],
    chunks: Sequence[tuple[str, Sequence[tuple[str, int]]]],
) -> Conservation:
    """Todo el texto de las secciones aparece en exactamente un chunk, sin pérdidas.

    sections: section_id → texto. pieces: section_id → slices. chunks: (texto del chunk,
    [(section_id, índice del pedazo), ...]).
    """
    res = Conservation(n_sections=len(sections))
    for sid, text in sections.items():
        sl = sorted(pieces.get(sid, []))
        res.n_pieces += len(sl)
        covered = bool(sl) and sl[0][0] == 0 and sl[-1][1] == len(text)
        covered = covered and all(a[1] == b[0] for a, b in zip(sl, sl[1:], strict=False))
        if not covered:
            res.gaps.append(sid)

    seen: Counter = Counter()
    for chunk_text, members in chunks:
        for sid, k in members:
            seen[(sid, k)] += 1
            a, b = pieces[sid][k]
            if sections[sid][a:b].strip() not in chunk_text:
                res.not_verbatim.append(f"{sid}[{k}]")
    for sid in sections:
        for k in range(len(pieces.get(sid, []))):
            if seen[(sid, k)] == 0:
                res.unassigned.append(f"{sid}[{k}]")
            elif seen[(sid, k)] > 1:
                res.duplicated.append(f"{sid}[{k}]")

    before = sum((_lines(t) for t in sections.values()), Counter())
    after = sum((_lines(t) for t, _ in chunks), Counter())
    res.lines_missing = sum((before - after).values())
    res.lines_extra = sum((after - before).values())
    return res
