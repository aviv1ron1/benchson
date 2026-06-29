"""Builds the description-grounded JSON benchmark (tasks 2a + 2b).

Uses a strong "builder" LLM to author ground-truth reference objects, natural
language descriptions, and injected-error variants from a schema corpus.

Usage:
    uv run python src/build_benchmark.py --config configs/build_benchmark.json
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import json

from llm.llm_provider import LLMProvider
from data_generation.benchmark_builder import BenchmarkBuilder


def main():
    parser = argparse.ArgumentParser(description="Build the JSON extraction/fix benchmark.")
    parser.add_argument("--config", type=str, required=True, help="Path to benchmark build config JSON.")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    llm_provider = LLMProvider.from_config(config["llm_provider"])
    validator_provider = None
    if "validator_provider" in config:
        validator_provider = LLMProvider.from_config(config["validator_provider"])

    builder = BenchmarkBuilder(config)
    builder.build(llm_provider, validator_provider)


if __name__ == "__main__":
    main()
