from tis.planner.models import PlanningRequest
from tis.planner.recommender import PlannerService


def test_recommend_returns_results() -> None:
    request = PlanningRequest.model_validate(
        {
            "workload": {
                "model": {
                    "name": "llama-13b",
                    "params": 13_000_000_000,
                    "hidden_dim": 5120,
                    "num_layers": 40,
                    "num_heads": 40,
                    "num_kv_heads": 40
                },
                "training": {
                    "method": "qlora",
                    "precision": "bf16",
                    "batch_size": 4,
                    "grad_accum": 8,
                    "seq_len": 2048,
                    "epochs": 3,
                },
                "data": {"dataset_tokens": 100_000_000},
            },
            "constraints": {
                "platforms": ["vast.ai", "runpod"],
                "max_budget": 30,
                "max_time_hours": 12,
                "region": ["us", "eu"],
                "max_gpus": 4,
            },
            "preference": {"optimize_for": "balanced"},
        }
    )

    response = PlannerService().recommend(request)

    assert response.recommendations
    assert any(rec.label == "cheapest" for rec in response.recommendations)
    assert any(rec.label == "fastest" for rec in response.recommendations)
    # Ensure notes from offers are propagated
    assert all(hasattr(rec, "notes") for rec in response.recommendations)
    assert response.recommendations[0].config.gpu
    assert response.provider_statuses
