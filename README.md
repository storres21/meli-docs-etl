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
uv run meli-etl normalize
uv run meli-etl dedup
uv run meli-etl chunk
uv run meli-etl split
uv run pytest
```

Entregable: `outputs/corpus.jsonl` (con su `split`). Reportes: `reports/profile.md`,
`reports/dedup.md`, `reports/chunk.md` y `reports/split.md`. Intermedios en `data/processed/`. Funciona offline después de clonar:
el tokenizer (tiktoken `o200k_base`) está cacheado en `data/cache/tiktoken/`.

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
| qa | `meli-etl qa` | ⏳ | `qa.jsonl`, datos RL/DPO |
| evaluate | `meli-etl evaluate` | ⏳ | métricas Recall@k / MRR |

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
   `near_dup_min_tokens` tokens solo participan del dedup exacto.
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

_TBD._

## Evaluación

_TBD._

## Limitaciones y trabajo futuro

_TBD._
