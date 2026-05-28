"""Tests for durable task store."""

import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.database import NoraDB
from mini_agent.durable_tasks import (
    DurableCheckpoint,
    DurableStep,
    DurableTask,
    DurableTaskStore,
    StepStatus,
    TaskStatus,
)


class DataStructureTests(unittest.TestCase):
    def test_step_defaults(self):
        step = DurableStep(id=1, text="do something")
        self.assertEqual(step.status, StepStatus.PENDING)
        self.assertEqual(step.note, "")
        self.assertIsNone(step.checkpoint_ref)

    def test_step_round_trip(self):
        step = DurableStep(id=1, text="step", status="done", note="ok", tool_hint="git")
        data = step.to_dict()
        restored = DurableStep.from_dict(data)
        self.assertEqual(restored.id, 1)
        self.assertEqual(restored.text, "step")
        self.assertEqual(restored.status, "done")

    def test_checkpoint_round_trip(self):
        cp = DurableCheckpoint(
            checkpoint_id="cp_1", step_id=1, run_id="run_1",
            created_at="2026-01-01T00:00:00Z",
            state_snapshot={"key": "val"}, description="test",
        )
        data = cp.to_dict()
        restored = DurableCheckpoint.from_dict(data)
        self.assertEqual(restored.checkpoint_id, "cp_1")
        self.assertEqual(restored.state_snapshot, {"key": "val"})

    def test_task_round_trip(self):
        task = DurableTask(
            task_id="dtask_1", run_id="run_1", status="pending",
            goal="test goal",
            steps=[DurableStep(id=1, text="step 1")],
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            checkpoints=[DurableCheckpoint(
                checkpoint_id="cp_1", step_id=1, run_id="run_1",
                created_at="2026-01-01T00:00:00Z", state_snapshot={},
            )],
            trace_refs=["trace_1"],
        )
        data = task.to_dict()
        restored = DurableTask.from_dict(data)
        self.assertEqual(restored.task_id, "dtask_1")
        self.assertEqual(len(restored.steps), 1)
        self.assertEqual(len(restored.checkpoints), 1)
        self.assertEqual(restored.trace_refs, ["trace_1"])


class SQLiteStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db = NoraDB(Path(self.tmpdir) / "test.db")
        self.store = DurableTaskStore(db=self.db)

    def tearDown(self):
        self.db.conn.close()

    def test_create_task(self):
        task = self.store.create_task(goal="build feature", steps=[{"text": "plan"}, {"text": "implement"}])
        self.assertEqual(task.task_id, "dtask_1")
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(len(task.steps), 2)
        self.assertEqual(task.steps[0].text, "plan")
        self.assertEqual(task.steps[1].id, 2)

    def test_create_task_increments_id(self):
        t1 = self.store.create_task(goal="first", steps=[])
        t2 = self.store.create_task(goal="second", steps=[])
        self.assertEqual(t1.task_id, "dtask_1")
        self.assertEqual(t2.task_id, "dtask_2")

    def test_get_task(self):
        self.store.create_task(goal="test", steps=[{"text": "s1"}])
        task = self.store.get_task("dtask_1")
        self.assertIsNotNone(task)
        self.assertEqual(task.goal, "test")

    def test_get_task_not_found(self):
        self.assertIsNone(self.store.get_task("dtask_999"))

    def test_list_tasks_empty(self):
        self.assertEqual(self.store.list_tasks(), [])

    def test_list_tasks(self):
        self.store.create_task(goal="first", steps=[])
        self.store.create_task(goal="second", steps=[])
        tasks = self.store.list_tasks()
        self.assertEqual(len(tasks), 2)
        # Most recent first
        self.assertEqual(tasks[0].goal, "second")

    def test_list_tasks_respects_limit(self):
        for i in range(5):
            self.store.create_task(goal=f"task {i}", steps=[])
        tasks = self.store.list_tasks(limit=3)
        self.assertEqual(len(tasks), 3)

    def test_update_status(self):
        self.store.create_task(goal="test", steps=[])
        task = self.store.update_status("dtask_1", TaskStatus.RUNNING)
        self.assertEqual(task.status, TaskStatus.RUNNING)
        self.assertIsNone(task.finished_at)

    def test_update_status_to_terminal_sets_finished_at(self):
        self.store.create_task(goal="test", steps=[])
        self.store.update_status("dtask_1", TaskStatus.RUNNING)
        task = self.store.update_status("dtask_1", TaskStatus.COMPLETED)
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(task.finished_at)

    def test_update_status_with_failure_reason(self):
        self.store.create_task(goal="test", steps=[])
        self.store.update_status("dtask_1", TaskStatus.RUNNING)
        task = self.store.update_status("dtask_1", TaskStatus.FAILED, failure_reason="timeout")
        self.assertEqual(task.failure_reason, "timeout")

    def test_update_status_not_found(self):
        self.assertIsNone(self.store.update_status("dtask_999", TaskStatus.RUNNING))

    def test_update_status_invalid_transition(self):
        self.store.create_task(goal="test", steps=[])
        with self.assertRaises(ValueError) as ctx:
            self.store.update_status("dtask_1", TaskStatus.COMPLETED)
        self.assertIn("pending", str(ctx.exception))

    def test_update_status_invalid_status(self):
        self.store.create_task(goal="test", steps=[])
        with self.assertRaises(ValueError) as ctx:
            self.store.update_status("dtask_1", "bogus")
        self.assertIn("Invalid status", str(ctx.exception))

    def test_add_checkpoint(self):
        self.store.create_task(goal="test", steps=[{"text": "s1"}])
        cp = self.store.add_checkpoint("dtask_1", {"step_id": 1, "run_id": "run_1", "state_snapshot": {"x": 1}})
        self.assertEqual(cp.checkpoint_id, "cp_1")
        self.assertEqual(cp.step_id, 1)

        task = self.store.get_task("dtask_1")
        self.assertEqual(len(task.checkpoints), 1)
        self.assertEqual(task.checkpoints[0].checkpoint_id, "cp_1")

    def test_add_checkpoint_increments_id(self):
        self.store.create_task(goal="test", steps=[{"text": "s1"}, {"text": "s2"}])
        self.store.add_checkpoint("dtask_1", {"step_id": 1, "run_id": "run_1", "state_snapshot": {}})
        cp2 = self.store.add_checkpoint("dtask_1", {"step_id": 2, "run_id": "run_1", "state_snapshot": {}})
        self.assertEqual(cp2.checkpoint_id, "cp_2")

    def test_add_checkpoint_not_found(self):
        self.assertIsNone(self.store.add_checkpoint("dtask_999", {"step_id": 1}))

    def test_create_with_parent(self):
        parent = self.store.create_task(goal="parent", steps=[])
        child = self.store.create_task(goal="child", steps=[], parent_task_id=parent.task_id)
        self.assertEqual(child.parent_task_id, parent.task_id)

    def test_create_with_optional_fields(self):
        task = self.store.create_task(
            goal="test", steps=[], worker_id="claude_a",
            input_summary="hello world", run_id="run_2",
        )
        self.assertEqual(task.worker_id, "claude_a")
        self.assertEqual(task.input_summary, "hello world")
        self.assertEqual(task.run_id, "run_2")

    def test_persistence_across_instances(self):
        self.store.create_task(goal="persistent", steps=[])
        self.db.conn.close()

        db2 = NoraDB(Path(self.tmpdir) / "test.db")
        store2 = DurableTaskStore(db=db2)
        task = store2.get_task("dtask_1")
        self.assertIsNotNone(task)
        self.assertEqual(task.goal, "persistent")
        db2.conn.close()


class JSONLStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = Path(self.tmpdir) / "tasks.jsonl"
        self.store = DurableTaskStore(path=self.path)

    def test_create_task(self):
        task = self.store.create_task(goal="test", steps=[{"text": "s1"}])
        self.assertEqual(task.task_id, "dtask_1")
        self.assertEqual(task.status, TaskStatus.PENDING)

    def test_get_task(self):
        self.store.create_task(goal="test", steps=[])
        task = self.store.get_task("dtask_1")
        self.assertIsNotNone(task)
        self.assertEqual(task.goal, "test")

    def test_get_task_not_found(self):
        self.assertIsNone(self.store.get_task("dtask_999"))

    def test_list_tasks(self):
        self.store.create_task(goal="first", steps=[])
        self.store.create_task(goal="second", steps=[])
        tasks = self.store.list_tasks()
        self.assertEqual(len(tasks), 2)

    def test_update_status(self):
        self.store.create_task(goal="test", steps=[])
        task = self.store.update_status("dtask_1", TaskStatus.RUNNING)
        self.assertEqual(task.status, TaskStatus.RUNNING)

        # Verify persistence
        task = self.store.get_task("dtask_1")
        self.assertEqual(task.status, TaskStatus.RUNNING)

    def test_update_status_invalid_transition(self):
        self.store.create_task(goal="test", steps=[])
        with self.assertRaises(ValueError):
            self.store.update_status("dtask_1", TaskStatus.COMPLETED)

    def test_add_checkpoint(self):
        self.store.create_task(goal="test", steps=[{"text": "s1"}])
        cp = self.store.add_checkpoint("dtask_1", {"step_id": 1, "run_id": "run_1", "state_snapshot": {"a": 1}})
        self.assertEqual(cp.checkpoint_id, "cp_1")

        task = self.store.get_task("dtask_1")
        self.assertEqual(len(task.checkpoints), 1)

    def test_persistence_across_instances(self):
        self.store.create_task(goal="persistent", steps=[])
        store2 = DurableTaskStore(path=self.path)
        task = store2.get_task("dtask_1")
        self.assertIsNotNone(task)
        self.assertEqual(task.goal, "persistent")

    def test_terminal_status_sets_finished_at(self):
        self.store.create_task(goal="test", steps=[])
        self.store.update_status("dtask_1", TaskStatus.RUNNING)
        task = self.store.update_status("dtask_1", TaskStatus.CANCELLED, failure_reason="user cancelled")
        self.assertIsNotNone(task.finished_at)
        self.assertEqual(task.failure_reason, "user cancelled")

    def test_id_increments_after_restart(self):
        self.store.create_task(goal="first", steps=[])
        store2 = DurableTaskStore(path=self.path)
        t2 = store2.create_task(goal="second", steps=[])
        self.assertEqual(t2.task_id, "dtask_2")


class TaskManagerMappingTests(unittest.TestCase):
    """Tests for task_manager_task_to_durable()."""

    def test_active_to_running(self):
        task = {
            "goal": "build feature",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
            "finished_at": None,
            "summary": "",
            "steps": [
                {"id": 1, "text": "plan", "status": "done", "note": "", "summary": "planned"},
                {"id": 2, "text": "build", "status": "in_progress", "note": "", "summary": ""},
            ],
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task)
        self.assertEqual(dt.status, TaskStatus.RUNNING)
        self.assertEqual(dt.goal, "build feature")
        self.assertEqual(dt.created_at, "2026-01-01T00:00:00Z")
        self.assertIsNone(dt.finished_at)

    def test_finished_to_completed(self):
        task = {
            "goal": "done task",
            "status": "finished",
            "created_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-02T00:00:00Z",
            "summary": "all good",
            "steps": [{"id": 1, "text": "do", "status": "done", "note": "", "summary": "did"}],
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task)
        self.assertEqual(dt.status, TaskStatus.COMPLETED)
        self.assertEqual(dt.finished_at, "2026-01-02T00:00:00Z")

    def test_active_all_pending_to_pending(self):
        task = {
            "goal": "new task",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
            "finished_at": None,
            "summary": "",
            "steps": [
                {"id": 1, "text": "step 1", "status": "pending", "note": "", "summary": ""},
                {"id": 2, "text": "step 2", "status": "pending", "note": "", "summary": ""},
            ],
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task)
        self.assertEqual(dt.status, TaskStatus.PENDING)

    def test_active_all_blocked_to_blocked(self):
        task = {
            "goal": "blocked task",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
            "finished_at": None,
            "summary": "",
            "steps": [
                {"id": 1, "text": "step 1", "status": "blocked", "note": "waiting", "summary": ""},
            ],
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task)
        self.assertEqual(dt.status, TaskStatus.BLOCKED)

    def test_step_field_mapping(self):
        task = {
            "goal": "test",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
            "finished_at": None,
            "summary": "",
            "steps": [
                {"id": 1, "text": "my step", "status": "in_progress", "note": "working", "summary": "partial"},
            ],
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task)
        step = dt.steps[0]
        self.assertEqual(step.id, 1)
        self.assertEqual(step.text, "my step")
        self.assertEqual(step.status, "in_progress")
        self.assertEqual(step.note, "working")
        self.assertEqual(step.summary, "partial")
        self.assertEqual(step.tool_hint, "")
        self.assertIsNone(step.checkpoint_ref)

    def test_missing_created_at_generates_now(self):
        task = {
            "goal": "no date",
            "status": "active",
            "finished_at": None,
            "summary": "",
            "steps": [],
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task)
        self.assertTrue(dt.created_at)  # auto-generated ISO timestamp

    def test_summary_preserved_as_input_summary(self):
        task = {
            "goal": "test",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
            "finished_at": None,
            "summary": "completed the feature and wrote tests",
            "steps": [],
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task)
        self.assertEqual(dt.input_summary, "completed the feature and wrote tests")

    def test_restored_from_creates_checkpoint(self):
        task = {
            "goal": "restored",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
            "finished_at": None,
            "summary": "",
            "steps": [],
            "restored_from": "task_5",
            "restored_at": "2026-01-03T12:00:00Z",
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task)
        self.assertEqual(len(dt.checkpoints), 1)
        cp = dt.checkpoints[0]
        self.assertEqual(cp.checkpoint_id, "cp_1")
        self.assertEqual(cp.step_id, 0)
        self.assertIn("task_5", cp.description)
        self.assertIn("2026-01-03T12:00:00Z", cp.description)
        self.assertEqual(cp.state_snapshot["restored_from"], "task_5")

    def test_no_restored_from_no_checkpoint(self):
        task = {
            "goal": "normal",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
            "finished_at": None,
            "summary": "",
            "steps": [],
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task)
        self.assertEqual(len(dt.checkpoints), 0)

    def test_custom_task_id_and_run_id(self):
        task = {
            "goal": "test",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
            "finished_at": None,
            "summary": "",
            "steps": [],
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task, task_id="dtask_42", run_id="run_3")
        self.assertEqual(dt.task_id, "dtask_42")
        self.assertEqual(dt.run_id, "run_3")

    def test_default_resume_policy(self):
        task = {
            "goal": "test",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
            "finished_at": None,
            "summary": "",
            "steps": [],
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task)
        self.assertEqual(dt.resume_policy, "from_step")

    def test_finished_at_preserved(self):
        task = {
            "goal": "done",
            "status": "finished",
            "created_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T05:00:00Z",
            "summary": "",
            "steps": [],
        }
        from mini_agent.durable_tasks import task_manager_task_to_durable
        dt = task_manager_task_to_durable(task)
        self.assertEqual(dt.finished_at, "2026-01-01T05:00:00Z")
        self.assertEqual(dt.status, TaskStatus.COMPLETED)


class RegistryToolTests(unittest.TestCase):
    """Tests for list_durable_tasks and get_durable_task registry tools."""

    def _make_registry(self, db):
        from mini_agent.tools import build_default_registry
        return build_default_registry(db=db)

    def test_registry_has_two_durable_tools(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                tools = {t["function"]["name"] for t in registry.to_openai_tools()}
                self.assertIn("list_durable_tasks", tools)
                self.assertIn("get_durable_task", tools)
            finally:
                db.close()

    def test_list_durable_tasks_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                result = registry.call("list_durable_tasks")
                self.assertIsInstance(result, str)
                parsed = json.loads(result)
                self.assertEqual(parsed, [])
            finally:
                db.close()

    def test_list_durable_tasks_with_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                store = registry.durable_task_store
                store.create_task(goal="build feature", steps=[{"text": "plan"}, {"text": "implement"}])
                store.add_checkpoint("dtask_1", {"step_id": 1, "run_id": "run_1", "state_snapshot": {}})

                result = registry.call("list_durable_tasks")
                parsed = json.loads(result)
                self.assertEqual(len(parsed), 1)
                self.assertEqual(parsed[0]["task_id"], "dtask_1")
                self.assertEqual(parsed[0]["status"], "pending")
                self.assertEqual(parsed[0]["goal"], "build feature")
                self.assertIsNone(parsed[0]["current_step"])
                self.assertEqual(parsed[0]["checkpoint_count"], 1)
            finally:
                db.close()

    def test_get_durable_task_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                store = registry.durable_task_store
                store.create_task(goal="test goal", steps=[{"text": "step 1"}])

                result = registry.call("get_durable_task", task_id="dtask_1")
                parsed = json.loads(result)
                self.assertEqual(parsed["task_id"], "dtask_1")
                self.assertEqual(parsed["goal"], "test goal")
                self.assertEqual(len(parsed["steps"]), 1)
                self.assertIn("checkpoints", parsed)
                self.assertIn("trace_refs", parsed)
            finally:
                db.close()

    def test_get_durable_task_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                result = registry.call("get_durable_task", task_id="dtask_999")
                parsed = json.loads(result)
                self.assertIn("error", parsed)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
