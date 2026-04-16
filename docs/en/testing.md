# Developer Guide: Automated Testing & VCR

To ensure stability when interacting with external cloud provider APIs (Vast.ai, Runpod, etc.), `Train in Silence` uses **VCR.py** via the `pytest-recording` plugin. This allows tests to record real network interactions and replay them without needing API keys.

## How it Works

1. **Replay Mode (Default)**: When you run `pytest`, the system looks for "cassettes" (recordings) in `tests/cassettes/`. It uses these saved responses instead of making real network calls.
2. **Record Mode**: If you are adding a new provider or updating logic, you can record new cassettes by providing real API keys and running `pytest --record-mode=once`.

## Running Tests

### Standard Run (No API keys needed)
```bash
pytest tests
```

### Recording New Cassettes (Requires API keys)
```bash
# Set your environment variables
$env:VAST_API_KEY="your_key"
$env:RUNPOD_API_KEY="your_key"

# Run pytest in rewrite mode for specific tests
pytest tests/test_networking.py --record-mode=rewrite
```

## Security & Privacy (Masking)

We use a custom configuration in `tests/conftest.py` to ensure sensitive data is **never** saved to cassettes:
- `Authorization` headers are replaced with `MASKED`.
- `api_key` query parameters are replaced with `MASKED`.
- Any other sensitive fields registered in the `vcr_config` will be automatically redacted.

> [!IMPORTANT]
> Always inspect the generated `.yaml` files in `tests/cassettes/` before committing to ensure no private information has leaked.

## Best Practices

- **Atomic Cassettes**: Each test should ideally have its own cassette to keep files manageable.
- **CI/CD Integration**: Our CI pipeline runs tests in replay mode, ensuring 100% pass rates without relying on external service uptime.
- **Cache Redirection**: Tests that generate local file caches should use the temporal `tests/.cache/` directory, which is ignored by Git.
