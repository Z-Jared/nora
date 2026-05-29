import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.controller import MiniAgent
from mini_agent.database import NoraDB
from mini_agent.durable_events import (
    CHECKPOINT_ADDED,
    DurableEvent,
    DurableEventStore,
    STEP_UPDATED,
    TASK_CREATED,
    TASK_FINISHED,
    TASK_STATUS_CHANGED,
    TRACE_LINKED,
)
from mini_agent.task_runner import TaskManager
from mini_agent.tools import build_default_registry
from mini_agent.traces import TraceStore


class DurableEventStoreTests(unittest.TestCase):
    def test_sqlite_record_list_get_and_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableEventStore(db=db)
                first = store.record(TASK_CREATED, task_id="dtask_1", summary="one")
                second = store.record(STEP_UPDATED, task_id="dtask_2", summary="two")

                self.assertEqual(first.event_id, "devt_1")
                self.assertEqual(second.event_id, "devt_2")
                self.assertEqual(store.get_event("devt_1").summary, "one")
                self.assertEqual([event.event_id for event in store.list_events()], ["devt_2", "devt_1"])
                self.assertEqual([event.event_id for event in store.list_events(task_id="dtask_1")], ["devt_1"])
            finally:
                db.close()

    def test_jsonl_record_list_get_and_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "events.jsonl"
            store = DurableEventStore(path=path)
            store.record(TASK_CREATED, task_id="dtask_1", summary="one")
            store.record(STEP_UPDATED, task_id="dtask_2", summary="two")

            self.assertEqual(store.get_event("devt_2").summary, "two")
            self.assertEqual([event.event_id for event in store.list_events(max_results=1)], ["devt_2"])
            self.assertEqual([event.event_id for event in store.list_events(task_id="dtask_1")], ["devt_1"])

    def test_dataclass_round_trip(self):
        event = DurableEvent(
            event_id="devt_1",
            task_id="dtask_1",
            event_type=TRACE_LINKED,
            created_at="2026-05-29T00:00:00Z",
            summary="linked",
            payload={"k": "v"},
            trace_id="trace_1",
            checkpoint_id="cp_1",
            worker_id="worker_1",
            source="test",
        )

        restored = DurableEvent.from_dict(event.to_dict())

        self.assertEqual(restored.event_id, "devt_1")
        self.assertEqual(restored.trace_id, "trace_1")
        self.assertEqual(restored.checkpoint_id, "cp_1")
        self.assertEqual(restored.worker_id, "worker_1")
        self.assertEqual(restored.payload, {"k": "v"})


class TaskManagerDurableEventTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.registry = build_default_registry(db=self.db, workspace_root=self.root)
        self.task_manager = self.registry.task_manager
        self.event_store = self.registry.durable_event_store

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_start_records_task_created_event(self):
        self.task_manager.start("build feature", "step one\nstep two")

        events = self.event_store.list_events()

        self.assertEqual(events[0].event_type, TASK_CREATED)
        self.assertEqual(events[0].task_id, "dtask_shadow_1")
        self.assertEqual(events[0].payload["step_count"], 2)

    def test_run_once_records_step_and_checkpoint_events(self):
        self.task_manager.start("build feature", "step one")
        self.task_manager.run_once()

        events = self.event_store.list_events()
        event_types = [event.event_type for event in events]

        self.assertIn(STEP_UPDATED, event_types)
        self.assertIn(CHECKPOINT_ADDED, event_types)
        checkpoint_event = next(event for event in events if event.event_type == CHECKPOINT_ADDED)
        self.assertEqual(checkpoint_event.task_id, "dtask_shadow_1")
        self.assertTrue(checkpoint_event.checkpoint_id.startswith("cp_"))

    def test_update_step_records_step_and_checkpoint_events(self):
        self.task_manager.start("build feature", "step one")
        self.task_manager.run_once()
        self.task_manager.update_step(1, "done", summary="finished")

        events = self.event_store.list_events()
        done_events = [
            event for event in events
            if event.event_type == STEP_UPDATED and event.payload.get("status") == "done"
        ]

        self.assertEqual(len(done_events), 1)
        self.assertTrue(done_events[0].checkpoint_id.startswith("cp_"))

    def test_finish_records_task_finished_event(self):
        self.task_manager.start("build feature", "step one")
        self.task_manager.finish("done")

        events = self.event_store.list_events()
        finish_event = next(event for event in events if event.event_type == TASK_FINISHED)

        self.assertEqual(finish_event.task_id, "dtask_shadow_1")
        self.assertEqual(finish_event.payload["summary"], "done")

    def test_restore_records_task_status_changed_event(self):
        self.task_manager.start("build feature", "step one")
        self.task_manager.finish("done")
        self.task_manager.restore("task_1")

        events = self.event_store.list_events()
        restore_event = next(event for event in events if event.event_type == TASK_STATUS_CHANGED)

        self.assertEqual(restore_event.payload["restored_from"], "task_1")

    def test_event_write_failure_does_not_break_task_flow(self):
        class BrokenEventStore:
            def record(self, **_kwargs):
                raise RuntimeError("disk full")

        manager = TaskManager(
            path=self.root / "task.json",
            history_path=self.root / "history.jsonl",
            db=None,
            event_store=BrokenEventStore(),
        )

        self.assertIn("已创建任务", manager.start("goal", "step one"))
        self.assertIn("已更新步骤", manager.update_step(1, "done", summary="ok"))
        self.assertIn("已完成任务", manager.finish("done"))


class MiniAgentDurableEventTests(unittest.TestCase):
    def test_trace_link_records_durable_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db = NoraDB(root / "test.db")
            try:
                registry = build_default_registry(db=db, workspace_root=root)
                registry.task_manager.start("build feature", "step one")
                agent = MiniAgent(
                    registry,
                    trace_store=TraceStore(db=db),
                    event_store=registry.durable_event_store,
                )
                agent.durable_task_store = registry.durable_task_store

                list(agent.run_events("hello"))

                events = registry.durable_event_store.list_events()
                trace_event = next(event for event in events if event.event_type == TRACE_LINKED)
                task = registry.durable_task_store.get_task("dtask_shadow_1")
                self.assertEqual(trace_event.task_id, "dtask_shadow_1")
                self.assertEqual(trace_event.trace_id, task.trace_refs[-1])
            finally:
                db.close()


class RegistryDurableEventToolTests(unittest.TestCase):
    def test_registry_tools_list_and_get_durable_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = build_default_registry(db=db, workspace_root=Path(tmpdir))
                registry.durable_event_store.record(TASK_CREATED, task_id="dtask_1", summary="created")

                listed = json.loads(registry.call("list_durable_events", task_id="dtask_1"))
                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["event_type"], TASK_CREATED)

                detail = json.loads(registry.call("get_durable_event", event_id=listed[0]["event_id"]))
                self.assertEqual(detail["summary"], "created")
            finally:
                db.close()

    def test_registry_tools_report_missing_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                registry = build_default_registry(db=db, workspace_root=Path(tmpdir))
                detail = json.loads(registry.call("get_durable_event", event_id="devt_999"))
                self.assertIn("error", detail)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
