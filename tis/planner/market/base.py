from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from tis.planner.models import Constraints, MarketOffer, ProviderStatus


@dataclass
class ProviderFetchResult:
    offers: list[MarketOffer] = field(default_factory=list)
    status: ProviderStatus | None = None


class MarketProvider(Protocol):
    platform: str

    def fetch(self, constraints: Constraints) -> ProviderFetchResult: ...
