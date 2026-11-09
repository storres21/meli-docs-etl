"""Tests del split: grupos enteros, proyecto retenido, estabilidad, determinismo y auditoría."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from meli_docs_etl.config import Config, load_config
from meli_docs_etl.split_utils import (
    EVAL_PROJECT,
    EVAL_SECTION,
    TRAIN,
    assign,
    audit_hard,
    build_groups,
    cross_split_similar,
    endpoint_leaks,
)
from meli_docs_etl.stages import split as stage

WORDS = "stock order vendor queue batch item price rule alert deploy cache table".split()


def chunk(
    cid: str,
    project: str,
    group: str,
    tokens: int = 100,
    cluster: str | None = None,
    source_type: str = "markdown",
    text: str | None = None,
    path: str | None = None,
    operation: dict | None = None,
) -> dict:
    """Ficha mínima con los campos que usa el split."""
    path = path or f"{project}/1.0/guide/{group}.md"
    section_id = None if source_type == "openapi" else f"{path}#{cid}"
    section_path = [f"{operation['method']} {operation['path']}"] if operation else [cid]
    body = text or " ".join(WORDS[(hash(cid) + i) % len(WORDS)] + cid for i in range(30))
    return {
        "chunk_id": f"ck-{cid}",
        "project": project,
        "split_group": group,
        "cluster_ids": [cluster or f"cl-{group}"],
        "n_tokens": tokens,
        "source_type": source_type,
        "language": "en",
        "occurrences": [{"section_id": section_id, "path": path, "section_path": section_path}],
        "source_path": path,
        "section_path": section_path,
        "part": 1,
        "operation": operation,
        "text": body,
        "contextualized_text": f"{project} › {path}\n\n{body}",
    }


def base_corpus() -> list[dict]:
    chunks = []
    # alpha: 20 grupos (uno de 3 fichas) en un solo estrato markdown.
    for i in range(20):
        n = 3 if i == 0 else 1
        for k in range(n):
            chunks.append(chunk(f"a{i}-{k}", "alpha", f"sg-alpha-{i:02d}", tokens=50 + 10 * i))
    # beta: el proyecto retenido.
    for i in range(4):
        chunks.append(chunk(f"b{i}", "beta", f"sg-beta-{i}"))
    # gamma: estrato chico (3 grupos < 4) → todo a train.
    for i in range(3):
        chunks.append(chunk(f"g{i}", "gamma", f"sg-gamma-{i}"))
    return chunks


def write_corpus(cfg: Config, chunks: list[dict]) -> None:
    path = cfg.paths.outputs_dir / "corpus.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(c, sort_keys=True) + "\n" for c in chunks), "utf-8")


def read_corpus(cfg: Config) -> list[dict]:
    text = (cfg.paths.outputs_dir / "corpus.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def manifest_splits(cfg: Config) -> dict[str, str]:
    m = json.loads((cfg.paths.splits_dir / "manifest.json").read_text(encoding="utf-8"))
    return {g: v["split"] for g, v in m["groups"].items()}


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    base = load_config(
        overrides={
            "outputs_dir": tmp_path / "outputs",
            "reports_dir": tmp_path / "reports",
            "splits_dir": tmp_path / "splits",
        }
    )
    cfg = dataclasses.replace(base, split=dataclasses.replace(base.split, eval_project="beta"))
    write_corpus(cfg, base_corpus())
    return cfg


def test_groups_never_split_and_held_out_project_is_complete(cfg: Config) -> None:
    stage.run(cfg)
    chunks = read_corpus(cfg)
    by_group: dict[str, set] = {}
    for c in chunks:
        by_group.setdefault(c["split_group"], set()).add(c["split"])
    assert all(len(s) == 1 for s in by_group.values())  # el grupo de 3 fichas incluido
    assert {c["split"] for c in chunks if c["project"] == "beta"} == {EVAL_PROJECT}
    assert {c["project"] for c in chunks if c["split"] == EVAL_PROJECT} == {"beta"}
    assert {c["split"] for c in chunks if c["project"] == "gamma"} == {TRAIN}  # estrato chico
    alpha = [c for c in chunks if c["project"] == "alpha"]
    share = sum(c["n_tokens"] for c in alpha if c["split"] == EVAL_SECTION) / sum(
        c["n_tokens"] for c in alpha
    )
    s = cfg.split
    assert s.eval_section_fraction - s.tolerance <= share <= s.eval_section_fraction + s.tolerance
    # Los chunk_id y el resto de los campos no cambian: solo se agrega `split`.
    original = {c["chunk_id"]: c for c in base_corpus()}
    for c in chunks:
        assert {k: v for k, v in c.items() if k != "split"} == original[c["chunk_id"]]


def test_deterministic(cfg: Config, tmp_path: Path) -> None:
    stage.run(cfg)
    corpus1 = (cfg.paths.outputs_dir / "corpus.jsonl").read_bytes()
    manifest1 = (cfg.paths.splits_dir / "manifest.json").read_bytes()
    stage.run(cfg)  # desde el manifiesto
    assert (cfg.paths.outputs_dir / "corpus.jsonl").read_bytes() == corpus1
    assert (cfg.paths.splits_dir / "manifest.json").read_bytes() == manifest1
    (cfg.paths.splits_dir / "manifest.json").unlink()
    stage.run(cfg)  # desde cero
    assert (cfg.paths.outputs_dir / "corpus.jsonl").read_bytes() == corpus1
    assert (cfg.paths.splits_dir / "manifest.json").read_bytes() == manifest1


def test_new_groups_do_not_move_existing_ones(cfg: Config) -> None:
    stage.run(cfg)
    before = manifest_splits(cfg)
    # Llegan documentos nuevos: 20 grupos en alpha. El estrato crece más de lo que cubre el
    # eval existente, así que la cuota tiene que tomar grupos nuevos (y solo nuevos).
    extra = [chunk(f"n{i}", "alpha", f"sg-alpha-new-{i}", tokens=80) for i in range(20)]
    write_corpus(cfg, base_corpus() + extra)
    stage.run(cfg)
    after = manifest_splits(cfg)
    assert {g: after[g] for g in before} == before
    assert any(after[f"sg-alpha-new-{i}"] == EVAL_SECTION for i in range(20))


def test_renamed_group_inherits_and_conflict_goes_to_train() -> None:
    params = {
        "seed": 42,
        "eval_project": "beta",
        "eval_section_fraction": 0.2,
        "tolerance": 0.05,
        "min_groups_per_stratum": 4,
    }
    old = build_groups(base_corpus())
    first = assign(old, params)
    manifest = {
        gid: {"split": first.split[gid], "chunk_ids": g.chunk_ids, "keys": g.keys}
        for gid, g in old.items()
    }
    ev = next(g for g in sorted(old) if first.split[g] == EVAL_SECTION)
    tr = next(g for g in sorted(old) if first.split[g] == TRAIN and g.startswith("sg-alpha"))

    # Un documento nuevo cambia el id del grupo de eval (nuevo cluster canónico): hereda.
    renamed = [
        {**c, "split_group": "sg-renamed"} if c["split_group"] == ev else c for c in base_corpus()
    ]
    res = assign(build_groups(renamed), params, manifest)
    assert res.split["sg-renamed"] == EVAL_SECTION and res.origin["sg-renamed"] == "inherited"

    # Un grupo nuevo une contenido de train y de eval: va a train y se registra el cambio.
    bridged = [
        {**c, "split_group": "sg-bridge"} if c["split_group"] in (ev, tr) else c
        for c in base_corpus()
    ]
    res = assign(build_groups(bridged), params, manifest)
    assert res.split["sg-bridge"] == TRAIN and res.origin["sg-bridge"] == "conflict"
    (change,) = res.changes
    assert change.previous == {ev: EVAL_SECTION, tr: TRAIN}
    assert change.left_eval_keys == old[ev].keys


def test_group_keeping_its_id_but_absorbing_train_content_is_a_conflict() -> None:
    """Un must-link une un grupo de eval con uno de train y el grupo unido conserva el id
    del de eval (el cluster canónico no cambió): no puede quedar en eval en silencio."""
    params = {
        "seed": 42,
        "eval_project": "beta",
        "eval_section_fraction": 0.2,
        "tolerance": 0.05,
        "min_groups_per_stratum": 4,
    }
    old = build_groups(base_corpus())
    first = assign(old, params)
    manifest = {
        gid: {"split": first.split[gid], "chunk_ids": g.chunk_ids, "keys": g.keys}
        for gid, g in old.items()
    }
    ev = next(g for g in sorted(old) if first.split[g] == EVAL_SECTION)
    tr = next(g for g in sorted(old) if first.split[g] == TRAIN and g.startswith("sg-alpha"))
    merged = [{**c, "split_group": ev} if c["split_group"] == tr else c for c in base_corpus()]
    res = assign(build_groups(merged), params, manifest)
    assert res.split[ev] == TRAIN and res.origin[ev] == "conflict"
    (change,) = res.changes
    assert change.previous == {ev: EVAL_SECTION, tr: TRAIN}
    assert change.left_eval_keys == old[ev].keys


def test_eval_change_is_logged_and_kept_in_manifest_history(cfg: Config) -> None:
    stage.run(cfg)
    before = manifest_splits(cfg)
    ev = next(g for g in sorted(before) if before[g] == EVAL_SECTION)
    tr = next(g for g in sorted(before) if before[g] == TRAIN and g.startswith("sg-alpha"))
    # Un must-link nuevo une ambos grupos y el unido conserva el id del de eval.
    merged = [{**c, "split_group": ev} if c["split_group"] == tr else c for c in base_corpus()]
    write_corpus(cfg, merged)
    stage.run(cfg)
    assert manifest_splits(cfg)[ev] == TRAIN
    report = (cfg.paths.reports_dir / "split.md").read_text(encoding="utf-8")
    assert "Cambio del conjunto de eval:** el grupo" in report

    def history() -> list[dict]:
        m = json.loads((cfg.paths.splits_dir / "manifest.json").read_text(encoding="utf-8"))
        return m["eval_changes"]

    (event,) = history()
    assert event["tipo"] == "union_entre_splits" and event["antes"] == {
        ev: EVAL_SECTION,
        tr: TRAIN,
    }
    stage.run(cfg)  # sin cambios nuevos: el historial se conserva, no se duplica
    assert len(history()) == 1


def test_eval_change_lists_chunks_that_actually_move_to_train(cfg: Config) -> None:
    """Caso real (catalog setup): una ficha de eval con dos secciones se re-chunkea y solo
    una sección se une a un grupo de train. El historial registra la ficha nueva que pasa a
    train y su sección, no los chunk_id viejos del manifiesto (que ya no existen o siguen
    en eval)."""
    stage.run(cfg)
    before = manifest_splits(cfg)
    ev = next(g for g in sorted(before) if before[g] == EVAL_SECTION)
    tr = next(g for g in sorted(before) if before[g] == TRAIN and g.startswith("sg-alpha"))
    (cfg.paths.splits_dir / "manifest.json").unlink()

    # Corpus 1: la ficha del grupo de eval cubre dos secciones (s_stay, s_moved).
    s_stay, s_moved = "alpha/1.0/guide/x.md#001", "alpha/1.0/guide/x.md#002"

    def occ(sid: str) -> dict:
        return {"section_id": sid, "path": "alpha/1.0/guide/x.md", "section_path": [sid]}

    first = base_corpus()
    old_id = next(c["chunk_id"] for c in first if c["split_group"] == ev)
    for c in first:
        if c["split_group"] == ev:
            c["occurrences"] = [occ(s_stay), occ(s_moved)]
    write_corpus(cfg, first)
    stage.run(cfg)
    assert manifest_splits(cfg)[ev] == EVAL_SECTION

    # Corpus 2: un must-link une s_moved con el grupo de train y el chunking la separa.
    second = [c for c in first if c["split_group"] != ev]
    stay = chunk("stay", "alpha", ev)
    moved = chunk("moved", "alpha", tr)
    stay["occurrences"], moved["occurrences"] = [occ(s_stay)], [occ(s_moved)]
    write_corpus(cfg, second + [stay, moved])
    stage.run(cfg)

    corpus = {c["chunk_id"]: c["split"] for c in read_corpus(cfg)}
    assert corpus["ck-stay"] == EVAL_SECTION and corpus["ck-moved"] == TRAIN
    m = json.loads((cfg.paths.splits_dir / "manifest.json").read_text(encoding="utf-8"))
    (event,) = m["eval_changes"]
    assert event["antes"] == {ev: EVAL_SECTION, tr: TRAIN}
    assert event["fichas_que_salen"] == ["ck-moved"]
    assert event["secciones_que_salen"] == [s_moved]
    assert old_id not in event["fichas_que_salen"]


def test_changed_params_require_rebuild(cfg: Config) -> None:
    stage.run(cfg)
    other = dataclasses.replace(cfg, seed=7)
    with pytest.raises(stage.SplitError, match="--rebuild"):
        stage.run(other)
    stage.run(other, rebuild=True)
    report = (cfg.paths.reports_dir / "split.md").read_text(encoding="utf-8")
    assert "conjunto de eval nuevo" in report


def test_missing_held_out_project_fails_with_table(cfg: Config) -> None:
    other = dataclasses.replace(cfg, split=dataclasses.replace(cfg.split, eval_project=None))
    with pytest.raises(stage.SplitError, match="alpha"):
        stage.run(other)


def test_hard_audit_detects_seeded_leak(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    # Unitario: un cluster compartido por dos grupos en splits distintos.
    chunks = base_corpus()
    for c in chunks:
        c["split"] = TRAIN if c["project"] != "beta" else EVAL_PROJECT
    chunks[0]["cluster_ids"] = ["cl-shared"]
    chunks[-1].update(cluster_ids=["cl-shared"], split=EVAL_SECTION)
    audit = audit_hard(chunks, "beta")
    assert not audit.ok and audit.clusters_split == ["cl-shared"]

    # En la etapa: si la asignación filtra, falla y no toca el corpus ni el manifiesto.
    original = (cfg.paths.outputs_dir / "corpus.jsonl").read_bytes()
    real_assign = stage.assign

    def leaky(groups, params, previous=None):
        res = real_assign(groups, params, previous)
        res.split["sg-beta-0"] = TRAIN  # proyecto retenido fuera de eval_project
        return res

    monkeypatch.setattr(stage, "assign", leaky)
    with pytest.raises(stage.SplitError, match="Fuga dura"):
        stage.run(cfg)
    assert (cfg.paths.outputs_dir / "corpus.jsonl").read_bytes() == original
    assert not (cfg.paths.splits_dir / "manifest.json").exists()


def test_subtle_audit_reports_endpoints_and_near_duplicates() -> None:
    op = {"method": "GET", "path": "/api/v1/items/{itemId}", "operation_id": None}
    text = "Returns one item with its stock, warehouse and price for the vendor dashboard."
    chunks = [
        chunk(
            "op",
            "gamma",
            "sg-op",
            source_type="openapi",
            operation=op,
            path="gamma/specs.yaml",
            text=f"## GET /api/v1/items/{{itemId}}\n\n{text}",
        ),
        chunk("md", "gamma", "sg-md", text="Call GET /items/{id} to read one item."),
        chunk("md2", "gamma", "sg-md2", text=f"Item endpoint. {text}"),
        chunk("other", "delta", "sg-other", text="GET /items/{id} in another project."),
    ]
    for c, split in zip(chunks, [EVAL_SECTION, TRAIN, TRAIN, TRAIN], strict=True):
        c["split"] = split
    (leak,) = endpoint_leaks(chunks)  # el de otro proyecto no cuenta
    assert (leak.markdown_chunk, leak.mentioned_as) == ("ck-md", "/items/{id}")
    pairs = cross_split_similar(chunks, 0.3, 5)
    assert ("ck-md2", "ck-op") in {(a, b) for _, a, b in pairs}
