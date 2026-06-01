"""Registry tool for review-memory capture."""

from __future__ import annotations

import json as _json

from mini_agent.memory_records import MemoryRecordStore
from mini_agent.registry import ToolPermission, ToolRegistry
from mini_agent.review_memory import ReviewMemoryCapture

_VALID_STATUSES = ("approved", "changes_requested", "blocked")


def register_review_memory_tool(
    registry: ToolRegistry,
    store: MemoryRecordStore,
) -> None:
    capture = ReviewMemoryCapture(store)

    def _capture_review_memory(
        task_id: str,
        status: str,
        title: str,
        summary: str,
        learnings: str = "",
        risks: str = "",
        decisions: str = "",
        source: str = "review",
    ) -> str:
        result = capture.capture(
            task_id=task_id,
            status=status,
            title=title,
            summary=summary,
            learnings=learnings,
            risks=risks,
            decisions=decisions,
            source=source,
        )
        # Return bounded JSON: record IDs/kinds only, not full content
        bounded = {
            "created": [
                {"record_id": r.get("record_id", ""), "kind": r.get("kind", ""), "title": r.get("title", "")}
                for r in result.get("created", [])
            ],
            "skipped": result.get("skipped", []),
        }
        if "error" in result:
            bounded["error"] = result["error"]
        return _json.dumps(bounded, ensure_ascii=False)

    registry.register(
        "capture_review_memory",
        "将 review/task 摘要转为结构化记忆记录。仅接受显式摘要字段，不接受 raw diff/shell/prompt。",
        _capture_review_memory,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "关联的任务 ID",
                },
                "status": {
                    "type": "string",
                    "description": f"review 状态，有效值: {', '.join(_VALID_STATUSES)}",
                },
                "title": {
                    "type": "string",
                    "description": "简短标题",
                },
                "summary": {
                    "type": "string",
                    "description": "review 摘要（纯文本，不含 diff/shell 输出）",
                },
                "learnings": {
                    "type": "string",
                    "description": "可选，任务中的经验教训",
                },
                "risks": {
                    "type": "string",
                    "description": "可选，识别到的风险（每行一条）",
                },
                "decisions": {
                    "type": "string",
                    "description": "可选，做出的决策（每行一条，仅 approved 状态写入）",
                },
                "source": {
                    "type": "string",
                    "description": "来源说明，默认 review",
                },
            },
            "required": ["task_id", "status", "title", "summary"],
        },
        permission=ToolPermission(category="memory", risk="write"),
    )
