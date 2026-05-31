"""Tests for durable worker registry (TASK-030)."""

import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.database import NoraDB
from mini_agent.durable_workers import DurableWorkerStore, DurableWorker, WorkerStatus
from mini_agent.tools import build_default_registry


class DurableWorkerStoreSqliteTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.store = DurableWorkerStore(db=self.db)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_register_and_get_worker(self):
        worker = self.store.register_worker(worker_id="w1", role="worker", workspace_path="/tmp/w1")

        self.assertEqual(worker.worker_id, "w1")
        self.assertEqual(worker.role, "worker")
        self.assertEqual(worker.status, WorkerStatus.IDLE)
        self.assertIsNone(worker.current_task_id)
        self.assertEqual(worker.workspace_path, "/tmp/w1")
        self.assertTrue(worker.created_at)

        got = self.store.get_worker("w1")
        self.assertEqual(got.worker_id, "w1")
        self.assertEqual(got.role, "worker")

    def test_register_upsert_updates_existing(self):
        self.store.register_worker(worker_id="w1", role="worker")
        self.store.register_worker(worker_id="w1", role="reviewer", workspace_path="/tmp/review")

        got = self.store.get_worker("w1")
        self.assertEqual(got.role, "reviewer")
        self.assertEqual(got.workspace_path, "/tmp/review")

    def test_list_workers(self):
        self.store.register_worker(worker_id="w1", role="worker")
        self.store.register_worker(worker_id="w2", role="reviewer")

        workers = self.store.list_workers()
        self.assertEqual(len(workers), 2)
        ids = {w.worker_id for w in workers}
        self.assertEqual(ids, {"w1", "w2"})

    def test_update_status(self):
        self.store.register_worker(worker_id="w1")
        worker = self.store.update_status("w1", WorkerStatus.RUNNING, current_task_id="dtask_1")

        self.assertEqual(worker.status, WorkerStatus.RUNNING)
        self.assertEqual(worker.current_task_id, "dtask_1")

        got = self.store.get_worker("w1")
        self.assertEqual(got.status, WorkerStatus.RUNNING)
        self.assertEqual(got.current_task_id, "dtask_1")

    def test_update_status_clears_task(self):
        self.store.register_worker(worker_id="w1")
        self.store.update_status("w1", WorkerStatus.RUNNING, current_task_id="dtask_1")
        worker = self.store.update_status("w1", WorkerStatus.IDLE, current_task_id=None)

        self.assertEqual(worker.status, WorkerStatus.IDLE)
        self.assertIsNone(worker.current_task_id)

    def test_update_status_unknown_returns_none(self):
        result = self.store.update_status("w999", WorkerStatus.RUNNING)
        self.assertIsNone(result)

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.store.get_worker("w999"))

    def test_touch_updates_last_seen(self):
        self.store.register_worker(worker_id="w1")
        before = self.store.get_worker("w1").last_seen_at
        worker = self.store.touch("w1")

        self.assertGreaterEqual(worker.last_seen_at, before)

    def test_dataclass_round_trip(self):
        worker = DurableWorker(
            worker_id="w1", role="worker", status=WorkerStatus.RUNNING,
            current_task_id="dtask_1", workspace_path="/tmp/w1",
            created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
            last_seen_at="2026-01-01T00:00:00Z",
        )
        restored = DurableWorker.from_dict(worker.to_dict())

        self.assertEqual(restored.worker_id, "w1")
        self.assertEqual(restored.status, WorkerStatus.RUNNING)
        self.assertEqual(restored.current_task_id, "dtask_1")


class DurableWorkerStoreJsonlTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.store = DurableWorkerStore(path=self.root / "workers.jsonl")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_register_and_get(self):
        self.store.register_worker(worker_id="w1", role="worker")
        got = self.store.get_worker("w1")

        self.assertEqual(got.worker_id, "w1")
        self.assertEqual(got.role, "worker")

    def test_list_workers(self):
        self.store.register_worker(worker_id="w1")
        self.store.register_worker(worker_id="w2")

        workers = self.store.list_workers()
        self.assertEqual(len(workers), 2)

    def test_update_status(self):
        self.store.register_worker(worker_id="w1")
        worker = self.store.update_status("w1", WorkerStatus.RUNNING, current_task_id="dtask_1")

        self.assertEqual(worker.status, WorkerStatus.RUNNING)
        self.assertEqual(worker.current_task_id, "dtask_1")

    def test_upsert_updates_existing(self):
        self.store.register_worker(worker_id="w1", role="old")
        self.store.register_worker(worker_id="w1", role="new")

        got = self.store.get_worker("w1")
        self.assertEqual(got.role, "new")


class RegistryWorkerToolTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.registry = build_default_registry(
            db=self.db, workspace_root=self.root, confirm_action=lambda _: True,
        )

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_register_worker_returns_json(self):
        result = self.registry.call("register_worker", worker_id="w1", role="worker", workspace_path="/tmp/w1")
        parsed = json.loads(result)

        self.assertEqual(parsed["worker_id"], "w1")
        self.assertEqual(parsed["role"], "worker")
        self.assertEqual(parsed["workspace_path"], "/tmp/w1")
        self.assertEqual(parsed["status"], "idle")

    def test_list_workers_returns_json(self):
        self.registry.call("register_worker", worker_id="w1")
        self.registry.call("register_worker", worker_id="w2")

        result = self.registry.call("list_workers")
        parsed = json.loads(result)

        self.assertEqual(len(parsed), 2)
        ids = {w["worker_id"] for w in parsed}
        self.assertEqual(ids, {"w1", "w2"})

    def test_get_worker_returns_json(self):
        self.registry.call("register_worker", worker_id="w1", role="reviewer")

        result = self.registry.call("get_worker", worker_id="w1")
        parsed = json.loads(result)

        self.assertEqual(parsed["worker_id"], "w1")
        self.assertEqual(parsed["role"], "reviewer")

    def test_get_unknown_worker_returns_error(self):
        result = self.registry.call("get_worker", worker_id="w999")
        parsed = json.loads(result)

        self.assertIn("error", parsed)

    def test_update_worker_status_returns_json(self):
        self.registry.call("register_worker", worker_id="w1")
        result = self.registry.call("update_worker_status", worker_id="w1", status="running", current_task_id="dtask_1")
        parsed = json.loads(result)

        self.assertEqual(parsed["status"], "running")
        self.assertEqual(parsed["current_task_id"], "dtask_1")

    def test_update_worker_status_invalid_status_returns_error(self):
        self.registry.call("register_worker", worker_id="w1")
        result = self.registry.call("update_worker_status", worker_id="w1", status="invalid_status")
        parsed = json.loads(result)

        self.assertIn("error", parsed)

    def test_empty_worker_id_returns_error(self):
        result = self.registry.call("register_worker", worker_id="")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_whitespace_worker_id_returns_error(self):
        result = self.registry.call("register_worker", worker_id="   ")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_get_empty_worker_id_returns_error(self):
        result = self.registry.call("get_worker", worker_id="")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_update_empty_worker_id_returns_error(self):
        result = self.registry.call("update_worker_status", worker_id="", status="running")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_update_worker_does_not_mutate_durable_task(self):
        self.registry.call("register_worker", worker_id="w1")
        create_result = self.registry.call("create_durable_task", goal="my task", steps="step one")
        task_id = json.loads(create_result)["task_id"]

        self.registry.call("update_worker_status", worker_id="w1", status="running", current_task_id=task_id)

        task_result = self.registry.call("get_durable_task", task_id=task_id)
        task = json.loads(task_result)
        self.assertEqual(task["status"], "pending")

    def test_durable_task_assignment_still_works(self):
        create_result = self.registry.call("create_durable_task", goal="my task", steps="step one", worker_id="w1")
        task = json.loads(create_result)
        self.assertEqual(task["worker_id"], "w1")

        assign_result = self.registry.call("assign_durable_task", task_id=task["task_id"], worker_id="w2")
        assigned = json.loads(assign_result)
        self.assertEqual(assigned["worker_id"], "w2")


if __name__ == "__main__":
    unittest.main()
