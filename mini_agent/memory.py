import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List


SENSITIVE_MARKERS = (
    "API_KEY",
    "LLM_API_KEY",
    "OPENAI_API_KEY",
    "sk-",
    ".env",
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
        memory_id = f"mem_{len(records) + 1}"
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

    def _read_records(self) -> List[dict]:
        if not self.path.exists():
            return []

        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records


def is_sensitive_text(text: str) -> bool:
    return any(marker in text for marker in SENSITIVE_MARKERS)


def _parse_tags(tags: str) -> list[str]:
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


def _format_record(record: dict) -> str:
    tags = ",".join(record.get("tags", [])) or "none"
    return f"{record.get('id')}: {record.get('text')} [tags={tags}]"
