from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

from tis.planner.market.cache import FileTTLCache
from tis.planner.market.providers import GPUHuntProvider, VastAIProvider, GPUFinderProvider
from tis.planner.market.service import MarketDataAggregator
from tis.planner.models import Constraints, MarketOffer

class MockGPUHuntOffer:
    def __init__(self, **kwargs):
        self.instance_name = kwargs.get("instance_name", "test-instance")
        self.provider = kwargs.get("provider", "lambda")
        self.location = kwargs.get("location", "us")
        self.cpu = kwargs.get("cpu", 64)
        self.memory = kwargs.get("memory", 128)
        self.gpu_count = kwargs.get("gpu_count", 1)
        self.gpu_name = kwargs.get("gpu_name", "A100")
        self.gpu_memory = kwargs.get("gpu_memory", 80)
        self.price = kwargs.get("price", 1.25)
        self.spot = kwargs.get("spot", False)

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

class MockGPUFinderRequester:
    def get_json(self, url: str, params: dict) -> list[dict]:
        return [
            {
                "id": "finder-1",
                "source": "lambda", # Exists in gpuhunt too
                "location": "us",
                "name": "A100",
                "vram_mb": 81920,
                "num_gpus": 1,
                "cpu_cores": 2, # Low detail compared to gpuhunt
                "ram_mb": 4096,
                "total_cost_ph": 1.29,
                "total_flops": 156,
            }
        ]

def _cache_dir(name: str) -> Path:
    root = Path("tests/.cache")
    target = root / f"{name}-{uuid.uuid4().hex}"
    return target

def test_gpuhunt_provider_mapping() -> None:
    import tis.planner.market.providers as providers
    providers.gpuhunt = MagicMock()
    providers.gpuhunt.query.return_value = [
        MockGPUHuntOffer(provider="lambda", gpu_name="A100", price=1.25, cpu=64)
    ]
    
    provider = GPUHuntProvider(cache=FileTTLCache(_cache_dir("gpuhunt-unit")))
    result = provider.fetch(Constraints(platforms=["lambda"], max_gpus=1))
    
    assert result.offers
    offer = result.offers[0]
    assert offer.platform == "lambda"
    assert offer.cpu == 64
    assert offer.source_detail == "live:gpuhunt"

def test_aggregator_3_layer_merging() -> None:
    import tis.planner.market.providers as providers
    providers.gpuhunt = MagicMock()
    
    # gpuhunt returns A100 (Lambda) and RTX 4090 (Vast)
    providers.gpuhunt.query.return_value = [
        MockGPUHuntOffer(provider="lambda", gpu_name="A100", price=1.20, cpu=64, ram_memory=256),
        MockGPUHuntOffer(provider="vastai", gpu_name="RTX 4090", price=0.79, cpu=32, location="us"),
    ]
    
    vast = VastAIProvider(
        api_key="test",
        requester=MockVastRequester(),
        cache=FileTTLCache(_cache_dir("3layer-vast")),
    )
    finder = GPUFinderProvider(
        requester=MockGPUFinderRequester(),
        cache=FileTTLCache(_cache_dir("3layer-finder")),
    )
    hunt = GPUHuntProvider(cache=FileTTLCache(_cache_dir("3layer-hunt")))
    
    aggregator = MarketDataAggregator(
        providers=[vast],
        gpuhunt_provider=hunt,
        universal_provider=finder,
        allow_sample_fallback=False
    )
    
    result = aggregator.fetch_market_data(Constraints(platforms=["vast.ai", "lambda"]))
    
    # 1. Vast should be supplemented by GPUHunt
    vast_offer = next(o for o in result.offers if o.platform == "vast.ai")
    assert vast_offer.price_per_hour == 0.75 # Official price wins
    assert vast_offer.cpu == 32              # Supplemented from gpuhunt (32 > 4)
    assert vast_offer.source_detail == "live:official+supplemented"
    
    # 2. Lambda should come from GPUHunt (Higher priority than Finder)
    lambda_offer = next(o for o in result.offers if o.platform == "lambda")
    assert lambda_offer.price_per_hour == 1.20 # gpuhunt price
    assert lambda_offer.cpu == 64              # gpuhunt cpu
    assert lambda_offer.source_detail == "live:gpuhunt"
    # It should NOT be supplemented by Finder if GPUHunt already had better detail
    # Finder has cpu=2, GPUHunt has cpu=64
