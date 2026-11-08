"""Carga de configuración YAML a dataclasses tipadas."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

import yaml


def find_project_root(start: Path | None = None) -> Path:
    """Sube desde `start` hasta encontrar pyproject.toml; si no, usa el cwd."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd().resolve()


def display_path(p: Path) -> str:
    """Ruta relativa a la raíz del proyecto (para logs y reportes deterministas)."""
    try:
        return p.relative_to(find_project_root()).as_posix()
    except ValueError:
        return p.as_posix()


T = TypeVar("T")

DEFAULT_CONFIG = find_project_root(Path(__file__).parent) / "configs" / "default.yaml"


@dataclass(frozen=True)
class Paths:
    raw_dir: Path
    processed_dir: Path
    outputs_dir: Path
    reports_dir: Path
    logs_dir: Path
    llm_cache_dir: Path
    labels_dir: Path


@dataclass(frozen=True)
class FilesConfig:
    # Navegación docsify: fuera del corpus, se guarda como metadata.
    nav_filenames: tuple[str, ...] = ("_sidebar.md", "_coverpage.md", "_navbar.md")


@dataclass(frozen=True)
class TextConfig:
    todo_patterns: tuple[str, ...] = (r"to\s*-?\s*do", "tbd", "wip")
    lang_min_stopwords: int = 3
    lang_mixed_threshold: float = 0.7


@dataclass(frozen=True)
class ProfileConfig:
    stub_max_words: int = 15


@dataclass(frozen=True)
class NormalizeConfig:
    stub_min_tokens: int = 8


@dataclass(frozen=True)
class DedupConfig:
    shingle_size: int = 5
    num_perm: int = 128
    near_dup_threshold: float = 0.6
    lsh_threshold: float = 0.45
    near_dup_min_tokens: int = 20
    n_diff_examples: int = 5


@dataclass(frozen=True)
class LabelsConfig:
    # Pares con Jaccard ≥ esto se exportan para etiquetado humano.
    review_min_jaccard: float = 0.1
    # Grilla de umbrales evaluada por validate-threshold.
    grid_start: float = 0.1
    grid_stop: float = 0.9
    grid_step: float = 0.05
    # True: recomienda el umbral más alto con recall máximo; False: el de mejor F1.
    recall_priority: bool = True
    # Con menos pares `same` que esto, la §8 avisa que la recomendación es frágil.
    min_same_pairs: int = 10


@dataclass(frozen=True)
class Config:
    seed: int
    paths: Paths
    log_level: str = "INFO"
    files: FilesConfig = field(default_factory=FilesConfig)
    text: TextConfig = field(default_factory=TextConfig)
    profile: ProfileConfig = field(default_factory=ProfileConfig)
    normalize: NormalizeConfig = field(default_factory=NormalizeConfig)
    dedup: DedupConfig = field(default_factory=DedupConfig)
    labels: LabelsConfig = field(default_factory=LabelsConfig)


def _resolve(base: Path, value: str) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (base / p).resolve()


def load_config(path: Path | None = None, overrides: dict[str, Any] | None = None) -> Config:
    """Lee el YAML y resuelve rutas relativas contra la raíz del proyecto.

    `overrides` permite pisar claves de `paths` (útil en tests y CLI).
    """
    config_path = Path(path) if path else DEFAULT_CONFIG
    with open(config_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    base = find_project_root(config_path.parent)
    raw_paths = {**raw.get("paths", {}), **(overrides or {})}
    paths = Paths(**{k: _resolve(base, str(v)) for k, v in raw_paths.items()})

    def section(cls: type[T], name: str) -> T:
        values = raw.get(name) or {}
        return cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in values.items()})

    return Config(
        seed=int(raw.get("seed", 42)),
        paths=paths,
        log_level=str(raw.get("logging", {}).get("level", "INFO")),
        files=section(FilesConfig, "files"),
        text=section(TextConfig, "text"),
        profile=section(ProfileConfig, "profile"),
        normalize=section(NormalizeConfig, "normalize"),
        dedup=section(DedupConfig, "dedup"),
        labels=section(LabelsConfig, "labels"),
    )
