from llm.llm_provider import LLMProvider


class HuggingFaceProvider(LLMProvider):

    def __init__(self, model, model_params=None, device_map="auto", torch_dtype="bfloat16", **kwargs):
        super().__init__(**kwargs)
        self.install_dependency("transformers")
        self.install_dependency("torch")
        self.install_dependency("accelerate")
        self.model_name = model
        self.model_params = model_params or {}
        self.device_map = device_map
        self.torch_dtype = torch_dtype
        self._pipe = None

    def _generate(self, messages, parameters=None):
        if self._pipe is None:
            import torch
            from transformers import pipeline
            _DTYPES = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}
            self._pipe = pipeline(
                "text-generation",
                model=self.model_name,
                device_map=self.device_map,
                torch_dtype=_DTYPES.get(self.torch_dtype, torch.bfloat16),
            )

        params = {**self.model_params, **(parameters or {})}
        max_new_tokens = params.pop("max_new_tokens", 1024)

        # Drop trailing empty assistant turn — pipeline adds the generation prompt itself
        msgs = [m for m in messages if not (m["role"] == "assistant" and not m.get("content"))]

        result = self._pipe(msgs, max_new_tokens=max_new_tokens, return_full_text=False, **params)
        output = result[0]["generated_text"]
        # When input is messages, pipeline may return the appended messages list
        if isinstance(output, list):
            return output[-1]["content"]
        return output
