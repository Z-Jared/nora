import tempfile
import unittest
from pathlib import Path

from mini_agent.memory import ConversationMemory
from mini_agent.session import SessionStore


class SessionStoreTests(unittest.TestCase):
    def test_save_and_load_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("你好")
            memory.add_assistant("你好！有什么可以帮你的？")
            memory.add_user("计算 1 + 1")
            memory.add_assistant("结果是 2")

            save_result = store.save(memory, name="test_session")
            self.assertIn("已保存会话", save_result)
            self.assertIn("4 条消息", save_result)

            new_memory = ConversationMemory()
            load_result = store.load("test_session", new_memory)
            self.assertIn("已恢复会话", load_result)
            self.assertEqual(len(new_memory.messages()), 4)
            self.assertEqual(new_memory.messages()[0]["content"], "你好")
            self.assertEqual(new_memory.messages()[3]["content"], "结果是 2")

    def test_save_generates_name_from_timestamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("hello")

            result = store.save(memory)

            self.assertIn("已保存会话", result)
            self.assertIn("session_", result)

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("msg1")
            store.save(memory, name="alpha")
            memory.add_user("msg2")
            store.save(memory, name="beta")

            result = store.list_sessions()

            self.assertIn("alpha", result)
            self.assertIn("beta", result)

    def test_list_sessions_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")

            result = store.list_sessions()

            self.assertEqual(result, "暂无保存的会话。")

    def test_load_nonexistent_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()

            result = store.load("missing", memory)

            self.assertIn("未找到会话", result)

    def test_save_rejects_empty_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()

            result = store.save(memory)

            self.assertIn("没有对话记录", result)

    def test_save_rejects_sensitive_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("hello")

            result = store.save(memory, name="session_API_KEY_test")

            self.assertIn("敏感信息", result)


if __name__ == "__main__":
    unittest.main()
