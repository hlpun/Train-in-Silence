# Train in Silence

`Train in Silence` is a hardware planner designed specifically for **LLM fine-tuning** scenarios. Briefly describe your workload (model/training params), and TIS will calculate the required VRAM/FLOPs to find the Pareto-optimal hardware across **10+ global cloud providers**.

## Core Value

- **Task-Aware & High Fidelity**: Precision resource estimation (VRAM, compute, bandwidth) based on transformer structural parameters.
- **Global Market Coverage**: Real-time aggregation from Vast.ai, RunPod, AWS (Public Pricing), GCP, Azure, Lambda Labs, and more.
- **Zero-Config (Keyless)**: No setup needed for AWS or universal providers. Instant market overview out of the box.
- **Multi-Objective Optimization**: Trade-off visualization between **Cost** and **Time**, optimized for LLM training/inference.
- **High Fidelity Context**: Designed to work with LLM assistants (Claude Code) by requiring precise model parameters.

## Quick Start

### 1. Installation

```bash
# Install the library (virtual environment recommended)
pip install train-in-silence
```

### 2. Run Your First Recommendation

```bash
tis recommend examples/request.yaml
```

## Documentation Guide

- [**CLI Guide**](./cli.md): Learn how to use the `tis` command-line tool.
- [**API Reference**](./api.md): Integrate via the FastAPI-based backend.
- [**Market Providers**](./providers.md): Understand the 5-layer hierarchy and how to configure platforms.
- [**Architecture & Logics**](./architecture.md): Deep dive into resource estimation and the optimization engine.
- [**MCP Plugin**](./mcp.md): Use TIS as a tool plugin for LLM assistants (Claude Code/Desktop).
- [**Integration Guide**](./integrations.md): Detailed setup steps for third-party tools.
