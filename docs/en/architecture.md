# Architecture & Core Logic

The core goal of `Train in Silence` is to transform abstract training workloads into specific hardware recommendations. The workflow is: Analyze -> Estimate -> Fetch -> Optimize.

## System Architecture

```text
Input (Workload + Constraints)
        - [Resource Estimator] ----> Calculates required VRAM, CPU, RAM, and total FLOPs
        - [Market Aggregator] ----> Aggregates offers using a 5-layer hierarchical strategy
        - [Optimizer Engine]  ----> Filters invalid options, calculates Time/Cost, generates Pareto Frontier
        - [Recommendation]    ----> Outputs labeled results with Source of Truth tags
```

## Core Algorithms

### 1. Resource Estimation

The estimation logic primarily follows these models (see `tis/planner/estimator.py`):
- **VRAM Estimation**: Precise calculation factoring in model params, precision, batch size, and KV Cache (based on `hidden_dim`, `num_heads`, and `num_layers`).
- **FLOPs & Throughput**: 
    - **Training**: Standard $6 \times \text{Params} \times \text{Tokens}$ scaling.
    - **Inference (Two-Stage)**: Distinguishes between **Prefill** (Total Params) and **Decoding** (Active Params for MoE). Formula: $2 \times (\text{Params} \times \text{Prefill\_Tokens} + \text{Active\_Params} \times \text{New\_Tokens})$.
- **Distributed Taxes**: Estimates CPU and RAM overhead for multi-GPU configurations (e.g. communication buffers and parallel orchestration).

### 2. Pareto Optimization

A "good" hardware configuration usually involves two conflicting metrics: **Lower Cost** and **Faster Time**.

The system doesn't just return a single "best" value; it computes the **Pareto Frontier**: the set of all options where no other option improves one metric without worsening another.

### 3. Hierarchical Data Strategy

The system utilizes a 5-layer approach to ensure a balance between official accuracy and global coverage:
1. **Official APIs**: Real-time prices for Vast.ai, Runpod, and AWS (Public Pricing).
2. **GPUHunt**: Dynamic market aggregation for Lambda, Fluidstack, etc. 
3. **GPUFinder**: Universal coverage for long-tail providers.
4. **Intelligent Consolidation**: 3-layer metadata merging (Official data supplemented by GPUHunt and GPUFinder for missing specs like Memory BW or CPU cores).
5. **Sample Fallback**: High-fidelity offline data.

Every result is tagged with a `source_detail` (e.g. `live:official`, `live:gpuhunt`) to ensure full transparency regarding data freshness.

## Module Overview

- `tis/planner/models.py`: Core data structure definitions (Pydantic models).
- `tis/planner/workload.py`: Request loading, validation, and parsing logic.
- `tis/planner/market/`: Implementation and abstraction layers for market providers.
- `tis/planner/pareto.py`: Algorithm for frontier calculation.
- `tis/planner/recommender.py`: Sorting recommendations and building responses.
