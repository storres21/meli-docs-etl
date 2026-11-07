"""Inventario de archivos crudos: clasificación, versión resuelta, hashes y métricas."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from meli_docs_etl.config import Config
from meli_docs_etl.lang import detect_language
from meli_docs_etl.md_utils import (
    compile_todo,
    extract_headers,
    is_placeholder,
    split_sections,
    strip_noise,
    words,
)

log = logging.getLogger(__name__)

META_FILENAME = "documentationTypes.json"
ALIAS_VERSIONS = frozenset({"latest", "current", "stable"})


@dataclass
class FileRecord:
    path: str  # relativo a raw_dir, siempre con "/"
    project: str
    version_dir: str
    resolved_version: str
    doc_kind: str  # guide | specs | root
    file_type: str  # content | nav | spec | meta | other
    ext: str
    size_bytes: int
    n_lines: int
    sha256: str
    sha256_norm: str  # hash tras normalizar espacios/saltos de línea
    utf8_ok: bool = True
    # Solo Markdown
    n_words: int = 0  # palabras útiles (sin código, badges, headers, URLs)
    status: str = "n/a"  # ok | empty | todo_only | stub | n/a
    n_sections: int = 0
    todo_sections: list[str] = field(default_factory=list)
    lang: str = "n/a"
    lang_es_hits: int = 0
    lang_en_hits: int = 0
    headers: list[dict[str, Any]] = field(default_factory=list)
    # Solo meta / spec
    source_urls: dict[str, str] = field(default_factory=dict)
    spec_info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_for_hash(text: str) -> str:
    """Normalización mínima: finales de línea, espacios a la derecha y líneas en blanco extra."""
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def classify(rel: Path, nav_filenames: tuple[str, ...]) -> str:
    name, ext = rel.name, rel.suffix.lower()
    if name == META_FILENAME:
        return "meta"
    if name in nav_filenames:
        return "nav"
    if ext in {".yaml", ".yml"} or (ext == ".json" and "specs" in rel.parts):
        return "spec"
    if ext in {".md", ".markdown"}:
        return "content"
    return "other"


def split_path(rel: Path) -> tuple[str, str, str]:
    parts = rel.parts
    project = parts[0] if len(parts) > 1 else ""
    version = parts[1] if len(parts) > 2 else ""
    kind = parts[2] if len(parts) > 3 else "root"
    return project, version, kind


def version_from_urls(urls: dict[str, str], project: str) -> str | None:
    pattern = re.compile(rf"/{re.escape(project)}/([^/]+)/")
    for url in urls.values():
        if m := pattern.search(url):
            return m.group(1)
    return None


def load_meta(raw_dir: Path) -> dict[tuple[str, str], dict[str, str]]:
    """Lee todos los documentationTypes.json → {(proyecto, versión_dir): urls}."""
    meta: dict[tuple[str, str], dict[str, str]] = {}
    for f in sorted(raw_dir.rglob(META_FILENAME)):
        project, version, _ = split_path(f.relative_to(raw_dir))
        try:
            meta[(project, version)] = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            log.warning("No se pudo parsear %s: %s", f, exc)
    return meta


def _analyze_markdown(rec: FileRecord, text: str, cfg: Config) -> None:
    todo_re = compile_todo(cfg.text.todo_patterns)
    rec.headers = [
        {"level": h.level, "title": h.title, "line": h.line, "malformed": h.malformed}
        for h in extract_headers(text)
    ]
    sections = split_sections(text)
    rec.n_sections = len(sections)
    rec.todo_sections = [
        " > ".join(s.path) or "(sin header)" for s in sections if is_placeholder(s.body, todo_re)
    ]
    useful = words(todo_re.sub(" ", strip_noise(text, drop_headers=True)))
    rec.n_words = len(useful)

    if not strip_noise(text).strip():
        rec.status = "empty"
    elif is_placeholder(text, todo_re):
        rec.status = "todo_only"
    elif rec.n_words < cfg.profile.stub_max_words:
        rec.status = "stub"
    else:
        rec.status = "ok"

    # Sin marcadores TODO: "TO DO" aportaría un falso hit inglés ("do").
    lang = detect_language(
        todo_re.sub(" ", text), cfg.text.lang_min_stopwords, cfg.text.lang_mixed_threshold
    )
    rec.lang, rec.lang_es_hits, rec.lang_en_hits = lang.label, lang.es_hits, lang.en_hits


def _analyze_spec(rec: FileRecord, text: str) -> None:
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        rec.spec_info = {"error": str(exc).splitlines()[0]}
        return
    info = doc.get("info", {}) if isinstance(doc, dict) else {}
    paths = doc.get("paths", {}) if isinstance(doc, dict) else {}
    rec.spec_info = {
        "format": "openapi" if "openapi" in doc else "swagger" if "swagger" in doc else "?",
        "spec_version": str(doc.get("openapi") or doc.get("swagger") or ""),
        "title": str(info.get("title", "")),
        "api_version": str(info.get("version", "")),
        "n_paths": len(paths) if isinstance(paths, dict) else 0,
        "n_operations": sum(
            len([k for k in v if k in {"get", "post", "put", "patch", "delete", "head", "options"}])
            for v in (paths.values() if isinstance(paths, dict) else [])
            if isinstance(v, dict)
        ),
    }


def build_inventory(raw_dir: Path, cfg: Config) -> list[FileRecord]:
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"raw_dir no existe: {raw_dir}")

    meta = load_meta(raw_dir)
    records: list[FileRecord] = []
    files = sorted(p for p in raw_dir.rglob("*") if p.is_file() and p.name != ".DS_Store")
    log.info("Perfilando %d archivos en %s", len(files), raw_dir)

    for f in files:
        rel = f.relative_to(raw_dir)
        project, version, kind = split_path(rel)
        data = f.read_bytes()
        try:
            text, utf8_ok = data.decode("utf-8"), True
        except UnicodeDecodeError:
            text, utf8_ok = data.decode("utf-8", errors="replace"), False
            log.warning("Archivo no UTF-8: %s", rel)

        urls = meta.get((project, version), {})
        resolved = version_from_urls(urls, project) or version
        rec = FileRecord(
            path=rel.as_posix(),
            project=project,
            version_dir=version,
            resolved_version=resolved,
            doc_kind=kind,
            file_type=classify(rel, cfg.files.nav_filenames),
            ext=rel.suffix.lower().lstrip("."),
            size_bytes=len(data),
            n_lines=text.count("\n") + (1 if text and not text.endswith("\n") else 0),
            sha256=sha256_bytes(data),
            sha256_norm=sha256_bytes(normalize_for_hash(text).encode("utf-8")),
            utf8_ok=utf8_ok,
        )
        if rec.file_type in {"content", "nav"}:
            _analyze_markdown(rec, text, cfg)
        elif rec.file_type == "spec":
            _analyze_spec(rec, text)
        elif rec.file_type == "meta":
            rec.source_urls = urls
        records.append(rec)
    return records
