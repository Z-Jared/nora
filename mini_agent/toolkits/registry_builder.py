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
from mini_agent.memory_records import MemoryRecordStore
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
from mini_agent.toolkits.register_memory_records import register_memory_record_tools
from mini_agent.toolkits.register_review_memory import register_review_memory_tool
from mini_agent.toolkits.register_state import register_state_tools
from mini_agent.toolkits.register_supermemory import register_supermemory_tools
from mini_agent.toolkits.supermemory import SupermemoryClient
from mini_agent.tool_results import ToolResultStore
from mini_agent.toolkits.workspace import WorkspaceFiles
from mini_agent.traces import TraceStore
from mini_agent.durable_tasks import DurableTaskStore
from mini_agent.durable_workers import DurableWorkerStore, WorkerStatus
from mini_agent.durable_events import (
    CHECKPOINT_ADDED,
    DurableEventStore,
    TASK_CREATED,
    TASK_STATUS_CHANGED,
    TASK_RETRIED,
)
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
    memory_record_store = MemoryRecordStore(db=db)
    context_compiler = ContextCompiler(
        root,
        symbol_index=symbol_index,
        project_rag=project_rag,
        memory_record_store=memory_record_store,
    )
    durable_task_store = DurableTaskStore(db=db)
    durable_event_store = DurableEventStore(db=db)
    durable_worker_store = DurableWorkerStore(db=db)
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
    supermemory_client = SupermemoryClient.from_env()
    register_supermemory_tools(registry, supermemory_client)
    register_memory_record_tools(registry, memory_record_store)
    register_review_memory_tool(registry, memory_record_store)
    registry.task_manager = task_manager
    registry.long_term_memory = long_term_memory
    registry.memory_record_store = memory_record_store
    registry.trace_store = trace_store
    registry.durable_task_store = durable_task_store
    registry.durable_event_store = durable_event_store
    registry.durable_worker_store = durable_worker_store
    workspace_files.event_store = durable_event_store
    shell_runner.event_store = durable_event_store
    git_tools.event_store = durable_event_store
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

    def _list_durable_events_json(
        task_id: str = "",
        max_results: int = 50,
        event_type: str = "",
        source: str = "",
        severity: str = "",
        worker_id: str = "",
        trace_id: str = "",
        checkpoint_id: str = "",
    ) -> str:
        events = durable_event_store.list_events(
            task_id=task_id or "",
            max_results=max_results,
            event_type=event_type or "",
            source=source or "",
            severity=severity or "",
            worker_id=worker_id or "",
            trace_id=trace_id or "",
            checkpoint_id=checkpoint_id or "",
        )
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
                "source": event.source,
                "severity": event.severity,
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
        "列出 durable event log 中最近的事件，可按 task_id、event_type、source、severity、worker_id、trace_id、checkpoint_id 过滤。",
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
                "event_type": {
                    "type": "string",
                    "description": "可选事件类型过滤，例如 tool_call_started、model_call_finished",
                },
                "source": {
                    "type": "string",
                    "description": "可选事件来源过滤，例如 controller、registry、task_manager",
                },
                "severity": {
                    "type": "string",
                    "description": "可选严重级别过滤：info、warning",
                },
                "worker_id": {
                    "type": "string",
                    "description": "可选 worker id 过滤",
                },
                "trace_id": {
                    "type": "string",
                    "description": "可选 trace id 过滤",
                },
                "checkpoint_id": {
                    "type": "string",
                    "description": "可选 checkpoint id 过滤",
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
                "worker_id": t.worker_id,
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

    def _create_durable_task_json(goal: str, steps: str, worker_id: str = "") -> str:
        parsed = [s.strip() for s in steps.splitlines() if s.strip()]
        step_dicts = [{"text": s} for s in parsed]
        worker_id = worker_id.strip()
        task = durable_task_store.create_task(goal=goal, steps=step_dicts, worker_id=worker_id or None)
        try:
            registry.durable_event_store.record(
                event_type=TASK_CREATED,
                task_id=task.task_id,
                worker_id=task.worker_id,
                summary="task created",
                payload={
                    "operation": "create",
                    "task_id": task.task_id,
                    "status": task.status,
                    "step_count": len(task.steps),
                    "max_retries": task.max_retries,
                    "worker_id_present": bool(task.worker_id),
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
        return _json.dumps(task.to_dict(), ensure_ascii=False)

    def _update_durable_task_json(task_id: str, status: str = "", failure_reason: str = "") -> str:
        if not status:
            return _json.dumps({"error": "status 参数必填"}, ensure_ascii=False)
        existing = durable_task_store.get_task(task_id)
        previous_status = existing.status if existing else ""
        try:
            task = durable_task_store.update_status(task_id, status, failure_reason=failure_reason)
        except ValueError as e:
            return _json.dumps({"error": str(e)}, ensure_ascii=False)
        if task is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        try:
            registry.durable_event_store.record(
                event_type=TASK_STATUS_CHANGED,
                task_id=task_id,
                worker_id=task.worker_id,
                summary="task status changed",
                payload={
                    "operation": "update",
                    "task_id": task_id,
                    "status": task.status,
                    "previous_status": previous_status,
                    "failure_reason_present": bool(failure_reason),
                    "worker_id_present": bool(task.worker_id),
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
        return _json.dumps(task.to_dict(), ensure_ascii=False)

    def _delete_durable_task_json(task_id: str) -> str:
        task = durable_task_store.get_task(task_id)
        previous_status = task.status if task else ""
        deleted = durable_task_store.delete_task(task_id)
        if not deleted:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        try:
            registry.durable_event_store.record(
                event_type=TASK_STATUS_CHANGED,
                task_id=task_id,
                worker_id=task.worker_id if task else None,
                summary="task deleted",
                payload={
                    "operation": "delete",
                    "task_id": task_id,
                    "deleted": True,
                    "previous_status": previous_status,
                    "worker_id_present": bool(task.worker_id) if task else False,
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
        return _json.dumps({"deleted": True, "task_id": task_id}, ensure_ascii=False)

    def _assign_durable_task_json(task_id: str, worker_id: str = "") -> str:
        existing = durable_task_store.get_task(task_id)
        previous_worker_id_present = bool(existing.worker_id) if existing else False
        task = durable_task_store.assign_worker(task_id, worker_id.strip())
        if task is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        try:
            registry.durable_event_store.record(
                event_type=TASK_STATUS_CHANGED,
                task_id=task_id,
                worker_id=task.worker_id,
                summary="task worker assigned",
                payload={
                    "operation": "assign",
                    "task_id": task_id,
                    "worker_id_present": bool(task.worker_id),
                    "previous_worker_id_present": previous_worker_id_present,
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
        return _json.dumps(task.to_dict(), ensure_ascii=False)

    registry.register(
        "create_durable_task",
        "创建一个新的 durable task。goal 是任务目标，steps 是每行一个步骤的文本。可选 worker_id 指定负责 worker。",
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
                "worker_id": {
                    "type": "string",
                    "description": "可选 worker id，指定负责此任务的 worker",
                },
            },
            "required": ["goal", "steps"],
        },
        permission=ToolPermission(category="task", risk="write", requires_confirmation=True),
    )
    registry.register(
        "assign_durable_task",
        "将 durable task 分配给指定 worker（或清除分配）。不会改变任务状态。",
        _assign_durable_task_json,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "durable task id，例如 dtask_1",
                },
                "worker_id": {
                    "type": "string",
                    "description": "worker id；为空则清除分配",
                },
            },
            "required": ["task_id"],
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
        try:
            registry.durable_event_store.record(
                event_type=TASK_RETRIED,
                task_id=task_id,
                worker_id=task.worker_id,
                summary="task retried",
                payload={
                    "operation": "retry",
                    "task_id": task_id,
                    "status": task.status,
                    "retry_count": task.retry_count,
                    "max_retries": task.max_retries,
                    "worker_id_present": bool(task.worker_id),
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
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

    def _register_worker_json(worker_id: str, role: str = "", workspace_path: str = "") -> str:
        worker_id = worker_id.strip()
        if not worker_id:
            return _json.dumps({"error": "worker_id 不能为空"}, ensure_ascii=False)
        worker = durable_worker_store.register_worker(
            worker_id=worker_id, role=role, workspace_path=workspace_path,
        )
        return _json.dumps(worker.to_dict(), ensure_ascii=False)

    def _list_workers_json(limit: int = 20) -> str:
        workers = durable_worker_store.list_workers(limit=limit)
        return _json.dumps([w.to_dict() for w in workers], ensure_ascii=False)

    def _get_worker_json(worker_id: str) -> str:
        worker_id = worker_id.strip()
        if not worker_id:
            return _json.dumps({"error": "worker_id 不能为空"}, ensure_ascii=False)
        worker = durable_worker_store.get_worker(worker_id)
        if worker is None:
            return _json.dumps({"error": f"未找到 worker: {worker_id}"}, ensure_ascii=False)
        return _json.dumps(worker.to_dict(), ensure_ascii=False)

    def _update_worker_status_json(worker_id: str, status: str, current_task_id: str = "") -> str:
        worker_id = worker_id.strip()
        if not worker_id:
            return _json.dumps({"error": "worker_id 不能为空"}, ensure_ascii=False)
        valid_statuses = {s.value for s in WorkerStatus}
        if status not in valid_statuses:
            return _json.dumps({"error": f"无效状态: {status!r}，可选: {sorted(valid_statuses)}"}, ensure_ascii=False)
        worker = durable_worker_store.update_status(
            worker_id=worker_id, status=status,
            current_task_id=current_task_id or None,
        )
        if worker is None:
            return _json.dumps({"error": f"未找到 worker: {worker_id}"}, ensure_ascii=False)
        return _json.dumps(worker.to_dict(), ensure_ascii=False)

    registry.register(
        "register_worker",
        "注册或更新一个 durable worker。worker_id 必填且不能为空。",
        _register_worker_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {
                    "type": "string",
                    "description": "worker id，例如 worker_1",
                },
                "role": {
                    "type": "string",
                    "description": "worker 角色，例如 worker、reviewer",
                },
                "workspace_path": {
                    "type": "string",
                    "description": "worker 的工作目录路径",
                },
            },
            "required": ["worker_id"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "list_workers",
        "列出已注册的 durable workers。",
        _list_workers_json,
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
        "get_worker",
        "按 worker_id 获取一条 durable worker 的完整信息。",
        _get_worker_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {
                    "type": "string",
                    "description": "worker id，例如 worker_1",
                }
            },
            "required": ["worker_id"],
        },
        permission=ToolPermission(category="logs", risk="read"),
    )
    registry.register(
        "update_worker_status",
        "更新 worker 状态和当前任务分配。",
        _update_worker_status_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {
                    "type": "string",
                    "description": "worker id，例如 worker_1",
                },
                "status": {
                    "type": "string",
                    "description": f"新状态: {', '.join(s.value for s in WorkerStatus)}",
                },
                "current_task_id": {
                    "type": "string",
                    "description": "可选，当前分配的 durable task id",
                },
            },
            "required": ["worker_id", "status"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )

    def _touch_worker_json(worker_id: str) -> str:
        worker_id = worker_id.strip()
        if not worker_id:
            return _json.dumps({"error": "worker_id 不能为空"}, ensure_ascii=False)
        worker = durable_worker_store.touch(worker_id)
        if worker is None:
            return _json.dumps({"error": f"未找到 worker: {worker_id}"}, ensure_ascii=False)
        return _json.dumps(worker.to_dict(), ensure_ascii=False)

    def _mark_stale_workers_offline_json(max_age_seconds: int = 300) -> str:
        if max_age_seconds < 1:
            return _json.dumps({"error": "max_age_seconds 必须 >= 1"}, ensure_ascii=False)
        changed = durable_worker_store.mark_stale_workers_offline(max_age_seconds=max_age_seconds)
        return _json.dumps(
            {"changed_count": len(changed), "workers": [w.to_dict() for w in changed]},
            ensure_ascii=False,
        )

    def _claim_durable_task_json(worker_id: str) -> str:
        worker_id = worker_id.strip()
        if not worker_id:
            return _json.dumps({"error": "worker_id 不能为空"}, ensure_ascii=False)
        worker = durable_worker_store.get_worker(worker_id)
        if worker is None:
            return _json.dumps({"error": f"未找到 worker: {worker_id}"}, ensure_ascii=False)
        if worker.status == WorkerStatus.OFFLINE:
            return _json.dumps({"error": f"worker {worker_id} 已离线，无法认领任务"}, ensure_ascii=False)
        if worker.current_task_id:
            existing_task = durable_task_store.get_task(worker.current_task_id)
            if existing_task:
                return _json.dumps({
                    "claimed": True,
                    "already_assigned": True,
                    "task_id": existing_task.task_id,
                    "task": existing_task.to_dict(),
                }, ensure_ascii=False)
        pending_tasks = [
            t for t in durable_task_store.list_tasks(limit=500)
            if t.status == "pending" and not t.worker_id
        ]
        if not pending_tasks:
            return _json.dumps({"claimed": False}, ensure_ascii=False)
        oldest = sorted(pending_tasks, key=lambda t: t.created_at)[0]
        previous_worker_id_present = bool(oldest.worker_id)
        task = durable_task_store.assign_worker(oldest.task_id, worker_id)
        if task is None:
            return _json.dumps({"error": f"任务分配失败: {oldest.task_id}"}, ensure_ascii=False)
        durable_worker_store.update_status(
            worker_id=worker_id, status=WorkerStatus.ASSIGNED,
            current_task_id=task.task_id,
        )
        try:
            registry.durable_event_store.record(
                event_type=TASK_STATUS_CHANGED,
                task_id=task.task_id,
                worker_id=worker_id,
                summary="task claimed by worker",
                payload={
                    "operation": "claim",
                    "task_id": task.task_id,
                    "worker_id_present": True,
                    "previous_worker_id_present": previous_worker_id_present,
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
        return _json.dumps({
            "claimed": True,
            "task_id": task.task_id,
            "task": task.to_dict(),
        }, ensure_ascii=False)

    def _dispatch_durable_tasks_json(max_assignments: int = 10) -> str:
        max_assignments = max(1, min(max_assignments, 50))
        durable_worker_store.mark_stale_workers_offline()
        all_workers = durable_worker_store.list_workers(limit=200)
        idle_workers = [
            w for w in all_workers
            if w.status == WorkerStatus.IDLE and not w.current_task_id
        ]
        if not idle_workers:
            return _json.dumps({"dispatched": 0, "assignments": []}, ensure_ascii=False)
        pending_tasks = [
            t for t in durable_task_store.list_tasks(limit=500)
            if t.status == "pending" and not t.worker_id
        ]
        if not pending_tasks:
            return _json.dumps({"dispatched": 0, "assignments": []}, ensure_ascii=False)
        pending_tasks.sort(key=lambda t: t.created_at)
        idle_workers.sort(key=lambda w: w.worker_id)
        assignments = []
        for worker, task in zip(idle_workers, pending_tasks):
            if len(assignments) >= max_assignments:
                break
            assigned_task = durable_task_store.assign_worker(task.task_id, worker.worker_id)
            if assigned_task is None:
                continue
            durable_worker_store.update_status(
                worker_id=worker.worker_id,
                status=WorkerStatus.ASSIGNED,
                current_task_id=task.task_id,
            )
            try:
                registry.durable_event_store.record(
                    event_type=TASK_STATUS_CHANGED,
                    task_id=task.task_id,
                    worker_id=worker.worker_id,
                    summary="task auto-dispatched to worker",
                    payload={
                        "operation": "dispatch",
                        "task_id": task.task_id,
                        "worker_id_present": True,
                    },
                    source="registry",
                    severity="info",
                )
            except Exception:
                pass
            assignments.append({
                "worker_id": worker.worker_id,
                "task_id": task.task_id,
                "status": "assigned",
            })
        return _json.dumps(
            {"dispatched": len(assignments), "assignments": assignments},
            ensure_ascii=False,
        )

    registry.register(
        "touch_worker",
        "更新 worker 的 last_seen_at 时间戳，表示 worker 仍然存活。",
        _touch_worker_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {
                    "type": "string",
                    "description": "worker id，例如 worker_1",
                }
            },
            "required": ["worker_id"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "mark_stale_workers_offline",
        "将超过指定时间未心跳的 worker 标记为 offline。返回状态变更的 worker 列表。",
        _mark_stale_workers_offline_json,
        parameters={
            "type": "object",
            "properties": {
                "max_age_seconds": {
                    "type": "integer",
                    "description": "心跳超时阈值（秒），默认 300",
                }
            },
        },
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "claim_durable_task",
        "让已注册且在线的 worker 认领最早的待分配持久任务。返回认领结果。",
        _claim_durable_task_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {
                    "type": "string",
                    "description": "执行认领的 worker id",
                }
            },
            "required": ["worker_id"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "dispatch_durable_tasks",
        "自动将待分配的持久任务派发给空闲 worker。找到最早的 pending 任务和空闲 worker，自动配对分配。返回派发结果摘要。",
        _dispatch_durable_tasks_json,
        parameters={
            "type": "object",
            "properties": {
                "max_assignments": {
                    "type": "integer",
                    "description": "最多派发几个任务，默认 10，上限 50",
                }
            },
        },
        permission=ToolPermission(category="task", risk="write"),
    )

    def _pause_durable_task_json(task_id: str, reason: str = "") -> str:
        existing = durable_task_store.get_task(task_id)
        if existing is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        previous_status = existing.status
        try:
            task = durable_task_store.update_status(task_id, "paused")
        except ValueError as e:
            return _json.dumps({"error": str(e)}, ensure_ascii=False)
        if task.worker_id:
            worker = durable_worker_store.get_worker(task.worker_id)
            if worker and worker.current_task_id == task_id and worker.status != WorkerStatus.OFFLINE:
                try:
                    durable_worker_store.update_status(task.worker_id, WorkerStatus.PAUSED, current_task_id=task_id)
                except Exception:
                    pass
        try:
            registry.durable_event_store.record(
                event_type=TASK_STATUS_CHANGED,
                task_id=task_id,
                worker_id=task.worker_id,
                summary="task paused",
                payload={
                    "operation": "pause",
                    "task_id": task_id,
                    "status": task.status,
                    "previous_status": previous_status,
                    "worker_id_present": bool(task.worker_id),
                    "reason_present": bool(reason.strip()),
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
        return _json.dumps({
            "task_id": task.task_id,
            "status": task.status,
            "previous_status": previous_status,
            "worker_id_present": bool(task.worker_id),
            "reason_present": bool(reason.strip()),
        }, ensure_ascii=False)

    def _resume_durable_task_json(task_id: str) -> str:
        existing = durable_task_store.get_task(task_id)
        if existing is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        if existing.status not in ("paused", "blocked"):
            return _json.dumps({"error": f"无法恢复: 当前状态 {existing.status!r} 不允许 resume，仅支持 paused 或 blocked"}, ensure_ascii=False)
        previous_status = existing.status
        try:
            task = durable_task_store.update_status(task_id, "running")
        except ValueError as e:
            return _json.dumps({"error": str(e)}, ensure_ascii=False)
        if task.worker_id:
            worker = durable_worker_store.get_worker(task.worker_id)
            if worker and worker.current_task_id == task_id and worker.status != WorkerStatus.OFFLINE:
                try:
                    durable_worker_store.update_status(task.worker_id, WorkerStatus.RUNNING, current_task_id=task_id)
                except Exception:
                    pass
        try:
            registry.durable_event_store.record(
                event_type=TASK_STATUS_CHANGED,
                task_id=task_id,
                worker_id=task.worker_id,
                summary="task resumed",
                payload={
                    "operation": "resume",
                    "task_id": task_id,
                    "status": task.status,
                    "previous_status": previous_status,
                    "worker_id_present": bool(task.worker_id),
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
        return _json.dumps({
            "task_id": task.task_id,
            "status": task.status,
            "previous_status": previous_status,
            "worker_id_present": bool(task.worker_id),
        }, ensure_ascii=False)

    def _cancel_durable_task_json(task_id: str, reason: str = "") -> str:
        existing = durable_task_store.get_task(task_id)
        if existing is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        previous_status = existing.status
        try:
            task = durable_task_store.update_status(task_id, "cancelled")
        except ValueError as e:
            return _json.dumps({"error": str(e)}, ensure_ascii=False)
        if task.worker_id:
            worker = durable_worker_store.get_worker(task.worker_id)
            if worker and worker.current_task_id == task_id and worker.status != WorkerStatus.OFFLINE:
                try:
                    durable_worker_store.update_status(task.worker_id, WorkerStatus.IDLE, current_task_id=None)
                except Exception:
                    pass
        try:
            registry.durable_event_store.record(
                event_type=TASK_STATUS_CHANGED,
                task_id=task_id,
                worker_id=task.worker_id,
                summary="task cancelled",
                payload={
                    "operation": "cancel",
                    "task_id": task_id,
                    "status": task.status,
                    "previous_status": previous_status,
                    "worker_id_present": bool(task.worker_id),
                    "reason_present": bool(reason.strip()),
                },
                source="registry",
                severity="warning",
            )
        except Exception:
            pass
        return _json.dumps({
            "task_id": task.task_id,
            "status": task.status,
            "previous_status": previous_status,
            "worker_id_present": bool(task.worker_id),
            "reason_present": bool(reason.strip()),
        }, ensure_ascii=False)

    registry.register(
        "pause_durable_task",
        "暂停一个正在运行的 durable task。仅允许 running -> paused 转换。",
        _pause_durable_task_json,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "durable task id，例如 dtask_1",
                },
                "reason": {
                    "type": "string",
                    "description": "暂停原因（可选，仅记录是否提供，不持久化原文）",
                },
            },
            "required": ["task_id"],
        },
        permission=ToolPermission(category="task", risk="write", requires_confirmation=True),
    )
    registry.register(
        "resume_durable_task",
        "恢复一个暂停或阻塞的 durable task。允许 paused -> running 和 blocked -> running。",
        _resume_durable_task_json,
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
        "cancel_durable_task",
        "取消一个 durable task。允许从 pending、running、paused、blocked 状态取消。",
        _cancel_durable_task_json,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "durable task id，例如 dtask_1",
                },
                "reason": {
                    "type": "string",
                    "description": "取消原因（可选，仅记录是否提供，不持久化原文）",
                },
            },
            "required": ["task_id"],
        },
        permission=ToolPermission(category="task", risk="write", requires_confirmation=True),
    )

    def _add_durable_checkpoint_json(task_id: str, step_id: int = 0, description: str = "", state_summary: str = "") -> str:
        task = durable_task_store.get_task(task_id)
        if task is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        try:
            step_id = max(0, int(step_id))
        except (TypeError, ValueError):
            return _json.dumps({"error": f"step_id 必须为整数: {step_id!r}"}, ensure_ascii=False)
        cp = durable_task_store.add_checkpoint(task_id, {
            "step_id": step_id,
            "state_snapshot": {
                "task_status": task.status,
                "current_step": task.current_step,
                "step_id": step_id,
                "description_present": bool(description.strip()),
                "state_summary_present": bool(state_summary.strip()),
            },
            "description": "",
        })
        if cp is None:
            return _json.dumps({"error": f"创建 checkpoint 失败: {task_id}"}, ensure_ascii=False)
        # Update step checkpoint_ref if step exists
        task = durable_task_store.get_task(task_id)
        if task:
            for step in task.steps:
                if step.id == step_id:
                    step.checkpoint_ref = cp.checkpoint_id
                    durable_task_store.upsert_task(task)
                    break
        try:
            registry.durable_event_store.record(
                event_type=CHECKPOINT_ADDED,
                task_id=task_id,
                checkpoint_id=cp.checkpoint_id,
                summary="checkpoint added",
                payload={
                    "operation": "checkpoint",
                    "checkpoint_id": cp.checkpoint_id,
                    "step_id": step_id,
                    "checkpoint_count": len(task.checkpoints) if task else 0,
                    "description_present": bool(description.strip()),
                    "state_summary_present": bool(state_summary.strip()),
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
        return _json.dumps({
            "task_id": task_id,
            "checkpoint_id": cp.checkpoint_id,
            "step_id": step_id,
            "checkpoint_count": len(task.checkpoints) if task else 0,
            "description_present": bool(description.strip()),
            "state_summary_present": bool(state_summary.strip()),
        }, ensure_ascii=False)

    registry.register(
        "add_durable_checkpoint",
        "为 durable task 创建一个 checkpoint。记录安全元数据，不存储原始目标、步骤文本或敏感内容。",
        _add_durable_checkpoint_json,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "durable task id，例如 dtask_1",
                },
                "step_id": {
                    "type": "integer",
                    "description": "关联的步骤 id，默认 0（不关联特定步骤）",
                },
                "description": {
                    "type": "string",
                    "description": "checkpoint 描述（可选，仅记录是否提供，不存储原文）",
                },
                "state_summary": {
                    "type": "string",
                    "description": "状态摘要（可选，仅记录是否提供，不存储原文）",
                },
            },
            "required": ["task_id"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )

    registry.register(
        "list_tool_permissions",
        "查看所有工具的权限分类和哪些工具需要确认。",
        registry.describe_permissions,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="local", risk="read"),
    )

    return registry
