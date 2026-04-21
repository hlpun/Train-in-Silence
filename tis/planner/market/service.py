from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

# Suppress gpuhunt warnings about missing API keys for optional providers
# (Crusoe, HotAisle, DigitalOcean) - these are not required for TIS functionality
logging.getLogger("gpuhunt._internal.default").setLevel(logging.ERROR)
logging.getLogger("gpuhunt.providers.cudo").setLevel(logging.ERROR)

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


@dataclass
class FetchResult:
    """Container for a single provider fetch result."""
    name: str
    result: ProviderFetchResult | None = None
    error: str | None = None


class MarketDataAggregator:
    def __init__(
        self,
        providers: list[object] | None = None,
        gpuhunt_provider: GPUHuntProvider | None = None,
        universal_provider: GPUFinderProvider | None = None,
        fallback_provider: SampleMarketProvider | None = None,
        allow_sample_fallback: bool | None = None,
        timeout_seconds: float = 20.0,
        max_workers: int = 8,
        parallel_gpuhunt: bool = False,
    ) -> None:
        # AWS Provider disabled by default due to 420MB price list download (~7+ minutes)
        # Users can explicitly enable it by passing providers=[..., AWSProvider()]
        self.providers = providers or [VastAIProvider(), RunpodProvider()]
        self.gpuhunt_provider = gpuhunt_provider or GPUHuntProvider()
        self.universal_provider = universal_provider or GPUFinderProvider()
        self.fallback_provider = fallback_provider or SampleMarketProvider()
        env_value = os.getenv("TIS_ALLOW_SAMPLE_FALLBACK", "true").lower()
        self.allow_sample_fallback = allow_sample_fallback if allow_sample_fallback is not None else env_value != "false"
        self.timeout_seconds = timeout_seconds
        self.max_workers = max_workers
        self.parallel_gpuhunt = parallel_gpuhunt

    def fetch_market_data(self, constraints: Constraints) -> MarketAggregation:
        """Fetch market data from all providers in parallel with overall timeout."""
        provider_statuses: list[ProviderStatus] = []
        requested_platforms = set(constraints.platforms)

        # Build list of providers to fetch
        fetch_tasks: list[tuple[str, Any]] = []

        # 1. Dedicated Providers (Official APIs)
        for provider in self.providers:
            if provider.platform not in requested_platforms:
                continue
            fetch_tasks.append((f"official:{provider.platform}", provider))

        # 2. GPUHunt - either parallel or single query
        if self.parallel_gpuhunt:
            # Share cache and catalog across all GPUHunt provider instances
            shared_cache = self.gpuhunt_provider.cache
            shared_catalog = self.gpuhunt_provider.catalog

            # Pre-load shared gpuhunt catalog before parallel execution
            # This ensures catalog is loaded once, then all queries use it in parallel
            gpuhunt_catalog = self._create_shared_gpuhunt_catalog()
            gpuhunt_catalog.load()  # Pre-load catalog data

            # Split GPUHunt into parallel queries for faster execution
            # Offline providers (from catalog, fast after initial load)
            fetch_tasks.append((
                "gpuhunt:offline",
                GPUHuntProvider(
                    cache=shared_cache,
                    catalog=shared_catalog,
                    providers=GPUHuntProvider.OFFLINE_PROVIDERS,
                    name="gpuhunt:offline",
                    gpuhunt_catalog=gpuhunt_catalog,
                )
            ))
            # Online providers (real-time API calls, slower)
            for online_provider in GPUHuntProvider.ONLINE_PROVIDERS:
                fetch_tasks.append((
                    f"gpuhunt:{online_provider}",
                    GPUHuntProvider(
                        cache=shared_cache,
                        catalog=shared_catalog,
                        providers=[online_provider],
                        name=f"gpuhunt:{online_provider}",
                        gpuhunt_catalog=gpuhunt_catalog,
                    )
                ))
        else:
            # Single GPUHunt query (original behavior)
            fetch_tasks.append(("gpuhunt", self.gpuhunt_provider))

        # 3. Universal Provider (gpufindr.com)
        fetch_tasks.append(("gpufindr", self.universal_provider))

        # Execute all fetches in parallel with timeout
        fetch_results = self._fetch_parallel(fetch_tasks, constraints)

        # Process results
        official_offers: list[MarketOffer] = []
        gpuhunt_offers: list[MarketOffer] = []
        universal_offers: list[MarketOffer] = []

        for fr in fetch_results:
            if fr.result is None:
                # Timeout or error
                if fr.error:
                    provider_statuses.append(ProviderStatus(
                        provider=fr.name,
                        source="live",
                        ok=False,
                        offers_count=0,
                        message=fr.error,
                    ))
                continue

            if fr.result.status is not None:
                provider_statuses.append(fr.result.status)

            if fr.name.startswith("official:"):
                official_offers.extend(fr.result.offers)
            elif fr.name.startswith("gpuhunt"):
                gpuhunt_offers.extend(fr.result.offers)
            elif fr.name == "gpufindr":
                universal_offers = fr.result.offers

        # Dedupe gpuhunt offers (may have duplicates from parallel queries)
        gpuhunt_offers = self._dedupe_gpuhunt_offers(gpuhunt_offers)

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

    def _create_shared_gpuhunt_catalog(self):
        """Create a shared gpuhunt Catalog with online providers attached.

        The catalog.load() will be called on first query, which happens in parallel.
        """
        import gpuhunt._internal.catalog as cat
        import importlib

        # Create catalog (auto_reload=False means we control when to load)
        catalog = cat.Catalog(auto_reload=False)

        # Add online providers that work without extra API keys
        for module_name, provider_name in [
            ("gpuhunt.providers.vastai", "VastAIProvider"),
            ("gpuhunt.providers.cudo", "CudoProvider"),
            ("gpuhunt.providers.vultr", "VultrProvider"),
        ]:
            try:
                mod = importlib.import_module(module_name)
                prov = getattr(mod, provider_name)()
                catalog.add_provider(prov)
            except Exception:
                pass  # Skip providers that fail to load

        return catalog

    @staticmethod
    def _dedupe_gpuhunt_offers(offers: list[MarketOffer]) -> list[MarketOffer]:
        """Dedupe offers from parallel gpuhunt queries, keeping cheapest price."""
        deduped: dict[tuple[str, str, int, str, bool], MarketOffer] = {}
        for offer in offers:
            key = (offer.platform, offer.gpu.lower(), offer.gpu_count, offer.region, offer.spot)
            existing = deduped.get(key)
            if existing is None or offer.price_per_hour < existing.price_per_hour:
                deduped[key] = offer
        return list(deduped.values())

    def _fetch_parallel(
        self,
        tasks: list[tuple[str, Any]],
        constraints: Constraints,
    ) -> list[FetchResult]:
        """Execute provider fetches in parallel with overall timeout."""
        results: list[FetchResult] = []

        def do_fetch(name: str, provider: Any) -> FetchResult:
            try:
                result = provider.fetch(constraints)
                return FetchResult(name=name, result=result)
            except Exception as e:
                return FetchResult(name=name, error=f"Fetch failed: {e}")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(do_fetch, name, provider): name for name, provider in tasks}

            # Wait for all futures with overall timeout
            try:
                for future in as_completed(futures, timeout=self.timeout_seconds):
                    results.append(future.result())
            except TimeoutError:
                # Mark any incomplete tasks as timed out
                completed_names = {fr.name for fr in results}
                for name in futures.values():
                    if name not in completed_names:
                        results.append(FetchResult(
                            name=name,
                            error=f"Timed out after {self.timeout_seconds}s",
                        ))

        return results

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
