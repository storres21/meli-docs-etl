# Evaluación de retrieval (BM25)

Generado por `meli-etl evaluate` (sin LLM, determinista). BM25 Okapi implementado a mano (k1 = 1.5, b = 0.75, idf no negativo); tokenización: minúsculas y secuencias de letras/dígitos. Se indexa el `contextualized_text` de **todo** el corpus de cada estrategia (los tres splits), como en un RAG real.

- **Preguntas:** 83 de `outputs/qa.jsonl` con split eval y tipo `llm` u `openapi` (64 eval_section, 19 eval_project; 68 llm, 15 openapi). Las `unanswerable` no tienen ficha correcta. 5 tienen `leak_risk`.
- **Acierto** (igual para cualquier estrategia): el chunk recuperado contiene literalmente la `evidence` de la pregunta (espacios normalizados); en `openapi`, el chunk es el de esa operación (proyecto + método + path). Más de un chunk puede acertar (p. ej. contenido repetido entre versiones).
- **Métricas:** Recall@k = fracción de preguntas con un acierto en el top k; MRR = media de 1/rango del primer acierto sobre el ranking completo (0 si ninguno). Baseline aleatorio: permutación con semilla `42|estrategia|qa_id`.

## 1. Estrategias

| Estrategia | Chunks | Tokens medios | Preguntas sin ningún chunk que acierte |
|---|---|---|---|
| section | 256 | 186 | 0 |
| section_split | 287 | 166 | 0 |
| merged | 235 | 203 | 0 |

## 2. Resultados: todas las preguntas

| Estrategia | Método | Split | n | R@1 | R@5 | R@10 | MRR |
|---|---|---|---|---|---|---|---|
| **section** | bm25 | eval_section | 64 | 0.719 | 0.891 | 0.953 | 0.807 |
| **section** | bm25 | eval_project | 19 | 0.737 | 0.842 | 0.947 | 0.800 |
| **section** | bm25 | total | 83 | 0.723 | 0.880 | 0.952 | 0.805 |
| section | aleatorio | eval_section | 64 | 0.016 | 0.031 | 0.047 | 0.033 |
| section | aleatorio | eval_project | 19 | 0.000 | 0.000 | 0.053 | 0.014 |
| section | aleatorio | total | 83 | 0.012 | 0.024 | 0.048 | 0.029 |
| **section_split** | bm25 | eval_section | 64 | 0.688 | 0.922 | 0.953 | 0.793 |
| **section_split** | bm25 | eval_project | 19 | 0.684 | 0.947 | 1.000 | 0.777 |
| **section_split** | bm25 | total | 83 | 0.687 | 0.928 | 0.964 | 0.790 |
| section_split | aleatorio | eval_section | 64 | 0.000 | 0.016 | 0.016 | 0.017 |
| section_split | aleatorio | eval_project | 19 | 0.000 | 0.053 | 0.053 | 0.023 |
| section_split | aleatorio | total | 83 | 0.000 | 0.024 | 0.024 | 0.019 |
| **merged** | bm25 | eval_section | 64 | 0.688 | 0.922 | 0.938 | 0.795 |
| **merged** | bm25 | eval_project | 19 | 0.737 | 0.947 | 1.000 | 0.832 |
| **merged** | bm25 | total | 83 | 0.699 | 0.928 | 0.952 | 0.803 |
| merged | aleatorio | eval_section | 64 | 0.016 | 0.047 | 0.078 | 0.046 |
| merged | aleatorio | eval_project | 19 | 0.000 | 0.000 | 0.000 | 0.015 |
| merged | aleatorio | total | 83 | 0.012 | 0.036 | 0.060 | 0.039 |

## 3. Resultados: sin las preguntas `leak_risk`

| Estrategia | Método | Split | n | R@1 | R@5 | R@10 | MRR |
|---|---|---|---|---|---|---|---|
| **section** | bm25 | eval_section | 59 | 0.695 | 0.881 | 0.949 | 0.790 |
| **section** | bm25 | eval_project | 19 | 0.737 | 0.842 | 0.947 | 0.800 |
| **section** | bm25 | total | 78 | 0.705 | 0.872 | 0.949 | 0.793 |
| section | aleatorio | eval_section | 59 | 0.017 | 0.017 | 0.034 | 0.031 |
| section | aleatorio | eval_project | 19 | 0.000 | 0.000 | 0.053 | 0.014 |
| section | aleatorio | total | 78 | 0.013 | 0.013 | 0.038 | 0.027 |
| **section_split** | bm25 | eval_section | 59 | 0.678 | 0.915 | 0.949 | 0.784 |
| **section_split** | bm25 | eval_project | 19 | 0.684 | 0.947 | 1.000 | 0.777 |
| **section_split** | bm25 | total | 78 | 0.679 | 0.923 | 0.962 | 0.783 |
| section_split | aleatorio | eval_section | 59 | 0.000 | 0.017 | 0.017 | 0.018 |
| section_split | aleatorio | eval_project | 19 | 0.000 | 0.053 | 0.053 | 0.023 |
| section_split | aleatorio | total | 78 | 0.000 | 0.026 | 0.026 | 0.019 |
| **merged** | bm25 | eval_section | 59 | 0.678 | 0.915 | 0.932 | 0.786 |
| **merged** | bm25 | eval_project | 19 | 0.737 | 0.947 | 1.000 | 0.832 |
| **merged** | bm25 | total | 78 | 0.692 | 0.923 | 0.949 | 0.797 |
| merged | aleatorio | eval_section | 59 | 0.000 | 0.034 | 0.068 | 0.032 |
| merged | aleatorio | eval_project | 19 | 0.000 | 0.000 | 0.000 | 0.015 |
| merged | aleatorio | total | 78 | 0.000 | 0.026 | 0.051 | 0.028 |

## 4. Conclusión: qué estrategia conviene

**merged** (MRR 0.797, R@5 0.923, R@10 0.949 sin `leak_risk`; aleatorio: MRR 0.028). Orden por MRR: merged (0.797) > section (0.793) > section_split (0.783).

- **Tamaño de chunk:** section ≈ 186 tokens, section_split ≈ 166 tokens, merged ≈ 203 tokens. Con BM25, un chunk más grande junta más términos de la pregunta (título, proyecto y cuerpo en el mismo documento) pero la normalización por largo (b) lo penaliza; un chunk chico es más preciso pero puede quedarse sin el contexto que nombra la pregunta.
- **Chunks partidos:** preguntas sin ningún chunk que contenga su evidencia: section 0, section_split 0, merged 0. Una evidencia cortada entre dos chunks es un fallo seguro, independiente del ranking.
- **Empate técnico** con `section` (ΔMRR +0.004, menos de lo que mueve una pregunta, 0.012): la elección se apoya en +0.051 de R@5 y en que es la estrategia del entregable (`outputs/corpus.jsonl`); no hay evidencia para preferir una sobre otra en calidad de retrieval.
- **Sesgo a tener en cuenta:** las preguntas `llm` se generaron leyendo fichas `merged`, así que su vocabulario sigue esos límites de chunk (el criterio de acierto por evidencia sí es neutral entre estrategias).
- **Recomendación:** usar `merged` como retriever de los brazos con RAG del plan de experimentos (`reports/experiment_plan.md`). Con 83 preguntas, una sola pregunta mueve el Recall 1.2%.

## 5. eval_section vs eval_project

| Split | n | R@1 | R@5 | R@10 | MRR |
|---|---|---|---|---|---|
| eval_section | 59 | 0.678 | 0.915 | 0.932 | 0.786 |
| eval_project | 19 | 0.737 | 0.947 | 1.000 | 0.832 |

Con `merged` y sin `leak_risk`, eval_project tiene MRR +0.046 respecto de eval_section. Para un retriever léxico sin entrenamiento las dos son el mismo problema (buscar en todo el corpus, que incluye el proyecto retenido): BM25 no aprende de train, así que "proyecto nunca visto" no lo afecta. La diferencia viene de la composición: eval_project es un solo proyecto (0 preguntas openapi de 19); eval_section mezcla secciones de los otros proyectos (10 openapi de 59). La distinción importa para los modelos entrenados del plan de experimentos. Con 19 preguntas en eval_project, el intervalo de confianza es amplio.

## 6. Efecto de quitar `leak_risk`

| Estrategia | n (todas) | n (sin leak) | MRR todas | MRR sin leak | Δ |
|---|---|---|---|---|---|
| section | 64 | 59 | 0.807 | 0.790 | -0.016 |
| section_split | 64 | 59 | 0.793 | 0.784 | -0.009 |
| merged | 64 | 59 | 0.795 | 0.786 | -0.009 |

Las 5 preguntas `leak_risk` son todas de eval_section (eval_project no tiene). Con `merged`, sus rangos del primer acierto: 1, 2, 1, 1, 1. `leak_risk` señala riesgo de **memorización** (el endpoint aparece en una ficha de train): afecta a un modelo entrenado, no a BM25, que no aprende nada de train. Acá el efecto es solo de composición de la muestra; en el plan de experimentos se reportan aparte.

## 7. Ejemplos de fallos (`merged`, BM25)

Los 5 peores fallos en el top 1 (rango del primer acierto más alto). Fallos en el top 10: 4 de 83. El diagnóstico es una heurística léxica (primera causa que aplica).

**1. `qa-34fe188f6d3dfefc`** · eval_section · openapi · rango del primer acierto: 18

- Pregunta: ¿Qué método HTTP y qué path usa la operación `getBlockedIP` de la API traffic-gate-api?
- Esperada: traffic-gate-api › specs/swagger.yaml › POST /v1/blocked/ip
- Top-1: traffic-gate-api › guide/sections/processes.md › Procesos de Whitelist y Purga › Encolamiento de IPs Bloquead…
- Diagnóstico: poca superposición léxica: solo 46% de los términos de la pregunta están en la ficha correcta (parafraseo); la correcta queda en el puesto 18.

**2. `qa-6261dc6bc5a389a9`** · eval_section · llm · rango del primer acierto: 13

- Pregunta: What is the expected response status code when the Feed Consumer is called successfully?
- Esperada: vendor-stockkeeper-api › guide/api.md › Domain › Services › Feed Consumer
- Top-1: vendor-stockkeeper-api › guide/alerts.md › Alerts › How to resolve › [IMPORTANT] Stockkeeper-api - Error rest…
- Diagnóstico: la pregunta no nombra el proyecto (vendor-stockkeeper-api) y compite con otras páginas del proyecto sin un término que la distinga; la correcta queda en el puesto 13.

**3. `qa-d334c81a450817ba`** · eval_section · llm · rango del primer acierto: 13

- Pregunta: Which version of MySQL is needed for the project?
- Esperada: catalog-portfolio-api › guide/setup/local-development.md › Local Development Setup › Prerequisites
- Top-1: demand-forecast-docs › guide/overview.md › Getting to know our tooling › Retail Data Framework › Creating wor…
- Diagnóstico: la pregunta no nombra el proyecto (catalog-portfolio-api) y compite con páginas parecidas de otros proyectos (top-1: demand-forecast-docs); la correcta queda en el puesto 13.

**4. `qa-5341d9d0cd534be5`** · eval_section · llm · rango del primer acierto: 11

- Pregunta: How is statelessness implemented in the catalog-portfolio-api to enhance scalability?
- Esperada: catalog-portfolio-api › guide/architecture/README.md › Architecture Overview › Key Architectural Principles ›…
- Top-1: catalog-portfolio-api › guide/architecture/README.md › Architecture Overview › System Overview
- Diagnóstico: la top-1 es otra sección del mismo archivo, con vocabulario casi igual; la correcta queda en el puesto 11.

**5. `qa-550c107b4b6f8ccc`** · eval_project · llm · rango del primer acierto: 7

- Pregunta: What is the URL for the New Relic dashboard of the order-workflow-api application?
- Esperada: order-workflow-api › guide/README.md › Getting started
- Top-1: order-workflow-api › guide/services/bigq.md › BigQ › Messages › Validate a pipeline
- Diagnóstico: poca superposición léxica: solo 38% de los términos de la pregunta están en la ficha correcta (parafraseo); la correcta queda en el puesto 7.

## 8. Calidad del dataset Q&A

Sobre `outputs/qa.jsonl` (239 preguntas, todos los splits y tipos) y `outputs/corpus.jsonl` (235 fichas). Sin LLM.

### 8.1 Cobertura: fichas con al menos una pregunta

| Proyecto | train | eval_section | eval_project | % cubiertas |
|---|---|---|---|---|
| 2p-revenue-optimizer-api | 5/8 | 1/3 | — | 55% |
| catalog-portfolio-api | 26/57 | 11/15 | — | 51% |
| demand-forecast-docs | 11/17 | 9/12 | — | 69% |
| order-workflow-api | — | — | 9/18 | 50% |
| payment-promise-gateway | 14/18 | 0/1 | — | 74% |
| price-engine-api | 1/4 | — | — | 25% |
| traffic-gate-api | 17/22 | 7/8 | — | 80% |
| unified-transaction-configs | 2/3 | 0/2 | — | 40% |
| vendor-stockkeeper-api | 8/14 | 5/7 | — | 62% |
| zenith-keeper | 18/22 | 4/4 | — | 85% |
| **Total** | 102/165 | 37/52 | 9/18 | 63% |

**Fichas sin preguntas: 87** (19 por ser más cortas que `qa.min_tokens`; el resto perdió todas sus candidatas en los filtros o el juez).

<details><summary>Lista</summary>

| Ficha | Proyecto | Split | Tokens | Ubicación | Motivo |
|---|---|---|---|---|---|
| `ck-79e5c9e8c7bb9c7b` | 2p-revenue-optimizer-api | eval_section | 139 | guide/README.md › Spring Boot App model for Java 17 › Usage › Web Ser… | descartadas: ambigua 2, juez_puntaje_bajo 1 |
| `ck-edccd0ce85826920` | 2p-revenue-optimizer-api | eval_section | 49 | guide/README.md › Spring Boot App model for Java 17 | descartadas: evidencia_no_literal 1, juez_puntaje_bajo 2 |
| `ck-1fac073cbdeae5a4` | 2p-revenue-optimizer-api | train | 162 | guide/README.md › Spring Boot App model for Java 17 › Release Process… | descartadas: evidencia_no_literal 1 |
| `ck-4e3647d5560abc07` | 2p-revenue-optimizer-api | train | 179 | guide/README.md › Spring Boot App model for Java 17 › Usage › SCOPE | descartadas: juez_puntaje_bajo 1 |
| `ck-977fd4e8ada6e832` | 2p-revenue-optimizer-api | train | 68 | guide/README.md › Spring Boot App model for Java 17 › API Documentati… | descartadas: juez_puntaje_bajo 1 |
| `ck-1980cb9e138b2aac` | catalog-portfolio-api | eval_section | 57 | guide/troubleshooting/README.md › Troubleshooting › Overview | descartadas: juez_puntaje_bajo 3 |
| `ck-40cade886a92ae1e` | catalog-portfolio-api | eval_section | 29 | guide/api-reference/README.md › API Reference | corta (29 < 32 tokens): no se generan preguntas |
| `ck-4c2ec768937858ee` | catalog-portfolio-api | eval_section | 10 | guide/api-reference/brands.md › Brand Endpoints › Activate Brand | corta (10 < 32 tokens): no se generan preguntas |
| `ck-62597615ef45d7b6` | catalog-portfolio-api | eval_section | 25 | guide/troubleshooting/README.md › Troubleshooting | corta (25 < 32 tokens): no se generan preguntas |
| `ck-0b1793af1f5ee7eb` | catalog-portfolio-api | train | 83 | guide/README.md › Catalog Portfolio API Documentation › 🔍 What You'll… | descartadas: juez_puntaje_bajo 1 |
| `ck-0ccfac81065eb02d` | catalog-portfolio-api | train | 41 | guide/README.md › Catalog Portfolio API Documentation › 🚀 Getting Sta… | descartadas: ambigua 1 |
| `ck-0e9636ac274306f6` | catalog-portfolio-api | train | 14 | guide/api-reference/brands.md › Brand Endpoints › Check Brand Activab… | corta (14 < 32 tokens): no se generan preguntas |
| `ck-18c136b6decc40c0` | catalog-portfolio-api | train | 21 | guide/setup/local-development.md › Local Development Setup | corta (21 < 32 tokens): no se generan preguntas |
| `ck-2221bd858704add5` | catalog-portfolio-api | train | 25 | guide/brand-management/README.md › Brand Management | corta (25 < 32 tokens): no se generan preguntas |
| `ck-2e9527b424188883` | catalog-portfolio-api | train | 56 | guide/setup/README.md › Setup & Installation › Next Steps | descartadas: juez_puntaje_bajo 1 |
| `ck-2fa817312bbbcabb` | catalog-portfolio-api | train | 116 | guide/architecture/README.md › Architecture Overview › Technology Sta… | descartadas: juez_puntaje_bajo 1 |
| `ck-33db17790633e420` | catalog-portfolio-api | train | 11 | guide/api-reference/brands.md › Brand Endpoints › Update Brand | corta (11 < 32 tokens): no se generan preguntas |
| `ck-38292c842f70a445` | catalog-portfolio-api | train | 65 | guide/troubleshooting/README.md › Troubleshooting › Monitoring and Al… | descartadas: juez_puntaje_bajo 1 |
| `ck-39f4a64f770731ce` | catalog-portfolio-api | train | 21 | guide/setup/README.md › Setup & Installation | corta (21 < 32 tokens): no se generan preguntas |
| `ck-524c5b21f77c6bdc` | catalog-portfolio-api | train | 35 | guide/setup/local-development.md › Local Development Setup › Step 1: … | descartadas: evidencia_no_literal 1 |
| `ck-569dff541154f405` | catalog-portfolio-api | train | 57 | guide/architecture/README.md › Architecture Overview › Performance Ch… | descartadas: juez_puntaje_bajo 1 |
| `ck-578efa914227148e` | catalog-portfolio-api | train | 14 | guide/api-reference/brands.md › Brand Endpoints › Delete Brand | corta (14 < 32 tokens): no se generan preguntas |
| `ck-714dc32ad42f0588` | catalog-portfolio-api | train | 11 | guide/api-reference/brands.md › Brand Endpoints › Get Brand | corta (11 < 32 tokens): no se generan preguntas |
| `ck-7a5663600b23de88` | catalog-portfolio-api | train | 68 | guide/api-reference/brands.md › Brand Endpoints › Base URL · Search B… | descartadas: juez_puntaje_bajo 1 |
| `ck-7ef1f122d8e77541` | catalog-portfolio-api | train | 38 | guide/README.md › Catalog Portfolio API Documentation | descartadas: evidencia_no_literal 1 |
| `ck-8e2c4aae97752189` | catalog-portfolio-api | train | 72 | guide/README.md › Catalog Portfolio API Documentation › 🛠️ Local Deve… | descartadas: evidencia_no_literal 1 |
| `ck-91262d147de79472` | catalog-portfolio-api | train | 19 | guide/api-reference/brands.md › Brand Endpoints | corta (19 < 32 tokens): no se generan preguntas |
| `ck-9224202064e22e37` | catalog-portfolio-api | train | 161 | guide/api-reference/brands.md › Brand Endpoints › Delete Brand › `DEL… | descartadas: evidencia_no_literal 1 |
| `ck-96a7d57e456887c6` | catalog-portfolio-api | train | 224 | guide/api-reference/README.md › API Reference › Quick Reference › Cor… | descartadas: evidencia_no_literal 1 |
| `ck-9cd2cdef83e39dd3` | catalog-portfolio-api | train | 12 | guide/api-reference/brands.md › Brand Endpoints › Create Brand | corta (12 < 32 tokens): no se generan preguntas |
| `ck-9fed6a445303042d` | catalog-portfolio-api | train | 22 | guide/architecture/README.md › Architecture Overview | corta (22 < 32 tokens): no se generan preguntas |
| `ck-a0e27f58cfef5924` | catalog-portfolio-api | train | 99 | guide/troubleshooting/README.md › Troubleshooting › Common Error Cate… | descartadas: juez_puntaje_bajo 1 |
| `ck-a516ff5115ba2bdc` | catalog-portfolio-api | train | 164 | guide/troubleshooting/README.md › Troubleshooting › Performance Issue… | descartadas: evidencia_no_literal 1 |
| `ck-a79fc72b3b5435b5` | catalog-portfolio-api | train | 82 | guide/troubleshooting/README.md › Troubleshooting › Debug Strategies … | descartadas: evidencia_no_literal 1 |
| `ck-cd10501906d41a8f` | catalog-portfolio-api | train | 66 | guide/api-reference/brands.md › Brand Endpoints › Rate Limiting | descartadas: juez_puntaje_bajo 1 |
| `ck-d0086ca9e4d64e89` | catalog-portfolio-api | train | 63 | guide/architecture/README.md › Architecture Overview › System Overview | descartadas: juez_puntaje_bajo 1 |
| `ck-d3d51b691c2b9e0c` | catalog-portfolio-api | train | 118 | guide/troubleshooting/README.md › Troubleshooting › Error Code Refere… | descartadas: juez_puntaje_bajo 1 |
| `ck-d52946466ab9717d` | catalog-portfolio-api | train | 96 | guide/README.md › Catalog Portfolio API Documentation › 📖 Documentati… | descartadas: juez_puntaje_bajo 1 |
| `ck-d6c6b6d3f62970b6` | catalog-portfolio-api | train | 205 | guide/brand-management/README.md › Brand Management › Brand States | descartadas: juez_puntaje_bajo 1 |
| `ck-d92b6cf6a140df19` | catalog-portfolio-api | train | 80 | guide/brand-management/README.md › Brand Management › Common Operatio… | sin candidatas registradas |
| `ck-87152c822553a83b` | demand-forecast-docs | eval_section | 65 | guide/overview.md › Overview | descartadas: evidencia_no_literal 2 |
| `ck-d2b96ecb95cc0eca` | demand-forecast-docs | eval_section | 327 | guide/explicabilidad/diarizacion.md › Diarización › Approach › Foreca… | descartadas: evidencia_no_literal 2, juez_puntaje_bajo 1 |
| `ck-fc3cc723c9567ed0` | demand-forecast-docs | eval_section | 205 | guide/explicabilidad/diarizacion.md › Diarización › Notation · Motiva… | descartadas: evidencia_no_literal 1, juez_puntaje_bajo 2 |
| `ck-016d8dc95cc8c990` | demand-forecast-docs | train | 335 | guide/overview.md › Getting to know our tooling › Retail Data Framewo… | descartadas: juez_puntaje_bajo 1 |
| `ck-0f84300b8cfcf774` | demand-forecast-docs | train | 192 | guide/overview.md › Getting to know our tooling › Retail Data Framewo… | descartadas: juez_puntaje_bajo 1 |
| `ck-3164a847ad80f4f2` | demand-forecast-docs | train | 191 | guide/overview.md › Getting to know our tooling › Retail Data Framewo… | descartadas: juez_puntaje_bajo 1 |
| `ck-32680de790e1eaf6` | demand-forecast-docs | train | 72 | guide/README.md › Welcome to marketplace forecasting technical docume… | descartadas: ambigua 1 |
| `ck-d1324ab6d513358f` | demand-forecast-docs | train | 336 | guide/explicabilidad/diarizacion.md › Diarización › Approach | descartadas: juez_puntaje_bajo 1 |
| `ck-e3a62504006ce539` | demand-forecast-docs | train | 17 | guide/explicabilidad/diarizacion.md › Diarización | corta (17 < 32 tokens): no se generan preguntas |
| `ck-0b18883b531bf53b` | order-workflow-api | eval_project | 373 | guide/use-cases.md › Use cases › Pipeline › Admin | descartadas: evidencia_no_literal 3 |
| `ck-209cc7c77240733b` | order-workflow-api | eval_project | 85 | guide/services/bigq.md › BigQ › Scopes › Test | descartadas: juez_puntaje_bajo 3 |
| `ck-505d10a8c472c348` | order-workflow-api | eval_project | 81 | guide/services/bigq.md › BigQ › Scopes › Production | descartadas: juez_puntaje_bajo 1, trivial 2 |
| `ck-53632696712db1be` | order-workflow-api | eval_project | 166 | guide/use-cases.md › Use cases › Workflow (part 3/3) | descartadas: evidencia_no_literal 3 |
| `ck-55b5c02067e28efc` | order-workflow-api | eval_project | 780 | guide/services/database.md › Database › Objects stored › Workflows | descartadas: juez_puntaje_bajo 1 |
| `ck-5a81d9e786cc363d` | order-workflow-api | eval_project | 18 | guide/use-cases.md › Use cases › Pipeline › Branches | corta (18 < 32 tokens): no se generan preguntas |
| `ck-77924ef083a72756` | order-workflow-api | eval_project | 219 | guide/use-cases.md › Use cases › Workflow (part 1/3) | descartadas: evidencia_no_literal 3 |
| `ck-7d4a78a8b21c6b3e` | order-workflow-api | eval_project | 423 | guide/use-cases.md › Use cases › Pipeline | descartadas: evidencia_no_literal 3 |
| `ck-d5421537ddf2fb6f` | order-workflow-api | eval_project | 30 | guide/usage.md › Usage › API | corta (30 < 32 tokens): no se generan preguntas |
| `ck-faa211d8944da567` | payment-promise-gateway | eval_section | 756 | guide/README.md › Payment Promise Gateway › Example Responses | descartadas: evidencia_no_literal 3 |
| `ck-0c65cad6a59045c5` | payment-promise-gateway | train | 177 | guide/README.md › Payment Promise Gateway › Sequence Diagrams › 4. PO… | descartadas: juez_puntaje_bajo 1 |
| `ck-2a5397d0698524ba` | payment-promise-gateway | train | 39 | guide/README.md › Payment Promise Gateway | descartadas: juez_puntaje_bajo 1 |
| `ck-627fe4c96334dec8` | payment-promise-gateway | train | 120 | guide/README.md › Payment Promise Gateway › Project Structure | descartadas: evidencia_no_literal 1 |
| `ck-a02bf37950ffb8d2` | payment-promise-gateway | train | 296 | guide/README.md › Payment Promise Gateway › Sequence Diagrams › Endpo… | descartadas: casi_duplicada 1 |
| `ck-2caef84585bd20ec` | price-engine-api | train | 43 | guide/contacto.md › Canales de Comunicación | descartadas: evidencia_no_literal 1 |
| `ck-c11626c3d68b191b` | price-engine-api | train | 15 | guide/contacto.md › Contacto | corta (15 < 32 tokens): no se generan preguntas |
| `ck-dd8bf0e5dc43a5a5` | price-engine-api | train | 263 | guide/contacto.md › Contacto › Equipo › Commerce Operations & Support | descartadas: juez_puntaje_bajo 1 |
| `ck-45a962fa73abb05f` | traffic-gate-api | eval_section | 200 | guide/sections/arch.md › Arquitectura › Módulos de la Aplicación | descartadas: evidencia_no_literal 3 |
| `ck-072791bcaf610359` | traffic-gate-api | train | 292 | guide/sections/processes.md › Procesos de Whitelist y Purga › Encolam… | descartadas: juez_puntaje_bajo 1 |
| `ck-3e0952405dfbae7d` | traffic-gate-api | train | 263 | guide/sections/processes.md › Procesos de Whitelist y Purga › Procesa… | descartadas: juez_puntaje_bajo 1 |
| `ck-6112a0bba6b13666` | traffic-gate-api | train | 388 | guide/sections/waf_config.md › Configuración WAF AWS (part 5/5) | descartadas: evidencia_no_literal 1 |
| `ck-d94976c297a352a7` | traffic-gate-api | train | 167 | guide/sections/waf_config.md › Configuración WAF AWS (part 3/5) | descartadas: juez_puntaje_bajo 1 |
| `ck-de50f4e20e85740b` | traffic-gate-api | train | 267 | guide/sections/processes.md › Procesos de Whitelist y Purga › Procesa… | descartadas: juez_puntaje_bajo 1 |
| `ck-0a6c63e488b63957` | unified-transaction-configs | eval_section | 80 | guide/howto.md › Howto › Actualizacion de configuraciones en mobile-f… | descartadas: juez_puntaje_bajo 3 |
| `ck-f54f1712488046a6` | unified-transaction-configs | eval_section | 24 | guide/README.md › Unified transaction configs | corta (24 < 32 tokens): no se generan preguntas |
| `ck-c450629ba507b197` | unified-transaction-configs | train | 193 | guide/howto.md › Howto › Carga de configuracion | descartadas: juez_puntaje_bajo 1 |
| `ck-85e8eebde45c9932` | vendor-stockkeeper-api | eval_section | 84 | guide/important.md › Verification of Items in Inventory Flows › Intro… | descartadas: juez_puntaje_bajo 3 |
| `ck-af3ccc4e9c582c6d` | vendor-stockkeeper-api | eval_section | 134 | guide/alerts.md › Alerts › How to resolve › Validation stock ERROR up… | descartadas: casi_duplicada 1, evidencia_no_literal 1, juez_puntaje_bajo 1 |
| `ck-188acb23df0bc741` | vendor-stockkeeper-api | train | 75 | guide/important.md › Verification of Items in Inventory Flows › Impor… | descartadas: ambigua 1 |
| `ck-1a77c50ed4eabb37` | vendor-stockkeeper-api | train | 185 | guide/alerts.md › Alerts › How to resolve › [IMPORTANT] Stockkeeper-a… | descartadas: juez_puntaje_bajo 1 |
| `ck-61e1b55946e948d0` | vendor-stockkeeper-api | train | 64 | guide/introduction.md › VENDOR STOCKKEEPER API › About | descartadas: juez_puntaje_bajo 1 |
| `ck-c4162d1c009f209c` | vendor-stockkeeper-api | train | 18 | guide/alerts.md › Alerts | corta (18 < 32 tokens): no se generan preguntas |
| `ck-db935ece1d521528` | vendor-stockkeeper-api | train | 75 | guide/important.md › Verification of Items in Inventory Flows › How c… | descartadas: juez_puntaje_bajo 1 |
| `ck-de0c3945f43c94ed` | vendor-stockkeeper-api | train | 216 | guide/alerts.md › Alerts › Alerts | descartadas: juez_puntaje_bajo 1 |
| `ck-019a768e7f735842` | zenith-keeper | train | 258 | guide/use-cases.md › Use cases (part 4/12) | descartadas: juez_puntaje_bajo 1 |
| `ck-24f5746ed048a1ec` | zenith-keeper | train | 205 | guide/use-cases.md › Use cases (part 10/12) | descartadas: juez_puntaje_bajo 1 |
| `ck-3661d6eb09e594ab` | zenith-keeper | train | 170 | guide/use-cases.md › Use cases (part 6/12) | descartadas: casi_duplicada 1 |
| `ck-e9d4aaf5d2fdfa6a` | zenith-keeper | train | 223 | guide/use-cases.md › Use cases (part 9/12) | descartadas: casi_duplicada 1 |

</details>

### 8.2 Balance

**Por fuente y split:**

| Split | llm | openapi | unanswerable | Total |
|---|---|---|---|---|
| train | 83 | 39 | 23 | 145 |
| eval_section | 49 | 15 | 9 | 73 |
| eval_project | 19 | 0 | 2 | 21 |

**Por proyecto y split** (y preguntas por ficha cubierta):

| Proyecto | train | eval_section | eval_project | Total | Preguntas / ficha |
|---|---|---|---|---|---|
| 2p-revenue-optimizer-api | 5 | 2 | 0 | 7 | 1.2 |
| catalog-portfolio-api | 31 | 23 | 0 | 54 | 1.5 |
| demand-forecast-docs | 13 | 17 | 0 | 30 | 1.5 |
| order-workflow-api | 0 | 0 | 21 | 21 | 2.3 |
| payment-promise-gateway | 17 | 0 | 0 | 17 | 1.2 |
| price-engine-api | 3 | 0 | 0 | 3 | 3.0 |
| traffic-gate-api | 28 | 9 | 0 | 37 | 1.5 |
| unified-transaction-configs | 2 | 0 | 0 | 2 | 1.0 |
| vendor-stockkeeper-api | 11 | 10 | 0 | 21 | 1.6 |
| zenith-keeper | 35 | 12 | 0 | 47 | 2.1 |

**Por idioma y split:**

| Idioma | train | eval_section | eval_project |
|---|---|---|---|
| en | 114 | 64 | 21 |
| es | 31 | 9 | 0 |

### 8.3 Diversidad

**Tipo de pregunta** (primera palabra; es/en unificados):

| Tipo | train | eval_section | eval_project | Total | % |
|---|---|---|---|---|---|
| qué | 104 | 52 | 17 | 173 | 72% |
| cuál | 35 | 15 | 2 | 52 | 22% |
| cómo | 3 | 5 | 0 | 8 | 3% |
| cuánto | 2 | 0 | 1 | 3 | 1% |
| dónde | 1 | 1 | 1 | 3 | 1% |

**Casi-duplicadas dentro de cada split** (preguntas con otra del mismo split a Jaccard de palabras de contenido ≥ umbral). Sin `openapi` es lo que controla el filtro de qa (≥ 0.8); con `openapi`, las plantillas deterministas comparten palabras a propósito (cambian el endpoint, no la redacción).

| Split | Preguntas sin openapi | ≥ 0.8 | ≥ 0.5 | ≥ 0.5 con openapi |
|---|---|---|---|---|
| train | 106 | 0.0% | 14.2% | 37.2% |
| eval_section | 58 | 0.0% | 10.3% | 27.4% |
| eval_project | 21 | 0.0% | 9.5% | 9.5% |

### 8.4 Longitudes (tokens, `o200k_base`)

|  | n | mín | p25 | mediana | p95 | máx |
|---|---|---|---|---|---|---|
| pregunta · llm | 151 | 7 | 12 | 14 | 21 | 28 |
| respuesta · llm | 151 | 1 | 9 | 13 | 30 | 232 |
| pregunta · openapi | 54 | 20 | 22 | 25 | 35 | 37 |
| respuesta · openapi | 54 | 6 | 9 | 13 | 30 | 35 |
| pregunta · unanswerable | 34 | 11 | 15 | 17 | 25 | 32 |
| respuesta · unanswerable | 34 | 7 | 7 | 7 | 7 | 7 |

**Casos extremos:**

- Pregunta más corta (7 tokens, `qa-10e3fbfb3f48e39c`): What does the Metrics Dashboard provide?
- Pregunta más larga (37 tokens, `qa-ca00d227dc961293`): ¿Qué códigos de respuesta HTTP documenta `GET /sites/{site_id}/sellers/{seller_id}/services/{service_id}/coverage/v1` de la API price-engine-api?
- Respuesta `llm` más corta (1 tokens, `qa-483e26f78dc147d0`): 409
- Respuesta `llm` más larga (232 tokens, `qa-550c107b4b6f8ccc`): https://one.newrelic.com/launcher/nr1-core.explorer?pane=eyJuZXJkbGV0SWQiOiJhcG0tbmVyZGxldHMub3ZlcnZpZXciLCJlbnRpdHlJZCI6Ik9UZzVOVGcyZkVGUVRYeEJVRkJNU1VOQlZFbF…

### 8.5 Fundamentación

| Tipo | Preguntas | Evidencia literal exacta | Literal con espacios normalizados |
|---|---|---|---|
| llm | 151 | 91% | 100% |
| openapi | 54 | 100% | 100% |
| **Total** | 205 | 93% | 100% |

✅ 205/205 respuestas tienen toda su evidencia literal en la ficha (con espacios normalizados): es invariante del pipeline y lo verifica `tests/test_dataset_integrity.py`. Las `unanswerable` no tienen evidencia por definición.

### 8.6 Fuga y abstención

| Split | Preguntas | `leak_risk` | % `leak_risk` | `unanswerable` | % `unanswerable` |
|---|---|---|---|---|---|
| train | 145 | 0 | 0% | 23 | 16% |
| eval_section | 73 | 6 | 8% | 9 | 12% |
| eval_project | 21 | 0 | 0% | 2 | 10% |

### 8.7 Conclusión: qué le falta al dataset

- **Volumen:** 239 preguntas (94 de eval) alcanzan para medir retrieval y para una prueba de entrenabilidad, no para un SFT con conclusiones finas ni para comparar por proyecto o idioma.
- **Cobertura:** 87 de 235 fichas no tienen preguntas (19 por cortas; el motivo de descarte más común es `juez_puntaje_bajo`, en 43 fichas). Con más tiempo: regenerar esas fichas con más preguntas por ficha o otro prompt, y revisar a mano una muestra de los rechazos del juez (puede ser demasiado estricto con fichas cortas o de listas).
- **Abstención:** solo 2 `unanswerable` en eval_project; la tasa de abstención por split no es estimable. Subir `unanswerable_ratio` en eval y generar preguntas sin respuesta "cercanas" (sobre hechos ausentes de la propia ficha).
- **Verificabilidad:** eval_project tiene 0 preguntas `openapi`; casi toda la señal con verificador exacto está en eval_section. Extraer más respuestas cortas verificables de las `llm` (valores, comandos, nombres).
- **Diversidad:** domina el tipo "qué" (72%). Pedir explícitamente preguntas de procedimiento (cómo), condición (cuándo/por qué) y multi-hop entre fichas del mismo archivo.
- **Idioma:** 40 preguntas en español de 239: el idioma sigue al de la documentación. Si el uso real es en español, generar también preguntas en español sobre fichas en inglés.
- **Calidad del juez:** sin etiquetas humanas todavía; completar `make label-qa` antes de usar sus puntajes como filtro o métrica.
