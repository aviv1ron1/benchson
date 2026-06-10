import json
from jsonschema import Draft7Validator, validate, exceptions as jsonschema_exceptions
from evaluations.evaluation import Evaluation
from evaluations.evaluation_result import EvaluationResult


class SchemaFromInstances(Evaluation):
    def prepare_test_case(self, test_instance_path):
        """
        Loads the original JSON data and ground truth from the dataset instance.
        """
        with open(test_instance_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        return {
            "instances": test_data.get("instances", []),
            "name": test_data.get("name", test_instance_path)
        }

    def format_for_llm(self, test_case):
        """
        Formats the input for the LLM.
        """
        instances_list = test_case["instances"]
        instances_str = "\n".join([json.dumps(instance, indent=2) for instance in instances_list])
        return [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates JSON Schema Draft-07 definitions for provided JSON data."
            },
            {
                "role": "user",
                "content": f"Given the following JSON instances:\n```json\n{instances_str}\n```\nGenerate a JSON Schema Draft-07 that validates each object individually. Output only the schema, with no extra explanations."
            },
            {
                "role": "assistant",
                "content": ""
            }
        ]

    def metric_function(self, test_case, llm_result):
        """
        Validates that the LLM-generated schema:
        1. Is a valid JSON Schema Draft-07.
        2. Successfully validates all provided instances.
        """
        print("\nRunning metric_function")
        print("Raw LLM result:\n", llm_result)

        cleaned_schema = llm_result.strip()
        if cleaned_schema.startswith("```json"):
            cleaned_schema = cleaned_schema[len("```json"):].strip()
        if cleaned_schema.endswith("```"):
            cleaned_schema = cleaned_schema[:-3].strip()
        print("Cleaned JSON Schema string:\n", cleaned_schema)

        try:
            schema = json.loads(cleaned_schema)
        except json.JSONDecodeError as e:
            print("JSON decode error:", e)
            return EvaluationResult(score=0, explanation=f"Output is not valid JSON: {e}")

        # Step 1: Validate schema structure
        try:
            Draft7Validator.check_schema(schema)
        except jsonschema_exceptions.SchemaError as e:
            print("Schema structure validation error:", e)
            return EvaluationResult(score=0, explanation=f"Invalid JSON Schema Draft-07: {e.message}")

        # Step 2: Validate all instances against the schema
        for i, instance in enumerate(test_case["instances"]):
            try:
                validate(instance, schema)
            except jsonschema_exceptions.ValidationError as e:
                print(f"Instance {i} failed validation: {e.message}")
                return EvaluationResult(score=0, explanation=f"Instance {i} failed validation against schema: {e.message}")

        print("All instances passed validation.")
        return EvaluationResult(score=1, explanation="Valid schema and all instances conform to it.")


