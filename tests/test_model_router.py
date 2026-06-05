"""Tests for minimal model routing inspection scaffold."""

import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.model_router import (
    POLICY_VERSION,
    SUPPORTED_PROVIDER_ORDER,
    _determine_route_type,
    _normalize_risk_level,
    _normalize_task_type,
    _select_fallback,
    inspect_model_routing,
    inspect_model_routing_json,
)
from mini_agent.settings import LLMSettings


class TestNormalizeTaskType(unittest.TestCase):
    def test_known_types(self):
        self.assertEqual(_normalize_task_type("code"), "code_generation")
        self.assertEqual(_normalize_task_type("coding"), "code_generation")
        self.assertEqual(_normalize_task_type("review"), "code_review")
        self.assertEqual(_normalize_task_type("test"), "testing")
        self.assertEqual(_normalize_task_type("debug"), "debugging")
        self.assertEqual(_normalize_task_type("fix"), "debugging")
        self.assertEqual(_normalize_task_type("research"), "research")
        self.assertEqual(_normalize_task_type("explain"), "explanation")
        self.assertEqual(_normalize_task_type("document"), "documentation")
        self.assertEqual(_normalize_task_type("plan"), "planning")
        self.assertEqual(_normalize_task_type("chat"), "general")

    def test_unknown_type_defaults_to_general(self):
        self.assertEqual(_normalize_task_type("secret-password-leak"), "general")

    def test_empty_defaults_to_general(self):
        self.assertEqual(_normalize_task_type(""), "general")


class TestNormalizeRiskLevel(unittest.TestCase):
    def test_known_levels(self):
        for level in ("low", "medium", "high", "critical"):
            self.assertEqual(_normalize_risk_level(level), level)

    def test_unknown_defaults_to_low(self):
        self.assertEqual(_normalize_risk_level("extreme"), "low")
        self.assertEqual(_normalize_risk_level(""), "low")


class TestDetermineRouteType(unittest.TestCase):
    def test_high_risk_takes_priority(self):
        self.assertEqual(_determine_route_type("general", "high", 200_000, True, True), "high_risk")
        self.assertEqual(_determine_route_type("general", "critical", 0, False, False), "high_risk")

    def test_review_required(self):
        self.assertEqual(_determine_route_type("general", "low", 0, False, True), "review_required")

    def test_long_context(self):
        self.assertEqual(_determine_route_type("general", "low", 200_000, False, False), "long_context")

    def test_tool_use(self):
        self.assertEqual(_determine_route_type("general", "low", 0, True, False), "tool_use")

    def test_standard(self):
        self.assertEqual(_determine_route_type("general", "low", 0, False, False), "standard")


class TestSelectFallback(unittest.TestCase):
    def test_fallback_available_in_stable_order(self):
        settings = LLMSettings(provider="openai-compatible", base_url="http://x", api_key="k", model="m")
        available, provider = _select_fallback(settings)

        self.assertTrue(available)
        self.assertEqual(provider, "anthropic")
        self.assertEqual(tuple(SUPPORTED_PROVIDER_ORDER), ("openai-compatible", "anthropic", "gemini"))

    def test_unknown_provider_uses_first_supported_fallback(self):
        settings = LLMSettings(provider="unknown", base_url="http://x", api_key="k", model="m")
        available, provider = _select_fallback(settings)

        self.assertTrue(available)
        self.assertEqual(provider, "openai-compatible")


class TestInspectModelRouting(unittest.TestCase):
    def test_configured_route(self):
        settings = LLMSettings(
            provider="openai-compatible",
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
            model="gpt-4.1-mini",
        )
        result = inspect_model_routing(settings)

        self.assertEqual(result["selected_provider"], "openai-compatible")
        self.assertEqual(result["selected_model"], "gpt-4.1-mini")
        self.assertTrue(result["is_llm_enabled"])
        self.assertIn("provider_configured", result["reason_labels"])
        self.assertEqual(result["policy_version"], POLICY_VERSION)
        self.assertEqual(result["errors"], [])

    def test_missing_api_key_disabled(self):
        settings = LLMSettings(
            provider="openai-compatible",
            base_url="https://api.openai.com/v1",
            api_key="",
            model="gpt-4.1-mini",
        )
        result = inspect_model_routing(settings)

        self.assertFalse(result["is_llm_enabled"])
        self.assertIn("provider_disabled", result["reason_labels"])
        self.assertIn("provider_disabled_or_not_fully_configured", result["warnings"])

    def test_unsupported_provider_is_bounded_and_no_raw_echo(self):
        settings = LLMSettings(
            provider="custom-secret-provider",
            base_url="http://x",
            api_key="sk-secret-key",
            model="secret-model-name",
        )
        result = inspect_model_routing(settings)
        result_text = json.dumps(result)

        self.assertEqual(result["selected_provider"], "unsupported")
        self.assertEqual(result["selected_model"], "")
        self.assertFalse(result["is_llm_enabled"])
        self.assertIn("unsupported_provider", result["errors"])
        self.assertIn("unsupported_provider", result["warnings"])
        self.assertNotIn("custom-secret-provider", result_text)
        self.assertNotIn("secret-model-name", result_text)
        self.assertNotIn("sk-secret-key", result_text)

    def test_anthropic_and_gemini_supported_routes(self):
        cases = [
            LLMSettings(
                provider="anthropic",
                base_url="https://api.anthropic.com/v1",
                api_key="k",
                model="claude-sonnet-4-5",
            ),
            LLMSettings(
                provider="gemini",
                base_url="https://generativelanguage.googleapis.com/v1beta",
                api_key="k",
                model="gemini-2.5-pro",
            ),
        ]

        for settings in cases:
            with self.subTest(provider=settings.provider):
                result = inspect_model_routing(settings)
                self.assertEqual(result["selected_provider"], settings.provider)
                self.assertEqual(result["selected_model"], settings.model)
                self.assertTrue(result["capabilities"]["provider_known"])

    def test_task_type_hint(self):
        settings = LLMSettings(provider="anthropic", base_url="https://api.anthropic.com", api_key="k", model="claude")
        result = inspect_model_routing(settings, task_type="review")

        self.assertEqual(result["task_type"], "code_review")
        self.assertIn("task_type:code_review", result["reason_labels"])

    def test_risk_level_hint(self):
        settings = LLMSettings(provider="gemini", base_url="https://api.google.com", api_key="k", model="gemini")
        result = inspect_model_routing(settings, risk_level="high")

        self.assertEqual(result["risk_level"], "high")
        self.assertIn("risk_level:high", result["reason_labels"])
        self.assertEqual(result["route_type"], "high_risk")

    def test_context_tokens_long_context(self):
        settings = LLMSettings(provider="openai-compatible", base_url="http://x", api_key="k", model="m")
        result = inspect_model_routing(settings, context_tokens=150_000)

        self.assertEqual(result["route_type"], "long_context")
        self.assertIn("long_context", result["reason_labels"])

    def test_requires_tools(self):
        settings = LLMSettings(provider="openai-compatible", base_url="http://x", api_key="k", model="m")
        result = inspect_model_routing(settings, requires_tools=True)

        self.assertEqual(result["route_type"], "tool_use")
        self.assertIn("requires_tools", result["reason_labels"])

    def test_requires_review(self):
        settings = LLMSettings(provider="openai-compatible", base_url="http://x", api_key="k", model="m")
        result = inspect_model_routing(settings, requires_review=True)

        self.assertEqual(result["route_type"], "review_required")
        self.assertIn("requires_review", result["reason_labels"])

    def test_invalid_context_tokens_are_bounded(self):
        settings = LLMSettings(provider="openai-compatible", base_url="http://x", api_key="k", model="m")
        result = inspect_model_routing(settings, context_tokens=-1)

        self.assertEqual(result["route_type"], "standard")
        self.assertIn("invalid_context_tokens_defaulted", result["warnings"])

    def test_no_secret_or_raw_prompt_leak(self):
        settings = LLMSettings(
            provider="openai-compatible",
            base_url="https://api.openai.com/v1",
            api_key="sk-super-secret-key-12345",
            model="gpt-4.1-mini",
        )
        result = inspect_model_routing(settings, task_type="secret-password-leak")
        result_text = json.dumps(result)

        self.assertNotIn("sk-super-secret-key-12345", result_text)
        self.assertNotIn("api_key", result_text.lower())
        self.assertNotIn("secret-password-leak", result_text)

    def test_capabilities_present(self):
        settings = LLMSettings(provider="openai-compatible", base_url="http://x", api_key="k", model="m")
        result = inspect_model_routing(settings)
        caps = result["capabilities"]

        self.assertIn("supports_tools", caps)
        self.assertIn("supports_vision", caps)
        self.assertIn("max_context_hint", caps)
        self.assertIn("provider_known", caps)


class TestInspectModelRoutingJson(unittest.TestCase):
    def test_returns_json_string(self):
        settings = LLMSettings(provider="openai-compatible", base_url="http://x", api_key="k", model="m")
        result = inspect_model_routing_json(settings=settings)
        parsed = json.loads(result)

        self.assertIsInstance(result, str)
        self.assertEqual(parsed["selected_provider"], "openai-compatible")

    def test_invalid_settings_object_returns_safe_json_error(self):
        parsed = json.loads(inspect_model_routing_json(settings=None))

        self.assertEqual(parsed["route_type"], "error")
        self.assertIn("invalid_settings", parsed["errors"])


class TestRegistryTool(unittest.TestCase):
    def test_tool_registered(self):
        from mini_agent.toolkits import build_default_registry

        reg = build_default_registry()
        tool_names = [t.name for t in reg._tools.values()]

        self.assertIn("inspect_model_routing", tool_names)

    def test_tool_permission(self):
        from mini_agent.toolkits import build_default_registry

        reg = build_default_registry()
        tool = reg._tools["inspect_model_routing"]

        self.assertEqual(tool.permission.category, "local")
        self.assertEqual(tool.permission.risk, "read")
        self.assertFalse(tool.permission.requires_confirmation)

    def test_tool_uses_injected_settings_without_secret_leak(self):
        from mini_agent.toolkits import build_default_registry

        settings = LLMSettings(
            provider="anthropic",
            base_url="https://api.anthropic.com/v1",
            api_key="sk-not-real",
            model="claude-sonnet-4-5",
        )
        reg = build_default_registry(settings=settings)
        result = reg.call("inspect_model_routing")
        parsed = json.loads(result)

        self.assertEqual(parsed["selected_provider"], "anthropic")
        self.assertEqual(parsed["selected_model"], "claude-sonnet-4-5")
        self.assertEqual(parsed["policy_version"], POLICY_VERSION)
        self.assertNotIn("sk-not-real", result)

    def test_tool_without_settings_returns_safe_error(self):
        from mini_agent.toolkits import build_default_registry

        reg = build_default_registry()
        result = reg.call("inspect_model_routing")
        parsed = json.loads(result)

        self.assertEqual(parsed["route_type"], "error")
        self.assertIn("invalid_settings", parsed["errors"])

    def test_tool_with_hints(self):
        from mini_agent.toolkits import build_default_registry

        settings = LLMSettings(provider="openai-compatible", base_url="http://x", api_key="k", model="m")
        reg = build_default_registry(settings=settings)
        result = reg.call("inspect_model_routing", task_type="code", risk_level="high")
        parsed = json.loads(result)

        self.assertEqual(parsed["task_type"], "code_generation")
        self.assertEqual(parsed["risk_level"], "high")
        self.assertEqual(parsed["route_type"], "high_risk")

    def test_tool_no_mutation(self):
        from mini_agent.toolkits import build_default_registry
        from mini_agent.database import NoraDB

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db = NoraDB(root / "nora.db")
            settings = LLMSettings(provider="openai-compatible", base_url="http://x", api_key="k", model="m")
            reg = build_default_registry(workspace_root=root, db=db, settings=settings)
            events_before = len(reg.event_store.list_events())

            reg.call("inspect_model_routing", task_type="test")

            events_after = len(reg.event_store.list_events())
            self.assertEqual(events_before, events_after)
            self.assertEqual(reg.durable_task_store.list_tasks(), [])
            self.assertEqual(reg.durable_worker_store.list_workers(), [])


if __name__ == "__main__":
    unittest.main()
