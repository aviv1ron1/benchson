from data_generation.tasks.base_task import BaseDataTask


class SchemaCreationTask(BaseDataTask):

    def generate(self, schema_path, llm_provider, max_retries):
        """Returns (messages, valid_json_str) or None."""
        result = self.generate_valid_json(schema_path, llm_provider, max_retries)
        if result is None:
            return None
        _, valid_json_str, initial_messages = result
        return initial_messages, valid_json_str
