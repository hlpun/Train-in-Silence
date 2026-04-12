# LLM Assistant Integration (MCP Plugin)

`Train in Silence` supports the **Model Context Protocol (MCP)**, a standard that allows large language models (like Claude) to safely use local tools and data.

## Why use the MCP Plugin?

When chatting with an AI like Claude, you can directly ask it to optimize your training setup:
- *"Optimize my Llama-3-70B full fine-tuning hardware configuration with a budget under $20."*
- *"Is the time estimate for this configuration accurate? Analyze the bottlenecks for me."*

The AI will automatically call the tools provided by `tis` to return structured recommendations.

## Quick Setup

### 1. Start the MCP Service

`tis` provides a built-in MCP server built on `FastMCP`.

```bash
tis-mcp
```

By default, it uses the `stdio` transport protocol.

### 2. Configure in Claude Desktop

Add the following to your `claude_desktop_config.json` (typically located at `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "tis": {
      "command": "tis-mcp",
      "env": {
        "VAST_API_KEY": "your_key",
        "RUNPOD_API_KEY": "your_key"
      }
    }
  }
}
```

## Tools Provided

The plugin exposes the following core capabilities:

- `validate_request`: Validates configurations.
- `recommend_hardware`: Generates ranked hardware configurations.
- `explain_plan`: Returns detailed resource estimates, market data, and sorting logic.
- `list_providers`: Checks the online status of supported providers.
- `probe_market`: (Debug) Shows raw success/failure and offer counts per provider.
- `dump_market_offers`: (Debug) Lists all normalized market offers considered.

## Security

The MCP plugin runs in your local environment. The AI can only access data through the exposed Tool interface. All final execution commands (such as purchasing or renting) are **not** included in this plugin, ensuring system safety.
