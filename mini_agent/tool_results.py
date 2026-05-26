from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mini_agent.memory import is_sensitive_text
from mini_agent.tools_common import read_jsonl


MAX_STORED_RESULT_CHARS = 200_000
MAX_READ_LIMIT = 20_000
MAX_SEARCH_RESULTS = 20


class ToolResultStore:
    def __init__(self, path: Path = None, db=None):
        self.path = path
        self.db = db

    def save(self, tool: str, result: str) -> str:
        if is_sensitive_text(result):
            return ""
        result = result[:MAX_STORED_RESULT_CHARS]
        if self.db:
            return self._save_db(tool, result)
        return self._save_jsonl(tool, result)

    def _save_db(self, tool: str, result: str) -> str:
        row = self.db.conn.execute(
            "SELECT MAX(CAST(SUBSTR(id, 4) AS INTEGER)) FROM tool_results WHERE id LIKE 'tr_%'"
        ).fetchone()
        next_num = (row[0] or 0) + 1
        result_id = f"tr_{next_num}"
        self.db.conn.execute(
            "INSERT INTO tool_results (id, tool, created_at, chars, result) VALUES (?, ?, ?, ?, ?)",
            (result_id, tool, datetime.now(timezone.utc).isoformat(), len(result), result),
        )
        self.db.conn.commit()
        return result_id

    def _save_jsonl(self, tool: str, result: str) -> str:
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
        if self.db:
            return self._list_db(max_results)
        return self._list_jsonl(max_results)

    def _list_db(self, max_results: int) -> str:
        rows = self.db.conn.execute(
            "SELECT id, tool, chars, created_at FROM tool_results ORDER BY rowid DESC LIMIT ?",
            (max_results,),
        ).fetchall()
        if not rows:
            return "没有缓存的工具结果。"
        return "\n".join(f"{r[0]} | {r[1]} | {r[2]} chars | {r[3]}" for r in rows)

    def _list_jsonl(self, max_results: int) -> str:
        records = self._read_records()
        if not records:
            return "没有缓存的工具结果。"
        return "\n".join(
            f"{r.get('id')} | {r.get('tool')} | {r.get('chars')} chars | {r.get('created_at')}"
            for r in records[-max_results:]
        )

    def read(self, result_id: str, offset: int = 0, limit: int = 4000) -> str:
        result_id = result_id.strip()
        if not result_id:
            return "请提供 result_id。"
        offset = max(0, offset)
        limit = max(1, min(limit, MAX_READ_LIMIT))
        if self.db:
            return self._read_db(result_id, offset, limit)
        return self._read_jsonl(result_id, offset, limit)

    def _read_db(self, result_id: str, offset: int, limit: int) -> str:
        row = self.db.conn.execute(
            "SELECT result FROM tool_results WHERE id = ?", (result_id,)
        ).fetchone()
        if not row:
            return f"没有找到工具结果: {result_id}"
        result = row[0] or ""
        end = min(len(result), offset + limit)
        chunk = result[offset:end]
        header = f"{result_id} offset={offset} limit={limit} chars={len(result)} shown={len(chunk)}"
        return header + "\n" + chunk

    def _read_jsonl(self, result_id: str, offset: int, limit: int) -> str:
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
        if self.db:
            return self._search_db(result_id, query, max_results)
        return self._search_jsonl(result_id, query, max_results)

    def _search_db(self, result_id: str, query: str, max_results: int) -> str:
        if result_id:
            rows = self.db.conn.execute(
                "SELECT id, tool, result FROM tool_results WHERE id = ?", (result_id,)
            ).fetchall()
        else:
            rows = self.db.conn.execute(
                "SELECT id, tool, result FROM tool_results"
            ).fetchall()
        matches = []
        for row in rows:
            result = row[2] or ""
            for line_number, line in enumerate(result.splitlines(), start=1):
                if query in line.lower():
                    matches.append(({"id": row[0], "tool": row[1]}, line_number, line.strip()))
                    if len(matches) >= max_results:
                        return _format_matches(matches)
        if not matches:
            return "没有找到匹配的工具结果。"
        return _format_matches(matches)

    def _search_jsonl(self, result_id: str, query: str, max_results: int) -> str:
        records = self._read_records()
        if result_id:
            records = [r for r in records if r.get("id") == result_id]
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
