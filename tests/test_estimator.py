from __future__ import annotations

import pytest
from tis.planner.estimator import ResourceEstimator
from tis.planner.models import DataSpec, ModelSpec, TrainingSpec, InferenceSpec, Workload


@pytest.fixture
def estimator() -> ResourceEstimator:
    return ResourceEstimator()


def test_estimate_vram_llama_7b_qlora(estimator: ResourceEstimator) -> None:
    workload = Workload(
        model=ModelSpec(
            name="llama-7b", params=7_000_000_000, 
            hidden_dim=4096, num_layers=32, num_heads=32, num_kv_heads=8
        ),
        training=TrainingSpec(method="qlora", precision="bf16", batch_size=4, seq_len=512),
        data=DataSpec(dataset_tokens=1_000_000),
    )
    estimate = estimator.estimate(workload)
    # 7B params in 4-bit (qlora) is roughly 3.5GB. 
    # Plus gradients and optimizer states (0.3 * params * 2 bytes = 4.2GB).
    # Total ~ 7.7GB + base overhead.
    assert 5.0 < estimate.required_vram_gb < 15.0


def test_estimate_vram_llama_7b_full(estimator: ResourceEstimator) -> None:
    workload = Workload(
        model=ModelSpec(
            name="llama-7b", params=7_000_000_000,
            hidden_dim=4096, num_layers=32, num_heads=32, num_kv_heads=8
        ),
        training=TrainingSpec(method="full", precision="fp32", batch_size=1, seq_len=512),
        data=DataSpec(dataset_tokens=1_000_000),
    )
    estimate = estimator.estimate(workload)
    # Full precision: Params(26G) + Grad/Opt(3 * Params * 4 = 78G) = 104G + overhead
    assert estimate.required_vram_gb > 100.0


def test_estimate_flops_count(estimator: ResourceEstimator) -> None:
    workload = Workload(
        model=ModelSpec(
            name="test", params=1_000_000_000,
            hidden_dim=2560, num_layers=24, num_heads=16, num_kv_heads=16
        ),
        training=TrainingSpec(),
        data=DataSpec(dataset_tokens=1_000_000),
    )
    estimate = estimator.estimate(workload)
    # 6 * params * tokens * factor = 6 * 1e9 * 1e6 * 0.18 (qlora) = 1.08e15
    assert estimate.total_flops == 1_080_000_000_000_000


def test_estimate_required_cpu_ram(estimator: ResourceEstimator) -> None:
    workload = Workload(
        model=ModelSpec(
            name="test", params=1_000_000,
            hidden_dim=128, num_layers=2, num_heads=2, num_kv_heads=2
        ),
        training=TrainingSpec(num_workers=8),
        data=DataSpec(dataset_tokens=1000),
    )
    estimate = estimator.estimate(workload)
    assert estimate.required_cpu_cores >= 8
    assert estimate.required_ram_gb >= 1.0


def test_grad_accum_impact(estimator: ResourceEstimator) -> None:
    w1 = Workload(
        model=ModelSpec(
            name="test", params=1_000_000_000,
            hidden_dim=2560, num_layers=24, num_heads=16, num_kv_heads=16
        ),
        training=TrainingSpec(grad_accum=1),
        data=DataSpec(dataset_tokens=1_000_000),
    )
    w2 = Workload(
        model=ModelSpec(
            name="test", params=1_000_000_000,
            hidden_dim=2560, num_layers=24, num_heads=16, num_kv_heads=16
        ),
        training=TrainingSpec(grad_accum=8),
        data=DataSpec(dataset_tokens=1_000_000),
    )
    e1 = estimator.estimate(w1)
    e2 = estimator.estimate(w2)
    
    # VRAM should be identical in current model
    assert e1.required_vram_gb == e2.required_vram_gb
def test_estimate_vram_deepseek_moe(estimator: ResourceEstimator, deepseek_v3_moe) -> None:
    workload = Workload(
        model=deepseek_v3_moe,
        inference=InferenceSpec(precision="int4", batch_size=1, prompt_tokens=512, max_new_tokens=1)
    )
    estimate = estimator.estimate(workload)
    
    # DeepSeek-V3 has 671B total params, but only 37B active.
    # In 4-bit (int4), total weights are ~335GB.
    # Active weights are much smaller, but total weights must be in VRAM for fast switching.
    assert estimate.required_vram_gb > 300.0
    
    # 2 * 671e9 * 513 = 6.878e14
    assert 6.0e14 < estimate.total_flops < 8.0e14


def test_estimate_pipeline_aggregation(estimator: ResourceEstimator, llama3_model) -> None:
    # 2-stage pipeline: Training then Inference
    w1 = Workload(
        model=llama3_model,
        training=TrainingSpec(method="lora", precision="bf16", batch_size=4, seq_len=1024),
        data=DataSpec(dataset_tokens=1000)
    )
    w2 = Workload(
        model=llama3_model,
        inference=InferenceSpec(precision="fp16", batch_size=8, prompt_tokens=100, max_new_tokens=128)
    )
    
    estimate = estimator.estimate([w1, w2])
    
    # VRAM should be the max of the two stages
    e1 = estimator.estimate(w1)
    e2 = estimator.estimate(w2)
    assert estimate.required_vram_gb == max(e1.required_vram_gb, e2.required_vram_gb)
    
    # FLOPS should be the sum
    assert estimate.total_flops == e1.total_flops + e2.total_flops
    assert estimate.stage_details is not None
    assert len(estimate.stage_details) == 2
