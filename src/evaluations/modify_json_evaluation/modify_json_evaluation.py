import json
from evaluations.evaluation import Evaluation
from evaluations.evaluation_result import EvaluationResult
from evaluations import metrics


class ModifyJson(Evaluation):
    def prepare_test_case(self, test_instance_path):
        """Loads the original JSON, the change instruction, and the ground truth.

        Expected fields: `data` (the object to modify), `instructions` (free-text
        change), `ground_truth` (the correctly modified object), and optionally
        `schema`. `source`/`subset` are echoed into the result name for slicing.
        """
        with open(test_instance_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        schema = test_data.get("schema")
        return {
            "data": test_data.get("data"),
            "schema": schema,
            "instructions": test_data.get("instructions"),
            "ground_truth": test_data.get("ground_truth"),
            "name": _instance_name(test_data, schema, test_instance_path),
        }

    def format_for_llm(self, test_case):
        """Formats the modification prompt, including the schema when present."""
        user_content = (
            f"Given the following JSON:\n```json\n{json.dumps(test_case['data'], indent=2)}\n```\n"
            f"Modify it as instructed: {test_case['instructions']}"
        )
        schema = test_case.get("schema")
        if schema is not None:
            user_content += (
                f"\n\nThe result must still conform to this schema:\n{json.dumps(schema, indent=2)}"
            )

        return [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that modifies JSON objects based on given "
                    "instructions. Output only the modified JSON with no other text or explanations."
                ),
            },
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": ""},
        ]

    def metric_function(self, test_case, llm_result):
        """Scores the modified JSON on three independent dimensions.

        - json_validity (metric): 1 if the output parses as JSON, else 0.
        - schema_compliance (primary score): 1 if the parsed output conforms to
          the schema, else 0. With no schema, falls back to exact match on the
          ground truth.
        - semantic_fidelity (metric): the fraction of ground-truth field values
          recovered in the output (i.e. whether the change was applied correctly).
        """
        schema = test_case.get("schema")
        ground_truth = test_case.get("ground_truth")

        parsed, parse_error = metrics.parse_json(llm_result)
        valid = parsed is not None
        result_metrics = {"json_validity": 1 if valid else 0}

        if not valid:
            score, explanation = 0, parse_error
        elif schema is not None:
            score, explanation = metrics.schema_compliance(parsed, schema)
        else:
            score = 1 if parsed == ground_truth else 0
            explanation = "matches ground truth" if score else "differs from ground truth"

        original = test_case.get("data")
        if ground_truth is not None:
            fidelity = metrics.semantic_fidelity(ground_truth, parsed) if valid else 0.0
            result_metrics["semantic_fidelity"] = round(fidelity, 4)
            explanation = f"{explanation} | semantic_fidelity={result_metrics['semantic_fidelity']}"
            # change_fidelity: did the model actually apply the requested edit?
            if original is not None:
                paths = metrics.changed_paths(original, ground_truth)
                cf = metrics.region_fidelity(parsed, ground_truth, paths) if valid else 0.0
                result_metrics["change_fidelity"] = round(cf, 4)

        return EvaluationResult(score=score, explanation=explanation, metrics=result_metrics)


def _instance_name(test_data, schema, path):
    """Builds a result name that embeds source/subset for later slicing."""
    base = test_data.get("name") or (schema or {}).get("title") or path
    tags = [test_data[k] for k in ("source", "subset") if test_data.get(k)]
    return f"{base} [{'/'.join(tags)}]" if tags else base
