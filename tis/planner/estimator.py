from __future__ import annotations

from tis.planner.models import ResourceEstimate, Workload


PRECISION_BYTES = {
    "fp32": 4.0,
    "fp16": 2.0,
    "bf16": 2.0,
    "int8": 1.0,
    "int4": 0.5,
}

METHOD_MULTIPLIER = {
    "full": 1.0,  # Base model footprint
    "lora": 1.0,  # Base model + small LoRA weights (delta ignored here for simplicity)
    "qlora": 0.25, # 4-bit base model
}

# Average bytes per parameter for non-model states (Gradients + Optimizer)
TRAINING_OVERHEAD_FACTOR = {
    "full": 3.0,  # Gradients(1x) + Multi-state Optimizer(2x)
    "lora": 0.5,  # LoRA gradients and optimizer only
    "qlora": 0.3, # QLoRA gradients and optimizer only
}

TRAINING_FLOPS_FACTOR = {
    "full": 1.0,
    "lora": 0.67,
    "qlora": 0.65,
}


class ResourceEstimator:
    """Hardware-aware estimator for training and inference workloads."""

    def estimate(self, workload: Workload | list[Workload]) -> ResourceEstimate:
        if isinstance(workload, list):
            return self._estimate_pipeline(workload)
        
        if workload.training and workload.inference:
            est_t = self._estimate_training(workload)
            est_i = self._estimate_inference(workload)
            return ResourceEstimate(
                required_vram_gb=max(est_t.required_vram_gb, est_i.required_vram_gb),
                required_cpu_cores=max(est_t.required_cpu_cores, est_i.required_cpu_cores),
                required_ram_gb=max(est_t.required_ram_gb, est_i.required_ram_gb),
                total_flops=est_t.total_flops + est_i.total_flops,
                throughput_tokens_per_second=0.0,
                kv_cache_gb=est_i.kv_cache_gb,
                stage_details=[est_t, est_i]
            )

        if workload.training:
            return self._estimate_training(workload)
        return self._estimate_inference(workload)

    def _estimate_pipeline(self, pipeline: list[Workload]) -> ResourceEstimate:
        """Aggregates multiple workload stages sequentially."""
        stage_estimates = []
        for stage in pipeline:
            if stage.inference:
                stage_estimates.append(self._estimate_inference(stage))
            else:
                stage_estimates.append(self._estimate_training(stage))
        
        if not stage_estimates:
            raise ValueError("Pipeline cannot be empty")

        return ResourceEstimate(
            required_vram_gb=max(e.required_vram_gb for e in stage_estimates),
            required_cpu_cores=max(e.required_cpu_cores for e in stage_estimates),
            required_ram_gb=max(e.required_ram_gb for e in stage_estimates),
            total_flops=sum(e.total_flops for e in stage_estimates),
            throughput_tokens_per_second=0.0,
            kv_cache_gb=max(e.kv_cache_gb for e in stage_estimates),
            stage_details=stage_estimates
        )

    def _estimate_inference(self, workload: Workload) -> ResourceEstimate:
        model = workload.model
        inference = workload.inference
        precision_bytes = PRECISION_BYTES[inference.precision]
        
        # Scaling for MoE
        active_params = model.active_experts / model.num_experts * model.params if model.num_experts > 0 else model.params
        
        # 1. Memory Calculation
        weight_gb = model.params * precision_bytes / (1024**3)
        
        context_len = inference.context_length or (inference.prompt_tokens + inference.max_new_tokens)
        head_dim = model.hidden_dim // model.num_heads
        
        # KV Cache: 2 (K and V) * bytes * layers * kv_heads * head_dim * seq_len * batch
        kv_cache_bytes = 2 * precision_bytes * model.num_layers * model.num_kv_heads * head_dim * context_len * inference.batch_size
        kv_cache_gb = kv_cache_bytes / (1024**3)
        
        # Activation & System Overhead
        activation_gb = (inference.batch_size * model.hidden_dim * 2) / (1024**3)
        system_overhead_gb = 2.0
        
        required_vram_gb = round(weight_gb + kv_cache_gb + activation_gb + system_overhead_gb, 2)
        required_cpu_cores = max(4, inference.batch_size * 2)
        
        # 1.1 Loading RAM: Original weights (usually FP16) + System reserve
        loading_ram_gb = (model.params * 2) / (1024**3)
        system_reserve_gb = 4.0
        required_ram_gb = round(max(16.0, weight_gb * 1.2, loading_ram_gb + system_reserve_gb), 2)

        # 2. Performance Metrics (Theoretical Workload Intensity)
        # Prefill: 2 * params * prompt_tokens
        # Decoding: 2 * active_params * max_new_tokens
        flops_prefill = 2 * model.params * inference.prompt_tokens
        flops_decoding = 2 * active_params * (inference.context_length - inference.prompt_tokens if inference.context_length else inference.max_new_tokens)
        total_flops = float((flops_prefill + flops_decoding) * inference.batch_size * workload.repeats)

        return ResourceEstimate(
            required_vram_gb=required_vram_gb,
            required_cpu_cores=required_cpu_cores,
            required_ram_gb=required_ram_gb,
            total_flops=total_flops,
            throughput_tokens_per_second=0.0, # Will be calculated by Optimizer based on hardware BW
            throughput_prefill_tps=0.0,
            throughput_decoding_tps=0.0,
            kv_cache_gb=round(kv_cache_gb, 2)
        )

    def _estimate_training(self, workload: Workload) -> ResourceEstimate:
        training = workload.training
        model = workload.model
        precision_bytes = PRECISION_BYTES[training.precision]
        method_factor = METHOD_MULTIPLIER[training.method]

        model_memory_gb = model.params * precision_bytes * method_factor / (1024**3)
        optimizer_overhead_gb = model.params * precision_bytes * TRAINING_OVERHEAD_FACTOR[training.method] / (1024**3)
        
        activation_gb = (
            training.batch_size
            * training.seq_len
            * model.hidden_dim
            * 2
            / (1024**3)
        )
        required_vram_gb = round(model_memory_gb + optimizer_overhead_gb + activation_gb + 2.0, 2)

        required_cpu_cores = max(training.num_workers + 2, 4)
        
        # 1.1 Loading RAM: Original weights (usually FP16) + Buffer for gradients/optimizer
        loading_ram_gb = (model.params * 2) / (1024**3)
        runtime_ram_gb = required_vram_gb * 1.5 + training.batch_size * 2.0
        required_ram_gb = round(max(16.0, runtime_ram_gb, loading_ram_gb + 8.0), 2)
        

        total_tokens = (workload.data.dataset_tokens if workload.data else 0) * training.epochs
        
        # Calculation for MoE: only active experts contribute to FLOPs
        active_params = (model.active_experts / model.num_experts * model.params) if model.num_experts > 0 else model.params
        total_flops = float(6 * active_params * total_tokens * TRAINING_FLOPS_FACTOR[training.method] * workload.repeats)

        return ResourceEstimate(
            required_vram_gb=required_vram_gb,
            required_cpu_cores=required_cpu_cores,
            required_ram_gb=required_ram_gb,
            total_flops=total_flops,
            throughput_tokens_per_second=0.0, # Calculated by Optimizer
            kv_cache_gb=0.0
        )

    @staticmethod
    def _infer_hidden_dim(params: int) -> int:
        if params <= 3_000_000_000:
            return 2560
        if params <= 7_000_000_000:
            return 4096
        if params <= 13_000_000_000:
            return 5120
        if params <= 34_000_000_000:
            return 6656
        return 8192
