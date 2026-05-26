from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mini_agent.memory import ConversationMemory, is_sensitive_text
from mini_agent.tools_common import read_jsonl


class SessionStore:
    def __init__(self, directory: Path):
        self.directory = directory

    def save(self, memory: ConversationMemory, name: str = "") -> str:
        messages = memory.messages()
        if not messages:
            return "当前没有对话记录可保存。"

        if not name:
            name = datetime.now(timezone.utc).strftime("session_%Y%m%d_%H%M%S")

        if is_sensitive_text(name):
            return "拒绝保存: 会话名称包含敏感信息。"

        safe_name = "".join(c for c in name if c.isalnum() or c in "-_").strip()
        if not safe_name:
            return "会话名称无效，只允许字母、数字、减号和下划线。"

        path = self._path(safe_name)
        path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "name": safe_name,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(messages),
        }
        with path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            for message in messages:
                f.write(json.dumps(message, ensure_ascii=False) + "\n")

        return f"已保存会话: {safe_name} ({len(messages)} 条消息)"

    def load(self, name: str, memory: ConversationMemory) -> str:
        path = self._path(name)
        if not path.exists():
            return f"未找到会话: {name}"

        records = read_jsonl(path)
        if len(records) < 2:
            return f"会话文件损坏: {name}"

        meta = records[0]
        messages = records[1:]

        memory._messages.clear()
        for message in messages:
            if isinstance(message, dict) and "role" in message and "content" in message:
                memory._messages.append(message)

        return f"已恢复会话: {name} ({meta.get('message_count', len(messages))} 条消息)"

    def list_sessions(self) -> str:
        if not self.directory.exists():
            return "暂无保存的会话。"

        sessions = []
        for path in sorted(self.directory.glob("*.jsonl")):
            records = read_jsonl(path)
            if records:
                meta = records[0]
                sessions.append(
                    f"- {meta.get('name', path.stem)}: "
                    f"{meta.get('message_count', '?')} 条消息, "
                    f"保存于 {meta.get('saved_at', '?')}"
                )

        if not sessions:
            return "暂无保存的会话。"
        return "\n".join(sessions)

    def _path(self, name: str) -> Path:
        return self.directory / f"{name}.jsonl"
