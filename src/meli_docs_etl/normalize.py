"""Normalización de Markdown: transformaciones puras, testeables una por una.

Principio: quitar ruido de formato sin tocar la señal. Los bloques de código, los
comandos curl y las tablas se preservan; solo se canonicaliza su representación
(entidades HTML, espacios finales, padding de tablas).
"""

from __future__ import annotations

import html
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from meli_docs_etl.md_utils import iter_lines

# Solo entidades con ";" final: html.unescape a secas también decodifica entidades
# "legacy" sin ";" y rompería query strings como `?a=1&copy=2`.
_ENTITY_RE = re.compile(r"&(?:#\d+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]{1,31});")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG_RE = re.compile(r"<[A-Za-z][^<>]*>")
_STYLE_ATTR_RE = re.compile(r"""\s+style\s*=\s*(?:"[^"]*"|'[^']*')""", re.IGNORECASE)
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(\s*([^)\s]*)(?:\s+[^)]*)?\)")
_HTML_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_ATTR_RE = r"""\b{}\s*=\s*["']([^"']*)["']"""
_IMG_SENTINEL = "\x00"  # marca temporal donde había una imagen (para limpiar espacios)
_EMPTY_LINK_RE = re.compile(r"\[[\s\x00]*\]\([^)]*\)")
_SENTINEL_RE = re.compile(r"[ \t]*\x00[ \t]*")
_HEADER_RE = re.compile(r"^ {0,3}(#{1,6})(?=[^#]|$)[ \t]*(.*?)[ \t]*$")
_CLOSING_HASHES_RE = re.compile(r"[ \t]+#+$")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_EMPHASIS_RE = re.compile(r"(\*\*|__)(.+?)\1")
_TABLE_SEP_CELL_RE = re.compile(r"^:?-{1,}:?$")
_PIPE_SPLIT_RE = re.compile(r"(?<!\\)\|")
_MULTISPACE_RE = re.compile(r"(?<=\S)[ \t]{2,}")
_BADGE_HINTS = ("shields.io", "/badge/", "badgen.net", "badge.svg")


@dataclass
class NormStats:
    """Contadores de transformaciones aplicadas (para el reporte)."""

    counts: Counter[str] = field(default_factory=Counter)

    def add(self, key: str, n: int = 1) -> None:
        if n:
            self.counts[key] += n


@dataclass
class NormResult:
    text: str
    images: list[dict[str, str]] = field(default_factory=list)
    badges: list[str] = field(default_factory=list)


def decode_entities(text: str, stats: NormStats | None = None) -> str:
    def repl(m: re.Match[str]) -> str:
        decoded = html.unescape(m.group(0))
        if stats is not None and decoded != m.group(0):
            stats.add("entities_decoded")
        return decoded

    return _ENTITY_RE.sub(repl, text)


def clean_title(title: str) -> str:
    """Título de header legible: sin entidades, comentarios, énfasis ni sintaxis de links."""
    t = decode_entities(title)
    t = _COMMENT_RE.sub("", t)
    t = _CLOSING_HASHES_RE.sub("", t.strip())
    t = _LINK_RE.sub(r"\1", t)
    t = _EMPHASIS_RE.sub(r"\2", t)
    return re.sub(r"\s+", " ", t).strip()


def title_from_filename(rel_path: str, project: str = "") -> str:
    """`setup/local-development.md` → "Local Development"; README.md → nombre de la carpeta."""
    p = PurePosixPath(rel_path)
    stem = p.stem
    if stem.lower() in {"readme", "index"}:
        parent = p.parent.name
        stem = parent if parent and parent not in {"guide", "."} else (project or stem)
    words = re.split(r"[-_\s]+", stem)
    return " ".join(w[:1].upper() + w[1:] for w in words if w)


def _badge_label(alt: str, src: str) -> str:
    """La URL del badge trae el dato completo (`/badge/Java-17-red` → "Java 17")."""
    m = re.search(r"/badge/([^/?]+)", src)
    if not m:
        return alt.strip() or src
    parts = m.group(1).replace("_", " ").split("-")
    return " ".join(parts[:-1] if len(parts) > 2 else parts)


def _extract_images(text: str, result: NormResult, stats: NormStats) -> str:
    def md_repl(m: re.Match[str]) -> str:
        alt, src = m.group(1).strip(), m.group(2).strip()
        _record_image(alt, src, result, stats)
        return _IMG_SENTINEL

    def html_repl(m: re.Match[str]) -> str:
        tag = m.group(0)
        src = re.search(_ATTR_RE.format("src"), tag, re.IGNORECASE)
        alt = re.search(_ATTR_RE.format("alt"), tag, re.IGNORECASE)
        _record_image(alt.group(1) if alt else "", src.group(1) if src else "", result, stats)
        return _IMG_SENTINEL

    text = _MD_IMAGE_RE.sub(md_repl, text)
    text = _HTML_IMG_RE.sub(html_repl, text)
    # Badges con link `[![x](badge)](url)` dejan un link vacío.
    return _EMPTY_LINK_RE.sub(_IMG_SENTINEL, text)


def _drop_sentinels(line: str) -> str:
    """Quita las marcas de imagen colapsando el espacio alrededor, sin tocar la indentación."""
    if _IMG_SENTINEL not in line:
        return line
    indent = line[: len(line) - len(line.lstrip(" \t"))]
    rest = _SENTINEL_RE.sub(" ", line[len(indent) :]).strip()
    return indent + rest if rest else ""


def _record_image(alt: str, src: str, result: NormResult, stats: NormStats) -> None:
    if src.startswith("#"):  # `![color](#f0f0f0)`: color de fondo docsify, no es imagen
        stats.add("docsify_colors_removed")
    elif any(h in src for h in _BADGE_HINTS):
        result.badges.append(_badge_label(alt, src))
        stats.add("badges_removed")
    else:
        result.images.append({"alt": alt, "src": src})
        stats.add("images_removed")


def _strip_style(text: str, stats: NormStats) -> str:
    def repl(m: re.Match[str]) -> str:
        new = _STYLE_ATTR_RE.sub("", m.group(0))
        if new != m.group(0):
            stats.add("style_attrs_removed")
        return new

    return _TAG_RE.sub(repl, text)


def normalize_header_line(line: str, stats: NormStats | None = None) -> str | None:
    """Devuelve la línea ATX canónica (`## Título`) o None si no es header.

    También repara headers mal formados (`#Título` → `# Título`).
    """
    m = _HEADER_RE.match(line)
    if not m:
        return None
    if stats is not None and m.group(2) and not re.match(r"^ {0,3}#{1,6}[ \t]", line):
        stats.add("malformed_headers_fixed")
    return f"{m.group(1)} {clean_title(m.group(2))}".rstrip()


def _is_table_sep(line: str) -> bool:
    cells = _split_row(line)
    return bool(cells) and all(_TABLE_SEP_CELL_RE.match(c) for c in cells)


def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip() for c in _PIPE_SPLIT_RE.split(s)]


def _canonical_sep(cell: str) -> str:
    left, right = cell.startswith(":"), cell.endswith(":")
    return (":" if left else "") + "---" + (":" if right else "")


def normalize_tables(lines: list[str], stats: NormStats | None = None) -> list[str]:
    """Reescribe tablas Markdown sin padding: `| a | b |` y separador `|---|---|`."""
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "|" in line and i + 1 < len(lines) and _is_table_sep(lines[i + 1]):
            j = i
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                cells = _split_row(lines[j])
                if j == i + 1:
                    cells = [_canonical_sep(c) for c in cells]
                if any(cells):
                    out.append("| " + " | ".join(cells) + " |")
                elif stats is not None:  # fila rota/vacía (p. ej. un `|` suelto al final)
                    stats.add("empty_table_rows_removed")
                j += 1
            if stats is not None:
                stats.add("tables_normalized")
            i = j
        else:
            out.append(line)
            i += 1
    return out


def _normalize_prose(text: str, result: NormResult, stats: NormStats) -> str:
    n_comments = len(_COMMENT_RE.findall(text))
    stats.add("html_comments_removed", n_comments)
    text = _COMMENT_RE.sub("", text)
    text = _strip_style(text, stats)
    text = _extract_images(text, result, stats)

    lines = []
    for line in text.split("\n"):
        line = _drop_sentinels(line)
        header = normalize_header_line(line, stats)
        if header is not None:
            lines.append(header)
            continue
        line = line.rstrip()
        lead = len(line) - len(line.lstrip())
        lines.append(line[:lead] + _MULTISPACE_RE.sub(" ", line[lead:]))
    lines = normalize_tables(lines, stats)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


def _segments(text: str) -> list[tuple[bool, str]]:
    """Parte el texto en tramos (es_código, texto) respetando fences."""
    segs: list[tuple[bool, list[str]]] = []
    for _, line, in_fence in iter_lines(text):
        if segs and segs[-1][0] == in_fence:
            segs[-1][1].append(line)
        else:
            segs.append((in_fence, [line]))
    return [(code, "\n".join(lines)) for code, lines in segs]


def normalize_markdown(text: str, stats: NormStats | None = None) -> NormResult:
    """Normaliza un fragmento de Markdown (documento o sección)."""
    stats = stats if stats is not None else NormStats()
    result = NormResult(text="")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Las entidades se decodifican en todo el texto, código incluido: en los datos aparecen
    # como artefacto de exportación (p. ej. `curl ... &#39;https://...&#39;`).
    text = decode_entities(text, stats)

    parts = []
    for is_code, seg in _segments(text):
        if is_code:
            parts.append("\n".join(ln.rstrip() for ln in seg.split("\n")))
        else:
            parts.append(_normalize_prose(seg, result, stats))
    result.text = re.sub(r"\n{3,}", "\n\n", "\n".join(parts)).strip("\n")
    return result


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_HTML_ANY_TAG_RE = re.compile(r"</?[A-Za-z][^<>]*>")


def content_tokens(markdown: str) -> list[str]:
    """Tokens de contenido: prosa, código, tablas y links; sin headers ni tags HTML."""
    body = [
        line for _, line, in_fence in iter_lines(markdown) if in_fence or not _HEADER_RE.match(line)
    ]
    return _TOKEN_RE.findall(_HTML_ANY_TAG_RE.sub(" ", "\n".join(body)))
