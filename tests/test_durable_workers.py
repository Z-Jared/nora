"""Tests for durable worker registry (TASK-030)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mini_agent.database import NoraDB
from mini_agent.durable_workers import DurableWorkerStore, DurableWorker, WorkerStatus
from mini_agent.tools import build_default_registry
from mini_agent.durable_events import DurableEventStore, TASK_STATUS_CHANGED


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


if __name__ == "__main__":
    unittest.main()
