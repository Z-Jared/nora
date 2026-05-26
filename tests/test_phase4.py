import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.config import validate_agent_config
from mini_agent.metrics import RequestMetrics
from mini_agent.plugins import load_plugins
from mini_agent.registry import ToolRegistry


class ConfigValidationTests(unittest.TestCase):
    def test_valid_config_no_warnings(self):
        data = {
            "llm": {"provider": "openai", "model": "gpt-4"},
            "safety": {"mode": "normal"},
        }
        warnings = validate_agent_config(data)
        self.assertEqual(warnings, [])

    def test_warns_unknown_top_key(self):
        data = {"unknown_key": "value"}
        warnings = validate_agent_config(data)
        self.assertTrue(any("unknown_key" in w for w in warnings))

    def test_warns_unknown_section_key(self):
        data = {"llm": {"unknown_field": "value"}}
        warnings = validate_agent_config(data)
        self.assertTrue(any("llm.unknown_field" in w for w in warnings))

    def test_warns_invalid_safety_mode(self):
        data = {"safety": {"mode": "invalid"}}
        warnings = validate_agent_config(data)
        self.assertTrue(any("safety.mode" in w for w in warnings))

    def test_accepts_strict_safety_mode(self):
        data = {"safety": {"mode": "strict"}}
        warnings = validate_agent_config(data)
        self.assertFalse(any("safety.mode" in w for w in warnings))


class RequestMetricsTests(unittest.TestCase):
    def test_records_requests(self):
        metrics = RequestMetrics()

        metrics.record("/chat", 200, 0.1)
        metrics.record("/chat", 200, 0.2)
        metrics.record("/health", 200, 0.01)

        summary = metrics.summary()
        self.assertEqual(summary["total_requests"], 3)
        self.assertEqual(summary["total_errors"], 0)
        self.assertEqual(summary["endpoints"]["/chat"], 2)
        self.assertEqual(summary["endpoints"]["/health"], 1)

    def test_tracks_errors(self):
        metrics = RequestMetrics()

        metrics.record("/chat", 200, 0.1)
        metrics.record("/chat", 500, 0.5)

        summary = metrics.summary()
        self.assertEqual(summary["total_requests"], 2)
        self.assertEqual(summary["total_errors"], 1)
        self.assertEqual(summary["error_rate"], 0.5)

    def test_records_tool_calls(self):
        metrics = RequestMetrics()

        metrics.record_tool_call("calculate")
        metrics.record_tool_call("calculate")
        metrics.record_tool_call("read_file")

        summary = metrics.summary()
        self.assertEqual(summary["tool_calls"]["calculate"], 2)
        self.assertEqual(summary["tool_calls"]["read_file"], 1)

    def test_latency_percentiles(self):
        metrics = RequestMetrics()

        for i in range(100):
            metrics.record("/chat", 200, i * 0.001)

        summary = metrics.summary()
        self.assertIn("p50", summary["latency_ms"])
        self.assertIn("p95", summary["latency_ms"])
        self.assertIn("p99", summary["latency_ms"])


class PluginSystemTests(unittest.TestCase):
    def test_loads_valid_plugin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "plugins"
            plugins_dir.mkdir()
            plugin_file = plugins_dir / "hello.py"
            plugin_file.write_text(
                'def register(registry):\n'
                '    registry.register("hello_plugin", "A test plugin", lambda: "hello")\n',
                encoding="utf-8",
            )
            registry = ToolRegistry()

            loaded = load_plugins(registry, plugins_dir)

            self.assertEqual(loaded, ["hello"])
            self.assertEqual(registry.call("hello_plugin"), "hello")

    def test_skips_private_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "plugins"
            plugins_dir.mkdir()
            (plugins_dir / "_private.py").write_text('def register(r): pass\n', encoding="utf-8")
            registry = ToolRegistry()

            loaded = load_plugins(registry, plugins_dir)

            self.assertEqual(loaded, [])

    def test_handles_missing_plugins_dir(self):
        registry = ToolRegistry()

        loaded = load_plugins(registry, Path("/nonexistent"))

        self.assertEqual(loaded, [])

    def test_handles_broken_plugin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "plugins"
            plugins_dir.mkdir()
            (plugins_dir / "broken.py").write_text('raise ImportError("bad")\n', encoding="utf-8")
            registry = ToolRegistry()

            loaded = load_plugins(registry, plugins_dir)

            self.assertEqual(loaded, [])


if __name__ == "__main__":
    unittest.main()
