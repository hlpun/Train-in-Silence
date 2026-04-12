from __future__ import annotations

import pytest
from tis.planner.estimator import ResourceEstimator
from tis.planner.models import DataSpec, ModelSpec, TrainingSpec, Workload


@pytest.fixture
def estimator() -> ResourceEstimator:
    return ResourceEstimator()


def test_estimate_vram_llama_7b_qlora(estimator: ResourceEstimator) -> None:
    workload = Workload(
        model=ModelSpec(name="llama-7b", params=7_000_000_000),
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
        model=ModelSpec(name="llama-7b", params=7_000_000_000),
        training=TrainingSpec(method="full", precision="fp32", batch_size=1, seq_len=512),
        data=DataSpec(dataset_tokens=1_000_000),
    )
    estimate = estimator.estimate(workload)
    # Full precision: Params(26G) + Grad/Opt(3 * Params * 4 = 78G) = 104G + overhead
    assert estimate.required_vram_gb > 100.0


def test_estimate_flops_count(estimator: ResourceEstimator) -> None:
    workload = Workload(
        model=ModelSpec(name="test", params=1_000_000_000),
        training=TrainingSpec(),
        data=DataSpec(dataset_tokens=1_000_000),
    )
    estimate = estimator.estimate(workload)
    # 6 * params * tokens * factor = 6 * 1e9 * 1e6 * 0.18 (qlora) = 1.08e15
    assert estimate.total_flops == 1_080_000_000_000_000


def test_estimate_required_cpu_ram(estimator: ResourceEstimator) -> None:
    workload = Workload(
        model=ModelSpec(name="test", params=1_000_000),
        training=TrainingSpec(num_workers=8),
        data=DataSpec(dataset_tokens=1000),
    )
    estimate = estimator.estimate(workload)
    assert estimate.required_cpu_cores >= 8
    assert estimate.required_ram_gb >= 1.0


def test_grad_accum_impact(estimator: ResourceEstimator) -> None:
    w1 = Workload(
        model=ModelSpec(name="test", params=1_000_000_000),
        training=TrainingSpec(grad_accum=1),
        data=DataSpec(dataset_tokens=1_000_000),
    )
    w2 = Workload(
        model=ModelSpec(name="test", params=1_000_000_000),
        training=TrainingSpec(grad_accum=8),
        data=DataSpec(dataset_tokens=1_000_000),
    )
    e1 = estimator.estimate(w1)
    e2 = estimator.estimate(w2)
    
    # VRAM should be identical in current model
    assert e1.required_vram_gb == e2.required_vram_gb
    # Throughput should be higher with 8 accum steps (bigger effective batch)
    assert e2.throughput_tokens_per_second > e1.throughput_tokens_per_second
