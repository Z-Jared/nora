#!/usr/bin/env python3
"""Best-effort repair for Codex Desktop local session listings."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CODEX_HOME = Path.home() / ".codex"
STATE_DB = CODEX_HOME / "state_5.sqlite"
SESSION_INDEX = CODEX_HOME / "session_index.jsonl"
SESSIONS_DIR = CODEX_HOME / "sessions"
ARCHIVED_DIR = CODEX_HOME / "archived_sessions"
BACKUP_DIR = CODEX_HOME / "backups"
TARGET_CWD = Path(os.environ.get("CODEX_RESTORE_CWD", Path.cwd())).resolve()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return []
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def parse_iso(value: str) -> int:
    if not value:
        return 0
    value = value.replace("Z", "+00:00")
    try:
        return int(datetime.fromisoformat(value).timestamp())
    except ValueError:
        return 0


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "\n".join(parts).strip()


def extract_session(path: Path) -> dict[str, Any] | None:
    rows = read_jsonl(path)
    if not rows:
        return None

    meta: dict[str, Any] = {}
    first_user = ""
    last_ts = 0
    for row in rows:
        ts = parse_iso(str(row.get("timestamp", "")))
        if ts:
            last_ts = max(last_ts, ts)
        payload = row.get("payload", {})
        if row.get("type") == "session_meta" and isinstance(payload, dict):
            meta = payload
            continue
        if first_user:
            continue
        if row.get("type") == "response_item" and isinstance(payload, dict):
            if payload.get("type") == "message" and payload.get("role") == "user":
                text = content_text(payload.get("content"))
                if text and not text.lstrip().startswith("<environment_context>"):
                    first_user = text.splitlines()[0][:120]

    session_id = str(meta.get("id") or "")
    if not session_id:
        return None

    created = parse_iso(str(meta.get("timestamp", ""))) or last_ts
    updated = last_ts or created
    title = first_user or session_id

    return {
        "id": session_id,
        "rollout_path": str(path),
        "created_at": created,
        "updated_at": updated,
        "source": str(meta.get("source") or meta.get("originator") or "local"),
        "model_provider": str(meta.get("model_provider") or ""),
        "cwd": str(meta.get("cwd") or ""),
        "title": title,
        "first_user_message": first_user,
        "preview": first_user,
        "cli_version": str(meta.get("cli_version") or ""),
        "thread_source": str(meta.get("thread_source") or ""),
        "model": str(meta.get("model") or ""),
        "reasoning_effort": str(meta.get("reasoning_effort") or ""),
    }


def all_sessions() -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    paths = list(SESSIONS_DIR.glob("**/*.jsonl")) + list(ARCHIVED_DIR.glob("*.jsonl"))
    for path in sorted(paths):
        session = extract_session(path)
        if not session:
            continue
        current = found.get(session["id"])
        if not current or session["updated_at"] >= current["updated_at"]:
            found[session["id"]] = session
    return sorted(found.values(), key=lambda row: (row["updated_at"], row["id"]), reverse=True)


def standard_session_path(session: dict[str, Any]) -> Path:
    created = int(session.get("created_at") or 0)
    dt = datetime.fromtimestamp(created, timezone.utc) if created else datetime.now(timezone.utc)
    return SESSIONS_DIR / f"{dt:%Y}" / f"{dt:%m}" / f"{dt:%d}" / Path(str(session["rollout_path"])).name


def restore_project_archived_sessions(sessions: list[dict[str, Any]]) -> int:
    restored = 0
    for session in sessions:
        cwd = str(session.get("cwd") or "")
        if not cwd:
            continue
        try:
            if Path(cwd).resolve() != TARGET_CWD:
                continue
        except OSError:
            continue

        source = Path(str(session["rollout_path"]))
        if source.parent != ARCHIVED_DIR or not source.exists():
            continue

        destination = standard_session_path(session)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)
            restored += 1
        session["rollout_path"] = str(destination)
    return restored


def is_target_project_session(session: dict[str, Any]) -> bool:
    cwd = str(session.get("cwd") or "")
    if not cwd:
        return False
    try:
        return Path(cwd).resolve() == TARGET_CWD
    except OSError:
        return False


def force_project_model_provider(sessions: list[dict[str, Any]], provider: str | None) -> int:
    if not provider:
        return 0
    changed = 0
    for session in sessions:
        if not is_target_project_session(session):
            continue
        if session.get("model_provider") == provider:
            continue
        path = Path(str(session["rollout_path"]))
        if not path.exists():
            continue

        rows = read_jsonl(path)
        patched = False
        for row in rows:
            payload = row.get("payload")
            if row.get("type") == "session_meta" and isinstance(payload, dict):
                payload["model_provider"] = provider
                patched = True
                break
        if not patched:
            continue
        write_jsonl(path, rows)
        session["model_provider"] = provider
        changed += 1
    return changed


def backup_files() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = BACKUP_DIR / f"codex-session-restore-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in [
        SESSION_INDEX,
        STATE_DB,
        STATE_DB.with_name(STATE_DB.name + "-wal"),
        STATE_DB.with_name(STATE_DB.name + "-shm"),
    ]:
        if path.exists():
            shutil.copy2(path, out / path.name)
    return out


def write_session_index(sessions: list[dict[str, Any]]) -> None:
    lines = []
    for session in sessions:
        updated = datetime.fromtimestamp(session["updated_at"], timezone.utc).isoformat().replace("+00:00", "Z")
        lines.append(json.dumps({"id": session["id"], "thread_name": session["title"], "updated_at": updated}, ensure_ascii=False))
    SESSION_INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")


def repair_state_db(sessions: list[dict[str, Any]]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    conn = sqlite3.connect(STATE_DB)
    try:
        for session in sessions:
            row = conn.execute(
                "SELECT title, cwd, rollout_path, updated_at FROM threads WHERE id = ?",
                (session["id"],),
            ).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO threads (
                        id, rollout_path, created_at, updated_at, source, model_provider, cwd, title,
                        sandbox_policy, approval_mode, tokens_used, has_user_event, archived,
                        cli_version, first_user_message, thread_source, preview, model, reasoning_effort
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, 0, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session["id"],
                        session["rollout_path"],
                        session["created_at"],
                        session["updated_at"],
                        session["source"],
                        session["model_provider"],
                        session["cwd"],
                        session["title"],
                        "workspace-write",
                        "on-request",
                        session["cli_version"],
                        session["first_user_message"],
                        session["thread_source"],
                        session["preview"],
                        session["model"],
                        session["reasoning_effort"],
                    ),
                )
                inserted += 1
                continue
            title, cwd, rollout_path, updated_at = row
            if not title or not cwd or not rollout_path or int(updated_at or 0) < int(session["updated_at"]):
                conn.execute(
                    """
                    UPDATE threads
                    SET title = CASE WHEN title = '' THEN ? ELSE title END,
                        cwd = CASE WHEN cwd = '' THEN ? ELSE cwd END,
                        rollout_path = CASE WHEN rollout_path = '' THEN ? ELSE rollout_path END,
                        updated_at = CASE WHEN updated_at < ? THEN ? ELSE updated_at END,
                        first_user_message = CASE WHEN first_user_message = '' THEN ? ELSE first_user_message END,
                        preview = CASE WHEN preview = '' THEN ? ELSE preview END
                    WHERE id = ?
                    """,
                    (
                        session["title"],
                        session["cwd"],
                        session["rollout_path"],
                        session["updated_at"],
                        session["updated_at"],
                        session["first_user_message"],
                        session["preview"],
                        session["id"],
                    ),
                )
                updated += 1
            if session.get("model_provider"):
                result = conn.execute(
                    "UPDATE threads SET model_provider = ? WHERE id = ? AND model_provider != ?",
                    (session["model_provider"], session["id"], session["model_provider"]),
                )
                if result.rowcount:
                    updated += 1
        conn.commit()
    finally:
        conn.close()
    return inserted, updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--desktop-provider",
        default="",
        help="Rewrite this project's session model_provider metadata so Codex Desktop's default list filter shows it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sessions = all_sessions()
    backup_dir = backup_files()
    restored = restore_project_archived_sessions(sessions)
    provider_patched = force_project_model_provider(sessions, args.desktop_provider)
    write_session_index(sessions)
    inserted, updated = repair_state_db(sessions)
    print(f"backup={backup_dir}")
    print(f"target_cwd={TARGET_CWD}")
    print(f"archived_sessions_restored={restored}")
    print(f"model_provider_patched={provider_patched}")
    print(f"sessions_indexed={len(sessions)}")
    print(f"threads_inserted={inserted}")
    print(f"threads_updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
