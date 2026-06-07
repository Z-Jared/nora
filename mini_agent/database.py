from __future__ import annotations

import sqlite3
from pathlib import Path

_TABLES = """
CREATE TABLE IF NOT EXISTS long_term_memory (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS context_summaries (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    summary TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_history (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT,
    finished_at TEXT,
    summary TEXT,
    steps_json TEXT,
    restored_from TEXT,
    restored_at TEXT
);

CREATE TABLE IF NOT EXISTS current_task (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    goal TEXT,
    status TEXT,
    created_at TEXT,
    finished_at TEXT,
    summary TEXT,
    steps_json TEXT,
    restored_from TEXT,
    restored_at TEXT
);

CREATE TABLE IF NOT EXISTS tool_results (
    id TEXT PRIMARY KEY,
    tool TEXT NOT NULL,
    created_at TEXT NOT NULL,
    chars INTEGER NOT NULL,
    result TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    tool TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    status TEXT NOT NULL,
    result_preview TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    name TEXT PRIMARY KEY,
    saved_at TEXT NOT NULL,
    message_count INTEGER NOT NULL,
    messages_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_traces (
    trace_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    input_preview TEXT NOT NULL DEFAULT '',
    event_counts_json TEXT NOT NULL DEFAULT '{}',
    tool_calls_json TEXT NOT NULL DEFAULT '[]',
    failure TEXT NOT NULL DEFAULT ''
);

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

CREATE TABLE IF NOT EXISTS memory_records (
    record_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'project',
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 1.0,
    related_task_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ltm_created ON long_term_memory(created_at);
CREATE INDEX IF NOT EXISTS idx_cs_created ON context_summaries(created_at);
CREATE INDEX IF NOT EXISTS idx_th_created ON task_history(created_at);
CREATE INDEX IF NOT EXISTS idx_tr_created ON tool_results(created_at);
CREATE INDEX IF NOT EXISTS idx_tr_tool ON tool_results(tool);
CREATE INDEX IF NOT EXISTS idx_tl_timestamp ON tool_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_tl_tool ON tool_logs(tool);
CREATE INDEX IF NOT EXISTS idx_tl_status ON tool_logs(status);
CREATE INDEX IF NOT EXISTS idx_rt_created ON run_traces(created_at);
CREATE INDEX IF NOT EXISTS idx_de_created ON durable_events(created_at);
CREATE INDEX IF NOT EXISTS idx_de_task ON durable_events(task_id);
CREATE INDEX IF NOT EXISTS idx_de_type ON durable_events(event_type);
CREATE INDEX IF NOT EXISTS idx_de_trace ON durable_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_de_checkpoint ON durable_events(checkpoint_id);

CREATE INDEX IF NOT EXISTS idx_mr_kind ON memory_records(kind);
CREATE INDEX IF NOT EXISTS idx_mr_scope ON memory_records(scope);
CREATE INDEX IF NOT EXISTS idx_mr_created ON memory_records(created_at);
CREATE INDEX IF NOT EXISTS idx_mr_updated ON memory_records(updated_at);
CREATE INDEX IF NOT EXISTS idx_mr_task ON memory_records(related_task_id);
"""


class NoraDB:
    """Single SQLite database for all Nora stores."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_TABLES)
        self._conn.executescript(_INDEXES)

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def close(self) -> None:
        self._conn.close()

    def table_count(self, table: str) -> int:
        row = self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return row[0] if row else 0

    def has_data(self, table: str) -> bool:
        return self.table_count(table) > 0
