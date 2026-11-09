"""Cliente LLM mínimo (Ollama / Anthropic / OpenAI) con cache versionada en disco.

Sin SDKs: cada proveedor es un POST JSON con `urllib`. La cache guarda un archivo por
respuesta en `<llm_cache_dir>/<prompt>/<clave>.json`; la clave es el sha256 de la plantilla
del prompt, el prompt renderizado (que incluye la ficha), el proveedor, el modelo y los
parámetros de muestreo. Así `qa` se reproduce sin API key ni red (`replay`), y una corrida
`record` que se corta se reanuda donde quedó (cada respuesta se escribe apenas llega).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from meli_docs_etl.config import LLMConfig

log = logging.getLogger(__name__)

PROVIDERS = ("ollama", "anthropic", "openai")
CACHE_MODES = ("replay", "record", "off")
DEFAULT_URLS = {
    "ollama": "http://localhost:11434",
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com",
}
API_KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
ANTHROPIC_VERSION = "2023-06-01"
_VAR = re.compile(r"\{\{(\w+)\}\}")

# (modelo, system, user) → texto de la respuesta.
CallFn = Callable[[str, str, str], str]


class LLMError(RuntimeError):
    pass


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- prompts


@dataclass(frozen=True)
class Prompt:
    """Plantilla `prompts/<name>.<version>.md` con secciones `## system` y `## user`.

    Los marcadores son `{{variable}}` (no `{x}`: las fichas OpenAPI tienen paths con llaves).
    """

    name: str
    version: str
    system: str
    user: str
    sha: str  # hash del archivo: cambiar el prompt invalida su cache

    @property
    def id(self) -> str:
        return f"{self.name}.{self.version}"

    def render(self, **values: Any) -> tuple[str, str]:
        """Una sola pasada sobre la plantilla: el texto insertado (las fichas pueden traer
        `{{ ENV }}` o incluso `{{question}}`) nunca se vuelve a reemplazar."""

        def fill(template: str) -> str:
            missing = sorted(set(_VAR.findall(template)) - set(values))
            if missing:
                raise LLMError(f"Prompt {self.id}: faltan valores para {missing}")
            return _VAR.sub(lambda m: str(values[m.group(1)]), template)

        return fill(self.system), fill(self.user)


def load_prompt(prompts_dir: Path, name: str, version: str) -> Prompt:
    path = prompts_dir / f"{name}.{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"No existe el prompt {path}")
    raw = path.read_text(encoding="utf-8")
    parts: dict[str, list[str]] = {}
    current = None
    for line in raw.splitlines():
        if line.strip() in ("## system", "## user"):
            current = line.strip()[3:]
            parts[current] = []
        elif current:
            parts[current].append(line)
    if set(parts) != {"system", "user"}:
        raise LLMError(f"{path}: se esperaban las secciones `## system` y `## user`")
    return Prompt(
        name=name,
        version=version,
        system="\n".join(parts["system"]).strip(),
        user="\n".join(parts["user"]).strip(),
        sha=sha256(raw),
    )


# --------------------------------------------------------------------------- proveedores


def _post(url: str, headers: Mapping[str, str], body: Mapping[str, Any], timeout: int) -> Any:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise LLMError(f"HTTP {exc.code} de {url}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise LLMError(f"No se pudo conectar con {url}: {exc}") from exc


def provider_call(cfg: LLMConfig, seed: int) -> CallFn:
    """Función (modelo, system, user) → texto para el proveedor configurado."""
    if cfg.provider not in PROVIDERS:
        raise LLMError(f"llm.provider = {cfg.provider!r}; opciones: {', '.join(PROVIDERS)}")
    base = (cfg.base_url or DEFAULT_URLS[cfg.provider]).rstrip("/")
    key = None
    if cfg.provider in API_KEY_ENV:
        key = os.environ.get(API_KEY_ENV[cfg.provider])
        if not key:
            raise LLMError(f"Falta la variable de entorno {API_KEY_ENV[cfg.provider]}")

    def ollama(model: str, system: str, user: str) -> str:
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": cfg.temperature,
                "seed": seed,
                "num_ctx": cfg.num_ctx,
                "num_predict": cfg.max_tokens,
            },
        }
        try:
            return _post(f"{base}/api/chat", {}, body, cfg.timeout_s)["message"]["content"]
        except LLMError as exc:
            raise LLMError(
                f"{exc}\n¿Está corriendo Ollama (`ollama serve`) y descargado el modelo "
                f"(`ollama pull {model}`)?"
            ) from exc

    def anthropic(model: str, system: str, user: str) -> str:
        body = {
            "model": model,
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {"x-api-key": key or "", "anthropic-version": ANTHROPIC_VERSION}
        out = _post(f"{base}/v1/messages", headers, body, cfg.timeout_s)
        return "".join(b.get("text", "") for b in out["content"] if b.get("type") == "text")

    def openai(model: str, system: str, user: str) -> str:
        body = {
            "model": model,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "seed": seed,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        headers = {"Authorization": f"Bearer {key}"}
        out = _post(f"{base}/v1/chat/completions", headers, body, cfg.timeout_s)
        return out["choices"][0]["message"]["content"]

    return {"ollama": ollama, "anthropic": anthropic, "openai": openai}[cfg.provider]


# --------------------------------------------------------------------------- cache


class CachedLLM:
    """Completa prompts pasando por la cache según `cache_mode`.

    En `replay` un miss devuelve None y se cuenta en `misses` (la etapa decide fallar al
    final, para informar cuántas faltan). `call` permite inyectar un proveedor falso.
    """

    def __init__(
        self, cfg: LLMConfig, cache_dir: Path, seed: int, call: CallFn | None = None
    ) -> None:
        if cfg.cache_mode not in CACHE_MODES:
            raise LLMError(f"llm.cache_mode = {cfg.cache_mode!r}; opciones: {CACHE_MODES}")
        self.cfg, self.cache_dir, self.seed = cfg, cache_dir, seed
        self._call = call
        self.hits = self.misses = self.calls = 0

    def _client(self) -> CallFn:
        if self._call is None:  # perezoso: en replay no hace falta proveedor ni API key
            self._call = provider_call(self.cfg, self.seed)
        return self._call

    def key(self, prompt: Prompt, model: str, system: str, user: str) -> str:
        payload = {
            "prompt": prompt.id,
            "prompt_sha": prompt.sha,
            "system": system,
            "user": user,
            "provider": self.cfg.provider,
            "model": model,
            "temperature": self.cfg.temperature,
            "max_tokens": self.cfg.max_tokens,
            "num_ctx": self.cfg.num_ctx,
            "seed": self.seed,
        }
        return sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False))

    def path(self, prompt: Prompt, key: str) -> Path:
        return self.cache_dir / prompt.name / f"{key}.json"

    def complete(
        self, prompt: Prompt, model: str, chunk_id: str, chunk_text: str, **values: Any
    ) -> str | None:
        system, user = prompt.render(**values)
        key = self.key(prompt, model, system, user)
        path = self.path(prompt, key)
        mode = self.cfg.cache_mode
        if mode != "off" and path.exists():
            self.hits += 1
            return json.loads(path.read_text(encoding="utf-8"))["response"]
        if mode == "replay":
            self.misses += 1
            return None
        self.calls += 1
        response = self._client()(model, system, user)
        if mode == "record":
            entry = {
                "key": key,
                "prompt": prompt.id,
                "prompt_sha": prompt.sha,
                "provider": self.cfg.provider,
                "model": model,
                "params": {
                    "temperature": self.cfg.temperature,
                    "max_tokens": self.cfg.max_tokens,
                    "num_ctx": self.cfg.num_ctx,
                    "seed": self.seed,
                },
                "chunk_id": chunk_id,
                "chunk_sha": sha256(chunk_text),
                "response": response,
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(entry, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.replace(tmp, path)  # atómico: un corte nunca deja una entrada a medias
        return response
