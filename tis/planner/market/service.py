from __future__ import annotations

import os

from tis.planner.market.base import ProviderFetchResult
from tis.planner.market.providers import (
    AWSProvider,
    GPUFinderProvider,
    GPUHuntProvider,
    RunpodProvider,
    SampleMarketProvider,
    VastAIProvider,
)
from tis.planner.models import Constraints, MarketAggregation, MarketOffer, ProviderStatus


class MarketDataAggregator:
    def __init__(
        self,
        providers: list[object] | None = None,
        gpuhunt_provider: GPUHuntProvider | None = None,
        universal_provider: GPUFinderProvider | None = None,
        fallback_provider: SampleMarketProvider | None = None,
        allow_sample_fallback: bool | None = None,
    ) -> None:
        self.providers = providers or [VastAIProvider(), RunpodProvider(), AWSProvider()]
        self.gpuhunt_provider = gpuhunt_provider or GPUHuntProvider()
        self.universal_provider = universal_provider or GPUFinderProvider()
        self.fallback_provider = fallback_provider or SampleMarketProvider()
        env_value = os.getenv("TIS_ALLOW_SAMPLE_FALLBACK", "true").lower()
        self.allow_sample_fallback = allow_sample_fallback if allow_sample_fallback is not None else env_value != "false"

    def fetch_market_data(self, constraints: Constraints) -> MarketAggregation:
        official_offers: list[MarketOffer] = []
        provider_statuses: list[ProviderStatus] = []
        requested_platforms = set(constraints.platforms)

        # 1. Fetch from Dedicated Providers (Official APIs)
        for provider in self.providers:
            if provider.platform not in requested_platforms:
                continue
            result: ProviderFetchResult = provider.fetch(constraints)
            if result.status is not None:
                provider_statuses.append(result.status)
            official_offers.extend(result.offers)

        # 2. Fetch from GPUHunt (High-priority Aggregator)
        gpuhunt_result = self.gpuhunt_provider.fetch(constraints)
        if gpuhunt_result.status:
            provider_statuses.append(gpuhunt_result.status)
        gpuhunt_offers = gpuhunt_result.offers

        # 3. Fetch from Universal Provider (gpufindr.com)
        universal_result = self.universal_provider.fetch(constraints)
        if universal_result.status:
            provider_statuses.append(universal_result.status)
        universal_offers = universal_result.offers

        # 4. Hierarchical Merging
        # Layer 1 + 2: Official supplemented/added by GPUHunt
        base_offers = self._merge_offers(official_offers, gpuhunt_offers, requested_platforms)
        # Layer 1/2 + 3: Result supplemented/added by GPUFinder
        final_offers = self._merge_offers(base_offers, universal_offers, requested_platforms)

        # 5. Final Fallback to Sample Data
        if not final_offers and self.allow_sample_fallback:
            fallback = self.fallback_provider.fetch(constraints)
            if fallback.status is not None:
                provider_statuses.append(fallback.status)
            for offer in fallback.offers:
                offer.source_detail = "sample"
            return MarketAggregation(offers=fallback.offers, provider_statuses=provider_statuses)

        return MarketAggregation(offers=final_offers, provider_statuses=provider_statuses)

    def _merge_offers(
        self,
        base: list[MarketOffer],
        supplemental: list[MarketOffer],
        requested_platforms: set[str],
    ) -> list[MarketOffer]:
        """
        Hierarchical merging:
        - Use 'base' as ground truth if available.
        - Supplement missing details from 'supplemental'.
        - Add platforms from 'supplemental' that aren't in 'base'.
        """
        # Group base offers for easy lookup
        # Key: (platform, gpu, count, region, spot)
        base_map: dict[tuple[str, str, int, str, bool], MarketOffer] = {
            (o.platform, o.gpu.lower(), o.gpu_count, o.region, o.spot): o for o in base
        }
        
        final_list: list[MarketOffer] = list(base)
        
        for s_offer in supplemental:
            # Skip if platform not requested
            if s_offer.platform not in requested_platforms:
                continue
                
            key = (s_offer.platform, s_offer.gpu.lower(), s_offer.gpu_count, s_offer.region, s_offer.spot)
            
            if key in base_map:
                # SUPPLEMENT Logic: Base exists, check if supplemental has better specs
                off = base_map[key]
                supplemented = False
                
                # If base has low detail and supplemental has more
                if off.cpu < s_offer.cpu:
                    off.cpu = s_offer.cpu
                    supplemented = True
                if off.ram_gb < s_offer.ram_gb:
                    off.ram_gb = s_offer.ram_gb
                    supplemented = True
                
                # Always trust supplemental TFLOPS if base is missing it (<= 0)
                if s_offer.gpu_flops_tflops > 0 and off.gpu_flops_tflops <= 0:
                    off.gpu_flops_tflops = s_offer.gpu_flops_tflops
                    supplemented = True
                
                if supplemented and "supplemented" not in off.source_detail:
                    off.source_detail += "+supplemented"
            else:
                # ADD Logic: New entry from supplemental layer
                final_list.append(s_offer)
                base_map[key] = s_offer # For multi-instance matches if any

        return final_list
