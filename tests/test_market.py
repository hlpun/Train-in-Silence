from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from tis.planner.market.cache import FileTTLCache
from tis.planner.market import AWSProvider, MarketDataAggregator, RunpodProvider, SampleMarketProvider, VastAIProvider
from tis.planner.models import Constraints


class VastRequester:
    def post_json(self, url: str, headers: dict, json: dict) -> dict:
        assert "Authorization" in headers
        assert url.startswith("https://console.vast.ai/")
        return {
            "offers": [
                {
                    "gpu_name": "RTX_4090",
                    "num_gpus": 1,
                    "gpu_ram": 24576,
                    "dph_total": 0.79,
                    "cpu_cores_effective": 16,
                    "cpu_ram": 65536,
                    "geolocation": "US",
                    "total_flops": 82.6,
                    "machine_id": "offer-123",
                }
            ]
        }


class RunpodRequester:
    def post_json(self, url: str, params: dict, json: dict, headers: dict) -> dict:
        assert url == "https://api.runpod.io/graphql"
        assert params["api_key"] == "runpod-test"
        return {
            "data": {
                "gpuTypes": [
                    {
                        "id": "NVIDIA GeForce RTX 4090",
                        "displayName": "RTX 4090",
                        "memoryInGb": 24,
                        "securePrice": 0.89,
                        "communityPrice": 0.75,
                        "secureSpotPrice": 0.52,
                        "lowestPrice": {
                            "uninterruptablePrice": 0.89,
                            "minimumBidPrice": 0.52,
                            "minVcpu": 8,
                            "minMemory": 32,
                            "stockStatus": "High",
                            "maxUnreservedGpuCount": 4,
                            "availableGpuCounts": [1, 2],
                        },
                    }
                ]
            }
        }


class AWSRequester:
    def get_json(self, url: str) -> dict:
        assert "pricing.us-east-1.amazonaws.com" in url
        return {
            "products": {
                "sku-g5xlarge": {
                    "attributes": {
                        "instanceType": "g5.xlarge",
                        "operatingSystem": "Linux",
                        "preInstalledSw": "NA",
                        "capacitystatus": "Used",
                        "tenancy": "Shared",
                    }
                }
            },
            "terms": {
                "OnDemand": {
                    "sku-g5xlarge": {
                        "term-1": {
                            "priceDimensions": {
                                "dim-1": {
                                    "unit": "Hrs",
                                    "pricePerUnit": {"USD": "1.006"}
                                }
                            }
                        }
                    }
                }
            },
        }


class FailingLiveProvider:
    platform = "vast.ai"

    def fetch(self, constraints: Constraints):
        from tis.planner.market.base import ProviderFetchResult
        from tis.planner.models import ProviderStatus

        return ProviderFetchResult(
            status=ProviderStatus(
                provider="vast.ai",
                source="live",
                ok=False,
                offers_count=0,
                message="Live request failed: network down",
            )
        )


def _cache_dir(name: str) -> Path:
    root = Path("tests/.cache")
    target = root / f"{name}-{uuid.uuid4().hex}"
    if target.exists():
        shutil.rmtree(target)
    return target


def test_vast_provider_maps_live_response() -> None:
    provider = VastAIProvider(
        api_key="vast-test",
        requester=VastRequester(),
        cache=FileTTLCache(_cache_dir("vast")),
    )
    result = provider.fetch(Constraints(platforms=["vast.ai"], region=["us"], max_gpus=2))
    assert result.offers
    assert result.offers[0].gpu == "RTX 4090"
    assert result.offers[0].source == "live"
    assert result.offers[0].is_availability_estimated is False
    assert result.offers[0].instance_type == "offer-123" # Mocked in my requester update
    assert result.status is not None and result.status.ok


def test_runpod_provider_maps_graphql_response() -> None:
    provider = RunpodProvider(
        api_key="runpod-test",
        requester=RunpodRequester(),
        cache=FileTTLCache(_cache_dir("runpod")),
    )
    result = provider.fetch(Constraints(platforms=["runpod"], region=["us"], max_gpus=2))
    assert result.offers
    assert any(offer.spot for offer in result.offers)
    assert result.offers[0].is_region_estimated is True
    assert result.status is not None and result.status.provider == "runpod"


def test_aws_provider_maps_public_price_list() -> None:
    provider = AWSProvider(
        requester=AWSRequester(),
        cache=FileTTLCache(_cache_dir("aws")),
    )
    result = provider.fetch(Constraints(platforms=["aws"], region=["us-east-1"], max_gpus=2))
    assert result.offers
    assert result.offers[0].platform == "aws"
    assert result.offers[0].gpu == "A10G"
    assert result.offers[0].price_per_hour == 1.006
    assert result.offers[0].is_availability_estimated is True
    assert result.offers[0].available_instances == 10


def test_market_aggregator_falls_back_to_sample_and_reports_failure() -> None:
    aggregator = MarketDataAggregator(
        providers=[FailingLiveProvider()],
        fallback_provider=SampleMarketProvider(),
        allow_sample_fallback=True,
    )
    result = aggregator.fetch_market_data(Constraints(platforms=["vast.ai", "runpod"], max_gpus=2))
    assert result.offers
    assert any(status.provider == "vast.ai" and not status.ok for status in result.provider_statuses)
    assert any(status.provider == "sample" and status.source == "sample" for status in result.provider_statuses)


def test_aws_provider_region_expansion() -> None:
    calls = []

    class CapturingRequester:
        def get_json(self, url: str) -> dict:
            calls.append(url)
            return {"products": {}, "terms": {"OnDemand": {}}}

    provider = AWSProvider(requester=CapturingRequester(), cache=FileTTLCache(_cache_dir("aws-expand")))
    provider.fetch(Constraints(platforms=["aws"], region=["us"]))
    
    # Should expand 'us' to at least us-east-1 and us-west-2
    assert any("us-east-1" in c for c in calls)
    assert any("us-west-2" in c for c in calls)
