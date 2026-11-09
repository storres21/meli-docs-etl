<!--
qa_retry v1 — único reintento de qa_generate / qa_unanswerable cuando la respuesta trae JSON
inválido o (solo llm) evidencia no literal. Repite el pedido original, muestra la respuesta
anterior y los errores concretos, y pide solo las preguntas que faltan.
Variables: original_system, original_request, previous, errors, kept, n.
-->
## system
{{original_system}}

## user
{{original_request}}

---

Your previous reply was:
<previous>
{{previous}}
</previous>

It had these problems:
{{errors}}

Questions already accepted (do not repeat them or ask about the same fact):
{{kept}}

Write exactly {{n}} new question(s) that fix these problems, following all the rules above. If "evidence" is required, copy it character by character from the fragment between the <doc> tags. Reply with JSON only, in the same format as requested above.
