"""Exporta los pares casi-duplicados candidatos para etiquetado humano (revisión ciega).

Lee `<processed_dir>/near_dup_pairs.jsonl` (dedup) y `sections.jsonl` (normalize) y escribe
en `<labels_dir>`:
- `near_dup_review.md`: cada par con sus rutas y el texto completo de ambas secciones en
  un diff, en orden aleatorio (semilla de la config) y **sin** el Jaccard.
- `near_dup_labels.csv`: `pair_id,label,nota` para completar. Si ya existe, se conservan
  las etiquetas cargadas: solo se agregan pares nuevos.
"""

from __future__ import annotations

import csv
import difflib
import json
import logging
import random
import re
from pathlib import Path
from typing import Any

from meli_docs_etl.config import Config, display_path
from meli_docs_etl.stages.normalize import SECTIONS_FILE
from meli_docs_etl.stages.validate_threshold import (
    LABEL_COLUMNS,
    LABELS_FILE,
    PAIRS_FILE,
    REVIEW_FILE,
    read_labels,
    read_pairs,
)

log = logging.getLogger(__name__)

_BACKTICKS = re.compile(r"`{3,}")

HEADER = """# Revisión de pares casi-duplicados

Cada par compara dos secciones del corpus normalizado (A y B). Completá la columna `label`
de `near_dup_labels.csv` con el `pair_id` correspondiente:

- `same`: es la misma sección en otra versión/edición (debería agruparse).
- `diff`: son secciones distintas aunque compartan plantilla.
- `unsure`: no estoy segura.

La columna `nota` es libre. Cómo leer el diff: las líneas sin prefijo están en A y en B,
las que empiezan con `-` solo en A y las que empiezan con `+` solo en B. Así cada texto se
lee completo una sola vez. Los pares están en orden aleatorio.
"""


def location(s: dict[str, Any]) -> str:
    """proyecto › versión/archivo › section_path"""
    rest = s["doc_path"].split("/", 1)[1]
    return " › ".join([s["project"], rest, *s["section_path"]])


def full_diff(a: str, b: str) -> list[str]:
    """Diff unificado con contexto completo, sin cabeceras (---, +++, @@)."""
    la, lb = a.splitlines(), b.splitlines()
    lines = difflib.unified_diff(la, lb, n=max(len(la), len(lb)), lineterm="")
    return [ln for ln in lines if not ln.startswith(("---", "+++", "@@"))]


def _fence(lines: list[str]) -> str:
    """Cerca más larga que cualquier secuencia de backticks del contenido."""
    longest = max((len(m) for ln in lines for m in _BACKTICKS.findall(ln)), default=0)
    return "`" * max(3, longest + 1)


def render_review(pairs: list[dict[str, Any]], sections: dict[str, dict[str, Any]]) -> str:
    out = [HEADER, f"Pares: {len(pairs)}.", ""]
    for i, p in enumerate(pairs, 1):
        a, b = sections[p["a"]], sections[p["b"]]
        lines = full_diff(a["text"], b["text"])
        fence = _fence(lines)
        out += [
            "---",
            "",
            f"### {i} · {p['pair_id']}",
            "",
            f"- **A**: {location(a)}",
            f"- **B**: {location(b)}",
            "",
            f"{fence}diff",
            *lines,
            fence,
            "",
        ]
    return "\n".join(out)


def write_labels(path: Path, order: list[str]) -> tuple[int, int, list[str]]:
    """Escribe el CSV en el orden de la revisión conservando etiquetas existentes.

    Devuelve (pares nuevos, etiquetas conservadas, pair_ids huérfanos).
    """
    existing = {r["pair_id"]: r for r in read_labels(path)} if path.exists() else {}
    current = set(order)
    orphans = [pid for pid in existing if pid not in current]
    rows = [existing.get(pid, {"pair_id": pid, "label": "", "nota": ""}) for pid in order]
    rows += [existing[pid] for pid in orphans]  # nunca se borra una etiqueta
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LABEL_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    kept = sum(bool(existing[pid]["label"]) for pid in order if pid in existing)
    return sum(pid not in existing for pid in order), kept, orphans


def run(cfg: Config) -> Path:
    processed, labels_dir = cfg.paths.processed_dir, cfg.paths.labels_dir
    pairs = sorted(read_pairs(processed / PAIRS_FILE).values(), key=lambda p: p["pair_id"])
    random.Random(cfg.seed).shuffle(pairs)
    with open(processed / SECTIONS_FILE, encoding="utf-8") as fh:
        sections = {s["section_id"]: s for s in map(json.loads, fh)}

    labels_dir.mkdir(parents=True, exist_ok=True)
    review = labels_dir / REVIEW_FILE
    review.write_text(render_review(pairs, sections), encoding="utf-8")
    new, kept, orphans = write_labels(labels_dir / LABELS_FILE, [p["pair_id"] for p in pairs])

    log.info(
        "%d pares en %s (orden aleatorio, seed=%d)", len(pairs), display_path(review), cfg.seed
    )
    log.info(
        "%s: %d pares nuevos, %d etiquetas conservadas",
        display_path(labels_dir / LABELS_FILE),
        new,
        kept,
    )
    for pid in orphans:
        log.warning("Etiqueta de un par que ya no existe (se conserva al final): %s", pid)
    return review
