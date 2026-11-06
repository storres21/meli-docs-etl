"""Carga de configuración YAML a dataclasses tipadas."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def find_project_root(start: Path | None = None) -> Path:
    """Sube desde `start` hasta encontrar pyproject.toml; si no, usa el cwd."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd().resolve()


DEFAULT_CONFIG = find_project_root(Path(__file__).parent) / "configs" / "default.yaml"


@dataclass(frozen=True)
class Paths:
    raw_dir: Path
    processed_dir: Path
    outputs_dir: Path
    reports_dir: Path
    logs_dir: Path
    llm_cache_dir: Path


@dataclass(frozen=True)
class ProfileConfig:
    nav_filenames: tuple[str, ...] = ("_sidebar.md", "_coverpage.md", "_navbar.md")
    stub_max_words: int = 15
    todo_patterns: tuple[str, ...] = (r"to\s*-?\s*do", "tbd", "wip")
    lang_min_stopwords: int = 3
    lang_mixed_threshold: float = 0.7


@dataclass(frozen=True)
class Config:
    seed: int
    paths: Paths
    log_level: str = "INFO"
    profile: ProfileConfig = field(default_factory=ProfileConfig)


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

    prof = raw.get("profile", {})
    profile = ProfileConfig(**{k: tuple(v) if isinstance(v, list) else v for k, v in prof.items()})
    return Config(
        seed=int(raw.get("seed", 42)),
        paths=paths,
        log_level=str(raw.get("logging", {}).get("level", "INFO")),
        profile=profile,
    )
