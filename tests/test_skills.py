"""Tests for skill manifest v1 parsing, validation, and inspection (TASK-116)."""

import json
import unittest
from pathlib import Path

from mini_agent.skills import (
    MAX_DESCRIPTION_LENGTH,
    MAX_LIST_ITEMS,
    MAX_LIST_ITEM_LENGTH,
    MAX_STRING_LENGTH,
    SkillManifest,
    SkillManifestValidationResult,
    inspect_skill_manifest,
    inspect_skill_manifest_json,
    manifest_to_safe_dict,
    parse_skill_manifest,
    parse_skill_manifest_json,
)

SECRET_SENTINEL = "sk-TASK116-SECRET-SENTINEL"


def _valid_manifest_dict(**overrides):
    """Helper: build a minimal valid skill manifest dict."""
    base = {
        "name": "test-skill",
        "version": "1.0.0",
        "description": "A test skill pack",
        "domains": ["coding"],
        "capabilities": ["search"],
        "workflows": ["code-review"],
        "deliverables": ["report"],
        "required_plugins": ["git-tools"],
        "risk_boundaries": ["no-shell"],
        "evals": ["test-eval"],
    }
    base.update(overrides)
    return base


class TestParseSkillManifestValid(unittest.TestCase):

    def test_valid_minimal(self):
        data = {"name": "s", "version": "1"}
        result = parse_skill_manifest(data)
        self.assertTrue(result.valid)
        self.assertEqual(result.manifest.name, "s")
        self.assertEqual(result.manifest.version, "1")
        self.assertEqual(result.manifest.description, "")
        self.assertEqual(result.manifest.domains, ())

    def test_valid_full(self):
        data = _valid_manifest_dict()
        result = parse_skill_manifest(data)
        self.assertTrue(result.valid)
        self.assertEqual(result.manifest.name, "test-skill")
        self.assertEqual(result.manifest.domains, ("coding",))
        self.assertEqual(result.manifest.capabilities, ("search",))
        self.assertEqual(result.manifest.workflows, ("code-review",))
        self.assertEqual(result.manifest.deliverables, ("report",))
        self.assertEqual(result.manifest.required_plugins, ("git-tools",))
        self.assertEqual(result.manifest.risk_boundaries, ("no-shell",))
        self.assertEqual(result.manifest.evals, ("test-eval",))

    def test_description_truncated(self):
        data = {"name": "p", "version": "1", "description": "x" * 1000}
        result = parse_skill_manifest(data)
        self.assertTrue(result.valid)
        self.assertLessEqual(len(result.manifest.description), MAX_DESCRIPTION_LENGTH)

    def test_list_fields_bounded(self):
        data = _valid_manifest_dict(domains=[f"d{i}" for i in range(50)])
        result = parse_skill_manifest(data)
        self.assertTrue(result.valid)
        self.assertLessEqual(len(result.manifest.domains), MAX_LIST_ITEMS)

    def test_list_item_truncated(self):
        data = _valid_manifest_dict(capabilities=["x" * 500])
        result = parse_skill_manifest(data)
        self.assertTrue(result.valid)
        self.assertLessEqual(len(result.manifest.capabilities[0]), MAX_LIST_ITEM_LENGTH)

    def test_unknown_fields_warned(self):
        data = _valid_manifest_dict(unknown_field="value")
        result = parse_skill_manifest(data)
        self.assertTrue(result.valid)
        self.assertTrue(any("unknown field" in w for w in result.warnings))


class TestParseSkillManifestErrors(unittest.TestCase):

    def test_not_a_dict(self):
        result = parse_skill_manifest("not a dict")
        self.assertFalse(result.valid)
        self.assertIn("must be a JSON object", result.errors[0])

    def test_missing_name(self):
        result = parse_skill_manifest({"version": "1"})
        self.assertFalse(result.valid)
        self.assertIn("name", result.errors[0])

    def test_missing_version(self):
        result = parse_skill_manifest({"name": "p"})
        self.assertFalse(result.valid)
        self.assertIn("version", result.errors[0])

    def test_empty_name(self):
        result = parse_skill_manifest({"name": "  ", "version": "1"})
        self.assertFalse(result.valid)

    def test_empty_version(self):
        result = parse_skill_manifest({"name": "p", "version": "  "})
        self.assertFalse(result.valid)

    def test_list_field_not_a_list(self):
        result = parse_skill_manifest({"name": "p", "version": "1", "domains": "bad"})
        self.assertTrue(result.valid)  # warning, not error
        self.assertTrue(any("domains must be a list" in w for w in result.warnings))

    def test_list_item_not_a_string(self):
        data = _valid_manifest_dict(capabilities=[123, True])
        result = parse_skill_manifest(data)
        self.assertTrue(result.valid)
        self.assertTrue(any("item must be a string" in w for w in result.warnings))


class TestParseSkillManifestJson(unittest.TestCase):

    def test_valid_json(self):
        text = json.dumps(_valid_manifest_dict())
        result = parse_skill_manifest_json(text)
        self.assertTrue(result.valid)

    def test_malformed_json(self):
        result = parse_skill_manifest_json("{bad json")
        self.assertFalse(result.valid)
        self.assertIn("invalid JSON", result.errors[0])

    def test_non_string_input(self):
        result = parse_skill_manifest_json(123)
        self.assertFalse(result.valid)
        self.assertIn("must be a string", result.errors[0])

    def test_json_array(self):
        result = parse_skill_manifest_json("[1, 2, 3]")
        self.assertFalse(result.valid)


class TestInspectSkillManifest(unittest.TestCase):

    def test_inspect_valid(self):
        data = _valid_manifest_dict()
        out = inspect_skill_manifest(data)
        self.assertTrue(out["valid"])
        self.assertIn("manifest", out)
        self.assertEqual(out["manifest"]["name"], "test-skill")

    def test_inspect_invalid(self):
        out = inspect_skill_manifest({"name": "p"})
        self.assertFalse(out["valid"])
        self.assertIn("errors", out)

    def test_inspect_json_valid(self):
        text = json.dumps(_valid_manifest_dict())
        out = inspect_skill_manifest_json(text)
        self.assertTrue(out["valid"])

    def test_inspect_json_malformed(self):
        out = inspect_skill_manifest_json("{bad")
        self.assertFalse(out["valid"])


class TestManifestToSafeDict(unittest.TestCase):

    def test_output_is_deterministic(self):
        data = _valid_manifest_dict()
        r1 = parse_skill_manifest(data)
        r2 = parse_skill_manifest(data)
        self.assertEqual(manifest_to_safe_dict(r1.manifest), manifest_to_safe_dict(r2.manifest))

    def test_no_raw_secrets_in_output(self):
        data = _valid_manifest_dict(
            name="my-skill",
            domains=["api_key_region"],
            capabilities=["token_manager"],
        )
        out = inspect_skill_manifest(data)
        text = json.dumps(out)
        self.assertNotIn("sk-", text)
        self.assertNotIn("SECRET", text)


class TestSentinelNoLeak(unittest.TestCase):
    """Secret-like sentinels must never appear in inspect_skill_manifest output."""

    def _assert_no_sentinel(self, data):
        out = inspect_skill_manifest(data)
        text = json.dumps(out)
        self.assertNotIn(SECRET_SENTINEL, text,
                         f"sentinel leaked in inspect_skill_manifest output")

    def test_name_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": SECRET_SENTINEL, "version": "1"})

    def test_description_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": "p", "version": "1", "description": SECRET_SENTINEL})

    def test_domains_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": "p", "version": "1", "domains": [SECRET_SENTINEL]})

    def test_capabilities_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": "p", "version": "1", "capabilities": [SECRET_SENTINEL]})

    def test_workflows_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": "p", "version": "1", "workflows": [SECRET_SENTINEL]})

    def test_deliverables_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": "p", "version": "1", "deliverables": [SECRET_SENTINEL]})

    def test_required_plugins_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": "p", "version": "1", "required_plugins": [SECRET_SENTINEL]})

    def test_risk_boundaries_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": "p", "version": "1", "risk_boundaries": [SECRET_SENTINEL]})

    def test_evals_sentinel_no_leak(self):
        self._assert_no_sentinel({"name": "p", "version": "1", "evals": [SECRET_SENTINEL]})

    def test_version_sentinel_no_leak(self):
        """Secret-like version must not leak in direct inspect output."""
        out = inspect_skill_manifest({"name": "p", "version": SECRET_SENTINEL})
        text = json.dumps(out)
        self.assertNotIn(SECRET_SENTINEL, text,
                         "sentinel leaked via version in inspect output")

    def test_version_sentinel_no_leak_registry(self):
        """Secret-like version must not leak via registry tool output."""
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        manifest_json = json.dumps({"name": "p", "version": SECRET_SENTINEL})
        result_str = reg.call("inspect_skill_manifest", manifest_json=manifest_json)
        self.assertNotIn(SECRET_SENTINEL, result_str,
                         "sentinel leaked via version in registry output")

    def test_combined_sentinels_no_leak(self):
        data = {
            "name": SECRET_SENTINEL,
            "version": "1",
            "description": SECRET_SENTINEL,
            "domains": [SECRET_SENTINEL],
            "capabilities": [SECRET_SENTINEL],
            "workflows": [SECRET_SENTINEL],
            "deliverables": [SECRET_SENTINEL],
            "required_plugins": [SECRET_SENTINEL],
            "risk_boundaries": [SECRET_SENTINEL],
            "evals": [SECRET_SENTINEL],
        }
        out = inspect_skill_manifest(data)
        text = json.dumps(out)
        self.assertNotIn(SECRET_SENTINEL, text,
                         "sentinel leaked in combined inspect_skill_manifest output")

    def test_unknown_key_sentinel_no_leak(self):
        data = {"name": "p", "version": "1", SECRET_SENTINEL: "v"}
        out = inspect_skill_manifest(data)
        text = json.dumps(out)
        self.assertNotIn(SECRET_SENTINEL, text,
                         "sentinel leaked via unknown key")


class TestReadOnlyNoMutation(unittest.TestCase):
    """inspect_skill_manifest must be read-only: no durable task/worker/event mutation."""

    def test_no_mutation_via_registry(self):
        from mini_agent.registry import ToolRegistry
        from mini_agent.durable_tasks import DurableTaskStore
        from mini_agent.durable_workers import DurableWorkerStore
        from mini_agent.durable_events import DurableEventStore
        import tempfile, os

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test.db"
            reg = ToolRegistry()
            # Wire up durable stores
            dts = DurableTaskStore(db_path)
            dws = DurableWorkerStore(db_path)
            des = DurableEventStore(db_path)
            reg.durable_task_store = dts
            reg.durable_worker_store = dws
            reg.durable_event_store = des

            # Import and register the skill manifest tool
            from mini_agent.skills import inspect_skill_manifest_json

            def _handler(manifest_json: str = "{}") -> str:
                result = inspect_skill_manifest_json(manifest_json)
                return json.dumps(result, ensure_ascii=False, indent=2)

            reg.register(
                "inspect_skill_manifest", "test", _handler,
                parameters={"type": "object", "properties": {"manifest_json": {"type": "string"}}, "required": ["manifest_json"]},
            )

            # Snapshot state
            tasks_before = dts.list_tasks()
            workers_before = dws.list_workers()
            events_before = des.list_events()

            # Call inspect
            text = json.dumps(_valid_manifest_dict())
            result = reg.call("inspect_skill_manifest", manifest_json=text)
            parsed = json.loads(result)
            self.assertTrue(parsed["valid"])

            # Verify no mutation
            tasks_after = dts.list_tasks()
            workers_after = dws.list_workers()
            events_after = des.list_events()
            self.assertEqual(len(tasks_after), len(tasks_before))
            self.assertEqual(len(workers_after), len(workers_before))
            self.assertEqual(len(events_after), len(events_before))


class TestConstants(unittest.TestCase):

    def test_max_string_length_positive(self):
        self.assertGreater(MAX_STRING_LENGTH, 0)

    def test_max_list_items_positive(self):
        self.assertGreater(MAX_LIST_ITEMS, 0)

    def test_max_description_length_positive(self):
        self.assertGreater(MAX_DESCRIPTION_LENGTH, 0)


class TestRegistryPermission(unittest.TestCase):
    """inspect_skill_manifest must be registered with exact ToolPermission(category='local', risk='read')."""

    def test_exact_permission(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        tool = reg._tools.get("inspect_skill_manifest")
        self.assertIsNotNone(tool, "inspect_skill_manifest not registered")
        self.assertEqual(tool.permission.category, "local")
        self.assertEqual(tool.permission.risk, "read")


if __name__ == "__main__":
    unittest.main()
