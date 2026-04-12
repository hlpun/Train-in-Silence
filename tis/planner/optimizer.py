from __future__ import annotations

from tis.planner.models import (
    Availability,
    Constraints,
    MarketOffer,
    Recommendation,
    RecommendationConfig,
    RecommendationMetrics,
    ResourceEstimate,
    RiskLevel,
)


class OptimizerEngine:
    def generate_candidates(
        self,
        estimate: ResourceEstimate,
        offers: list[MarketOffer],
        constraints: Constraints,
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []

        for offer in offers:
            total_vram = offer.vram_gb * offer.gpu_count
            if total_vram < estimate.required_vram_gb:
                continue
            if offer.cpu < estimate.required_cpu_cores:
                continue
            if offer.ram_gb < estimate.required_ram_gb:
                continue

            time_hours = self._estimate_time_hours(estimate, offer)
            cost_usd = round(time_hours * offer.price_per_hour, 2)

            if constraints.max_budget is not None and cost_usd > constraints.max_budget:
                continue
            if constraints.max_time_hours is not None and time_hours > constraints.max_time_hours:
                continue

            availability = self._availability(offer)
            gpu_utilization = min(0.95, estimate.required_vram_gb / max(total_vram, 1.0))
            recommendations.append(
                Recommendation(
                    label="candidate",
                    config=RecommendationConfig(
                        gpu=offer.gpu,
                        gpu_count=offer.gpu_count,
                        cpu=offer.cpu,
                        ram=offer.ram_gb,
                        platform=offer.platform,
                        region=offer.region,
                    ),
                    metrics=RecommendationMetrics(
                        time_hours=round(time_hours, 2),
                        cost_usd=cost_usd,
                        gpu_utilization=round(gpu_utilization, 2),
                    ),
                    availability=availability,
                    source=offer.source,
                    notes=self._generate_offer_notes(offer),
                    explanation=(
                        f"{offer.platform} {offer.gpu_count}x {offer.gpu} "
                        f"with {offer.ram_gb:.0f}GB RAM meets the estimated resource floor."
                    ),
                )
            )

        return recommendations

    @staticmethod
    def _estimate_time_hours(estimate: ResourceEstimate, offer: MarketOffer) -> float:
        effective_tflops = offer.gpu_flops_tflops * offer.gpu_count * 1e12
        efficiency = 0.35 if offer.gpu_count == 1 else 0.3
        seconds = estimate.total_flops / max(effective_tflops * efficiency, 1.0)
        return max(seconds / 3600.0, 0.1)

    def _availability(self, offer: MarketOffer) -> Availability:
        if offer.is_availability_estimated:
            # Optimistic default for catalog-only data (like AWS)
            return Availability(score=0.8, risk=RiskLevel.LOW)

        score = min(1.0, offer.available_instances / 10.0)
        if score >= 0.7:
            risk = RiskLevel.LOW
        elif score >= 0.4:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.HIGH
        return Availability(score=round(score, 2), risk=risk)

    @staticmethod
    def _generate_offer_notes(offer: MarketOffer) -> list[str]:
        notes = []
        if offer.is_availability_estimated:
            notes.append("Availability is estimated based on historical catalog data.")
        if offer.is_region_estimated:
            notes.append("Region is inferred from provider availability status.")
        return notes
