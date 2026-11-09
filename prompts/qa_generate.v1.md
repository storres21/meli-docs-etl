<!--
qa_generate v1 — preguntas y respuestas ancladas a una ficha (qa_type = llm).
Variables: project, location, text, n, language_name, short_max.
Instrucciones en inglés (los modelos chicos las siguen mejor); el idioma de salida va
explícito en language_name. Cambiar este archivo invalida su cache (el hash está en la clave).
-->
## system
You write question-answer pairs used to train and evaluate assistants on internal software documentation. You only use information present in the documentation fragment you are given. You reply with JSON only.

## user
Project: {{project}}
Location: {{location}}

Documentation fragment (between <doc> tags):
<doc>
{{text}}
</doc>

Write exactly {{n}} question(s) in {{language_name}} about this fragment, following these rules:
1. Self-contained: the question must make sense to someone who has NOT seen the fragment. Name the project ({{project}}) or the specific component, endpoint, command or concept. Never refer to "this document", "this section", "the text", "the fragment", "the above" (nor "este documento", "esta sección", "el texto", "según el fragmento").
2. Answerable only with the fragment. Do not use outside knowledge.
3. Not trivial: do not just turn a heading into a question, and the answer must not appear in the question. Prefer facts a developer needs: values, commands, steps, behaviors, conditions, errors.
4. "answer": a complete and faithful answer in {{language_name}} (1 to 3 sentences).
5. "evidence": an EXACT, verbatim copy of one contiguous span of the fragment (one sentence or one line, at most about 200 characters) that supports the answer. Copy the characters exactly as they appear, including markdown symbols such as `, *, | and #. Do not paraphrase, translate, shorten with "..." or join separate pieces.
6. "short_answer": if the answer is a short fact (a value, name, command or number of at most {{short_max}} words) that appears exactly in the fragment, copy it here; otherwise use null.
If you write more than one question, each must ask about a different fact.

Reply with JSON only, in exactly this format:
{"questions": [{"question": "...", "answer": "...", "evidence": "...", "short_answer": null}]}
