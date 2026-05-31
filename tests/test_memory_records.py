"""Tests for structured memory record store (TASK-038)."""

import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.database import NoraDB
from mini_agent.memory_records import MemoryRecordStore, VALID_KINDS, VALID_SCOPES
from mini_agent.registry import ToolRegistry
from mini_agent.toolkits.register_memory_records import register_memory_record_tools


class MemoryRecordSqliteTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        self.db = NoraDB(self.db_path)
        self.store = MemoryRecordStore(db=self.db)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_create_and_get(self):
        msg, rid = self.store.create(kind="decision", title="Use SQLite", content="SQLite for persistence")
        self.assertIn("已保存", msg)
        self.assertTrue(rid.startswith("mrec_"))
        rec = self.store.get(rid)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["kind"], "decision")
        self.assertEqual(rec["title"], "Use SQLite")
        self.assertEqual(rec["content"], "SQLite for persistence")
        self.assertEqual(rec["scope"], "project")
        self.assertEqual(rec["confidence"], 1.0)

    def test_create_all_kinds(self):
        for kind in VALID_KINDS:
            msg, rid = self.store.create(kind=kind, title=f"Test {kind}", content=f"Content for {kind}")
            self.assertTrue(rid.startswith("mrec_"), f"Failed for kind={kind}")

    def test_create_with_all_fields(self):
        msg, rid = self.store.create(
            kind="task_learning",
            title="Never mock DB",
            content="Integration tests are more reliable",
            scope="user",
            tags="testing,quality",
            source="review",
            confidence=0.9,
            related_task_id="task_42",
        )
        rec = self.store.get(rid)
        self.assertEqual(rec["tags"], ["testing", "quality"])
        self.assertEqual(rec["source"], "review")
        self.assertEqual(rec["confidence"], 0.9)
        self.assertEqual(rec["related_task_id"], "task_42")
        self.assertEqual(rec["scope"], "user")

    def test_create_invalid_kind(self):
        msg, rid = self.store.create(kind="invalid", title="t", content="c")
        self.assertEqual(rid, "")
        self.assertIn("无效", msg)

    def test_create_invalid_scope(self):
        msg, rid = self.store.create(kind="note", title="t", content="c", scope="bad_scope")
        self.assertEqual(rid, "")
        self.assertIn("无效的 scope", msg)

    def test_create_valid_scopes(self):
        for scope in VALID_SCOPES:
            msg, rid = self.store.create(kind="note", title=f"T {scope}", content="c", scope=scope)
            self.assertTrue(rid.startswith("mrec_"), f"Failed for scope={scope}")
            rec = self.store.get(rid)
            self.assertEqual(rec["scope"], scope)

    def test_create_empty_title(self):
        msg, rid = self.store.create(kind="note", title="", content="c")
        self.assertEqual(rid, "")

    def test_create_empty_content(self):
        msg, rid = self.store.create(kind="note", title="t", content="")
        self.assertEqual(rid, "")

    def test_create_sensitive_content(self):
        msg, rid = self.store.create(kind="note", title="API_KEY=sk-123", content="secret")
        self.assertEqual(rid, "")
        self.assertIn("敏感", msg)

    def test_create_confidence_clamped(self):
        _, rid = self.store.create(kind="note", title="t", content="c", confidence=2.0)
        rec = self.store.get(rid)
        self.assertEqual(rec["confidence"], 1.0)

        _, rid2 = self.store.create(kind="note", title="t2", content="c2", confidence=-0.5)
        rec2 = self.store.get(rid2)
        self.assertEqual(rec2["confidence"], 0.0)

    def test_get_nonexistent(self):
        self.assertIsNone(self.store.get("mrec_999"))
        self.assertIsNone(self.store.get(""))
        self.assertIsNone(self.store.get("  "))

    def test_list_all(self):
        self.store.create(kind="decision", title="A", content="a")
        self.store.create(kind="preference", title="B", content="b")
        results = self.store.list()
        self.assertEqual(len(results), 2)

    def test_list_filter_kind(self):
        self.store.create(kind="decision", title="A", content="a")
        self.store.create(kind="note", title="B", content="b")
        results = self.store.list(kind="decision")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["kind"], "decision")

    def test_list_filter_scope(self):
        self.store.create(kind="note", title="A", content="a", scope="project")
        self.store.create(kind="note", title="B", content="b", scope="user")
        results = self.store.list(scope="user")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["scope"], "user")

    def test_list_max_results(self):
        for i in range(5):
            self.store.create(kind="note", title=f"T{i}", content=f"c{i}")
        results = self.store.list(max_results=3)
        self.assertEqual(len(results), 3)

    def test_search(self):
        self.store.create(kind="decision", title="Use PostgreSQL", content="Switch from SQLite for prod")
        self.store.create(kind="note", title="Lunch", content="Pizza today")
        results = self.store.search("SQLite")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Use PostgreSQL")

    def test_search_filter_kind(self):
        self.store.create(kind="decision", title="Use X", content="X is good")
        self.store.create(kind="note", title="Use X too", content="X note")
        results = self.store.search("X", kind="note")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["kind"], "note")

    def test_search_empty_query(self):
        self.store.create(kind="note", title="T", content="C")
        results = self.store.search("")
        self.assertEqual(results, [])

    def test_search_filter_scope(self):
        self.store.create(kind="note", title="Proj A", content="alpha", scope="project")
        self.store.create(kind="note", title="User B", content="alpha", scope="user")
        results = self.store.search("alpha", scope="user")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["scope"], "user")

    def test_search_filter_tags(self):
        self.store.create(kind="note", title="Tagged", content="findme", tags="go,perf")
        self.store.create(kind="note", title="Other", content="findme", tags="python")
        results = self.store.search("findme", tags="go")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Tagged")

    def test_search_filter_tags_all_must_match(self):
        self.store.create(kind="note", title="Both", content="x", tags="go,perf")
        self.store.create(kind="note", title="OnlyGo", content="x", tags="go")
        results = self.store.search("x", tags="go,perf")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Both")

    def test_search_combined_filters(self):
        self.store.create(kind="decision", title="A", content="match", scope="project", tags="important")
        self.store.create(kind="note", title="B", content="match", scope="user", tags="important")
        self.store.create(kind="decision", title="C", content="match", scope="project", tags="other")
        results = self.store.search("match", kind="decision", scope="project", tags="important")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "A")

    def test_delete(self):
        _, rid = self.store.create(kind="note", title="T", content="C")
        msg = self.store.delete(rid)
        self.assertIn("已删除", msg)
        self.assertIsNone(self.store.get(rid))

    def test_delete_nonexistent(self):
        msg = self.store.delete("mrec_999")
        self.assertIn("未找到", msg)

    def test_delete_empty_id(self):
        msg = self.store.delete("")
        self.assertIn("不能为空", msg)

    def test_sequential_ids(self):
        _, rid1 = self.store.create(kind="note", title="A", content="a")
        _, rid2 = self.store.create(kind="note", title="B", content="b")
        num1 = int(rid1.split("_")[1])
        num2 = int(rid2.split("_")[1])
        self.assertEqual(num2, num1 + 1)


class MemoryRecordJsonlTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmpdir.name) / "records.jsonl"
        self.store = MemoryRecordStore(path=self.path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_create_and_get(self):
        msg, rid = self.store.create(kind="fact", title="Earth is round", content="Scientific fact")
        self.assertIn("已保存", msg)
        rec = self.store.get(rid)
        self.assertEqual(rec["kind"], "fact")
        self.assertEqual(rec["title"], "Earth is round")

    def test_list(self):
        self.store.create(kind="decision", title="A", content="a")
        self.store.create(kind="risk", title="B", content="b")
        results = self.store.list()
        self.assertEqual(len(results), 2)

    def test_list_filter_kind(self):
        self.store.create(kind="decision", title="A", content="a")
        self.store.create(kind="note", title="B", content="b")
        results = self.store.list(kind="decision")
        self.assertEqual(len(results), 1)

    def test_search(self):
        self.store.create(kind="decision", title="Use Redis", content="Cache layer")
        self.store.create(kind="note", title="Lunch", content="Sushi")
        results = self.store.search("Redis")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Use Redis")

    def test_delete(self):
        _, rid = self.store.create(kind="note", title="T", content="C")
        msg = self.store.delete(rid)
        self.assertIn("已删除", msg)
        self.assertIsNone(self.store.get(rid))

    def test_delete_nonexistent(self):
        msg = self.store.delete("mrec_999")
        self.assertIn("未找到", msg)

    def test_tags_stored_as_list(self):
        _, rid = self.store.create(kind="note", title="T", content="C", tags="a,b,c")
        rec = self.store.get(rid)
        self.assertIsInstance(rec["tags"], list)
        self.assertEqual(rec["tags"], ["a", "b", "c"])

    def test_search_filter_scope_jsonl(self):
        self.store.create(kind="note", title="Proj", content="alpha", scope="project")
        self.store.create(kind="note", title="User", content="alpha", scope="user")
        results = self.store.search("alpha", scope="user")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["scope"], "user")

    def test_search_filter_tags_jsonl(self):
        self.store.create(kind="note", title="Tagged", content="findme", tags="go,perf")
        self.store.create(kind="note", title="Other", content="findme", tags="python")
        results = self.store.search("findme", tags="perf")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Tagged")

    def test_invalid_scope_rejected_jsonl(self):
        msg, rid = self.store.create(kind="note", title="t", content="c", scope="nope")
        self.assertEqual(rid, "")
        self.assertIn("无效的 scope", msg)


class MemoryRecordRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        self.db = NoraDB(self.db_path)
        self.registry = ToolRegistry()
        self.store = MemoryRecordStore(db=self.db)
        register_memory_record_tools(self.registry, self.store)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_save_returns_json(self):
        result = self.registry.call(
            "save_memory_record", kind="decision", title="Use Go", content="Performance critical",
        )
        parsed = json.loads(result)
        self.assertEqual(parsed["kind"], "decision")
        self.assertEqual(parsed["title"], "Use Go")
        self.assertIn("record_id", parsed)

    def test_save_validation_error(self):
        result = self.registry.call(
            "save_memory_record", kind="invalid", title="T", content="C",
        )
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_search_returns_summaries(self):
        self.registry.call("save_memory_record", kind="fact", title="Speed of light", content="299792458 m/s")
        result = self.registry.call("search_memory_records", query="light")
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 1)
        self.assertIn("record_id", parsed[0])
        self.assertIn("title", parsed[0])
        # content should NOT be in search summaries
        self.assertNotIn("content", parsed[0])

    def test_list_returns_summaries(self):
        self.registry.call("save_memory_record", kind="note", title="A", content="aaa")
        result = self.registry.call("list_memory_records")
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 1)
        self.assertNotIn("content", parsed[0])

    def test_get_returns_full_content(self):
        result = self.registry.call(
            "save_memory_record", kind="decision", title="Use Rust", content="Memory safety",
        )
        rid = json.loads(result)["record_id"]
        result = self.registry.call("get_memory_record", record_id=rid)
        parsed = json.loads(result)
        self.assertEqual(parsed["content"], "Memory safety")

    def test_get_nonexistent(self):
        result = self.registry.call("get_memory_record", record_id="mrec_999")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_delete(self):
        result = self.registry.call(
            "save_memory_record", kind="note", title="T", content="C",
        )
        rid = json.loads(result)["record_id"]
        result = self.registry.call("delete_memory_record", record_id=rid)
        parsed = json.loads(result)
        self.assertTrue(parsed["ok"])

    def test_delete_nonexistent(self):
        result = self.registry.call("delete_memory_record", record_id="mrec_999")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_sensitive_content_rejected(self):
        result = self.registry.call(
            "save_memory_record", kind="note", title="Key", content="API_KEY=sk-abc123",
        )
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_existing_memory_tools_still_work(self):
        """save_memory and search_memory must keep working."""
        from mini_agent.toolkits import build_default_registry
        full_registry = build_default_registry(
            db=self.db, workspace_root=Path(self.tmpdir.name),
            confirm_action=lambda _: True,
        )
        full_registry.call("save_memory", text="test memory record compat", tags="test")
        result = full_registry.call("search_memory", query="memory record compat")
        self.assertTrue(len(result) > 0)

    def test_tools_registered(self):
        tools = {t.name for t in self.registry._tools.values()}
        for name in ("save_memory_record", "search_memory_records", "list_memory_records",
                      "get_memory_record", "delete_memory_record"):
            self.assertIn(name, tools)

    def test_search_with_scope_filter(self):
        self.registry.call("save_memory_record", kind="note", title="P", content="alpha", scope="project")
        self.registry.call("save_memory_record", kind="note", title="U", content="alpha", scope="user")
        result = self.registry.call("search_memory_records", query="alpha", scope="user")
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["scope"], "user")

    def test_search_with_tags_filter(self):
        self.registry.call("save_memory_record", kind="note", title="Tagged", content="findme", tags="go,perf")
        self.registry.call("save_memory_record", kind="note", title="Other", content="findme", tags="python")
        result = self.registry.call("search_memory_records", query="findme", tags="go")
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["title"], "Tagged")

    def test_save_invalid_scope_returns_error(self):
        result = self.registry.call(
            "save_memory_record", kind="note", title="T", content="C", scope="bad",
        )
        parsed = json.loads(result)
        self.assertIn("error", parsed)
        self.assertIn("scope", parsed["error"])


if __name__ == "__main__":
    unittest.main()
