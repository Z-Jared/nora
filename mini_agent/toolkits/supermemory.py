"""Optional Supermemory-backed memory toolkit for Nora.

Provides save, search, and profile tools when SUPERMEMORY_API_KEY is configured.
Uses only the standard library (urllib). Network failures return JSON errors.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional

DEFAULT_BASE_URL = "https://api.supermemory.ai"
MAX_CONTENT_CHARS = 10_000
MAX_RESULTS_DEFAULT = 5
MAX_RESULTS_LIMIT = 20
REQUEST_TIMEOUT = 15
CONTAINER_TAG = "nora"


class SupermemoryClient:
    """Thin wrapper around the Supermemory HTTP API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        container_tag: str = CONTAINER_TAG,
        timeout: int = REQUEST_TIMEOUT,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.container_tag = container_tag
        self.timeout = timeout

    @classmethod
    def from_env(cls, container_tag: str = CONTAINER_TAG) -> Optional["SupermemoryClient"]:
        api_key = os.environ.get("SUPERMEMORY_API_KEY", "").strip()
        if not api_key:
            return None
        base_url = os.environ.get("SUPERMEMORY_BASE_URL", "").strip() or DEFAULT_BASE_URL
        tag = os.environ.get("SUPERMEMORY_CONTAINER_TAG", "").strip() or container_tag
        return cls(api_key=api_key, base_url=base_url, container_tag=tag)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url, data=data, headers=self._headers(), method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def save(self, content: str, metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        content = content[:MAX_CONTENT_CHARS]
        body: dict[str, Any] = {
            "containerTag": self.container_tag,
            "content": content,
            "taskType": "memory",
        }
        if metadata:
            body["metadata"] = metadata
        return self._post("/v3/documents", body)

    def search(
        self,
        query: str,
        limit: int = MAX_RESULTS_DEFAULT,
        threshold: float = 0.5,
        search_mode: str = "hybrid",
    ) -> dict[str, Any]:
        limit = min(max(1, limit), MAX_RESULTS_LIMIT)
        body: dict[str, Any] = {
            "q": query,
            "containerTag": self.container_tag,
            "searchMode": search_mode,
            "limit": limit,
            "threshold": threshold,
        }
        return self._post("/v4/search", body)

    def profile(
        self,
        query: Optional[str] = None,
        threshold: float = 0.5,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "containerTag": self.container_tag,
            "threshold": threshold,
        }
        if query:
            body["q"] = query
        return self._post("/v4/profile", body)
