from __future__ import annotations

import json
import shutil
from pathlib import Path

from mini_agent.database import NoraDB
from mini_agent.tools_common import read_jsonl


def migrate_jsonl_to_sqlite(db: NoraDB, data_dir: Path, logs_dir: Path | None = None) -> list[str]:
    """Migrate existing JSONL files to SQLite. Returns list of migrated store names."""
    migrated = []
    logs_dir = logs_dir or data_dir.parent / "logs"

    # Long-term memory
    ltm_path = data_dir / "long_term_memory.jsonl"
    if ltm_path.exists() and not db.has_data("long_term_memory"):
        records = read_jsonl(ltm_path)
        for r in records:
            tags = r.get("tags", [])
            if isinstance(tags, list):
                tags = ",".join(tags)
            db.conn.execute(
                "INSERT OR IGNORE INTO long_term_memory (id, text, tags, created_at) VALUES (?, ?, ?, ?)",
                (r.get("id", ""), r.get("text", ""), tags, r.get("created_at", "")),
            )
        db.conn.commit()
        _backup(ltm_path)
        migrated.append("long_term_memory")

    # Context summaries
    cs_path = data_dir / "context_summaries.jsonl"
    if cs_path.exists() and not db.has_data("context_summaries"):
        records = read_jsonl(cs_path)
        for r in records:
            db.conn.execute(
                "INSERT OR IGNORE INTO context_summaries (id, topic, summary, source, created_at) VALUES (?, ?, ?, ?, ?)",
                (r.get("id", ""), r.get("topic", ""), r.get("summary", ""), r.get("source", ""), r.get("created_at", "")),
            )
        db.conn.commit()
        _backup(cs_path)
        migrated.append("context_summaries")

    # Task history
    th_path = data_dir / "task_history.jsonl"
    if th_path.exists() and not db.has_data("task_history"):
        records = read_jsonl(th_path)
        for r in records:
            steps = r.get("steps", [])
            db.conn.execute(
                "INSERT OR IGNORE INTO task_history (id, goal, status, created_at, finished_at, summary, steps_json, restored_from, restored_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    r.get("id", ""),
                    r.get("goal", ""),
                    r.get("status", ""),
                    r.get("created_at", ""),
                    r.get("finished_at", ""),
                    r.get("summary", ""),
                    json.dumps(steps, ensure_ascii=False) if steps else None,
                    r.get("restored_from"),
                    r.get("restored_at"),
                ),
            )
        db.conn.commit()
        _backup(th_path)
        migrated.append("task_history")

    # Current task (JSON file)
    ct_path = data_dir / "current_task.json"
    if ct_path.exists() and not db.has_data("current_task"):
        try:
            r = json.loads(ct_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            r = {}
        if r and r.get("goal"):
            steps = r.get("steps", [])
            db.conn.execute(
                "INSERT OR REPLACE INTO current_task (id, goal, status, created_at, finished_at, summary, steps_json, restored_from, restored_at) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    r.get("goal", ""),
                    r.get("status", ""),
                    r.get("created_at", ""),
                    r.get("finished_at", ""),
                    r.get("summary", ""),
                    json.dumps(steps, ensure_ascii=False) if steps else None,
                    r.get("restored_from"),
                    r.get("restored_at"),
                ),
            )
            db.conn.commit()
            _backup(ct_path)
            migrated.append("current_task")

    # Tool results
    tr_path = data_dir / "tool_results.jsonl"
    if tr_path.exists() and not db.has_data("tool_results"):
        records = read_jsonl(tr_path)
        for r in records:
            db.conn.execute(
                "INSERT OR IGNORE INTO tool_results (id, tool, created_at, chars, result) VALUES (?, ?, ?, ?, ?)",
                (r.get("id", ""), r.get("tool", ""), r.get("created_at", ""), r.get("chars", 0), r.get("result", "")),
            )
        db.conn.commit()
        _backup(tr_path)
        migrated.append("tool_results")

    # Tool logs
    tl_path = logs_dir / "tool_calls.jsonl"
    if tl_path.exists() and not db.has_data("tool_logs"):
        records = read_jsonl(tl_path)
        for r in records:
            arguments = r.get("arguments", {})
            db.conn.execute(
                "INSERT INTO tool_logs (timestamp, tool, arguments_json, status, result_preview) VALUES (?, ?, ?, ?, ?)",
                (
                    r.get("timestamp", ""),
                    r.get("tool", ""),
                    json.dumps(arguments, ensure_ascii=False) if isinstance(arguments, dict) else str(arguments),
                    r.get("status", ""),
                    r.get("result_preview", ""),
                ),
            )
        db.conn.commit()
        _backup(tl_path)
        migrated.append("tool_logs")

    # Durable tasks
    dt_path = data_dir / "durable_tasks.jsonl"
    if dt_path.exists():
        from mini_agent.durable_tasks import DurableTask, DurableTaskStore, DurableStep, DurableCheckpoint

        dt_store = DurableTaskStore(db=db)
        dt_store._ensure_table()
        if not db.has_data("durable_tasks"):
            records = read_jsonl(dt_path)
            for r in records:
                try:
                    task = DurableTask.from_dict(r)
                    dt_store.upsert_task(task)
                except (KeyError, TypeError, ValueError):
                    continue
            _backup(dt_path)
            migrated.append("durable_tasks")

    # Sessions
    sessions_dir = data_dir / "sessions"
    if sessions_dir.exists() and sessions_dir.is_dir() and not db.has_data("sessions"):
        for path in sorted(sessions_dir.glob("*.jsonl")):
            records = read_jsonl(path)
            if not records:
                continue
            meta = records[0]
            messages = records[1:]
            name = meta.get("name", path.stem)
            db.conn.execute(
                "INSERT OR IGNORE INTO sessions (name, saved_at, message_count, messages_json) VALUES (?, ?, ?, ?)",
                (name, meta.get("saved_at", ""), meta.get("message_count", len(messages)), json.dumps(messages, ensure_ascii=False)),
            )
        db.conn.commit()
        _backup(sessions_dir)
        migrated.append("sessions")

    return migrated


def _backup(path: Path) -> None:
    """Rename file/dir to .bak, preserving originals."""
    if not path.exists():
        return
    bak = path.with_suffix(path.suffix + ".bak")
    if bak.exists():
        return
    try:
        if path.is_dir():
            shutil.move(str(path), str(bak))
        else:
            path.rename(bak)
    except OSError:
        pass
