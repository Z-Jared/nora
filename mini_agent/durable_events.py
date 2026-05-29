"""Durable event log for Nora runtime lifecycle events."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


TASK_CREATED = "task_created"
TASK_FINISHED = "task_finished"
TASK_STATUS_CHANGED = "task_status_changed"
STEP_UPDATED = "step_updated"
CHECKPOINT_ADDED = "checkpoint_added"
TASK_RETRIED = "task_retried"
TRACE_LINKED = "trace_linked"
ERROR = "error"

VALID_EVENT_TYPES = {
    TASK_CREATED,
    TASK_FINISHED,
    TASK_STATUS_CHANGED,
    STEP_UPDATED,
    CHECKPOINT_ADDED,
    TASK_RETRIED,
    TRACE_LINKED,
    ERROR,
}

_DURABLE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS durable_events (
    event_id TEXT PRIMARY KEY,
    task_id TEXT,
    event_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    trace_id TEXT,
    checkpoint_id TEXT,
    worker_id TEXT,
    source TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL DEFAULT 'info'
);
"""

_DURABLE_EVENTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_de_created ON durable_events(created_at);
CREATE INDEX IF NOT EXISTS idx_de_task ON durable_events(task_id);
CREATE INDEX IF NOT EXISTS idx_de_type ON durable_events(event_type);
CREATE INDEX IF NOT EXISTS idx_de_trace ON durable_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_de_checkpoint ON durable_events(checkpoint_id);
"""


@dataclass(frozen=True)
class DurableEvent:
    event_id: str
    task_id: Optional[str]
    event_type: str
    created_at: str
    summary: str = ""
    payload: dict = field(default_factory=dict)
    trace_id: Optional[str] = None
    checkpoint_id: Optional[str] = None
    worker_id: Optional[str] = None
    source: str = ""
    severity: str = "info"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DurableEvent":
        return cls(
            event_id=data["event_id"],
            task_id=data.get("task_id"),
            event_type=data["event_type"],
            created_at=data["created_at"],
            summary=data.get("summary", ""),
            payload=data.get("payload", {}),
            trace_id=data.get("trace_id"),
            checkpoint_id=data.get("checkpoint_id"),
            worker_id=data.get("worker_id"),
            source=data.get("source", ""),
            severity=data.get("severity", "info"),
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_id(prefix: str, existing_ids: list[str]) -> str:
    max_num = 0
    for event_id in existing_ids:
        if not event_id.startswith(prefix):
            continue
        try:
            max_num = max(max_num, int(event_id[len(prefix):]))
        except ValueError:
            continue
    return f"{prefix}{max_num + 1}"


class DurableEventStore:
    """Append-only event store with SQLite and JSONL backends."""

    def __init__(self, path: Path = None, db=None):
        self.path = path or Path("data/durable_events.jsonl")
        self.db = db
        self._table_created = False

    def record(
        self,
        event_type: str,
        task_id: Optional[str] = None,
        summary: str = "",
        payload: Optional[dict] = None,
        trace_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
        worker_id: Optional[str] = None,
        source: str = "",
        severity: str = "info",
    ) -> DurableEvent:
        event = DurableEvent(
            event_id=_next_id("devt_", self._all_ids()),
            task_id=task_id,
            event_type=event_type,
            created_at=_now_iso(),
            summary=summary,
            payload=payload or {},
            trace_id=trace_id,
            checkpoint_id=checkpoint_id,
            worker_id=worker_id,
            source=source,
            severity=severity,
        )
        if self.db:
            self._insert_db(event)
        else:
            self._append_jsonl(event)
        return event

    def list_events(self, task_id: str = "", max_results: int = 50) -> list[DurableEvent]:
        max_results = max(1, min(int(max_results or 50), 500))
        if self.db:
            return self._list_db(task_id=task_id.strip(), max_results=max_results)
        events = self._read_jsonl()
        if task_id.strip():
            events = [event for event in events if event.task_id == task_id.strip()]
        return events[-max_results:][::-1]

    def get_event(self, event_id: str) -> Optional[DurableEvent]:
        if self.db:
            return self._get_db(event_id)
        for event in self._read_jsonl():
            if event.event_id == event_id:
                return event
        return None

    def _ensure_table(self) -> None:
        if self.db and not self._table_created:
            self.db.conn.executescript(_DURABLE_EVENTS_TABLE)
            self.db.conn.executescript(_DURABLE_EVENTS_INDEXES)
            self._table_created = True

    def _insert_db(self, event: DurableEvent) -> None:
        self._ensure_table()
        self.db.conn.execute(
            """INSERT INTO durable_events
               (event_id, task_id, event_type, created_at, summary, payload_json,
                trace_id, checkpoint_id, worker_id, source, severity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                event.task_id,
                event.event_type,
                event.created_at,
                event.summary,
                json.dumps(event.payload, ensure_ascii=False),
                event.trace_id,
                event.checkpoint_id,
                event.worker_id,
                event.source,
                event.severity,
            ),
        )
        self.db.conn.commit()

    def _list_db(self, task_id: str, max_results: int) -> list[DurableEvent]:
        self._ensure_table()
        if task_id:
            rows = self.db.conn.execute(
                """SELECT event_id, task_id, event_type, created_at, summary,
                          payload_json, trace_id, checkpoint_id, worker_id,
                          source, severity
                   FROM durable_events
                   WHERE task_id = ?
                   ORDER BY rowid DESC LIMIT ?""",
                (task_id, max_results),
            ).fetchall()
        else:
            rows = self.db.conn.execute(
                """SELECT event_id, task_id, event_type, created_at, summary,
                          payload_json, trace_id, checkpoint_id, worker_id,
                          source, severity
                   FROM durable_events
                   ORDER BY rowid DESC LIMIT ?""",
                (max_results,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def _get_db(self, event_id: str) -> Optional[DurableEvent]:
        self._ensure_table()
        row = self.db.conn.execute(
            """SELECT event_id, task_id, event_type, created_at, summary,
                      payload_json, trace_id, checkpoint_id, worker_id,
                      source, severity
               FROM durable_events
               WHERE event_id = ?""",
            (event_id,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_event(row)

    def _row_to_event(self, row) -> DurableEvent:
        return DurableEvent(
            event_id=row[0],
            task_id=row[1],
            event_type=row[2],
            created_at=row[3],
            summary=row[4] or "",
            payload=json.loads(row[5] or "{}"),
            trace_id=row[6],
            checkpoint_id=row[7],
            worker_id=row[8],
            source=row[9] or "",
            severity=row[10] or "info",
        )

    def _all_ids(self) -> list[str]:
        if self.db:
            self._ensure_table()
            rows = self.db.conn.execute("SELECT event_id FROM durable_events").fetchall()
            return [row[0] for row in rows]
        return [event.event_id for event in self._read_jsonl()]

    def _append_jsonl(self, event: DurableEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def _read_jsonl(self) -> list[DurableEvent]:
        if not self.path.exists():
            return []
        events = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(DurableEvent.from_dict(json.loads(line)))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        return events
