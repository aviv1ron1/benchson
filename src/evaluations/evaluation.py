import json
import os
from typing import Optional
from benchson_datasets.dataset import Dataset
from llm.llm_provider import LLMProvider
from observability.observability_provider import ObservabilityProvider
from evaluations.evaluation_result import EvaluationResult


class Evaluation:
    def __init__(
        self,
        name,
        datasets: Dataset,
        llm_provider: LLMProvider,
        observability_provider: Optional[ObservabilityProvider] = None,
    ):
        self.name = name

        if not isinstance(datasets, list):
            datasets = [datasets]

        self.datasets = datasets
        self.llm_provider = llm_provider
        self.observability_provider = observability_provider

    def iterate_test_cases(self):
        """Iterates through test instances from all datasets."""
        for dataset in self.datasets:
            for test_instance_path in dataset.iterate_files(mode="test"):
                yield self.prepare_test_case(test_instance_path)

    def prepare_test_case(self, test_instance_path):
        """Prepares a test case. Can be overridden in subclasses."""
        with open(test_instance_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        test_case = {
            "data": test_data.get("data"),
            "name": test_data.get("name", os.path.basename(test_instance_path)),
        }

        if "ground_truth" in test_data:
            test_case["ground_truth"] = test_data["ground_truth"]

        return test_case

    def format_for_llm(self, test_case):
        """Formats the test case into an LLM-ready input. Can be overridden."""
        return [
            {
                "role": "user",
                "content": f"Process the following data: {test_case['data']}",
            },
        ]

    def metric_function(self, test_case, llm_result) -> Optional[EvaluationResult]:
        """Computes a similarity score between the LLM result and the ground truth. Can be overridden."""
        ground_truth = test_case.get("ground_truth")
        if ground_truth is None:
            return None  # No ground truth available, cannot compute score

        return self._compute_similarity(llm_result, ground_truth)

    @staticmethod
    def _compute_similarity(self, result, ground_truth) -> EvaluationResult:
        """Default similarity function (Jaccard similarity). Can be overridden in subclasses."""
        set_result = set(result.split())
        set_ground_truth = set(ground_truth.split())

        intersection = len(set_result & set_ground_truth)
        union = len(set_result | set_ground_truth)

        return EvaluationResult(
            score=intersection / union if union != 0 else 0,
            ground_truth=ground_truth,
            explanation=f"intersection: {intersection} union: {union}",
        )

    def execute_evaluation(self):
        """Executes the evaluation, computing scores and returning results as a list."""
        results = []
        for test_case in self.iterate_test_cases():
            formatted_input = self.format_for_llm(test_case)
            llm_result, trace = self.llm_provider.generate(formatted_input)
            evaluation_result = self.metric_function(test_case, llm_result)
            if self.observability_provider:
                self.observability_provider.log_evaluation(
                    trace=trace, evaluation_result=evaluation_result
                )
            results.append((self.name, test_case["name"], evaluation_result.score))

        return results

    def __repr__(self):
        return f"Evaluation(name='{self.name}', datasets={[d.path for d in self.datasets]})"
