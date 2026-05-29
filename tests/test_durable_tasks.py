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


class DeleteTaskTests(unittest.TestCase):
    """Tests for DurableTaskStore.delete_task()."""

    def test_delete_existing_sqlite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task(goal="to delete", steps=[{"text": "s1"}])
                self.assertIsNotNone(store.get_task("dtask_1"))
                result = store.delete_task("dtask_1")
                self.assertTrue(result)
                self.assertIsNone(store.get_task("dtask_1"))
                self.assertEqual(store.list_tasks(), [])
            finally:
                db.close()

    def test_delete_nonexistent_sqlite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                result = store.delete_task("dtask_999")
                self.assertFalse(result)
            finally:
                db.close()

    def test_delete_existing_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "tasks.jsonl"
            store = DurableTaskStore(path=path)
            store.create_task(goal="to delete", steps=[])
            self.assertTrue(store.delete_task("dtask_1"))
            self.assertIsNone(store.get_task("dtask_1"))

    def test_delete_nonexistent_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "tasks.jsonl"
            store = DurableTaskStore(path=path)
            self.assertFalse(store.delete_task("dtask_999"))

    def test_delete_does_not_affect_other_tasks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task(goal="keep", steps=[])
                store.create_task(goal="delete me", steps=[])
                store.delete_task("dtask_2")
                remaining = store.list_tasks()
                self.assertEqual(len(remaining), 1)
                self.assertEqual(remaining[0].goal, "keep")
            finally:
                db.close()


class CRUDRegistryToolTests(unittest.TestCase):
    """Tests for create_durable_task, update_durable_task, delete_durable_task registry tools."""

    def _make_registry(self, db):
        from mini_agent.tools import build_default_registry
        return build_default_registry(db=db, confirm_action=lambda _: True)

    def test_registry_has_crud_tools(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                tools = {t["function"]["name"] for t in registry.to_openai_tools()}
                self.assertIn("create_durable_task", tools)
                self.assertIn("update_durable_task", tools)
                self.assertIn("delete_durable_task", tools)
            finally:
                db.close()

    def test_create_durable_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                result = registry.call("create_durable_task", goal="build feature", steps="plan\nimplement\ntest")
                parsed = json.loads(result)
                self.assertEqual(parsed["task_id"], "dtask_1")
                self.assertEqual(parsed["goal"], "build feature")
                self.assertEqual(parsed["status"], "pending")
                self.assertEqual(len(parsed["steps"]), 3)
                self.assertEqual(parsed["steps"][0]["text"], "plan")
            finally:
                db.close()

    def test_create_durable_task_empty_steps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                result = registry.call("create_durable_task", goal="simple", steps="")
                parsed = json.loads(result)
                self.assertEqual(parsed["task_id"], "dtask_1")
                self.assertEqual(len(parsed["steps"]), 0)
            finally:
                db.close()

    def test_update_durable_task_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                registry.call("create_durable_task", goal="test", steps="step1")
                result = registry.call("update_durable_task", task_id="dtask_1", status="running")
                parsed = json.loads(result)
                self.assertEqual(parsed["status"], "running")
            finally:
                db.close()

    def test_update_durable_task_to_completed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                registry.call("create_durable_task", goal="test", steps="step1")
                registry.call("update_durable_task", task_id="dtask_1", status="running")
                result = registry.call("update_durable_task", task_id="dtask_1", status="completed")
                parsed = json.loads(result)
                self.assertEqual(parsed["status"], "completed")
                self.assertIsNotNone(parsed["finished_at"])
            finally:
                db.close()

    def test_update_durable_task_with_failure_reason(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                registry.call("create_durable_task", goal="test", steps="step1")
                registry.call("update_durable_task", task_id="dtask_1", status="running")
                result = registry.call("update_durable_task", task_id="dtask_1", status="failed", failure_reason="timeout")
                parsed = json.loads(result)
                self.assertEqual(parsed["status"], "failed")
                self.assertEqual(parsed["failure_reason"], "timeout")
            finally:
                db.close()

    def test_update_durable_task_invalid_transition(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                registry.call("create_durable_task", goal="test", steps="step1")
                result = registry.call("update_durable_task", task_id="dtask_1", status="completed")
                parsed = json.loads(result)
                self.assertIn("error", parsed)
                self.assertIn("pending", parsed["error"])
            finally:
                db.close()

    def test_update_durable_task_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                result = registry.call("update_durable_task", task_id="dtask_999", status="running")
                parsed = json.loads(result)
                self.assertIn("error", parsed)
            finally:
                db.close()

    def test_update_durable_task_missing_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                result = registry.call("update_durable_task", task_id="dtask_1")
                parsed = json.loads(result)
                self.assertIn("error", parsed)
            finally:
                db.close()

    def test_delete_durable_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                registry.call("create_durable_task", goal="to delete", steps="step1")
                result = registry.call("delete_durable_task", task_id="dtask_1")
                parsed = json.loads(result)
                self.assertTrue(parsed["deleted"])
                self.assertEqual(parsed["task_id"], "dtask_1")
                # Verify actually gone
                result2 = registry.call("get_durable_task", task_id="dtask_1")
                parsed2 = json.loads(result2)
                self.assertIn("error", parsed2)
            finally:
                db.close()

    def test_delete_durable_task_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                result = registry.call("delete_durable_task", task_id="dtask_999")
                parsed = json.loads(result)
                self.assertIn("error", parsed)
            finally:
                db.close()

    def test_full_crud_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                # Create
                result = registry.call("create_durable_task", goal="lifecycle test", steps="s1\ns2")
                task = json.loads(result)
                task_id = task["task_id"]
                self.assertEqual(task["status"], "pending")
                # Read
                result = registry.call("get_durable_task", task_id=task_id)
                self.assertEqual(json.loads(result)["goal"], "lifecycle test")
                # Update
                result = registry.call("update_durable_task", task_id=task_id, status="running")
                self.assertEqual(json.loads(result)["status"], "running")
                result = registry.call("update_durable_task", task_id=task_id, status="completed")
                self.assertEqual(json.loads(result)["status"], "completed")
                # Delete
                result = registry.call("delete_durable_task", task_id=task_id)
                self.assertTrue(json.loads(result)["deleted"])
                # Confirm gone
                result = registry.call("get_durable_task", task_id=task_id)
                self.assertIn("error", json.loads(result))
            finally:
                db.close()


class TaskManagerDurableStoreWiringTests(unittest.TestCase):
    """Tests that TaskManager receives durable_store."""

    def test_task_manager_has_durable_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                from mini_agent.tools import build_default_registry
                registry = build_default_registry(db=db)
                tm = registry.task_manager
                self.assertIsNotNone(tm.durable_store)
                self.assertIsInstance(tm.durable_store, DurableTaskStore)
            finally:
                db.close()

    def test_task_manager_durable_store_is_same_as_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                from mini_agent.tools import build_default_registry
                registry = build_default_registry(db=db)
                self.assertIs(registry.task_manager.durable_store, registry.durable_task_store)
            finally:
                db.close()

    def test_task_manager_without_durable_store(self):
        from mini_agent.task_runner import TaskManager
        tm = TaskManager()
        self.assertIsNone(tm.durable_store)


class RetryFieldTests(unittest.TestCase):
    """Tests for retry_count and max_retries fields on DurableTask."""

    def test_default_retry_fields(self):
        task = DurableTask(
            task_id="dtask_1", run_id="run_1", status="pending",
            goal="test", steps=[], created_at="2026-01-01", updated_at="2026-01-01",
        )
        self.assertEqual(task.retry_count, 0)
        self.assertEqual(task.max_retries, 3)

    def test_custom_max_retries_on_create(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                task = store.create_task(goal="test", steps=[{"text": "s1"}], max_retries=5)
                self.assertEqual(task.max_retries, 5)
                self.assertEqual(task.retry_count, 0)
            finally:
                db.close()

    def test_retry_fields_in_to_dict(self):
        task = DurableTask(
            task_id="dtask_1", run_id="run_1", status="pending",
            goal="test", steps=[], created_at="2026-01-01", updated_at="2026-01-01",
            retry_count=2, max_retries=5,
        )
        d = task.to_dict()
        self.assertEqual(d["retry_count"], 2)
        self.assertEqual(d["max_retries"], 5)

    def test_retry_fields_from_dict(self):
        data = {
            "task_id": "dtask_1", "run_id": "run_1", "status": "pending",
            "goal": "test", "steps": [], "created_at": "2026-01-01", "updated_at": "2026-01-01",
            "retry_count": 1, "max_retries": 5,
        }
        task = DurableTask.from_dict(data)
        self.assertEqual(task.retry_count, 1)
        self.assertEqual(task.max_retries, 5)

    def test_retry_fields_backward_compat_from_dict(self):
        """from_dict with no retry fields should use defaults."""
        data = {
            "task_id": "dtask_1", "run_id": "run_1", "status": "pending",
            "goal": "test", "steps": [], "created_at": "2026-01-01", "updated_at": "2026-01-01",
        }
        task = DurableTask.from_dict(data)
        self.assertEqual(task.retry_count, 0)
        self.assertEqual(task.max_retries, 3)

    def test_retry_fields_persist_sqlite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task(goal="test", steps=[], max_retries=7)
                task = store.get_task("dtask_1")
                self.assertEqual(task.retry_count, 0)
                self.assertEqual(task.max_retries, 7)
            finally:
                db.close()


class RetryDurableTaskTests(unittest.TestCase):
    """Tests for DurableTaskStore.retry_durable_task()."""

    def _make_failed_task(self, store, max_retries=3):
        store.create_task(goal="test", steps=[{"text": "s1"}, {"text": "s2"}], max_retries=max_retries)
        store.update_status("dtask_1", TaskStatus.RUNNING)
        store.update_status("dtask_1", TaskStatus.FAILED, failure_reason="timeout")

    def test_retry_resets_to_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                self._make_failed_task(store)
                task = store.retry_durable_task("dtask_1")
                self.assertEqual(task.status, TaskStatus.PENDING)
                self.assertEqual(task.retry_count, 1)
                self.assertEqual(task.failure_reason, "")
                self.assertIsNone(task.finished_at)
            finally:
                db.close()

    def test_retry_resets_steps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task(goal="test", steps=[{"text": "s1", "status": "done"}])
                store.update_status("dtask_1", TaskStatus.RUNNING)
                store.update_status("dtask_1", TaskStatus.FAILED)
                task = store.retry_durable_task("dtask_1")
                for step in task.steps:
                    self.assertEqual(step.status, StepStatus.PENDING)
                    self.assertEqual(step.note, "")
            finally:
                db.close()

    def test_retry_increments_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                self._make_failed_task(store, max_retries=3)
                store.retry_durable_task("dtask_1")
                store.update_status("dtask_1", TaskStatus.RUNNING)
                store.update_status("dtask_1", TaskStatus.FAILED, failure_reason="err2")
                task = store.retry_durable_task("dtask_1")
                self.assertEqual(task.retry_count, 2)
            finally:
                db.close()

    def test_retry_max_retries_exceeded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                self._make_failed_task(store, max_retries=1)
                store.retry_durable_task("dtask_1")
                store.update_status("dtask_1", TaskStatus.RUNNING)
                store.update_status("dtask_1", TaskStatus.FAILED)
                with self.assertRaises(ValueError) as ctx:
                    store.retry_durable_task("dtask_1")
                self.assertIn("Max retries", str(ctx.exception))
            finally:
                db.close()

    def test_retry_non_failed_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task(goal="test", steps=[])
                with self.assertRaises(ValueError) as ctx:
                    store.retry_durable_task("dtask_1")
                self.assertIn("pending", str(ctx.exception))
            finally:
                db.close()

    def test_retry_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                result = store.retry_durable_task("dtask_999")
                self.assertIsNone(result)
            finally:
                db.close()

    def test_retry_persists_sqlite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                self._make_failed_task(store)
                store.retry_durable_task("dtask_1")
                task = store.get_task("dtask_1")
                self.assertEqual(task.status, TaskStatus.PENDING)
                self.assertEqual(task.retry_count, 1)
            finally:
                db.close()

    def test_retry_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "tasks.jsonl"
            store = DurableTaskStore(path=path)
            self._make_failed_task(store)
            task = store.retry_durable_task("dtask_1")
            self.assertEqual(task.status, TaskStatus.PENDING)
            self.assertEqual(task.retry_count, 1)
            # Verify persistence
            task2 = store.get_task("dtask_1")
            self.assertEqual(task2.status, TaskStatus.PENDING)

    def test_retry_zero_max_retries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task(goal="test", steps=[], max_retries=0)
                store.update_status("dtask_1", TaskStatus.RUNNING)
                store.update_status("dtask_1", TaskStatus.FAILED)
                with self.assertRaises(ValueError):
                    store.retry_durable_task("dtask_1")
            finally:
                db.close()

    def test_update_status_blocks_failed_to_pending(self):
        """update_status() must reject FAILED -> PENDING; only retry_durable_task() can do this."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                self._make_failed_task(store)
                with self.assertRaises(ValueError) as ctx:
                    store.update_status("dtask_1", TaskStatus.PENDING)
                self.assertIn("Invalid transition", str(ctx.exception))
                # Verify task is still FAILED
                task = store.get_task("dtask_1")
                self.assertEqual(task.status, TaskStatus.FAILED)
            finally:
                db.close()


class RetryRegistryToolTests(unittest.TestCase):
    """Tests for retry_durable_task registry tool."""

    def _make_registry(self, db):
        from mini_agent.tools import build_default_registry
        return build_default_registry(db=db, confirm_action=lambda _: True)

    def test_retry_tool_registered(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                tools = {t["function"]["name"] for t in registry.to_openai_tools()}
                self.assertIn("retry_durable_task", tools)
            finally:
                db.close()

    def test_retry_tool_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                registry.call("create_durable_task", goal="test", steps="s1")
                registry.call("update_durable_task", task_id="dtask_1", status="running")
                registry.call("update_durable_task", task_id="dtask_1", status="failed", failure_reason="err")
                result = registry.call("retry_durable_task", task_id="dtask_1")
                parsed = json.loads(result)
                self.assertEqual(parsed["status"], "pending")
                self.assertEqual(parsed["retry_count"], 1)
            finally:
                db.close()

    def test_retry_tool_max_retries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                registry.call("create_durable_task", goal="test", steps="s1")
                registry.call("update_durable_task", task_id="dtask_1", status="running")
                registry.call("update_durable_task", task_id="dtask_1", status="failed")
                # Default max_retries=3, so retry 3 times
                for _ in range(3):
                    registry.call("retry_durable_task", task_id="dtask_1")
                    registry.call("update_durable_task", task_id="dtask_1", status="running")
                    registry.call("update_durable_task", task_id="dtask_1", status="failed")
                result = registry.call("retry_durable_task", task_id="dtask_1")
                parsed = json.loads(result)
                self.assertIn("error", parsed)
            finally:
                db.close()

    def test_retry_tool_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = self._make_registry(db)
                result = registry.call("retry_durable_task", task_id="dtask_999")
                parsed = json.loads(result)
                self.assertIn("error", parsed)
            finally:
                db.close()


class CurrentStepMappingTests(unittest.TestCase):
    """Tests for current_step in task_manager_task_to_durable()."""

    def test_current_step_none_when_no_in_progress(self):
        from mini_agent.durable_tasks import task_manager_task_to_durable
        task = {
            "goal": "test", "status": "active",
            "created_at": "2026-01-01T00:00:00Z", "finished_at": None, "summary": "",
            "steps": [
                {"id": 1, "text": "s1", "status": "pending", "note": "", "summary": ""},
                {"id": 2, "text": "s2", "status": "done", "note": "", "summary": ""},
            ],
        }
        dt = task_manager_task_to_durable(task)
        self.assertIsNone(dt.current_step)

    def test_current_step_set_to_in_progress_step(self):
        from mini_agent.durable_tasks import task_manager_task_to_durable
        task = {
            "goal": "test", "status": "active",
            "created_at": "2026-01-01T00:00:00Z", "finished_at": None, "summary": "",
            "steps": [
                {"id": 1, "text": "s1", "status": "done", "note": "", "summary": ""},
                {"id": 2, "text": "s2", "status": "in_progress", "note": "", "summary": ""},
                {"id": 3, "text": "s3", "status": "pending", "note": "", "summary": ""},
            ],
        }
        dt = task_manager_task_to_durable(task)
        self.assertEqual(dt.current_step, 2)

    def test_current_step_first_in_progress(self):
        from mini_agent.durable_tasks import task_manager_task_to_durable
        task = {
            "goal": "test", "status": "active",
            "created_at": "2026-01-01T00:00:00Z", "finished_at": None, "summary": "",
            "steps": [
                {"id": 1, "text": "s1", "status": "in_progress", "note": "", "summary": ""},
                {"id": 2, "text": "s2", "status": "in_progress", "note": "", "summary": ""},
            ],
        }
        dt = task_manager_task_to_durable(task)
        self.assertEqual(dt.current_step, 1)

    def test_current_step_finished_task(self):
        from mini_agent.durable_tasks import task_manager_task_to_durable
        task = {
            "goal": "test", "status": "finished",
            "created_at": "2026-01-01T00:00:00Z", "finished_at": "2026-01-02T00:00:00Z", "summary": "",
            "steps": [
                {"id": 1, "text": "s1", "status": "done", "note": "", "summary": ""},
            ],
        }
        dt = task_manager_task_to_durable(task)
        self.assertIsNone(dt.current_step)


class ShadowWriteRunOnceTests(unittest.TestCase):
    """Tests that run_once() syncs to durable store."""

    def test_run_once_syncs_to_durable(self):
        from mini_agent.task_runner import TaskManager
        from mini_agent.durable_tasks import DurableTaskStore, TaskStatus
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "durable.db")
            try:
                store = DurableTaskStore(db=db)
                manager = TaskManager(
                    Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                    durable_store=store, enable_durable_shadow=True,
                )
                manager.start("build feature", "plan\nimplement\ntest")
                manager.run_once()  # marks step 1 as in_progress

                tasks = store.list_tasks()
                self.assertEqual(len(tasks), 1)
                dt = tasks[0]
                self.assertEqual(dt.status, "running")
                self.assertEqual(dt.current_step, 1)
                self.assertEqual(dt.steps[0].status, "in_progress")
                self.assertEqual(dt.steps[1].status, "pending")
            finally:
                db.close()

    def test_run_once_existing_in_progress_syncs(self):
        from mini_agent.task_runner import TaskManager
        from mini_agent.durable_tasks import DurableTaskStore
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "durable.db")
            try:
                store = DurableTaskStore(db=db)
                manager = TaskManager(
                    Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                    durable_store=store, enable_durable_shadow=True,
                )
                manager.start("build feature", "plan\nimplement")
                manager.run_once()  # step 1 in_progress
                manager.update_step(1, "done", summary="planned")
                manager.run_once()  # step 2 in_progress

                tasks = store.list_tasks()
                dt = tasks[0]
                self.assertEqual(dt.current_step, 2)
                self.assertEqual(dt.steps[0].status, "done")
                self.assertEqual(dt.steps[1].status, "in_progress")
            finally:
                db.close()


class CheckpointLifecycleTests(unittest.TestCase):
    """Tests that checkpoints are created during task lifecycle."""

    def test_run_once_creates_checkpoint_with_ref(self):
        from mini_agent.task_runner import TaskManager
        from mini_agent.durable_tasks import DurableTaskStore
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "durable.db")
            try:
                store = DurableTaskStore(db=db)
                manager = TaskManager(
                    Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                    durable_store=store, enable_durable_shadow=True,
                )
                manager.start("build feature", "plan\nimplement")
                manager.run_once()

                dt = store.get_task("dtask_shadow_1")
                self.assertIsNotNone(dt)
                self.assertEqual(len(dt.checkpoints), 1)
                cp = dt.checkpoints[0]
                self.assertEqual(cp.step_id, 1)
                self.assertIn("run_once", cp.description)
                self.assertIn("in_progress", cp.description)
                self.assertEqual(cp.state_snapshot["goal"], "build feature")
                self.assertEqual(cp.state_snapshot["current_step"], 1)

                self.assertEqual(dt.steps[0].checkpoint_ref, cp.checkpoint_id)
                self.assertIsNone(dt.steps[1].checkpoint_ref)
            finally:
                db.close()

    def test_update_step_done_creates_checkpoint_with_ref(self):
        from mini_agent.task_runner import TaskManager
        from mini_agent.durable_tasks import DurableTaskStore
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "durable.db")
            try:
                store = DurableTaskStore(db=db)
                manager = TaskManager(
                    Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                    durable_store=store, enable_durable_shadow=True,
                )
                manager.start("build feature", "plan\nimplement")
                manager.run_once()
                manager.update_step(1, "done", summary="planned")

                dt = store.get_task("dtask_shadow_1")
                self.assertEqual(len(dt.checkpoints), 2)
                done_cp = dt.checkpoints[1]
                self.assertEqual(done_cp.step_id, 1)
                self.assertIn("update_step", done_cp.description)
                self.assertIn("done", done_cp.description)
                self.assertEqual(done_cp.state_snapshot["summary"], "planned")

                self.assertEqual(dt.steps[0].checkpoint_ref, done_cp.checkpoint_id)
            finally:
                db.close()

    def test_blocked_step_checkpoint_includes_note(self):
        from mini_agent.task_runner import TaskManager
        from mini_agent.durable_tasks import DurableTaskStore
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "durable.db")
            try:
                store = DurableTaskStore(db=db)
                manager = TaskManager(
                    Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                    durable_store=store, enable_durable_shadow=True,
                )
                manager.start("build feature", "plan\nimplement")
                manager.run_once()
                manager.update_step(1, "blocked", note="waiting for API key", summary="need auth")

                dt = store.get_task("dtask_shadow_1")
                self.assertEqual(len(dt.checkpoints), 2)
                blocked_cp = dt.checkpoints[1]
                self.assertEqual(blocked_cp.step_id, 1)
                self.assertIn("blocked", blocked_cp.description)
                self.assertEqual(blocked_cp.state_snapshot["note"], "waiting for API key")
                self.assertEqual(blocked_cp.state_snapshot["summary"], "need auth")

                self.assertEqual(dt.steps[0].checkpoint_ref, blocked_cp.checkpoint_id)
            finally:
                db.close()

    def test_multiple_steps_checkpoint_refs(self):
        from mini_agent.task_runner import TaskManager
        from mini_agent.durable_tasks import DurableTaskStore
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "durable.db")
            try:
                store = DurableTaskStore(db=db)
                manager = TaskManager(
                    Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                    durable_store=store, enable_durable_shadow=True,
                )
                manager.start("build feature", "plan\nimplement\ntest")
                manager.run_once()  # step 1 in_progress -> cp_1
                manager.update_step(1, "done", summary="planned")  # step 1 done -> cp_2
                manager.run_once()  # step 2 in_progress -> cp_3

                dt = store.get_task("dtask_shadow_1")
                self.assertEqual(len(dt.checkpoints), 3)
                self.assertEqual(dt.steps[0].checkpoint_ref, "cp_2")
                self.assertEqual(dt.steps[1].checkpoint_ref, "cp_3")
                self.assertIsNone(dt.steps[2].checkpoint_ref)
            finally:
                db.close()

    def test_checkpoint_jsonl_backend(self):
        from mini_agent.task_runner import TaskManager
        from mini_agent.durable_tasks import DurableTaskStore
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "tasks.jsonl"
            store = DurableTaskStore(path=path)
            manager = TaskManager(
                Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                durable_store=store, enable_durable_shadow=True,
            )
            manager.start("build feature", "plan\nimplement")
            manager.run_once()
            manager.update_step(1, "done", summary="planned")

            dt = store.get_task("dtask_shadow_1")
            self.assertIsNotNone(dt)
            self.assertEqual(len(dt.checkpoints), 2)
            self.assertEqual(dt.steps[0].checkpoint_ref, "cp_2")
            self.assertIsNone(dt.steps[1].checkpoint_ref)

    def test_trace_refs_preserved_across_shadow_syncs(self):
        from mini_agent.task_runner import TaskManager
        from mini_agent.durable_tasks import DurableTaskStore
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "durable.db")
            try:
                store = DurableTaskStore(db=db)
                manager = TaskManager(
                    Path(tmpdir) / "task.json", Path(tmpdir) / "history.jsonl",
                    durable_store=store, enable_durable_shadow=True,
                )
                manager.start("build feature", "plan\nimplement")

                # Simulate external trace binding (e.g., by trace system)
                dt = store.get_task("dtask_shadow_1")
                dt.trace_refs = ["trace_1", "trace_2"]
                store.upsert_task(dt)

                # Shadow sync should preserve trace_refs
                manager.run_once()
                dt = store.get_task("dtask_shadow_1")
                self.assertEqual(dt.trace_refs, ["trace_1", "trace_2"])

                manager.update_step(1, "done", summary="planned")
                dt = store.get_task("dtask_shadow_1")
                self.assertEqual(dt.trace_refs, ["trace_1", "trace_2"])

                manager.run_once()
                dt = store.get_task("dtask_shadow_1")
                self.assertEqual(dt.trace_refs, ["trace_1", "trace_2"])
            finally:
                db.close()


class ShadowEnabledByDefaultTests(unittest.TestCase):
    """Tests that build_default_registry() enables shadow write."""

    def test_shadow_enabled_in_default_registry(self):
        from mini_agent.tools import build_default_registry
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = build_default_registry(db=db)
                tm = registry.task_manager
                self.assertTrue(tm.enable_durable_shadow)
            finally:
                db.close()

    def test_default_registry_syncs_on_start(self):
        from mini_agent.tools import build_default_registry
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = build_default_registry(db=db)
                tm = registry.task_manager
                store = registry.durable_task_store
                tm.start("test goal", "step a\nstep b")

                tasks = store.list_tasks()
                self.assertEqual(len(tasks), 1)
                self.assertEqual(tasks[0].goal, "test goal")
                self.assertEqual(tasks[0].status, "pending")
            finally:
                db.close()

    def test_default_registry_syncs_on_finish(self):
        from mini_agent.tools import build_default_registry
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = build_default_registry(db=db)
                tm = registry.task_manager
                store = registry.durable_task_store
                tm.start("test goal", "step a")
                tm.finish("done")

                tasks = store.list_tasks()
                dt = tasks[0]
                self.assertEqual(dt.status, "completed")
                self.assertEqual(dt.input_summary, "done")
            finally:
                db.close()


class AddTraceRefTests(unittest.TestCase):
    """Tests for DurableTaskStore.add_trace_ref()."""

    def test_add_trace_ref_to_running_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task("goal", [{"text": "s1"}, {"text": "s2"}])
                store.update_status("dtask_1", "running")
                result = store.add_trace_ref("trace_1")
                self.assertTrue(result)
                task = store.get_task("dtask_1")
                self.assertIn("trace_1", task.trace_refs)
            finally:
                db.close()

    def test_add_trace_ref_to_pending_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task("goal", [{"text": "s1"}])
                result = store.add_trace_ref("trace_5")
                self.assertTrue(result)
                task = store.get_task("dtask_1")
                self.assertEqual(task.trace_refs, ["trace_5"])
            finally:
                db.close()

    def test_add_trace_ref_dedup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task("goal", [{"text": "s1"}])
                store.update_status("dtask_1", "running")
                store.add_trace_ref("trace_1")
                store.add_trace_ref("trace_1")
                task = store.get_task("dtask_1")
                self.assertEqual(task.trace_refs.count("trace_1"), 1)
            finally:
                db.close()

    def test_add_trace_ref_skips_terminal_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task("goal", [{"text": "s1"}])
                store.update_status("dtask_1", "running")
                store.update_status("dtask_1", "completed")
                result = store.add_trace_ref("trace_1")
                self.assertFalse(result)
                task = store.get_task("dtask_1")
                self.assertEqual(task.trace_refs, [])
            finally:
                db.close()

    def test_add_trace_ref_no_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                result = store.add_trace_ref("trace_1")
                self.assertFalse(result)
            finally:
                db.close()

    def test_add_trace_ref_jsonl_backend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dtasks.jsonl"
            store = DurableTaskStore(path=path)
            store.create_task("goal", [{"text": "s1"}])
            store.update_status("dtask_1", "running")
            result = store.add_trace_ref("trace_7")
            self.assertTrue(result)
            task = store.get_task("dtask_1")
            self.assertIn("trace_7", task.trace_refs)

    def test_add_trace_ref_multiple_tasks_picks_first_active(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task("goal1", [{"text": "s1"}])
                store.update_status("dtask_1", "running")
                store.update_status("dtask_1", "completed")
                store.create_task("goal2", [{"text": "s2"}])
                store.update_status("dtask_2", "running")
                result = store.add_trace_ref("trace_1")
                self.assertTrue(result)
                task1 = store.get_task("dtask_1")
                task2 = store.get_task("dtask_2")
                self.assertNotIn("trace_1", task1.trace_refs)
                self.assertIn("trace_1", task2.trace_refs)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
