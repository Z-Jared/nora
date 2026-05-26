import time
import unittest

from mini_agent.tool_cache import ToolResultCache


class ToolResultCacheTests(unittest.TestCase):
    def test_cache_returns_stored_result(self):
        cache = ToolResultCache()

        cache.put("read_file", {"path": "README.md"}, "file content")

        self.assertEqual(cache.get("read_file", {"path": "README.md"}), "file content")

    def test_cache_returns_none_for_miss(self):
        cache = ToolResultCache()

        self.assertIsNone(cache.get("read_file", {"path": "missing.md"}))

    def test_cache_differentiates_arguments(self):
        cache = ToolResultCache()

        cache.put("read_file", {"path": "a.md"}, "content a")
        cache.put("read_file", {"path": "b.md"}, "content b")

        self.assertEqual(cache.get("read_file", {"path": "a.md"}), "content a")
        self.assertEqual(cache.get("read_file", {"path": "b.md"}), "content b")

    def test_cache_differentiates_tool_names(self):
        cache = ToolResultCache()

        cache.put("tool_a", {"x": "1"}, "result a")
        cache.put("tool_b", {"x": "1"}, "result b")

        self.assertEqual(cache.get("tool_a", {"x": "1"}), "result a")
        self.assertEqual(cache.get("tool_b", {"x": "1"}), "result b")

    def test_cache_expires_after_ttl(self):
        cache = ToolResultCache(ttl_seconds=1)

        cache.put("tool", {"x": "1"}, "result")
        self.assertEqual(cache.get("tool", {"x": "1"}), "result")

        time.sleep(1.1)
        self.assertIsNone(cache.get("tool", {"x": "1"}))

    def test_cache_evicts_oldest_when_full(self):
        cache = ToolResultCache(max_size=2)

        cache.put("tool", {"x": "1"}, "first")
        cache.put("tool", {"x": "2"}, "second")
        cache.put("tool", {"x": "3"}, "third")

        self.assertIsNone(cache.get("tool", {"x": "1"}))
        self.assertEqual(cache.get("tool", {"x": "2"}), "second")
        self.assertEqual(cache.get("tool", {"x": "3"}), "third")

    def test_cache_clear(self):
        cache = ToolResultCache()

        cache.put("tool", {"x": "1"}, "result")
        cache.clear()

        self.assertIsNone(cache.get("tool", {"x": "1"}))


class MiniAgentToolCacheIntegrationTests(unittest.TestCase):
    def test_read_only_tools_are_cached(self):
        from mini_agent.controller import MiniAgent
        from mini_agent.registry import ToolPermission, ToolRegistry

        call_count = [0]

        def counting_handler(expression: str) -> str:
            call_count[0] += 1
            return f"result: {expression}"

        registry = ToolRegistry()
        registry.register(
            "cached_tool",
            "A cached tool",
            counting_handler,
            parameters={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
            permission=ToolPermission(category="local", risk="read"),
        )

        agent = MiniAgent(registry)

        agent._call_tool("cached_tool", {"expression": "2+3"})
        agent._call_tool("cached_tool", {"expression": "2+3"})

        self.assertEqual(call_count[0], 1)

    def test_write_tools_are_not_cached(self):
        from mini_agent.controller import MiniAgent
        from mini_agent.registry import ToolPermission, ToolRegistry

        call_count = [0]

        def counting_handler(text: str) -> str:
            call_count[0] += 1
            return f"saved: {text}"

        registry = ToolRegistry()
        registry.register(
            "write_tool",
            "A write tool",
            counting_handler,
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
            permission=ToolPermission(category="notes", risk="write"),
        )

        agent = MiniAgent(registry)

        agent._call_tool("write_tool", {"text": "hello"})
        agent._call_tool("write_tool", {"text": "hello"})

        self.assertEqual(call_count[0], 2)


if __name__ == "__main__":
    unittest.main()
