"""OpenAPI → texto legible, una operación por chunk (puro).

Los `$ref` internos se resuelven como punteros JSON (`#/a/b/c`), así que también funcionan
raíces no estándar como `#/models/...`. Las referencias recursivas se cortan con detección
de ciclos y las que no existen quedan indicadas en el texto y en `missing_refs`.

Las etiquetas del texto (Parameters, Request body, Responses) usan el vocabulario de
OpenAPI en inglés, igual que Swagger UI; el contenido de las descripciones no se toca.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

METHODS = ("get", "put", "post", "delete", "patch", "options", "head", "trace")
_STANDARD_ROOTS = ("#/components/", "#/definitions/")


@dataclass
class Operation:
    method: str
    path: str
    operation_id: str | None
    summary: str
    text: str
    prose: str  # solo descripciones: insumo para detectar el idioma
    missing_refs: list[str] = field(default_factory=list)


class _Resolver:
    def __init__(self, doc: dict[str, Any]) -> None:
        self.doc = doc
        self.missing: list[str] = []

    def lookup(self, ref: str) -> Any | None:
        if not ref.startswith("#/"):
            return None
        node: Any = self.doc
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    def deref(self, node: Any, stack: tuple[str, ...] = ()) -> tuple[Any, str | None, bool]:
        """(nodo resuelto, última ref seguida, es ciclo). Sigue cadenas de $ref; `stack`
        son las refs completas que se están expandiendo."""
        ref = None
        while isinstance(node, dict) and "$ref" in node:
            ref = node["$ref"]
            if ref in stack:
                return None, ref, True
            target = self.lookup(ref)
            if target is None:
                if ref not in self.missing:
                    self.missing.append(ref)
                return None, ref, False
            stack = (*stack, ref)
            node = target
        return node, ref, False


def _name(ref: str | None) -> str | None:
    return ref.rsplit("/", 1)[-1] if ref else None


def _type_of(schema: dict[str, Any]) -> str:
    t = schema.get("type") or ("object" if "properties" in schema else "")
    if schema.get("format"):
        t = f"{t}, {schema['format']}" if t else schema["format"]
    return t or "any"


def _facets(schema: dict[str, Any]) -> list[str]:
    out = []
    if "enum" in schema:
        out.append("values: " + ", ".join(str(v) for v in schema["enum"]))
    if "default" in schema:
        out.append(f"default: {schema['default']}")
    if "example" in schema and not isinstance(schema["example"], dict | list):
        out.append(f"example: {schema['example']}")
    return out


def _clean(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


class _Renderer:
    def __init__(self, doc: dict[str, Any], max_depth: int) -> None:
        self.r = _Resolver(doc)
        self.max_depth = max_depth
        self.prose: list[str] = []

    def desc(self, text: Any) -> str:
        t = _clean(text)
        if t:
            self.prose.append(t)
        return t

    def schema_lines(
        self, node: Any, indent: int, depth: int, stack: tuple[str, ...] = ()
    ) -> list[str]:
        """Campos de un esquema como lista indentada (`- campo (tipo, required): desc`)."""
        schema, ref, cyclic = self.r.deref(node, stack)
        name = _name(ref)
        pad = "  " * indent
        if cyclic:
            return [f"{pad}- (see {name}, recursive)"]
        if schema is None:
            return [f"{pad}- (unresolved reference: {name})"] if name else []
        if ref:
            stack = (*stack, ref)
        if depth > self.max_depth:
            return [f"{pad}- … ({name or 'nested object'})"]

        lines: list[str] = []
        for key in ("allOf", "oneOf", "anyOf"):
            for i, sub in enumerate(schema.get(key, [])):
                if key != "allOf":
                    lines.append(f"{pad}- option {i + 1}:")
                lines += self.schema_lines(sub, indent + (key != "allOf"), depth + 1, stack)
        if schema.get("type") == "array" or "items" in schema:
            items, item_ref, _ = self.r.deref(schema.get("items", {}), stack)
            if items is not None and (items.get("properties") or items.get("allOf")):
                return lines + self.schema_lines(schema.get("items", {}), indent, depth, stack)
            label = _name(item_ref) or (_type_of(items) if items else "any")
            return lines + [f"{pad}- items: {label}"]
        required = set(schema.get("required", []))
        for prop, sub in (schema.get("properties") or {}).items():
            resolved, sub_ref, sub_cyclic = self.r.deref(sub, stack)
            sub_name = _name(sub_ref)
            if resolved is None:
                kind = f"{sub_name}, recursive" if sub_cyclic else f"unresolved {sub_name}"
                lines.append(f"{pad}- `{prop}` ({kind})")
                continue
            t = _type_of(resolved)
            if resolved.get("type") == "array":
                items, item_ref, item_cyclic = self.r.deref(resolved.get("items", {}), stack)
                label = _name(item_ref) or (_type_of(items) if items else "any")
                t = f"array of {label}" + (", recursive" if item_cyclic else "")
            elif sub_name:
                t = f"{sub_name}, {t}"
            bits = [t] + (["required"] if prop in required else []) + _facets(resolved)
            d = self.desc(resolved.get("description"))
            lines.append(f"{pad}- `{prop}` ({'; '.join(bits)})" + (f": {d}" if d else ""))
            nested = resolved.get("items") if resolved.get("type") == "array" else resolved
            n_res, _, _ = self.r.deref(nested or {}, stack)
            if n_res and (n_res.get("properties") or n_res.get("allOf")):
                lines += self.schema_lines(nested, indent + 1, depth + 1, stack)
        return lines

    def examples(self, media: dict[str, Any]) -> list[str]:
        out = []
        items: list[tuple[str, Any]] = []
        if "example" in media:
            items.append(("", media["example"]))
        for key, ex in (media.get("examples") or {}).items():
            ex, _, _ = self.r.deref(ex)
            if ex is not None and "value" in ex:
                items.append((key, ex["value"]))
        for key, value in items:
            body = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False)
            out += [f"Example{f' ({key})' if key else ''}:", "```json", body, "```"]
        return out

    def content(self, content: dict[str, Any], indent: int) -> list[str]:
        out = []
        for mtype, media in (content or {}).items():
            schema = media.get("schema")
            _, ref, _ = self.r.deref(schema or {})
            name = _name(ref)
            out.append(f"{'  ' * indent}Content ({mtype})" + (f": {name}" if name else ""))
            if schema is not None:
                out += self.schema_lines(schema, indent + 1, 1)
            out += self.examples(media)
        return out

    def parameter(self, node: Any) -> str:
        p, ref, _ = self.r.deref(node)
        if p is None:
            return f"- (unresolved parameter: {_name(ref)})"
        schema, _, _ = self.r.deref(p.get("schema") or {})
        schema = schema or {}
        bits = [p.get("in", "?"), _type_of(schema)]
        bits += ["required"] if p.get("required") else []
        bits += _facets(schema)
        d = self.desc(p.get("description"))
        return f"- `{p.get('name')}` ({'; '.join(bits)})" + (f": {d}" if d else "")


def _servers(doc: dict[str, Any], *nodes: dict[str, Any]) -> list[str]:
    for node in (*nodes, doc):
        if node.get("servers"):
            return [s.get("url", "") for s in node["servers"]]
    return []


def render_operations(doc: dict[str, Any], max_depth: int = 4) -> list[Operation]:
    ops = []
    for path, item in (doc.get("paths") or {}).items():
        for method, op in item.items():
            if method not in METHODS:
                continue
            rd = _Renderer(doc, max_depth)
            summary = rd.desc(op.get("summary"))
            lines = [f"## {method.upper()} {path}", ""]
            if summary:
                lines += [summary, ""]
            if rd.desc(op.get("description")):
                lines += [str(op["description"]).strip(), ""]
            meta = []
            if op.get("operationId"):
                meta.append(f"Operation ID: {op['operationId']}")
            if op.get("tags"):
                meta.append("Tags: " + ", ".join(op["tags"]))
            if servers := _servers(doc, op, item):
                meta.append("Servers: " + ", ".join(servers))
            security = op.get("security", doc.get("security"))
            if security:
                meta.append("Security: " + ", ".join(k for req in security for k in req))
            if op.get("deprecated"):
                meta.append("Deprecated: yes")
            lines += [*meta, ""] if meta else []

            # Parámetros: los de la operación pisan a los del path (mismo name + in).
            params: dict[tuple[str, str], Any] = {}
            for node in [*(item.get("parameters") or []), *(op.get("parameters") or [])]:
                p, _, _ = rd.r.deref(node)
                key = (p.get("name", ""), p.get("in", "")) if p else (str(node), "")
                params[key] = node
            if params:
                lines += ["Parameters:", *(rd.parameter(n) for n in params.values()), ""]

            if "requestBody" in op:
                body, _, _ = rd.r.deref(op["requestBody"])
                body = body or {}
                head = "Request body" + (" (required)" if body.get("required") else "")
                d = rd.desc(body.get("description"))
                lines += [head + (f": {d}" if d else ":"), *rd.content(body.get("content"), 0), ""]

            if op.get("responses"):
                lines.append("Responses:")
                for code, resp in op["responses"].items():
                    res, ref, _ = rd.r.deref(resp)
                    if res is None:
                        lines.append(f"- `{code}`: (unresolved response: {_name(ref)})")
                        continue
                    d = rd.desc(res.get("description"))
                    lines.append(f"- `{code}`" + (f": {d}" if d else ""))
                    lines += rd.content(res.get("content"), 1)
            text = "\n".join(lines).strip()
            ops.append(
                Operation(
                    method=method.upper(),
                    path=path,
                    operation_id=op.get("operationId"),
                    summary=summary,
                    text=text,
                    prose="\n".join(rd.prose),
                    missing_refs=list(rd.r.missing),
                )
            )
    return ops


def quality_notes(doc: dict[str, Any], project: str) -> list[str]:
    """Inconsistencias de la spec que conviene reportar (no se corrigen)."""
    notes = []
    title = str((doc.get("info") or {}).get("title", ""))
    if title and _norm(title) != _norm(project) and _norm(title) not in _norm(project):
        notes.append(f"`info.title` es `{title}`, distinto del proyecto `{project}`.")
    refs = sorted(set(re.findall(r"'?\$ref'?:\s*'([^']+)'", repr(doc))))
    odd = [r for r in refs if r.startswith("#/") and not r.startswith(_STANDARD_ROOTS)]
    if odd:
        notes.append(
            "Referencias fuera de `#/components` (no estándar en OpenAPI 3): "
            + ", ".join(f"`{r}`" for r in odd)
            + "."
        )
    params = (doc.get("components") or {}).get("parameters") or {}
    keys = {_norm(k): k for k in params}
    for key, p in params.items():
        name = str(p.get("name", ""))
        other = keys.get(_norm(name))
        if other and other != key:
            notes.append(
                f"El parámetro `{key}` declara `name: {name}`, que corresponde a `{other}`: "
                "nombres intercambiados."
            )
    return notes


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())
