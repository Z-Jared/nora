"""Lightweight run trace store for Nora agent turns.

Records one trace per MiniAgent.run_events() turn with:
- trace_id, created_at, status
- user input preview (truncated, never full prompt)
- event counts by type
- tool calls: name/status/result_preview only
- failure text when blocked/error

Supports SQLite (via NoraDB) and JSONL fallback.
Does NOT store raw API keys, tokens, full prompts, full model outputs, or full tool results.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mini_agent.memory import is_sensitive_text


_INPUT_PREVIEW_LIMIT = 200
_RESULT_PREVIEW_LIMIT = 200
_REDACTED = "[redacted]"


@dataclass(frozen=True)
class ToolCallTrace:
    name: str
    status: str
    result_preview: str


@dataclass(frozen=True)
class RunTrace:
    trace_id: str
    created_at: str
    status: str
    input_preview: str
    event_counts: dict[str, int]
    tool_calls: list[ToolCallTrace]
    failure: str = ""

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "created_at": self.created_at,
            "status": self.status,
            "input_preview": self.input_preview,
            "event_counts": self.event_counts,
            "tool_calls": [asdict(tc) for tc in self.tool_calls],
            "failure": self.failure,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RunTrace:
        tool_calls = [
            ToolCallTrace(**tc) for tc in data.get("tool_calls", [])
        ]
        return cls(
            trace_id=data["trace_id"],
            created_at=data["created_at"],
            status=data["status"],
            input_preview=data["input_preview"],
            event_counts=data.get("event_counts", {}),
            tool_calls=tool_calls,
            failure=data.get("failure", ""),
        )


def truncate_preview(text: str, limit: int = _INPUT_PREVIEW_LIMIT) -> str:
    text = text.strip()
    if is_sensitive_text(text):
        return _REDACTED
    if len(text) <= limit:
        return text
    preview = text[:limit].rstrip() + "…"
    if is_sensitive_text(preview):
        return _REDACTED
    return preview


def build_trace(
    trace_id: str,
    user_input: str,
    status: str,
    events: list[dict],
    tool_records: list,
    failure: str = "",
) -> RunTrace:
    """Build a RunTrace from collected run data.

    tool_records: objects with .name, .status, .result_preview attributes
    (ToolRunRecord from controller).
    """
    event_counts: dict[str, int] = {}
    for evt in events:
        evt_type = evt.get("type", "unknown")
        event_counts[evt_type] = event_counts.get(evt_type, 0) + 1

    tool_calls = [
        ToolCallTrace(
            name=getattr(r, "name", str(r)),
            status=getattr(r, "status", "ok"),
            result_preview=truncate_preview(
                getattr(r, "result_preview", ""), _RESULT_PREVIEW_LIMIT
            ),
        )
        for r in tool_records
    ]

    return RunTrace(
        trace_id=trace_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        input_preview=truncate_preview(user_input),
        event_counts=event_counts,
        tool_calls=tool_calls,
        failure=truncate_preview(failure or ""),
    )


def _next_trace_id(records: list[dict]) -> str:
    max_num = 0
    for r in records:
        tid = r.get("trace_id", "")
        if tid.startswith("trace_"):
            try:
                num = int(tid[6:])
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return f"trace_{max_num + 1}"


class TraceStore:
    """Run trace storage with SQLite (via NoraDB) or JSONL fallback."""

    def __init__(self, directory: Path = None, db=None):
        self.directory = directory
        self.db = db

    def record(self, trace: RunTrace) -> str:
        """Store a trace and return its trace_id."""
        if self.db:
            return self._record_db(trace)
        return self._record_jsonl(trace)

    def list_traces(self, max_results: int = 50) -> list[dict]:
        """Return recent traces as dicts (most recent first)."""
        if self.db:
            return self._list_db(max_results)
        return self._list_jsonl(max_results)

    def get_trace(self, trace_id: str) -> Optional[dict]:
        """Return a single trace dict or None."""
        if self.db:
            return self._get_db(trace_id)
        return self._get_jsonl(trace_id)

    # --- SQLite backend ---

    def _record_db(self, trace: RunTrace) -> str:
        self.db.conn.execute(
            """INSERT INTO run_traces
               (trace_id, created_at, status, input_preview,
                event_counts_json, tool_calls_json, failure)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                trace.trace_id,
                trace.created_at,
                trace.status,
                trace.input_preview,
                json.dumps(trace.event_counts, ensure_ascii=False),
                json.dumps([asdict(tc) for tc in trace.tool_calls], ensure_ascii=False),
                trace.failure,
            ),
        )
        self.db.conn.commit()
        return trace.trace_id

    def _list_db(self, max_results: int) -> list[dict]:
        rows = self.db.conn.execute(
            """SELECT trace_id, created_at, status, input_preview,
                      event_counts_json, tool_calls_json, failure
               FROM run_traces ORDER BY rowid DESC LIMIT ?""",
            (max_results,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def _get_db(self, trace_id: str) -> Optional[dict]:
        row = self.db.conn.execute(
            """SELECT trace_id, created_at, status, input_preview,
                      event_counts_json, tool_calls_json, failure
               FROM run_traces WHERE trace_id = ?""",
            (trace_id,),
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def _row_to_dict(self, row) -> dict:
        tool_calls_raw = json.loads(row[5]) if row[5] else []
        return {
            "trace_id": row[0],
            "created_at": row[1],
            "status": row[2],
            "input_preview": row[3],
            "event_counts": json.loads(row[4]) if row[4] else {},
            "tool_calls": tool_calls_raw,
            "failure": row[6] or "",
        }

    # --- JSONL backend ---

    def _record_jsonl(self, trace: RunTrace) -> str:
        if self.directory:
            self.directory.mkdir(parents=True, exist_ok=True)
        path = self._jsonl_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trace.to_dict(), ensure_ascii=False) + "\n")
        return trace.trace_id

    def _list_jsonl(self, max_results: int) -> list[dict]:
        records = self._read_all()
        return records[-max_results:][::-1]

    def _get_jsonl(self, trace_id: str) -> Optional[dict]:
        for record in self._read_all():
            if record.get("trace_id") == trace_id:
                return record
        return None

    def _read_all(self) -> list[dict]:
        path = self._jsonl_path()
        if not path.exists():
            return []
        records = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def _jsonl_path(self) -> Path:
        if self.directory:
            return self.directory / "traces.jsonl"
        return Path("traces.jsonl")

    # --- Auto-ID support ---

    def next_trace_id(self) -> str:
        """Generate the next trace_id."""
        if self.db:
            row = self.db.conn.execute(
                "SELECT MAX(CAST(SUBSTR(trace_id, 7) AS INTEGER)) FROM run_traces WHERE trace_id LIKE 'trace_%'"
            ).fetchone()
            max_num = row[0] or 0
            return f"trace_{max_num + 1}"
        records = self._read_all()
        return _next_trace_id(records)
