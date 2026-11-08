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
    """(pendiente) Chunking por secciones → corpus.jsonl con procedencia."""
    _not_implemented("chunk", config, log_level)


@app.command()
def split(config: ConfigOpt = None, log_level: LevelOpt = None) -> None:
    """(pendiente) Split train/eval por cluster de duplicados (sin leakage)."""
    _not_implemented("split", config, log_level)


@app.command()
def qa(config: ConfigOpt = None, log_level: LevelOpt = None) -> None:
    """(pendiente) Genera qa.jsonl y datos para RL/DPO."""
    _not_implemented("qa", config, log_level)


@app.command()
def evaluate(config: ConfigOpt = None, log_level: LevelOpt = None) -> None:
    """(pendiente) Reporte de calidad + Recall@k/MRR con BM25."""
    _not_implemented("evaluate", config, log_level)


if __name__ == "__main__":
    app()
