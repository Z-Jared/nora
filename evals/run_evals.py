from dataclasses import dataclass
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from mini_agent.cli import MiniAgentCLI
from mini_agent.config import AgentConfig, load_agent_config
from mini_agent.context_compiler import ContextCompiler
from mini_agent.context_summary import ContextSummaryStore
from mini_agent.database import NoraDB
from mini_agent.context_system import ContextSystem
from mini_agent.context_window import ContextWindow
from mini_agent.controller import MiniAgent
from mini_agent.diagnostics import Diagnostics
from mini_agent.git_tools import GitTools
from mini_agent.llm import LLMError, LLMResponse, ToolCall
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
from mini_agent.durable_tasks import DurableTaskStore, TaskStatus
from mini_agent.durable_events import DurableEventStore, FILE_EDIT_BLOCKED, FILE_EDIT_ERROR, FILE_EDIT_FINISHED, FILE_EDIT_STARTED, MODEL_CALL_ERROR, MODEL_CALL_FINISHED, MODEL_CALL_STARTED, SHELL_COMMAND_BLOCKED, SHELL_COMMAND_ERROR, SHELL_COMMAND_FINISHED, SHELL_COMMAND_STARTED, TEST_RUN_BLOCKED, TEST_RUN_ERROR, TEST_RUN_FINISHED, TEST_RUN_STARTED, TOOL_CALL_BLOCKED, TOOL_CALL_ERROR, TOOL_CALL_FINISHED, TOOL_CALL_STARTED
from mini_agent.traces import TraceStore, RunTrace, ToolCallTrace, build_trace, truncate_preview


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
        EvalCase("cli_doctor_reports_runtime_status", eval_cli_doctor_reports_runtime_status),
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
        EvalCase("context_system_injects_auto_context", eval_context_system_injects_auto_context),
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
        EvalCase("context_compiler_includes_git_status_and_outline", eval_context_compiler_includes_git_status_and_outline),
        EvalCase("context_compiler_skips_sensitive_paths", eval_context_compiler_skips_sensitive_paths),
        EvalCase("context_compiler_tool_returns_markdown", eval_context_compiler_tool_returns_markdown),
        EvalCase("trace_store_records_run", eval_trace_store_records_run),
        EvalCase("trace_redacts_sensitive_input", eval_trace_redacts_sensitive_input),
        EvalCase("trace_redacts_sensitive_tool_preview", eval_trace_redacts_sensitive_tool_preview),
        EvalCase("trace_lists_and_gets", eval_trace_lists_and_gets),
        EvalCase("trace_inspection_tools_via_registry", eval_trace_inspection_tools_via_registry),
        EvalCase("durable_task_schema_spec", eval_durable_task_schema_spec),
        EvalCase("durable_task_taskmanager_mapping_spec", eval_durable_task_taskmanager_mapping_spec),
        EvalCase("list_durable_tasks_returns_correct_fields", eval_list_durable_tasks_returns_correct_fields),
        EvalCase("get_durable_task_returns_complete_data", eval_get_durable_task_returns_complete_data),
        EvalCase("durable_task_status_transitions", eval_durable_task_status_transitions),
        EvalCase("cli_durable_tasks_output_format", eval_cli_durable_tasks_output_format),
        EvalCase("cli_durable_task_detail_output", eval_cli_durable_task_detail_output),
        EvalCase("cli_dashboard_shows_status_distribution", eval_cli_dashboard_shows_status_distribution),
        EvalCase("cli_dashboard_shows_running_and_completed", eval_cli_dashboard_shows_running_and_completed),
        EvalCase("crud_create_durable_task", eval_crud_create_durable_task),
        EvalCase("crud_get_durable_task", eval_crud_get_durable_task),
        EvalCase("crud_update_durable_task", eval_crud_update_durable_task),
        EvalCase("crud_delete_durable_task", eval_crud_delete_durable_task),
        EvalCase("crud_full_lifecycle", eval_crud_full_lifecycle),
        EvalCase("task_manager_durable_shadow_consistency", eval_task_manager_durable_shadow_consistency),
        EvalCase("task_manager_durable_shadow_failure_isolation", eval_task_manager_durable_shadow_failure_isolation),
        EvalCase("retry_state_machine_consistency", eval_retry_state_machine_consistency),
        EvalCase("trace_links_to_durable_task", eval_trace_links_to_durable_task),
        EvalCase("durable_event_store_basics", eval_durable_event_store_basics),
        EvalCase("durable_event_task_lifecycle", eval_durable_event_task_lifecycle),
        EvalCase("durable_event_trace_linkage", eval_durable_event_trace_linkage),
        EvalCase("durable_event_failure_isolation", eval_durable_event_failure_isolation),
        EvalCase("tool_call_event_success", eval_tool_call_event_success),
        EvalCase("tool_call_event_error", eval_tool_call_event_error),
        EvalCase("tool_call_event_permission_blocked_or_cancelled", eval_tool_call_event_permission_blocked_or_cancelled),
        EvalCase("tool_call_event_failure_isolation", eval_tool_call_event_failure_isolation),
        EvalCase("model_call_event_success", eval_model_call_event_success),
        EvalCase("model_call_event_with_tool_calls", eval_model_call_event_with_tool_calls),
        EvalCase("model_call_event_error", eval_model_call_event_error),
        EvalCase("model_call_event_streaming", eval_model_call_event_streaming),
        EvalCase("model_call_event_failure_isolation", eval_model_call_event_failure_isolation),
        EvalCase("file_edit_event_success", eval_file_edit_event_success),
        EvalCase("file_edit_event_patch_metadata", eval_file_edit_event_patch_metadata),
        EvalCase("file_edit_event_blocked_or_cancelled", eval_file_edit_event_blocked_or_cancelled),
        EvalCase("file_edit_event_error", eval_file_edit_event_error),
        EvalCase("file_edit_event_failure_isolation", eval_file_edit_event_failure_isolation),
        EvalCase("shell_command_event_success", eval_shell_command_event_success),
        EvalCase("shell_command_event_blocked", eval_shell_command_event_blocked),
        EvalCase("shell_command_event_cancelled", eval_shell_command_event_cancelled),
        EvalCase("shell_command_event_error", eval_shell_command_event_error),
        EvalCase("shell_command_event_failure_isolation", eval_shell_command_event_failure_isolation),
        EvalCase("test_run_event_success", eval_test_run_event_success),
        EvalCase("test_run_event_failure", eval_test_run_event_failure),
        EvalCase("test_run_event_blocked", eval_test_run_event_blocked),
        EvalCase("test_run_event_timeout_or_error", eval_test_run_event_timeout_or_error),
        EvalCase("test_run_event_failure_isolation", eval_test_run_event_failure_isolation),
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
    assert "Nora 已启动" in outputs[0]
    assert "高风险工具会先确认" in outputs[0]
    assert any("Agent: reply: hello" in output for output in outputs)


def eval_cli_handles_help_command():
    agent = FakeCLIAgent()
    outputs = []
    cli = MiniAgentCLI(agent, FakeCLIRegistry(), input_func=_fake_input(["/help", "exit"]), output_func=outputs.append)
    cli.run()
    help_output = "\n".join(outputs)
    assert agent.inputs == []
    assert "Nora 命令帮助" in help_output
    assert "推荐开始:" in help_output
    assert "Git:" in help_output
    assert "/auto [n] <goal>" in help_output
    assert "/status" in help_output


def eval_cli_slash_status_uses_registry():
    registry = FakeCLIRegistry()
    result = MiniAgentCLI(FakeCLIAgent(), registry).handle_slash_command("/status")
    assert registry.calls[-1] == ("git_status", {})
    assert "called git_status" in result


def eval_cli_doctor_reports_runtime_status():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = MiniAgentCLI(FakeCLIAgent(), FakeCLIRegistry(), root=Path(tmpdir)).handle_slash_command("/doctor")
    assert "Nora doctor" in result
    assert "workspace:" in result
    assert "git:" in result
    assert "llm:" in result
    assert "tools: 1" in result
    assert "nora command:" in result
    assert "suggestions:" in result
    assert "LLM_API_KEY" in result


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


def eval_context_system_injects_auto_context():
    class FakeContextAwareLLM:
        def __init__(self):
            self.calls = []

        def chat(self, messages, tools=None):
            self.calls.append(messages)
            all_content = " ".join(m.get("content", "") for m in messages)
            if "Nora 自动上下文" in all_content and "context packs" in all_content:
                return LLMResponse(content="saw automatic context")
            return LLMResponse(content="missing context")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "README.md").write_text("Nora can inject context packs automatically", encoding="utf-8")
        context_system = ContextSystem(rag=ProjectRAG(root), context_window=ContextWindow(max_context_pack_chars=1000))
        llm = FakeContextAwareLLM()
        agent = MiniAgent(build_default_registry(workspace_root=root), llm=llm, context_system=context_system)

        result = agent.run("How do context packs work?")

    assert result == "saw automatic context", result
    assert len(llm.calls) == 1


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


def eval_context_compiler_includes_git_status_and_outline():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _init_git_repo(root)
        (root / "main.py").write_text("def hello():\n    return 'hi'\n\ndef world():\n    pass\n", encoding="utf-8")
        subprocess.run(["git", "add", "main.py"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "add main.py"], cwd=root, capture_output=True, check=True)
        (root / "new.txt").write_text("new content\n", encoding="utf-8")

        compiler = ContextCompiler(root)
        pack = compiler.compile(
            "eval test",
            include_git_status=True,
            include_changed_files=True,
            include_file_outlines=["main.py"],
        )
        md = pack.to_markdown()

        assert "eval test" in md, "task description missing"
        assert "Git Status" in md, "git status section missing"
        assert "Changed Files" in md, "changed files section missing"
        assert "Outline: main.py" in md, "outline section missing"
        assert "hello" in md, "function name missing from outline"
        assert "new.txt" in md, "changed file missing"


def eval_context_compiler_skips_sensitive_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _init_git_repo(root)
        (root / ".env").write_text("LLM_API_KEY=secret123\n", encoding="utf-8")
        (root / "data").mkdir()
        (root / "data" / "secret.json").write_text('{"key": "value"}\n', encoding="utf-8")
        (root / "logs").mkdir()
        (root / "logs" / "app.log").write_text("log entry\n", encoding="utf-8")
        (root / "public.md").write_text("public content\n", encoding="utf-8")

        compiler = ContextCompiler(root)
        pack = compiler.compile(
            "eval sensitive",
            include_knowledge_excerpts=[".env", "data/secret.json", "logs/app.log", "public.md"],
        )
        md = pack.to_markdown()

        assert "secret123" not in md, ".env content leaked"
        assert "public.md" in md, "public file should be included"
        assert ".env" not in md or "Knowledge: .env" not in md, ".env should be skipped"


def eval_context_compiler_tool_returns_markdown():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "README.md").write_text("# Eval Project\nTest project.\n", encoding="utf-8")
        registry = build_default_registry(workspace_root=root)
        result = registry.call(
            "compile_context_pack",
            task_description="eval tool test",
            include_git_status=False,
            include_changed_files=False,
            include_knowledge_excerpts=["README.md"],
        )
        assert isinstance(result, str), f"expected string, got {type(result)}"
        assert "# Context Pack: eval tool test" in result, "markdown header missing"
        assert "README.md" in result, "knowledge excerpt missing"


def eval_trace_store_records_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TraceStore(Path(tmpdir))
        trace = RunTrace(
            trace_id="trace_1",
            created_at="2026-05-28T12:00:00Z",
            status="done",
            input_preview="calculate 2+3",
            event_counts={"delta": 3, "done": 1},
            tool_calls=[
                ToolCallTrace(name="calculate", status="ok", result_preview="5"),
            ],
            failure="",
        )
        store.record(trace)

        traces = store.list_traces()
        assert len(traces) == 1, f"expected 1 trace, got {len(traces)}"
        t = traces[0]
        assert t["trace_id"] == "trace_1"
        assert t["status"] == "done"
        assert t["event_counts"]["delta"] == 3
        assert t["tool_calls"][0]["name"] == "calculate"
        assert t["tool_calls"][0]["result_preview"] == "5"
        assert t["failure"] == ""


def eval_trace_redacts_sensitive_input():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TraceStore(Path(tmpdir))
        trace = build_trace(
            trace_id="trace_1",
            user_input="OPENAI_API_KEY=sk-secret1234567890abcdef please help",
            status="done",
            events=[{"type": "delta"}],
            tool_records=[],
        )
        store.record(trace)

        traces = store.list_traces()
        assert "sk-secret" not in traces[0]["input_preview"], "API key leaked in trace"
        assert "[redacted]" in traces[0]["input_preview"], "should be redacted"


def eval_trace_redacts_sensitive_tool_preview():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TraceStore(Path(tmpdir))

        class FakeRecord:
            name = "read_file"
            status = "ok"
            result_preview = "ANTHROPIC_API_KEY=sk-ant-secret1234567890abcdef"

        trace = build_trace(
            trace_id="trace_1",
            user_input="read config",
            status="done",
            events=[{"type": "tool_result"}],
            tool_records=[FakeRecord()],
        )
        store.record(trace)

        traces = store.list_traces()
        preview = traces[0]["tool_calls"][0]["result_preview"]
        assert "sk-ant-secret" not in preview, "API key leaked in tool preview"
        assert "[redacted]" in preview, "should be redacted"


def eval_trace_lists_and_gets():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TraceStore(Path(tmpdir))
        for i in range(3):
            trace = RunTrace(
                trace_id=f"trace_{i+1}",
                created_at=f"2026-05-28T12:0{i}:00Z",
                status="done" if i < 2 else "error",
                input_preview=f"input {i+1}",
                event_counts={"delta": i},
                tool_calls=[],
                failure="" if i < 2 else "timeout",
            )
            store.record(trace)

        traces = store.list_traces(max_results=10)
        assert len(traces) == 3, f"expected 3, got {len(traces)}"
        assert traces[0]["trace_id"] == "trace_3", "should be most recent first"

        single = store.get_trace("trace_2")
        assert single is not None
        assert single["status"] == "done"
        assert single["input_preview"] == "input 2"

        missing = store.get_trace("trace_999")
        assert missing is None


def eval_trace_inspection_tools_via_registry():
    import json as _json

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmp_path, db=db)

            # Empty state: list_run_traces returns "[]"
            result = registry.call("list_run_traces")
            assert isinstance(result, str), f"expected str, got {type(result)}"
            parsed = _json.loads(result)
            assert parsed == [], f"expected empty list, got {parsed}"

            # Record a trace via registry.trace_store
            trace = RunTrace(
                trace_id="trace_1",
                created_at="2026-05-29T10:00:00Z",
                status="done",
                input_preview="calculate 2+3",
                event_counts={"delta": 2, "done": 1},
                tool_calls=[
                    ToolCallTrace(name="calculate", status="ok", result_preview="5"),
                ],
                failure="",
            )
            registry.trace_store.record(trace)

            # list_run_traces returns JSON array with trace data
            result = registry.call("list_run_traces")
            assert isinstance(result, str), f"expected str, got {type(result)}"
            parsed = _json.loads(result)
            assert len(parsed) == 1, f"expected 1 trace, got {len(parsed)}"
            assert parsed[0]["trace_id"] == "trace_1"
            assert parsed[0]["status"] == "done"
            assert "input_preview" in parsed[0]

            # get_run_trace returns full trace object
            result = registry.call("get_run_trace", trace_id="trace_1")
            assert isinstance(result, str), f"expected str, got {type(result)}"
            parsed = _json.loads(result)
            assert parsed["trace_id"] == "trace_1"
            assert parsed["status"] == "done"
            assert parsed["event_counts"]["delta"] == 2
            assert len(parsed["tool_calls"]) == 1
            assert parsed["tool_calls"][0]["name"] == "calculate"
            assert parsed["failure"] == ""

            # get_run_trace for non-existent trace returns error object
            result = registry.call("get_run_trace", trace_id="trace_999")
            assert isinstance(result, str), f"expected str, got {type(result)}"
            parsed = _json.loads(result)
            assert "error" in parsed, f"expected error key, got {parsed}"
        finally:
            db.close()


def eval_durable_task_schema_spec():
    """Check that the durable task schema spec exists and contains required fields, status enum, and lifecycle keywords."""
    schema_path = PROJECT_ROOT / "docs" / "knowledge" / "DURABLE_TASK_SCHEMA.md"
    assert schema_path.exists(), f"spec not found: {schema_path}"
    text = schema_path.read_text(encoding="utf-8")

    # Required fields
    required_fields = [
        "task_id",
        "run_id",
        "parent_task_id",
        "status",
        "current_step",
        "checkpoints",
        "input_summary",
        "context_pack_ref",
        "trace_refs",
        "worker_id",
        "created_at",
        "updated_at",
        "failure_reason",
        "resume_policy",
        "retry_count",
        "max_retries",
    ]
    for field in required_fields:
        assert field in text, f"required field '{field}' not found in spec"

    # Status enum values
    status_values = ["pending", "running", "paused", "blocked", "completed", "failed", "cancelled"]
    for status in status_values:
        assert status in text, f"status value '{status}' not found in spec"

    # Lifecycle keywords
    lifecycle_keywords = ["intake", "plan", "execute", "checkpoint", "pause", "resume", "review", "complete", "fail", "cancel"]
    for keyword in lifecycle_keywords:
        assert keyword in text.lower(), f"lifecycle keyword '{keyword}' not found in spec"


def eval_durable_task_taskmanager_mapping_spec():
    """Check that the durable task schema spec contains TaskManager compatibility mapping."""
    schema_path = PROJECT_ROOT / "docs" / "knowledge" / "DURABLE_TASK_SCHEMA.md"
    assert schema_path.exists(), f"spec not found: {schema_path}"
    text = schema_path.read_text(encoding="utf-8")

    required_keywords = [
        "TaskManager Compatibility Mapping",
        "current_task.json",
        "task_history.jsonl",
        "active -> running",
        "finished -> completed",
        "goal -> goal",
        "steps -> steps",
        "tool_hint -> tool_hint",
        "summary -> summary",
        "无法保真",
    ]
    for keyword in required_keywords:
        assert keyword in text, f"keyword '{keyword}' not found in spec"

    # Case-insensitive check for "lossy" (spec uses "Lossy Migrations")
    assert "lossy" in text.lower(), "keyword 'lossy' not found in spec"


def eval_list_durable_tasks_returns_correct_fields():
    """list_durable_tasks registry tool returns correct task count and fields."""
    import json as _json

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmp_path, db=db)

            # Empty state returns empty JSON array
            result = registry.call("list_durable_tasks")
            parsed = _json.loads(result)
            assert parsed == [], f"expected empty list, got {parsed}"

            # Create 3 tasks
            store = registry.durable_task_store
            store.create_task(
                goal="task one",
                steps=[{"text": "step A"}, {"text": "step B"}],
            )
            store.create_task(
                goal="task two",
                steps=[{"text": "step X"}],
                input_summary="input summary two",
            )
            store.create_task(
                goal="task three",
                steps=[{"text": "step Y"}, {"text": "step Z"}],
            )

            # list returns all 3 with correct fields
            result = registry.call("list_durable_tasks")
            parsed = _json.loads(result)
            assert len(parsed) == 3, f"expected 3 tasks, got {len(parsed)}"

            required_fields = {"task_id", "status", "goal", "current_step", "checkpoint_count"}
            for item in parsed:
                assert required_fields.issubset(item.keys()), f"missing fields in {item}"
                assert item["status"] == "pending", f"expected pending, got {item['status']}"
                assert item["current_step"] is None, f"expected None, got {item['current_step']}"
                assert item["checkpoint_count"] == 0, f"expected 0, got {item['checkpoint_count']}"

            # Verify specific goals
            goals = {item["goal"] for item in parsed}
            assert goals == {"task one", "task two", "task three"}, f"unexpected goals: {goals}"

            # Limit works
            result = registry.call("list_durable_tasks", limit=1)
            parsed = _json.loads(result)
            assert len(parsed) == 1, f"expected 1 task with limit=1, got {len(parsed)}"

            # Non-existent task returns error
            result = registry.call("get_durable_task", task_id="dtask_999")
            parsed = _json.loads(result)
            assert "error" in parsed, f"expected error key, got {parsed}"
        finally:
            db.close()


def eval_get_durable_task_returns_complete_data():
    """get_durable_task registry tool returns complete task data including steps, checkpoints, and failure."""
    import json as _json

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmp_path, db=db)
            store = registry.durable_task_store

            task = store.create_task(
                goal="full data task",
                steps=[{"text": "prepare"}, {"text": "execute"}, {"text": "verify"}],
                run_id="run_42",
                input_summary="do something important",
                worker_id="worker_1",
            )

            # Add a checkpoint
            store.add_checkpoint(task.task_id, {
                "step_id": 1,
                "run_id": "run_42",
                "state_snapshot": {"progress": "half done"},
                "description": "mid-task snapshot",
            })

            # Advance to running
            store.update_status(task.task_id, "running")

            result = registry.call("get_durable_task", task_id=task.task_id)
            parsed = _json.loads(result)

            assert parsed["task_id"] == task.task_id
            assert parsed["run_id"] == "run_42"
            assert parsed["status"] == "running"
            assert parsed["goal"] == "full data task"
            assert parsed["input_summary"] == "do something important"
            assert parsed["worker_id"] == "worker_1"
            assert len(parsed["steps"]) == 3
            assert parsed["steps"][0]["text"] == "prepare"
            assert parsed["steps"][0]["status"] == "pending"
            assert len(parsed["checkpoints"]) == 1
            assert parsed["checkpoints"][0]["description"] == "mid-task snapshot"
            assert parsed["checkpoints"][0]["state_snapshot"]["progress"] == "half done"
            assert parsed["failure_reason"] == ""
        finally:
            db.close()


def eval_durable_task_status_transitions():
    """Task status transitions are validated: valid transitions succeed, invalid ones raise."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            store = DurableTaskStore(db=db)

            # Happy path: pending -> running -> completed
            t1 = store.create_task(goal="happy path", steps=[{"text": "do it"}])
            assert t1.status == "pending"
            t1 = store.update_status(t1.task_id, "running")
            assert t1.status == "running"
            assert t1.finished_at is None
            t1 = store.update_status(t1.task_id, "completed")
            assert t1.status == "completed"
            assert t1.finished_at is not None

            # Pending -> cancelled
            t2 = store.create_task(goal="cancel path", steps=[{"text": "do it"}])
            t2 = store.update_status(t2.task_id, "cancelled")
            assert t2.status == "cancelled"
            assert t2.finished_at is not None

            # Running -> paused -> running -> failed
            t3 = store.create_task(goal="pause resume fail", steps=[{"text": "do it"}])
            store.update_status(t3.task_id, "running")
            t3 = store.update_status(t3.task_id, "paused")
            assert t3.status == "paused"
            t3 = store.update_status(t3.task_id, "running")
            assert t3.status == "running"
            t3 = store.update_status(t3.task_id, "failed", failure_reason="timeout")
            assert t3.status == "failed"
            assert t3.failure_reason == "timeout"

            # Running -> blocked -> running
            t4 = store.create_task(goal="blocked path", steps=[{"text": "do it"}])
            store.update_status(t4.task_id, "running")
            t4 = store.update_status(t4.task_id, "blocked")
            assert t4.status == "blocked"
            t4 = store.update_status(t4.task_id, "running")
            assert t4.status == "running"

            # Invalid transitions raise ValueError
            t5 = store.create_task(goal="invalid transitions", steps=[{"text": "do it"}])
            try:
                store.update_status(t5.task_id, "completed")
                assert False, "should have raised for pending->completed"
            except ValueError as e:
                assert "Invalid transition" in str(e)

            # Terminal states cannot transition
            t6 = store.create_task(goal="terminal", steps=[{"text": "do it"}])
            store.update_status(t6.task_id, "running")
            store.update_status(t6.task_id, "completed")
            try:
                store.update_status(t6.task_id, "running")
                assert False, "should have raised for completed->running"
            except ValueError as e:
                assert "Invalid transition" in str(e)
        finally:
            db.close()


def eval_cli_durable_tasks_output_format():
    """CLI /durable-tasks output is readable and contains task summary lines."""
    import json as _json

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmp_path, db=db)
            store = registry.durable_task_store

            # Empty state
            cli = MiniAgentCLI(FakeCLIAgent(), registry, root=tmp_path)
            result = cli.handle_slash_command("/durable-tasks")
            assert "暂无 durable tasks" in result, f"expected empty message, got: {result}"

            # Create tasks
            t1 = store.create_task(
                goal="implement feature X",
                steps=[{"text": "design"}, {"text": "code"}, {"text": "test"}],
            )
            store.create_task(
                goal="fix bug Y in the authentication module",
                steps=[{"text": "reproduce"}, {"text": "fix"}],
            )

            result = cli.handle_slash_command("/durable-tasks")
            assert "最近 2 条 durable tasks" in result, f"expected count header, got: {result}"
            assert "dtask_" in result, f"expected task_id, got: {result}"
            assert "pending" in result, f"expected status, got: {result}"
            assert "implement feature X" in result, f"expected goal, got: {result}"
            assert "checkpoints=0" in result, f"expected checkpoint count, got: {result}"
            assert "step=-" in result, f"expected step placeholder for pending task, got: {result}"

            # After advancing a task, output reflects the change
            store.update_status(t1.task_id, "running")
            result = cli.handle_slash_command("/durable-tasks")
            assert "running" in result, f"expected running status, got: {result}"
        finally:
            db.close()


def eval_cli_durable_task_detail_output():
    """CLI /durable-task <task_id> returns full JSON detail."""
    import json as _json

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmp_path, db=db)
            store = registry.durable_task_store

            task = store.create_task(
                goal="detail test task",
                steps=[{"text": "step one"}, {"text": "step two"}],
                run_id="run_detail",
                input_summary="test detail output",
            )
            store.add_checkpoint(task.task_id, {
                "step_id": 1,
                "run_id": "run_detail",
                "state_snapshot": {},
                "description": "test checkpoint",
            })

            cli = MiniAgentCLI(FakeCLIAgent(), registry, root=tmp_path)

            # Valid task returns JSON
            result = cli.handle_slash_command(f"/durable-task {task.task_id}")
            parsed = _json.loads(result)
            assert parsed["task_id"] == task.task_id
            assert parsed["goal"] == "detail test task"
            assert parsed["run_id"] == "run_detail"
            assert len(parsed["steps"]) == 2
            assert len(parsed["checkpoints"]) == 1
            assert parsed["checkpoints"][0]["description"] == "test checkpoint"

            # Non-existent task returns error message
            result = cli.handle_slash_command("/durable-task dtask_999")
            assert "未找到" in result, f"expected not-found message, got: {result}"
        finally:
            db.close()


def eval_cli_dashboard_shows_status_distribution():
    """CLI /dashboard shows status counts and total."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmp_path, db=db)
            store = registry.durable_task_store

            # Empty state
            cli = MiniAgentCLI(FakeCLIAgent(), registry, root=tmp_path)
            result = cli.handle_slash_command("/dashboard")
            assert "暂无 durable tasks" in result

            # Create tasks in various statuses
            t1 = store.create_task(goal="pending task", steps=[{"text": "a"}])
            t2 = store.create_task(goal="running task", steps=[{"text": "b"}, {"text": "c"}])
            store.update_status(t2.task_id, "running")
            t3 = store.create_task(goal="done task", steps=[{"text": "d"}])
            store.update_status(t3.task_id, "running")
            store.update_status(t3.task_id, "completed")
            t4 = store.create_task(goal="failed task", steps=[{"text": "e"}])
            store.update_status(t4.task_id, "running")
            store.update_status(t4.task_id, "failed", failure_reason="crash")

            result = cli.handle_slash_command("/dashboard")
            assert "Durable Task Dashboard" in result, f"missing header: {result}"
            assert "pending: 1" in result, f"missing pending count: {result}"
            assert "running: 1" in result, f"missing running count: {result}"
            assert "completed: 1" in result, f"missing completed count: {result}"
            assert "failed: 1" in result, f"missing failed count: {result}"
            assert "总计: 4" in result, f"missing total: {result}"
        finally:
            db.close()


def eval_cli_dashboard_shows_running_and_completed():
    """CLI /dashboard lists running tasks with step info and recent completions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmp_path, db=db)
            store = registry.durable_task_store

            # Create running task
            t_running = store.create_task(
                goal="build dashboard feature",
                steps=[{"text": "design"}, {"text": "implement"}, {"text": "test"}],
            )
            store.update_status(t_running.task_id, "running")

            # Create completed task
            t_done = store.create_task(
                goal="fix authentication bug",
                steps=[{"text": "reproduce"}, {"text": "fix"}],
            )
            store.update_status(t_done.task_id, "running")
            store.update_status(t_done.task_id, "completed")

            # Create failed task
            t_fail = store.create_task(
                goal="deploy to production",
                steps=[{"text": "build"}, {"text": "deploy"}],
            )
            store.update_status(t_fail.task_id, "running")
            store.update_status(t_fail.task_id, "failed", failure_reason="timeout error")

            cli = MiniAgentCLI(FakeCLIAgent(), registry, root=tmp_path)
            result = cli.handle_slash_command("/dashboard")

            # Running section
            assert "进行中的任务" in result, f"missing running section: {result}"
            assert "build dashboard feature" in result, f"missing running goal: {result}"

            # Completed section
            assert "最近完成的任务" in result, f"missing completed section: {result}"
            assert "fix authentication bug" in result, f"missing completed goal: {result}"

            # Failed section
            assert "失败的任务" in result, f"missing failed section: {result}"
            assert "deploy to production" in result, f"missing failed goal: {result}"
            assert "timeout error" in result, f"missing failure reason: {result}"
        finally:
            db.close()


def eval_crud_create_durable_task():
    """create_durable_task registry tool returns correct fields."""
    import json as _json

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(
                workspace_root=tmp_path, db=db,
                confirm_action=lambda prompt: True,
            )
            result = registry.call(
                "create_durable_task",
                goal="eval CRUD create",
                steps="step one\nstep two\nstep three",
            )
            parsed = _json.loads(result)
            assert "task_id" in parsed, f"missing task_id: {parsed}"
            assert parsed["task_id"].startswith("dtask_"), f"bad id format: {parsed['task_id']}"
            assert parsed["goal"] == "eval CRUD create"
            assert parsed["status"] == "pending"
            assert len(parsed["steps"]) == 3
            assert parsed["steps"][0]["text"] == "step one"
            assert parsed["steps"][0]["status"] == "pending"
            assert parsed["steps"][2]["text"] == "step three"
            assert parsed["created_at"], f"missing created_at"
            assert parsed["updated_at"], f"missing updated_at"
            assert parsed["failure_reason"] == ""
        finally:
            db.close()


def eval_crud_get_durable_task():
    """get_durable_task registry tool returns complete data for created task."""
    import json as _json

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(
                workspace_root=tmp_path, db=db,
                confirm_action=lambda prompt: True,
            )
            create_result = registry.call(
                "create_durable_task",
                goal="eval CRUD get",
                steps="step A\nstep B",
            )
            created = _json.loads(create_result)
            task_id = created["task_id"]

            result = registry.call("get_durable_task", task_id=task_id)
            parsed = _json.loads(result)
            assert parsed["task_id"] == task_id
            assert parsed["goal"] == "eval CRUD get"
            assert parsed["status"] == "pending"
            assert len(parsed["steps"]) == 2
            assert parsed["steps"][0]["text"] == "step A"
            assert parsed["steps"][1]["text"] == "step B"

            # Non-existent task
            result = registry.call("get_durable_task", task_id="dtask_999")
            parsed = _json.loads(result)
            assert "error" in parsed, f"expected error: {parsed}"
        finally:
            db.close()


def eval_crud_update_durable_task():
    """update_durable_task registry tool updates status correctly."""
    import json as _json

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(
                workspace_root=tmp_path, db=db,
                confirm_action=lambda prompt: True,
            )
            create_result = registry.call(
                "create_durable_task",
                goal="eval CRUD update",
                steps="step X",
            )
            created = _json.loads(create_result)
            task_id = created["task_id"]

            # pending -> running
            result = registry.call("update_durable_task", task_id=task_id, status="running")
            parsed = _json.loads(result)
            assert parsed["status"] == "running"
            assert parsed["task_id"] == task_id

            # running -> failed with reason
            result = registry.call(
                "update_durable_task",
                task_id=task_id,
                status="failed",
                failure_reason="timeout",
            )
            parsed = _json.loads(result)
            assert parsed["status"] == "failed"
            assert parsed["failure_reason"] == "timeout"
            assert parsed["finished_at"] is not None

            # Invalid transition returns error
            result = registry.call("update_durable_task", task_id=task_id, status="running")
            parsed = _json.loads(result)
            assert "error" in parsed, f"expected error for invalid transition: {parsed}"

            # Missing status returns error
            result = registry.call("update_durable_task", task_id=task_id, status="")
            parsed = _json.loads(result)
            assert "error" in parsed, f"expected error for missing status: {parsed}"
        finally:
            db.close()


def eval_crud_delete_durable_task():
    """delete_durable_task registry tool removes task and confirms deletion."""
    import json as _json

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(
                workspace_root=tmp_path, db=db,
                confirm_action=lambda prompt: True,
            )
            create_result = registry.call(
                "create_durable_task",
                goal="eval CRUD delete",
                steps="step D",
            )
            created = _json.loads(create_result)
            task_id = created["task_id"]

            # Delete succeeds
            result = registry.call("delete_durable_task", task_id=task_id)
            parsed = _json.loads(result)
            assert parsed["deleted"] is True
            assert parsed["task_id"] == task_id

            # Verify task is gone
            result = registry.call("get_durable_task", task_id=task_id)
            parsed = _json.loads(result)
            assert "error" in parsed, f"expected error after delete: {parsed}"

            # Delete non-existent returns error
            result = registry.call("delete_durable_task", task_id="dtask_999")
            parsed = _json.loads(result)
            assert "error" in parsed, f"expected error for missing task: {parsed}"
        finally:
            db.close()


def eval_crud_full_lifecycle():
    """Full CRUD lifecycle: create -> get -> update -> delete."""
    import json as _json

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            registry = build_default_registry(
                workspace_root=tmp_path, db=db,
                confirm_action=lambda prompt: True,
            )

            # Create
            result = registry.call(
                "create_durable_task",
                goal="lifecycle test",
                steps="prepare\nexecute\nverify",
            )
            created = _json.loads(result)
            task_id = created["task_id"]
            assert created["status"] == "pending"
            assert len(created["steps"]) == 3

            # Get
            result = registry.call("get_durable_task", task_id=task_id)
            fetched = _json.loads(result)
            assert fetched["task_id"] == task_id
            assert fetched["goal"] == "lifecycle test"

            # Update pending -> running
            result = registry.call("update_durable_task", task_id=task_id, status="running")
            updated = _json.loads(result)
            assert updated["status"] == "running"

            # Update running -> completed
            result = registry.call("update_durable_task", task_id=task_id, status="completed")
            updated = _json.loads(result)
            assert updated["status"] == "completed"
            assert updated["finished_at"] is not None

            # Verify final state via get
            result = registry.call("get_durable_task", task_id=task_id)
            final = _json.loads(result)
            assert final["status"] == "completed"

            # Delete
            result = registry.call("delete_durable_task", task_id=task_id)
            deleted = _json.loads(result)
            assert deleted["deleted"] is True

            # Confirm gone
            result = registry.call("get_durable_task", task_id=task_id)
            assert "error" in _json.loads(result)

            # Also verify list no longer contains it
            result = registry.call("list_durable_tasks")
            listing = _json.loads(result)
            assert all(item["task_id"] != task_id for item in listing), "deleted task still in list"
        finally:
            db.close()


def eval_task_manager_durable_shadow_consistency():
    """Verify that TaskManager shadow-writes to DurableTaskStore with consistent semantics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = NoraDB(tmp_path / "test.db")
        try:
            durable_store = DurableTaskStore(db=db)
            manager = TaskManager(
                tmp_path / "task.json",
                durable_store=durable_store,
                enable_durable_shadow=True,
            )

            # Create task
            manager.start("构建功能", "写代码\n写测试\n提交")

            # Update step 1 to done with summary
            manager.update_step(1, "done", note="代码完成", summary="实现了核心功能")

            # Update step 2 to done
            manager.update_step(2, "done", summary="测试通过")

            # Finish task
            manager.finish("功能完成，所有测试通过")

            # Verify DurableTaskStore has the shadow task
            tasks = durable_store.list_tasks()
            assert len(tasks) >= 1, f"expected >=1 durable task, got {len(tasks)}"

            # Find the shadow task (most recent)
            dt = tasks[0]
            assert dt.goal == "构建功能", f"goal mismatch: {dt.goal}"
            assert dt.status == TaskStatus.COMPLETED, f"status mismatch: {dt.status}"
            assert len(dt.steps) == 3, f"step count mismatch: {len(dt.steps)}"
            assert dt.finished_at is not None, "finished_at should be set"

            # Step text consistency
            assert dt.steps[0].text == "写代码", f"step 0 text: {dt.steps[0].text}"
            assert dt.steps[1].text == "写测试", f"step 1 text: {dt.steps[1].text}"
            assert dt.steps[2].text == "提交", f"step 2 text: {dt.steps[2].text}"

            # Step status consistency
            assert dt.steps[0].status == "done", f"step 0 status: {dt.steps[0].status}"
            assert dt.steps[1].status == "done", f"step 1 status: {dt.steps[1].status}"
            # Step 2 may be pending or done depending on shadow implementation

            # Step summary consistency
            assert dt.steps[0].summary == "实现了核心功能", f"step 0 summary: {dt.steps[0].summary}"
            assert dt.steps[1].summary == "测试通过", f"step 1 summary: {dt.steps[1].summary}"
        finally:
            db.close()


def eval_task_manager_durable_shadow_failure_isolation():
    """Verify that DurableTaskStore failures don't break TaskManager."""
    class FailingDurableStore:
        """A fake store that always raises on write operations."""
        def create_task(self, **kwargs):
            raise RuntimeError("store unavailable")

        def get_task(self, task_id):
            raise RuntimeError("store unavailable")

        def list_tasks(self, limit=50):
            raise RuntimeError("store unavailable")

        def update_status(self, task_id, status, failure_reason=""):
            raise RuntimeError("store unavailable")

        def add_checkpoint(self, task_id, checkpoint):
            raise RuntimeError("store unavailable")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        failing_store = FailingDurableStore()
        manager = TaskManager(
            tmp_path / "task.json",
            durable_store=failing_store,
            enable_durable_shadow=True,
        )

        # TaskManager should still work despite durable store failures
        result = manager.start("测试隔离", "步骤一\n步骤二")
        assert "已创建任务" in result, f"start failed: {result}"

        result = manager.update_step(1, "done", summary="完成")
        assert "已更新步骤" in result, f"update_step failed: {result}"

        result = manager.finish("隔离测试完成")
        assert "已完成任务" in result, f"finish failed: {result}"

        # Old task data should be intact
        task = manager.get_current_task()
        assert task["goal"] == "测试隔离", f"goal mismatch: {task['goal']}"
        assert task["status"] == "finished", f"status mismatch: {task['status']}"


def eval_retry_state_machine_consistency():
    """Verify retry state machine: FAILED->PENDING only via retry_durable_task(), not update_status()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = NoraDB(Path(tmpdir) / "test.db")
        try:
            store = DurableTaskStore(db=db)

            # Create and fail a task
            store.create_task(goal="retry test", steps=[{"text": "s1"}, {"text": "s2"}], max_retries=2)
            store.update_status("dtask_1", TaskStatus.RUNNING)
            store.update_status("dtask_1", TaskStatus.FAILED, failure_reason="timeout")

            # 1. update_status() must reject FAILED -> PENDING
            try:
                store.update_status("dtask_1", TaskStatus.PENDING)
                assert False, "update_status should reject FAILED -> PENDING"
            except ValueError as e:
                assert "Invalid transition" in str(e), f"wrong error: {e}"

            # 2. retry_durable_task() must succeed and increment retry_count
            task = store.retry_durable_task("dtask_1")
            assert task.status == TaskStatus.PENDING, f"status after retry: {task.status}"
            assert task.retry_count == 1, f"retry_count: {task.retry_count}"
            assert task.failure_reason == "", f"failure_reason not cleared: {task.failure_reason}"

            # 3. Second retry cycle
            store.update_status("dtask_1", TaskStatus.RUNNING)
            store.update_status("dtask_1", TaskStatus.FAILED, failure_reason="err2")
            task = store.retry_durable_task("dtask_1")
            assert task.retry_count == 2, f"retry_count after 2nd retry: {task.retry_count}"

            # 4. Third retry must fail (max_retries=2)
            store.update_status("dtask_1", TaskStatus.RUNNING)
            store.update_status("dtask_1", TaskStatus.FAILED, failure_reason="err3")
            try:
                store.retry_durable_task("dtask_1")
                assert False, "retry should fail after max_retries"
            except ValueError as e:
                assert "Max retries" in str(e), f"wrong error: {e}"

            # 5. FAILED -> CANCELLED is still allowed via update_status()
            task = store.update_status("dtask_1", TaskStatus.CANCELLED)
            assert task.status == TaskStatus.CANCELLED, f"cancelled status: {task.status}"
        finally:
            db.close()


def eval_trace_links_to_durable_task():
    """Verify that agent.run links trace_id to active durable task's trace_refs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            from mini_agent.traces import TraceStore as TStore
            trace_store = TStore(db=db)
            durable_store = DurableTaskStore(db=db)

            # Create a running durable task
            durable_store.create_task("eval goal", [{"text": "s1"}, {"text": "s2"}])
            durable_store.update_status("dtask_1", TaskStatus.RUNNING)

            # Build agent with trace + durable store
            registry = build_default_registry(
                workspace_root=tmpdir,
                notes_path=tmpdir / "notes.txt",
                db=db,
            )
            agent = MiniAgent(registry, trace_store=trace_store)
            agent.durable_task_store = durable_store

            # Run agent
            list(agent.run_events("计算 2 + 3"))

            # Verify trace was recorded
            traces = trace_store.list_traces()
            assert len(traces) == 1, f"expected 1 trace, got {len(traces)}"
            trace_id = traces[0]["trace_id"]

            # Verify trace_id linked to durable task
            task = durable_store.get_task("dtask_1")
            assert trace_id in task.trace_refs, f"{trace_id} not in {task.trace_refs}"

            # Verify no duplicate on second run
            list(agent.run_events("计算 4 + 5"))
            task = durable_store.get_task("dtask_1")
            assert len(task.trace_refs) == 2, f"expected 2 trace refs, got {len(task.trace_refs)}"
            assert len(set(task.trace_refs)) == 2, f"duplicate trace refs: {task.trace_refs}"
        finally:
            db.close()


def eval_durable_event_store_basics():
    """DurableEventStore can record, list, get, and filter events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            store = DurableEventStore(db=db)
            event1 = store.record(
                "task_created",
                task_id="dtask_1",
                summary="created",
                payload={"goal": "eval"},
            )
            event2 = store.record(
                "step_updated",
                task_id="dtask_2",
                checkpoint_id="cp_1",
                summary="updated",
            )

            assert event1.event_id == "devt_1", event1.event_id
            assert event2.event_id == "devt_2", event2.event_id
            all_events = store.list_events()
            assert [e.event_id for e in all_events] == ["devt_2", "devt_1"], all_events
            filtered = store.list_events(task_id="dtask_1")
            assert len(filtered) == 1 and filtered[0].event_id == "devt_1", filtered
            detail = store.get_event("devt_1")
            assert detail.payload["goal"] == "eval", detail
        finally:
            db.close()


def eval_durable_event_task_lifecycle():
    """TaskManager lifecycle writes task, step, checkpoint, and finish events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmpdir, db=db, confirm_action=lambda _prompt: True)
            manager = registry.task_manager
            event_store = registry.durable_event_store

            manager.start("event eval", "step one")
            manager.run_once()
            manager.update_step(1, "done", summary="finished")
            manager.finish("done")

            events = event_store.list_events()
            event_types = [event.event_type for event in events]
            assert "task_created" in event_types, event_types
            assert "step_updated" in event_types, event_types
            assert "checkpoint_added" in event_types, event_types
            assert "task_finished" in event_types, event_types
            checkpoint_events = [e for e in events if e.event_type == "checkpoint_added"]
            assert checkpoint_events[0].checkpoint_id, checkpoint_events[0]
            task_events = event_store.list_events(task_id="dtask_shadow_1")
            assert len(task_events) == len(events), (len(task_events), len(events))
        finally:
            db.close()


def eval_durable_event_trace_linkage():
    """Agent trace linkage writes both trace_refs and trace_linked event."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmpdir, db=db, confirm_action=lambda _prompt: True)
            registry.task_manager.start("event trace eval", "step one")
            agent = MiniAgent(
                registry,
                trace_store=TraceStore(db=db),
                event_store=registry.durable_event_store,
            )
            agent.durable_task_store = registry.durable_task_store

            list(agent.run_events("计算 2 + 3"))

            task = registry.durable_task_store.get_task("dtask_shadow_1")
            assert len(task.trace_refs) == 1, task.trace_refs
            trace_id = task.trace_refs[0]
            events = registry.durable_event_store.list_events()
            linked = [e for e in events if e.event_type == "trace_linked"]
            assert len(linked) == 1, events
            assert linked[0].task_id == "dtask_shadow_1", linked[0]
            assert linked[0].trace_id == trace_id, linked[0]
        finally:
            db.close()


def eval_durable_event_failure_isolation():
    """Broken event stores must not break task flow or trace recording."""
    class BrokenEventStore:
        def record(self, **_kwargs):
            raise RuntimeError("event store unavailable")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            durable_store = DurableTaskStore(db=db)
            manager = TaskManager(
                path=tmpdir / "task.json",
                history_path=tmpdir / "history.jsonl",
                db=db,
                durable_store=durable_store,
                enable_durable_shadow=True,
                event_store=BrokenEventStore(),
            )
            assert "已创建任务" in manager.start("event failure eval", "step one")
            assert "下一步" in manager.run_once()
            assert "已更新步骤" in manager.update_step(1, "done", summary="ok")

            registry = build_default_registry(workspace_root=tmpdir, db=db, confirm_action=lambda _prompt: True)
            trace_store = TraceStore(db=db)
            agent = MiniAgent(registry, trace_store=trace_store, event_store=BrokenEventStore())
            registry.durable_task_store.create_task("trace eval", [{"text": "s"}])
            agent.durable_task_store = registry.durable_task_store
            list(agent.run_events("hello"))
            assert len(trace_store.list_traces()) == 1, "trace recording should survive event failure"
        finally:
            db.close()


def eval_tool_call_event_success():
    """Successful tool call writes TOOL_CALL_STARTED and TOOL_CALL_FINISHED with correct payload fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmpdir, db=db, confirm_action=lambda _prompt: True)
            event_store = registry.durable_event_store
            agent = MiniAgent(registry, event_store=event_store)

            agent.run("计算 2 + 3")

            events = event_store.list_events()
            started = [e for e in events if e.event_type == TOOL_CALL_STARTED]
            finished = [e for e in events if e.event_type == TOOL_CALL_FINISHED]

            assert len(started) >= 1, f"expected >=1 started event, got {len(started)}"
            assert len(finished) >= 1, f"expected >=1 finished event, got {len(finished)}"

            s = started[0]
            assert s.payload["tool_name"] == "calculate", f"tool_name: {s.payload['tool_name']}"
            assert s.payload["status"] == "started"
            assert s.severity == "info"

            f = finished[0]
            assert f.payload["tool_name"] == "calculate"
            assert f.payload["status"] == "ok"
            assert "result_preview" in f.payload
            assert f.severity == "info"

            # result_preview must contain the actual result
            assert "5" in f.payload["result_preview"], f"result_preview: {f.payload['result_preview']}"

            # started and finished must share the same tool_name
            assert s.payload["tool_name"] == f.payload["tool_name"]
        finally:
            db.close()


def eval_tool_call_event_error():
    """Tool that raises records TOOL_CALL_ERROR with error status and no crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            event_store = DurableEventStore(db=db)

            class FailingRegistry:
                def call(self, name, **kwargs):
                    raise RuntimeError("simulated failure for eval")
                def permission_for(self, name):
                    return None
                def to_openai_tools(self):
                    return []
                def describe(self):
                    return ""

            agent = MiniAgent(FailingRegistry(), event_store=event_store)
            agent._active_tool_records = []
            result = agent._call_tool("broken_tool", {"arg": "val"})

            # Agent must not crash — returns an error message instead
            assert "工具调用失败" in result, f"expected error message, got: {result}"
            assert "simulated failure" in result

            events = event_store.list_events()
            started = [e for e in events if e.event_type == TOOL_CALL_STARTED]
            errors = [e for e in events if e.event_type == TOOL_CALL_ERROR]
            finished = [e for e in events if e.event_type == TOOL_CALL_FINISHED]

            assert len(started) == 1, f"expected 1 started, got {len(started)}"
            assert len(errors) == 1, f"expected 1 error, got {len(errors)}"
            assert len(finished) == 0, f"error path must not emit finished event, got {len(finished)}"

            err = errors[0]
            assert err.payload["tool_name"] == "broken_tool"
            assert err.payload["status"] == "error"
            assert err.severity == "warning"
            assert "simulated failure" in err.payload["result_preview"]
        finally:
            db.close()


def eval_tool_call_event_permission_blocked_or_cancelled():
    """Permission-blocked and user-cancelled tool calls emit TOOL_CALL_BLOCKED with correct status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            # --- blocked: permission requires reason but none given ---
            registry = build_default_registry(
                db=db, workspace_root=tmpdir,
                permission_overrides={"calculate": True},
            )
            event_store = registry.durable_event_store
            agent = MiniAgent(registry, event_store=event_store)
            agent._active_tool_records = []
            result = agent._call_tool("calculate", {"expression": "2 + 3"})

            assert "拒绝调用" in result, f"expected blocked message, got: {result}"
            events = event_store.list_events()
            blocked = [e for e in events if e.event_type == TOOL_CALL_BLOCKED]
            assert len(blocked) == 1, f"expected 1 blocked event, got {len(blocked)}"
            assert blocked[0].payload["tool_name"] == "calculate"
            assert blocked[0].payload["status"] == "blocked"
            assert blocked[0].severity == "warning"

            # --- cancelled: user denies confirmation ---
            registry2 = build_default_registry(
                db=db, workspace_root=tmpdir,
                confirm_action=lambda _prompt: False,
            )
            event_store2 = registry2.durable_event_store
            agent2 = MiniAgent(registry2, event_store=event_store2)
            agent2._active_tool_records = []
            result2 = agent2._call_tool("git_commit_staged", {"message": "test", "reason": "eval"})

            assert "已取消操作" in result2, f"expected cancel message, got: {result2}"
            events2 = event_store2.list_events()
            cancelled = [e for e in events2
                         if e.event_type == TOOL_CALL_BLOCKED and e.payload.get("status") == "cancelled"]
            finished2 = [e for e in events2 if e.event_type == TOOL_CALL_FINISHED]
            assert len(cancelled) == 1, f"expected 1 cancelled event, got {len(cancelled)}"
            assert len(finished2) == 0, "cancelled tool must not emit finished event"
            assert cancelled[0].severity == "warning"
        finally:
            db.close()


def eval_tool_call_event_failure_isolation():
    """Broken event store must not break tool execution or return value."""
    class BrokenEventStore:
        def record(self, **kwargs):
            raise RuntimeError("event store offline")
        def list_events(self, **kwargs):
            return []
        def get_event(self, event_id):
            return None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        registry = build_default_registry(workspace_root=tmpdir)
        agent = MiniAgent(registry, event_store=BrokenEventStore())

        # Tool execution must still succeed despite broken event store
        result = agent.run("计算 2 + 3")
        assert "5" in result, f"expected result containing 5, got: {result}"

        # run_events must also survive
        events_list = list(agent.run_events("计算 4 + 5"))
        # The stream should complete without raising
        assert len(events_list) > 0, "run_events should produce at least one event"


def _assert_model_events_do_not_store_raw_context(events, forbidden_values: list[str]) -> None:
    forbidden_payload_keys = {"messages", "tools", "tool_schema", "tool_schemas", "functions", "parameters"}
    for event in events:
        if event.event_type not in (MODEL_CALL_STARTED, MODEL_CALL_FINISHED, MODEL_CALL_ERROR):
            continue
        serialized = json.dumps(event.to_dict(), ensure_ascii=False)
        for value in forbidden_values:
            assert value not in serialized, f"model event stored forbidden raw context {value!r}: {serialized}"
        payload_keys = set(event.payload)
        leaked_keys = forbidden_payload_keys & payload_keys
        assert not leaked_keys, f"model event stored raw context keys {sorted(leaked_keys)}: {event.payload}"


def eval_model_call_event_success():
    """Successful model call writes MODEL_CALL_STARTED and MODEL_CALL_FINISHED with safe metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            sentinel_prompt = "RAW_PROMPT_SHOULD_NOT_BE_STORED_73F1"

            class FakeLLM:
                provider = "eval-provider"
                model = "eval-model"
                def chat(self, messages, tools=None):
                    assert sentinel_prompt in messages[-1]["content"], "sentinel prompt must reach the model"
                    return LLMResponse(content="eval answer 42")

            registry = build_default_registry(workspace_root=tmpdir, db=db, confirm_action=lambda _prompt: True)
            event_store = registry.durable_event_store
            agent = MiniAgent(registry, llm=FakeLLM(), event_store=event_store)

            result = agent.run(sentinel_prompt)

            assert "eval answer 42" in result, f"expected answer in result, got: {result}"

            events = event_store.list_events()
            started = [e for e in events if e.event_type == MODEL_CALL_STARTED]
            finished = [e for e in events if e.event_type == MODEL_CALL_FINISHED]

            assert len(started) >= 1, f"expected >=1 started event, got {len(started)}"
            assert len(finished) >= 1, f"expected >=1 finished event, got {len(finished)}"

            s = started[0]
            assert s.payload["status"] == "started"
            assert s.payload["streaming"] is False
            assert "message_count" in s.payload, f"missing message_count: {s.payload}"
            assert s.severity == "info"
            assert s.source == "controller"
            assert "eval-provider/eval-model" in s.summary

            f = finished[0]
            assert f.payload["status"] == "ok"
            assert f.payload["streaming"] is False
            assert "latency_ms" in f.payload, f"missing latency_ms: {f.payload}"
            assert f.payload["latency_ms"] >= 0
            assert "response_preview" in f.payload, f"missing response_preview: {f.payload}"
            assert "eval answer" in f.payload["response_preview"]
            assert f.severity == "info"

            _assert_model_events_do_not_store_raw_context(events, [sentinel_prompt])
        finally:
            db.close()


def eval_model_call_event_with_tool_calls():
    """Model call that returns tool calls records tool_call_count in finished event."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            call_count = [0]
            sentinel_prompt = "TOOL_PROMPT_SHOULD_NOT_BE_STORED_9A2B"
            sentinel_tool_result = "TOOL_RESULT_SHOULD_NOT_BE_STORED_4C8D"
            (tmpdir / "context.txt").write_text(sentinel_tool_result, encoding="utf-8")

            class FakeToolLLM:
                provider = "eval"
                model = "tool-model"
                def chat(self, messages, tools=None):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        assert sentinel_prompt in messages[-1]["content"], "sentinel prompt must reach the model"
                        return LLMResponse(
                            content="",
                            tool_calls=[ToolCall(call_id="c1", name="read_project_file", arguments={"path": "context.txt"})],
                        )
                    assert any(sentinel_tool_result in str(m.get("content", "")) for m in messages), \
                        "sentinel tool result must reach the follow-up model call"
                    return LLMResponse(content="result is 2")

            registry = build_default_registry(workspace_root=tmpdir, db=db, confirm_action=lambda _prompt: True)
            event_store = registry.durable_event_store
            agent = MiniAgent(registry, llm=FakeToolLLM(), event_store=event_store)

            result = agent.run(sentinel_prompt)

            assert "2" in result, f"expected 2 in result, got: {result}"

            events = event_store.list_events()
            finished = [e for e in events if e.event_type == MODEL_CALL_FINISHED]
            assert len(finished) >= 1, f"expected >=1 finished event, got {len(finished)}"

            # First finished event should have tool_call_count > 0
            first_finished = finished[-1]  # oldest (reversed order)
            assert first_finished.payload.get("tool_call_count", 0) >= 1, \
                f"expected tool_call_count >= 1: {first_finished.payload}"

            for event in events:
                if event.event_type in (MODEL_CALL_STARTED, MODEL_CALL_FINISHED):
                    assert event.task_id is None, "model event must not bind to unrelated task"
            _assert_model_events_do_not_store_raw_context(events, [sentinel_prompt, sentinel_tool_result])
        finally:
            db.close()


def eval_model_call_event_error():
    """Model call that raises LLMError records MODEL_CALL_ERROR without crashing existing behavior."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            class FailingLLM:
                provider = "eval"
                model = "fail-model"
                def chat(self, messages, tools=None):
                    raise LLMError("simulated model failure")

            registry = build_default_registry(workspace_root=tmpdir, db=db)
            event_store = registry.durable_event_store
            agent = MiniAgent(registry, llm=FailingLLM(), event_store=event_store)

            # run() should not crash — returns error message
            result = agent.run("hello")
            assert "模型调用失败" in result, f"expected error message, got: {result}"

            events = event_store.list_events()
            started = [e for e in events if e.event_type == MODEL_CALL_STARTED]
            errors = [e for e in events if e.event_type == MODEL_CALL_ERROR]
            finished = [e for e in events if e.event_type == MODEL_CALL_FINISHED]

            assert len(started) >= 1, f"expected >=1 started, got {len(started)}"
            assert len(errors) >= 1, f"expected >=1 error, got {len(errors)}"
            assert len(finished) == 0, f"error path must not emit finished, got {len(finished)}"

            err = errors[0]
            assert err.payload["status"] == "error"
            assert err.payload["streaming"] is False
            assert "simulated model failure" in err.payload.get("error", "")
            assert err.severity == "warning"
            assert err.source == "controller"
        finally:
            db.close()


def eval_model_call_event_streaming():
    """Streaming model call via stream_chat records model events with streaming=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            class FakeStreamingLLM:
                provider = "eval"
                model = "stream-model"
                def chat(self, messages, tools=None):
                    return LLMResponse(
                        content="",
                        tool_calls=[ToolCall(call_id="c1", name="calculate", arguments={"expression": "1+1"})],
                    )
                def stream_chat(self, messages, tools=None):
                    for word in ["streamed ", "answer ", "42"]:
                        yield word

            registry = build_default_registry(workspace_root=tmpdir, db=db)
            event_store = registry.durable_event_store
            agent = MiniAgent(registry, llm=FakeStreamingLLM(), event_store=event_store)

            result = agent.run("计算 1+1")

            assert "streamed" in result or "42" in result, f"expected streamed content, got: {result}"

            events = event_store.list_events()
            started = [e for e in events if e.event_type == MODEL_CALL_STARTED]
            finished = [e for e in events if e.event_type == MODEL_CALL_FINISHED]

            # Should have both chat model events and streaming model events
            assert len(started) >= 2, f"expected >=2 started events, got {len(started)}"
            assert len(finished) >= 2, f"expected >=2 finished events, got {len(finished)}"

            # Find the streaming started/finished pair
            streaming_started = [e for e in started if e.payload.get("streaming") is True]
            streaming_finished = [e for e in finished if e.payload.get("streaming") is True]

            assert len(streaming_started) >= 1, f"expected >=1 streaming started, got {len(streaming_started)}"
            assert len(streaming_finished) >= 1, f"expected >=1 streaming finished, got {len(streaming_finished)}"

            sf = streaming_finished[0]
            assert sf.payload["status"] == "ok"
            assert "latency_ms" in sf.payload, f"missing latency_ms: {sf.payload}"
            assert "response_preview" in sf.payload, f"missing response_preview: {sf.payload}"
            assert "streamed answer 42" in sf.payload["response_preview"]
        finally:
            db.close()


def eval_model_call_event_failure_isolation():
    """Broken event store must not break model execution or streaming."""
    class BrokenEventStore:
        def record(self, **kwargs):
            raise RuntimeError("event store offline")
        def list_events(self, **kwargs):
            return []
        def get_event(self, event_id):
            return None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        class FakeLLM:
            provider = "eval"
            model = "iso-model"
            def chat(self, messages, tools=None):
                return LLMResponse(content="survived")

        class FakeStreamingLLM:
            provider = "eval"
            model = "iso-stream"
            def chat(self, messages, tools=None):
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(call_id="c1", name="calculate", arguments={"expression": "1+1"})],
                )
            def stream_chat(self, messages, tools=None):
                yield "streamed ok"

        registry = build_default_registry(workspace_root=tmpdir)

        # 1. chat path survives broken event store
        agent = MiniAgent(registry, llm=FakeLLM(), event_store=BrokenEventStore())
        result = agent.run("hello")
        assert "survived" in result, f"chat path failed: {result}"

        # 2. run_events stream survives broken event store
        events_list = list(agent.run_events("hello again"))
        assert len(events_list) > 0, "run_events should produce events despite broken store"

        # 3. streaming path survives broken event store
        agent2 = MiniAgent(registry, llm=FakeStreamingLLM(), event_store=BrokenEventStore())
        result2 = agent2.run("计算 1+1")
        assert "ok" in result2 or "1" in result2, f"streaming path failed: {result2}"


_FILE_EDIT_SENTINELS = [
    "RAW_FILE_CONTENT_SHOULD_NOT_BE_STORED_6C2D",
    "RAW_REPLACEMENT_TEXT_SHOULD_NOT_BE_STORED_8E4A",
    "RAW_PATCH_TEXT_SHOULD_NOT_BE_STORED_1B7F",
    "RAW_OS_ERROR_SHOULD_NOT_BE_STORED_9D3E",
    "RAW_REASON_SHOULD_NOT_BE_STORED_2A5C",
]


def _file_edit_events(event_store):
    events = [
        event for event in event_store.list_events()
        if event.event_type in (FILE_EDIT_STARTED, FILE_EDIT_FINISHED, FILE_EDIT_BLOCKED, FILE_EDIT_ERROR)
    ]
    events.reverse()
    return events


def _assert_file_edit_events_safe(events) -> None:
    serialized = json.dumps([event.to_dict() for event in events], ensure_ascii=False)
    for sentinel in _FILE_EDIT_SENTINELS + ["PATCH_REPLACEMENT_MARKER_8E4A"]:
        assert sentinel not in serialized, f"file-edit event leaked sentinel {sentinel}: {serialized}"
    forbidden_keys = {"content", "old_text", "new_text", "patch", "diff", "reason", "exception", "traceback"}
    for event in events:
        leaked_keys = forbidden_keys & set(event.payload)
        assert not leaked_keys, f"file-edit event stored raw-data keys {sorted(leaked_keys)}: {event.payload}"


def eval_file_edit_event_success():
    """Registry-wired workspace write records started/finished with safe metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmpdir, db=db, confirm_action=lambda _prompt: True)
            result = registry.call(
                "write_project_file",
                path="notes.txt",
                content=_FILE_EDIT_SENTINELS[0],
                reason=_FILE_EDIT_SENTINELS[4],
            )
            assert "已写入" in result, result

            events = _file_edit_events(registry.durable_event_store)
            assert [event.event_type for event in events] == [FILE_EDIT_STARTED, FILE_EDIT_FINISHED], events
            started, finished = events
            assert started.payload["operation"] == "write", started.payload
            assert started.payload["status"] == "started", started.payload
            assert started.payload["path"] == "notes.txt", started.payload
            assert started.payload["paths"] == ["notes.txt"], started.payload
            assert finished.payload["status"] == "finished", finished.payload
            assert finished.payload["bytes_before"] == 0, finished.payload
            assert finished.payload["bytes_after"] == len(_FILE_EDIT_SENTINELS[0].encode("utf-8")), finished.payload
            assert finished.severity == "info", finished
            assert all(event.task_id is None for event in events), events
            _assert_file_edit_events_safe(events)
        finally:
            db.close()


def eval_file_edit_event_patch_metadata():
    """Patch and multi-patch events record paths/file_count/bytes without raw patch or replacement text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmpdir, db=db, confirm_action=lambda _prompt: True)
            (tmpdir / "a.txt").write_text("alpha\n", encoding="utf-8")
            (tmpdir / "b.txt").write_text("bravo\n", encoding="utf-8")
            (tmpdir / "c.txt").write_text("charlie\n", encoding="utf-8")

            patch_text = (
                "--- a/a.txt\n"
                "+++ b/a.txt\n"
                "@@ -1 +1 @@\n"
                "-alpha\n"
                "+PATCH_REPLACEMENT_MARKER_8E4A\n"
            )
            result = registry.call("apply_project_patch", patch=patch_text, reason=_FILE_EDIT_SENTINELS[4])
            assert "已应用 patch" in result, result

            multi_patch_text = (
                "--- a/b.txt\n"
                "+++ b/b.txt\n"
                "@@ -1 +1 @@\n"
                "-bravo\n"
                "+BRAVO\n"
                "--- a/c.txt\n"
                "+++ b/c.txt\n"
                "@@ -1 +1 @@\n"
                "-charlie\n"
                "+CHARLIE\n"
            )
            result2 = registry.call("apply_project_multi_patch", patch=multi_patch_text, reason=_FILE_EDIT_SENTINELS[4])
            assert "已应用多文件 patch" in result2, result2

            events = _file_edit_events(registry.durable_event_store)
            patch_events = [event for event in events if event.payload.get("operation") == "patch"]
            multi_events = [event for event in events if event.payload.get("operation") == "multi_patch"]
            assert [event.event_type for event in patch_events] == [FILE_EDIT_STARTED, FILE_EDIT_FINISHED], patch_events
            assert [event.event_type for event in multi_events] == [FILE_EDIT_STARTED, FILE_EDIT_FINISHED], multi_events
            assert patch_events[1].payload["path"] == "a.txt", patch_events[1].payload
            assert multi_events[1].payload["paths"] == ["b.txt", "c.txt"], multi_events[1].payload
            assert multi_events[1].payload["file_count"] == 2, multi_events[1].payload
            assert "bytes_before" in multi_events[1].payload, multi_events[1].payload
            assert "bytes_after" in multi_events[1].payload, multi_events[1].payload

            _assert_file_edit_events_safe(events)
            serialized = json.dumps([event.to_dict() for event in events], ensure_ascii=False)
            assert patch_text not in serialized, "single-file patch text leaked into file-edit events"
            assert multi_patch_text not in serialized, "multi-file patch text leaked into file-edit events"
        finally:
            db.close()


def eval_file_edit_event_blocked_or_cancelled():
    """Denied pre-checks are blocked-only; confirmation cancellation is started->blocked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            registry = build_default_registry(workspace_root=tmpdir, db=db, confirm_action=lambda _prompt: True)
            denied = registry.call(
                "write_project_file",
                path=".env",
                content=_FILE_EDIT_SENTINELS[0],
                reason=_FILE_EDIT_SENTINELS[4],
            )
            assert "拒绝写入" in denied, denied
            denied_events = _file_edit_events(registry.durable_event_store)
            assert [event.event_type for event in denied_events] == [FILE_EDIT_BLOCKED], denied_events
            assert denied_events[0].payload["status"] == "blocked", denied_events[0].payload
            assert denied_events[0].payload["error"] == "denied_path", denied_events[0].payload
            assert denied_events[0].severity == "warning", denied_events[0]
            _assert_file_edit_events_safe(denied_events)

            cancel_store = DurableEventStore(db=db)
            cancelling_files = WorkspaceFiles(
                tmpdir,
                confirm_action=lambda _prompt: False,
                event_store=cancel_store,
            )
            cancelled = cancelling_files.write(
                "cancelled.txt",
                _FILE_EDIT_SENTINELS[0],
                reason=_FILE_EDIT_SENTINELS[4],
            )
            assert "已取消写入" in cancelled, cancelled
            cancel_events = [
                event for event in _file_edit_events(cancel_store)
                if event.payload.get("path") == "cancelled.txt"
            ]
            assert [event.event_type for event in cancel_events] == [FILE_EDIT_STARTED, FILE_EDIT_BLOCKED], cancel_events
            assert cancel_events[1].payload["status"] == "cancelled", cancel_events[1].payload
            assert cancel_events[1].payload["error"] == "cancelled", cancel_events[1].payload
            assert not any(event.event_type == FILE_EDIT_FINISHED for event in cancel_events), cancel_events
            _assert_file_edit_events_safe(cancel_events)
        finally:
            db.close()


def eval_file_edit_event_error():
    """OS write failure records started->error with a generic label and preserves existing return behavior."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            event_store = DurableEventStore(db=db)
            files = WorkspaceFiles(tmpdir, require_confirmation=False, event_store=event_store)
            with patch.object(Path, "write_text", side_effect=OSError(_FILE_EDIT_SENTINELS[3])):
                result = files.write("error.txt", _FILE_EDIT_SENTINELS[0], reason=_FILE_EDIT_SENTINELS[4])
            assert "写入失败" in result, result
            assert _FILE_EDIT_SENTINELS[3] in result, "user-visible error behavior should be preserved"

            events = _file_edit_events(event_store)
            assert [event.event_type for event in events] == [FILE_EDIT_STARTED, FILE_EDIT_ERROR], events
            assert events[1].payload["status"] == "error", events[1].payload
            assert events[1].payload["error"] == "write_failed", events[1].payload
            assert events[1].severity == "warning", events[1]
            _assert_file_edit_events_safe(events)
        finally:
            db.close()


def eval_file_edit_event_failure_isolation():
    """Broken event store must not change workspace operation behavior."""
    class BrokenEventStore:
        def record(self, **kwargs):
            raise RuntimeError("event store offline")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        files = WorkspaceFiles(tmpdir, require_confirmation=False, event_store=BrokenEventStore())

        result = files.write("ok.txt", _FILE_EDIT_SENTINELS[0], reason=_FILE_EDIT_SENTINELS[4])
        assert "已写入" in result, result
        assert (tmpdir / "ok.txt").read_text(encoding="utf-8") == _FILE_EDIT_SENTINELS[0]

        (tmpdir / "replace.txt").write_text("old\n", encoding="utf-8")
        replaced = files.replace("replace.txt", "old", "new", reason=_FILE_EDIT_SENTINELS[4])
        assert "已修改" in replaced, replaced
        assert (tmpdir / "replace.txt").read_text(encoding="utf-8") == "new\n"


_SHELL_SENTINEL_CMD = "NORA_EVAL_SHELL_SENTINEL_a7c3e1f9"
_SHELL_SENTINEL_OUTPUT = "NORA_EVAL_SHELL_OUTPUT_SECRET_d4b28e61"
_SHELL_SENTINEL_REASON = "NORA_EVAL_SHELL_REASON_9f1e3d7a"
_SHELL_FORBIDDEN_PAYLOAD_KEYS = {"command", "args", "argv", "stdout", "stderr", "output", "result", "reason", "exception", "traceback"}


def _shell_events(event_store, event_type=None):
    events = event_store.list_events()
    shell_types = (SHELL_COMMAND_STARTED, SHELL_COMMAND_FINISHED, SHELL_COMMAND_ERROR, SHELL_COMMAND_BLOCKED)
    if event_type:
        return [e for e in events if e.event_type == event_type]
    return [e for e in events if e.event_type in shell_types]


def _serialized_shell_events(event_store):
    return json.dumps(
        [event.to_dict() for event in _shell_events(event_store)],
        ensure_ascii=False,
        sort_keys=True,
    )


def _assert_shell_events_safe(event_store, forbidden_values: list[str]) -> None:
    serialized = _serialized_shell_events(event_store)
    for value in forbidden_values:
        assert value not in serialized, f"shell event stored forbidden raw value {value!r}: {serialized}"
    for event in _shell_events(event_store):
        leaked_keys = _SHELL_FORBIDDEN_PAYLOAD_KEYS & set(event.payload)
        assert not leaked_keys, f"shell event payload leaked forbidden keys {leaked_keys}: {event.payload}"


def eval_shell_command_event_success():
    """Successful allowed command records started/finished with safe metadata. No raw command text persisted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            event_store = DurableEventStore(db=db)
            runner = ShellRunner(tmpdir, require_confirmation=False, event_store=event_store)
            result = runner.run("pwd", reason=_SHELL_SENTINEL_REASON)

            assert "exit_code: 0" in result, f"expected exit_code 0, got: {result}"

            started = _shell_events(event_store, SHELL_COMMAND_STARTED)
            finished = _shell_events(event_store, SHELL_COMMAND_FINISHED)
            assert len(started) == 1, f"expected 1 started, got {len(started)}"
            assert len(finished) == 1, f"expected 1 finished, got {len(finished)}"

            assert started[0].payload["executable"] == "pwd"
            assert started[0].severity == "info"
            assert started[0].task_id is None

            assert finished[0].payload["exit_code"] == 0
            assert finished[0].payload["status"] == "finished"
            assert finished[0].payload["stdout_bytes"] > 0
            assert finished[0].severity == "info"
            assert finished[0].task_id is None

            _assert_shell_events_safe(event_store, [_SHELL_SENTINEL_REASON])

            arg_db = NoraDB(tmpdir / "arg.db")
            try:
                arg_store = DurableEventStore(db=arg_db)
                sentinel_path = f"{_SHELL_SENTINEL_CMD}.py"
                (tmpdir / sentinel_path).write_text("x = 1\n", encoding="utf-8")
                arg_result = ShellRunner(tmpdir, require_confirmation=False, event_store=arg_store).run(
                    f"python3 -m py_compile {sentinel_path}"
                )
                assert "exit_code: 0" in arg_result, f"expected py_compile success, got: {arg_result}"
                _assert_shell_events_safe(arg_store, [_SHELL_SENTINEL_CMD, sentinel_path])
            finally:
                arg_db.close()
        finally:
            db.close()


def eval_shell_command_event_blocked():
    """Disallowed command records blocked event with no started/finished."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            event_store = DurableEventStore(db=db)
            runner = ShellRunner(tmpdir, require_confirmation=False, event_store=event_store)
            result = runner.run("rm -rf /")

            assert "拒绝" in result, f"expected rejection, got: {result}"

            blocked = _shell_events(event_store, SHELL_COMMAND_BLOCKED)
            started = _shell_events(event_store, SHELL_COMMAND_STARTED)
            finished = _shell_events(event_store, SHELL_COMMAND_FINISHED)
            assert len(blocked) == 1, f"expected 1 blocked, got {len(blocked)}"
            assert len(started) == 0, f"expected 0 started, got {len(started)}"
            assert len(finished) == 0, f"expected 0 finished, got {len(finished)}"

            assert blocked[0].payload["error"] == "disallowed_command"
            assert blocked[0].payload["status"] == "blocked"
            assert blocked[0].severity == "warning"

            # Safety: raw command args must not leak
            sentinel = _SHELL_SENTINEL_CMD
            runner2 = ShellRunner(tmpdir, require_confirmation=False, event_store=event_store)
            runner2.run(f"'{sentinel}")
            _assert_shell_events_safe(event_store, [sentinel])
        finally:
            db.close()


def eval_shell_command_event_cancelled():
    """User-cancelled command records blocked event with no started."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            event_store = DurableEventStore(db=db)
            runner = ShellRunner(
                tmpdir, require_confirmation=True,
                confirm_action=lambda _: False,
                event_store=event_store,
            )
            result = runner.run("pwd")

            assert "已取消" in result, f"expected cancel message, got: {result}"

            started = _shell_events(event_store, SHELL_COMMAND_STARTED)
            blocked = _shell_events(event_store, SHELL_COMMAND_BLOCKED)
            finished = _shell_events(event_store, SHELL_COMMAND_FINISHED)
            assert len(started) == 0, f"cancelled command must not emit started, got {len(started)}"
            assert len(blocked) == 1, f"expected 1 blocked, got {len(blocked)}"
            assert len(finished) == 0, f"cancelled command must not emit finished, got {len(finished)}"

            assert blocked[0].payload["error"] == "cancelled"
            assert blocked[0].severity == "warning"
            _assert_shell_events_safe(event_store, [])
        finally:
            db.close()


def eval_shell_command_event_error():
    """Timeout and OSError emit error events. No raw output or exception text in payload."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            event_store = DurableEventStore(db=db)

            # --- timeout ---
            (tmpdir / "main.py").write_text(
                f"import time\nprint('{_SHELL_SENTINEL_OUTPUT}', flush=True)\ntime.sleep(30)\n",
                encoding="utf-8",
            )
            runner = ShellRunner(tmpdir, require_confirmation=False, timeout_seconds=1, event_store=event_store)
            result = runner.run("python3 main.py")

            assert "timeout" in result, f"expected timeout in result, got: {result}"
            errors = _shell_events(event_store, SHELL_COMMAND_ERROR)
            started = _shell_events(event_store, SHELL_COMMAND_STARTED)
            assert len(started) == 1, f"timeout should record started, got {len(started)}"
            assert len(errors) == 1, f"expected 1 error, got {len(errors)}"
            assert errors[0].payload["error"] == "timeout"
            assert errors[0].payload["status"] == "timeout"
            assert errors[0].payload["timeout"] is True
            assert errors[0].severity == "warning"

            # Sentinel output must not appear in serialized events
            _assert_shell_events_safe(event_store, [_SHELL_SENTINEL_OUTPUT])

            # --- OSError ---
            db2 = NoraDB(tmpdir / "test2.db")
            try:
                event_store2 = DurableEventStore(db=db2)
                runner2 = ShellRunner(tmpdir, require_confirmation=False, event_store=event_store2)
                os_sentinel = "NORA_EVAL_OSERROR_SENTINEL_c8d4f2a1"
                with patch("mini_agent.shell.subprocess.run", side_effect=OSError(os_sentinel)):
                    result2 = runner2.run("pwd")

                assert "OSError" in result2, f"expected OSError in result, got: {result2}"
                assert os_sentinel not in result2, "raw OSError leaked to user"

                errors2 = _shell_events(event_store2, SHELL_COMMAND_ERROR)
                assert len(errors2) == 1
                assert errors2[0].payload["error"] == "os_error"
                assert errors2[0].severity == "warning"
                _assert_shell_events_safe(event_store2, [os_sentinel])
            finally:
                db2.close()
        finally:
            db.close()


def eval_shell_command_event_failure_isolation():
    """Broken event store must not break shell execution."""
    class BrokenEventStore:
        def record(self, **kwargs):
            raise RuntimeError("event store offline")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        runner = ShellRunner(tmpdir, require_confirmation=False, event_store=BrokenEventStore())
        result = runner.run("pwd")
        assert "exit_code: 0" in result, f"shell must work with broken event store, got: {result}"

        # Also verify no event store is fine
        runner2 = ShellRunner(tmpdir, require_confirmation=False, event_store=None)
        result2 = runner2.run("pwd")
        assert "exit_code: 0" in result2, f"shell must work without event store, got: {result2}"


# --- Test-run event eval helpers ---

_TEST_SENTINEL_OUTPUT = "NORA_EVAL_TEST_OUTPUT_SENTINEL_e5a7b3c1"
_TEST_SENTINEL_TRACEBACK = "NORA_EVAL_TEST_TRACEBACK_SENTINEL_f9d2c4e8"
_TEST_SENTINEL_EXCEPTION = "NORA_EVAL_TEST_EXCEPTION_SENTINEL_a1b6d9f3"
_TEST_SENTINEL_SECRET = "NORA_EVAL_SECRET_TOKEN_sk-test-9f8e7d6c5b4a"
_TEST_FORBIDDEN_PAYLOAD_KEYS = {"stdout", "stderr", "output", "result", "reason", "exception", "traceback", "command", "args"}


def _test_run_events(event_store, event_type=None):
    events = event_store.list_events()
    test_types = (TEST_RUN_STARTED, TEST_RUN_FINISHED, TEST_RUN_ERROR, TEST_RUN_BLOCKED)
    if event_type:
        return [e for e in events if e.event_type == event_type]
    return [e for e in events if e.event_type in test_types]


def _serialized_test_run_events(event_store):
    import json as _json
    return _json.dumps(
        [event.to_dict() for event in _test_run_events(event_store)],
        ensure_ascii=False,
        sort_keys=True,
    )


def _assert_test_run_events_safe(event_store, forbidden_values: list[str]) -> None:
    serialized = _serialized_test_run_events(event_store)
    for value in forbidden_values:
        assert value not in serialized, f"test-run event stored forbidden raw value {value!r}: {serialized[:500]}"
    for event in _test_run_events(event_store):
        leaked_keys = _TEST_FORBIDDEN_PAYLOAD_KEYS & set(event.payload)
        assert not leaked_keys, f"test-run event payload leaked forbidden keys {leaked_keys}: {event.payload}"


def eval_test_run_event_success():
    """Successful test run records started/finished with safe metadata. No raw output persisted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            # Create a passing test file that prints sentinel output
            tests_dir = tmpdir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_pass.py").write_text(
                f"import unittest\nprint('{_TEST_SENTINEL_OUTPUT}', flush=True)\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            event_store = DurableEventStore(db=db)
            diag = Diagnostics(tmpdir, event_store=event_store)
            result = diag.run_tests()

            assert "exit_code: 0" in result, f"expected exit_code 0, got: {result}"
            # User-visible result may contain the sentinel output
            # (this proves the test actually ran and produced output)

            started = _test_run_events(event_store, TEST_RUN_STARTED)
            finished = _test_run_events(event_store, TEST_RUN_FINISHED)
            assert len(started) == 1, f"expected 1 started, got {len(started)}"
            assert len(finished) == 1, f"expected 1 finished, got {len(finished)}"

            assert started[0].payload["status"] == "started"
            assert started[0].payload["command_kind"] == "unittest_discover"
            assert started[0].severity == "info"
            assert started[0].task_id is None
            assert "max_output_chars" in started[0].payload

            assert finished[0].payload["status"] == "finished"
            assert finished[0].payload["exit_code"] == 0
            assert finished[0].payload["stdout_bytes"] + finished[0].payload["stderr_bytes"] > 0
            assert finished[0].severity == "info"
            assert finished[0].task_id is None

            # Sentinel output must NOT appear in durable events
            _assert_test_run_events_safe(event_store, [_TEST_SENTINEL_OUTPUT])
        finally:
            db.close()


def eval_test_run_event_failure():
    """Failing test run records finished with nonzero exit_code. No raw failure body or traceback in events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            tests_dir = tmpdir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_fail.py").write_text(
                f"import unittest\n\nclass T(unittest.TestCase):\n    def test_fail(self):\n        self.fail('{_TEST_SENTINEL_TRACEBACK}')\n",
                encoding="utf-8",
            )

            event_store = DurableEventStore(db=db)
            diag = Diagnostics(tmpdir, event_store=event_store)
            result = diag.run_tests()

            assert "exit_code:" in result, f"expected exit_code in result, got: {result}"
            assert "1" in result.split("exit_code:")[1].split("\n")[0], f"expected nonzero exit_code, got: {result}"

            finished = _test_run_events(event_store, TEST_RUN_FINISHED)
            assert len(finished) == 1, f"expected 1 finished, got {len(finished)}"
            assert finished[0].payload["exit_code"] != 0
            assert finished[0].payload["status"] == "finished"
            assert finished[0].severity == "info"

            # Sentinel traceback text must not appear in events
            _assert_test_run_events_safe(event_store, [_TEST_SENTINEL_TRACEBACK])
        finally:
            db.close()


def eval_test_run_event_blocked():
    """Disallowed command records blocked event with no started/finished."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            event_store = DurableEventStore(db=db)
            diag = Diagnostics(tmpdir, event_store=event_store)
            result = diag.run_tests(command="rm -rf /")

            assert "拒绝" in result, f"expected rejection, got: {result}"

            blocked = _test_run_events(event_store, TEST_RUN_BLOCKED)
            started = _test_run_events(event_store, TEST_RUN_STARTED)
            finished = _test_run_events(event_store, TEST_RUN_FINISHED)
            assert len(blocked) == 1, f"expected 1 blocked, got {len(blocked)}"
            assert len(started) == 0, f"expected 0 started, got {len(started)}"
            assert len(finished) == 0, f"expected 0 finished, got {len(finished)}"

            assert blocked[0].payload["status"] == "blocked"
            assert blocked[0].payload["error"] == "disallowed_command"
            assert blocked[0].severity == "warning"

            # Safety: raw command must not leak
            sentinel_cmd = "NORA_EVAL_BLOCKED_CMD_SENTINEL_b7c9d1e3"
            diag2 = Diagnostics(tmpdir, event_store=event_store)
            diag2.run_tests(command=sentinel_cmd)
            _assert_test_run_events_safe(event_store, [sentinel_cmd])
        finally:
            db.close()


def eval_test_run_event_timeout_or_error():
    """Timeout and OSError emit error events. No raw output or exception text in payload."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db = NoraDB(tmpdir / "test.db")
        try:
            # --- timeout ---
            tests_dir = tmpdir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_slow.py").write_text(
                f"import unittest, time\nprint('{_TEST_SENTINEL_OUTPUT}', flush=True)\nclass T(unittest.TestCase):\n    def test_slow(self):\n        time.sleep(30)\n",
                encoding="utf-8",
            )

            event_store = DurableEventStore(db=db)
            diag = Diagnostics(tmpdir, timeout_seconds=1, event_store=event_store)
            result = diag.run_tests()

            assert "timeout" in result, f"expected timeout in result, got: {result}"

            errors = _test_run_events(event_store, TEST_RUN_ERROR)
            started = _test_run_events(event_store, TEST_RUN_STARTED)
            assert len(started) == 1, f"timeout should record started, got {len(started)}"
            assert len(errors) == 1, f"expected 1 error, got {len(errors)}"
            assert errors[0].payload["error"] == "timeout"
            assert errors[0].payload["status"] == "timeout"
            assert errors[0].payload["timeout"] is True
            assert errors[0].severity == "warning"

            # Sentinel output must not appear in events
            _assert_test_run_events_safe(event_store, [_TEST_SENTINEL_OUTPUT])

            # --- OSError ---
            db2 = NoraDB(tmpdir / "test2.db")
            try:
                event_store2 = DurableEventStore(db=db2)
                diag2 = Diagnostics(tmpdir, event_store=event_store2)
                with patch("mini_agent.diagnostics.subprocess.run", side_effect=OSError(_TEST_SENTINEL_EXCEPTION)):
                    result2 = diag2.run_tests()

                assert "OSError" in result2, f"expected OSError in result, got: {result2}"
                assert _TEST_SENTINEL_EXCEPTION not in result2, "raw OSError leaked to user"

                errors2 = _test_run_events(event_store2, TEST_RUN_ERROR)
                assert len(errors2) == 1
                assert errors2[0].payload["error"] == "os_error"
                assert errors2[0].severity == "warning"
                _assert_test_run_events_safe(event_store2, [_TEST_SENTINEL_EXCEPTION])
            finally:
                db2.close()
        finally:
            db.close()


def eval_test_run_event_failure_isolation():
    """Broken event store must not change existing diagnostics behavior."""
    class BrokenEventStore:
        def record(self, **kwargs):
            raise RuntimeError("event store offline")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create a passing test
        tests_dir = tmpdir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_pass.py").write_text(
            "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
            encoding="utf-8",
        )

        # 1. Broken event store: run_tests must still succeed
        diag = Diagnostics(tmpdir, event_store=BrokenEventStore())
        result = diag.run_tests()
        assert "exit_code: 0" in result, f"diagnostics must work with broken event store, got: {result}"

        # 2. No event store: run_tests must still succeed
        diag2 = Diagnostics(tmpdir, event_store=None)
        result2 = diag2.run_tests()
        assert "exit_code: 0" in result2, f"diagnostics must work without event store, got: {result2}"

        # 3. Blocked command with broken store must still reject
        diag3 = Diagnostics(tmpdir, event_store=BrokenEventStore())
        result3 = diag3.run_tests(command="rm -rf /")
        assert "拒绝" in result3, f"blocked command must still reject with broken store, got: {result3}"

        # 4. diagnose_test_failure must work regardless of event store
        diag4 = Diagnostics(tmpdir, event_store=BrokenEventStore())
        diagnosis = diag4.diagnose_test_failure("FAIL: test_x (tests.test_x.TestX.test_x)\nAssertionError: 1 != 2")
        assert "FAIL" in diagnosis, f"diagnose_test_failure must work, got: {diagnosis}"


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
