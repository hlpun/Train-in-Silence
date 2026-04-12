from __future__ import annotations

import pytest
from tis.planner.models import Constraints, MarketOffer, ResourceEstimate, RiskLevel
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
    # Ensure time is calculated correctly (ExpensiveFast is faster)
    assert recs[1].metrics.time_hours < recs[0].metrics.time_hours
