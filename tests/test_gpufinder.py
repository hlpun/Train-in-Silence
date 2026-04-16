from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from tis.planner.market.cache import FileTTLCache
from tis.planner.market.providers import GPUFinderProvider, VastAIProvider
from tis.planner.market.service import MarketDataAggregator
from tis.planner.models import Constraints, MarketOffer


class MockGPUFinderRequester:
    def get_json(self, url: str, params: dict) -> list[dict]:
        return [
            {
                "id": "lambda-1",
                "source": "lambda",
                "location": "us-east-1",
                "name": "A100-80GB",
                "vram_mb": 81920,
                "num_gpus": 1,
                "cpu_cores": 64,
                "ram_mb": 458752,
                "total_cost_ph": 1.29,
                "total_flops": 156,
            },
            {
                "id": "runpod-1",
                "source": "runpod",
                "location": "us-west",
                "name": "RTX 4090",
                "vram_mb": 24576,
                "num_gpus": 1,
                "cpu_cores": 32,
                "ram_mb": 131072,
                "total_cost_ph": 0.69,
                "total_flops": 82,
            },
            {
                "id": "vast-1",
                "source": "vast.ai",
                "location": "us",
                "name": "RTX 4090",
                "vram_mb": 24576,
                "num_gpus": 1,
                "cpu_cores": 32,
                "ram_mb": 131072,
                "total_cost_ph": 0.79, # Different price, but match is on GPU/Platform/Region
                "total_flops": 82,
            }
        ]


class MockVastRequester:
    def post_json(self, url: str, headers: dict, json: dict) -> dict:
        return {
            "offers": [
                {
                    "gpu_name": "RTX 4090",
                    "num_gpus": 1,
                    "gpu_ram": 24576,
                    "dph_total": 0.75,
                    "cpu_cores_effective": 4, # Low detail
                    "cpu_ram": 16384,         # Low detail
                    "geolocation": "Oregon, US",
                    "total_flops": 0,         # Missing
                    "machine_id": "vast-4090",
                }
            ]
        }


def _cache_dir(name: str) -> Path:
    root = Path("tests/.cache")
    target = root / f"{name}-{uuid.uuid4().hex}"
    return target


def test_gpufinder_provider_fetches_and_maps() -> None:
    provider = GPUFinderProvider(
        requester=MockGPUFinderRequester(),
        cache=FileTTLCache(_cache_dir("gpufinder-unit")),
    )
    result = provider.fetch(Constraints(platforms=["lambda"], max_gpus=1))
    assert result.offers
    offer = next(o for o in result.offers if o.platform == "lambda")
    assert "A100" in offer.gpu
    assert offer.price_per_hour == 1.29
    assert offer.source_detail == "live:gpufindr"
    assert offer.cpu == 64


def test_aggregator_hierarchical_merge_and_supplement() -> None:
    vast = VastAIProvider(
        api_key="test",
        requester=MockVastRequester(),
        cache=FileTTLCache(_cache_dir("agg-vast")),
    )
    finder = GPUFinderProvider(
        requester=MockGPUFinderRequester(),
        cache=FileTTLCache(_cache_dir("agg-finder")),
    )
    
    aggregator = MarketDataAggregator(
        providers=[vast],
        universal_provider=finder,
        allow_sample_fallback=False
    )
    
    # RunPod is not in providers, but in Finder -> Keyless Fallback
    # Vast is in both -> Supplementation
    result = aggregator.fetch_market_data(Constraints(platforms=["vast.ai", "runpod", "lambda"]))
    
    # 1. Check Keyless Fallback (Lambda/RunPod)
    assert any(o.platform == "lambda" for o in result.offers)
    assert any(o.platform == "runpod" for o in result.offers)
    
    # 2. Check Supplementation (Vast)
    vast_offer = next(o for o in result.offers if o.platform == "vast.ai")
    assert vast_offer.price_per_hour == 0.75 # Kept official price
    assert vast_offer.cpu == 32              # Supplemented from gpufindr (32 > 4)
    assert vast_offer.gpu_flops_tflops == 82.6 # Already resolved from catalog in VastAIProvider
    assert vast_offer.source_detail == "live:official+supplemented"
