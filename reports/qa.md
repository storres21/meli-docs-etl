# QA: preguntas ancladas a fichas

Generado por `meli-etl qa` desde `outputs/corpus.jsonl` (235 fichas). Salida: `outputs/qa.jsonl`. Proveedor `ollama`; generador `qwen2.5:7b`, juez `llama3.1:8b` (familias distintas para reducir la auto-aprobación); temperatura 0. Respuestas del LLM cacheadas en `data/cache/llm/` (la etapa se reproduce sin red).

Prompts: `qa_generate.v1` (sha `baa607ec1a66`), `qa_unanswerable.v1` (sha `6e9652e6743d`), `qa_judge.v1` (sha `3a2a949cedf4`), `qa_judge_unanswerable.v1` (sha `0f4e48e4b7e7`); OpenAPI: plantillas deterministas `openapi_template.v1`.

## 1. Conteos

| Split | llm | openapi | unanswerable | Total |
|---|---|---|---|---|
| train | 72 | 39 | 23 | 134 |
| eval_section | 17 | 15 | 9 | 41 |
| eval_project | 6 | 0 | 2 | 8 |
| **Total** | 95 | 54 | 34 | 183 |

**Por proyecto:**

| Proyecto | train | eval_section | eval_project | Total |
|---|---|---|---|---|
| 2p-revenue-optimizer-api | 5 | 1 | 0 | 6 |
| catalog-portfolio-api | 28 | 11 | 0 | 39 |
| demand-forecast-docs | 10 | 6 | 0 | 16 |
| order-workflow-api | 0 | 0 | 8 | 8 |
| payment-promise-gateway | 17 | 0 | 0 | 17 |
| price-engine-api | 3 | 0 | 0 | 3 |
| traffic-gate-api | 25 | 5 | 0 | 30 |
| unified-transaction-configs | 2 | 0 | 0 | 2 |
| vendor-stockkeeper-api | 9 | 6 | 0 | 15 |
| zenith-keeper | 35 | 12 | 0 | 47 |

**Por idioma** (idioma de la pregunta = idioma de la ficha):

| Idioma | llm | openapi | unanswerable | Total |
|---|---|---|---|---|
| en | 84 | 37 | 29 | 150 |
| es | 11 | 17 | 5 | 33 |

Origen del idioma: 133 preguntas de fichas es/en, 50 de fichas `unknown`/`mixed` resueltas con el idioma mayoritario de su proyecto, 0 con el default (`qa.default_language = en`).

**Tipo de respuesta y verificador** (útil para RL con recompensa verificable):

| answer_type | verifier | Preguntas |
|---|---|---|
| long | — | 89 |
| short | exact | 23 |
| short | normalized | 40 |
| short | set | 31 |

## 2. Embudo de descartes

Orden de los filtros: JSON inválido → evidencia no literal (solo `llm`) → trivial → ambigua → casi-duplicada → juez. `openapi` es determinista: no pasa por los filtros ni por el juez. Casi-duplicadas: Jaccard de palabras de contenido ≥ 0.8; el juez exige cada criterio ≥ 3.

| Tipo | Generadas | json_invalido | evidencia_no_literal | trivial | ambigua | casi_duplicada | casi_duplicada_entre_splits | juez_json_invalido | juez_respondible | juez_puntaje_bajo | Final |
|---|---|---|---|---|---|---|---|---|---|---|---|
| llm | 210 | 10 | 40 |  | 3 | 2 | 1 |  |  | 59 | 95 |
| openapi | 54 |  |  |  |  |  |  |  |  |  | 54 |
| unanswerable | 38 |  |  |  | 1 |  |  | 2 |  | 1 | 34 |

Evidencia aceptada solo colapsando espacios en blanco: 11 (el resto es literal exacta).

## 3. Casi-duplicadas entre splits (descartadas de eval)

Se conserva la de train (o la del split que va primero) y se descarta la de eval, para que eval no pregunte lo mismo que train.

| Jaccard | Descartada | Split | Conservada | Split |
|---|---|---|---|---|
| 0.83 | What is the required parameter for the GET /{brandId} endpoint? | eval_section | What is the required parameter for the GET /{brandId}/activable endpoint? | train |

## 4. Riesgo de fuga (`leak_risk = true`)

Preguntas de eval sobre fichas cuyo endpoint también aparece en una ficha de train (auditoría §5.2 de `reports/split.md`): un modelo entrenado en train puede responderlas sin haber aprendido la ficha. Se conservan, marcadas, para poder excluirlas o reportarlas aparte en `evaluate`. Total: 6.

| qa_id | Split | Tipo | Endpoint | Mención en train | Pregunta |
|---|---|---|---|---|---|
| qa-7b7757160d025b1c | eval_section | openapi | PUT /v1/whitelist | /v1/whitelist | ¿Qué método HTTP y qué path usa la operación `whitelistIP` de la API traffic-gate-api? |
| qa-94bb3b2c638f3fa4 | eval_section | openapi | PUT /v1/whitelist | /v1/whitelist | ¿Qué códigos de respuesta HTTP documenta `PUT /v1/whitelist` de la API traffic-gate-api? |
| qa-0c0cdb1199576bc7 | eval_section | openapi | GET /api/v1/fresh-products/list-category{category} | /fresh-products/list-category{category} | Which HTTP method and path does the `productListForCategory` operation of the zenith-keep… |
| qa-d80d72f736c82420 | eval_section | openapi | GET /api/v1/fresh-products/list-category{category} | /fresh-products/list-category{category} | Which parameters are required by `GET /api/v1/fresh-products/list-category{category}` in … |
| qa-d9410ab215e8183f | eval_section | openapi | GET /api/v1/fresh-products/list-category{category} | /fresh-products/list-category{category} | Which HTTP response codes are documented for `GET /api/v1/fresh-products/list-category{ca… |
| qa-f2b7892995335229 | eval_section | unanswerable | GET /api/v1/fresh-products/list-category{category} | /fresh-products/list-category{category} | What is the default sorting order for the products list when no additional parameters are… |

## 5. LLM-juez

| Tipo | Juzgadas | faithfulness | clarity | usefulness | Respondible (descartada) | Aprobadas |
|---|---|---|---|---|---|---|
| llm | 154 | 3.23 | 4.48 | 4.44 | — | 62% |
| unanswerable | 35 | — | 4.83 | 4.74 | 0 | 97% |

## 6. Acuerdo juez-humano

Sin etiquetas todavía. `meli-etl label-qa` exporta una muestra de 30 preguntas juzgadas (estratificada por tipo y veredicto del juez, sin mostrar sus puntajes) a `data/labels/qa_review.md`; completá `data/labels/qa_judge_labels.csv` y volvé a correr `meli-etl qa`.

## 7. Ejemplos

### llm

`qa-03b196b135b5b6c4` · llm · train · en · `ck-f39f891b90b7ac3a` (payment-promise-gateway/0.0.10-test-crc-migration/guide/README.md)

- **Pregunta:** Which version of Java is used in the payment-promise-gateway project?
- **Respuesta:** Java 17
- **Evidencia:** `- **Language**: Java 17`
- **reference_answer** (normalized): `"Java 17"`
- **Juez:** {'faithfulness': 5, 'clarity': 5, 'usefulness': 5}

`qa-055cfd2f44267f9f` · llm · eval_section · en · `ck-a65d35c3e7dacc3c` (2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_row.md)

- **Pregunta:** What type of key is the 'id' field in the rule_row table?
- **Respuesta:** The 'id' field is an auto-increment primary key.
- **Evidencia:** `| id | bigint | Not null | Auto-increment primary key |`
- **Juez:** {'faithfulness': 5, 'clarity': 5, 'usefulness': 5}

### openapi

`qa-07c8abe4901a8c01` · openapi · train · en · `ck-7f8fbf3dbd31f19f` (zenith-keeper/1.1.6/specs/swagger.yaml)

- **Pregunta:** Which HTTP method and path does the `searchAllProductsBatch` operation of the zenith-keeper API use?
- **Respuesta:** The `searchAllProductsBatch` operation uses `GET /api/v1/fresh-products/list{productId}/{sort}`.
- **Evidencia:** `## GET /api/v1/fresh-products/list{productId}/{sort}`
- **Evidencia:** `Operation ID: searchAllProductsBatch`
- **reference_answer** (exact): `"GET /api/v1/fresh-products/list{productId}/{sort}"`

`qa-0c0cdb1199576bc7` · openapi · eval_section · en · `ck-d2a47cb9bfc51ffd` (zenith-keeper/1.1.6/specs/swagger.yaml)

- **Pregunta:** Which HTTP method and path does the `productListForCategory` operation of the zenith-keeper API use?
- **Respuesta:** The `productListForCategory` operation uses `GET /api/v1/fresh-products/list-category{category}`.
- **Evidencia:** `## GET /api/v1/fresh-products/list-category{category}`
- **Evidencia:** `Operation ID: productListForCategory`
- **reference_answer** (exact): `"GET /api/v1/fresh-products/list-category{category}"`

### unanswerable

`qa-01c33063d1a7719b` · unanswerable · train · en · `ck-40a2d38030357ea6` (2p-revenue-optimizer-api/0.2.2/guide/README.md)

- **Pregunta:** What is the process for integrating the VendorFlow CLI commands into the Spring Boot application for generating API specs?
- **Respuesta:** The documentation does not specify this.
- **reference_answer** (normalized): `"The documentation does not specify this."`
- **Juez:** {'clarity': 5, 'usefulness': 4, 'answered': False}

`qa-073a47900296e455` · unanswerable · train · es · `ck-27fd01bda376fb06` (traffic-gate-api/latest/guide/sections/processes.md)

- **Pregunta:** ¿Cuál es el tiempo máximo de espera para que se realice la actualización en la tabla execution?
- **Respuesta:** La documentación no lo especifica.
- **reference_answer** (normalized): `"La documentación no lo especifica."`
- **Juez:** {'clarity': 5, 'usefulness': 5, 'answered': False}
