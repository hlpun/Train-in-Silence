# Train in Silence

`Train in Silence` 是专门为 **LLM 微调 (Fine-tuning)** 场景设计的硬件规划器。只需简要描述您的工作负载（模型/训练参数），TIS 即可自动计算所需的 VRAM/FLOPs，并在 **10 多家全球云服务商** 中寻找最优的硬件配置。

## 核心价值

- **高保真任务建模 (High Fidelity)**：基于 Transformer 结构化参数进行精准估算（显存、算力、带宽）。
- **全球市场全覆盖**：聚合 Vast.ai, RunPod, AWS (公开价格), GCP, Azure, Lambda Labs 等平台实时数据。
- **免配置 (Keyless)**：AWS 与通用聚合器无需任何 API Key，真正做到开箱即用。
- **多目标优化**：直观展示 **成本 (Cost)** 与 **时间 (Time)** 之间的权衡，专为生成式 AI 优化。
- **透明可追溯**：每条建议均包含完整的数据来源标签与资源估算逻辑拆解。

## 快速开始

### 1. 安装

```bash
# 安装库（建议使用虚拟环境）
pip install train-in-silence
```

### 2. 生成首个推荐

```bash
tis recommend examples/request.yaml
```

## 文档指南

- [**CLI 指南**](./cli.md): 学习如何使用 `tis` 命令行工具。
- [**API 参考**](./api.md): 通过基于 FastAPI 的后端进行集成。
- [**市场供应商**](./providers.md): 了解 5 层级数据架构以及如何配置平台。
- [**架构与逻辑**](./architecture.md): 深入了解资源估算和优化引擎。
- [**MCP 插件**](./mcp.md): 将 TIS 作为 LLM 助手（Claude Code/Desktop）的工具插件使用。
- [**集成指南**](./integrations.md): 第三方工具的详细设置步骤。
