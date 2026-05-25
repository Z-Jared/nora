import tempfile
import unittest
from pathlib import Path

from mini_agent.context_summary import ContextSummaryStore
from mini_agent.context_window import ContextWindow
from mini_agent.memory import ConversationMemory, LongTermMemory
from mini_agent.tool_results import ToolResultStore

class ContextWindowTests(unittest.TestCase):
    def test_keeps_small_tool_results_unchanged(self):
        window = ContextWindow(max_tool_result_chars=100)

        self.assertEqual(window.compact_tool_result("read_file", "short"), "short")

    def test_compacts_large_tool_results_with_head_tail_and_metadata(self):
        window = ContextWindow(max_tool_result_chars=10, head_chars=5, tail_chars=5)

        result = window.compact_tool_result("read_file", "aaaaaMIDDLEzzzzz")

        self.assertIn("tool_result_compacted", result)
        self.assertIn("tool=read_file", result)
        self.assertIn("original_chars=16", result)
        self.assertIn("aaaaa", result)
        self.assertIn("zzzzz", result)
        self.assertNotIn("MIDDLE", result)


class ConversationMemoryTests(unittest.TestCase):
    def test_keeps_recent_messages_only(self):
        memory = ConversationMemory(max_messages=3)

        memory.add_user("one")
        memory.add_assistant("two")
        memory.add_user("three")
        memory.add_assistant("four")

        self.assertEqual(
            memory.messages(),
            [
                {"role": "assistant", "content": "two"},
                {"role": "user", "content": "three"},
                {"role": "assistant", "content": "four"},
            ],
        )

    def test_skips_sensitive_content(self):
        memory = ConversationMemory(max_messages=10)

        memory.add_user("LLM_API_KEY=secret")

        self.assertEqual(memory.messages(), [])


class ContextSummaryStoreTests(unittest.TestCase):
    def test_saves_searches_and_lists_summaries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ContextSummaryStore(Path(tmpdir) / "context.jsonl")
            saved = store.save_summary("测试诊断", "失败在断言", source="tests/test_demo.py")
            search = store.search_summaries("断言")
            listing = store.list_summaries()

        self.assertIn("已保存上下文摘要", saved)
        self.assertIn("失败在断言", search)
        self.assertIn("tests/test_demo.py", listing)

    def test_rejects_sensitive_context_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ContextSummaryStore(Path(tmpdir) / "context.jsonl")

            result = store.save_summary("secret", "OPENAI_API_KEY=secret")

        self.assertIn("拒绝保存", result)


class ToolResultStoreTests(unittest.TestCase):
    def test_saves_lists_reads_and_searches_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ToolResultStore(Path(tmpdir) / "tool_results.jsonl")
            result_id = store.save("read_project_file", "alpha\nneedle line\nomega")

            listing = store.list()
            chunk = store.read(result_id, offset=6, limit=20)
            search = store.search(query="needle")

        self.assertIn(result_id, listing)
        self.assertIn("needle line", chunk)
        self.assertIn("needle line", search)

    def test_rejects_sensitive_results(self):
        fake_key = "sk" + "-secret"
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "tool_results.jsonl"
            store = ToolResultStore(path)

            result_id = store.save("read_project_file", fake_key)

        self.assertEqual(result_id, "")
        self.assertFalse(path.exists())

    def test_rejects_common_token_patterns(self):
        github_token = "gh" + "p_" + "b" * 36
        google_key = "AI" + "za" + "c" * 35
        jwt = "ey" + "J" + "d" * 20 + "." + "e" * 20 + "." + "f" * 20
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "tool_results.jsonl"
            store = ToolResultStore(path)

            github_result_id = store.save("read_project_file", github_token)
            google_result_id = store.save("read_project_file", google_key)
            jwt_result_id = store.save("read_project_file", jwt)

        self.assertEqual(github_result_id, "")
        self.assertEqual(google_result_id, "")
        self.assertEqual(jwt_result_id, "")
        self.assertFalse(path.exists())

    def test_read_result_enforces_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ToolResultStore(Path(tmpdir) / "tool_results.jsonl")
            result_id = store.save("tool", "abcdef")

            result = store.read(result_id, offset=1, limit=2)

        self.assertIn("shown=2", result)
        self.assertTrue(result.endswith("bc"))


class LongTermMemoryTests(unittest.TestCase):
    def test_saves_and_searches_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "memory.jsonl")

            result = memory.save("项目偏好: 先写测试再实现", tags="preference,tdd")
            search = memory.search("测试", max_results=5)

        self.assertIn("已保存记忆", result)
        self.assertIn("先写测试再实现", search)
        self.assertIn("preference", search)

    def test_rejects_sensitive_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "memory.jsonl")

            result = memory.save("OPENAI_API_KEY=secret")

            self.assertIn("拒绝保存", result)
            self.assertFalse((Path(tmpdir) / "memory.jsonl").exists())

    def test_lists_and_deletes_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "memory.jsonl")
            memory.save("第一条记忆", tags="one")
            memory.save("第二条记忆", tags="two")

            listing = memory.list(max_results=10)
            delete_result = memory.delete("mem_1")
            after_delete = memory.list(max_results=10)

        self.assertIn("mem_1", listing)
        self.assertIn("mem_2", listing)
        self.assertIn("已删除记忆: mem_1", delete_result)
        self.assertNotIn("第一条记忆", after_delete)
        self.assertIn("第二条记忆", after_delete)



if __name__ == "__main__":
    unittest.main()
