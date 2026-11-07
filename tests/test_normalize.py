"""Tests de normalización, filtrado y navegación."""

from __future__ import annotations

from meli_docs_etl.config import load_config
from meli_docs_etl.nav import parse_coverpage, parse_sidebar, resolve_link
from meli_docs_etl.normalize import (
    NormStats,
    clean_title,
    normalize_header_line,
    normalize_markdown,
    title_from_filename,
)
from meli_docs_etl.stages.normalize import Normalizer, split_raw_sections

META = {"project": "proj", "version_dir": "1.0", "declared_version": "1.0", "source_url": None}


def norm(text: str) -> str:
    return normalize_markdown(text).text


def test_entities_decoded_everywhere_including_code() -> None:
    raw = "It&#39;s &gt; 0\n\n```bash\ncurl &#39;https://x.io/a?b=1&#39; -d &#34;{}&#34;\n```\n"
    assert norm(raw) == "It's > 0\n\n```bash\ncurl 'https://x.io/a?b=1' -d \"{}\"\n```"
    # Sin ";" no es una entidad: no se toca (evita romper query strings).
    assert norm("https://x.io/?a=1&copy=2") == "https://x.io/?a=1&copy=2"


def test_tables_with_different_padding_become_identical() -> None:
    a = "| METHOD | PATH      |\n|--------|-----------|\n| GET    | `/a`      |\n"
    b = "| METHOD            | PATH |\n|:------------------|------|\n| GET | `/a` |\n| |\n"
    assert norm(a) == "| METHOD | PATH |\n| --- | --- |\n| GET | `/a` |"
    # Alineación preservada; la fila vacía (rota) se elimina.
    assert norm(b) == "| METHOD | PATH |\n| :--- | --- |\n| GET | `/a` |"


def test_badges_images_comments_and_style() -> None:
    raw = (
        "<!-- docsify -->\n"
        "[![Java](https://img.shields.io/badge/Java-17-red.svg?style=for-the-badge)](https://x)\n"
        "![arch](media/arch.png) Texto ![color](#f0f0f0)\n"
        '<summary style="border: 1px">Respuesta</summary>\n'
    )
    res = normalize_markdown(raw, stats := NormStats())
    assert res.text == "Texto\n<summary>Respuesta</summary>"
    assert res.badges == ["Java 17"]
    assert res.images == [{"alt": "arch", "src": "media/arch.png"}]
    assert stats.counts["html_comments_removed"] == 1
    assert stats.counts["style_attrs_removed"] == 1


def test_code_blocks_are_preserved() -> None:
    raw = "Intro\n\n```python\n# no es header\nx  =  1   \n![img](a.png)\n```\n"
    assert norm(raw) == "Intro\n\n```python\n# no es header\nx  =  1\n![img](a.png)\n```"


def test_headers_and_titles() -> None:
    assert normalize_header_line("#Use cases") == "# Use cases"
    assert normalize_header_line("### [Link](http://x) **bold** ###") == "### Link bold"
    assert normalize_header_line("texto # no") is None
    assert clean_title("Price Engine <!-- {docsify-ignore} -->") == "Price Engine"
    assert title_from_filename("p/1/guide/setup/local-development.md") == "Local Development"
    assert title_from_filename("p/1/guide/setup/README.md") == "Setup"
    assert title_from_filename("p/1/guide/README.md", "my-proj") == "My Proj"


def test_split_synthesizes_h1_and_section_paths() -> None:
    doc, secs = Normalizer(load_config()).process_doc(
        "## Carga\nEl servicio carga la configuración de cada flujo de pagos.\n\n"
        "### Paso 1\nSe ejecuta el comando de carga para el flujo indicado.\n",
        "proj/1.0/guide/howto.md",
        META,
    )
    assert doc["title"] == "Howto" and doc["title_synthetic"]
    assert doc["text"].startswith("# Howto\n\n## Carga")
    assert [s["section_path"] for s in secs] == [["Howto", "Carga"], ["Howto", "Carga", "Paso 1"]]
    assert all(s["language"] == "es" for s in secs)
    title, synthetic, raw = split_raw_sections("#Titulo\ntexto\n", "a.md", "p")
    assert (title, synthetic, raw[0].malformed) == ("Titulo", False, True)


def test_stub_filter_counts_code_and_tables() -> None:
    n = Normalizer(load_config())
    table_only = (
        "# Jobs\n\n| Name | Timerule | Endpoint |\n| --- | --- | --- |\n"
        "| midday | 0 12 * * * | /cron/midday |\n| nightly | 0 20 * * * | /cron/nightly |\n"
    )
    images_only = "# Architecture\n\n#### Prod\n![Prod](/a.png)\n"
    todo = "# General\n\n## Intro\nTO DO.\n"
    assert n.process_doc(table_only, "p/1/guide/jobs.md", META)[0]["status"] == "ok"
    assert n.process_doc(images_only, "p/1/guide/arch.md", META)[0]["status"] == "stub"
    assert n.process_doc(todo, "p/1/guide/general.md", META)[0]["status"] == "todo_only"

    doc, secs = n.process_doc(
        "# API\n\n# Domain\nEl dominio expone servicios de stock para vendedores.\n"
        "## Pendiente\nTODO\n",
        "p/1/guide/api.md",
        META,
    )
    assert [s["drop_reason"] for s in secs] == ["empty_body", None, "todo"]


def test_nav_parsing() -> None:
    assert resolve_link("/introduction") == ("introduction.md", None)
    assert resolve_link("setup/") == ("setup/README.md", None)
    assert resolve_link("/") == ("README.md", None)
    assert resolve_link("howto.md#carga") == ("howto.md", "carga")
    assert resolve_link("https://github.com/x") == (None, None)

    entries = parse_sidebar("- Guide\n    * [Usage](/usage.md)\n- [**Inicio**](README.md)\n")
    assert [(e.title, e.depth, e.target, e.parent) for e in entries] == [
        ("Guide", 0, None, None),
        ("Usage", 1, "usage.md", "Guide"),
        ("Inicio", 0, "README.md", None),
    ]
    cover = parse_coverpage(
        "![logo](a.png &#39;:size=200&#39;)\n\n# VENDOR API\n\n&gt; Application responsible "
        "for stocking.\n\n[GitHub](https://g)\n[Start](intro.md)\n\n![color](#f0f0f0)\n"
    )
    assert cover == {"title": "VENDOR API", "tagline": "Application responsible for stocking."}
