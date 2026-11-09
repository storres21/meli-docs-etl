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
    tiktoken_cache_dir: Path
    splits_dir: Path
    prompts_dir: Path


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
    # Número fijo, o "auto": etiquetas humanas → valle de Jaccard → threshold_fallback.
    near_dup_threshold: float | str = "auto"
    threshold_fallback: float = 0.6
    # El valle se busca dentro de este rango; solo cuenta si mide ≥ min_valley_width.
    threshold_bounds: tuple[float, float] = (0.3, 0.9)
    min_valley_width: float = 0.1
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
class ChunkConfig:
    # merged | section_split | section (ver stages/chunk.py)
    strategy: str = "merged"
    tokenizer: str = "o200k_base"
    min_tokens: int = 64
    target_tokens: int = 256
    max_tokens: int = 512
    # Profundidad máxima al aplanar esquemas OpenAPI anidados.
    openapi_max_depth: int = 4


@dataclass(frozen=True)
class SplitConfig:
    # Proyecto retenido entero en eval_project (lo elige una persona; sin default).
    eval_project: str | None = None
    # Fracción de tokens de cada estrato (proyecto × source_type) que va a eval_section.
    eval_section_fraction: float = 0.175
    # Un grupo no entra a eval_section si deja al estrato por encima de fracción + tolerancia.
    tolerance: float = 0.05
    # Estratos con menos grupos que esto quedan enteros en train.
    min_groups_per_stratum: int = 4
    # Pares de fichas en splits distintos con Jaccard ≥ esto se reportan como fuga sutil.
    audit_jaccard_min: float = 0.3


@dataclass(frozen=True)
class LLMConfig:
    # ollama | anthropic | openai (API keys por variable de entorno, nunca en la config).
    provider: str = "ollama"
    # None = URL por defecto del proveedor.
    base_url: str | None = None
    generator_model: str = "qwen2.5:7b"
    judge_model: str = "llama3.1:8b"
    temperature: float = 0.0
    max_tokens: int = 1024
    # Ventana de contexto (solo Ollama).
    num_ctx: int = 8192
    timeout_s: int = 600
    # replay | record | off (ver llm.py).
    cache_mode: str = "replay"


@dataclass(frozen=True)
class QAConfig:
    prompt_version: str = "v1"
    # Fichas con menos tokens no generan preguntas.
    min_tokens: int = 32
    # 2 preguntas LLM si la ficha supera esto; si no, 1.
    two_questions_min_tokens: int = 400
    # Preguntas LLM por ficha en eval_section / eval_project (train usa la regla de arriba).
    eval_questions_per_chunk: int = 3
    # Fracción de fichas con una pregunta sin respuesta.
    unanswerable_ratio: float = 0.2
    # Idioma si ni la ficha ni su proyecto tienen es/en.
    default_language: str = "en"
    min_question_words: int = 5
    short_answer_max_words: int = 8
    near_dup_jaccard: float = 0.8
    judge_min_score: int = 3
    neighbors: int = 3
    neighbor_max_chars: int = 1500
    human_sample_size: int = 30


@dataclass(frozen=True)
class EvaluateConfig:
    # BM25 Okapi.
    k1: float = 1.5
    b: float = 0.75
    # Cortes de Recall@k (el último también define "fallo" en los ejemplos del reporte).
    ks: tuple[int, ...] = (1, 5, 10)
    n_failure_examples: int = 5


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
    chunk: ChunkConfig = field(default_factory=ChunkConfig)
    split: SplitConfig = field(default_factory=SplitConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    qa: QAConfig = field(default_factory=QAConfig)
    evaluate: EvaluateConfig = field(default_factory=EvaluateConfig)


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
        chunk=section(ChunkConfig, "chunk"),
        split=section(SplitConfig, "split"),
        llm=section(LLMConfig, "llm"),
        qa=section(QAConfig, "qa"),
        evaluate=section(EvaluateConfig, "evaluate"),
    )
