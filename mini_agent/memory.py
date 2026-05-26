from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from mini_agent.tools_common import read_jsonl

SENSITIVE_MARKERS = (
    "API_KEY",
    "LLM_API_KEY",
    "OPENAI_API_KEY",
    "sk-",
    ".env",
)

SENSITIVE_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b", re.IGNORECASE),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(sk_live|pk_live|sk_test|pk_test)_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b(postgres|mysql|mongodb)://\S+", re.IGNORECASE),
)


class ConversationMemory:
    def __init__(self, max_messages: int = 20):
        self.max_messages = max(1, max_messages)
        self._messages: list[dict] = []

    def add_user(self, content: str) -> None:
        self._add({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self._add({"role": "assistant", "content": content})

    def add_message(self, message: dict) -> None:
        self._add(message)

    def messages(self) -> list[dict]:
        return [dict(message) for message in self._messages]

    def _add(self, message: dict) -> None:
        if self._is_sensitive(message):
            return

        self._messages.append(dict(message))
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages :]

    def _is_sensitive(self, message: dict) -> bool:
        content = str(message.get("content") or "")
        return is_sensitive_text(content)


class LongTermMemory:
    def __init__(self, path: Path = None, db=None):
        self.path = path
        self.db = db

    def save(self, text: str, tags: str = "") -> str:
        text = text.strip()
        if not text:
            return "请提供要保存的记忆内容。"

        if is_sensitive_text(text) or is_sensitive_text(tags):
            return "拒绝保存: 内容看起来包含敏感信息。"

        if self.db:
            return self._save_db(text, tags)
        return self._save_jsonl(text, tags)

    def _save_db(self, text: str, tags: str) -> str:
        row = self.db.conn.execute(
            "SELECT MAX(CAST(SUBSTR(id, 5) AS INTEGER)) FROM long_term_memory WHERE id LIKE 'mem_%'"
        ).fetchone()
        next_num = (row[0] or 0) + 1
        memory_id = f"mem_{next_num}"
        self.db.conn.execute(
            "INSERT INTO long_term_memory (id, text, tags, created_at) VALUES (?, ?, ?, ?)",
            (memory_id, text, _parse_tags_str(tags), datetime.now(timezone.utc).isoformat()),
        )
        self.db.conn.commit()
        return f"已保存记忆: {memory_id}"

    def _save_jsonl(self, text: str, tags: str) -> str:
        records = self._read_records()
        memory_id = f"mem_{_next_id(records, 'mem_')}"
        record = {
            "id": memory_id,
            "text": text,
            "tags": _parse_tags(tags),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return f"已保存记忆: {memory_id}"

    def search(self, query: str, max_results: int = 5) -> str:
        terms = [term.lower() for term in query.split() if term.strip()]
        if not terms:
            return "请提供搜索关键词。"

        max_results = max(1, min(max_results, 20))
        if self.db:
            return self._search_db(terms, max_results)
        return self._search_jsonl(terms, max_results)

    def _search_db(self, terms: list[str], max_results: int) -> str:
        conditions = " OR ".join(["text LIKE ? OR tags LIKE ?"] * len(terms))
        params = []
        for term in terms:
            params.extend([f"%{term}%", f"%{term}%"])
        rows = self.db.conn.execute(
            f"SELECT id, text, tags, created_at FROM long_term_memory WHERE {conditions} ORDER BY created_at DESC",
            params,
        ).fetchall()
        if not rows:
            return "没有找到相关长期记忆。"
        scored = []
        for row in rows:
            haystack = f"{row[1]} {row[2]}".lower()
            score = sum(haystack.count(term) for term in terms)
            if score > 0:
                scored.append((score, {"id": row[0], "text": row[1], "tags": row[2].split(",") if row[2] else [], "created_at": row[3]}))
        if not scored:
            return "没有找到相关长期记忆。"
        scored.sort(key=lambda item: (-item[0], item[1]["id"]))
        return "\n".join(_format_record(record) for _, record in scored[:max_results])

    def _search_jsonl(self, terms: list[str], max_results: int) -> str:
        scored = []
        for record in self._read_records():
            haystack = " ".join(
                [record.get("text", ""), " ".join(record.get("tags", []))]
            ).lower()
            score = sum(haystack.count(term) for term in terms)
            if score > 0:
                scored.append((score, record))
        if not scored:
            return "没有找到相关长期记忆。"
        scored.sort(key=lambda item: (-item[0], item[1]["id"]))
        return "\n".join(_format_record(record) for _, record in scored[:max_results])

    def list(self, max_results: int = 20) -> str:
        max_results = max(1, min(max_results, 100))
        if self.db:
            return self._list_db(max_results)
        return self._list_jsonl(max_results)

    def _list_db(self, max_results: int) -> str:
        rows = self.db.conn.execute(
            "SELECT id, text, tags, created_at FROM long_term_memory ORDER BY created_at DESC LIMIT ?",
            (max_results,),
        ).fetchall()
        if not rows:
            return "暂无长期记忆。"
        return "\n".join(
            _format_record({"id": r[0], "text": r[1], "tags": r[2].split(",") if r[2] else [], "created_at": r[3]})
            for r in rows
        )

    def _list_jsonl(self, max_results: int) -> str:
        records = self._read_records()[:max_results]
        if not records:
            return "暂无长期记忆。"
        return "\n".join(_format_record(record) for record in records)

    def delete(self, memory_id: str) -> str:
        if self.db:
            return self._delete_db(memory_id)
        return self._delete_jsonl(memory_id)

    def _delete_db(self, memory_id: str) -> str:
        cursor = self.db.conn.execute("DELETE FROM long_term_memory WHERE id = ?", (memory_id,))
        self.db.conn.commit()
        if cursor.rowcount == 0:
            return f"没有找到记忆: {memory_id}"
        return f"已删除记忆: {memory_id}"

    def _delete_jsonl(self, memory_id: str) -> str:
        records = self._read_records()
        kept = [record for record in records if record.get("id") != memory_id]
        if len(kept) == len(records):
            return f"没有找到记忆: {memory_id}"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            for record in kept:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return f"已删除记忆: {memory_id}"

    def _read_records(self) -> list[dict]:
        return read_jsonl(self.path)


def is_sensitive_text(text: str) -> bool:
    return any(marker in text for marker in SENSITIVE_MARKERS) or any(
        pattern.search(text) for pattern in SENSITIVE_PATTERNS
    )


def _next_id(records: list[dict], prefix: str) -> int:
    max_id = 0
    for record in records:
        raw = str(record.get("id", ""))
        if raw.startswith(prefix):
            try:
                max_id = max(max_id, int(raw[len(prefix):]))
            except ValueError:
                pass
    return max_id + 1


def _parse_tags(tags: str) -> list[str]:
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


def _parse_tags_str(tags: str) -> str:
    return ",".join(tag.strip() for tag in tags.split(",") if tag.strip())


def _format_record(record: dict) -> str:
    tags = ",".join(record.get("tags", [])) or "none"
    return f"{record.get('id')}: {record.get('text')} [tags={tags}]"
