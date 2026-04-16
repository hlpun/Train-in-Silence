from __future__ import annotations

import os
import pytest
from tis.planner.market.providers import VastAIProvider, RunpodProvider, AWSProvider, GPUFinderProvider
from tis.planner.models import Constraints

@pytest.mark.vcr
def test_vast_ai_live_fetch():
    # This test will record real interaction if VAST_API_KEY is set.
    # Otherwise it uses the recorded cassette.
    api_key = os.getenv("VAST_API_KEY", "pseudo-key")
    provider = VastAIProvider(api_key=api_key)
    
    # We use a broad constraint to ensure we get some results
    constraints = Constraints(platforms=["vast.ai"], max_gpus=1)
    result = provider.fetch(constraints)
    
    # Assertions on the structure of the live response mapping
    assert result.status.ok or "Skipped" in result.status.message
    if result.offers:
        offer = result.offers[0]
        assert offer.platform == "vast.ai"
        assert offer.price_per_hour > 0
        assert offer.gpu_flops_tflops >= 0

@pytest.mark.vcr
def test_runpod_live_fetch():
    api_key = os.getenv("RUNPOD_API_KEY", "pseudo-key")
    provider = RunpodProvider(api_key=api_key)
    
    constraints = Constraints(platforms=["runpod"], max_gpus=2)
    result = provider.fetch(constraints)
    
    assert result.status.ok or "Skipped" in result.status.message
    if result.offers:
        assert any(o.platform == "runpod" for o in result.offers)

@pytest.mark.vcr
def test_aws_public_price_list_fetch():
    # AWS doesn't require keys for the public price list
    provider = AWSProvider()
    constraints = Constraints(platforms=["aws"], region=["us-east-1"], max_gpus=1)
    result = provider.fetch(constraints)
    
    assert result.status.ok
    assert len(result.offers) > 0
    assert result.offers[0].platform == "aws"

@pytest.mark.vcr
def test_gpufinder_live_fetch():
    provider = GPUFinderProvider()
    constraints = Constraints(platforms=["lambda"], max_gpus=1)
    result = provider.fetch(constraints)
    
    assert result.status.ok
    if result.offers:
        assert any("lambda" in o.platform.lower() for o in result.offers)
