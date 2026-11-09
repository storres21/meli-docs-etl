"""Tests de chunking: bloques atómicos, conservación, ids estables, split_group y OpenAPI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meli_docs_etl.chunk_utils import pack_blocks, parse_blocks, split_text
from meli_docs_etl.config import Config, load_config
from meli_docs_etl.stages import chunk, dedup, normalize


def words(text: str) -> int:
    return len(text.split())


LONG = """## Deploy

First paragraph explains the deploy process in a few plain words for the reader.

```bash
kubectl apply -f app.yaml

# esto no es un header
kubectl rollout status deploy/app
```

| Step | Command | Notes |
| --- | --- | --- |
| build | make build | runs tests too |
| push | make push | needs registry credentials |

- check the dashboards after the deploy finishes
- roll back with the previous tag

  if the error rate grows above the alert threshold
- announce in the team channel

Last paragraph closes the section with some words about monitoring and alerts."""


def test_blocks_never_cut_inside_code_table_or_list() -> None:
    blocks = parse_blocks(LONG)
    assert "".join(LONG[b.start : b.end] for b in blocks) == LONG
    assert [b.kind for b in blocks] == ["paragraph", "code", "table", "list", "paragraph"]

    slices = split_text(LONG, words, target=12, min_size=3, max_size=30)
    pieces = [LONG[a:b] for a, b in slices]
    assert "".join(pieces) == LONG  # cubren el texto exacto
    for p in pieces:
        assert p.count("```") % 2 == 0  # ningún fence abierto
    joined = "\n".join(LONG.splitlines()[11:15])  # la tabla entera
    assert any(joined in p for p in pieces)
    assert any("- check" in p and "- announce" in p for p in pieces)  # la lista entera


def test_oversize_block_is_kept_whole_with_its_intro() -> None:
    code = "```python\n" + "\n".join(f"x{i} = {i}" for i in range(60)) + "\n```"
    text = f"## Big\n\nThe whole job is shown below:\n\n{code}\n\nClosing words here."
    # La intro ("…below:") viaja con su bloque; el cierre chico se une al vecino oversize.
    assert [b.kind for b in parse_blocks(text)] == ["code", "paragraph"]
    assert split_text(text, words, target=20, min_size=5, max_size=40) == [(0, len(text))]
    # Huérfanos: un grupo chico se une al vecino oversize en vez de quedar suelto.
    assert pack_blocks([3, 100, 30], target=20, min_size=5, max_size=40) == [(0, 2), (2, 3)]


# --------------------------------------------------------------------------- end-to-end

LINES = [
    "The restock consumer reads every message from the restock queue topic",
    "It validates the quantity against the warehouse stock before saving",
    "Invalid messages are sent to the dead letter queue for manual review",
    "Each processed message updates the item stock in the inventory table",
    "Metrics are published for every message processed by the consumer app",
    "Alerts fire when the error rate is above five percent for ten minutes",
    "The consumer retries three times before giving up on a single message",
    "Operators can replay messages from the dead letter queue using the tool",
]
RESTOCK = "\n".join(LINES)
RESTOCK_V2 = "\n".join([*LINES[:-1], LINES[-1].replace("tool", "console")])
FEED = "The feed consumer stores the catalog feed sent by each vendor every day."
SPEC = {
    "openapi": "3.0.1",
    "info": {"title": "stock", "version": "9.9.9"},
    "paths": {
        "/items/{itemId}": {
            "get": {
                "summary": "Get one item",
                "parameters": [{"$ref": "#/components/parameters/ItemID"}],
                "responses": {
                    "200": {
                        "description": "The item",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                        },
                    },
                    "404": {
                        "description": "Not found",
                        "content": {"application/json": {"schema": {"$ref": "#/models/Error"}}},
                    },
                },
            }
        }
    },
    "components": {
        "parameters": {
            "ItemID": {
                "in": "path",
                "name": "itemId",
                "required": True,
                "description": "Item identifier.",
                "schema": {"type": "integer"},
            }
        },
        "schemas": {
            "Item": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "integer", "description": "Item id."},
                    "warehouse": {"$ref": "#/components/schemas/Warehouse"},
                    "children": {"type": "array", "items": {"$ref": "#/components/schemas/Item"}},
                },
            },
            "Warehouse": {"type": "object", "properties": {"code": {"type": "string"}}},
        },
    },
    "models": {
        "Error": {
            "type": "object",
            "properties": {"code": {"type": "string"}, "message": {"type": "string"}},
        }
    },
}


def api_md(restock: str) -> str:
    return (
        "# Stock API\n\n## Services\n\n"
        f"### Feed Consumer\n\n{FEED}\n\n### Restock Consumer\n\n{restock}\n\n"
        f"## Deploy guide\n\n{LONG.split(chr(10), 2)[2] * 6}\n"
    )


def build_tree(root: Path) -> None:
    files = {
        "stock/0.0.10/guide/api.md": api_md(RESTOCK),
        # latest: Feed idéntico (absorbido) y Restock con una línea propia (variante).
        "stock/latest/guide/api.md": (
            f"# Stock API\n\n## Services\n\n### Feed Consumer\n\n{FEED}\n\n"
            f"### Restock Consumer\n\n{RESTOCK_V2}\n"
        ),
        "stock/0.0.10/specs/swagger.yaml": json.dumps(SPEC),
        "stock/0.0.10/documentationTypes.json": json.dumps(
            {
                "guide": "https://d.s3.amazonaws.com/stock/0.0.10/guide/index.html",
                "specifications": "https://d.s3.amazonaws.com/stock/0.0.10/specs/swagger.yaml",
            }
        ),
    }
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content, encoding="utf-8")


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    build_tree(tmp_path / "raw")
    return load_config(
        overrides={
            "raw_dir": tmp_path / "raw",
            "processed_dir": tmp_path / "processed",
            "reports_dir": tmp_path / "reports",
            "outputs_dir": tmp_path / "outputs",
            "labels_dir": tmp_path / "labels",
        }
    )


def run_all(cfg: Config) -> list[dict]:
    normalize.run(cfg)
    dedup.run(cfg)
    corpus = chunk.run(cfg)
    return [json.loads(line) for line in corpus.read_text(encoding="utf-8").splitlines()]


def test_conservation_and_strategies(cfg: Config) -> None:
    chunks = run_all(cfg)
    ctx = chunk.load_context(cfg)
    specs = chunk.load_specs(cfg, {})
    for strategy in chunk.STRATEGIES:
        res = chunk.build_strategy(ctx, specs, [], strategy)
        assert res.conservation.ok, strategy
    # Cada sección canónica o variante se reconstruye con sus pedazos, en orden.
    for sid, rec in ctx.records.items():
        parts = sorted((c for c in chunks if sid in c["section_ids"]), key=lambda c: c["part"])
        if len(parts) == 1:
            assert rec["text"].strip() in parts[0]["text"]
        else:  # partida: los pedazos en orden reconstruyen la sección (salvo espacios)
            assert " ".join(rec["text"].split()) == " ".join(
                " ".join(c["text"] for c in parts).split()
            )
    assert any(c["chunk_kind"] == "split" for c in chunks)
    assert any(c["chunk_kind"] == "merged" for c in chunks)
    report = (cfg.paths.reports_dir / "chunk.md").read_text(encoding="utf-8")
    assert "## 6. Chequeo de conservación" in report and "❌" not in report


def test_chunk_ids_are_stable(cfg: Config) -> None:
    first = {c["chunk_id"]: c for c in run_all(cfg)}
    second = {c["chunk_id"]: c for c in run_all(cfg)}
    assert first.keys() == second.keys()

    # Cambiar una sección solo cambia los ids de los chunks que la contienen.
    path = cfg.paths.raw_dir / "stock/0.0.10/guide/api.md"
    path.write_text(path.read_text().replace("every day", "every night"), encoding="utf-8")
    third = {c["chunk_id"]: c for c in run_all(cfg)}
    changed = set(first) - set(third)
    assert changed and all(any("Feed" in t for t in first[c]["section_titles"]) for c in changed)


def test_split_group_joins_merged_clusters_and_variants(cfg: Config) -> None:
    chunks = run_all(cfg)
    merged = [c for c in chunks if c["chunk_kind"] == "merged"]
    (services,) = [
        c for c in merged if c["section_titles"] == ["Feed Consumer", "Restock Consumer"]
    ]
    assert len(services["cluster_ids"]) == 2  # la fusión une dos clusters

    (variant,) = [c for c in chunks if c["role"] == "variant"]
    assert variant["version_dir"] == "latest"
    assert variant["variant_of_chunks"] == [services["chunk_id"]]
    # Variante (otro archivo) y el chunk fusionado comparten el cluster de Restock → mismo
    # grupo; el cluster de Feed entra transitivamente.
    assert set(variant["cluster_ids"]) < set(services["cluster_ids"])
    assert variant["split_group"] == services["split_group"]
    groups = {}
    for c in chunks:
        for cid in c["cluster_ids"]:
            groups.setdefault(cid, set()).add(c["split_group"])
    assert all(len(g) == 1 for g in groups.values())  # ningún cluster en dos grupos


def test_openapi_operations_resolve_refs(cfg: Config) -> None:
    chunks = run_all(cfg)
    (op,) = [c for c in chunks if c["source_type"] == "openapi"]
    text = op["text"]
    assert text.startswith("## GET /items/{itemId}")
    assert "`itemId` (path; integer; required): Item identifier." in text  # $ref de parámetro
    assert "`warehouse` (Warehouse, object)" in text and "`code` (string)" in text  # anidado
    assert "`children` (array of Item, recursive)" in text  # ciclo cortado en el 1er nivel
    assert text.count("`warehouse`") == 1
    assert "`message` (string)" in text  # puntero no estándar #/models/Error
    assert "unresolved" not in text
    assert op["source_url"].endswith("/specs/swagger.yaml")
    assert op["spec_version"] == "9.9.9" and op["cluster_ids"][0].startswith("oa-")
    assert op["contextualized_text"].startswith("stock › specs/swagger.yaml › GET /items/{itemId}")
