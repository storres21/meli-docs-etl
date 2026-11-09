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
