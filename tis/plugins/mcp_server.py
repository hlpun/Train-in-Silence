from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, model_validator

from tis.planner.models import Constraints, MarketOffer, PlanningRequest, PlanningResponse, PlanningRun, ProviderStatus
from tis.planner.recommender import PlannerService
from tis.planner.workload import load_request

APP_VERSION = "0.1.2"


class RequestEnvelope(BaseModel):
    request: PlanningRequest | None = None
    config_path: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "RequestEnvelope":
        if self.request is None and self.config_path is None:
            raise ValueError("Either request or config_path must be provided.")
        if self.request is not None and self.config_path is not None:
            raise ValueError("Provide either request or config_path, not both.")
        return self


class ValidationResult(BaseModel):
    ok: bool = True
    version: str = APP_VERSION
    summary: str
    request: PlanningRequest


class ProvidersResult(BaseModel):
    version: str = APP_VERSION
    providers: list[ProviderStatus]


class MarketOffersResult(BaseModel):
    version: str = APP_VERSION
    provider_statuses: list[ProviderStatus]
    offers: list[MarketOffer]


class MCPMetadata(BaseModel):
    name: str = "train-in-silence"
    version: str = APP_VERSION
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    capabilities: list[str] = Field(
        default_factory=lambda: [
            "validate_request",
            "recommend_hardware",
            "explain_plan",
            "list_providers",
            "probe_market",
            "dump_market_offers",
        ]
    )


class TISPlannerPlugin:
    """MCP wrapper around the planner service."""

    def __init__(self, service: PlannerService | None = None) -> None:
        self._service = service or PlannerService()

    def validate(self, payload: RequestEnvelope) -> ValidationResult:
        request = self._resolve_request(payload)
        return ValidationResult(
            summary=(
                f"Model={request.workload.model.name} | "
                f"optimize_for={request.preference.optimize_for} | "
                f"platforms={','.join(request.constraints.platforms)}"
            ),
            request=request,
        )

    def recommend(self, payload: RequestEnvelope) -> PlanningResponse:
        request = self._resolve_request(payload)
        return self._service.recommend(request)

    def explain(self, payload: RequestEnvelope) -> PlanningRun:
        request = self._resolve_request(payload)
        return self._service.run(request)

    def providers(self, constraints: Constraints | None = None) -> ProvidersResult:
        market = self._service.market.fetch_market_data(constraints or Constraints())
        return ProvidersResult(providers=market.provider_statuses)

    def probe_market(self, payload: RequestEnvelope) -> ProvidersResult:
        request = self._resolve_request(payload)
        run = self._service.run(request)
        return ProvidersResult(providers=run.response.provider_statuses)

    def dump_offers(self, payload: RequestEnvelope) -> MarketOffersResult:
        request = self._resolve_request(payload)
        run = self._service.run(request)
        return MarketOffersResult(
            provider_statuses=run.response.provider_statuses,
            offers=run.market.offers,
        )

    @staticmethod
    def _resolve_request(payload: RequestEnvelope) -> PlanningRequest:
        if payload.request is not None:
            return payload.request
        if payload.config_path is not None:
            return load_request(payload.config_path)
        raise ValueError("Either request or config_path must be provided.")


def create_server(service: PlannerService | None = None) -> FastMCP:
    plugin = TISPlannerPlugin(service=service)
    server = FastMCP(
        name="train-in-silence",
        instructions=(
            "Plan hardware for LLM fine-tuning workloads. "
            "Use validate_request before execution when the request shape is uncertain. "
            "recommend_hardware returns ranked recommendations. "
            "explain_plan returns resource estimates and normalized market data."
        ),
    )

    @server.tool(
        name="planner_metadata",
        description="Return MCP server metadata and the exposed planner capabilities.",
        structured_output=True,
    )
    def planner_metadata() -> MCPMetadata:
        return MCPMetadata()

    @server.tool(
        name="validate_request",
        description="Validate a planning request provided inline or loaded from a YAML/JSON config path.",
        structured_output=True,
    )
    def validate_request(payload: RequestEnvelope) -> ValidationResult:
        return plugin.validate(payload)

    @server.tool(
        name="recommend_hardware",
        description="Generate ranked hardware recommendations for an LLM fine-tuning planning request.",
        structured_output=True,
    )
    def recommend_hardware(payload: RequestEnvelope) -> PlanningResponse:
        return plugin.recommend(payload)

    @server.tool(
        name="explain_plan",
        description="Run the full planner and return estimates, normalized market offers, provider statuses, and recommendations.",
        structured_output=True,
    )
    def explain_plan(payload: RequestEnvelope) -> PlanningRun:
        return plugin.explain(payload)

    @server.tool(
        name="list_providers",
        description="Fetch provider health statuses using optional planning constraints.",
        structured_output=True,
    )
    def list_providers(constraints: Constraints | None = None) -> ProvidersResult:
        return plugin.providers(constraints)

    @server.tool(
        name="probe_market",
        description="Run market aggregation for a planning request and return provider statuses.",
        structured_output=True,
    )
    def probe_market(payload: RequestEnvelope) -> ProvidersResult:
        return plugin.probe_market(payload)

    @server.tool(
        name="dump_market_offers",
        description="Return normalized market offers considered for a planning request.",
        structured_output=True,
    )
    def dump_market_offers(payload: RequestEnvelope) -> MarketOffersResult:
        return plugin.dump_offers(payload)

    return server


def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    create_server().run(transport=transport)


if __name__ == "__main__":
    run_server()
