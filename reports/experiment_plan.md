# Plan de experimentos: SFT sobre la documentación interna

Documento de diseño: no se entrena nada en este repo. Las cifras salen de los entregables
actuales (`outputs/corpus.jsonl`, `outputs/qa.jsonl`) y de `reports/evaluate.md`. Si esos
archivos se regeneran, las cifras de este plan hay que actualizarlas a mano.

## 1. Hipótesis

**H1.** Un SFT ligero con el Q&A de train mejora dos cosas en la documentación interna:

- **Responder fundamentado:** la respuesta es correcta y está respaldada por la
  documentación.
- **Abstenerse cuando no hay respuesta:** "la documentación no lo especifica" en lugar de
  inventar.

La mejora se mide sobre `eval_section` (secciones no vistas de proyectos vistos) y sobre
`eval_project` (un proyecto entero no visto).

**H0 de control.** El SFT no degrada la capacidad general del modelo: su caída en un
benchmark general queda dentro del margen definido en §6.

**H2 (secundaria).** Con contexto recuperado (RAG), el SFT aporta sobre todo
**abstención y formato**, no conocimiento. Sin contexto (closed-book), puede aportar
conocimiento en `eval_section`, pero no en `eval_project`.

## 2. Datos disponibles

| Split | llm | openapi | unanswerable | Total | Tokens del corpus |
|---|---|---|---|---|---|
| train | 83 | 39 | 23 | 145 | ≈ 42 k |
| eval_section | 49 | 15 (5 `leak_risk`) | 9 (1 `leak_risk`) | 73 | ≈ 9,8 k |
| eval_project | 19 | 0 | 2 | 21 | ≈ 4,7 k |

Lo que estas cifras condicionan:

- **El train es chico** (145 ejemplos). El experimento mide si un SFT pequeño y barato
  cambia el comportamiento; no puede inyectar conocimiento de forma robusta.
- **Margen de error.** Con 94 preguntas de eval, una proporción tiene un error estándar de
  ≈ 5 pp (IC 95 % de ± 10 pp). Por eso todas las comparaciones son **pareadas**
  (mismas preguntas en todos los brazos), lo que reduce bastante la varianza.
- **Tamaño mínimo detectable:** con estas cifras, alrededor de 8–10 pp en métricas
  binarias.
- **Abstención:** hay solo 11 `unanswerable` en eval y 2 en `eval_project`. Esta métrica es
  indicativa; el criterio de éxito la usa sobre eval total, no por split.
- **Exactitud verificable:** las preguntas `openapi` solo existen en `eval_section` (15, o
  10 sin `leak_risk`). Las `llm` con respuesta corta verificable son solo 7 en eval y 5 en
  train: casi toda la señal verificable viene de OpenAPI.

## 3. Modelo base: Qwen2.5-7B-Instruct + QLoRA

- **Por qué Qwen2.5-7B-Instruct:**
  - Es un instruct abierto (Apache 2.0) que sigue bien instrucciones en inglés y español,
    los dos idiomas del corpus.
  - Tiene contexto largo: 32 k tokens, de sobra para el top-k de BM25.
  - Es la misma familia que el generador de preguntas (qwen2.5:7b en Ollama). Por eso el
    base ya produce el estilo de respuesta del dataset, y el efecto medido es contenido y
    abstención, no formato.
  - **Riesgo de esa elección:** auto-preferencia del estilo. Lo mitiga que el juez sea de
    otra familia (llama3.1:8b) y que las métricas principales sean verificadores
    automáticos, no el juez.
  - **Alternativa:** Llama-3.1-8B-Instruct, de otra familia. Se puede repetir el brazo D con
    ella como chequeo de robustez.
- **Por qué QLoRA:**
  - Entra en una GPU de 24 GB: base en 4 bits NF4 y adaptadores LoRA en bf16.
  - Con 145 ejemplos, un adaptador de rango bajo (r = 16, α = 32, dropout 0,05, sobre todas
    las proyecciones lineales) limita el sobreajuste y el olvido mejor que un fine-tuning
    completo.
  - El adaptador pesa unos MB y se versiona junto con el dataset.
- **Hiperparámetros de partida:**
  - lr 1e-4, coseno, warmup 5 %, 3 épocas, batch efectivo 16, máx. 2048 tokens.
  - La pérdida se calcula solo sobre el turno del asistente.
  - No hay validación aparte: se separa ~10 % de train por `split_group`, como describe el
    README, para early stopping y para elegir la época.

## 4. Brazos

Todos usan el mismo system prompt, la misma plantilla de chat y la misma decodificación.

| Brazo | Entrenamiento | Contexto en inferencia | Qué aísla |
|---|---|---|---|
| **A** base closed-book | — | ninguno | piso: qué sabe el modelo de documentación que nunca vio |
| **B** base + RAG | — | top-5 BM25 (`merged`, ver `reports/evaluate.md`) | aporte del retrieval solo |
| **C** SFT closed-book | QLoRA sobre `messages_closed_book` de train | ninguno | conocimiento y abstención aprendidos sin contexto |
| **D** SFT + RAG | QLoRA sobre `messages_rag` de train | top-5 BM25 (`merged`) | el sistema propuesto |
| *(opc.)* **E** CPT → SFT + RAG | CPT con LoRA sobre `corpus.jsonl` (solo train, ≈ 42 k tokens, 2 épocas) y luego como D | top-5 BM25 | si leer la documentación antes ayuda al SFT |

Notas de diseño:

- **Desajuste en D.** `messages_rag` se entrena con la **ficha correcta** como contexto,
  pero en inferencia el contexto viene del retriever. Variante D′, estilo RAFT: entrenar con
  la ficha correcta más 2–4 fichas recuperadas por BM25 como distractores y, en ~20 % de
  los ejemplos, sin la ficha correcta, con la respuesta de abstención. Si el presupuesto
  alcanza para un solo brazo con RAG entrenado, D′ es la opción preferida.
- **Contexto de B y D.** Top-5 de BM25 sobre **todo** el corpus (los tres splits), como en
  producción. Si la ficha correcta no aparece en el top-5 (≈ 7 % de las preguntas, según
  `R@5` en `reports/evaluate.md`), una respuesta fiel debería abstenerse. Esos casos se
  reportan aparte.
- **Unanswerable en C y D.** Se incluyen en train (23 ejemplos) con la respuesta localizada.
  Es lo que enseña a abstenerse.

## 5. Métricas (por brazo, sobre `eval_section`, `eval_project` y el total)

1. **Exactitud verificable** en las preguntas `openapi` y en las `llm` con `answer_type =
   short`. Se usa el `verifier` de cada pregunta (`exact`, `set` o `normalized`) contra
   `reference_answer`. Es la métrica más dura y no depende de ningún juez.
2. **Fidelidad a la evidencia** en las `llm`, con dos mediciones:
   - automática: recall de tokens de la `evidence` en la respuesta, más F1 de tokens
     contra `answer`;
   - del juez: puntaje `faithfulness`, 1–5.
   - En B y D se mide además si la respuesta solo usa el contexto dado: el juez recibe ese
     contexto, no la ficha correcta.
3. **Abstención y alucinación:**
   - abstención correcta = fracción de `unanswerable` respondidas con la frase de
     abstención. Se detecta normalizando la respuesta contra las dos frases localizadas más
     una lista corta de variantes;
   - tasa de alucinación = `unanswerable` respondidas con contenido, más `llm`
     respondidas con hechos que el juez marca como no respaldados;
   - abstención indebida = preguntas respondibles en las que el modelo se abstuvo. Sin
     esta métrica, un modelo que siempre se abstiene parecería perfecto.
4. **Puntaje del juez** (llama3.1:8b, rúbrica de `prompts/qa_judge.v1.md`):
   faithfulness, clarity y usefulness. ⚠️ **El juez todavía no está validado contra
   humanos** (`reports/qa.md` §6 sin etiquetas). Antes de usar esta métrica en una
   conclusión hay que completar `make label-qa`. Si el κ juez-humano es < 0,4, el juez
   queda como métrica descriptiva y no entra en el criterio de éxito.
5. **Recall@k del retriever** en B y D: Recall@1/5/10 y MRR de BM25 `merged` sobre las
   mismas preguntas (los de `reports/evaluate.md`). Sirve para separar errores de
   retrieval de errores de generación: la exactitud se reporta condicionada a "ficha
   correcta en el contexto" sí/no.
6. **Control de olvido:** un benchmark general chico corrido igual en A y C/D. Sirve una
   muestra fija de 500 preguntas de MMLU (5-shot) más IFEval completo (541 prompts,
   verificación automática). Se reporta la diferencia respecto de A.

Todas las métricas se reportan **también sin las preguntas `leak_risk`** y por idioma
(es/en).

## 6. Rigor y criterio de éxito

- **Semillas:** 3 semillas de entrenamiento por brazo entrenado (C, D, E); se reportan la
  media y el rango. A y B no se entrenan y usan decodificación greedy, así que son
  deterministas.
- **Intervalos:** bootstrap pareado por pregunta (10 000 remuestreos, semilla fija) para
  cada diferencia entre brazos, con IC 95 %. Con 3 semillas, se remuestrean preguntas y
  semillas juntas.
- **Mismas condiciones:**
  - Todos los brazos usan el mismo system prompt, la misma plantilla y la misma
    decodificación (greedy, temperatura 0, máx. 256 tokens nuevos).
  - B y D reciben exactamente el mismo top-5.
  - Las salidas se cachean igual que en `qa`, por lo que la evaluación se puede volver a
    correr sin GPU.
- **Decontaminación:**
  - Eval nunca entra en train: el split es por `split_group`, sobre un manifiesto
    congelado.
  - Las preguntas casi duplicadas entre splits ya se descartaron del lado de eval
    (`reports/qa.md` §3).
  - `leak_risk` se reporta aparte.
  - El retriever indexa todo el corpus, pero ningún brazo se entrena con fichas de eval.
- **Criterio de éxito (pre-registrado).** H1 se acepta si **D supera a B** en las tres
  cosas siguientes:
  1. exactitud verificable sobre eval total, por ≥ 5 pp con un IC 95 % que excluya 0;
  2. abstención correcta, por ≥ 15 pp sobre eval total, sin aumentar la abstención indebida
     en más de 5 pp;
  3. sin olvido: la caída en MMLU e IFEval es ≤ 2 pp respecto de A.

  Para H2 basta con observar el patrón: C > A en `eval_section`, pero no en
  `eval_project`.
- **Si falla:**
  - **D ≈ B:** el retrieval ya resuelve la tarea y el SFT no aporta.
    1. Mirar las métricas condicionadas al retrieval. Si los errores de D son casos sin la
       ficha en el contexto, el cuello de botella es el retriever: probar híbrido BM25 +
       denso y re-ranking antes que más SFT.
    2. Si D falla con la ficha presente, entrenar D′ (distractores) y aumentar los datos de
       train: más preguntas por ficha y paráfrasis, con el mismo pipeline `qa`.
  - **Mejora la exactitud pero sube la abstención indebida:** rebalancear la proporción de
    `unanswerable` en train.
  - **Hay olvido:** bajar lr o épocas, bajar el rango, o mezclar 20–50 % de datos
    instruct generales en el SFT.
  - **Ninguna variante supera el umbral:** concluir que, con este volumen de datos, RAG sin
    SFT es la opción. Es un resultado válido y más barato.

## 7. Extensión RL (solo diseño)

- **GRPO con recompensa verificable.** Se usan las preguntas `openapi` de train (39) y las
  `llm` con `answer_type = short` (5), 44 prompts en total:
  - recompensa = 1 si el `verifier` acepta la respuesta frente a `reference_answer` y 0 si
    no;
  - 8 muestras por prompt, temperatura 0,8;
  - penalización KL contra el modelo SFT (D) como referencia;
  - una recompensa extra por abstenerse correctamente en las `unanswerable` de train.
- **DPO.** Pares chosen/rejected construidos sin humanos:
  - chosen = la respuesta de referencia;
  - rejected = las respuestas de A (base closed-book) que el verificador o el juez
    marcan como incorrectas o alucinadas;
  - en las `unanswerable`: chosen = la abstención, rejected = la respuesta inventada por A.
- Con este volumen (44 prompts verificables y ≈ 145 pares DPO como mucho), la extensión RL sirve como prueba de concepto de la
  tubería de recompensas. Se evaluaría con las mismas métricas y el mismo criterio que §6.

## 8. Costo, tiempo y riesgos

**Costo y tiempo aproximados** (1 GPU de 24–80 GB, p. ej. L4/A10G/A100; QLoRA requiere
CUDA, en Apple Silicon habría que usar LoRA con MLX):

| Paso | Tiempo | Notas |
|---|---|---|
| SFT C o D (145 ejemplos × 3 épocas) | ~5–10 min por semilla | 3 semillas × 2 brazos ≈ 1 h |
| CPT opcional (≈ 42 k tokens × 2 épocas) | ~5 min | más el SFT encima |
| Inferencia (94 preguntas × 4–5 brazos × 3 semillas) | ~20–30 min | greedy, vLLM o HF generate |
| Benchmark de olvido (MMLU 500 + IFEval 541) × 4 modelos | ~1–2 h | |
| Juez (≈ 1 100 juicios con llama3.1:8b local) | ~2–3 h | cacheado como en `qa` |
| Etiquetado humano del juez (30 preguntas) | ~1 h de una persona | prerequisito del criterio con juez |

Total: menos de un día de cómputo. En la nube, del orden de USD 10–30 (A100 a ~USD 1–2 la
hora). El costo principal es el tiempo de análisis.

**Riesgos:**

- **Pocos datos y mucho ruido.**
  - Con 145 ejemplos de train y 94 de eval, efectos de < 8 pp no se distinguen del ruido.
  - Con 2 `unanswerable` en `eval_project`, la abstención en ese split es anecdótica.
  - Mitigación: comparaciones pareadas, IC bootstrap y criterio pre-registrado sobre eval
    total.
- **Juez sin validar.** Mitigación: el criterio de éxito usa solo verificadores
  automáticos, y el juez entra después de medir el κ juez-humano.
- **Sesgo del generador.** Las preguntas las escribió qwen2.5 y el base es Qwen2.5:
  - el estilo favorece a la familia;
  - las preguntas pueden ser más fáciles para ella.
  - Mitigación: repetir D con Llama-3.1-8B.
- **Memorización vs. comprensión.** C puede memorizar respuestas de train. Las preguntas
  de eval preguntan otros hechos y otras secciones; los casos de `leak_risk` se reportan
  aparte.
- **Techo del retriever.** BM25 deja ~7 % de las preguntas sin la ficha en el top-5, y eso
  limita a B y D por igual. Se reporta el desempeño condicionado al retrieval.
- Una prueba local con mlx-lm en Mac falló porque algunos ejemplos superan los 2048 tokens; para entrenar hay que filtrar o limitar la longitud de secuencia.
- **Desbalance de idioma:** solo 9 preguntas en español en eval, así que no hay potencia
  para conclusiones por idioma.
