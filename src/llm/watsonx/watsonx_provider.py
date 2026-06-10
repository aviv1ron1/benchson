import importlib

from ..llm_provider import LLMProvider
from typing import Any, Dict, List


class IBMWatsonXProvider(LLMProvider):
    def __init__(
            self,
            api_key,
            project_id,
            model_params,
            model="ibm-mistral-7b",
            api_endpoint="https://us-south.ml.cloud.ibm.com/",
            **kwargs
    ):
        super().__init__(**kwargs)
        self.install_dependency("langchain_core")  # Ensure the package is installed
        self.install_dependency("langchain_ibm")  # Ensure the package is installed
        self.install_dependency("jinja2")  # Ensure the package is installed

        self.api_key = api_key
        self.api_endpoint = api_key
        self.project_id = project_id
        self.api_endpoint = api_endpoint
        self.model = model
        self.parameters = model_params or {}

    def _generate(
        self, messages: List[Dict[str, str]], parameters: Dict[str, Any] = None
    ) -> str:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_ibm import WatsonxLLM

        llm = WatsonxLLM(
            url=self.api_endpoint,
            project_id=self.project_id,
            apikey=self.api_key,
            model_id=self.model,
            params=parameters or self.parameters
        )

        prompt = ChatPromptTemplate.from_messages(
            messages=messages, template_format="jinja2"
        )
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke({})
        return response
