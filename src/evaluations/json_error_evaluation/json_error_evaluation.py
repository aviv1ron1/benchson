import json
from evaluations.evaluation import Evaluation
from evaluations.evaluation_result import EvaluationResult
from evaluations import metrics


class ErrorJson(Evaluation):
    def prepare_test_case(self, test_instance_path):
        """Loads an invalid JSON object, its schema, and the ground-truth fix.

        Expected fields: `erroneous_json`, `schema`, `valid_json` (or
        `reference_json`), and optionally a `description` of the intended object
        (used to help recover values that the injected error removed). `source`
        and `subset` are echoed into the result name for slicing.
        """
        with open(test_instance_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        schema = test_data.get("schema")
        return {
            "data": test_data.get("erroneous_json"),
            "schema": schema,
            "ground_truth": test_data.get("valid_json", test_data.get("reference_json")),
            "description": test_data.get("description"),
            "name": _instance_name(test_data, schema, test_instance_path),
        }

    def format_for_llm(self, test_case):
        """Formats the fix-it prompt for the LLM."""
        user_content = (
            "Please correct the following JSON so that it fully matches the given schema:\n\n"
            "JSON:\n```json\n"
            f"{json.dumps(test_case['data'], indent=2)}\n```\n\n"
            "Schema:\n```json\n"
            f"{json.dumps(test_case['schema'], indent=2)}\n```"
        )
        description = test_case.get("description")
        if description:
            user_content += (
                "\n\nThe corrected JSON should describe the following:\n"
                f"{description}"
            )

        return [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant tasked with fixing JSON objects to conform precisely "
                    "to the provided JSON schema. Return ONLY the corrected JSON object, "
                    "with no additional text or explanation."
                ),
            },
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": ""},
        ]

    def metric_function(self, test_case, llm_result):
        """Scores the corrected JSON on three independent dimensions.

        - json_validity (metric): 1 if the output parses as JSON, else 0.
        - schema_compliance (primary score): 1 if the parsed output conforms to
          the schema, else 0.
        - semantic_fidelity (metric, only when ground truth is present): the
          fraction of ground-truth field values recovered in the output.
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
            # No schema to validate against — fall back to exact match on ground truth.
            score = 1 if parsed == ground_truth else 0
            explanation = "matches ground truth" if score else "differs from ground truth"

        erroneous = test_case.get("data")
        if ground_truth is not None:
            fidelity = metrics.semantic_fidelity(ground_truth, parsed) if valid else 0.0
            result_metrics["semantic_fidelity"] = round(fidelity, 4)
            explanation = f"{explanation} | semantic_fidelity={result_metrics['semantic_fidelity']}"
            # change_fidelity: did the model fix the field(s) that were actually broken?
            if erroneous is not None:
                paths = metrics.changed_paths(erroneous, ground_truth)
                cf = metrics.region_fidelity(parsed, ground_truth, paths) if valid else 0.0
                result_metrics["change_fidelity"] = round(cf, 4)
            # exact_match: strict, fully-correct repair (valid + schema-compliant + all fields).
            result_metrics["exact_match"] = 1 if (score == 1 and fidelity >= 1.0) else 0

        return EvaluationResult(score=score, explanation=explanation, metrics=result_metrics)


def _instance_name(test_data, schema, path):
    """Builds a result name that embeds source/subset for later slicing."""
    base = test_data.get("name") or (schema or {}).get("title") or path
    tags = [test_data[k] for k in ("source", "subset") if test_data.get(k)]
    return f"{base} [{'/'.join(tags)}]" if tags else base
