# Train in Silence

`Train in Silence` 是一个专为 LLM 微调场景设计的硬件规划器。它根据您的工作负载（模型/训练参数）、约束条件（平台、预算）和偏好，结合实时市场数据和启发式资源模型，推荐帕累托最优（Pareto-optimal）的硬件配置。

## 核心价值

- **精确建模**：基于模型架构和训练参数，估算显存（VRAM）、计算能力和带宽需求。
- **实时市场**：聚合来自 Vast.ai、RunPod 和 AWS 等主流算力市场的实时报价。
- **多目标优化**：在成本和时间之间寻找平衡，生成帕累托前沿（Pareto Frontier）候选方案。
- **数据透明**：明确标记估算或推断的数据（例如仅有目录的库存），确保结果可信。

## 快速开始

### 1. 安装

```bash
# 安装库（建议使用虚拟环境）
pip install train-in-silence
```

### 2. 运行首次推荐

```bash
tis recommend examples/request.yaml
```

## 文档指南

- [**CLI 指南**](./cli.md): 了解如何使用 `tis` 命令行工具。
- [**API 参考**](./api.md): 通过基于 FastAPI 的后端进行集成。
- [**市场供应商**](./providers.md): 了解平台数据源和配置。
- [**架构与逻辑**](./architecture.md): 深入了解资源估算和优化引擎。
- [**MCP 插件**](./mcp.md): 作为 LLM 助手的工具插件使用。
- [**集成指南**](./integrations.md): 配置 Claude Code 或 Claude Desktop。
