"""Tests for optional MCP server adapter (TASK-040).

All tests must pass WITHOUT the ``mcp`` package installed.
"""

import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.database import NoraDB
from mini_agent.mcp_server import (
    DEFAULT_ALLOWLIST,
    _truncate,
    call_mcp_tool,
    create_server,
    is_tool_allowed,
    registry_to_mcp_tools,
)
from mini_agent.registry import ToolPermission, ToolRegistry
from mini_agent.toolkits import build_default_registry


class MetadataConversionTests(unittest.TestCase):
    """registry_to_mcp_tools preserves name, description, parameters."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = NoraDB(Path(self.tmpdir.name) / "test.db")
        self.registry = build_default_registry(
            db=self.db,
            workspace_root=Path(self.tmpdir.name),
            confirm_action=lambda _: True,
        )

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_conversion_preserves_name(self):
        tools = registry_to_mcp_tools(self.registry)
        names = {t["name"] for t in tools}
        self.assertIn("calculate", names)

    def test_conversion_preserves_description(self):
        tools = registry_to_mcp_tools(self.registry)
        calc = next(t for t in tools if t["name"] == "calculate")
        self.assertTrue(len(calc["description"]) > 0)

    def test_conversion_preserves_parameters(self):
        tools = registry_to_mcp_tools(self.registry)
        calc = next(t for t in tools if t["name"] == "calculate")
        self.assertIn("inputSchema", calc)
        schema = calc["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)

    def test_conversion_returns_dicts_with_expected_keys(self):
        tools = registry_to_mcp_tools(self.registry)
        for t in tools:
            self.assertIn("name", t)
            self.assertIn("description", t)
            self.assertIn("inputSchema", t)


class AllowlistTests(unittest.TestCase):
    """Default allowlist excludes high-risk tools."""

    def test_default_allowlist_includes_safe_tools(self):
        for name in (
            "calculate",
            "search_memory",
            "save_memory",
            "search_memory_records",
            "list_memory_records",
            "get_memory_record",
            "save_memory_record",
        ):
            self.assertIn(name, DEFAULT_ALLOWLIST, f"{name} should be in default allowlist")

    def test_default_allowlist_excludes_high_risk(self):
        for name in (
            "run_shell_command",
            "write_file",
            "replace_in_file",
            "git_commit",
            "git_push",
            "browser_click",
            "process_start",
            "list_tool_permissions",
        ):
            self.assertNotIn(name, DEFAULT_ALLOWLIST, f"{name} should NOT be in default allowlist")

    def test_is_tool_allowed_with_default(self):
        self.assertTrue(is_tool_allowed("calculate"))
        self.assertFalse(is_tool_allowed("run_shell_command"))

    def test_is_tool_allowed_with_custom(self):
        custom = {"my_tool", "other_tool"}
        self.assertTrue(is_tool_allowed("my_tool", custom))
        self.assertFalse(is_tool_allowed("calculate", custom))

    def test_conversion_filters_by_allowlist(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        db = NoraDB(Path(tmpdir.name) / "test.db")
        self.addCleanup(db.close)
        registry = build_default_registry(
            db=db, workspace_root=Path(tmpdir.name), confirm_action=lambda _: True,
        )
        tools = registry_to_mcp_tools(registry)
        names = {t["name"] for t in tools}
        # Must NOT include high-risk tools
        self.assertNotIn("run_shell_command", names)
        self.assertNotIn("write_file", names)
        self.assertNotIn("git_commit", names)
        # Must include allowed tools
        self.assertIn("calculate", names)

    def test_custom_allowlist(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        db = NoraDB(Path(tmpdir.name) / "test.db")
        self.addCleanup(db.close)
        registry = build_default_registry(
            db=db, workspace_root=Path(tmpdir.name), confirm_action=lambda _: True,
        )
        tools = registry_to_mcp_tools(registry, allowlist={"calculate"})
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "calculate")


class CallMcpToolTests(unittest.TestCase):
    """call_mcp_tool handles allowlist, unknown, malformed, errors, truncation."""

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.register(
            "fake_tool",
            "A fake tool for testing.",
            lambda x="default": f"result:{x}",
            parameters={
                "type": "object",
                "properties": {"x": {"type": "string"}},
            },
        )
        self.registry.register(
            "strict_tool",
            "Requires an int.",
            lambda n: f"got:{n}",
            parameters={
                "type": "object",
                "properties": {"n": {"type": "integer"}},
                "required": ["n"],
            },
        )
        self.registry.register(
            "explode_tool",
            "Always raises.",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            parameters={"type": "object", "properties": {}},
        )

    def test_allowed_tool_returns_result(self):
        result = call_mcp_tool(
            self.registry, "fake_tool", {"x": "hello"},
            allowlist={"fake_tool", "strict_tool", "explode_tool"},
        )
        self.assertEqual(result, "result:hello")

    def test_default_allowlist_rejects_unlisted_tool(self):
        result = call_mcp_tool(self.registry, "fake_tool", {"x": "hello"})
        data = json.loads(result)
        self.assertIn("未在允许列表中", data["error"])

    def test_allowed_tool_with_custom_allowlist(self):
        result = call_mcp_tool(
            self.registry, "fake_tool", {"x": "hi"}, allowlist={"fake_tool"},
        )
        self.assertEqual(result, "result:hi")

    def test_disallowed_tool_returns_json_error(self):
        result = call_mcp_tool(
            self.registry, "run_shell_command", {},
            allowlist={"fake_tool"},
        )
        data = json.loads(result)
        self.assertIn("未在允许列表中", data["error"])
        self.assertIn("run_shell_command", data["error"])

    def test_unknown_tool_returns_json_error(self):
        result = call_mcp_tool(
            self.registry, "nonexistent_tool", {},
            allowlist={"nonexistent_tool"},
        )
        data = json.loads(result)
        self.assertIn("未知工具", data["error"])

    def test_malformed_args_returns_json_error(self):
        result = call_mcp_tool(
            self.registry, "strict_tool", {},
            allowlist={"strict_tool"},
        )
        data = json.loads(result)
        self.assertIn("参数错误", data["error"])

    def test_handler_error_returns_json_error(self):
        result = call_mcp_tool(
            self.registry, "explode_tool", {},
            allowlist={"explode_tool"},
        )
        data = json.loads(result)
        self.assertEqual(data["error"], "工具调用失败")

    def test_handler_error_does_not_leak_secret(self):
        secret = "sk-super-secret-token-REDACTED-12345"
        self.registry.register(
            "leaky_tool",
            "Raises with a secret.",
            lambda: (_ for _ in ()).throw(RuntimeError(secret)),
            parameters={"type": "object", "properties": {}},
        )
        result = call_mcp_tool(
            self.registry, "leaky_tool", {},
            allowlist={"leaky_tool"},
        )
        self.assertNotIn(secret, result)
        data = json.loads(result)
        self.assertEqual(data["error"], "工具调用失败")

    def test_long_output_is_truncated(self):
        self.registry.register(
            "long_tool",
            "Returns long text.",
            lambda: "Z" * 5000,
            parameters={"type": "object", "properties": {}},
        )
        result = call_mcp_tool(
            self.registry, "long_tool", {},
            allowlist={"long_tool"},
        )
        self.assertIn("truncated", result)
        self.assertLess(len(result), 5000)


class MissingDependencyTests(unittest.TestCase):
    """Missing mcp dependency returns a clear message."""

    def test_create_server_raises_without_mcp(self):
        registry = ToolRegistry()
        with self.assertRaises(ImportError) as ctx:
            create_server(registry)
        self.assertIn("mcp", str(ctx.exception).lower())

    def test_import_module_without_mcp_succeeds(self):
        """The module itself must be importable without mcp."""
        import importlib
        mod = importlib.import_module("mini_agent.mcp_server")
        self.assertTrue(hasattr(mod, "DEFAULT_ALLOWLIST"))
        self.assertTrue(hasattr(mod, "create_server"))
        self.assertTrue(hasattr(mod, "main"))


class TruncationTests(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(_truncate("hello"), "hello")

    def test_long_text_truncated(self):
        long = "x" * 5000
        result = _truncate(long, max_chars=100)
        self.assertEqual(len(result), len("x" * 100 + "\n…[truncated, 5000 chars total]"))
        self.assertIn("truncated", result)


class ExistingRegistryTests(unittest.TestCase):
    """Existing registry behavior remains unchanged."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = NoraDB(Path(self.tmpdir.name) / "test.db")
        self.registry = build_default_registry(
            db=self.db,
            workspace_root=Path(self.tmpdir.name),
            confirm_action=lambda _: True,
        )

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_save_and_search_memory_still_work(self):
        self.registry.call("save_memory", text="mcp test memory", tags="test")
        result = self.registry.call("search_memory", query="mcp test memory")
        self.assertTrue(len(result) > 0)

    def test_calculate_still_works(self):
        result = self.registry.call("calculate", expression="2+3")
        self.assertTrue(len(result) > 0)


if __name__ == "__main__":
    unittest.main()
