# API Reference

`Train in Silence` includes a built-in HTTP server based on FastAPI for use in web environments or distributed systems.

## Start the Service

```bash
uvicorn tis.api.server:app --reload
```

By default, it runs at `http://127.0.0.1:8000`.

## Core Endpoints

### 1. Get Hardware Recommendations (`POST /recommend`)

Receives hardware requirements and return ranked configurations. Supports both single-workload and multi-stage pipeline requests.

**Request Schema (High Fidelity):**
To ensure accurate estimation, `ModelSpec` requires the following architecture parameters:
- `hidden_dim`: Hidden dimension size.
- `num_layers`: Number of transformer layers.
- `num_heads`: Number of query attention heads.
- `num_kv_heads`: Number of KV attention heads (critical for GQA/MQA models).

**Advanced Task Constraints (`Constraints`):**
We use a physical overhead model to ensure realistic time and cost estimates. You can tune these parameters for your environment:
- `network_speed_gbps`: Estimated download speed (default: 1.0).
- `storage_speed_gbps`: Estimated disk-to-VRAM bandwidth (default: 3.0).
- `skip_download`: Whether to skip model download time (default: true).

**Request Format:**

```json
{
  "workload": {
    "model": {
      "name": "llama-3-8b", "params": 8030000000, 
      "hidden_dim": 4096, "num_layers": 32, 
      "num_heads": 32, "num_kv_heads": 8
    },
    ...
  }
}
```

**Pipeline Requests:**
Instead of a single `workload`, you can provide a `pipeline` (a list of workloads) to optimize for multi-stage fine-tuning or inference workflows.

**Response Example:**
```json
{
  "version": "0.1.5",
  "summary": "Found 5 viable configurations...",
  "provider_statuses": [...],
  "recommendations": [
    {
      "label": "cheapest",
      "config": { ... },
      "metrics": {
        "time_hours": 10.5,
        "cost_usd": 12.0,
        "gpu_utilization": 0.85
      },
      "availability": {
        "score": 0.8,
        "risk": "low"
      },
      "source_detail": "live:official+supplemented",
      "notes": ["Availability is estimated based on historical catalog data."],
      "explanation": "..."
    }
  ]
}
```

### 2. Version Information (`GET /version`)

**Returns:** `{"version": "0.1.0"}`

### 3. Health Check (`GET /health`)

Lists all currently configured compute providers and their online status.

## Error Handling

The API uses standard HTTP status codes and returns structured error messages:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [...]
  },
  "version": "0.1.0"
}
```

Common codes:
- `validation_error`: Invalid request parameters.
- `internal_error`: Market fetching or algorithm processing failure.
