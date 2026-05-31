"""Register Supermemory tools in the Nora registry.

Tools are always registered so they are discoverable. When no API key is
configured, calls return a clear JSON error instead of making network requests.
"""

from __future__ import annotations

import json as _json
from typing import Optional

from mini_agent.registry import ToolPermission, ToolRegistry
from mini_agent.toolkits.supermemory import SupermemoryClient


_NO_KEY_ERROR = _json.dumps(
    {"error": "Supermemory 未配置。请设置 SUPERMEMORY_API_KEY 环境变量。"},
    ensure_ascii=False,
)


def register_supermemory_tools(
    registry: ToolRegistry,
    client: Optional[SupermemoryClient],
) -> None:
    def _save(content: str, metadata: Optional[str] = None) -> str:
        if client is None:
            return _NO_KEY_ERROR
        parsed_meta = None
        if metadata:
            try:
                parsed_meta = _json.loads(metadata)
                if not isinstance(parsed_meta, dict):
                    parsed_meta = {"value": metadata}
            except _json.JSONDecodeError:
                parsed_meta = {"value": metadata}
        try:
            result = client.save(content=content, metadata=parsed_meta)
            return _json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            return _json.dumps({"error": f"Supermemory save failed: {exc}"}, ensure_ascii=False)

    def _search(query: str, limit: int = 5, threshold: float = 0.5) -> str:
        if client is None:
            return _NO_KEY_ERROR
        try:
            result = client.search(query=query, limit=limit, threshold=threshold)
            # Bound the output: extract only summary fields from results
            bounded = _bound_search_output(result)
            return _json.dumps(bounded, ensure_ascii=False)
        except Exception as exc:
            return _json.dumps({"error": f"Supermemory search failed: {exc}"}, ensure_ascii=False)

    def _profile(query: Optional[str] = None, threshold: float = 0.5) -> str:
        if client is None:
            return _NO_KEY_ERROR
        try:
            result = client.profile(query=query, threshold=threshold)
            bounded = _bound_profile_output(result)
            return _json.dumps(bounded, ensure_ascii=False)
        except Exception as exc:
            return _json.dumps({"error": f"Supermemory profile failed: {exc}"}, ensure_ascii=False)

    registry.register(
        "supermemory_save",
        "将用户提供的内容保存到 Supermemory 长期记忆。需要 SUPERMEMORY_API_KEY。",
        _save,
        parameters={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "要保存的内容文本（最多 10000 字符）",
                },
                "metadata": {
                    "type": "string",
                    "description": "可选的 JSON 字符串形式的元数据，例如 '{\"category\": \"research\"}'",
                },
            },
            "required": ["content"],
        },
        permission=ToolPermission(category="memory", risk="write"),
    )
    registry.register(
        "supermemory_search",
        "在 Supermemory 中搜索长期记忆。返回匹配结果摘要。需要 SUPERMEMORY_API_KEY。",
        _search,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询",
                },
                "limit": {
                    "type": "integer",
                    "description": "最多返回结果数，默认 5，最大 20",
                },
                "threshold": {
                    "type": "number",
                    "description": "相似度阈值 0-1，默认 0.5",
                },
            },
            "required": ["query"],
        },
        permission=ToolPermission(category="memory", risk="read"),
    )
    registry.register(
        "supermemory_profile",
        "获取 Supermemory 中的用户/项目画像。需要 SUPERMEMORY_API_KEY。",
        _profile,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "可选的查询，用于获取相关搜索结果",
                },
                "threshold": {
                    "type": "number",
                    "description": "相似度阈值 0-1，默认 0.5",
                },
            },
        },
        permission=ToolPermission(category="memory", risk="read"),
    )


_METADATA_VALUE_MAX_CHARS = 300
_METADATA_MAX_FIELDS = 20
_SENSITIVE_METADATA_KEYS = ("secret", "token", "api_key", "apikey", "password", "authorization", "bearer")
_SENSITIVE_VALUE_MARKERS = ("sk-", "bearer ", "api_key", "password", "secret")


def _looks_sensitive_key(key: object) -> bool:
    lower = str(key).lower()
    return any(marker in lower for marker in _SENSITIVE_METADATA_KEYS)


def _looks_sensitive_value(value: object) -> bool:
    if not isinstance(value, str):
        return False
    lower = value.lower()
    return any(marker in lower for marker in _SENSITIVE_VALUE_MARKERS)


def _bound_metadata(meta: dict) -> dict:
    """Keep only JSON-safe scalar fields, truncate strings, limit field count."""
    out = {}
    for i, (k, v) in enumerate(meta.items()):
        if i >= _METADATA_MAX_FIELDS:
            break
        if _looks_sensitive_key(k) or _looks_sensitive_value(v):
            continue
        if isinstance(v, bool):
            out[k] = v
        elif isinstance(v, (int, float)):
            out[k] = v
        elif isinstance(v, str):
            out[k] = v[:_METADATA_VALUE_MAX_CHARS]
        # skip non-scalar values (lists, dicts, nested objects)
    return out


def _bound_search_output(result: dict) -> dict:
    """Extract summary fields from search results, dropping raw chunks."""
    results = result.get("results", [])
    bounded = []
    for item in results[:20]:
        entry: dict = {"id": item.get("id", "")}
        if "memory" in item:
            entry["memory"] = item["memory"][:2000]
        elif "chunk" in item:
            entry["chunk_preview"] = item["chunk"][:500]
        if "similarity" in item:
            entry["similarity"] = item["similarity"]
        if "metadata" in item and item["metadata"]:
            entry["metadata"] = _bound_metadata(item["metadata"])
        bounded.append(entry)
    return {"results": bounded, "total": result.get("total", len(bounded))}


def _bound_profile_output(result: dict) -> dict:
    """Bound profile output to prevent huge payloads."""
    profile = result.get("profile", {})
    bounded_profile = {
        "static": [s[:1000] for s in profile.get("static", [])[:20]],
        "dynamic": [d[:1000] for d in profile.get("dynamic", [])[:20]],
    }
    out: dict = {"profile": bounded_profile}
    if "searchResults" in result:
        out["searchResults"] = _bound_search_output(result["searchResults"])
    return out
