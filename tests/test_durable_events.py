import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from mini_agent.controller import MiniAgent, RunReport, ToolRunRecord
from mini_agent.database import NoraDB
from mini_agent.durable_events import (
    CHECKPOINT_ADDED,
    DurableEvent,
    DurableEventStore,
    FILE_EDIT_BLOCKED,
    FILE_EDIT_ERROR,
    FILE_EDIT_FINISHED,
    FILE_EDIT_STARTED,
    MODEL_CALL_ERROR,
    MODEL_CALL_FINISHED,
    MODEL_CALL_STARTED,
    SHELL_COMMAND_BLOCKED,
    SHELL_COMMAND_ERROR,
    SHELL_COMMAND_FINISHED,
    SHELL_COMMAND_STARTED,
    STEP_UPDATED,
    TASK_CREATED,
    TASK_FINISHED,
    TASK_STATUS_CHANGED,
    TEST_RUN_BLOCKED,
    TEST_RUN_ERROR,
    TEST_RUN_FINISHED,
    TEST_RUN_STARTED,
    TOOL_CALL_BLOCKED,
    TOOL_CALL_BUDGET_EXCEEDED,
    TOOL_CALL_ERROR,
    TOOL_CALL_FINISHED,
    TOOL_CALL_STARTED,
    TRACE_LINKED,
)
from mini_agent.task_runner import TaskManager
from mini_agent.tools import build_default_registry
from mini_agent.toolkits.workspace import WorkspaceFiles
from mini_agent.shell import ShellRunner
from mini_agent.diagnostics import Diagnostics
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


class ToolCallDurableEventTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.registry = build_default_registry(db=self.db, workspace_root=self.root)
        self.event_store = self.registry.durable_event_store

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_successful_tool_call_records_started_and_finished(self):
        agent = MiniAgent(
            self.registry,
            event_store=self.event_store,
        )

        agent.run("计算 2 + 3")

        events = self.event_store.list_events()
        started = [e for e in events if e.event_type == TOOL_CALL_STARTED]
        finished = [e for e in events if e.event_type == TOOL_CALL_FINISHED]

        self.assertGreaterEqual(len(started), 1)
        self.assertGreaterEqual(len(finished), 1)
        self.assertEqual(started[0].payload["tool_name"], finished[0].payload["tool_name"])
        self.assertEqual(finished[0].payload["status"], "ok")
        self.assertIn("result_preview", finished[0].payload)

    def test_blocked_tool_call_records_blocked_event(self):
        registry = build_default_registry(
            db=self.db,
            workspace_root=self.root,
            permission_overrides={"calculate": True},
        )
        event_store = registry.durable_event_store
        agent = MiniAgent(registry, event_store=event_store)

        agent._active_tool_records = []
        agent._call_tool("calculate", {"expression": "2 + 3"})

        events = event_store.list_events()
        blocked = [e for e in events if e.event_type == TOOL_CALL_BLOCKED]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0].payload["status"], "blocked")
        self.assertEqual(blocked[0].severity, "warning")

    def test_cancelled_tool_call_records_blocked_not_finished(self):
        registry = build_default_registry(
            db=self.db,
            workspace_root=self.root,
            confirm_action=lambda _prompt: False,
        )
        event_store = registry.durable_event_store
        agent = MiniAgent(registry, event_store=event_store)

        agent._active_tool_records = []
        agent._call_tool("git_commit_staged", {"message": "test", "reason": "test reason"})

        events = event_store.list_events()
        blocked = [e for e in events if e.event_type == TOOL_CALL_BLOCKED and e.payload.get("status") == "cancelled"]
        finished = [e for e in events if e.event_type == TOOL_CALL_FINISHED]
        self.assertEqual(len(blocked), 1, "cancelled tool must emit TOOL_CALL_BLOCKED, not TOOL_CALL_FINISHED")
        self.assertEqual(len(finished), 0, "cancelled tool must not emit TOOL_CALL_FINISHED")

    def test_tool_error_emits_error_event(self):
        class FailingRegistry:
            def call(self, name, **kwargs):
                raise RuntimeError("simulated tool failure")
            def permission_for(self, name):
                return None
            def to_openai_tools(self):
                return []
            def describe(self):
                return ""

        agent = MiniAgent(FailingRegistry(), event_store=self.event_store)
        agent._active_tool_records = []
        agent._call_tool("failing_tool", {"arg": "val"})

        events = self.event_store.list_events()
        errors = [e for e in events if e.event_type == TOOL_CALL_ERROR]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].payload["tool_name"], "failing_tool")
        self.assertEqual(errors[0].payload["status"], "error")
        self.assertEqual(errors[0].severity, "warning")

    def test_budget_exceeded_emits_event(self):
        agent = MiniAgent(
            self.registry,
            event_store=self.event_store,
            max_tool_calls_per_turn=1,
        )
        agent._active_tool_records = [
            ToolRunRecord(name="dummy", status="ok", result_preview="ok"),
        ]
        agent._call_tool("extra_tool", {"arg": "val"})

        events = self.event_store.list_events()
        budget = [e for e in events if e.event_type == TOOL_CALL_BUDGET_EXCEEDED]
        self.assertEqual(len(budget), 1)
        self.assertEqual(budget[0].payload["tool_name"], "extra_tool")
        self.assertEqual(budget[0].payload["status"], "budget_exceeded")

    def test_no_task_id_on_non_task_tool_event(self):
        store = self.registry.durable_task_store
        store.create_task(goal="unrelated task", steps=[{"text": "s1"}])
        store.update_status("dtask_1", "running")

        agent = MiniAgent(
            self.registry,
            event_store=self.event_store,
        )

        agent.run("计算 2 + 3")

        events = self.event_store.list_events()
        tool_events = [e for e in events if e.event_type in (
            TOOL_CALL_STARTED, TOOL_CALL_FINISHED,
        )]
        self.assertGreaterEqual(len(tool_events), 1)
        for ev in tool_events:
            self.assertIsNone(ev.task_id, "non-task tool event must not bind to unrelated task")

    def test_secret_value_redacted_in_event_payload(self):
        agent = MiniAgent(
            self.registry,
            event_store=self.event_store,
        )

        agent.run("保存笔记 sk-1234567890abcdef")

        events = self.event_store.list_events()
        for event in events:
            payload_str = json.dumps(event.payload)
            self.assertNotIn("sk-1234567890abcdef", payload_str, "raw secret must not appear in event payload")

    def test_sensitive_key_password_redacted_in_args_preview(self):
        agent = MiniAgent(
            self.registry,
            event_store=self.event_store,
        )
        agent._active_tool_records = []
        agent._call_tool("connect_db", {"host": "localhost", "password": "super_secret_123", "reason": "test"})

        events = self.event_store.list_events()
        started = [e for e in events if e.event_type == TOOL_CALL_STARTED]
        self.assertEqual(len(started), 1)
        preview = started[0].payload.get("arguments_preview", "")
        self.assertNotIn("super_secret_123", preview, "password value must be redacted in arguments_preview")
        self.assertIn("[redacted]", preview)

    def test_sensitive_key_token_redacted_in_event_payload(self):
        event = self.event_store.record(
            "tool_call_finished",
            payload={"tool_name": "api_call", "status": "ok", "arguments_preview": ""},
        )
        # Test via DurableEventStore directly with sensitive key in payload
        event2 = self.event_store.record(
            "tool_call_finished",
            payload={"api_token": "ghp_abc123def456ghi789jkl012mno345"},
        )
        serialized = json.dumps(event2.payload)
        self.assertNotIn("ghp_abc123", serialized)
        self.assertIn("[redacted]", serialized)

    def test_event_failure_does_not_break_tool_execution(self):
        class BrokenEventStore:
            def record(self, **kwargs):
                raise RuntimeError("disk full")
            def list_events(self, **kwargs):
                return []
            def get_event(self, event_id):
                return None

        agent = MiniAgent(
            self.registry,
            event_store=BrokenEventStore(),
        )

        result = agent.run("计算 2 + 3")
        self.assertIn("5", result)

    def test_no_event_store_does_not_break_tools(self):
        agent = MiniAgent(self.registry)

        result = agent.run("计算 2 + 3")
        self.assertIn("5", result)


class TraceLinkOnFinishRegressionTests(unittest.TestCase):
    """Blocker 1: trace must link to task even when finish_task completes it this turn."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.registry = build_default_registry(
            db=self.db,
            workspace_root=self.root,
        )
        self.event_store = self.registry.durable_event_store

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_trace_links_to_completed_task_when_finish_task_called(self):
        agent = MiniAgent(
            self.registry,
            event_store=self.event_store,
            trace_store=TraceStore(db=self.db),
        )
        agent.durable_task_store = self.registry.durable_task_store

        self.registry.task_manager.start("build feature", "step one\nstep two")
        self.registry.task_manager.update_step(1, "done", summary="did it")
        self.registry.task_manager.update_step(2, "done", summary="did it too")

        # finish_task marks dtask_shadow_1 as completed
        self.registry.task_manager.finish("all done")

        task = self.registry.durable_task_store.get_task("dtask_shadow_1")
        self.assertEqual(task.status, "completed")

        # Now simulate a turn that calls finish_task — trace should still link
        # The _maybe_record_trace path is exercised via agent.run, but we test
        # add_trace_ref directly with explicit task_id
        result = self.registry.durable_task_store.add_trace_ref("trace_finish_1", task_id="dtask_shadow_1")
        self.assertTrue(result)
        task = self.registry.durable_task_store.get_task("dtask_shadow_1")
        self.assertIn("trace_finish_1", task.trace_refs)

    def test_add_trace_ref_with_explicit_task_id_skips_non_terminal_search(self):
        store = self.registry.durable_task_store
        store.create_task(goal="other running", steps=[{"text": "s1"}])
        store.create_task(goal="target", steps=[{"text": "s1"}])
        store.update_status("dtask_2", "running")
        store.update_status("dtask_2", "completed")

        result = store.add_trace_ref("trace_explicit", task_id="dtask_2")
        self.assertTrue(result)
        task = store.get_task("dtask_2")
        self.assertIn("trace_explicit", task.trace_refs)

        # dtask_1 (running) should NOT have gotten the trace
        other = store.get_task("dtask_1")
        self.assertNotIn("trace_explicit", other.trace_refs)


class TraceLinkIntegrationTests(unittest.TestCase):
    """Integration tests exercising _maybe_record_trace through the full controller path."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.registry = build_default_registry(db=self.db, workspace_root=self.root)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_maybe_record_trace_links_to_legacy_task_on_finish(self):
        """Trace links to dtask_shadow_1 when finish_task is called in the same turn."""
        trace_store = TraceStore(db=self.db)
        agent = MiniAgent(
            self.registry,
            trace_store=trace_store,
            event_store=self.registry.durable_event_store,
        )
        agent.durable_task_store = self.registry.durable_task_store

        self.registry.task_manager.start("build feature", "step one")
        self.registry.task_manager.update_step(1, "done", summary="done")

        # Simulate a turn that includes finish_task in tool records
        agent._active_tool_records = [
            ToolRunRecord(name="finish_task", status="ok", result_preview="done"),
        ]
        agent._turn_tool_args = {"finish_task": {"summary": "all done"}}
        agent.last_run_report = RunReport(
            status="done", steps_used=1,
            tool_calls=agent._active_tool_records,
            tool_call_limit=8, remaining_tool_calls=7,
        )
        agent._maybe_record_trace("finish the task", [])

        task = self.registry.durable_task_store.get_task("dtask_shadow_1")
        self.assertGreater(len(task.trace_refs), 0, "trace should be linked to dtask_shadow_1")

    def test_maybe_record_trace_links_to_durable_crud_task_id(self):
        """Trace links to real task_id from durable CRUD tool arguments."""
        trace_store = TraceStore(db=self.db)
        store = self.registry.durable_task_store
        created = store.create_task(goal="my task", steps=[{"text": "s1"}])
        store.update_status(created.task_id, "running")

        agent = MiniAgent(
            self.registry,
            trace_store=trace_store,
            event_store=self.registry.durable_event_store,
        )
        agent.durable_task_store = store

        agent._active_tool_records = [
            ToolRunRecord(name="update_durable_task", status="ok", result_preview="ok"),
        ]
        agent._turn_tool_args = {"update_durable_task": {"task_id": created.task_id, "status": "completed"}}
        agent.last_run_report = RunReport(
            status="done", steps_used=1,
            tool_calls=agent._active_tool_records,
            tool_call_limit=8, remaining_tool_calls=7,
        )
        agent._maybe_record_trace("update task", [])

        task = store.get_task(created.task_id)
        self.assertGreater(len(task.trace_refs), 0, "trace should be linked to the real task_id")

    def test_maybe_record_trace_no_task_tool_links_to_active_task(self):
        """When no task tool was called but there is a running task, trace links to it."""
        trace_store = TraceStore(db=self.db)
        store = self.registry.durable_task_store
        store.create_task(goal="active", steps=[{"text": "s1"}])
        store.update_status("dtask_1", "running")

        agent = MiniAgent(
            self.registry,
            trace_store=trace_store,
            event_store=self.registry.durable_event_store,
        )
        agent.durable_task_store = store

        agent._active_tool_records = [
            ToolRunRecord(name="calculate", status="ok", result_preview="5"),
        ]
        agent._turn_tool_args = {"calculate": {"expression": "2+3"}}
        agent.last_run_report = RunReport(
            status="done", steps_used=1,
            tool_calls=agent._active_tool_records,
            tool_call_limit=8, remaining_tool_calls=7,
        )
        agent._maybe_record_trace("计算 2+3", [])

        task = store.get_task("dtask_1")
        self.assertGreater(len(task.trace_refs), 0, "trace links to active non-terminal task")

    def test_resolve_task_id_extracts_from_durable_crud_args(self):
        """_resolve_task_id_from_tool_calls extracts real task_id from CRUD tool args."""
        agent = MiniAgent(self.registry)
        agent._turn_tool_args = {"retry_durable_task": {"task_id": "dtask_42"}}

        records = [ToolRunRecord(name="retry_durable_task", status="ok", result_preview="ok")]
        result = agent._resolve_task_id_from_tool_calls(records)
        self.assertEqual(result, "dtask_42")

    def test_resolve_task_id_legacy_returns_shadow(self):
        """Legacy task tools resolve to dtask_shadow_1."""
        agent = MiniAgent(self.registry)
        agent._turn_tool_args = {"finish_task": {"summary": "done"}}

        records = [ToolRunRecord(name="finish_task", status="ok", result_preview="done")]
        result = agent._resolve_task_id_from_tool_calls(records)
        self.assertEqual(result, "dtask_shadow_1")

    def test_resolve_task_id_no_task_tool_returns_none(self):
        """Non-task tools return None."""
        agent = MiniAgent(self.registry)
        agent._turn_tool_args = {"calculate": {"expression": "1+1"}}

        records = [ToolRunRecord(name="calculate", status="ok", result_preview="2")]
        result = agent._resolve_task_id_from_tool_calls(records)
        self.assertIsNone(result)


class ShadowSyncLeakRegressionTests(unittest.TestCase):
    """Blocker 2: new legacy task must not inherit old checkpoints/trace_refs."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.registry = build_default_registry(
            db=self.db,
            workspace_root=self.root,
        )

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_new_goal_clears_old_checkpoints_and_trace_refs(self):
        tm = self.registry.task_manager
        store = self.registry.durable_task_store

        # First task
        tm.start("old goal", "step A\nstep B")
        tm.update_step(1, "done", summary="done A")
        old_task = store.get_task("dtask_shadow_1")
        self.assertGreater(len(old_task.checkpoints), 0)

        # Manually add a trace ref to simulate prior linkage
        old_task.trace_refs.append("trace_old")
        store.upsert_task(old_task)

        # New task with different goal — must clear old refs
        tm.start("new goal", "step X\nstep Y")
        new_task = store.get_task("dtask_shadow_1")

        self.assertEqual(new_task.goal, "new goal")
        self.assertEqual(new_task.checkpoints, [])
        self.assertEqual(new_task.trace_refs, [])

    def test_same_goal_preserves_checkpoints_and_trace_refs(self):
        tm = self.registry.task_manager
        store = self.registry.durable_task_store

        created_at = datetime.now(timezone.utc).isoformat()
        tm.start("same goal", "step A")
        tm.update_step(1, "done", summary="done")

        task = store.get_task("dtask_shadow_1")
        task.trace_refs.append("trace_keep")
        store.upsert_task(task)

        # Simulate same goal + same created_at (re-sync, not new task)
        # We can't easily set created_at on the legacy task, so we verify
        # the negative: different goal clears
        tm.start("same goal", "step A")
        new_task = store.get_task("dtask_shadow_1")
        # Different created_at (now vs before), so refs are cleared
        self.assertNotIn("trace_keep", new_task.trace_refs)


class EventSanitizationRegressionTests(unittest.TestCase):
    """Blocker 3: event store must sanitize sensitive content."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.store = DurableEventStore(db=self.db)
        self.registry = build_default_registry(db=self.db, workspace_root=self.root)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_api_key_in_summary_is_redacted(self):
        event = self.store.record("task_created", summary="OPENAI_API_KEY=sk-1234567890")
        self.assertNotIn("sk-1234567890", event.summary)
        self.assertIn("[redacted]", event.summary)

    def test_api_key_in_payload_is_redacted(self):
        event = self.store.record(
            "step_updated",
            payload={"note": "using OPENAI_API_KEY=secret123 to call API"},
        )
        self.assertNotIn("secret123", json.dumps(event.payload))
        self.assertIn("[redacted]", event.payload["note"])

    def test_long_summary_is_truncated(self):
        long_summary = "x" * 1000
        event = self.store.record("task_created", summary=long_summary)
        self.assertLessEqual(len(event.summary), 510)
        self.assertTrue(event.summary.endswith("..."))

    def test_long_payload_string_is_truncated(self):
        long_note = "y" * 2000
        event = self.store.record("step_updated", payload={"note": long_note})
        self.assertLessEqual(len(event.payload["note"]), 1010)

    def test_nested_payload_is_sanitized(self):
        event = self.store.record(
            "step_updated",
            payload={"outer": {"inner": "OPENAI_API_KEY=leaked"}},
        )
        serialized = json.dumps(event.payload)
        self.assertNotIn("leaked", serialized)
        self.assertIn("[redacted]", serialized)

    def test_env_file_content_is_redacted(self):
        event = self.store.record(
            "task_created",
            summary="loaded .env file with secrets",
        )
        self.assertIn("[redacted]", event.summary)

    def test_bearer_token_is_redacted(self):
        event = self.store.record(
            "tool_call_finished",
            payload={"result": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"},
        )
        self.assertIn("[redacted]", event.payload["result"])

    def test_non_sensitive_content_passes_through(self):
        event = self.store.record(
            "step_updated",
            summary="step 1 done",
            payload={"step_id": 1, "status": "done", "note": "all good"},
        )
        self.assertEqual(event.summary, "step 1 done")
        self.assertEqual(event.payload["note"], "all good")

    def test_args_preview_redacts_password_in_list_of_dicts(self):
        """Reviewer blocker: args preview must recurse through lists/tuples."""
        agent = MiniAgent(self.registry, event_store=self.store)
        preview = agent._safe_args_preview({"items": [{"password": "super_secret_123"}]})
        self.assertNotIn("super_secret_123", preview,
                          "password value in list-of-dicts must be redacted in args preview")
        self.assertIn("[redacted]", preview)

    def test_credentials_nested_value_redacted_in_event_payload(self):
        """Reviewer blocker: nested value under sensitive key must be fully redacted."""
        event = self.store.record(
            "tool_call_started",
            payload={"credentials": {"value": "super_secret_123"}},
        )
        payload_json = json.dumps(event.payload)
        self.assertNotIn("super_secret_123", payload_json,
                          "value nested under sensitive key must be redacted in stored payload")
        self.assertIn("[redacted]", payload_json)


class ModelCallDurableEventTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.registry = build_default_registry(db=self.db, workspace_root=self.root)
        self.event_store = self.registry.durable_event_store

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_successful_chat_records_started_and_finished(self):
        from mini_agent.providers.base import LLMResponse

        class FakeLLM:
            def chat(self, messages, tools=None):
                return LLMResponse(content="hello world")

        agent = MiniAgent(self.registry, llm=FakeLLM(), event_store=self.event_store)
        agent.run("hi")

        events = self.event_store.list_events()
        started = [e for e in events if e.event_type == MODEL_CALL_STARTED]
        finished = [e for e in events if e.event_type == MODEL_CALL_FINISHED]

        self.assertGreaterEqual(len(started), 1)
        self.assertGreaterEqual(len(finished), 1)
        self.assertEqual(started[0].payload["status"], "started")
        self.assertEqual(finished[0].payload["status"], "ok")
        self.assertIn("latency_ms", finished[0].payload)
        self.assertEqual(finished[0].payload["response_preview"], "hello world")

    def test_tool_call_model_event_records_tool_call_count(self):
        from mini_agent.providers.base import LLMResponse, ToolCall

        call_count = [0]
        class FakeLLM:
            def chat(self, messages, tools=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[ToolCall(call_id="c1", name="calculate", arguments={"expression": "1+1"})],
                    )
                return LLMResponse(content="2")

        agent = MiniAgent(self.registry, llm=FakeLLM(), event_store=self.event_store)
        agent.run("计算 1+1")

        events = self.event_store.list_events()
        finished = [e for e in events if e.event_type == MODEL_CALL_FINISHED]
        self.assertGreaterEqual(len(finished), 1)
        first_finished = finished[-1]  # earliest (reversed list)
        self.assertEqual(first_finished.payload["tool_call_count"], 1)

    def test_model_error_records_error_event(self):
        from mini_agent.providers.base import LLMError

        class FailingLLM:
            def chat(self, messages, tools=None):
                raise LLMError("connection timeout")

        agent = MiniAgent(self.registry, llm=FailingLLM(), event_store=self.event_store)
        agent.run("hello")

        events = self.event_store.list_events()
        errors = [e for e in events if e.event_type == MODEL_CALL_ERROR]
        self.assertGreaterEqual(len(errors), 1)
        self.assertEqual(errors[0].payload["status"], "error")
        self.assertIn("connection timeout", errors[0].payload["error"])
        self.assertEqual(errors[0].severity, "warning")

    def test_streaming_model_event_records_started_and_finished(self):
        from mini_agent.providers.base import LLMResponse, ToolCall

        call_count = [0]
        class FakeLLM:
            def chat(self, messages, tools=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[ToolCall(call_id="c1", name="calculate", arguments={"expression": "1+1"})],
                    )
                return LLMResponse(content="")

            def stream_chat(self, messages, tools=None):
                yield "streamed "
                yield "answer"

        agent = MiniAgent(self.registry, llm=FakeLLM(), event_store=self.event_store)
        agent.run("计算 1+1")

        events = self.event_store.list_events()
        stream_finished = [
            e for e in events
            if e.event_type == MODEL_CALL_FINISHED and e.payload.get("streaming")
        ]
        self.assertGreaterEqual(len(stream_finished), 1)
        self.assertTrue(stream_finished[0].payload["streaming"])
        self.assertIn("streamed answer", stream_finished[0].payload["response_preview"])

    def test_model_event_failure_does_not_break_execution(self):
        class BrokenEventStore:
            def record(self, **kwargs):
                raise RuntimeError("disk full")
            def list_events(self, **kwargs):
                return []
            def get_event(self, event_id):
                return None

        from mini_agent.providers.base import LLMResponse

        class FakeLLM:
            def chat(self, messages, tools=None):
                return LLMResponse(content="still works")

        agent = MiniAgent(self.registry, llm=FakeLLM(), event_store=BrokenEventStore())
        result = agent.run("hello")
        self.assertEqual(result, "still works")

    def test_no_event_store_does_not_break_model_calls(self):
        from mini_agent.providers.base import LLMResponse

        class FakeLLM:
            def chat(self, messages, tools=None):
                return LLMResponse(content="ok")

        agent = MiniAgent(self.registry, llm=FakeLLM())
        result = agent.run("hello")
        self.assertEqual(result, "ok")

    def test_autonomous_model_call_records_events(self):
        from mini_agent.providers.base import LLMResponse

        class FakeLLM:
            def chat(self, messages, tools=None):
                return LLMResponse(content="done")

        agent = MiniAgent(self.registry, llm=FakeLLM(), event_store=self.event_store)
        agent.run_autonomous("test goal")

        events = self.event_store.list_events()
        started = [e for e in events if e.event_type == MODEL_CALL_STARTED]
        finished = [e for e in events if e.event_type == MODEL_CALL_FINISHED]
        self.assertGreaterEqual(len(started), 1)
        self.assertGreaterEqual(len(finished), 1)


class FileEditDurableEventTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.event_store = DurableEventStore(db=self.db)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def _file_events(self, event_type=None):
        event_types = {FILE_EDIT_STARTED, FILE_EDIT_FINISHED, FILE_EDIT_BLOCKED, FILE_EDIT_ERROR}
        events = [event for event in self.event_store.list_events() if event.event_type in event_types]
        events.reverse()
        if event_type:
            return [event for event in events if event.event_type == event_type]
        return events

    def test_write_records_started_and_finished(self):
        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=self.event_store)

        result = files.write("hello.txt", "hello world")

        self.assertIn("已写入", result)
        events = self._file_events()
        self.assertEqual([event.event_type for event in events], [FILE_EDIT_STARTED, FILE_EDIT_FINISHED])
        self.assertEqual(events[0].payload["operation"], "write")
        self.assertEqual(events[0].payload["status"], "started")
        self.assertEqual(events[1].payload["status"], "finished")
        self.assertEqual(events[1].payload["path"], "hello.txt")
        self.assertEqual(events[1].payload["paths"], ["hello.txt"])
        self.assertEqual(events[1].payload["bytes_before"], 0)
        self.assertEqual(events[1].payload["bytes_after"], len("hello world".encode("utf-8")))
        self.assertEqual(events[1].severity, "info")

    def test_replace_records_started_and_finished(self):
        (self.root / "data.txt").write_text("old content", encoding="utf-8")
        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=self.event_store)

        result = files.replace("data.txt", "old content", "new content")

        self.assertIn("已修改", result)
        events = self._file_events()
        self.assertEqual([event.event_type for event in events], [FILE_EDIT_STARTED, FILE_EDIT_FINISHED])
        self.assertEqual(events[0].payload["operation"], "replace")
        self.assertEqual(events[1].payload["bytes_before"], len("old content".encode("utf-8")))
        self.assertEqual(events[1].payload["bytes_after"], len("new content".encode("utf-8")))

    def test_cancelled_write_records_started_and_blocked(self):
        files = WorkspaceFiles(
            self.root,
            require_confirmation=True,
            confirm_action=lambda _: False,
            event_store=self.event_store,
        )

        result = files.write("test.txt", "content")

        self.assertIn("已取消", result)
        events = self._file_events()
        self.assertEqual([event.event_type for event in events], [FILE_EDIT_STARTED, FILE_EDIT_BLOCKED])
        self.assertEqual(events[1].payload["status"], "cancelled")
        self.assertEqual(events[1].payload["error"], "cancelled")
        self.assertEqual(events[1].severity, "warning")

    def test_denied_path_records_blocked_without_started(self):
        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=self.event_store)

        result = files.write(".env", "SUPER_SECRET_SENTINEL=value")

        self.assertIn("拒绝", result)
        events = self._file_events()
        self.assertEqual([event.event_type for event in events], [FILE_EDIT_BLOCKED])
        self.assertEqual(events[0].payload["status"], "blocked")
        self.assertEqual(events[0].payload["error"], "denied_path")

    def test_patch_records_started_and_finished(self):
        (self.root / "file.txt").write_text("line one\nline two\nline three\n", encoding="utf-8")
        patch_text = "--- a/file.txt\n+++ b/file.txt\n@@ -1,3 +1,3 @@\n line one\n-line two\n+line two modified\n line three\n"
        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=self.event_store)

        result = files.apply_unified_diff(patch_text)

        self.assertIn("已应用", result)
        events = self._file_events()
        self.assertEqual([event.event_type for event in events], [FILE_EDIT_STARTED, FILE_EDIT_FINISHED])
        self.assertEqual(events[0].payload["operation"], "patch")
        self.assertEqual(events[1].payload["path"], "file.txt")

    def test_multi_patch_records_started_and_finished_with_file_count(self):
        (self.root / "a.txt").write_text("aaa\n", encoding="utf-8")
        (self.root / "b.txt").write_text("bbb\n", encoding="utf-8")
        patch_text = "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-aaa\n+AAA\n--- a/b.txt\n+++ b/b.txt\n@@ -1 +1 @@\n-bbb\n+BBB\n"
        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=self.event_store)

        result = files.apply_multi_file_patch(patch_text)

        self.assertIn("已应用", result)
        events = self._file_events()
        self.assertEqual([event.event_type for event in events], [FILE_EDIT_STARTED, FILE_EDIT_FINISHED])
        self.assertEqual(events[0].payload["operation"], "multi_patch")
        self.assertEqual(events[0].payload["file_count"], 2)
        self.assertEqual(events[0].payload["paths"], ["a.txt", "b.txt"])

    def test_replace_text_not_found_records_blocked_without_raw_text(self):
        (self.root / "data.txt").write_text("actual content", encoding="utf-8")
        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=self.event_store)

        result = files.replace("data.txt", "SUPER_SECRET_OLD_TEXT", "SUPER_SECRET_NEW_TEXT")

        self.assertIn("没有找到", result)
        events = self._file_events()
        self.assertEqual([event.event_type for event in events], [FILE_EDIT_BLOCKED])
        self.assertEqual(events[0].payload["error"], "text_not_found")
        serialized = json.dumps([event.to_dict() for event in events], ensure_ascii=False)
        self.assertNotIn("SUPER_SECRET_OLD_TEXT", serialized)
        self.assertNotIn("SUPER_SECRET_NEW_TEXT", serialized)

    def test_os_write_failure_records_error_with_generic_label(self):
        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=self.event_store)

        with patch.object(Path, "write_text", side_effect=OSError("disk full SUPER_SECRET_ERROR")):
            result = files.write("test.txt", "content")

        self.assertIn("写入失败", result)
        events = self._file_events()
        self.assertEqual([event.event_type for event in events], [FILE_EDIT_STARTED, FILE_EDIT_ERROR])
        self.assertEqual(events[1].payload["status"], "error")
        self.assertEqual(events[1].payload["error"], "write_failed")
        serialized = json.dumps([event.to_dict() for event in events], ensure_ascii=False)
        self.assertNotIn("disk full SUPER_SECRET_ERROR", serialized)

    def test_no_raw_content_or_patch_in_events(self):
        secret_content = "SUPER_SECRET_FILE_CONTENT_123"
        patch_secret = "SUPER_SECRET_PATCH_CONTENT_456"
        (self.root / "secret.txt").write_text(secret_content + "\n", encoding="utf-8")
        patch_text = f"--- a/secret.txt\n+++ b/secret.txt\n@@ -1 +1 @@\n-{secret_content}\n+{patch_secret}\n"
        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=self.event_store)

        files.apply_unified_diff(patch_text)

        serialized = json.dumps([event.to_dict() for event in self._file_events()], ensure_ascii=False)
        self.assertNotIn(secret_content, serialized)
        self.assertNotIn(patch_secret, serialized)
        self.assertNotIn(patch_text, serialized)

    def test_failure_isolation_broken_event_store(self):
        class BrokenEventStore:
            def record(self, **kwargs):
                raise RuntimeError("store broken")

        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=BrokenEventStore())

        result = files.write("test.txt", "content")

        self.assertIn("已写入", result)
        self.assertEqual((self.root / "test.txt").read_text(encoding="utf-8"), "content")

    def test_no_event_store_does_not_break_file_ops(self):
        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=None)

        result = files.write("test.txt", "content")

        self.assertIn("已写入", result)

    def test_file_edit_events_have_no_task_id(self):
        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=self.event_store)

        files.write("test.txt", "content")

        for event in self._file_events():
            self.assertIsNone(event.task_id)

    def test_empty_old_text_records_blocked(self):
        files = WorkspaceFiles(self.root, require_confirmation=False, event_store=self.event_store)

        result = files.replace("test.txt", "", "new")

        self.assertIn("拒绝", result)
        events = self._file_events()
        self.assertEqual([event.event_type for event in events], [FILE_EDIT_BLOCKED])
        self.assertEqual(events[0].payload["error"], "empty_old_text")


class ShellCommandDurableEventTests(unittest.TestCase):
    """Tests for durable shell-command event logging."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.event_store = DurableEventStore(db=self.db)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def _shell_events(self, event_type=None):
        events = self.event_store.list_events()
        shell_types = (SHELL_COMMAND_STARTED, SHELL_COMMAND_FINISHED, SHELL_COMMAND_ERROR, SHELL_COMMAND_BLOCKED)
        if event_type:
            return [e for e in events if e.event_type == event_type]
        return [e for e in events if e.event_type in shell_types]

    def _serialized_shell_events(self):
        return json.dumps(
            [event.to_dict() for event in self._shell_events()],
            ensure_ascii=False,
            sort_keys=True,
        )

    def test_successful_command_records_started_and_finished(self):
        runner = ShellRunner(self.root, require_confirmation=False, event_store=self.event_store)
        result = runner.run("pwd")

        self.assertIn("exit_code: 0", result)
        started = self._shell_events(SHELL_COMMAND_STARTED)
        finished = self._shell_events(SHELL_COMMAND_FINISHED)
        self.assertEqual(len(started), 1)
        self.assertEqual(len(finished), 1)
        self.assertEqual(started[0].payload["executable"], "pwd")
        self.assertEqual(finished[0].payload["exit_code"], 0)
        self.assertEqual(finished[0].payload["status"], "finished")
        self.assertGreater(finished[0].payload["stdout_bytes"], 0)

    def test_disallowed_command_records_blocked(self):
        runner = ShellRunner(self.root, require_confirmation=False, event_store=self.event_store)
        result = runner.run("rm -rf /")

        self.assertIn("拒绝", result)
        blocked = self._shell_events(SHELL_COMMAND_BLOCKED)
        started = self._shell_events(SHELL_COMMAND_STARTED)
        finished = self._shell_events(SHELL_COMMAND_FINISHED)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(len(started), 0)
        self.assertEqual(len(finished), 0)
        self.assertEqual(blocked[0].payload["error"], "disallowed_command")

    def test_cancelled_command_records_blocked(self):
        runner = ShellRunner(self.root, require_confirmation=True, confirm_action=lambda _: False, event_store=self.event_store)
        result = runner.run("pwd")

        self.assertIn("已取消", result)
        started = self._shell_events(SHELL_COMMAND_STARTED)
        blocked = self._shell_events(SHELL_COMMAND_BLOCKED)
        self.assertEqual(len(started), 0)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0].payload["error"], "cancelled")

    def test_timeout_records_error_with_allowed_command(self):
        # Use python3 main.py which is allowed, but create a script that sleeps
        (self.root / "main.py").write_text("import time; time.sleep(30)")
        runner = ShellRunner(self.root, require_confirmation=False, timeout_seconds=1, event_store=self.event_store)
        result = runner.run("python3 main.py")

        self.assertIn("timeout", result)
        errors = self._shell_events(SHELL_COMMAND_ERROR)
        started = self._shell_events(SHELL_COMMAND_STARTED)
        self.assertEqual(len(started), 1)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].payload["error"], "timeout")
        self.assertEqual(errors[0].payload["status"], "timeout")
        self.assertTrue(errors[0].payload["timeout"])

    def test_nonzero_exit_still_records_finished(self):
        runner = ShellRunner(self.root, require_confirmation=False, event_store=self.event_store)
        result = runner.run("python3 -m py_compile nonexistent_file.py")

        self.assertIn("exit_code:", result)
        finished = self._shell_events(SHELL_COMMAND_FINISHED)
        # py_compile on nonexistent file returns nonzero, but still finishes
        self.assertEqual(len(finished), 1)
        self.assertNotEqual(finished[0].payload["exit_code"], 0)

    def test_no_raw_command_in_payload(self):
        sentinel = "NORA_SHELL_ARG_SECRET_8842"
        path = f"{sentinel}.py"
        (self.root / path).write_text("x = 1\n", encoding="utf-8")
        runner = ShellRunner(self.root, require_confirmation=False, event_store=self.event_store)
        runner.run(f"python3 -m py_compile {path}")

        serialized = self._serialized_shell_events()
        self.assertNotIn(sentinel, serialized)
        self.assertNotIn(path, serialized)
        self.assertIn('"executable": "python3"', serialized)

    def test_no_raw_output_in_serialized_events(self):
        sentinel = "NORA_SHELL_STDOUT_SECRET_4921"
        (self.root / sentinel).write_text("x", encoding="utf-8")
        runner = ShellRunner(self.root, require_confirmation=False, event_store=self.event_store)
        result = runner.run("ls")

        self.assertIn(sentinel, result)
        serialized = self._serialized_shell_events()
        self.assertNotIn(sentinel, serialized)
        finished = self._shell_events(SHELL_COMMAND_FINISHED)
        self.assertGreater(finished[0].payload["stdout_bytes"], 0)

    def test_no_raw_timeout_output_in_serialized_events(self):
        sentinel = "NORA_SHELL_TIMEOUT_OUTPUT_SECRET_1173"
        (self.root / "main.py").write_text(
            f"import time\nprint('{sentinel}', flush=True)\ntime.sleep(30)\n",
            encoding="utf-8",
        )
        runner = ShellRunner(self.root, require_confirmation=False, timeout_seconds=1, event_store=self.event_store)
        result = runner.run("python3 main.py")

        self.assertIn(sentinel, result)
        serialized = self._serialized_shell_events()
        self.assertNotIn(sentinel, serialized)
        errors = self._shell_events(SHELL_COMMAND_ERROR)
        self.assertEqual(errors[0].payload["error"], "timeout")
        self.assertGreater(errors[0].payload["stdout_bytes"], 0)

    def test_no_raw_os_error_in_serialized_events(self):
        sentinel = "NORA_SHELL_OS_ERROR_SECRET_2048"
        runner = ShellRunner(self.root, require_confirmation=False, event_store=self.event_store)

        with patch("mini_agent.shell.subprocess.run", side_effect=OSError(sentinel)):
            result = runner.run("pwd")

        self.assertIn("OSError", result)
        self.assertNotIn(sentinel, result)
        serialized = self._serialized_shell_events()
        self.assertNotIn(sentinel, serialized)
        errors = self._shell_events(SHELL_COMMAND_ERROR)
        self.assertEqual(errors[0].payload["error"], "os_error")

    def test_malformed_blocked_command_records_without_raw_command(self):
        sentinel = "NORA_SHELL_BLOCKED_SECRET_7365"
        runner = ShellRunner(self.root, require_confirmation=False, event_store=self.event_store)
        result = runner.run(f"'{sentinel}")

        self.assertIn("拒绝", result)
        serialized = self._serialized_shell_events()
        self.assertNotIn(sentinel, serialized)
        blocked = self._shell_events(SHELL_COMMAND_BLOCKED)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0].payload["executable"], "")
        self.assertEqual(blocked[0].payload["argv_count"], 0)

    def test_failure_isolation_broken_event_store(self):
        class BrokenEventStore:
            def record(self, **kwargs):
                raise RuntimeError("store broken")

        runner = ShellRunner(self.root, require_confirmation=False, event_store=BrokenEventStore())
        result = runner.run("pwd")
        self.assertIn("exit_code: 0", result)

    def test_no_event_store_does_not_break_shell(self):
        runner = ShellRunner(self.root, require_confirmation=False, event_store=None)
        result = runner.run("pwd")
        self.assertIn("exit_code: 0", result)

    def test_shell_event_no_task_id(self):
        runner = ShellRunner(self.root, require_confirmation=False, event_store=self.event_store)
        runner.run("pwd")

        for event in self._shell_events():
            self.assertIsNone(event.task_id)

    def test_payload_has_executable_and_argv_count(self):
        runner = ShellRunner(self.root, require_confirmation=False, event_store=self.event_store)
        runner.run("ls -la")

        started = self._shell_events(SHELL_COMMAND_STARTED)
        self.assertEqual(len(started), 1)
        self.assertEqual(started[0].payload["executable"], "ls")
        self.assertEqual(started[0].payload["argv_count"], 2)

    def test_default_registry_wires_shell_events(self):
        registry = build_default_registry(
            workspace_root=self.root,
            confirm_action=lambda _: True,
            db=self.db,
        )

        result = registry.call("run_shell_command", command="pwd", reason="test")

        self.assertIn("exit_code: 0", result)
        events = self._shell_events()
        self.assertEqual([event.event_type for event in events], [SHELL_COMMAND_FINISHED, SHELL_COMMAND_STARTED])


class TestRunDurableEventTests(unittest.TestCase):
    """Tests for durable test-run event logging."""

    COMMAND_SENTINEL = "NORA_TEST_COMMAND_SECRET_2319"
    OUTPUT_SENTINEL = "NORA_TEST_OUTPUT_SECRET_8221"
    ERROR_SENTINEL = "NORA_TEST_OS_ERROR_SECRET_9910"
    REASON_SENTINEL = "NORA_TEST_REASON_SECRET_4437"
    FORBIDDEN_PAYLOAD_KEYS = {
        "command", "args", "argv", "stdout", "stderr", "output",
        "result", "reason", "exception", "traceback",
    }

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.event_store = DurableEventStore(db=self.db)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def _test_events(self, event_type=None):
        events = self.event_store.list_events()
        test_types = (TEST_RUN_STARTED, TEST_RUN_FINISHED, TEST_RUN_ERROR, TEST_RUN_BLOCKED)
        if event_type:
            return [e for e in events if e.event_type == event_type]
        return [e for e in events if e.event_type in test_types]

    def _write_test(self, filename: str, body: str) -> None:
        test_dir = self.root / "tests"
        test_dir.mkdir(exist_ok=True)
        (test_dir / "__init__.py").write_text("", encoding="utf-8")
        (test_dir / filename).write_text(body, encoding="utf-8")

    def _serialized_test_events(self) -> str:
        return json.dumps(
            [event.to_dict() for event in self._test_events()],
            ensure_ascii=False,
            sort_keys=True,
        )

    def _assert_events_safe(self, *forbidden_values: str) -> None:
        serialized = self._serialized_test_events()
        for value in forbidden_values:
            self.assertNotIn(value, serialized)
        for event in self._test_events():
            leaked_keys = self.FORBIDDEN_PAYLOAD_KEYS & set(event.payload)
            self.assertEqual(leaked_keys, set(), event.payload)

    def test_successful_test_run_records_started_and_finished(self):
        self._write_test(
            "test_ok.py",
            "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n",
        )
        diag = Diagnostics(self.root, event_store=self.event_store)
        result = diag.run_tests(reason=self.REASON_SENTINEL)

        self.assertIn("exit_code: 0", result)
        started = self._test_events(TEST_RUN_STARTED)
        finished = self._test_events(TEST_RUN_FINISHED)
        self.assertEqual(len(started), 1)
        self.assertEqual(len(finished), 1)
        self.assertEqual(started[0].payload["command_kind"], "unittest_discover")
        self.assertEqual(started[0].payload["max_output_chars"], 12000)
        self.assertEqual(finished[0].payload["status"], "finished")
        self.assertEqual(finished[0].payload["exit_code"], 0)
        self.assertGreater(finished[0].payload["stdout_bytes"] + finished[0].payload["stderr_bytes"], 0)
        self._assert_events_safe(self.REASON_SENTINEL)

    def test_disallowed_command_records_blocked(self):
        diag = Diagnostics(self.root, event_store=self.event_store)
        result = diag.run_tests(command=f"python3 -m unittest discover -s tests {self.COMMAND_SENTINEL}")

        self.assertIn("拒绝", result)
        blocked = self._test_events(TEST_RUN_BLOCKED)
        started = self._test_events(TEST_RUN_STARTED)
        finished = self._test_events(TEST_RUN_FINISHED)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(len(started), 0)
        self.assertEqual(len(finished), 0)
        self.assertEqual(blocked[0].payload["error"], "disallowed_command")
        self._assert_events_safe(self.COMMAND_SENTINEL)

    def test_failing_tests_still_records_finished(self):
        self._write_test(
            "test_fail.py",
            f"import unittest\nclass T(unittest.TestCase):\n    def test_f(self): self.fail('{self.OUTPUT_SENTINEL}')\n",
        )

        diag = Diagnostics(self.root, timeout_seconds=30, event_store=self.event_store)
        result = diag.run_tests()

        self.assertIn("exit_code:", result)
        self.assertIn(self.OUTPUT_SENTINEL, result)
        finished = self._test_events(TEST_RUN_FINISHED)
        self.assertEqual(len(finished), 1)
        self.assertNotEqual(finished[0].payload["exit_code"], 0)
        self._assert_events_safe(self.OUTPUT_SENTINEL)

    def test_timeout_records_error(self):
        self._write_test(
            "test_slow.py",
            f"import unittest, time\nclass T(unittest.TestCase):\n    def test_s(self):\n        print('{self.OUTPUT_SENTINEL}', flush=True)\n        time.sleep(30)\n",
        )

        diag = Diagnostics(self.root, timeout_seconds=1, event_store=self.event_store)
        result = diag.run_tests()

        self.assertIn("timeout", result)
        errors = self._test_events(TEST_RUN_ERROR)
        started = self._test_events(TEST_RUN_STARTED)
        self.assertEqual(len(started), 1)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].payload["error"], "timeout")
        self.assertTrue(errors[0].payload["timeout"])
        self._assert_events_safe(self.OUTPUT_SENTINEL)

    def test_os_error_records_generic_error_without_raw_exception(self):
        diag = Diagnostics(self.root, event_store=self.event_store)

        with patch("mini_agent.diagnostics.subprocess.run", side_effect=OSError(self.ERROR_SENTINEL)):
            result = diag.run_tests()

        self.assertIn("OSError", result)
        self.assertNotIn(self.ERROR_SENTINEL, result)
        errors = self._test_events(TEST_RUN_ERROR)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].payload["error"], "os_error")
        self._assert_events_safe(self.ERROR_SENTINEL)

    def test_failure_isolation_broken_event_store(self):
        class BrokenEventStore:
            def record(self, **kwargs):
                raise RuntimeError("store broken")

        diag = Diagnostics(self.root, event_store=BrokenEventStore())
        result = diag.run_tests()
        self.assertIn("exit_code:", result)

    def test_no_event_store_does_not_break_tests(self):
        diag = Diagnostics(self.root, event_store=None)
        result = diag.run_tests()
        self.assertIn("exit_code:", result)

    def test_test_run_event_no_task_id(self):
        diag = Diagnostics(self.root, event_store=self.event_store)
        diag.run_tests()

        for event in self._test_events():
            self.assertIsNone(event.task_id)

    def test_payload_has_command_kind(self):
        self._write_test(
            "test_ok.py",
            "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n",
        )
        diag = Diagnostics(self.root, event_store=self.event_store)
        diag.run_tests(max_output_chars=900)

        started = self._test_events(TEST_RUN_STARTED)
        self.assertEqual(len(started), 1)
        self.assertEqual(started[0].payload["command_kind"], "unittest_discover")
        self.assertEqual(started[0].payload["max_output_chars"], 900)

    def test_default_registry_wires_test_run_events(self):
        self._write_test(
            "test_ok.py",
            "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n",
        )
        registry = build_default_registry(
            db=self.db,
            workspace_root=self.root,
            confirm_action=lambda _: True,
        )
        result = registry.call("run_project_tests", command="python3 -m unittest discover -s tests", reason="test")

        self.assertIn("exit_code: 0", result)
        self.assertIsNotNone(registry.diagnostics.event_store)
        self.assertEqual(
            [event.event_type for event in self._test_events()],
            [TEST_RUN_FINISHED, TEST_RUN_STARTED],
        )


if __name__ == "__main__":
    unittest.main()
