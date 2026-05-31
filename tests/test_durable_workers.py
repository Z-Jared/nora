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

    def test_touch_worker_returns_json(self):
        self.registry.call("register_worker", worker_id="w1", role="worker")
        result = self.registry.call("touch_worker", worker_id="w1")
        parsed = json.loads(result)
        self.assertEqual(parsed["worker_id"], "w1")
        self.assertIn("last_seen_at", parsed)

    def test_touch_worker_unknown_returns_error(self):
        result = self.registry.call("touch_worker", worker_id="w999")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_touch_worker_empty_id_returns_error(self):
        result = self.registry.call("touch_worker", worker_id="")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_mark_stale_workers_offline_returns_json(self):
        self.registry.call("register_worker", worker_id="w1")
        result = self.registry.call("mark_stale_workers_offline", max_age_seconds=1)
        parsed = json.loads(result)
        self.assertIn("changed_count", parsed)
        self.assertIn("workers", parsed)

    def test_mark_stale_workers_offline_invalid_threshold_returns_error(self):
        result = self.registry.call("mark_stale_workers_offline", max_age_seconds=0)
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_mark_offline_does_not_mutate_durable_task(self):
        self.registry.call("register_worker", worker_id="w1")
        create_result = self.registry.call("create_durable_task", goal="my task", steps="step one", worker_id="w1")
        task_id = json.loads(create_result)["task_id"]

        # Mark worker offline (won't actually change since it was just registered, but verify task untouched)
        self.registry.call("mark_stale_workers_offline", max_age_seconds=999999)

        task_result = self.registry.call("get_durable_task", task_id=task_id)
        task = json.loads(task_result)
        self.assertEqual(task["worker_id"], "w1")
        self.assertEqual(task["status"], "pending")


class DurableWorkerHeartbeatTests(unittest.TestCase):
    """Tests for heartbeat and stale→offline lifecycle."""

    def test_sqlite_touch_updates_last_seen_and_updated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableWorkerStore(db=db)
                store.register_worker(worker_id="w1")
                before = store.get_worker("w1")
                worker = store.touch("w1")

                self.assertGreaterEqual(worker.last_seen_at, before.last_seen_at)
                self.assertGreaterEqual(worker.updated_at, before.updated_at)

                after = store.get_worker("w1")
                self.assertEqual(after.last_seen_at, worker.last_seen_at)
            finally:
                db.close()

    def test_jsonl_touch_updates_last_seen_and_updated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = DurableWorkerStore(path=Path(tmpdir) / "workers.jsonl")
            store.register_worker(worker_id="w1")
            before = store.get_worker("w1")
            worker = store.touch("w1")

            self.assertGreaterEqual(worker.last_seen_at, before.last_seen_at)
            self.assertGreaterEqual(worker.updated_at, before.updated_at)

    def test_sqlite_stale_workers_become_offline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableWorkerStore(db=db)
                store.register_worker(worker_id="w1")
                # Manually set last_seen_at to old timestamp
                worker = store.get_worker("w1")
                worker.last_seen_at = "2020-01-01T00:00:00+00:00"
                store._save(worker)

                changed = store.mark_stale_workers_offline(max_age_seconds=60)
                self.assertEqual(len(changed), 1)
                self.assertEqual(changed[0].worker_id, "w1")
                self.assertEqual(changed[0].status, WorkerStatus.OFFLINE)

                # last_seen_at should remain the old timestamp
                after = store.get_worker("w1")
                self.assertEqual(after.last_seen_at, "2020-01-01T00:00:00+00:00")
                self.assertEqual(after.status, WorkerStatus.OFFLINE)
            finally:
                db.close()

    def test_jsonl_stale_workers_become_offline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = DurableWorkerStore(path=Path(tmpdir) / "workers.jsonl")
            store.register_worker(worker_id="w1")
            worker = store.get_worker("w1")
            worker.last_seen_at = "2020-01-01T00:00:00+00:00"
            store._save(worker)

            changed = store.mark_stale_workers_offline(max_age_seconds=60)
            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0].status, WorkerStatus.OFFLINE)

    def test_fresh_workers_not_marked_offline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableWorkerStore(db=db)
                store.register_worker(worker_id="w1")

                changed = store.mark_stale_workers_offline(max_age_seconds=300)
                self.assertEqual(len(changed), 0)

                worker = store.get_worker("w1")
                self.assertEqual(worker.status, WorkerStatus.IDLE)
            finally:
                db.close()

    def test_already_offline_workers_not_returned_as_changed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableWorkerStore(db=db)
                store.register_worker(worker_id="w1")
                worker = store.get_worker("w1")
                worker.last_seen_at = "2020-01-01T00:00:00+00:00"
                worker.status = WorkerStatus.OFFLINE
                store._save(worker)

                changed = store.mark_stale_workers_offline(max_age_seconds=60)
                self.assertEqual(len(changed), 0)
            finally:
                db.close()

    def test_mark_offline_preserves_current_task_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableWorkerStore(db=db)
                store.register_worker(worker_id="w1")
                store.update_status("w1", WorkerStatus.RUNNING, current_task_id="dtask_1")
                worker = store.get_worker("w1")
                worker.last_seen_at = "2020-01-01T00:00:00+00:00"
                store._save(worker)

                changed = store.mark_stale_workers_offline(max_age_seconds=60)
                self.assertEqual(len(changed), 1)
                self.assertEqual(changed[0].current_task_id, "dtask_1")
            finally:
                db.close()

    def test_touch_unknown_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableWorkerStore(db=db)
                result = store.touch("w999")
                self.assertIsNone(result)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
