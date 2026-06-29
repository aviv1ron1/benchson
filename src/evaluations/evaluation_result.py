from typing import Optional


class EvaluationResult:
    def __init__(
        self,
        score: int,
        explanation: str,
        ground_truth: Optional[str] = None,
        metrics: Optional[dict] = None,
    ):
        if score not in [0, 1]:
            raise ValueError("Score must be either 0 or 1.")

        self.score = score
        self.explanation = explanation
        self.ground_truth = ground_truth
        # Optional named secondary metrics (e.g. semantic_fidelity). Each value
        # is a float; the primary binary `score` is reported separately.
        self.metrics = metrics or {}

    def __repr__(self):
        return (
            f"EvaluationResult(score={self.score}, explanation={self.explanation}, "
            f"ground_truth={self.ground_truth}, metrics={self.metrics})"
        )
