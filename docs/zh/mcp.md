# LLM 助手集成 (MCP 插件)

`Train in Silence` 支持 **Model Context Protocol (MCP)**。这是一项标准，允许大型语言模型（如 Claude）安全地使用本地工具和数据。

## 为什么要使用 MCP 插件？

当您与 Claude 等 AI 聊天时，可以直接要求它优化您的训练方案：
- *“帮我优化 Llama-3-70B 全量微调的硬件配置，预算在 $20 以内。”*
- *“这个配置的时间预估准确吗？帮我分析一下瓶颈。”*

AI 将自动调用 `tis` 提供的工具，为您返回结构化的推荐。

## 快速设置

### 1. 启动 MCP 服务

`tis` 提供了一个基于 `FastMCP` 构建的内置 MCP 服务器。

```bash
tis-mcp
```

默认情况下，它使用 `stdio` 传输协议。

### 2. 在 Claude Desktop 中配置

将以下内容添加到您的 `claude_desktop_config.json`（通常位于 `%APPDATA%\Claude\claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "tis": {
      "command": "tis-mcp",
      "env": {
        "VAST_API_KEY": "您的 Key",
        "RUNPOD_API_KEY": "您的 Key"
      }
    }
  }
}
```

## 提供的工具

该插件公开了以下核心能力：

- `validate_request`: 验证配置信息。
- `recommend_hardware`: 生成排序后的硬件配置建议。
- `explain_plan`: 返回详细的资源预估、市场报价及排序逻辑。
- `list_providers`: 检查支持的算力供应商的在线状态。
- `probe_market`: (调试) 显示每个服务商的原始成功/失败状态及报价数量。
- `dump_market_offers`: (调试) 列出所考虑的所有归一化市场报价数据。

## 安全性

MCP 插件在您的本地环境中运行。AI 只能通过公开的工具接口（Tool interface）访问数据。所有的最终执行命令（如购买或租赁）**不**包含在此插件中，以确保系统安全性。
