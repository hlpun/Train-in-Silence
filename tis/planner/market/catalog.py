from __future__ import annotations

import json
from pathlib import Path


class GPUSpecCatalog:
    def __init__(self, path: str | Path | None = None) -> None:
        base = Path(__file__).resolve().parents[2]
        self.path = Path(path) if path else base / "data" / "gpu_specs.json"
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self._specs = {item["name"].lower(): item for item in payload}
        self._aliases = {}
        for item in payload:
            for alias in item.get("aliases", []):
                self._aliases[alias.lower()] = item["name"].lower()

    def resolve_name(self, raw_name: str) -> str:
        normalized = " ".join(raw_name.replace("_", " ").replace("-", " - ").split()).lower()
        canonical = self._aliases.get(normalized, normalized)
        spec = self._specs.get(canonical)
        return spec["name"] if spec else raw_name.strip()

    def get(self, raw_name: str) -> dict[str, object] | None:
        normalized = " ".join(raw_name.replace("_", " ").replace("-", " - ").split()).lower()
        canonical = self._aliases.get(normalized, normalized)
        return self._specs.get(canonical)

    def flops_for(self, raw_name: str, default: float = 100.0) -> float:
        spec = self.get(raw_name)
        if spec is None:
            return default
        return float(spec["gpu_flops_tflops"])

    def vram_for(self, raw_name: str, default: float | None = None) -> float | None:
        spec = self.get(raw_name)
        if spec is None:
            return default
        return float(spec["vram_gb"])

    def bandwidth_for(self, raw_name: str, default: float = 0.0) -> float:
        spec = self.get(raw_name)
        if spec is None:
            return default
        return float(spec.get("memory_bw_gbps", default))

    def export(self) -> list[dict[str, object]]:
        return list(self._specs.values())


class AWSSpecCatalog:
    def __init__(self, path: str | Path | None = None) -> None:
        base = Path(__file__).resolve().parents[2]
        self.path = Path(path) if path else base / "data" / "aws_gpu_instances.json"
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self._specs = {item["instance_type"]: item for item in payload}

    def get(self, instance_type: str) -> dict[str, object] | None:
        return self._specs.get(instance_type)
