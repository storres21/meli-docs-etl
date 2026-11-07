.PHONY: help setup all pipeline profile normalize dedup chunk split qa evaluate test lint clean

CONFIG ?= configs/default.yaml
RUN = uv run meli-etl

help:  ## Lista los comandos disponibles
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup:  ## Crea el entorno (.venv) desde uv.lock
	uv sync

all: setup pipeline test  ## Setup + etapas implementadas + tests

pipeline: profile normalize dedup  ## Etapas implementadas, en orden

profile:  ## Etapa 1: reports/profile.md + inventory.jsonl
	$(RUN) profile --config $(CONFIG)

normalize:  ## Etapa 2: normaliza, parte en secciones y filtra
	$(RUN) normalize --config $(CONFIG)

dedup:  ## Etapa 3: dedup de secciones → reports/dedup.md
	$(RUN) dedup --config $(CONFIG)

chunk:  ## Etapa 4 (pendiente)
	$(RUN) chunk --config $(CONFIG)

split:  ## Etapa 5 (pendiente)
	$(RUN) split --config $(CONFIG)

qa:  ## Etapa 6 (pendiente)
	$(RUN) qa --config $(CONFIG)

evaluate:  ## Etapa 7 (pendiente)
	$(RUN) evaluate --config $(CONFIG)

test:  ## Corre pytest
	uv run pytest

lint:  ## Ruff
	uv run ruff check src tests

clean:  ## Borra intermedios y logs (no toca data/raw, data/cache, outputs/*.jsonl ni reports/)
	rm -rf data/processed/* outputs/logs .pytest_cache .ruff_cache
	touch data/processed/.gitkeep
