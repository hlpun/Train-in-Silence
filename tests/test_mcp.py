from __future__ import annotations

import anyio

from tis.plugins.mcp_server import create_server


def _call_tool(name: str, arguments: dict) -> dict:
    async def runner() -> dict:
        server = create_server()
        result = await server.call_tool(name, arguments)
        if isinstance(result, tuple):
            return result[1]
        raise AssertionError(f"Expected structured output tuple, got {type(result)!r}")

    return anyio.run(runner)


def test_mcp_server_lists_expected_tools() -> None:
    async def runner() -> list[str]:
        server = create_server()
        tools = await server.list_tools()
        return sorted(tool.name for tool in tools)

    names = anyio.run(runner)
    assert "validate_request" in names
    assert "recommend_hardware" in names
    assert "explain_plan" in names
    assert "list_providers" in names
    assert "probe_market" in names
    assert "dump_market_offers" in names


def test_mcp_validate_request_supports_config_path() -> None:
    payload = _call_tool("validate_request", {"payload": {"config_path": "examples/request.yaml"}})
    assert payload["ok"] is True
    assert payload["request"]["workload"]["model"]["name"] == "llama-13b"


def test_mcp_recommend_hardware_supports_inline_request() -> None:
    payload = _call_tool(
        "recommend_hardware",
        {
            "payload": {
                "request": {
                    "workload": {
                        "model": {"name": "llama-13b", "params": 13000000000, "architecture": "decoder-only"},
                        "training": {
                            "method": "qlora",
                            "precision": "bf16",
                            "batch_size": 4,
                            "grad_accum": 8,
                            "seq_len": 2048,
                            "epochs": 3,
                        },
                        "data": {"dataset_tokens": 100000000},
                    },
                    "constraints": {
                        "platforms": ["vast.ai", "runpod"],
                        "max_budget": 20,
                        "max_time_hours": 12,
                        "region": ["us", "eu"],
                        "max_gpus": 4,
                    },
                    "preference": {"optimize_for": "balanced"},
                }
            }
        },
    )
    assert "summary" in payload
    assert "provider_statuses" in payload
    assert "recommendations" in payload


def test_mcp_dump_market_offers_returns_offers_and_statuses() -> None:
    payload = _call_tool("dump_market_offers", {"payload": {"config_path": "examples/request.yaml"}})
    assert "provider_statuses" in payload
    assert "offers" in payload
