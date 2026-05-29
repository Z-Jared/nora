"""Durable task store for Nora agent.

Provides DurableTask, DurableStep, DurableCheckpoint data structures
and DurableTaskStore with SQLite (via NoraDB) and JSONL backends.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class ResumePolicy(str, Enum):
    FROM_CHECKPOINT = "from_checkpoint"
    FROM_STEP = "from_step"
    FROM_BEGINNING = "from_beginning"


_VALID_TRANSITIONS: dict[str, set[str]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.PAUSED, TaskStatus.BLOCKED, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.PAUSED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.BLOCKED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),
    # FAILED -> PENDING is NOT listed here; it can only happen via
    # retry_durable_task(), which enforces retry_count < max_retries.
    TaskStatus.FAILED: {TaskStatus.CANCELLED},
    TaskStatus.CANCELLED: set(),
}


@dataclass
class DurableCheckpoint:
    checkpoint_id: str
    step_id: int
    run_id: str
    created_at: str
    state_snapshot: dict
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> DurableCheckpoint:
        return cls(**data)


@dataclass
class DurableStep:
    id: int
    text: str
    status: str = StepStatus.PENDING
    note: str = ""
    summary: str = ""
    tool_hint: str = ""
    checkpoint_ref: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> DurableStep:
        return cls(**data)


@dataclass
class DurableTask:
    task_id: str
    run_id: str
    status: str
    goal: str
    steps: list[DurableStep]
    created_at: str
    updated_at: str
    parent_task_id: Optional[str] = None
    current_step: Optional[int] = None
    checkpoints: list[DurableCheckpoint] = field(default_factory=list)
    input_summary: str = ""
    context_pack_ref: Optional[str] = None
    trace_refs: list[str] = field(default_factory=list)
    worker_id: Optional[str] = None
    finished_at: Optional[str] = None
    failure_reason: str = ""
    resume_policy: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "run_id": self.run_id,
            "parent_task_id": self.parent_task_id,
            "status": self.status,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "current_step": self.current_step,
            "checkpoints": [c.to_dict() for c in self.checkpoints],
            "input_summary": self.input_summary,
            "context_pack_ref": self.context_pack_ref,
            "trace_refs": self.trace_refs,
            "worker_id": self.worker_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "finished_at": self.finished_at,
            "failure_reason": self.failure_reason,
            "resume_policy": self.resume_policy,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DurableTask:
        steps = [DurableStep.from_dict(s) for s in data.get("steps", [])]
        checkpoints = [DurableCheckpoint.from_dict(c) for c in data.get("checkpoints", [])]
        return cls(
            task_id=data["task_id"],
            run_id=data["run_id"],
            status=data["status"],
            goal=data["goal"],
            steps=steps,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            parent_task_id=data.get("parent_task_id"),
            current_step=data.get("current_step"),
            checkpoints=checkpoints,
            input_summary=data.get("input_summary", ""),
            context_pack_ref=data.get("context_pack_ref"),
            trace_refs=data.get("trace_refs", []),
            worker_id=data.get("worker_id"),
            finished_at=data.get("finished_at"),
            failure_reason=data.get("failure_reason", ""),
            resume_policy=data.get("resume_policy"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )


_DURABLE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS durable_tasks (
    task_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    parent_task_id TEXT,
    status TEXT NOT NULL,
    goal TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    current_step INTEGER,
    checkpoints_json TEXT NOT NULL DEFAULT '[]',
    input_summary TEXT NOT NULL DEFAULT '',
    context_pack_ref TEXT,
    trace_refs_json TEXT NOT NULL DEFAULT '[]',
    worker_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT,
    failure_reason TEXT NOT NULL DEFAULT '',
    resume_policy TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3
);
"""

_DURABLE_TASKS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_dt_status ON durable_tasks(status);
CREATE INDEX IF NOT EXISTS idx_dt_created ON durable_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_dt_updated ON durable_tasks(updated_at);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_id(prefix: str, existing_ids: list[str]) -> str:
    max_num = 0
    for tid in existing_ids:
        if tid.startswith(prefix):
            try:
                num = int(tid[len(prefix):])
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return f"{prefix}{max_num + 1}"


class DurableTaskStore:
    """Durable task storage with SQLite (via NoraDB) or JSONL fallback."""

    def __init__(self, path: Path = None, db=None):
        self.path = path or Path("data/durable_tasks.jsonl")
        self.db = db
        self._table_created = False

    def _ensure_table(self) -> None:
        if self.db and not self._table_created:
            self.db.conn.executescript(_DURABLE_TASKS_TABLE)
            self.db.conn.executescript(_DURABLE_TASKS_INDEX)
            self._migrate_retry_columns()
            self._table_created = True

    def _migrate_retry_columns(self) -> None:
        """Add retry_count and max_retries columns if they don't exist."""
        columns = {row[1] for row in self.db.conn.execute("PRAGMA table_info(durable_tasks)").fetchall()}
        if "retry_count" not in columns:
            self.db.conn.execute("ALTER TABLE durable_tasks ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0")
        if "max_retries" not in columns:
            self.db.conn.execute("ALTER TABLE durable_tasks ADD COLUMN max_retries INTEGER NOT NULL DEFAULT 3")
        self.db.conn.commit()

    def create_task(
        self,
        goal: str,
        steps: list[dict],
        run_id: str = "run_1",
        parent_task_id: Optional[str] = None,
        input_summary: str = "",
        worker_id: Optional[str] = None,
        max_retries: int = 3,
    ) -> DurableTask:
        now = _now_iso()
        existing = self._all_ids()
        task_id = _next_id("dtask_", existing)

        step_objs = []
        for i, s in enumerate(steps, 1):
            step_objs.append(DurableStep(
                id=i,
                text=s.get("text", ""),
                status=s.get("status", StepStatus.PENDING),
                note=s.get("note", ""),
                summary=s.get("summary", ""),
                tool_hint=s.get("tool_hint", ""),
            ))

        task = DurableTask(
            task_id=task_id,
            run_id=run_id,
            status=TaskStatus.PENDING,
            goal=goal,
            steps=step_objs,
            created_at=now,
            updated_at=now,
            parent_task_id=parent_task_id,
            input_summary=input_summary,
            worker_id=worker_id,
            max_retries=max(0, int(max_retries)),
        )

        if self.db:
            self._insert_db(task)
        else:
            self._append_jsonl(task)

        return task

    def get_task(self, task_id: str) -> Optional[DurableTask]:
        if self.db:
            return self._get_db(task_id)
        return self._get_jsonl(task_id)

    def list_tasks(self, limit: int = 50) -> list[DurableTask]:
        if self.db:
            return self._list_db(limit)
        return self._list_jsonl(limit)

    def update_status(self, task_id: str, status: str, failure_reason: str = "") -> Optional[DurableTask]:
        valid_statuses = {s.value for s in TaskStatus}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status!r}. Must be one of {sorted(valid_statuses)}")

        task = self.get_task(task_id)
        if task is None:
            return None

        valid_targets = _VALID_TRANSITIONS.get(task.status, set())
        if status not in valid_targets:
            raise ValueError(
                f"Invalid transition: {task.status!r} -> {status!r}. "
                f"Valid targets from {task.status!r}: {sorted(valid_targets)}"
            )

        now = _now_iso()
        task.status = status
        task.updated_at = now
        task.failure_reason = failure_reason

        terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
        if status in terminal:
            task.finished_at = now

        if self.db:
            self._update_db(task)
        else:
            self._rewrite_jsonl(task)

        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by id. Returns True if deleted, False if not found."""
        task = self.get_task(task_id)
        if task is None:
            return False
        if self.db:
            self._ensure_table()
            self.db.conn.execute("DELETE FROM durable_tasks WHERE task_id = ?", (task_id,))
            self.db.conn.commit()
        else:
            tasks = [t for t in self._read_all_jsonl() if t.task_id != task_id]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as f:
                for t in tasks:
                    f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")
        return True

    def retry_durable_task(self, task_id: str) -> Optional[DurableTask]:
        """Retry a failed task: reset to pending, increment retry_count, reset steps.

        Returns the updated task, or None if not found.
        Raises ValueError if task is not FAILED or max_retries reached.
        """
        task = self.get_task(task_id)
        if task is None:
            return None

        if task.status != TaskStatus.FAILED:
            raise ValueError(
                f"Cannot retry task in status {task.status!r}. Only FAILED tasks can be retried."
            )
        if task.retry_count >= task.max_retries:
            raise ValueError(
                f"Max retries ({task.max_retries}) reached for task {task_id}."
            )

        now = _now_iso()
        task.status = TaskStatus.PENDING
        task.retry_count += 1
        task.finished_at = None
        task.failure_reason = ""
        task.updated_at = now
        # Reset all steps to pending
        for step in task.steps:
            step.status = StepStatus.PENDING
            step.note = ""
            step.summary = ""

        if self.db:
            self._update_db(task)
        else:
            self._rewrite_jsonl(task)

        return task

    def upsert_task(self, task: DurableTask) -> None:
        """Insert or update a DurableTask. Overwrites if task_id already exists."""
        if self.db:
            self._ensure_table()
            self.db.conn.execute(
                """INSERT OR REPLACE INTO durable_tasks
                   (task_id, run_id, parent_task_id, status, goal,
                    steps_json, current_step, checkpoints_json,
                    input_summary, context_pack_ref, trace_refs_json,
                    worker_id, created_at, updated_at, finished_at,
                    failure_reason, resume_policy, retry_count, max_retries)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.task_id,
                    task.run_id,
                    task.parent_task_id,
                    task.status,
                    task.goal,
                    json.dumps([s.to_dict() for s in task.steps], ensure_ascii=False),
                    task.current_step,
                    json.dumps([c.to_dict() for c in task.checkpoints], ensure_ascii=False),
                    task.input_summary,
                    task.context_pack_ref,
                    json.dumps(task.trace_refs, ensure_ascii=False),
                    task.worker_id,
                    task.created_at,
                    task.updated_at,
                    task.finished_at,
                    task.failure_reason,
                    task.resume_policy,
                    task.retry_count,
                    task.max_retries,
                ),
            )
            self.db.conn.commit()
        else:
            self._rewrite_jsonl(task)

    def add_trace_ref(self, trace_id: str) -> bool:
        """Append trace_id to the first active/running durable task. Returns True if linked."""
        non_terminal = {TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED, TaskStatus.BLOCKED}
        tasks = self.list_tasks(limit=50)
        for task in tasks:
            if task.status in non_terminal:
                if trace_id in task.trace_refs:
                    return True
                task.trace_refs.append(trace_id)
                task.updated_at = _now_iso()
                if self.db:
                    self._update_db(task)
                else:
                    self._rewrite_jsonl(task)
                return True
        return False

    def add_checkpoint(self, task_id: str, checkpoint: dict) -> Optional[DurableCheckpoint]:
        task = self.get_task(task_id)
        if task is None:
            return None

        existing_ids = [c.checkpoint_id for c in task.checkpoints]
        cp_id = _next_id("cp_", existing_ids)

        cp = DurableCheckpoint(
            checkpoint_id=cp_id,
            step_id=checkpoint.get("step_id", 0),
            run_id=checkpoint.get("run_id", task.run_id),
            created_at=_now_iso(),
            state_snapshot=checkpoint.get("state_snapshot", {}),
            description=checkpoint.get("description", ""),
        )

        task.checkpoints.append(cp)
        task.updated_at = _now_iso()

        if self.db:
            self._update_db(task)
        else:
            self._rewrite_jsonl(task)

        return cp

    # --- SQLite backend ---

    def _insert_db(self, task: DurableTask) -> None:
        self._ensure_table()
        self.db.conn.execute(
            """INSERT INTO durable_tasks
               (task_id, run_id, parent_task_id, status, goal,
                steps_json, current_step, checkpoints_json,
                input_summary, context_pack_ref, trace_refs_json,
                worker_id, created_at, updated_at, finished_at,
                failure_reason, resume_policy, retry_count, max_retries)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.task_id,
                task.run_id,
                task.parent_task_id,
                task.status,
                task.goal,
                json.dumps([s.to_dict() for s in task.steps], ensure_ascii=False),
                task.current_step,
                json.dumps([c.to_dict() for c in task.checkpoints], ensure_ascii=False),
                task.input_summary,
                task.context_pack_ref,
                json.dumps(task.trace_refs, ensure_ascii=False),
                task.worker_id,
                task.created_at,
                task.updated_at,
                task.finished_at,
                task.failure_reason,
                task.resume_policy,
                task.retry_count,
                task.max_retries,
            ),
        )
        self.db.conn.commit()

    def _update_db(self, task: DurableTask) -> None:
        self._ensure_table()
        self.db.conn.execute(
            """UPDATE durable_tasks SET
               run_id=?, parent_task_id=?, status=?, goal=?,
               steps_json=?, current_step=?, checkpoints_json=?,
               input_summary=?, context_pack_ref=?, trace_refs_json=?,
               worker_id=?, updated_at=?, finished_at=?,
               failure_reason=?, resume_policy=?, retry_count=?, max_retries=?
               WHERE task_id=?""",
            (
                task.run_id,
                task.parent_task_id,
                task.status,
                task.goal,
                json.dumps([s.to_dict() for s in task.steps], ensure_ascii=False),
                task.current_step,
                json.dumps([c.to_dict() for c in task.checkpoints], ensure_ascii=False),
                task.input_summary,
                task.context_pack_ref,
                json.dumps(task.trace_refs, ensure_ascii=False),
                task.worker_id,
                task.updated_at,
                task.finished_at,
                task.failure_reason,
                task.resume_policy,
                task.retry_count,
                task.max_retries,
                task.task_id,
            ),
        )
        self.db.conn.commit()

    def _get_db(self, task_id: str) -> Optional[DurableTask]:
        self._ensure_table()
        row = self.db.conn.execute(
            """SELECT task_id, run_id, parent_task_id, status, goal,
                      steps_json, current_step, checkpoints_json,
                      input_summary, context_pack_ref, trace_refs_json,
                      worker_id, created_at, updated_at, finished_at,
                      failure_reason, resume_policy, retry_count, max_retries
               FROM durable_tasks WHERE task_id=?""",
            (task_id,),
        ).fetchone()
        return self._row_to_task(row) if row else None

    def _list_db(self, limit: int) -> list[DurableTask]:
        self._ensure_table()
        rows = self.db.conn.execute(
            """SELECT task_id, run_id, parent_task_id, status, goal,
                      steps_json, current_step, checkpoints_json,
                      input_summary, context_pack_ref, trace_refs_json,
                      worker_id, created_at, updated_at, finished_at,
                      failure_reason, resume_policy, retry_count, max_retries
               FROM durable_tasks ORDER BY rowid DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def _all_ids_db(self) -> list[str]:
        self._ensure_table()
        rows = self.db.conn.execute("SELECT task_id FROM durable_tasks").fetchall()
        return [r[0] for r in rows]

    def _row_to_task(self, row) -> DurableTask:
        steps = [DurableStep.from_dict(s) for s in json.loads(row[5])]
        checkpoints = [DurableCheckpoint.from_dict(c) for c in json.loads(row[7] or "[]")]
        trace_refs = json.loads(row[10] or "[]")
        return DurableTask(
            task_id=row[0],
            run_id=row[1],
            parent_task_id=row[2],
            status=row[3],
            goal=row[4],
            steps=steps,
            current_step=row[6],
            checkpoints=checkpoints,
            input_summary=row[8] or "",
            context_pack_ref=row[9],
            trace_refs=trace_refs,
            worker_id=row[11],
            created_at=row[12],
            updated_at=row[13],
            finished_at=row[14],
            failure_reason=row[15] or "",
            resume_policy=row[16],
            retry_count=row[17] or 0,
            max_retries=row[18] if row[18] is not None else 3,
        )

    # --- JSONL backend ---

    def _append_jsonl(self, task: DurableTask) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(task.to_dict(), ensure_ascii=False) + "\n")

    def _read_all_jsonl(self) -> list[DurableTask]:
        if not self.path.exists():
            return []
        tasks = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        tasks.append(DurableTask.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, KeyError):
                        continue
        return tasks

    def _get_jsonl(self, task_id: str) -> Optional[DurableTask]:
        for task in self._read_all_jsonl():
            if task.task_id == task_id:
                return task
        return None

    def _list_jsonl(self, limit: int) -> list[DurableTask]:
        tasks = self._read_all_jsonl()
        return tasks[-limit:][::-1]

    def _rewrite_jsonl(self, updated: DurableTask) -> None:
        tasks = self._read_all_jsonl()
        found = False
        for i, t in enumerate(tasks):
            if t.task_id == updated.task_id:
                tasks[i] = updated
                found = True
                break
        if not found:
            tasks.append(updated)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for t in tasks:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

    def _all_ids(self) -> list[str]:
        if self.db:
            return self._all_ids_db()
        return [t.task_id for t in self._read_all_jsonl()]


def _infer_status(task: dict) -> str:
    old_status = task.get("status", "active")
    steps = task.get("steps", [])
    if old_status == "finished":
        return TaskStatus.COMPLETED
    # active: infer from steps
    if steps and all(s.get("status") == "pending" for s in steps):
        return TaskStatus.PENDING
    if steps and all(s.get("status") == "blocked" for s in steps):
        return TaskStatus.BLOCKED
    return TaskStatus.RUNNING


def task_manager_task_to_durable(
    task: dict,
    task_id: Optional[str] = None,
    run_id: str = "run_1",
    checkpoints: Optional[list[DurableCheckpoint]] = None,
    step_checkpoint_refs: Optional[dict[int, str]] = None,
) -> DurableTask:
    """Convert a legacy TaskManager task dict to a DurableTask.

    Mapping rules:
    - goal -> goal
    - steps -> steps (DurableStep with id/text/status/note/summary)
    - active + all pending -> pending
    - active + all blocked -> blocked
    - active otherwise -> running
    - finished -> completed
    - created_at preserved; missing -> now
    - finished_at preserved
    - summary -> input_summary (preserved, not lost)
    - restored_from/restored_at -> checkpoint with description (preserved, not lost)
    - tool_hint empty (not present in old format)
    - checkpoint_ref None
    - failure_reason empty
    - resume_policy from_step
    """
    now = _now_iso()
    task_id = task_id or "dtask_1"
    status = _infer_status(task)
    created_at = task.get("created_at") or now

    steps = []
    refs = step_checkpoint_refs or {}
    for s in task.get("steps", []):
        sid = s.get("id", 0)
        steps.append(DurableStep(
            id=sid,
            text=s.get("text", ""),
            status=s.get("status", StepStatus.PENDING),
            note=s.get("note", ""),
            summary=s.get("summary", ""),
            tool_hint=s.get("tool_hint", ""),
            checkpoint_ref=refs.get(sid),
        ))

    existing_checkpoints = []
    restored_from = task.get("restored_from")
    restored_at = task.get("restored_at")
    if restored_from:
        description = f"restored_from={restored_from}"
        if restored_at:
            description += f" restored_at={restored_at}"
        existing_checkpoints.append(DurableCheckpoint(
            checkpoint_id="cp_1",
            step_id=0,
            run_id=run_id,
            created_at=restored_at or now,
            state_snapshot={"restored_from": restored_from, "restored_at": restored_at},
            description=description,
        ))

    if checkpoints:
        existing_checkpoints.extend(checkpoints)

    input_summary = task.get("summary", "")

    # Find current_step: 1-based index of the in_progress step, or None
    current_step = None
    for s in task.get("steps", []):
        if s.get("status") == "in_progress":
            current_step = s.get("id")
            break

    return DurableTask(
        task_id=task_id,
        run_id=run_id,
        status=status,
        goal=task.get("goal", ""),
        steps=steps,
        created_at=created_at,
        updated_at=now,
        current_step=current_step,
        finished_at=task.get("finished_at"),
        input_summary=input_summary,
        checkpoints=existing_checkpoints,
        resume_policy=ResumePolicy.FROM_STEP,
    )
