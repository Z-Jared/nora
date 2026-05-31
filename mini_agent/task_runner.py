from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mini_agent.durable_events import HANDOFF_ACCEPTED, HANDOFF_CREATED
from mini_agent.tools_common import read_jsonl


VALID_STEP_STATUSES = {"pending", "in_progress", "done", "blocked"}


class TaskManager:
    def __init__(self, path: Path = None, history_path: Path = None, db=None,
                 durable_store=None, enable_durable_shadow: bool = False, event_store=None):
        self.path = path
        self.history_path = history_path or Path("data/task_history.jsonl")
        self.db = db
        self.durable_store = durable_store
        self.enable_durable_shadow = enable_durable_shadow
        self.event_store = event_store

    def _record_event(
        self,
        event_type: str,
        summary: str = "",
        task_id: str = None,
        trace_id: str = None,
        checkpoint_id: str = None,
        source: str = "task_manager",
        payload: dict = None,
    ) -> None:
        if not self.event_store:
            return
        try:
            self.event_store.record(
                event_type=event_type,
                task_id=task_id,
                trace_id=trace_id,
                checkpoint_id=checkpoint_id,
                source=source,
                summary=summary,
                payload=payload or {},
            )
        except Exception:
            pass

    def _record_checkpoint_event(self, sync_result: dict, summary: str, payload: dict) -> None:
        checkpoint_id = sync_result.get("checkpoint_id") if sync_result else None
        if not checkpoint_id:
            return
        self._record_event(
            "checkpoint_added",
            task_id=sync_result.get("task_id"),
            checkpoint_id=checkpoint_id,
            summary=summary,
            payload=payload,
        )

    def start(self, goal: str, steps: str) -> str:
        goal = goal.strip()
        parsed_steps = [line.strip() for line in steps.splitlines() if line.strip()]
        if not goal:
            return "请提供任务目标。"
        if not parsed_steps:
            return "请提供任务步骤。"

        task = {
            "goal": goal,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "summary": "",
            "steps": [
                {"id": index, "text": step, "status": "pending", "note": "", "summary": ""}
                for index, step in enumerate(parsed_steps, 1)
            ],
        }
        self._write(task)
        sync_result = self._shadow_sync_to_durable(task)
        self._record_event(
            "task_created",
            task_id=sync_result.get("task_id"),
            summary=goal,
            payload={"goal": goal, "step_count": len(parsed_steps)},
        )
        return f"已创建任务: {goal}\n{self._format(task)}"

    def update_step(self, step_id: int, status: str, note: str = "", summary: str = "") -> str:
        if status not in VALID_STEP_STATUSES:
            return f"无效状态: {status}。可用状态: pending, in_progress, done, blocked。"

        note = note.strip()
        summary = summary.strip()
        if status == "blocked" and not note and not summary:
            return "标记 blocked 时请填写 note 或 summary 说明阻塞原因。"

        task = self._read()
        if not task:
            return "暂无任务。"

        for step in task["steps"]:
            if step["id"] == step_id:
                step["status"] = status
                step["note"] = note
                step["summary"] = summary
                self._write(task)
                checkpoint = None
                if status in ("done", "blocked"):
                    snapshot = {
                        "goal": task.get("goal", ""),
                        "status": task.get("status", ""),
                        "steps": task.get("steps", []),
                        "current_step": step_id,
                    }
                    if note:
                        snapshot["note"] = note
                    if summary:
                        snapshot["summary"] = summary
                    checkpoint = {
                        "step_id": step_id,
                        "run_id": "run_1",
                        "state_snapshot": snapshot,
                        "description": f"update_step: step {step_id} {status}",
                    }
                sync_result = self._shadow_sync_to_durable(task, checkpoint=checkpoint)
                payload = {
                    "step_id": step_id,
                    "status": status,
                    "note": note,
                    "summary": summary,
                }
                self._record_event(
                    "step_updated",
                    task_id=sync_result.get("task_id"),
                    checkpoint_id=sync_result.get("checkpoint_id"),
                    summary=f"step {step_id} -> {status}",
                    payload=payload,
                )
                self._record_checkpoint_event(
                    sync_result,
                    summary=f"checkpoint for step {step_id} {status}",
                    payload=payload,
                )
                message = f"已更新步骤 {step_id}: {status}"
                if status == "done" and not summary:
                    message += "。建议填写 summary 记录执行结果。"
                return message

        return f"没有找到步骤: {step_id}"

    def get_current_task(self) -> dict:
        return self._read()

    def list(self) -> str:
        task = self._read()
        if not task:
            return "暂无任务。"
        return self._format(task)

    def finish(self, summary: str) -> str:
        task = self._read()
        if not task:
            return "暂无任务。"

        task["status"] = "finished"
        task["finished_at"] = datetime.now(timezone.utc).isoformat()
        task["summary"] = summary.strip()
        self._write(task)
        history_id = self._append_history(task)
        sync_result = self._shadow_sync_to_durable(task)
        self._record_event(
            "task_finished",
            task_id=sync_result.get("task_id"),
            summary=task["goal"],
            payload={"goal": task["goal"], "summary": task["summary"]},
        )
        steps = task.get("steps") or []
        self._record_event(
            HANDOFF_CREATED,
            task_id=sync_result.get("task_id"),
            summary=f"handoff created: {history_id}",
            payload={
                "artifact_type": "task_history",
                "history_id": history_id,
                "status": "created",
                "step_count": len(steps),
                "done_step_count": sum(1 for s in steps if s.get("status") == "done"),
                "blocked_step_count": sum(1 for s in steps if s.get("status") == "blocked"),
                "summary_present": bool(task.get("summary", "").strip()),
            },
        )
        return f"已完成任务: {task['goal']}\n总结: {task['summary']}"

    def _shadow_sync_to_durable(self, task: dict, checkpoint: dict = None) -> dict:
        if not self.enable_durable_shadow or not self.durable_store:
            return {}
        try:
            from mini_agent.durable_tasks import task_manager_task_to_durable

            # Preserve existing checkpoints, checkpoint_refs, and trace_refs
            # only if this is the same legacy task (goal + created_at match)
            existing_checkpoints = []
            step_checkpoint_refs = {}
            existing_trace_refs = []
            existing = self.durable_store.get_task("dtask_shadow_1")
            if existing:
                same_task = (
                    existing.goal == task.get("goal", "")
                    and existing.created_at == task.get("created_at", "")
                )
                if same_task:
                    existing_checkpoints = list(existing.checkpoints)
                    existing_trace_refs = list(existing.trace_refs)
                    for s in existing.steps:
                        if s.checkpoint_ref:
                            step_checkpoint_refs[s.id] = s.checkpoint_ref

            # Create new checkpoint if requested
            new_checkpoint = None
            if checkpoint:
                from mini_agent.durable_tasks import DurableCheckpoint, _next_id, _now_iso
                existing_ids = [c.checkpoint_id for c in existing_checkpoints]
                cp_id = _next_id("cp_", existing_ids)
                new_checkpoint = DurableCheckpoint(
                    checkpoint_id=cp_id,
                    step_id=checkpoint.get("step_id", 0),
                    run_id=checkpoint.get("run_id", "run_1"),
                    created_at=_now_iso(),
                    state_snapshot=checkpoint.get("state_snapshot", {}),
                    description=checkpoint.get("description", ""),
                )
                existing_checkpoints.append(new_checkpoint)
                step_checkpoint_refs[checkpoint.get("step_id", 0)] = cp_id

            durable_task = task_manager_task_to_durable(
                task, task_id="dtask_shadow_1",
                checkpoints=existing_checkpoints if existing_checkpoints else None,
                step_checkpoint_refs=step_checkpoint_refs if step_checkpoint_refs else None,
            )
            durable_task.trace_refs = existing_trace_refs
            self.durable_store.upsert_task(durable_task)
            return {
                "task_id": durable_task.task_id,
                "checkpoint_id": new_checkpoint.checkpoint_id if new_checkpoint else None,
            }
        except Exception:
            return {}

    def list_history(self, max_results: int = 20) -> str:
        records = self._read_history()
        if not records:
            return "暂无任务历史。"
        max_results = max(1, min(max_results, 100))
        return "\n".join(_format_history_record(record) for record in records[-max_results:])

    def search_history(self, query: str, max_results: int = 10) -> str:
        terms = [term.lower() for term in query.split() if term.strip()]
        if not terms:
            return "请提供搜索关键词。"
        max_results = max(1, min(max_results, 50))
        if self.db:
            return self._search_history_db(terms, max_results)
        return self._search_history_jsonl(terms, max_results)

    def _search_history_db(self, terms: list[str], max_results: int) -> str:
        conditions = " OR ".join(["goal LIKE ? OR summary LIKE ? OR steps_json LIKE ?"] * len(terms))
        params = []
        for term in terms:
            params.extend([f"%{term}%", f"%{term}%", f"%{term}%"])
        rows = self.db.conn.execute(
            f"SELECT id, goal, status, created_at, finished_at, summary, steps_json FROM task_history WHERE {conditions} ORDER BY created_at DESC",
            params,
        ).fetchall()
        if not rows:
            return "没有找到匹配的任务历史。"
        matches = []
        for row in rows:
            record = _row_to_history_record(row)
            haystack = json.dumps(record, ensure_ascii=False).lower()
            score = sum(haystack.count(term) for term in terms)
            if score > 0:
                matches.append((score, record))
        if not matches:
            return "没有找到匹配的任务历史。"
        matches.sort(key=lambda item: (-item[0], item[1].get("id", "")))
        return "\n".join(_format_history_record(record) for _, record in matches[:max_results])

    def _search_history_jsonl(self, terms: list[str], max_results: int) -> str:
        matches = []
        for record in self._read_history():
            haystack = json.dumps(record, ensure_ascii=False).lower()
            score = sum(haystack.count(term) for term in terms)
            if score > 0:
                matches.append((score, record))
        if not matches:
            return "没有找到匹配的任务历史。"
        matches.sort(key=lambda item: (-item[0], item[1].get("id", "")))
        return "\n".join(_format_history_record(record) for _, record in matches[:max_results])

    def restore(self, history_id: str) -> str:
        history_id = history_id.strip()
        if not history_id:
            return "请提供任务历史 id。"
        record = self._find_history(history_id)
        if not record:
            return f"没有找到任务历史: {history_id}"

        task = dict(record)
        task.pop("id", None)
        task["status"] = "active"
        task["finished_at"] = None
        task["restored_from"] = history_id
        task["restored_at"] = datetime.now(timezone.utc).isoformat()
        self._write(task)
        sync_result = self._shadow_sync_to_durable(task)
        self._record_event(
            "task_status_changed",
            task_id=sync_result.get("task_id"),
            summary=f"restored from {history_id}",
            payload={"restored_from": history_id, "status": "active"},
        )
        steps = task.get("steps") or []
        self._record_event(
            HANDOFF_ACCEPTED,
            task_id=sync_result.get("task_id"),
            summary=f"handoff accepted: {history_id}",
            payload={
                "artifact_type": "task_history",
                "history_id": history_id,
                "status": "accepted",
                "step_count": len(steps),
                "done_step_count": sum(1 for s in steps if s.get("status") == "done"),
                "blocked_step_count": sum(1 for s in steps if s.get("status") == "blocked"),
                "restored_from_present": bool(history_id),
            },
        )
        return f"已恢复任务: {history_id}\n{self._format(task)}"

    def run_once(self) -> str:
        task = self._read()
        if not task:
            return "暂无任务。"

        if task.get("status") == "finished":
            return "任务已完成，无需继续执行。"

        for step in task["steps"]:
            if step["status"] in {"pending", "blocked"}:
                step["status"] = "in_progress"
                step["note"] = "已选为下一步执行"
                self._write(task)
                checkpoint = {
                    "step_id": step["id"],
                    "run_id": "run_1",
                    "state_snapshot": {
                        "goal": task.get("goal", ""),
                        "status": task.get("status", ""),
                        "steps": task.get("steps", []),
                        "current_step": step["id"],
                    },
                    "description": f"run_once: step {step['id']} in_progress",
                }
                sync_result = self._shadow_sync_to_durable(task, checkpoint=checkpoint)
                payload = {
                    "step_id": step["id"],
                    "status": "in_progress",
                    "text": step["text"],
                    "note": step["note"],
                }
                self._record_event(
                    "step_updated",
                    task_id=sync_result.get("task_id"),
                    checkpoint_id=sync_result.get("checkpoint_id"),
                    summary=f"step {step['id']} -> in_progress",
                    payload=payload,
                )
                self._record_checkpoint_event(
                    sync_result,
                    summary=f"checkpoint for step {step['id']} in_progress",
                    payload=payload,
                )
                return "\n".join(
                    [
                        f"下一步: {step['id']}. {step['text']}",
                        f"建议工具类型: {_suggest_tool_type(step['text'])}",
                        "请根据该步骤选择合适工具执行，完成后调用 update_task_step 更新状态并填写 summary。",
                    ]
                )

            if step["status"] == "in_progress":
                sync_result = self._shadow_sync_to_durable(task)
                self._record_event(
                    "step_updated",
                    task_id=sync_result.get("task_id"),
                    summary=f"step {step['id']} still in_progress",
                    payload={"step_id": step["id"], "status": "in_progress", "text": step["text"]},
                )
                return "\n".join(
                    [
                        f"继续当前步骤: {step['id']}. {step['text']}",
                        f"建议工具类型: {_suggest_tool_type(step['text'])}",
                        "请根据该步骤选择合适工具执行，完成后调用 update_task_step 更新状态并填写 summary。",
                    ]
                )

        return "没有待执行步骤。可以调用 finish_task 完成任务。"

    def _read(self) -> dict:
        if self.db:
            return self._read_db()
        return self._read_json()

    def _read_db(self) -> dict:
        row = self.db.conn.execute(
            "SELECT goal, status, created_at, finished_at, summary, steps_json, restored_from, restored_at FROM current_task WHERE id = 1"
        ).fetchone()
        if not row or not row[0]:
            return {}
        steps = json.loads(row[5]) if row[5] else []
        return {
            "goal": row[0],
            "status": row[1],
            "created_at": row[2],
            "finished_at": row[3],
            "summary": row[4] or "",
            "steps": steps,
            "restored_from": row[6],
            "restored_at": row[7],
        }

    def _read_json(self) -> dict:
        if not self.path or not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write(self, task: dict) -> None:
        if self.db:
            self._write_db(task)
        else:
            self._write_json(task)

    def _write_db(self, task: dict) -> None:
        self.db.conn.execute(
            "INSERT OR REPLACE INTO current_task (id, goal, status, created_at, finished_at, summary, steps_json, restored_from, restored_at) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task.get("goal", ""),
                task.get("status", ""),
                task.get("created_at", ""),
                task.get("finished_at"),
                task.get("summary", ""),
                json.dumps(task.get("steps", []), ensure_ascii=False),
                task.get("restored_from"),
                task.get("restored_at"),
            ),
        )
        self.db.conn.commit()

    def _write_json(self, task: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_history(self, task: dict) -> str:
        if self.db:
            return self._append_history_db(task)
        return self._append_history_jsonl(task)

    def _append_history_db(self, task: dict) -> str:
        row = self.db.conn.execute(
            "SELECT MAX(CAST(SUBSTR(id, 6) AS INTEGER)) FROM task_history WHERE id LIKE 'task_%'"
        ).fetchone()
        next_num = (row[0] or 0) + 1
        history_id = f"task_{next_num}"
        self.db.conn.execute(
            "INSERT INTO task_history (id, goal, status, created_at, finished_at, summary, steps_json, restored_from, restored_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                history_id,
                task.get("goal", ""),
                task.get("status", ""),
                task.get("created_at", ""),
                task.get("finished_at"),
                task.get("summary", ""),
                json.dumps(task.get("steps", []), ensure_ascii=False),
                task.get("restored_from"),
                task.get("restored_at"),
            ),
        )
        self.db.conn.commit()
        return history_id

    def _append_history_jsonl(self, task: dict) -> str:
        history_id = f"task_{_next_history_id(self._read_history())}"
        record = dict(task)
        record["id"] = history_id
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        with self.history_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return history_id

    def _read_history(self) -> list[dict]:
        if self.db:
            return self._read_history_db()
        return read_jsonl(self.history_path)

    def _read_history_db(self) -> list[dict]:
        rows = self.db.conn.execute(
            "SELECT id, goal, status, created_at, finished_at, summary, steps_json FROM task_history ORDER BY created_at"
        ).fetchall()
        return [_row_to_history_record(row) for row in rows]

    def _find_history(self, history_id: str) -> dict:
        if self.db:
            row = self.db.conn.execute(
                "SELECT id, goal, status, created_at, finished_at, summary, steps_json FROM task_history WHERE id = ?",
                (history_id,),
            ).fetchone()
            return _row_to_history_record(row) if row else {}
        for record in self._read_history():
            if record.get("id") == history_id:
                return record
        return {}

    def _format(self, task: dict) -> str:
        lines = [f"任务: {task['goal']} (status={task['status']})"]
        if task.get("restored_from"):
            lines.append(f"restored_from={task['restored_from']}")
        current_steps = [step for step in task["steps"] if step.get("status") == "in_progress"]
        if current_steps:
            lines.append("当前步骤: " + ", ".join(f"{step['id']}. {step['text']}" for step in current_steps))
        for step in task["steps"]:
            details = []
            if step.get("note"):
                details.append(f"备注: {step['note']}")
            if step.get("summary"):
                details.append(f"总结: {step['summary']}")
            suffix = f" - {'; '.join(details)}" if details else ""
            lines.append(f"{step['id']}. [{step['status']}] {step['text']}{suffix}")
        if task.get("summary"):
            lines.append(f"总结: {task['summary']}")
        return "\n".join(lines)


def _row_to_history_record(row) -> dict:
    steps = json.loads(row[6]) if row[6] else []
    return {
        "id": row[0],
        "goal": row[1],
        "status": row[2],
        "created_at": row[3],
        "finished_at": row[4],
        "summary": row[5] or "",
        "steps": steps,
    }


def _next_history_id(records: list[dict]) -> int:
    max_id = 0
    for record in records:
        raw = str(record.get("id", ""))
        if raw.startswith("task_"):
            try:
                max_id = max(max_id, int(raw[5:]))
            except ValueError:
                pass
    return max_id + 1


def _suggest_tool_type(step_text: str) -> str:
    text = step_text.lower()
    if any(term in text for term in ["测试", "test", "unittest", "验证"]):
        return "test/read 或 test/execute；运行测试等高风险执行仍需确认"
    if any(term in text for term in ["git", "提交", "暂存", "commit", "diff"]):
        return "git/read 或 git/write；暂存和提交仍需确认"
    if any(term in text for term in ["浏览器", "browser", "页面", "click", "点击", "输入"]):
        return "browser/read 或 browser/interact；点击和输入仍需确认"
    if any(term in text for term in ["进程", "process", "启动", "停止", "后台"]):
        return "process/read 或 process/execute；启动和停止仍需确认"
    if any(term in text for term in ["写", "修改", "实现", "patch", "文件", "代码"]):
        return "workspace/read 或 workspace/write；写入和 patch 仍需确认"
    return "workspace/read 或 planning/read"


def _format_history_record(record: dict) -> str:
    steps = record.get("steps") or []
    done = sum(1 for step in steps if step.get("status") == "done")
    blocked = sum(1 for step in steps if step.get("status") == "blocked")
    return " | ".join(
        [
            str(record.get("id", "")),
            str(record.get("goal", "")),
            f"status={record.get('status', '')}",
            f"done={done}/{len(steps)}",
            f"blocked={blocked}",
            f"summary={record.get('summary', '')}",
        ]
    )
