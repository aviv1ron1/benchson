"""Task utilities for running the Benchson JSON benchmark under
lm-evaluation-harness (https://github.com/EleutherAI/lm-evaluation-harness).

Self-contained: depends only on `jsonschema` and `deepdiff`. The prompt builders
and metric functions intentionally MIRROR the repo's source of truth so that lm-eval
scores match `src/main.py`:

  - prompts  ↔ src/evaluations/*/{create_by_schema,json_error_evaluation,modify_json_evaluation}.py :: format_for_llm
  - metrics  ↔ src/evaluations/metrics.py

If you change those, update this file too.

Each task's dataset row is one Benchson instance JSON (loaded straight from
data/benchmark_<task>/test/*.json), so `doc` already contains `schema`, the task
inputs, and the ground truth.
"""

import json
import re

import jsonschema


# --------------------------------------------------------------------- metrics
# (mirror of src/evaluations/metrics.py)

def parse_json(text):
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"```json\s*|\s*```", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def schema_compliance(obj, schema):
    try:
        jsonschema.validate(instance=obj, schema=schema)
        return 1
    except jsonschema.ValidationError:
        return 0
    except Exception:
        # malformed schema / unresolvable $ref → can't validate → not compliant
        return 0


def _iter_leaves(value, path=()):
    if isinstance(value, dict) and value:
        for k, v in value.items():
            yield from _iter_leaves(v, path + (k,))
    elif isinstance(value, list) and value:
        for i, v in enumerate(value):
            yield from _iter_leaves(v, path + (i,))
    else:
        yield path, value


def _navigate(obj, path):
    cur = obj
    for step in path:
        if isinstance(step, int):
            if isinstance(cur, list) and 0 <= step < len(cur):
                cur = cur[step]
            else:
                return False, None
        elif isinstance(cur, dict) and step in cur:
            cur = cur[step]
        else:
            return False, None
    return True, cur


def _values_equal(a, b):
    from deepdiff import DeepDiff
    return not DeepDiff(a, b, ignore_order=True)


def semantic_fidelity(reference, output):
    leaves = list(_iter_leaves(reference))
    if not leaves:
        return 1.0
    matches = 0
    for path, value in leaves:
        found, out_value = _navigate(output, path)
        if found and _values_equal(value, out_value):
            matches += 1
    return matches / len(leaves)


# --------------------------------------------------------------------- prompts
# (mirror of each evaluation's format_for_llm; system + user folded into one
#  string so the task works with or without --apply_chat_template)

def _obj(v):
    """Normalize a JSON-valued field: parse it if it arrived as a string.

    Local repo instances store `schema`/`reference_json`/... as objects; the HF
    dataset stores them as JSON strings (for a uniform Arrow schema). Accept both.
    """
    return json.loads(v) if isinstance(v, str) else v


def _join(system, user):
    return f"{system}\n\n{user}"


def doc_to_text_create(doc):
    schema = _obj(doc["schema"])
    grounding = doc.get("description") or doc.get("source_doc")
    system = ("You are a helpful assistant that turns a described object into JSON data "
              "matching a given schema. Output only the json with no other text or explanations.")
    if grounding:
        instructions = doc.get("instructions") or (
            "Create a JSON object that conforms to the schema, using the information in "
            "the following description.")
        user = (f"{instructions}\n\nDescription:\n{grounding}\n\n"
                f"Schema:\n{json.dumps(schema, indent=2)}")
    else:
        user = ("Generate a JSON object that conforms to the following schema: "
                f"{json.dumps(schema, indent=2)}")
        system = ("You are a helpful assistant that generates JSON data based on a given "
                  "schema. Output only the json with no other text or explanations.")
    return _join(system, user)


def doc_to_text_fix(doc):
    system = ("You are a helpful assistant tasked with fixing JSON objects to conform precisely "
              "to the provided JSON schema. Return ONLY the corrected JSON object, with no "
              "additional text or explanation.")
    user = ("Please correct the following JSON so that it fully matches the given schema:\n\n"
            f"JSON:\n```json\n{json.dumps(_obj(doc['erroneous_json']), indent=2)}\n```\n\n"
            f"Schema:\n```json\n{json.dumps(_obj(doc['schema']), indent=2)}\n```")
    if doc.get("description"):
        user += f"\n\nThe corrected JSON should describe the following:\n{doc['description']}"
    return _join(system, user)


def doc_to_text_modify(doc):
    system = ("You are a helpful assistant that modifies JSON objects based on given "
              "instructions. Output only the modified JSON with no other text or explanations.")
    user = (f"Given the following JSON:\n```json\n{json.dumps(_obj(doc['data']), indent=2)}\n```\n"
            f"Modify it as instructed: {doc['instructions']}")
    if doc.get("schema") is not None:
        user += f"\n\nThe result must still conform to this schema:\n{json.dumps(_obj(doc['schema']), indent=2)}"
    return _join(system, user)


# --------------------------------------------------------- targets (logging only)

def doc_to_target_create(doc):
    return json.dumps(doc.get("reference_json"))


def doc_to_target_fix(doc):
    return json.dumps(doc.get("valid_json", doc.get("reference_json")))


def doc_to_target_modify(doc):
    return json.dumps(doc.get("ground_truth"))


# ----------------------------------------------------------------- scoring
# process_results(doc, results) -> {metric_name: value}; results[0] is the generation.

def _score(generation, schema, reference):
    parsed = parse_json(generation)
    valid = parsed is not None
    return {
        "json_validity": 1 if valid else 0,
        "schema_compliance": schema_compliance(parsed, schema) if valid else 0,
        "semantic_fidelity": round(semantic_fidelity(reference, parsed), 4) if valid else 0.0,
    }


# ------------------------------------------------------- per-tier filtering
# Subset-filtered subtasks (benchson_<family>_<tier>) report scores per difficulty
# tier / source instead of one aggregate. Each tier gets a `keep_<tier>` process_docs
# function (registered in globals) that the generated YAMLs reference via !function.

def doc_tier(doc):
    """The tier label of a row: its `subset` (jsb) or `source` (e.g. 'schemas')."""
    return doc.get("subset") or doc.get("source")


def tier_fn_name(tier):
    return "keep_" + re.sub(r"[^a-z0-9]+", "_", str(tier).lower()).strip("_")


def _make_keep(tier):
    def keep(dataset):
        return dataset.filter(lambda doc: doc_tier(doc) == tier)
    keep.__name__ = tier_fn_name(tier)
    return keep


# Tiers present across the benchmark; keep in sync with the imported subsets.
TIERS = ["Github_easy", "Github_medium", "Github_hard", "Github_ultra",
         "Kubernetes", "Snowplow", "Glaiveai2K", "schemas"]
for _t in TIERS:
    globals()[tier_fn_name(_t)] = _make_keep(_t)


def process_results_create(doc, results):
    return _score(results[0], _obj(doc["schema"]), _obj(doc.get("reference_json")))


def process_results_fix(doc, results):
    return _score(results[0], _obj(doc["schema"]), _obj(doc.get("valid_json", doc.get("reference_json"))))


def process_results_modify(doc, results):
    return _score(results[0], _obj(doc.get("schema")), _obj(doc.get("ground_truth")))
