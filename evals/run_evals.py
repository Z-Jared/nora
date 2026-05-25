from dataclasses import dataclass
from pathlib import Path
import os
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from mini_agent.controller import MiniAgent
from mini_agent.memory import LongTermMemory
from mini_agent.providers.anthropic import AnthropicClient
from mini_agent.providers.factory import build_llm_client
from mini_agent.providers.gemini import GeminiClient
from mini_agent.providers.openai_compatible import OpenAICompatibleClient
from mini_agent.rag import ProjectRAG
from mini_agent.shell import ShellRunner
from mini_agent.settings import load_settings
from mini_agent.task_runner import TaskManager
from mini_agent.tools import WorkspaceFiles, build_default_registry


@dataclass
class EvalCase:
    name: str
    run: callable


def main() -> int:
    cases = [
        EvalCase("agent_calculates_math", eval_agent_calculates_math),
        EvalCase("notes_round_trip", eval_notes_round_trip),
        EvalCase("workspace_rejects_env", eval_workspace_rejects_env),
        EvalCase("workspace_writes_when_confirmed", eval_workspace_writes_when_confirmed),
        EvalCase("registry_cancels_unconfirmed_write", eval_registry_cancels_unconfirmed_write),
        EvalCase("registry_cancels_unconfirmed_shell", eval_registry_cancels_unconfirmed_shell),
        EvalCase("browser_tools_read_page", eval_browser_tools_read_page),
        EvalCase("registry_cancels_unconfirmed_browser_click", eval_registry_cancels_unconfirmed_browser_click),
        EvalCase("rag_finds_project_context", eval_rag_finds_project_context),
        EvalCase("memory_rejects_secret", eval_memory_rejects_secret),
        EvalCase("shell_rejects_rm", eval_shell_rejects_rm),
        EvalCase("task_run_once_marks_step", eval_task_run_once_marks_step),
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


def eval_llm_calculate_tool_call():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请使用工具计算 2 + 3 * 4，最终只需要说明结果。")
    assert "14" in result, result


def eval_llm_read_project_file():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请读取 README.md，并用一句话说明这个项目是什么。")
    assert "Mini Agent" in result or "agent" in result.lower(), result


def eval_llm_search_project_context():
    agent = _build_real_llm_agent(PROJECT_ROOT)
    result = agent.run("请搜索项目上下文：tool calling 是在哪里实现的？")
    assert "tool" in result.lower() or "工具" in result, result


def _build_real_llm_agent(workspace_root: Path) -> MiniAgent:
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
        confirm_action=lambda prompt: False,
    )
    return MiniAgent(registry, llm=llm)


class FakeBrowserBackend:
    def __init__(self):
        self.opened_url = ""
        self.clicked = []

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

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"eval")


if __name__ == "__main__":
    raise SystemExit(main())
