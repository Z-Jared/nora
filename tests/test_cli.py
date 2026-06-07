import subprocess
import tempfile
import time
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
        self.assertIn("local mode", outputs[0])
        self.assertFalse(any("local-first" in output for output in outputs[1:]))

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

    def test_test_command_passes_selected_whitelisted_command(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        result = cli.handle_slash_command("/test python3 evals/run_evals.py --filter tty_")

        self.assertEqual(
            registry.calls[-1],
            ("run_project_tests", {"command": "python3 evals/run_evals.py --filter tty_"}),
        )
        self.assertIn("called run_project_tests", result)

    def test_test_command_rejects_non_whitelisted_command(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        result = cli.handle_slash_command("/test rm -rf /")

        self.assertIn("拒绝执行测试", result)
        self.assertEqual(registry.calls, [])

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

    def test_default_run_does_not_repeat_status_footer(self):
        outputs = []
        cli = MiniAgentCLI(
            FakeCLIAgent(),
            FakeCLIRegistry(),
            input_func=_fake_input(["hello", "exit"]),
            output_func=outputs.append,
        )

        cli.run()

        repeated_footers = [output for output in outputs[1:] if "local-first" in output]
        self.assertEqual(repeated_footers, [])

    def test_agent_response_is_terminal_plain_text(self):
        agent = FakeCLIAgent()
        agent.run = lambda text: "# Title 👋\n\n**Bold**\n* item"
        cli = MiniAgentCLI(agent, FakeCLIRegistry())

        result = cli.handle_input("format")

        self.assertIn("Title", result)
        self.assertIn("Bold", result)
        self.assertIn("  item", result)
        self.assertNotIn("# Title", result)
        self.assertNotIn("**", result)
        self.assertNotIn("* item", result)
        self.assertNotIn("👋", result)

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

    def test_configured_banner_shows_credentials_configured(self):
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
            self.assertIn("credentials: configured", banner)
            self.assertNotIn("API key:", banner)
            self.assertNotIn("sk-test", banner)
            self.assertNotIn("local mode", banner)

    def test_cli_autosaves_normal_chat_and_restores_next_start(self):
        from mini_agent.memory import ConversationMemory
        from mini_agent.session import CLI_AUTOSAVE_SESSION, SessionStore

        class MemoryAgent:
            def __init__(self):
                self.memory = ConversationMemory()
                self.last_run_report = FakeRunReport()

            def run(self, text):
                answer = f"reply: {text}"
                self.memory.add_user(text)
                self.memory.add_assistant(answer)
                return answer

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            first_agent = MemoryAgent()
            cli = MiniAgentCLI(first_agent, FakeCLIRegistry(), session_store=store)
            result = cli.handle_input("hello")
            second_agent = MemoryAgent()
            restored_cli = MiniAgentCLI(second_agent, FakeCLIRegistry(), session_store=store)
            saved_messages = store.load_messages(CLI_AUTOSAVE_SESSION)

        self.assertIn("reply: hello", result)
        self.assertEqual(restored_cli.restored_session_message_count, 2)
        self.assertEqual(saved_messages[0]["content"], "hello")
        self.assertEqual(second_agent.memory.messages()[1]["content"], "reply: hello")

    def test_cli_slash_command_does_not_autosave_conversation(self):
        from mini_agent.session import CLI_AUTOSAVE_SESSION, SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), session_store=store)
            result = cli.handle_input("/help")

        self.assertIn("/wake", result)
        self.assertEqual(store.load_messages(CLI_AUTOSAVE_SESSION), [])

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
        self.confirm_action = None

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
            self.assertIn("credentials: missing", result)
            self.assertIn("ANTHROPIC_API_KEY", result)

    def test_model_shows_key_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(provider="openai-compatible", model="gpt-4.1-mini", api_key="sk-test")
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            result = cli.handle_slash_command("/model")
            self.assertIn("credentials: configured", result)
            self.assertNotIn("API key:", result)
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


class SlashCommandNamesTests(unittest.TestCase):
    def test_contains_core_commands(self):
        names = MiniAgentCLI.slash_command_names()
        for command in [
            "/", "/help", "/wake", "/model", "/setup", "/workers",
            "/permissions", "/doctor", "/status", "/test", "/tools", "/exit",
        ]:
            self.assertIn(command, names)

    def test_no_duplicates(self):
        names = MiniAgentCLI.slash_command_names()
        self.assertEqual(len(names), len(set(names)))

    def test_all_start_with_slash(self):
        for name in MiniAgentCLI.slash_command_names():
            self.assertTrue(name.startswith("/"), name)


class InteractiveCLITests(unittest.TestCase):
    def test_tty_prompt_matches_raw_terminal_contract(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(
                provider="openai-compatible",
                model="deepseek-v4-flash",
                api_key="sk-secret123",
            )
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            app = cli._make_application()
            banner = cli._tty_banner()
            toolbar = cli._bottom_toolbar()

        self.assertTrue(app.full_screen)
        self.assertIn("[::]    Nora Code", banner)
        self.assertNotIn("API key", banner)
        self.assertNotIn("sk-secret123", banner)
        self.assertIn("Ready", toolbar.value)
        self.assertIn("/ commands", toolbar.value)
        self.assertIn("Esc clear", toolbar.value)
        self.assertIn("Ctrl-D exit", toolbar.value)
        self.assertNotIn("API key", toolbar.value)

    def test_tty_startup_renders_restored_autosave_preview(self):
        from mini_agent.memory import ConversationMemory
        from mini_agent.session import SessionStore
        from mini_agent import interactive_cli

        class MemoryAgent:
            def __init__(self):
                self.memory = ConversationMemory()
                self.last_run_report = FakeRunReport()

            def run(self, text):
                return "unused"

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("old question")
            memory.add_assistant("old answer")
            store.save_cli_autosave(memory)
            agent = MemoryAgent()
            cli = interactive_cli.InteractiveCLI(agent, FakeCLIRegistry(), root=Path(tmpdir), session_store=store)
            body = "".join(fragment for _, fragment in cli._render_body(max_lines=6, width=80))

        self.assertIn("restored previous session", body)
        self.assertIn("last: old question", body)
        self.assertIn("reply: old answer", body)

    def test_tty_restored_history_preview_is_clipped_for_first_screen(self):
        from mini_agent.memory import ConversationMemory
        from mini_agent.session import SessionStore
        from mini_agent import interactive_cli

        class MemoryAgent:
            def __init__(self):
                self.memory = ConversationMemory()
                self.last_run_report = FakeRunReport()

            def run(self, text):
                return "unused"

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("old question")
            memory.add_assistant("\n".join(f"old answer line {index}" for index in range(20)))
            store.save_cli_autosave(memory)
            agent = MemoryAgent()
            cli = interactive_cli.InteractiveCLI(agent, FakeCLIRegistry(), root=Path(tmpdir), session_store=store)
            body = "".join(fragment for _, fragment in cli._render_body(max_lines=10, width=80))

        self.assertIn("restored previous session", body)
        self.assertIn("reply: old answer line 0", body)
        self.assertNotIn("old answer line 19", body)

    def test_tty_restored_history_hides_internal_tool_markup(self):
        from mini_agent.memory import ConversationMemory
        from mini_agent.session import SessionStore
        from mini_agent import interactive_cli

        class MemoryAgent:
            def __init__(self):
                self.memory = ConversationMemory()
                self.last_run_report = FakeRunReport()

            def run(self, text):
                return "unused"

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_assistant(
                "\n".join([
                    "<｜｜DSML｜｜tool_calls>",
                    "<tool_call>",
                    "visible restored answer",
                    "</｜｜DSML｜｜tool_calls>",
                ])
            )
            store.save_cli_autosave(memory)
            cli = interactive_cli.InteractiveCLI(MemoryAgent(), FakeCLIRegistry(), root=Path(tmpdir), session_store=store)
            body = "".join(fragment for _, fragment in cli._render_body(max_lines=8, width=80))

        self.assertIn("visible restored answer", body)
        self.assertNotIn("DSML", body)
        self.assertNotIn("<tool_call>", body)

    def test_tty_restored_history_skips_error_noise(self):
        from mini_agent.memory import ConversationMemory
        from mini_agent.session import SessionStore
        from mini_agent import interactive_cli

        class MemoryAgent:
            def __init__(self):
                self.memory = ConversationMemory()
                self.last_run_report = FakeRunReport()

            def run(self, text):
                return "unused"

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("h/exit")
            memory.add_assistant("'utf-8' codec can't decode byte 0xe4")
            memory.add_user("real question")
            memory.add_assistant("real answer")
            store.save_cli_autosave(memory)
            cli = interactive_cli.InteractiveCLI(MemoryAgent(), FakeCLIRegistry(), root=Path(tmpdir), session_store=store)
            body = "".join(fragment for _, fragment in cli._render_body(max_lines=8, width=80))

        self.assertIn("last: real question", body)
        self.assertIn("reply: real answer", body)
        self.assertNotIn("h/exit", body)
        self.assertNotIn("codec can't decode", body)

    def test_tty_restored_history_uses_latest_valid_pair(self):
        from mini_agent.memory import ConversationMemory
        from mini_agent.session import SessionStore
        from mini_agent import interactive_cli

        class MemoryAgent:
            def __init__(self):
                self.memory = ConversationMemory()
                self.last_run_report = FakeRunReport()

            def run(self, text):
                return "unused"

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            memory = ConversationMemory()
            memory.add_user("useful question")
            memory.add_assistant("useful answer")
            memory.add_user("/exit")
            memory.add_assistant("好的，再见！")
            store.save_cli_autosave(memory)
            cli = interactive_cli.InteractiveCLI(MemoryAgent(), FakeCLIRegistry(), root=Path(tmpdir), session_store=store)
            body = "".join(fragment for _, fragment in cli._render_body(max_lines=8, width=80))

        self.assertIn("last: useful question", body)
        self.assertIn("reply: useful answer", body)
        self.assertNotIn("好的，再见", body)

    def test_tty_session_load_syncs_restored_memory_to_transcript(self):
        from mini_agent.memory import ConversationMemory
        from mini_agent.session import SessionStore
        from mini_agent import interactive_cli

        class MemoryAgent:
            def __init__(self):
                self.memory = ConversationMemory()
                self.last_run_report = FakeRunReport()

            def run(self, text):
                return "unused"

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions")
            saved = ConversationMemory()
            saved.add_user("saved question")
            saved.add_assistant("saved answer")
            store.save(saved, name="manual")
            cli = interactive_cli.InteractiveCLI(MemoryAgent(), FakeCLIRegistry(), root=Path(tmpdir), session_store=store)
            cli._run_cli_input("/session-load manual")
            transcript = "\n".join(cli._transcript)

        self.assertIn("> saved question", transcript)
        self.assertIn("saved answer", transcript)
        self.assertIn("已恢复会话", transcript)

    def test_tty_exact_slash_opens_launcher_without_transcript_echo(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))

            class FakeBuffer:
                text = "/"

            cli._handle_app_input(FakeBuffer())
            panel = "".join(fragment for _, fragment in cli._render_slash_panel())

        self.assertEqual(cli._transcript, [])
        self.assertEqual(cli._current_input, "/")
        self.assertIn("/ commands", panel)
        self.assertIn("Common/", panel)
        self.assertIn("Project/", panel)
        self.assertIn("Tools/", panel)

    def test_tty_slash_prefix_renders_matching_launcher_panel(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._current_input = "/mo"
            rendered = "".join(fragment for _, fragment in cli._render_slash_panel())
            body = "".join(fragment for _, fragment in cli._render_body())

        self.assertIn("/ commands", rendered)
        self.assertIn("/model", rendered)
        self.assertNotIn("/workers", rendered)
        self.assertNotIn("/ commands", body)

    def test_tty_slash_launcher_filters_full_command_catalog(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._current_input = "/t"
            rendered = "".join(fragment for _, fragment in cli._render_slash_panel())

        self.assertIn("/tasks", rendered)
        self.assertIn("/tools", rendered)
        self.assertIn("/test", rendered)
        self.assertNotIn("/model", rendered)

    def test_tty_slash_launcher_panel_is_lightweight_and_fits_container(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            panel = cli._slash_launcher_panel("/t", selected=0)

        self.assertLessEqual(len(panel.splitlines()), 10)
        self.assertNotIn("+", panel)
        self.assertNotIn("|", panel)
        self.assertIn("/ commands", panel)

    def test_tty_slash_group_enters_second_level(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._current_input = "/"

            class FakeBuffer:
                text = "/"
                cursor_position = 1

            class FakeEvent:
                class App:
                    current_buffer = FakeBuffer()

                app = App()

            cli._accept_slash_selection(FakeEvent())
            panel = cli._slash_launcher_panel("/", cli._slash_selected)

        self.assertEqual(cli._slash_group, "Common")
        self.assertEqual(FakeEvent.app.current_buffer.text, "/")
        self.assertIn("/ commands / Common", panel)
        self.assertIn("/wake", panel)
        self.assertIn("/status", panel)
        self.assertNotIn("current", "\n".join(cli._transcript))

    def test_tty_slash_launcher_has_own_selection_state(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._current_input = "/"
            cli._move_slash(1)
            panel = cli._slash_launcher_panel("/", cli._slash_selected)

        self.assertEqual(cli._selected_slash_row()["value"], "Project")
        self.assertIn("> Project/", panel)
        self.assertNotIn("> Common/", panel)

    def test_tty_slash_selection_fills_input_without_executing(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._current_input = "/"
            cli._slash_group = "Project"
            for _ in range(20):
                if cli._selected_slash_row()["value"] == "/setup":
                    break
                cli._move_slash(1)

            class FakeBuffer:
                text = "/"
                cursor_position = 1

            class FakeEvent:
                class App:
                    current_buffer = FakeBuffer()

                app = App()

            cli._accept_slash_selection(FakeEvent())

        transcript = "\n".join(cli._transcript)
        self.assertEqual(FakeEvent.app.current_buffer.text, "/setup")
        self.assertEqual(cli._current_input, "/setup")
        self.assertIn("Enter to run", cli._status_message)
        self.assertIsNone(cli._worker_thread)
        self.assertNotIn("> /setup", transcript)
        self.assertNotIn("current", transcript)

    def test_tty_slash_command_with_args_enters_argument_level(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._current_input = "/"
            cli._slash_group = "Git"
            for _ in range(20):
                if cli._selected_slash_row()["value"] == "/git-stage":
                    break
                cli._move_slash(1)
            self.assertEqual(cli._selected_slash_row()["value"], "/git-stage")

            class FakeBuffer:
                text = "/"
                cursor_position = 1

            class FakeEvent:
                class App:
                    current_buffer = FakeBuffer()

                app = App()

            cli._accept_slash_selection(FakeEvent())
            panel = cli._slash_launcher_panel("/", cli._slash_selected)

        self.assertEqual(cli._slash_command, "/git-stage")
        self.assertEqual(cli._slash_arg_step, 0)
        self.assertEqual(FakeEvent.app.current_buffer.text, "/")
        self.assertIn("/git-stage", panel)
        self.assertIn("<path>", panel)
        self.assertNotIn("current", "\n".join(cli._transcript))

    def test_tty_slash_argument_choice_fills_command_template(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._current_input = "/"
            cli._slash_command = "/git-stage"
            cli._slash_arg_step = 0

            class FakeBuffer:
                text = "/"
                cursor_position = 1

            class FakeEvent:
                class App:
                    current_buffer = FakeBuffer()

                app = App()

            cli._accept_slash_selection(FakeEvent())

        self.assertEqual(FakeEvent.app.current_buffer.text, "/git-stage <path>")
        self.assertEqual(cli._current_input, "/git-stage <path>")
        self.assertIn("replace <path>", cli._status_message)
        self.assertEqual(FakeEvent.app.current_buffer.cursor_position, len("/git-stage "))
        self.assertIsNone(cli._worker_thread)

    def test_tty_slash_multi_argument_command_advances_steps(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._current_input = "/"
            cli._slash_group = "Tasks"
            for _ in range(20):
                if cli._selected_slash_row()["value"] == "/auto":
                    break
                cli._move_slash(1)
            self.assertEqual(cli._selected_slash_row()["value"], "/auto")

            class FakeBuffer:
                text = "/"
                cursor_position = 1

            class FakeEvent:
                class App:
                    current_buffer = FakeBuffer()

                app = App()

            cli._accept_slash_selection(FakeEvent())
            first = cli._slash_launcher_panel("/", cli._slash_selected)
            cli._accept_slash_selection(FakeEvent())
            second = cli._slash_launcher_panel("/", cli._slash_selected)

        self.assertEqual(cli._slash_command, "/auto")
        self.assertEqual(cli._slash_arg_step, 1)
        self.assertIn("<steps>", first)
        self.assertIn("<goal>", second)
        self.assertNotIn("current", "\n".join(cli._transcript))

    def test_tty_slash_multi_argument_command_preserves_choices(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._current_input = "/"
            cli._slash_command = "/auto"
            cli._slash_arg_step = 0
            for _ in range(12):
                if cli._selected_slash_row()["value"] == "3":
                    break
                cli._move_slash(1)
            self.assertEqual(cli._selected_slash_row()["value"], "3")

            class FakeBuffer:
                text = "/"
                cursor_position = 1

            class FakeEvent:
                class App:
                    current_buffer = FakeBuffer()

                app = App()

            cli._accept_slash_selection(FakeEvent())
            self.assertEqual(cli._slash_arg_step, 1)
            self.assertEqual(FakeEvent.app.current_buffer.text, "/")
            cli._accept_slash_selection(FakeEvent())

        self.assertEqual(FakeEvent.app.current_buffer.text, "/auto 3 <goal>")
        self.assertEqual(cli._current_input, "/auto 3 <goal>")
        self.assertIn("replace <goal>", cli._status_message)
        self.assertEqual(FakeEvent.app.current_buffer.cursor_position, len("/auto 3 "))
        self.assertIsNone(cli._worker_thread)

    def test_tty_slash_path_argument_uses_workspace_candidates(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=root)
            cli._current_input = "/"
            cli._slash_command = "/git-stage"
            cli._slash_arg_step = 0
            panel = cli._slash_launcher_panel("/", cli._slash_selected)

        self.assertIn("src/app.py", panel)
        self.assertIn("<path>", panel)

    def test_tty_slash_test_command_suggests_common_checks(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._current_input = "/"
            cli._slash_command = "/test"
            cli._slash_arg_step = 0
            panel = cli._slash_launcher_panel("/", cli._slash_selected)

        self.assertIn("python3 -m unittest discover -s tests", panel)
        self.assertIn("python3 evals/run_evals.py --filter tty_", panel)
        self.assertIn("格式检查", panel)

    def test_tty_slash_argument_quotes_values_with_spaces(self):
        from mini_agent import interactive_cli

        self.assertEqual(
            interactive_cli._command_template("/git-stage", ["docs/My File.md"]),
            "/git-stage 'docs/My File.md'",
        )

    def test_tty_exact_slash_command_enter_executes_after_fill(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))

            class FakeBuffer:
                text = "/setup"

            cli._handle_app_input(FakeBuffer())
            for _ in range(20):
                if "current" in "\n".join(cli._transcript):
                    break
                time.sleep(0.01)

        transcript = "\n".join(cli._transcript)
        self.assertNotIn("> /setup", transcript)
        self.assertIn("current", transcript)

    def test_tty_multiline_paste_submits_as_single_turn(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))

            class FakeBuffer:
                text = "hello\nworld\n  again"

            cli._handle_app_input(FakeBuffer())
            for _ in range(20):
                if "reply: hello world again" in "\n".join(cli._transcript):
                    break
                time.sleep(0.01)

        transcript = "\n".join(cli._transcript)
        self.assertIn("> hello world again", transcript)
        self.assertIn("reply: hello world again", transcript)
        self.assertEqual(cli._input_history[-1], "hello world again")

    def test_tty_input_history_up_down_restores_draft(self):
        from mini_agent import interactive_cli

        class FakeBuffer:
            text = "draft"
            cursor_position = 5

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._record_input_history("first")
            cli._record_input_history("second")
            buffer = FakeBuffer()
            cli._move_input_history(buffer, -1)
            latest = buffer.text
            cli._move_input_history(buffer, -1)
            previous = buffer.text
            cli._move_input_history(buffer, 1)
            forward = buffer.text
            cli._move_input_history(buffer, 1)
            restored = buffer.text

        self.assertEqual(latest, "second")
        self.assertEqual(previous, "first")
        self.assertEqual(forward, "second")
        self.assertEqual(restored, "draft")
        self.assertEqual(buffer.cursor_position, len("draft"))

    def test_tty_input_history_dedupes_consecutive_entries(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._record_input_history("same")
            cli._record_input_history("same")

        self.assertEqual(cli._input_history, ["same"])

    def test_tty_bottom_input_is_framed_and_fixed_in_layout(self):
        import unittest.mock
        from prompt_toolkit.widgets import Frame
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            with unittest.mock.patch.object(interactive_cli.shutil, "get_terminal_size", return_value=(100, 30)):
                cli._make_application()

        self.assertIsInstance(cli._input_frame, Frame)
        self.assertEqual(cli._input_frame.title, "Nora")

    def test_tty_standard_terminal_keeps_framed_input(self):
        import unittest.mock
        from prompt_toolkit.widgets import Frame
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            with unittest.mock.patch.object(interactive_cli.shutil, "get_terminal_size", return_value=(80, 24)):
                cli._make_application()

        self.assertIsInstance(cli._input_frame, Frame)

    def test_tty_status_line_is_below_input_frame(self):
        import unittest.mock
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            with unittest.mock.patch.object(interactive_cli.shutil, "get_terminal_size", return_value=(100, 30)):
                app = cli._make_application()
            children = app.layout.container.children

        self.assertIs(children[-2], cli._input_frame.container)
        self.assertIn("_render_status", repr(children[-1]))

    def test_tty_status_line_preserves_shortcuts(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = FakeSettings(
                provider="openai-compatible",
                model="deepseek-v4-flash",
                api_key="sk-secret123",
            )
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), settings=settings, root=Path(tmpdir))
            status = "".join(fragment for _, fragment in cli._render_status())

        self.assertIn("Ready", status)
        self.assertIn("/ commands", status)
        self.assertIn("Ctrl-Up/Down scroll", status)
        self.assertIn("Esc clear", status)
        self.assertIn("Ctrl-D exit", status)
        self.assertNotIn("deepseek-v4-flash", status)
        self.assertNotIn("API key", status)

    def test_tty_compact_status_keeps_ready_visible(self):
        import unittest.mock
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            with unittest.mock.patch.object(interactive_cli.shutil, "get_terminal_size", return_value=(60, 16)):
                status = "".join(fragment for _, fragment in cli._render_status())

        self.assertIn("Ready", status)
        self.assertIn("/ commands", status)

    def test_tty_status_line_is_padded_to_clear_old_text(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._status_message = "status: thinking"
            status = "".join(fragment for _, fragment in cli._render_status())

        self.assertTrue(status.startswith("status: thinking"))
        self.assertGreater(len(status), len("status: thinking"))
        self.assertEqual(status[-1], " ")

    def test_tty_body_tails_long_chat_to_latest_lines(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._transcript = ["\n".join(f"line {index}" for index in range(120))]
            body = "".join(fragment for _, fragment in cli._render_body(max_lines=20))

        self.assertNotIn("line 0\n", body)
        self.assertIn("line 119", body)
        self.assertLessEqual(body.count("\n"), 20)

    def test_tty_body_pageup_pages_back_through_history(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._transcript = ["\n".join(f"line {index}" for index in range(80))]
            latest = "".join(fragment for _, fragment in cli._render_body(max_lines=10, width=80))
            cli._scroll_body(-1, page_size=10)
            older = "".join(fragment for _, fragment in cli._render_body(max_lines=10, width=80))

        self.assertIn("line 79", latest)
        self.assertNotIn("line 79", older)
        self.assertIn("line 69", older)

    def test_tty_body_pagedown_returns_to_latest(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._transcript = ["\n".join(f"line {index}" for index in range(80))]
            cli._scroll_body(-1, page_size=10)
            cli._scroll_body(1, page_size=10)
            body = "".join(fragment for _, fragment in cli._render_body(max_lines=10, width=80))

        self.assertIn("line 79", body)

    def test_tty_new_reply_keeps_manual_scroll_position(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._transcript = ["\n".join(f"line {index}" for index in range(80))]
            cli._scroll_body(-1, page_size=10)
            cli._append_transcript("new final line")
            body = "".join(fragment for _, fragment in cli._render_body(max_lines=10, width=80))

        self.assertIn("line 69", body)
        self.assertNotIn("new final line", body)

    def test_tty_new_reply_follows_when_not_scrolled(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._transcript = ["\n".join(f"line {index}" for index in range(80))]
            cli._append_transcript("new final line")
            body = "".join(fragment for _, fragment in cli._render_body(max_lines=10, width=80))

        self.assertIn("new final line", body)

    def test_tty_body_wraps_long_single_line_before_tailing(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._transcript = ["A" * 180 + " END"]
            body = "".join(fragment for _, fragment in cli._render_body(max_lines=3, width=40))

        self.assertIn("END", body)
        self.assertNotIn("A" * 80, body)
        self.assertLessEqual(body.count("\n"), 3)

    def test_tty_body_wraps_cjk_before_tailing(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._transcript = ["中文测试" * 60 + "\n最后一行END"]
            body = "".join(fragment for _, fragment in cli._render_body(max_lines=4, width=36))

        self.assertIn("最后一行END", body)
        self.assertNotIn("中文测试" * 20, body)

    def test_tty_layout_uses_compact_input_on_small_screens(self):
        import unittest.mock
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            with unittest.mock.patch.object(interactive_cli.shutil, "get_terminal_size", return_value=(60, 18)):
                app = cli._make_application()

        self.assertFalse(any(getattr(child, "title", None) == "Nora" for child in app.layout.container.children))
        self.assertIsNone(cli._input_frame)

    def test_tty_input_change_clears_temporary_status(self):
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            app = cli._make_application()
            cli._status_message = "Use /exit or Ctrl-D to exit"
            input_buffer = app.layout.current_control.buffer
            input_buffer.text = "h"

        self.assertEqual(cli._status_message, "")

    def test_escape_clears_input_without_exiting(self):
        from mini_agent import interactive_cli

        class FakeBuffer:
            def __init__(self, text):
                self.text = text

        class FakeApp:
            def __init__(self, text):
                self.current_buffer = FakeBuffer(text)
                self.invalidated = False
                self.exited = False

            def invalidate(self):
                self.invalidated = True

            def exit(self):
                self.exited = True

        class FakeEvent:
            def __init__(self, app):
                self.app = app

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            app_with_input = FakeApp("/")
            cli._handle_escape(FakeEvent(app_with_input))
            app_without_input = FakeApp("")
            cli._handle_escape(FakeEvent(app_without_input))

        self.assertEqual(app_with_input.current_buffer.text, "")
        self.assertTrue(app_with_input.invalidated)
        self.assertFalse(app_with_input.exited)
        self.assertFalse(app_without_input.exited)
        self.assertTrue(app_without_input.invalidated)
        self.assertEqual(cli._status_message, "Use /exit or Ctrl-D to exit")

    def test_ctrl_c_clears_input_before_exit(self):
        from mini_agent import interactive_cli

        class FakeBuffer:
            def __init__(self, text):
                self.text = text

        class FakeApp:
            def __init__(self, text):
                self.current_buffer = FakeBuffer(text)
                self.invalidated = False
                self.exited = False

            def invalidate(self):
                self.invalidated = True

            def exit(self):
                self.exited = True

        class FakeEvent:
            def __init__(self, app):
                self.app = app

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            app_with_input = FakeApp("draft")
            cli._handle_interrupt(FakeEvent(app_with_input))
            app_without_input = FakeApp("")
            cli._handle_interrupt(FakeEvent(app_without_input))

        self.assertEqual(app_with_input.current_buffer.text, "")
        self.assertTrue(app_with_input.invalidated)
        self.assertFalse(app_with_input.exited)
        self.assertTrue(app_without_input.exited)

    def test_ctrl_d_exits_even_with_input(self):
        from mini_agent import interactive_cli

        class FakeBuffer:
            def __init__(self, text):
                self.text = text

        class FakeApp:
            def __init__(self, text):
                self.current_buffer = FakeBuffer(text)
                self.exited = False

            def exit(self):
                self.exited = True

        class FakeEvent:
            def __init__(self, app):
                self.app = app

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            app_with_input = FakeApp("draft")
            cli._handle_exit(FakeEvent(app_with_input))

        self.assertTrue(app_with_input.exited)

    def test_ctrl_c_during_work_cancels_current_turn(self):
        from mini_agent import interactive_cli

        class FakeBuffer:
            text = ""

        class FakeApp:
            current_buffer = FakeBuffer()
            invalidated = False
            exited = False

            def invalidate(self):
                self.invalidated = True

            def exit(self):
                self.exited = True

        class FakeEvent:
            app = FakeApp()

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._is_working = True
            cli._active_turn_id = 7
            cli._handle_interrupt(FakeEvent())

        self.assertFalse(FakeEvent.app.exited)
        self.assertTrue(FakeEvent.app.invalidated)
        self.assertFalse(cli._is_working)
        self.assertEqual(cli._cancelled_turn_ids, {7})
        self.assertIn("Cancelled", cli._status_message)

    def test_tty_cancelled_live_worker_blocks_next_submit_and_keeps_draft(self):
        import threading
        from mini_agent import interactive_cli

        class FakeBuffer:
            text = "next task"

        class FakeApp:
            invalidated = False

            def invalidate(self):
                self.invalidated = True

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli.app = FakeApp()
            blocker = threading.Event()
            cli._worker_thread = threading.Thread(target=blocker.wait, daemon=True)
            cli._worker_thread.start()
            existing_thread = cli._worker_thread
            cli._is_working = False
            buffer = FakeBuffer()
            handled = cli._handle_app_input(buffer)
            blocker.set()
            cli._worker_thread.join(timeout=1)

        self.assertTrue(handled)
        self.assertEqual(buffer.text, "next task")
        self.assertIs(cli._worker_thread, existing_thread)
        self.assertEqual(cli._active_turn_id, 0)
        self.assertIn("Cancelling current turn", cli._status_message)
        self.assertTrue(cli.app.invalidated)

    def test_cancelled_worker_result_is_ignored(self):
        from mini_agent.interactive_cli import InteractiveCLI

        class SlowAgent:
            def run(self, text):
                return "late reply"

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = InteractiveCLI(SlowAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._active_turn_id = 3
            cli._cancelled_turn_ids.add(3)
            cli._is_working = True
            cli._run_cli_input("hello", turn_id=3)

        self.assertNotIn("late reply", "\n".join(cli._transcript))
        self.assertFalse(cli._is_working)
        self.assertIn("Cancelled", cli._status_message)

    def test_non_current_worker_result_is_ignored(self):
        from mini_agent.interactive_cli import InteractiveCLI

        class SlowAgent:
            def run(self, text):
                return "stale reply"

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = InteractiveCLI(SlowAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._active_turn_id = 4
            cli._is_working = True
            cli._run_cli_input("hello", turn_id=3)

        self.assertNotIn("stale reply", "\n".join(cli._transcript))
        self.assertTrue(cli._is_working)

    def test_legacy_non_tty_emits_lifecycle(self):
        agent = FakeCLIAgent()
        outputs = []
        cli = MiniAgentCLI(
            agent,
            FakeCLIRegistry(),
            input_func=_fake_input(["hello", "exit"]),
            output_func=outputs.append,
        )

        cli.run()

        self.assertIn("Working...", outputs)
        self.assertIn("Done.", outputs)

    def test_tty_interactive_suppresses_lifecycle(self):
        from mini_agent.interactive_cli import InteractiveCLI

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            result = cli.cli.handle_input("hello")

        self.assertIn("reply: hello", result)
        self.assertEqual(cli._status_events, ["status: thinking", "Done."])

    def test_tty_run_events_shows_tool_activity_without_transcript_noise(self):
        from mini_agent.memory import ConversationMemory
        from mini_agent.interactive_cli import InteractiveCLI

        class EventAgent:
            def __init__(self):
                self.memory = ConversationMemory()
                self.last_run_report = FakeRunReport()

            def run_events(self, text):
                self.memory.add_user(text)
                yield {"type": "typing"}
                yield {"type": "tool_call_start", "name": "read_project_file", "arguments": {"path": "README.md"}}
                yield {"type": "tool_call_result", "name": "read_project_file", "status": "ok", "result": "content"}
                yield {"type": "delta", "content": "final answer"}
                self.memory.add_assistant("final answer")
                yield {"type": "done", "status": "done"}

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = InteractiveCLI(EventAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._run_agent_events_input("inspect project", turn_id=0)
            body_during = "\n".join(cli._activity_lines)
            transcript = "\n".join(cli._transcript)

        self.assertIn("tool: read_project_file ok", body_during)
        self.assertIn("final answer", transcript)
        self.assertNotIn("tool: read_project_file", transcript)

    def test_tty_run_events_streams_delta_into_body_then_commits_once(self):
        from mini_agent.memory import ConversationMemory
        from mini_agent.interactive_cli import InteractiveCLI

        class EventAgent:
            def __init__(self):
                self.memory = ConversationMemory()
                self.last_run_report = FakeRunReport()

            def run_events(self, text):
                self.memory.add_user(text)
                yield {"type": "typing"}
                yield {"type": "delta", "content": "hello"}
                yield {"type": "delta", "content": " world"}
                self.memory.add_assistant("hello world")
                yield {"type": "done", "status": "done"}

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = InteractiveCLI(EventAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            seen = []
            original_set_streaming = cli._set_streaming_answer

            def capture_stream(text):
                seen.append(text)
                original_set_streaming(text)

            cli._set_streaming_answer = capture_stream
            cli._run_agent_events_input("say hello", turn_id=0)
            transcript = "\n".join(cli._transcript)

        self.assertEqual(seen, ["hello", "hello world"])
        self.assertEqual(cli._streaming_answer, "")
        self.assertEqual(transcript.count("hello world"), 1)

    def test_tty_worker_errors_render_in_transcript(self):
        from mini_agent.interactive_cli import InteractiveCLI

        class ErrorAgent:
            def run(self, text):
                raise RuntimeError("boom")

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = InteractiveCLI(ErrorAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli._run_cli_input("hello")

        self.assertIn("error: boom", "\n".join(cli._transcript))
        self.assertEqual(cli._status_message, "")

    def test_interactive_cli_wires_confirm_action(self):
        from mini_agent.interactive_cli import InteractiveCLI

        with tempfile.TemporaryDirectory() as tmpdir:
            registry = FakeCLIRegistry()
            cli = InteractiveCLI(FakeCLIAgent(), registry, root=Path(tmpdir))

        self.assertEqual(registry.confirm_action, cli._confirm_action)

    def test_interactive_confirm_falls_back_before_app_runs(self):
        import unittest.mock
        from mini_agent import interactive_cli

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            with unittest.mock.patch.object(interactive_cli, "selectable_confirm", return_value=True) as fallback:
                result = cli._confirm_action("工具需要确认: run_shell_command\n原因: inspect project")

        self.assertTrue(result)
        fallback.assert_called_once()

    def test_selectable_confirm_uses_inline_card_when_stdout_is_tty(self):
        import unittest.mock
        from mini_agent import interactive_cli

        class FakeStdout:
            def isatty(self):
                return True

        with unittest.mock.patch.object(interactive_cli.sys, "stdout", FakeStdout()):
            with unittest.mock.patch.object(interactive_cli, "_run_approval_card", return_value=True) as card:
                result = interactive_cli.selectable_confirm("工具需要确认: run_shell_command\n原因: inspect project")

        self.assertTrue(result)
        card.assert_called_once()

    def test_approval_card_lines_match_design_contract(self):
        from mini_agent.interactive_cli import _approval_lines

        lines = "\n".join(_approval_lines("工具需要确认: run_shell_command\n权限: terminal/execute, 需要确认\n原因: inspect project", selected=2))

        self.assertIn("Tool approval", lines)
        self.assertIn("run_shell_command", lines)
        self.assertIn("execute", lines)
        self.assertIn("scope: terminal", lines)
        self.assertIn("why: inspect project", lines)
        self.assertIn("risk:", lines)
        self.assertIn("  Allow once", lines)
        self.assertIn("  Deny", lines)
        self.assertIn("> Always allow run_shell_command this session", lines)
        self.assertIn("Esc/Ctrl-C deny", lines)
        self.assertNotIn("+", lines)
        self.assertNotIn("|", lines)

    def test_approval_panel_height_fits_all_options(self):
        from mini_agent.interactive_cli import _approval_lines, _approval_panel_height

        prompt = "工具需要确认: run_shell_command\n权限: terminal/execute, 需要确认\n原因: inspect project"

        self.assertGreaterEqual(_approval_panel_height(), len(_approval_lines(prompt)))

    def test_approval_default_selection_matches_risk(self):
        from mini_agent.interactive_cli import _approval_default_index

        self.assertEqual(
            _approval_default_index("工具需要确认: read_project_file\n权限: workspace/read, 需要确认\n原因: inspect"),
            0,
        )
        self.assertEqual(
            _approval_default_index("工具需要确认: run_shell_command\n权限: terminal/execute, 需要确认\n原因: inspect"),
            1,
        )

    def test_approval_card_handles_wide_cjk_text(self):
        from mini_agent.interactive_cli import _approval_lines

        lines = _approval_lines(
            "工具需要确认: run_shell_command\n"
            "权限: terminal/execute, 需要确认\n"
            "原因: 查看项目根目录并确认中文不会撑歪线框",
            selected=0,
        )

        self.assertFalse(any(line.startswith(("+", "|")) for line in lines))
        self.assertIn("查看项目根目录", "\n".join(lines))
        self.assertTrue(all(len(line) <= 72 for line in lines))

    def test_in_app_approval_ctrl_c_denies_without_exit(self):
        import threading
        from mini_agent import interactive_cli

        class FakeApp:
            exited = False

            def exit(self):
                self.exited = True

        class FakeEvent:
            app = FakeApp()

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            event = threading.Event()
            cli._approval_state = {
                "prompt": "工具需要确认: run_shell_command\n原因: inspect project",
                "selected": 0,
                "event": event,
                "result": True,
            }
            cli._resolve_approval(False)

        self.assertTrue(event.is_set())
        self.assertFalse(cli._approval_state["result"])
        self.assertFalse(FakeEvent.app.exited)

    def test_in_app_approval_defaults_to_deny_for_execute(self):
        import threading
        from mini_agent import interactive_cli

        class FakeApp:
            _is_running = True
            invalidated = False

            def invalidate(self):
                self.invalidated = True

        prompt = "工具需要确认: run_shell_command\n权限: terminal/execute, 需要确认\n原因: inspect project"
        selected = []

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = interactive_cli.InteractiveCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir))
            cli.app = FakeApp()

            def release():
                while cli._approval_state is None:
                    pass
                selected.append(cli._approval_state["selected"])
                cli._approval_state["result"] = False
                cli._approval_state["event"].set()

            thread = threading.Thread(target=release)
            thread.start()
            result = cli._confirm_action(prompt)
            thread.join(timeout=1)

        self.assertFalse(result)
        self.assertEqual(selected, [1])

    def test_selectable_confirm_session_choice_allows_same_tool(self):
        import unittest.mock
        from mini_agent import interactive_cli

        class FakeStdout:
            def isatty(self):
                return True

        interactive_cli._SESSION_ALLOWED_TOOLS.clear()
        prompt = "工具需要确认: run_shell_command\n原因: inspect project"
        with unittest.mock.patch.object(interactive_cli.sys, "stdout", FakeStdout()):
            with unittest.mock.patch.object(interactive_cli, "_run_approval_card", return_value="session") as card:
                first = interactive_cli.selectable_confirm(prompt)
            with unittest.mock.patch.object(interactive_cli, "_run_approval_card") as second_card:
                second = interactive_cli.selectable_confirm(prompt)

        self.assertTrue(first)
        self.assertTrue(second)
        card.assert_called_once()
        second_card.assert_not_called()
        interactive_cli._SESSION_ALLOWED_TOOLS.clear()


class SlashCompleterTests(unittest.TestCase):
    def _get_completions(self, text):
        from prompt_toolkit.document import Document
        from mini_agent.interactive_cli import SlashCompleter

        completer = SlashCompleter(MiniAgentCLI.slash_command_names())
        document = Document(text=text, cursor_position=len(text))
        return [completion.text for completion in completer.get_completions(document, None)]

    def _get_completion_objects(self, text):
        from prompt_toolkit.document import Document
        from mini_agent.interactive_cli import SlashCompleter

        completer = SlashCompleter(MiniAgentCLI.slash_command_names())
        document = Document(text=text, cursor_position=len(text))
        return list(completer.get_completions(document, None))

    def test_slash_shows_commands(self):
        completions = self._get_completions("/")
        self.assertIn("/model", completions)
        self.assertIn("/help", completions)
        self.assertIn("/wake", completions)

    def test_slash_prefix_completes_model(self):
        self.assertIn("/model", self._get_completions("/m"))
        self.assertIn("/model", self._get_completions("/mo"))
        self.assertIn("/model", self._get_completions("/mod"))

    def test_slash_completion_includes_design_meta_and_style(self):
        completions = self._get_completion_objects("/")
        model = next(completion for completion in completions if completion.text == "/model")

        self.assertEqual(model.display_meta_text, "模型设置")
        self.assertIn("#3a3127", model.selected_style)

    def test_slash_match_supports_tab_binding(self):
        from mini_agent.interactive_cli import SlashCompleter

        completer = SlashCompleter(MiniAgentCLI.slash_command_names())

        self.assertEqual(completer.match("/mo"), ["/model"])
        self.assertEqual(completer.match("hello"), [])

    def test_exact_match_does_not_suggest_itself(self):
        self.assertNotIn("/model", self._get_completions("/model"))

    def test_non_slash_returns_nothing(self):
        self.assertEqual(self._get_completions("hello"), [])


if __name__ == "__main__":
    unittest.main()
