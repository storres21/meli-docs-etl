"""Etapa 1 — perfilado de los docs crudos.

Salidas:
- `<processed_dir>/inventory.jsonl`: una fila por archivo (la reutilizan dedup/split).
- `<reports_dir>/profile.md`: reporte legible.

El reporte es determinista (sin timestamps, orden estable) para que dos corridas
sobre la misma entrada produzcan exactamente el mismo archivo.
"""

from __future__ import annotations

import json
import logging
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path

from meli_docs_etl.config import Config, ProfileConfig, find_project_root
from meli_docs_etl.inventory import ALIAS_VERSIONS, FileRecord, build_inventory

log = logging.getLogger(__name__)

FILE_TYPES = ("content", "nav", "spec", "meta", "other")


def _table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    def cell(v: object) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


def _kb(n: int) -> str:
    return f"{n / 1024:.1f}"


def _dup_groups(records: list[FileRecord], key: str) -> list[list[FileRecord]]:
    groups: dict[str, list[FileRecord]] = defaultdict(list)
    for r in records:
        groups[getattr(r, key)].append(r)
    dups = [g for g in groups.values() if len(g) > 1]
    return sorted(dups, key=lambda g: (-len(g), g[0].path))


def _display_path(p: Path) -> str:
    root = find_project_root()
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return p.as_posix()


def render_report(records: list[FileRecord], raw_dir: Path, pcfg: ProfileConfig) -> str:
    md = [r for r in records if r.file_type in {"content", "nav"}]
    content = [r for r in records if r.file_type == "content"]
    projects = sorted({r.project for r in records})
    versions = sorted({(r.project, r.version_dir) for r in records})
    exact = _dup_groups(records, "sha256")
    exact_hashes = {g[0].sha256 for g in exact}
    norm_only = [g for g in _dup_groups(records, "sha256_norm") if len({r.sha256 for r in g}) > 1]
    redundant = sum(len(g) - 1 for g in exact)
    status = Counter(r.status for r in content)
    langs = Counter(r.lang for r in content)

    out: list[str] = ["# Perfil de `docs_raw`", ""]
    out.append(
        f"Fuente: `{_display_path(raw_dir)}`. Generado por `meli-etl profile` "
        "(determinista: misma entrada → mismo reporte)."
    )

    # 1. Resumen
    out += ["", "## 1. Resumen", ""]
    out.append(
        _table(
            ["Métrica", "Valor"],
            [
                ("Proyectos", len(projects)),
                ("Carpetas de versión", len(versions)),
                ("Archivos", len(records)),
                ("Tamaño total (KB)", _kb(sum(r.size_bytes for r in records))),
                ("Markdown de contenido", len(content)),
                (
                    "Markdown de navegación (_sidebar/_coverpage)",
                    sum(r.file_type == "nav" for r in records),
                ),
                ("Specs (swagger/openapi)", sum(r.file_type == "spec" for r in records)),
                (
                    "Metadatos (documentationTypes.json)",
                    sum(r.file_type == "meta" for r in records),
                ),
                ("Grupos de duplicados exactos (sha256)", len(exact)),
                (
                    "Archivos redundantes (copias sobre el primero)",
                    f"{redundant} ({redundant / max(len(records), 1):.0%})",
                ),
                ("Grupos duplicados solo tras normalizar espacios", len(norm_only)),
                (
                    "Contenido vacío / solo TO DO / stub",
                    f"{status['empty']} / {status['todo_only']} / {status['stub']}",
                ),
                (
                    "Contenido con al menos una sección TO DO",
                    sum(bool(r.todo_sections) for r in content),
                ),
                (
                    "Idioma del contenido (es / en / mixed / unknown)",
                    f"{langs['es']} / {langs['en']} / {langs['mixed']} / {langs['unknown']}",
                ),
                ("Archivos no UTF-8", sum(not r.utf8_ok for r in records)),
            ],
        )
    )

    # 2. Por proyecto y versión
    out += ["", "## 2. Archivos por proyecto / versión / tipo", ""]
    rows = []
    for project, version in versions:
        group = [r for r in records if r.project == project and r.version_dir == version]
        c = Counter(r.file_type for r in group)
        resolved = group[0].resolved_version
        rows.append(
            (
                project,
                version,
                resolved if resolved != version else "=",
                len(group),
                *(c[t] for t in FILE_TYPES),
                _kb(sum(r.size_bytes for r in group)),
            )
        )
    out.append(
        _table(
            ["Proyecto", "Versión (carpeta)", "Versión resuelta", "Total", *FILE_TYPES, "KB"], rows
        )
    )
    out += ["", "### Totales por tipo", ""]
    out.append(
        _table(
            ["Tipo", "Extensiones", "Archivos", "KB"],
            [
                (
                    t,
                    ", ".join(sorted({r.ext for r in records if r.file_type == t})),
                    sum(r.file_type == t for r in records),
                    _kb(sum(r.size_bytes for r in records if r.file_type == t)),
                )
                for t in FILE_TYPES
                if any(r.file_type == t for r in records)
            ],
        )
    )

    # 3. Versiones alias
    aliases = sorted(
        {
            (r.project, r.version_dir, r.resolved_version)
            for r in records
            if r.version_dir in ALIAS_VERSIONS
        }
    )
    out += ["", "### Versiones alias (`latest`) resueltas vía documentationTypes.json", ""]
    if aliases:
        siblings = {(r.project, r.version_dir) for r in records}
        out.append(
            _table(
                ["Proyecto", "Alias", "Apunta a", "¿Esa versión también está en docs_raw?"],
                [
                    (p, v, res, "sí" if (p, res) in siblings and res != v else "no")
                    for p, v, res in aliases
                ],
            )
        )
    else:
        out.append("_No hay carpetas alias._")

    # 4. Tamaños
    out += ["", "## 3. Tamaños (Markdown de contenido)", ""]
    if content:
        sizes = sorted(r.size_bytes for r in content)
        wcount = sorted(r.n_words for r in content)
        q = lambda xs, p: xs[min(len(xs) - 1, int(p * len(xs)))]  # noqa: E731
        out.append(
            _table(
                ["Métrica", "min", "p25", "mediana", "p90", "max", "media"],
                [
                    (
                        "Bytes",
                        sizes[0],
                        q(sizes, 0.25),
                        int(statistics.median(sizes)),
                        q(sizes, 0.9),
                        sizes[-1],
                        int(statistics.mean(sizes)),
                    ),
                    (
                        "Palabras útiles",
                        wcount[0],
                        q(wcount, 0.25),
                        int(statistics.median(wcount)),
                        q(wcount, 0.9),
                        wcount[-1],
                        int(statistics.mean(wcount)),
                    ),
                ],
            )
        )
        by_size = sorted(content, key=lambda r: (-r.size_bytes, r.path))
        out += ["", "**Los 10 más grandes**", ""]
        out.append(
            _table(
                ["Archivo", "Bytes", "Palabras"],
                [(r.path, r.size_bytes, r.n_words) for r in by_size[:10]],
            )
        )
        out += ["", "**Los 10 más chicos**", ""]
        out.append(
            _table(
                ["Archivo", "Bytes", "Palabras"],
                [(r.path, r.size_bytes, r.n_words) for r in by_size[::-1][:10]],
            )
        )

    # 5. Duplicados
    out += ["", "## 4. Duplicados exactos (sha256 de bytes)", ""]
    if exact:
        rows = []
        for g in exact:
            rows.append(
                (
                    f"`{g[0].sha256[:10]}`",
                    g[0].file_type,
                    len(g),
                    "sí" if len({r.version_dir for r in g}) > 1 else "no",
                    "sí" if len({r.project for r in g}) > 1 else "no",
                    "<br>".join(r.path for r in g),
                )
            )
        out.append(
            _table(
                ["Hash", "Tipo", "Copias", "Cruza versiones", "Cruza proyectos", "Archivos"], rows
            )
        )
        out += [
            "",
            "**Redundancia por proyecto** (archivos que tienen al menos una copia exacta)",
            "",
        ]
        out.append(
            _table(
                ["Proyecto", "Archivos", "Con copia exacta", "%"],
                [
                    (
                        p,
                        n := sum(r.project == p for r in records),
                        d := sum(r.project == p and r.sha256 in exact_hashes for r in records),
                        f"{d / n:.0%}",
                    )
                    for p in projects
                ],
            )
        )
    else:
        out.append("_Sin duplicados exactos._")
    out += ["", "### Duplicados solo tras normalizar espacios / saltos de línea", ""]
    if norm_only:
        out.append(
            _table(
                ["Hash norm.", "Archivos"],
                [(f"`{g[0].sha256_norm[:10]}`", "<br>".join(r.path for r in g)) for g in norm_only],
            )
        )
    else:
        out.append(
            "_Ninguno adicional: las copias o son idénticas byte a byte o difieren en contenido._"
        )

    # 6. Calidad
    out += ["", '## 5. Archivos vacíos, "TO DO" y stubs', ""]
    flagged = sorted((r for r in content if r.status != "ok"), key=lambda r: (r.status, r.path))
    if flagged:
        out.append(
            _table(
                ["Archivo", "Estado", "Palabras útiles", "Bytes"],
                [(r.path, r.status, r.n_words, r.size_bytes) for r in flagged],
            )
        )
    else:
        out.append("_Todos los archivos de contenido tienen texto útil._")
    with_todo = sorted(
        (r for r in content if r.todo_sections), key=lambda r: (-len(r.todo_sections), r.path)
    )
    out += ["", "### Secciones TO DO dentro de archivos", ""]
    if with_todo:
        out.append(
            _table(
                ["Archivo", "Secciones TO DO / total", "Secciones"],
                [
                    (
                        r.path,
                        f"{len(r.todo_sections)} / {r.n_sections}",
                        "<br>".join(r.todo_sections),
                    )
                    for r in with_todo
                ],
            )
        )
    else:
        out.append("_Ninguna._")

    # 7. Idioma
    out += ["", "## 6. Idioma detectado", ""]
    out.append(
        "Heurística de stopwords es/en sobre el texto sin código, URLs ni badges. "
        f"`mixed` = el idioma dominante tiene < {pcfg.lang_mixed_threshold:.0%} de las stopwords; "
        f"`unknown` = menos de {pcfg.lang_min_stopwords} stopwords."
    )
    out += [""]
    out.append(
        _table(
            ["Proyecto", "es", "en", "mixed", "unknown"],
            [
                (
                    p,
                    *(
                        sum(r.project == p and r.lang == lab for r in content)
                        for lab in ("es", "en", "mixed", "unknown")
                    ),
                )
                for p in projects
            ],
        )
    )
    out += ["", "<details><summary>Idioma por archivo de contenido</summary>", ""]
    out.append(
        _table(
            ["Archivo", "Idioma", "hits es", "hits en"],
            [(r.path, r.lang, r.lang_es_hits, r.lang_en_hits) for r in content],
        )
    )
    out += ["", "</details>"]

    # 8. Headers
    out += ["", "## 7. Headers por archivo", ""]
    out.append(
        "`H1` = cantidad de headers de nivel 1; `saltos` = transiciones que saltean niveles "
        "(p. ej. H1→H3); `mal formados` = `#Título` sin espacio (no es header en CommonMark)."
    )
    out += [""]
    rows = []
    for r in md:
        levels = [h["level"] for h in r.headers]
        jumps = sum(1 for a, b in zip(levels, levels[1:], strict=False) if b > a + 1)
        rows.append(
            (
                r.path,
                r.file_type,
                len(levels),
                levels.count(1),
                max(levels) if levels else 0,
                jumps,
                sum(h["malformed"] for h in r.headers),
            )
        )
    out.append(
        _table(["Archivo", "Tipo", "Headers", "H1", "Prof. máx.", "Saltos", "Mal formados"], rows)
    )
    malformed = [(r.path, h) for r in md for h in r.headers if h["malformed"]]
    if malformed:
        out += ["", "**Headers mal formados**", ""]
        out.append(
            _table(
                ["Archivo", "Línea", "Texto"], [(p, h["line"], h["title"]) for p, h in malformed]
            )
        )
    out += ["", "<details><summary>Outline completo por archivo</summary>", ""]
    for r in md:
        out += [f"**{r.path}**", ""]
        if r.headers:
            out += (
                ["```text"]
                + [("  " * (h["level"] - 1)) + f"H{h['level']} {h['title']}" for h in r.headers]
                + ["```", ""]
            )
        else:
            out += ["_(sin headers)_", ""]
    out += ["</details>"]

    # 9. Specs y metadatos
    specs = [r for r in records if r.file_type == "spec"]
    out += ["", "## 8. Specs y metadatos", ""]
    if specs:
        out.append(
            _table(
                ["Archivo", "Formato", "Título", "Versión API", "Paths", "Operaciones"],
                [
                    (
                        r.path,
                        f"{r.spec_info.get('format', '?')} "
                        f"{r.spec_info.get('spec_version', '')}".strip(),
                        r.spec_info.get("title", ""),
                        r.spec_info.get("api_version", ""),
                        r.spec_info.get("n_paths", ""),
                        r.spec_info.get("n_operations", r.spec_info.get("error", "")),
                    )
                    for r in specs
                ],
            )
        )
        out += [""]
    metas = [r for r in records if r.file_type == "meta"]
    out.append(
        _table(
            ["Archivo", "Tipos", "URL de origen (guide)"],
            [
                (r.path, ", ".join(sorted(r.source_urls)), r.source_urls.get("guide", ""))
                for r in metas
            ],
        )
    )

    out += [
        "",
        "## Notas metodológicas",
        "",
        "- **Tipo**: `nav` = archivos de navegación docsify; `meta` = documentationTypes.json; "
        "`spec` = YAML/JSON de API; `content` = el resto del Markdown.",
        "- **Palabras útiles**: tras quitar bloques de código, inline code, comentarios HTML, "
        "imágenes/badges, URLs, tags HTML, headers y marcadores TO DO.",
        "- **Estados**: `empty` = sin texto tras limpiar; `todo_only` = solo marcadores TO DO; "
        f"`stub` = menos de {pcfg.stub_max_words} palabras útiles (`stub_max_words`).",
        "- **Duplicados**: aquí solo exactos. Los casi duplicados (MinHash/shingles) "
        "se tratan en la etapa `dedup`.",
        "- El inventario completo está en `inventory.jsonl` dentro de `processed_dir`.",
        "",
    ]
    return "\n".join(out)


def run(cfg: Config) -> Path:
    records = build_inventory(cfg.paths.raw_dir, cfg.profile)

    cfg.paths.processed_dir.mkdir(parents=True, exist_ok=True)
    inv_path = cfg.paths.processed_dir / "inventory.jsonl"
    with open(inv_path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    log.info("Inventario escrito en %s (%d filas)", inv_path, len(records))

    cfg.paths.reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = cfg.paths.reports_dir / "profile.md"
    report_path.write_text(render_report(records, cfg.paths.raw_dir, cfg.profile), encoding="utf-8")
    log.info("Reporte escrito en %s", report_path)
    return report_path
