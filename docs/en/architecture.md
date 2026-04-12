# Architecture & Core Logic

The core goal of `Train in Silence` is to transform abstract training workloads into specific hardware recommendations. The workflow is: Analyze -> Estimate -> Fetch -> Optimize.

## System Architecture

```text
Input (Workload + Constraints)
        �?[Resource Estimator] ----> Calculates required VRAM, CPU, RAM, and total FLOPs
        �?[Market Aggregator] ----> Aggregates and normalizes offers from all Providers
        �?[Optimizer Engine]  ----> Filters invalid options, calculates Time/Cost, generates Pareto Frontier
        �?[Recommendation]    ----> Outputs labeled results (Cheapest, Fastest, Balanced)
```

## Core Algorithms

### 1. Resource Estimation

The estimation logic primarily follows these models (see `tis/planner/estimator.py`):
- **VRAM Estimation**: Weighs model params, precision, batch size, and activation values.
- **FLOPs & Throughput**: Factors in $6 \times \text{Params} \times \text{Tokens}$ and gradient accumulation to predict training duration.

### 2. Pareto Optimization

A "good" hardware configuration usually involves two conflicting metrics: **Lower Cost** and **Faster Time**.

The system doesn't just return a single "best" value; it computes the **Pareto Frontier**: the set of all options where no other option improves one metric without worsening another.

### 3. Availability & Risk Assessment

Based on real-time inventory and historical experience, the system scores each option (Score 0.0-1.0):
- **0.7 - 1.0**: Low Risk (Recommended)
- **0.4 - 0.7**: Medium Risk (May face preemptions or partial stockouts)
- **0.0 - 0.4**: High Risk (Suggests choosing a different option or platform)

## Module Overview

- `tis/planner/models.py`: Core data structure definitions (Pydantic models).
- `tis/planner/workload.py`: Request loading, validation, and parsing logic.
- `tis/planner/market/`: Implementation and abstraction layers for market providers.
- `tis/planner/pareto.py`: Algorithm for frontier calculation.
- `tis/planner/recommender.py`: Sorting recommendations and building responses.
