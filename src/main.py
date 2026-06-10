import importlib
import json
import argparse
import csv
from benchson_datasets.dataset import Dataset
from llm.llm_provider import LLMProvider
from observability.observability_provider import ObservabilityProvider
import sys
import os
from pathlib import Path



sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def load_config(config_path):
    """Loads configuration from a JSON file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(results, output_path):
    """Saves evaluation results to a CSV file."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Evaluation Name", "Task Name", "Score"])
        writer.writerows(results)
    print(f"Results saved to {output_path}")


def run_evaluations(config):
    """Runs evaluations based on the provided configuration."""
    results = []

    observability_provider = None
    if "observability_provider" in config:
        observability_provider = ObservabilityProvider.from_config(
            config["observability_provider"]
        )

    llm_provider = LLMProvider.from_config(
        config["llm_provider"], observability_provider
    )

    for evaluation_config in config["evaluations"]:
        eval_name = evaluation_config["name"]
        datasets = [Dataset(ds) for ds in evaluation_config["datasets"]]

        evaluation_module = evaluation_config.get(
            "module", "src.evaluations.evaluation"
        )
        evaluation_class_name = evaluation_config.get("class", "Evaluation")

        try:
            module = importlib.import_module(evaluation_module)
            evaluation_class = getattr(module, evaluation_class_name)
        except (ModuleNotFoundError, AttributeError) as e:
            raise ImportError(
                f"Error loading evaluation class {evaluation_class_name} from {evaluation_module}: {e}"
            )

        # Instantiate the correct evaluation class
        eval_instance = evaluation_class(
            eval_name, datasets, llm_provider, observability_provider
        )
        eval_result = eval_instance.execute_evaluation()
        results.extend(eval_result)

    # compute and append total score
    total_score = sum(score for (_, _, score) in results)
    instances_num = len(results)

    orig = Path(config.get("output_file", "results.csv"))
    new_name = f"{orig.stem}-{total_score}-{instances_num}{orig.suffix}"
    output_path = str(orig.with_name(new_name))

    save_results(results, output_path)


def main():
    parser = argparse.ArgumentParser(description="Run LLM evaluations.")
    parser.add_argument(
        "--config", type=str, help="Path to the configuration JSON file."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results.csv",
        help="Path to save the CSV results.",
    )

    args = parser.parse_args()

    if not args.config:
        print("Error: Configuration file is required. Use --config <path>")
        return

    config = load_config(args.config)
    # Only override if config did not specify an output_file
    if config.get("output_file") is None:
        config["output_file"] = args.output

    run_evaluations(config)


if __name__ == "__main__":
    main()
