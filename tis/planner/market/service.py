from __future__ import annotations

import os

from tis.planner.market.base import ProviderFetchResult
from tis.planner.market.providers import AWSProvider, RunpodProvider, SampleMarketProvider, VastAIProvider
from tis.planner.models import Constraints, MarketAggregation, ProviderStatus


class MarketDataAggregator:
    def __init__(
        self,
        providers: list[object] | None = None,
        fallback_provider: SampleMarketProvider | None = None,
        allow_sample_fallback: bool | None = None,
    ) -> None:
        self.providers = providers or [VastAIProvider(), RunpodProvider(), AWSProvider()]
        self.fallback_provider = fallback_provider or SampleMarketProvider()
        env_value = os.getenv("TIS_ALLOW_SAMPLE_FALLBACK", "true").lower()
        self.allow_sample_fallback = allow_sample_fallback if allow_sample_fallback is not None else env_value != "false"

    def fetch_market_data(self, constraints: Constraints) -> MarketAggregation:
        offers = []
        provider_statuses: list[ProviderStatus] = []
        requested_platforms = set(constraints.platforms)

        for provider in self.providers:
            if provider.platform not in requested_platforms:
                provider_statuses.append(
                    ProviderStatus(
                        provider=provider.platform,
                        source="live",
                        ok=False,
                        offers_count=0,
                        message="Skipped because provider was not requested.",
                    )
                )
                continue
            result: ProviderFetchResult = provider.fetch(constraints)
            if result.status is not None:
                provider_statuses.append(result.status)
            offers.extend(result.offers)

        if offers:
            return MarketAggregation(offers=offers, provider_statuses=provider_statuses)

        if self.allow_sample_fallback:
            fallback = self.fallback_provider.fetch(constraints)
            if fallback.status is not None:
                provider_statuses.append(fallback.status)
            return MarketAggregation(offers=fallback.offers, provider_statuses=provider_statuses)

        return MarketAggregation(offers=[], provider_statuses=provider_statuses)
