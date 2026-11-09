"""Conteo de tokens con tiktoken usando una caché local versionada (funciona offline)."""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=4)
def token_counter(name: str, cache_dir: Path) -> Callable[[str], int]:
    """Devuelve una función texto → n_tokens.

    tiktoken busca el archivo BPE en TIKTOKEN_CACHE_DIR (verificando su hash) y solo lo
    descarga si no está; la caché vive en el repo para que no haga falta red.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TIKTOKEN_CACHE_DIR"] = str(cache_dir)
    import tiktoken

    enc = tiktoken.get_encoding(name)
    return lambda text: len(enc.encode(text, disallowed_special=()))
