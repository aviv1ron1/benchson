# ModifyJsonEvaluation

This evaluation tests the LLM's ability to modify a JSON object according to specified instructions.

The metric is 1 if the modified JSON matches the expected output, and 0 otherwise.

The expected output should be valid JSON or JSON wrapped with backticks ({JSON object} or json{JSON object}).

Any other text will fail the evaluation.
