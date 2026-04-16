from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from tis.planner.models import ModelSpec, Workload, TrainingSpec, InferenceSpec

import json

def prune_aws_response(response):
    """Prune massive AWS pricing JSON to just a few entries to save disk space."""
    try:
        body_bytes = response["body"]["string"]
        if len(body_bytes) < 1000000: # If it's already small, ignore
            return response
            
        import json
        body_str = body_bytes.decode("utf-8")
        if "formatVersion" in body_str and "AmazonEC2" in body_str:
            data = json.loads(body_str)
            
            # Smart Prune: Find Linux GPU instances (g*, p*)
            products = data.get("products", {})
            selected_skus = []
            for sku, info in products.items():
                attrs = info.get("attributes", {})
                itype = attrs.get("instanceType", "")
                os_val = attrs.get("operatingSystem", "")
                if any(itype.startswith(prefix) for prefix in ["g", "p"]) and os_val == "Linux":
                    selected_skus.append(sku)
                if len(selected_skus) >= 10:
                    break
            
            # Fallback to first 2 if none found
            if not selected_skus:
                selected_skus = list(products.keys())[:2]
            
            data["products"] = {sku: products[sku] for sku in selected_skus}
            on_demand = data.get("terms", {}).get("OnDemand", {})
            data["terms"] = {
                "OnDemand": {sku: on_demand[sku] for sku in selected_skus if sku in on_demand}
            }
            
            # Remove large metadata
            for key in list(data.keys()):
                if key not in {"formatVersion", "products", "terms", "offerCode"}:
                    data[key] = "pruned"
            
            response["body"]["string"] = json.dumps(data).encode("utf-8")
    except Exception:
        pass
    return response

@pytest.fixture
def vcr_config():
    return {
        "filter_headers": [("Authorization", "Bearer MASKED")],
        "filter_query_parameters": [("api_key", "MASKED")],
        "decode_compressed_response": True,
        "record_mode": "new_episodes",
        "before_record_response": prune_aws_response,
    }

@pytest.fixture
def llama3_model() -> ModelSpec:
    return ModelSpec(
        name="Llama-3-8B",
        params=8_000_000_000,
        hidden_dim=4096,
        num_layers=32,
        num_heads=32,
        num_kv_heads=8,
    )

@pytest.fixture
def deepseek_v3_moe() -> ModelSpec:
    return ModelSpec(
        name="DeepSeek-V3",
        params=671_000_000_000,
        active_experts=2, # Number of experts, not params
        num_experts=2,    # Set to same to make all params active for this test
        hidden_dim=7168,
        num_layers=61,
        num_heads=128,
        num_kv_heads=1,
    )

@pytest.fixture
def sample_training_workload(llama3_model) -> Workload:
    return Workload(
        model=llama3_model,
        training=TrainingSpec(
            method="lora",
            precision="bf16",
            batch_size=4,
            seq_len=2048,
            epochs=3
        )
    )

@pytest.fixture
def sample_inference_workload(llama3_model) -> Workload:
    return Workload(
        model=llama3_model,
        inference=InferenceSpec(
            precision="fp16",
            batch_size=1,
            prompt_tokens=512,
            max_new_tokens=1024
        )
    )
