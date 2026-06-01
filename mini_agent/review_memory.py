"""Review-memory capture for Nora.

Turns bounded review/task summaries into structured memory records.
Never saves raw diffs, prompts, shell output, env vars, or full DONE/REVIEW bodies.
"""

from __future__ import annotations

import re
from typing import Optional

from mini_agent.memory import is_sensitive_text
from mini_agent.memory_records import MemoryRecordStore

# Boundaries
_MAX_TITLE = 200
_MAX_CONTENT = 2000
_MAX_LEARNINGS = 500
_MAX_RISKS = 500
_MAX_DECISIONS = 500

# Raw content patterns to reject
_RAW_PATTERNS = [
    re.compile(r"^diff --git", re.MULTILINE),
    re.compile(r"^@@\s+[-+]\d+", re.MULTILINE),
    re.compile(r"^\+\+\+\s+[ab]/", re.MULTILINE),
    re.compile(r"^---\s+[ab]/", re.MULTILINE),
    re.compile(r"OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY", re.IGNORECASE),
    re.compile(r"Bearer\s+ey[A-Za-z0-9]", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"^\$\s+", re.MULTILINE),  # shell prompts
    re.compile(r"^PS\s+", re.MULTILINE),  # PowerShell prompts
    # Env var assignment: FOO=bar, export FOO=bar, or embedded in prose
    re.compile(r"(?:export\s+)?[A-Z_][A-Z0-9_]*="),
    # Prompt / transcript markers
    re.compile(r"^(?:system|user|assistant)\s*:", re.MULTILINE | re.IGNORECASE),
    re.compile(r"<\|(?:system|user|assistant|endoftext)\|>", re.IGNORECASE),
    re.compile(r"\[/?INST\]", re.IGNORECASE),
    re.compile(r"### (?:System|User|Assistant)\s*:", re.IGNORECASE),
]


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _contains_raw_content(text: str) -> bool:
    """Check if text contains raw diff/shell/env/prompt markers."""
    for pattern in _RAW_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _is_safe(text: str) -> bool:
    """Check if text is safe to save: not sensitive, no raw content."""
    if not text or not text.strip():
        return False
    if is_sensitive_text(text):
        return False
    if _contains_raw_content(text):
        return False
    return True


def _build_dedupe_key(task_id: str, status: str, title: str, kind: str) -> str:
    return f"{task_id}|{status}|{title.strip().lower()}|{kind}"


class ReviewMemoryCapture:
    """Captures bounded review/task summaries as structured memory records."""

    def __init__(self, store: MemoryRecordStore):
        self.store = store

    def capture(
        self,
        task_id: str,
        status: str,
        title: str,
        summary: str = "",
        learnings: str = "",
        risks: str = "",
        decisions: str = "",
        source: str = "review",
    ) -> dict:
        """Capture review summary as memory records.

        Returns dict with 'created' (list of record dicts) and 'skipped' (list of reasons).
        """
        created = []
        skipped = []

        # Validate status
        if status not in ("approved", "changes_requested", "blocked"):
            return {"created": [], "skipped": [f"无效的 status: {status}"]}

        # Validate and bound title
        title = _truncate(title, _MAX_TITLE)
        if not _is_safe(title):
            return {"created": [], "skipped": ["title 包含敏感或原始内容"]}

        # Build tags
        tags = f"review,{status}"
        if task_id:
            tags += ",task"

        # For approved: create task_learning, decision, risk, fact records
        if status == "approved":
            # Task learning from summary
            if summary and _is_safe(summary):
                summary_bounded = _truncate(summary, _MAX_CONTENT)
                rec = self._create_if_not_dup(
                    kind="task_learning",
                    title=title,
                    content=summary_bounded,
                    tags=tags,
                    source=source,
                    related_task_id=task_id,
                    status=status,
                )
                if rec:
                    created.append(rec)
                else:
                    skipped.append("task_learning 重复或创建失败")

            # Learnings
            if learnings and _is_safe(learnings):
                learnings_bounded = _truncate(learnings, _MAX_LEARNINGS)
                rec = self._create_if_not_dup(
                    kind="task_learning",
                    title=f"{title} - 学习",
                    content=learnings_bounded,
                    tags=tags + ",learnings",
                    source=source,
                    related_task_id=task_id,
                    status=status,
                )
                if rec:
                    created.append(rec)

            # Decisions
            if decisions and _is_safe(decisions):
                decisions_bounded = _truncate(decisions, _MAX_DECISIONS)
                rec = self._create_if_not_dup(
                    kind="decision",
                    title=title,
                    content=decisions_bounded,
                    tags=tags,
                    source=source,
                    related_task_id=task_id,
                    status=status,
                )
                if rec:
                    created.append(rec)

            # Risks
            if risks and _is_safe(risks):
                risks_bounded = _truncate(risks, _MAX_RISKS)
                rec = self._create_if_not_dup(
                    kind="risk",
                    title=title,
                    content=risks_bounded,
                    tags=tags,
                    source=source,
                    related_task_id=task_id,
                    status=status,
                )
                if rec:
                    created.append(rec)

        # For changes_requested/blocked: only allow explicit risk
        else:
            if risks and _is_safe(risks):
                risks_bounded = _truncate(risks, _MAX_RISKS)
                rec = self._create_if_not_dup(
                    kind="risk",
                    title=f"{title} - {status}",
                    content=risks_bounded,
                    tags=tags,
                    source=source,
                    related_task_id=task_id,
                    status=status,
                )
                if rec:
                    created.append(rec)

        return {"created": created, "skipped": skipped}

    def _create_if_not_dup(
        self,
        kind: str,
        title: str,
        content: str,
        tags: str,
        source: str,
        related_task_id: str,
        status: str,
    ) -> Optional[dict]:
        """Create record if not a duplicate based on task_id/status/title/kind."""
        # Check for existing duplicate
        dedupe_key = _build_dedupe_key(related_task_id, status, title, kind)
        existing = self.store.list(kind=kind, max_results=100)
        for rec in existing:
            if rec.get("related_task_id") == related_task_id:
                existing_key = _build_dedupe_key(
                    rec.get("related_task_id", ""),
                    status,
                    rec.get("title", ""),
                    rec.get("kind", ""),
                )
                if existing_key == dedupe_key:
                    return None  # Duplicate

        # Create record
        msg, record_id = self.store.create(
            kind=kind,
            title=title,
            content=content,
            scope="project",
            tags=tags,
            source=source,
            related_task_id=related_task_id,
        )
        if record_id:
            return self.store.get(record_id)
        return None
