<p align="center">
  <h1 align="center">Train in Silence</h1>
    首个“任务感知型” (Task-Aware) LLM 微调 MCP 服务。
    别比价了，去训练吧。
  </p>
  <p align="center">
    <a href="https://github.com/hlpun/Train-in-Silence/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
    <a href="https://github.com/hlpun/Train-in-Silence/blob/main/README.md">English</a>
  </p>
</p>

---

你想微调一个 LLM。你打开了 Vast.ai、RunPod、AWS 等平台——十多个标签页，十多种计价方式，十多种 GPU 命名规则。哪个选择能把手上的代码跑起来，并且更便宜、更快？一小时后你还在 Excel 里比价，一行训练代码都没写。

**Train in Silence** 是首个专为LLM微调设计的**“任务感知型” (Task-Aware) MCP 服务**。它不只是列出报价，而是通过理解你的训练负载，自动计算所需的 VRAM/FLOPs 需求，并在几秒钟内横跨 **十多家云服务商** 返回最便宜、最快、最均衡的硬件方案。

## 快速开始

### 方式一：让 Claude Code 帮你选（推荐）

安装库并注册为 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 的内置工具：

```bash
pip install train-in-silence
claude mcp add tis --scope user -- tis-mcp
```

然后用自然语言提问即可：

```
> 我想运行当前项目中的微调代码，希望20小时内完成。
  帮我从 Vast.ai、RunPod、Lambda 中找最优的 GPU 配置。
```

Claude Code 会在后台调用 TIS，直接返回结构化的推荐方案——不用写 YAML，不用手动比价。

### 方式二：命令行

```bash
pip install train-in-silence
tis recommend examples/request.yaml
```

```bash
$ tis recommend examples/request.yaml

  找到 5 个可行配置
  最低成本: $4.32 | 最快用时: 2.1 小时

  #1 [cheapest]  RunPod 1x A6000 (48 GB)    $4.32 / 6.8 h
  #2 [fastest]   Vast.ai 2x A100 (80 GB)    $9.10 / 2.1 h
  #3 [balanced]  RunPod 1x A100 (80 GB)     $6.40 / 3.2 h
  ...
```

> **注意**：以上输出仅为示意，实际结果取决于实时市场数据。

## 灵活接入

| 使用方式 | 命令 | 文档 |
|---------|---------|------|
| **命令行** | `tis recommend request.yaml` | [CLI 指南](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/cli.md) |
| **REST API** | `uvicorn tis.api.server:app` | [API 参考](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/api.md) |
| **Claude Code** | `claude mcp add tis --scope user --tis-mcp` | [MCP 指南](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/mcp.md) |
| **Claude Desktop** | 在 `claude_desktop_config.json` 中添加 `tis-mcp` | [MCP 指南](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/mcp.md) |

### 数据来源

TIS 实时聚合十多家 GPU 云厂商的报价。API Key 是**可选的**：如果不提供，TIS 会自动依次通过通用聚合器 (GPUHunt/GPUFinder) 或内置样例数据进行兜底。

| 服务商类别 | 包含平台 | 需要鉴权 |
|----------------|--------------------|---------------|
| **直连厂商** | Vast.ai, RunPod, AWS | **可选** (推荐配置以获得最高精度) |
| **聚合厂商** | Vast.ai, RunPod, AWS, CoreWeave, Lambda Labs, Tensordock, Vultr, GCP, Azure, OCI, Nebius, CloudRift, Cudo Compute, Verda | **无** (自动兜底) |

每条推荐都会标注**数据来源**（如 `live:official`、`live:gpuhunt`、`live:gpufinder` 或 `sample`），确保你始终了解数据的实时性。[-> 数据源详情](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/providers.md)

## 架构一览

```
YAML 请求 -> 资源估算器 -> 市场聚合器 -> 优化器 -> 帕累托前沿 -> 排序输出
                |                |              |
           VRAM/FLOPs    10+ 全球算力云  成本 vs. 时间
```

每条推荐都会标注**数据来源**（`live` 或 `sample`），并对任何估算字段做出透明标记——没有暗箱操作。[-> 架构详解](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/architecture.md)

## 已知局限

- 估算模型固定，未引入校准机制。未来版本中将通过实际运行时间校准模型。
- 上游 Provider API 格式如有变化，映射层需要同步更新。

## 🚧 项目状态与贡献

本项目目前仍处于 **实验性开发阶段 (Experimental)**。

- **反馈问题与建议**：如果您在使用过程中遇到任何 Bug、架构参数估算不准的情况，或有任何改进建议，请随时提交 [GitHub Issue](https://github.com/hlpun/Train-in-Silence/issues)。
- **参与贡献**：如果您想优化代码或补全更多硬件元数据，非常欢迎提交 Pull Request！我们期待与社区共同完善这个 LLM 算力规划工具。
