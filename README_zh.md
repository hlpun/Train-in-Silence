<p align="center">
  <h1 align="center">Train in Silence</h1>
  <p align="center">
    别比价了，去训练吧。
  </p>
  <p align="center">
    <a href="https://github.com/hlpun/Train-in-Silence/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
    <a href="https://github.com/hlpun/Train-in-Silence/blob/main/README.md">English</a>
  </p>
</p>

---

你想微调一个 LLM。你打开了 Vast.ai、RunPod、AWS——三个标签页，三种计价方式，三种 GPU 命名规则。一小时后你还在 Excel 里比价，一行训练代码都没写。

**Train in Silence** 帮你搞定这些。描述一次工作负载，几秒钟内返回最便宜、最快、最均衡的硬件方案——横跨多家云服务商。

## 快速开始

### 方式一：让 Claude 帮你选（推荐）

安装库并注册为 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 的内置工具：

```bash
pip install train-in-silence
claude mcp add tis --scope user -- tis-mcp
```

然后用自然语言提问即可：

```
> 我想用 QLoRA 微调 Llama-13B，数据量 1 亿 token，预算 20 美元以内。
  帮我从 Vast.ai、RunPod、AWS 中找最优的 GPU 配置。
```

Claude 会在后台调用 TIS，直接返回结构化的推荐方案——不用写 YAML，不用手动比价。

### 方式二：命令行

```bash
pip install train-in-silence
tis recommend examples/request.yaml
```

```bash
$ tis recommend examples/request.yaml

  找到 5 个可行配置
  最低成本: $4.32 | 最快用时: 2.1 小时

  #1 [最便宜]  RunPod 1x A6000 (48 GB)    $4.32 / 6.8 h
  #2 [最快]    Vast.ai 2x A100 (80 GB)    $9.10 / 2.1 h
  #3 [均衡]    RunPod 1x A100 (80 GB)     $6.40 / 3.2 h
  ...
```

> **注意**：以上输出仅为示意，实际结果取决于实时市场数据。

## 灵活接入

| 使用方式 | 命令 | 文档 |
|---------|---------|------|
| **命令行** | `tis recommend request.yaml` | [CLI 指南](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/cli.md) |
| **REST API** | `uvicorn tis.api.server:app` | [API 参考](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/api.md) |
| **Claude Code** | `claude mcp add tis --scope user -- tis-mcp` | [MCP 指南](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/mcp.md) |
| **Claude Desktop** | 在 `claude_desktop_config.json` 中添加 `tis-mcp` | [MCP 指南](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/mcp.md) |

### 数据来源

实时接入三家云服务商报价——无需手动录入数据：

| 服务商 | 数据来源 | 需要鉴权 |
|----------|--------|---------------|
| **Vast.ai** | REST API | `VAST_API_KEY` |
| **RunPod** | GraphQL API | `RUNPOD_API_KEY` |
| **AWS** | 公开 EC2 价格表 | 无 |

如果某个服务商不可达，TIS 会优雅回退到内置的样例数据，并在结果中明确标注。[-> 数据源详情](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/providers.md)

## 架构一览

```
YAML 请求 -> 资源估算器 -> 市场聚合器 -> 优化器 -> 帕累托前沿 -> 排序输出
                |                |              |
           VRAM/FLOPs     Vast+RunPod+AWS  成本 vs. 时间
```

每条推荐都会标注**数据来源**（`live` 或 `sample`），并对任何估算字段做出透明标记——没有暗箱操作。[-> 架构详解](https://github.com/hlpun/Train-in-Silence/blob/main/docs/zh/architecture.md)

## 已知局限

- 估算模型固定，未引入校准机制。未来版本中将通过实际运行时间校准模型。
- 由于 AWS 未提供实时实例列表接口，AWS 可用性数据采用近似方法（已透明标注）。
- 上游 Provider API 格式如有变化，映射层需要同步更新。
