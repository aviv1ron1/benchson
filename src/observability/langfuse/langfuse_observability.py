import os
from typing import Dict, Any
from observability.observability_provider import ObservabilityProvider
from evaluations.evaluation_result import EvaluationResult


class LangfuseObservability(ObservabilityProvider):
    """Langfuse observability provider for logging LLM calls."""

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        host: str,
        httpx_client_file_path: str,
        tags=None,
        metadata=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.install_dependency("langfuse")
        self.install_dependency("httpx")
        from langfuse import Langfuse
        import httpx

        httpx_client = httpx.Client(verify=os.getcwd() + os.sep + httpx_client_file_path)
        self.langfuse = Langfuse(
            public_key=public_key, secret_key=secret_key, host=host, httpx_client=httpx_client
        )
        self.tags = tags
        self.metadata = metadata

    def log_request(self, request: Dict[str, Any]) -> Any:
        trace = self.langfuse.trace(metadata=self.metadata, tags=self.tags)

        generation = trace.generation(
            model=request.get("model", "unknown-model"),
            model_parameters=request.get("parameters", {}),
            input=request.get("messages", []),
            metadata=request.get("metadata", {}),
        )
        return generation

    def log_response(self, trace: Any, response: Dict[str, Any]) -> None:
        """Logs the LLM response to Langfuse using the trace object returned by log_request."""
        if trace:
            trace.end(
                output=response.get("completion", ""),
                usage_details=response.get("usage", {}),
            )

    def log_evaluation(self, trace: Any, evaluation_result: EvaluationResult) -> None:
        if trace:
            trace_id = trace.trace_id
            self.langfuse.trace(
                id=trace_id,
                output=f"score: {evaluation_result.score}",
                metadata={
                    "explanation": evaluation_result.explanation,
                    "ground_truth": evaluation_result.ground_truth,
                },
            )
