"""Durable worker registry for Nora agent.

Provides DurableWorker data structure and DurableWorkerStore
with SQLite (via NoraDB) and JSONL backends.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class WorkerStatus(str, Enum):
    IDLE = "idle"
    ASSIGNED = "assigned"
    RUNNING = "running"
    PAUSED = "paused"
    OFFLINE = "offline"


_DURABLE_WORKERS_TABLE = """
CREATE TABLE IF NOT EXISTS durable_workers (
    worker_id TEXT PRIMARY KEY,
    role TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'idle',
    current_task_id TEXT,
    workspace_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);
"""

_DURABLE_WORKERS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_dw_status ON durable_workers(status);
CREATE INDEX IF NOT EXISTS idx_dw_updated ON durable_workers(updated_at);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DurableWorker:
    worker_id: str
    role: str = ""
    status: str = WorkerStatus.IDLE
    current_task_id: Optional[str] = None
    workspace_path: str = ""
    created_at: str = ""
    updated_at: str = ""
    last_seen_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DurableWorker":
        return cls(
            worker_id=data["worker_id"],
            role=data.get("role", ""),
            status=data.get("status", WorkerStatus.IDLE),
            current_task_id=data.get("current_task_id"),
            workspace_path=data.get("workspace_path", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            last_seen_at=data.get("last_seen_at", ""),
        )


class DurableWorkerStore:
    """Durable worker storage with SQLite (via NoraDB) or JSONL fallback."""

    def __init__(self, path: Path = None, db=None):
        self.path = path or Path("data/durable_workers.jsonl")
        self.db = db
        self._table_created = False

    def _ensure_table(self) -> None:
        if self.db and not self._table_created:
            self.db.conn.executescript(_DURABLE_WORKERS_TABLE)
            self.db.conn.executescript(_DURABLE_WORKERS_INDEX)
            self._table_created = True

    def register_worker(
        self,
        worker_id: str,
        role: str = "",
        status: str = WorkerStatus.IDLE,
        workspace_path: str = "",
    ) -> DurableWorker:
        now = _now_iso()
        existing = self.get_worker(worker_id)
        if existing:
            existing.role = role or existing.role
            existing.status = status if status != WorkerStatus.IDLE else existing.status
            existing.workspace_path = workspace_path or existing.workspace_path
            existing.updated_at = now
            existing.last_seen_at = now
            self._save(existing)
            return existing

        worker = DurableWorker(
            worker_id=worker_id,
            role=role,
            status=status,
            workspace_path=workspace_path,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )
        self._save(worker)
        return worker

    def get_worker(self, worker_id: str) -> Optional[DurableWorker]:
        if self.db:
            return self._get_db(worker_id)
        return self._get_jsonl(worker_id)

    def list_workers(self, limit: int = 50) -> list[DurableWorker]:
        if self.db:
            return self._list_db(limit)
        return self._list_jsonl(limit)

    def update_status(
        self,
        worker_id: str,
        status: str,
        current_task_id: Optional[str] = None,
    ) -> Optional[DurableWorker]:
        worker = self.get_worker(worker_id)
        if worker is None:
            return None

        worker.status = status
        worker.current_task_id = current_task_id
        worker.updated_at = _now_iso()
        worker.last_seen_at = _now_iso()
        self._save(worker)
        return worker

    def touch(self, worker_id: str) -> Optional[DurableWorker]:
        worker = self.get_worker(worker_id)
        if worker is None:
            return None
        worker.last_seen_at = _now_iso()
        worker.updated_at = _now_iso()
        self._save(worker)
        return worker

    def mark_stale_workers_offline(self, max_age_seconds: int = 300) -> list[DurableWorker]:
        now = datetime.now(timezone.utc)
        threshold = now.timestamp() - max(1, max_age_seconds)
        changed = []
        for worker in self.list_workers(limit=500):
            if worker.status == WorkerStatus.OFFLINE:
                continue
            try:
                last_seen = datetime.fromisoformat(worker.last_seen_at)
                if last_seen.timestamp() < threshold:
                    worker.status = WorkerStatus.OFFLINE
                    worker.updated_at = _now_iso()
                    self._save(worker)
                    changed.append(worker)
            except (ValueError, TypeError):
                continue
        return changed

    def _save(self, worker: DurableWorker) -> None:
        if self.db:
            self._upsert_db(worker)
        else:
            self._upsert_jsonl(worker)

    # --- SQLite backend ---

    def _upsert_db(self, worker: DurableWorker) -> None:
        self._ensure_table()
        self.db.conn.execute(
            """INSERT OR REPLACE INTO durable_workers
               (worker_id, role, status, current_task_id, workspace_path,
                created_at, updated_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                worker.worker_id,
                worker.role,
                worker.status,
                worker.current_task_id,
                worker.workspace_path,
                worker.created_at,
                worker.updated_at,
                worker.last_seen_at,
            ),
        )
        self.db.conn.commit()

    def _get_db(self, worker_id: str) -> Optional[DurableWorker]:
        self._ensure_table()
        row = self.db.conn.execute(
            """SELECT worker_id, role, status, current_task_id,
                      workspace_path, created_at, updated_at, last_seen_at
               FROM durable_workers WHERE worker_id = ?""",
            (worker_id,),
        ).fetchone()
        return self._row_to_worker(row) if row else None

    def _list_db(self, limit: int) -> list[DurableWorker]:
        self._ensure_table()
        rows = self.db.conn.execute(
            """SELECT worker_id, role, status, current_task_id,
                      workspace_path, created_at, updated_at, last_seen_at
               FROM durable_workers ORDER BY rowid DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [self._row_to_worker(r) for r in rows]

    def _row_to_worker(self, row) -> DurableWorker:
        return DurableWorker(
            worker_id=row[0],
            role=row[1] or "",
            status=row[2] or WorkerStatus.IDLE,
            current_task_id=row[3],
            workspace_path=row[4] or "",
            created_at=row[5] or "",
            updated_at=row[6] or "",
            last_seen_at=row[7] or "",
        )

    # --- JSONL backend ---

    def _upsert_jsonl(self, worker: DurableWorker) -> None:
        workers = self._read_all_jsonl()
        replaced = False
        for i, w in enumerate(workers):
            if w.worker_id == worker.worker_id:
                workers[i] = worker
                replaced = True
                break
        if not replaced:
            workers.append(worker)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for w in workers:
                f.write(json.dumps(w.to_dict(), ensure_ascii=False) + "\n")

    def _get_jsonl(self, worker_id: str) -> Optional[DurableWorker]:
        for w in self._read_all_jsonl():
            if w.worker_id == worker_id:
                return w
        return None

    def _list_jsonl(self, limit: int) -> list[DurableWorker]:
        workers = self._read_all_jsonl()
        return workers[-limit:][::-1]

    def _read_all_jsonl(self) -> list[DurableWorker]:
        if not self.path.exists():
            return []
        workers = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        workers.append(DurableWorker.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, KeyError):
                        continue
        return workers


def _next_lease_id(existing_ids: list[str]) -> str:
    prefix = "wlease_"
    max_num = 0
    for lid in existing_ids:
        if lid.startswith(prefix):
            try:
                num = int(lid[len(prefix):])
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return f"{prefix}{max_num + 1}"


@dataclass
class DurableWorkspaceLease:
    lease_id: str
    worker_id: str
    task_id: str
    workspace_path: str
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DurableWorkspaceLease":
        return cls(
            lease_id=data["lease_id"],
            worker_id=data["worker_id"],
            task_id=data["task_id"],
            workspace_path=data.get("workspace_path", ""),
            created_at=data.get("created_at", ""),
        )


_WORKSPACE_LEASES_TABLE = """
CREATE TABLE IF NOT EXISTS workspace_leases (
    lease_id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    workspace_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""

_WORKSPACE_LEASES_INDEX = """
CREATE INDEX IF NOT EXISTS idx_wl_worker ON workspace_leases(worker_id);
CREATE INDEX IF NOT EXISTS idx_wl_task ON workspace_leases(task_id);
"""


class WorkspaceLeaseStore:
    """Workspace lease storage with SQLite (via NoraDB) or JSONL fallback."""

    def __init__(self, path: Path = None, db=None):
        self.path = path or Path("data/workspace_leases.jsonl")
        self.db = db
        self._table_created = False

    def _ensure_table(self) -> None:
        if self.db and not self._table_created:
            self.db.conn.executescript(_WORKSPACE_LEASES_TABLE)
            self.db.conn.executescript(_WORKSPACE_LEASES_INDEX)
            self._table_created = True

    def create_lease(
        self,
        worker_id: str,
        task_id: str,
        workspace_path: str,
    ) -> DurableWorkspaceLease:
        now = _now_iso()
        existing_ids = [l.lease_id for l in self._all_leases()]
        lease_id = _next_lease_id(existing_ids)
        lease = DurableWorkspaceLease(
            lease_id=lease_id,
            worker_id=worker_id,
            task_id=task_id,
            workspace_path=workspace_path,
            created_at=now,
        )
        self._save(lease)
        return lease

    def get_lease_by_worker(self, worker_id: str) -> Optional[DurableWorkspaceLease]:
        if self.db:
            self._ensure_table()
            row = self.db.conn.execute(
                """SELECT lease_id, worker_id, task_id, workspace_path, created_at
                   FROM workspace_leases WHERE worker_id = ? LIMIT 1""",
                (worker_id,),
            ).fetchone()
            return self._row_to_lease(row) if row else None
        for lease in self._read_all_jsonl():
            if lease.worker_id == worker_id:
                return lease
        return None

    def get_lease_by_task(self, task_id: str) -> Optional[DurableWorkspaceLease]:
        if self.db:
            self._ensure_table()
            row = self.db.conn.execute(
                """SELECT lease_id, worker_id, task_id, workspace_path, created_at
                   FROM workspace_leases WHERE task_id = ? LIMIT 1""",
                (task_id,),
            ).fetchone()
            return self._row_to_lease(row) if row else None
        for lease in self._read_all_jsonl():
            if lease.task_id == task_id:
                return lease
        return None

    def release_lease(self, lease_id: str) -> bool:
        if self.db:
            self._ensure_table()
            cursor = self.db.conn.execute(
                "DELETE FROM workspace_leases WHERE lease_id = ?", (lease_id,)
            )
            self.db.conn.commit()
            return cursor.rowcount > 0
        leases = self._read_all_jsonl()
        kept = [l for l in leases if l.lease_id != lease_id]
        if len(kept) == len(leases):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for l in kept:
                f.write(json.dumps(l.to_dict(), ensure_ascii=False) + "\n")
        return True

    def _save(self, lease: DurableWorkspaceLease) -> None:
        if self.db:
            self._upsert_db(lease)
        else:
            self._upsert_jsonl(lease)

    def _all_leases(self) -> list[DurableWorkspaceLease]:
        if self.db:
            self._ensure_table()
            rows = self.db.conn.execute(
                "SELECT lease_id, worker_id, task_id, workspace_path, created_at FROM workspace_leases"
            ).fetchall()
            return [self._row_to_lease(r) for r in rows]
        return self._read_all_jsonl()

    def _upsert_db(self, lease: DurableWorkspaceLease) -> None:
        self._ensure_table()
        self.db.conn.execute(
            """INSERT OR REPLACE INTO workspace_leases
               (lease_id, worker_id, task_id, workspace_path, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (lease.lease_id, lease.worker_id, lease.task_id,
             lease.workspace_path, lease.created_at),
        )
        self.db.conn.commit()

    def _row_to_lease(self, row) -> DurableWorkspaceLease:
        return DurableWorkspaceLease(
            lease_id=row[0],
            worker_id=row[1],
            task_id=row[2],
            workspace_path=row[3] or "",
            created_at=row[4] or "",
        )

    def _upsert_jsonl(self, lease: DurableWorkspaceLease) -> None:
        leases = self._read_all_jsonl()
        replaced = False
        for i, l in enumerate(leases):
            if l.lease_id == lease.lease_id:
                leases[i] = lease
                replaced = True
                break
        if not replaced:
            leases.append(lease)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for l in leases:
                f.write(json.dumps(l.to_dict(), ensure_ascii=False) + "\n")

    def _read_all_jsonl(self) -> list[DurableWorkspaceLease]:
        if not self.path.exists():
            return []
        leases = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        leases.append(DurableWorkspaceLease.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, KeyError):
                        continue
        return leases
