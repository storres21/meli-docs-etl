"""Etapa 2 — normalize: Markdown crudo → documentos y secciones normalizadas + filtrado.

Se parte el archivo CRUDO en secciones y luego se normaliza cada sección. Así cada
sección conserva su texto original y su hash crudo, lo que permite medir cuántos
duplicados aparecen solo gracias a la normalización.

Salidas (en processed_dir):
- normalized_docs.jsonl: un registro por archivo .md (incluye excluidos y motivo).
- sections.jsonl: todas las secciones (incluye descartadas y motivo).
- nav.jsonl: sidebar/coverpage parseados.
- normalize_stats.json: contadores de transformaciones.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from meli_docs_etl.config import Config
from meli_docs_etl.inventory import classify, load_meta, sha256_bytes, split_path, version_from_urls
from meli_docs_etl.lang import detect_language
from meli_docs_etl.md_utils import compile_todo, extract_headers, is_placeholder
from meli_docs_etl.nav import NavEntry, parse_coverpage, parse_sidebar
from meli_docs_etl.normalize import (
    NormStats,
    clean_title,
    content_tokens,
    normalize_markdown,
    title_from_filename,
)

log = logging.getLogger(__name__)

_WORD_RE = re.compile(r"\w+", re.UNICODE)
DOCS_FILE = "normalized_docs.jsonl"
SECTIONS_FILE = "sections.jsonl"
NAV_FILE = "nav.jsonl"
STATS_FILE = "normalize_stats.json"


def n_words(text: str) -> int:
    return len(_WORD_RE.findall(text))


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


@dataclass
class RawSection:
    level: int
    title: str
    synthetic: bool  # header sintetizado (archivo sin H1)
    raw_text: str  # header + cuerpo, tal cual en el archivo
    raw_body: str
    malformed: bool = False  # `#Título` sin espacio, reparado


def split_raw_sections(raw: str, rel: str, project: str) -> tuple[str, bool, list[RawSection]]:
    """Parte el Markdown crudo por headers. Devuelve (título_doc, título_sintético, secciones).

    Si el archivo no tiene H1 se sintetiza uno a partir del nombre de archivo, que pasa a
    ser la raíz de section_path. El texto previo al primer header (preámbulo) queda bajo
    el título del documento.
    """
    lines = raw.split("\n")
    headers = extract_headers(raw)
    h1 = next((h for h in headers if h.level == 1), None)
    synthetic = h1 is None
    doc_title = title_from_filename(rel, project) if synthetic else clean_title(h1.title)

    sections: list[RawSection] = []
    first = headers[0].line if headers else len(lines) + 1
    preamble = lines[: first - 1]
    if any(ln.strip() for ln in preamble):
        body = "\n".join(preamble)
        sections.append(RawSection(1, doc_title, True, body, body))

    for i, h in enumerate(headers):
        start = h.line - 1
        # Setext: el subrayado es parte del header.
        is_setext = start + 1 < len(lines) and re.match(r"^ {0,3}(=+|-+)\s*$", lines[start + 1])
        body_start = start + (2 if is_setext and not lines[start].lstrip().startswith("#") else 1)
        end = headers[i + 1].line - 1 if i + 1 < len(headers) else len(lines)
        sections.append(
            RawSection(
                level=h.level,
                title=clean_title(h.title),
                synthetic=False,
                raw_text="\n".join(lines[start:end]),
                raw_body="\n".join(lines[body_start:end]),
                malformed=h.malformed,
            )
        )
    return doc_title, synthetic, sections


def _section_paths(doc_title: str, synthetic: bool, sections: list[RawSection]) -> list[list[str]]:
    stack: list[tuple[int, str]] = [(0, doc_title)] if synthetic else []
    paths = []
    for s in sections:
        if s.synthetic:
            paths.append([doc_title])
            continue
        stack = [x for x in stack if x[0] < s.level]
        stack.append((s.level, s.title))
        paths.append([t for _, t in stack])
    return paths


class Normalizer:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.todo_re = compile_todo(cfg.text.todo_patterns)
        self.stats = NormStats()

    def lang(self, text: str) -> str:
        t = self.cfg.text
        return detect_language(
            self.todo_re.sub(" ", text), t.lang_min_stopwords, t.lang_mixed_threshold
        ).label

    def process_doc(
        self, raw: str, rel: str, meta: dict[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        raw = raw.replace("\r\n", "\n").replace("\r", "\n")
        doc_title, synthetic, raw_sections = split_raw_sections(raw, rel, meta["project"])
        if synthetic:
            self.stats.add("h1_synthesized")
        paths = _section_paths(doc_title, synthetic, raw_sections)

        sections: list[dict[str, Any]] = []
        images: list[dict[str, str]] = []
        badges: list[str] = []
        parts = [f"# {doc_title}"] if synthetic else []
        for i, (rs, path) in enumerate(zip(raw_sections, paths, strict=True)):
            norm = normalize_markdown(rs.raw_body, self.stats)
            self.stats.add("malformed_headers_fixed", int(rs.malformed))
            images += norm.images
            badges += norm.badges
            header = f"{'#' * rs.level} {rs.title}"
            if not (rs.synthetic and synthetic):  # el H1 sintético ya está en parts
                parts.append(header)
            if norm.text:
                parts.append(norm.text)
            text = f"{header}\n\n{norm.text}" if norm.text else header
            sections.append(
                {
                    "section_id": f"{rel}#{i:03d}",
                    "doc_path": rel,
                    "ordinal": i,
                    **meta,
                    "level": rs.level,
                    "title": rs.title,
                    "section_path": path,
                    "is_preamble": rs.synthetic,
                    "raw_text": rs.raw_text,
                    "raw_hash": sha256_text(rs.raw_text.strip()),
                    "body": norm.text,
                    "text": text,
                    "norm_hash": sha256_text(text),
                    "tokens": n_words(text),
                    "content_tokens": len(content_tokens(norm.text)),
                }
            )

        doc_text = "\n\n".join(parts) + "\n"
        n_content = len(content_tokens(doc_text))
        if is_placeholder(doc_text, self.todo_re):
            status = "todo_only"
        elif n_content < self.cfg.normalize.stub_min_tokens:
            status = "stub"
        else:
            status = "ok"
        doc_lang = self.lang(doc_text)

        for s in sections:
            lang = self.lang(s["text"])
            s["language"], s["language_source"] = (
                (lang, "section") if lang != "unknown" else (doc_lang, "document")
            )
            if status != "ok":
                s["kept"], s["drop_reason"] = False, f"doc_{status}"
            elif s["content_tokens"] == 0:
                s["kept"], s["drop_reason"] = False, "empty_body"
            elif is_placeholder(s["body"], self.todo_re):
                s["kept"], s["drop_reason"] = False, "todo"
            else:
                s["kept"], s["drop_reason"] = True, None

        doc = {
            "doc_id": rel,
            "path": rel,
            **meta,
            "file_type": "content",
            "title": doc_title,
            "title_synthetic": synthetic,
            "status": status,
            "kept": status == "ok",
            "drop_reason": None if status == "ok" else status,
            "language": doc_lang,
            "content_tokens": n_content,
            "tokens_raw": n_words(raw),
            "tokens": n_words(doc_text),
            "raw_sha256": sha256_text(raw),
            "norm_sha256": sha256_text(doc_text),
            "images": images,
            "badges": sorted(set(badges)),
            "n_sections": len(sections),
            "text": doc_text,
        }
        return doc, sections


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
            n += 1
    return n


def _guide_relative(rel: Path) -> str:
    """Ruta relativa a la carpeta de documentación (guide/) para cruzar con el sidebar."""
    return "/".join(rel.parts[3:]) if len(rel.parts) > 3 else rel.name


def run(cfg: Config) -> dict[str, Any]:
    raw_dir = cfg.paths.raw_dir
    meta_urls = load_meta(raw_dir)
    files = sorted(p for p in raw_dir.rglob("*.md") if p.is_file())
    log.info("Normalizando %d archivos Markdown de %s", len(files), raw_dir)
    normalizer = Normalizer(cfg)

    def file_meta(rel: Path) -> dict[str, Any]:
        project, version_dir, _ = split_path(rel)
        urls = meta_urls.get((project, version_dir), {})
        return {
            "project": project,
            "version_dir": version_dir,
            "declared_version": version_from_urls(urls, project) or version_dir,
            "source_url": urls.get("guide"),
        }

    # 1) Navegación primero: aporta metadata (orden, títulos, tagline) a los documentos.
    nav_rows: list[dict[str, Any]] = []
    sidebar: dict[tuple[str, str], list[NavEntry]] = {}
    covers: dict[tuple[str, str], dict[str, Any]] = {}
    docs: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    for f in files:
        rel = f.relative_to(raw_dir)
        if classify(rel, cfg.files.nav_filenames) != "nav":
            continue
        meta = file_meta(rel)
        key = (meta["project"], meta["version_dir"])
        raw = f.read_text(encoding="utf-8", errors="replace")
        if "sidebar" in f.name or "navbar" in f.name:
            entries = parse_sidebar(raw)
            sidebar[key] = entries
            nav_rows.append(
                {
                    **meta,
                    "path": rel.as_posix(),
                    "kind": "sidebar",
                    "entries": [e.to_dict() for e in entries],
                }
            )
        else:
            cover = parse_coverpage(raw)
            covers[key] = cover
            nav_rows.append({**meta, "path": rel.as_posix(), "kind": "coverpage", **cover})
        docs.append(
            {
                "doc_id": rel.as_posix(),
                "path": rel.as_posix(),
                **meta,
                "file_type": "nav",
                "kept": False,
                "drop_reason": "nav",
                "status": "nav",
                "tokens_raw": n_words(raw),
                "tokens": n_words(normalize_markdown(raw).text),
                "raw_sha256": sha256_text(raw),
                "n_sections": 0,
            }
        )

    # 2) Contenido.
    for f in files:
        rel = f.relative_to(raw_dir)
        if classify(rel, cfg.files.nav_filenames) != "content":
            continue
        meta = file_meta(rel)
        key = (meta["project"], meta["version_dir"])
        doc, secs = normalizer.process_doc(
            f.read_text(encoding="utf-8", errors="replace"), rel.as_posix(), meta
        )
        guide_rel = _guide_relative(rel)
        entry = next(
            (e for e in sidebar.get(key, []) if e.target == guide_rel and not e.anchor),
            next((e for e in sidebar.get(key, []) if e.target == guide_rel), None),
        )
        doc["nav_title"] = entry.title if entry else None
        doc["nav_order"] = entry.order if entry else None
        doc["nav_parent"] = entry.parent if entry else None
        doc["project_tagline"] = covers.get(key, {}).get("tagline")
        docs.append(doc)
        sections.extend(secs)

    out = cfg.paths.processed_dir
    out.mkdir(parents=True, exist_ok=True)
    n_docs = _write_jsonl(out / DOCS_FILE, docs)
    n_secs = _write_jsonl(out / SECTIONS_FILE, sections)
    _write_jsonl(out / NAV_FILE, nav_rows)
    stats = {"transformations": dict(sorted(normalizer.stats.counts.items()))}
    (out / STATS_FILE).write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")

    kept_docs = sum(d["kept"] for d in docs)
    kept_secs = sum(s["kept"] for s in sections)
    log.info(
        "Docs: %d (%d en corpus) | secciones: %d (%d en corpus)",
        n_docs,
        kept_docs,
        n_secs,
        kept_secs,
    )
    for d in docs:
        if d["file_type"] == "content" and not d["kept"]:
            log.info(
                "Excluido %s: %s (%d tokens de contenido)",
                d["path"],
                d["drop_reason"],
                d["content_tokens"],
            )
    return stats
