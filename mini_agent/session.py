from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mini_agent.memory import ConversationMemory, is_sensitive_text
from mini_agent.tools_common import read_jsonl


class SessionStore:
    def __init__(self, directory: Path = None, db=None):
        self.directory = directory
        self.db = db

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

        if self.db:
            return self._save_db(safe_name, messages)
        return self._save_jsonl(safe_name, messages)

    def _save_db(self, name: str, messages: list[dict]) -> str:
        self.db.conn.execute(
            "INSERT OR REPLACE INTO sessions (name, saved_at, message_count, messages_json) VALUES (?, ?, ?, ?)",
            (name, datetime.now(timezone.utc).isoformat(), len(messages), json.dumps(messages, ensure_ascii=False)),
        )
        self.db.conn.commit()
        return f"已保存会话: {name} ({len(messages)} 条消息)"

    def _save_jsonl(self, name: str, messages: list[dict]) -> str:
        path = self._path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "name": name,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(messages),
        }
        with path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            for message in messages:
                f.write(json.dumps(message, ensure_ascii=False) + "\n")
        return f"已保存会话: {name} ({len(messages)} 条消息)"

    def load(self, name: str, memory: ConversationMemory) -> str:
        if self.db:
            return self._load_db(name, memory)
        return self._load_jsonl(name, memory)

    def _load_db(self, name: str, memory: ConversationMemory) -> str:
        row = self.db.conn.execute(
            "SELECT message_count, messages_json FROM sessions WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            return f"未找到会话: {name}"
        try:
            messages = json.loads(row[1])
        except (json.JSONDecodeError, TypeError):
            return f"会话数据损坏: {name}"
        memory._messages.clear()
        for message in messages:
            if isinstance(message, dict) and "role" in message and "content" in message:
                memory._messages.append(message)
        return f"已恢复会话: {name} ({row[0]} 条消息)"

    def _load_jsonl(self, name: str, memory: ConversationMemory) -> str:
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
        if self.db:
            return self._list_sessions_db()
        return self._list_sessions_jsonl()

    def list_sessions_structured(self) -> list[dict]:
        if self.db:
            return self._list_sessions_structured_db()
        return self._list_sessions_structured_jsonl()

    def _list_sessions_structured_db(self) -> list[dict]:
        rows = self.db.conn.execute(
            "SELECT name, message_count, saved_at FROM sessions ORDER BY saved_at DESC"
        ).fetchall()
        return [{"name": r[0], "message_count": r[1], "saved_at": r[2]} for r in rows]

    def _list_sessions_structured_jsonl(self) -> list[dict]:
        if not self.directory or not self.directory.exists():
            return []
        sessions = []
        for path in sorted(self.directory.glob("*.jsonl")):
            records = read_jsonl(path)
            if records:
                meta = records[0]
                sessions.append({
                    "name": meta.get("name", path.stem),
                    "message_count": meta.get("message_count", 0),
                    "saved_at": meta.get("saved_at", ""),
                })
        return sessions

    def _list_sessions_db(self) -> str:
        rows = self.db.conn.execute(
            "SELECT name, message_count, saved_at FROM sessions ORDER BY saved_at DESC"
        ).fetchall()
        if not rows:
            return "暂无保存的会话。"
        return "\n".join(f"- {r[0]}: {r[1]} 条消息, 保存于 {r[2]}" for r in rows)

    def _list_sessions_jsonl(self) -> str:
        if not self.directory or not self.directory.exists():
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
