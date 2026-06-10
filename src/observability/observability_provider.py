import importlib
from typing import Dict, Any
from provider import Provider
from evaluations.evaluation_result import EvaluationResult


class ObservabilityProvider(Provider):
    """Base class for observability providers to track LLM calls."""

    def log_request(self, request: Dict[str, Any]) -> Any:
        """Logs the LLM request."""
        raise NotImplementedError("Subclasses must implement log_request")

    def log_response(self, trace: Any, response: Dict[str, Any]) -> Any:
        """Logs the LLM response."""
        raise NotImplementedError("Subclasses must implement log_response")

    def log_evaluation(self, trace: Any, evaluation_result: EvaluationResult) -> None:
        """Logs evaluation results"""
        raise NotImplementedError("Subclasses must implement log_evaluation")

    @staticmethod
    def from_config(config: Dict[str, Any]) -> "ObservabilityProvider":
        """Dynamically loads an observability provider from configuration."""
        provider_module = config.get("module")
        provider_class = config.get("class")
        params = config.get("params", {})

        if not provider_module or not provider_class:
            raise ValueError("Configuration must include 'module' and 'class' fields.")

        try:
            module = importlib.import_module(provider_module)
            observability_cls = getattr(module, provider_class)
        except ModuleNotFoundError:
            ObservabilityProvider.install_dependency(provider_module)
            module = importlib.import_module(provider_module)
            observability_cls = getattr(module, provider_class)
        except Exception as e:
            raise ImportError(
                f"Unexpected error while loading class {provider_class} from module {provider_module}: {e}"
            )

        return observability_cls(**params)
