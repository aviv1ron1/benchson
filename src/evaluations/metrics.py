"""Shared scoring helpers for JSON-generation evaluations.

Three independent dimensions are reported across the benchmark:

- json_validity   — is the model output parseable JSON at all?
- schema_compliance — does the parsed output validate against the schema?
- semantic_fidelity — what fraction of the ground-truth field values are recovered?
"""

import json
import re

import jsonschema


def parse_json(text):
    """Parses model output into a Python object, tolerating ``` / ```json fences.

    Returns (obj, None) on success or (None, error_str) on failure.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"```json\s*|\s*```", "", cleaned).strip()
    try:
        return json.loads(cleaned), None
    except json.JSONDecodeError as e:
        return None, str(e)


def schema_compliance(obj, schema):
    """Validates obj against schema. Returns (1, 'valid') or (0, error_message)."""
    try:
        jsonschema.validate(instance=obj, schema=schema)
        return 1, "valid"
    except jsonschema.ValidationError as e:
        return 0, e.message
    except Exception as e:
        # Malformed schema, or a $ref to an unreachable URL, etc. Can't validate →
        # treat as non-compliant rather than letting it crash the caller.
        return 0, f"schema/validation error: {e}"


def semantic_fidelity(reference, output):
    """Fraction of reference leaf-field values recovered (by value) in output.

    Fields present in the output but absent from the reference are ignored — they
    are valid additions, not errors. Returns a float in [0, 1].
    """
    leaves = list(_iter_leaves(reference))
    if not leaves:
        return 1.0

    matches = 0
    for path, value in leaves:
        found, out_value = _navigate(output, path)
        if found and _values_equal(value, out_value):
            matches += 1

    return matches / len(leaves)


def _iter_leaves(value, path=()):
    """Yields (path, value) for every leaf in a nested structure.

    Empty dicts/lists and scalars are themselves leaves.
    """
    if isinstance(value, dict) and value:
        for key, sub in value.items():
            yield from _iter_leaves(sub, path + (key,))
    elif isinstance(value, list) and value:
        for idx, sub in enumerate(value):
            yield from _iter_leaves(sub, path + (idx,))
    else:
        yield path, value


def _navigate(obj, path):
    """Walks `path` into `obj`. Returns (found, value)."""
    current = obj
    for step in path:
        if isinstance(step, int):
            if isinstance(current, list) and 0 <= step < len(current):
                current = current[step]
            else:
                return False, None
        else:
            if isinstance(current, dict) and step in current:
                current = current[step]
            else:
                return False, None
    return True, current


def _values_equal(a, b):
    """Deep value equality via deepdiff (empty diff == equal)."""
    from deepdiff import DeepDiff

    return not DeepDiff(a, b, ignore_order=True)
