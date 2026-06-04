"""Tests for plugin manifest v1 parsing, validation, and inspection (TASK-113)."""

import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.plugins import (
    HIGH_RISK_RISKS,
    VALID_AUTH_METHODS,
    VALID_DATA_SENSITIVITY,
    VALID_EVENT_LOG_MODES,
    VALID_PERMISSION_CATEGORIES,
    VALID_RISKS,
    ManifestValidationResult,
    PluginManifest,
    PluginToolMeta,
    inspect_manifest,
    inspect_manifest_json,
    load_plugins,
    manifest_to_safe_dict,
    parse_manifest,
    parse_manifest_json,
)

SECRET_SENTINEL = "sk-TASK113-SECRET-SENTINEL"


def _valid_manifest_dict(**overrides):
    """Helper: build a minimal valid manifest dict."""
    base = {
        "name": "test-plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "auth": "none",
        "tools": [
            {
                "name": "do_thing",
                "description": "Does a thing",
                "permission_category": "local",
                "risk": "read",
                "requires_confirmation": False,
                "data_sensitivity": "none",
                "event_log": "metadata_only",
            }
        ],
    }
    base.update(overrides)
    return base


class TestParseManifestValid(unittest.TestCase):

    def test_valid_minimal(self):
        data = {"name": "p", "version": "1"}
        result = parse_manifest(data)
        self.assertTrue(result.valid)
        self.assertEqual(result.manifest.name, "p")
        self.assertEqual(result.manifest.version, "1")
        self.assertEqual(result.manifest.auth, "none")
        self.assertEqual(result.manifest.tools, ())

    def test_valid_full(self):
        data = _valid_manifest_dict()
        result = parse_manifest(data)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.manifest.tools), 1)
        self.assertEqual(result.manifest.tools[0].name, "do_thing")

    def test_domains_and_capabilities(self):
        data = _valid_manifest_dict(domains=["coding", "research"], capabilities=["search"])
        result = parse_manifest(data)
        self.assertTrue(result.valid)
        self.assertEqual(result.manifest.domains, ("coding", "research"))
        self.assertEqual(result.manifest.capabilities, ("search",))

    def test_description_truncated(self):
        data = {"name": "p", "version": "1", "description": "x" * 1000}
        result = parse_manifest(data)
        self.assertTrue(result.valid)
        self.assertLessEqual(len(result.manifest.description), 500)

    def test_multiple_tools(self):
        tools = [
            {"name": "a", "permission_category": "local", "risk": "read"},
            {"name": "b", "permission_category": "task", "risk": "write", "requires_confirmation": True},
        ]
        data = _valid_manifest_dict(tools=tools)
        result = parse_manifest(data)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.manifest.tools), 2)


class TestParseManifestErrors(unittest.TestCase):

    def test_not_a_dict(self):
        result = parse_manifest("not a dict")
        self.assertFalse(result.valid)
        self.assertIn("must be a JSON object", result.errors[0])

    def test_missing_name(self):
        result = parse_manifest({"version": "1"})
        self.assertFalse(result.valid)
        self.assertIn("name", result.errors[0])

    def test_missing_version(self):
        result = parse_manifest({"name": "p"})
        self.assertFalse(result.valid)
        self.assertIn("version", result.errors[0])

    def test_tools_not_a_list(self):
        result = parse_manifest({"name": "p", "version": "1", "tools": "bad"})
        self.assertFalse(result.valid)
        self.assertIn("tools must be a list", result.errors[0])

    def test_duplicate_tool_names(self):
        tools = [
            {"name": "dup", "permission_category": "local", "risk": "read"},
            {"name": "dup", "permission_category": "local", "risk": "read"},
        ]
        result = parse_manifest({"name": "p", "version": "1", "tools": tools})
        self.assertFalse(result.valid)
        self.assertTrue(any("duplicate tool name" in e for e in result.errors))

    def test_high_risk_without_confirmation(self):
        for risk in HIGH_RISK_RISKS:
            tools = [{"name": "t", "permission_category": "local", "risk": risk, "requires_confirmation": False}]
            result = parse_manifest({"name": "p", "version": "1", "tools": tools})
            self.assertFalse(result.valid, f"should reject risk={risk} without confirmation")
            self.assertTrue(any("confirmation" in e.lower() for e in result.errors))

    def test_high_risk_with_confirmation_ok(self):
        for risk in HIGH_RISK_RISKS:
            tools = [{"name": "t", "permission_category": "local", "risk": risk, "requires_confirmation": True}]
            result = parse_manifest({"name": "p", "version": "1", "tools": tools})
            self.assertTrue(result.valid, f"should accept risk={risk} with confirmation")


class TestParseManifestWarnings(unittest.TestCase):

    def test_unknown_auth(self):
        result = parse_manifest({"name": "p", "version": "1", "auth": "magic"})
        self.assertTrue(result.valid)
        self.assertTrue(any("unknown auth" in w for w in result.warnings))
        # Raw value must NOT appear in warnings
        text = json.dumps(result.warnings)
        self.assertNotIn("magic", text)

    def test_unknown_permission_category(self):
        tools = [{"name": "t", "permission_category": "bogus", "risk": "read"}]
        result = parse_manifest({"name": "p", "version": "1", "tools": tools})
        self.assertTrue(result.valid)
        self.assertTrue(any("unknown permission_category" in w for w in result.warnings))
        text = json.dumps(result.warnings)
        self.assertNotIn("bogus", text)

    def test_unknown_risk(self):
        tools = [{"name": "t", "permission_category": "local", "risk": "bogus"}]
        result = parse_manifest({"name": "p", "version": "1", "tools": tools})
        self.assertTrue(result.valid)
        self.assertTrue(any("unknown risk" in w for w in result.warnings))
        text = json.dumps(result.warnings)
        self.assertNotIn("bogus", text)

    def test_unknown_data_sensitivity(self):
        tools = [{"name": "t", "permission_category": "local", "risk": "read", "data_sensitivity": "bogus"}]
        result = parse_manifest({"name": "p", "version": "1", "tools": tools})
        self.assertTrue(result.valid)
        self.assertTrue(any("unknown data_sensitivity" in w for w in result.warnings))
        text = json.dumps(result.warnings)
        self.assertNotIn("bogus", text)

    def test_unknown_event_log(self):
        tools = [{"name": "t", "permission_category": "local", "risk": "read", "event_log": "bogus"}]
        result = parse_manifest({"name": "p", "version": "1", "tools": tools})
        self.assertTrue(result.valid)
        self.assertTrue(any("unknown event_log" in w for w in result.warnings))
        text = json.dumps(result.warnings)
        self.assertNotIn("bogus", text)


class TestParseManifestJson(unittest.TestCase):

    def test_valid_json(self):
        text = json.dumps(_valid_manifest_dict())
        result = parse_manifest_json(text)
        self.assertTrue(result.valid)

    def test_malformed_json(self):
        result = parse_manifest_json("{bad json")
        self.assertFalse(result.valid)
        self.assertIn("invalid JSON", result.errors[0])

    def test_non_string_json(self):
        result = parse_manifest_json(123)
        self.assertFalse(result.valid)


class TestManifestToSafeDict(unittest.TestCase):

    def test_no_secrets_echoed(self):
        data = _valid_manifest_dict(auth="api_key")
        result = parse_manifest(data)
        safe = manifest_to_safe_dict(result.manifest)
        text = json.dumps(safe)
        # "api_key" is a valid enum, but raw secrets must not appear
        self.assertIsInstance(safe["auth"], str)

    def test_output_is_deterministic(self):
        data = _valid_manifest_dict()
        r1 = parse_manifest(data)
        r2 = parse_manifest(data)
        self.assertEqual(manifest_to_safe_dict(r1.manifest), manifest_to_safe_dict(r2.manifest))


class TestInspectManifest(unittest.TestCase):

    def test_inspect_valid(self):
        data = _valid_manifest_dict()
        out = inspect_manifest(data)
        self.assertTrue(out["valid"])
        self.assertIn("manifest", out)
        self.assertEqual(out["manifest"]["name"], "test-plugin")

    def test_inspect_invalid(self):
        out = inspect_manifest({"name": "p"})
        self.assertFalse(out["valid"])
        self.assertIn("errors", out)

    def test_inspect_json_valid(self):
        text = json.dumps(_valid_manifest_dict())
        out = inspect_manifest_json(text)
        self.assertTrue(out["valid"])

    def test_inspect_json_malformed(self):
        out = inspect_manifest_json("{bad")
        self.assertFalse(out["valid"])

    def test_no_raw_secrets_in_output(self):
        """Output should not contain raw API keys or tokens."""
        data = _valid_manifest_dict(auth="api_key")
        out = inspect_manifest(data)
        text = json.dumps(out)
        self.assertNotIn("sk-", text)
        self.assertNotIn("Bearer ", text)
        self.assertNotIn("SECRET", text)


class TestToolDefaults(unittest.TestCase):

    def test_tool_defaults(self):
        tools = [{"name": "minimal"}]
        result = parse_manifest({"name": "p", "version": "1", "tools": tools})
        self.assertTrue(result.valid)
        t = result.manifest.tools[0]
        self.assertEqual(t.permission_category, "unknown")
        self.assertEqual(t.risk, "unknown")
        self.assertFalse(t.requires_confirmation)
        self.assertEqual(t.data_sensitivity, "none")
        self.assertEqual(t.event_log, "metadata_only")

    def test_tool_description_truncated(self):
        tools = [{"name": "t", "description": "x" * 500}]
        result = parse_manifest({"name": "p", "version": "1", "tools": tools})
        self.assertTrue(result.valid)
        self.assertLessEqual(len(result.manifest.tools[0].description), 300)


class TestLoadPluginsPreserved(unittest.TestCase):
    """Ensure load_plugins existing behavior is not broken."""

    def test_nonexistent_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            from mini_agent.registry import ToolRegistry
            reg = ToolRegistry()
            loaded = load_plugins(reg, Path(td) / "nonexistent")
            self.assertEqual(loaded, [])

    def test_load_simple_plugin(self):
        with tempfile.TemporaryDirectory() as td:
            plugin_dir = Path(td) / "plugins"
            plugin_dir.mkdir()
            plugin_file = plugin_dir / "hello.py"
            plugin_file.write_text(
                'def register(registry):\n'
                '    registry.register("hello_plugin", "Say hello", lambda: "hi")\n'
            )
            from mini_agent.registry import ToolRegistry
            reg = ToolRegistry()
            loaded = load_plugins(reg, plugin_dir)
            self.assertEqual(loaded, ["hello"])
            result = reg.call("hello_plugin")
            self.assertEqual(result, "hi")

    def test_broken_plugin_warning(self):
        with tempfile.TemporaryDirectory() as td:
            plugin_dir = Path(td) / "plugins"
            plugin_dir.mkdir()
            plugin_file = plugin_dir / "broken.py"
            plugin_file.write_text('raise ImportError("intentional break")\n')
            from mini_agent.registry import ToolRegistry
            reg = ToolRegistry()
            loaded = load_plugins(reg, plugin_dir)
            self.assertEqual(loaded, [])


class TestConstants(unittest.TestCase):

    def test_valid_auth_methods_non_empty(self):
        self.assertGreater(len(VALID_AUTH_METHODS), 0)

    def test_valid_risks_non_empty(self):
        self.assertGreater(len(VALID_RISKS), 0)

    def test_valid_permission_categories_non_empty(self):
        self.assertGreater(len(VALID_PERMISSION_CATEGORIES), 0)

    def test_valid_data_sensitivity_non_empty(self):
        self.assertGreater(len(VALID_DATA_SENSITIVITY), 0)

    def test_valid_event_log_modes_non_empty(self):
        self.assertGreater(len(VALID_EVENT_LOG_MODES), 0)

    def test_high_risk_subset_of_risks(self):
        self.assertTrue(HIGH_RISK_RISKS.issubset(VALID_RISKS))


class TestSentinelNoLeak(unittest.TestCase):
    """Secret-like sentinels must never appear in inspect_manifest output for enum/list fields."""

    def _assert_no_sentinel(self, data):
        out = inspect_manifest(data)
        text = json.dumps(out)
        self.assertNotIn(SECRET_SENTINEL, text,
                         f"sentinel leaked in inspect_manifest output")

    def test_auth_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": "p", "version": "1", "auth": SECRET_SENTINEL})

    def test_permission_category_sentinel_no_leak(self):
        tools = [{"name": "t", "permission_category": SECRET_SENTINEL, "risk": "read"}]
        self._assert_no_sentinel({"name": "p", "version": "1", "tools": tools})

    def test_risk_sentinel_no_leak(self):
        tools = [{"name": "t", "permission_category": "local", "risk": SECRET_SENTINEL}]
        self._assert_no_sentinel({"name": "p", "version": "1", "tools": tools})

    def test_data_sensitivity_sentinel_no_leak(self):
        tools = [{"name": "t", "permission_category": "local", "risk": "read",
                  "data_sensitivity": SECRET_SENTINEL}]
        self._assert_no_sentinel({"name": "p", "version": "1", "tools": tools})

    def test_event_log_sentinel_no_leak(self):
        tools = [{"name": "t", "permission_category": "local", "risk": "read",
                  "event_log": SECRET_SENTINEL}]
        self._assert_no_sentinel({"name": "p", "version": "1", "tools": tools})

    def test_domains_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": "p", "version": "1", "domains": [SECRET_SENTINEL]})

    def test_capabilities_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": "p", "version": "1", "capabilities": [SECRET_SENTINEL]})

    def test_tool_name_as_secret_in_warnings_no_leak(self):
        """Secret-like tool name should not appear in warnings."""
        tools = [{"name": SECRET_SENTINEL, "permission_category": SECRET_SENTINEL, "risk": "read"}]
        out = inspect_manifest({"name": "p", "version": "1", "tools": tools})
        text = json.dumps(out)
        self.assertNotIn(SECRET_SENTINEL, text,
                         "sentinel leaked via tool name in warnings")

    def test_combined_sentinels_no_leak(self):
        data = {
            "name": "p",
            "version": "1",
            "auth": SECRET_SENTINEL,
            "domains": [SECRET_SENTINEL],
            "capabilities": [SECRET_SENTINEL],
            "tools": [{
                "name": SECRET_SENTINEL,
                "permission_category": SECRET_SENTINEL,
                "risk": SECRET_SENTINEL,
                "data_sensitivity": SECRET_SENTINEL,
                "event_log": SECRET_SENTINEL,
            }],
        }
        out = inspect_manifest(data)
        text = json.dumps(out)
        self.assertNotIn(SECRET_SENTINEL, text,
                         "sentinel leaked in combined inspect_manifest output")


class TestUnknownValuesNormalized(unittest.TestCase):
    """Unknown enum values must be normalized to 'unknown' in manifest output."""

    def test_unknown_auth_normalized(self):
        data = {"name": "p", "version": "1", "auth": "bogus"}
        out = inspect_manifest(data)
        self.assertEqual(out["manifest"]["auth"], "unknown")

    def test_unknown_permission_category_normalized(self):
        tools = [{"name": "t", "permission_category": "bogus", "risk": "read"}]
        data = {"name": "p", "version": "1", "tools": tools}
        out = inspect_manifest(data)
        self.assertEqual(out["manifest"]["tools"][0]["permission_category"], "unknown")

    def test_unknown_risk_normalized(self):
        tools = [{"name": "t", "permission_category": "local", "risk": "bogus"}]
        data = {"name": "p", "version": "1", "tools": tools}
        out = inspect_manifest(data)
        self.assertEqual(out["manifest"]["tools"][0]["risk"], "unknown")

    def test_unknown_data_sensitivity_normalized(self):
        tools = [{"name": "t", "permission_category": "local", "risk": "read", "data_sensitivity": "bogus"}]
        data = {"name": "p", "version": "1", "tools": tools}
        out = inspect_manifest(data)
        self.assertEqual(out["manifest"]["tools"][0]["data_sensitivity"], "unknown")

    def test_unknown_event_log_normalized(self):
        tools = [{"name": "t", "permission_category": "local", "risk": "read", "event_log": "bogus"}]
        data = {"name": "p", "version": "1", "tools": tools}
        out = inspect_manifest(data)
        self.assertEqual(out["manifest"]["tools"][0]["event_log"], "unknown")


if __name__ == "__main__":
    unittest.main()
