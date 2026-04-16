from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from tis.planner.market.base import ProviderFetchResult
from tis.planner.market.cache import FileTTLCache
from tis.planner.market.catalog import AWSSpecCatalog, GPUSpecCatalog
from tis.planner.market.http import HTTPRequester, RequestPolicy
from tis.planner.models import Constraints, MarketOffer, ProviderStatus

try:
    import gpuhunt
except ImportError:
    gpuhunt = None

VAST_OFFERS_URL = "https://console.vast.ai/api/v0/bundles/"
RUNPOD_GRAPHQL_URL = "https://api.runpod.io/graphql"
AWS_PRICE_LIST_URL_TEMPLATE = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/{region}/index.json"
GPUFINDER_URL = "https://gpufindr.com/gpus"


@dataclass
class ProviderAuth:
    env_var: str
    explicit_value: str | None = None
    required: bool = True

    def value(self) -> str | None:
        return self.explicit_value or os.getenv(self.env_var)

    def is_enabled(self) -> bool:
        if not self.required:
            return True
        return bool(self.value())


class SampleMarketProvider:
    platform = "sample"

    def __init__(self, data_path: str | None = None) -> None:
        from pathlib import Path
        import json

        base = Path(__file__).resolve().parents[2]
        self._data_path = Path(data_path) if data_path else base / "data" / "gpu_offers.json"
        self._json = json

    def fetch(self, constraints: Constraints) -> ProviderFetchResult:
        payload = self._json.loads(self._data_path.read_text(encoding="utf-8"))
        offers = [MarketOffer.model_validate(item) for item in payload]
        for offer in offers:
            offer.source_detail = "sample"
        offers = _apply_constraints(offers, constraints)
        return ProviderFetchResult(
            offers=offers,
            status=ProviderStatus(
                provider="sample",
                source="sample",
                ok=True,
                offers_count=len(offers),
                message="Loaded bundled sample offers.",
            ),
        )


class VastAIProvider:
    platform = "vast.ai"

    def __init__(
        self,
        api_key: str | None = None,
        requester: HTTPRequester | None = None,
        cache: FileTTLCache | None = None,
        catalog: GPUSpecCatalog | None = None,
    ) -> None:
        self.auth = ProviderAuth("VAST_API_KEY", api_key, required=True)
        self.requester = requester or HTTPRequester(RequestPolicy(timeout_seconds=15.0))
        self.cache = cache or FileTTLCache(ttl_seconds=300)
        self.catalog = catalog or GPUSpecCatalog()

    def fetch(self, constraints: Constraints) -> ProviderFetchResult:
        if not self.auth.is_enabled():
            return ProviderFetchResult(
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=False,
                    offers_count=0,
                    message="Skipped because VAST_API_KEY is not configured.",
                )
            )

        cache_key = f"vast:{','.join(sorted(constraints.region))}:{constraints.max_gpus}"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            offers = [MarketOffer.model_validate(item) for item in cached]
            offers = _apply_constraints(offers, constraints)
            return ProviderFetchResult(
                offers=offers,
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=True,
                    offers_count=len(offers),
                    message="Loaded live offers from persistent cache.",
                ),
            )

        headers = {
            "Authorization": f"Bearer {self.auth.value()}",
            "Content-Type": "application/json",
        }
        body: dict[str, object] = {
            "limit": 100,
            "type": "on-demand",
            "verified": {"eq": True},
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "num_gpus": {"gte": 1, "lte": constraints.max_gpus},
        }
        if constraints.region:
            body["geolocation"] = {"in": [region.upper() for region in constraints.region]}

        try:
            payload = self.requester.post_json(VAST_OFFERS_URL, headers=headers, json=body)
            raw_offers = payload.get("offers", []) if isinstance(payload, dict) else []
            if isinstance(raw_offers, dict):
                raw_offers = [raw_offers]

            offers: list[MarketOffer] = []
            for item in raw_offers:
                gpu_name = str(item.get("gpu_name") or item.get("gpu_display_name") or "unknown")
                resolved_gpu = self.catalog.resolve_name(gpu_name)
                vram_gb = float(item.get("gpu_ram", 0)) / 1024.0
                total_price = float(item.get("dph_total") or item.get("dph_base") or 0.0)
                cpu = int(item.get("cpu_cores_effective") or item.get("cpu_cores") or 0)
                ram_gb = float(item.get("cpu_ram", 0)) / 1024.0
                if total_price <= 0 or vram_gb <= 0 or cpu <= 0 or ram_gb <= 0:
                    continue
                offers.append(
                    MarketOffer(
                        gpu=resolved_gpu,
                        gpu_count=int(item.get("num_gpus") or 1),
                        vram_gb=round(vram_gb, 2),
                        price_per_hour=round(total_price, 4),
                        cpu=cpu,
                        ram_gb=round(ram_gb, 2),
                        gpu_flops_tflops=float(item.get("total_flops") or self.catalog.flops_for(gpu_name)),
                        memory_bw_gbps=self.catalog.bandwidth_for(gpu_name),
                        platform=self.platform,
                        region=_vast_region_label(str(item.get("geolocation") or item.get("country") or "global")),
                        source="live",
                        source_detail="live:official",
                        spot=False,
                        available_instances=int(item.get("num_gpus") or 1), # Vast lists individual machine offers
                        is_availability_estimated=False,
                        instance_type=str(item.get("machine_id") or ""),
                    )
                )

            offers = _dedupe_offers(_apply_constraints(offers, constraints))
            self.cache.set_json(cache_key, [item.model_dump(mode="json") for item in offers])
            return ProviderFetchResult(
                offers=offers,
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=True,
                    offers_count=len(offers),
                    message="Fetched live offers from Vast.ai.",
                ),
            )
        except (httpx.HTTPError, ValueError) as exc:
            return ProviderFetchResult(
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=False,
                    offers_count=0,
                    message=f"Live request failed: {exc}",
                )
            )


class RunpodProvider:
    platform = "runpod"

    def __init__(
        self,
        api_key: str | None = None,
        requester: HTTPRequester | None = None,
        cache: FileTTLCache | None = None,
        catalog: GPUSpecCatalog | None = None,
    ) -> None:
        self.auth = ProviderAuth("RUNPOD_API_KEY", api_key, required=True)
        self.requester = requester or HTTPRequester(RequestPolicy(timeout_seconds=15.0))
        self.cache = cache or FileTTLCache(ttl_seconds=300)
        self.catalog = catalog or GPUSpecCatalog()

    def fetch(self, constraints: Constraints) -> ProviderFetchResult:
        if not self.auth.is_enabled():
            return ProviderFetchResult(
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=False,
                    offers_count=0,
                    message="Skipped because RUNPOD_API_KEY is not configured.",
                )
            )

        cache_key = f"runpod:{','.join(sorted(constraints.region))}:{constraints.max_gpus}"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            offers = [MarketOffer.model_validate(item) for item in cached]
            offers = _apply_constraints(offers, constraints)
            return ProviderFetchResult(
                offers=offers,
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=True,
                    offers_count=len(offers),
                    message="Loaded live offers from persistent cache.",
                ),
            )

        query = """
        query GpuTypes {
          gpuTypes {
            id
            displayName
            memoryInGb
            securePrice
            communityPrice
            secureSpotPrice
            lowestPrice(input: {
              gpuCount: 1,
              minDisk: 0,
              minMemoryInGb: 8,
              minVcpuCount: 2,
              secureCloud: true
            }) {
              uninterruptablePrice
              minimumBidPrice
              minVcpu
              minMemory
              stockStatus
              maxUnreservedGpuCount
              availableGpuCounts
            }
          }
        }
        """
        try:
            payload = self.requester.post_json(
                RUNPOD_GRAPHQL_URL,
                params={"api_key": self.auth.value()},
                json={"query": query},
                headers={"content-type": "application/json"},
            )
            raw_types = payload.get("data", {}).get("gpuTypes", []) if isinstance(payload, dict) else []
            offers: list[MarketOffer] = []
            for item in raw_types:
                name = str(item.get("displayName") or item.get("id") or "unknown")
                resolved_gpu = self.catalog.resolve_name(name)
                memory = float(item.get("memoryInGb") or self.catalog.vram_for(name, 0.0) or 0.0)
                lowest_price = item.get("lowestPrice") or {}
                available_gpu_counts = lowest_price.get("availableGpuCounts") or [1]
                max_unreserved = int(lowest_price.get("maxUnreservedGpuCount") or 1)
                for gpu_count in available_gpu_counts:
                    if not isinstance(gpu_count, int) or gpu_count <= 0 or gpu_count > constraints.max_gpus:
                        continue
                    candidates = [
                        (lowest_price.get("uninterruptablePrice") or item.get("securePrice"), False),
                        (item.get("communityPrice"), False),
                        (lowest_price.get("minimumBidPrice") or item.get("secureSpotPrice"), True),
                    ]
                    for price, is_spot in candidates:
                        if price is None or float(price) <= 0:
                            continue
                        offers.append(
                            MarketOffer(
                                gpu=resolved_gpu,
                                gpu_count=gpu_count,
                                vram_gb=memory,
                                price_per_hour=round(float(price) * gpu_count, 4),
                                cpu=int(lowest_price.get("minVcpu") or max(4, gpu_count * 8)),
                                ram_gb=float(lowest_price.get("minMemory") or max(16, gpu_count * memory * 1.5)),
                                gpu_flops_tflops=self.catalog.flops_for(name),
                                memory_bw_gbps=self.catalog.bandwidth_for(name),
                                platform=self.platform,
                                region=_runpod_region_from_stock(lowest_price.get("stockStatus") or ""),
                                source="live",
                                source_detail="live:official",
                                spot=is_spot,
                                available_instances=max(1, max_unreserved // gpu_count),
                                is_availability_estimated=False,
                                is_region_estimated=True,
                                instance_type=str(item.get("id") or name),
                            )
                        )
            offers = _dedupe_offers(_apply_constraints(offers, constraints))
            self.cache.set_json(cache_key, [item.model_dump(mode="json") for item in offers])
            return ProviderFetchResult(
                offers=offers,
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=True,
                    offers_count=len(offers),
                    message="Fetched live offers from RunPod.",
                ),
            )
        except (httpx.HTTPError, ValueError) as exc:
            return ProviderFetchResult(
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=False,
                    offers_count=0,
                    message=f"Live request failed: {exc}",
                )
            )


class AWSProvider:
    platform = "aws"

    def __init__(
        self,
        requester: HTTPRequester | None = None,
        cache: FileTTLCache | None = None,
        catalog: AWSSpecCatalog | None = None,
    ) -> None:
        self.auth = ProviderAuth("AWS_PRICE_LIST_PUBLIC", required=False)
        self.requester = requester or HTTPRequester(RequestPolicy(timeout_seconds=30.0))
        self.cache = cache or FileTTLCache(ttl_seconds=300)
        self.catalog = catalog or AWSSpecCatalog()

    def fetch(self, constraints: Constraints) -> ProviderFetchResult:
        offers: list[MarketOffer] = []
        try:
            for region in _expand_aws_regions(constraints.region):
                cache_key = f"aws:{region}"
                cached = self.cache.get_json(cache_key)
                if cached is not None:
                    offers.extend([MarketOffer.model_validate(item) for item in cached])
                    continue
                payload = self.requester.get_json(AWS_PRICE_LIST_URL_TEMPLATE.format(region=region))
                raw_products = payload.get("products", {}) if isinstance(payload, dict) else {}
                terms = payload.get("terms", {}).get("OnDemand", {}) if isinstance(payload, dict) else {}
                region_offers: list[MarketOffer] = []
                for sku, product in raw_products.items():
                    attributes = product.get("attributes", {})
                    instance_type = attributes.get("instanceType")
                    spec = self.catalog.get(instance_type) if instance_type else None
                    if spec is None:
                        continue
                    if attributes.get("operatingSystem") != "Linux":
                        continue
                    if attributes.get("preInstalledSw") not in {"NA", None, ""}:
                        continue
                    if attributes.get("tenancy") not in {"Shared", None, ""}:
                        continue
                    if attributes.get("marketoption") not in {"OnDemand", None, ""}:
                        continue
                    if attributes.get("capacitystatus") not in {"Used", None, ""}:
                        continue
                    price = _extract_aws_ondemand_hourly_price(terms.get(sku, {}))
                    if price is None or price <= 0:
                        continue
                    region_offers.append(
                        MarketOffer(
                            gpu=str(spec["gpu"]),
                            gpu_count=int(spec["gpu_count"]),
                            vram_gb=float(spec["vram_gb"]),
                            price_per_hour=round(price, 4),
                            cpu=int(spec["cpu"]),
                            ram_gb=float(spec["ram_gb"]),
                            gpu_flops_tflops=float(spec["gpu_flops_tflops"]),
                            memory_bw_gbps=float(spec.get("memory_bw_gbps", 0.0)),
                            platform=self.platform,
                            region=region.lower(),
                            source="live",
                            source_detail="live:official",
                            spot=False,
                            available_instances=10, # Defaulting to 10 for massive clouds when real-time availability is unknown
                            is_availability_estimated=True,
                            instance_type=instance_type,
                        )
                    )
                region_offers = _dedupe_offers(region_offers)
                self.cache.set_json(cache_key, [item.model_dump(mode="json") for item in region_offers])
                offers.extend(region_offers)
            offers = _dedupe_offers(_apply_constraints(offers, constraints))
            return ProviderFetchResult(
                offers=offers,
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=True,
                    offers_count=len(offers),
                    message="Fetched public AWS EC2 price list data.",
                ),
            )
        except (httpx.HTTPError, ValueError) as exc:
            return ProviderFetchResult(
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=False,
                    offers_count=0,
                    message=f"Live request failed: {exc}",
                )
            )


class GPUFinderProvider:
    platform = "gpufindr"

    def __init__(
        self,
        requester: HTTPRequester | None = None,
        cache: FileTTLCache | None = None,
        catalog: GPUSpecCatalog | None = None,
    ) -> None:
        self.requester = requester or HTTPRequester(RequestPolicy(timeout_seconds=20.0))
        self.cache = cache or FileTTLCache(ttl_seconds=300)
        self.catalog = catalog or GPUSpecCatalog()

    def fetch(self, constraints: Constraints) -> ProviderFetchResult:
        cache_key = f"gpufinder:{','.join(sorted(constraints.platforms))}:{constraints.max_gpus}"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            offers = [MarketOffer.model_validate(item) for item in cached]
            offers = _apply_constraints(offers, constraints)
            return ProviderFetchResult(
                offers=offers,
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=True,
                    offers_count=len(offers),
                    message="Loaded live offers from gpufindr cache.",
                ),
            )

        try:
            params = {
                "limit": 200,
                "max_price": constraints.max_budget if constraints.max_budget else 100.0,
            }
            payload = self.requester.get_json(GPUFINDER_URL, params=params)
            raw_offers = payload if isinstance(payload, list) else []

            offers: list[MarketOffer] = []
            for item in raw_offers:
                source_platform = str(item.get("source") or "unknown").lower()
                gpu_name = str(item.get("name") or "unknown")
                resolved_gpu = self.catalog.resolve_name(gpu_name)
                
                vram_gb = float(item.get("vram_mb") or 0) / 1024.0
                ram_gb = float(item.get("ram_mb") or 0) / 1024.0
                price = float(item.get("total_cost_ph") or 0.0)
                gpu_count = int(item.get("num_gpus") or 1)
                
                if price <= 0 or vram_gb <= 0:
                    continue
                
                offers.append(
                    MarketOffer(
                        gpu=resolved_gpu,
                        gpu_count=gpu_count,
                        vram_gb=round(vram_gb, 2),
                        price_per_hour=round(price, 4),
                        cpu=int(item.get("cpu_cores") or 2),
                        ram_gb=round(ram_gb, 2),
                        gpu_flops_tflops=float(item.get("total_flops") or self.catalog.flops_for(gpu_name)),
                        memory_bw_gbps=self.catalog.bandwidth_for(gpu_name),
                        platform=source_platform,
                        region=str(item.get("location") or "unknown").lower(),
                        source="live",
                        source_detail="live:gpufindr",
                        spot=False,
                        available_instances=1,
                        instance_type=str(item.get("id") or ""),
                    )
                )

            self.cache.set_json(cache_key, [item.model_dump(mode="json") for item in offers])
            return ProviderFetchResult(
                offers=offers,
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=True,
                    offers_count=len(offers),
                    message="Fetched live offers from gpufindr.com.",
                ),
            )
        except (httpx.HTTPError, ValueError) as exc:
            return ProviderFetchResult(
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=False,
                    offers_count=0,
                    message=f"gpufindr request failed: {exc}",
                )
            )


class GPUHuntProvider:
    platform = "gpuhunt"

    def __init__(
        self,
        cache: FileTTLCache | None = None,
        catalog: GPUSpecCatalog | None = None,
    ) -> None:
        self.cache = cache or FileTTLCache(ttl_seconds=300)
        self.catalog = catalog or GPUSpecCatalog()

    def fetch(self, constraints: Constraints) -> ProviderFetchResult:
        if gpuhunt is None:
            return ProviderFetchResult(
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=False,
                    offers_count=0,
                    message="gpuhunt library is not installed.",
                )
            )

        cache_key = f"gpuhunt:{','.join(sorted(constraints.platforms))}:{constraints.max_gpus}"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            offers = [MarketOffer.model_validate(item) for item in cached]
            offers = _apply_constraints(offers, constraints)
            return ProviderFetchResult(
                offers=offers,
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=True,
                    offers_count=len(offers),
                    message="Loaded live offers from gpuhunt cache.",
                ),
            )

        try:
            # We fetch all and filter locally to ensure consistency with our Constraints
            raw_results = gpuhunt.query()
            
            offers: list[MarketOffer] = []
            for item in raw_results:
                # Map gpuhunt provider name to TIS platform name
                provider_name = str(item.provider).lower()
                if provider_name == "vastai":
                    provider_name = "vast.ai"
                
                gpu_name = str(item.gpu_name)
                resolved_gpu = self.catalog.resolve_name(gpu_name)
                
                vram_gb = float(item.gpu_memory or 0)
                ram_gb = float(item.memory or 0)
                price = float(item.price or 0.0)
                gpu_count = int(item.gpu_count or 1)
                
                if price <= 0 or vram_gb <= 0:
                    continue
                
                offers.append(
                    MarketOffer(
                        gpu=resolved_gpu,
                        gpu_count=gpu_count,
                        vram_gb=round(vram_gb, 2),
                        price_per_hour=round(price, 4),
                        cpu=int(item.cpu or 2),
                        ram_gb=round(ram_gb, 2),
                        gpu_flops_tflops=self.catalog.flops_for(gpu_name),
                        memory_bw_gbps=self.catalog.bandwidth_for(gpu_name),
                        platform=provider_name,
                        region=str(item.location or "unknown").lower(),
                        source="live",
                        source_detail="live:gpuhunt",
                        spot=bool(item.spot),
                        available_instances=1,
                        instance_type=str(item.instance_name or ""),
                    )
                )

            # Apply constraints and dedupe
            offers = _dedupe_offers(_apply_constraints(offers, constraints))
            
            self.cache.set_json(cache_key, [item.model_dump(mode="json") for item in offers])
            return ProviderFetchResult(
                offers=offers,
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=True,
                    offers_count=len(offers),
                    message="Fetched live offers using gpuhunt library.",
                ),
            )
        except Exception as exc:
            return ProviderFetchResult(
                status=ProviderStatus(
                    provider=self.platform,
                    source="live",
                    ok=False,
                    offers_count=0,
                    message=f"gpuhunt query failed: {exc}",
                )
            )



def _apply_constraints(offers: list[MarketOffer], constraints: Constraints) -> list[MarketOffer]:
    filtered: list[MarketOffer] = []
    allowed_platforms = set(constraints.platforms)
    allowed_regions = set(constraints.region)
    for offer in offers:
        if offer.platform not in allowed_platforms:
            continue
        if allowed_regions and not _region_matches(offer.region, allowed_regions):
            continue
        if offer.gpu_count > constraints.max_gpus:
            continue
        filtered.append(offer)
    return filtered


def _dedupe_offers(offers: list[MarketOffer]) -> list[MarketOffer]:
    deduped: dict[tuple[str, int, str, str, bool], MarketOffer] = {}
    for offer in offers:
        key = (offer.gpu.lower(), offer.gpu_count, offer.platform, offer.region, offer.spot)
        existing = deduped.get(key)
        if existing is None or offer.price_per_hour < existing.price_per_hour:
            deduped[key] = offer
    return list(deduped.values())


def _runpod_region_from_stock(stock_status: str) -> str:
    if stock_status in {"high", "medium", "low"}:
        return "us"
    return "global"


def _gpu_count_cap(values: list[int]) -> int:
    valid = [value for value in values if isinstance(value, int) and value > 0]
    return max(valid, default=1)


def _extract_aws_ondemand_hourly_price(term_payload: dict) -> float | None:
    for term in term_payload.values():
        for dimension in term.get("priceDimensions", {}).values():
            if dimension.get("unit") != "Hrs":
                continue
            usd = dimension.get("pricePerUnit", {}).get("USD")
            if usd:
                return float(usd)
    return None


def _expand_aws_regions(requested_regions: list[str]) -> list[str]:
    if not requested_regions:
        return ["us-east-1", "us-west-2", "eu-west-1", "eu-central-1"]
    aliases = {
        "us": ["us-east-1", "us-west-2"],
        "eu": ["eu-west-1", "eu-central-1"],
        "ap": ["ap-northeast-1", "ap-southeast-1"],
    }
    expanded: list[str] = []
    for region in requested_regions:
        expanded.extend(aliases.get(region, [region]))
    result: list[str] = []
    for region in expanded:
        if region not in result:
            result.append(region)
    return result


def _region_matches(offer_region: str, allowed_regions: set[str]) -> bool:
    if offer_region == "global":
        return True
    for region in allowed_regions:
        if offer_region == region:
            return True
        if offer_region.startswith(region + "-"):
            return True
        if region.startswith(offer_region + "-"):
            return True
    return False


def _vast_region_label(geolocation: str) -> str:
    value = geolocation.lower()
    if any(token in value for token in [", us", " united states", "oregon", "texas", "michigan", "north carolina", "virginia", "california"]):
        return "us"
    if any(token in value for token in [", es", ", fr", ", de", ", pl", ", hu", "france", "germany", "spain", "poland", "hungary", "eu"]):
        return "eu"
    if any(token in value for token in [", kr", ", vn", ", jp", ", sg", "south korea", "vietnam", "japan", "singapore"]):
        return "ap"
    return "global"
