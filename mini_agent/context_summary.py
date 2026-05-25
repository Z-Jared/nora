import json
from datetime import datetime, timezone
from pathlib import Path

from mini_agent.memory import is_sensitive_text


class ContextSummaryStore:
    def __init__(self, path: Path):
        self.path = path

    def save_summary(self, topic: str, summary: str, source: str = "") -> str:
        topic = topic.strip()
        summary = summary.strip()
        source = source.strip()
        if not topic or not summary:
            return "请提供 topic 和 summary。"
        if is_sensitive_text(topic) or is_sensitive_text(summary) or is_sensitive_text(source):
            return "拒绝保存上下文摘要: 内容看起来包含敏感信息。"

        records = self._read_records()
        summary_id = f"ctx_{len(records) + 1}"
        record = {
            "id": summary_id,
            "topic": topic,
            "summary": summary,
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return f"已保存上下文摘要: {summary_id}"

    def search_summaries(self, query: str, max_results: int = 10) -> str:
        terms = [term.lower() for term in query.split() if term.strip()]
        if not terms:
            return "请提供搜索关键词。"
        max_results = max(1, min(max_results, 50))
        scored = []
        for record in self._read_records():
            haystack = " ".join([record.get("topic", ""), record.get("summary", ""), record.get("source", "")]).lower()
            score = sum(haystack.count(term) for term in terms)
            if score > 0:
                scored.append((score, record))
        if not scored:
            return "没有找到相关上下文摘要。"
        scored.sort(key=lambda item: (-item[0], item[1].get("id", "")))
        return "\n".join(_format_record(record) for _, record in scored[:max_results])

    def list_summaries(self, max_results: int = 20) -> str:
        max_results = max(1, min(max_results, 100))
        records = self._read_records()[-max_results:]
        if not records:
            return "暂无上下文摘要。"
        return "\n".join(_format_record(record) for record in records)

    def _read_records(self) -> list[dict]:
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


def _format_record(record: dict) -> str:
    source = f" source={record.get('source')}" if record.get("source") else ""
    return f"{record.get('id')}: {record.get('topic')} - {record.get('summary')}{source}"
