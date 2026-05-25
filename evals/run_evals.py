from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from mini_agent.cli import MiniAgentCLI
from mini_agent.config import AgentConfig, load_agent_config
from mini_agent.context_summary import ContextSummaryStore
from mini_agent.context_window import ContextWindow
from mini_agent.controller import MiniAgent
from mini_agent.diagnostics import Diagnostics
from mini_agent.git_tools import GitTools
from mini_agent.llm import LLMResponse, ToolCall
from mini_agent.memory import LongTermMemory
from mini_agent.process_manager import ProcessManager
from mini_agent.providers.anthropic import AnthropicClient
from mini_agent.providers.factory import build_llm_client
from mini_agent.providers.gemini import GeminiClient
from mini_agent.providers.openai_compatible import OpenAICompatibleClient
from mini_agent.rag import ProjectRAG
from mini_agent.repair_loop import RepairLoop
from mini_agent.shell import ShellRunner
from mini_agent.settings import load_settings
from mini_agent.symbols import PythonSymbolIndex
from mini_agent.task_runner import TaskManager
from mini_agent.tool_results import ToolResultStore
from mini_agent.tools import WorkspaceFiles, build_default_registry


@dataclass
class EvalCase:
    name: str
    run: callable


def main() -> int:
    cases = [
        EvalCase("agent_calculates_math", eval_agent_calculates_math),
        EvalCase("cli_runs_command_and_exits", eval_cli_runs_command_and_exits),
        EvalCase("cli_handles_help_command", eval_cli_handles_help_command),
        EvalCase("cli_slash_status_uses_registry", eval_cli_slash_status_uses_registry),
        EvalCase("cli_multiline_input", eval_cli_multiline_input),
        EvalCase("notes_round_trip", eval_notes_round_trip),
        EvalCase("workspace_rejects_env", eval_workspace_rejects_env),
        EvalCase("workspace_writes_when_confirmed", eval_workspace_writes_when_confirmed),
        EvalCase("workspace_preview_replace_does_not_modify", eval_workspace_preview_replace_does_not_modify),
        EvalCase("workspace_apply_patch", eval_workspace_apply_patch),
        EvalCase("workspace_preview_multi_patch_does_not_modify", eval_workspace_preview_multi_patch_does_not_modify),
        EvalCase("workspace_apply_multi_patch", eval_workspace_apply_multi_patch),
        EvalCase("workspace_multi_patch_rejects_partial_failure", eval_workspace_multi_patch_rejects_partial_failure),
        EvalCase("registry_cancels_unconfirmed_write", eval_registry_cancels_unconfirmed_write),
        EvalCase("registry_cancels_unconfirmed_shell", eval_registry_cancels_unconfirmed_shell),
        EvalCase("browser_tools_read_page", eval_browser_tools_read_page),
        EvalCase("browser_tools_page_elements", eval_browser_tools_page_elements),
        EvalCase("registry_cancels_unconfirmed_browser_click", eval_registry_cancels_unconfirmed_browser_click),
        EvalCase("rag_finds_project_context", eval_rag_finds_project_context),
        EvalCase("rag_ranks_relevant_context_first", eval_rag_ranks_relevant_context_first),
        EvalCase("rag_reports_chunk_line_ranges", eval_rag_reports_chunk_line_ranges),
        EvalCase("rag_respects_include_paths", eval_rag_respects_include_paths),
        EvalCase("rag_skips_sensitive_paths", eval_rag_skips_sensitive_paths),
        EvalCase("tool_logs_can_be_viewed", eval_tool_logs_can_be_viewed),
        EvalCase("tool_audit_report", eval_tool_audit_report),
        EvalCase("git_status_readonly", eval_git_status_readonly),
        EvalCase("git_stage_and_commit_local", eval_git_stage_and_commit_local),
        EvalCase("git_rejects_sensitive_stage_path", eval_git_rejects_sensitive_stage_path),
        EvalCase("git_check_before_commit", eval_git_check_before_commit),
        EvalCase("registry_cancels_unconfirmed_git_write", eval_registry_cancels_unconfirmed_git_write),
        EvalCase("diagnostics_extracts_failure", eval_diagnostics_extracts_failure),
        EvalCase("repair_loop_reports_failure", eval_repair_loop_reports_failure),
        EvalCase("process_manager_start_read_stop", eval_process_manager_start_read_stop),
        EvalCase("registry_cancels_unconfirmed_process_start", eval_registry_cancels_unconfirmed_process_start),
        EvalCase("symbols_find_tool_registry", eval_symbols_find_tool_registry),
        EvalCase("symbols_describe_symbol", eval_symbols_describe_symbol),
        EvalCase("symbols_find_references", eval_symbols_find_references),
        EvalCase("cli_symbol_and_refs_commands", eval_cli_symbol_and_refs_commands),
        EvalCase("context_summary_round_trip", eval_context_summary_round_trip),
        EvalCase("agent_config_loads_yaml", eval_agent_config_loads_yaml),
        EvalCase("agent_config_disables_tools", eval_agent_config_disables_tools),
        EvalCase("agent_config_permission_policy", eval_agent_config_permission_policy),
        EvalCase("context_window_compacts_tool_result", eval_context_window_compacts_tool_result),
        EvalCase("tool_result_store_round_trip", eval_tool_result_store_round_trip),
        EvalCase("memory_rejects_secret", eval_memory_rejects_secret),
        EvalCase("shell_rejects_rm", eval_shell_rejects_rm),
        EvalCase("task_run_once_marks_step", eval_task_run_once_marks_step),
        EvalCase("task_update_step_records_summary", eval_task_update_step_records_summary),
        EvalCase("task_run_once_suggests_tool_type", eval_task_run_once_suggests_tool_type),
        EvalCase("task_blocked_requires_reason", eval_task_blocked_requires_reason),
        EvalCase("autonomous_loop_calculates_and_stops", eval_autonomous_loop_calculates_and_stops),
        EvalCase("autonomous_loop_respects_max_steps", eval_autonomous_loop_respects_max_steps),
        EvalCase("autonomous_loop_cancels_unconfirmed_write", eval_autonomous_loop_cancels_unconfirmed_write),
        EvalCase("cli_auto_command", eval_cli_auto_command),
        EvalCase("provider_factory_openai", eval_provider_factory_openai),
        EvalCase("provider_factory_anthropic", eval_provider_factory_anthropic),
        EvalCase("provider_factory_gemini", eval_provider_factory_gemini),
    ]
    if os.environ.get("EVAL_USE_LLM") == "1":
        cases.extend(
            [
                EvalCase("llm_calculate_tool_call", eval_llm_calculate_tool_call),
                EvalCase("llm_read_project_file", eval_llm_read_project_file),
                EvalCase("llm_search_project_context", eval_llm_search_project_context),
                EvalCase("llm_rag_project_qa", eval_llm_rag_project_qa),
                EvalCase("llm_preview_replace_tool_call", eval_llm_preview_replace_tool_call),
                EvalCase("llm_view_tool_logs", eval_llm_view_tool_logs),
                EvalCase("llm_git_status", eval_llm_git_status),
                EvalCase("llm_find_python_symbol", eval_llm_find_python_symbol),
                EvalCase("llm_run_project_tests", eval_llm_run_project_tests),
                EvalCase("llm_git_staged_diff", eval_llm_git_staged_diff),
                EvalCase("llm_browser_readonly_summary", eval_llm_browser_readonly_summary),
                EvalCase("llm_permission_denied_response", eval_llm_permission_denied_response),
                EvalCase("llm_compacted_tool_result_marker", eval_llm_compacted_tool_result_marker),
                EvalCase("llm_repair_loop_summary", eval_llm_repair_loop_summary),
                EvalCase("llm_background_process_status", eval_llm_background_process_status),
                EvalCase("llm_answer_with_project_context", eval_llm_answer_with_project_context),
                EvalCase("llm_task_step_summary", eval_llm_task_step_summary),
            ]
        )
    else:
        print("SKIP llm_* evals (set EVAL_USE_LLM=1 to run real model checks)")

    failures = []
    for case in cases:
        try:
            case.run()
        except AssertionError as error:
            failures.append((case.name, str(error)))
            print(f"FAIL {case.name}: {error}")
        except Exception as error:
            failures.append((case.name, repr(error)))
            print(f"ERROR {case.name}: {error!r}")
        else:
            print(f"PASS {case.name}")

    passed = len(cases) - len(failures)
    print(f"\n{passed} passed, {len(failures)} failed")
    return 1 if failures else 0


def eval_agent_calculates_math():
    agent = MiniAgent(build_default_registry())
    assert agent.run("计算 2 + 3 * 4") == "计算结果: 14"


def eval_cli_runs_command_and_exits():
    agent = FakeCLIAgent()
    outputs = []
    cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["hello", "exit"]), output_func=outputs.append)
    cli.run()
    assert agent.inputs == ["hello"]
    assert any("Agent: reply: hello" in output for output in outputs)


def eval_cli_handles_help_command():
    agent = FakeCLIAgent()
    outputs = []
    cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["/help", "exit"]), output_func=outputs.append)
    cli.run()
    assert agent.inputs == []
    assert any("/status" in output for output in outputs)


def eval_cli_slash_status_uses_registry():
    registry = FakeCLIRegistry()
    result = MiniAgentCLI(FakeCLIAgent(), registry).handle_slash_command("/status")
    assert registry.calls[-1] == ("git_status", {})
    assert "called git_status" in result


def eval_cli_multiline_input():
    agent = FakeCLIAgent()
    cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["<<<", "line1", "line2", ">>>", "exit"]), output_func=lambda output: None)
    cli.run()
    assert agent.inputs == ["line1\nline2"]


def eval_notes_round_trip():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = build_default_registry(notes_path=Path(tmpdir) / "notes.txt")
        agent = MiniAgent(registry)
        assert agent.run("保存笔记 eval note") == "笔记已保存。"
        assert "eval note" in agent.run("读取笔记")


def eval_workspace_rejects_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".env").write_text("LLM_API_KEY=secret", encoding="utf-8")
        files = WorkspaceFiles(root)
        assert "拒绝读取" in files.read(".env")


def eval_workspace_writes_when_confirmed():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        files = WorkspaceFiles(root, confirm_action=lambda prompt: True)
        assert "已写入文件" in files.write("docs/eval.md", "ok", reason="eval")
        assert (root / "docs" / "eval.md").read_text(encoding="utf-8") == "ok"


def eval_workspace_preview_replace_does_not_modify():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target = root / "README.md"
        target.write_text("hello old\n", encoding="utf-8")
        files = WorkspaceFiles(root)
        result = files.preview_replace("README.md", "old", "new")
        assert "-hello old" in result
        assert "+hello new" in result
        assert target.read_text(encoding="utf-8") == "hello old\n"


def eval_workspace_apply_patch():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target = root / "README.md"
        target.write_text("hello old\n", encoding="utf-8")
        files = WorkspaceFiles(root, confirm_action=lambda prompt: True)
        patch = """--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-hello old
+hello new
"""
        result = files.apply_unified_diff(patch, reason="eval")
        assert "已应用 patch" in result
        assert target.read_text(encoding="utf-8") == "hello new\n"


def eval_workspace_preview_multi_patch_does_not_modify():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "a.txt").write_text("old a\n", encoding="utf-8")
        (root / "b.txt").write_text("old b\n", encoding="utf-8")
        patch = """--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-old a
+new a
--- a/b.txt
+++ b/b.txt
@@ -1 +1 @@
-old b
+new b
"""
        result = WorkspaceFiles(root).preview_multi_file_patch(patch)
        assert "a.txt" in result and "b.txt" in result
        assert (root / "a.txt").read_text(encoding="utf-8") == "old a\n"
        assert (root / "b.txt").read_text(encoding="utf-8") == "old b\n"


def eval_workspace_apply_multi_patch():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "a.txt").write_text("old a\n", encoding="utf-8")
        (root / "b.txt").write_text("old b\n", encoding="utf-8")
        patch = """--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-old a
+new a
--- a/b.txt
+++ b/b.txt
@@ -1 +1 @@
-old b
+new b
"""
        result = WorkspaceFiles(root, confirm_action=lambda prompt: True).apply_multi_file_patch(patch, reason="eval")
        assert "已应用多文件 patch" in result
        assert (root / "a.txt").read_text(encoding="utf-8") == "new a\n"
        assert (root / "b.txt").read_text(encoding="utf-8") == "new b\n"


def eval_workspace_multi_patch_rejects_partial_failure():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "a.txt").write_text("old a\n", encoding="utf-8")
        (root / "b.txt").write_text("old b\n", encoding="utf-8")
        patch = """--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-old a
+new a
--- a/b.txt
+++ b/b.txt
@@ -1 +1 @@
-missing
+new b
"""
        result = WorkspaceFiles(root, confirm_action=lambda prompt: True).apply_multi_file_patch(patch, reason="eval")
        assert "不匹配" in result
        assert (root / "a.txt").read_text(encoding="utf-8") == "old a\n"
        assert (root / "b.txt").read_text(encoding="utf-8") == "old b\n"


def eval_registry_cancels_unconfirmed_write():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        registry = build_default_registry(
            workspace_root=root,
            confirm_action=lambda prompt: False,
        )
        result = registry.call(
            "write_project_file",
            path="docs/eval.md",
            content="ok",
            reason="eval",
        )
        assert result == "已取消操作。"
        assert not (root / "docs" / "eval.md").exists()


def eval_registry_cancels_unconfirmed_shell():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = build_default_registry(
            workspace_root=Path(tmpdir),
            confirm_action=lambda prompt: False,
        )
        result = registry.call(
            "run_shell_command",
            command="pwd",
            reason="eval",
        )
        assert result == "已取消操作。"


def eval_browser_tools_read_page():
    backend = FakeBrowserBackend()
    registry = build_default_registry(browser_backend=backend)
    assert registry.call("browser_open_url", url="https://example.com") == "已打开页面: https://example.com"
    assert registry.call("browser_page_title") == "页面标题: Eval Page"
    assert "Eval browser text" in registry.call("browser_page_text", max_chars=1000)


def eval_browser_tools_page_elements():
    backend = FakeBrowserBackend()
    registry = build_default_registry(browser_backend=backend)
    assert registry.call("browser_wait_for_selector", selector="#submit") == "已找到元素: #submit"
    elements = registry.call("browser_page_elements", max_items=5)
    summary = registry.call("browser_page_summary", max_text_chars=500, max_elements=5)
    assert "Eval Docs - https://example.com/docs" in elements
    assert "#submit text=Submit" in elements
    assert "#q type=text" in elements
    assert "title: Eval Page" in summary


def eval_registry_cancels_unconfirmed_browser_click():
    backend = FakeBrowserBackend()
    registry = build_default_registry(
        browser_backend=backend,
        confirm_action=lambda prompt: False,
    )
    result = registry.call("browser_click", selector="#submit", reason="eval")
    assert result == "已取消操作。"
    assert backend.clicked == []


def eval_rag_finds_project_context():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "README.md").write_text("agent tool calling architecture", encoding="utf-8")
        rag = ProjectRAG(root)
        result = rag.search("tool architecture")
        assert "README.md" in result
        assert "tool calling architecture" in result


def eval_rag_ranks_relevant_context_first():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "partial.md").write_text("tool " * 20, encoding="utf-8")
        (root / "complete.md").write_text("tool architecture", encoding="utf-8")
        results = ProjectRAG(root).search_results("tool architecture", max_results=2)
        assert results[0].path == "complete.md", results


def eval_rag_reports_chunk_line_ranges():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        lines = [f"filler {index}" for index in range(25)]
        lines[4] = "needle first"
        lines[16] = "needle second"
        (root / "guide.md").write_text("\n".join(lines), encoding="utf-8")
        result = ProjectRAG(root, chunk_size=10, chunk_overlap=0).search("needle", max_results=2)
        assert "path=guide.md lines=1-10" in result, result
        assert "score=" in result, result


def eval_rag_respects_include_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "src").mkdir()
        (root / "docs").mkdir()
        (root / "src" / "app.py").write_text("needle src", encoding="utf-8")
        (root / "docs" / "guide.md").write_text("needle docs", encoding="utf-8")
        result = ProjectRAG(root, include_paths=["src"]).search("needle")
        assert "src/app.py" in result, result
        assert "docs/guide.md" not in result, result


def eval_rag_skips_sensitive_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        for dirname in ("data", "logs", ".git"):
            (root / dirname).mkdir()
            (root / dirname / "secret.md").write_text("needle", encoding="utf-8")
        (root / "public.md").write_text("needle", encoding="utf-8")
        result = ProjectRAG(root).search("needle")
        assert "public.md" in result
        assert "secret.md" not in result


def eval_tool_logs_can_be_viewed():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        log_path = root / "tool_calls.jsonl"
        registry = build_default_registry(workspace_root=root, log_path=log_path)
        registry.call("calculate", expression="1 + 2")
        result = registry.call("view_tool_logs", max_entries=5)
        assert "calculate" in result
        assert "ok" in result
        assert "expression" not in result


def eval_tool_audit_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        log_path = root / "tool_calls.jsonl"
        registry = build_default_registry(workspace_root=root, log_path=log_path, confirm_action=lambda prompt: False)
        registry.call("calculate", expression="1 + 2")
        registry.call("write_project_file", path="notes.md", content="ok", reason="eval")
        result = registry.call("generate_audit_report", max_entries=10)
        assert "审计范围" in result, result
        assert "write_project_file" in result, result
        assert "cancelled" in result, result


def eval_git_status_readonly():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=root, capture_output=True, text=True, check=True)
        (root / "README.md").write_text("eval\n", encoding="utf-8")
        result = GitTools(root).status()
        assert "README.md" in result
        assert (root / "README.md").read_text(encoding="utf-8") == "eval\n"


def eval_git_stage_and_commit_local():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _init_git_repo(root)
        (root / "README.md").write_text("eval changed\n", encoding="utf-8")
        git = GitTools(root)
        assert "已暂存路径" in git.stage_paths(["README.md"])
        assert "+eval changed" in git.staged_diff()
        assert "已创建本地提交" in git.commit_staged("eval commit")
        assert "eval commit" in git.log(max_count=1)


def eval_git_rejects_sensitive_stage_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _init_git_repo(root)
        (root / ".env").write_text("secret", encoding="utf-8")
        assert "拒绝暂存" in GitTools(root).stage_paths([".env"])


def eval_registry_cancels_unconfirmed_git_write():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _init_git_repo(root)
        (root / "README.md").write_text("eval changed\n", encoding="utf-8")
        registry = build_default_registry(workspace_root=root, confirm_action=lambda prompt: False)
        result = registry.call("git_stage_paths", paths=["README.md"], reason="eval")
        assert result == "已取消操作。"
        assert "+eval changed" not in GitTools(root).staged_diff()


def eval_git_check_before_commit():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _init_git_repo(root)
        git = GitTools(root)
        assert "staged changes: 无" in git.check_before_commit()
        (root / "README.md").write_text("eval changed\n", encoding="utf-8")
        assert "unstaged/untracked changes: 有" in git.check_before_commit()
        git.stage_paths(["README.md"])
        assert "staged changes: 有" in git.check_before_commit()


def eval_diagnostics_extracts_failure():
    output = '''FAIL: test_eval (tests.test_eval.EvalTest.test_eval)
Traceback (most recent call last):
  File "tests/test_eval.py", line 7, in test_eval
    self.assertEqual(1, 2)
AssertionError: 1 != 2
'''
    result = Diagnostics(PROJECT_ROOT).diagnose_test_failure(output)
    assert "FAIL: test_eval" in result
    assert "tests/test_eval.py" in result
    assert "AssertionError" in result


def eval_repair_loop_reports_failure():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        tests_dir = root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_fail.py").write_text(
            "import unittest\n\nclass T(unittest.TestCase):\n    def test_fail(self):\n        self.assertEqual(1, 2)\n",
            encoding="utf-8",
        )
        result = RepairLoop(Diagnostics(root)).run(max_attempts=1)
        assert "attempt 1" in result
        assert "AssertionError" in result
        assert "未自动应用 patch" in result


def eval_process_manager_start_read_stop():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ProcessManager(
            Path(tmpdir),
            profiles={"slow": ["python3", "-c", "import time; print('ready', flush=True); time.sleep(5)"]},
        )
        started = manager.start("slow")
        process_id = started.split()[1]
        assert "已启动后台进程" in started
        assert "已匹配" in manager.wait_for_output(process_id, "ready", timeout_seconds=5)
        assert "ready" in manager.read_output(process_id)
        assert "已停止后台进程" in manager.stop(process_id)


def eval_registry_cancels_unconfirmed_process_start():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = build_default_registry(workspace_root=Path(tmpdir), confirm_action=lambda prompt: False)
        result = registry.call("start_background_process", profile="static_server_8000", reason="eval")
        assert result == "已取消操作。"


def eval_symbols_find_tool_registry():
    result = PythonSymbolIndex(PROJECT_ROOT).find_symbol("ToolRegistry")
    assert "mini_agent/registry.py" in result
    assert "class ToolRegistry" in result


def eval_symbols_describe_symbol():
    result = PythonSymbolIndex(PROJECT_ROOT).describe_symbol("ToolRegistry.call", context_lines=2)
    assert "mini_agent/registry.py" in result
    assert "ToolRegistry.call" in result
    assert "signature:" in result


def eval_symbols_find_references():
    result = PythonSymbolIndex(PROJECT_ROOT).find_references("ToolRegistry", max_results=20)
    assert "可能引用 ToolRegistry" in result
    assert "Name" in result or "Attribute" in result


def eval_cli_symbol_and_refs_commands():
    registry = FakeCLIRegistry()
    cli = MiniAgentCLI(FakeCLIAgent(), registry)
    cli.handle_slash_command("/symbol ToolRegistry")
    cli.handle_slash_command("/refs ToolRegistry")
    assert registry.calls[-2] == ("describe_python_symbol", {"name": "ToolRegistry"})
    assert registry.calls[-1] == ("find_python_references", {"name": "ToolRegistry"})


def eval_context_summary_round_trip():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ContextSummaryStore(Path(tmpdir) / "context.jsonl")
        assert "已保存上下文摘要" in store.save_summary("eval topic", "eval summary", source="eval")
        assert "eval topic" in store.search_summaries("summary")
        assert "eval summary" in store.list_summaries()


def eval_agent_config_loads_yaml():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "agent.yaml"
        path.write_text(
            "\n".join(
                [
                    "paths:",
                    "  notes: state/notes.txt",
                    "context_window:",
                    "  max_tool_result_chars: 1234",
                    "processes:",
                    "  profiles:",
                    "    ready:",
                    "      command: [\"python3\", \"-c\", \"print('ready')\"]",
                ]
            ),
            encoding="utf-8",
        )
        config = load_agent_config(path)
        assert config.paths.notes == Path("state/notes.txt")
        assert config.context_window.max_tool_result_chars == 1234
        assert config.processes.profiles["ready"] == ["python3", "-c", "print('ready')"]


def eval_agent_config_disables_tools():
    config = AgentConfig.from_dict({"tools": {"disabled": ["fetch_url"]}})
    registry = build_default_registry(disabled_tools=config.tools.disabled)
    tool_names = {tool["function"]["name"] for tool in registry.to_openai_tools()}
    assert "fetch_url" not in tool_names


def eval_agent_config_permission_policy():
    config = AgentConfig.from_dict(
        {
            "permissions": {
                "deny": ["run_shell_command"],
                "confirmation_overrides": {"fetch_url": True},
            }
        }
    )
    registry = build_default_registry(
        disabled_tools=config.disabled_tools(),
        permission_overrides=config.permission_overrides(),
        confirm_action=lambda prompt: False,
        web_fetch=lambda url, timeout: "ok",
    )
    tool_names = {tool["function"]["name"] for tool in registry.to_openai_tools()}
    assert "run_shell_command" not in tool_names
    assert registry.call("fetch_url", url="https://example.com") == "已取消操作。"


def eval_context_window_compacts_tool_result():
    window = ContextWindow(max_tool_result_chars=20, head_chars=6, tail_chars=6)
    result = window.compact_tool_result("eval_tool", "AAAAAA" + "MIDDLE" * 5 + "ZZZZZZ")
    assert "tool_result_compacted" in result
    assert "eval_tool" in result
    assert "AAAAAA" in result
    assert "ZZZZZZ" in result
    assert "MIDDLEMIDDLE" not in result


def eval_tool_result_store_round_trip():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ToolResultStore(Path(tmpdir) / "tool_results.jsonl")
        result_id = store.save("eval_tool", "first line\nneedle line\nlast line")
        assert result_id.startswith("tr_")
        assert result_id in store.list()
        assert "needle line" in store.read(result_id, offset=0, limit=100)
        assert "needle line" in store.search(query="needle")


def eval_memory_rejects_secret():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = LongTermMemory(Path(tmpdir) / "memory.jsonl")
        assert "拒绝保存" in memory.save("OPENAI_API_KEY=secret")


def eval_shell_rejects_rm():
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = ShellRunner(Path(tmpdir), confirm_action=lambda prompt: True)
        assert "拒绝执行" in runner.run("rm -rf .", reason="eval")


def eval_task_run_once_marks_step():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = TaskManager(Path(tmpdir) / "task.json")
        manager.start("eval task", "读代码\n写测试")
        assert "下一步: 1. 读代码" in manager.run_once()
        assert "1. [in_progress] 读代码" in manager.list()


def eval_task_update_step_records_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = TaskManager(Path(tmpdir) / "task.json")
        manager.start("eval task", "实现")
        manager.update_step(1, "done", note="测试通过", summary="实现完成")
        listing = manager.list()
        assert "备注: 测试通过" in listing
        assert "总结: 实现完成" in listing


def eval_task_run_once_suggests_tool_type():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = TaskManager(Path(tmpdir) / "task.json")
        manager.start("eval task", "运行测试")
        result = manager.run_once()
        listing = manager.list()
        assert "建议工具类型" in result, result
        assert "test/" in result, result
        assert "当前步骤: 1. 运行测试" in listing, listing


def eval_task_blocked_requires_reason():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = TaskManager(Path(tmpdir) / "task.json")
        manager.start("eval task", "等待依赖")
        result = manager.update_step(1, "blocked")
        assert "阻塞原因" in result, result


def eval_autonomous_loop_calculates_and_stops():
    class FakeToolCallingLLM:
        def __init__(self):
            self.calls = []

        def chat(self, messages, tools=None):
            self.calls.append(messages)
            if len(self.calls) == 1:
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(call_id="call_1", name="calculate", arguments={"expression": "2 + 3"})],
                )
            return LLMResponse(content="done: 5")

    agent = MiniAgent(build_default_registry(), llm=FakeToolCallingLLM())
    result = agent.run_autonomous("计算 2 + 3", max_steps=3)
    assert "受控自主执行已停止: done" in result, result
    assert "tool:calculate" in result, result
    assert "5" in result, result


def eval_autonomous_loop_respects_max_steps():
    class FakeToolCallingLLM:
        def __init__(self):
            self.calls = []

        def chat(self, messages, tools=None):
            self.calls.append(messages)
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(call_id=f"call_{len(self.calls)}", name="calculate", arguments={"expression": "1 + 1"})],
            )

    llm = FakeToolCallingLLM()
    result = MiniAgent(build_default_registry(), llm=llm).run_autonomous("持续计算", max_steps=2)
    assert "max_steps_reached" in result, result
    assert len(llm.calls) == 2


def eval_autonomous_loop_cancels_unconfirmed_write():
    class FakeToolCallingLLM:
        def chat(self, messages, tools=None):
            return LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        call_id="call_1",
                        name="write_project_file",
                        arguments={"path": "docs/auto.md", "content": "hello", "reason": "eval"},
                    )
                ],
            )

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        registry = build_default_registry(workspace_root=root, confirm_action=lambda prompt: False)
        result = MiniAgent(registry, llm=FakeToolCallingLLM()).run_autonomous("写文件", max_steps=3)
        assert "blocked" in result, result
        assert "已取消操作" in result, result
        assert not (root / "docs" / "auto.md").exists()


def eval_cli_auto_command():
    agent = FakeCLIAgent()
    result = MiniAgentCLI(agent, FakeCLIRegistry()).handle_slash_command("/auto 3 inspect project")
    assert agent.autonomous_calls == [("inspect project", 3)]
    assert "Agent: auto reply: inspect project / 3" in result, result


def eval_provider_factory_openai():
    settings = load_settings(
        environ={
            "LLM_PROVIDER": "openai-compatible",
            "LLM_BASE_URL": "https://example.com/v1",
            "LLM_API_KEY": "test-key",
            "LLM_MODEL": "test-model",
        }
    )
    assert isinstance(build_llm_client(settings), OpenAICompatibleClient)


def eval_provider_factory_anthropic():
    settings = load_settings(
        environ={
            "LLM_PROVIDER": "anthropic",
            "ANTHROPIC_API_KEY": "test-key",
            "ANTHROPIC_MODEL": "claude-test",
        }
    )
    assert isinstance(build_llm_client(settings), AnthropicClient)


def eval_provider_factory_gemini():
    settings = load_settings(
        environ={
            "LLM_PROVIDER": "gemini",
            "GEMINI_API_KEY": "test-key",
            "GEMINI_MODEL": "gemini-test",
        }
    )
    assert isinstance(build_llm_client(settings), GeminiClient)


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=root, capture_output=True, text=True, check=True)


def eval_llm_calculate_tool_call():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请使用工具计算 2 + 3 * 4，最终只需要说明结果。")
    assert "14" in result, result


def eval_llm_read_project_file():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请读取 README.md，并用一句话说明这个项目是什么。")
    assert "Nora" in result or "agent" in result.lower(), result


def eval_llm_search_project_context():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请搜索项目上下文：tool calling 是在哪里实现的？")
    assert "tool" in result.lower() or "工具" in result, result


def eval_llm_rag_project_qa():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请使用 answer_with_project_context 工具回答：MiniAgentCLI 的 slash command 入口在哪里？")
    assert "MiniAgentCLI" in result or "cli.py" in result or "slash" in result.lower(), result


def eval_llm_preview_replace_tool_call():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请使用工具预览把 README.md 里的 Nora 替换成 Nora Eval，最终说明 diff 里出现了什么。")
    assert "README.md" in result or "diff" in result.lower() or "Nora Eval" in result, result


def eval_llm_view_tool_logs():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    agent.run("请使用工具计算 1 + 2。")
    result = agent.run("请查看最近 5 条工具调用日志。")
    assert "calculate" in result or "工具" in result or "日志" in result, result


def eval_llm_git_status():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请使用 git_status 工具查看当前 git 状态，并简短说明结果。")
    assert "git" in result.lower() or "状态" in result or "文件" in result, result


def eval_llm_find_python_symbol():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请使用 find_python_symbol 工具查找 ToolRegistry 在哪里定义。")
    assert "ToolRegistry" in result or "registry.py" in result, result


def eval_llm_run_project_tests():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请使用 run_project_tests 工具运行项目测试，并简短说明是否通过。")
    assert "OK" in result or "测试" in result or "pass" in result.lower(), result


def eval_llm_git_staged_diff():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请使用 git_staged_diff 工具查看已暂存 diff，并说明是否有内容。")
    assert "diff" in result.lower() or "暂存" in result or "Git" in result, result


def eval_llm_browser_readonly_summary():
    agent = _build_real_llm_agent(PROJECT_ROOT, browser_backend=FakeBrowserBackend())
    result = agent.run("请使用 browser_page_summary 或 browser_page_elements 读取当前浏览器页面摘要，不要点击或输入，然后说明页面标题。")
    assert "Eval Page" in result or "页面" in result or "title" in result.lower(), result


def eval_llm_permission_denied_response():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请尝试使用 write_project_file 写入 docs/llm_denied_eval.md，内容 ok；如果操作被取消，请解释已取消，不要再尝试其他写操作。")
    assert "取消" in result or "拒绝" in result or "permission" in result.lower() or "confirm" in result.lower(), result
    assert not (PROJECT_ROOT / "docs" / "llm_denied_eval.md").exists()


def eval_llm_compacted_tool_result_marker():
    agent = _build_real_llm_agent(
        PROJECT_ROOT,
        context_window=ContextWindow(max_tool_result_chars=200, head_chars=80, tail_chars=80),
    )
    result = agent.run("请读取 README.md，并判断工具结果里是否出现 tool_result_compacted 标记；如果出现请明确写出 tool_result_compacted。")
    assert "tool_result_compacted" in result or "压缩" in result or "compacted" in result.lower(), result


def eval_llm_repair_loop_summary():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请使用 run_repair_loop 工具最多运行 1 轮，并简短说明结果。")
    assert "取消" in result or "测试" in result or "repair" in result.lower(), result


def eval_llm_background_process_status():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请使用 list_background_processes 工具查看后台进程状态。")
    assert "后台进程" in result or "process" in result.lower(), result


def eval_llm_answer_with_project_context():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请使用 answer_with_project_context 工具回答：TaskManager 在哪里实现？")
    assert "TaskManager" in result or "task_runner" in result or "任务" in result, result


def eval_llm_task_step_summary():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请创建一个任务，目标是 eval summary，步骤只有一行：检查；然后把第 1 步标记为 done，summary 写 eval summary done，最后查看任务。")
    assert "eval summary" in result or "done" in result, result


def _build_real_llm_agent(
    workspace_root: Path,
    browser_backend=None,
    context_window: ContextWindow = None,
) -> MiniAgent:
    settings = load_settings(PROJECT_ROOT / ".env")
    llm = build_llm_client(settings)
    assert llm is not None, "LLM is not configured. Check .env before using EVAL_USE_LLM=1."
    tmp_root = PROJECT_ROOT / "evals" / ".tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    registry = build_default_registry(
        workspace_root=workspace_root,
        notes_path=tmp_root / "notes.txt",
        log_path=tmp_root / "tool_calls.jsonl",
        long_term_memory_path=tmp_root / "memory.jsonl",
        task_state_path=tmp_root / "task.json",
        browser_backend=browser_backend,
        confirm_action=lambda prompt: False,
    )
    return MiniAgent(
        registry,
        llm=llm,
        context_window=context_window,
        tool_result_store=ToolResultStore(tmp_root / "tool_results.jsonl"),
    )


class FakeCLIAgent:
    def __init__(self):
        self.inputs = []
        self.autonomous_calls = []

    def run(self, text):
        self.inputs.append(text)
        return f"reply: {text}"

    def run_autonomous(self, goal, max_steps=None):
        self.autonomous_calls.append((goal, max_steps))
        return f"auto reply: {goal} / {max_steps}"


class FakeCLIRegistry:
    def __init__(self):
        self.calls = []

    def call(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        return f"called {tool_name}"

    def describe(self):
        return "tools"

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


class FakeBrowserBackend:
    def __init__(self):
        self.opened_url = ""
        self.clicked = []
        self.waited = []

    def open_url(self, url: str) -> None:
        self.opened_url = url

    def page_title(self) -> str:
        return "Eval Page"

    def page_text(self) -> str:
        return "Eval browser text"

    def click(self, selector: str) -> None:
        self.clicked.append(selector)

    def fill(self, selector: str, text: str) -> None:
        pass

    def wait_for_selector(self, selector: str, timeout_ms: int) -> None:
        self.waited.append((selector, timeout_ms))

    def page_elements(self, max_items: int):
        return {
            "links": [{"text": "Eval Docs", "href": "https://example.com/docs"}],
            "buttons": [{"text": "Submit", "selector": "#submit"}],
            "inputs": [{"selector": "#q", "type": "text", "name": "q", "placeholder": "Search"}],
        }

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"eval")


if __name__ == "__main__":
    raise SystemExit(main())
