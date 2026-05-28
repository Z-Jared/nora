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

    def test_save_rejects_empty_sanitized_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("hello")

            result = store.save(memory, name="!!!")

            self.assertIn("无效", result)

    def test_list_sessions_after_save_two(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("msg1")
            store.save(memory, name="first")
            memory.add_user("msg2")
            store.save(memory, name="second")

            result = store.list_sessions()

            self.assertIn("first", result)
            self.assertIn("second", result)
            self.assertIn("1 条消息", result)
            self.assertIn("2 条消息", result)

    def test_load_preserves_message_roles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("q1")
            memory.add_assistant("a1")
            memory.add_user("q2")
            store.save(memory, name="roles")

            new_memory = ConversationMemory()
            store.load("roles", new_memory)
            messages = new_memory.messages()

            self.assertEqual(messages[0]["role"], "user")
            self.assertEqual(messages[0]["content"], "q1")
            self.assertEqual(messages[1]["role"], "assistant")
            self.assertEqual(messages[1]["content"], "a1")
            self.assertEqual(messages[2]["role"], "user")
            self.assertEqual(messages[2]["content"], "q2")

    def test_save_overwrites_existing_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("old message")
            store.save(memory, name="dup")

            new_memory = ConversationMemory()
            new_memory.add_user("new message")
            result = store.save(new_memory, name="dup")
            self.assertIn("已保存", result)

            loaded = ConversationMemory()
            store.load("dup", loaded)
            contents = [m["content"] for m in loaded.messages()]
            self.assertIn("new message", contents)
            self.assertNotIn("old message", contents)

    def test_save_strips_dots_from_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("hello")

            result = store.save(memory, name="v1.0-release")

            self.assertIn("已保存", result)
            self.assertIn("v10-release", result)

    def test_list_sessions_structured_returns_dicts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("msg1")
            store.save(memory, name="alpha")

            sessions = store.list_sessions_structured()

            self.assertIsInstance(sessions, list)
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["name"], "alpha")
            self.assertEqual(sessions[0]["message_count"], 1)
            self.assertTrue(sessions[0]["saved_at"])

    def test_list_sessions_structured_two_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("msg1")
            store.save(memory, name="first")
            memory.add_user("msg2")
            store.save(memory, name="second")

            sessions = store.list_sessions_structured()

            self.assertEqual(len(sessions), 2)
            names = [s["name"] for s in sessions]
            self.assertIn("first", names)
            self.assertIn("second", names)

    def test_list_sessions_structured_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")

            sessions = store.list_sessions_structured()

            self.assertEqual(sessions, [])


if __name__ == "__main__":
    unittest.main()
