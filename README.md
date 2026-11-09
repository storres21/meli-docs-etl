# meli-docs-etl

Pipeline local y reproducible que transforma documentación Markdown cruda de 10 proyectos
de software en datos para LLMs: corpus para retrieval/CPT, pares Q&A para SFT/evaluación,
datos para RL y métricas de calidad/retrieval.

## Instalación y ejecución, paso a paso

Todo corre local y sin red: el input (`data/raw/`), el tokenizer y las respuestas del LLM
están versionados. Solo hace falta red para instalar las herramientas y, opcionalmente, para
**regenerar** las preguntas con un LLM (paso 7).

### 1. Requisitos

| Herramienta | Para qué | Obligatoria |
|---|---|---|
| `git` | clonar el repo | sí |
| [`uv`](https://docs.astral.sh/uv/) ≥ 0.4 | entorno e instalación de dependencias (lockfile `uv.lock`) | sí |
| Python ≥ 3.10 | lo instala `uv` si no lo tenés | sí (vía uv) |
| `make` | atajos (`make all`, `make qa`, …) | no: cada target tiene su comando `uv run` |
| [Ollama](https://ollama.com) | solo para regenerar el Q&A con LLM local (paso 7) | no |

Instalar `uv` (y `make` si no está):

```bash
# macOS
brew install uv                 # o: curl -LsSf https://astral.sh/uv/install.sh | sh
xcode-select --install          # trae make y git, si no los tenés

# Linux (Debian/Ubuntu)
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo apt-get install -y make git

# Windows (PowerShell): sin make, usar los comandos `uv run` de abajo
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Abrí una terminal nueva y verificá:

```bash
uv --version
git --version
make --version     # opcional
```

Si no tenés Python ≥ 3.10, `uv sync` lo descarga solo; también podés hacerlo a mano con
`uv python install 3.12`.

### 2. Clonar

```bash
git clone https://github.com/storres21/meli-docs-etl.git
cd meli-docs-etl
```

### 3. Instalar dependencias

```bash
uv sync
```

Crea `.venv/` con las versiones exactas de `uv.lock`, incluidas las de desarrollo (pytest,
ruff). No hace falta activar el entorno: todo se corre con `uv run …`. Para ver los comandos
disponibles: `uv run meli-etl --help` o `make help`.

### 4. Correr el pipeline

```bash
make all      # = uv sync + profile → normalize → dedup → chunk → split → qa → evaluate + pytest
```

Lo mismo, comando a comando y sin `make`:

```bash
uv run meli-etl profile      # inventario y perfil       → reports/profile.md
uv run meli-etl normalize    # secciones normalizadas    → data/processed/sections.jsonl
uv run meli-etl dedup        # dedup exacto + casi-dup   → reports/dedup.md
uv run meli-etl chunk        # fichas                    → outputs/corpus.jsonl, reports/chunk.md
uv run meli-etl split        # train / eval (manifiesto) → split en corpus.jsonl, reports/split.md
uv run meli-etl qa           # preguntas (replay)        → outputs/qa.jsonl, reports/qa.md
uv run meli-etl evaluate     # BM25 por estrategia       → reports/evaluate.md
uv run pytest                # tests (sintéticos, sin red)
```

El orden importa: cada etapa lee la salida de la anterior en `data/processed/`. Tarda menos de
un minuto en total. `qa` corre en modo replay: lee las respuestas del LLM de la cache
versionada, sin red ni API key, y el log termina en `cache: N aciertos, 0 llamadas`.
`evaluate` no usa LLM.

Todas las etapas aceptan `--config <yaml>` (default `configs/default.yaml`) y
`--log-level DEBUG|INFO|WARNING`. Con make: `make dedup CONFIG=otra.yaml`.

### 5. Verificar el resultado

```bash
wc -l outputs/corpus.jsonl outputs/qa.jsonl   # 235 fichas y 239 preguntas
git status --short outputs data/splits        # vacío: salida idéntica a la versionada
```

El pipeline es determinista (semilla en la config, reportes sin timestamps), así que una
corrida sobre un clon limpio reproduce byte a byte `outputs/` y el manifiesto del split. Si
`git status` muestra cambios en `reports/split.md` después de correr `split` dos veces, es
esperable: la segunda corrida ya encuentra todos los grupos en el manifiesto (`kept`).

Resultados:

- Entregables: `outputs/corpus.jsonl` (fichas con `split`), `outputs/qa.jsonl` (preguntas
  ancladas a fichas) y `outputs/retrieval_metrics.json` (métricas de `evaluate`). Esquemas en
  «Esquemas de salida».
- Reportes: `reports/profile.md`, `dedup.md`, `chunk.md`, `split.md`, `qa.md`,
  [`evaluate.md`](reports/evaluate.md) y el diseño
  [`experiment_plan.md`](reports/experiment_plan.md) (no lo genera el pipeline).
- Intermedios: `data/processed/` (no versionados; se regeneran). Logs:
  `outputs/logs/<etapa>.log`.

### 6. Otros comandos útiles

```bash
uv run pytest tests/test_qa.py                             # un archivo de tests
uv run pytest tests/test_dedup.py::test_numeric_threshold_is_respected   # un test
uv run ruff check src tests && uv run ruff format src tests              # lint + formato
make clean       # borra data/processed/* y logs (no toca outputs/, reports/ ni caches)
make split-rebuild   # rehace el split desde cero: genera un eval NUEVO (ver «Split y manifiesto»)
```

Revisión humana (fuera de `make all`, nunca borran etiquetas cargadas):

```bash
make label-pairs          # pares casi-duplicados para etiquetar → data/labels/near_dup_*
make validate-threshold   # métricas del umbral con esas etiquetas → reports/dedup.md §8
make label-qa             # muestra de 30 preguntas para revisar al juez → data/labels/qa_*
```

### 7. (Opcional) Regenerar el Q&A con un LLM

Solo hace falta si cambiás prompts, modelos, parámetros de `qa:`/`llm:` o el corpus: en
ese caso `make qa` falla con `Faltan N respuestas del LLM en la cache` y no escribe nada.

**Con Ollama (default, local, sin API key):**

```bash
# macOS: brew install ollama   ·   Linux: curl -fsSL https://ollama.com/install.sh | sh
ollama serve &                                # si no quedó corriendo como servicio
ollama pull qwen2.5:7b                        # generador (~4,7 GB)
ollama pull llama3.1:8b                       # juez (~4,9 GB)
curl -s localhost:11434/api/tags              # debe listar ambos modelos

make qa-record      # = uv run meli-etl qa --cache-mode record
make qa             # verifica en replay que la cache quedó completa
```

`record` solo llama al modelo por lo que falta en `data/cache/llm/` y guarda cada respuesta
apenas llega: si se corta, se vuelve a correr el mismo comando y retoma. El log muestra el
avance y un ETA. Como referencia, unas 450 llamadas tardan ~1 h en Apple Silicon; en CPU,
varias horas. Si el modelo falla al generar (p. ej. HTTP 500 `token repeat limit`), se
reintenta una vez con `repeat_penalty` más alto y, si vuelve a fallar, se salta y se cuenta
como `llm_error` en `reports/qa.md`. Un error de conexión (Ollama apagado, modelo sin
descargar) corta la etapa con un mensaje que dice qué hacer.

**Con Anthropic u OpenAI:** copiar la config, cambiar el proveedor y los modelos, y pasar la
key por variable de entorno (nunca se escribe en el repo ni en la cache):

```bash
cp configs/default.yaml configs/anthropic.yaml
# editar en configs/anthropic.yaml: llm.provider: anthropic, generator_model y judge_model
export ANTHROPIC_API_KEY=...          # u OPENAI_API_KEY para provider: openai
uv run meli-etl qa --cache-mode record --config configs/anthropic.yaml
```

La cache distingue proveedor y modelo, así que no pisa las respuestas de Ollama.

### 8. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `uv: command not found` | Abrir una terminal nueva tras instalar uv (agrega `~/.local/bin` al `PATH`). |
| `make: command not found` | Usar los comandos `uv run meli-etl …` del paso 4, o instalar make (paso 1). |
| `… no existe: corré antes meli-etl <etapa>` | Se corrió una etapa sin las anteriores: correr el pipeline en orden (paso 4). |
| `qa`: `Faltan N respuestas del LLM en la cache` | Cambió algo que entra en la clave de la cache (prompt, modelo, parámetros, corpus): grabar con `make qa-record` (paso 7). |
| `qa`: `¿Está corriendo Ollama?` | `ollama serve` y `ollama pull <modelo>`; verificar con `curl localhost:11434/api/tags`. |
| `split` falla diciendo que cambiaron parámetros | Se editó `seed` o `split.*`: es a propósito; `make split-rebuild` si se quiere un eval nuevo. |
| `chunk` termina con código 1 | Falló el chequeo de conservación (contenido perdido o duplicado): ver `reports/chunk.md`. |
| WARNING de `threshold_fallback` en `dedup` | No hay un valle claro de Jaccard: ver «Umbral `auto`» y recalibrar con etiquetas. |

## Estructura

```
configs/            configuración (rutas, semilla, umbrales)
data/raw/docs_raw/  input crudo (versionado)
data/processed/     salidas intermedias (ignoradas por git)
data/cache/llm/     cache de respuestas del LLM (versionada → qa reproducible sin API key)
data/cache/tiktoken/ archivo BPE del tokenizer (versionado → chunk funciona offline)
data/labels/        etiquetas humanas (versionadas): validación del umbral de casi-duplicados
data/splits/        manifiesto del split (versionado, NO editar a mano): ver «Split y manifiesto»
outputs/            datasets finales: corpus.jsonl, qa.jsonl, ... (versionados)
outputs/logs/       logs por etapa (ignorados por git)
reports/            reportes legibles (profile.md, dedup.md, ...)
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
| normalize | `meli-etl normalize` | ✅ | `normalized_docs.jsonl`, `sections.jsonl`, `nav.jsonl` |
| dedup | `meli-etl dedup` | ✅ | `sections_dedup.jsonl`, `versions.json`, `near_dup_pairs.jsonl`, `reports/dedup.md` |
| (aux) | `meli-etl label-pairs` | ✅ | `data/labels/near_dup_review.md`, `near_dup_labels.csv` |
| (aux) | `meli-etl validate-threshold` | ✅ | `reports/dedup.md` §8 |
| chunk | `meli-etl chunk` | ✅ | `outputs/corpus.jsonl`, `corpus_<estrategia>.jsonl`, `reports/chunk.md` |
| split | `meli-etl split` | ✅ | campo `split` en `corpus.jsonl`, `data/splits/manifest.json`, `reports/split.md` |
| qa | `meli-etl qa` | ✅ (replay desde la cache grabada) | `outputs/qa.jsonl`, `qa_candidates.jsonl`, `reports/qa.md` |
| (aux) | `meli-etl label-qa` | ✅ | `data/labels/qa_review.md`, `qa_judge_labels.csv` |
| evaluate | `meli-etl evaluate` | ✅ | `reports/evaluate.md`, `outputs/retrieval_metrics.json` |

### normalize

Parte cada archivo **crudo** en secciones (header + cuerpo hasta el siguiente header) y
normaliza cada una, conservando texto y hash crudos para medir el efecto de normalizar.

- **Normalización**: decodifica entidades HTML (también dentro de código: en los datos son
  un artefacto de exportación, p. ej. `curl ... &#39;url&#39;`; solo entidades con `;`);
  tablas sin padding y sin filas vacías; colapsa espacios; quita comentarios HTML/docsify,
  atributos `style`, imágenes y badges (→ metadata `images` / `badges`, p. ej. "Java 17");
  repara `#Título` → `# Título`; sintetiza un H1 desde el nombre de archivo si falta, para
  que `section_path` siempre tenga raíz. **Se preservan** bloques de código, `curl` y tablas.
- **Filtrado**: fuera del corpus quedan la navegación (`_sidebar`, `_coverpage`,
  `coverpage.md`; su orden, títulos y frase de portada pasan a metadata `nav_title`,
  `nav_order`, `nav_parent`, `project_tagline`), los `todo_only` y los stubs reales: menos de
  `normalize.stub_min_tokens` tokens **contando código, tablas y links** (una tabla de crons
  sobrevive; un archivo con solo imágenes, no). Dentro de los archivos se descartan secciones
  sin cuerpo propio (su título sigue en el `section_path` de las hijas) y secciones TO DO.
- **Idioma**: por sección, heredando el del documento si la sección es muy corta. El texto
  se mantiene en su idioma original. Los `swagger.yaml` no se procesan en esta etapa.

### dedup

1. **Exacto** por `sha256` del título + cuerpo normalizados. La canónica es una versión
   concreta antes que un alias (`latest`).
2. **Casi-duplicados**: shingles de 5 palabras, MinHash + LSH para candidatos y Jaccard
   **exacto** para verificar (`dedup.near_dup_threshold`). Las secciones con menos de
   `near_dup_min_tokens` tokens solo participan del dedup exacto. El umbral puede ser un
   número fijo o `auto` (el default; ver abajo).
3. **Regla de fusión sin pérdida**: dentro de un cluster, la canónica es la sección con más
   líneas; otra se absorbe (pasa a `occurrences`) solo si **todas** sus líneas ya están en
   una sección conservada. Si aporta una línea nueva queda como `variant` con el mismo
   `cluster_id`, `variant_of` y `jaccard_vs_canonical` (similitud de shingles contra la
   canónica). La redundancia que esto deja se cuantifica en el reporte.
4. **Versiones**: la versión efectiva de una carpeta alias es la carpeta concreta con
   contenido idéntico; las inconsistencias con `documentationTypes.json` se reportan.

`cluster_id` agrupa duplicados exactos y casi-duplicados: es la clave del split train/eval
sin leakage. Cómo leer `reports/dedup.md`: §1 embudo por paso, §3 efecto de normalizar,
§4 distribución de similitudes (justifica el umbral), §5 clusters y redundancia,
§6 diffs de ejemplo, §7 versiones, §8 validación del umbral con etiquetas humanas.

#### Umbral `auto`

Con `dedup.near_dup_threshold: auto`, dedup elige el umbral a partir de los datos, en este
orden (determinista):

1. **Etiquetas** (`labels`): si `data/labels/near_dup_labels.csv` tiene al menos
   `labels.min_same_pairs` pares `same` y otros tantos `diff`, usa la lógica de
   `validate-threshold` con criterio F1: el punto medio (en la grilla `labels.grid_*`) del
   intervalo de umbrales con mejor F1.
2. **Valle** (`valley`): si no, toma el Jaccard de los pares candidatos de LSH y busca el
   hueco sin pares más ancho dentro de `dedup.threshold_bounds` (`[0.3, 0.9]`); usa su
   punto medio. Es la idea de §4: debajo quedan secciones hermanas con plantilla común,
   encima la misma sección en otra versión.
3. **Fallback** (`fallback`): si ese hueco mide menos de `dedup.min_valley_width` (0.1), usa
   `dedup.threshold_fallback` (0.6) y escribe un WARNING.

Un número en `near_dup_threshold` desactiva todo esto y se usa tal cual (método `config`).
El umbral usado, el método, el valle y su ancho, y el histograma de Jaccard de los candidatos
quedan en `reports/dedup.md` §4 y en `data/processed/versions.json` (clave
`near_dup_threshold`). Las etapas posteriores (`chunk`, `split`, `validate-threshold`) leen el
umbral de ahí. Con los datos actuales, las etiquetas no alcanzan (6 `same`), así que se usa el
valle [0.30, 0.69] → 0.494. Ningún par cae entre 0.494 y 0.6, por eso los clusters son
idénticos a los de 0.6.

**Cuándo recalibrar con etiquetas** (`meli-etl label-pairs`, etiquetar, `make
validate-threshold`):

- cuando cambian las fuentes (proyectos o versiones nuevas, otra exportación de la
  documentación): el valle puede moverse o desaparecer;
- cuando aparece el WARNING de fallback: no hay un hueco claro y 0.6 es solo un valor por
  defecto;
- cuando hay pocos pares candidatos: el valle se apoya en pocos puntos, como hoy, con 6
  candidatos.

### Validación del umbral con etiquetas humanas

Fuera de `make pipeline`, para que nada automático toque las etiquetas:

```bash
make label-pairs         # data/labels/near_dup_review.md + near_dup_labels.csv
# completar la columna label: same | diff | unsure
make validate-threshold  # tabla por umbral + recomendación en reports/dedup.md §8
```

- **Revisión ciega**: `near_dup_review.md` muestra los pares con Jaccard ≥
  `labels.review_min_jaccard` en orden aleatorio (`seed`), con rutas y el texto completo de
  ambas secciones en un diff, **sin** el Jaccard ni el cluster actual.
- `pair_id` = hash de los dos `section_id`: estable aunque cambie el orden o el corpus.
  Volver a correr `label-pairs` **conserva** las etiquetas ya cargadas.
- `validate-threshold` barre la grilla `labels.grid_*` y calcula TP/FP/FN/TN, precisión,
  recall y F1 (los `unsure` se excluyen pero se cuentan). Recomienda, priorizando recall,
  el punto medio del intervalo de umbrales con recall máximo y mejor precisión: un falso
  negativo es leakage train/eval; un falso positivo solo agranda un cluster (la regla de
  fusión no pierde contenido). No cambia la config: la decisión es manual.
- `dedup` vuelve a generar la §8 desde las etiquetas, así que no se pierde al re-correr.
- **Must-links**: los pares etiquetados `same` se agrupan en `dedup` aunque su Jaccard quede
  bajo el umbral (`match: human_label`); las etiquetas `diff` nunca separan pares.
- **Must-links manuales** (`data/labels/manual_must_links.csv`, columnas `section_a,
  section_b, origen, nota`): para pares que no están en la muestra etiquetable (Jaccard < 0.1
  o secciones con < 20 tokens), por ejemplo los que encuentra la auditoría sutil del split.
  Se declaran por `section_id`, se unen con `match: audit_link` y se reportan aparte
  (`dedup.md` §5 y §8); no entran en las métricas del umbral porque no tienen un Jaccard
  comparable.

### chunk

Estructura primero, tamaño después (tokens de tiktoken `o200k_base`; mín/objetivo/máx =
64/256/512 en `chunk.*`, justificados con la distribución de secciones en `reports/chunk.md` §2):

1. **Unidad base = sección** canónica o variante de dedup. Las ocurrencias absorbidas no
   generan chunks: su procedencia viaja en `occurrences`.
2. **Fusión** (`merged`): hermanas consecutivas del mismo archivo (mismo padre, contiguas en
   el original, ninguna variante) se juntan si alguna tiene < 64 tokens, hasta 256.
3. **Partición**: secciones > 512 se cortan **solo entre bloques**. Código, tablas, listas y
   `<details>` son atómicos; un párrafo que presenta al bloque siguiente (termina en `:`, va
   pegado o es una línea) viaja con él; un pedazo < 64 se une a su vecino. Un bloque > 512
   queda entero como chunk `oversize`.
4. **OpenAPI**: cada operación de los `swagger.yaml` es un chunk `openapi` legible (método,
   path, parámetros, body, respuestas, ejemplos) con los `$ref` resueltos como punteros JSON
   (incluso raíces no estándar como `#/models`), ciclos cortados.
5. **split_group**: componente conexa del grafo chunk–cluster (union-find). Un chunk
   fusionado puede tener varios `cluster_ids`; una canónica y su variante comparten cluster.
   `split` reparte grupos enteros, así ningún cluster queda en train y eval.
6. **Estrategias**: `section`, `section_split` y `merged` se generan siempre en
   `data/processed/corpus_<estrategia>.jsonl` para compararlas en `evaluate`; la de
   `chunk.strategy` (default `merged`) es `outputs/corpus.jsonl`.
7. **Conservación**: la etapa falla si algún contenido de las secciones no aparece en
   exactamente un chunk (§6 del reporte).

### split

Tres splits, con el `split_group` como unidad (un grupo entero va a un solo split):

| Split | Qué mide |
|---|---|
| `train` | Entrenamiento (CPT/SFT/RL). |
| `eval_section` | ~17,5 % de los tokens de los proyectos no retenidos: ¿el modelo aprendió el contenido de documentación que vio? |
| `eval_project` | Un proyecto entero retenido (`split.eval_project`, hoy `order-workflow-api`): ¿generaliza a documentación nueva? (el caso RAG) |

- **Estratificación**: por proyecto × `source_type`. En cada estrato los grupos se recorren en
  orden de `sha256(seed|split_group)` y se toman hasta la fracción objetivo de tokens; un
  grupo que dejaría el estrato por encima de fracción + tolerancia se saltea, y los estratos
  con menos de 4 grupos quedan en train (`reports/split.md` §2 muestra objetivo vs logrado).
- **Auditoría de fuga**: la etapa falla si un `split_group` o un `cluster_id` aparece en dos
  splits o si una ficha del proyecto retenido queda fuera de `eval_project`. Reporta (sin
  fallar) pares de fichas parecidas entre splits, endpoints del swagger mencionados en un
  `.md` de otro split y archivos repartidos entre train y eval_section.

## Split y manifiesto

El split no se recalcula en cada corrida: queda **congelado** en
`data/splits/manifest.json`, que dice a qué split va cada `split_group` (y guarda sus
fichas, clusters y las ocurrencias que contiene).

**Por qué está versionado.** El conjunto de eval es parte del experimento: si cambiara
silenciosamente, los resultados de dos evaluaciones dejarían de ser comparables y una
ficha de eval podría haber pasado por train. Versionarlo hace que cualquier cambio del eval
quede visible en un diff y en git. **No lo edites a mano**: mover un grupo a mano puede
generar una fuga (un cluster en dos splits) o romper la estratificación; siempre se
regenera con `meli-etl split`.

**Corrida normal** (`make split`, o `make pipeline`, que la incluye): los grupos que ya
están en el manifiesto conservan su split; solo se asignan los grupos nuevos.

```bash
make split
# sin make:
uv run meli-etl split
```

**Cuándo hace falta `--rebuild`.** Solo si cambiás alguno de estos parámetros: `seed`,
`split.eval_project` (el proyecto retenido), `split.eval_section_fraction`,
`split.tolerance` o `split.min_groups_per_stratum`.

```bash
make split-rebuild
# sin make:
uv run meli-etl split --rebuild
```

**Si cambiás uno de esos parámetros sin `--rebuild`, la etapa falla** y lista qué cambió.
Es intencional: aplicar un parámetro nuevo implica rehacer el conjunto de eval, y eso no
debería pasar por accidente al editar la config. `--rebuild` es la forma de decir "sí,
quiero un eval nuevo".

**Un `--rebuild` genera un conjunto de eval nuevo.** El reporte y el log dicen cuántas
fichas entraron y salieron del eval. Los resultados de evaluación anteriores (métricas de
retrieval, Q&A de eval) **dejan de ser comparables** con los nuevos: hay que volver a
evaluar todo sobre el eval nuevo.

**Qué pasa al agregar documentos nuevos** (sin `--rebuild`):
- Los grupos existentes **no se mueven**.
- Los grupos realmente nuevos completan la cuota de su estrato, en orden de hash.
- Un grupo cuyo id cambió (por ejemplo, llegó una versión más completa de una sección y
  cambió su cluster) **hereda** el split de los grupos anteriores con los que comparte
  ocurrencias.
- **Cuándo cambia el conjunto de eval**: (1) si un documento nuevo une contenido que estaba
  en splits distintos (por ejemplo, una sección de train y una de eval pasan a ser
  casi-duplicadas): el grupo unido va a **train** para no filtrar, y el log y
  `reports/split.md` §3 lo marcan como **«cambio del conjunto de eval»** listando las fichas
  que salieron; (2) si se borra contenido que estaba en eval. Pasa lo mismo cuando un
  must-link nuevo (etiqueta `same` o manual) une un grupo de eval con uno de train, aunque
  el grupo unido conserve el id de uno de los dos. En todos los casos conviene re-evaluar.
- Cada cambio del conjunto de eval (y cada `--rebuild` que lo modifique) queda en el
  historial `eval_changes` del manifiesto, así que se ve en git aunque el log ya no esté.

**Cómo sacar una validación desde train** (no se genera hoy): aplicar el mismo algoritmo
dentro de `train`, con otra sal — en cada estrato, ordenar los grupos de train por
`sha256(seed|val|split_group)` y tomar ~10 % de los tokens. Así la validación también
respeta grupos enteros y no comparte clusters con train ni con los eval; las Q&A heredan
el split de su ficha.

## Hallazgos del perfilado

_TBD: resumen de `reports/profile.md`._

## Decisiones de diseño

_TBD._

## Esquemas de salida

### `outputs/corpus.jsonl`

Una fila por chunk, ordenadas por tipo, archivo y posición. Claves en orden alfabético.

| Campo | Tipo | Descripción |
|---|---|---|
| `chunk_id` | str | `ck-` + sha1 de (tipo, secciones u operación, parte, sha1 del texto). Estable entre corridas; cambia solo si cambia el contenido o su origen, así una Q&A nunca queda anclada a otro texto. |
| `text` | str | Contenido limpio, tal cual la documentación normalizada. Para CPT (sin texto sintético), para buscar/verificar respuestas y para el chequeo de conservación. |
| `contextualized_text` | str | `text` con encabezado `proyecto › archivo › section_path (part i/n)` + `Versions: …`. Para indexar (BM25/embeddings): agrega los términos que las consultas mencionan y el cuerpo no (proyecto, tema), clave para pedazos y secciones cortas. |
| `n_tokens`, `n_tokens_ctx` | int | Tokens (`o200k_base`) de `text` y de `contextualized_text`. |
| `source_type` | str | `markdown` u `openapi`. |
| `chunk_strategy` | str | Estrategia que lo generó: `section`, `section_split` o `merged`. |
| `chunk_kind` | str | `section` (una sección entera), `merged` (varias hermanas), `split` (pedazo) u `operation` (OpenAPI). |
| `project` | str | Proyecto. |
| `section_ids` | list[str] | Secciones de dedup que contiene, en orden (vacío en OpenAPI). |
| `section_path` | list[str] | Ruta de headers. En un chunk fusionado, el padre común; en OpenAPI, `[MÉTODO path]`. |
| `section_titles` | list[str] | Títulos de las secciones (o el summary de la operación). |
| `part`, `n_parts` | int | Posición del pedazo si la sección se partió (1/1 si no). |
| `source_path` | str | Archivo de donde sale el texto (relativo a `data/raw/docs_raw`). |
| `source_paths` | list[str] | Todos los archivos donde aparece el contenido, incluidas las copias absorbidas. |
| `source_url` | str \| null | URL publicada: página docsify (`…/guide/index.html#/ruta`) o la spec (`documentationTypes.json`). |
| `version_dir`, `declared_version`, `effective_version` | str | Carpeta, versión declarada por la URL y versión real por contenido del origen. |
| `versions_declared`, `versions_effective` | list[str] | Todas las versiones que cubre el chunk, sumando las ocurrencias. |
| `occurrences` | list[obj] | Cada aparición del contenido: `section_id`, `project`, `version_dir`, versiones, `path`, `section_path`, `match` (`self`, `exact`, `near_dup`, `human_label`, `audit_link`, `transitive`), `jaccard`, `source_url`. |
| `role` | str | `canonical` o `variant`. |
| `variant_of`, `variant_of_chunks` | str, list[str] | En una variante: `section_id` canónica y los `chunk_id` donde vive. |
| `cluster_ids` | list[str] | Clusters de dedup (`cl-…`) u operación (`oa-…`) del chunk. |
| `split_group` | str | `sg-…`: componente conexa de chunks que comparten algún cluster. **Unidad del split train/eval.** |
| `language` | str | `es`, `en`, `mixed` o `unknown`. |
| `has_code`, `has_table`, `has_list` | bool | Banderas estructurales (útiles para filtrar en `qa`). |
| `oversize` | bool | Supera `max_tokens` por un bloque que no se puede partir. |
| `spec_version`, `operation` | str, obj | Solo OpenAPI: `info.version` y `{method, path, operation_id}`. |
| `split` | str | `train`, `eval_section` o `eval_project` (lo agrega la etapa `split`; las Q&A heredan el de su ficha). |

### `outputs/qa.jsonl`

Una pregunta por línea, anclada a una ficha de `corpus.jsonl` y con su split. Tres tipos:
`llm` (generada desde el `text` de la ficha, con evidencia literal), `openapi` (determinista
desde el swagger: método y path, parámetros obligatorios, códigos de respuesta) y
`unanswerable` (plausible pero sin respuesta en la ficha ni en sus vecinas; respuesta "la
documentación no lo especifica" en el idioma de la ficha). Filtros, embudo de descartes,
fuga y acuerdo juez-humano: `reports/qa.md`.

| Campo | Tipo | Descripción |
|---|---|---|
| `qa_id` | str | `qa-` + sha256(chunk_id \| qa_type \| pregunta normalizada)[:16]: estable. |
| `question`, `answer` | str | En el idioma de la ficha (`unknown`/`mixed` → el mayoritario del proyecto). |
| `evidence` | list[str] | Citas literales de la ficha (una en `llm`, las líneas del swagger en `openapi`, vacía en `unanswerable`). |
| `qa_type` | str | `llm`, `openapi` o `unanswerable`. |
| `answer_type` | str | `short` (verificable) o `long`. |
| `reference_answer`, `verifier` | str/list, str | Solo si `short`: respuesta de referencia y cómo compararla (`exact`, `normalized`, `set`); para recompensas verificables en RL. |
| `chunk_id`, `split`, `project`, `source_path`, `section_path` | | Procedencia (heredada de la ficha). |
| `language` | str | `es` o `en`. |
| `leak_risk` | bool | Pregunta de eval sobre un endpoint que también aparece en una ficha de train (auditoría de split §5.2). |
| `judge_scores` | obj | Rúbrica del LLM-juez (1-5): `faithfulness`, `clarity`, `usefulness`; en `unanswerable`, `answered` en lugar de `faithfulness`. `null` en `openapi`. |
| `generator` | obj | Modelo y versión del prompt (o plantilla OpenAPI) que la generó. |
| `messages_rag` | list | Chat para SFT con la ficha como contexto (caso RAG; p. ej. `eval_project`). |
| `messages_closed_book` | list | Chat sin la ficha (conocimiento aprendido; p. ej. `eval_section`). |

**Reproducibilidad.** El LLM (Ollama local por default; también Anthropic u OpenAI, con la
key por variable de entorno) pasa por una cache versionada en `data/cache/llm/` cuya clave
incluye el hash del prompt (`prompts/*.v1.md`), el modelo, los parámetros y la ficha. `make
qa` corre en `replay` (sin red; falla si falta algo). `make qa-record` graba lo que falte y se
reanuda si se corta. La revisión humana del juez: `make label-qa`, completar
`data/labels/qa_judge_labels.csv` y volver a correr `make qa`.

## Evaluación

**Retrieval** ([`reports/evaluate.md`](reports/evaluate.md), `meli-etl evaluate`):

- **Método:** BM25 Okapi implementado a mano (`retrieval.py`; k1 = 1,5, b = 0,75; minúsculas
  y secuencias de letras/dígitos) sobre el `contextualized_text`. Se corre para cada una de
  las tres estrategias de chunking (`data/processed/corpus_<estrategia>.jsonl`), indexando
  todo el corpus.
- **Preguntas:** las de `eval_section` y `eval_project` de `outputs/qa.jsonl`, sin las
  `unanswerable`. Se reporta con y sin las `leak_risk`.
- **Criterio de acierto** (vale para cualquier estrategia): el chunk recuperado contiene
  literalmente la `evidence`, con espacios normalizados. En las `openapi`, el chunk es el de
  esa operación (proyecto + método + path).
- **Métricas:** Recall@1/5/10 y MRR, más un baseline aleatorio con semilla. El reporte
  incluye además:
  - la tabla estrategia × split × métrica;
  - la estrategia recomendada y por qué;
  - eval_section vs eval_project;
  - el efecto de quitar `leak_risk`;
  - 5 fallos diagnosticados.
- **Resultado actual:** `merged` y `section` empatan (MRR ≈ 0,80, R@5 ≈ 0,93 con `merged`,
  frente a MRR ≈ 0,03 del azar). Se recomienda `merged`, que es la estrategia del
  entregable.

**Plan de experimentos** ([`reports/experiment_plan.md`](reports/experiment_plan.md)): diseño
(sin entrenar) de un SFT con QLoRA sobre Qwen2.5-7B-Instruct. Contenido:

- brazos base, base + RAG, SFT closed-book y SFT + RAG;
- métricas: exactitud verificable, fidelidad, abstención y alucinación, juez, Recall@k y
  olvido;
- rigor: 3 semillas, bootstrap pareado y decontaminación;
- criterio de éxito pre-registrado, extensión a GRPO/DPO, costo y riesgos.

## Limitaciones y trabajo futuro

_TBD._
