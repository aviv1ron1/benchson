import concurrent.futures
import json
import os
import random
import threading
import time


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
        elif name == "source_doc_extraction":
            from data_generation.tasks.source_doc_extraction import SourceDocExtractionTask
            _TASK_CLASSES[name] = SourceDocExtractionTask
        else:
            raise ValueError(f"Unknown task type: '{name}'. Supported: schema_creation, described_schema_creation, source_doc_extraction, error_correction")
    return _TASK_CLASSES[name]


class DataGenerator:

    def __init__(self, config):
        self.output_path = config["output"]["path"]
        self.output_format = config["output"].get("format", "chat")
        self.tasks = config["tasks"]

    # Substrings in the system message that uniquely identify each task type.
    # Used as a fallback to classify lines written before task_type tagging was added.
    _TASK_FINGERPRINTS = {
        "schema_creation": "generates JSON data based on a given schema",
        "described_schema_creation": "generates JSON data. Output only the JSON",
        "source_doc_extraction": "extracts information from text into JSON data",
        "error_correction": "fixing JSON objects to conform precisely",
    }

    def generate(self, llm_provider):
        os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)

        for task_config in self.tasks:
            self._run_task(task_config, llm_provider)

    def _count_existing(self, task_type):
        """Count lines in the output file that belong to task_type."""
        if not os.path.exists(self.output_path):
            return 0
        fingerprint = self._TASK_FINGERPRINTS.get(task_type, "")
        count = 0
        with open(self.output_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("task_type") == task_type:
                    count += 1
                elif "task_type" not in obj and fingerprint:
                    raw = json.dumps(obj)
                    if fingerprint in raw:
                        count += 1
        return count

    def _run_task(self, task_config, llm_provider):
        task_type = task_config["type"]
        count = task_config["count"]
        max_retries = task_config.get("max_retries", 3)
        concurrency = task_config.get("concurrency", 1)

        task = _task_class(task_type)(system_prompt_prefix=task_config.get("system_prompt_prefix", ""))
        instances = task.load_instances(
            source=task_config.get("source"),
            filter_kw=task_config.get("filter"),
            files=task_config.get("files"),
            max_schema_kb=task_config.get("max_schema_kb", 10),
        )

        collected = self._count_existing(task_type)
        if collected >= count:
            print(f"[{task_type}] Already have {collected}/{count} — skipping.")
            return
        if collected > 0:
            print(f"[{task_type}] Resuming from {collected}/{count}.")

        lock = threading.Lock()
        counter = [collected]

        def _attempt():
            schema_path = random.choice(instances)
            try:
                result = task.generate(schema_path, llm_provider, max_retries)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate limit" in err_str.lower() or "too many" in err_str.lower():
                    print(f"[{task_type}] Rate limited — sleeping 30s ({e})")
                    time.sleep(30)
                else:
                    print(f"[{task_type}] Skipping sample (error: {e})")
                return None
            return result

        remaining = count - collected
        max_attempts = remaining * 10
        submitted = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            pending = set()

            while counter[0] < count and submitted < max_attempts:
                # Keep the pool full.
                while len(pending) < concurrency and submitted < max_attempts:
                    pending.add(executor.submit(_attempt))
                    submitted += 1

                done, pending = concurrent.futures.wait(
                    pending, return_when=concurrent.futures.FIRST_COMPLETED
                )

                for future in done:
                    result = future.result()
                    if result is None:
                        continue
                    messages, output = result
                    if len(output.strip()) < 10:
                        print(f"[{task_type}] Skipping trivial output: {output.strip()!r}")
                        continue
                    with lock:
                        if counter[0] >= count:
                            continue
                        example = task.format_example(messages, output, self.output_format)
                        example["task_type"] = task_type
                        with open(self.output_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(example) + "\n")
                        counter[0] += 1
                        print(f"[{task_type}] {counter[0]}/{count} collected")

            # Cancel any still-pending futures once the target is reached.
            for future in pending:
                future.cancel()

        if counter[0] < count:
            print(
                f"Warning: [{task_type}] only collected {counter[0]}/{count} examples "
                f"after {submitted} attempts. The LLM may be struggling with these schemas."
            )
        else:
            print(f"[{task_type}] Done — {counter[0]} examples written to {self.output_path}")
