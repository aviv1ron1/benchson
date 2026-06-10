
### ** WatsonX Provider (IBM)**
This provider connects to IBM’s WatsonX LLM service.

**Configuration Example:**
```json
"llm_provider": {
    "module": "src.llm.watsonx.watsonx_provider",
    "class": "IBMWatsonXProvider",
    "params": {
        "api_key": "your-ibm-api-key",
        "project_id": "your-watsonx-project-id",
        "model": "ibm/granite-13b",
        "model_params": {},
        "api_endpoint": "https://us-south.ml.cloud.ibm.com/"
    }
}
```

**Required Parameters:**
- `api_key`: IBM Cloud API key.
- `project_id`: WatsonX project ID.
- `model_params`: Dictionary of model parameters (e.g. `{"max_new_tokens": 512}`). Pass `{}` for defaults.

**Optional Parameters:**
- `model`: Model ID (default: `ibm-mistral-7b`).
- `api_endpoint`: WatsonX API endpoint (default: `https://us-south.ml.cloud.ibm.com/`).

---