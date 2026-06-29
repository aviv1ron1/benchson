from typing import Any, Dict, List
from src.llm.llm_provider import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key, model="gpt-4", base_url=None, extra_headers=None, model_params=None, **kwargs):
        super().__init__(**kwargs)  # must call it
        self.install_dependency("openai")  # Ensure the package is installed
        import openai

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        if extra_headers:
            client_kwargs["default_headers"] = extra_headers
        self.client = openai.OpenAI(**client_kwargs)
        self.model = model
        self.model_params = model_params or {}

    def _generate(
        self, messages: List[Dict[str, str]], parameters: Dict[str, Any] = None
    ) -> str:
        params = {**self.model_params, **(parameters or {})}
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, **params
        )
        return response.choices[0].message.content
