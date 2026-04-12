<p align="center">
  <h1 align="center">Train in Silence</h1>
  <p align="center">
    Stop comparing GPU prices. Start training.
  </p>
  <p align="center">
    <a href="https://github.com/hlpun/Train-in-Silence/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
    <a href="https://github.com/hlpun/Train-in-Silence/blob/main/README_zh.md">中文</a>
  </p>
</p>

---

You want to fine-tune an LLM. You open Vast.ai, RunPod, AWS -- three tabs, three pricing models, three different ways to describe a GPU. An hour later you're still in a spreadsheet and haven't written a single line of training code.

**Train in Silence** does that homework for you. Describe your workload once, and it returns the cheapest, fastest, and most balanced hardware options across cloud providers -- in seconds.

## Quickstart

### Option A: Ask Claude (recommended)

Install the library and register it as a tool in [Claude Code](https://docs.anthropic.com/en/docs/claude-code):

```bash
pip install train-in-silence
claude mcp add tis --scope user -- tis-mcp
```

Then just ask in natural language:

```
> I want to QLoRA fine-tune Llama-13B on 100M tokens, budget under $20.
  Find me the best GPU options across Vast.ai, RunPod, and AWS.
```

Claude calls TIS behind the scenes and returns a structured recommendation -- no YAML, no config files, no manual comparison.

### Option B: CLI

```bash
pip install train-in-silence
tis recommend examples/request.yaml
```

```bash
$ tis recommend examples/request.yaml

  Found 5 viable configurations
  Lowest cost: $4.32 | Fastest runtime: 2.1 hours

  #1 [cheapest]  RunPod 1x A6000 (48 GB)    $4.32 / 6.8 h
  #2 [fastest]   Vast.ai 2x A100 (80 GB)    $9.10 / 2.1 h
  #3 [balanced]  RunPod 1x A100 (80 GB)     $6.40 / 3.2 h
  ...
```

> **Note**: Output above is illustrative. Actual results depend on live market data.

## Use It Your Way

| Channel | Command | Docs |
|---------|---------|------|
| **CLI** | `tis recommend request.yaml` | [CLI Guide](https://github.com/hlpun/Train-in-Silence/blob/main/docs/en/cli.md) |
| **REST API** | `uvicorn tis.api.server:app` | [API Reference](https://github.com/hlpun/Train-in-Silence/blob/main/docs/en/api.md) |
| **Claude Code** | `claude mcp add tis --scope user -- tis-mcp` | [MCP Guide](https://github.com/hlpun/Train-in-Silence/blob/main/docs/en/mcp.md) |
| **Claude Desktop** | Add `tis-mcp` to `claude_desktop_config.json` | [MCP Guide](https://github.com/hlpun/Train-in-Silence/blob/main/docs/en/mcp.md) |

### Market Providers

Live pricing from three providers -- no manual data entry:

| Provider | Source | Auth Required |
|----------|--------|---------------|
| **Vast.ai** | REST API | `VAST_API_KEY` |
| **RunPod** | GraphQL API | `RUNPOD_API_KEY` |
| **AWS** | Public EC2 Price List | None |

If a provider is unreachable, TIS gracefully falls back to bundled sample data and marks the result accordingly. [-> Provider details](https://github.com/hlpun/Train-in-Silence/blob/main/docs/en/providers.md)

## Architecture at a Glance

```
YAML request -> Estimator -> Market Aggregator -> Optimizer -> Pareto Frontier -> Ranked Output
                  |                |                 |
              VRAM/FLOPs     Vast+RunPod+AWS    Cost vs. Time
```

Each recommendation shows **where the data came from** (`live` or `sample`) and flags any estimated fields -- no silent guesswork. [-> Architecture deep-dive](https://github.com/hlpun/Train-in-Silence/blob/main/docs/en/architecture.md)

## Known Limitations

- Estimation model is fixed with no built-in calibration; future versions will calibrate using real runtimes.
- AWS availability uses an approximation method due to the lack of a real-time instance list API (flagged transparently).
- Upstream Provider API schema changes will require synchronized mapping updates.
