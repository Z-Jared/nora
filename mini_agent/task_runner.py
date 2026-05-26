from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mini_agent.tools_common import read_jsonl


VALID_STEP_STATUSES = {"pending", "in_progress", "done", "blocked"}


class TaskManager:
    def __init__(self, path: Path, history_path: Path = Path("data/task_history.jsonl")):
        self.path = path
        self.history_path = history_path

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
                message = f"已更新步骤 {step_id}: {status}"
                if status == "done" and not summary:
                    message += "。建议填写 summary 记录执行结果。"
                return message

        return f"没有找到步骤: {step_id}"

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
        self._append_history(task)
        return f"已完成任务: {task['goal']}\n总结: {task['summary']}"

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
                return "\n".join(
                    [
                        f"下一步: {step['id']}. {step['text']}",
                        f"建议工具类型: {_suggest_tool_type(step['text'])}",
                        "请根据该步骤选择合适工具执行，完成后调用 update_task_step 更新状态并填写 summary。",
                    ]
                )

            if step["status"] == "in_progress":
                return "\n".join(
                    [
                        f"继续当前步骤: {step['id']}. {step['text']}",
                        f"建议工具类型: {_suggest_tool_type(step['text'])}",
                        "请根据该步骤选择合适工具执行，完成后调用 update_task_step 更新状态并填写 summary。",
                    ]
                )

        return "没有待执行步骤。可以调用 finish_task 完成任务。"

    def _read(self) -> dict:
        if not self.path.exists():
            return {}

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write(self, task: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_history(self, task: dict) -> str:
        history_id = f"task_{_next_history_id(self._read_history())}"
        record = dict(task)
        record["id"] = history_id
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        with self.history_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return history_id

    def _read_history(self) -> list[dict]:
        return read_jsonl(self.history_path)

    def _find_history(self, history_id: str) -> dict:
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
