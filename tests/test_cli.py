import subprocess
import tempfile
import unittest
from pathlib import Path

from mini_agent.cli import MiniAgentCLI


class MiniAgentCLITests(unittest.TestCase):
    def test_runs_agent_until_exit(self):
        agent = FakeCLIAgent()
        outputs = []
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["hello", "exit"]), output_func=outputs.append)

        cli.run()

        self.assertEqual(agent.inputs, ["hello"])
        self.assertIn("Nora Code", outputs[0])
        self.assertTrue(any("reply: hello" in output for output in outputs))
        self.assertTrue(any("model:" in output and "/ for commands" in output for output in outputs))

    def test_quit_exits_without_agent_call(self):
        agent = FakeCLIAgent()
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["quit"]), output_func=lambda output: None)

        cli.run()

        self.assertEqual(agent.inputs, [])

    def test_ignores_blank_input(self):
        agent = FakeCLIAgent()
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["", "   ", "hello", "exit"]), output_func=lambda output: None)

        cli.run()

        self.assertEqual(agent.inputs, ["hello"])

    def test_eof_exits_cleanly(self):
        agent = FakeCLIAgent()
        outputs = []
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input([]), output_func=outputs.append)

        cli.run()

        self.assertEqual(agent.inputs, [])
        self.assertTrue(outputs)

    def test_handles_help_command_without_agent_call(self):
        agent = FakeCLIAgent()
        outputs = []
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["/help", "exit"]), output_func=outputs.append)

        cli.run()

        self.assertEqual(agent.inputs, [])
        help_output = "\n".join(outputs)
        self.assertIn("Commands", help_output)
        self.assertIn("Project", help_output)
        self.assertIn("Tasks & Memory", help_output)
        self.assertIn("Git", help_output)
        self.assertIn("Code", help_output)
        self.assertIn("/auto [n] <goal>", help_output)
        self.assertIn("/status", help_output)

    def test_status_command_calls_registry(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        result = cli.handle_slash_command("/status")

        self.assertEqual(registry.calls[-1], ("git_status", {}))
        self.assertIn("called git_status", result)

    def test_doctor_reports_runtime_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=root)

            result = cli.handle_slash_command("/doctor")

        self.assertIn("Nora doctor", result)
        self.assertIn("workspace:", result)
        self.assertIn("git:", result)
        self.assertIn("llm:", result)
        self.assertIn("tools: 1", result)
        self.assertIn("data path:", result)
        self.assertIn("logs path:", result)
        self.assertIn("nora command:", result)
        self.assertIn("suggestions:", result)
        self.assertIn("git init", result)
        self.assertIn("LLM_API_KEY", result)
        self.assertIn("data/ will be created", result)

    def test_symbol_commands_call_registry(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        cli.handle_slash_command("/symbols ToolRegistry")
        cli.handle_slash_command("/symbol ToolRegistry.call")
        cli.handle_slash_command("/refs ToolRegistry")
        cli.handle_slash_command("/outline mini_agent/registry.py")

        self.assertEqual(registry.calls[-4], ("list_python_symbols", {"query": "ToolRegistry"}))
        self.assertEqual(registry.calls[-3], ("describe_python_symbol", {"name": "ToolRegistry.call"}))
        self.assertEqual(registry.calls[-2], ("find_python_references", {"name": "ToolRegistry"}))
        self.assertEqual(registry.calls[-1], ("outline_python_file", {"path": "mini_agent/registry.py"}))

    def test_git_review_commands_call_registry(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        cli.handle_slash_command("/changes")
        cli.handle_slash_command("/review-staged")
        cli.handle_slash_command("/check-commit")

        self.assertEqual(registry.calls[-3], ("git_summarize_changes", {}))
        self.assertEqual(registry.calls[-2], ("git_review_staged_diff", {}))
        self.assertEqual(registry.calls[-1], ("git_check_before_commit", {}))

    def test_audit_command_calls_registry(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        cli.handle_slash_command("/audit 7")

        self.assertEqual(registry.calls[-1], ("generate_audit_report", {"max_entries": 7}))

    def test_auto_command_calls_agent_autonomous_loop(self):
        agent = FakeCLIAgent()
        cli = MiniAgentCLI(agent, FakeCLIRegistry())

        result = cli.handle_slash_command("/auto 3 inspect project")

        self.assertEqual(agent.autonomous_calls, [("inspect project", 3)])
        self.assertIn("auto reply: inspect project / 3", result)

    def test_task_history_commands_call_registry(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        cli.handle_slash_command("/task-history 5")
        cli.handle_slash_command("/task-search blocked step")
        cli.handle_slash_command("/task-restore task_1")

        self.assertEqual(registry.calls[-3], ("list_task_history", {"max_results": 5}))
        self.assertEqual(registry.calls[-2], ("search_task_history", {"query": "blocked step"}))
        self.assertEqual(registry.calls[-1], ("restore_task", {"history_id": "task_1"}))

    def test_auto_command_requires_goal(self):
        agent = FakeCLIAgent()
        cli = MiniAgentCLI(agent, FakeCLIRegistry())

        self.assertIn("usage", cli.handle_slash_command("/auto"))
        self.assertIn("usage", cli.handle_slash_command("/auto 3"))
        self.assertEqual(agent.autonomous_calls, [])

    def test_symbol_commands_require_arguments(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        self.assertIn("usage", cli.handle_slash_command("/symbol"))
        self.assertIn("usage", cli.handle_slash_command("/refs"))
        self.assertIn("usage", cli.handle_slash_command("/outline"))
        self.assertEqual(registry.calls, [])

    def test_write_slash_command_uses_registry_path(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        cli.handle_slash_command("/git-stage README.md")

        self.assertEqual(
            registry.calls[-1],
            ("git_stage_paths", {"paths": ["README.md"], "reason": "cli slash command"}),
        )

    def test_multiline_input(self):
        agent = FakeCLIAgent()
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["<<<", "line1", "line2", ">>>", "exit"]), output_func=lambda output: None)

        cli.run()

        self.assertEqual(agent.inputs, ["line1\nline2"])

    def test_prompt_is_minimal(self):
        cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry())
        self.assertEqual(cli.prompt(), "> ")

    def test_input_status_line_shows_model_info(self):
        cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry())

        status = cli._input_status_line()

        self.assertIn("model:", status)
        self.assertIn("/ for commands", status)
        self.assertNotIn("Workspace:", status)

    def test_disabled_banner_shows_api_key_line(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs = []
            cli = MiniAgentCLI(
                FakeCLIAgent(),
                FakeCLIRegistry(),
                settings=None,
                root=Path(tmpdir),
                input_func=_fake_input(["exit"]),
                output_func=outputs.append,
            )

            cli.run()

            banner = outputs[0]
            self.assertIn("Nora Code", banner)
            self.assertIn("local mode", banner)
            self.assertNotIn("API key", banner)

    def test_configured_banner_shows_api_key_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(provider="openai", model="gpt-4", api_key="sk-test")
            outputs = []
            cli = MiniAgentCLI(
                FakeCLIAgent(),
                FakeCLIRegistry(),
                settings=settings,
                root=Path(tmpdir),
                input_func=_fake_input(["exit"]),
                output_func=outputs.append,
            )

            cli.run()

            banner = outputs[0]
            self.assertIn("Nora Code", banner)
            self.assertIn("model: openai / gpt-4", banner)
            self.assertIn("API key: configured", banner)
            self.assertNotIn("sk-test", banner)
            self.assertNotIn("local mode", banner)


    def test_durable_tasks_empty(self):
        import tempfile
        from mini_agent.database import NoraDB
        from mini_agent.durable_tasks import DurableTaskStore
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                registry = FakeCLIRegistry()
                registry.durable_task_store = store
                cli = MiniAgentCLI(FakeCLIAgent(), registry)

                result = cli.handle_slash_command("/durable-tasks")

                self.assertIn("no durable tasks", result)
            finally:
                db.close()

    def test_durable_tasks_with_data(self):
        import tempfile
        from mini_agent.database import NoraDB
        from mini_agent.durable_tasks import DurableTaskStore
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task(goal="first task", steps=[{"text": "s1"}])
                store.create_task(goal="second task", steps=[{"text": "s1"}, {"text": "s2"}])
                store.add_checkpoint("dtask_1", {"step_id": 1, "run_id": "run_1", "state_snapshot": {}})

                registry = FakeCLIRegistry()
                registry.durable_task_store = store
                cli = MiniAgentCLI(FakeCLIAgent(), registry)

                result = cli.handle_slash_command("/durable-tasks 2")

                self.assertIn("dtask_1", result)
                self.assertIn("dtask_2", result)
                self.assertIn("checkpoints=1", result)
                self.assertIn("first task", result)
            finally:
                db.close()

    def test_durable_task_found(self):
        import json
        import tempfile
        from mini_agent.database import NoraDB
        from mini_agent.durable_tasks import DurableTaskStore
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)
                store.create_task(goal="test goal", steps=[{"text": "step 1"}])

                registry = FakeCLIRegistry()
                registry.durable_task_store = store
                cli = MiniAgentCLI(FakeCLIAgent(), registry)

                result = cli.handle_slash_command("/durable-task dtask_1")

                parsed = json.loads(result)
                self.assertEqual(parsed["task_id"], "dtask_1")
                self.assertEqual(parsed["goal"], "test goal")
            finally:
                db.close()

    def test_durable_task_not_found(self):
        import tempfile
        from mini_agent.database import NoraDB
        from mini_agent.durable_tasks import DurableTaskStore
        with tempfile.TemporaryDirectory() as tmpdir:
            db = NoraDB(Path(tmpdir) / "test.db")
            try:
                store = DurableTaskStore(db=db)

                registry = FakeCLIRegistry()
                registry.durable_task_store = store
                cli = MiniAgentCLI(FakeCLIAgent(), registry)

                result = cli.handle_slash_command("/durable-task dtask_999")

                self.assertIn("not found", result)
            finally:
                db.close()

    def test_durable_tasks_no_store(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        result = cli.handle_slash_command("/durable-tasks")

        self.assertIn("not configured", result)

    def test_durable_task_no_store(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        result = cli.handle_slash_command("/durable-task dtask_1")

        self.assertIn("not configured", result)

    def test_durable_task_requires_id(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        result = cli.handle_slash_command("/durable-task")

        self.assertIn("usage", result)


class FakeCLIAgent:
    def __init__(self):
        self.inputs = []
        self.autonomous_calls = []
        self.last_run_report = FakeRunReport()

    def run(self, text):
        self.inputs.append(text)
        return f"reply: {text}"

    def run_autonomous(self, goal, max_steps=None):
        self.autonomous_calls.append((goal, max_steps))
        return f"auto reply: {goal} / {max_steps}"


class FakeRunReport:
    def format(self):
        return "\n".join(
            [
                "运行报告:",
                "- 状态: done",
                "- 步骤: 1",
                "- 工具: fake_tool(ok)",
                "- 失败: 无",
                "- 下一步: 无",
            ]
        )


class FakeCLIRegistry:
    def __init__(self):
        self.calls = []

    def call(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        return f"called {tool_name}"

    def describe(self):
        return "tools"

    def describe_permissions(self):
        return "permissions"

    def to_openai_tools(self):
        return [{"function": {"name": "fake"}}]


class FakeSettings:
    def __init__(self, provider="", model="", api_key=""):
        self.provider = provider
        self.model = model
        self.api_key = api_key

    @property
    def is_llm_enabled(self):
        return bool(self.api_key and self.model)


class CLIDoctorProviderTests(unittest.TestCase):
    def test_doctor_openai_compatible_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            settings = FakeSettings(provider="openai-compatible", model="gpt-4.1-mini")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=root)

            result = cli.handle_slash_command("/doctor")

        self.assertIn("llm: disabled", result)
        self.assertIn("LLM_PROVIDER", result)
        self.assertIn("LLM_API_KEY", result)
        self.assertIn("LLM_MODEL", result)
        self.assertIn("OPENAI_API_KEY", result)
        self.assertIn("also accepts", result)
        self.assertNotIn("ANTHROPIC_API_KEY", result)
        self.assertNotIn("GEMINI_API_KEY", result)

    def test_doctor_anthropic_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            settings = FakeSettings(provider="anthropic", model="claude-sonnet-4-5")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=root)

            result = cli.handle_slash_command("/doctor")

        self.assertIn("llm: disabled", result)
        self.assertIn("LLM_PROVIDER", result)
        self.assertIn("ANTHROPIC_API_KEY", result)
        self.assertIn("ANTHROPIC_MODEL", result)
        self.assertNotIn("LLM_API_KEY", result)
        self.assertNotIn("LLM_MODEL", result)
        self.assertNotIn("OPENAI_API_KEY", result)
        self.assertNotIn("GEMINI_API_KEY", result)

    def test_doctor_gemini_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            settings = FakeSettings(provider="gemini", model="gemini-2.5-pro")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=root)

            result = cli.handle_slash_command("/doctor")

        self.assertIn("llm: disabled", result)
        self.assertIn("LLM_PROVIDER", result)
        self.assertIn("GEMINI_API_KEY", result)
        self.assertIn("GEMINI_MODEL", result)
        self.assertNotIn("LLM_API_KEY", result)
        self.assertNotIn("LLM_MODEL", result)
        self.assertNotIn("OPENAI_API_KEY", result)
        self.assertNotIn("ANTHROPIC_API_KEY", result)

    def test_doctor_no_settings_uses_generic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=None, root=root)

            result = cli.handle_slash_command("/doctor")

        self.assertIn("llm: disabled", result)
        self.assertIn("LLM_API_KEY", result)

    def test_doctor_no_key_leak(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            settings = FakeSettings(provider="openai-compatible", model="gpt-4.1-mini", api_key="sk-secret123")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=root)

            result = cli.handle_slash_command("/doctor")

        self.assertNotIn("sk-secret123", result)


def _fake_input(values):
    iterator = iter(values)

    def fake_input(prompt):
        try:
            return next(iterator)
        except StopIteration:
            raise EOFError

    return fake_input


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True)


class CLITaskCommandTests(unittest.TestCase):
    """Tests for /task, /tasks, /durable-tasks, /durable-task CLI commands."""

    def _make_cli(self, tmpdir):
        from mini_agent.database import NoraDB
        from mini_agent.tools import build_default_registry
        db = NoraDB(Path(tmpdir) / "test.db")
        registry = build_default_registry(db=db, workspace_root=Path(tmpdir))
        cli = MiniAgentCLI(FakeCLIAgent(), registry, root=Path(tmpdir))
        return cli, db

    def test_task_no_args_calls_legacy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli, db = self._make_cli(tmpdir)
            result = cli.handle_slash_command("/task")
            self.assertIn("暂无任务", result)
            db.close()

    def test_task_with_id_gets_durable_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli, db = self._make_cli(tmpdir)
            store = cli.registry.durable_task_store
            store.create_task(goal="test goal", steps=[{"text": "s1"}])
            result = cli.handle_slash_command("/task dtask_1")
            self.assertIn("dtask_1", result)
            self.assertIn("test goal", result)
            db.close()

    def test_task_with_id_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli, db = self._make_cli(tmpdir)
            result = cli.handle_slash_command("/task dtask_999")
            self.assertIn("not found", result)
            db.close()

    def test_tasks_lists_durable_tasks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli, db = self._make_cli(tmpdir)
            store = cli.registry.durable_task_store
            store.create_task(goal="task a", steps=[])
            store.create_task(goal="task b", steps=[])
            result = cli.handle_slash_command("/tasks")
            self.assertIn("recent 2", result)
            self.assertIn("task a", result)
            self.assertIn("task b", result)
            db.close()

    def test_tasks_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli, db = self._make_cli(tmpdir)
            result = cli.handle_slash_command("/tasks")
            self.assertIn("no durable tasks", result)
            db.close()

    def test_tasks_with_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli, db = self._make_cli(tmpdir)
            store = cli.registry.durable_task_store
            for i in range(5):
                store.create_task(goal=f"task {i}", steps=[])
            result = cli.handle_slash_command("/tasks 2")
            self.assertIn("recent 2", result)
            db.close()

    def test_durable_tasks_still_works(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli, db = self._make_cli(tmpdir)
            store = cli.registry.durable_task_store
            store.create_task(goal="legacy cmd", steps=[])
            result = cli.handle_slash_command("/durable-tasks")
            self.assertIn("legacy cmd", result)
            db.close()

    def test_durable_task_still_works(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli, db = self._make_cli(tmpdir)
            store = cli.registry.durable_task_store
            store.create_task(goal="detail test", steps=[])
            result = cli.handle_slash_command("/durable-task dtask_1")
            self.assertIn("dtask_1", result)
            self.assertIn("detail test", result)
            db.close()

    def test_help_includes_new_commands(self):
        cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry())
        result = cli._help()
        self.assertIn("/task", result)
        self.assertIn("/tasks [n]", result)
        self.assertIn("/dashboard", result)
        self.assertIn("/wake", result)
        self.assertIn("/model", result)
        self.assertIn("/workers", result)


class CLIWakeCommandTests(unittest.TestCase):
    """Tests for /wake command (TASK-129)."""

    def test_wake_panel_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=root)
            result = cli.handle_slash_command("/wake")
            self.assertIn("Workspace:", result)
            self.assertIn("Branch:", result)
            self.assertIn("model:", result)

    def test_wake_panel_shows_knowledge_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            kb = root / "docs" / "knowledge"
            kb.mkdir(parents=True)
            (kb / "PROJECT_WAKEUP.md").write_text("# Wakeup\n")
            (kb / "DECISIONS.md").write_text("# Decisions\n")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=root)
            result = cli.handle_slash_command("/wake")
            self.assertIn("PROJECT_WAKEUP.md", result)
            self.assertIn("DECISIONS.md", result)
            self.assertIn("Knowledge:", result)

    def test_wake_panel_shows_missing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=root)
            result = cli.handle_slash_command("/wake")
            self.assertIn("Missing:", result)

    def test_wake_panel_no_git_repo_hint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=root)
            result = cli.handle_slash_command("/wake")
            self.assertIn("not in a git repo", result)

    def test_wake_panel_with_git_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=root)
            result = cli.handle_slash_command("/wake")
            self.assertIn("Branch:", result)
            self.assertNotIn("未在 Git 项目中", result)


class CLIModelCommandTests(unittest.TestCase):
    """Tests for /model command (TASK-129)."""

    def test_model_no_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=None, root=Path(tmpdir))
            result = cli.handle_slash_command("/model")
            self.assertIn("settings not loaded", result)
            self.assertIn("LLM_PROVIDER", result)

    def test_model_shows_provider_info(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(provider="openai-compatible", model="gpt-4.1-mini")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            result = cli.handle_slash_command("/model")
            self.assertIn("openai-compatible", result)
            self.assertIn("gpt-4.1-mini", result)

    def test_model_shows_key_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(provider="anthropic", model="claude-sonnet-4-5")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            result = cli.handle_slash_command("/model")
            self.assertIn("API key: missing", result)
            self.assertIn("ANTHROPIC_API_KEY", result)

    def test_model_shows_key_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(provider="openai-compatible", model="gpt-4.1-mini", api_key="sk-test")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            result = cli.handle_slash_command("/model")
            self.assertIn("API key: configured", result)
            self.assertNotIn("sk-test", result)

    def test_model_no_key_leak(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(provider="openai-compatible", model="gpt-4.1-mini", api_key="sk-secret123")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            result = cli.handle_slash_command("/model")
            self.assertNotIn("sk-secret123", result)

    def test_model_shows_recovery_hints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(provider="anthropic", model="claude-sonnet-4-5")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            result = cli.handle_slash_command("/model")
            self.assertIn("missing key", result)
            self.assertIn("ANTHROPIC_API_KEY", result)


class CLIWorkersCommandTests(unittest.TestCase):
    """Tests for /workers command (TASK-129)."""

    def test_workers_no_ccb_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            result = cli.handle_slash_command("/workers")
            self.assertIn("No .ccb/", result)

    def test_workers_shows_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ccb = root / ".ccb" / "workspaces"
            claude_a = ccb / "claude-a" / "agent_tasks"
            claude_a.mkdir(parents=True)
            (claude_a / "A_TASK.md").write_text("# TASK-129: Test task\n", encoding="utf-8")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=root)
            result = cli.handle_slash_command("/workers")
            self.assertIn("claude-a", result)
            self.assertIn("TASK-129", result)

    def test_workers_shows_done_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ccb = root / ".ccb" / "workspaces"
            claude_a = ccb / "claude-a" / "agent_tasks"
            claude_a.mkdir(parents=True)
            (claude_a / "A_DONE.md").write_text("Status: ready for review\n", encoding="utf-8")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=root)
            result = cli.handle_slash_command("/workers")
            self.assertIn("ready for PM review", result)

    def test_banner_detects_done_file(self):
        """banner() worker summary should detect A_DONE.md as done."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ccb = root / ".ccb" / "workspaces"
            claude_a = ccb / "claude-a" / "agent_tasks"
            claude_a.mkdir(parents=True)
            (claude_a / "A_DONE.md").write_text("Status: ready for review\n", encoding="utf-8")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=root)
            banner = cli.banner()
            self.assertIn("claude-a: done", banner)


class CLISetupCommandTests(unittest.TestCase):
    """Tests for /setup and /config commands (TASK-131)."""

    def test_setup_no_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=None, root=Path(tmpdir))
            result = cli.handle_slash_command("/setup")
            self.assertIn("settings not loaded", result)
            self.assertIn("openai-compatible", result)
            self.assertIn("anthropic", result)
            self.assertIn("gemini", result)

    def test_config_is_alias_for_setup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=None, root=Path(tmpdir))
            setup_result = cli.handle_slash_command("/setup")
            config_result = cli.handle_slash_command("/config")
            self.assertEqual(setup_result, config_result)

    def test_setup_shows_provider_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(provider="anthropic", model="claude-sonnet-4-5")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            result = cli.handle_slash_command("/setup")
            self.assertIn("ANTHROPIC_API_KEY", result)
            self.assertIn("ANTHROPIC_MODEL", result)
            self.assertIn("ANTHROPIC_BASE_URL", result)

    def test_setup_shows_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(provider="openai-compatible", model="gpt-4.1-mini")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            result = cli.handle_slash_command("/setup")
            self.assertIn("missing API key", result)
            self.assertIn("LLM_API_KEY", result)

    def test_setup_no_key_leak(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(provider="openai-compatible", model="gpt-4.1-mini", api_key="sk-secret123")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            result = cli.handle_slash_command("/setup")
            self.assertNotIn("sk-secret123", result)

    def test_setup_shows_error_recovery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            result = cli.handle_slash_command("/setup")
            self.assertIn("401 Unauthorized", result)
            self.assertIn("provider/model mismatch", result)
            self.assertIn("port in use", result)

    def test_setup_shows_mismatch_guidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(provider="anthropic", model="claude-sonnet-4-5")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            result = cli.handle_slash_command("/setup")
            self.assertIn("provider/model mismatch", result)

    def test_help_includes_setup(self):
        cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry())
        result = cli._help()
        self.assertIn("/setup", result)
        self.assertIn("/config", result)


class CLIResponseStatusTests(unittest.TestCase):
    """Tests for response lifecycle lines (TASK-145 working indicator)."""

    def test_model_call_shows_working_indicator(self):
        agent = FakeCLIAgent()
        outputs = []
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["hello", "exit"]), output_func=outputs.append)

        cli.run()

        self.assertIn("Working...", outputs)
        self.assertIn("Done.", outputs)

    def test_slash_command_no_lifecycle_noise(self):
        agent = FakeCLIAgent()
        outputs = []
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["/help", "exit"]), output_func=outputs.append)

        cli.run()

        self.assertNotIn("Working...", outputs)
        self.assertNotIn("Done.", outputs)

    def test_blank_input_no_lifecycle_noise(self):
        agent = FakeCLIAgent()
        outputs = []
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["", "   ", "exit"]), output_func=outputs.append)

        cli.run()

        self.assertNotIn("Working...", outputs)
        self.assertNotIn("Done.", outputs)

    def test_exit_no_lifecycle_noise(self):
        agent = FakeCLIAgent()
        outputs = []
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["exit"]), output_func=outputs.append)

        cli.run()

        self.assertNotIn("Working...", outputs)
        self.assertNotIn("Done.", outputs)

    def test_multiline_input_shows_working_indicator(self):
        agent = FakeCLIAgent()
        outputs = []
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["<<<", "line1", ">>>", "exit"]), output_func=outputs.append)

        cli.run()

        self.assertIn("Working...", outputs)
        self.assertIn("Done.", outputs)


class CLISlashLauncherTests(unittest.TestCase):
    """Tests for exact / slash launcher/menu (TASK-133)."""

    def test_exact_slash_shows_grouped_menu(self):
        cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry())
        result = cli.handle_slash_command("/")
        self.assertIn("Commands", result)
        for command in ["/wake", "/setup", "/model", "/workers", "/status", "/test", "/help"]:
            self.assertIn(command, result)

    def test_exact_slash_is_plain_text_not_json(self):
        cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry())
        result = cli.handle_slash_command("/")
        self.assertFalse(result.lstrip().startswith("{"))
        self.assertFalse(result.lstrip().startswith("["))

    def test_exact_slash_no_agent_call_or_status_noise(self):
        agent = FakeCLIAgent()
        outputs = []
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["/", "exit"]), output_func=outputs.append)

        cli.run()

        self.assertEqual(agent.inputs, [])
        joined = "\n".join(outputs)
        self.assertIn("Commands", joined)
        self.assertNotIn("Working...", joined)
        self.assertNotIn("Done.", joined)

    def test_banner_shows_next_action_and_preserves_core_info(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs = []
            cli = MiniAgentCLI(
                FakeCLIAgent(),
                FakeCLIRegistry(),
                root=Path(tmpdir),
                input_func=_fake_input(["exit"]),
                output_func=outputs.append,
            )

            cli.run()

            banner = outputs[0]
            self.assertIn("Nora Code", banner)
            self.assertIn("local mode", banner)
            self.assertIn(str(Path(tmpdir).resolve()), banner)
            self.assertNotIn("Nora 已启动", banner)

    def test_unknown_slash_points_to_launcher(self):
        cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry())
        result = cli.handle_slash_command("/does-not-exist")
        self.assertIn("unknown command", result)
        self.assertIn("/help", result)


class CLIErrorRecoveryTests(unittest.TestCase):
    """Tests for error recovery hints (TASK-149)."""

    def test_hint_for_401(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            hint = cli._error_recovery_hint("Error: 401 Unauthorized")
            self.assertIn("API key", hint)
            self.assertIn("hint:", hint)

    def test_hint_for_connection_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            hint = cli._error_recovery_hint("Connection timeout")
            self.assertIn("network", hint)

    def test_hint_for_model_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            hint = cli._error_recovery_hint("Model not found")
            self.assertIn("model name", hint)

    def test_hint_for_rate_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            hint = cli._error_recovery_hint("Rate limit exceeded")
            self.assertIn("rate limited", hint)

    def test_hint_for_missing_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            hint = cli._error_recovery_hint("Missing API key")
            self.assertIn("API key", hint)

    def test_hint_for_port_in_use(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            hint = cli._error_recovery_hint("Port 8080 already in use")
            self.assertIn("port in use", hint)

    def test_no_hint_for_normal_response(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            hint = cli._error_recovery_hint("Everything looks good")
            self.assertEqual(hint, "")

    def test_agent_response_gets_recovery_hint(self):
        agent = FakeCLIAgent()
        agent.run = lambda text: "Error: 401 Unauthorized"
        cli = MiniAgentCLI(agent, FakeCLIRegistry(), root=Path("/tmp"))
        result = cli.handle_input("test")
        self.assertIn("hint:", result)


if __name__ == "__main__":
    unittest.main()
