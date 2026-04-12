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
    "lora": 0.3,
    "qlora": 0.18,
}


class ResourceEstimator:
    """Heuristic estimator for MVP use cases."""

    def estimate(self, workload: Workload) -> ResourceEstimate:
        training = workload.training
        model = workload.model
        precision_bytes = PRECISION_BYTES[training.precision]
        method_factor = METHOD_MULTIPLIER[training.method]
        hidden_dim = model.hidden_dim or self._infer_hidden_dim(model.params)

        model_memory_gb = model.params * precision_bytes * method_factor / (1024**3)
        # Non-model overhead: Gradients and Optimizer states
        optimizer_overhead_gb = model.params * precision_bytes * TRAINING_OVERHEAD_FACTOR[training.method] / (1024**3)
        
        activation_gb = (
            training.batch_size
            * training.seq_len
            * hidden_dim
            * 2
            / (1024**3)
        )
        required_vram_gb = round(model_memory_gb + optimizer_overhead_gb + activation_gb + 2.0, 2)

        required_cpu_cores = max(training.num_workers + 2, 4)
        required_ram_gb = round(max(16.0, required_vram_gb * 1.5 + training.batch_size * 2.0), 2)

        total_tokens = workload.data.dataset_tokens * training.epochs
        total_flops = float(6 * model.params * total_tokens * TRAINING_FLOPS_FACTOR[training.method])
        throughput_tokens_per_second = max(
            32.0,
            (hidden_dim * training.batch_size * training.grad_accum) / 32.0,
        )

        return ResourceEstimate(
            required_vram_gb=required_vram_gb,
            required_cpu_cores=required_cpu_cores,
            required_ram_gb=required_ram_gb,
            total_flops=total_flops,
            throughput_tokens_per_second=throughput_tokens_per_second,
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
