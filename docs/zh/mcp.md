# LLM 助手集成 (MCP 插件)

`Train in Silence` 支持 **Model Context Protocol (MCP)**。该协议允许大型语言模型（如 Claude）安全地访问本地工具和数据。

## 为什么要使用 MCP 插件？

集成 MCP 后，您的 AI 助手可以直接根据当前项目代码优化您的训练硬件配置：

- **Claude Code**: *"我想运行当前项目中的微调代码，并希望在 20 小时内完成。帮我从 Vast.ai、RunPod 和 Lambda 中找最优的 GPU 配置。"*
- **Claude Desktop**: *"这个时间估算准确吗？帮我分析一下瓶颈。"*

AI 会自动调用 `tis` 提供的工具并返回结构化的推荐方案。

### 核心 AI 工作流：自动参数提取
由于 `tis` 强制执行高保真 `ModelSpec` 契约，AI 助手（如 Claude）可以分析您项目中的 `config.json` 或模型定义文件，自动提取 `hidden_dim`, `num_layers`, `num_heads` 等参数。这种“分析 -> 规划”的闭环确保了成本和时间的估算是基于您实际使用的架构信息。

## 快速设置

### 1. 集成到 Claude Code (推荐)

Claude Code 支持直接通过终端添加 MCP 服务。运行以下命令即可：

```bash
claude mcp add tis --scope user --tis-mcp
```

### 2. 集成到 Claude Desktop

将以下内容添加到您的 `claude_desktop_config.json` 中（通常位于 `%APPDATA%\Claude\claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "tis": {
      "command": "tis-mcp",
      "env": {
        "VAST_API_KEY": "可选_KEY",
        "RUNPOD_API_KEY": "可选_KEY"
      }
    }
  }
}
```

> [!TIP]
> 环境变量是**可选的**。如果省略，TIS 将自动使用通用聚合器寻找算力资源。

## 提供的工具

该插件暴露了以下核心能力：

- `validate_request`: 验证配置请求。
- `recommend_hardware`: 横跨 10 多家厂商生成排序后的硬件推荐。
- `explain_plan`: 返回详细的资源估算、市场数据和优化逻辑。
- `list_providers`: 检查所有直连厂商和聚合层级的在线状态。
- `probe_market`: (调试用) 显示每个服务商的价格获取成功率和 offer 数量。
- `dump_market_offers`: (调试用) 列出所有考虑到的归一化市场报价。

## 安全性

MCP 插件运行在您的本地环境中。AI 只能通过暴露的工具接口访问数据。所有最终执行命令（如购买或租赁）都**不**包含在该插件中，以确保系统安全。
