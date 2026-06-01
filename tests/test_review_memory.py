"""Tests for review-memory capture (TASK-042)."""

import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.database import NoraDB
from mini_agent.memory_records import MemoryRecordStore
from mini_agent.review_memory import ReviewMemoryCapture, _is_safe, _contains_raw_content, _truncate


class SafetyChecksTests(unittest.TestCase):
    """_is_safe and _contains_raw_content reject unsafe content."""

    def test_empty_text_not_safe(self):
        self.assertFalse(_is_safe(""))
        self.assertFalse(_is_safe("  "))

    def test_normal_text_is_safe(self):
        self.assertTrue(_is_safe("Implemented feature X successfully"))

    def test_api_key_not_safe(self):
        self.assertFalse(_is_safe("OPENAI_API_KEY=sk-abc123"))
        self.assertFalse(_is_safe("Bearer eyJhbGciOiJIUzI1NiJ9"))

    def test_diff_markers_not_safe(self):
        self.assertFalse(_is_safe("diff --git a/file.py b/file.py"))
        self.assertFalse(_is_safe("@@ -1,3 +1,4 @@"))
        self.assertFalse(_is_safe("+++ b/file.py"))
        self.assertFalse(_is_safe("--- a/file.py"))

    def test_shell_prompt_not_safe(self):
        self.assertFalse(_is_safe("$ ls -la"))
        self.assertFalse(_is_safe("PS C:\\> Get-ChildItem"))

    def test_truncate_beyond_limit(self):
        long = "x" * 3000
        result = _truncate(long, 2000)
        self.assertLessEqual(len(result), 2001)  # +1 for ellipsis
        self.assertTrue(result.endswith("…"))

    def test_truncate_within_limit(self):
        short = "hello"
        result = _truncate(short, 2000)
        self.assertEqual(result, "hello")


class ApprovedCaptureTests(unittest.TestCase):
    """Approved review creates task_learning, decision, risk records."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = NoraDB(Path(self.tmpdir.name) / "test.db")
        self.store = MemoryRecordStore(db=self.db)
        self.capture = ReviewMemoryCapture(self.store)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_approved_creates_task_learning(self):
        result = self.capture.capture(
            task_id="dtask_1",
            status="approved",
            title="Feature X implemented",
            summary="Implemented feature X with tests passing",
        )
        self.assertEqual(len(result["created"]), 1)
        rec = result["created"][0]
        self.assertEqual(rec["kind"], "task_learning")
        self.assertEqual(rec.get("related_task_id"), "dtask_1")
        self.assertIn("review", rec.get("tags", []))
        self.assertIn("approved", rec.get("tags", []))

    def test_approved_creates_decision(self):
        result = self.capture.capture(
            task_id="dtask_2",
            status="approved",
            title="Architecture decision",
            decisions="Use SQLite for local storage",
        )
        self.assertEqual(len(result["created"]), 1)
        self.assertEqual(result["created"][0]["kind"], "decision")

    def test_approved_creates_risk(self):
        result = self.capture.capture(
            task_id="dtask_3",
            status="approved",
            title="Risk identified",
            risks="API rate limiting may cause issues",
        )
        self.assertEqual(len(result["created"]), 1)
        self.assertEqual(result["created"][0]["kind"], "risk")

    def test_approved_creates_multiple_records(self):
        result = self.capture.capture(
            task_id="dtask_4",
            status="approved",
            title="Full review",
            summary="All tests pass",
            learnings="Better to test early",
            decisions="Use type hints everywhere",
            risks="None identified",
        )
        kinds = {r["kind"] for r in result["created"]}
        self.assertIn("task_learning", kinds)
        self.assertIn("decision", kinds)
        self.assertIn("risk", kinds)


class ChangesRequestedCaptureTests(unittest.TestCase):
    """Changes requested does not create decision/fact records."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = NoraDB(Path(self.tmpdir.name) / "test.db")
        self.store = MemoryRecordStore(db=self.db)
        self.capture = ReviewMemoryCapture(self.store)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_changes_requested_no_decision(self):
        result = self.capture.capture(
            task_id="dtask_5",
            status="changes_requested",
            title="Needs fix",
            summary="Fix the bug",
            decisions="Should use pattern X",  # Should be ignored
        )
        kinds = {r["kind"] for r in result["created"]}
        self.assertNotIn("decision", kinds)
        self.assertNotIn("task_learning", kinds)

    def test_changes_requested_explicit_risk(self):
        result = self.capture.capture(
            task_id="dtask_6",
            status="changes_requested",
            title="Risk noted",
            risks="Memory leak in module Y",
        )
        self.assertEqual(len(result["created"]), 1)
        self.assertEqual(result["created"][0]["kind"], "risk")

    def test_blocked_no_decision(self):
        result = self.capture.capture(
            task_id="dtask_7",
            status="blocked",
            title="Blocked by dependency",
            summary="Waiting for API",
            decisions="Use workaround",  # Should be ignored
        )
        kinds = {r["kind"] for r in result["created"]}
        self.assertNotIn("decision", kinds)


class DedupeTests(unittest.TestCase):
    """Dedupe prevents repeated capture duplicates."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = NoraDB(Path(self.tmpdir.name) / "test.db")
        self.store = MemoryRecordStore(db=self.db)
        self.capture = ReviewMemoryCapture(self.store)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_duplicate_capture_skipped(self):
        self.capture.capture(
            task_id="dtask_8",
            status="approved",
            title="Same title",
            summary="Same summary",
        )
        result2 = self.capture.capture(
            task_id="dtask_8",
            status="approved",
            title="Same title",
            summary="Same summary",
        )
        self.assertEqual(len(result2["created"]), 0)
        self.assertTrue(len(result2["skipped"]) > 0)

    def test_different_task_not_dupe(self):
        self.capture.capture(
            task_id="dtask_9",
            status="approved",
            title="Same title",
            summary="Same summary",
        )
        result2 = self.capture.capture(
            task_id="dtask_10",
            status="approved",
            title="Same title",
            summary="Same summary",
        )
        self.assertEqual(len(result2["created"]), 1)


class SecretContentTests(unittest.TestCase):
    """Secret-like content is rejected/skipped."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = NoraDB(Path(self.tmpdir.name) / "test.db")
        self.store = MemoryRecordStore(db=self.db)
        self.capture = ReviewMemoryCapture(self.store)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_secret_in_summary_rejected(self):
        result = self.capture.capture(
            task_id="dtask_11",
            status="approved",
            title="Normal title",
            summary="API_KEY=sk-1234567890abcdef was used",
        )
        self.assertEqual(len(result["created"]), 0)

    def test_secret_in_title_rejected(self):
        result = self.capture.capture(
            task_id="dtask_12",
            status="approved",
            title="Used OPENAI_API_KEY=secret",
            summary="Normal summary",
        )
        self.assertEqual(len(result["created"]), 0)

    def test_diff_in_summary_rejected(self):
        result = self.capture.capture(
            task_id="dtask_13",
            status="approved",
            title="Normal title",
            summary="diff --git a/file.py b/file.py\n+new line",
        )
        self.assertEqual(len(result["created"]), 0)


class RawContentTests(unittest.TestCase):
    """Raw diff/shell/env/prompt-like content is rejected."""

    def test_diff_marker_rejected(self):
        self.assertFalse(_is_safe("diff --git a/test.py b/test.py\n--- a/test.py"))

    def test_hunk_header_rejected(self):
        self.assertFalse(_is_safe("@@ -10,5 +10,6 @@"))

    def test_shell_command_rejected(self):
        self.assertFalse(_is_safe("$ npm install express"))

    def test_prompt_system_marker_rejected(self):
        self.assertFalse(_is_safe("system: You are a helpful assistant"))
        self.assertFalse(_is_safe("System: Follow these instructions"))

    def test_prompt_user_marker_rejected(self):
        self.assertFalse(_is_safe("user: What is the capital of France?"))
        self.assertFalse(_is_safe("User: Tell me about Python"))

    def test_prompt_assistant_marker_rejected(self):
        self.assertFalse(_is_safe("assistant: The capital is Paris"))
        self.assertFalse(_is_safe("Assistant: Here is the answer"))

    def test_chat_template_markers_rejected(self):
        self.assertFalse(_is_safe("<|system|>You are helpful"))
        self.assertFalse(_is_safe("<|user|>Hello"))
        self.assertFalse(_is_safe("<|assistant|>Hi there"))
        self.assertFalse(_is_safe("text<|endoftext|>"))

    def test_inst_markers_rejected(self):
        self.assertFalse(_is_safe("[INST] Explain this [/INST]"))
        self.assertFalse(_is_safe("[INST]What is Python?[/INST]"))

    def test_hash_header_markers_rejected(self):
        self.assertFalse(_is_safe("### System: You are a coding assistant"))
        self.assertFalse(_is_safe("### User: Write a function"))
        self.assertFalse(_is_safe("### Assistant: Here is the code"))

    def test_prompt_in_capture_rejected(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        db = NoraDB(Path(tmpdir.name) / "test.db")
        self.addCleanup(db.close)
        store = MemoryRecordStore(db=db)
        capture = ReviewMemoryCapture(store)
        result = capture.capture(
            task_id="dtask_p1",
            status="approved",
            title="Prompt test",
            summary="system: You are a helpful assistant\nuser: Hello\nassistant: Hi",
        )
        self.assertEqual(len(result["created"]), 0)

    def test_env_var_in_capture_rejected(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        db = NoraDB(Path(tmpdir.name) / "test.db")
        self.addCleanup(db.close)
        store = MemoryRecordStore(db=db)
        capture = ReviewMemoryCapture(store)
        result = capture.capture(
            task_id="dtask_e1",
            status="approved",
            title="Config update",
            summary="Set DATABASE_URL=postgres://user:pass@host/db for prod",
        )
        self.assertEqual(len(result["created"]), 0)

    def test_env_var_assignment_rejected(self):
        self.assertFalse(_is_safe("AWS_SECRET_ACCESS_KEY=abc123"))
        self.assertFalse(_is_safe("DATABASE_URL=postgres://user:pass@host/db"))
        self.assertFalse(_is_safe("NORA_DB_PATH=/tmp/db"))
        self.assertFalse(_is_safe("MY_CUSTOM_TOKEN=secret_value"))

    def test_export_env_var_rejected(self):
        self.assertFalse(_is_safe("export DATABASE_URL=postgres://localhost/mydb"))
        self.assertFalse(_is_safe("export  MY_VAR=some_value"))

    def test_env_var_in_multiline_rejected(self):
        self.assertFalse(_is_safe("Some context\nAPI_HOST=https://api.example.com\nMore text"))

    def test_embedded_env_var_in_prose_rejected(self):
        self.assertFalse(_is_safe("Set NORA_DB_PATH=/tmp/db"))
        self.assertFalse(_is_safe("Config used: MY_CUSTOM_TOKEN=value"))
        self.assertFalse(_is_safe("Config used: AWS_SECRET_ACCESS_KEY=abc"))

    def test_embedded_env_var_in_capture_rejected(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        db = NoraDB(Path(tmpdir.name) / "test.db")
        self.addCleanup(db.close)
        store = MemoryRecordStore(db=db)
        capture = ReviewMemoryCapture(store)
        result = capture.capture(
            task_id="dtask_e2",
            status="approved",
            title="Config update",
            summary="Set NORA_DB_PATH=/tmp/db for local dev",
        )
        self.assertEqual(len(result["created"]), 0)

    def test_lowercase_env_not_rejected(self):
        # Only uppercase env vars are rejected; lowercase key=value is fine
        self.assertTrue(_is_safe("sqlite is used for local storage"))
        self.assertTrue(_is_safe("config setting = some value"))

    def test_normal_technical_content_accepted(self):
        self.assertTrue(_is_safe("Implemented REST API with Express.js"))
        self.assertTrue(_is_safe("Used SQLite for local storage"))
        self.assertTrue(_is_safe("Set timeout to 30 seconds"))
        self.assertTrue(_is_safe("Changed port from 8080 to 3000"))


class RegistryToolTests(unittest.TestCase):
    """Registry tool returns bounded JSON, not full content."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = NoraDB(Path(self.tmpdir.name) / "test.db")
        from mini_agent.toolkits import build_default_registry
        self.registry = build_default_registry(
            db=self.db,
            workspace_root=Path(self.tmpdir.name),
            confirm_action=lambda _: True,
        )

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_capture_returns_bounded_json(self):
        result = self.registry.call(
            "capture_review_memory",
            task_id="dtask_20",
            status="approved",
            title="Feature done",
            summary="Implemented feature with tests",
        )
        parsed = json.loads(result)
        self.assertIn("created", parsed)
        self.assertIn("skipped", parsed)
        # Created records have bounded fields only
        for rec in parsed["created"]:
            self.assertIn("record_id", rec)
            self.assertIn("kind", rec)
            self.assertIn("title", rec)
            # Should NOT contain full content
            self.assertNotIn("content", rec)

    def test_capture_with_all_fields(self):
        result = self.registry.call(
            "capture_review_memory",
            task_id="dtask_21",
            status="approved",
            title="Full capture",
            summary="Summary text",
            learnings="Learned X",
            risks="Risk Y",
            decisions="Decided Z",
        )
        parsed = json.loads(result)
        self.assertGreaterEqual(len(parsed["created"]), 1)

    def test_capture_changes_requested(self):
        result = self.registry.call(
            "capture_review_memory",
            task_id="dtask_22",
            status="changes_requested",
            title="Needs work",
            summary="Some issues found",
            risks="Risk noted",
        )
        parsed = json.loads(result)
        self.assertGreaterEqual(len(parsed["created"]), 1)

    def test_capture_source_passed_through(self):
        result = self.registry.call(
            "capture_review_memory",
            task_id="dtask_23",
            status="approved",
            title="Source test",
            summary="Verifying source field",
            source="retro",
        )
        parsed = json.loads(result)
        self.assertGreaterEqual(len(parsed["created"]), 1)
        record_id = parsed["created"][0]["record_id"]
        store = self.registry.memory_record_store
        rec = store.get(record_id)
        self.assertEqual(rec["source"], "retro")

    def test_capture_default_source_is_review(self):
        result = self.registry.call(
            "capture_review_memory",
            task_id="dtask_24",
            status="approved",
            title="Default source",
            summary="Checking default source",
        )
        parsed = json.loads(result)
        record_id = parsed["created"][0]["record_id"]
        store = self.registry.memory_record_store
        rec = store.get(record_id)
        self.assertEqual(rec["source"], "review")


if __name__ == "__main__":
    unittest.main()
