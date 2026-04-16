<p align="center">
  <h1 align="center">Train in Silence</h1>
    The first Task-Aware MCP server for LLM fine-tuning.
    Stop comparing GPU prices. Start training.
  </p>
  <p align="center">
    <a href="https://github.com/hlpun/Train-in-Silence/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
    <a href="https://github.com/hlpun/Train-in-Silence/blob/main/README_zh.md">中文</a>
  </p>
</p>

---

You want to fine-tune an LLM. You open Vast.ai, RunPod, AWS, etc. -- a dozen tabs, a dozen pricing models, a dozen different ways to describe a GPU. Which option can run your code, and do so more cheaply and quickly? An hour later you're still in a spreadsheet and haven't written a single line of training code.

**Train in Silence** is the first **Task-Aware MCP server** for LLM fine-tuning. It doesn't just list prices; it understands your workload. Describe your training job once, and it calculates the required VRAM/FLOPs to return the cheapest, fastest, and most balanced hardware options across **a dozen cloud providers** -- in seconds.

## Quickstart

### Option A: Ask Claude Code (recommended)

Install the library and register it as a tool in [Claude Code](https://docs.anthropic.com/en/docs/claude-code):

```bash
pip install train-in-silence
claude mcp add tis --scope user -- tis-mcp
```

Then just ask in natural language:

```
> I want to run the fine-tune code in my current directory, and finish it within 20 hours.
  Find me the best GPU options across Vast.ai, RunPod, and Lambda.
```

Claude Code calls TIS behind the scenes and returns a structured recommendation -- no YAML, no config files, no manual comparison.

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
| **Claude Code** | `claude mcp add tis --scope user --tis-mcp` | [MCP Guide](https://github.com/hlpun/Train-in-Silence/blob/main/docs/en/mcp.md) |
| **Claude Desktop** | Add `tis-mcp` to `claude_desktop_config.json` | [MCP Guide](https://github.com/hlpun/Train-in-Silence/blob/main/docs/en/mcp.md) |

### Market Providers

TIS aggregates live pricing across a dozen GPU clouds. API keys are **optional**: if not provided, TIS automatically falls back sequentially to universal live aggregators (GPUHunt/GPUFinder) or bundled sample data.

| Provider Class | Included Platforms | Auth Required |
|----------------|--------------------|---------------|
| **Dedicated** | Vast.ai, RunPod, AWS | **Optional** (Highly Recommended) |
| **Aggregated** | Vast.ai, RunPod, AWS, CoreWeave, Lambda Labs, Tensordock, Vultr, GCP, Azure, OCI, Nebius, CloudRift, Cudo Compute, Verda | **None** (Auto-fallback) |

Every recommendation clearly identifies its **Source of Truth** (e.g., `live:official`, `live:gpuhunt`, `live:gpufinder`, or `sample`) so you always know how fresh the data is. [-> Provider details](https://github.com/hlpun/Train-in-Silence/blob/main/docs/en/providers.md)

## Architecture at a Glance

```
YAML request -> Estimator -> Market Aggregator -> Optimizer -> Pareto Frontier -> Ranked Output
                  |                |                 |
              VRAM/FLOPs     10+ GPU Clouds    Cost vs. Time
```

Each recommendation shows **where the data came from** (`live` or `sample`) and flags any estimated fields -- no silent guesswork. [-> Architecture deep-dive](https://github.com/hlpun/Train-in-Silence/blob/main/docs/en/architecture.md)

## Known Limitations

- Estimation model is fixed with no built-in calibration; future versions will calibrate using real runtimes.
- Upstream Provider API schema changes will require synchronized mapping updates.

## 🚧 Project Status & Contribution

This project is currently in the **experimental development stage (Experimental)**.

- **Issues & Suggestions**: If you encounter any bugs, inaccurate estimations, or have suggestions for improvement, please feel free to submit a [GitHub Issue](https://github.com/hlpun/Train-in-Silence/issues).
- **Contribute**: If you'd like to improve the code or supplement hardware metadata, Pull Requests are highly welcome! We look forward to refining this LLM hardware planner with the community.
