# Benchson tasks for lm-evaluation-harness

Run the Benchson JSON benchmark under
[lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness), so it
can be scored with lm-eval's model backends (HuggingFace, vLLM, OpenAI, …) alongside
other tasks.

## Tasks

| Task | Inputs → output |
|---|---|
| `benchson_create` | schema + description → JSON |
| `benchson_fix`    | schema + invalid JSON → repaired JSON |
| `benchson_modify` | schema + JSON + instruction → modified JSON |
| `benchson` (group) | the three families — headline scores |
| `benchson_tiers` (group) | every family split by difficulty tier / source (`benchson_<family>_<tier>`) |

Each task reports mean-aggregated **json_validity**, **schema_compliance**, and
**semantic_fidelity**; `fix`/`modify` add **change_fidelity** (fidelity over just the
field(s) the task changed — whole-object fidelity is dominated by unchanged fields).
Prompts are byte-for-byte identical to `src/main.py`'s `format_for_llm`, so scores are
comparable to the native runner.

## Data source

The tasks load the **published HF dataset** (`dataset_path: aviv1ron1/Benchson`,
configs `create`/`fix`/`modify`, split `test`). The raw per-instance files under
`data/benchmark_*/test/` are **not** directly loadable by `datasets` — each row's
nested `schema` differs, so Arrow schema inference fails. The HF export
(`src/export_hf.py`) serializes JSON fields to strings to give a uniform, loadable
schema; `utils.py` accepts both strings and raw objects.

To evaluate a **local** build without uploading, first run the export, then set in each
`benchson_*.yaml`:

```yaml
dataset_path: json
dataset_kwargs: { data_files: { test: outputs/hf_dataset/create/test.jsonl } }   # fix/modify likewise
```

## Requirements

- `pip install lm-eval jsonschema deepdiff`

## Run

```bash
# headline: one row per family
lm_eval --model hf --model_args pretrained=meta-llama/Llama-3.1-8B-Instruct \
  --tasks benchson --include_path lm_eval_tasks --apply_chat_template --output_path results/

# per-tier breakdown (Github_easy…hard, Kubernetes, Snowplow, Glaiveai2K, schemas, …)
lm_eval --model hf --model_args pretrained=... \
  --tasks benchson_tiers --include_path lm_eval_tasks --apply_chat_template

# a single family or a single tier
lm_eval --model hf --model_args pretrained=... \
  --tasks benchson_modify,benchson_create_Github_hard --include_path lm_eval_tasks --apply_chat_template
```

`--apply_chat_template` is recommended for instruct models (the prompt folds the
system + user content into one turn). Other backends work the same way, e.g.
`--model local-completions` / `--model openai-completions`.

## Per-tier tasks

`benchson_tiers` and the `tiers/benchson_<family>_<tier>.yaml` files are **generated** —
each `include:`s its base family task and filters docs to one tier via
`utils.keep_<tier>`. The single aggregate hides a large spread across difficulty
tiers, so use `benchson_tiers` to see it. Regenerate after rebuilding the benchmark
(tiers are read from the data):

```bash
uv run python lm_eval_tasks/generate_tier_tasks.py
```

## Notes

- **Scoring only:** build-time gates (round-trip validator, etc.) aren't part of scoring.
- **Held-out test only:** tasks use the `test` split; `train` is for fine-tuning and is never scored.
- `utils.py` mirrors `src/evaluations/metrics.py` and the evals' `format_for_llm`. If you
  change those, update `utils.py` (parity check: fold each eval's system+user with `\n\n`
  and compare to the matching `doc_to_text_*`).
