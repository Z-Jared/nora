"""Registry tools for structured memory records."""

from __future__ import annotations

import json as _json
from typing import Optional

from mini_agent.memory_records import MemoryRecordStore, VALID_KINDS, VALID_SCOPES
from mini_agent.registry import ToolPermission, ToolRegistry


def register_memory_record_tools(
    registry: ToolRegistry,
    store: MemoryRecordStore,
) -> None:

    def _save_memory_record(
        kind: str,
        title: str,
        content: str,
        scope: str = "project",
        tags: str = "",
        source: str = "",
        confidence: float = 1.0,
        related_task_id: str = "",
    ) -> str:
        msg, record_id = store.create(
            kind=kind, title=title, content=content, scope=scope,
            tags=tags, source=source, confidence=confidence,
            related_task_id=related_task_id,
        )
        if not record_id:
            return _json.dumps({"error": msg}, ensure_ascii=False)
        rec = store.get(record_id)
        return _json.dumps(rec, ensure_ascii=False)

    def _search_memory_records(query: str, max_results: int = 5, kind: str = "", scope: str = "", tags: str = "") -> str:
        results = store.search(query=query, max_results=max_results, kind=kind, scope=scope, tags=tags)
        summaries = [
            {
                "record_id": r["record_id"],
                "kind": r["kind"],
                "scope": r["scope"],
                "title": r["title"],
                "tags": r["tags"],
                "confidence": r["confidence"],
                "updated_at": r["updated_at"],
            }
            for r in results
        ]
        return _json.dumps(summaries, ensure_ascii=False)

    def _list_memory_records(kind: str = "", scope: str = "", max_results: int = 20) -> str:
        results = store.list(kind=kind, scope=scope, max_results=max_results)
        summaries = [
            {
                "record_id": r["record_id"],
                "kind": r["kind"],
                "scope": r["scope"],
                "title": r["title"],
                "tags": r["tags"],
                "confidence": r["confidence"],
                "updated_at": r["updated_at"],
            }
            for r in results
        ]
        return _json.dumps(summaries, ensure_ascii=False)

    def _get_memory_record(record_id: str) -> str:
        rec = store.get(record_id.strip())
        if rec is None:
            return _json.dumps({"error": f"未找到记录: {record_id}"}, ensure_ascii=False)
        return _json.dumps(rec, ensure_ascii=False)

    def _delete_memory_record(record_id: str) -> str:
        msg = store.delete(record_id.strip())
        if msg.startswith("未找到") or msg.startswith("record_id"):
            return _json.dumps({"error": msg}, ensure_ascii=False)
        return _json.dumps({"ok": True, "message": msg}, ensure_ascii=False)

    registry.register(
        "save_memory_record",
        "保存结构化记忆记录（决策、偏好、事实、任务学习、风险、备注）。不会自动保存 prompt、diff、shell 输出等。",
        _save_memory_record,
        parameters={
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "description": f"记录类型，有效值: {', '.join(VALID_KINDS)}",
                },
                "title": {
                    "type": "string",
                    "description": "简短标题",
                },
                "content": {
                    "type": "string",
                    "description": "记录内容",
                },
                "scope": {
                    "type": "string",
                    "description": "作用域（project/user/global），默认 project",
                },
                "tags": {
                    "type": "string",
                    "description": "逗号分隔的标签",
                },
                "source": {
                    "type": "string",
                    "description": "来源说明",
                },
                "confidence": {
                    "type": "number",
                    "description": "置信度 0.0-1.0，默认 1.0",
                },
                "related_task_id": {
                    "type": "string",
                    "description": "关联任务 ID",
                },
            },
            "required": ["kind", "title", "content"],
        },
        permission=ToolPermission(category="memory", risk="write"),
    )
    registry.register(
        "search_memory_records",
        "搜索结构化记忆记录，返回摘要列表（不含完整内容）。可按 kind、scope 和 tags 过滤。",
        _search_memory_records,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回结果数，默认 5，最大 20",
                },
                "kind": {
                    "type": "string",
                    "description": "可选，按类型过滤",
                },
                "scope": {
                    "type": "string",
                    "description": f"可选，按作用域过滤，有效值: {', '.join(VALID_SCOPES)}",
                },
                "tags": {
                    "type": "string",
                    "description": "可选，逗号分隔的标签，所有标签必须匹配",
                },
            },
            "required": ["query"],
        },
        permission=ToolPermission(category="memory", risk="read"),
    )
    registry.register(
        "list_memory_records",
        "列出结构化记忆记录，返回摘要列表（不含完整内容）。可按 kind 和 scope 过滤。",
        _list_memory_records,
        parameters={
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "description": "可选，按类型过滤",
                },
                "scope": {
                    "type": "string",
                    "description": "可选，按作用域过滤",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回结果数，默认 20，最大 100",
                },
            },
        },
        permission=ToolPermission(category="memory", risk="read"),
    )
    registry.register(
        "get_memory_record",
        "获取单条结构化记忆记录的完整内容。",
        _get_memory_record,
        parameters={
            "type": "object",
            "properties": {
                "record_id": {
                    "type": "string",
                    "description": "记录 ID",
                }
            },
            "required": ["record_id"],
        },
        permission=ToolPermission(category="memory", risk="read"),
    )
    registry.register(
        "delete_memory_record",
        "删除一条结构化记忆记录。",
        _delete_memory_record,
        parameters={
            "type": "object",
            "properties": {
                "record_id": {
                    "type": "string",
                    "description": "要删除的记录 ID",
                }
            },
            "required": ["record_id"],
        },
        permission=ToolPermission(category="memory", risk="delete"),
    )
