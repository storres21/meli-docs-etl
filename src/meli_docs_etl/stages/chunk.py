"""Etapa 4 — chunking: secciones deduplicadas + operaciones OpenAPI → corpus.jsonl.

Estructura primero, tamaño después:
- unidad base = sección (canónica o variante de `sections_dedup.jsonl`); las ocurrencias
  absorbidas no generan chunks pero viajan en `occurrences`;
- `section_split`: las secciones > max_tokens se parten entre bloques (párrafos), nunca
  dentro de código, tablas, listas ni `<details>`;
- `merged`: además se juntan hermanas consecutivas del mismo archivo cuando alguna es
  corta (< min_tokens), hasta target_tokens;
- cada operación de los `swagger.yaml` es un chunk `openapi` con los `$ref` resueltos.

Se generan las tres estrategias en `<processed_dir>/corpus_<estrategia>.jsonl` (para
comparar en evaluate) y la configurada se copia a `<outputs_dir>/corpus.jsonl`.
`split_group` = componente conexa de chunks que comparten algún cluster: es la unidad
que el split no puede repartir entre train y eval.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from meli_docs_etl.chunk_utils import (
    Conservation,
    MergeUnit,
    block_kinds,
    check_conservation,
    merge_siblings,
    parse_blocks,
    split_text,
)
from meli_docs_etl.config import Config, display_path
from meli_docs_etl.dedup_utils import UnionFind, jaccard, shingles, tokenize
from meli_docs_etl.inventory import load_meta, split_path, version_from_urls
from meli_docs_etl.lang import detect_language
from meli_docs_etl.openapi import Operation, quality_notes, render_operations
from meli_docs_etl.stages.dedup import DEDUP_FILE, VERSIONS_FILE
from meli_docs_etl.stages.normalize import SECTIONS_FILE
from meli_docs_etl.stages.validate_threshold import near_dup_threshold
from meli_docs_etl.tokens import token_counter

log = logging.getLogger(__name__)

STRATEGIES = ("section", "section_split", "merged")
CORPUS_FILE = "corpus.jsonl"
Record = dict[str, Any]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"{path} no existe: corré antes `meli-etl dedup`.")
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def chunk_id(source_type: str, key: str, part: int, text: str) -> str:
    """Estable entre corridas; cambia solo si cambia el contenido o su origen."""
    return "ck-" + _sha1(f"{source_type}|{key}|{part}|{_sha1(text)}")[:16]


def docsify_url(base: str | None, doc_path: str) -> str | None:
    """URL publicada de la página: `<base>#/<ruta sin .md>` (README → carpeta)."""
    if not base:
        return None
    rest = doc_path.split("/", 3)[3] if doc_path.count("/") >= 3 else ""
    route = rest[: -len("README.md")] if rest.endswith("README.md") else rest.removesuffix(".md")
    return f"{base}#/{route}"


def _file_rel(path: str) -> str:
    """Ruta dentro de la versión: `guide/setup/README.md`."""
    return path.split("/", 2)[2] if path.count("/") >= 2 else path


def context_header(
    project: str, file_rel: str, path: list[str], part: int, n_parts: int, versions: list[str]
) -> str:
    line = " › ".join([project, file_rel, *path])
    if n_parts > 1:
        line += f" (part {part}/{n_parts})"
    return line + ("\nVersions: " + ", ".join(versions) if versions else "")


# --------------------------------------------------------------------------- markdown


@dataclass
class Context:
    cfg: Config
    count: Callable[[str], int]
    records: dict[str, Record]
    file_order: dict[str, list[str]]  # doc_path → section_ids conservadas, en orden
    section_url: dict[str, str | None]


def _common_prefix(paths: list[list[str]]) -> list[str]:
    out: list[str] = []
    for parts in zip(*paths, strict=False):
        if len(set(parts)) != 1:
            break
        out.append(parts[0])
    return out


def _language(langs: list[str]) -> str:
    known = sorted({lang for lang in langs if lang != "unknown"})
    if not known:
        return "unknown"
    return known[0] if len(known) == 1 else "mixed"


def _flags(text: str) -> dict[str, bool]:
    kinds = block_kinds(text)
    return {
        "has_code": "code" in kinds or "```" in text,
        "has_table": "table" in kinds,
        "has_list": "list" in kinds,
    }


def _occurrences(ctx: Context, rec: Record) -> list[dict[str, Any]]:
    return [
        {**o, "source_url": docsify_url(ctx.section_url.get(o["section_id"]), o["path"])}
        for o in rec["occurrences"]
    ]


def _markdown_chunk(
    ctx: Context, strategy: str, kind: str, recs: list[Record], text: str, part: int, n: int
) -> dict[str, Any]:
    first = recs[0]
    occ = [o for r in recs for o in _occurrences(ctx, r)]
    if len(recs) == 1:
        section_path = first["section_path"]
        ctx_path = section_path
    else:
        section_path = _common_prefix([r["section_path"][:-1] for r in recs])
        ctx_path = [*section_path, " · ".join(r["title"] for r in recs)]
    versions_eff = sorted({o["effective_version"] for o in occ})
    sids = [r["section_id"] for r in recs]
    ctx_text = (
        context_header(first["project"], _file_rel(first["path"]), ctx_path, part, n, versions_eff)
        + "\n\n"
        + text
    )
    return {
        "chunk_id": chunk_id("markdown", ",".join(sids), part, text),
        "source_type": "markdown",
        "chunk_strategy": strategy,
        "chunk_kind": kind,
        "project": first["project"],
        "section_ids": sids,
        "section_path": section_path,
        "section_titles": [r["title"] for r in recs],
        "part": part,
        "n_parts": n,
        "source_path": first["path"],
        "source_paths": sorted({o["path"] for o in occ}),
        "source_url": docsify_url(ctx.section_url.get(first["section_id"]), first["path"]),
        "version_dir": first["version_dir"],
        "declared_version": first["declared_version"],
        "effective_version": first["effective_version"],
        "versions_declared": sorted({o["declared_version"] for o in occ}),
        "versions_effective": versions_eff,
        "occurrences": occ,
        "role": first["role"],
        "variant_of": first["variant_of"],
        "variant_of_chunks": [],
        "cluster_ids": sorted({r["cluster_id"] for r in recs}),
        "split_group": None,
        "language": _language([r["language"] for r in recs]),
        **_flags(text),
        "oversize": False,
        "n_tokens": 0,
        "n_tokens_ctx": 0,
        "spec_version": None,
        "operation": None,
        "text": text,
        "contextualized_text": ctx_text,
    }


@dataclass
class MarkdownResult:
    chunks: list[dict[str, Any]]
    pieces: dict[str, list[tuple[int, int]]]
    members: list[list[tuple[str, int]]]  # por chunk: (section_id, índice de pedazo)


def build_markdown(ctx: Context, strategy: str) -> MarkdownResult:
    c = ctx.cfg.chunk
    pieces: dict[str, list[tuple[int, int]]] = {}
    for sid, rec in ctx.records.items():
        text = rec["text"]
        if strategy != "section" and ctx.count(text) > c.max_tokens:
            pieces[sid] = split_text(text, ctx.count, c.target_tokens, c.min_tokens, c.max_tokens)
        else:
            pieces[sid] = [(0, len(text))]

    chunks: list[dict[str, Any]] = []
    members: list[list[tuple[str, int]]] = []
    for doc_path in sorted(ctx.file_order):
        units, prev_was_record = [], False
        for sid in ctx.file_order[doc_path]:
            rec = ctx.records.get(sid)
            if rec is None:  # absorbida en otro lado: corta la contigüidad
                prev_was_record = False
                continue
            units.append(
                MergeUnit(
                    key=sid,
                    parent=tuple(rec["section_path"][:-1]),
                    tokens=ctx.count(rec["text"]),
                    mergeable=rec["role"] == "canonical" and len(pieces[sid]) == 1,
                    adjacent=prev_was_record,
                )
            )
            prev_was_record = True
        if strategy == "merged":
            groups = merge_siblings(units, c.min_tokens, c.target_tokens)
        else:
            groups = [[u.key] for u in units]

        for group in groups:
            recs = [ctx.records[sid] for sid in group]
            if len(group) > 1:
                text = "\n\n".join(r["text"].strip() for r in recs)
                chunks.append(_markdown_chunk(ctx, strategy, "merged", recs, text, 1, 1))
                members.append([(sid, 0) for sid in group])
                continue
            sid = group[0]
            sl = pieces[sid]
            for k, (a, b) in enumerate(sl):
                text = ctx.records[sid]["text"][a:b].strip()
                kind = "split" if len(sl) > 1 else "section"
                chunks.append(_markdown_chunk(ctx, strategy, kind, recs, text, k + 1, len(sl)))
                members.append([(sid, k)])
    return MarkdownResult(chunks, pieces, members)


# --------------------------------------------------------------------------- openapi


@dataclass
class Spec:
    path: str  # relativo a raw_dir
    project: str
    version_dir: str
    declared_version: str
    effective_version: str
    source_url: str | None
    info_version: str | None
    title: str
    operations: list[Operation]
    notes: list[str]


def load_specs(cfg: Config, versions: dict[str, Any]) -> list[Spec]:
    raw = cfg.paths.raw_dir
    meta = load_meta(raw)
    specs = []
    for f in sorted([*raw.rglob("*.yaml"), *raw.rglob("*.yml")]):
        rel = f.relative_to(raw)
        project, version_dir, _ = split_path(rel)
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or "paths" not in doc:
            continue
        urls = meta.get((project, version_dir), {})
        v = versions.get(f"{project}/{version_dir}")
        declared = v["declared_version"] if v else version_from_urls(urls, project) or version_dir
        info = doc.get("info") or {}
        specs.append(
            Spec(
                path=rel.as_posix(),
                project=project,
                version_dir=version_dir,
                declared_version=declared,
                effective_version=v["effective_version"] if v else declared,
                source_url=urls.get("specifications"),
                info_version=str(info["version"]) if "version" in info else None,
                title=str(info.get("title", "")),
                operations=render_operations(doc, cfg.chunk.openapi_max_depth),
                notes=quality_notes(doc, project),
            )
        )
    return specs


def openapi_cluster(spec: Spec, op: Operation) -> str:
    return "oa-" + _sha1(f"{spec.project}|{spec.version_dir}|{op.method} {op.path}")[:12]


def build_openapi(ctx: Context, specs: list[Spec], strategy: str) -> list[dict[str, Any]]:
    t = ctx.cfg.text
    chunks = []
    for spec in specs:
        for op in spec.operations:
            key = f"{op.method} {op.path}"
            occ = {
                "section_id": None,
                "project": spec.project,
                "version_dir": spec.version_dir,
                "declared_version": spec.declared_version,
                "effective_version": spec.effective_version,
                "path": spec.path,
                "section_path": [key],
                "match": "self",
                "jaccard": None,
                "source_url": spec.source_url,
            }
            header = context_header(
                spec.project, _file_rel(spec.path), [key], 1, 1, [spec.effective_version]
            )
            lang = detect_language(op.prose, t.lang_min_stopwords, t.lang_mixed_threshold)
            chunks.append(
                {
                    "chunk_id": chunk_id("openapi", f"{spec.path}|{key}", 1, op.text),
                    "source_type": "openapi",
                    "chunk_strategy": strategy,
                    "chunk_kind": "operation",
                    "project": spec.project,
                    "section_ids": [],
                    "section_path": [key],
                    "section_titles": [op.summary or key],
                    "part": 1,
                    "n_parts": 1,
                    "source_path": spec.path,
                    "source_paths": [spec.path],
                    "source_url": spec.source_url,
                    "version_dir": spec.version_dir,
                    "declared_version": spec.declared_version,
                    "effective_version": spec.effective_version,
                    "versions_declared": [spec.declared_version],
                    "versions_effective": [spec.effective_version],
                    "occurrences": [occ],
                    "role": "canonical",
                    "variant_of": None,
                    "variant_of_chunks": [],
                    "cluster_ids": [openapi_cluster(spec, op)],
                    "split_group": None,
                    "language": lang.label,
                    **_flags(op.text),
                    "oversize": False,
                    "n_tokens": 0,
                    "n_tokens_ctx": 0,
                    "spec_version": spec.info_version,
                    "operation": {
                        "method": op.method,
                        "path": op.path,
                        "operation_id": op.operation_id,
                    },
                    "text": op.text,
                    "contextualized_text": header + "\n\n" + op.text,
                }
            )
    return chunks


def openapi_markdown_links(
    specs: list[Spec], records: dict[str, Record], cfg: Config
) -> list[tuple[str, str, float]]:
    """Operaciones casi-duplicadas de una sección Markdown (mismo Jaccard/umbral que dedup)."""
    d, thr = cfg.dedup, near_dup_threshold(cfg)
    md = {
        r["cluster_id"]: shingles(tokenize(r["text"]), d.shingle_size)
        for r in records.values()
        if r["tokens"] >= d.near_dup_min_tokens
    }
    links = []
    for spec in specs:
        for op in spec.operations:
            sh = shingles(tokenize(op.text), d.shingle_size)
            for cid, other in md.items():
                j = jaccard(sh, other)
                if j >= thr:
                    links.append((openapi_cluster(spec, op), cid, j))
    return sorted(links)


# --------------------------------------------------------------------------- ensamblado


def assign_split_groups(
    chunks: list[dict[str, Any]], extra_links: list[tuple[str, str, float]] = ()
) -> None:
    """split_group = componente conexa del grafo chunk–cluster (union-find sobre clusters)."""
    clusters = sorted({c for ch in chunks for c in ch["cluster_ids"]})
    uf: UnionFind[str] = UnionFind(clusters)
    for ch in chunks:
        for other in ch["cluster_ids"][1:]:
            uf.union(ch["cluster_ids"][0], other)
    for a, b, _ in extra_links:
        if a in uf.parent and b in uf.parent:
            uf.union(a, b)
    group_id = {
        c: "sg-" + _sha1(",".join(sorted(group)))[:12] for group in uf.groups() for c in group
    }
    for ch in chunks:
        ch["split_group"] = group_id[ch["cluster_ids"][0]]


def finalize(chunks: list[dict[str, Any]], count: Callable[[str], int], max_tokens: int) -> None:
    for ch in chunks:
        ch["n_tokens"] = count(ch["text"])
        ch["n_tokens_ctx"] = count(ch["contextualized_text"])
        ch["oversize"] = ch["n_tokens"] > max_tokens
    by_section: dict[str, list[str]] = defaultdict(list)
    for ch in chunks:
        for sid in ch["section_ids"]:
            by_section[sid].append(ch["chunk_id"])
    for ch in chunks:
        if ch["variant_of"]:
            ch["variant_of_chunks"] = by_section.get(ch["variant_of"], [])
    chunks.sort(
        key=lambda ch: (
            (ch["source_type"], ch["source_path"], ch["section_path"], ch["part"])
            if ch["source_type"] == "openapi"
            else (ch["source_type"], ch["source_path"], ch["section_ids"][0], ch["part"])
        )
    )


@dataclass
class StrategyResult:
    strategy: str
    chunks: list[dict[str, Any]]
    markdown: MarkdownResult
    conservation: Conservation


def build_strategy(
    ctx: Context, specs: list[Spec], links: list[tuple[str, str, float]], strategy: str
) -> StrategyResult:
    md = build_markdown(ctx, strategy)
    chunks = md.chunks + build_openapi(ctx, specs, strategy)
    assign_split_groups(chunks, links)
    finalize(chunks, ctx.count, ctx.cfg.chunk.max_tokens)
    cons = check_conservation(
        {sid: r["text"] for sid, r in ctx.records.items()},
        md.pieces,
        [(ch["text"], m) for ch, m in zip(md.chunks, md.members, strict=True)],
    )
    return StrategyResult(strategy, chunks, md, cons)


def load_context(cfg: Config) -> Context:
    processed = cfg.paths.processed_dir
    records = {r["section_id"]: r for r in _read_jsonl(processed / DEDUP_FILE)}
    file_order: dict[str, list[str]] = defaultdict(list)
    section_url: dict[str, str | None] = {}
    for s in _read_jsonl(processed / SECTIONS_FILE):
        section_url[s["section_id"]] = s.get("source_url")
        if s["kept"]:
            file_order[s["doc_path"]].append(s["section_id"])
    for order in file_order.values():
        order.sort()  # section_id = <ruta>#<ordinal con ceros>: orden del archivo
    count = token_counter(cfg.chunk.tokenizer, cfg.paths.tiktoken_cache_dir)
    return Context(cfg, count, records, dict(file_order), section_url)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def run(cfg: Config) -> Path:
    if cfg.chunk.strategy not in STRATEGIES:
        raise ValueError(f"chunk.strategy debe ser una de {STRATEGIES}: {cfg.chunk.strategy!r}")
    ctx = load_context(cfg)
    versions = json.loads((cfg.paths.processed_dir / VERSIONS_FILE).read_text(encoding="utf-8"))
    specs = load_specs(cfg, versions)
    links = openapi_markdown_links(specs, ctx.records, cfg)
    log.info(
        "Chunking de %d secciones y %d operaciones OpenAPI (%d specs)",
        len(ctx.records),
        sum(len(s.operations) for s in specs),
        len(specs),
    )

    results = {s: build_strategy(ctx, specs, links, s) for s in STRATEGIES}
    for s, res in results.items():
        _write_jsonl(cfg.paths.processed_dir / f"corpus_{s}.jsonl", res.chunks)
        log.info(
            "%s: %d chunks | conservación %s",
            s,
            len(res.chunks),
            "OK" if res.conservation.ok else "FALLA",
        )
    chosen = results[cfg.chunk.strategy]
    corpus = cfg.paths.outputs_dir / CORPUS_FILE
    _write_jsonl(corpus, chosen.chunks)

    cfg.paths.reports_dir.mkdir(parents=True, exist_ok=True)
    report = cfg.paths.reports_dir / "chunk.md"
    report.write_text(render_report(ctx, specs, links, results, cfg), encoding="utf-8")
    log.info("Corpus: %s (%d chunks)", display_path(corpus), len(chosen.chunks))
    log.info("Reporte escrito en %s", display_path(report))

    failed = [s for s, r in results.items() if not r.conservation.ok]
    if failed:
        raise RuntimeError(f"Chequeo de conservación fallido en: {', '.join(failed)}")
    return corpus


# --------------------------------------------------------------------------- reporte


def _pct(values: list[int], q: float) -> int:
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))] if s else 0


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    def cell(v: Any) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    return out + ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]


def _bar(n: int, total: int, width: int = 30) -> str:
    return "█" * round(width * n / total) if total else ""


def _fence(text: str) -> str:
    """Cerca más larga que cualquier secuencia de backticks del contenido."""
    longest = max((len(m) for m in re.findall(r"`{3,}", text)), default=0)
    return "`" * max(4, longest + 1)


def _show(ch: dict[str, Any], max_lines: int = 40) -> list[str]:
    lines = ch["contextualized_text"].split("\n")
    shown = "\n".join(lines[:max_lines]) + (
        f"\n… ({len(lines) - max_lines} líneas más)" if len(lines) > max_lines else ""
    )
    fence = _fence(shown)
    return [
        f"`{ch['chunk_id']}` · {ch['chunk_kind']} · {ch['n_tokens']} tokens · "
        f"split_group `{ch['split_group']}`",
        "",
        f"{fence}markdown",
        shown,
        fence,
        "",
    ]


def _size_hist(values: list[int], cfg: Config) -> list[str]:
    c = cfg.chunk
    edges = [0, 32, c.min_tokens, 128, 192, c.target_tokens, 384, c.max_tokens, 1024, 10**9]
    rows = []
    for lo, hi in zip(edges, edges[1:], strict=False):
        n = sum(lo <= v < hi for v in values)
        label = f"[{lo}, {hi})" if hi < 10**9 else f"≥ {lo}"
        mark = {c.min_tokens: "← mín", c.target_tokens: "← objetivo", c.max_tokens: "← máx"}
        rows.append([label, n, _bar(n, len(values)) + (f" {mark[hi]}" if hi in mark else "")])
    return _table(["Tokens", "Chunks", ""], rows)


def _stats(res: StrategyResult, cfg: Config) -> list[Any]:
    sizes = [ch["n_tokens"] for ch in res.chunks]
    md = [ch for ch in res.chunks if ch["source_type"] == "markdown"]
    groups = Counter(ch["split_group"] for ch in res.chunks)
    return [
        f"`{res.strategy}`" + (" (entregable)" if res.strategy == cfg.chunk.strategy else ""),
        len(md),
        len(res.chunks) - len(md),
        len(res.chunks),
        round(statistics.mean(sizes)),
        _pct(sizes, 0.5),
        _pct(sizes, 0.9),
        max(sizes),
        sum(s < cfg.chunk.min_tokens for s in sizes),
        sum(ch["oversize"] for ch in res.chunks),
        len(groups),
        max(groups.values()),
        "✅" if res.conservation.ok else "❌",
    ]


def render_report(
    ctx: Context,
    specs: list[Spec],
    links: list[tuple[str, str, float]],
    results: dict[str, StrategyResult],
    cfg: Config,
) -> str:
    c = cfg.chunk
    res = results[c.strategy]
    chunks = res.chunks
    md = [ch for ch in chunks if ch["source_type"] == "markdown"]
    oa = [ch for ch in chunks if ch["source_type"] == "openapi"]
    recs = list(ctx.records.values())
    n_occ = sum(len(r["occurrences"]) for r in recs)
    sec_tokens = [ctx.count(r["text"]) for r in recs]
    split_secs = {sid: p for sid, p in res.markdown.pieces.items() if len(p) > 1}
    merged = [ch for ch in md if ch["chunk_kind"] == "merged"]
    n_merged_secs = sum(len(ch["section_ids"]) for ch in merged)

    out = [
        "# Chunking del corpus",
        "",
        f"Generado por `meli-etl chunk`. Estrategia del entregable: **`{c.strategy}`**; "
        f"tokenizer `{c.tokenizer}` (tiktoken); tamaños mín/objetivo/máx = "
        f"{c.min_tokens}/{c.target_tokens}/{c.max_tokens} tokens.",
        "",
        "## 1. Embudo",
        "",
    ]
    out += _table(
        ["Paso", "Cantidad", "Detalle"],
        [
            [
                "Registros de dedup",
                len(recs),
                f"{sum(r['role'] == 'canonical' for r in recs)} canónicas + "
                f"{sum(r['role'] == 'variant' for r in recs)} variantes; cubren {n_occ} "
                "secciones (las absorbidas viajan en `occurrences`)",
            ],
            [
                "Secciones partidas",
                len(split_secs),
                f"→ {sum(len(p) for p in split_secs.values())} pedazos",
            ],
            [
                "Secciones fusionadas",
                n_merged_secs,
                f"→ {len(merged)} chunks (hermanas consecutivas del mismo archivo)",
            ],
            ["Chunks Markdown", len(md), ""],
            [
                "Chunks OpenAPI",
                len(oa),
                f"{len(specs)} specs: "
                + ", ".join(f"{s.project} ({len(s.operations)})" for s in specs),
            ],
            [
                "**Total**",
                f"**{len(chunks)}**",
                f"`{display_path(cfg.paths.outputs_dir)}/corpus.jsonl`",
            ],
        ],
    )

    # 2. Tamaños
    below = {
        t: sum(v < t for v in sec_tokens) / len(sec_tokens)
        for t in (c.min_tokens, c.target_tokens, c.max_tokens)
    }
    out += [
        "",
        "## 2. Tamaños",
        "",
        f"**Secciones de entrada** (n = {len(sec_tokens)}): p10 {_pct(sec_tokens, 0.1)} · "
        f"p25 {_pct(sec_tokens, 0.25)} · p50 {_pct(sec_tokens, 0.5)} · p75 "
        f"{_pct(sec_tokens, 0.75)} · p90 {_pct(sec_tokens, 0.9)} · p95 {_pct(sec_tokens, 0.95)} · "
        f"máx {max(sec_tokens)} tokens.",
        "",
        f"- **mín = {c.min_tokens}** (el {below[c.min_tokens]:.0%} de las secciones está por "
        "debajo): son fragmentos —un endpoint de una línea, una alerta corta— que conviene "
        "juntar con sus hermanas.",
        f"- **objetivo = {c.target_tokens}** ({below[c.target_tokens]:.0%} por debajo): se "
        "fusiona hasta el tamaño de una sección típica, sin inflar.",
        f"- **máx = {c.max_tokens}** ({below[c.max_tokens]:.0%} por debajo): solo se parten "
        "las secciones realmente largas; coincide con la ventana usual de modelos de "
        "embeddings (e5/BGE base).",
        "",
        f"**Chunks del entregable** (`{c.strategy}`, n = {len(chunks)}):",
        "",
    ]
    out += _size_hist([ch["n_tokens"] for ch in chunks], cfg)

    # 3. Fusiones y particiones
    out += ["", "## 3. Fusiones, particiones y chunks fuera de rango", ""]
    by_size = Counter(len(ch["section_ids"]) for ch in merged)
    out.append(
        "**Fusiones:** "
        + (
            ", ".join(f"{n} chunks de {k} secciones" for k, n in sorted(by_size.items()))
            if by_size
            else "ninguna"
        )
        + "."
    )
    out += ["", "**Secciones partidas** (cortes solo entre párrafos/bloques):", ""]
    out += (
        _table(
            ["Sección", "Tokens", "Pedazos", "Tokens por pedazo"],
            [
                [
                    sid,
                    ctx.count(ctx.records[sid]["text"]),
                    len(p),
                    ", ".join(str(ch["n_tokens"]) for ch in md if ch["section_ids"] == [sid]),
                ]
                for sid, p in sorted(split_secs.items())
            ],
        )
        if split_secs
        else ["Ninguna."]
    )
    over = [ch for ch in chunks if ch["oversize"]]
    out += [
        "",
        f"**Chunks oversize** (> {c.max_tokens} tokens por un bloque que no se puede partir): "
        f"{len(over)}.",
        "",
    ]
    out += (
        _table(
            ["Chunk", "Tokens", "Origen", "Bloque más grande"],
            [
                [
                    ch["chunk_id"],
                    ch["n_tokens"],
                    ch["section_ids"][0] if ch["section_ids"] else ch["section_path"][0],
                    _largest_block(ch["text"], ctx.count),
                ]
                for ch in over
            ],
        )
        if over
        else ["Ninguno."]
    )
    small = [ch for ch in md if ch["n_tokens"] < c.min_tokens]
    out += [
        "",
        f"**Chunks bajo el mínimo:** {len(small)} de {len(md)} Markdown. No tienen una hermana "
        "contigua del mismo archivo con la que sumar sin pasar el objetivo (archivos de una "
        "sola sección, hijas únicas o vecinas absorbidas en otra versión); juntarlos con algo "
        f"que no es hermano mezclaría temas. Variantes que quedan solas: "
        f"{sum(ch['role'] == 'variant' for ch in small)}.",
    ]

    # 4. Clusters
    groups = Counter(ch["split_group"] for ch in chunks)
    biggest, size = max(sorted(groups.items()), key=lambda x: x[1])
    big = [ch for ch in chunks if ch["split_group"] == biggest]
    multi = [ch for ch in chunks if len(ch["cluster_ids"]) > 1]
    group_sizes = Counter(groups.values())
    out += [
        "",
        "## 4. Clusters y split_group",
        "",
        "`split_group` = componente conexa del grafo chunk–cluster: dos chunks están en el "
        "mismo grupo si comparten un cluster (directa o transitivamente). Así una canónica y "
        "su variante (en archivos distintos) y los clusters unidos por una fusión quedan "
        "juntos, y `split` puede repartir grupos enteros sin que un cluster quede en train y "
        "eval a la vez. Los must-link humanos ya están dentro de los clusters de dedup.",
        "",
        f"- **split_groups:** {len(groups)} para {len(chunks)} chunks. Tamaños: "
        + ", ".join(f"{n} de {k}" for k, n in sorted(group_sizes.items()))
        + ".",
        f"- **Más grande:** `{biggest}` con {size} chunks, "
        f"{len({cid for ch in big for cid in ch['cluster_ids']})} clusters, proyecto(s) "
        + ", ".join(sorted({ch["project"] for ch in big}))
        + f", {sum(ch['n_tokens'] for ch in big)} tokens.",
        f"- **Chunks con varios clusters** (por fusión): {len(multi)}.",
        f"- **Uniones OpenAPI ↔ Markdown** (Jaccard ≥ {near_dup_threshold(cfg)}): "
        + (
            ", ".join(f"`{a}` ↔ `{b}` ({j:.2f})" for a, b, j in links)
            if links
            else "ninguna; las specs no repiten la guía, cada operación es su propio grupo"
        )
        + ".",
    ]
    out += ["", "**Chunks del grupo más grande:**", ""]
    out += _table(
        ["Chunk", "Tipo", "Rol", "Secciones", "Clusters"],
        [
            [
                ch["chunk_id"],
                ch["chunk_kind"],
                ch["role"],
                ", ".join(ch["section_ids"]) or ch["section_path"][0],
                ", ".join(ch["cluster_ids"]),
            ]
            for ch in big
        ],
    )

    # 5. Ejemplos
    out += ["", "## 5. Ejemplos", "", "Se muestra `contextualized_text` (encabezado + `text`).", ""]
    small_ex = min(md, key=lambda ch: (ch["n_tokens"], ch["chunk_id"]))
    out += ["### Chunk chico", "", *_show(small_ex)]
    if merged:
        ex = max(merged, key=lambda ch: (len(ch["section_ids"]), -ch["n_tokens"], ch["chunk_id"]))
        out += ["### Chunk fusionado", "", *_show(ex)]
    if split_secs:
        # La sección partida en menos pedazos y más tokens: muestra el corte entero.
        sid = min(
            sorted(split_secs),
            key=lambda s: (len(split_secs[s]), -ctx.count(ctx.records[s]["text"])),
        )
        parts = [ch for ch in md if ch["section_ids"] == [sid]]
        out += [f"### Sección partida: `{sid}` ({len(parts)} pedazos)", ""]
        for ch in parts:
            out += _show(ch, max_lines=20)
    if oa:
        ex = sorted(oa, key=lambda ch: (ch["n_tokens"], ch["chunk_id"]))[len(oa) // 2]
        out += ["### Operación OpenAPI", "", *_show(ex, max_lines=60)]

    # 6. Conservación
    out += [
        "",
        "## 6. Chequeo de conservación",
        "",
        "Todo el contenido de las secciones canónicas y variantes aparece en exactamente un "
        "chunk: (a) los pedazos de cada sección son slices contiguos que la cubren entera; "
        "(b) cada pedazo está asignado a un solo chunk y aparece literal en su texto; (c) el "
        "multiconjunto de líneas no vacías de las secciones es igual al de los chunks "
        "Markdown (ni pérdidas ni duplicados).",
        "",
    ]
    out += _table(
        [
            "Estrategia",
            "Secciones",
            "Pedazos",
            "Sin cubrir",
            "Sin chunk",
            "Duplicados",
            "No literal",
            "Líneas faltantes",
            "Líneas sobrantes",
            "Resultado",
        ],
        [
            [
                f"`{s}`",
                r.conservation.n_sections,
                r.conservation.n_pieces,
                len(r.conservation.gaps),
                len(r.conservation.unassigned),
                len(r.conservation.duplicated),
                len(r.conservation.not_verbatim),
                r.conservation.lines_missing,
                r.conservation.lines_extra,
                "✅" if r.conservation.ok else "❌",
            ]
            for s, r in results.items()
        ],
    )
    for s, r in results.items():
        probs = r.conservation.gaps + r.conservation.unassigned + r.conservation.duplicated
        if probs:
            out += ["", f"Problemas en `{s}`: " + ", ".join(probs[:20])]

    # 7. Estrategias
    out += [
        "",
        "## 7. Comparación de estrategias",
        "",
        "Las tres se escriben en `data/processed/corpus_<estrategia>.jsonl` para compararlas en "
        "`evaluate`; la del entregable se configura con `chunk.strategy`.",
        "",
    ]
    out += _table(
        [
            "Estrategia",
            "Markdown",
            "OpenAPI",
            "Total",
            "Media",
            "p50",
            "p90",
            "Máx",
            f"< {c.min_tokens}",
            "Oversize",
            "split_groups",
            "Grupo más grande",
            "Conservación",
        ],
        [_stats(r, cfg) for r in results.values()],
    )

    # 8. Specs
    out += ["", "## 8. Specs OpenAPI", ""]
    out += _table(
        [
            "Spec",
            "Título",
            "info.version",
            "Versión declarada",
            "Versión efectiva",
            "Operaciones",
            "$ref sin resolver",
        ],
        [
            [
                s.path,
                s.title,
                s.info_version or "—",
                s.declared_version,
                s.effective_version,
                len(s.operations),
                ", ".join(sorted({m for op in s.operations for m in op.missing_refs})) or "ninguna",
            ]
            for s in specs
        ],
    )
    notes = [(s.path, n) for s in specs for n in s.notes]
    out += ["", "**Inconsistencias en las specs** (se reportan, no se corrigen):", ""]
    out += [f"- `{p}`: {n}" for p, n in notes] or ["- Ninguna."]

    out += [
        "",
        "## Salidas",
        "",
        "- `outputs/corpus.jsonl`: entregable (esquema en el README).",
        "- `data/processed/corpus_<estrategia>.jsonl`: las tres estrategias.",
        "",
    ]
    return "\n".join(out)


def _largest_block(text: str, count: Callable[[str], int]) -> str:
    blocks = parse_blocks(text)
    b = max(blocks, key=lambda b: count(text[b.start : b.end]))
    first = text[b.start : b.end].strip().split("\n", 1)[0].strip("`# ")[:40]
    return f"{b.kind} de {count(text[b.start : b.end])} tokens" + (f" ({first})" if first else "")
