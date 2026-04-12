from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


class FileTTLCache:
    def __init__(self, cache_dir: str | Path = ".tis_cache", ttl_seconds: int = 300) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

    def get_json(self, key: str) -> object | None:
        path = self._path_for_key(key)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        expires_at = float(payload.get("expires_at", 0))
        if time.time() >= expires_at:
            path.unlink(missing_ok=True)
            return None
        return payload.get("value")

    def set_json(self, key: str, value: object) -> None:
        path = self._path_for_key(key)
        payload = {
            "expires_at": time.time() + self.ttl_seconds,
            "value": value,
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _path_for_key(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"
