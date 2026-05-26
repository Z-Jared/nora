from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from mini_agent.memory import is_sensitive_text
from mini_agent.tools_common import read_jsonl

MAX_LOG_PREVIEW_CHARS = 500
REDACTED = "[redacted]"
SENSITIVE_ARGUMENT_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "key",
    "password",
    "secret",
    "token",
}


class JsonlToolLogger:
    def __init__(self, path: Path = None, db=None):
        self.path = path
        self.db = db

    def record(self, tool: str, arguments: dict, status: str, result: str = "") -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "arguments": _redact_value(arguments),
            "status": status,
            "result_preview": _redact_text(result)[:MAX_LOG_PREVIEW_CHARS],
        }
        if self.db:
            self._record_db(entry)
        else:
            self._record_jsonl(entry)

    def _record_db(self, entry: dict) -> None:
        self.db.conn.execute(
            "INSERT INTO tool_logs (timestamp, tool, arguments_json, status, result_preview) VALUES (?, ?, ?, ?, ?)",
            (
                entry["timestamp"],
                entry["tool"],
                json.dumps(entry["arguments"], ensure_ascii=False) if isinstance(entry["arguments"], dict) else str(entry["arguments"]),
                entry["status"],
                entry["result_preview"],
            ),
        )
        self.db.conn.commit()

    def _record_jsonl(self, entry: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def list_recent(
        self,
        max_entries: int = 20,
        tool: str = "",
        status: str = "",
        include_arguments: bool = False,
    ) -> str:
        if self.db:
            return self._list_recent_db(max_entries, tool, status, include_arguments)
        return self._list_recent_jsonl(max_entries, tool, status, include_arguments)

    def _list_recent_db(self, max_entries: int, tool: str, status: str, include_arguments: bool) -> str:
        tool = tool.strip()
        status = status.strip()
        conditions = []
        params = []
        if tool:
            conditions.append("tool = ?")
            params.append(tool)
        if status:
            conditions.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        max_entries = max(1, min(max_entries, 100))
        rows = self.db.conn.execute(
            f"SELECT timestamp, tool, status, result_preview, arguments_json FROM tool_logs {where} ORDER BY id DESC LIMIT ?",
            params + [max_entries],
        ).fetchall()
        if not rows:
            return "没有工具调用日志。" if not tool and not status else "没有匹配的工具调用日志。"
        lines = []
        for row in rows:
            line = " | ".join([str(row[0]), str(row[1]), str(row[2]), str(row[3])])
            if include_arguments:
                line = f"{line} | args={str(row[4])[:MAX_LOG_PREVIEW_CHARS]}"
            lines.append(line)
        return "\n".join(lines)

    def _list_recent_jsonl(self, max_entries: int, tool: str, status: str, include_arguments: bool) -> str:
        records = self._records(tool=tool, status=status)
        if not records:
            return "没有工具调用日志。" if not tool and not status else "没有匹配的工具调用日志。"
        max_entries = max(1, min(max_entries, 100))
        lines = []
        for record in records[-max_entries:]:
            line = " | ".join(
                [
                    str(record.get("timestamp", "")),
                    str(record.get("tool", "")),
                    str(record.get("status", "")),
                    str(record.get("result_preview", "")),
                ]
            )
            if include_arguments:
                arguments = json.dumps(record.get("arguments", {}), ensure_ascii=False)
                line = f"{line} | args={arguments[:MAX_LOG_PREVIEW_CHARS]}"
            lines.append(line)
        return "\n".join(lines)

    def generate_audit_report(self, max_entries: int = 50) -> str:
        if self.db:
            return self._audit_report_db(max_entries)
        return self._audit_report_jsonl(max_entries)

    def _audit_report_db(self, max_entries: int) -> str:
        max_entries = max(1, min(max_entries, 200))
        total = self.db.conn.execute("SELECT COUNT(*) FROM tool_logs").fetchone()[0]
        if total == 0:
            return "没有工具调用日志。"
        rows = self.db.conn.execute(
            "SELECT timestamp, tool, status, result_preview, arguments_json FROM tool_logs ORDER BY id DESC LIMIT ?",
            (max_entries,),
        ).fetchall()
        return self._build_audit_report(rows, max_entries)

    def _audit_report_jsonl(self, max_entries: int) -> str:
        records = self._records()
        if not records:
            return "没有工具调用日志。"
        max_entries = max(1, min(max_entries, 200))
        selected = records[-max_entries:]
        rows = [(r.get("timestamp", ""), r.get("tool", ""), r.get("status", ""), r.get("result_preview", ""), json.dumps(r.get("arguments", {}), ensure_ascii=False)) for r in selected]
        return self._build_audit_report(rows, max_entries)

    def _build_audit_report(self, rows: list, max_entries: int) -> str:
        status_counts = {"ok": 0, "error": 0, "cancelled": 0}
        tool_counts = {}
        category_counts = {"write": 0, "terminal": 0, "git": 0, "browser_interact": 0, "process": 0}
        sensitive_hits = []
        rejected_hits = []
        last_high_risk = None

        for row in rows:
            tool = str(row[1])
            status = str(row[2])
            result_preview = str(row[3])
            status_counts[status] = status_counts.get(status, 0) + 1
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
            categories = _audit_categories(tool)
            for category in categories:
                category_counts[category] = category_counts.get(category, 0) + 1
            if categories:
                last_high_risk = row
            record_text = f"{row[0]} {row[1]} {row[2]} {row[3]} {row[4]}"
            if _mentions_sensitive_path(record_text):
                sensitive_hits.append(tool)
            if status == "cancelled" or "拒绝" in result_preview:
                rejected_hits.append(tool)

        tool_lines = [f"- {tool}: {count}" for tool, count in sorted(tool_counts.items())]
        lines = [
            f"审计范围: 最近 {len(rows)} 条工具调用",
            "",
            "## 工具调用",
            *(tool_lines or ["- 无"]),
            "",
            "## 状态统计",
            f"- success(ok): {status_counts.get('ok', 0)}",
            f"- failed(error): {status_counts.get('error', 0)}",
            f"- cancelled: {status_counts.get('cancelled', 0)}",
            "",
            "## 高风险类别",
            f"- 写操作: {category_counts.get('write', 0)}",
            f"- 终端: {category_counts.get('terminal', 0)}",
            f"- Git: {category_counts.get('git', 0)}",
            f"- 浏览器交互: {category_counts.get('browser_interact', 0)}",
            f"- process 操作: {category_counts.get('process', 0)}",
            "",
            "## 安全提示",
            f"- 涉及敏感路径: {_format_unique(sensitive_hits)}",
            f"- 被拒绝或取消操作: {_format_unique(rejected_hits)}",
            f"- 最近高风险操作: {_format_high_risk(last_high_risk)}",
        ]
        return "\n".join(lines)

    def _records(self, tool: str = "", status: str = "") -> list[dict]:
        tool = tool.strip()
        status = status.strip()
        records = read_jsonl(self.path)
        if tool:
            records = [r for r in records if r.get("tool") == tool]
        if status:
            records = [r for r in records if r.get("status") == status]
        return records


def _audit_categories(tool: str) -> list[str]:
    categories = []
    if any(term in tool for term in ["write", "replace", "apply", "save", "delete"]):
        categories.append("write")
    if "shell" in tool or "test" in tool or "repair_loop" in tool:
        categories.append("terminal")
    if tool.startswith("git_"):
        categories.append("git")
    if tool in {"browser_click", "browser_fill"}:
        categories.append("browser_interact")
    if "background_process" in tool:
        categories.append("process")
    return categories


def _mentions_sensitive_path(text: str) -> bool:
    return any(marker in text for marker in [".env", "data/", "logs/", ".git", "evals/.tmp"])


def _format_unique(items: list[str]) -> str:
    if not items:
        return "无"
    return ", ".join(sorted(set(items)))


def _format_high_risk(record) -> str:
    if not record:
        return "无"
    return " | ".join(
        [
            str(record[0] if isinstance(record, (list, tuple)) else record.get("timestamp", ""))[:200],
            str(record[1] if isinstance(record, (list, tuple)) else record.get("tool", "")),
            str(record[2] if isinstance(record, (list, tuple)) else record.get("status", "")),
            str(record[3] if isinstance(record, (list, tuple)) else record.get("result_preview", ""))[:200],
        ]
    )


def _redact_value(value: Any, key: str = "") -> Any:
    if _is_sensitive_key(key):
        return REDACTED
    if isinstance(value, dict):
        return {name: _redact_value(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item, key) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _redact_text(text: str) -> str:
    if not text:
        return text
    if is_sensitive_text(text):
        return REDACTED
    return text


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in SENSITIVE_ARGUMENT_KEYS or any(
        sensitive in normalized
        for sensitive in ("api_key", "password", "secret", "token")
    )
