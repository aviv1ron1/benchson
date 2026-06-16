# Benchson tasks for lm-evaluation-harness

Run the Benchson JSON benchmark under
[lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness), so it
can be scored with lm-eval's model backends (HuggingFace, vLLM, OpenAI, …) alongside
other tasks.

## Tasks

| Task | Dataset (local) | Inputs → output |
|---|---|---|
| `benchson_create` | `data/benchmark_create/test/*.json` | schema + description → JSON |
| `benchson_fix`    | `data/benchmark_fix/test/*.json`    | schema + invalid JSON → repaired JSON |
| `benchson_modify` | `data/benchmark_modify/test/*.json` | schema + JSON + instruction → modified JSON |
| `benchson` (group) | all three | runs them together |

Each task reports three metrics (mean-aggregated): **json_validity**,
**schema_compliance**, **semantic_fidelity**. Prompts are byte-for-byte identical to
`src/main.py`'s `format_for_llm`, so scores are comparable to the native runner.

## Requirements

- `pip install lm-eval` (the harness)
- `pip install jsonschema deepdiff` (used by `utils.py` for scoring)
- The benchmark must be built first (`data/benchmark_*/test/` populated) — see
  [../BENCHMARK.md](../BENCHMARK.md).

## Run

From the **repo root** (the dataset globs are relative to the working directory):

```bash
# all three tasks, e.g. against a local HF model
lm_eval --model hf \
  --model_args pretrained=meta-llama/Llama-3.1-8B-Instruct \
  --tasks benchson \
  --include_path lm_eval_tasks \
  --apply_chat_template \
  --output_path results/

# a single task
lm_eval --model hf --model_args pretrained=... \
  --tasks benchson_modify --include_path lm_eval_tasks --apply_chat_template
```

`--apply_chat_template` is recommended for instruct models (the prompt folds the
system + user content into one turn). Other backends work the same way, e.g.
`--model local-completions`/`--model openai-completions` with the appropriate
`--model_args`.

## Notes

- **Scoring only:** the build-time quality gates (round-trip validator, etc.) are not
  part of scoring, so nothing is lost vs. the native runner.
- **Held-out test only:** these tasks point at `test/`. The `train/` split is for
  fine-tuning and is never scored.
- **Sharing:** to run elsewhere, push the `test/` splits to the HF Hub and change
  `dataset_path` in each YAML from `json` + local globs to the dataset repo id.
- `utils.py` mirrors `src/evaluations/metrics.py` and the evals' `format_for_llm`.
  If you change those, update `utils.py` (a parity check: fold each eval's
  system+user with `\n\n` and compare to the matching `doc_to_text_*`).
