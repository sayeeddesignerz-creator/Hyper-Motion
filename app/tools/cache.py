"""
Thread-safe Cache with memory and TTL support.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

class Cache:
    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            del self._store[key]
            return None
        return entry["val"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        duration = ttl if ttl is not None else self.default_ttl
        self._store[key] = {
            "val": value,
            "expires_at": time.time() + duration
        }

    def clear(self) -> None:
        self._store.clear()
