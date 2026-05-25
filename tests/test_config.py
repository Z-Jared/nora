import tempfile
import unittest
from pathlib import Path

from mini_agent.config import AgentConfig, load_agent_config
from mini_agent.controller import MiniAgent
from mini_agent.llm import LLMResponse
from mini_agent.settings import load_settings
from mini_agent.tools import build_default_registry

class AgentConfigTests(unittest.TestCase):
    def test_missing_config_uses_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_agent_config(Path(tmpdir) / "agent.yaml")

        self.assertEqual(config.paths.notes, Path("data/notes.txt"))
        self.assertEqual(config.context_window.max_tool_result_chars, 8000)
        self.assertIn("static_server_8000", config.processes.profiles)

    def test_loads_agent_yaml_subset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "agent.yaml"
            path.write_text(
                "\n".join(
                    [
                        "llm:",
                        "  provider: anthropic",
                        "  model: claude-test",
                        "paths:",
                        "  notes: custom/notes.txt",
                        "  tool_logs: custom/tool_calls.jsonl",
                        "  task_history: custom/task_history.jsonl",
                        "context_window:",
                        "  max_tool_result_chars: 40",
                        "  head_chars: 12",
                        "  tail_chars: 8",
                        "rag:",
                        "  include_paths: [\"mini_agent\", \"README.md\"]",
                        "  exclude_dirs: [\"vendor\"]",
                        "  max_file_bytes: 4096",
                        "  chunk_size: 20",
                        "  chunk_overlap: 5",
                        "safety:",
                        "  mode: strict",
                        "  allow_shell_execute: true",
                        "  allow_git_write: false",
                        "  allow_browser_interact: false",
                        "  allow_autonomous_write: false",
                        "tools:",
                        "  disabled: [\"fetch_url\", \"browser_click\"]",
                        "permissions:",
                        "  deny: [\"run_shell_command\"]",
                        "  confirmation_overrides:",
                        "    web_search: true",
                        "    write_project_file: false",
                        "processes:",
                        "  profiles:",
                        "    ready:",
                        "      command: [\"python3\", \"-c\", \"print('ready', flush=True)\"]",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_agent_config(path)

        self.assertEqual(config.llm.provider, "anthropic")
        self.assertEqual(config.llm.model, "claude-test")
        self.assertEqual(config.paths.notes, Path("custom/notes.txt"))
        self.assertEqual(config.paths.tool_logs, Path("custom/tool_calls.jsonl"))
        self.assertEqual(config.paths.task_history, Path("custom/task_history.jsonl"))
        self.assertEqual(config.context_window.max_tool_result_chars, 40)
        self.assertEqual(config.context_window.head_chars, 12)
        self.assertEqual(config.context_window.tail_chars, 8)
        self.assertEqual(config.rag.include_paths, ["mini_agent", "README.md"])
        self.assertEqual(config.rag.exclude_dirs, ["vendor"])
        self.assertEqual(config.rag.max_file_bytes, 4096)
        self.assertEqual(config.rag.chunk_size, 20)
        self.assertEqual(config.rag.chunk_overlap, 5)
        self.assertEqual(config.safety.mode, "strict")
        self.assertTrue(config.safety.allow_shell_execute)
        self.assertFalse(config.safety.allow_git_write)
        self.assertFalse(config.safety.allow_browser_interact)
        self.assertFalse(config.safety.allow_autonomous_write)
        self.assertEqual(config.tools.disabled, {"fetch_url", "browser_click"})
        self.assertEqual(config.permissions.deny, {"run_shell_command"})
        self.assertEqual(
            config.permissions.confirmation_overrides,
            {"web_search": True, "write_project_file": False},
        )
        self.assertEqual(config.processes.profiles["ready"], ["python3", "-c", "print('ready', flush=True)"])

    def test_config_overrides_llm_settings_without_storing_key(self):
        settings = load_settings(
            environ={
                "LLM_PROVIDER": "openai-compatible",
                "LLM_BASE_URL": "https://example.com/v1",
                "LLM_API_KEY": "test-key",
                "LLM_MODEL": "old-model",
            }
        )
        config = AgentConfig.from_dict(
            {"llm": {"provider": "gemini", "model": "gemini-test", "base_url": "https://gemini.test/v1beta"}}
        )

        updated = config.apply_to_llm_settings(settings)

        self.assertEqual(updated.provider, "gemini")
        self.assertEqual(updated.model, "gemini-test")
        self.assertEqual(updated.base_url, "https://gemini.test/v1beta")
        self.assertEqual(updated.api_key, "test-key")

    def test_registry_uses_configured_paths_and_process_profiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "agent.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "paths:",
                        "  notes: state/notes.txt",
                        "  tool_logs: state/tool_calls.jsonl",
                        "processes:",
                        "  profiles:",
                        "    ready:",
                        "      command: [\"python3\", \"-c\", \"print('ready', flush=True)\"]",
                    ]
                ),
                encoding="utf-8",
            )
            config = load_agent_config(config_path)
            registry = build_default_registry(
                workspace_root=root,
                notes_path=config.resolve_path(root, config.paths.notes),
                log_path=config.resolve_path(root, config.paths.tool_logs),
                process_profiles=config.processes.profiles,
                confirm_action=lambda prompt: True,
            )

            self.assertEqual(registry.call("save_note", text="configured"), "笔记已保存。")
            self.assertTrue((root / "state" / "notes.txt").exists())
            started = registry.call("start_background_process", profile="ready", reason="test")
            process_id = started.split()[1]
            self.assertIn("已匹配", registry.call("wait_for_background_process_output", process_id=process_id, pattern="ready"))

    def test_config_can_disable_tools(self):
        config = AgentConfig.from_dict({"tools": {"disabled": ["fetch_url", "browser_click"]}})

        registry = build_default_registry(disabled_tools=config.tools.disabled)
        tool_names = {tool["function"]["name"] for tool in registry.to_openai_tools()}

        self.assertEqual(config.tools.disabled, {"fetch_url", "browser_click"})
        self.assertNotIn("fetch_url", tool_names)
        self.assertNotIn("browser_click", tool_names)
        with self.assertRaises(KeyError):
            registry.call("fetch_url", url="https://example.com")

    def test_config_can_deny_tools_and_override_confirmation(self):
        config = AgentConfig.from_dict(
            {
                "permissions": {
                    "deny": ["run_shell_command"],
                    "confirmation_overrides": {
                        "fetch_url": True,
                        "write_project_file": False,
                    },
                }
            }
        )

        prompts = []
        registry = build_default_registry(
            disabled_tools=config.disabled_tools(),
            permission_overrides=config.permission_overrides(),
            confirm_action=lambda prompt: prompts.append(prompt) or False,
            web_fetch=lambda url, timeout: "ok",
        )
        tool_names = {tool["function"]["name"] for tool in registry.to_openai_tools()}

        self.assertNotIn("run_shell_command", tool_names)
        self.assertEqual(registry.call("fetch_url", url="https://example.com"), "已取消操作。")
        self.assertTrue(prompts)
        self.assertIn("fetch_url", registry.describe_permissions())
        self.assertIn("fetch_url: network/read, 需要确认", registry.describe_permissions())
        with self.assertRaises(KeyError):
            registry.call("run_shell_command", command="pwd")

    def test_strict_safety_mode_disables_high_risk_tools_by_default(self):
        config = AgentConfig.from_dict({"safety": {"mode": "strict"}})

        disabled_tools = config.disabled_tools()

        self.assertIn("run_shell_command", disabled_tools)
        self.assertIn("run_project_tests", disabled_tools)
        self.assertIn("git_stage_paths", disabled_tools)
        self.assertIn("git_commit_staged", disabled_tools)
        self.assertIn("browser_click", disabled_tools)
        self.assertIn("browser_fill", disabled_tools)
        self.assertIn("write_project_file", config.autonomous_disabled_tools())
        self.assertIn("apply_project_patch", config.autonomous_disabled_tools())

    def test_safety_flags_can_allow_specific_risky_tool_groups(self):
        config = AgentConfig.from_dict(
            {
                "safety": {
                    "mode": "strict",
                    "allow_shell_execute": True,
                    "allow_git_write": True,
                    "allow_browser_interact": True,
                    "allow_autonomous_write": True,
                }
            }
        )

        disabled_tools = config.disabled_tools()

        self.assertNotIn("run_shell_command", disabled_tools)
        self.assertNotIn("git_stage_paths", disabled_tools)
        self.assertNotIn("browser_click", disabled_tools)
        self.assertEqual(config.autonomous_disabled_tools(), set())

    def test_autonomous_loop_hides_disabled_tools(self):
        class CapturingToolLLM:
            def __init__(self):
                self.tool_names = []

            def chat(self, messages, tools=None):
                self.tool_names = [tool["function"]["name"] for tool in tools or []]
                return LLMResponse(content="done")

        llm = CapturingToolLLM()
        agent = MiniAgent(
            build_default_registry(),
            llm=llm,
            autonomous_disabled_tools={"write_project_file", "run_shell_command"},
        )

        answer = agent.run_autonomous("检查项目", max_steps=1)

        self.assertIn("done", answer)
        self.assertIn("calculate", llm.tool_names)
        self.assertNotIn("write_project_file", llm.tool_names)
        self.assertNotIn("run_shell_command", llm.tool_names)




class SettingsTests(unittest.TestCase):
    def test_loads_provider_settings_from_env_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "LLM_PROVIDER=openai-compatible",
                        "LLM_BASE_URL=https://example.com/v1",
                        "LLM_API_KEY=test-key",
                        "LLM_MODEL=test-model",
                    ]
                ),
                encoding="utf-8",
            )

            settings = load_settings(env_path=env_path, environ={})

        self.assertTrue(settings.is_llm_enabled)
        self.assertEqual(settings.base_url, "https://example.com/v1")
        self.assertEqual(settings.api_key, "test-key")
        self.assertEqual(settings.model, "test-model")



if __name__ == "__main__":
    unittest.main()
