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
    MIN_TRAINING_TIME_HOURS = 1e-3
    MIN_INFERENCE_TIME_HOURS = 1e-6
    MIN_COST_USD = 0.0001

    # Physical Constants for Overhead Estimation
    PLATFORM_BOOT_TAX_HOURS = {
        "runpod": 0.033,   # ~2 mins
        "vast.ai": 0.05,    # ~3 mins
        "aws": 0.083,      # ~5 mins
        "lambda": 0.05,    # ~3 mins
        "default": 0.05,
    }
    IO_BANDWIDTH_GBPS = 1.0    # Persistent disk/SSD to VRAM bandwidth
    PREPROCESSING_TPS = 50000  # Tokens per second for preprocessing

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

            time_hours = self._estimate_time_hours(estimate, offer, constraints, workload)
            
            # Filter redundant hardware: if the task is so small it hits the performance floor, 
            # it means the hardware is excessively powerful for this workload.
            if time_hours <= self._get_time_floor(workload):
                continue

            cost_usd = max(round(time_hours * offer.price_per_hour, 4), OptimizerEngine.MIN_COST_USD)

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
                    notes=self._generate_offer_notes(offer, estimate),
                    explanation=(
                        f"{offer.platform} {offer.gpu_count}x {offer.gpu} "
                        f"with {offer.ram_gb:.0f}GB RAM fits the '{estimate.required_vram_gb}GB' pipeline bottleneck."
                    ),
                )
            )

        return recommendations

    @staticmethod
    def _estimate_single_stage_time(
        estimate: ResourceEstimate, 
        offer: MarketOffer, 
        workload: Workload,
        constraints: Constraints
    ) -> float:
        effective_tflops = offer.gpu_flops_tflops * offer.gpu_count * 1e12
        
        # 1. Physics-based Overhead Calculation
        # A. Weight Loading (Disk -> RAM -> VRAM)
        weights_gb = estimate.required_vram_gb - 2.0  # Subtracting system overhead approx
        io_hours = weights_gb / (constraints.storage_speed_gbps * 3600.0)
        
        # B. Download (Optional)
        download_hours = 0.0
        if not constraints.skip_download:
             download_hours = weights_gb / (constraints.network_speed_gbps / 8.0 * 3600.0)
        
        # C. Preprocessing (CPU bound)
        tokens = 0
        if workload.training:
            tokens += (workload.data.dataset_tokens if workload.data else 0) * workload.training.epochs
        if workload.inference:
            # For inference, tokens = total tokens in the prompt + generated
            tokens += (workload.inference.prompt_tokens + workload.inference.max_new_tokens) * workload.inference.batch_size
        
        tokens *= workload.repeats
        preprocess_hours = tokens / (OptimizerEngine.PREPROCESSING_TPS * 3600.0)

        # 2. Compute Calculation
        compute_hours = 0.0
        
        # A. Training Compute
        if workload.training:
            # Use training-only flops from stage_details if available, else use total_flops
            training_flops = estimate.total_flops
            if estimate.stage_details and len(estimate.stage_details) > 0:
                # In mixed mode, training is index 0
                training_flops = estimate.stage_details[0].total_flops
            
            efficiency = 0.45 if offer.gpu_count == 1 else 0.35
            seconds = training_flops / max(effective_tflops * efficiency, 1.0)
            compute_hours += seconds / 3600.0

        # B. Inference Compute
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
            
            inf_seconds = (prefill_seconds + decoding_seconds) * workload.repeats
            compute_hours += inf_seconds / 3600.0

        total_hours = compute_hours + io_hours + download_hours + preprocess_hours
        floor = OptimizerEngine.MIN_INFERENCE_TIME_HOURS if not workload.training else OptimizerEngine.MIN_TRAINING_TIME_HOURS
        return max(total_hours, floor)


    @staticmethod
    def _estimate_time_hours(
        estimate: ResourceEstimate, 
        offer: MarketOffer, 
        constraints: Constraints,
        workload: Workload | list[Workload] | None = None
    ) -> float:
        # print(f"DEBUG: workload type={type(workload)} flops={estimate.total_flops}")
        # One-time Boot Tax (Setup)
        boot_tax = OptimizerEngine.PLATFORM_BOOT_TAX_HOURS.get(
            offer.platform, OptimizerEngine.PLATFORM_BOOT_TAX_HOURS["default"]
        )
        
        if isinstance(workload, list) and estimate.stage_details:
            total_time = boot_tax
            for stage_workload, stage_estimate in zip(workload, estimate.stage_details):
                total_time += OptimizerEngine._estimate_single_stage_time(
                    stage_estimate, offer, stage_workload, constraints
                )
            return total_time
        
        if isinstance(workload, Workload):
            return boot_tax + OptimizerEngine._estimate_single_stage_time(
                estimate, offer, workload, constraints
            )

        # Fallback to simple FLOPs/Speed ratio if workload info is missing
        effective_tflops = offer.gpu_flops_tflops * offer.gpu_count * 1e12
        efficiency = 0.35
        seconds = estimate.total_flops / max(effective_tflops * efficiency, 1.0)
        compute_hours = seconds / 3600.0
        return max(boot_tax + compute_hours, OptimizerEngine.MIN_TRAINING_TIME_HOURS)

    @staticmethod
    def _get_time_floor(workload: Workload | list[Workload] | None) -> float:
        if isinstance(workload, list):
            return sum(
                OptimizerEngine.MIN_INFERENCE_TIME_HOURS if w.inference else OptimizerEngine.MIN_TRAINING_TIME_HOURS
                for w in workload
            )
        if isinstance(workload, Workload):
            return OptimizerEngine.MIN_INFERENCE_TIME_HOURS if workload.inference else OptimizerEngine.MIN_TRAINING_TIME_HOURS
        return OptimizerEngine.MIN_TRAINING_TIME_HOURS

    def _availability(self, offer: MarketOffer) -> Availability:
        if offer.is_availability_estimated:
            # Optimistic default for catalog-only data (like AWS)
            return Availability(score=0.8, risk=RiskLevel.LOW)

        # Check if this is an aggregated source without real availability data
        if offer.source_detail in {"live:gpufindr", "live:gpuhunt"}:
            return Availability(score=0.0, risk=RiskLevel.UNKNOWN)

        score = min(1.0, offer.available_instances / 10.0)
        if score >= 0.7:
            risk = RiskLevel.LOW
        elif score >= 0.4:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.HIGH
        return Availability(score=round(score, 2), risk=risk)

    @staticmethod
    def _generate_offer_notes(offer: MarketOffer, estimate: ResourceEstimate) -> list[str]:
        notes = ["Time estimate includes physical overheads (boot setup, model loading, and preprocessing)."]
        
        # Explain why "overkill" GPUs are recommended if they are cost-effective
        total_vram = offer.vram_gb * offer.gpu_count
        if total_vram > estimate.required_vram_gb * 1.5:
             notes.append("High-capacity configuration selected for superior price-performance despite low VRAM utilization.")
             
        if offer.is_availability_estimated:
            notes.append("Availability is estimated based on historical catalog data.")
        if offer.is_region_estimated:
            notes.append("Region is inferred from provider availability status.")
        return notes
