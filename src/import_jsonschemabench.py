"""Imports schemas from the JSONSchemaBench HuggingFace dataset into a local
Benchson dataset directory.

JSONSchemaBench (epfl-dlab/JSONSchemaBench, MIT license) provides difficulty-tiered
and domain-diverse real-world schemas that Benchson's JSONSchemaStore corpus lacks.
We import only the *extra* subsets (GitHub tiers, Kubernetes, Snowplow, function
calls); the JsonSchemaStore subset is skipped because it overlaps Benchson's
existing data/schemas.

Usage:
    uv run python src/import_jsonschemabench.py --config configs/import_jsonschemabench.json
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import json
import random
import re

from jsonschema.validators import validator_for

from src.provider import Provider

_DATASET = "epfl-dlab/JSONSchemaBench"

# Sensible default: every subset except the JsonSchemaStore overlap and the
# aggregate "default" config. Values are how many schemas to sample per subset.
_DEFAULT_SUBSETS = {
    "Github_easy": 12,
    "Github_medium": 10,
    "Github_hard": 6,
    "Kubernetes": 6,
    "Snowplow": 3,
    "Glaiveai2K": 6,
}


def _safe_filename(subset, unique_id, idx):
    raw = f"{subset}__{unique_id or idx}"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", raw) + ".json"


def _is_well_formed(schema):
    """True if the schema itself is a valid JSON Schema (any supported draft)."""
    try:
        validator_cls = validator_for(schema)
        validator_cls.check_schema(schema)
        return True
    except Exception:
        return False


def import_subset(load_dataset, subset, count, split, size_limit, rng, out_dir):
    """Imports up to `count` well-formed, size-bounded schemas from one subset."""
    try:
        ds = load_dataset(_DATASET, subset, split=split)
    except Exception as e:
        print(f"[{subset}] Failed to load (skipping): {e}")
        return 0

    indices = list(range(len(ds)))
    rng.shuffle(indices)

    written = 0
    for idx in indices:
        if written >= count:
            break
        row = ds[idx]
        raw = row.get("json_schema")
        if not raw:
            continue
        if len(raw.encode("utf-8")) > size_limit:
            continue
        try:
            schema = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(schema, dict) or not _is_well_formed(schema):
            continue

        filename = _safe_filename(subset, row.get("unique_id"), idx)
        record = {
            "name": row.get("unique_id") or filename,
            "source": "jsonschemabench",
            "subset": subset,
            "schema": schema,
        }
        with open(os.path.join(out_dir, filename), "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        written += 1

    print(f"[{subset}] imported {written}/{count}")
    return written


def main():
    parser = argparse.ArgumentParser(description="Import JSONSchemaBench schemas.")
    parser.add_argument("--config", type=str, required=True, help="Path to import config JSON.")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    output_dataset = config.get("output_dataset", "jsb_schemas")
    split = config.get("split", "test")
    size_limit = config.get("max_schema_kb", 10) * 1024
    subsets = config.get("subsets", _DEFAULT_SUBSETS)
    rng = random.Random(config.get("seed", 0))

    Provider.install_dependency("datasets")
    from datasets import load_dataset

    out_dir = os.path.join(os.getcwd(), "data", output_dataset, "test")
    os.makedirs(out_dir, exist_ok=True)
    # Placeholder so Dataset() doesn't warn about a missing train split.
    os.makedirs(os.path.join(os.getcwd(), "data", output_dataset, "train"), exist_ok=True)

    total = 0
    for subset, count in subsets.items():
        total += import_subset(load_dataset, subset, count, split, size_limit, rng, out_dir)

    print(f"Done — {total} schemas written to {out_dir}")


if __name__ == "__main__":
    main()
