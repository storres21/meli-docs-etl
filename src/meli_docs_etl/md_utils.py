"""Utilidades de Markdown: headers, secciones, limpieza de ruido y placeholders.

Se usa regex con seguimiento de bloques de código en lugar de un parser CommonMark
porque necesitamos *detectar* headers mal formados (p.ej. `#Titulo` sin espacio),
que un parser estricto descartaría silenciosamente.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
# '#' pegado al texto: no es header en CommonMark, pero claramente se intentó uno.
MALFORMED_ATX_RE = re.compile(r"^ {0,3}(#{1,6})([^#\s].*)$")
SETEXT_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
CLOSING_HASHES_RE = re.compile(r"[ \t]+#+[ \t]*$")

_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_URL_RE = re.compile(r"https?://\S+")
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}.*$", re.MULTILINE)
_WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?", re.UNICODE)


@dataclass(frozen=True)
class Header:
    level: int
    title: str
    line: int  # 1-indexed
    malformed: bool = False


@dataclass(frozen=True)
class Section:
    path: tuple[str, ...]  # ruta de headers desde la raíz
    body: str


def iter_lines(text: str) -> Iterator[tuple[int, str, bool]]:
    """Itera (n_línea, línea, dentro_de_fence). Las líneas delimitadoras cuentan como dentro."""
    fence: str | None = None
    for i, line in enumerate(text.splitlines(), start=1):
        m = FENCE_RE.match(line)
        if fence is None and m:
            fence = m.group(1)[0] * len(m.group(1))
            yield i, line, True
        elif fence is not None:
            closing = m is not None and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence)
            yield i, line, True
            if closing:
                fence = None
        else:
            yield i, line, False


def _clean_title(raw: str) -> str:
    title = HTML_COMMENT_RE.sub("", raw)
    title = CLOSING_HASHES_RE.sub("", title)
    return title.strip()


def extract_headers(text: str) -> list[Header]:
    headers: list[Header] = []
    prev: tuple[int, str] | None = None  # última línea de párrafo candidata a setext
    for n, line, in_fence in iter_lines(text):
        if in_fence:
            prev = None
            continue
        if m := ATX_RE.match(line):
            headers.append(Header(len(m.group(1)), _clean_title(m.group(2) or ""), n))
            prev = None
        elif m := MALFORMED_ATX_RE.match(line):
            headers.append(Header(len(m.group(1)), _clean_title(m.group(2)), n, malformed=True))
            prev = None
        elif (m := SETEXT_RE.match(line)) and prev is not None:
            level = 1 if m.group(1).startswith("=") else 2
            headers.append(Header(level, _clean_title(prev[1]), prev[0]))
            prev = None
        elif line.strip() and not line.lstrip().startswith(("-", "*", "+", "|", ">", "<")):
            prev = (n, line)
        else:
            prev = None
    return headers


def split_sections(text: str) -> list[Section]:
    """Divide el documento en secciones (ruta de headers, cuerpo)."""
    headers = {h.line: h for h in extract_headers(text)}
    setext_underlines = {h.line + 1 for h in headers.values() if not h.malformed}
    lines = text.splitlines()
    stack: list[Header] = []
    sections: list[Section] = []
    body: list[str] = []

    def flush() -> None:
        sections.append(Section(tuple(h.title for h in stack), "\n".join(body)))

    for n, line in enumerate(lines, start=1):
        if n in headers:
            flush()
            body = []
            h = headers[n]
            stack = [s for s in stack if s.level < h.level] + [h]
        elif n in setext_underlines and SETEXT_RE.match(line) and (n - 1) in headers:
            continue
        else:
            body.append(line)
    flush()
    return [s for s in sections if s.path or s.body.strip()]


def strip_noise(text: str, drop_headers: bool = False) -> str:
    """Quita código, comentarios, imágenes/badges, URLs y HTML; conserva el texto de links."""
    kept = []
    for _, line, in_fence in iter_lines(text):
        if in_fence:
            continue
        if drop_headers and (ATX_RE.match(line) or MALFORMED_ATX_RE.match(line)):
            continue
        kept.append(line)
    out = "\n".join(kept)
    out = HTML_COMMENT_RE.sub(" ", out)
    out = _IMAGE_RE.sub(" ", out)
    out = _LINK_RE.sub(r"\1", out)
    out = _INLINE_CODE_RE.sub(" ", out)
    out = _URL_RE.sub(" ", out)
    out = _HTML_TAG_RE.sub(" ", out)
    out = _TABLE_SEP_RE.sub(" ", out)
    if drop_headers:
        out = "\n".join(ln for ln in out.splitlines() if not SETEXT_RE.match(ln))
    return out


def words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def compile_todo(patterns: Sequence[str]) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(patterns) + r")\b", re.IGNORECASE)


def is_placeholder(text: str, todo_re: re.Pattern[str]) -> bool:
    """True si el texto contiene un marcador TODO y nada más con letras."""
    cleaned = strip_noise(text, drop_headers=True)
    if not todo_re.search(cleaned):
        return False
    return not words(todo_re.sub(" ", cleaned))
