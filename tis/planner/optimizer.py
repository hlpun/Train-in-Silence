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
    Workload,
)

# Helper for calculation
PRECISION_BYTES = {"fp32": 4.0, "fp16": 2.0, "bf16": 2.0, "int8": 1.0, "int4": 0.5}


class OptimizerEngine:
    def generate_candidates(
        self,
        estimate: ResourceEstimate,
        offers: list[MarketOffer],
        constraints: Constraints,
        workload: Workload | list[Workload] | None = None,
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []

        for offer in offers:
            # Distributed Tax (C): Additional overhead for multi-GPU orchestration
            dist_cpu_tax = (offer.gpu_count - 1) * 2 if offer.gpu_count > 1 else 0
            dist_ram_tax = offer.gpu_count * 2.0 if offer.gpu_count > 1 else 0
            
            total_vram = offer.vram_gb * offer.gpu_count
            if total_vram < estimate.required_vram_gb:
                continue
            if offer.cpu < (estimate.required_cpu_cores + dist_cpu_tax):
                continue
            if offer.ram_gb < (estimate.required_ram_gb + dist_ram_tax):
                continue

            time_hours = self._estimate_time_hours(estimate, offer, workload)
            cost_usd = round(time_hours * offer.price_per_hour, 2)

            if constraints.max_budget is not None and cost_usd > constraints.max_budget:
                continue
            if constraints.max_time_hours is not None and time_hours > constraints.max_time_hours:
                continue

            availability = self._availability(offer)
            gpu_utilization = min(0.98, estimate.required_vram_gb / max(total_vram, 1.0))
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
                        time_hours=round(time_hours, 4),
                        cost_usd=cost_usd,
                        gpu_utilization=round(gpu_utilization, 2),
                    ),
                    availability=availability,
                    source=offer.source,
                    notes=self._generate_offer_notes(offer),
                    explanation=(
                        f"{offer.platform} {offer.gpu_count}x {offer.gpu} "
                        f"with {offer.ram_gb:.0f}GB RAM fits the '{estimate.required_vram_gb}GB' pipeline bottleneck."
                    ),
                )
            )

        return recommendations

    @staticmethod
    def _estimate_single_stage_time(estimate: ResourceEstimate, offer: MarketOffer, workload: Workload) -> float:
        effective_tflops = offer.gpu_flops_tflops * offer.gpu_count * 1e12
        
        # Branch 1: Inference Logic (Bandwidth vs Compute)
        if workload.inference:
            inf = workload.inference
            model = workload.model
            
            # Prefill (Compute-bound)
            mfu_prefill = 0.6 if offer.gpu_count == 1 else 0.5
            prefill_flops = 2 * model.params * inf.prompt_tokens
            prefill_seconds = prefill_flops / max(effective_tflops * mfu_prefill, 1.0)
            
            # Decoding (Bandwidth-bound)
            bytes_per_param = PRECISION_BYTES.get(inf.precision, 2.0)
            
            # Use active params for MoE decoding
            active_params = model.active_experts / model.num_experts * model.params if model.num_experts > 0 else model.params
            active_model_size_gb = active_params * bytes_per_param / (1024**3)
            
            total_bandwidth_gbps = offer.memory_bw_gbps * offer.gpu_count
            decoding_tps_bandwidth = total_bandwidth_gbps / max(active_model_size_gb, 0.001)
            
            decoding_tps_compute = (effective_tflops * 0.4) / (2 * active_params)
            
            decoding_tps = min(decoding_tps_bandwidth, decoding_tps_compute)
            decoding_seconds = inf.max_new_tokens / max(decoding_tps, 1e-6)
            
            total_seconds = prefill_seconds + decoding_seconds
            return max(total_seconds / 3600.0, 1e-6)

        # Branch 2: Training Logic
        efficiency = 0.45 if offer.gpu_count == 1 else 0.35
        seconds = estimate.total_flops / max(effective_tflops * efficiency, 1.0)
        return max(seconds / 3600.0, 1e-3)

    @staticmethod
    def _estimate_time_hours(
        estimate: ResourceEstimate, 
        offer: MarketOffer, 
        workload: Workload | list[Workload] | None = None
    ) -> float:
        if isinstance(workload, list) and estimate.stage_details:
            total_time = 0.0
            for stage_workload, stage_estimate in zip(workload, estimate.stage_details):
                total_time += OptimizerEngine._estimate_single_stage_time(stage_estimate, offer, stage_workload)
            return total_time
        
        if isinstance(workload, Workload):
            return OptimizerEngine._estimate_single_stage_time(estimate, offer, workload)

        # Fallback to simple FLOPs/Speed ratio if workload info is missing
        effective_tflops = offer.gpu_flops_tflops * offer.gpu_count * 1e12
        efficiency = 0.35
        seconds = estimate.total_flops / max(effective_tflops * efficiency, 1.0)
        return max(seconds / 3600.0, 1e-3)

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
