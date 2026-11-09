# meli-docs-etl

Por favor encuentre la presentación que detalla el proceso de pensamiento detrás del proyecto [aquí](https://docs.google.com/presentation/d/1pn-H6Wov8zlbdAgt9mzNG0G92i02XVV3FwV0xqV441U/edit?usp=sharing)

Pipeline local, determinista y reproducible que convierte la documentación Markdown cruda de
10 proyectos de software (`data/raw/docs_raw/<proyecto>/<versión>/…`) en datos para entrenar y
evaluar LLMs.

**Entregables** (versionados en `outputs/`):

1. **`outputs/corpus.jsonl`**: 235 fichas (chunks) deduplicadas, con procedencia completa y
   asignadas a `train`, `eval_section` o `eval_project` sin fuga entre splits. Sirve para
   retrieval/RAG y para pre-entrenamiento continuo (CPT).
2. **`outputs/qa.jsonl`**: 239 preguntas ancladas a fichas, con evidencia literal y el split
   de su ficha. Sirve para SFT, evaluación y RL con recompensa verificable. Hay tres tipos:
   generadas por LLM, deterministas desde OpenAPI, y sin respuesta.

Además, `evaluate` mide el retrieval con BM25 sobre las tres estrategias de chunking y la
calidad del dataset Q&A (`reports/evaluate.md`). `reports/experiment_plan.md` diseña el
experimento de fine-tuning.

## Instalación desde cero

**Requisitos:**

- `git`;
- [`uv`](https://docs.astral.sh/uv/), que también instala Python ≥ 3.10 si hace falta;
- `make`, opcional: cada target tiene su equivalente `uv run`.

**No hace falta un LLM ni red para correr el pipeline.** La etapa `qa` corre por defecto en
modo *replay*: lee las respuestas del LLM de la caché versionada en `data/cache/llm/`. Ollama
solo es necesario para **regenerar** las preguntas (ver más abajo).

```bash
# 1. Instalar uv (y make/git si faltan)
# macOS:          brew install uv        (make y git: xcode-select --install)
# Linux:          curl -LsSf https://astral.sh/uv/install.sh | sh ; sudo apt-get install -y make git
# Windows (PS):   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Clonar e instalar dependencias (versiones exactas de uv.lock, incluye pytest y ruff)
git clone https://github.com/storres21/meli-docs-etl.git
cd meli-docs-etl
uv sync
```

No hace falta activar el entorno: todo se corre con `uv run …` o `make …`.
`make help` lista los targets y `uv run meli-etl --help` lista los comandos.

## Cómo correr

```bash
make all     # uv sync + todas las etapas en orden + tests (unos segundos, sin red, 0 llamadas al LLM)
make test    # solo los tests (uv run pytest)
make lint    # ruff
```

Cada etapa por separado, en este orden (cada una lee la salida de la anterior):

```bash
make profile     # o: uv run meli-etl profile
make normalize   # o: uv run meli-etl normalize
make dedup       # o: uv run meli-etl dedup
make chunk       # o: uv run meli-etl chunk
make split       # o: uv run meli-etl split
make qa          # o: uv run meli-etl qa          (replay desde la caché)
make evaluate    # o: uv run meli-etl evaluate
```

- **Opciones comunes:** todas las etapas aceptan `--config <yaml>` (default
  `configs/default.yaml`) y `--log-level`. Con make: `make dedup CONFIG=otra.yaml`.
- **Logs:** quedan en `outputs/logs/<etapa>.log`.
- **Limpieza:** `make clean` borra los intermedios (`data/processed/*`) y los logs; no toca
  `outputs/*.jsonl`, `reports/` ni las cachés.

**Verificar** que la corrida reproduce los entregables versionados:

```bash
wc -l outputs/corpus.jsonl outputs/qa.jsonl   # 235 y 239
git status --short outputs data/splits        # vacío
```

El log de `qa` termina en `cache: 592 aciertos, 0 llamadas`.

### Regenerar el Q&A con Ollama (opcional)

Hace falta solo si cambian los prompts (`prompts/*.v1.md`), los modelos, los parámetros de
`llm:`/`qa:` o el corpus. En ese caso `make qa` falla con
`Faltan N respuestas del LLM en la cache` y no escribe nada.

```bash
# macOS: brew install ollama   ·   Linux: curl -fsSL https://ollama.com/install.sh | sh
ollama serve &                   # si no quedó corriendo como servicio (localhost:11434)
ollama pull qwen2.5:7b           # generador
ollama pull llama3.1:8b          # juez (otra familia, para no auto-aprobar su estilo)
make qa-record                   # = uv run meli-etl qa --cache-mode record
make qa                          # comprueba en replay que la caché quedó completa
```

- **Qué graba `record`:** llama al modelo solo por lo que falta y guarda cada respuesta apenas
  llega. Si se corta, se relanza el mismo comando y retoma donde quedó.
- **Errores del modelo:** un error de generación (HTTP 5xx, p. ej. `token repeat limit`) se
  reintenta una vez con `repeat_penalty` 1,15; si vuelve a fallar, se salta y se cuenta como
  `llm_error`. Un error de conexión corta la etapa con un mensaje que indica qué hacer.
- **Otros proveedores:** Anthropic u OpenAI funcionan con `llm.provider: anthropic|openai` en
  una copia de la config y la key en `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`. La key nunca se
  escribe en el repo ni en la caché.

### Revisión humana (fuera de `make all`; nunca borran etiquetas ya cargadas)

```bash
make label-pairs          # pares casi-duplicados para etiquetar → data/labels/near_dup_review.md + near_dup_labels.csv
make validate-threshold   # métricas del umbral con esas etiquetas → reports/dedup.md §8
make label-qa             # muestra de 30 preguntas para validar al juez → data/labels/qa_review.md + qa_judge_labels.csv
```

### Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `… no existe: corré antes meli-etl <etapa>` | Se corrió una etapa sin las anteriores: `make all`. |
| `qa`: `Faltan N respuestas del LLM en la cache` | Cambió algo que entra en la clave de la caché: `make qa-record`. |
| `qa`: `¿Está corriendo Ollama?` | `ollama serve` y `ollama pull <modelo>` (solo en `record`). |
| `split`: `Cambiaron parámetros del split` | Se editó `seed` o `split.*`: es intencional; `make split-rebuild` si se quiere un eval nuevo. |
| `evaluate`: `` `qa.jsonl` está desactualizado `` | El corpus cambió después de generar el Q&A: `make qa`. |
| WARNING de `threshold_fallback` en `dedup` | No hay un valle claro de similitud: etiquetar pares y recalibrar (ver «Decisiones clave»). |

## Etapas

| Etapa | Entrada | Salida | Reporte |
|---|---|---|---|
| `profile` | `data/raw/docs_raw/` | `data/processed/inventory.jsonl` | `reports/profile.md` |
| `normalize` | `data/raw/docs_raw/` | `data/processed/normalized_docs.jsonl`, `sections.jsonl`, `nav.jsonl`, `normalize_stats.json` | (en `reports/dedup.md` §3) |
| `dedup` | `sections.jsonl`, `normalized_docs.jsonl`, `data/labels/near_dup_labels.csv`, `data/labels/manual_must_links.csv` | `data/processed/sections_dedup.jsonl`, `versions.json` (incluye el umbral usado), `near_dup_pairs.jsonl` | `reports/dedup.md` |
| `chunk` | `sections_dedup.jsonl`, `versions.json`, `swagger.yaml` de `data/raw/` | `outputs/corpus.jsonl`, `data/processed/corpus_{section,section_split,merged}.jsonl` | `reports/chunk.md` |
| `split` | `outputs/corpus.jsonl`, `data/splits/manifest.json` | campo `split` en `outputs/corpus.jsonl`, `data/splits/manifest.json` | `reports/split.md` |
| `qa` | `outputs/corpus.jsonl`, `prompts/`, `data/cache/llm/`, `data/labels/qa_judge_labels.csv` | `outputs/qa.jsonl`, `data/processed/qa_candidates.jsonl` | `reports/qa.md` |
| `evaluate` | `outputs/qa.jsonl`, `outputs/corpus.jsonl`, `data/processed/corpus_*.jsonl`, `qa_candidates.jsonl` | `outputs/retrieval_metrics.json` | `reports/evaluate.md` |

Auxiliares: `label-pairs`, `validate-threshold` y `label-qa` (ver arriba). Todos los
parámetros salen de `configs/default.yaml`; las rutas relativas se resuelven contra la raíz
del proyecto.

**Versionado:** `data/raw/`, `outputs/` (menos `logs/`), `reports/`, `prompts/`,
`data/cache/llm/`, `data/cache/tiktoken/` (tokenizer offline), `data/labels/` y
`data/splits/manifest.json`. `data/processed/` se regenera y no se versiona.

## Esquemas de salida

### `outputs/corpus.jsonl`

Una fila por ficha.

| Campo | Tipo | Descripción |
|---|---|---|
| `chunk_id` | str | `ck-` + hash de (tipo, secciones u operación, parte, texto). Estable mientras no cambie el contenido. |
| `text` | str | Contenido limpio, tal cual la documentación normalizada (para CPT y para verificar respuestas). |
| `contextualized_text` | str | `text` con encabezado `proyecto › archivo › section_path` + `Versions: …`; es lo que se indexa. |
| `n_tokens`, `n_tokens_ctx` | int | Tokens (`o200k_base`) de `text` y de `contextualized_text`. |
| `source_type` | str | `markdown` u `openapi`. |
| `chunk_strategy`, `chunk_kind` | str | Estrategia (`merged` en el entregable) y tipo: `section`, `merged`, `split` u `operation`. |
| `project` | str | Proyecto. |
| `section_ids`, `section_path`, `section_titles` | list[str] | Secciones de dedup que contiene, ruta de headers y títulos. |
| `part`, `n_parts` | int | Posición si la sección se partió (1/1 si no). |
| `source_path`, `source_paths`, `source_url` | str, list[str], str\|null | Archivo de origen, todos los archivos con este contenido y URL publicada. |
| `version_dir`, `declared_version`, `effective_version` | str | Carpeta, versión declarada y versión real por contenido. |
| `versions_declared`, `versions_effective` | list[str] | Todas las versiones que cubre la ficha. |
| `occurrences` | list[obj] | Cada aparición del contenido, con `section_id`, `path`, versiones, `match` (`self`, `exact`, `near_dup`, `human_label`, `audit_link`, `transitive`) y `jaccard`. |
| `role`, `variant_of`, `variant_of_chunks` | str, str, list[str] | `canonical` o `variant` (y de qué sección/fichas es variante). |
| `cluster_ids` | list[str] | Clusters de dedup (`cl-…`) u operación OpenAPI (`oa-…`). |
| `split_group` | str | `sg-…`: componente conexa de fichas que comparten un cluster. **Unidad del split.** |
| `split` | str | `train`, `eval_section` o `eval_project`. |
| `language` | str | `es`, `en`, `mixed` o `unknown`. |
| `has_code`, `has_table`, `has_list`, `oversize` | bool | Banderas estructurales; `oversize` = bloque indivisible > `chunk.max_tokens`. |
| `spec_version`, `operation` | str, obj | Solo OpenAPI: versión de la spec y `{method, path, operation_id}`. |

### `outputs/qa.jsonl`

Una pregunta por fila, anclada a una ficha de `corpus.jsonl`.

| Campo | Tipo | Descripción |
|---|---|---|
| `qa_id` | str | `qa-` + hash de (chunk_id, tipo, pregunta normalizada): estable. |
| `question`, `answer` | str | En el idioma de la ficha (`mixed`/`unknown` → el mayoritario del proyecto). |
| `evidence` | list[str] | Citas literales de la ficha (una en `llm`, las líneas del swagger en `openapi`, vacía en `unanswerable`). |
| `qa_type` | str | `llm`, `openapi` o `unanswerable`. |
| `answer_type` | str | `short` (verificable) o `long`. |
| `reference_answer`, `verifier` | str/list, str | Solo si `short`: respuesta de referencia y cómo compararla (`exact`, `set`, `normalized`). |
| `chunk_id`, `split`, `project`, `source_path`, `section_path` | | Procedencia, heredada de la ficha. |
| `language` | str | `es` o `en`. |
| `leak_risk` | bool | Pregunta de eval sobre un endpoint que también aparece en una ficha de train. |
| `judge_scores` | obj\|null | Rúbrica del LLM-juez (1-5): `faithfulness`, `clarity`, `usefulness` (`answered` en `unanswerable`); `null` en `openapi`. |
| `generator` | obj | Modelo y prompt que la generó (y `retry` si salió del reintento), o la plantilla OpenAPI. |
| `messages_rag` | list | Chat system/user/assistant con la ficha como contexto. |
| `messages_closed_book` | list | El mismo chat sin la ficha. |

## Decisiones clave

- **Dedup con umbral automático** (`dedup.near_dup_threshold: auto`).
  - **Método:** dedup exacto por hash del texto normalizado y, después, casi-duplicados con
    MinHash/LSH verificados con Jaccard exacto sobre shingles de 5 palabras.
  - **Elección del umbral:** usa etiquetas humanas si hay ≥ `labels.min_same_pairs` pares
    `same` y `diff` (punto medio del intervalo con mejor F1). Si no, el punto medio del
    hueco más ancho sin pares en el Jaccard de los candidatos, dentro de `[0.3, 0.9]`. Si ese
    hueco mide < 0,1, usa `threshold_fallback` (0,6) con un WARNING.
  - **Hoy:** las etiquetas no alcanzan (6 `same`), el valle es [0,30, 0,69] y el umbral queda
    en **0,494**. Agrupa exactamente lo mismo que 0,6.
  - **Registro:** el umbral usado queda en `versions.json` y en `reports/dedup.md` §4; las
    etapas posteriores lo leen de ahí.
  - **Recalibrar con etiquetas** cuando cambian las fuentes o aparece el WARNING.
  - **Regla de fusión sin pérdida:** una sección se absorbe solo si todas sus líneas ya
    están en otra; si aporta algo, queda como `variant` del mismo cluster.
- **Must-link.**
  - Los pares etiquetados `same` en `data/labels/near_dup_labels.csv` se agrupan aunque estén
    bajo el umbral (`match: human_label`); las etiquetas `diff` nunca separan.
  - `data/labels/manual_must_links.csv` declara uniones por `section_id` para pares fuera de
    la muestra etiquetable (`match: audit_link`), por ejemplo resumen vs. detalle hallados en
    la auditoría del split. Hoy hay 4.
- **Split con manifiesto congelado.**
  - **Unidad:** `split_group`, de modo que un cluster nunca queda en dos splits.
  - **Asignación:** `eval_project` es un proyecto entero retenido (`order-workflow-api`).
    `eval_section` toma ~17,5 % de los tokens de cada estrato (proyecto × tipo de fuente), en
    orden de `sha256(seed|split_group)`.
  - **Manifiesto:** la asignación queda en `data/splits/manifest.json`. Los grupos existentes
    no se mueven; los nuevos heredan o completan la cuota. Si contenido nuevo une eval con
    train, el grupo va a train y queda registrado en el historial `eval_changes`.
  - **Parámetros:** cambiar `seed` o `split.*` hace fallar la etapa a propósito; `make
    split-rebuild` (`--rebuild`) genera un eval nuevo, y los resultados anteriores dejan de
    ser comparables.
  - **Fuga dura:** un grupo o cluster en dos splits hace fallar la etapa.
- **Filtros de Q&A**, en orden:
  1. JSON inválido;
  2. evidencia no literal en la ficha (solo se tolera colapsar espacios);
  3. pregunta trivial (corta, contiene su respuesta o es un título);
  4. ambigua ("esta sección", "el texto"…);
  5. casi-duplicada (Jaccard ≥ 0,8; entre splits se descarta la de eval);
  6. LLM-juez de otra familia, que exige cada criterio ≥ 3.

  Además:
  - Ante JSON inválido o evidencia no literal hay **un reintento** con el error concreto.
  - En eval se piden 3 preguntas por ficha.
  - `leak_risk` marca las preguntas de eval sobre endpoints que también aparecen en train,
    reusando la auditoría del split.
  - Las preguntas OpenAPI son deterministas (método y path, parámetros obligatorios, códigos
    de respuesta), con verificador exacto.

## Resultados principales

| | |
|---|---|
| Entrada | 107 archivos de 10 proyectos; 432 secciones con contenido |
| Dedup | 432 → 233 secciones (226 clusters, 7 variantes); umbral 0,494 (valle) |
| Corpus | 235 fichas (`merged`): train 165, eval_section 52, eval_project 18; eval_section = 17,8 % de los tokens no retenidos |
| Q&A | 239 preguntas: 151 `llm`, 54 `openapi`, 34 `unanswerable`; train 145, eval_section 73, eval_project 21 |
| Embudo `llm` | 320 pedidas → 151 finales (el juez descarta 99; el reintento recupera 66) |
| Fundamentación | 205/205 respuestas con evidencia literal en su ficha (test de integridad) |
| Cobertura | 148/235 fichas (63 %) con al menos una pregunta |
| Fuga | 6 preguntas `leak_risk`, todas en eval_section |

**Retrieval BM25** sobre las 83 preguntas de eval sin `unanswerable` (`reports/evaluate.md`):

| Estrategia | Fichas | R@1 | R@5 | R@10 | MRR |
|---|---|---|---|---|---|
| section | 256 | 0,723 | 0,880 | 0,952 | 0,805 |
| section_split | 287 | 0,687 | 0,928 | 0,964 | 0,790 |
| **merged** | 235 | 0,699 | 0,928 | 0,952 | 0,803 |
| azar (`merged`) | 235 | 0,012 | 0,036 | 0,060 | 0,039 |

- **`merged` y `section` empatan:** la diferencia es menor que lo que mueve una pregunta. Se
  recomienda `merged`, la estrategia del entregable, por su R@5.
- **Causa típica de fallo:** que la pregunta no nombre el proyecto.

El reporte incluye además la calidad del dataset Q&A (§8): balance, diversidad (72 % de las
preguntas empiezan con "qué/what"), longitudes, fuga y abstención.

## Limitaciones y próximos pasos

- **Validar el juez.** El juez (llama3.1:8b) explica 99 de los 169 descartes `llm` y todavía
  no tiene etiquetas humanas. Hay que completar `make label-qa` (30 preguntas) y medir el κ
  de Cohen juez-humano en `reports/qa.md` §6. Con κ < 0,4, el juez no debería filtrar ni usarse
  como métrica.
- **Prompt de Q&A que nombre el proyecto.** Varias preguntas no nombran su proyecto ("Which
  version of MySQL is needed for the project?") y son ambiguas fuera de contexto: es la
  primera causa de fallo de retrieval. Hace falta exigirlo en `prompts/qa_generate`, con un
  filtro que lo verifique.
- **Dedup entre idiomas.** Los shingles de palabras no detectan la misma sección traducida
  (es ↔ en), así que una traducción puede quedar en otro split. Habría que comparar con
  embeddings multilingües o traducir antes de comparar.
- **Volumen y balance.** 145 preguntas de train y 94 de eval (11 `unanswerable`, 0 OpenAPI
  en eval_project) alcanzan para medir retrieval, no para un SFT con conclusiones finas.
  Hay que generar más preguntas por ficha y más sin respuesta.
- **Extensión RL.** Dos líneas, descritas en `reports/experiment_plan.md` §7:
  - GRPO con recompensa verificable (1/0 con el `verifier`) sobre las preguntas `openapi` y
    las `short`;
  - DPO con pares chosen/rejected: referencia o abstención vs. respuestas alucinadas del
    modelo base.
- **Fine-tuning.** El diseño (QLoRA sobre Qwen2.5-7B-Instruct, 4 brazos, criterio de éxito)
  está en `reports/experiment_plan.md`; no se entrenó nada.
