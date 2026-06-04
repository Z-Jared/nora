"""Tests for optional MCP server adapter (TASK-040, TASK-111).

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
    inspect_mcp_tool_surface,
    is_tool_allowed,
    registry_to_mcp_tools,
    validate_allowlist,
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

    def test_conversion_includes_permission_metadata(self):
        tools = registry_to_mcp_tools(self.registry)
        calc = next(t for t in tools if t["name"] == "calculate")
        self.assertIn("category", calc)
        self.assertIn("risk", calc)
        self.assertIn("requires_confirmation", calc)
        self.assertIsInstance(calc["requires_confirmation"], bool)

    def test_permission_metadata_matches_registry(self):
        tools = registry_to_mcp_tools(self.registry)
        for t in tools:
            perm = self.registry.permission_for(t["name"])
            if perm:
                self.assertEqual(t["category"], perm.category)
                self.assertEqual(t["risk"], perm.risk)
                self.assertEqual(t["requires_confirmation"], perm.requires_confirmation)

    def test_inspection_surface_includes_unexposed_tools(self):
        surface = inspect_mcp_tool_surface(self.registry)
        by_name = {t["name"]: t for t in surface}
        self.assertTrue(by_name["calculate"]["exposed"])
        self.assertFalse(by_name["run_shell_command"]["exposed"])
        self.assertEqual(by_name["run_shell_command"]["block_reason"], "confirmation_required")
        self.assertEqual(by_name["run_shell_command"]["category"], "terminal")
        self.assertEqual(by_name["run_shell_command"]["risk"], "execute")
        self.assertTrue(by_name["run_shell_command"]["requires_confirmation"])

    def test_registry_to_mcp_tools_returns_only_exposed_surface(self):
        surface = inspect_mcp_tool_surface(self.registry)
        exported = registry_to_mcp_tools(self.registry)
        exposed_names = {t["name"] for t in surface if t["exposed"]}
        exported_names = {t["name"] for t in exported}
        self.assertEqual(exported_names, exposed_names)

    def test_inspection_surface_reflects_unsafe_opt_in(self):
        default_surface = inspect_mcp_tool_surface(
            self.registry,
            allowlist={"register_worker"},
        )
        default_register = next(t for t in default_surface if t["name"] == "register_worker")
        self.assertFalse(default_register["exposed"])
        self.assertEqual(default_register["block_reason"], "unsafe_write")

        unsafe_surface = inspect_mcp_tool_surface(
            self.registry,
            allowlist={"register_worker"},
            allow_unsafe_tools=True,
        )
        unsafe_register = next(t for t in unsafe_surface if t["name"] == "register_worker")
        self.assertTrue(unsafe_register["exposed"])
        self.assertNotIn("block_reason", unsafe_register)


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

    def test_custom_allowlist_filters_unsafe_without_opt_in(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        db = NoraDB(Path(tmpdir.name) / "test.db")
        self.addCleanup(db.close)
        registry = build_default_registry(
            db=db, workspace_root=Path(tmpdir.name), confirm_action=lambda _: True,
        )
        tools = registry_to_mcp_tools(registry, allowlist={"calculate", "register_worker"})
        names = {t["name"] for t in tools}
        self.assertEqual(names, {"calculate"})

    def test_custom_allowlist_can_explicitly_include_unsafe(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        db = NoraDB(Path(tmpdir.name) / "test.db")
        self.addCleanup(db.close)
        registry = build_default_registry(
            db=db, workspace_root=Path(tmpdir.name), confirm_action=lambda _: True,
        )
        tools = registry_to_mcp_tools(
            registry,
            allowlist={"register_worker"},
            allow_unsafe_tools=True,
        )
        self.assertEqual([t["name"] for t in tools], ["register_worker"])


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


class ValidateAllowlistTests(unittest.TestCase):
    """validate_allowlist flags high-risk and confirmation-required tools."""

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

    def test_default_allowlist_clean(self):
        result = validate_allowlist(self.registry, set(DEFAULT_ALLOWLIST))
        self.assertEqual(result["high_risk"], [])
        self.assertEqual(result["confirmation_required"], [])

    def test_shell_command_flagged(self):
        result = validate_allowlist(self.registry, {"run_shell_command"})
        self.assertIn("run_shell_command", result["confirmation_required"])
        self.assertIn("run_shell_command", result["high_risk"])

    def test_git_commit_flagged(self):
        result = validate_allowlist(self.registry, {"git_commit_staged"})
        self.assertIn("git_commit_staged", result["confirmation_required"])
        self.assertIn("git_commit_staged", result["high_risk"])

    def test_browser_click_flagged(self):
        result = validate_allowlist(self.registry, {"browser_click"})
        self.assertIn("browser_click", result["high_risk"])
        self.assertIn("browser_click", result["confirmation_required"])

    def test_save_memory_not_flagged(self):
        result = validate_allowlist(self.registry, {"save_memory"})
        self.assertEqual(result["high_risk"], [])
        self.assertEqual(result["confirmation_required"], [])

    def test_task_write_without_confirmation_flagged(self):
        result = validate_allowlist(self.registry, {"register_worker"})
        self.assertIn("register_worker", result["high_risk"])
        self.assertNotIn("register_worker", result["confirmation_required"])

    def test_mixed_allowlist(self):
        result = validate_allowlist(self.registry, {"calculate", "run_shell_command", "save_memory"})
        self.assertIn("run_shell_command", result["confirmation_required"])
        self.assertIn("run_shell_command", result["high_risk"])
        self.assertNotIn("calculate", result["confirmation_required"])
        self.assertNotIn("save_memory", result["high_risk"])

    def test_empty_allowlist(self):
        result = validate_allowlist(self.registry, set())
        self.assertEqual(result["high_risk"], [])
        self.assertEqual(result["confirmation_required"], [])

    def test_unknown_tool_ignored(self):
        result = validate_allowlist(self.registry, {"nonexistent_tool"})
        self.assertEqual(result["high_risk"], [])
        self.assertEqual(result["confirmation_required"], [])


class ConfirmationBlockingTests(unittest.TestCase):
    """call_mcp_tool blocks unsafe tools unless explicitly opted in."""

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

    def test_confirmation_required_tool_blocked(self):
        result = call_mcp_tool(
            self.registry, "run_shell_command", {"command": "echo hi"},
            allowlist={"run_shell_command"},
        )
        data = json.loads(result)
        self.assertIn("权限不允许", data["error"])
        self.assertIn("run_shell_command", data["error"])
        self.assertEqual(data["reason"], "confirmation_required")
        self.assertEqual(data["category"], "terminal")
        self.assertEqual(data["risk"], "execute")

    def test_confirmation_required_tool_blocked_even_if_allowed(self):
        """A tool in the allowlist is still blocked if it requires confirmation."""
        result = call_mcp_tool(
            self.registry, "git_commit_staged", {"message": "test"},
            allowlist={"git_commit_staged"},
        )
        data = json.loads(result)
        self.assertIn("权限不允许", data["error"])
        self.assertEqual(data["reason"], "confirmation_required")

    def test_task_write_without_confirmation_blocked(self):
        result = call_mcp_tool(
            self.registry, "register_worker", {"worker_id": "w_mcp"},
            allowlist={"register_worker"},
        )
        data = json.loads(result)
        self.assertIn("权限不允许", data["error"])
        self.assertEqual(data["reason"], "unsafe_write")
        self.assertEqual(data["category"], "task")
        self.assertEqual(data["risk"], "write")

    def test_explicit_unsafe_opt_in_allows_task_write(self):
        result = call_mcp_tool(
            self.registry, "register_worker", {"worker_id": "w_mcp"},
            allowlist={"register_worker"},
            allow_unsafe_tools=True,
        )
        data = json.loads(result)
        self.assertEqual(data["worker_id"], "w_mcp")

    def test_non_confirmation_tool_works(self):
        result = call_mcp_tool(
            self.registry, "calculate", {"expression": "1+1"},
            allowlist={"calculate"},
        )
        self.assertNotIn("error", result)

    def test_allowlist_rejection_takes_precedence(self):
        """Allowlist rejection is checked before confirmation blocking."""
        result = call_mcp_tool(
            self.registry, "run_shell_command", {},
            allowlist={"calculate"},
        )
        data = json.loads(result)
        self.assertIn("未在允许列表中", data["error"])
        self.assertNotIn("权限不允许", data["error"])

    def test_no_permission_info_not_blocked(self):
        """Tools without permission info are not blocked."""
        reg = ToolRegistry()
        reg.register(
            "bare_tool",
            "No permission set.",
            lambda: "ok",
            parameters={"type": "object", "properties": {}},
        )
        result = call_mcp_tool(reg, "bare_tool", {}, allowlist={"bare_tool"})
        self.assertEqual(result, "ok")


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
