from __future__ import annotations

import hashlib
import json
import time
from typing import Optional


class ToolResultCache:
    def __init__(self, max_size: int = 256, ttl_seconds: int = 300):
        self.max_size = max(1, max_size)
        self.ttl_seconds = max(1, ttl_seconds)
        self._cache: dict[str, tuple[float, str]] = {}

    def get(self, tool_name: str, arguments: dict) -> Optional[str]:
        key = self._key(tool_name, arguments)
        entry = self._cache.get(key)
        if entry is None:
            return None
        timestamp, result = entry
        if time.monotonic() - timestamp > self.ttl_seconds:
            del self._cache[key]
            return None
        return result

    def put(self, tool_name: str, arguments: dict, result: str) -> None:
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k][0])
            del self._cache[oldest_key]
        key = self._key(tool_name, arguments)
        self._cache[key] = (time.monotonic(), result)

    def clear(self) -> None:
        self._cache.clear()

    def _key(self, tool_name: str, arguments: dict) -> str:
        raw = json.dumps({"tool": tool_name, "args": arguments}, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()
