from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx


@dataclass
class RetryPolicy:
    max_attempts: int = 2
    backoff_seconds: float = 0.25


@dataclass
class RequestPolicy:
    timeout_seconds: float = 15.0
    retry: RetryPolicy = field(default_factory=RetryPolicy)


class HTTPRequester:
    def __init__(self, request_policy: RequestPolicy | None = None, client: httpx.Client | None = None) -> None:
        self.request_policy = request_policy or RequestPolicy()
        self.client = client or httpx.Client(timeout=self.request_policy.timeout_seconds)

    def get_json(self, url: str, **kwargs) -> object:
        return self._request_json("GET", url, **kwargs)

    def post_json(self, url: str, **kwargs) -> object:
        return self._request_json("POST", url, **kwargs)

    def _request_json(self, method: str, url: str, **kwargs) -> object:
        last_error: Exception | None = None
        for attempt in range(1, self.request_policy.retry.max_attempts + 1):
            try:
                response = self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt >= self.request_policy.retry.max_attempts:
                    raise
                time.sleep(self.request_policy.retry.backoff_seconds * attempt)
        if last_error is not None:
            raise last_error
        raise RuntimeError("unreachable")
