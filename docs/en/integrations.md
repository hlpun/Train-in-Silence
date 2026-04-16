# Integration Guide (Claude Code / MCP)

`Train in Silence (TIS)` can be integrated into your AI development workflow in several ways.

## 1. Using with Claude Code (CLI)

Claude Code is Anthropic's command-line assistant. It can directly interact with tools installed on your system.

### A. CLI Mode (Direct Execution)

If you want Claude to run `tis` commands directly during a session, ensure:

1.  **Installation**: Run `pip install train-in-silence` in your development environment.
2.  **Environment Variables**: Claude Code inherits your current shell's environment variables. 
    > [!TIP]
    > API keys are **optional**. TIS will automatically fall back to universal aggregators if keys are not provided.
3.  **Direct Interaction**: You can simply tell Claude: "Run `tis recommend examples/request.yaml` and analyze the output."

### B. MCP Mode (Interactive Tool)

Using the Model Context Protocol (MCP), Claude can use `tis` as an internal tool without you needing to specify the full command manually.

**Quick Add (Keyless):**
Run the following in your terminal:
```bash
claude mcp add tis-mcp --scope user --tis-mcp
```

**Add with API Keys:**
```bash
claude mcp add tis-mcp --scope user -e VAST_API_KEY=xxx -e RUNPOD_API_KEY=xxx --tis-mcp
```

## 2. Using with Claude Desktop

Edit your `claude_desktop_config.json` file:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS/Linux**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Configuration Example:**
```json
{
  "mcpServers": {
    "tis": {
      "command": "tis-mcp",
      "env": {
        "VAST_API_KEY": "optional_key",
        "RUNPOD_API_KEY": "optional_key"
      }
    }
  }
}
```

After configuring, restart Claude Desktop; you will see the tool icon in the sidebar.

## 3. Environment Variables Reference

| Variable | Description | Requirement |
| :--- | :--- | :--- |
| `VAST_API_KEY` | API Key for Vast.ai | **Optional** |
| `RUNPOD_API_KEY` | API Key for RunPod | **Optional** |
| `TIS_ALLOW_SAMPLE_FALLBACK` | Whether to allow using built-in sample data when online requests fail (default: true) | - |
