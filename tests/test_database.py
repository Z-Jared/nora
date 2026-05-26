import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.database import NoraDB
from mini_agent.memory import LongTermMemory
from mini_agent.context_summary import ContextSummaryStore
from mini_agent.task_runner import TaskManager
from mini_agent.tool_results import ToolResultStore
from mini_agent.logs import JsonlToolLogger
from mini_agent.session import SessionStore, ConversationMemory
from mini_agent.migration import migrate_jsonl_to_sqlite


class NoraDBTests(unittest.TestCase):
    def test_creates_tables(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            tables = db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = {t[0] for t in tables}
            self.assertIn("long_term_memory", table_names)
            self.assertIn("context_summaries", table_names)
            self.assertIn("task_history", table_names)
            self.assertIn("current_task", table_names)
            self.assertIn("tool_results", table_names)
            self.assertIn("tool_logs", table_names)
            self.assertIn("sessions", table_names)
            db.close()

    def test_wal_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            mode = db.conn.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(mode, "wal")
            db.close()

    def test_table_count_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            self.assertEqual(db.table_count("long_term_memory"), 0)
            self.assertFalse(db.has_data("long_term_memory"))
            db.close()


class LongTermMemoryDBTests(unittest.TestCase):
    def test_save_and_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            mem = LongTermMemory(db=db)
            result = mem.save("hello world", "test,note")
            self.assertIn("mem_1", result)
            listing = mem.list()
            self.assertIn("hello world", listing)
            self.assertIn("test", listing)
            db.close()

    def test_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            mem = LongTermMemory(db=db)
            mem.save("Python is great", "lang")
            mem.save("JavaScript is fast", "lang")
            result = mem.search("Python")
            self.assertIn("Python", result)
            self.assertNotIn("JavaScript", result)
            db.close()

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            mem = LongTermMemory(db=db)
            mem.save("to delete")
            result = mem.delete("mem_1")
            self.assertIn("已删除", result)
            self.assertEqual(mem.list(), "暂无长期记忆。")
            db.close()

    def test_delete_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            mem = LongTermMemory(db=db)
            result = mem.delete("mem_999")
            self.assertIn("没有找到", result)
            db.close()

    def test_rejects_sensitive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            mem = LongTermMemory(db=db)
            result = mem.save("my API_KEY is secret")
            self.assertIn("拒绝", result)
            db.close()

    def test_empty_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            mem = LongTermMemory(db=db)
            self.assertEqual(mem.search(""), "请提供搜索关键词。")
            db.close()

    def test_list_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            mem = LongTermMemory(db=db)
            self.assertEqual(mem.list(), "暂无长期记忆。")
            db.close()


class ContextSummaryDBTests(unittest.TestCase):
    def test_save_and_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            store = ContextSummaryStore(db=db)
            result = store.save_summary("topic1", "summary1", "src")
            self.assertIn("ctx_1", result)
            listing = store.list_summaries()
            self.assertIn("topic1", listing)
            db.close()

    def test_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            store = ContextSummaryStore(db=db)
            store.save_summary("auth flow", "OAuth2 implementation")
            store.save_summary("db schema", "PostgreSQL tables")
            result = store.search_summaries("OAuth")
            self.assertIn("auth flow", result)
            self.assertNotIn("db schema", result)
            db.close()

    def test_empty_fields_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            store = ContextSummaryStore(db=db)
            self.assertIn("请提供", store.save_summary("", "s"))
            self.assertIn("请提供", store.save_summary("t", ""))
            db.close()


class TaskManagerDBTests(unittest.TestCase):
    def test_start_and_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            tm = TaskManager(db=db)
            result = tm.start("build feature", "step 1\nstep 2")
            self.assertIn("build feature", result)
            self.assertIn("step 1", tm.list())
            db.close()

    def test_update_step(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            tm = TaskManager(db=db)
            tm.start("goal", "a\nb")
            result = tm.update_step(1, "done", summary="finished")
            self.assertIn("已更新", result)
            db.close()

    def test_finish_and_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            tm = TaskManager(db=db)
            tm.start("goal", "step 1")
            tm.finish("all done")
            history = tm.list_history()
            self.assertIn("goal", history)
            db.close()

    def test_search_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            tm = TaskManager(db=db)
            tm.start("deploy app", "build\nship")
            tm.finish("deployed")
            result = tm.search_history("deploy")
            self.assertIn("deploy app", result)
            db.close()

    def test_restore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            tm = TaskManager(db=db)
            tm.start("goal", "step 1")
            tm.finish("done")
            result = tm.restore("task_1")
            self.assertIn("已恢复", result)
            listing = tm.list()
            self.assertIn("goal", listing)
            db.close()

    def test_no_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            tm = TaskManager(db=db)
            self.assertEqual(tm.list(), "暂无任务。")
            self.assertEqual(tm.list_history(), "暂无任务历史。")
            db.close()


class ToolResultDBTests(unittest.TestCase):
    def test_save_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            store = ToolResultStore(db=db)
            result_id = store.save("shell", "output text")
            self.assertTrue(result_id.startswith("tr_"))
            content = store.read(result_id)
            self.assertIn("output text", content)
            db.close()

    def test_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            store = ToolResultStore(db=db)
            store.save("tool1", "result1")
            store.save("tool2", "result2")
            listing = store.list()
            self.assertIn("tool1", listing)
            self.assertIn("tool2", listing)
            db.close()

    def test_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            store = ToolResultStore(db=db)
            store.save("shell", "hello world\nfoo bar")
            store.save("git", "commit abc123")
            result = store.search(query="hello")
            self.assertIn("hello world", result)
            db.close()

    def test_read_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            store = ToolResultStore(db=db)
            self.assertIn("没有找到", store.read("tr_999"))
            db.close()


class JsonlToolLoggerDBTests(unittest.TestCase):
    def test_record_and_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            logger = JsonlToolLogger(db=db)
            logger.record("shell", {"cmd": "ls"}, "ok", "file1\nfile2")
            result = logger.list_recent()
            self.assertIn("shell", result)
            self.assertIn("ok", result)
            db.close()

    def test_filter_by_tool(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            logger = JsonlToolLogger(db=db)
            logger.record("shell", {}, "ok")
            logger.record("git", {}, "ok")
            result = logger.list_recent(tool="shell")
            self.assertIn("shell", result)
            self.assertNotIn("git", result)
            db.close()

    def test_audit_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            logger = JsonlToolLogger(db=db)
            logger.record("shell", {"cmd": "ls"}, "ok", "output")
            logger.record("write_file", {"path": "test.py"}, "ok", "wrote")
            report = logger.generate_audit_report()
            self.assertIn("审计范围", report)
            self.assertIn("shell", report)
            db.close()

    def test_redaction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            logger = JsonlToolLogger(db=db)
            logger.record("tool", {"api_key": "secret123"}, "ok")
            result = logger.list_recent(include_arguments=True)
            self.assertIn("[redacted]", result)
            self.assertNotIn("secret123", result)
            db.close()


class SessionStoreDBTests(unittest.TestCase):
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            store = SessionStore(db=db)
            mem = ConversationMemory()
            mem.add_user("hello")
            mem.add_assistant("hi there")
            result = store.save(mem, "test_session")
            self.assertIn("已保存", result)

            mem2 = ConversationMemory()
            result = store.load("test_session", mem2)
            self.assertIn("已恢复", result)
            self.assertEqual(len(mem2.messages()), 2)
            db.close()

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            store = SessionStore(db=db)
            mem = ConversationMemory()
            mem.add_user("test")
            store.save(mem, "session1")
            listing = store.list_sessions()
            self.assertIn("session1", listing)
            db.close()

    def test_load_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            store = SessionStore(db=db)
            result = store.load("nope", ConversationMemory())
            self.assertIn("未找到", result)
            db.close()

    def test_list_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            store = SessionStore(db=db)
            self.assertEqual(store.list_sessions(), "暂无保存的会话。")
            db.close()


class MigrationTests(unittest.TestCase):
    def test_migrates_long_term_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            data_dir = tmpdir / "data"
            data_dir.mkdir()
            ltm_path = data_dir / "long_term_memory.jsonl"
            ltm_path.write_text(
                '{"id":"mem_1","text":"hello","tags":["a"],"created_at":"2024-01-01"}\n'
                '{"id":"mem_2","text":"world","tags":["b"],"created_at":"2024-01-02"}\n',
                encoding="utf-8",
            )
            db = NoraDB(tmpdir / "test.db")
            migrated = migrate_jsonl_to_sqlite(db, data_dir)
            self.assertIn("long_term_memory", migrated)
            mem = LongTermMemory(db=db)
            listing = mem.list()
            self.assertIn("hello", listing)
            self.assertIn("world", listing)
            self.assertTrue(ltm_path.with_suffix(".jsonl.bak").exists())
            db.close()

    def test_migrates_context_summaries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            data_dir = tmpdir / "data"
            data_dir.mkdir()
            cs_path = data_dir / "context_summaries.jsonl"
            cs_path.write_text(
                '{"id":"ctx_1","topic":"t","summary":"s","source":"src","created_at":"2024-01-01"}\n',
                encoding="utf-8",
            )
            db = NoraDB(tmpdir / "test.db")
            migrated = migrate_jsonl_to_sqlite(db, data_dir)
            self.assertIn("context_summaries", migrated)
            store = ContextSummaryStore(db=db)
            self.assertIn("t", store.list_summaries())
            db.close()

    def test_migrates_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            data_dir = tmpdir / "data"
            sessions_dir = data_dir / "sessions"
            sessions_dir.mkdir(parents=True)
            session_path = sessions_dir / "test.jsonl"
            session_path.write_text(
                '{"name":"test","saved_at":"2024-01-01","message_count":1}\n'
                '{"role":"user","content":"hi"}\n',
                encoding="utf-8",
            )
            db = NoraDB(tmpdir / "test.db")
            migrated = migrate_jsonl_to_sqlite(db, data_dir)
            self.assertIn("sessions", migrated)
            store = SessionStore(db=db)
            listing = store.list_sessions()
            self.assertIn("test", listing)
            db.close()

    def test_migrates_tool_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            data_dir = tmpdir / "data"
            data_dir.mkdir()
            tr_path = data_dir / "tool_results.jsonl"
            tr_path.write_text(
                '{"id":"tr_1","tool":"shell","created_at":"2024-01-01","chars":5,"result":"hello"}\n',
                encoding="utf-8",
            )
            db = NoraDB(tmpdir / "test.db")
            migrated = migrate_jsonl_to_sqlite(db, data_dir)
            self.assertIn("tool_results", migrated)
            store = ToolResultStore(db=db)
            self.assertIn("hello", store.read("tr_1"))
            db.close()

    def test_migrates_tool_logs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            data_dir = tmpdir / "data"
            data_dir.mkdir()
            logs_dir = tmpdir / "logs"
            logs_dir.mkdir()
            tl_path = logs_dir / "tool_calls.jsonl"
            tl_path.write_text(
                '{"timestamp":"2024-01-01","tool":"shell","arguments":{"cmd":"ls"},"status":"ok","result_preview":"file1"}\n',
                encoding="utf-8",
            )
            db = NoraDB(tmpdir / "test.db")
            migrated = migrate_jsonl_to_sqlite(db, data_dir, logs_dir)
            self.assertIn("tool_logs", migrated)
            logger = JsonlToolLogger(db=db)
            result = logger.list_recent()
            self.assertIn("shell", result)
            db.close()

    def test_migrates_task_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            data_dir = tmpdir / "data"
            data_dir.mkdir()
            th_path = data_dir / "task_history.jsonl"
            th_path.write_text(
                '{"id":"task_1","goal":"test","status":"finished","created_at":"2024-01-01","finished_at":"2024-01-02","summary":"done","steps":[]}\n',
                encoding="utf-8",
            )
            db = NoraDB(tmpdir / "test.db")
            migrated = migrate_jsonl_to_sqlite(db, data_dir)
            self.assertIn("task_history", migrated)
            tm = TaskManager(db=db)
            self.assertIn("test", tm.list_history())
            db.close()

    def test_migrates_current_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            data_dir = tmpdir / "data"
            data_dir.mkdir()
            ct_path = data_dir / "current_task.json"
            ct_path.write_text(
                json.dumps({"goal": "active goal", "status": "active", "steps": [{"id": 1, "text": "s", "status": "pending", "note": "", "summary": ""}]}),
                encoding="utf-8",
            )
            db = NoraDB(tmpdir / "test.db")
            migrated = migrate_jsonl_to_sqlite(db, data_dir)
            self.assertIn("current_task", migrated)
            tm = TaskManager(db=db)
            self.assertIn("active goal", tm.list())
            db.close()

    def test_idempotent_migration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            data_dir = tmpdir / "data"
            data_dir.mkdir()
            ltm_path = data_dir / "long_term_memory.jsonl"
            ltm_path.write_text('{"id":"mem_1","text":"hello","tags":[],"created_at":"2024-01-01"}\n', encoding="utf-8")
            db = NoraDB(tmpdir / "test.db")
            migrate_jsonl_to_sqlite(db, data_dir)
            # Second migration should not duplicate
            migrate_jsonl_to_sqlite(db, data_dir)
            mem = LongTermMemory(db=db)
            self.assertEqual(mem.list().count("hello"), 1)
            db.close()


class BackwardCompatTests(unittest.TestCase):
    """Verify stores still work with Path (JSONL mode)."""

    def test_long_term_memory_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mem.jsonl"
            mem = LongTermMemory(path=path)
            mem.save("test", "tag")
            self.assertIn("test", mem.list())
            self.assertIn("test", mem.search("test"))
            mem.delete("mem_1")
            self.assertEqual(mem.list(), "暂无长期记忆。")

    def test_context_summary_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ctx.jsonl"
            store = ContextSummaryStore(path=path)
            store.save_summary("topic", "summary")
            self.assertIn("topic", store.list_summaries())
            self.assertIn("topic", store.search_summaries("topic"))

    def test_task_manager_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "task.json"
            hist = Path(tmpdir) / "history.jsonl"
            tm = TaskManager(path=path, history_path=hist)
            tm.start("goal", "step 1")
            self.assertIn("goal", tm.list())
            tm.finish("done")
            self.assertIn("goal", tm.list_history())

    def test_tool_results_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "results.jsonl"
            store = ToolResultStore(path=path)
            rid = store.save("tool", "result")
            self.assertIn("result", store.read(rid))
            self.assertIn("tool", store.list())

    def test_logger_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "logs.jsonl"
            logger = JsonlToolLogger(path=path)
            logger.record("tool", {}, "ok", "result")
            self.assertIn("tool", logger.list_recent())

    def test_session_store_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir) / "sessions"
            store = SessionStore(directory=d)
            mem = ConversationMemory()
            mem.add_user("hi")
            store.save(mem, "test")
            mem2 = ConversationMemory()
            store.load("test", mem2)
            self.assertEqual(len(mem2.messages()), 1)


if __name__ == "__main__":
    unittest.main()
