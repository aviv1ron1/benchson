# CreateBySchema

This evaluation loads a JSON schema from the dataset and asks the LLM to produce a JSON object that conforms to it. It supports two test-case formats.

## Schema-only (legacy)

The test file is a raw JSON Schema. The model is asked to invent a conforming object. There is no source content and no ground truth — this measures schema comprehension only.

The expected output should be JSON, optionally wrapped in backticks (```` ```{JSON} ``` ```` or ```` ```json{JSON} ``` ````). Any other surrounding text will fail validation.

## Source-doc grounded (enriched)

The test file is an object with a `schema` key, plus optional `source_doc`, `reference_json`, and `instructions`:

```json
{
  "source_doc": "Alice Johnson joined on January 15, 2024. She is 30, username alicej.",
  "schema": { "type": "object", "properties": { "name": {"...": "..."} } },
  "reference_json": { "name": "Alice Johnson", "age": 30, "username": "alicej" },
  "instructions": "Extract the user profile from the text and return it as a JSON object matching the schema."
}
```

When a `source_doc` is present, the model is asked to **extract** the information from the text rather than invent it. This tests source comprehension and schema compliance simultaneously, the way real extraction workloads do.

## Metrics

Each record is scored on two independent dimensions:

- **schema_compliance** (the primary `Score` column): `1` if the output is valid JSON conforming to the schema, `0` otherwise.
- **semantic_fidelity** (reported only when `reference_json` is present): the fraction of reference leaf-field values that are recovered in the output, computed with `deepdiff`. Fields present in the output but absent from the reference are treated as valid additions and not penalized.

A model can pass one and fail the other: valid JSON with wrong values (schema_compliance 1, low fidelity), or malformed structure with the right content (schema_compliance 0, partial fidelity). Passing both is the target.

Secondary metrics appear as extra columns in the results CSV alongside `Score`.
