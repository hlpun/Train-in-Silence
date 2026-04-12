# 架构与逻辑

`Train in Silence` 的核心设计思路是解耦工作负载估算、市场聚合与方案优化。

## 工作流程

```mermaid
graph TD
    A[用户请求 (YAML/JSON)] --> B[Resource Estimator]
    B --> C{资源需求}
    C --> D[Market Aggregator]
    D --> E[Market Providers (Vast/RunPod/AWS)]
    E --> F[Optimizer Engine]
    F --> G[Pareto Frontier Filter]
    G --> H[推荐方案 (Cheapest, Fastest, Balanced)]
```

## 核心算法

### 1. 资源估算 (Resource Estimation)

估算逻辑遵循以下模型（参见 `tis/planner/estimator.py`）：
- **显存估算**：综合考虑模型参数、计算精度（Precision）、批大小（Batch Size）以及激活值（Activations）。
- **FLOPs 与吞吐量**：基于 $6 \times \text{Params} \times \text{Tokens}$ 公式，并结合梯度累积（Grad Accumulation）来预测训练总时长。

### 2. 帕累托优化 (Pareto Optimization)

“好的”硬件配置通常涉及两个相互冲突的指标：**更低的成本**和**更快的时间**。

系统不仅仅返回一个“最佳”值，它会计算 **帕累托前沿（Pareto Frontier）**：即所有满足以下条件的方案集——在不恶化一个指标的情况下，无法改进另一个指标。

### 3. 可用性与风险评估

基于实时库存和历史经验，系统对每个选项进行评分（得分 0.0-1.0）：
- **0.7 - 1.0**: 低风险（推荐）
- **0.4 - 0.7**: 中风险（可能面临抢占或部分缺货）
- **0.0 - 0.4**: 高风险（建议选择其他选项或平台）

## 模块概览

- `tis/planner/models.py`: 核心数据结构定义 (Pydantic 模型)。
- `tis/planner/workload.py`: 请求加载、校验与解析逻辑。
- `tis/planner/market/`: 市场供应商的实现与抽象层。
- `tis/planner/pareto.py`: 前沿计算算法。
- `tis/planner/recommender.py`: 推荐结果排序与响应构建。
