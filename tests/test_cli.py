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
        self.assertIn("Nora 已启动", outputs[0])
        self.assertIn("高风险工具会先确认", outputs[0])
        self.assertIn("Workspace:", outputs[0])
        self.assertIn("Tools:", outputs[0])
        self.assertTrue(any("Agent: reply: hello" in output for output in outputs))
        self.assertTrue(any("运行报告:" in output for output in outputs))
        self.assertTrue(any("工具: fake_tool(ok)" in output for output in outputs))

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
        self.assertIn("Nora 命令帮助", help_output)
        self.assertIn("推荐开始:", help_output)
        self.assertIn("Git:", help_output)
        self.assertIn("代码理解与测试:", help_output)
        self.assertIn("任务、记忆与上下文:", help_output)
        self.assertIn("自主执行:", help_output)
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
        self.assertIn("进入 Git 项目目录", result)
        self.assertIn("LLM_PROVIDER", result)
        self.assertIn("data/ 缺失通常没关系", result)

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
        self.assertIn("Agent: auto reply: inspect project / 3", result)

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

        self.assertIn("用法", cli.handle_slash_command("/auto"))
        self.assertIn("用法", cli.handle_slash_command("/auto 3"))
        self.assertEqual(agent.autonomous_calls, [])

    def test_symbol_commands_require_arguments(self):
        registry = FakeCLIRegistry()
        cli = MiniAgentCLI(FakeCLIAgent(), registry)

        self.assertIn("用法", cli.handle_slash_command("/symbol"))
        self.assertIn("用法", cli.handle_slash_command("/refs"))
        self.assertIn("用法", cli.handle_slash_command("/outline"))
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

    def test_prompt_includes_branch_when_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            cli = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=root)

            self.assertIn("Nora(", cli.prompt())


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


if __name__ == "__main__":
    unittest.main()
