from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tis.planner.market import AWSProvider, GPUSpecCatalog, RunpodProvider, VastAIProvider
from tis.planner.models import Constraints


def build_sample_offers(
    offers_by_provider: dict[str, list[dict[str, object]]],
    max_per_platform: int = 10,
) -> list[dict[str, object]]:
    sample: list[dict[str, object]] = []
    for platform, offers in offers_by_provider.items():
        chosen = _select_platform_sample(offers, max_per_platform=max_per_platform)
        for offer in chosen:
            offer = dict(offer)
            offer["source"] = "sample"
            sample.append(offer)
    return sorted(
        sample,
        key=lambda item: (
            str(item.get("platform", "")),
            float(item.get("price_per_hour", 0.0)),
            -float(item.get("vram_gb", 0.0)),
            str(item.get("gpu", "")),
        ),
    )


def _select_platform_sample(offers: list[dict[str, object]], max_per_platform: int) -> list[dict[str, object]]:
    if not offers:
        return []

    deduped: dict[tuple[str, int, str, bool], dict[str, object]] = {}
    for offer in offers:
        key = (
            str(offer.get("gpu")),
            int(offer.get("gpu_count", 1)),
            str(offer.get("region")),
            bool(offer.get("spot", False)),
        )
        existing = deduped.get(key)
        if existing is None or float(offer.get("price_per_hour", 0.0)) < float(existing.get("price_per_hour", 0.0)):
            deduped[key] = offer

    pool = list(deduped.values())
    by_price = sorted(pool, key=lambda item: float(item.get("price_per_hour", 0.0)))
    by_vram = sorted(pool, key=lambda item: float(item.get("vram_gb", 0.0)), reverse=True)
    by_compute = sorted(pool, key=lambda item: float(item.get("gpu_flops_tflops", 0.0)), reverse=True)

    chosen_keys: set[tuple[str, int, str, bool]] = set()
    chosen: list[dict[str, object]] = []

    def add_offer(offer: dict[str, object]) -> None:
        key = (
            str(offer.get("gpu")),
            int(offer.get("gpu_count", 1)),
            str(offer.get("region")),
            bool(offer.get("spot", False)),
        )
        if key in chosen_keys:
            return
        chosen_keys.add(key)
        chosen.append(offer)

    # Cheapest representative ladder.
    for index in [0, len(by_price) // 4, len(by_price) // 2]:
        add_offer(by_price[index])

    # Strongest compute and largest memory representatives.
    add_offer(by_compute[0])
    add_offer(by_vram[0])

    # Region coverage.
    seen_regions: set[str] = set()
    for offer in by_price:
        region = str(offer.get("region"))
        if region in seen_regions:
            continue
        seen_regions.add(region)
        add_offer(offer)

    # GPU family coverage.
    seen_gpus: set[str] = set()
    for offer in by_price:
        gpu = str(offer.get("gpu"))
        if gpu in seen_gpus:
            continue
        seen_gpus.add(gpu)
        add_offer(offer)
        if len(chosen) >= max_per_platform:
            break

    # Ensure at least one spot and one multi-GPU example when available.
    for offer in by_price:
        if bool(offer.get("spot", False)):
            add_offer(offer)
            break
    for offer in by_price:
        if int(offer.get("gpu_count", 1)) > 1:
            add_offer(offer)
            break

    if len(chosen) < max_per_platform:
        for offer in by_price:
            add_offer(offer)
            if len(chosen) >= max_per_platform:
                break

    return chosen[:max_per_platform]


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh live market snapshots from supported providers.")
    parser.add_argument("--region", action="append", default=["us", "eu"], help="Requested region alias or region code.")
    parser.add_argument("--max-gpus", type=int, default=2, help="Maximum GPU count to request from providers.")
    parser.add_argument(
        "--output",
        default="data/live_market_snapshot.json",
        help="Path to write the aggregated live market snapshot JSON.",
    )
    parser.add_argument(
        "--update-sample-data",
        action="store_true",
        help="Generate bundled sample data from the freshly downloaded live snapshot.",
    )
    parser.add_argument(
        "--sample-output",
        default="data/gpu_offers.json",
        help="Path to write bundled sample offers when --update-sample-data is used.",
    )
    parser.add_argument(
        "--sample-max-per-platform",
        type=int,
        default=12,
        help="Maximum number of bundled sample offers to keep per platform.",
    )
    args = parser.parse_args()

    constraints = Constraints(
        platforms=["vast.ai", "runpod", "aws"],
        region=args.region,
        max_gpus=args.max_gpus,
    )
    providers = [VastAIProvider(), RunpodProvider(), AWSProvider()]

    provider_statuses: list[dict[str, object]] = []
    offers_by_provider: dict[str, list[dict[str, object]]] = {}
    for provider in providers:
        result = provider.fetch(constraints)
        provider_statuses.append(
            result.status.model_dump(mode="json") if result.status is not None else {
                "provider": provider.platform,
                "source": "live",
                "ok": False,
                "offers_count": 0,
                "message": "No provider status returned.",
            }
        )
        offers_by_provider[provider.platform] = [offer.model_dump(mode="json") for offer in result.offers]

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "constraints": constraints.model_dump(mode="json"),
        "provider_statuses": provider_statuses,
        "offers_by_provider": offers_by_provider,
        "gpu_specs_catalog": GPUSpecCatalog().export(),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Wrote live snapshot to {output_path}")
    for status in provider_statuses:
        print(
            f"{status['provider']}: ok={status['ok']} offers={status['offers_count']} source={status['source']} "
            f"message={status.get('message') or ''}"
        )

    if args.update_sample_data:
        sample_offers = build_sample_offers(
            offers_by_provider,
            max_per_platform=args.sample_max_per_platform,
        )
        sample_path = Path(args.sample_output)
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        sample_path.write_text(json.dumps(sample_offers, indent=2), encoding="utf-8")
        print(f"Wrote bundled sample offers to {sample_path} ({len(sample_offers)} offers)")


if __name__ == "__main__":
    main()
