from __future__ import annotations

from typer.testing import CliRunner

from tis.cli.main import app

runner = CliRunner()


def test_validate_command() -> None:
    result = runner.invoke(app, ["validate", "examples/request.yaml"])
    assert result.exit_code == 0
    assert "Config is valid." in result.stdout


def test_market_probe_shows_provider_statuses() -> None:
    result = runner.invoke(app, ["market", "probe", "examples/request.yaml"])
    assert "Providers:" in result.stdout
    assert result.exit_code in {0, 1}


def test_explain_json_contains_market_and_response() -> None:
    result = runner.invoke(app, ["explain", "examples/request.yaml", "--output", "json"])
    assert result.exit_code == 0
    assert '"market"' in result.stdout
    assert '"provider_statuses"' in result.stdout


def test_explain_rich_terminal_output() -> None:
    result = runner.invoke(app, ["explain", "examples/request.yaml"])
    assert result.exit_code == 0
    assert "Metrics:" in result.stdout
    assert "Availability:" in result.stdout
    assert "Logic:" in result.stdout
