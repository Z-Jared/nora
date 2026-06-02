"""Tests for durable worker registry (TASK-030)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mini_agent.database import NoraDB
from mini_agent.durable_workers import DurableWorkerStore, DurableWorker, WorkerStatus
from mini_agent.tools import build_default_registry
from mini_agent.durable_events import DurableEventStore, FILE_EDIT_BLOCKED, FILE_EDIT_ERROR, FILE_EDIT_FINISHED, TASK_STATUS_CHANGED


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


class DurableWorkerClaimTests(unittest.TestCase):
    """Tests for claim_durable_task registry tool (TASK-034)."""

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

    def _create_task(self, goal="test task", steps="step one"):
        result = self.registry.call("create_durable_task", goal=goal, steps=steps)
        return json.loads(result)

    def _register_worker(self, worker_id, role="worker"):
        result = self.registry.call("register_worker", worker_id=worker_id, role=role)
        return json.loads(result)

    def test_idle_worker_claims_oldest_pending_task(self):
        self._register_worker("w1")
        t1 = self._create_task(goal="first task")
        t2 = self._create_task(goal="second task")

        result = self.registry.call("claim_durable_task", worker_id="w1")
        parsed = json.loads(result)

        self.assertTrue(parsed["claimed"])
        self.assertEqual(parsed["task_id"], t1["task_id"])

    def test_claim_updates_task_worker_id_and_worker_state(self):
        self._register_worker("w1")
        task = self._create_task()

        self.registry.call("claim_durable_task", worker_id="w1")

        task_result = json.loads(self.registry.call("get_durable_task", task_id=task["task_id"]))
        self.assertEqual(task_result["worker_id"], "w1")

        worker_result = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(worker_result["status"], "assigned")
        self.assertEqual(worker_result["current_task_id"], task["task_id"])

    def test_claim_does_not_change_task_status(self):
        self._register_worker("w1")
        task = self._create_task()

        self.registry.call("claim_durable_task", worker_id="w1")

        task_result = json.loads(self.registry.call("get_durable_task", task_id=task["task_id"]))
        self.assertEqual(task_result["status"], "pending")

    def test_unknown_worker_returns_error(self):
        result = self.registry.call("claim_durable_task", worker_id="w999")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_offline_worker_returns_error(self):
        self._register_worker("w1")
        # Manually mark offline via store
        store = self.registry.durable_worker_store
        store.update_status("w1", WorkerStatus.OFFLINE)

        result = self.registry.call("claim_durable_task", worker_id="w1")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_worker_with_current_task_returns_existing(self):
        self._register_worker("w1")
        t1 = self._create_task(goal="first")
        t2 = self._create_task(goal="second")

        # Claim first task
        self.registry.call("claim_durable_task", worker_id="w1")
        # Try to claim again
        result = self.registry.call("claim_durable_task", worker_id="w1")
        parsed = json.loads(result)

        self.assertTrue(parsed["claimed"])
        self.assertTrue(parsed["already_assigned"])
        self.assertEqual(parsed["task_id"], t1["task_id"])

    def test_no_available_task_returns_claimed_false(self):
        self._register_worker("w1")

        result = self.registry.call("claim_durable_task", worker_id="w1")
        parsed = json.loads(result)

        self.assertFalse(parsed["claimed"])
        self.assertNotIn("task_id", parsed)

    def test_no_available_task_does_not_mutate_worker(self):
        self._register_worker("w1")

        self.registry.call("claim_durable_task", worker_id="w1")

        worker_result = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(worker_result["status"], "idle")
        self.assertIsNone(worker_result.get("current_task_id"))

    def test_claim_emits_safe_event(self):
        self._register_worker("w1")
        self._create_task(goal="sensitive goal", steps="secret steps")

        self.registry.call("claim_durable_task", worker_id="w1")

        events = self.registry.durable_event_store.list_events(max_results=10)
        claim_events = [e for e in events if e.payload and e.payload.get("operation") == "claim"]
        self.assertEqual(len(claim_events), 1)

        payload = claim_events[0].payload
        self.assertEqual(payload["operation"], "claim")
        self.assertIn("task_id", payload)
        self.assertIn("worker_id_present", payload)
        self.assertIn("previous_worker_id_present", payload)
        # Must not leak raw content
        self.assertNotIn("sensitive goal", json.dumps(payload))
        self.assertNotIn("secret steps", json.dumps(payload))
        self.assertNotIn("goal", payload)
        self.assertNotIn("steps", payload)

    def test_broken_event_store_does_not_prevent_claim(self):
        self._register_worker("w1")
        task = self._create_task()

        with patch.object(self.registry.durable_event_store, "record", side_effect=RuntimeError("boom")):
            result = self.registry.call("claim_durable_task", worker_id="w1")

        parsed = json.loads(result)
        self.assertTrue(parsed["claimed"])
        self.assertEqual(parsed["task_id"], task["task_id"])

        # Verify task was actually assigned
        task_result = json.loads(self.registry.call("get_durable_task", task_id=task["task_id"]))
        self.assertEqual(task_result["worker_id"], "w1")

        # Verify worker state was updated
        worker_result = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(worker_result["status"], "assigned")
        self.assertEqual(worker_result["current_task_id"], task["task_id"])

    def test_claim_empty_worker_id_returns_error(self):
        result = self.registry.call("claim_durable_task", worker_id="")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_claim_whitespace_worker_id_returns_error(self):
        result = self.registry.call("claim_durable_task", worker_id="   ")
        parsed = json.loads(result)
        self.assertIn("error", parsed)


class DurableWorkerDispatchTests(unittest.TestCase):
    """Tests for dispatch_durable_tasks registry tool."""

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

    def _create_task(self, goal="test task"):
        return json.loads(self.registry.call("create_durable_task", goal=goal, steps="step one"))

    def _register_worker(self, worker_id, role="worker"):
        return json.loads(self.registry.call("register_worker", worker_id=worker_id, role=role))

    def test_basic_dispatch(self):
        self._register_worker("w1")
        self._create_task(goal="task one")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 1)
        self.assertEqual(result["assignments"][0]["worker_id"], "w1")
        self.assertEqual(result["assignments"][0]["status"], "assigned")

    def test_dispatch_multiple_workers_and_tasks(self):
        self._register_worker("w1")
        self._register_worker("w2")
        self._register_worker("w3")
        self._create_task(goal="task A")
        self._create_task(goal="task B")
        self._create_task(goal="task C")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 3)
        worker_ids = [a["worker_id"] for a in result["assignments"]]
        self.assertEqual(len(set(worker_ids)), 3)

    def test_dispatch_respects_max_assignments(self):
        self._register_worker("w1")
        self._register_worker("w2")
        self._register_worker("w3")
        self._create_task(goal="task A")
        self._create_task(goal="task B")
        self._create_task(goal="task C")

        result = json.loads(self.registry.call("dispatch_durable_tasks", max_assignments=2))

        self.assertEqual(result["dispatched"], 2)

    def test_dispatch_no_idle_workers(self):
        self._register_worker("w1")
        self._create_task(goal="task one")
        self.registry.call("dispatch_durable_tasks")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 0)
        self.assertEqual(result["assignments"], [])

    def test_dispatch_no_pending_tasks(self):
        self._register_worker("w1")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 0)
        self.assertEqual(result["assignments"], [])

    def test_dispatch_skips_offline_workers(self):
        self._register_worker("w1")
        self._register_worker("w2")
        self.registry.call("update_worker_status", worker_id="w2", status="offline")
        self._create_task(goal="task one")
        self._create_task(goal="task two")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 1)
        self.assertEqual(result["assignments"][0]["worker_id"], "w1")

    def test_dispatch_skips_stale_idle_workers(self):
        self._register_worker("w1")
        self._register_worker("w2")
        # Make w1 stale by setting last_seen_at to old timestamp
        store = self.registry.durable_worker_store
        worker = store.get_worker("w1")
        worker.last_seen_at = "2020-01-01T00:00:00+00:00"
        store._save(worker)
        self._create_task(goal="task one")
        self._create_task(goal="task two")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 1)
        self.assertEqual(result["assignments"][0]["worker_id"], "w2")
        # w1 should now be offline
        w1 = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(w1["status"], "offline")

    def test_dispatch_skips_running_workers(self):
        self._register_worker("w1")
        self._create_task(goal="task one")
        self.registry.call("dispatch_durable_tasks")
        self.registry.call("update_worker_status", worker_id="w1", status="running")
        self._register_worker("w2")
        self._create_task(goal="task two")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 1)
        self.assertEqual(result["assignments"][0]["worker_id"], "w2")

    def test_dispatch_does_not_reassign_existing_tasks(self):
        self._register_worker("w1")
        self._create_task(goal="task one")
        self.registry.call("dispatch_durable_tasks")

        self._register_worker("w2")
        self._create_task(goal="task two")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 1)
        task_ids = [a["task_id"] for a in result["assignments"]]
        self.assertNotIn("dtask_1", task_ids)

    def test_dispatch_assigns_worker_and_task_consistently(self):
        self._register_worker("w1")
        t1 = self._create_task(goal="task one")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))
        assignment = result["assignments"][0]

        task = json.loads(self.registry.call("get_durable_task", task_id=assignment["task_id"]))
        worker = json.loads(self.registry.call("get_worker", worker_id=assignment["worker_id"]))

        self.assertEqual(task["worker_id"], "w1")
        self.assertEqual(worker["status"], "assigned")
        self.assertEqual(worker["current_task_id"], t1["task_id"])

    def test_dispatch_output_bounded_no_goal_leak(self):
        self._register_worker("w1")
        self._create_task(goal="SECRET_GOAL_VALUE_12345")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        result_str = json.dumps(result)
        self.assertNotIn("SECRET_GOAL_VALUE_12345", result_str)
        self.assertNotIn("step one", result_str)

    def test_dispatch_event_failure_does_not_block(self):
        self._register_worker("w1")
        self._create_task(goal="task one")

        class BrokenEventStore:
            def record(self, **kwargs):
                raise RuntimeError("event store broken")

        self.registry.durable_event_store = BrokenEventStore()

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 1)

    def test_dispatch_max_assignments_bounded(self):
        self._register_worker("w1")
        self._create_task(goal="task one")

        result = json.loads(self.registry.call("dispatch_durable_tasks", max_assignments=200))

        self.assertEqual(result["dispatched"], 1)

    def test_dispatch_more_tasks_than_workers(self):
        self._register_worker("w1")
        self._create_task(goal="task A")
        self._create_task(goal="task B")
        self._create_task(goal="task C")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 1)

    def test_dispatch_more_workers_than_tasks(self):
        self._register_worker("w1")
        self._register_worker("w2")
        self._register_worker("w3")
        self._create_task(goal="task A")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 1)


class WorkspaceLeaseTests(unittest.TestCase):
    """Tests for workspace lease / isolation tools (TASK-060)."""

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

    def _register_worker(self, worker_id, role="worker"):
        return json.loads(self.registry.call("register_worker", worker_id=worker_id, role=role))

    def _create_task(self, goal="test task", worker_id=None):
        kwargs = {"goal": goal, "steps": "step one"}
        if worker_id:
            kwargs["worker_id"] = worker_id
        return json.loads(self.registry.call("create_durable_task", **kwargs))

    def _assign_and_activate(self, task_id, worker_id):
        """Assign task to worker and update worker status to assigned with current_task_id."""
        self.registry.call("assign_durable_task", task_id=task_id, worker_id=worker_id)
        self.registry.call("update_worker_status", worker_id=worker_id, status="assigned", current_task_id=task_id)

    def test_prepare_basic(self):
        self._register_worker("w1")
        task = self._create_task(goal="task one", worker_id="w1")
        self._assign_and_activate(task["task_id"], "w1")

        result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"]))

        self.assertIn("lease_id", result)
        self.assertEqual(result["worker_id"], "w1")
        self.assertEqual(result["task_id"], task["task_id"])
        self.assertIn("workspace_path", result)
        self.assertIn("created_at", result)
        # Directory should exist
        self.assertTrue(Path(result["workspace_path"]).exists())

    def test_prepare_unknown_worker_returns_error(self):
        result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w999", task_id="dtask_1"))
        self.assertIn("error", result)

    def test_prepare_offline_worker_returns_error(self):
        self._register_worker("w1")
        task = self._create_task(goal="task one", worker_id="w1")
        self._assign_and_activate(task["task_id"], "w1")
        self.registry.call("update_worker_status", worker_id="w1", status="offline")

        result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"]))
        self.assertIn("error", result)

    def test_prepare_idle_worker_returns_error(self):
        self._register_worker("w1")
        task = self._create_task(goal="task one", worker_id="w1")
        # assign_durable_task sets task.worker_id but worker stays idle
        self.registry.call("assign_durable_task", task_id=task["task_id"], worker_id="w1")

        result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"]))
        self.assertIn("error", result)
        self.assertIn("空闲", result["error"])

    def test_prepare_unknown_task_returns_error(self):
        self._register_worker("w1")

        result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id="dtask_999"))
        self.assertIn("error", result)

    def test_prepare_task_not_assigned_to_worker_returns_error(self):
        self._register_worker("w1")
        self._register_worker("w2")
        task = self._create_task(goal="task one", worker_id="w1")
        self._assign_and_activate(task["task_id"], "w1")

        result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w2", task_id=task["task_id"]))
        self.assertIn("error", result)

    def test_prepare_worker_current_task_mismatch_returns_error(self):
        self._register_worker("w1")
        t1 = self._create_task(goal="task one", worker_id="w1")
        t2 = self._create_task(goal="task two", worker_id="w1")
        self._assign_and_activate(t1["task_id"], "w1")
        # w1's current_task_id is t1, try to prepare for t2
        self.registry.call("assign_durable_task", task_id=t2["task_id"], worker_id="w1")

        result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=t2["task_id"]))
        self.assertIn("error", result)
        self.assertIn("当前未执行", result["error"])

    def test_prepare_worker_already_has_lease_returns_error(self):
        self._register_worker("w1")
        t1 = self._create_task(goal="task one", worker_id="w1")
        t2 = self._create_task(goal="task two", worker_id="w1")
        self._assign_and_activate(t1["task_id"], "w1")

        self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=t1["task_id"])

        # Switch to t2
        self._assign_and_activate(t2["task_id"], "w1")

        result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=t2["task_id"]))
        self.assertIn("error", result)
        self.assertIn("existing_lease_id", result)

    def test_prepare_same_task_returns_reused(self):
        self._register_worker("w1")
        task = self._create_task(goal="task one", worker_id="w1")
        self._assign_and_activate(task["task_id"], "w1")

        first = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"]))
        second = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"]))

        self.assertTrue(second["reused"])
        self.assertEqual(second["lease_id"], first["lease_id"])
        self.assertEqual(second["worker_id"], "w1")
        self.assertEqual(second["task_id"], task["task_id"])

    def test_prepare_task_already_leased_returns_error(self):
        self._register_worker("w1")
        self._register_worker("w2")
        task = self._create_task(goal="task one")
        self._assign_and_activate(task["task_id"], "w1")

        self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"])

        # Reassign task to w2 — but w1's lease on this task still exists
        self._assign_and_activate(task["task_id"], "w2")

        result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w2", task_id=task["task_id"]))
        self.assertIn("error", result)
        self.assertIn("existing_lease_id", result)

    def test_release_basic(self):
        self._register_worker("w1")
        task = self._create_task(goal="task one", worker_id="w1")
        self._assign_and_activate(task["task_id"], "w1")
        prepared = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"]))

        result = json.loads(self.registry.call("release_worker_workspace", worker_id="w1"))

        self.assertTrue(result["released"])
        self.assertEqual(result["lease_id"], prepared["lease_id"])
        self.assertEqual(result["worker_id"], "w1")

    def test_release_no_lease_returns_released_false(self):
        self._register_worker("w1")

        result = json.loads(self.registry.call("release_worker_workspace", worker_id="w1"))

        self.assertFalse(result["released"])
        self.assertEqual(result["worker_id"], "w1")

    def test_release_unknown_worker_returns_error(self):
        result = json.loads(self.registry.call("release_worker_workspace", worker_id="w999"))
        self.assertIn("error", result)

    def test_output_bounded_no_goal_leak(self):
        self._register_worker("w1")
        task = self._create_task(goal="SECRET_GOAL_98765", worker_id="w1")
        self._assign_and_activate(task["task_id"], "w1")

        result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"]))

        result_str = json.dumps(result)
        self.assertNotIn("SECRET_GOAL_98765", result_str)
        self.assertNotIn("step one", result_str)

    def test_event_failure_does_not_block_prepare(self):
        self._register_worker("w1")
        task = self._create_task(goal="task one", worker_id="w1")
        self._assign_and_activate(task["task_id"], "w1")

        with patch.object(self.registry.durable_event_store, "record", side_effect=RuntimeError("boom")):
            result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"]))

        self.assertIn("lease_id", result)
        self.assertEqual(result["worker_id"], "w1")

    def test_event_failure_does_not_block_release(self):
        self._register_worker("w1")
        task = self._create_task(goal="task one", worker_id="w1")
        self._assign_and_activate(task["task_id"], "w1")
        self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"])

        with patch.object(self.registry.durable_event_store, "record", side_effect=RuntimeError("boom")):
            result = json.loads(self.registry.call("release_worker_workspace", worker_id="w1"))

        self.assertTrue(result["released"])

    def test_prepare_emits_safe_event(self):
        self._register_worker("w1")
        task = self._create_task(goal="SECRET_GOAL_ABC", worker_id="w1")
        self._assign_and_activate(task["task_id"], "w1")

        self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"])

        events = self.registry.durable_event_store.list_events(max_results=10)
        ws_events = [e for e in events if e.event_type == "workspace_prepared"]
        self.assertEqual(len(ws_events), 1)

        payload = ws_events[0].payload
        self.assertEqual(payload["operation"], "prepare")
        self.assertIn("lease_id", payload)
        self.assertEqual(payload["worker_id"], "w1")
        self.assertEqual(payload["task_id"], task["task_id"])
        # Must not leak raw content
        self.assertNotIn("SECRET_GOAL_ABC", json.dumps(payload))
        self.assertNotIn("step one", json.dumps(payload))
        self.assertNotIn("goal", payload)
        self.assertNotIn("steps", payload)

    def test_mkdir_failure_returns_error_no_lease(self):
        self._register_worker("w1")
        task = self._create_task(goal="task one", worker_id="w1")
        self._assign_and_activate(task["task_id"], "w1")
        # Create a file where the .workspaces directory would be
        (self.root / ".workspaces").touch()

        result = json.loads(self.registry.call("prepare_worker_workspace", worker_id="w1", task_id=task["task_id"]))

        self.assertIn("error", result)
        # No lease should be created
        lease = self.registry.workspace_lease_store.get_lease_by_worker("w1")
        self.assertIsNone(lease)


class WorkspaceIntegrationTests(unittest.TestCase):
    """Tests for workspace lease integration into claim/dispatch (TASK-062)."""

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

    def _register_worker(self, worker_id, role="worker"):
        return json.loads(self.registry.call("register_worker", worker_id=worker_id, role=role))

    def _create_task(self, goal="test task"):
        return json.loads(self.registry.call("create_durable_task", goal=goal, steps="step one"))

    def test_claim_auto_prepares_workspace(self):
        self._register_worker("w1")
        self._create_task(goal="task one")

        result = json.loads(self.registry.call("claim_durable_task", worker_id="w1"))

        self.assertTrue(result["claimed"])
        ws = result["workspace"]
        self.assertIn("lease_id", ws)
        self.assertEqual(ws["worker_id"], "w1")
        self.assertEqual(ws["task_id"], result["task_id"])
        self.assertTrue(Path(ws["workspace_path"]).exists())

    def test_dispatch_auto_prepares_workspace(self):
        self._register_worker("w1")
        self._create_task(goal="task one")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 1)
        ws = result["assignments"][0]["workspace"]
        self.assertIn("lease_id", ws)
        self.assertEqual(ws["worker_id"], "w1")
        self.assertEqual(ws["task_id"], result["assignments"][0]["task_id"])
        self.assertTrue(Path(ws["workspace_path"]).exists())

    def test_claim_reuses_existing_workspace(self):
        self._register_worker("w1")
        task = self._create_task(goal="task one")

        # Claim once — creates workspace
        first = json.loads(self.registry.call("claim_durable_task", worker_id="w1"))
        # Claim again — should reuse
        second = json.loads(self.registry.call("claim_durable_task", worker_id="w1"))

        self.assertTrue(second["already_assigned"])
        ws = second["workspace"]
        self.assertTrue(ws["reused"])
        self.assertEqual(ws["lease_id"], first["workspace"]["lease_id"])

    def test_dispatch_multiple_workers_each_get_workspace(self):
        self._register_worker("w1")
        self._register_worker("w2")
        self._create_task(goal="task A")
        self._create_task(goal="task B")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 2)
        for assignment in result["assignments"]:
            ws = assignment["workspace"]
            self.assertIn("lease_id", ws)
            self.assertEqual(ws["worker_id"], assignment["worker_id"])
            self.assertTrue(Path(ws["workspace_path"]).exists())

    def test_claim_workspace_failure_does_not_block(self):
        self._register_worker("w1")
        self._create_task(goal="task one")

        # Make workspace preparation fail by creating a file at .workspaces
        (self.root / ".workspaces").touch()

        result = json.loads(self.registry.call("claim_durable_task", worker_id="w1"))

        self.assertTrue(result["claimed"])
        self.assertIn("workspace", result)
        self.assertIn("error", result["workspace"])

    def test_dispatch_workspace_failure_does_not_block(self):
        self._register_worker("w1")
        self._create_task(goal="task one")

        (self.root / ".workspaces").touch()

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 1)
        ws = result["assignments"][0]["workspace"]
        self.assertIn("error", ws)

    def test_claim_workspace_no_goal_leak(self):
        self._register_worker("w1")
        self._create_task(goal="SECRET_WS_GOAL_XYZ")

        result = json.loads(self.registry.call("claim_durable_task", worker_id="w1"))

        # Workspace output must not leak goal/steps
        ws_str = json.dumps(result["workspace"])
        self.assertNotIn("SECRET_WS_GOAL_XYZ", ws_str)
        self.assertNotIn("step one", ws_str)

    def test_dispatch_workspace_no_goal_leak(self):
        self._register_worker("w1")
        self._create_task(goal="SECRET_WS_GOAL_ABC")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        ws_str = json.dumps(result["assignments"][0]["workspace"])
        self.assertNotIn("SECRET_WS_GOAL_ABC", ws_str)
        self.assertNotIn("step one", ws_str)

    def test_claim_workspace_event_emitted(self):
        self._register_worker("w1")
        self._create_task(goal="task one")

        self.registry.call("claim_durable_task", worker_id="w1")

        events = self.registry.durable_event_store.list_events(max_results=20)
        ws_events = [e for e in events if e.event_type == "workspace_prepared"]
        self.assertEqual(len(ws_events), 1)
        self.assertEqual(ws_events[0].payload["worker_id"], "w1")

    def test_dispatch_workspace_event_emitted(self):
        self._register_worker("w1")
        self._create_task(goal="task one")

        self.registry.call("dispatch_durable_tasks")

        events = self.registry.durable_event_store.list_events(max_results=20)
        ws_events = [e for e in events if e.event_type == "workspace_prepared"]
        self.assertEqual(len(ws_events), 1)

    def test_dispatch_no_tasks_no_workspace(self):
        self._register_worker("w1")

        result = json.loads(self.registry.call("dispatch_durable_tasks"))

        self.assertEqual(result["dispatched"], 0)
        # No workspace events
        events = self.registry.durable_event_store.list_events(max_results=10)
        ws_events = [e for e in events if e.event_type == "workspace_prepared"]
        self.assertEqual(len(ws_events), 0)


class WorkspaceSandboxGuardTests(unittest.TestCase):
    """Tests for workspace sandbox guard tools (TASK-064)."""

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

    def _register_and_assign(self, worker_id="w1", goal="task one"):
        self.registry.call("register_worker", worker_id=worker_id)
        task = json.loads(self.registry.call("create_durable_task", goal=goal, steps="step one"))
        self.registry.call("assign_durable_task", task_id=task["task_id"], worker_id=worker_id)
        self.registry.call("update_worker_status", worker_id=worker_id, status="assigned", current_task_id=task["task_id"])
        return task["task_id"]

    def _prepare_workspace(self, worker_id, task_id):
        return json.loads(self.registry.call("prepare_worker_workspace", worker_id=worker_id, task_id=task_id))

    # --- get_worker_workspace ---

    def test_get_workspace_returns_lease(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))

        self.assertEqual(result["worker_id"], "w1")
        self.assertEqual(result["task_id"], task_id)
        self.assertIn("lease_id", result)
        self.assertIn("workspace_path", result)

    def test_get_workspace_no_lease_returns_error(self):
        task_id = self._register_and_assign()

        result = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))

        self.assertIn("error", result)
        self.assertIn("无 workspace lease", result["error"])

    def test_get_workspace_unknown_worker_returns_error(self):
        result = json.loads(self.registry.call("get_worker_workspace", worker_id="w999", task_id="dtask_1"))
        self.assertIn("error", result)

    def test_get_workspace_task_mismatch_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id="dtask_999"))
        self.assertIn("error", result)

    def test_get_workspace_worker_not_executing_task_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        # Change worker's current_task_id
        self.registry.call("update_worker_status", worker_id="w1", status="assigned", current_task_id="dtask_999")

        result = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))
        self.assertIn("error", result)
        self.assertIn("当前未执行", result["error"])

    # --- validate_worker_workspace_path ---

    def test_validate_path_inside_workspace(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws_path = lease["workspace_path"]

        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task_id,
            path=ws_path + "/src/main.py",
        ))

        self.assertTrue(result["valid"])
        self.assertIn("path", result)
        self.assertIn("workspace_path", result)

    def test_validate_path_workspace_root_itself(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws_path = lease["workspace_path"]

        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task_id,
            path=ws_path,
        ))

        self.assertTrue(result["valid"])

    def test_validate_path_traversal_escape_returns_error(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws_path = lease["workspace_path"]

        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task_id,
            path=ws_path + "/../../etc/passwd",
        ))

        self.assertIn("error", result)
        self.assertIn("不在 workspace 内", result["error"])

    def test_validate_path_absolute_escape_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task_id,
            path="/etc/passwd",
        ))

        self.assertIn("error", result)
        self.assertIn("不在 workspace 内", result["error"])

    def test_validate_path_no_lease_returns_error(self):
        task_id = self._register_and_assign()

        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task_id,
            path="/tmp/some/file",
        ))

        self.assertIn("error", result)
        self.assertIn("无 workspace lease", result["error"])

    def test_validate_path_unknown_worker_returns_error(self):
        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w999", task_id="dtask_1", path="/tmp/x",
        ))
        self.assertIn("error", result)

    def test_validate_path_empty_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task_id, path="",
        ))
        self.assertIn("error", result)

    def test_validate_path_worker_task_mismatch_returns_error(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws_path = lease["workspace_path"]
        self.registry.call("update_worker_status", worker_id="w1", status="assigned", current_task_id="dtask_999")

        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task_id,
            path=ws_path + "/file.txt",
        ))
        self.assertIn("error", result)

    def test_validate_path_lease_for_different_task_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        # Create a second task and try to validate against it
        task2 = json.loads(self.registry.call("create_durable_task", goal="task two", steps="step two"))

        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task2["task_id"],
            path="/tmp/x",
        ))
        self.assertIn("error", result)

    def test_validate_path_no_goal_leak(self):
        task_id = self._register_and_assign(goal="SECRET_SANDBOX_GOAL_777")
        lease = self._prepare_workspace("w1", task_id)
        ws_path = lease["workspace_path"]

        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task_id,
            path=ws_path + "/file.txt",
        ))

        result_str = json.dumps(result)
        self.assertNotIn("SECRET_SANDBOX_GOAL_777", result_str)
        self.assertNotIn("step one", result_str)

    def test_validate_path_with_dot_dot_normalized(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws_path = lease["workspace_path"]
        # Path with .. that still stays within workspace after resolution
        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task_id,
            path=ws_path + "/subdir/../file.txt",
        ))
        self.assertTrue(result["valid"])

    def test_get_workspace_offline_worker_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="offline")

        result = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))
        self.assertIn("error", result)
        self.assertIn("已离线", result["error"])

    def test_validate_path_offline_worker_returns_error(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws_path = lease["workspace_path"]
        self.registry.call("update_worker_status", worker_id="w1", status="offline")

        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task_id,
            path=ws_path + "/file.txt",
        ))
        self.assertIn("error", result)
        self.assertIn("已离线", result["error"])

    def test_get_workspace_idle_worker_with_task_id_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        # Set idle but keep current_task_id (edge case: lease still exists)
        store = self.registry.durable_worker_store
        worker = store.get_worker("w1")
        worker.status = "idle"
        store._save(worker)

        result = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))
        self.assertIn("error", result)
        self.assertIn("空闲", result["error"])

    def test_validate_path_idle_worker_with_task_id_returns_error(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws_path = lease["workspace_path"]
        store = self.registry.durable_worker_store
        worker = store.get_worker("w1")
        worker.status = "idle"
        store._save(worker)

        result = json.loads(self.registry.call(
            "validate_worker_workspace_path",
            worker_id="w1", task_id=task_id,
            path=ws_path + "/file.txt",
        ))
        self.assertIn("error", result)
        self.assertIn("空闲", result["error"])


class WorkspaceFileInspectionTests(unittest.TestCase):
    """Tests for worker workspace file inspection tools (TASK-066)."""

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

    def _register_and_assign(self, worker_id="w1", goal="task one"):
        self.registry.call("register_worker", worker_id=worker_id)
        task = json.loads(self.registry.call("create_durable_task", goal=goal, steps="step one"))
        self.registry.call("assign_durable_task", task_id=task["task_id"], worker_id=worker_id)
        self.registry.call("update_worker_status", worker_id=worker_id, status="assigned", current_task_id=task["task_id"])
        return task["task_id"]

    def _prepare_workspace(self, worker_id, task_id):
        return json.loads(self.registry.call("prepare_worker_workspace", worker_id=worker_id, task_id=task_id))

    def _write_file(self, ws_path, rel_path, content):
        p = Path(ws_path) / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    # --- list_worker_workspace_files ---

    def test_list_files_empty_workspace(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id))

        self.assertEqual(result["files"], [])
        self.assertEqual(result["count"], 0)

    def test_list_files_returns_relative_paths(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "src/main.py", "print('hi')")
        self._write_file(ws, "README.md", "# hello")

        result = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id))

        self.assertIn("src/main.py", result["files"])
        self.assertIn("README.md", result["files"])
        self.assertEqual(result["count"], 2)

    def test_list_files_skips_sensitive_files(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "app.py", "code")
        self._write_file(ws, ".env", "SECRET=1")

        result = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id))

        self.assertIn("app.py", result["files"])
        self.assertNotIn(".env", result["files"])

    def test_list_files_skips_sensitive_dirs(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "src/app.py", "code")
        self._write_file(ws, ".git/config", "[core]")

        result = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id))

        self.assertIn("src/app.py", result["files"])
        for f in result["files"]:
            self.assertFalse(f.startswith(".git/"), f"should not list .git files: {f}")

    def test_list_files_max_bounded(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        for i in range(5):
            self._write_file(ws, f"f{i}.txt", f"content {i}")

        result = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id, max_files=3))

        self.assertEqual(result["count"], 3)
        self.assertEqual(len(result["files"]), 3)

    def test_list_files_no_lease_returns_error(self):
        task_id = self._register_and_assign()

        result = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id))
        self.assertIn("error", result)

    def test_list_files_unknown_worker_returns_error(self):
        result = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w999", task_id="dtask_1"))
        self.assertIn("error", result)

    def test_list_files_no_goal_leak(self):
        task_id = self._register_and_assign(goal="SECRET_LIST_GOAL_555")
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id))

        self.assertNotIn("SECRET_LIST_GOAL_555", json.dumps(result))
        self.assertNotIn("step one", json.dumps(result))

    # --- read_worker_workspace_file ---

    def test_read_file_returns_content(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "hello.py", "print('hello world')")

        result = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="hello.py"))

        self.assertEqual(result["content"], "print('hello world')")
        self.assertEqual(result["path"], "hello.py")

    def test_read_file_absolute_inside_workspace(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "data.txt", "some data")
        abs_path = str(Path(ws) / "data.txt")

        result = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path=abs_path))

        self.assertEqual(result["content"], "some data")

    def test_read_file_traversal_rejected(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="../../etc/passwd"))

        self.assertIn("error", result)
        self.assertIn("不在 workspace 内", result["error"])

    def test_read_file_absolute_escape_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="/etc/passwd"))

        self.assertIn("error", result)

    def test_read_file_missing_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="no_such_file.txt"))

        self.assertIn("error", result)
        self.assertIn("不存在", result["error"])

    def test_read_file_sensitive_rejected(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, ".env", "SECRET=value")

        result = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path=".env"))

        self.assertIn("error", result)
        self.assertIn("敏感", result["error"])

    def test_read_file_empty_path_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path=""))

        self.assertIn("error", result)

    def test_read_file_offline_worker_returns_error(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "f.txt", "data")
        self.registry.call("update_worker_status", worker_id="w1", status="offline")

        result = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="f.txt"))
        self.assertIn("error", result)
        self.assertIn("已离线", result["error"])

    def test_read_file_no_goal_leak(self):
        task_id = self._register_and_assign(goal="SECRET_READ_GOAL_666")
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "f.txt", "normal content")

        result = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="f.txt"))

        self.assertNotIn("SECRET_READ_GOAL_666", json.dumps(result))
        self.assertNotIn("step one", json.dumps(result))

    # --- preview_worker_workspace_write ---

    def test_preview_write_new_file(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "preview_worker_workspace_write",
            worker_id="w1", task_id=task_id,
            path="new_file.py", content="print('new')",
        ))

        self.assertIn("preview", result)
        self.assertTrue(result["will_create"])
        self.assertIn("print('new')", result["preview"])

    def test_preview_write_existing_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "existing.py", "old content")

        result = json.loads(self.registry.call(
            "preview_worker_workspace_write",
            worker_id="w1", task_id=task_id,
            path="existing.py", content="new content",
        ))

        self.assertIn("preview", result)
        self.assertFalse(result["will_create"])
        self.assertIn("-old content", result["preview"])
        self.assertIn("+new content", result["preview"])

    def test_preview_write_no_actual_file_change(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        self.registry.call(
            "preview_worker_workspace_write",
            worker_id="w1", task_id=task_id,
            path="phantom.py", content="should not exist",
        )

        self.assertFalse((Path(self.registry.workspace_lease_store.get_lease_by_worker("w1").workspace_path) / "phantom.py").exists())

    def test_preview_write_traversal_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "preview_worker_workspace_write",
            worker_id="w1", task_id=task_id,
            path="../../etc/evil", content="bad",
        ))

        self.assertIn("error", result)

    def test_preview_write_sensitive_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "preview_worker_workspace_write",
            worker_id="w1", task_id=task_id,
            path=".env", content="SECRET=1",
        ))

        self.assertIn("error", result)
        self.assertIn("敏感", result["error"])

    def test_preview_write_no_goal_leak(self):
        task_id = self._register_and_assign(goal="SECRET_PREVIEW_GOAL_777")
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "preview_worker_workspace_write",
            worker_id="w1", task_id=task_id,
            path="f.txt", content="safe content",
        ))

        self.assertNotIn("SECRET_PREVIEW_GOAL_777", json.dumps(result))
        self.assertNotIn("step one", json.dumps(result))

    def test_preview_write_no_mutation_of_task_state(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        self.registry.call(
            "preview_worker_workspace_write",
            worker_id="w1", task_id=task_id,
            path="f.txt", content="data",
        )

        task = json.loads(self.registry.call("get_durable_task", task_id=task_id))
        self.assertEqual(task["status"], "pending")

    def test_preview_write_context_lines(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "preview_worker_workspace_write",
            worker_id="w1", task_id=task_id,
            path="f.txt", content="line1\nline2\nline3",
            context_lines=0,
        ))

        self.assertIn("preview", result)

    def test_list_files_no_mutation(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "f.txt", "data")

        self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id)

        task = json.loads(self.registry.call("get_durable_task", task_id=task_id))
        self.assertEqual(task["status"], "pending")
        worker = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(worker["status"], "assigned")

    def test_read_file_no_mutation(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "f.txt", "data")

        self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="f.txt")

        task = json.loads(self.registry.call("get_durable_task", task_id=task_id))
        self.assertEqual(task["status"], "pending")

    def test_list_files_bad_max_files_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "list_worker_workspace_files", worker_id="w1", task_id=task_id, max_files="bad",
        ))

        self.assertIn("error", result)
        self.assertIn("max_files", result["error"])

    def test_preview_write_bad_context_lines_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "preview_worker_workspace_write",
            worker_id="w1", task_id=task_id,
            path="f.txt", content="data", context_lines="bad",
        ))

        self.assertIn("error", result)
        self.assertIn("context_lines", result["error"])

    def test_list_files_skips_symlink_escape(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        # Create a file outside the workspace
        outside = self.root / "outside.txt"
        outside.write_text("outside content")
        # Create a symlink inside workspace pointing outside
        (ws / "link.txt").symlink_to(outside)
        # Create a normal file too
        (ws / "real.txt").write_text("real content")

        result = json.loads(self.registry.call(
            "list_worker_workspace_files", worker_id="w1", task_id=task_id,
        ))

        self.assertIn("real.txt", result["files"])
        self.assertNotIn("link.txt", result["files"])

    def test_list_files_skips_symlink_to_git_dir(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        # Create .git/config inside workspace
        git_dir = ws / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]\n\tbare = false")
        # Create a symlink at workspace root pointing to .git/config
        (ws / "gitlink").symlink_to(git_dir / "config")
        (ws / "real.txt").write_text("real content")

        result = json.loads(self.registry.call(
            "list_worker_workspace_files", worker_id="w1", task_id=task_id,
        ))

        self.assertIn("real.txt", result["files"])
        self.assertNotIn("gitlink", result["files"])

    def test_list_files_skips_symlink_to_logs_dir(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        # Create logs/app.log inside workspace
        logs_dir = ws / "logs"
        logs_dir.mkdir()
        (logs_dir / "app.log").write_text("log data")
        # Create a symlink pointing to logs/app.log
        (ws / "loglink").symlink_to(logs_dir / "app.log")
        (ws / "main.py").write_text("print('hi')")

        result = json.loads(self.registry.call(
            "list_worker_workspace_files", worker_id="w1", task_id=task_id,
        ))

        self.assertIn("main.py", result["files"])
        self.assertNotIn("loglink", result["files"])


class WorkspaceFileWriteTests(unittest.TestCase):
    """Tests for worker workspace write tools (TASK-068)."""

    SECRET_SENTINEL = "SECRET_GOAL_12345"

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

    def _register_and_assign(self, worker_id="w1", goal="task one"):
        self.registry.call("register_worker", worker_id=worker_id)
        task = json.loads(self.registry.call("create_durable_task", goal=goal, steps="step one"))
        self.registry.call("assign_durable_task", task_id=task["task_id"], worker_id=worker_id)
        self.registry.call("update_worker_status", worker_id=worker_id, status="assigned", current_task_id=task["task_id"])
        return task["task_id"]

    def _prepare_workspace(self, worker_id, task_id):
        return json.loads(self.registry.call("prepare_worker_workspace", worker_id=worker_id, task_id=task_id))

    def _write_file(self, ws_path, rel_path, content):
        p = Path(ws_path) / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    # --- write_worker_workspace_file ---

    def test_write_new_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="src/main.py", content="print('hello')",
        ))

        self.assertEqual(result["operation"], "write")
        self.assertEqual(result["path"], "src/main.py")
        self.assertTrue(result["created"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["bytes_after"], len("print('hello')".encode("utf-8")))
        written = (Path(ws) / "src/main.py").read_text(encoding="utf-8")
        self.assertEqual(written, "print('hello')")

    def test_write_overwrites_existing_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "app.py", "old content")

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="app.py", content="new content",
        ))

        self.assertFalse(result["created"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["bytes_before"], len("old content".encode("utf-8")))
        self.assertEqual((Path(ws) / "app.py").read_text(), "new content")

    def test_write_creates_parent_dirs(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])

        self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="a/b/c/file.txt", content="deep",
        )

        self.assertEqual((ws / "a/b/c/file.txt").read_text(), "deep")

    def test_write_returns_safe_metadata(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="f.txt", content="data",
        ))

        self.assertIn("lease_id", result)
        self.assertEqual(result["worker_id"], "w1")
        self.assertEqual(result["task_id"], task_id)
        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_write_traversal_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="../escape.txt", content="bad",
        ))

        self.assertIn("error", result)
        self.assertIn("workspace", result["error"])

    def test_write_absolute_escape_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="/tmp/escape.txt", content="bad",
        ))

        self.assertIn("error", result)

    def test_write_env_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path=".env", content="SECRET=1",
        ))

        self.assertIn("error", result)
        self.assertIn("敏感", result["error"])

    def test_write_env_directory_rejected(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path=".env/config", content="SECRET=1",
        ))

        self.assertIn("error", result)
        self.assertIn("敏感", result["error"])
        self.assertFalse((ws / ".env/config").exists())

    def test_write_denied_path_records_blocked_without_content(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        secret_content = "SECRET_WRITE_CONTENT_555"

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path=".env/config", content=secret_content,
        ))

        self.assertIn("error", result)
        events = self.registry.durable_event_store.list_events(
            event_type=FILE_EDIT_BLOCKED,
            source="worker_workspace",
            worker_id="w1",
            max_results=10,
        )
        self.assertEqual(events[0].payload["error"], "denied_path")
        serialized = json.dumps([event.to_dict() for event in events], ensure_ascii=False)
        self.assertNotIn(secret_content, serialized)

    def test_write_git_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path=".git/config", content="[core]",
        ))

        self.assertIn("error", result)

    def test_write_logs_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="logs/app.log", content="log",
        ))

        self.assertIn("error", result)

    def test_write_data_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="data/secret.csv", content="a,b",
        ))

        self.assertIn("error", result)

    def test_write_unknown_worker_error(self):
        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w999", task_id="dtask_1", path="f.txt", content="x",
        ))
        self.assertIn("error", result)

    def test_write_no_lease_error(self):
        task_id = self._register_and_assign()
        # Don't prepare workspace

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="f.txt", content="x",
        ))
        self.assertIn("error", result)
        self.assertIn("lease", result["error"])

    def test_write_task_mismatch_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        # Create another task and try to use it
        task2 = json.loads(self.registry.call("create_durable_task", goal="other", steps="other"))

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task2["task_id"], path="f.txt", content="x",
        ))
        self.assertIn("error", result)

    def test_write_offline_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="offline")

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="f.txt", content="x",
        ))
        self.assertIn("error", result)
        self.assertIn("离线", result["error"])

    def test_write_idle_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="idle", current_task_id=None)

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="f.txt", content="x",
        ))
        self.assertIn("error", result)
        self.assertIn("空闲", result["error"])

    def test_write_oversized_content(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        big = "x" * (64 * 1024 + 1)

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="big.txt", content=big,
        ))

        self.assertIn("error", result)
        self.assertIn("过大", result["error"])

    def test_write_no_goal_leak(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="f.txt", content="ok",
        ))

        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_write_no_mutation_of_task_worker_lease(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        lease_id = lease["lease_id"]

        self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="f.txt", content="data",
        )

        worker = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(worker["status"], "assigned")
        self.assertEqual(worker["current_task_id"], task_id)
        lease_info = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))
        self.assertEqual(lease_info["lease_id"], lease_id)

    # --- replace_worker_workspace_file ---

    def test_replace_text_in_workspace_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "app.py", "hello world")

        result = json.loads(self.registry.call(
            "replace_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="app.py",
            old_text="world", new_text="nora",
        ))

        self.assertEqual(result["operation"], "replace")
        self.assertTrue(result["changed"])
        self.assertEqual((Path(ws) / "app.py").read_text(), "hello nora")

    def test_replace_old_text_not_found(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_file(lease["workspace_path"], "app.py", "hello world")

        result = json.loads(self.registry.call(
            "replace_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="app.py",
            old_text="not_there", new_text="x",
        ))

        self.assertIn("error", result)
        self.assertIn("没有找到", result["error"])

    def test_replace_empty_old_text(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_file(lease["workspace_path"], "app.py", "hello")

        result = json.loads(self.registry.call(
            "replace_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="app.py",
            old_text="", new_text="x",
        ))

        self.assertIn("error", result)
        self.assertIn("old_text", result["error"])

    def test_replace_only_first_occurrence(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "app.py", "aaa")

        self.registry.call(
            "replace_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="app.py",
            old_text="a", new_text="b",
        )

        self.assertEqual((Path(ws) / "app.py").read_text(), "baa")

    def test_replace_file_not_found(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "replace_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="missing.py",
            old_text="a", new_text="b",
        ))

        self.assertIn("error", result)
        self.assertIn("不存在", result["error"])

    def test_replace_oversized_result(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        small = "a" * 100
        self._write_file(ws, "f.txt", small)
        big_new = "b" * (64 * 1024 + 1)

        result = json.loads(self.registry.call(
            "replace_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="f.txt",
            old_text=small, new_text=big_new,
        ))

        self.assertIn("error", result)
        self.assertIn("过大", result["error"])

    def test_replace_no_goal_leak(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        self._write_file(lease["workspace_path"], "f.txt", "hello")

        result = json.loads(self.registry.call(
            "replace_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="f.txt",
            old_text="hello", new_text="bye",
        ))

        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    # --- apply_worker_workspace_patch ---

    def test_apply_patch_to_workspace_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "main.py", "line1\nline2\nline3\n")

        patch = (
            "--- a/main.py\n"
            "+++ b/main.py\n"
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            "-line2\n"
            "+line2_modified\n"
            " line3\n"
        )

        result = json.loads(self.registry.call(
            "apply_worker_workspace_patch",
            worker_id="w1", task_id=task_id, patch=patch,
        ))

        self.assertEqual(result["operation"], "patch")
        self.assertTrue(result["changed"])
        self.assertIn("main.py", result["files"])
        self.assertEqual((Path(ws) / "main.py").read_text(), "line1\nline2_modified\nline3\n")

    def test_apply_patch_file_not_found(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        patch = (
            "--- a/missing.py\n"
            "+++ b/missing.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new\n"
        )

        result = json.loads(self.registry.call(
            "apply_worker_workspace_patch",
            worker_id="w1", task_id=task_id, patch=patch,
        ))

        self.assertIn("error", result)
        self.assertIn("不存在", result["error"])

    def test_apply_patch_empty(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "apply_worker_workspace_patch",
            worker_id="w1", task_id=task_id, patch="",
        ))

        self.assertIn("error", result)
        self.assertIn("不能为空", result["error"])

    def test_apply_patch_context_mismatch(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_file(lease["workspace_path"], "main.py", "actual content\n")

        patch = (
            "--- a/main.py\n"
            "+++ b/main.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-different content\n"
            "+new\n"
        )

        result = json.loads(self.registry.call(
            "apply_worker_workspace_patch",
            worker_id="w1", task_id=task_id, patch=patch,
        ))

        self.assertIn("error", result)

    def test_apply_patch_no_goal_leak(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        self._write_file(lease["workspace_path"], "f.py", "old\n")

        patch = (
            "--- a/f.py\n"
            "+++ b/f.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new\n"
        )

        result = json.loads(self.registry.call(
            "apply_worker_workspace_patch",
            worker_id="w1", task_id=task_id, patch=patch,
        ))

        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_apply_patch_traversal_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        patch = (
            "--- a/../../../escape.py\n"
            "+++ b/../../../escape.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new\n"
        )

        result = json.loads(self.registry.call(
            "apply_worker_workspace_patch",
            worker_id="w1", task_id=task_id, patch=patch,
        ))

        self.assertIn("error", result)

    def test_apply_patch_env_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        patch = (
            "--- a/.env\n"
            "+++ b/.env\n"
            "@@ -1,1 +1,1 @@\n"
            "-OLD\n"
            "+NEW\n"
        )

        result = json.loads(self.registry.call(
            "apply_worker_workspace_patch",
            worker_id="w1", task_id=task_id, patch=patch,
        ))

        self.assertIn("error", result)

    def test_apply_patch_env_directory_rejected(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, ".env/config", "OLD\n")

        patch = (
            "--- a/.env/config\n"
            "+++ b/.env/config\n"
            "@@ -1,1 +1,1 @@\n"
            "-OLD\n"
            "+NEW\n"
        )

        result = json.loads(self.registry.call(
            "apply_worker_workspace_patch",
            worker_id="w1", task_id=task_id, patch=patch,
        ))

        self.assertIn("error", result)
        self.assertIn("敏感", result["error"])
        self.assertEqual((Path(ws) / ".env/config").read_text(encoding="utf-8"), "OLD\n")

    def test_apply_patch_write_failure_rolls_back_failed_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "a.txt", "aaa\n")
        self._write_file(ws, "b.txt", "bbb\n")
        patch_text = (
            "--- a/a.txt\n"
            "+++ b/a.txt\n"
            "@@ -1,1 +1,1 @@\n"
            "-aaa\n"
            "+AAA\n"
            "--- a/b.txt\n"
            "+++ b/b.txt\n"
            "@@ -1,1 +1,1 @@\n"
            "-bbb\n"
            "+BBB\n"
        )
        original_write_text = Path.write_text
        failed_once = {"value": False}

        def flaky_write(path_obj, data, *args, **kwargs):
            if path_obj.name == "b.txt" and not failed_once["value"]:
                failed_once["value"] = True
                original_write_text(path_obj, "PARTIAL\n", *args, **kwargs)
                raise OSError("disk full SECRET_PATCH_ERROR")
            return original_write_text(path_obj, data, *args, **kwargs)

        with patch.object(Path, "write_text", flaky_write):
            result = json.loads(self.registry.call(
                "apply_worker_workspace_patch",
                worker_id="w1", task_id=task_id, patch=patch_text,
            ))

        self.assertIn("error", result)
        self.assertEqual((Path(ws) / "a.txt").read_text(encoding="utf-8"), "aaa\n")
        self.assertEqual((Path(ws) / "b.txt").read_text(encoding="utf-8"), "bbb\n")
        events = self.registry.durable_event_store.list_events(
            event_type=FILE_EDIT_ERROR,
            source="worker_workspace",
            worker_id="w1",
            max_results=10,
        )
        serialized = json.dumps([event.to_dict() for event in events], ensure_ascii=False)
        self.assertNotIn("SECRET_PATCH_ERROR", serialized)

    # --- existing read/list/preview still work after writes ---

    def test_read_list_preview_still_work_after_write(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_file(ws, "existing.py", "original")

        # Write a new file
        self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="new.py", content="new file",
        )
        # Replace in existing file
        self.registry.call(
            "replace_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="existing.py",
            old_text="original", new_text="updated",
        )

        # All read tools should still work
        files = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id))
        self.assertIn("new.py", files["files"])
        self.assertIn("existing.py", files["files"])

        content = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="existing.py"))
        self.assertEqual(content["content"], "updated")

        preview = json.loads(self.registry.call("preview_worker_workspace_write", worker_id="w1", task_id=task_id, path="existing.py", content="final"))
        self.assertIn("preview", preview)

    def test_list_skips_env_directory_files(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        self._write_file(ws, ".env/config", "SECRET=1")
        self._write_file(ws, "visible.txt", "ok")

        files = json.loads(self.registry.call(
            "list_worker_workspace_files",
            worker_id="w1",
            task_id=task_id,
        ))

        self.assertIn("visible.txt", files["files"])
        self.assertNotIn(".env/config", files["files"])

    def test_write_after_failed_write_still_works(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        # First write fails (traversal)
        self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="../bad.txt", content="bad",
        )
        # Second write should succeed
        result = json.loads(self.registry.call(
            "write_worker_workspace_file",
            worker_id="w1", task_id=task_id, path="good.txt", content="ok",
        ))
        self.assertEqual(result["operation"], "write")
        self.assertTrue(result["changed"])


class WorkspaceChangeSummaryTests(unittest.TestCase):
    """Tests for worker workspace change summary and patch export tools (TASK-070)."""

    SECRET_SENTINEL = "SECRET_GOAL_78901"

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

    def _register_and_assign(self, worker_id="w1", goal="task one"):
        self.registry.call("register_worker", worker_id=worker_id)
        task = json.loads(self.registry.call("create_durable_task", goal=goal, steps="step one"))
        self.registry.call("assign_durable_task", task_id=task["task_id"], worker_id=worker_id)
        self.registry.call("update_worker_status", worker_id=worker_id, status="assigned", current_task_id=task["task_id"])
        return task["task_id"]

    def _prepare_workspace(self, worker_id, task_id):
        return json.loads(self.registry.call("prepare_worker_workspace", worker_id=worker_id, task_id=task_id))

    def _write_project_file(self, rel_path, content):
        p = self.root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _write_ws_file(self, ws_path, rel_path, content):
        p = Path(ws_path) / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    # --- summarize_worker_workspace_changes ---

    def test_summary_detects_created_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, "new.py", "new content")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        created = [f for f in result["files"] if f["status"] == "created"]
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["path"], "new.py")
        self.assertFalse(created[0]["project"]["exists"])
        self.assertEqual(result["created"], 1)

    def test_summary_detects_modified_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("app.py", "original")
        self._write_ws_file(ws, "app.py", "modified")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        modified = [f for f in result["files"] if f["status"] == "modified"]
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]["path"], "app.py")
        self.assertEqual(result["modified"], 1)

    def test_summary_detects_same_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("app.py", "same content")
        self._write_ws_file(ws, "app.py", "same content")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        same = [f for f in result["files"] if f["status"] == "same"]
        self.assertEqual(len(same), 1)
        self.assertEqual(result["same"], 1)

    def test_summary_skips_env_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, ".env", "SECRET=1")
        self._write_ws_file(ws, "app.py", "code")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        paths = [f["path"] for f in result["files"]]
        self.assertIn("app.py", paths)
        self.assertNotIn(".env", paths)

    def test_summary_skips_env_directory_component_without_leak(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        sentinel = "SECRET_ENV_DIRECTORY_COMPONENT_789"
        (ws / ".env").mkdir()
        (ws / ".env" / "config").write_text(sentinel, encoding="utf-8")
        self._write_ws_file(str(ws), "app.py", "code")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        serialized = json.dumps(result)
        paths = [f["path"] for f in result["files"]]
        self.assertIn("app.py", paths)
        self.assertNotIn(".env/config", paths)
        self.assertNotIn(sentinel, serialized)

    def test_summary_skips_env_local_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, ".env.local", "LOCAL=1")
        self._write_ws_file(ws, "app.py", "code")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        paths = [f["path"] for f in result["files"]]
        self.assertNotIn(".env.local", paths)

    def test_summary_skips_env_production_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, ".env.production", "PROD=1")
        self._write_ws_file(ws, "app.py", "code")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        paths = [f["path"] for f in result["files"]]
        self.assertNotIn(".env.production", paths)

    def test_summary_skips_git_dir(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        (ws / ".git").mkdir()
        (ws / ".git" / "config").write_text("[core]")
        self._write_ws_file(str(ws), "app.py", "code")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        paths = [f["path"] for f in result["files"]]
        self.assertNotIn(".git/config", paths)

    def test_summary_skips_logs_dir(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        (ws / "logs").mkdir()
        (ws / "logs" / "app.log").write_text("log")
        self._write_ws_file(str(ws), "app.py", "code")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        paths = [f["path"] for f in result["files"]]
        self.assertNotIn("logs/app.log", paths)

    def test_summary_skips_data_dir(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        (ws / "data").mkdir()
        (ws / "data" / "db.csv").write_text("a,b")
        self._write_ws_file(str(ws), "app.py", "code")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        paths = [f["path"] for f in result["files"]]
        self.assertNotIn("data/db.csv", paths)

    def test_summary_max_files_bounded(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        for i in range(10):
            self._write_ws_file(ws, f"f{i}.py", f"content {i}")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id, max_files=3,
        ))

        self.assertEqual(result["count"], 3)

    def test_summary_bad_max_files_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id, max_files="abc",
        ))

        self.assertIn("error", result)

    def test_summary_unknown_worker_error(self):
        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w999", task_id="dtask_1",
        ))
        self.assertIn("error", result)

    def test_summary_no_lease_error(self):
        task_id = self._register_and_assign()

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)
        self.assertIn("lease", result["error"])

    def test_summary_task_mismatch_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        task2 = json.loads(self.registry.call("create_durable_task", goal="other", steps="other"))

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task2["task_id"],
        ))
        self.assertIn("error", result)

    def test_summary_offline_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="offline")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)
        self.assertIn("离线", result["error"])

    def test_summary_idle_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="idle", current_task_id=None)

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)
        self.assertIn("空闲", result["error"])

    def test_summary_no_goal_leak(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "app.py", "code")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_summary_no_mutation(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("app.py", "original")
        self._write_ws_file(ws, "app.py", "modified")

        self.registry.call("summarize_worker_workspace_changes", worker_id="w1", task_id=task_id)

        # Project file unchanged
        self.assertEqual((self.root / "app.py").read_text(), "original")
        # Worker file unchanged
        self.assertEqual((Path(ws) / "app.py").read_text(), "modified")
        # Worker/task/lease state unchanged
        worker = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(worker["status"], "assigned")
        lease_info = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))
        self.assertEqual(lease_info["lease_id"], lease["lease_id"])

    def test_summary_returns_safe_metadata(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "f.txt", "data")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        self.assertIn("lease_id", result)
        self.assertEqual(result["worker_id"], "w1")
        self.assertEqual(result["task_id"], task_id)
        self.assertIn("created", result)
        self.assertIn("modified", result)
        self.assertIn("same", result)
        self.assertIn("skipped", result)
        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_summary_skips_project_symlink_escape(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        # Create a symlink in project root pointing truly outside
        outside_dir = tempfile.mkdtemp()
        outside = Path(outside_dir) / "outside_target.txt"
        outside.write_text("outside")
        (self.root / "escape_link").symlink_to(outside)
        # Create a file in worker workspace with same name
        self._write_ws_file(str(ws), "escape_link", "worker content")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        entry = next((f for f in result["files"] if f["path"] == "escape_link"), None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["status"], "skipped")
        self.assertIn("symlink", entry["reason"])
        shutil.rmtree(outside_dir, ignore_errors=True)

    def test_summary_oversized_project_file_skipped(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        big = "x" * (64 * 1024 + 1)
        (self.root / "big.txt").write_text(big)
        self._write_ws_file(ws, "big.txt", "small")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        entry = next((f for f in result["files"] if f["path"] == "big.txt"), None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["status"], "skipped")
        self.assertIn("oversized", entry["reason"])

    def test_summary_skips_worker_binary_and_oversized_created_files(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        (ws / "binary.bin").write_bytes(b"\xff\xfe\x00")
        (ws / "huge.txt").write_text("x" * (64 * 1024 + 1), encoding="utf-8")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        by_path = {f["path"]: f for f in result["files"]}
        self.assertEqual(by_path["binary.bin"]["status"], "skipped")
        self.assertEqual(by_path["binary.bin"]["reason"], "worker_binary")
        self.assertEqual(by_path["huge.txt"]["status"], "skipped")
        self.assertEqual(by_path["huge.txt"]["reason"], "worker_oversized")

    def test_summary_skips_project_symlink_to_sensitive_file_without_leak(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        sentinel = "SECRET_PROJECT_SYMLINK_ENV_321"
        (self.root / ".env").write_text(sentinel, encoding="utf-8")
        (self.root / "safe_link").symlink_to(self.root / ".env")
        self._write_ws_file(lease["workspace_path"], "safe_link", "worker content")

        result = json.loads(self.registry.call(
            "summarize_worker_workspace_changes", worker_id="w1", task_id=task_id,
        ))

        serialized = json.dumps(result)
        entry = next((f for f in result["files"] if f["path"] == "safe_link"), None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["status"], "skipped")
        self.assertEqual(entry["reason"], "project_sensitive_path")
        self.assertNotIn(sentinel, serialized)

    # --- export_worker_workspace_patch ---

    def test_patch_export_created_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, "new.py", "new content\n")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id,
        ))

        self.assertEqual(result["count"], 1)
        p = result["patches"][0]
        self.assertEqual(p["path"], "new.py")
        self.assertEqual(p["status"], "created")
        self.assertTrue(p["has_changes"])
        self.assertIn("new content", p["patch"])
        self.assertIn("/dev/null", p["patch"])

    def test_patch_export_modified_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("app.py", "line1\nline2\nline3\n")
        self._write_ws_file(ws, "app.py", "line1\nline2_modified\nline3\n")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id,
        ))

        self.assertEqual(result["count"], 1)
        p = result["patches"][0]
        self.assertEqual(p["path"], "app.py")
        self.assertEqual(p["status"], "modified")
        self.assertIn("line2_modified", p["patch"])
        self.assertIn("-line2", p["patch"])

    def test_patch_export_same_file_excluded(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("app.py", "same content")
        self._write_ws_file(ws, "app.py", "same content")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id,
        ))

        self.assertEqual(result["count"], 0)

    def test_patch_export_single_path_no_change(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("app.py", "same content")
        self._write_ws_file(ws, "app.py", "same content")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id, path="app.py",
        ))

        self.assertEqual(result["path"], "app.py")
        self.assertEqual(result["status"], "same")
        self.assertFalse(result["has_changes"])

    def test_patch_export_single_path_created(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, "new.py", "new\n")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id, path="new.py",
        ))

        self.assertEqual(result["status"], "created")
        self.assertTrue(result["has_changes"])
        self.assertIn("new", result["patch"])

    def test_patch_export_max_files_bounded(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        for i in range(10):
            self._write_ws_file(ws, f"f{i}.py", f"content {i}\n")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id, max_files=3,
        ))

        self.assertEqual(result["count"], 3)

    def test_patch_export_context_lines(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        lines = "\n".join(f"line{i}" for i in range(20)) + "\n"
        self._write_project_file("big.py", lines)
        modified = lines.replace("line10", "line10_modified")
        self._write_ws_file(ws, "big.py", modified)

        result_default = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id, path="big.py",
        ))
        result_wide = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id, path="big.py", context_lines=10,
        ))

        self.assertTrue(len(result_wide["patch"]) >= len(result_default["patch"]))

    def test_patch_export_bad_context_lines_returns_error(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "f.txt", "x")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id, path="f.txt", context_lines="abc",
        ))

        self.assertIn("error", result)

    def test_patch_export_path_traversal_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id, path="../escape.py",
        ))

        self.assertIn("error", result)
        self.assertIn("workspace", result["error"])

    def test_patch_export_env_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id, path=".env",
        ))

        self.assertIn("error", result)
        self.assertIn("敏感", result["error"])

    def test_patch_export_skips_env_directory_component_without_leak(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        sentinel = "SECRET_PATCH_ENV_DIRECTORY_COMPONENT_123"
        (ws / ".env").mkdir()
        (ws / ".env" / "config").write_text(sentinel, encoding="utf-8")
        self._write_ws_file(str(ws), "app.py", "code\n")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id,
        ))

        serialized = json.dumps(result)
        paths = [p["path"] for p in result["patches"]]
        self.assertIn("app.py", paths)
        self.assertNotIn(".env/config", paths)
        self.assertNotIn(sentinel, serialized)

    def test_patch_export_unknown_worker_error(self):
        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w999", task_id="dtask_1",
        ))
        self.assertIn("error", result)

    def test_patch_export_no_lease_error(self):
        task_id = self._register_and_assign()

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)
        self.assertIn("lease", result["error"])

    def test_patch_export_offline_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="offline")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)
        self.assertIn("离线", result["error"])

    def test_patch_export_idle_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="idle", current_task_id=None)

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)
        self.assertIn("空闲", result["error"])

    def test_patch_export_no_goal_leak(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "f.py", "new\n")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id,
        ))

        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_patch_export_no_mutation(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("app.py", "original")
        self._write_ws_file(ws, "app.py", "modified")

        self.registry.call("export_worker_workspace_patch", worker_id="w1", task_id=task_id)

        self.assertEqual((self.root / "app.py").read_text(), "original")
        self.assertEqual((Path(ws) / "app.py").read_text(), "modified")
        worker = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(worker["status"], "assigned")

    def test_patch_export_returns_safe_metadata(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "f.txt", "data\n")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id,
        ))

        self.assertIn("lease_id", result)
        self.assertEqual(result["worker_id"], "w1")
        self.assertEqual(result["task_id"], task_id)
        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_patch_export_skips_project_symlink_escape(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        outside_dir = tempfile.mkdtemp()
        outside = Path(outside_dir) / "outside.txt"
        outside.write_text("outside")
        (self.root / "escape_link").symlink_to(outside)
        self._write_ws_file(str(ws), "escape_link", "worker content")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id,
        ))

        paths = [p["path"] for p in result["patches"]]
        self.assertNotIn("escape_link", paths)
        shutil.rmtree(outside_dir, ignore_errors=True)

    def test_patch_export_rejects_project_symlink_to_sensitive_file_without_leak(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        sentinel = "SECRET_PROJECT_PATCH_SYMLINK_ENV_654"
        (self.root / ".env").write_text(sentinel, encoding="utf-8")
        (self.root / "safe_link").symlink_to(self.root / ".env")
        self._write_ws_file(lease["workspace_path"], "safe_link", "worker content")

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id, path="safe_link",
        ))

        serialized = json.dumps(result)
        self.assertIn("error", result)
        self.assertIn("project_sensitive_path", result["error"])
        self.assertNotIn(sentinel, serialized)

    def test_patch_export_single_file_patch_size_is_bounded(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "big_created.txt", "x" * (64 * 1024))

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id, path="big_created.txt",
        ))

        self.assertIn("error", result)
        self.assertIn("patch 过大", result["error"])

    def test_patch_export_multi_file_total_patch_size_is_bounded(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, "large_a.txt", "a" * (40 * 1024))
        self._write_ws_file(ws, "large_b.txt", "b" * (40 * 1024))

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id,
        ))

        self.assertLessEqual(result["patch_bytes"], 64 * 1024)
        self.assertEqual(result["count"], 1)
        self.assertTrue(any(
            item["path"] == "large_b.txt" and item["reason"] == "patch_budget_exceeded"
            for item in result["skipped"]
        ))

    # --- compatibility ---

    def test_read_list_preview_write_still_work_after_summary_and_patch(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("app.py", "original")
        self._write_ws_file(ws, "app.py", "modified")
        self._write_ws_file(ws, "new.py", "new")

        # Run summary and patch export
        self.registry.call("summarize_worker_workspace_changes", worker_id="w1", task_id=task_id)
        self.registry.call("export_worker_workspace_patch", worker_id="w1", task_id=task_id)

        # Existing tools still work
        files = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id))
        self.assertIn("app.py", files["files"])
        self.assertIn("new.py", files["files"])

        content = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="app.py"))
        self.assertEqual(content["content"], "modified")

        preview = json.loads(self.registry.call("preview_worker_workspace_write", worker_id="w1", task_id=task_id, path="app.py", content="final"))
        self.assertIn("preview", preview)

        write_result = json.loads(self.registry.call(
            "write_worker_workspace_file", worker_id="w1", task_id=task_id, path="another.py", content="x",
        ))
        self.assertEqual(write_result["operation"], "write")

    def test_patch_export_bad_max_files_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "export_worker_workspace_patch", worker_id="w1", task_id=task_id, max_files="abc",
        ))

        self.assertIn("error", result)


class WorkspaceReviewGateTests(unittest.TestCase):
    """Tests for worker workspace review gate tools (TASK-072)."""

    SECRET_SENTINEL = "REVIEW_GATE_SECRET_999"

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

    def _register_and_assign(self, worker_id="w1", goal="task one"):
        self.registry.call("register_worker", worker_id=worker_id)
        task = json.loads(self.registry.call("create_durable_task", goal=goal, steps="step one"))
        self.registry.call("assign_durable_task", task_id=task["task_id"], worker_id=worker_id)
        self.registry.call("update_worker_status", worker_id=worker_id, status="assigned", current_task_id=task["task_id"])
        return task["task_id"]

    def _prepare_workspace(self, worker_id, task_id):
        return json.loads(self.registry.call("prepare_worker_workspace", worker_id=worker_id, task_id=task_id))

    # --- record_worker_workspace_review_gate ---

    def test_approved_gate_records_safe_metadata(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
        ))

        self.assertTrue(result["recorded"])
        self.assertEqual(result["decision"], "approved")
        self.assertEqual(result["reviewer"], "codex_pm")
        self.assertTrue(result["checks_passed"])
        self.assertTrue(result["patch_exported"])
        self.assertIn("event_id", result)
        self.assertIn("created_at", result)
        self.assertIn("lease_id", result)
        self.assertEqual(result["worker_id"], "w1")
        self.assertEqual(result["task_id"], task_id)

    def test_changes_requested_decision_accepted(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="changes_requested",
        ))

        self.assertTrue(result["recorded"])
        self.assertEqual(result["decision"], "changes_requested")

    def test_blocked_decision_accepted(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="blocked",
        ))

        self.assertTrue(result["recorded"])
        self.assertEqual(result["decision"], "blocked")

    def test_custom_reviewer_and_summary(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
            reviewer="human", summary="Looks good, all tests pass",
        ))

        self.assertEqual(result["reviewer"], "human")
        self.assertTrue(result["summary_present"])
        self.assertGreater(result["summary_length"], 0)

    def test_sensitive_reviewer_redacted_in_record_get_and_event(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        sensitive_reviewer = "OPENAI_API_KEY=reviewer_secret_123"

        result_str = self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
            reviewer=sensitive_reviewer,
        )
        result = json.loads(result_str)

        self.assertTrue(result["recorded"])
        self.assertEqual(result["reviewer"], "[redacted]")
        self.assertNotIn("reviewer_secret_123", result_str)

        get_str = self.registry.call(
            "get_worker_workspace_review_gate", worker_id="w1", task_id=task_id,
        )
        self.assertNotIn("reviewer_secret_123", get_str)

        events = json.loads(self.registry.call(
            "list_durable_events", task_id=task_id, event_type="review_gate_finished",
        ))
        self.assertNotIn("reviewer_secret_123", json.dumps(events))

    def test_summary_length_bounded_in_output(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        long_summary = "x" * 500

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
            summary=long_summary,
        ))

        self.assertTrue(result["summary_present"])
        self.assertEqual(result["summary_length"], 500)
        self.assertNotIn(long_summary, json.dumps(result))

    def test_checks_passed_false(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="changes_requested",
            checks_passed=False, patch_exported=False,
        ))

        self.assertFalse(result["checks_passed"])
        self.assertFalse(result["patch_exported"])

    def test_unknown_decision_rejected(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="maybe",
        ))

        self.assertIn("error", result)
        self.assertIn("decision", result["error"])

    def test_unknown_worker_error(self):
        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w999", task_id="dtask_1", decision="approved",
        ))
        self.assertIn("error", result)

    def test_no_lease_error(self):
        task_id = self._register_and_assign()

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
        ))
        self.assertIn("error", result)
        self.assertIn("lease", result["error"])

    def test_task_mismatch_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        task2 = json.loads(self.registry.call("create_durable_task", goal="other", steps="other"))

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task2["task_id"], decision="approved",
        ))
        self.assertIn("error", result)

    def test_offline_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="offline")

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
        ))
        self.assertIn("error", result)
        self.assertIn("离线", result["error"])

    def test_idle_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="idle", current_task_id=None)

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
        ))
        self.assertIn("error", result)
        self.assertIn("空闲", result["error"])

    def test_no_goal_leak_in_record(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
        ))

        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_no_summary_body_leak_in_record(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        sensitive_summary = "This contains secret: PASSWORD_ABC123"

        result = json.loads(self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
            summary=sensitive_summary,
        ))

        self.assertNotIn("PASSWORD_ABC123", json.dumps(result))
        self.assertTrue(result["summary_present"])
        self.assertEqual(result["summary_length"], len(sensitive_summary))

    def test_no_goal_leak_in_event_payload(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        self._prepare_workspace("w1", task_id)

        self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
        )

        events = json.loads(self.registry.call(
            "list_durable_events", task_id=task_id, event_type="review_gate_finished",
        ))
        for evt in events:
            self.assertNotIn(self.SECRET_SENTINEL, json.dumps(evt))

    def test_record_no_mutation(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        (ws / "f.txt").write_text("data")

        self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
        )

        # Project root unchanged
        self.assertFalse((self.root / "f.txt").exists())
        # Worker workspace unchanged
        self.assertEqual((ws / "f.txt").read_text(), "data")
        # Worker/task/lease state unchanged
        worker = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(worker["status"], "assigned")
        self.assertEqual(worker["current_task_id"], task_id)
        lease_info = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))
        self.assertEqual(lease_info["lease_id"], lease["lease_id"])

    def test_record_event_failure_bounded_error_no_mutation(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        (ws / "f.txt").write_text("data")

        original_record = self.registry.durable_event_store.record

        def broken_record(*args, **kwargs):
            raise RuntimeError("raw failure " + self.SECRET_SENTINEL)

        self.registry.durable_event_store.record = broken_record
        try:
            result = json.loads(self.registry.call(
                "record_worker_workspace_review_gate",
                worker_id="w1", task_id=task_id, decision="approved",
            ))
        finally:
            self.registry.durable_event_store.record = original_record

        self.assertIn("error", result)
        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))
        self.assertEqual((ws / "f.txt").read_text(), "data")
        worker = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(worker["status"], "assigned")
        lease_info = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))
        self.assertEqual(lease_info["lease_id"], lease["lease_id"])

    # --- get_worker_workspace_review_gate ---

    def test_get_gate_returns_no_gate_before_record(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "get_worker_workspace_review_gate", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["has_gate"])
        self.assertEqual(result["worker_id"], "w1")
        self.assertEqual(result["task_id"], task_id)

    def test_get_gate_returns_latest_after_record(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="changes_requested",
            summary="Fix the bugs",
        )
        self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
            summary="All fixed",
        )

        result = json.loads(self.registry.call(
            "get_worker_workspace_review_gate", worker_id="w1", task_id=task_id,
        ))

        self.assertTrue(result["has_gate"])
        self.assertEqual(result["decision"], "approved")
        self.assertTrue(result["summary_present"])
        self.assertGreater(result["summary_length"], 0)

    def test_get_gate_unknown_worker_error(self):
        result = json.loads(self.registry.call(
            "get_worker_workspace_review_gate", worker_id="w999", task_id="dtask_1",
        ))
        self.assertIn("error", result)

    def test_get_gate_no_lease_error(self):
        task_id = self._register_and_assign()

        result = json.loads(self.registry.call(
            "get_worker_workspace_review_gate", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)
        self.assertIn("lease", result["error"])

    def test_get_gate_offline_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="offline")

        result = json.loads(self.registry.call(
            "get_worker_workspace_review_gate", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)

    def test_get_gate_idle_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="idle", current_task_id=None)

        result = json.loads(self.registry.call(
            "get_worker_workspace_review_gate", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)

    def test_get_gate_no_goal_leak(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        self._prepare_workspace("w1", task_id)

        self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
        )

        result = json.loads(self.registry.call(
            "get_worker_workspace_review_gate", worker_id="w1", task_id=task_id,
        ))

        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_get_gate_query_failure_bounded_error(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        self._prepare_workspace("w1", task_id)
        original_list_events = self.registry.durable_event_store.list_events

        def broken_list_events(*args, **kwargs):
            raise RuntimeError("raw query failure " + self.SECRET_SENTINEL)

        self.registry.durable_event_store.list_events = broken_list_events
        try:
            result = json.loads(self.registry.call(
                "get_worker_workspace_review_gate", worker_id="w1", task_id=task_id,
            ))
        finally:
            self.registry.durable_event_store.list_events = original_list_events

        self.assertIn("error", result)
        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    # --- compatibility ---

    def test_existing_tools_still_work_after_gate(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        (Path(ws) / "app.py").write_text("code")
        (self.root / "app.py").write_text("original")

        # Record a gate
        self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision="approved",
        )

        # All existing tools still work
        files = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id))
        self.assertIn("app.py", files["files"])

        content = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="app.py"))
        self.assertEqual(content["content"], "code")

        preview = json.loads(self.registry.call("preview_worker_workspace_write", worker_id="w1", task_id=task_id, path="app.py", content="new"))
        self.assertIn("preview", preview)

        write_result = json.loads(self.registry.call(
            "write_worker_workspace_file", worker_id="w1", task_id=task_id, path="new.py", content="x",
        ))
        self.assertEqual(write_result["operation"], "write")

        summary = json.loads(self.registry.call("summarize_worker_workspace_changes", worker_id="w1", task_id=task_id))
        self.assertIn("files", summary)

        patch = json.loads(self.registry.call("export_worker_workspace_patch", worker_id="w1", task_id=task_id))
        self.assertIn("patches", patch)


class WorkspaceDryRunMergeTests(unittest.TestCase):
    """Tests for worker workspace dry-run merge tool (TASK-074)."""

    SECRET_SENTINEL = "DRYRUN_SECRET_456"

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

    def _register_and_assign(self, worker_id="w1", goal="task one"):
        self.registry.call("register_worker", worker_id=worker_id)
        task = json.loads(self.registry.call("create_durable_task", goal=goal, steps="step one"))
        self.registry.call("assign_durable_task", task_id=task["task_id"], worker_id=worker_id)
        self.registry.call("update_worker_status", worker_id=worker_id, status="assigned", current_task_id=task["task_id"])
        return task["task_id"]

    def _prepare_workspace(self, worker_id, task_id):
        return json.loads(self.registry.call("prepare_worker_workspace", worker_id=worker_id, task_id=task_id))

    def _write_project_file(self, rel_path, content):
        p = self.root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _write_ws_file(self, ws_path, rel_path, content):
        p = Path(ws_path) / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _record_gate(self, task_id, decision="approved", **kwargs):
        self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision=decision, **kwargs,
        )

    # --- ready cases ---

    def test_ready_with_approved_gate_and_created_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "new.py", "new\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertTrue(result["ready"])
        self.assertEqual(result["reasons"], [])
        self.assertTrue(result["has_review_gate"])
        self.assertEqual(result["decision"], "approved")
        self.assertFalse(result["requires_review"])
        self.assertEqual(result["created"], 1)
        self.assertGreater(result["patch_count"], 0)

    def test_ready_with_approved_gate_and_modified_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_project_file("app.py", "original\n")
        self._write_ws_file(lease["workspace_path"], "app.py", "modified\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertTrue(result["ready"])
        self.assertEqual(result["modified"], 1)
        self.assertGreater(result["patch_count"], 0)

    def test_ready_with_mixed_created_and_same(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_project_file("same.py", "same")
        self._write_ws_file(lease["workspace_path"], "same.py", "same")
        self._write_ws_file(lease["workspace_path"], "new.py", "new\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertTrue(result["ready"])
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["same"], 1)

    # --- not ready cases ---

    def test_not_ready_no_gate(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "new.py", "new\n")

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["ready"])
        self.assertTrue(result["requires_review"])
        self.assertFalse(result["has_review_gate"])
        self.assertIn("no_review_gate", result["reasons"])

    def test_not_ready_changes_requested(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "new.py", "new\n")
        self._record_gate(task_id, decision="changes_requested")

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["ready"])
        self.assertIn("gate_changes_requested", result["reasons"])
        self.assertEqual(result["decision"], "changes_requested")

    def test_not_ready_blocked(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "new.py", "new\n")
        self._record_gate(task_id, decision="blocked")

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["ready"])
        self.assertIn("gate_blocked", result["reasons"])

    def test_not_ready_no_changes(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_project_file("app.py", "same")
        self._write_ws_file(lease["workspace_path"], "app.py", "same")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["ready"])
        self.assertIn("no_changes", result["reasons"])
        self.assertEqual(result["patch_count"], 0)

    def test_not_ready_summary_has_skipped(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        # Create a file that will be skipped (oversized in project root)
        big = "x" * (64 * 1024 + 1)
        (self.root / "big.txt").write_text(big)
        self._write_ws_file(str(ws), "big.txt", "small")
        self._write_ws_file(str(ws), "good.py", "ok\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["ready"])
        self.assertIn("summary_has_skipped", result["reasons"])
        self.assertGreater(result["skipped_summary"], 0)

    def test_not_ready_patch_budget_exceeded(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, "large_a.txt", "a" * (40 * 1024))
        self._write_ws_file(ws, "large_b.txt", "b" * (40 * 1024))
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["ready"])
        self.assertIn("patch_export_has_skipped", result["reasons"])
        self.assertIn("patch_budget_exceeded", result["reasons"])
        self.assertGreater(result["skipped_patch_count"], 0)
        self.assertLessEqual(result["patch_bytes"], 64 * 1024)

    def test_not_ready_project_symlink_to_sensitive_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        sentinel = "DRYRUN_PROJECT_SYMLINK_SECRET"
        (self.root / ".env").write_text(sentinel, encoding="utf-8")
        (self.root / "safe_link").symlink_to(self.root / ".env")
        self._write_ws_file(lease["workspace_path"], "safe_link", "worker content")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["ready"])
        self.assertIn("summary_has_skipped", result["reasons"])
        self.assertIn("patch_export_has_skipped", result["reasons"])
        self.assertNotIn(sentinel, json.dumps(result))

    # --- validation errors ---

    def test_unknown_worker_error(self):
        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w999", task_id="dtask_1",
        ))
        self.assertIn("error", result)

    def test_no_lease_error(self):
        task_id = self._register_and_assign()

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)
        self.assertIn("lease", result["error"])

    def test_task_mismatch_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        task2 = json.loads(self.registry.call("create_durable_task", goal="other", steps="other"))

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task2["task_id"],
        ))
        self.assertIn("error", result)

    def test_offline_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="offline")

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)
        self.assertIn("离线", result["error"])

    def test_idle_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="idle", current_task_id=None)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)
        self.assertIn("空闲", result["error"])

    def test_bad_max_files_returns_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id, max_files="abc",
        ))
        self.assertIn("error", result)

    # --- safety ---

    def test_no_goal_leak(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "f.py", "new\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_no_raw_patch_leak(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_project_file("app.py", "old\n")
        self._write_ws_file(lease["workspace_path"], "app.py", "new\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        # Should not contain raw diff content
        self.assertNotIn("-old", json.dumps(result))
        self.assertNotIn("+new", json.dumps(result))

    def test_no_raw_file_content_leak(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        secret_content = "API_KEY=super_secret_value"
        self._write_ws_file(lease["workspace_path"], "config.py", secret_content)
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertNotIn(secret_content, json.dumps(result))

    def test_no_summary_body_leak(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "f.py", "new\n")
        self._record_gate(task_id, summary="Secret reviewer notes: HACKED")

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertNotIn("HACKED", json.dumps(result))

    def test_returns_safe_metadata(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "f.py", "new\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertIn("lease_id", result)
        self.assertEqual(result["worker_id"], "w1")
        self.assertEqual(result["task_id"], task_id)
        self.assertIn("ready", result)
        self.assertIn("reasons", result)
        self.assertIn("created", result)
        self.assertIn("modified", result)
        self.assertIn("same", result)
        self.assertIn("patch_count", result)
        self.assertIn("patch_bytes", result)
        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_no_mutation(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        self._write_project_file("app.py", "original")
        self._write_ws_file(str(ws), "app.py", "modified")
        self._record_gate(task_id)

        self.registry.call("dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id)

        # Project root unchanged
        self.assertEqual((self.root / "app.py").read_text(), "original")
        # Worker workspace unchanged
        self.assertEqual((ws / "app.py").read_text(), "modified")
        # Worker/task/lease state unchanged
        worker = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(worker["status"], "assigned")
        self.assertEqual(worker["current_task_id"], task_id)
        lease_info = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))
        self.assertEqual(lease_info["lease_id"], lease["lease_id"])

    # --- compatibility ---

    def test_existing_tools_still_work_after_dry_run(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        (Path(ws) / "app.py").write_text("code")
        (self.root / "app.py").write_text("original")
        self._record_gate(task_id)

        self.registry.call("dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id)

        # All existing tools still work
        files = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id))
        self.assertIn("app.py", files["files"])

        content = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="app.py"))
        self.assertEqual(content["content"], "code")

        preview = json.loads(self.registry.call("preview_worker_workspace_write", worker_id="w1", task_id=task_id, path="app.py", content="new"))
        self.assertIn("preview", preview)

        write = json.loads(self.registry.call("write_worker_workspace_file", worker_id="w1", task_id=task_id, path="new.py", content="x"))
        self.assertEqual(write["operation"], "write")

        summary = json.loads(self.registry.call("summarize_worker_workspace_changes", worker_id="w1", task_id=task_id))
        self.assertIn("files", summary)

        patch = json.loads(self.registry.call("export_worker_workspace_patch", worker_id="w1", task_id=task_id))
        self.assertIn("patches", patch)

        gate = json.loads(self.registry.call("get_worker_workspace_review_gate", worker_id="w1", task_id=task_id))
        self.assertTrue(gate["has_gate"])

        self.registry.call("register_worker", worker_id="w_claim")
        claim_task = json.loads(self.registry.call("create_durable_task", goal="claim", steps="s"))
        claim = json.loads(self.registry.call("claim_durable_task", worker_id="w_claim"))
        self.assertEqual(claim["task_id"], claim_task["task_id"])

        self.registry.call("register_worker", worker_id="w_dispatch")
        self.registry.call("create_durable_task", goal="dispatch", steps="s")
        dispatch = json.loads(self.registry.call("dispatch_durable_tasks"))
        self.assertIn("dispatched", dispatch)


class WorkspaceApplyMergeTests(unittest.TestCase):
    """Tests for apply_reviewed_worker_workspace_merge (TASK-076)."""

    SECRET_SENTINEL = "APPLY_MERGE_SECRET_789"

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

    def _register_and_assign(self, worker_id="w1", goal="task one"):
        self.registry.call("register_worker", worker_id=worker_id)
        task = json.loads(self.registry.call("create_durable_task", goal=goal, steps="step one"))
        self.registry.call("assign_durable_task", task_id=task["task_id"], worker_id=worker_id)
        self.registry.call("update_worker_status", worker_id=worker_id, status="assigned", current_task_id=task["task_id"])
        return task["task_id"]

    def _prepare_workspace(self, worker_id, task_id):
        return json.loads(self.registry.call("prepare_worker_workspace", worker_id=worker_id, task_id=task_id))

    def _write_project_file(self, rel_path, content):
        p = self.root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _write_ws_file(self, ws_path, rel_path, content):
        p = Path(ws_path) / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _record_gate(self, task_id, decision="approved", **kwargs):
        self.registry.call(
            "record_worker_workspace_review_gate",
            worker_id="w1", task_id=task_id, decision=decision, **kwargs,
        )

    # --- apply happy paths ---

    def test_apply_created_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, "new.py", "new content\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertTrue(result["applied"])
        self.assertEqual(result["created_count"], 1)
        self.assertEqual(result["applied_count"], 1)
        self.assertEqual((self.root / "new.py").read_text(), "new content\n")

    def test_apply_modified_file(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("app.py", "original\n")
        self._write_ws_file(ws, "app.py", "modified\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertTrue(result["applied"])
        self.assertEqual(result["modified_count"], 1)
        self.assertEqual((self.root / "app.py").read_text(), "modified\n")

    def test_apply_mixed_created_and_modified(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("existing.py", "old\n")
        self._write_ws_file(ws, "existing.py", "updated\n")
        self._write_ws_file(ws, "brand_new.py", "brand new\n")
        self._write_project_file("same.py", "same")
        self._write_ws_file(ws, "same.py", "same")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertTrue(result["applied"])
        self.assertEqual(result["created_count"], 1)
        self.assertEqual(result["modified_count"], 1)
        self.assertEqual(result["applied_count"], 2)
        self.assertEqual((self.root / "existing.py").read_text(), "updated\n")
        self.assertEqual((self.root / "brand_new.py").read_text(), "brand new\n")
        # Same file should not be touched
        self.assertEqual((self.root / "same.py").read_text(), "same")

    def test_apply_creates_parent_dirs(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, "a/b/c/deep.py", "deep\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertTrue(result["applied"])
        self.assertEqual((self.root / "a/b/c/deep.py").read_text(), "deep\n")

    # --- reject cases ---

    def test_reject_no_gate(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "new.py", "new\n")

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["applied"])
        self.assertIn("no_review_gate", result["reasons"])

    def test_reject_changes_requested(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "new.py", "new\n")
        self._record_gate(task_id, decision="changes_requested")

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["applied"])
        self.assertIn("gate_changes_requested", result["reasons"])

    def test_reject_blocked(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "new.py", "new\n")
        self._record_gate(task_id, decision="blocked")

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["applied"])
        self.assertIn("gate_blocked", result["reasons"])

    def test_reject_no_changes(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_project_file("app.py", "same")
        self._write_ws_file(lease["workspace_path"], "app.py", "same")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["applied"])
        self.assertIn("no_changes", result["reasons"])

    def test_reject_summary_has_skipped(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        big = "x" * (64 * 1024 + 1)
        (self.root / "big.txt").write_text(big)
        self._write_ws_file(str(ws), "big.txt", "small")
        self._write_ws_file(str(ws), "good.py", "ok\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["applied"])
        self.assertIn("summary_has_skipped", result["reasons"])

    def test_reject_patch_budget_exceeded(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, "large_a.txt", "a" * (40 * 1024))
        self._write_ws_file(ws, "large_b.txt", "b" * (40 * 1024))
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["applied"])
        self.assertIn("patch_export_has_skipped", result["reasons"])
        self.assertIn("patch_budget_exceeded", result["reasons"])
        self.assertFalse((self.root / "large_a.txt").exists())
        self.assertFalse((self.root / "large_b.txt").exists())

    def test_reject_project_symlink_to_sensitive_file_without_leak(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        sentinel = "APPLY_PROJECT_SYMLINK_SECRET"
        (self.root / ".env").write_text(sentinel, encoding="utf-8")
        (self.root / "safe_link").symlink_to(self.root / ".env")
        self._write_ws_file(lease["workspace_path"], "safe_link", "worker content")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        serialized = json.dumps(result)
        self.assertFalse(result["applied"])
        self.assertIn("summary_has_skipped", result["reasons"])
        self.assertNotIn(sentinel, serialized)

    def test_reject_worker_binary_and_oversized(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = Path(lease["workspace_path"])
        (ws / "binary.bin").write_bytes(b"\xff\xfe\x00")
        (ws / "huge.txt").write_text("x" * (64 * 1024 + 1), encoding="utf-8")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertFalse(result["applied"])
        self.assertIn("summary_has_skipped", result["reasons"])
        self.assertFalse((self.root / "binary.bin").exists())
        self.assertFalse((self.root / "huge.txt").exists())

    # --- validation errors ---

    def test_unknown_worker_error(self):
        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w999", task_id="dtask_1",
        ))
        self.assertIn("error", result)

    def test_no_lease_error(self):
        task_id = self._register_and_assign()

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)

    def test_task_mismatch_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        task2 = json.loads(self.registry.call("create_durable_task", goal="other", steps="other"))

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task2["task_id"],
        ))
        self.assertIn("error", result)

    def test_offline_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="offline")

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)

    def test_idle_worker_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)
        self.registry.call("update_worker_status", worker_id="w1", status="idle", current_task_id=None)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))
        self.assertIn("error", result)

    def test_bad_max_files_error(self):
        task_id = self._register_and_assign()
        self._prepare_workspace("w1", task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id, max_files="abc",
        ))
        self.assertIn("error", result)

    # --- safety ---

    def test_no_goal_leak(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "f.py", "new\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_no_reviewer_summary_shell_env_request_leak(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        review_secret = "APPLY_REVIEW_SUMMARY_SECRET"
        shell_secret = "APPLY_SHELL_OUTPUT_SECRET"
        request_secret = "APPLY_REQUEST_STRING_SECRET"
        env_secret = "APPLY_ENV_SECRET=abc123"
        self._write_ws_file(lease["workspace_path"], "f.py", "new\n")
        self._record_gate(
            task_id,
            summary=f"{review_secret}\n{shell_secret}\n{request_secret}\n{env_secret}",
        )

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        serialized = json.dumps(result)
        self.assertNotIn(review_secret, serialized)
        self.assertNotIn(shell_secret, serialized)
        self.assertNotIn(request_secret, serialized)
        self.assertNotIn(env_secret, serialized)

    def test_no_raw_content_leak(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        secret = "API_KEY=super_secret_12345"
        self._write_ws_file(lease["workspace_path"], "config.py", secret)
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        # The raw content should not appear in the result JSON
        serialized = json.dumps(result)
        self.assertNotIn(secret, serialized)
        self.assertNotIn("--- ", serialized)
        self.assertNotIn("+++ ", serialized)
        self.assertNotIn("@@ ", serialized)

    def test_write_failure_error_is_bounded(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "config.py", "safe content")
        self._record_gate(task_id)
        raw_error = "RAW_DISK_SECRET_SHOULD_NOT_LEAK"

        original_write_text = Path.write_text

        def failing_write_text(self_path, data, encoding="utf-8"):
            if self_path.name == "config.py":
                raise OSError(raw_error)
            return original_write_text(self_path, data, encoding=encoding)

        with patch.object(Path, "write_text", failing_write_text):
            result = json.loads(self.registry.call(
                "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
            ))

        serialized = json.dumps(result)
        self.assertFalse(result["applied"])
        self.assertEqual(result["error"], "project_write_failed")
        self.assertIn("project_write_failed", result["reasons"])
        self.assertNotIn(raw_error, serialized)

    def test_returns_safe_metadata(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "f.py", "new\n")
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertIn("lease_id", result)
        self.assertEqual(result["worker_id"], "w1")
        self.assertEqual(result["task_id"], task_id)
        self.assertIn("applied", result)
        self.assertIn("applied_count", result)
        self.assertIn("created_count", result)
        self.assertIn("modified_count", result)
        self.assertIn("files", result)
        self.assertNotIn(self.SECRET_SENTINEL, json.dumps(result))

    def test_apply_event_safe_metadata(self):
        task_id = self._register_and_assign(goal=self.SECRET_SENTINEL)
        lease = self._prepare_workspace("w1", task_id)
        secret = "APPLY_EVENT_FILE_SECRET"
        self._write_ws_file(lease["workspace_path"], "f.py", secret)
        self._record_gate(task_id)

        result = json.loads(self.registry.call(
            "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
        ))

        self.assertTrue(result["applied"])
        events = self.registry.durable_event_store.list_events(
            task_id=task_id, event_type=FILE_EDIT_FINISHED, max_results=20,
        )
        merge_events = [event for event in events if event.source == "workspace_merge"]
        self.assertEqual(len(merge_events), 1)
        serialized = json.dumps({
            "summary": merge_events[0].summary,
            "payload": merge_events[0].payload,
        })
        self.assertIn("workspace_merge_apply", serialized)
        self.assertNotIn(self.SECRET_SENTINEL, serialized)
        self.assertNotIn(secret, serialized)

    def test_no_deletion(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("keep.py", "keep me")
        self._write_ws_file(ws, "new.py", "new\n")
        self._record_gate(task_id)

        self.registry.call("apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id)

        # Original file should still exist
        self.assertEqual((self.root / "keep.py").read_text(), "keep me")

    # --- rollback ---

    def test_rollback_removes_created_file_on_later_failure(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, "good.py", "good\n")
        self._write_ws_file(ws, "a/b/ok.py", "ok\n")
        self._record_gate(task_id)

        # Inject a write failure after the first file succeeds
        original_write_text = Path.write_text
        call_count = [0]
        def failing_write_text(self_path, data, encoding="utf-8"):
            call_count[0] += 1
            if call_count[0] > 1:
                raise OSError("disk full")
            return original_write_text(self_path, data, encoding=encoding)

        with patch.object(Path, "write_text", failing_write_text):
            result = json.loads(self.registry.call(
                "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
            ))

        self.assertFalse(result["applied"])
        self.assertEqual(result["rollback"], "ok")
        # Created files should be rolled back
        self.assertFalse((self.root / "good.py").exists())
        self.assertFalse((self.root / "a/b/ok.py").exists())

    def test_rollback_restores_modified_file_on_failure(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("existing.py", "original\n")
        self._write_ws_file(ws, "existing.py", "modified\n")
        self._write_ws_file(ws, "will_fail.py", "fail\n")
        self._record_gate(task_id)

        # Make writes to will_fail.py fail, but allow rollback writes
        original_write_text = Path.write_text
        def failing_write_text(self_path, data, encoding="utf-8"):
            if self_path.name == "will_fail.py" and not self_path.parent.name == "existing.py":
                raise OSError("disk full")
            return original_write_text(self_path, data, encoding=encoding)

        with patch.object(Path, "write_text", failing_write_text):
            result = json.loads(self.registry.call(
                "apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id,
            ))

        self.assertFalse(result["applied"])
        # Modified file should be restored to original
        self.assertEqual((self.root / "existing.py").read_text(), "original\n")

    # --- worker/workspace/task/lease state unchanged ---

    def test_apply_no_state_mutation(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_ws_file(ws, "new.py", "new\n")
        self._record_gate(task_id)

        self.registry.call("apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id)

        worker = json.loads(self.registry.call("get_worker", worker_id="w1"))
        self.assertEqual(worker["status"], "assigned")
        self.assertEqual(worker["current_task_id"], task_id)
        lease_info = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))
        self.assertEqual(lease_info["lease_id"], lease["lease_id"])
        # Worker workspace file still exists
        self.assertEqual((Path(ws) / "new.py").read_text(), "new\n")

    def test_apply_review_gate_unchanged(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        self._write_ws_file(lease["workspace_path"], "f.py", "new\n")
        self._record_gate(task_id)

        self.registry.call("apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id)

        gate = json.loads(self.registry.call("get_worker_workspace_review_gate", worker_id="w1", task_id=task_id))
        self.assertTrue(gate["has_gate"])
        self.assertEqual(gate["decision"], "approved")

    # --- compatibility ---

    def test_existing_tools_still_work_after_apply(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("app.py", "original\n")
        self._write_ws_file(ws, "app.py", "modified\n")
        self._write_ws_file(ws, "new.py", "new\n")
        self._record_gate(task_id)

        self.registry.call("apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id)

        # Dry-run still works
        dry = json.loads(self.registry.call("dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id))
        self.assertIn("ready", dry)

        # Summary still works
        summary = json.loads(self.registry.call("summarize_worker_workspace_changes", worker_id="w1", task_id=task_id))
        self.assertIn("files", summary)

        # Patch export still works
        patch = json.loads(self.registry.call("export_worker_workspace_patch", worker_id="w1", task_id=task_id))
        self.assertIn("patches", patch)

        # Review gate still works
        gate = json.loads(self.registry.call("get_worker_workspace_review_gate", worker_id="w1", task_id=task_id))
        self.assertTrue(gate["has_gate"])

        # Read/list/write still work
        files = json.loads(self.registry.call("list_worker_workspace_files", worker_id="w1", task_id=task_id))
        self.assertIn("app.py", files["files"])

        content = json.loads(self.registry.call("read_worker_workspace_file", worker_id="w1", task_id=task_id, path="app.py"))
        self.assertEqual(content["content"], "modified\n")

        lease_info = json.loads(self.registry.call("get_worker_workspace", worker_id="w1", task_id=task_id))
        self.assertEqual(lease_info["lease_id"], lease["lease_id"])

        valid = json.loads(self.registry.call(
            "validate_worker_workspace_path", worker_id="w1", task_id=task_id, path=str(Path(ws) / "app.py"),
        ))
        self.assertTrue(valid["valid"])

        preview = json.loads(self.registry.call(
            "preview_worker_workspace_write", worker_id="w1", task_id=task_id, path="app.py", content="again\n",
        ))
        self.assertIn("preview", preview)

        write = json.loads(self.registry.call(
            "write_worker_workspace_file", worker_id="w1", task_id=task_id, path="after_apply.py", content="ok\n",
        ))
        self.assertEqual(write["operation"], "write")

        self.registry.call("register_worker", worker_id="w_claim")
        claim_task = json.loads(self.registry.call("create_durable_task", goal="claim", steps="s"))
        claim = json.loads(self.registry.call("claim_durable_task", worker_id="w_claim"))
        self.assertEqual(claim["task_id"], claim_task["task_id"])

        self.registry.call("register_worker", worker_id="w_dispatch")
        self.registry.call("create_durable_task", goal="dispatch", steps="s")
        dispatch = json.loads(self.registry.call("dispatch_durable_tasks"))
        self.assertIn("dispatched", dispatch)

    def test_apply_idempotent_dry_run_after_apply(self):
        task_id = self._register_and_assign()
        lease = self._prepare_workspace("w1", task_id)
        ws = lease["workspace_path"]
        self._write_project_file("app.py", "original\n")
        self._write_ws_file(ws, "app.py", "modified\n")
        self._record_gate(task_id)

        self.registry.call("apply_reviewed_worker_workspace_merge", worker_id="w1", task_id=task_id)

        # After apply, dry-run should show no_changes (project now matches worker)
        dry = json.loads(self.registry.call("dry_run_worker_workspace_merge", worker_id="w1", task_id=task_id))
        self.assertFalse(dry["ready"])
        self.assertIn("no_changes", dry["reasons"])


if __name__ == "__main__":
    unittest.main()
