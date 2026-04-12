from __future__ import annotations

from tis.planner.estimator import ResourceEstimator
from tis.planner.market import MarketDataAggregator
from tis.planner.models import OptimizeFor, PlanningRequest, PlanningResponse, PlanningRun, Recommendation
from tis.planner.optimizer import OptimizerEngine
from tis.planner.pareto import pareto_frontier


class PlannerService:
    def __init__(
        self,
        estimator: ResourceEstimator | None = None,
        market: MarketDataAggregator | None = None,
        optimizer: OptimizerEngine | None = None,
    ) -> None:
        self.estimator = estimator or ResourceEstimator()
        self.market = market or MarketDataAggregator()
        self.optimizer = optimizer or OptimizerEngine()

    def run(self, request: PlanningRequest) -> PlanningRun:
        estimate = self.estimator.estimate(request.workload)
        market = self.market.fetch_market_data(request.constraints)
        candidates = self.optimizer.generate_candidates(estimate, market.offers, request.constraints)
        frontier = pareto_frontier(candidates)
        ranked = self._rank(frontier or candidates, request.preference.optimize_for)[:5]
        labeled = self._label_recommendations(ranked)
        summary = self._build_summary(labeled, market.provider_statuses)
        response = PlanningResponse(
            summary=summary,
            provider_statuses=market.provider_statuses,
            recommendations=labeled,
        )
        return PlanningRun(estimate=estimate, market=market, response=response)

    def recommend(self, request: PlanningRequest) -> PlanningResponse:
        return self.run(request).response

    @staticmethod
    def _rank(recommendations: list[Recommendation], mode: OptimizeFor) -> list[Recommendation]:
        if mode == OptimizeFor.MIN_COST:
            return sorted(recommendations, key=lambda item: (item.metrics.cost_usd, item.metrics.time_hours))
        if mode == OptimizeFor.MIN_TIME:
            return sorted(recommendations, key=lambda item: (item.metrics.time_hours, item.metrics.cost_usd))
        return sorted(
            recommendations,
            key=lambda item: (item.metrics.cost_usd * 0.5) + (item.metrics.time_hours * 0.5),
        )

    @staticmethod
    def _label_recommendations(recommendations: list[Recommendation]) -> list[Recommendation]:
        if not recommendations:
            return []

        cheapest = min(recommendations, key=lambda item: item.metrics.cost_usd)
        fastest = min(recommendations, key=lambda item: item.metrics.time_hours)
        balanced = min(
            recommendations,
            key=lambda item: (item.metrics.cost_usd * 0.5) + (item.metrics.time_hours * 0.5),
        )

        labeled: list[Recommendation] = []
        for item in recommendations:
            if item is cheapest:
                label = "cheapest"
            elif item is fastest:
                label = "fastest"
            elif item is balanced:
                label = "balanced"
            else:
                label = "candidate"
            labeled.append(item.model_copy(update={"label": label}))
        return labeled

    @staticmethod
    def _build_summary(recommendations: list[Recommendation], provider_statuses) -> str:
        live_ok = [status.provider for status in provider_statuses if status.ok and status.source == "live"]
        sample_used = any(status.source == "sample" and status.ok for status in provider_statuses)
        if not recommendations:
            if sample_used:
                return "No viable hardware configuration matched the current constraints. Results used bundled sample market data."
            if live_ok:
                return "No viable hardware configuration matched the current constraints from current live provider data."
            return "No viable hardware configuration matched the current constraints."
        cheapest = min(recommendations, key=lambda item: item.metrics.cost_usd)
        fastest = min(recommendations, key=lambda item: item.metrics.time_hours)
        source = "sample market data" if sample_used else "live market data"
        return (
            f"Found {len(recommendations)} viable configurations. "
            f"Lowest cost is ${cheapest.metrics.cost_usd:.2f}; "
            f"fastest estimated runtime is {fastest.metrics.time_hours:.2f} hours. "
            f"Computed from {source}."
        )
