# API Reference

`Train in Silence` includes a built-in HTTP server based on FastAPI for use in web environments or distributed systems.

## Start the Service

```bash
uvicorn tis.api.server:app --reload
```

By default, it runs at `http://127.0.0.1:8000`.

## Core Endpoints

### 1. Get Hardware Recommendations (`POST /recommend`)

Receives a full Planning Request structure and returns filtered and ranked hardware configurations.

**Request Format:**
See [Workload Definition](./index.md) or the JSON version of `examples/request.yaml`.

**Response Example:**
```json
{
  "version": "0.1.0",
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
