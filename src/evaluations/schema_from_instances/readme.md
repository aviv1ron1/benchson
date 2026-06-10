# SchemaFromInstancesEvaluation

This evaluation tests the LLM's ability to generate a JSON Schema that accurately describes a set of given JSON instances.

The metric is 1 if the generated schema validates all provided JSON instances, and 0 otherwise.

The schema must conform to the JSON Schema Draft-07 specification and include a $schema declaration.

Any output that is not a valid JSON Schema or that fails to validate the input instances will result in evaluation failure.
