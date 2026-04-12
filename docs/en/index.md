# Train in Silence

`Train in Silence` is a hardware planner designed for LLM fine-tuning scenarios. It takes your workload (model/training params), constraints (platforms, budget), and preferences, and uses real-time market data alongside heuristic resource models to recommend Pareto-optimal hardware configurations.

## Core Value

- **Precise Modeling**: Estimate VRAM, compute capacity, and bandwidth requirements based on model architecture and training parameters.
- **Real-Time Market**: Aggregates live pricing from major compute markets like Vast.ai, RunPod, and AWS.
- **Multi-Objective Optimization**: Finds the balance between cost and time, generating Pareto Frontier candidates.
- **Data Transparency**: Explicitly flags estimated or inferred data (e.g., catalog-only inventory) to ensure trustworthy results.

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
- [**Market Providers**](./providers.md): Understand platform data sources and configuration.
- [**Architecture & Logics**](./architecture.md): Deep dive into resource estimation and the optimization engine.
- [**MCP Plugin**](./mcp.md): Use it as a tool plugin for LLM assistants.
- [**Integration Guide**](./integrations.md): Set up with Claude Code or Claude Desktop.
