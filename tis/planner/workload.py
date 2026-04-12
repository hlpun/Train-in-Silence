from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from tis.planner.models import PlanningRequest


def load_request(path: str | Path) -> PlanningRequest:
    source = Path(path)
    raw = source.read_text(encoding="utf-8")
    payload: dict[str, Any]
    if source.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(raw)
    else:
        payload = json.loads(raw)
    return PlanningRequest.model_validate(payload)
