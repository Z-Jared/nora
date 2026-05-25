import json
from datetime import datetime, timezone
from pathlib import Path


VALID_STEP_STATUSES = {"pending", "in_progress", "done", "blocked"}


class TaskManager:
    def __init__(self, path: Path):
        self.path = path

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

        task = self._read()
        if not task:
            return "暂无任务。"

        for step in task["steps"]:
            if step["id"] == step_id:
                step["status"] = status
                step["note"] = note.strip()
                step["summary"] = summary.strip()
                self._write(task)
                return f"已更新步骤 {step_id}: {status}"

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
        return f"已完成任务: {task['goal']}\n总结: {task['summary']}"

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
                        "请根据该步骤选择合适工具执行，完成后调用 update_task_step 更新状态并填写 summary。",
                    ]
                )

            if step["status"] == "in_progress":
                return "\n".join(
                    [
                        f"继续当前步骤: {step['id']}. {step['text']}",
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

    def _format(self, task: dict) -> str:
        lines = [f"任务: {task['goal']} (status={task['status']})"]
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
