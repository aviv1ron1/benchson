from typing import List, Dict, Any, Optional, Tuple
import importlib
from src.provider import Provider
from src.observability.observability_provider import ObservabilityProvider


class LLMProvider(Provider):

    def __init__(
        self, observability_provider: Optional[ObservabilityProvider] = None, **kwargs
    ):
        self.observability_provider = observability_provider
        self.model = None
        super().__init__(**kwargs)  # Ensure subclass initialization doesn't break

    def generate(
        self, messages: List[Dict[str, str]], parameters: Dict[str, Any] = None
    ) -> tuple[str, Any | None]:
        """
        Generates a response from an LLM, with observability tracking.
        """
        request_data = {
            "name": "llm-request",
            "model": self.model,
            "parameters": parameters or {},
            "messages": messages,
        }

        trace = None
        if self.observability_provider:
            trace = self.observability_provider.log_request(request_data)

        response = self._generate(messages, parameters)

        if self.observability_provider:
            self.observability_provider.log_response(trace, {"completion": response})

        return response, trace

    def _generate(
        self, messages: List[Dict[str, str]], parameters: Dict[str, Any] = None
    ) -> str:
        """
        Generates a response from an LLM.

        Args:
            messages (List[Dict[str, str]]): A list of messages in the format
                [{'role': 'system', 'content': '...'}, {'role': 'user', 'content': '...'}].
            parameters (Dict[str, Any], optional): Additional parameters like temperature, max tokens, etc.

        Returns:
            str: The generated response.
        """
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def from_config(
        config: Dict[str, Any],
        observability_provider: Optional[ObservabilityProvider] = None,
    ):
        """Dynamically loads and instantiates an LLMProvider based on configuration."""
        provider_module = config.get("module")
        provider_class = config.get("class")
        params = config.get("params", {})

        if not provider_module or not provider_class:
            raise ValueError("Configuration must include 'module' and 'class' fields.")

        try:
            module = importlib.import_module(provider_module)
            provider_cls = getattr(module, provider_class)
        except ModuleNotFoundError:
            LLMProvider.install_dependency(provider_module)
            module = importlib.import_module(provider_module)
            provider_cls = getattr(module, provider_class)
        except Exception as e:
            raise ImportError(
                f"Unexpected error while loading class {provider_class} from module {provider_module}: {e}"
            )

        return provider_cls(observability_provider=observability_provider, **params)
