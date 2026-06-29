"""Projects the benchmark's `train/` records into chat/alpaca training data.

No LLM calls — each rich train record already contains the prompt inputs and the
ground-truth answer. To guarantee the training prompt matches what the model sees
at eval time, the prompt is built with the *evaluation's own* `format_for_llm`, and
the trailing (empty) assistant turn is replaced with the gold answer.

Only the `train/` split is exported; the held-out `test/` split is never touched.

Usage:
    uv run python src/export_training.py --config configs/export_training.json
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import json

from data_generation.tasks.base_task import BaseDataTask
from evaluations.create_by_schema.create_by_schema import CreateBySchema
from evaluations.json_error_evaluation.json_error_evaluation import ErrorJson
from evaluations.modify_json_evaluation.modify_json_evaluation import ModifyJson

# For each task: the eval that defines the prompt, a function mapping a stored
# record to that eval's test_case shape, and the record key holding the gold answer.
_TASKS = {
    "create": {
        "eval": CreateBySchema,
        "test_case": lambda r: {"data": r["schema"], "source_doc": r.get("description"),
                                "instructions": r.get("instructions")},
        "gold": "reference_json",
    },
    "fix": {
        "eval": ErrorJson,
        "test_case": lambda r: {"data": r["erroneous_json"], "schema": r["schema"],
                                "description": r.get("description")},
        "gold": "valid_json",
    },
    "modify": {
        "eval": ModifyJson,
        "test_case": lambda r: {"data": r["data"], "schema": r.get("schema"),
                                "instructions": r["instructions"]},
        "gold": "ground_truth",
    },
}


def export(config):
    out_cfg = config.get("output", {})
    out_path = out_cfg.get("path", "outputs/training_data/benchmark_train.jsonl")
    fmt = out_cfg.get("format", "chat")
    datasets = config.get("datasets", {
        "create": "benchmark_create", "fix": "benchmark_fix", "modify": "benchmark_modify"})

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    formatter = BaseDataTask()
    written = {}

    with open(out_path, "w", encoding="utf-8") as out:
        for task, spec in _TASKS.items():
            dataset = datasets.get(task)
            if not dataset:
                continue
            train_dir = os.path.join(os.getcwd(), "data", dataset, "train")
            if not os.path.isdir(train_dir):
                continue
            evaluator = spec["eval"].__new__(spec["eval"])  # format_for_llm needs no state
            n = 0
            for fn in sorted(os.listdir(train_dir)):
                if not fn.endswith(".json"):
                    continue
                with open(os.path.join(train_dir, fn), "r", encoding="utf-8") as f:
                    record = json.load(f)
                if spec["gold"] not in record:
                    continue
                messages = evaluator.format_for_llm(spec["test_case"](record))
                completion = json.dumps(record[spec["gold"]])
                example = formatter.format_example(messages, completion, fmt)
                example["task_type"] = task
                out.write(json.dumps(example) + "\n")
                n += 1
            written[task] = n
            print(f"[{task}] exported {n} examples from {dataset}/train")

    print(f"Wrote {sum(written.values())} training examples to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Export benchmark train split to training JSONL.")
    parser.add_argument("--config", type=str, required=True, help="Path to export config JSON.")
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    export(config)


if __name__ == "__main__":
    main()
