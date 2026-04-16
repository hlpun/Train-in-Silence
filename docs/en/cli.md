# CLI Guide

`Train in Silence` provides a command-line interface called `tis`, covering everything from request validation to recommendation generation.

## Base Commands

All commands require a request configuration file in YAML or JSON format. You can refer to `examples/request.yaml`.

### 1. Generate Hardware Recommendations (`recommend`)

This is the most commonly used command. It estimates resource requirements, fetches market data, and outputs the best options.

```bash
tis recommend examples/request.yaml
```

**Common Options:**
- `--output json`: Output results in a structured JSON format.
- `--platforms vast.ai`: Filter for specific platforms only.

### 2. Detailed Process Analysis (`explain`)

If you want to know why these configurations were recommended, use the `explain` command. It displays:
- Specific resource estimate values (VRAM, FLOPs, CPU/RAM needs).
- Normalized market data.
- Time and price calculation details for each option.

```bash
tis recommend examples/request.yaml --explain
# Or use the direct command
tis explain examples/request.yaml
```

### 3. Validate Configuration (`validate`)

Before submitting complex fine-tuning tasks, validate that the workload and constraints definitions are valid.

```bash
tis validate examples/request.yaml
```

### 4. Market Probing (`market`)

These subcommands are used for debugging compute provider status.

- **Probe Status**: `tis market probe examples/request.yaml` (shows whether each provider succeeded, reasons, and offer counts).
- **Dump Raw Offers**: `tis market dump-offers examples/request.yaml` (outputs standardized raw data from third-party markets).

## Environment Variables

CLI behavior is influenced by the following environment variables:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `TIS_ALLOW_SAMPLE_FALLBACK` | Whether to allow falling back to sample data when online markets fail. | `true` |
| `VAST_API_KEY` | Your Vast.ai API Key (Optional). | - |
| `RUNPOD_API_KEY` | Your RunPod API Key (Optional). | - |

## Caching Mechanism

To reduce API calls and improve speed, `tis` caches market data in a local directory called `.tis_cache`.
- **Default TTL**: 300 seconds.
- You can manually delete `.tis_cache` at any time to force a data refresh.
