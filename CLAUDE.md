# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running

Always run from the project root (not from `src/`). The entry point resolves imports and dataset paths relative to the working directory.

```bash
# Install dependencies
uv sync

# Run with a config file
uv run python src/main.py --config configs/example.json

# Override output path (only used if config has no output_file)
uv run python src/main.py --config configs/example.json --output my_results.csv
```

The output CSV is automatically renamed to `{stem}-{total_score}-{total_instances}{ext}` (e.g., `results-17-20.csv`).

Configs placed in `configs/` (other than `example.json`) are git-ignored, so private API keys stay local.

## Architecture

The framework is config-driven. A single JSON config wires together one LLM provider, one optional observability provider, and N evaluations, each over N datasets. All three are **dynamically loaded** at runtime via `importlib` — the config specifies `module` (dotted import path) and `class` (class name).

### Core classes

| File | Purpose |
|---|---|
| `src/main.py` | Entry point. Loads config, instantiates providers/evaluations, writes CSV. |
| `src/provider.py` | `Provider` base: `install_dependency()` does lazy pip-install so only needed libraries are required. |
| `src/llm/llm_provider.py` | `LLMProvider(Provider)`: wraps `_generate()` with observability hooks. Implement `_generate()` in subclasses. |
| `src/observability/observability_provider.py` | `ObservabilityProvider(Provider)`: implement `log_request`, `log_response`, `log_evaluation`. |
| `src/evaluations/evaluation.py` | `Evaluation` base: override `prepare_test_case`, `format_for_llm`, `metric_function`. |
| `src/evaluations/evaluation_result.py` | `EvaluationResult(score, explanation, ground_truth)` — score must be 0 or 1. |
| `src/benchson_datasets/dataset.py` | `Dataset`: resolves relative paths as `{cwd}/data/{name}`, expects `train/` and `test/` subdirs. |

### LLM provider config placement

The `llm_provider` and `observability_provider` keys are **top-level** in the config (shared across all evaluations), not nested per-evaluation.

### Adding a new evaluation

Create `src/evaluations/{name}/{name}.py` + `__init__.py` + a readme. Extend `Evaluation`, implement `format_for_llm(test_case) -> list[dict]` and `metric_function(test_case, llm_result) -> EvaluationResult`. Optionally override `prepare_test_case(path)`.

### Adding a new LLM provider

Create `src/llm/{name}/{name}_provider.py` + `__init__.py` + a readme. Extend `LLMProvider`, call `self.install_dependency("lib")` in `__init__`, implement `_generate(messages, parameters) -> str`. Constructor must accept `**kwargs` and call `super().__init__(**kwargs)`.

### Adding a new observability provider

Same pattern under `src/observability/{name}/`. Extend `ObservabilityProvider`, implement the three `log_*` methods.

### Datasets

Placed under `data/`. Each dataset: `data/{name}/train/*.json` and `data/{name}/test/*.json`. Instances follow `{"data": {...}, "ground_truth": {...}}`. Test files drive evaluation; train files are optional reference material.
