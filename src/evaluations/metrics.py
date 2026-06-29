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


def changed_paths(before, after):
    """Leaf paths that differ between two objects (added, removed, or changed).

    Used to score *what the task actually changed* (a fix/modify edit) rather than
    the whole object — on a large schema, copying the many unchanged fields would
    otherwise dilute the signal from the few that mattered.
    """
    bl = {p: v for p, v in _iter_leaves(before)}
    al = {p: v for p, v in _iter_leaves(after)}
    changed = set()
    for p in set(bl) | set(al):
        if p not in bl or p not in al or not _values_equal(bl[p], al[p]):
            changed.add(p)
    return changed


def region_fidelity(output, reference, paths):
    """Fraction of the given leaf paths that `output` gets right vs `reference`.

    A path present in `reference` must be present and equal in `output`; a path
    absent from `reference` (a deletion) must also be absent in `output`. Returns
    1.0 when there are no paths to check.
    """
    paths = list(paths)
    if not paths:
        return 1.0
    hits = 0
    for p in paths:
        ref_present, ref_val = _navigate(reference, p)
        out_present, out_val = _navigate(output, p)
        if ref_present:
            ok = out_present and _values_equal(ref_val, out_val)
        else:
            ok = not out_present
        hits += 1 if ok else 0
    return hits / len(paths)


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
    """JSON-aware deep value equality.

    Numbers compare by value, so `10 == 10.0` (JSON has no int/float distinction
    and a model shouldn't be penalized for emitting one form vs the other). But
    booleans stay distinct from numbers (`true != 1`) and strings stay distinct
    from numbers (`"10" != 10`) — those are real type differences in JSON.
    """
    a_bool, b_bool = isinstance(a, bool), isinstance(b, bool)
    if a_bool or b_bool:
        return a_bool and b_bool and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_values_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_values_equal(x, y) for x, y in zip(a, b))
    return a == b
