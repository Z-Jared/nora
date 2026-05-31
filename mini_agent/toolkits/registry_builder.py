import json as _json
from pathlib import Path
from typing import Callable, Optional

from mini_agent.code_quality import CodeQualityTools
from mini_agent.context_compiler import ContextCompiler
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
from mini_agent.traces import TraceStore
from mini_agent.durable_tasks import DurableTaskStore
from mini_agent.durable_events import DurableEventStore
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
    context_compiler = ContextCompiler(
        root,
        symbol_index=symbol_index,
        project_rag=project_rag,
    )
    long_term_memory = LongTermMemory(path=long_term_memory_path or Path("data/long_term_memory.jsonl"), db=db)
    durable_task_store = DurableTaskStore(db=db)
    durable_event_store = DurableEventStore(db=db)
    task_manager = TaskManager(
        path=task_state_path or Path("data/current_task.json"),
        history_path=task_history_path or Path("data/task_history.jsonl"),
        db=db,
        durable_store=durable_task_store,
        enable_durable_shadow=True,
        event_store=durable_event_store,
    )
    context_summaries = ContextSummaryStore(path=context_summary_path or Path("data/context_summaries.jsonl"), db=db)
    tool_results = ToolResultStore(path=tool_results_path or Path("data/tool_results.jsonl"), db=db)
    trace_store = TraceStore(db=db)
    logger = JsonlToolLogger(path=log_path or Path("logs/tool_calls.jsonl"), db=db)
    registry = ToolRegistry(
        logger=logger,
        confirm_action=confirm_action,
        disabled_tools=disabled_tools,
        permission_overrides=permission_overrides,
        event_store=durable_event_store,
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
        context_compiler=context_compiler,
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
    registry.task_manager = task_manager
    registry.long_term_memory = long_term_memory
    registry.trace_store = trace_store
    registry.durable_task_store = durable_task_store
    registry.durable_event_store = durable_event_store
    workspace_files.event_store = durable_event_store
    shell_runner.event_store = durable_event_store
    diagnostics.event_store = durable_event_store
    registry.diagnostics = diagnostics

    def _list_traces_json(max_results: int = 20) -> str:
        traces = trace_store.list_traces(max_results=max_results)
        return _json.dumps(traces, ensure_ascii=False)

    def _get_trace_json(trace_id: str) -> str:
        trace = trace_store.get_trace(trace_id)
        if trace is None:
            return _json.dumps({"error": f"未找到 trace: {trace_id}"}, ensure_ascii=False)
        return _json.dumps(trace, ensure_ascii=False)

    registry.register(
        "list_run_traces",
        "列出最近的运行 trace，包括 trace_id、状态、输入预览和工具调用数。",
        _list_traces_json,
        parameters={
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少条 trace，默认 20，最大 100",
                }
            },
        },
        permission=ToolPermission(category="logs", risk="read"),
    )
    registry.register(
        "get_run_trace",
        "按 trace_id 获取一条运行 trace 的完整信息，包括事件计数、工具调用详情和失败原因。",
        _get_trace_json,
        parameters={
            "type": "object",
            "properties": {
                "trace_id": {
                    "type": "string",
                    "description": "trace id，例如 trace_1",
                }
            },
            "required": ["trace_id"],
        },
        permission=ToolPermission(category="logs", risk="read"),
    )

    def _list_durable_events_json(task_id: str = "", max_results: int = 50) -> str:
        events = durable_event_store.list_events(task_id=task_id or "", max_results=max_results)
        summary = [
            {
                "event_id": event.event_id,
                "task_id": event.task_id,
                "event_type": event.event_type,
                "created_at": event.created_at,
                "summary": event.summary,
                "trace_id": event.trace_id,
                "checkpoint_id": event.checkpoint_id,
                "worker_id": event.worker_id,
            }
            for event in events
        ]
        return _json.dumps(summary, ensure_ascii=False)

    def _get_durable_event_json(event_id: str) -> str:
        event = durable_event_store.get_event(event_id)
        if event is None:
            return _json.dumps({"error": f"未找到 durable event: {event_id}"}, ensure_ascii=False)
        return _json.dumps(event.to_dict(), ensure_ascii=False)

    registry.register(
        "list_durable_events",
        "列出 durable event log 中最近的事件，可按 task_id 过滤。",
        _list_durable_events_json,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "可选 durable task id，例如 dtask_1；为空则列出所有事件",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少条，默认 50，最大 500",
                },
            },
        },
        permission=ToolPermission(category="logs", risk="read"),
    )
    registry.register(
        "get_durable_event",
        "按 event_id 获取一条 durable event 的完整信息。",
        _get_durable_event_json,
        parameters={
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "durable event id，例如 devt_1",
                }
            },
            "required": ["event_id"],
        },
        permission=ToolPermission(category="logs", risk="read"),
    )

    def _list_durable_tasks_json(limit: int = 20) -> str:
        tasks = durable_task_store.list_tasks(limit=limit)
        summary = [
            {
                "task_id": t.task_id,
                "status": t.status,
                "goal": t.goal,
                "current_step": t.current_step,
                "checkpoint_count": len(t.checkpoints),
            }
            for t in tasks
        ]
        return _json.dumps(summary, ensure_ascii=False)

    def _get_durable_task_json(task_id: str) -> str:
        task = durable_task_store.get_task(task_id)
        if task is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        return _json.dumps(task.to_dict(), ensure_ascii=False)

    registry.register(
        "list_durable_tasks",
        "列出最近的 durable tasks，包括 task_id、状态、goal、当前步骤和 checkpoint 数量。",
        _list_durable_tasks_json,
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "最多返回多少条，默认 20，最大 100",
                }
            },
        },
        permission=ToolPermission(category="logs", risk="read"),
    )
    registry.register(
        "get_durable_task",
        "按 task_id 获取一条 durable task 的完整信息，包括步骤、checkpoints、trace 引用和失败原因。",
        _get_durable_task_json,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "durable task id，例如 dtask_1",
                }
            },
            "required": ["task_id"],
        },
        permission=ToolPermission(category="logs", risk="read"),
    )

    def _create_durable_task_json(goal: str, steps: str) -> str:
        parsed = [s.strip() for s in steps.splitlines() if s.strip()]
        step_dicts = [{"text": s} for s in parsed]
        task = durable_task_store.create_task(goal=goal, steps=step_dicts)
        return _json.dumps(task.to_dict(), ensure_ascii=False)

    def _update_durable_task_json(task_id: str, status: str = "", failure_reason: str = "") -> str:
        if not status:
            return _json.dumps({"error": "status 参数必填"}, ensure_ascii=False)
        try:
            task = durable_task_store.update_status(task_id, status, failure_reason=failure_reason)
        except ValueError as e:
            return _json.dumps({"error": str(e)}, ensure_ascii=False)
        if task is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        return _json.dumps(task.to_dict(), ensure_ascii=False)

    def _delete_durable_task_json(task_id: str) -> str:
        deleted = durable_task_store.delete_task(task_id)
        if not deleted:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        return _json.dumps({"deleted": True, "task_id": task_id}, ensure_ascii=False)

    registry.register(
        "create_durable_task",
        "创建一个新的 durable task。goal 是任务目标，steps 是每行一个步骤的文本。",
        _create_durable_task_json,
        parameters={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "任务目标描述",
                },
                "steps": {
                    "type": "string",
                    "description": "每行一个步骤的文本",
                },
            },
            "required": ["goal", "steps"],
        },
        permission=ToolPermission(category="task", risk="write", requires_confirmation=True),
    )
    registry.register(
        "update_durable_task",
        "更新 durable task 的状态（如 running、completed、failed、cancelled）。",
        _update_durable_task_json,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "durable task id，例如 dtask_1",
                },
                "status": {
                    "type": "string",
                    "description": "新状态: running, paused, blocked, completed, failed, cancelled",
                },
                "failure_reason": {
                    "type": "string",
                    "description": "失败原因（可选，仅 failed/cancelled 时使用）",
                },
            },
            "required": ["task_id", "status"],
        },
        permission=ToolPermission(category="task", risk="write", requires_confirmation=True),
    )
    registry.register(
        "delete_durable_task",
        "删除一条 durable task。此操作不可逆。",
        _delete_durable_task_json,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "durable task id，例如 dtask_1",
                }
            },
            "required": ["task_id"],
        },
        permission=ToolPermission(category="task", risk="write", requires_confirmation=True),
    )

    def _retry_durable_task_json(task_id: str) -> str:
        try:
            task = durable_task_store.retry_durable_task(task_id)
        except ValueError as e:
            return _json.dumps({"error": str(e)}, ensure_ascii=False)
        if task is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        return _json.dumps(task.to_dict(), ensure_ascii=False)

    registry.register(
        "retry_durable_task",
        "重试一个失败的 durable task。将状态重置为 pending，步骤也重置，retry_count 加 1。仅 FAILED 状态可重试，且不能超过 max_retries。",
        _retry_durable_task_json,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "durable task id，例如 dtask_1",
                }
            },
            "required": ["task_id"],
        },
        permission=ToolPermission(category="task", risk="write", requires_confirmation=True),
    )

    registry.register(
        "list_tool_permissions",
        "查看所有工具的权限分类和哪些工具需要确认。",
        registry.describe_permissions,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="local", risk="read"),
    )
    return registry
