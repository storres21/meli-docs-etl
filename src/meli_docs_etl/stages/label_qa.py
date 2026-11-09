"""Exporta una muestra de preguntas juzgadas para revisión humana del LLM-juez (ciega).

Lee `<processed_dir>/qa_candidates.jsonl` (etapa qa) y `outputs/corpus.jsonl`, y escribe en
`<labels_dir>`:
- `qa_review.md`: cada pregunta con su respuesta, evidencia y la ficha completa, **sin** los
  puntajes ni el veredicto del juez. Muestra estratificada por (tipo, veredicto) en
  round-robin, así entran también preguntas que el juez rechazó.
- `qa_judge_labels.csv`: `qa_id,accept,faithfulness,clarity,usefulness,nota` para completar.
  Si ya existe, se conservan las etiquetas cargadas (nunca se borra una).

`meli-etl qa` lee el CSV y reporta el acuerdo juez-humano (reports/qa.md §6).
"""

from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from typing import Any

from meli_docs_etl.config import Config, display_path
from meli_docs_etl.qa_utils import human_sample, location
from meli_docs_etl.stages.chunk import CORPUS_FILE
from meli_docs_etl.stages.qa import CANDIDATES_FILE, HUMAN_LABELS_FILE, HUMAN_REVIEW_FILE

log = logging.getLogger(__name__)

LABEL_COLUMNS = ["qa_id", "accept", "faithfulness", "clarity", "usefulness", "nota"]

HEADER = """# Revisión humana del LLM-juez (QA)

Para cada pregunta, completá su fila en `qa_judge_labels.csv` (por `qa_id`):

- `accept`: `si` si la pregunta debería quedar en el dataset, `no` si no.
- `faithfulness` (1-5, solo `llm`): ¿la respuesta está totalmente respaldada por la ficha?
- `clarity` (1-5): ¿la pregunta se entiende sin ver la ficha y tiene una sola respuesta?
- `usefulness` (1-5): ¿alguien que trabaja con el proyecto la haría? ¿no es trivial?
- `nota`: libre.

En `unanswerable` la respuesta esperada es que la documentación no lo especifica: aceptala
solo si la ficha (y, hasta donde sepas, el resto de la documentación del proyecto) no la
responde. El orden es aleatorio y no se muestran los puntajes del juez.
"""


def _fence(text: str) -> str:
    """Cerca más larga que cualquier secuencia de backticks del contenido."""
    longest = max((len(m) for m in re.findall(r"`{3,}", text)), default=0)
    return "`" * max(3, longest + 1)


def render_review(items: list[dict[str, Any]], chunks: dict[str, dict[str, Any]]) -> str:
    out = [HEADER, f"Preguntas: {len(items)}.", ""]
    for i, c in enumerate(items, 1):
        ch = chunks[c["chunk_id"]]
        fence = _fence(ch["text"])
        out += [
            "---",
            "",
            f"### {i} · {c['qa_id']} · {c['qa_type']}",
            "",
            f"- **Ficha:** {location(ch)} (`{c['chunk_id']}`)",
            f"- **Pregunta:** {c['question']}",
            f"- **Respuesta:** {c['answer']}",
        ]
        out += [f"- **Evidencia:** `{ev}`" for ev in c["evidence"]]
        out += ["", f"{fence}markdown", ch["text"], fence, ""]
    return "\n".join(out)


def write_labels(path: Path, order: list[str]) -> tuple[int, int]:
    """CSV en el orden de la revisión, conservando filas existentes (también huérfanas)."""
    existing: dict[str, dict[str, str]] = {}
    if path.exists():
        with open(path, encoding="utf-8", newline="") as fh:
            existing = {r["qa_id"]: r for r in csv.DictReader(fh)}
    rows = [existing.get(q, {"qa_id": q}) for q in order]
    rows += [r for q, r in existing.items() if q not in set(order)]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LABEL_COLUMNS, lineterminator="\n", restval="")
        writer.writeheader()
        writer.writerows({k: r.get(k, "") for k in LABEL_COLUMNS} for r in rows)
    kept = sum(bool(existing[q].get("accept")) for q in order if q in existing)
    return sum(q not in existing for q in order), kept


def run(cfg: Config) -> Path:
    cands_path = cfg.paths.processed_dir / CANDIDATES_FILE
    if not cands_path.exists():
        raise FileNotFoundError(f"{cands_path} no existe: corré antes `meli-etl qa`.")
    with open(cands_path, encoding="utf-8") as fh:
        judged = [c for c in map(json.loads, fh) if c["judge_pass"] is not None]
    with open(cfg.paths.outputs_dir / CORPUS_FILE, encoding="utf-8") as fh:
        chunks = {ch["chunk_id"]: ch for ch in map(json.loads, fh)}

    sample = [dict(c) for c in human_sample(judged, cfg.qa.human_sample_size, cfg.seed)]
    labels_dir = cfg.paths.labels_dir
    labels_dir.mkdir(parents=True, exist_ok=True)
    review = labels_dir / HUMAN_REVIEW_FILE
    review.write_text(render_review(sample, chunks), encoding="utf-8")
    new, kept = write_labels(labels_dir / HUMAN_LABELS_FILE, [c["qa_id"] for c in sample])
    log.info("%d preguntas en %s (seed=%d)", len(sample), display_path(review), cfg.seed)
    log.info(
        "%s: %d filas nuevas, %d etiquetas conservadas",
        display_path(labels_dir / HUMAN_LABELS_FILE),
        new,
        kept,
    )
    return review
