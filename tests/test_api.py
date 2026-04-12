from __future__ import annotations

from fastapi.testclient import TestClient

from tis.api.server import app

from unittest.mock import patch
from tis.planner.models import MarketAggregation, ProviderStatus

client = TestClient(app)


def test_health_returns_status() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_version_returns_valid_json() -> None:
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json()["version"] == "0.1.0"


@patch("tis.api.server.service.market.fetch_market_data")
def test_providers_endpoint_returns_statuses(mock_fetch) -> None:
    mock_fetch.return_value = MarketAggregation(
        offers=[],
        provider_statuses=[
            ProviderStatus(provider="test", source="sample", ok=True, offers_count=0)
        ]
    )
    response = client.get("/providers")
    assert response.status_code == 200
    payload = response.json()
    assert "providers" in payload
    assert payload["providers"][0]["provider"] == "test"


@patch("tis.api.server.service.market.fetch_market_data")
def test_recommend_success(mock_fetch) -> None:
    mock_fetch.return_value = MarketAggregation(
        offers=[], # Can be empty for basic success check if recommender handles it
        provider_statuses=[]
    )
    payload = {
        "workload": {
            "model": {"name": "llama-7b", "params": 7000000000},
            "training": {"method": "qlora", "precision": "bf16"},
            "data": {"dataset_tokens": 1000000}
        }
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 200
    assert "recommendations" in response.json()


def test_recommend_invalid_params() -> None:
    payload = {
        "workload": {
            "model": {"name": "test", "params": -1}, # Invalid params
            "training": {"method": "full"},
            "data": {"dataset_tokens": 1000}
        }
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 422


def test_recommend_validation_error_is_structured() -> None:
    response = client.post("/recommend", json={})
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
