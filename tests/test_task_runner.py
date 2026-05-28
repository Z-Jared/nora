import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.task_runner import TaskManager


class TaskManagerTests(unittest.TestCase):
    def test_starts_updates_lists_and_finishes_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json", Path(tmpdir) / "task_history.jsonl")

            started = manager.start("给 agent 增加新工具", "读代码\n写测试\n实现")
            manager.update_step(2, "done", "测试已写好")
            listing = manager.list()
            finished = manager.finish("实现完成并通过测试")
            finished_listing = manager.list()
            history = manager.list_history()
            search = manager.search_history("通过测试")

        self.assertIn("已创建任务", started)
        self.assertIn("2. [done] 写测试 - 备注: 测试已写好", listing)
        self.assertIn("已完成任务", finished)
        self.assertIn("status=finished", finished_listing)
        self.assertIn("task_1", history)
        self.assertIn("给 agent 增加新工具", history)
        self.assertIn("实现完成并通过测试", search)

    def test_history_reports_empty_and_search_requires_query(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json", Path(tmpdir) / "task_history.jsonl")

            history = manager.list_history()
            search = manager.search_history("")

        self.assertIn("暂无任务历史", history)
        self.assertIn("请提供搜索关键词", search)

    def test_restores_task_from_history_as_active_current_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json", Path(tmpdir) / "task_history.jsonl")
            manager.start("恢复目标", "已完成步骤\n阻塞步骤")
            manager.update_step(1, "done", summary="done summary")
            manager.update_step(2, "blocked", note="等待信息")
            manager.finish("暂时完成")

            restored = manager.restore("task_1")
            listing = manager.list()
            next_step = manager.run_once()

        self.assertIn("已恢复任务: task_1", restored)
        self.assertIn("任务: 恢复目标 (status=active)", listing)
        self.assertIn("restored_from=task_1", listing)
        self.assertIn("1. [done] 已完成步骤", listing)
        self.assertIn("2. [blocked] 阻塞步骤", listing)
        self.assertIn("下一步: 2. 阻塞步骤", next_step)

    def test_restore_reports_missing_history_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json", Path(tmpdir) / "task_history.jsonl")

            result = manager.restore("task_99")

        self.assertIn("没有找到任务历史", result)

    def test_rejects_invalid_step_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("目标", "步骤一")

            result = manager.update_step(1, "bad", "nope")

        self.assertIn("无效状态", result)

    def test_reports_no_active_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")

            self.assertEqual(manager.list(), "暂无任务。")

    def test_run_once_marks_next_pending_step_in_progress(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("给 agent 增加新工具", "读代码\n写测试")

            result = manager.run_once()
            listing = manager.list()

        self.assertIn("下一步: 1. 读代码", result)
        self.assertIn("1. [in_progress] 读代码", listing)

    def test_run_once_reports_when_no_steps_left(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("目标", "步骤一")
            manager.update_step(1, "done", "完成")

            result = manager.run_once()

        self.assertIn("没有待执行步骤", result)

    def test_update_step_records_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("目标", "步骤一")

            manager.update_step(1, "done", note="测试通过", summary="实现了新工具")
            listing = manager.list()

        self.assertIn("备注: 测试通过", listing)
        self.assertIn("总结: 实现了新工具", listing)

    def test_lists_legacy_task_without_step_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "task.json"
            path.write_text(
                json.dumps(
                    {
                        "goal": "旧任务",
                        "status": "active",
                        "steps": [{"id": 1, "text": "步骤一", "status": "pending", "note": ""}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            manager = TaskManager(path)

            listing = manager.list()

        self.assertIn("旧任务", listing)
        self.assertIn("1. [pending] 步骤一", listing)

    def test_run_once_mentions_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("目标", "步骤一")

            result = manager.run_once()

        self.assertIn("summary", result)

    def test_done_without_summary_returns_guidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("目标", "步骤一")

            result = manager.update_step(1, "done")

        self.assertIn("建议填写 summary", result)

    def test_blocked_requires_reason(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("目标", "步骤一")

            result = manager.update_step(1, "blocked")

        self.assertIn("阻塞原因", result)

    def test_list_highlights_current_step(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("目标", "步骤一\n步骤二")
            manager.run_once()

            listing = manager.list()

        self.assertIn("当前步骤: 1. 步骤一", listing)

    def test_run_once_suggests_tool_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("目标", "运行测试")

            result = manager.run_once()

        self.assertIn("建议工具类型", result)
        self.assertIn("test/", result)


class ShadowWriteTests(unittest.TestCase):
    """Tests for TaskManager optional durable shadow write."""

    def test_default_no_shadow_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from mini_agent.durable_tasks import DurableTaskStore
            db_path = Path(tmpdir) / "durable.db"
            from mini_agent.database import NoraDB
            db = NoraDB(db_path)
            store = DurableTaskStore(db=db)
            manager = TaskManager(Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                                  durable_store=store, enable_durable_shadow=False)
            manager.start("test goal", "step one")
            tasks = store.list_tasks()
            self.assertEqual(tasks, [])
            db.conn.close()

    def test_shadow_write_on_start(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from mini_agent.durable_tasks import DurableTaskStore
            db_path = Path(tmpdir) / "durable.db"
            from mini_agent.database import NoraDB
            db = NoraDB(db_path)
            store = DurableTaskStore(db=db)
            manager = TaskManager(Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                                  durable_store=store, enable_durable_shadow=True)
            manager.start("build feature", "plan\nimplement\ntest")
            tasks = store.list_tasks()
            self.assertEqual(len(tasks), 1)
            dt = tasks[0]
            self.assertEqual(dt.goal, "build feature")
            self.assertEqual(dt.status, "pending")  # all steps pending
            self.assertEqual(len(dt.steps), 3)
            db.conn.close()

    def test_shadow_write_on_update_step(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from mini_agent.durable_tasks import DurableTaskStore
            db_path = Path(tmpdir) / "durable.db"
            from mini_agent.database import NoraDB
            db = NoraDB(db_path)
            store = DurableTaskStore(db=db)
            manager = TaskManager(Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                                  durable_store=store, enable_durable_shadow=True)
            manager.start("build feature", "plan\nimplement")
            manager.update_step(1, "done", summary="planned")

            tasks = store.list_tasks()
            dt = tasks[0]
            self.assertEqual(dt.status, "running")  # mixed done/pending = running
            self.assertEqual(dt.steps[0].status, "done")
            self.assertEqual(dt.steps[0].summary, "planned")
            self.assertEqual(dt.steps[1].status, "pending")
            db.conn.close()

    def test_shadow_write_on_finish(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from mini_agent.durable_tasks import DurableTaskStore
            db_path = Path(tmpdir) / "durable.db"
            from mini_agent.database import NoraDB
            db = NoraDB(db_path)
            store = DurableTaskStore(db=db)
            manager = TaskManager(Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                                  durable_store=store, enable_durable_shadow=True)
            manager.start("test goal", "step one")
            manager.finish("done")

            tasks = store.list_tasks()
            dt = tasks[0]
            self.assertEqual(dt.status, "completed")
            self.assertIsNotNone(dt.finished_at)
            self.assertEqual(dt.input_summary, "done")
            db.conn.close()

    def test_shadow_write_failure_does_not_affect_task_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            class BrokenStore:
                def upsert_task(self, task):
                    raise RuntimeError("store broken")

            manager = TaskManager(Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                                  durable_store=BrokenStore(), enable_durable_shadow=True)
            result = manager.start("test goal", "step one")
            self.assertIn("已创建任务", result)

            result = manager.update_step(1, "done", summary="done")
            self.assertIn("已更新步骤", result)

            result = manager.finish("completed")
            self.assertIn("已完成任务", result)

            # Verify old task manager state is intact
            listing = manager.list()
            self.assertIn("status=finished", listing)

    def test_shadow_write_with_real_sqlite_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from mini_agent.durable_tasks import DurableTaskStore, TaskStatus
            db_path = Path(tmpdir) / "durable.db"
            from mini_agent.database import NoraDB
            db = NoraDB(db_path)
            store = DurableTaskStore(db=db)
            manager = TaskManager(Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                                  durable_store=store, enable_durable_shadow=True)

            manager.start("real task", "step a\nstep b")
            manager.update_step(1, "done", summary="a done")
            manager.update_step(2, "blocked", note="waiting for input")
            manager.finish("all done")

            tasks = store.list_tasks()
            self.assertEqual(len(tasks), 1)
            dt = tasks[0]
            self.assertEqual(dt.goal, "real task")
            self.assertEqual(dt.status, "completed")
            self.assertEqual(dt.steps[0].status, "done")
            self.assertEqual(dt.steps[1].status, "blocked")
            self.assertEqual(dt.steps[1].note, "waiting for input")
            db.conn.close()
