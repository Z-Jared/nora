from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List

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
    def __init__(self, path: Path):
        self.path = path

    def save(self, text: str, tags: str = "") -> str:
        text = text.strip()
        if not text:
            return "请提供要保存的记忆内容。"

        if is_sensitive_text(text) or is_sensitive_text(tags):
            return "拒绝保存: 内容看起来包含敏感信息。"

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
        records = self._read_records()[:max_results]
        if not records:
            return "暂无长期记忆。"

        return "\n".join(_format_record(record) for record in records)

    def delete(self, memory_id: str) -> str:
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


def _format_record(record: dict) -> str:
    tags = ",".join(record.get("tags", [])) or "none"
    return f"{record.get('id')}: {record.get('text')} [tags={tags}]"
