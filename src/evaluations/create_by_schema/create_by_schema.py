import json
from evaluations.evaluation import Evaluation
from evaluations.evaluation_result import EvaluationResult
from evaluations import metrics


class CreateBySchema(Evaluation):
    def prepare_test_case(self, test_instance_path):
        """Loads a test case from the dataset.

        Two formats are supported:
        - Legacy: the file is a raw JSON Schema. The model is asked to invent a
          conforming object.
        - Enriched (grounded): the file is an object with a `schema` key, plus
          optional grounding text (`source_doc` or `description`), a
          `reference_json` ground truth, and `instructions`. The model is asked to
          produce the JSON from the grounding text, and the output is additionally
          scored for semantic fidelity against `reference_json`.
        """
        with open(test_instance_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        if isinstance(loaded, dict) and "schema" in loaded:
            schema = loaded["schema"]
            # `description` and `source_doc` are interchangeable grounding text.
            grounding = loaded.get("source_doc") or loaded.get("description")
            test_case = {
                "data": schema,
                "name": _instance_name(loaded, schema, test_instance_path),
                "source_doc": grounding,
                "instructions": loaded.get("instructions"),
            }
            if "reference_json" in loaded:
                test_case["reference_json"] = loaded["reference_json"]
            return test_case

        # Legacy: the whole file is the schema.
        return {
            "data": loaded,
            "name": loaded.get("title", test_instance_path),
        }

    def format_for_llm(self, test_case):
        """Formats the test case to prompt the LLM.

        When grounding text is present, the model is asked to extract/produce the
        information from it; otherwise it is asked to invent a conforming object
        (legacy behavior).
        """
        schema = test_case["data"]
        grounding = test_case.get("source_doc")

        if grounding:
            instructions = test_case.get("instructions") or (
                "Create a JSON object that conforms to the schema, using the "
                "information in the following description."
            )
            user_content = (
                f"{instructions}\n\n"
                f"Description:\n{grounding}\n\n"
                f"Schema:\n{json.dumps(schema, indent=2)}"
            )
            system_content = (
                "You are a helpful assistant that turns a described object into JSON "
                "data matching a given schema. Output only the json with no other "
                "text or explanations."
            )
        else:
            user_content = (
                f"Generate a JSON object that conforms to the following schema: "
                f"{json.dumps(schema, indent=2)}"
            )
            system_content = (
                "You are a helpful assistant that generates JSON data based on a given "
                "schema. Output only the json with no other text or explanations."
            )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": ""},
        ]

    def metric_function(self, test_case, llm_result):
        """Scores the model output on three independent dimensions.

        - json_validity (metric): 1 if the output parses as JSON, else 0.
        - schema_compliance (primary score): 1 if the parsed output conforms to
          the schema, else 0.
        - semantic_fidelity (metric, only when `reference_json` is present): the
          fraction of reference field values recovered in the output. Extra fields
          in the output are not penalized.
        """
        schema = test_case["data"]
        reference = test_case.get("reference_json")

        parsed, parse_error = metrics.parse_json(llm_result)
        valid = parsed is not None
        result_metrics = {"json_validity": 1 if valid else 0}

        if not valid:
            score, explanation = 0, parse_error
        else:
            score, explanation = metrics.schema_compliance(parsed, schema)

        if reference is not None:
            fidelity = metrics.semantic_fidelity(reference, parsed) if valid else 0.0
            result_metrics["semantic_fidelity"] = round(fidelity, 4)
            explanation = f"{explanation} | semantic_fidelity={result_metrics['semantic_fidelity']}"

        return EvaluationResult(score=score, explanation=explanation, metrics=result_metrics)


def _instance_name(loaded, schema, path):
    """Builds a result name that embeds source/subset for later slicing."""
    base = loaded.get("name") or schema.get("title") or path
    tags = [loaded[k] for k in ("source", "subset") if loaded.get(k)]
    return f"{base} [{'/'.join(tags)}]" if tags else base
