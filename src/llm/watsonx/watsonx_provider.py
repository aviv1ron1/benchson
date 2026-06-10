import warnings

from ..llm_provider import LLMProvider
from typing import Any, Dict, List, Optional


class IBMWatsonXProvider(LLMProvider):
    def __init__(
            self,
            api_key,
            project_id,
            model_params,
            model="ibm/granite-3-1-8b-instruct",
            api_endpoint="https://us-south.ml.cloud.ibm.com/",
            **kwargs
    ):
        super().__init__(**kwargs)
        self.install_dependency("langchain_ibm")
        self.api_key = api_key
        self.project_id = project_id
        self.api_endpoint = api_endpoint
        self.model = model
        self.parameters = model_params or {}

    def _generate(
        self, messages: List[Dict[str, str]], parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        from langchain_ibm import ChatWatsonx
        from pydantic import SecretStr

        role_map = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}
        lc_messages = [
            role_map.get(m["role"], HumanMessage)(content=m["content"])
            for m in messages
            if m.get("content")  # skip empty assistant turn used as prompt prefix
        ]

        chat = ChatWatsonx(
            model_id=self.model,
            url=SecretStr(self.api_endpoint),
            project_id=self.project_id,
            apikey=self.api_key,
            params=parameters or self.parameters,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = chat.invoke(lc_messages)
        content = response.content
        return content if isinstance(content, str) else str(content)
