# ErrorJson

This evaluation (task **2b — fix-invalid**) gives the model a schema-violating JSON
object and asks it to repair the object so it conforms to the schema. When the
instance includes a `description` of the intended object, it is added to the prompt
so the model can recover values that the injected error removed.

## Instance format

```json
{
  "erroneous_json": { "...": "..." },
  "schema": { "...": "..." },
  "valid_json": { "...": "..." },
  "description": "optional natural-language description of the intended object",
  "name": "...", "source": "...", "subset": "..."
}
```

`reference_json` is accepted as an alias for `valid_json`. `source`/`subset` are
echoed into the result name for slicing.

## Metrics

Scored on three independent dimensions (shared with `CreateBySchema` via
`src/evaluations/metrics.py`):

- **json_validity** (metric): 1 if the corrected output parses as JSON.
- **schema_compliance** (the primary `Score`): 1 if the corrected output validates against the schema.
- **semantic_fidelity** (metric): fraction of ground-truth field values recovered.

The expected output is JSON, optionally wrapped in backticks; surrounding prose will
fail JSON parsing.
