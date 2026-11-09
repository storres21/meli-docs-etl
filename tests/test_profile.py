"""Tests de la etapa de perfilado sobre un árbol sintético (no dependen de docs_raw)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meli_docs_etl.config import TextConfig, load_config
from meli_docs_etl.inventory import build_inventory
from meli_docs_etl.lang import detect_language
from meli_docs_etl.md_utils import compile_todo, extract_headers, is_placeholder
from meli_docs_etl.stages import profile

ES_DOC = """# Introducción

![badge](https://img.shields.io/badge/x-y-blue.svg)

Este servicio es responsable de calcular el precio de los productos para cada vendedor.
Se ejecuta cuando llega un evento y guarda el resultado en la base de datos del equipo.

## Uso

```bash
# esto es un comentario, no un header
curl http://localhost:8080/health
```
"""

EN_DOC = """# Overview

This service is responsible for the stock of the items. It reads events from the queue
and writes the result to the database, which is then used by other teams.
"""

FILES = {
    "proj-a/1.0.0/guide/README.md": ES_DOC,
    "proj-a/latest/guide/README.md": ES_DOC,  # duplicado exacto entre versiones
    "proj-a/latest/guide/todo.md": "# Pendiente\n\nTO DO.\n",
    "proj-a/latest/guide/es_todo.md": "# General\n\n## Intro\nTO DO.\n\n"
    "## Alcance\nEl servicio es responsable de la cuenta del vendedor.\n",
    "proj-a/latest/guide/empty.md": "<!-- docsify -->\n",
    "proj-a/latest/guide/mixed.md": "# General\n\n## Intro\nTO DO.\n\n#Malformado\n" + EN_DOC,
    "proj-a/latest/guide/_sidebar.md": "- [Inicio](/README.md)\n",
    "proj-a/latest/documentationTypes.json": json.dumps(
        {"guide": "https://x.s3.amazonaws.com/proj-a/2.3.0/guide/index.html"}
    ),
    "proj-b/latest/specs/swagger.yaml": "openapi: 3.0.0\ninfo: {title: B, version: '1'}\n"
    "paths:\n  /a: {get: {}, post: {}}\n",
}


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    root = tmp_path / "raw"
    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


def test_headers_ignore_code_fences_and_flag_malformed() -> None:
    titles = [h.title for h in extract_headers(ES_DOC)]
    assert titles == ["Introducción", "Uso"]
    hs = extract_headers("#Titulo pegado\n\nTexto\n===\n")
    assert [(h.level, h.title, h.malformed) for h in hs] == [
        (1, "Titulo pegado", True),
        (1, "Texto", False),
    ]


def test_placeholder_detection() -> None:
    todo_re = compile_todo(TextConfig().todo_patterns)
    assert is_placeholder("TO DO.", todo_re)
    assert is_placeholder("### Algo <!-- {docsify-ignore} -->\nTODO", todo_re)
    assert not is_placeholder("TODO: documentar el endpoint de pagos", todo_re)
    assert not is_placeholder("Texto normal", todo_re)


@pytest.mark.parametrize(
    "text", ["_TODO_", "*TODO*", "**TODO**", "__TODO__", "_TBD_", "**WIP**", "### Cron\n_TODO_"]
)
def test_placeholder_detects_emphasized_markers(text: str) -> None:
    assert is_placeholder(text, compile_todo(TextConfig().todo_patterns))


def test_placeholder_needs_whole_word() -> None:
    todo_re = compile_todo(TextConfig().todo_patterns)
    assert not is_placeholder("_TODO_ revisar el endpoint de pagos", todo_re)
    assert not todo_re.search("TODOS los campos")  # palabra más larga
    assert not todo_re.search("wiping")


def test_language_detection() -> None:
    assert detect_language(ES_DOC).label == "es"
    assert detect_language(EN_DOC).label == "en"
    assert detect_language("```\ncode only\n```").label == "unknown"


def test_inventory(raw_dir: Path) -> None:
    recs = {r.path: r for r in build_inventory(raw_dir, load_config())}
    a, b = recs["proj-a/1.0.0/guide/README.md"], recs["proj-a/latest/guide/README.md"]
    assert a.sha256 == b.sha256
    assert b.resolved_version == "2.3.0" and a.resolved_version == "1.0.0"
    assert recs["proj-a/latest/guide/todo.md"].status == "todo_only"
    assert recs["proj-a/latest/guide/empty.md"].status == "empty"
    assert recs["proj-a/latest/guide/es_todo.md"].lang == "es"  # "TO DO" no suma hits en inglés
    mixed = recs["proj-a/latest/guide/mixed.md"]
    assert mixed.status == "ok" and mixed.todo_sections == ["General > Intro"]
    assert recs["proj-a/latest/guide/_sidebar.md"].file_type == "nav"
    assert recs["proj-a/latest/documentationTypes.json"].file_type == "meta"
    spec = recs["proj-b/latest/specs/swagger.yaml"]
    assert spec.file_type == "spec" and spec.spec_info["n_operations"] == 2


def test_profile_end_to_end_is_deterministic(raw_dir: Path, tmp_path: Path) -> None:
    cfg = load_config(
        overrides={
            "raw_dir": raw_dir,
            "processed_dir": tmp_path / "processed",
            "reports_dir": tmp_path / "reports",
        }
    )
    report = profile.run(cfg)
    first = report.read_text(encoding="utf-8")
    assert "## 4. Duplicados exactos" in first
    assert "proj-a/latest/guide/todo.md | todo_only" in first
    assert len((tmp_path / "processed" / "inventory.jsonl").read_text().splitlines()) == len(FILES)

    profile.run(cfg)
    assert report.read_text(encoding="utf-8") == first
