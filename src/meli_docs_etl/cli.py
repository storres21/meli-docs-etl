"""CLI `meli-etl`: un subcomando por etapa del pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from meli_docs_etl.config import Config, load_config
from meli_docs_etl.logging_utils import setup_logging
from meli_docs_etl.seed import set_seed

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)
log = logging.getLogger("meli_docs_etl")

ConfigOpt = Annotated[
    Path | None,
    typer.Option("--config", "-c", help="YAML de configuración (default: configs/default.yaml)."),
]
LevelOpt = Annotated[
    str | None,
    typer.Option("--log-level", help="Pisa logging.level de la config."),
]


def _bootstrap(stage: str, config: Path | None, log_level: str | None) -> Config:
    cfg = load_config(config)
    setup_logging(log_level or cfg.log_level, cfg.paths.logs_dir / f"{stage}.log")
    set_seed(cfg.seed)
    log.info("Etapa '%s' | seed=%d | raw_dir=%s", stage, cfg.seed, cfg.paths.raw_dir)
    return cfg


def _not_implemented(stage: str, config: Path | None, log_level: str | None) -> None:
    _bootstrap(stage, config, log_level)
    log.error("La etapa '%s' todavía no está implementada.", stage)
    raise typer.Exit(code=2)


@app.command()
def profile(config: ConfigOpt = None, log_level: LevelOpt = None) -> None:
    """Perfila docs_raw → reports/profile.md + inventory.jsonl."""
    from meli_docs_etl.stages import profile as stage

    stage.run(_bootstrap("profile", config, log_level))


@app.command()
def normalize(config: ConfigOpt = None, log_level: LevelOpt = None) -> None:
    """Normaliza Markdown, parte en secciones y filtra (nav, stubs, TO DO)."""
    from meli_docs_etl.stages import normalize as stage

    stage.run(_bootstrap("normalize", config, log_level))


@app.command()
def dedup(config: ConfigOpt = None, log_level: LevelOpt = None) -> None:
    """Dedup de secciones (exacto + MinHash) → sections_dedup.jsonl + reports/dedup.md."""
    from meli_docs_etl.stages import dedup as stage

    stage.run(_bootstrap("dedup", config, log_level))


@app.command("label-pairs")
def label_pairs(config: ConfigOpt = None, log_level: LevelOpt = None) -> None:
    """Exporta pares casi-duplicados para etiquetar → data/labels/ (review.md + labels.csv)."""
    from meli_docs_etl.stages import label_pairs as stage

    stage.run(_bootstrap("label-pairs", config, log_level))


@app.command("validate-threshold")
def validate_threshold(config: ConfigOpt = None, log_level: LevelOpt = None) -> None:
    """Valida el umbral de casi-duplicados con las etiquetas → reports/dedup.md §8."""
    from meli_docs_etl.stages import validate_threshold as stage

    cfg = _bootstrap("validate-threshold", config, log_level)
    try:
        stage.run(cfg)
    except (FileNotFoundError, ValueError) as exc:
        log.error("%s", exc)
        raise typer.Exit(code=2) from exc


@app.command()
def chunk(config: ConfigOpt = None, log_level: LevelOpt = None) -> None:
    """Chunking (secciones + OpenAPI) → outputs/corpus.jsonl + reports/chunk.md."""
    from meli_docs_etl.stages import chunk as stage

    cfg = _bootstrap("chunk", config, log_level)
    try:
        stage.run(cfg)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        log.error("%s", exc)
        raise typer.Exit(code=1) from exc


@app.command()
def split(
    config: ConfigOpt = None,
    log_level: LevelOpt = None,
    rebuild: Annotated[
        bool,
        typer.Option(
            "--rebuild",
            help="Recalcula el split desde cero (ignora el manifiesto): genera un conjunto de "
            "eval nuevo. Necesario si cambian seed o parámetros de `split:`.",
        ),
    ] = False,
) -> None:
    """Split train / eval_section / eval_project por split_group → corpus.jsonl + manifiesto."""
    from meli_docs_etl.stages import split as stage

    cfg = _bootstrap("split", config, log_level)
    try:
        stage.run(cfg, rebuild=rebuild)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        log.error("%s", exc)
        raise typer.Exit(code=1) from exc


@app.command()
def qa(
    config: ConfigOpt = None,
    log_level: LevelOpt = None,
    cache_mode: Annotated[
        str | None,
        typer.Option(
            "--cache-mode",
            help="Pisa llm.cache_mode: replay (solo cache, default), record (llama al "
            "proveedor ante un miss y guarda; reanudable) u off.",
        ),
    ] = None,
) -> None:
    """Q&A anclado a fichas (LLM + OpenAPI + sin respuesta) → outputs/qa.jsonl + reports/qa.md."""
    import dataclasses

    from meli_docs_etl.llm import LLMError
    from meli_docs_etl.stages import qa as stage

    cfg = _bootstrap("qa", config, log_level)
    if cache_mode:
        cfg = dataclasses.replace(cfg, llm=dataclasses.replace(cfg.llm, cache_mode=cache_mode))
    try:
        stage.run(cfg)
    except (FileNotFoundError, ValueError, RuntimeError, LLMError) as exc:
        log.error("%s", exc)
        raise typer.Exit(code=1) from exc


@app.command("label-qa")
def label_qa(config: ConfigOpt = None, log_level: LevelOpt = None) -> None:
    """Exporta una muestra de preguntas juzgadas para revisión humana → data/labels/."""
    from meli_docs_etl.stages import label_qa as stage

    cfg = _bootstrap("label-qa", config, log_level)
    try:
        stage.run(cfg)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        raise typer.Exit(code=2) from exc


@app.command()
def evaluate(config: ConfigOpt = None, log_level: LevelOpt = None) -> None:
    """(pendiente) Reporte de calidad + Recall@k/MRR con BM25."""
    _not_implemented("evaluate", config, log_level)


if __name__ == "__main__":
    app()
