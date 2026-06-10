import json
from evaluations.evaluation import Evaluation
from evaluations.evaluation_result import EvaluationResult


class ErrorJson(Evaluation):
    def prepare_test_case(self, test_instance_path):
        """
        Loads the original JSON data and ground truth from the dataset instance.
        """
        with open(test_instance_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        return {
            "data": test_data.get("erroneous_json"),
            "schema": test_data.get("schema"),
            "ground_truth": test_data.get("valid_json"),
            "name": test_data.get("name", test_instance_path),
        }

    def format_for_llm(self, test_case):
        """
        Formats the input for the LLM.
        """
        return [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant tasked with fixing JSON objects to conform precisely "
                    "to the provided JSON schema. Return ONLY the corrected JSON object, "
                    "with no additional text or explanation."
                )
            },
            {
                "role": "user",
                "content": (
                    "Please correct the following JSON so that it fully matches the given schema:\n\n"
                    "JSON:\n```json\n"
                    f"{json.dumps(test_case['data'], indent=2)}\n```\n\n"
                    "Schema:\n```json\n"
                    f"{json.dumps(test_case['schema'], indent=2)}\n```"
                )
            },
            {
                "role": "assistant",
                "content": ""
            }
        ]

    def metric_function(self, test_case, llm_result):
        """
        Compares the LLM's output to the expected ground truth JSON.
        Prints details for debugging during evaluation.
        """
        print("\n🔍 Running metric_function")
        print("🔸 Raw LLM result:\n", llm_result)

        cleaned_json = llm_result.strip()
        if cleaned_json.startswith("```json"):
            cleaned_json = cleaned_json[len("```json"):].strip()
        if cleaned_json.endswith("```"):
            cleaned_json = cleaned_json[:-3].strip()
        print("🔹 Cleaned JSON string:\n", cleaned_json)

        try:
            llm_output = json.loads(cleaned_json)
            ground_truth = test_case.get('ground_truth')

            print("✅ Parsed LLM output:", llm_output)
            print("🎯 Ground truth:", ground_truth)

            if ground_truth is None:
                print("⚠️ No ground truth provided — assuming valid.")
                return EvaluationResult(score=1, explanation="No ground truth provided. Output is assumed valid.")

            if llm_output == ground_truth:
                print("✅ Match: JSON was corrected correctly.")
                return EvaluationResult(score=1, explanation="JSON corrected exactly matches ground truth.")
            else:
                print("❌ Mismatch: corrected JSON does not match expected.")
                return EvaluationResult(score=0, explanation="Corrected JSON does not match expected output.")

        except json.JSONDecodeError as e:
            print("❌ JSON decode error:", e)
            return EvaluationResult(score=0, explanation=f"Invalid JSON format: {e}")


