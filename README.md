# meli-docs-etl

Pipeline local y reproducible que transforma documentación Markdown cruda de 10 proyectos
de software en datos para LLMs: corpus para retrieval/CPT, pares Q&A para SFT/evaluación,
datos para RL y métricas de calidad/retrieval.

## Quickstart

Requisitos: Python ≥ 3.10 y [uv](https://docs.astral.sh/uv/).

```bash
make all
```

Esto crea el entorno desde `uv.lock`, corre las etapas implementadas y ejecuta los tests.
Sin `make`:

```bash
uv sync
uv run meli-etl profile
uv run pytest
```

Resultado: `reports/profile.md` y `data/processed/inventory.jsonl`.

## Estructura

```
configs/            configuración (rutas, semilla, umbrales)
data/raw/docs_raw/  input crudo (versionado)
data/processed/     salidas intermedias (ignoradas por git)
data/cache/llm/     cache de respuestas del LLM (versionada → qa reproducible sin API key)
outputs/            datasets finales: corpus.jsonl, qa.jsonl, ... (versionados)
outputs/logs/       logs por etapa (ignorados por git)
reports/            reportes legibles (profile.md, ...)
src/meli_docs_etl/  paquete
tests/              tests + fixtures sintéticos
```

## Configuración

Todo sale de `configs/default.yaml`; nada está hardcodeado. Las rutas relativas se resuelven
contra la raíz del proyecto. Se puede usar otra config con `--config` (o `make profile CONFIG=...`).
La semilla (`seed`) se fija al inicio de cada etapa y los logs quedan en `outputs/logs/<etapa>.log`.

## Etapas

| Etapa | Comando | Estado | Salida |
|---|---|---|---|
| profile | `meli-etl profile` | ✅ | `reports/profile.md`, `inventory.jsonl` |
| normalize | `meli-etl normalize` | ⏳ | _TBD_ |
| dedup | `meli-etl dedup` | ⏳ | _TBD_ |
| chunk | `meli-etl chunk` | ⏳ | `corpus.jsonl` |
| split | `meli-etl split` | ⏳ | _TBD_ |
| qa | `meli-etl qa` | ⏳ | `qa.jsonl`, datos RL/DPO |
| evaluate | `meli-etl evaluate` | ⏳ | métricas Recall@k / MRR |

## Hallazgos del perfilado

_TBD: resumen de `reports/profile.md`._

## Decisiones de diseño

_TBD._

## Esquemas de salida

_TBD: `corpus.jsonl`, `qa.jsonl`._

## Evaluación

_TBD._

## Limitaciones y trabajo futuro

_TBD._
