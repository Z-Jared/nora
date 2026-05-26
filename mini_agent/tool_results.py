from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from mini_agent.memory import is_sensitive_text
from mini_agent.tools_common import read_jsonl


MAX_STORED_RESULT_CHARS = 200_000
MAX_READ_LIMIT = 20_000
MAX_SEARCH_RESULTS = 20


class ToolResultStore:
    def __init__(self, path: Path):
        self.path = path

    def save(self, tool: str, result: str) -> str:
        if is_sensitive_text(result):
            return ""
        result = result[:MAX_STORED_RESULT_CHARS]
        records = self._read_records()
        result_id = f"tr_{_next_id(records, 'tr_')}"
        record = {
            "id": result_id,
            "tool": tool,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "chars": len(result),
            "result": result,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return result_id

    def list(self, max_results: int = 20) -> str:
        max_results = max(1, min(max_results, 100))
        records = self._read_records()
        if not records:
            return "没有缓存的工具结果。"
        lines = []
        for record in records[-max_results:]:
            lines.append(
                f"{record.get('id')} | {record.get('tool')} | {record.get('chars')} chars | {record.get('created_at')}"
            )
        return "\n".join(lines)

    def read(self, result_id: str, offset: int = 0, limit: int = 4000) -> str:
        result_id = result_id.strip()
        if not result_id:
            return "请提供 result_id。"
        offset = max(0, offset)
        limit = max(1, min(limit, MAX_READ_LIMIT))
        record = self._find(result_id)
        if record is None:
            return f"没有找到工具结果: {result_id}"
        result = str(record.get("result", ""))
        end = min(len(result), offset + limit)
        chunk = result[offset:end]
        header = f"{result_id} offset={offset} limit={limit} chars={len(result)} shown={len(chunk)}"
        return header + "\n" + chunk

    def search(self, result_id: str = "", query: str = "", max_results: int = 10) -> str:
        query = query.strip().lower()
        result_id = result_id.strip()
        max_results = max(1, min(max_results, MAX_SEARCH_RESULTS))
        if not query:
            return "请提供搜索关键词。"
        records = self._read_records()
        if result_id:
            records = [record for record in records if record.get("id") == result_id]
        matches = []
        for record in records:
            result = str(record.get("result", ""))
            for line_number, line in enumerate(result.splitlines(), start=1):
                if query in line.lower():
                    matches.append((record, line_number, line.strip()))
                    if len(matches) >= max_results:
                        return _format_matches(matches)
        if not matches:
            return "没有找到匹配的工具结果。"
        return _format_matches(matches)

    def _find(self, result_id: str) -> Optional[dict]:
        for record in self._read_records():
            if record.get("id") == result_id:
                return record
        return None

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


def _format_matches(matches: list[tuple[dict, int, str]]) -> str:
    lines = []
    for record, line_number, line in matches:
        lines.append(f"{record.get('id')}:{line_number} {record.get('tool')} | {line[:500]}")
    return "\n".join(lines)
