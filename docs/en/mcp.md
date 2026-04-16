# LLM Assistant Integration (MCP Plugin)

`Train in Silence` supports the **Model Context Protocol (MCP)**, a standard that allows large language models (like Claude) to safely use local tools and data.

## Why use the MCP Plugin?

Integration allows your AI assistant to directly optimize your training hardware based on your project code:

- **Claude Code**: *"I want to run the fine-tune code in my current directory, and finish it within 20 hours. Find me the best GPU options across Vast.ai, RunPod, and Lambda."*
- **Claude Desktop**: *"Is this time estimate accurate? Analyze the bottlenecks for me."*

The AI will automatically call the tools provided by `tis` to return structured recommendations.

### Key AI Workflow: Auto-Extraction
Because `tis` enforces a high-fidelity `ModelSpec`, AI assistants (like Claude) can analyze your project's `config.json` or model weight files to automatically extract parameters like `hidden_dim`, `num_layers`, and `num_heads`. This "Analyis -> Plan" loop ensures the cost and time estimates are based on the actual architecture you are using.

## Quick Setup

### 1. Integration with Claude Code (Recommended)

Claude Code supports adding MCP servers directly via the terminal. Run the following command to add TIS:

```bash
claude mcp add tis --scope user --tis-mcp
```

### 2. Integration with Claude Desktop

Add the following to your `claude_desktop_config.json` (typically located at `%APPDATA%\Claude\claude_desktop_config.json`):

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

> [!TIP]
> Environment variables are **optional**. If omitted, TIS will automatically use universal aggregators to find hardware.

## Tools Provided

The plugin exposes the following core capabilities:

- `validate_request`: Validates configurations.
- `recommend_hardware`: Generates ranked hardware configurations across 10+ providers.
- `explain_plan`: Returns detailed resource estimates and optimization logic.
- `list_providers`: Checks the status of all supported direct and aggregator layers.
- `probe_market`: (Debug) Shows success/failure and offer counts per provider.
- `dump_market_offers`: (Debug) Lists all normalized market offers considered.

## Security

The MCP plugin runs in your local environment. The AI can only access data through the exposed tool interface. All final execution commands (such as purchasing or renting) are **not** included in this plugin, ensuring system safety.
