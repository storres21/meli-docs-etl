.PHONY: help setup all pipeline profile normalize dedup label-pairs validate-threshold chunk split-rebuild split qa qa-record label-qa evaluate test lint clean

CONFIG ?= configs/default.yaml
RUN = uv run meli-etl

help:  ## Lista los comandos disponibles
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-19s %s\n", $$1, $$2}'

setup:  ## Crea el entorno (.venv) desde uv.lock
	uv sync

all: setup pipeline test  ## Setup + etapas implementadas + tests

pipeline: profile normalize dedup chunk split qa evaluate  ## Etapas, en orden (qa en replay: sin red)

profile:  ## Etapa 1: reports/profile.md + inventory.jsonl
	$(RUN) profile --config $(CONFIG)

normalize:  ## Etapa 2: normaliza, parte en secciones y filtra
	$(RUN) normalize --config $(CONFIG)

dedup:  ## Etapa 3: dedup de secciones → reports/dedup.md
	$(RUN) dedup --config $(CONFIG)

label-pairs:  ## Exporta pares casi-dup para etiquetar (no pisa etiquetas)
	$(RUN) label-pairs --config $(CONFIG)

validate-threshold: dedup  ## Aplica must-link (dedup) y valida el umbral → dedup.md §8
	$(RUN) validate-threshold --config $(CONFIG)

chunk:  ## Etapa 4: chunks + OpenAPI → outputs/corpus.jsonl + reports/chunk.md
	$(RUN) chunk --config $(CONFIG)

split:  ## Etapa 5: train/eval_section/eval_project desde el manifiesto → reports/split.md
	$(RUN) split --config $(CONFIG)

split-rebuild:  ## Recalcula el split desde cero (conjunto de eval nuevo; ver README)
	$(RUN) split --rebuild --config $(CONFIG)

qa:  ## Etapa 6: Q&A desde la cache del LLM (sin red) → outputs/qa.jsonl + reports/qa.md
	$(RUN) qa --config $(CONFIG)

qa-record:  ## Etapa 6 grabando en la cache lo que falte (requiere el proveedor; reanudable)
	$(RUN) qa --cache-mode record --config $(CONFIG)

label-qa:  ## Exporta muestra para revisión humana del juez (no pisa etiquetas)
	$(RUN) label-qa --config $(CONFIG)

evaluate:  ## Etapa 7: BM25 Recall@k/MRR por estrategia → reports/evaluate.md
	$(RUN) evaluate --config $(CONFIG)

test:  ## Corre pytest
	uv run pytest

lint:  ## Ruff
	uv run ruff check src tests

clean:  ## Borra intermedios y logs (no toca data/raw, data/cache, outputs/*.jsonl ni reports/)
	rm -rf data/processed/* outputs/logs .pytest_cache .ruff_cache
	touch data/processed/.gitkeep
