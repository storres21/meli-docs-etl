<!--
qa_unanswerable v1 — preguntas plausibles cuya respuesta NO está en la ficha
(qa_type = unanswerable; la respuesta del dataset es "la documentación no lo especifica",
localizada). Variables: project, location, text, n, language_name.
-->
## system
You write realistic questions about internal software documentation that the documentation does NOT answer. They are used to teach assistants to say when the documentation does not specify something. You reply with JSON only.

## user
Project: {{project}}
Location: {{location}}

Documentation fragment (between <doc> tags):
<doc>
{{text}}
</doc>

Write exactly {{n}} question(s) in {{language_name}} that a developer working with {{project}} could plausibly ask about the topic of this fragment, but whose answer is NOT in the fragment. Good examples ask for a limit, default value, timeout, version, permission, error code, configuration option or behavior that the fragment does not mention.
Rules:
1. Self-contained: name the project or the specific component, endpoint or concept. Never refer to "this document", "this section", "the text" or "the fragment" (nor "este documento", "esta sección", "el texto").
2. The fragment must not contain the answer, not even partially, and must not allow inferring it.
3. Stay on the topic of the fragment: the question must be plausible for someone reading it.
4. "missing_information": briefly say what information the fragment lacks.

Reply with JSON only, in exactly this format:
{"questions": [{"question": "...", "missing_information": "..."}]}
