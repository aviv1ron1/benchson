import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import json
from llm.llm_provider import LLMProvider
from data_generation.generator import DataGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate LoRA training data.")
    parser.add_argument("--config", type=str, required=True, help="Path to data generation config JSON.")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    llm_provider = LLMProvider.from_config(config["llm_provider"])
    generator = DataGenerator(config)
    generator.generate(llm_provider)


if __name__ == "__main__":
    main()
