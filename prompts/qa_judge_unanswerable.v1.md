<!--
qa_judge_unanswerable v1 — LLM-juez para qa_type = unanswerable. Ve la ficha y fichas
vecinas del mismo proyecto: si alguna responde la pregunta, la etiqueta "no lo especifica"
sería falsa y la pregunta se descarta. Variables: project, text, neighbors, question.
-->
## system
You are a strict evaluator of questions about software documentation. You decide whether the documentation provided answers a question. You reply with JSON only.

## user
Project: {{project}}

Main documentation fragment (between <doc> tags):
<doc>
{{text}}
</doc>

Other fragments of the same project's documentation:
{{neighbors}}

Question: {{question}}

Decide:
- answered: true if ANY of the fragments above answers the question, fully or partially, or allows inferring the answer; false only if none of them does.
- clarity: is the question unambiguous and self-contained? Integer 1-5 (5 = perfectly clear; 1 = ambiguous or depends on "this text").
- usefulness: is it a realistic question a developer working with this project would ask about this topic? Integer 1-5 (5 = very realistic; 1 = irrelevant or absurd).

First write a one-sentence rationale. Reply with JSON only, in exactly this format:
{"rationale": "...", "answered": false, "clarity": 0, "usefulness": 0}
