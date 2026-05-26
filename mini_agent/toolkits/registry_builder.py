from pathlib import Path
from typing import Callable, Optional

from mini_agent.code_quality import CodeQualityTools
from mini_agent.context_summary import ContextSummaryStore
from mini_agent.database import NoraDB
from mini_agent.diagnostics import Diagnostics
from mini_agent.git_tools import GitTools
from mini_agent.logs import JsonlToolLogger
from mini_agent.memory import LongTermMemory
from mini_agent.process_manager import ProcessManager
from mini_agent.rag import ProjectRAG
from mini_agent.registry import ToolPermission, ToolRegistry
from mini_agent.repair_loop import RepairLoop
from mini_agent.shell import ShellRunner
from mini_agent.symbols import PythonSymbolIndex
from mini_agent.task_runner import TaskManager
from mini_agent.toolkits.browser import BrowserBackend, BrowserTools
from mini_agent.toolkits.notes import NotesStore
from mini_agent.toolkits.register_core import register_core_tools
from mini_agent.toolkits.register_developer import register_developer_tools
from mini_agent.toolkits.register_external import register_external_tools
from mini_agent.toolkits.register_git import register_git_tools
from mini_agent.toolkits.register_state import register_state_tools
from mini_agent.tool_results import ToolResultStore
from mini_agent.toolkits.workspace import WorkspaceFiles
from mini_agent.web_tools import WebTools


def build_default_registry(
    notes_path: Optional[Path] = None,
    workspace_root: Optional[Path] = None,
    log_path: Optional[Path] = None,
    confirm_action: Optional[Callable[[str], bool]] = None,
    web_fetch: Optional[Callable[[str, int], str]] = None,
    browser_backend: Optional[BrowserBackend] = None,
    long_term_memory_path: Optional[Path] = None,
    task_state_path: Optional[Path] = None,
    task_history_path: Optional[Path] = None,
    context_summary_path: Optional[Path] = None,
    process_profiles: Optional[dict[str, list[str]]] = None,
    disabled_tools: Optional[set[str]] = None,
    permission_overrides: Optional[dict[str, bool]] = None,
    tool_results_path: Optional[Path] = None,
    rag_include_paths: Optional[list[str]] = None,
    rag_exclude_dirs: Optional[list[str]] = None,
    rag_max_file_bytes: int = 64 * 1024,
    rag_chunk_size: int = 80,
    rag_chunk_overlap: int = 20,
    db: Optional[NoraDB] = None,
) -> ToolRegistry:
    root = workspace_root or Path.cwd()
    notes = NotesStore(notes_path or Path("data/notes.txt"))
    workspace_files = WorkspaceFiles(root, require_confirmation=False)
    shell_runner = ShellRunner(root, require_confirmation=False)
    git_tools = GitTools(root)
    diagnostics = Diagnostics(root)
    repair_loop = RepairLoop(diagnostics)
    symbol_index = PythonSymbolIndex(root)
    project_rag = ProjectRAG(
        root,
        max_file_bytes=rag_max_file_bytes,
        include_paths=rag_include_paths,
        exclude_dirs=rag_exclude_dirs,
        chunk_size=rag_chunk_size,
        chunk_overlap=rag_chunk_overlap,
    )
    web_tools = WebTools(fetcher=web_fetch)
    browser_tools = BrowserTools(root=root, backend=browser_backend)
    process_manager = ProcessManager(root, profiles=process_profiles)
    code_quality = CodeQualityTools(root)
    long_term_memory = LongTermMemory(path=long_term_memory_path or Path("data/long_term_memory.jsonl"), db=db)
    task_manager = TaskManager(
        path=task_state_path or Path("data/current_task.json"),
        history_path=task_history_path or Path("data/task_history.jsonl"),
        db=db,
    )
    context_summaries = ContextSummaryStore(path=context_summary_path or Path("data/context_summaries.jsonl"), db=db)
    tool_results = ToolResultStore(path=tool_results_path or Path("data/tool_results.jsonl"), db=db)
    logger = JsonlToolLogger(path=log_path or Path("logs/tool_calls.jsonl"), db=db)
    registry = ToolRegistry(
        logger=logger,
        confirm_action=confirm_action,
        disabled_tools=disabled_tools,
        permission_overrides=permission_overrides,
    )

    register_core_tools(registry, notes, workspace_files)
    register_git_tools(registry, git_tools)
    register_developer_tools(
        registry,
        workspace_files,
        diagnostics,
        repair_loop,
        symbol_index,
        shell_runner,
        process_manager,
        code_quality=code_quality,
    )
    register_external_tools(registry, project_rag, web_tools, browser_tools)
    register_state_tools(
        registry,
        logger,
        tool_results,
        context_summaries,
        long_term_memory,
        task_manager,
    )
    registry.register(
        "list_tool_permissions",
        "查看所有工具的权限分类和哪些工具需要确认。",
        registry.describe_permissions,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="local", risk="read"),
    )
    return registry
