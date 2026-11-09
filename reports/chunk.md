# Chunking del corpus

Generado por `meli-etl chunk`. Estrategia del entregable: **`merged`**; tokenizer `o200k_base` (tiktoken); tamaños mín/objetivo/máx = 64/256/512 tokens.

## 1. Embudo

| Paso | Cantidad | Detalle |
|---|---|---|
| Registros de dedup | 233 | 226 canónicas + 7 variantes; cubren 432 secciones (las absorbidas viajan en `occurrences`) |
| Secciones partidas | 10 | → 41 pedazos |
| Secciones fusionadas | 86 | → 34 chunks (hermanas consecutivas del mismo archivo) |
| Chunks Markdown | 212 |  |
| Chunks OpenAPI | 23 | 3 specs: price-engine-api (1), traffic-gate-api (8), zenith-keeper (14) |
| **Total** | **235** | `outputs/corpus.jsonl` |

## 2. Tamaños

**Secciones de entrada** (n = 233): p10 22 · p25 43 · p50 72 · p75 175 · p90 410 · p95 617 · máx 3024 tokens.

- **mín = 64** (el 42% de las secciones está por debajo): son fragmentos —un endpoint de una línea, una alerta corta— que conviene juntar con sus hermanas.
- **objetivo = 256** (83% por debajo): se fusiona hasta el tamaño de una sección típica, sin inflar.
- **máx = 512** (94% por debajo): solo se parten las secciones realmente largas; coincide con la ventana usual de modelos de embeddings (e5/BGE base).

**Chunks del entregable** (`merged`, n = 235):

| Tokens | Chunks |  |
|---|---|---|
| [0, 32) | 19 | ██ |
| [32, 64) | 18 | ██ ← mín |
| [64, 128) | 58 | ███████ |
| [128, 192) | 57 | ███████ |
| [192, 256) | 35 | ████ ← objetivo |
| [256, 384) | 26 | ███ |
| [384, 512) | 15 | ██ ← máx |
| [512, 1024) | 5 | █ |
| ≥ 1024 | 2 |  |

## 3. Fusiones, particiones y chunks fuera de rango

**Fusiones:** 22 chunks de 2 secciones, 8 chunks de 3 secciones, 2 chunks de 4 secciones, 2 chunks de 5 secciones.

**Secciones partidas** (cortes solo entre párrafos/bloques):

| Sección | Tokens | Pedazos | Tokens por pedazo |
|---|---|---|---|
| demand-forecast-docs/latest/guide/overview.md#011 | 542 | 3 | 158, 191, 192 |
| demand-forecast-docs/latest/guide/overview.md#015 | 586 | 3 | 216, 136, 234 |
| demand-forecast-docs/latest/guide/overview.md#016 | 518 | 2 | 253, 265 |
| order-workflow-api/5.6.2-hotfix-1/guide/use-cases.md#001 | 659 | 3 | 219, 272, 166 |
| traffic-gate-api/latest/guide/README.md#001 | 688 | 4 | 109, 192, 131, 256 |
| traffic-gate-api/latest/guide/sections/processes.md#001 | 617 | 3 | 292, 122, 203 |
| traffic-gate-api/latest/guide/sections/processes.md#002 | 762 | 3 | 232, 263, 267 |
| traffic-gate-api/latest/guide/sections/waf_config.md#000 | 1327 | 5 | 195, 443, 167, 134, 388 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/important.md#007 | 1879 | 3 | 75, 863, 940 |
| zenith-keeper/1.1.6/guide/use-cases.md#000 | 2435 | 12 | 226, 213, 164, 258, 189, 170, 218, 212, 223, 205, 168, 178 |

**Chunks oversize** (> 512 tokens por un bloque que no se puede partir): 7.

| Chunk | Tokens | Origen | Bloque más grande |
|---|---|---|---|
| ck-9dbf61c11cb1768a | 3012 | demand-forecast-docs/latest/guide/overview.md#013 | code de 2965 tokens (mermaid) |
| ck-64575bc6e142290b | 3024 | demand-forecast-docs/latest/guide/overview.md#014 | code de 3024 tokens (Explicabilidad pipeline) |
| ck-55b5c02067e28efc | 780 | order-workflow-api/5.6.2-hotfix-1/guide/services/database.md#005 | code de 749 tokens (A Workflow object is represented as a JS) |
| ck-593936ef8cc6744b | 728 | payment-promise-gateway/0.0.10-test-crc-migration/guide/README.md#019 | code de 728 tokens (API Examples) |
| ck-faa211d8944da567 | 756 | payment-promise-gateway/0.0.10-test-crc-migration/guide/README.md#020 | code de 756 tokens (Example Responses) |
| ck-dcd7e3dfd3a6e44c | 863 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/important.md#007 | html de 863 tokens (<details>) |
| ck-fd5ec7799c66dc3a | 940 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/important.md#007 | html de 832 tokens (<details>) |

**Chunks bajo el mínimo:** 36 de 212 Markdown. No tienen una hermana contigua del mismo archivo con la que sumar sin pasar el objetivo (archivos de una sola sección, hijas únicas o vecinas absorbidas en otra versión); juntarlos con algo que no es hermano mezclaría temas. Variantes que quedan solas: 4.

## 4. Clusters y split_group

`split_group` = componente conexa del grafo chunk–cluster: dos chunks están en el mismo grupo si comparten un cluster (directa o transitivamente). Así una canónica y su variante (en archivos distintos) y los clusters unidos por una fusión quedan juntos, y `split` puede repartir grupos enteros sin que un cluster quede en train y eval a la vez. Los must-link humanos ya están dentro de los clusters de dedup.

- **split_groups:** 197 para 235 chunks. Tamaños: 180 de 1, 8 de 2, 6 de 3, 1 de 4, 1 de 5, 1 de 12.
- **Más grande:** `sg-6206cf4d3521` con 12 chunks, 1 clusters, proyecto(s) zenith-keeper, 2424 tokens.
- **Chunks con varios clusters** (por fusión): 34.
- **Uniones OpenAPI ↔ Markdown** (Jaccard ≥ 0.4941): ninguna; las specs no repiten la guía, cada operación es su propio grupo.

**Chunks del grupo más grande:**

| Chunk | Tipo | Rol | Secciones | Clusters |
|---|---|---|---|---|
| ck-136611699b35c70e | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |
| ck-9ad1ffc84e577617 | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |
| ck-9563ac9e9dbdfc6c | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |
| ck-019a768e7f735842 | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |
| ck-1b9ef332811c9267 | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |
| ck-3661d6eb09e594ab | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |
| ck-245826a063f142a4 | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |
| ck-6c54d470a4025bbd | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |
| ck-e9d4aaf5d2fdfa6a | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |
| ck-24f5746ed048a1ec | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |
| ck-d24981647908141a | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |
| ck-052cf6f58ca412cb | split | canonical | zenith-keeper/1.1.6/guide/use-cases.md#000 | cl-65caa7510f09 |

## 5. Ejemplos

Se muestra `contextualized_text` (encabezado + `text`).

### Chunk chico

`ck-4c2ec768937858ee` · section · 10 tokens · split_group `sg-fc6a9b3229f2`

````markdown
catalog-portfolio-api › guide/api-reference/brands.md › Brand Endpoints › Activate Brand
Versions: 0.0.1-test-bench-v2a

## Activate Brand

Activate a brand after validation.
````

### Chunk fusionado

`ck-a8c7f433d24d2ef8` · merged · 157 tokens · split_group `sg-229e3a017a65`

````markdown
order-workflow-api › guide/development.md › Development › Requirements · Clone · Install · Testing · Running
Versions: 5.6.2-hotfix-1

### Requirements

* Docker
* Java (Spring Boot)
* MySQL

### Clone

`retailcorp get order-workflow-api`

### Install

`mvn package`

### Testing

First, make sure you provide the private key to use to communicate with
gh-proxy. To to this, create a file in `src/main/resources/workflow-gh-proxy.key`
and add the full private key in that file.

Then, to run the unit and integration tests locally try:

`mvn test`

### Running

Copy the file`application-local.yml.dist` located in the `resources` directory
and rename it to `application-local.yml`.

Edit the parameters to match your environment and then run the application with:

`mvn spring-boot:run`
````

### Sección partida: `demand-forecast-docs/latest/guide/overview.md#016` (2 pedazos)

`ck-d3eefde6a1cd5eb3` · split · 253 tokens · split_group `sg-aa06c2e63b2a`

````markdown
demand-forecast-docs › guide/overview.md › Getting to know our tooling › A deeper dive in how retailpipes is used with Retail Data Framework (part 1/2)
Versions: 0.1.3

## A deeper dive in how retailpipes is used with Retail Data Framework

If you take a look at the `src/app/pipes/main.py`, you will see a dictionary of pipelines mapping names to pipeline classes and the creation of a catalog. This catalog is a mapping between names and dataset classes. The names are outputs or inputs of steps in the pipelines (the green boxes in the figures above). Those are the key ingredients here. Let's understand how they talk with retail and each other.

In the Retail Data Framework's tasks.yml file, we have to pass an entrypoint informing which file are we willing to execute. On the cloud, retail will do something like `python <entrypoint file>`, executing what is inside it. We can then access the parameters passed in the task through `retailtk.rda2` library. Note how cumbersome it would be to have to create a new file for every new parameter or task we have...

To overcome it, we have an "orchestrate" function, which, according to the parameter "pipeline_name" passed in `tasks.yml`, executes a specific pipeline. Then, we can use a single file for all tasks (and in some cases the same task-image), which simplifies the process of deploying.
````

`ck-379c2a4ffb073c55` · split · 265 tokens · split_group `sg-aa06c2e63b2a`

````markdown
demand-forecast-docs › guide/overview.md › Getting to know our tooling › A deeper dive in how retailpipes is used with Retail Data Framework (part 2/2)
Versions: 0.1.3

The other key ingredient is the catalog. The catalog receives a dictionary of dataset names and dataset classes and handle all the saving/loading. In marketplace, the datasets are defined in a yml file. You can search the names of the datasets to see which pipelines are generating them in the code.

In the examples above, we aren't passing a catalog to the pipeline, because it is optional. By default, we save the datasets in memory. To save on bigquery, you should do:

```python

from retailpipes.rda.datasets import BigQueryTable
from marketplace.pipes.main import catalog
from retailpipes import Context, Pipeline
from marketplace.pipes.ingest import HolidaysDatasetPipe, IngestMarketplaceData
from marketplace.pipes.forecasting.vertical_iniciativa_pipeline import (
    ProphetVerticalIniciativaPipeline,
)
from marketplace.pipes.preprocessing import PreprocessExogenous, PreprocessTarget

pipe =  (

… (16 líneas más)
````

### Operación OpenAPI

`ck-7358ba628c78ba20` · operation · 195 tokens · split_group `sg-87503ec28c81`

````markdown
zenith-keeper › specs/swagger.yaml › PUT /api/v1/fresh-products/orders{idOrder}
Versions: 1.1.6

## PUT /api/v1/fresh-products/orders{idOrder}

Update order with products list

Operation ID: updateExistProductListOrder
Tags: Products
Servers: http://localhost:8080

Parameters:
- `idOrder` (path; object, Long; required)

Request body (required):
Content (application/json): PurchaseDTO
  - `purchaseOrder` (PurchaseOrderDTO, object)
    - `date` (object, LocalDate)
    - `buyerId` (string)
    - `orderStatus` (OrderStatusDTO, object)
      - `statusCode` (string)
    - `products` (array of ProductsDTO)
      - `productId` (string)
      - `quantity` (integer)

Responses:
- `201`: CREATED
  Content (application/json): PricePurchaseOrderDTO
    - `totalPrice` (object, Long)
- `400`: ERROR
  Content (application/json)
````


## 6. Chequeo de conservación

Todo el contenido de las secciones canónicas y variantes aparece en exactamente un chunk: (a) los pedazos de cada sección son slices contiguos que la cubren entera; (b) cada pedazo está asignado a un solo chunk y aparece literal en su texto; (c) el multiconjunto de líneas no vacías de las secciones es igual al de los chunks Markdown (ni pérdidas ni duplicados).

| Estrategia | Secciones | Pedazos | Sin cubrir | Sin chunk | Duplicados | No literal | Líneas faltantes | Líneas sobrantes | Resultado |
|---|---|---|---|---|---|---|---|---|---|
| `section` | 233 | 233 | 0 | 0 | 0 | 0 | 0 | 0 | ✅ |
| `section_split` | 233 | 264 | 0 | 0 | 0 | 0 | 0 | 0 | ✅ |
| `merged` | 233 | 264 | 0 | 0 | 0 | 0 | 0 | 0 | ✅ |

## 7. Comparación de estrategias

Las tres se escriben en `data/processed/corpus_<estrategia>.jsonl` para compararlas en `evaluate`; la del entregable se configura con `chunk.strategy`.

| Estrategia | Markdown | OpenAPI | Total | Media | p50 | p90 | Máx | < 64 | Oversize | split_groups | Grupo más grande | Conservación |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `section` | 233 | 23 | 256 | 186 | 83 | 410 | 3024 | 100 | 15 | 249 | 2 | ✅ |
| `section_split` | 264 | 23 | 287 | 166 | 94 | 335 | 3024 | 100 | 7 | 249 | 12 | ✅ |
| `merged` (entregable) | 212 | 23 | 235 | 203 | 158 | 370 | 3024 | 37 | 7 | 197 | 12 | ✅ |

## 8. Specs OpenAPI

| Spec | Título | info.version | Versión declarada | Versión efectiva | Operaciones | $ref sin resolver |
|---|---|---|---|---|---|---|
| price-engine-api/latest/specs/swagger.yaml | Price Engine API | 0.1.0 | 0.0.2-setting-up | 0.0.2-setting-up | 1 | ninguna |
| traffic-gate-api/latest/specs/swagger.yaml | traffic-gate-api | 1.7.0 | 1.65.0 | 1.65.0 | 8 | ninguna |
| zenith-keeper/1.1.6/specs/swagger.yaml | fresh-products-api | 0.0.1 | 1.1.6 | 1.1.6 | 14 | ninguna |

**Inconsistencias en las specs** (se reportan, no se corrigen):

- `price-engine-api/latest/specs/swagger.yaml`: Referencias fuera de `#/components` (no estándar en OpenAPI 3): `#/models/RequestError`, `#/models/Zones`.
- `price-engine-api/latest/specs/swagger.yaml`: El parámetro `SellerID` declara `name: service_id`, que corresponde a `ServiceID`: nombres intercambiados.
- `price-engine-api/latest/specs/swagger.yaml`: El parámetro `ServiceID` declara `name: seller_id`, que corresponde a `SellerID`: nombres intercambiados.
- `zenith-keeper/1.1.6/specs/swagger.yaml`: `info.title` es `fresh-products-api`, distinto del proyecto `zenith-keeper`.

## Salidas

- `outputs/corpus.jsonl`: entregable (esquema en el README).
- `data/processed/corpus_<estrategia>.jsonl`: las tres estrategias.
