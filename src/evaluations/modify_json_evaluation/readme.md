# ModifyJson

This evaluation (task **2c — modify-by-instruction**) gives the model a JSON object,
its schema, and a free-text change instruction (e.g. "remove the first two items from
the cart"), and asks it to return the correctly modified object.

## Instance format

```json
{
  "data": { "...": "..." },
  "instructions": "free-text change request",
  "ground_truth": { "...": "..." },
  "schema": { "...": "..." },
  "name": "...", "source": "...", "subset": "..."
}
```

`schema` is optional (legacy modification instances omit it); `source`/`subset` are
echoed into the result name for slicing.

## Metrics

Scored on three independent dimensions (shared with the other benchmark evals via
`src/evaluations/metrics.py`):

- **json_validity** (metric): 1 if the output parses as JSON.
- **schema_compliance** (the primary `Score`): 1 if the output validates against the schema. With no schema, falls back to exact match on the ground truth.
- **semantic_fidelity** (metric): fraction of ground-truth field values recovered — i.e. whether the change was applied correctly.

The expected output is JSON, optionally wrapped in backticks; surrounding prose will
fail JSON parsing.
