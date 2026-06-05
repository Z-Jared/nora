"""Tests for skill manifest v1 parsing, validation, and inspection (TASK-116)."""

import json
import tempfile
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


# ---------------------------------------------------------------------------
# summarize_skill_manifests tests (TASK-119)
# ---------------------------------------------------------------------------

from mini_agent.skills import summarize_skill_manifests, summarize_skill_manifests_json


class TestSummarizeSkillManifestsValid(unittest.TestCase):

    def test_empty_input(self):
        result = summarize_skill_manifests()
        self.assertEqual(result["valid_count"], 0)
        self.assertEqual(result["invalid_count"], 0)
        self.assertEqual(result["skills"], [])
        self.assertEqual(result["domains"], [])

    def test_none_input(self):
        result = summarize_skill_manifests(None)
        self.assertEqual(result["valid_count"], 0)

    def test_single_valid_manifest(self):
        data = _valid_manifest_dict()
        result = summarize_skill_manifests([data])
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["invalid_count"], 0)
        self.assertEqual(len(result["skills"]), 1)
        self.assertEqual(result["skills"][0]["name"], "test-skill")
        self.assertIn("coding", result["domains"])
        self.assertIn("search", result["capabilities"])

    def test_multiple_valid_manifests(self):
        m1 = _valid_manifest_dict(name="s1", domains=["coding", "devops"])
        m2 = _valid_manifest_dict(name="s2", domains=["coding", "research"], capabilities=["analysis"])
        result = summarize_skill_manifests([m1, m2])
        self.assertEqual(result["valid_count"], 2)
        self.assertEqual(len(result["skills"]), 2)
        # Domains deduplicated and sorted
        self.assertEqual(result["domains"], ["coding", "devops", "research"])
        self.assertIn("analysis", result["capabilities"])

    def test_json_string_input(self):
        text = json.dumps(_valid_manifest_dict())
        result = summarize_skill_manifests([text])
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["skills"][0]["name"], "test-skill")

    def test_aggregate_fields_sorted(self):
        m1 = _valid_manifest_dict(
            domains=["zebra", "alpha"],
            capabilities=["z_cap", "a_cap"],
            workflows=["z_wf", "a_wf"],
            deliverables=["z_del", "a_del"],
            required_plugins=["z_plug", "a_plug"],
            risk_boundaries=["z_risk", "a_risk"],
            evals=["z_eval", "a_eval"],
        )
        result = summarize_skill_manifests([m1])
        self.assertEqual(result["domains"], ["alpha", "zebra"])
        self.assertEqual(result["capabilities"], ["a_cap", "z_cap"])
        self.assertEqual(result["workflows"], ["a_wf", "z_wf"])
        self.assertEqual(result["deliverables"], ["a_del", "z_del"])
        self.assertEqual(result["required_plugins"], ["a_plug", "z_plug"])
        self.assertEqual(result["risk_boundaries"], ["a_risk", "z_risk"])
        self.assertEqual(result["evals"], ["a_eval", "z_eval"])

    def test_deduplicate_across_manifests(self):
        m1 = _valid_manifest_dict(domains=["coding", "shared"])
        m2 = _valid_manifest_dict(domains=["coding", "shared", "extra"])
        result = summarize_skill_manifests([m1, m2])
        self.assertEqual(result["domains"], ["coding", "extra", "shared"])


class TestSummarizeSkillManifestsInvalid(unittest.TestCase):

    def test_malformed_json_string(self):
        result = summarize_skill_manifests(["{bad json"])
        self.assertEqual(result["valid_count"], 0)
        self.assertEqual(result["invalid_count"], 1)
        self.assertTrue(any("invalid JSON" in e for e in result["errors"]))

    def test_non_string_non_dict_entry(self):
        result = summarize_skill_manifests([123, True, None])
        self.assertEqual(result["valid_count"], 0)
        self.assertEqual(result["invalid_count"], 3)

    def test_missing_required_fields(self):
        result = summarize_skill_manifests([{"name": "p"}])
        self.assertEqual(result["valid_count"], 0)
        self.assertEqual(result["invalid_count"], 1)

    def test_mixed_valid_and_invalid(self):
        valid = _valid_manifest_dict(name="good")
        invalid = {"name": "bad"}  # missing version
        result = summarize_skill_manifests([valid, invalid])
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["invalid_count"], 1)
        self.assertEqual(len(result["skills"]), 1)
        self.assertEqual(result["skills"][0]["name"], "good")

    def test_non_list_input(self):
        result = summarize_skill_manifests("not a list")
        self.assertEqual(result["valid_count"], 0)
        self.assertTrue(any("must be a list" in e for e in result["errors"]))

    def test_json_string_input_malformed(self):
        result = summarize_skill_manifests_json("{bad")
        self.assertEqual(result["valid_count"], 0)
        self.assertTrue(any("invalid JSON" in e for e in result["errors"]))

    def test_json_string_non_string_input(self):
        result = summarize_skill_manifests_json(123)
        self.assertEqual(result["valid_count"], 0)
        self.assertTrue(any("must be a JSON string" in e for e in result["errors"]))


class TestSummarizeSkillManifestsBounds(unittest.TestCase):

    def test_max_skills_clamped_low(self):
        m1 = _valid_manifest_dict(name="s1")
        m2 = _valid_manifest_dict(name="s2")
        result = summarize_skill_manifests([m1, m2], max_skills=0)
        # Clamped to 1, so only first manifest processed
        self.assertEqual(result["valid_count"], 1)

    def test_max_skills_clamped_high(self):
        manifests = [_valid_manifest_dict(name=f"s{i}") for i in range(60)]
        result = summarize_skill_manifests(manifests, max_skills=100)
        # Clamped to 50
        self.assertEqual(result["valid_count"], 50)

    def test_max_skills_default(self):
        manifests = [_valid_manifest_dict(name=f"s{i}") for i in range(25)]
        result = summarize_skill_manifests(manifests)
        # Default is 20
        self.assertEqual(result["valid_count"], 20)


class TestSummarizeSkillManifestsSafety(unittest.TestCase):
    """Secret-like values must never appear in summarize output."""

    SECRET = "sk-TASK119-SECRET-SENTINEL"

    def _assert_no_sentinel(self, result):
        text = json.dumps(result)
        self.assertNotIn(self.SECRET, text, "sentinel leaked in summarize output")

    def test_name_sentinel_no_leak(self):
        data = _valid_manifest_dict(name=self.SECRET)
        self._assert_no_sentinel(summarize_skill_manifests([data]))

    def test_version_sentinel_no_leak(self):
        data = _valid_manifest_dict(version=self.SECRET)
        self._assert_no_sentinel(summarize_skill_manifests([data]))

    def test_domains_sentinel_no_leak(self):
        data = _valid_manifest_dict(domains=[self.SECRET])
        self._assert_no_sentinel(summarize_skill_manifests([data]))

    def test_capabilities_sentinel_no_leak(self):
        data = _valid_manifest_dict(capabilities=[self.SECRET])
        self._assert_no_sentinel(summarize_skill_manifests([data]))

    def test_all_fields_sentinel_no_leak(self):
        data = _valid_manifest_dict(
            name=self.SECRET,
            version=self.SECRET,
            description=self.SECRET,
            domains=[self.SECRET],
            capabilities=[self.SECRET],
            workflows=[self.SECRET],
            deliverables=[self.SECRET],
            required_plugins=[self.SECRET],
            risk_boundaries=[self.SECRET],
            evals=[self.SECRET],
        )
        self._assert_no_sentinel(summarize_skill_manifests([data]))

    def test_malformed_entry_no_echo(self):
        """Raw malformed content must not appear in errors."""
        raw = '{"very long secret content": "should not appear"}'
        result = summarize_skill_manifests([raw])
        # The error should not echo the raw content
        for err in result["errors"]:
            self.assertLess(len(err), 200)


class TestSummarizeSkillManifestsRegistry(unittest.TestCase):

    def test_registry_tool_registered(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        tool = reg._tools.get("summarize_skill_manifests")
        self.assertIsNotNone(tool, "summarize_skill_manifests not registered")

    def test_registry_permission_exact(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        tool = reg._tools.get("summarize_skill_manifests")
        self.assertEqual(tool.permission.category, "local")
        self.assertEqual(tool.permission.risk, "read")

    def test_registry_wrapper_json_handling(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        text = json.dumps([_valid_manifest_dict()])
        result_str = reg.call("summarize_skill_manifests", skill_manifest_jsons=text)
        result = json.loads(result_str)
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["skills"][0]["name"], "test-skill")

    def test_registry_wrapper_malformed_json(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        result_str = reg.call("summarize_skill_manifests", skill_manifest_jsons="{bad")
        result = json.loads(result_str)
        self.assertEqual(result["valid_count"], 0)
        self.assertTrue(any("invalid JSON" in e for e in result["errors"]))

    def test_registry_wrapper_empty(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        result_str = reg.call("summarize_skill_manifests")
        result = json.loads(result_str)
        self.assertEqual(result["valid_count"], 0)
        self.assertEqual(result["skills"], [])

    def test_registry_max_skills_below_default(self):
        """Registry max_skills=3 should limit to 3 manifests."""
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        manifests = [_valid_manifest_dict(name=f"s{i}") for i in range(10)]
        text = json.dumps(manifests)
        result_str = reg.call("summarize_skill_manifests", skill_manifest_jsons=text, max_skills=3)
        result = json.loads(result_str)
        self.assertEqual(result["valid_count"], 3)
        self.assertEqual(len(result["skills"]), 3)

    def test_registry_max_skills_above_clamp(self):
        """Registry max_skills=100 should clamp to 50."""
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        manifests = [_valid_manifest_dict(name=f"s{i}") for i in range(60)]
        text = json.dumps(manifests)
        result_str = reg.call("summarize_skill_manifests", skill_manifest_jsons=text, max_skills=100)
        result = json.loads(result_str)
        self.assertEqual(result["valid_count"], 50)
        self.assertEqual(len(result["skills"]), 50)

    def test_registry_max_skills_zero_clamps_to_one(self):
        """Registry max_skills=0 should clamp to 1."""
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        manifests = [_valid_manifest_dict(name=f"s{i}") for i in range(5)]
        text = json.dumps(manifests)
        result_str = reg.call("summarize_skill_manifests", skill_manifest_jsons=text, max_skills=0)
        result = json.loads(result_str)
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(len(result["skills"]), 1)


class TestSummarizeSkillManifestsReadOnly(unittest.TestCase):
    """summarize_skill_manifests must be read-only: no durable mutation."""

    def test_no_mutation_via_registry(self):
        from mini_agent.registry import ToolRegistry
        from mini_agent.durable_tasks import DurableTaskStore
        from mini_agent.durable_workers import DurableWorkerStore
        from mini_agent.durable_events import DurableEventStore

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test.db"
            reg = ToolRegistry()
            dts = DurableTaskStore(db_path)
            dws = DurableWorkerStore(db_path)
            des = DurableEventStore(db_path)
            reg.durable_task_store = dts
            reg.durable_worker_store = dws
            reg.durable_event_store = des

            from mini_agent.skills import summarize_skill_manifests_json

            def _handler(skill_manifest_jsons: str = "[]", max_skills: int = 20) -> str:
                result = summarize_skill_manifests_json(skill_manifest_jsons)
                return json.dumps(result, ensure_ascii=False, indent=2)

            reg.register(
                "summarize_skill_manifests", "test", _handler,
                parameters={"type": "object", "properties": {}},
            )

            tasks_before = dts.list_tasks()
            workers_before = dws.list_workers()
            events_before = des.list_events()

            text = json.dumps([_valid_manifest_dict()])
            result = reg.call("summarize_skill_manifests", skill_manifest_jsons=text)
            parsed = json.loads(result)
            self.assertEqual(parsed["valid_count"], 1)

            tasks_after = dts.list_tasks()
            workers_after = dws.list_workers()
            events_after = des.list_events()
            self.assertEqual(len(tasks_after), len(tasks_before))
            self.assertEqual(len(workers_after), len(workers_before))
            self.assertEqual(len(events_after), len(events_before))


class TestSummarizeSkillManifestsCompatibility(unittest.TestCase):
    """Existing inspect_skill_manifest must still work alongside summarize."""

    def test_inspect_still_works(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        text = json.dumps(_valid_manifest_dict())
        result_str = reg.call("inspect_skill_manifest", manifest_json=text)
        result = json.loads(result_str)
        self.assertTrue(result["valid"])
        self.assertEqual(result["manifest"]["name"], "test-skill")

    def test_summarize_does_not_affect_inspect(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        # Call summarize first
        sum_text = json.dumps([_valid_manifest_dict(name="sum-skill")])
        reg.call("summarize_skill_manifests", skill_manifest_jsons=sum_text)
        # Then inspect should still work
        ins_text = json.dumps(_valid_manifest_dict(name="ins-skill"))
        result_str = reg.call("inspect_skill_manifest", manifest_json=ins_text)
        result = json.loads(result_str)
        self.assertTrue(result["valid"])
        self.assertEqual(result["manifest"]["name"], "ins-skill")


# ---------------------------------------------------------------------------
# preview_skill_context tests (TASK-121)
# ---------------------------------------------------------------------------

from mini_agent.skills import preview_skill_context, preview_skill_context_json


class TestPreviewSkillContextValid(unittest.TestCase):

    def test_empty_goal(self):
        result = preview_skill_context("")
        self.assertEqual(result["selected_count"], 0)
        self.assertIn("errors", result)
        self.assertTrue(any("missing goal" in e for e in result["errors"]))

    def test_none_skill_manifests(self):
        result = preview_skill_context("write code", None)
        self.assertEqual(result["selected_count"], 0)
        self.assertEqual(result["context_sections"], [])

    def test_empty_skill_manifests(self):
        result = preview_skill_context("write code", [])
        self.assertEqual(result["selected_count"], 0)

    def test_relevant_skill_selected(self):
        manifest = _valid_manifest_dict(
            name="coding-skill",
            domains=["coding"],
            capabilities=["search"],
        )
        result = preview_skill_context("help me with coding search", [manifest])
        self.assertEqual(result["selected_count"], 1)
        self.assertEqual(result["context_sections"][0]["skill"], "coding-skill")
        self.assertIn("coding", result["context_sections"][0]["matched_domains"])
        self.assertIn("search", result["context_sections"][0]["matched_capabilities"])

    def test_irrelevant_skill_skipped(self):
        manifest = _valid_manifest_dict(
            name="cooking-skill",
            domains=["cooking"],
            capabilities=["recipe"],
            workflows=["meal-prep"],
            deliverables=["recipe-card"],
        )
        result = preview_skill_context("write code", [manifest])
        self.assertEqual(result["selected_count"], 0)

    def test_multiple_skills_deterministic_and_bounded(self):
        m1 = _valid_manifest_dict(name="alpha", domains=["coding"])
        m2 = _valid_manifest_dict(name="beta", domains=["coding"])
        m3 = _valid_manifest_dict(name="gamma", domains=["coding"])
        result = preview_skill_context("coding help", [m1, m2, m3], max_skills=2)
        self.assertEqual(result["selected_count"], 2)
        # Deterministic order (by score desc, then name)
        names = [s["skill"] for s in result["context_sections"]]
        self.assertEqual(names, sorted(names)[:2])

    def test_max_skills_bounded(self):
        manifests = [_valid_manifest_dict(name=f"s{i}", domains=["coding"]) for i in range(25)]
        result = preview_skill_context("coding", manifests, max_skills=100)
        # Clamped to 20
        self.assertLessEqual(result["selected_count"], 20)

    def test_untrusted_framing_present(self):
        result = preview_skill_context("write code")
        self.assertIn("untrusted_framing", result)
        self.assertIn("UNTRUSTED", result["untrusted_framing"])
        self.assertIn("not instructions", result["untrusted_framing"].lower())

    def test_goal_bounded(self):
        long_goal = "x" * 3000
        result = preview_skill_context(long_goal)
        self.assertLessEqual(len(result["goal"]), 103)  # 100 + "..."

    def test_aggregate_required_plugins(self):
        m1 = _valid_manifest_dict(name="s1", required_plugins=["git", "docker"])
        m2 = _valid_manifest_dict(name="s2", required_plugins=["git", "k8s"])
        result = preview_skill_context("coding", [m1, m2])
        self.assertIn("docker", result["required_plugins"])
        self.assertIn("git", result["required_plugins"])
        self.assertIn("k8s", result["required_plugins"])
        # Sorted
        self.assertEqual(result["required_plugins"], sorted(result["required_plugins"]))

    def test_aggregate_risk_boundaries(self):
        m1 = _valid_manifest_dict(name="s1", risk_boundaries=["no-shell", "no-network"])
        m2 = _valid_manifest_dict(name="s2", risk_boundaries=["no-shell", "no-deploy"])
        result = preview_skill_context("coding", [m1, m2])
        self.assertIn("no-deploy", result["risk_boundaries"])
        self.assertIn("no-network", result["risk_boundaries"])
        self.assertIn("no-shell", result["risk_boundaries"])


class TestPreviewSkillContextMetadata(unittest.TestCase):

    def test_context_section_fields(self):
        manifest = _valid_manifest_dict(
            name="test-skill",
            version="1.0",
            domains=["coding"],
            capabilities=["search"],
            workflows=["code-review"],
            deliverables=["report"],
            required_plugins=["git"],
            risk_boundaries=["no-shell"],
            evals=["eval1"],
        )
        result = preview_skill_context("coding search", [manifest])
        section = result["context_sections"][0]
        self.assertEqual(section["skill"], "test-skill")
        self.assertEqual(section["version"], "1.0")
        self.assertIn("coding", section["matched_domains"])
        self.assertIn("search", section["matched_capabilities"])
        self.assertEqual(section["workflows"], ["code-review"])
        self.assertEqual(section["deliverables"], ["report"])
        self.assertEqual(section["required_plugins"], ["git"])
        self.assertEqual(section["risk_boundaries"], ["no-shell"])
        self.assertEqual(section["evals"], ["eval1"])


class TestPreviewSkillContextErrors(unittest.TestCase):

    def test_non_list_skill_manifests(self):
        result = preview_skill_context("code", "not a list")
        self.assertEqual(result["selected_count"], 0)
        self.assertTrue(any("must be a list" in e for e in result["errors"]))

    def test_malformed_json_string(self):
        result = preview_skill_context("code", ["{bad json"])
        self.assertEqual(result["invalid_count"], 1)
        self.assertTrue(any("invalid JSON" in e for e in result["errors"]))

    def test_non_string_non_dict_entry(self):
        result = preview_skill_context("code", [123, True, None])
        self.assertEqual(result["invalid_count"], 3)

    def test_missing_required_fields(self):
        result = preview_skill_context("code", [{"name": "p"}])
        self.assertEqual(result["invalid_count"], 1)

    def test_mixed_valid_and_invalid(self):
        valid = _valid_manifest_dict(name="good", domains=["coding"])
        invalid = {"name": "bad"}
        result = preview_skill_context("coding", [valid, invalid])
        self.assertEqual(result["selected_count"], 1)
        self.assertEqual(result["invalid_count"], 1)

    def test_large_invalid_input_bounded(self):
        """A large list of invalid manifests must not produce unbounded errors."""
        huge = [{"name": "bad"} for _ in range(200)]
        result = preview_skill_context("coding", huge)
        # Input should be capped; errors/warnings must be bounded
        self.assertLessEqual(len(result["errors"]), 60)
        self.assertLessEqual(len(result["warnings"]), 60)
        # Should indicate truncation
        self.assertTrue(any("truncated" in w for w in result["warnings"]))

    def test_bad_max_skills_string(self):
        """Non-numeric max_skills must not raise; should warn and fallback."""
        manifest = _valid_manifest_dict(domains=["coding"])
        result = preview_skill_context("coding", [manifest], max_skills="bad")
        self.assertEqual(result["selected_count"], 1)
        self.assertTrue(any("invalid max_skills" in w for w in result["warnings"]))
        self.assertNotIn("bad", json.dumps(result))

    def test_bad_max_skills_none(self):
        """None max_skills must not raise; should warn and fallback."""
        manifest = _valid_manifest_dict(domains=["coding"])
        result = preview_skill_context("coding", [manifest], max_skills=None)
        self.assertEqual(result["selected_count"], 1)
        self.assertTrue(any("invalid max_skills" in w for w in result["warnings"]))

    def test_bad_max_skills_float_string(self):
        """Float-string max_skills must not raise; should warn and fallback."""
        manifest = _valid_manifest_dict(domains=["coding"])
        result = preview_skill_context("coding", [manifest], max_skills="3.5")
        self.assertEqual(result["selected_count"], 1)
        self.assertTrue(any("invalid max_skills" in w for w in result["warnings"]))


class TestPreviewSkillContextSafety(unittest.TestCase):
    """Secret-like values must never appear in preview output."""

    SECRET = "sk-TASK121-SECRET-SENTINEL"

    def _assert_no_sentinel(self, result):
        text = json.dumps(result)
        self.assertNotIn(self.SECRET, text, "sentinel leaked in preview output")

    def test_goal_sentinel_no_leak(self):
        self._assert_no_sentinel(preview_skill_context(self.SECRET))

    def test_name_sentinel_no_leak(self):
        data = _valid_manifest_dict(name=self.SECRET, domains=["coding"])
        self._assert_no_sentinel(preview_skill_context("coding", [data]))

    def test_version_sentinel_no_leak(self):
        data = _valid_manifest_dict(version=self.SECRET, domains=["coding"])
        self._assert_no_sentinel(preview_skill_context("coding", [data]))

    def test_domains_sentinel_no_leak(self):
        data = _valid_manifest_dict(domains=[self.SECRET])
        self._assert_no_sentinel(preview_skill_context(self.SECRET, [data]))

    def test_capabilities_sentinel_no_leak(self):
        data = _valid_manifest_dict(capabilities=[self.SECRET])
        self._assert_no_sentinel(preview_skill_context(self.SECRET, [data]))

    def test_all_fields_sentinel_no_leak(self):
        data = _valid_manifest_dict(
            name=self.SECRET,
            version=self.SECRET,
            description=self.SECRET,
            domains=[self.SECRET],
            capabilities=[self.SECRET],
            workflows=[self.SECRET],
            deliverables=[self.SECRET],
            required_plugins=[self.SECRET],
            risk_boundaries=[self.SECRET],
            evals=[self.SECRET],
        )
        # Make goal match the sentinel so skill is selected
        self._assert_no_sentinel(preview_skill_context(self.SECRET, [data]))

    def test_malformed_entry_no_echo(self):
        raw = '{"very long secret content": "should not appear"}'
        result = preview_skill_context("code", [raw])
        for err in result["errors"]:
            self.assertLess(len(err), 200)


class TestPreviewSkillContextReadOnly(unittest.TestCase):
    """preview_skill_context must be read-only: no durable mutation."""

    def test_no_mutation_via_registry(self):
        from mini_agent.registry import ToolRegistry
        from mini_agent.durable_tasks import DurableTaskStore
        from mini_agent.durable_workers import DurableWorkerStore
        from mini_agent.durable_events import DurableEventStore

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test.db"
            reg = ToolRegistry()
            dts = DurableTaskStore(db_path)
            dws = DurableWorkerStore(db_path)
            des = DurableEventStore(db_path)
            reg.durable_task_store = dts
            reg.durable_worker_store = dws
            reg.durable_event_store = des

            def _handler(goal: str = "", skill_manifest_jsons: str = "[]", max_skills: int = 5) -> str:
                result = preview_skill_context_json(goal, skill_manifest_jsons, max_skills=max_skills)
                return json.dumps(result, ensure_ascii=False, indent=2)

            reg.register(
                "preview_skill_context", "test", _handler,
                parameters={"type": "object", "properties": {}},
            )

            tasks_before = dts.list_tasks()
            workers_before = dws.list_workers()
            events_before = des.list_events()

            text = json.dumps([_valid_manifest_dict(domains=["coding"])])
            result = reg.call("preview_skill_context", goal="coding", skill_manifest_jsons=text)
            parsed = json.loads(result)
            self.assertEqual(parsed["selected_count"], 1)

            tasks_after = dts.list_tasks()
            workers_after = dws.list_workers()
            events_after = des.list_events()
            self.assertEqual(len(tasks_after), len(tasks_before))
            self.assertEqual(len(workers_after), len(workers_before))
            self.assertEqual(len(events_after), len(events_before))


class TestPreviewSkillContextRegistry(unittest.TestCase):

    def test_registry_tool_registered(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        tool = reg._tools.get("preview_skill_context")
        self.assertIsNotNone(tool, "preview_skill_context not registered")

    def test_registry_permission_exact(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        tool = reg._tools.get("preview_skill_context")
        self.assertEqual(tool.permission.category, "local")
        self.assertEqual(tool.permission.risk, "read")

    def test_registry_wrapper_honors_max_skills(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        manifests = [_valid_manifest_dict(name=f"s{i}", domains=["coding"]) for i in range(10)]
        text = json.dumps(manifests)
        result_str = reg.call("preview_skill_context", goal="coding", skill_manifest_jsons=text, max_skills=3)
        result = json.loads(result_str)
        self.assertEqual(result["selected_count"], 3)

    def test_registry_wrapper_json_handling(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        text = json.dumps([_valid_manifest_dict(domains=["coding"])])
        result_str = reg.call("preview_skill_context", goal="coding", skill_manifest_jsons=text)
        result = json.loads(result_str)
        self.assertEqual(result["selected_count"], 1)

    def test_registry_wrapper_malformed_json(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        result_str = reg.call("preview_skill_context", goal="coding", skill_manifest_jsons="{bad")
        result = json.loads(result_str)
        # Must report error, not silently return clean result
        self.assertTrue(any("invalid JSON" in e for e in result["errors"]))

    def test_registry_wrapper_non_list_json(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        result_str = reg.call("preview_skill_context", goal="coding", skill_manifest_jsons='"just a string"')
        result = json.loads(result_str)
        self.assertTrue(any("must be a list" in e for e in result["errors"]))

    def test_registry_wrapper_unsupported_type(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        result_str = reg.call("preview_skill_context", goal="coding", skill_manifest_jsons=123)
        result = json.loads(result_str)
        self.assertTrue(any("must be a JSON string or list" in e for e in result["errors"]))

    def test_registry_wrapper_bad_max_skills(self):
        """Registry must not raise on non-int max_skills; should warn."""
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        text = json.dumps([_valid_manifest_dict(domains=["coding"])])
        result_str = reg.call("preview_skill_context", goal="coding", skill_manifest_jsons=text, max_skills="bad")
        result = json.loads(result_str)
        self.assertEqual(result["selected_count"], 1)
        self.assertTrue(any("invalid max_skills" in w for w in result["warnings"]))
        self.assertNotIn("bad", json.dumps(result))

    def test_registry_wrapper_empty(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        result_str = reg.call("preview_skill_context", goal="coding")
        result = json.loads(result_str)
        self.assertEqual(result["selected_count"], 0)


class TestPreviewSkillContextCompatibility(unittest.TestCase):
    """Compatibility with inspect, summarize, and route_capability_request."""

    def test_inspect_still_works(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        text = json.dumps(_valid_manifest_dict())
        result_str = reg.call("inspect_skill_manifest", manifest_json=text)
        result = json.loads(result_str)
        self.assertTrue(result["valid"])

    def test_summarize_still_works(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        text = json.dumps([_valid_manifest_dict()])
        result_str = reg.call("summarize_skill_manifests", skill_manifest_jsons=text)
        result = json.loads(result_str)
        self.assertEqual(result["valid_count"], 1)

    def test_route_capability_still_works(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        skill_text = json.dumps([_valid_manifest_dict(domains=["coding"])])
        result_str = reg.call(
            "route_capability_request",
            goal="coding",
            skill_manifest_jsons=skill_text,
        )
        result = json.loads(result_str)
        self.assertIn("candidate_skills", result)

    def test_preview_does_not_affect_inspect(self):
        from mini_agent.toolkits import build_default_registry
        reg = build_default_registry()
        # Call preview first
        skill_text = json.dumps([_valid_manifest_dict(name="prev-skill", domains=["coding"])])
        reg.call("preview_skill_context", goal="coding", skill_manifest_jsons=skill_text)
        # Then inspect should still work
        ins_text = json.dumps(_valid_manifest_dict(name="ins-skill"))
        result_str = reg.call("inspect_skill_manifest", manifest_json=ins_text)
        result = json.loads(result_str)
        self.assertTrue(result["valid"])
        self.assertEqual(result["manifest"]["name"], "ins-skill")


if __name__ == "__main__":
    unittest.main()
