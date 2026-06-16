# Description-grounded JSON benchmark

This benchmark measures whether a model produces the *correct* JSON for a schema —
not merely a schema-valid stub. Each record is grounded in a description of a
specific object and carries a ground-truth `reference_json`, so outputs are scored
for content fidelity as well as validity.

## Tasks

- **2a — create-by-description**: given a schema and a natural-language description
  of an object, produce a JSON object that conforms to the schema and matches the
  description.
- **2b — fix-invalid**: given a schema-violating version of a 2a object (plus the
  schema and description), repair it back to a valid object that matches the
  intended content.
- **2c — modify-by-instruction**: given a valid object, its schema, and a free-text
  change instruction (e.g. "remove the first two items from the cart"), return the
  correctly modified object. The change is applied programmatically to mint the
  ground truth (correct by construction and schema-valid), and the instruction is
  LLM-naturalized then round-trip gated so a fresh model can reproduce the result.

## Metrics (three independent axes)

Reported per record; the binary `Score` column is `schema_compliance`, the rest are
extra CSV columns.

| Metric | Meaning |
|---|---|
| `json_validity` | 1 if the output parses as JSON, else 0 |
| `schema_compliance` (`Score`) | 1 if the parsed output validates against the schema, else 0 |
| `semantic_fidelity` | fraction of ground-truth field values recovered in the output (extra output fields are not penalized) |

A model can pass one axis and fail another — valid JSON with wrong values (compliance
1, low fidelity), or malformed structure with the right content (compliance 0,
partial fidelity). Implemented in `src/evaluations/metrics.py` and shared by all
three evaluations.

## Schema corpus

| Source | Origin | License |
|---|---|---|
| `data/schemas` | JSONSchemaStore real-world schemas (shipped with Benchson) | MIT |
| `data/jsb_schemas` | JSONSchemaBench extra subsets — GitHub Easy/Medium/Hard, Kubernetes, Snowplow, GlaiveAI function-call | MIT (attribution below) |

JSONSchemaBench's own JSONSchemaStore subset is intentionally **not** imported — it
overlaps the schemas Benchson already ships. The import adds difficulty tiers and
domain diversity (Kubernetes, function-call, etc.) that the JSONSchemaStore corpus
lacks. Each generated instance records its `source` and `subset`, embedded in the
result `name`, so the CSV can be sliced by origin and difficulty tier.

> **Note on comparison.** JSONSchemaBench's published results measure *schema
> coverage* (can a framework emit any valid instance) across constrained-decoding
> backends — a different task. These scores are **not** directly comparable to the
> JSONSchemaBench leaderboard. JSONSchemaBench is used here only as a schema source.

> **Attribution.** Real-life schemas in `data/jsb_schemas` are sourced from
> [epfl-dlab/JSONSchemaBench](https://huggingface.co/datasets/epfl-dlab/JSONSchemaBench)
> (MIT), arXiv:2501.10868.

## Train / test split (contamination-safe)

The builder emits **both** a held-out `test/` benchmark and a `train/` set for
fine-tuning, into the same dataset structure (`data/benchmark_<task>/{train,test}/`).
The two are drawn from **disjoint schema pools** — schemas are partitioned (stratified
by source/subset, deterministic by seed, `split.test_ratio` default 0.15) so a model
fine-tuned on `train/` is never evaluated on a schema it saw. This schema-level split
is the real anti-contamination guarantee; the per-dataset folders are just where each
side lands.

Per-split gates differ by intent:

| | `test/` (benchmark) | `train/` (fine-tuning) |
|---|---|---|
| Sizing | ~150 / task | ~1,000 / task |
| Gates | full, incl. the round-trip validator | deterministic only (no round-trip) — cheaper, noise-tolerant |

`train/` records are projected into chat JSONL for SFT with the exporter
(`src/export_training.py`), which builds each prompt from the *evaluation's own*
`format_for_llm` so training prompts match eval prompts exactly. `test/` is never
exported. Only `test/` is scored by `run_benchmark.json`.

## Pipeline

Three config-driven stages, each run from the project root:

```bash
# 1. Import real-life schemas (no API key needed)
uv run python src/import_jsonschemabench.py --config configs/import_jsonschemabench.json

# 2. Build ground truth with a strong "builder" model (needs that provider's key)
uv run python src/build_benchmark.py --config configs/build_benchmark.json

# 3. Run the benchmark on a target model (set its provider in the config)
uv run python src/main.py --config configs/run_benchmark.json

# 4. (Optional) Export the train split to chat JSONL for fine-tuning
uv run python src/export_training.py --config configs/export_training.json
```

Stage 2 writes `data/benchmark_create/`, `data/benchmark_fix/`, and
`data/benchmark_modify/` (each with a `test/*.json` set), plus a `manifest.json` in
each dataset root recording provenance (builder model, per-source/subset counts,
seed, timestamp, attribution). A single minted reference object feeds all three
tasks. Both build and import are idempotent/resumable — re-running tops up to the
configured `counts`. The results CSV is renamed to
`{stem}-{total_score}-{total_instances}{ext}` as usual, with `json_validity` and
`semantic_fidelity` as extra columns.

The build process is intentionally **not reproducible** (the ground truth is
LLM-authored). The frozen, versioned dataset — not the generation step — is the
artifact: generate once, then commit it (or push it to the HF Hub) and version it.
The `manifest.json` is how each frozen dataset documents how it was made.

### Quality gates (stage 2)

Each candidate is validated before being written; failures are regenerated up to
`max_build_attempts` times, then the schema is skipped. Configured under
`validation` in `configs/build_benchmark.json`:

- **Deterministic (free):**
  - `reference_json` validates against the schema (enforced by the generation fix loop).
  - **Non-trivial** — at least `min_populated_fields` leaf values are non-empty/default (rejects stub-like objects).
  - **Value-grounding** — distinctive string values (names, ids, emails, enum labels) appear in the description, at ≥ `grounding_threshold`. Numbers/dates/booleans are skipped since prose legitimately rewords them.
  - **`erroneous_json` is genuinely schema-invalid** — error mutations that happen to still validate are discarded.
  - **modify edits stay schema-valid** — the modified object is re-validated against the schema; edits that would break it (e.g. clearing an array below `minItems`) are rejected and another edit is chosen.
- **Round-trip (one extra LLM call per instance):** a fresh model call attempts the task and the instance is kept only if `semantic_fidelity` vs the ground truth ≥ `round_trip_threshold` — re-extracting from the description (2a) or applying the naturalized instruction (2c). This proves each instance is actually solvable.

Generation stays **JSON-first** (the reference object is minted first, so the ground
truth is correct by construction); the round-trip check confirms the description /
instruction is a sufficient, unambiguous route to the expected output.

The 2c change-operation library (`src/data_generation/modifications.py`) covers
**array edits** (clear, remove first/last/Nth, keep-first, append a copy),
**scalar changes** (set/increment a number, toggle a boolean, switch an enum, change
a string), and **field add/remove** (delete an optional field, add a missing one) —
over top-level fields and one level of nesting inside object properties.

### Instance formats

`benchmark_create` instance:

```json
{
  "name": "...", "source": "jsonschemabench", "subset": "Github_easy",
  "schema": { "...": "..." },
  "description": "natural-language description encoding every value",
  "reference_json": { "...": "..." }
}
```

`benchmark_fix` instance additionally carries `erroneous_json` (a single
schema-violating mutation of `reference_json`) and stores the ground truth as
`valid_json`.

`benchmark_modify` instance:

```json
{
  "name": "...", "source": "...", "subset": "...",
  "schema": { "...": "..." },
  "data": { "...": "..." },                     // the object to modify
  "instructions": "free-text change request",
  "ground_truth": { "...": "..." },             // the correctly modified object
  "modification": { "op": "...", "path": ["..."], "precise_instruction": "..." }
}
```
