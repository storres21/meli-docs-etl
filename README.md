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
uv run pytest
```

Reportes: `reports/profile.md` y `reports/dedup.md`. Intermedios en `data/processed/`.

## Estructura

```
configs/            configuración (rutas, semilla, umbrales)
data/raw/docs_raw/  input crudo (versionado)
data/processed/     salidas intermedias (ignoradas por git)
data/cache/llm/     cache de respuestas del LLM (versionada → qa reproducible sin API key)
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
| dedup | `meli-etl dedup` | ✅ | `sections_dedup.jsonl`, `versions.json`, `reports/dedup.md` |
| chunk | `meli-etl chunk` | ⏳ | `corpus.jsonl` |
| split | `meli-etl split` | ⏳ | _TBD_ |
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
   `cluster_id`. La redundancia que esto deja se cuantifica en el reporte.
4. **Versiones**: la versión efectiva de una carpeta alias es la carpeta concreta con
   contenido idéntico; las inconsistencias con `documentationTypes.json` se reportan.

`cluster_id` agrupa duplicados exactos y casi-duplicados: es la clave del split train/eval
sin leakage. Cómo leer `reports/dedup.md`: §1 embudo por paso, §3 efecto de normalizar,
§4 distribución de similitudes (justifica el umbral), §5 clusters y redundancia,
§6 diffs de ejemplo, §7 versiones.

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
