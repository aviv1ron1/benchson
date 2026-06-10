import json
import re
import jsonschema
from evaluations.evaluation import Evaluation
from evaluations.evaluation_result import EvaluationResult


class CreateBySchema(Evaluation):
    def prepare_test_case(self, test_instance_path):
        """Loads a JSON schema from the dataset."""
        with open(test_instance_path, "r", encoding="utf-8") as f:
            schema_data = json.load(f)

        return {
            "data": schema_data,
            "name": schema_data.get("title", test_instance_path),
        }

    def format_for_llm(self, test_case):
        """Formats the test case to prompt the LLM to generate JSON conforming to the schema."""
        return [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates JSON data based on a given schema. Output only the json with no other text or explanations.",
            },
            {
                "role": "user",
                "content": f"Generate a JSON object that conforms to the following schema: {json.dumps(test_case['data'], indent=2)}",
            },
            {
                "role": "assistant",
                "content": ""
            }
        ]

    def metric_function(self, test_case, llm_result):
        """Checks if the generated JSON is valid against the schema. Returns 1 if valid, 0 otherwise."""
        schema = test_case["data"]
        try:
            if llm_result.startswith("```json"):
                llm_result = re.sub(r"```json\s*|\s*```", "", llm_result).strip()
            generated_json = json.loads(llm_result)
            jsonschema.validate(instance=generated_json, schema=schema)
            # Valid JSON according to schema
            return EvaluationResult(score=1, explanation="valid")
        except (json.JSONDecodeError, jsonschema.ValidationError) as e:
            # Invalid JSON or does not conform to schema
            return EvaluationResult(score=0, explanation=f"{e}")
