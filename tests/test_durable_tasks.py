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


if __name__ == "__main__":
    unittest.main()
