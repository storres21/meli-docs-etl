"""Parseo de navegación docsify (_sidebar / _coverpage) a metadata."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any

from meli_docs_etl.normalize import clean_title, normalize_markdown

_ITEM_RE = re.compile(r"^(\s*)[-*+]\s+(.*\S)\s*$")
_LINK_RE = re.compile(r"^\[(.*)\]\(([^)]*)\)$")
_LINK_ONLY_LINE_RE = re.compile(r"^\s*\[[^\]]*\]\([^)]*\)\s*$")


@dataclass(frozen=True)
class NavEntry:
    order: int
    depth: int
    title: str
    link: str | None  # link original
    target: str | None  # archivo .md resuelto, relativo a guide/ (None si externo o grupo)
    anchor: str | None
    parent: str | None  # título del ítem padre (grupo)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_link(link: str) -> tuple[str | None, str | None]:
    """Link docsify → (archivo .md relativo a guide/, ancla)."""
    if re.match(r"^[a-z]+://", link) or link.startswith("mailto:"):
        return None, None
    path, _, anchor = link.partition("#")
    path = path.strip().lstrip("/")
    if path.startswith("./"):
        path = path[2:]
    if not path or path.endswith("/"):
        path += "README.md"
    elif not PurePosixPath(path).suffix:
        path += ".md"
    return path, anchor or None


def parse_sidebar(text: str) -> list[NavEntry]:
    text = normalize_markdown(text).text
    items: list[tuple[int, str]] = []
    for line in text.splitlines():
        if m := _ITEM_RE.match(line):
            items.append((len(m.group(1).expandtabs(4)), m.group(2)))
    indents = sorted({indent for indent, _ in items})
    entries: list[NavEntry] = []
    stack: list[tuple[int, str]] = []  # (depth, title)
    for order, (indent, body) in enumerate(items):
        depth = indents.index(indent)
        link = None
        if m := _LINK_RE.match(body):
            title, link = m.group(1), m.group(2).strip()
        else:
            title = body
        title = clean_title(title)
        target, anchor = resolve_link(link) if link else (None, None)
        stack = [s for s in stack if s[0] < depth]
        parent = stack[-1][1] if stack else None
        entries.append(NavEntry(order, depth, title, link, target, anchor, parent))
        stack.append((depth, title))
    return entries


def parse_coverpage(text: str) -> dict[str, Any]:
    """Título (primer header) y frase descriptiva (prosa que no es link ni header)."""
    norm = normalize_markdown(text)
    title = None
    tagline: list[str] = []
    for line in norm.text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            title = title or clean_title(s.lstrip("#"))
        elif not _LINK_ONLY_LINE_RE.match(s):
            tagline.append(clean_title(s.lstrip("> ").strip()))
    return {"title": title, "tagline": " ".join(t for t in tagline if t) or None}
