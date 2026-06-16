import json

from data_generation.tasks.base_task import BaseDataTask


class SourceDocExtractionTask(BaseDataTask):
    """Generates (source_doc -> json) extraction examples.

    For a given schema it first produces a valid reference JSON, then asks the
    LLM to write a natural language document that contains all of that
    information. The training example teaches the model to recover the JSON from
    the document, grounding generation in real source content rather than
    invented values.
    """

    def generate(self, schema_path, llm_provider, max_retries):
        """Returns (messages, reference_json_str) or None."""
        result = self.generate_valid_json(schema_path, llm_provider, max_retries)
        if result is None:
            return None

        schema, reference_json_str, _ = result
        reference_json = json.loads(reference_json_str)

        source_doc = self._generate_source_doc(schema, reference_json, llm_provider)
        if not source_doc:
            return None

        messages = self._build_extraction_prompt(schema, source_doc)
        return messages, reference_json_str

    def _generate_source_doc(self, schema, reference_json, llm_provider):
        prompt = self._build_source_doc_prompt(schema, reference_json)
        doc, _ = llm_provider.generate(prompt)
        return doc.strip()
