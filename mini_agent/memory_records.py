"""Structured memory record store for Nora.

Provides typed, local-first memory records for decisions, preferences,
task learnings, and project facts.  Dual-backend: SQLite (NoraDB) with
JSONL fallback.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mini_agent.memory import is_sensitive_text
from mini_agent.tools_common import read_jsonl

VALID_KINDS = ("decision", "preference", "fact", "task_learning", "risk", "note")
VALID_SCOPES = ("project", "user", "global")

_RECORD_PREFIX = "mrec_"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_id(records: list[dict]) -> int:
    max_id = 0
    for record in records:
        raw = str(record.get("record_id", ""))
        if raw.startswith(_RECORD_PREFIX):
            try:
                max_id = max(max_id, int(raw[len(_RECORD_PREFIX):]))
            except ValueError:
                pass
    return max_id + 1


def _parse_tags_str(tags: str) -> list[str]:
    return [t.strip() for t in tags.split(",") if t.strip()]


def _validate_create(kind: str, title: str, content: str, scope: str = "project") -> Optional[str]:
    if not kind or kind not in VALID_KINDS:
        return f"无效的 kind: {kind}，有效值: {', '.join(VALID_KINDS)}"
    if scope and scope not in VALID_SCOPES:
        return f"无效的 scope: {scope}，有效值: {', '.join(VALID_SCOPES)}"
    if not title or not title.strip():
        return "title 不能为空"
    if not content or not content.strip():
        return "content 不能为空"
    if is_sensitive_text(title) or is_sensitive_text(content):
        return "检测到敏感内容（API key、token 等），拒绝保存。"
    return None


def _row_to_record(row) -> dict:
    return {
        "record_id": row[0],
        "kind": row[1],
        "scope": row[2],
        "title": row[3],
        "content": row[4],
        "tags": row[5].split(",") if row[5] else [],
        "source": row[6],
        "confidence": row[7],
        "related_task_id": row[8],
        "created_at": row[9],
        "updated_at": row[10],
    }


_COLUMNS = "record_id, kind, scope, title, content, tags, source, confidence, related_task_id, created_at, updated_at"


class MemoryRecordStore:
    """Structured memory record store with SQLite (NoraDB) or JSONL fallback."""

    def __init__(self, path: Path = Path("data/memory_records.jsonl"), db=None):
        self.path = path
        self.db = db

    # ── create ──────────────────────────────────────────────────────────

    def create(
        self,
        kind: str,
        title: str,
        content: str,
        scope: str = "project",
        tags: str = "",
        source: str = "",
        confidence: float = 1.0,
        related_task_id: str = "",
    ) -> tuple[str, str]:
        error = _validate_create(kind, title, content, scope)
        if error:
            return error, ""
        tags_clean = ",".join(t.strip() for t in tags.split(",") if t.strip()) if tags else ""
        confidence = max(0.0, min(1.0, confidence))
        now = _now_iso()
        if self.db:
            return self._create_db(
                kind, title.strip(), content.strip(), scope, tags_clean,
                source, confidence, related_task_id, now,
            )
        return self._create_jsonl(
            kind, title.strip(), content.strip(), scope, tags_clean,
            source, confidence, related_task_id, now,
        )

    def _create_db(
        self, kind, title, content, scope, tags, source, confidence, related_task_id, now,
    ) -> tuple[str, str]:
        row = self.db.conn.execute(
            "SELECT MAX(CAST(SUBSTR(record_id, ?) AS INTEGER)) FROM memory_records WHERE record_id LIKE ?",
            (len(_RECORD_PREFIX) + 1, f"{_RECORD_PREFIX}%"),
        ).fetchone()
        next_num = (row[0] or 0) + 1
        record_id = f"{_RECORD_PREFIX}{next_num}"
        self.db.conn.execute(
            f"INSERT INTO memory_records ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record_id, kind, scope, title, content, tags, source, confidence, related_task_id, now, now),
        )
        self.db.conn.commit()
        return f"已保存记忆记录: {record_id}", record_id

    def _create_jsonl(
        self, kind, title, content, scope, tags, source, confidence, related_task_id, now,
    ) -> tuple[str, str]:
        records = self._read_all()
        record_id = f"{_RECORD_PREFIX}{_next_id(records)}"
        record = {
            "record_id": record_id,
            "kind": kind,
            "scope": scope,
            "title": title,
            "content": content,
            "tags": _parse_tags_str(tags),
            "source": source,
            "confidence": confidence,
            "related_task_id": related_task_id,
            "created_at": now,
            "updated_at": now,
        }
        self._append(record)
        return f"已保存记忆记录: {record_id}", record_id

    # ── get ─────────────────────────────────────────────────────────────

    def get(self, record_id: str) -> Optional[dict]:
        if not record_id or not record_id.strip():
            return None
        record_id = record_id.strip()
        if self.db:
            row = self.db.conn.execute(
                f"SELECT {_COLUMNS} FROM memory_records WHERE record_id = ?",
                (record_id,),
            ).fetchone()
            return _row_to_record(row) if row else None
        for rec in self._read_all():
            if rec.get("record_id") == record_id:
                return rec
        return None

    # ── list ────────────────────────────────────────────────────────────

    def list(
        self,
        kind: str = "",
        scope: str = "",
        max_results: int = 20,
    ) -> list[dict]:
        max_results = max(1, min(max_results, 100))
        if self.db:
            return self._list_db(kind, scope, max_results)
        return self._list_jsonl(kind, scope, max_results)

    def _list_db(self, kind: str, scope: str, max_results: int) -> list[dict]:
        conditions = []
        params: list = []
        if kind:
            conditions.append("kind = ?")
            params.append(kind)
        if scope:
            conditions.append("scope = ?")
            params.append(scope)
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self.db.conn.execute(
            f"SELECT {_COLUMNS} FROM memory_records{where} ORDER BY updated_at DESC LIMIT ?",
            params + [max_results],
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def _list_jsonl(self, kind: str, scope: str, max_results: int) -> list[dict]:
        records = self._read_all()
        if kind:
            records = [r for r in records if r.get("kind") == kind]
        if scope:
            records = [r for r in records if r.get("scope") == scope]
        records.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
        return records[:max_results]

    # ── search ──────────────────────────────────────────────────────────

    def search(self, query: str, max_results: int = 5, kind: str = "", scope: str = "", tags: str = "") -> list[dict]:
        terms = [t.lower() for t in query.split() if t.strip()]
        if not terms:
            return []
        max_results = max(1, min(max_results, 20))
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []
        if self.db:
            return self._search_db(terms, max_results, kind, scope, tag_list)
        return self._search_jsonl(terms, max_results, kind, scope, tag_list)

    def _search_db(self, terms: list[str], max_results: int, kind: str, scope: str, tag_list: list[str]) -> list[dict]:
        like_clauses = []
        params: list = []
        for term in terms:
            like_clauses.append("title LIKE ? OR content LIKE ? OR tags LIKE ?")
            params.extend([f"%{term}%", f"%{term}%", f"%{term}%"])
        where = f"WHERE ({' OR '.join(like_clauses)})"
        if kind:
            where += " AND kind = ?"
            params.append(kind)
        if scope:
            where += " AND scope = ?"
            params.append(scope)
        if tag_list:
            for tag in tag_list:
                where += " AND tags LIKE ?"
                params.append(f"%{tag}%")
        rows = self.db.conn.execute(
            f"SELECT {_COLUMNS} FROM memory_records {where} ORDER BY updated_at DESC",
            params,
        ).fetchall()
        scored = []
        for row in rows:
            record = _row_to_record(row)
            haystack = f"{record['title']} {record['content']} {' '.join(record['tags'])}".lower()
            score = sum(haystack.count(term) for term in terms)
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda x: (-x[0], x[1]["record_id"]))
        return [r for _, r in scored[:max_results]]

    def _search_jsonl(self, terms: list[str], max_results: int, kind: str, scope: str, tag_list: list[str]) -> list[dict]:
        scored = []
        for rec in self._read_all():
            if kind and rec.get("kind") != kind:
                continue
            if scope and rec.get("scope") != scope:
                continue
            if tag_list:
                rec_tags = [t.lower() for t in rec.get("tags", [])]
                if not all(any(ft in rt for rt in rec_tags) for ft in tag_list):
                    continue
            haystack = f"{rec.get('title', '')} {rec.get('content', '')} {' '.join(rec.get('tags', []))}".lower()
            score = sum(haystack.count(term) for term in terms)
            if score > 0:
                scored.append((score, rec))
        scored.sort(key=lambda x: (-x[0], x[1].get("record_id", "")))
        return [r for _, r in scored[:max_results]]

    # ── delete ──────────────────────────────────────────────────────────

    def delete(self, record_id: str) -> str:
        if not record_id or not record_id.strip():
            return "record_id 不能为空"
        record_id = record_id.strip()
        if self.db:
            row = self.db.conn.execute(
                "SELECT 1 FROM memory_records WHERE record_id = ?", (record_id,),
            ).fetchone()
            if not row:
                return f"未找到记录: {record_id}"
            self.db.conn.execute("DELETE FROM memory_records WHERE record_id = ?", (record_id,))
            self.db.conn.commit()
            return f"已删除记录: {record_id}"
        records = self._read_all()
        found = any(r.get("record_id") == record_id for r in records)
        if not found:
            return f"未找到记录: {record_id}"
        records = [r for r in records if r.get("record_id") != record_id]
        self._rewrite_all(records)
        return f"已删除记录: {record_id}"

    # ── JSONL helpers ───────────────────────────────────────────────────

    def _read_all(self) -> list[dict]:
        return read_jsonl(self.path)

    def _append(self, record: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _rewrite_all(self, records: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
