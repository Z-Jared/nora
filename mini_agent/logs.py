import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mini_agent.memory import is_sensitive_text

MAX_LOG_PREVIEW_CHARS = 500
REDACTED = "[redacted]"
SENSITIVE_ARGUMENT_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "content",
    "key",
    "password",
    "patch",
    "secret",
    "text",
    "token",
}


class JsonlToolLogger:
    def __init__(self, path: Path):
        self.path = path

    def record(self, tool: str, arguments: dict, status: str, result: str = "") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "arguments": _redact_value(arguments),
            "status": status,
            "result_preview": _redact_text(result)[:MAX_LOG_PREVIEW_CHARS],
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def list_recent(
        self,
        max_entries: int = 20,
        tool: str = "",
        status: str = "",
        include_arguments: bool = False,
    ) -> str:
        if not self.path.exists():
            return "没有工具调用日志。"

        max_entries = max(1, min(max_entries, 100))
        tool = tool.strip()
        status = status.strip()
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if tool and record.get("tool") != tool:
                continue
            if status and record.get("status") != status:
                continue
            records.append(record)

        if not records:
            return "没有匹配的工具调用日志。"

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
