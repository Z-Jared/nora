from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mini_agent.memory import is_sensitive_text
from mini_agent.tools_common import read_jsonl


class ContextSummaryStore:
    def __init__(self, path: Path = None, db=None):
        self.path = path
        self.db = db

    def save_summary(self, topic: str, summary: str, source: str = "") -> str:
        topic = topic.strip()
        summary = summary.strip()
        source = source.strip()
        if not topic or not summary:
            return "请提供 topic 和 summary。"
        if is_sensitive_text(topic) or is_sensitive_text(summary) or is_sensitive_text(source):
            return "拒绝保存上下文摘要: 内容看起来包含敏感信息。"

        if self.db:
            return self._save_db(topic, summary, source)
        return self._save_jsonl(topic, summary, source)

    def _save_db(self, topic: str, summary: str, source: str) -> str:
        row = self.db.conn.execute(
            "SELECT MAX(CAST(SUBSTR(id, 5) AS INTEGER)) FROM context_summaries WHERE id LIKE 'ctx_%'"
        ).fetchone()
        next_num = (row[0] or 0) + 1
        summary_id = f"ctx_{next_num}"
        self.db.conn.execute(
            "INSERT INTO context_summaries (id, topic, summary, source, created_at) VALUES (?, ?, ?, ?, ?)",
            (summary_id, topic, summary, source, datetime.now(timezone.utc).isoformat()),
        )
        self.db.conn.commit()
        return f"已保存上下文摘要: {summary_id}"

    def _save_jsonl(self, topic: str, summary: str, source: str) -> str:
        records = self._read_records()
        summary_id = f"ctx_{_next_id(records, 'ctx_')}"
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
        if self.db:
            return self._search_db(terms, max_results)
        return self._search_jsonl(terms, max_results)

    def _search_db(self, terms: list[str], max_results: int) -> str:
        conditions = " OR ".join(["topic LIKE ? OR summary LIKE ? OR source LIKE ?"] * len(terms))
        params = []
        for term in terms:
            params.extend([f"%{term}%", f"%{term}%", f"%{term}%"])
        rows = self.db.conn.execute(
            f"SELECT id, topic, summary, source, created_at FROM context_summaries WHERE {conditions} ORDER BY created_at DESC",
            params,
        ).fetchall()
        if not rows:
            return "没有找到相关上下文摘要。"
        scored = []
        for row in rows:
            haystack = f"{row[1]} {row[2]} {row[3]}".lower()
            score = sum(haystack.count(term) for term in terms)
            if score > 0:
                scored.append((score, {"id": row[0], "topic": row[1], "summary": row[2], "source": row[3], "created_at": row[4]}))
        if not scored:
            return "没有找到相关上下文摘要。"
        scored.sort(key=lambda item: (-item[0], item[1].get("id", "")))
        return "\n".join(_format_record(record) for _, record in scored[:max_results])

    def _search_jsonl(self, terms: list[str], max_results: int) -> str:
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
        if self.db:
            return self._list_db(max_results)
        return self._list_jsonl(max_results)

    def _list_db(self, max_results: int) -> str:
        rows = self.db.conn.execute(
            "SELECT id, topic, summary, source, created_at FROM context_summaries ORDER BY created_at DESC LIMIT ?",
            (max_results,),
        ).fetchall()
        if not rows:
            return "暂无上下文摘要。"
        return "\n".join(
            _format_record({"id": r[0], "topic": r[1], "summary": r[2], "source": r[3], "created_at": r[4]})
            for r in rows
        )

    def _list_jsonl(self, max_results: int) -> str:
        records = self._read_records()[-max_results:]
        if not records:
            return "暂无上下文摘要。"
        return "\n".join(_format_record(record) for record in records)

    def _read_records(self) -> list[dict]:
        return read_jsonl(self.path)


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


def _format_record(record: dict) -> str:
    source = f" source={record.get('source')}" if record.get("source") else ""
    return f"{record.get('id')}: {record.get('topic')} - {record.get('summary')}{source}"
