"""Tests for run trace store and controller integration."""

import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.controller import MiniAgent
from mini_agent.tools import build_default_registry
from mini_agent.traces import (
    RunTrace,
    ToolCallTrace,
    TraceStore,
    build_trace,
    truncate_preview,
)


class TruncatePreviewTests(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(truncate_preview("hello"), "hello")

    def test_empty_text(self):
        self.assertEqual(truncate_preview(""), "")
        self.assertEqual(truncate_preview("   "), "")

    def test_long_text_truncated(self):
        text = "a" * 300
        result = truncate_preview(text, limit=200)
        self.assertEqual(len(result), 201)  # 200 + ellipsis
        self.assertTrue(result.endswith("…"))

    def test_exact_limit(self):
        text = "a" * 200
        result = truncate_preview(text, limit=200)
        self.assertEqual(result, text)

    def test_strips_whitespace_before_truncate(self):
        result = truncate_preview("  hello  ")
        self.assertEqual(result, "hello")


class BuildTraceTests(unittest.TestCase):
    def test_basic_trace(self):
        trace = build_trace(
            trace_id="trace_1",
            user_input="计算 2 + 3",
            status="done",
            events=[
                {"type": "typing"},
                {"type": "delta", "content": "计算结果: 5"},
                {"type": "done", "status": "done"},
            ],
            tool_records=[],
        )
        self.assertEqual(trace.trace_id, "trace_1")
        self.assertEqual(trace.status, "done")
        self.assertEqual(trace.input_preview, "计算 2 + 3")
        self.assertEqual(trace.event_counts, {"typing": 1, "delta": 1, "done": 1})
        self.assertEqual(trace.tool_calls, [])
        self.assertEqual(trace.failure, "")

    def test_trace_with_tool_records(self):
        class FakeRecord:
            def __init__(self, name, status, result_preview):
                self.name = name
                self.status = status
                self.result_preview = result_preview

        records = [FakeRecord("calculate", "ok", "计算结果: 5")]
        trace = build_trace(
            trace_id="trace_2",
            user_input="计算 2 + 3",
            status="done",
            events=[{"type": "done"}],
            tool_records=records,
        )
        self.assertEqual(len(trace.tool_calls), 1)
        self.assertEqual(trace.tool_calls[0].name, "calculate")
        self.assertEqual(trace.tool_calls[0].status, "ok")

    def test_trace_with_failure(self):
        trace = build_trace(
            trace_id="trace_3",
            user_input="do something",
            status="blocked",
            events=[{"type": "error"}],
            tool_records=[],
            failure="model exploded",
        )
        self.assertEqual(trace.status, "blocked")
        self.assertEqual(trace.failure, "model exploded")

    def test_input_preview_truncated(self):
        long_input = "x" * 500
        trace = build_trace(
            trace_id="trace_4",
            user_input=long_input,
            status="done",
            events=[],
            tool_records=[],
        )
        self.assertEqual(len(trace.input_preview), 201)
        self.assertTrue(trace.input_preview.endswith("…"))

    def test_result_preview_truncated(self):
        class LongResultRecord:
            name = "tool"
            status = "ok"
            result_preview = "y" * 500

        trace = build_trace(
            trace_id="trace_5",
            user_input="test",
            status="done",
            events=[],
            tool_records=[LongResultRecord()],
        )
        self.assertEqual(len(trace.tool_calls[0].result_preview), 201)


class RunTraceDataclassTests(unittest.TestCase):
    def test_to_dict_and_from_dict_roundtrip(self):
        trace = RunTrace(
            trace_id="trace_10",
            created_at="2026-05-28T12:00:00Z",
            status="done",
            input_preview="hello",
            event_counts={"typing": 1, "delta": 1},
            tool_calls=[ToolCallTrace("calc", "ok", "5")],
            failure="",
        )
        d = trace.to_dict()
        restored = RunTrace.from_dict(d)
        self.assertEqual(restored.trace_id, "trace_10")
        self.assertEqual(restored.tool_calls[0].name, "calc")
        self.assertEqual(restored.event_counts["typing"], 1)


class TraceStoreJSONLTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = TraceStore(directory=Path(self.tmpdir) / "traces")

    def test_record_and_list(self):
        trace = build_trace("trace_1", "hello", "done", [{"type": "done"}], [])
        self.store.record(trace)
        traces = self.store.list_traces()
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["trace_id"], "trace_1")

    def test_list_most_recent_first(self):
        for i in range(5):
            trace = build_trace(f"trace_{i}", f"msg {i}", "done", [], [])
            self.store.record(trace)
        traces = self.store.list_traces(max_results=3)
        self.assertEqual(len(traces), 3)
        self.assertEqual(traces[0]["trace_id"], "trace_4")

    def test_get_trace_by_id(self):
        trace = build_trace("trace_7", "test input", "blocked", [{"type": "error"}], [], failure="err")
        self.store.record(trace)
        result = self.store.get_trace("trace_7")
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["failure"], "err")

    def test_get_nonexistent_returns_none(self):
        self.assertIsNone(self.store.get_trace("trace_999"))

    def test_empty_store(self):
        self.assertEqual(self.store.list_traces(), [])
        self.assertIsNone(self.store.get_trace("trace_1"))

    def test_next_trace_id_increments(self):
        self.assertEqual(self.store.next_trace_id(), "trace_1")
        self.store.record(build_trace("trace_1", "a", "done", [], []))
        self.assertEqual(self.store.next_trace_id(), "trace_2")

    def test_tool_calls_preserved(self):
        tc = ToolCallTrace("calculate", "ok", "计算结果: 5")
        trace = RunTrace(
            trace_id="trace_1",
            created_at="2026-01-01T00:00:00Z",
            status="done",
            input_preview="test",
            event_counts={},
            tool_calls=[tc],
        )
        self.store.record(trace)
        result = self.store.get_trace("trace_1")
        self.assertEqual(len(result["tool_calls"]), 1)
        self.assertEqual(result["tool_calls"][0]["name"], "calculate")

    def test_event_counts_preserved(self):
        trace = build_trace("trace_1", "x", "done", [
            {"type": "typing"}, {"type": "delta"}, {"type": "delta"}, {"type": "done"}
        ], [])
        self.store.record(trace)
        result = self.store.get_trace("trace_1")
        self.assertEqual(result["event_counts"], {"typing": 1, "delta": 2, "done": 1})

    def test_no_sensitive_data_stored(self):
        """Full prompts, API keys, and model outputs must not appear in traces."""
        trace = build_trace(
            "trace_1",
            "sk-1234567890abcdef " + "x" * 500,
            "done",
            [{"type": "delta", "content": "secret model output " + "y" * 500}],
            [],
        )
        self.store.record(trace)
        result = self.store.get_trace("trace_1")
        # input_preview is truncated
        self.assertLessEqual(len(result["input_preview"]), 201)
        # Full prompt is not stored
        self.assertNotIn("sk-1234567890abcdef x" * 10, json.dumps(result))

    def test_sensitive_input_preview_is_redacted(self):
        trace = build_trace(
            "trace_1",
            "OPENAI_API_KEY=secret-value",
            "done",
            [],
            [],
        )
        self.store.record(trace)
        result = self.store.get_trace("trace_1")
        self.assertEqual(result["input_preview"], "[redacted]")
        self.assertNotIn("secret-value", json.dumps(result))

    def test_sensitive_tool_result_preview_is_redacted(self):
        class SensitiveRecord:
            name = "read_project_file"
            status = "ok"
            result_preview = "OPENAI_API_KEY=secret-value"

        trace = build_trace(
            "trace_1",
            "test",
            "done",
            [],
            [SensitiveRecord()],
        )
        self.store.record(trace)
        result = self.store.get_trace("trace_1")
        self.assertEqual(result["tool_calls"][0]["result_preview"], "[redacted]")
        self.assertNotIn("secret-value", json.dumps(result))


class TraceStoreDBTests(unittest.TestCase):
    def setUp(self):
        from mini_agent.database import NoraDB
        self.tmpdir = tempfile.mkdtemp()
        self.db = NoraDB(Path(self.tmpdir) / "test.db")
        self.store = TraceStore(db=self.db)

    def tearDown(self):
        self.db.close()

    def test_record_and_list(self):
        trace = build_trace("trace_1", "hello", "done", [{"type": "done"}], [])
        self.store.record(trace)
        traces = self.store.list_traces()
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["trace_id"], "trace_1")

    def test_get_trace_by_id(self):
        trace = build_trace("trace_5", "input", "blocked", [], [], failure="err")
        self.store.record(trace)
        result = self.store.get_trace("trace_5")
        self.assertIsNotNone(result)
        self.assertEqual(result["failure"], "err")

    def test_next_trace_id_increments(self):
        self.assertEqual(self.store.next_trace_id(), "trace_1")
        self.store.record(build_trace("trace_1", "a", "done", [], []))
        self.assertEqual(self.store.next_trace_id(), "trace_2")

    def test_list_respects_limit(self):
        for i in range(10):
            self.store.record(build_trace(f"trace_{i}", f"msg {i}", "done", [], []))
        traces = self.store.list_traces(max_results=5)
        self.assertEqual(len(traces), 5)

    def test_empty_db(self):
        self.assertEqual(self.store.list_traces(), [])
        self.assertIsNone(self.store.get_trace("trace_1"))


class ControllerTraceIntegrationTests(unittest.TestCase):
    """Test that MiniAgent.run_events() records traces when trace_store is set."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.trace_store = TraceStore(directory=Path(self.tmpdir) / "traces")

    def test_trace_recorded_on_successful_turn(self):
        agent = MiniAgent(
            build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"),
            trace_store=self.trace_store,
        )
        events = list(agent.run_events("计算 2 + 3"))
        types = [e["type"] for e in events]
        self.assertIn("done", types)

        traces = self.trace_store.list_traces()
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["status"], "done")
        self.assertIn("计算", traces[0]["input_preview"])
        self.assertIn("done", traces[0]["event_counts"])

    def test_trace_recorded_on_blocked_turn(self):
        agent = MiniAgent(
            build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"),
            trace_store=self.trace_store,
        )
        list(agent.run_events("帮我订机票"))
        traces = self.trace_store.list_traces()
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["status"], "done")

    def test_trace_records_tool_calls(self):
        agent = MiniAgent(
            build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"),
            trace_store=self.trace_store,
        )
        list(agent.run_events("计算 2 + 3"))
        traces = self.trace_store.list_traces()
        self.assertEqual(len(traces), 1)
        tool_calls = traces[0]["tool_calls"]
        self.assertGreater(len(tool_calls), 0)
        self.assertEqual(tool_calls[0]["name"], "calculate")
        self.assertIn(tool_calls[0]["status"], ("ok", "error", "blocked", "cancelled"))

    def test_no_trace_when_no_store(self):
        agent = MiniAgent(build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"))
        list(agent.run_events("hello"))
        # No crash, no trace store to check

    def test_trace_failure_does_not_break_run(self):
        """If trace recording fails, the run should still succeed."""
        class BrokenTraceStore:
            def next_trace_id(self):
                return "trace_1"
            def record(self, trace):
                raise RuntimeError("disk full")

        agent = MiniAgent(
            build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"),
            trace_store=BrokenTraceStore(),
        )
        events = list(agent.run_events("计算 2 + 3"))
        types = [e["type"] for e in events]
        self.assertIn("done", types)
        # No crash

    def test_multiple_traces_increment_ids(self):
        agent = MiniAgent(
            build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"),
            trace_store=self.trace_store,
        )
        list(agent.run_events("计算 1 + 1"))
        list(agent.run_events("计算 2 + 2"))
        list(agent.run_events("计算 3 + 3"))
        traces = self.trace_store.list_traces()
        self.assertEqual(len(traces), 3)
        ids = [t["trace_id"] for t in traces]
        self.assertEqual(ids, ["trace_3", "trace_2", "trace_1"])

    def test_trace_event_counts_match_actual_events(self):
        agent = MiniAgent(
            build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"),
            trace_store=self.trace_store,
        )
        events = list(agent.run_events("计算 2 + 3"))
        traces = self.trace_store.list_traces()
        trace = traces[0]

        # Count events manually
        expected_counts = {}
        for evt in events:
            t = evt.get("type", "unknown")
            expected_counts[t] = expected_counts.get(t, 0) + 1
        self.assertEqual(trace["event_counts"], expected_counts)

    def test_input_preview_not_full_input(self):
        long_input = "请帮我计算 " + "x" * 500
        agent = MiniAgent(
            build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"),
            trace_store=self.trace_store,
        )
        list(agent.run_events(long_input))
        traces = self.trace_store.list_traces()
        self.assertLess(len(traces[0]["input_preview"]), len(long_input))
        self.assertLessEqual(len(traces[0]["input_preview"]), 201)


if __name__ == "__main__":
    unittest.main()
