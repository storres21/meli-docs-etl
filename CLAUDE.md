# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Technical assessment (Mercado Libre, Data Scientist – LLMs). A local, reproducible pipeline that turns raw Markdown docs of 10 fictional software projects (`data/raw/docs_raw/<project>/<version>/...`) into:
`outputs/corpus.jsonl` (chunks with provenance), `outputs/qa.jsonl` (Q&A anchored to chunks, train/eval split **by duplicate cluster** to avoid leakage), RL data (verifiable answers, unanswerable questions, DPO pairs), and retrieval metrics (BM25 Recall@k/MRR).

Stages, in order: `profile → normalize → dedup → chunk → split → qa → evaluate`. `profile`, `normalize`, `dedup`, `chunk` and `split` are implemented; the rest are CLI stubs that exit with code 2. Two auxiliary commands outside `make pipeline`: `label-pairs` (exports near-dup pairs for blind human labeling to `data/labels/`) and `validate-threshold` (sweeps thresholds against those labels → `reports/dedup.md` §8). Each stage reads the previous one's output from `data/processed/`. Code, comments, logs and reports are written in Spanish.

## Commands

Uses `uv` (lockfile `uv.lock`), Python ≥ 3.10.

```bash
make all                     # uv sync + pipeline (profile, normalize, dedup) + pytest
make pipeline                # implemented stages, in order
make profile                 # = uv run meli-etl profile --config configs/default.yaml
make <stage> CONFIG=x.yaml   # any stage with an alternative config
uv run meli-etl --help       # CLI; each stage also accepts --log-level
uv run pytest                # all tests
uv run pytest tests/test_profile.py::test_inventory   # single test
uv run ruff check src tests && uv run ruff format src tests   # line-length 100
make clean                   # removes data/processed/* and outputs/logs only
```

## Architecture

- `cli.py`: one Typer subcommand per stage. `_bootstrap()` loads config → sets up logging (console + `outputs/logs/<stage>.log`) → fixes the seed. New stages go in `src/meli_docs_etl/stages/<stage>.py` exposing `run(cfg: Config)`, imported lazily from the CLI.
- `config.py`: `configs/default.yaml` → frozen dataclasses (one per YAML block: `files`, `text`, `profile`, `normalize`, `dedup`). Relative paths resolve against the project root (the directory containing `pyproject.toml`), never against the cwd. **Every key under `paths:` must exist as a field in `Paths`** (it's built with `Paths(**...)`); `load_config(overrides=...)` overrides paths (used by tests). The `llm:` block (`cache_mode: replay|record|off`) is reserved for `qa` and not parsed yet.
- `inventory.py`: walks `raw_dir` and builds one `FileRecord` per file. Project, version, and section come from the path; `file_type` is `content | nav | spec | meta | other`. `resolved_version` comes from the sibling `documentationTypes.json` URL: `latest` is an alias (e.g. `catalog-portfolio-api/latest` == `0.0.1-test-bench-v2a`, almost identical). Hashes: `sha256` (bytes) and `sha256_norm` (whitespace-normalized).
- `md_utils.py`: headers via regex with code-fence tracking, deliberately not a CommonMark parser, so it can **flag** malformed headers like `#Title`. Also handles sections (header path → body), `strip_noise` (removes code, badges, HTML/docsify comments, URLs), and TODO-placeholder detection.
- `lang.py`: deterministic es/en stopword heuristic → `es | en | mixed | unknown`. Strip TODO markers before calling it ("TO DO" would add an English hit on "do").
- `normalize.py` (pure transforms) + `stages/normalize.py`: splits the RAW file into sections first, then normalizes each one, so every section keeps `raw_hash` and `norm_hash`. HTML entities are decoded inside code blocks too (export artifact in the data). Nav files become metadata (`nav.py`). Stub filtering uses `content_tokens`, which counts code and tables. Do not reuse profile's prose-only `n_words` for this.
- `dedup_utils.py` + `stages/dedup.py`: exact dedup by `norm_hash` (title + body), then MinHash/LSH candidates verified with exact Jaccard. The lossless merge rule: absorb a section only if all its lines are already in a kept section, otherwise keep it as `variant`. Human `same` labels are must-links (`match: human_label`); `data/labels/manual_must_links.csv` declares must-links by section_id for pairs outside the labelable sample (`match: audit_link`). `cluster_id` feeds `split_group` (built in `chunk`), which is the actual split key. The near-dup threshold (0.6) was chosen from the observed similarity valley; see `reports/dedup.md` §4 (and §8, human-label validation) before changing it. §8 lives between `<!-- threshold-validation -->` markers so both `dedup` and `validate-threshold` render it.
- `chunk_utils.py` + `openapi.py` + `stages/chunk.py`: Markdown is split into contiguous blocks covering the text exactly (code, tables, lists, `<details>` are atomic; cuts only between blocks), so pieces are exact slices and the conservation check (every section's content in exactly one chunk) is strict — the stage exits 1 if it fails. Always builds the 3 strategies (`section`, `section_split`, `merged`) into `data/processed/corpus_<s>.jsonl`; `chunk.strategy` goes to `outputs/corpus.jsonl`. `split_group` (union-find over `cluster_ids`) is the split key for leakage. OpenAPI `$ref`s are resolved as JSON pointers with a stack of full refs for cycle detection. Tokens via `tokens.token_counter` (tiktoken, cache dir from config).
- `split_utils.py` + `stages/split.py`: assigns each `split_group` to `train | eval_section | eval_project` (held-out project from `split.eval_project`, chosen by a human). Quota per stratum (project × source_type) in `sha256(seed|split_group)` order, frozen in `data/splits/manifest.json`: existing groups never move; every group (even one whose id is already in the manifest) is checked against the old groups owning its occurrence keys; new groups inherit via shared occurrence keys (section_ids, not cluster_ids, which change when the canonical changes) or fill the quota; a group bridging splits goes to train and is logged as an eval-set change, appended to the versioned `eval_changes` history in the manifest. Changing split params or seed without `--rebuild` fails on purpose. Hard leaks (group/cluster in two splits, held-out project outside eval_project) fail the stage before writing anything. `chunk` rewrites `corpus.jsonl` without `split`, so `split` must run after it.
- `stages/profile.py`: writes `data/processed/inventory.jsonl` (meant for reuse by dedup/split) and `reports/profile.md`. Reports must stay **deterministic** (no timestamps, stable ordering); a test checks two runs produce identical output.

## Conventions and constraints

- Nothing hardcoded: paths, thresholds and seed come from the YAML config.
- Versioned: `data/raw/`, `outputs/` (final datasets are deliverables), `reports/`, `data/cache/llm/`, `data/cache/tiktoken/` (tokenizer BPE, keeps `chunk` offline), `data/splits/manifest.json` (frozen split; never hand-edit), `data/labels/` (human labels: `label-pairs` must never drop a filled label, and the review file must never show Jaccard). Ignored: `data/processed/*`, `outputs/logs/`.
- `data/cache/llm/` will cache LLM responses so `qa` is reproducible without an API key (`replay` mode by default). Do not call any LLM unless asked.
- Tests use a synthetic tree built in `tmp_path`, not the real data.
- Only declare dependencies that are actually used; add them when their stage gets implemented.
