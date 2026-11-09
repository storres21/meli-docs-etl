# Split train / eval

Generado por `meli-etl split`. Unidad: `split_group`. Proyecto retenido (`eval_project`): **order-workflow-api**. eval_section: 17.5% de los tokens de cada estrato (proyecto × source_type), tolerancia ±5%, orden `sha256(seed=42|split_group)`. Manifiesto: `data/splits/manifest.json`.

## 1. Tamaños por split

| Split | Fichas | Tokens | % tokens | split_groups | Para qué |
|---|---|---|---|---|---|
| `train` | 165 | 35856 | 75.1% | 134 | entrenamiento (CPT/SFT/RL) |
| `eval_section` | 52 | 7787 | 16.3% | 47 | ¿aprendió el contenido de proyectos que vio? |
| `eval_project` | 18 | 4102 | 8.6% | 16 | ¿generaliza a documentación nueva? (caso RAG) |
| **Total** | 235 | 47745 | 100% | 197 |  |

**eval_section sobre los proyectos no retenidos: 17.8%** de 43643 tokens (objetivo 17.5%, rango [12.5%, 22.5%]: ✅ dentro).

## 2. Estratificación: objetivo vs logrado

| Proyecto | Tipo | Grupos | Tokens | eval_section | Logrado | vs objetivo | Nota |
|---|---|---|---|---|---|---|---|
| 2p-revenue-optimizer-api | markdown | 10 | 1621 | 342 | 21.1% | +3.6% |  |
| catalog-portfolio-api | markdown | 67 | 8184 | 1547 | 18.9% | +1.4% |  |
| demand-forecast-docs | markdown | 24 | 11319 | 2008 | 17.7% | +0.2% | no entra en la cuota: `sg-5c26df6e8cbf` (3024 tok), `sg-8662f6b25141` (3012 tok) |
| payment-promise-gateway | markdown | 19 | 4119 | 756 | 18.4% | +0.9% |  |
| price-engine-api | markdown | 3 | 321 | 0 | 0.0% | -17.5% | estrato chico (3 grupos < 4) → train |
| price-engine-api | openapi | 1 | 498 | 0 | 0.0% | -17.5% | estrato chico (1 grupo < 4) → train |
| traffic-gate-api | markdown | 11 | 5476 | 1043 | 19.0% | +1.5% | no entra en la cuota: `sg-ebd38fd358d6` (1327 tok) |
| traffic-gate-api | openapi | 8 | 2173 | 474 | 21.8% | +4.3% | no entra en la cuota: `sg-f082813aab98` (496 tok) |
| unified-transaction-configs | markdown | 5 | 484 | 104 | 21.5% | +4.0% | no entra en la cuota: `sg-4ce6fdfbda6b` (193 tok) |
| vendor-stockkeeper-api | markdown | 18 | 4591 | 992 | 21.6% | +4.1% | no entra en la cuota: `sg-88e72dd495ac` (1878 tok) |
| zenith-keeper | markdown | 1 | 2424 | 0 | 0.0% | -17.5% | estrato chico (1 grupo < 4) → train |
| zenith-keeper | openapi | 14 | 2433 | 521 | 21.4% | +3.9% |  |

El grupo más grande (`sg-6206cf4d3521`, 12 fichas, 2424 tokens, zenith-keeper) quedó en **train**: es el único grupo de su estrato, así que no hay nada que retener sin vaciarlo.

**Por proyecto** (tokens y % dentro de cada split; última columna = eval_section / (train + eval_section)):

| Proyecto | train | eval_section | eval_project | eval_section |
|---|---|---|---|---|
| demand-forecast-docs | 9311 (26.0%) | 2008 (25.8%) | 0 (0.0%) | 17.7% |
| catalog-portfolio-api | 6637 (18.5%) | 1547 (19.9%) | 0 (0.0%) | 18.9% |
| traffic-gate-api | 6132 (17.1%) | 1517 (19.5%) | 0 (0.0%) | 19.8% |
| zenith-keeper | 4336 (12.1%) | 521 (6.7%) | 0 (0.0%) | 10.7% |
| vendor-stockkeeper-api | 3599 (10.0%) | 992 (12.7%) | 0 (0.0%) | 21.6% |
| payment-promise-gateway | 3363 (9.4%) | 756 (9.7%) | 0 (0.0%) | 18.4% |
| order-workflow-api | 0 (0.0%) | 0 (0.0%) | 4102 (100.0%) | — |
| 2p-revenue-optimizer-api | 1279 (3.6%) | 342 (4.4%) | 0 (0.0%) | 21.1% |
| price-engine-api | 819 (2.3%) | 0 (0.0%) | 0 (0.0%) | 0.0% |
| unified-transaction-configs | 380 (1.1%) | 104 (1.3%) | 0 (0.0%) | 21.5% |

**Por idioma:**

| Idioma | train | eval_section | eval_project | eval_section |
|---|---|---|---|---|
| en | 24190 (67.5%) | 5217 (67.0%) | 4037 (98.4%) | 17.7% |
| es | 7068 (19.7%) | 1393 (17.9%) | 0 (0.0%) | 16.5% |
| unknown | 4407 (12.3%) | 744 (9.6%) | 65 (1.6%) | 14.4% |
| mixed | 191 (0.5%) | 433 (5.6%) | 0 (0.0%) | 69.4% |

**Por source_type:**

| Tipo | train | eval_section | eval_project | eval_section |
|---|---|---|---|---|
| markdown | 31747 (88.5%) | 6792 (87.2%) | 4102 (100.0%) | 17.6% |
| openapi | 4109 (11.5%) | 995 (12.8%) | 0 (0.0%) | 19.5% |

El idioma no es una dimensión de estratificación aparte: depende casi por completo del proyecto (en español: price-engine-api, traffic-gate-api, unified-transaction-configs), así que estratificar por proyecto ya lo balancea; agregarlo crearía estratos de 1–2 fichas.

## 3. Estabilidad y manifiesto

Origen de cada asignación en esta corrida: kept 181, held_out 16 (desde el manifiesto).

**Cambios del conjunto de eval en esta corrida:**

Ninguno.

**Historial de cambios del conjunto de eval** (guardado en el manifiesto, versionado):

1. el grupo `sg-ac1600e0130e` une contenido de splits distintos (`sg-1e48b23f1af1` (train), `sg-ac1600e0130e` (eval_section)) y va a **train** para no filtrar; pasan de eval a train 1 fichas: `ck-39f4a64f770731ce`
2. el grupo `sg-4c97d3c309dc` une contenido de splits distintos (`sg-3657ccb5478f` (eval_section), `sg-4c97d3c309dc` (train)) y va a **train** para no filtrar; pasan de eval a train 1 fichas: `ck-524c5b21f77c6bdc` (secciones: `catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/local-development.md#002`, `catalog-portfolio-api/latest/guide/setup/local-development.md#002`)

**Por qué cuota en orden de hash + manifiesto, y no hash puro.** Con hash puro cada grupo decide solo (`h(grupo) < fracción`): es perfectamente estable y, con muchos grupos, la ley de los grandes números deja la proporción cerca del objetivo en cada estrato, así que a escala bastaría. Acá la muestra es chica (181 grupos de tamaños muy desiguales): simulando 200 semillas, el hash puro deja eval_section entre **7% y 33%** de los tokens (media 17%). La cuota por estrato fija la proporción; el manifiesto recupera la estabilidad (los grupos asignados no se mueven al llegar documentos nuevos).

## 4. Auditoría de fuga dura

| Chequeo | Casos | Resultado |
|---|---|---|
| split_group en más de un split | 0 | ✅ |
| cluster_id en más de un split | 0 | ✅ |
| Fichas sin split | 0 | ✅ |
| Fichas de order-workflow-api fuera de eval_project | 0 | ✅ |

**Resultado: ✅ sin fuga dura.**

## 5. Auditoría de fuga sutil (para revisión, no falla)

### 5.1 Fichas parecidas en splits distintos (Jaccard ≥ 0.3)

- **≥ 0.4941 (umbral de dedup):** 1 pares. Dedup agrupa secciones; una ficha fusionada podría combinarlas de forma que supere el umbral sin compartir cluster.
- **[0.3, 0.4941):** 0 pares — plantilla o contenido compartido que dedup no considera duplicado (la §8 de dedup.md valida esa zona con etiquetas humanas).

| Jaccard | Ficha A | Split A | Ficha B | Split B |
|---|---|---|---|---|
| 0.543 | zenith-keeper/1.1.6/specs/swagger.yaml › POST /api/v1/fresh-products/orders | train | zenith-keeper/1.1.6/specs/swagger.yaml › PUT /api/v1/fresh-products/orders{idOrder} | eval_section |

### 5.2 Endpoints del swagger mencionados en un .md de otro split

3 casos (mismo proyecto; el path del .md coincide con el del swagger o es un sufijo de ≥ 2 segmentos, con `{param}` normalizado). Una pregunta de eval sobre la operación puede responderse con lo visto en train.

| Proyecto | Endpoint (swagger) | Split | Mención en .md | Ficha .md | Split |
|---|---|---|---|---|---|
| traffic-gate-api | PUT /v1/whitelist | eval_section | /v1/whitelist | traffic-gate-api/latest/guide/sections/processes.md (parte 1) | train |
| traffic-gate-api | PUT /v1/whitelist | eval_section | /v1/whitelist | traffic-gate-api/latest/guide/sections/processes.md (parte 3) | train |
| zenith-keeper | GET /api/v1/fresh-products/list-category{category} | eval_section | /fresh-products/list-category{category} | zenith-keeper/1.1.6/guide/use-cases.md (parte 4) | train |

### 5.3 Archivos con fichas en train y en eval_section

19 de 23 archivos con fichas en eval_section también tienen fichas en train (permitido: son secciones distintas, pero comparten contexto).

| Archivo | train | eval_section |
|---|---|---|
| 2p-revenue-optimizer-api/0.2.2/guide/README.md | 5 | 2 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/api-reference/README.md | 5 | 1 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/api-reference/brands.md | 14 | 3 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/architecture/README.md | 6 | 1 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/brand-management/README.md | 7 | 2 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/README.md | 3 | 1 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/local-development.md | 6 | 2 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/troubleshooting/README.md | 9 | 5 |
| demand-forecast-docs/latest/guide/explicabilidad/diarizacion.md | 2 | 3 |
| demand-forecast-docs/latest/guide/overview.md | 13 | 8 |
| payment-promise-gateway/0.0.10-test-crc-migration/guide/README.md | 18 | 1 |
| traffic-gate-api/latest/guide/README.md | 1 | 5 |
| traffic-gate-api/latest/guide/sections/arch.md | 1 | 1 |
| traffic-gate-api/latest/specs/swagger.yaml | 6 | 2 |
| unified-transaction-configs/v0.0.2/guide/howto.md | 3 | 1 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md | 5 | 1 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/api.md | 2 | 3 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/important.md | 5 | 2 |
| zenith-keeper/1.1.6/specs/swagger.yaml | 10 | 4 |

## 6. Ejemplos

### eval_section y su vecina de train (mismo archivo)

`ck-79e5c9e8c7bb9c7b` · **eval_section** · 139 tokens · `sg-50dc3c2b44de`

````markdown
2p-revenue-optimizer-api › guide/README.md › Spring Boot App model for Java 17 › Usage › Web Server · Main · Error Handling
Versions: 0.0.3-rc-1, 0.2.2

### Web Server

Each Spring Boot web application includes an embedded web server. For servlet stack applications, Its supports three web Servers:
  * Tomcat (`spring-boot-starter-tomcat`)
  * Jetty (`spring-boot-starter-jetty`)
  * Undertow (`spring-boot-starter-undertow`)

This project is configured with Jetty, but to exchange WebServer, it is enough to configure the dependencies mentioned above in the build.gradle file.

… (7 líneas más)
````

`ck-1fac073cbdeae5a4` · **train** · 162 tokens · `sg-6832a2422e4a`

````markdown
2p-revenue-optimizer-api › guide/README.md › Spring Boot App model for Java 17 › Release Process › Usage · Questions
Versions: 0.0.3-rc-1, 0.2.2

### Usage

1. Specify the correct tag for your app in your `Dockerfile` and `Dockerfile.runtime`, according to the desired Java runtime version.

```
# Dockerfile
FROM hub.vendorflow-cloud.io/vendorflow/java:17-mini
```

… (14 líneas más)
````

### eval_project

`ck-7670fef69e3105ca` · **eval_project** · 272 tokens · `sg-604d77af424c`

````markdown
order-workflow-api › guide/use-cases.md › Use cases › Workflow (part 2/3)
Versions: 5.6.2-hotfix-1

```mermaid
    sequenceDiagram
    participant C as Configs API
    participant D as Database
    participant W as Workflow API
    participant G as Github Proxy

    C->>W: Edit workflow message
    activate W
… (32 líneas más)
````

### Par sutil más alto (Jaccard 0.543)

`ck-4578804c98be6225` · **train** · 177 tokens · `sg-6df7e7910227`

````markdown
zenith-keeper › specs/swagger.yaml › POST /api/v1/fresh-products/orders
Versions: 1.1.6

## POST /api/v1/fresh-products/orders

Inserts order with products list

Operation ID: addProductListOrder
Tags: Products
Servers: http://localhost:8080

Request body (required):
… (16 líneas más)
````

`ck-7358ba628c78ba20` · **eval_section** · 195 tokens · `sg-87503ec28c81`

````markdown
zenith-keeper › specs/swagger.yaml › PUT /api/v1/fresh-products/orders{idOrder}
Versions: 1.1.6

## PUT /api/v1/fresh-products/orders{idOrder}

Update order with products list

Operation ID: updateExistProductListOrder
Tags: Products
Servers: http://localhost:8080

Parameters:
… (19 líneas más)
````


## 7. Validación para entrenamiento (no se crea acá)

Se saca de `train` con el mismo algoritmo y una sal distinta, así también respeta split_groups enteros: ordenar los grupos de train de cada estrato por `sha256(seed|val|split_group)` y tomar ~10% de los tokens. Las Q&A heredan el split de su ficha, así que la validación no comparte clusters con train ni con los eval.
