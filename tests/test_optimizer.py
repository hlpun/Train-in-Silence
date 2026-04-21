from __future__ import annotations

import pytest
from tis.planner.models import Constraints, MarketOffer, ResourceEstimate, RiskLevel, Workload, InferenceSpec
from tis.planner.optimizer import OptimizerEngine


@pytest.fixture
def optimizer() -> OptimizerEngine:
    return OptimizerEngine()


@pytest.fixture
def basic_estimate() -> ResourceEstimate:
    return ResourceEstimate(
        required_vram_gb=20.0,
        required_cpu_cores=4,
        required_ram_gb=32.0,
        total_flops=1e17,
        throughput_tokens_per_second=100.0,
    )


def test_optimizer_filters_insufficient_vram(optimizer: OptimizerEngine, basic_estimate: ResourceEstimate) -> None:
    offers = [
        MarketOffer(
            gpu="LowVRAM", gpu_count=1, vram_gb=16.0, price_per_hour=0.5,
            cpu=8, ram_gb=64.0, gpu_flops_tflops=10.0, platform="p1", region="r1"
        ),
        MarketOffer(
            gpu="HighVRAM", gpu_count=1, vram_gb=24.0, price_per_hour=1.0,
            cpu=8, ram_gb=64.0, gpu_flops_tflops=10.0, platform="p1", region="r1"
        )
    ]
    recs = optimizer.generate_candidates(basic_estimate, offers, Constraints())
    assert len(recs) == 1
    assert recs[0].config.gpu == "HighVRAM"


def test_optimizer_transparency_notes_and_optimistic_risk(optimizer: OptimizerEngine, basic_estimate: ResourceEstimate) -> None:
    offers = [
        MarketOffer(
            gpu="A100", gpu_count=1, vram_gb=80.0, price_per_hour=2.0,
            cpu=16, ram_gb=128.0, gpu_flops_tflops=312.0, platform="aws", region="us-east-1",
            is_availability_estimated=True # This is a catalog-only offer
        )
    ]
    recs = optimizer.generate_candidates(basic_estimate, offers, Constraints())
    assert len(recs) == 1
    rec = recs[0]

    # Transparency Notes
    assert any("Availability is estimated" in note for note in rec.notes)

    # Optimistic Risk Logic (should be LOW risk even if available_instances is missing/low)
    assert rec.availability.risk == RiskLevel.LOW
    assert rec.availability.score == 0.8


def test_optimizer_pareto_concept(optimizer: OptimizerEngine, basic_estimate: ResourceEstimate) -> None:
    # We test that optimizer generates the raw candidates; the PlannerService actually does the Pareto filtering.
    # But we check that if price is higher it doesn't filter it OUT yet (it's just a candidate).
    offers = [
        MarketOffer(
            gpu="CheapSlow", gpu_count=1, vram_gb=24.0, price_per_hour=0.5,
            cpu=8, ram_gb=64.0, gpu_flops_tflops=10.0, platform="p1", region="r1"
        ),
        MarketOffer(
            gpu="ExpensiveFast", gpu_count=1, vram_gb=24.0, price_per_hour=2.0,
            cpu=8, ram_gb=64.0, gpu_flops_tflops=100.0, platform="p1", region="r1"
        )
    ]
    recs = optimizer.generate_candidates(basic_estimate, offers, Constraints())
    assert len(recs) == 2
def test_optimizer_distributed_tax(optimizer: OptimizerEngine) -> None:
    # Estimate requires 16GB RAM and 4 CPU
    estimate = ResourceEstimate(
        required_vram_gb=40.0, required_cpu_cores=4, required_ram_gb=16.0,
        total_flops=1e15, throughput_tokens_per_second=0
    )
    
    # Offer has exactly 16GB RAM and 4 CPU but has 2 GPUs
    # This should FAIL because of distributed tax:
    # Tax = (2-1)*2 = 2 CPU, so 4+2=6 required
    # Tax = 2*2 = 4 RAM, so 16+4=20 required
    offer_multi = MarketOffer(
        gpu="A100", gpu_count=2, vram_gb=40.0, price_per_hour=2.0,
        cpu=5, ram_gb=18.0, # Not enough for tax
        gpu_flops_tflops=312.0, platform="p1", region="r1"
    )
    
    recs = optimizer.generate_candidates(estimate, [offer_multi], Constraints())
    assert len(recs) == 0


def test_optimizer_inference_tps_logic(optimizer: OptimizerEngine, llama3_model) -> None:
    # 8B model, FP16 -> 16GB.
    # Bandwidth bound test.
    workload = Workload(
        model=llama3_model,
        inference=InferenceSpec(precision="fp16", batch_size=1, prompt_tokens=100, max_new_tokens=10000)
    )
    estimate = ResourceEstimate(
        required_vram_gb=18.0, required_cpu_cores=2, required_ram_gb=32.0,
        total_flops=0, throughput_tokens_per_second=0
    )

    # Offer 1: Slow bandwidth (RTX 4090 ~1TB/s)
    # Offer 2: Fast bandwidth (H100 ~3.3TB/s)
    o1 = MarketOffer(
        gpu="4090", gpu_count=1, vram_gb=24.0, price_per_hour=0.7,
        cpu=16, ram_gb=64.0, gpu_flops_tflops=82.0, memory_bw_gbps=1000.0,
        platform="p1", region="r1", source="live"
    )
    o2 = MarketOffer(
        gpu="H100", gpu_count=1, vram_gb=80.0, price_per_hour=3.0,
        cpu=16, ram_gb=64.0, gpu_flops_tflops=989.0, memory_bw_gbps=3350.0,
        platform="p1", region="r1", source="live"
    )

    recs = optimizer.generate_candidates(estimate, [o1, o2], Constraints(), workload=workload)
    assert len(recs) == 2

    # H100 should be faster due to higher bandwidth
    tps_4090 = recs[0].metrics.time_hours
    tps_h100 = recs[1].metrics.time_hours
    assert tps_h100 < tps_4090
