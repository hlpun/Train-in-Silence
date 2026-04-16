# 集成指南 (Claude Code / MCP)

`Train in Silence (TIS)` 可以通过多种方式集成到您的 AI 开发工作流中。

## 1. 在 Claude Code (CLI) 中使用

Claude Code 是 Anthropic 推出的命令行助手，它可以直接调用您系统中安装的工具。

### A. CLI 方式 (推荐直接安装)

如果您希望在 Claude Code 会话中直接让 Claude 运行 `tis` 命令，只需确保：

1.  **安装库**：在您的开发环境中运行 `pip install train-in-silence`。
2.  **配置环境变量**：Claude Code 会继承您当前的 Shell 环境变量。
    > [!TIP]
    > API Key 现在是**可选的**。如果不提供 Key，TIS 会自动回退到通用聚合器获取数据。
3.  **直接要求**：您可以对 Claude 说：“运行 `tis recommend examples/request.yaml` 并分析结果。”

### B. MCP 插件方式 (更强的交互体验)

通过 MCP (Model Context Protocol)，Claude 可以将 `tis` 作为内置工具调用，而无需您手动指定完整命令。

**快速添加工具 (无需 Key)：**
在终端运行以下命令：
```bash
claude mcp add tis-mcp --scope user --tis-mcp
```

**添加带 API Key 的工具：**
```bash
claude mcp add tis-mcp --scope user -e VAST_API_KEY=xxx -e RUNPOD_API_KEY=xxx --tis-mcp
```

## 2. 在 Claude Desktop (桌面端) 中使用

编辑您的 `claude_desktop_config.json` 文件：

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS/Linux**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**配置示例：**
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

配置完成后，重启 Claude Desktop，您会在侧边栏看到工具图标。

## 3. 环境变量参考

| 变量名 | 说明 | 必要性 |
| :--- | :--- | :--- |
| `VAST_API_KEY` | Vast.ai 的 API 密钥 | **可选** |
| `RUNPOD_API_KEY` | RunPod 的 API 密钥 | **可选** |
| `TIS_ALLOW_SAMPLE_FALLBACK` | 当网络请求失败时，是否允许使用内置样例数据 (默认 true) | - |
