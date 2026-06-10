import json
import os
import random


_TASK_CLASSES = {}


def _task_class(name):
    if name not in _TASK_CLASSES:
        if name == "schema_creation":
            from data_generation.tasks.schema_creation import SchemaCreationTask
            _TASK_CLASSES[name] = SchemaCreationTask
        elif name == "error_correction":
            from data_generation.tasks.error_correction import ErrorCorrectionTask
            _TASK_CLASSES[name] = ErrorCorrectionTask
        elif name == "described_schema_creation":
            from data_generation.tasks.described_schema_creation import DescribedSchemaCreationTask
            _TASK_CLASSES[name] = DescribedSchemaCreationTask
        else:
            raise ValueError(f"Unknown task type: '{name}'. Supported: schema_creation, described_schema_creation, error_correction")
    return _TASK_CLASSES[name]


class DataGenerator:

    def __init__(self, config):
        self.output_path = config["output"]["path"]
        self.output_format = config["output"].get("format", "chat")
        self.tasks = config["tasks"]

    def generate(self, llm_provider):
        os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)

        for task_config in self.tasks:
            self._run_task(task_config, llm_provider)

    def _run_task(self, task_config, llm_provider):
        task_type = task_config["type"]
        count = task_config["count"]
        max_retries = task_config.get("max_retries", 3)

        task = _task_class(task_type)()
        instances = task.load_instances(
            source=task_config.get("source"),
            filter_kw=task_config.get("filter"),
            files=task_config.get("files"),
        )

        collected = 0
        max_attempts = count * 10

        for attempt in range(max_attempts):
            if collected >= count:
                break

            schema_path = random.choice(instances)
            result = task.generate(schema_path, llm_provider, max_retries)

            if result is not None:
                messages, output = result
                example = task.format_example(messages, output, self.output_format)
                with open(self.output_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(example) + "\n")
                collected += 1
                print(f"[{task_type}] {collected}/{count} collected")

        if collected < count:
            print(
                f"Warning: [{task_type}] only collected {collected}/{count} examples "
                f"after {max_attempts} attempts. The LLM may be struggling with these schemas."
            )
        else:
            print(f"[{task_type}] Done — {collected} examples written to {self.output_path}")
