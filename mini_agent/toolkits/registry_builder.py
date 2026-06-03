import difflib
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
from mini_agent.memory import LongTermMemory, is_sensitive_text
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
from mini_agent.durable_tasks import DurableTaskStore, StepStatus
from mini_agent.durable_workers import DurableWorkerStore, WorkerStatus, WorkspaceLeaseStore
from mini_agent.durable_events import (
    CHECKPOINT_ADDED,
    DurableEventStore,
    FILE_EDIT_BLOCKED,
    FILE_EDIT_ERROR,
    FILE_EDIT_FINISHED,
    FILE_EDIT_STARTED,
    RECOVERY_PLANNED,
    REVIEW_GATE_FINISHED,
    SCHEDULER_DECISION,
    TASK_CREATED,
    TASK_STATUS_CHANGED,
    TASK_RETRIED,
    WORKSPACE_PREPARED,
    WORKSPACE_RELEASED,
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
    workspace_lease_store = WorkspaceLeaseStore(db=db)
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
    registry.workspace_lease_store = workspace_lease_store
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

    def _try_prepare_workspace(worker_id: str, task_id: str) -> dict:
        """Best-effort workspace lease preparation. Never raises."""
        try:
            result = _prepare_worker_workspace_json(worker_id, task_id)
            return _json.loads(result)
        except Exception:
            return {"error": "workspace preparation failed"}

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
                ws = _try_prepare_workspace(worker_id, existing_task.task_id)
                return _json.dumps({
                    "claimed": True,
                    "already_assigned": True,
                    "task_id": existing_task.task_id,
                    "task": existing_task.to_dict(),
                    "workspace": ws,
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
        ws = _try_prepare_workspace(worker_id, task.task_id)
        return _json.dumps({
            "claimed": True,
            "task_id": task.task_id,
            "task": task.to_dict(),
            "workspace": ws,
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
            ws = _try_prepare_workspace(worker.worker_id, task.task_id)
            assignments.append({
                "worker_id": worker.worker_id,
                "task_id": task.task_id,
                "status": "assigned",
                "workspace": ws,
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

    def _prepare_worker_workspace_json(worker_id: str, task_id: str) -> str:
        worker_id = worker_id.strip()
        task_id = task_id.strip()
        if not worker_id:
            return _json.dumps({"error": "worker_id 不能为空"}, ensure_ascii=False)
        if not task_id:
            return _json.dumps({"error": "task_id 不能为空"}, ensure_ascii=False)
        worker = durable_worker_store.get_worker(worker_id)
        if worker is None:
            return _json.dumps({"error": f"未找到 worker: {worker_id}"}, ensure_ascii=False)
        if worker.status == WorkerStatus.OFFLINE:
            return _json.dumps({"error": f"worker {worker_id} 已离线，无法准备 workspace"}, ensure_ascii=False)
        if worker.status == WorkerStatus.IDLE:
            return _json.dumps({"error": f"worker {worker_id} 空闲中，需要先分配任务才能准备 workspace"}, ensure_ascii=False)
        if worker.current_task_id != task_id:
            return _json.dumps({"error": f"worker {worker_id} 当前未执行 task {task_id}"}, ensure_ascii=False)
        task = durable_task_store.get_task(task_id)
        if task is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        if task.worker_id != worker_id:
            return _json.dumps({"error": f"task {task_id} 未分配给 worker {worker_id}"}, ensure_ascii=False)
        existing_worker_lease = workspace_lease_store.get_lease_by_worker(worker_id)
        if existing_worker_lease:
            if existing_worker_lease.task_id == task_id:
                return _json.dumps({
                    "reused": True,
                    "lease_id": existing_worker_lease.lease_id,
                    "worker_id": worker_id,
                    "task_id": task_id,
                    "workspace_path": existing_worker_lease.workspace_path,
                    "created_at": existing_worker_lease.created_at,
                }, ensure_ascii=False)
            return _json.dumps({
                "error": f"worker {worker_id} 已有 workspace lease",
                "existing_lease_id": existing_worker_lease.lease_id,
            }, ensure_ascii=False)
        existing_task_lease = workspace_lease_store.get_lease_by_task(task_id)
        if existing_task_lease:
            return _json.dumps({
                "error": f"task {task_id} 已有 workspace lease",
                "existing_lease_id": existing_task_lease.lease_id,
            }, ensure_ascii=False)
        ws_path = str(root / ".workspaces" / f"{worker_id}_{task_id}")
        try:
            Path(ws_path).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return _json.dumps({"error": f"workspace 目录创建失败: {ws_path}"}, ensure_ascii=False)
        lease = workspace_lease_store.create_lease(
            worker_id=worker_id,
            task_id=task_id,
            workspace_path=ws_path,
        )
        try:
            registry.durable_event_store.record(
                event_type=WORKSPACE_PREPARED,
                task_id=task_id,
                worker_id=worker_id,
                summary="workspace prepared for worker",
                payload={
                    "operation": "prepare",
                    "lease_id": lease.lease_id,
                    "worker_id": worker_id,
                    "task_id": task_id,
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
        return _json.dumps(lease.to_dict(), ensure_ascii=False)

    def _release_worker_workspace_json(worker_id: str) -> str:
        worker_id = worker_id.strip()
        if not worker_id:
            return _json.dumps({"error": "worker_id 不能为空"}, ensure_ascii=False)
        worker = durable_worker_store.get_worker(worker_id)
        if worker is None:
            return _json.dumps({"error": f"未找到 worker: {worker_id}"}, ensure_ascii=False)
        lease = workspace_lease_store.get_lease_by_worker(worker_id)
        if lease is None:
            return _json.dumps({"released": False, "worker_id": worker_id}, ensure_ascii=False)
        lease_id = lease.lease_id
        workspace_lease_store.release_lease(lease_id)
        try:
            registry.durable_event_store.record(
                event_type=WORKSPACE_RELEASED,
                worker_id=worker_id,
                summary="workspace lease released",
                payload={
                    "operation": "release",
                    "lease_id": lease_id,
                    "worker_id": worker_id,
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
        return _json.dumps({
            "released": True,
            "lease_id": lease_id,
            "worker_id": worker_id,
        }, ensure_ascii=False)

    registry.register(
        "prepare_worker_workspace",
        "为已分配任务的 worker 准备隔离工作区目录并创建 lease。worker 必须在线且 task 已分配给该 worker。",
        _prepare_worker_workspace_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {
                    "type": "string",
                    "description": "worker id",
                },
                "task_id": {
                    "type": "string",
                    "description": "durable task id",
                },
            },
            "required": ["worker_id", "task_id"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "release_worker_workspace",
        "释放 worker 的 workspace lease。不删除文件系统目录。",
        _release_worker_workspace_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {
                    "type": "string",
                    "description": "worker id",
                }
            },
            "required": ["worker_id"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )

    def _resolve_and_validate_lease(worker_id: str, task_id: str):
        """Resolve and validate a workspace lease for worker+task.

        Returns (lease, None) on success or (None, error_dict) on failure.
        """
        worker_id = worker_id.strip()
        task_id = task_id.strip()
        if not worker_id:
            return None, {"error": "worker_id 不能为空"}
        if not task_id:
            return None, {"error": "task_id 不能为空"}
        worker = durable_worker_store.get_worker(worker_id)
        if worker is None:
            return None, {"error": f"未找到 worker: {worker_id}"}
        if worker.status == WorkerStatus.OFFLINE:
            return None, {"error": f"worker {worker_id} 已离线，无法使用 workspace"}
        if worker.status == WorkerStatus.IDLE:
            return None, {"error": f"worker {worker_id} 空闲中，无法使用 workspace"}
        if worker.current_task_id != task_id:
            return None, {"error": f"worker {worker_id} 当前未执行 task {task_id}"}
        task = durable_task_store.get_task(task_id)
        if task is None:
            return None, {"error": f"未找到 durable task: {task_id}"}
        if task.worker_id != worker_id:
            return None, {"error": f"task {task_id} 未分配给 worker {worker_id}"}
        lease = workspace_lease_store.get_lease_by_worker(worker_id)
        if lease is None:
            return None, {"error": f"worker {worker_id} 无 workspace lease"}
        if lease.task_id != task_id:
            return None, {"error": f"worker {worker_id} 的 lease 属于 task {lease.task_id}，非 {task_id}"}
        return lease, None

    def _get_worker_workspace_json(worker_id: str, task_id: str) -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        return _json.dumps(lease.to_dict(), ensure_ascii=False)

    def _validate_worker_workspace_path_json(worker_id: str, task_id: str, path: str) -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        path = path.strip()
        if not path:
            return _json.dumps({"error": "path 不能为空"}, ensure_ascii=False)
        ws_root = Path(lease.workspace_path)
        try:
            resolved = Path(path).resolve()
        except OSError:
            return _json.dumps({"error": f"path 解析失败: {path}"}, ensure_ascii=False)
        try:
            resolved.relative_to(ws_root.resolve())
        except ValueError:
            return _json.dumps({
                "error": f"path 不在 workspace 内",
                "path": path,
                "workspace_path": lease.workspace_path,
            }, ensure_ascii=False)
        return _json.dumps({
            "valid": True,
            "path": str(resolved),
            "workspace_path": lease.workspace_path,
            "lease_id": lease.lease_id,
        }, ensure_ascii=False)

    registry.register(
        "get_worker_workspace",
        "获取 worker 的 workspace lease 信息。需要 worker 当前正在执行指定 task。",
        _get_worker_workspace_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {
                    "type": "string",
                    "description": "worker id",
                },
                "task_id": {
                    "type": "string",
                    "description": "durable task id",
                },
            },
            "required": ["worker_id", "task_id"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )
    registry.register(
        "validate_worker_workspace_path",
        "校验目标 path 是否在 worker 的 workspace lease 目录内。防止 path traversal 和绝对路径逃逸。",
        _validate_worker_workspace_path_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {
                    "type": "string",
                    "description": "worker id",
                },
                "task_id": {
                    "type": "string",
                    "description": "durable task id",
                },
                "path": {
                    "type": "string",
                    "description": "要校验的文件路径",
                },
            },
            "required": ["worker_id", "task_id", "path"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )

    from mini_agent.toolkits.workspace import DENIED_FILE_NAMES, DENIED_DIR_NAMES, MAX_FILE_BYTES

    def _resolve_workspace_path(lease, path: str):
        """Resolve a path under a workspace lease, with safety checks.

        Returns (resolved_path, None) on success or (None, error_dict) on failure.
        """
        path = path.strip()
        if not path:
            return None, {"error": "path 不能为空"}
        ws_root = Path(lease.workspace_path).resolve()
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                resolved = candidate.resolve()
            except OSError:
                return None, {"error": f"path 解析失败: {path}"}
        else:
            try:
                resolved = (ws_root / candidate).resolve()
            except OSError:
                return None, {"error": f"path 解析失败: {path}"}
        try:
            resolved.relative_to(ws_root)
        except ValueError:
            return None, {
                "error": "path 不在 workspace 内",
                "path": path,
                "workspace_path": lease.workspace_path,
            }
        rel_parts = resolved.relative_to(ws_root).parts
        if any(part in DENIED_FILE_NAMES for part in rel_parts):
            return None, {"error": "path 包含禁止访问的敏感文件名"}
        if any(part in DENIED_DIR_NAMES for part in rel_parts):
            return None, {"error": f"path 包含禁止访问的目录"}
        return resolved, None

    def _list_worker_workspace_files_json(worker_id: str, task_id: str, max_files: int = 50) -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        try:
            max_files = max(1, min(int(max_files or 50), 200))
        except (ValueError, TypeError):
            return _json.dumps({"error": "max_files 必须是整数"}, ensure_ascii=False)
        ws_root = Path(lease.workspace_path).resolve()
        files = []
        try:
            for target in sorted(ws_root.rglob("*")):
                if len(files) >= max_files:
                    break
                if not target.is_file():
                    continue
                # Resolve symlinks and ensure the real target stays inside workspace
                try:
                    resolved = target.resolve()
                except OSError:
                    continue
                try:
                    resolved.relative_to(ws_root)
                except ValueError:
                    continue
                rel = target.relative_to(ws_root)
                if resolved.name in DENIED_FILE_NAMES or target.name in DENIED_FILE_NAMES:
                    continue
                if any(part in DENIED_FILE_NAMES or part in DENIED_DIR_NAMES for part in rel.parts):
                    continue
                # Also check resolved target path for denied directories
                try:
                    resolved_rel = resolved.relative_to(ws_root)
                    if any(part in DENIED_FILE_NAMES or part in DENIED_DIR_NAMES for part in resolved_rel.parts):
                        continue
                except ValueError:
                    continue
                files.append(rel.as_posix())
        except OSError:
            return _json.dumps({"error": "workspace 目录读取失败"}, ensure_ascii=False)
        return _json.dumps({
            "files": files,
            "count": len(files),
            "workspace_path": lease.workspace_path,
            "lease_id": lease.lease_id,
        }, ensure_ascii=False)

    def _read_worker_workspace_file_json(worker_id: str, task_id: str, path: str) -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        resolved, err = _resolve_workspace_path(lease, path)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        if not resolved.exists():
            return _json.dumps({"error": f"文件不存在: {path}"}, ensure_ascii=False)
        if not resolved.is_file():
            return _json.dumps({"error": f"不是文件: {path}"}, ensure_ascii=False)
        if resolved.stat().st_size > MAX_FILE_BYTES:
            return _json.dumps({"error": f"文件过大: 最大支持 {MAX_FILE_BYTES} bytes"}, ensure_ascii=False)
        try:
            content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return _json.dumps({"error": "只支持 UTF-8 文本文件"}, ensure_ascii=False)
        except OSError as e:
            return _json.dumps({"error": f"读取失败"}, ensure_ascii=False)
        rel = resolved.relative_to(Path(lease.workspace_path).resolve()).as_posix()
        return _json.dumps({
            "content": content,
            "path": rel,
            "size": len(content),
            "workspace_path": lease.workspace_path,
            "lease_id": lease.lease_id,
        }, ensure_ascii=False)

    def _preview_worker_workspace_write_json(worker_id: str, task_id: str, path: str, content: str, context_lines: int = 3) -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        resolved, err = _resolve_workspace_path(lease, path)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > MAX_FILE_BYTES:
            return _json.dumps({"error": f"内容过大: 最大支持 {MAX_FILE_BYTES} bytes"}, ensure_ascii=False)
        try:
            context_lines = max(0, min(int(context_lines or 3), 20))
        except (ValueError, TypeError):
            return _json.dumps({"error": "context_lines 必须是整数"}, ensure_ascii=False)
        current = ""
        if resolved.exists():
            if not resolved.is_file():
                return _json.dumps({"error": f"不是文件: {path}"}, ensure_ascii=False)
            if resolved.stat().st_size > MAX_FILE_BYTES:
                return _json.dumps({"error": f"文件过大: 最大支持 {MAX_FILE_BYTES} bytes"}, ensure_ascii=False)
            try:
                current = resolved.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return _json.dumps({"error": "只支持 UTF-8 文本文件"}, ensure_ascii=False)
            except OSError:
                return _json.dumps({"error": "读取失败"}, ensure_ascii=False)
        old_lines = current.splitlines(keepends=True)
        new_lines = content.splitlines(keepends=True)
        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{path}", tofile=f"b/{path}",
            n=context_lines,
        ))
        rel = resolved.relative_to(Path(lease.workspace_path).resolve()).as_posix()
        return _json.dumps({
            "preview": "".join(diff),
            "path": rel,
            "current_size": len(current),
            "new_size": content_bytes,
            "will_create": not resolved.exists(),
            "workspace_path": lease.workspace_path,
            "lease_id": lease.lease_id,
        }, ensure_ascii=False)

    registry.register(
        "list_worker_workspace_files",
        "列出 worker workspace 中的文件（相对路径）。只列出非敏感文件。",
        _list_worker_workspace_files_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "max_files": {"type": "integer", "description": "最大文件数，默认 50，上限 200"},
            },
            "required": ["worker_id", "task_id"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )
    registry.register(
        "read_worker_workspace_file",
        "读取 worker workspace 中的一个文件。只支持 UTF-8 文本。",
        _read_worker_workspace_file_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "path": {"type": "string", "description": "文件路径（相对于 workspace 或绝对路径）"},
            },
            "required": ["worker_id", "task_id", "path"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )
    registry.register(
        "preview_worker_workspace_write",
        "预览写入 worker workspace 文件的 diff。不实际写入。",
        _preview_worker_workspace_write_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要写入的内容"},
                "context_lines": {"type": "integer", "description": "diff 上下文行数，默认 3"},
            },
            "required": ["worker_id", "task_id", "path", "content"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )

    def _record_worker_file_edit_event(
        event_type: str,
        path: str,
        operation: str,
        worker_id: str = "",
        task_id: str = "",
        lease_id: str = "",
        status: str = "",
        error: str = "",
        bytes_before: int = None,
        bytes_after: int = None,
    ) -> None:
        payload = {
            "path": path,
            "operation": operation,
            "worker_id": worker_id,
            "task_id": task_id,
            "lease_id": lease_id,
            "status": status,
        }
        if error:
            payload["error"] = error
        if bytes_before is not None:
            payload["bytes_before"] = bytes_before
        if bytes_after is not None:
            payload["bytes_after"] = bytes_after
        severity = "warning" if event_type in (FILE_EDIT_BLOCKED, FILE_EDIT_ERROR) else "info"
        try:
            registry.durable_event_store.record(
                event_type=event_type,
                task_id=task_id,
                worker_id=worker_id,
                source="worker_workspace",
                summary=f"{event_type}: {path} ({operation})",
                severity=severity,
                payload=payload,
            )
        except Exception:
            pass

    def _write_worker_workspace_file_json(worker_id: str, task_id: str, path: str, content: str, reason: str = "") -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        resolved, err = _resolve_workspace_path(lease, path)
        if err:
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "write",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="denied_path",
            )
            return _json.dumps(err, ensure_ascii=False)
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > MAX_FILE_BYTES:
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "write",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="file_too_large",
            )
            return _json.dumps({"error": f"内容过大: 最大支持 {MAX_FILE_BYTES} bytes"}, ensure_ascii=False)
        if resolved.is_symlink():
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "write",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="symlink",
            )
            return _json.dumps({"error": "不能写入符号链接"}, ensure_ascii=False)
        bytes_before = 0
        will_create = not resolved.exists()
        if resolved.exists():
            if not resolved.is_file():
                _record_worker_file_edit_event(
                    FILE_EDIT_BLOCKED, path, "write",
                    worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                    status="blocked", error="not_file",
                )
                return _json.dumps({"error": f"不是文件: {path}"}, ensure_ascii=False)
            bytes_before = resolved.stat().st_size
        _record_worker_file_edit_event(
            FILE_EDIT_STARTED, path, "write",
            worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
            status="started", bytes_before=bytes_before, bytes_after=content_bytes,
        )
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
        except OSError:
            _record_worker_file_edit_event(
                FILE_EDIT_ERROR, path, "write",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="error", error="write_failed",
            )
            return _json.dumps({"error": "写入失败"}, ensure_ascii=False)
        _record_worker_file_edit_event(
            FILE_EDIT_FINISHED, path, "write",
            worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
            status="finished", bytes_before=bytes_before, bytes_after=content_bytes,
        )
        rel = resolved.relative_to(Path(lease.workspace_path).resolve()).as_posix()
        return _json.dumps({
            "operation": "write",
            "path": rel,
            "bytes_before": bytes_before,
            "bytes_after": content_bytes,
            "created": will_create,
            "changed": True,
            "lease_id": lease.lease_id,
            "worker_id": worker_id,
            "task_id": task_id,
        }, ensure_ascii=False)

    def _replace_worker_workspace_file_json(worker_id: str, task_id: str, path: str, old_text: str, new_text: str, reason: str = "") -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        resolved, err = _resolve_workspace_path(lease, path)
        if err:
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "replace",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="denied_path",
            )
            return _json.dumps(err, ensure_ascii=False)
        if not old_text:
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "replace",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="empty_old_text",
            )
            return _json.dumps({"error": "old_text 不能为空"}, ensure_ascii=False)
        if not resolved.exists():
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "replace",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="file_not_found",
            )
            return _json.dumps({"error": f"文件不存在: {path}"}, ensure_ascii=False)
        if not resolved.is_file():
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "replace",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="not_file",
            )
            return _json.dumps({"error": f"不是文件: {path}"}, ensure_ascii=False)
        if resolved.stat().st_size > MAX_FILE_BYTES:
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "replace",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="file_too_large",
            )
            return _json.dumps({"error": f"文件过大: 最大支持 {MAX_FILE_BYTES} bytes"}, ensure_ascii=False)
        try:
            current = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "replace",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="not_utf8",
            )
            return _json.dumps({"error": "只支持 UTF-8 文本文件"}, ensure_ascii=False)
        except OSError:
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "replace",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="read_failed",
            )
            return _json.dumps({"error": "读取失败"}, ensure_ascii=False)
        if old_text not in current:
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "replace",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="text_not_found",
            )
            return _json.dumps({"error": "没有找到要替换的文本"}, ensure_ascii=False)
        updated = current.replace(old_text, new_text, 1)
        bytes_before = len(current.encode("utf-8"))
        bytes_after = len(updated.encode("utf-8"))
        if bytes_after > MAX_FILE_BYTES:
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, path, "replace",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="file_too_large",
            )
            return _json.dumps({"error": f"替换后内容过大: 最大支持 {MAX_FILE_BYTES} bytes"}, ensure_ascii=False)
        _record_worker_file_edit_event(
            FILE_EDIT_STARTED, path, "replace",
            worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
            status="started", bytes_before=bytes_before, bytes_after=bytes_after,
        )
        try:
            resolved.write_text(updated, encoding="utf-8")
        except OSError:
            _record_worker_file_edit_event(
                FILE_EDIT_ERROR, path, "replace",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="error", error="write_failed",
            )
            return _json.dumps({"error": "写入失败"}, ensure_ascii=False)
        _record_worker_file_edit_event(
            FILE_EDIT_FINISHED, path, "replace",
            worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
            status="finished", bytes_before=bytes_before, bytes_after=bytes_after,
        )
        rel = resolved.relative_to(Path(lease.workspace_path).resolve()).as_posix()
        return _json.dumps({
            "operation": "replace",
            "path": rel,
            "bytes_before": bytes_before,
            "bytes_after": bytes_after,
            "created": False,
            "changed": True,
            "lease_id": lease.lease_id,
            "worker_id": worker_id,
            "task_id": task_id,
        }, ensure_ascii=False)

    def _apply_worker_workspace_patch_json(worker_id: str, task_id: str, patch: str, reason: str = "") -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        if not patch.strip():
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, "", "patch",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="empty_patch",
            )
            return _json.dumps({"error": "patch 不能为空"}, ensure_ascii=False)
        if len(patch.encode("utf-8")) > MAX_FILE_BYTES:
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, "", "patch",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="patch_too_large",
            )
            return _json.dumps({"error": f"patch 过大: 最大支持 {MAX_FILE_BYTES} bytes"}, ensure_ascii=False)
        ws_root = Path(lease.workspace_path).resolve()
        ws = WorkspaceFiles(
            root=ws_root,
            max_file_bytes=MAX_FILE_BYTES,
            require_confirmation=False,
            event_store=None,
        )
        parsed = ws._parse_multi_file_patch(patch)
        if isinstance(parsed, str):
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, "", "patch",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="patch_parse_error",
            )
            return _json.dumps({"error": parsed}, ensure_ascii=False)
        results = []
        for rel_path, hunks in parsed:
            resolved, err = _resolve_workspace_path(lease, rel_path)
            if err:
                _record_worker_file_edit_event(
                    FILE_EDIT_BLOCKED, rel_path, "patch",
                    worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                    status="blocked", error="denied_path",
                )
                return _json.dumps(err, ensure_ascii=False)
            if not resolved.exists():
                _record_worker_file_edit_event(
                    FILE_EDIT_BLOCKED, rel_path, "patch",
                    worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                    status="blocked", error="file_not_found",
                )
                return _json.dumps({"error": f"文件不存在: {rel_path}"}, ensure_ascii=False)
            if not resolved.is_file():
                _record_worker_file_edit_event(
                    FILE_EDIT_BLOCKED, rel_path, "patch",
                    worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                    status="blocked", error="not_file",
                )
                return _json.dumps({"error": f"不是文件: {rel_path}"}, ensure_ascii=False)
            if resolved.stat().st_size > MAX_FILE_BYTES:
                _record_worker_file_edit_event(
                    FILE_EDIT_BLOCKED, rel_path, "patch",
                    worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                    status="blocked", error="file_too_large",
                )
                return _json.dumps({"error": f"文件过大: {rel_path}"}, ensure_ascii=False)
            try:
                current = resolved.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                _record_worker_file_edit_event(
                    FILE_EDIT_BLOCKED, rel_path, "patch",
                    worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                    status="blocked", error="not_utf8",
                )
                return _json.dumps({"error": f"只支持 UTF-8 文本文件: {rel_path}"}, ensure_ascii=False)
            except OSError:
                _record_worker_file_edit_event(
                    FILE_EDIT_BLOCKED, rel_path, "patch",
                    worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                    status="blocked", error="read_failed",
                )
                return _json.dumps({"error": f"读取失败: {rel_path}"}, ensure_ascii=False)
            ok, applied = ws._apply_hunks(current, hunks)
            if not ok:
                _record_worker_file_edit_event(
                    FILE_EDIT_BLOCKED, rel_path, "patch",
                    worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                    status="blocked", error="patch_context_mismatch",
                )
                return _json.dumps({"error": applied}, ensure_ascii=False)
            if len(applied.encode("utf-8")) > MAX_FILE_BYTES:
                _record_worker_file_edit_event(
                    FILE_EDIT_BLOCKED, rel_path, "patch",
                    worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                    status="blocked", error="file_too_large",
                )
                return _json.dumps({"error": f"patch 后文件过大: {rel_path}"}, ensure_ascii=False)
            results.append((rel_path, resolved, current, applied))
        if not results:
            _record_worker_file_edit_event(
                FILE_EDIT_BLOCKED, "", "patch",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="blocked", error="empty_patch",
            )
            return _json.dumps({"error": "patch 没有变化"}, ensure_ascii=False)
        written = []
        try:
            for rel_path, resolved, current, updated in results:
                bytes_before = len(current.encode("utf-8"))
                bytes_after = len(updated.encode("utf-8"))
                _record_worker_file_edit_event(
                    FILE_EDIT_STARTED, rel_path, "patch",
                    worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                    status="started", bytes_before=bytes_before, bytes_after=bytes_after,
                )
                written.append((rel_path, resolved, current, bytes_before, bytes_after))
                resolved.write_text(updated, encoding="utf-8")
        except OSError:
            for rel_path, resolved, original, _bb, _ba in written:
                try:
                    resolved.write_text(original, encoding="utf-8")
                except OSError:
                    pass
            _record_worker_file_edit_event(
                FILE_EDIT_ERROR, rel_path, "patch",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="error", error="patch_write_failed_rolled_back",
            )
            return _json.dumps({"error": "patch 写入失败，已回滚"}, ensure_ascii=False)
        for rel_path, _resolved, _current, bytes_before, bytes_after in written:
            _record_worker_file_edit_event(
                FILE_EDIT_FINISHED, rel_path, "patch",
                worker_id=worker_id, task_id=task_id, lease_id=lease.lease_id,
                status="finished", bytes_before=bytes_before, bytes_after=bytes_after,
            )
        return _json.dumps({
            "operation": "patch",
            "files": [rel for rel, *_ in written],
            "file_count": len(written),
            "changed": True,
            "lease_id": lease.lease_id,
            "worker_id": worker_id,
            "task_id": task_id,
        }, ensure_ascii=False)

    registry.register(
        "write_worker_workspace_file",
        "写入文件到 worker workspace。只写入 lease 内的非敏感文件。",
        _write_worker_workspace_file_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "path": {"type": "string", "description": "文件路径（相对于 workspace 或绝对路径）"},
                "content": {"type": "string", "description": "要写入的内容"},
                "reason": {"type": "string", "description": "写入原因"},
            },
            "required": ["worker_id", "task_id", "path", "content"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "replace_worker_workspace_file",
        "替换 worker workspace 文件中的文本。只替换第一次出现。",
        _replace_worker_workspace_file_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "path": {"type": "string", "description": "文件路径"},
                "old_text": {"type": "string", "description": "要替换的文本"},
                "new_text": {"type": "string", "description": "替换后的文本"},
                "reason": {"type": "string", "description": "替换原因"},
            },
            "required": ["worker_id", "task_id", "path", "old_text", "new_text"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "apply_worker_workspace_patch",
        "对 worker workspace 文件应用 unified diff patch。",
        _apply_worker_workspace_patch_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "patch": {"type": "string", "description": "unified diff patch"},
                "reason": {"type": "string", "description": "应用原因"},
            },
            "required": ["worker_id", "task_id", "patch"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )

    def _safe_read_file_content(file_path: Path):
        """Read a file with size/binary/encoding checks.

        Returns (content, metadata_dict) on success or (None, metadata_dict) on skip/error.
        """
        if not file_path.exists():
            return None, {"exists": False}
        if not file_path.is_file():
            return None, {"exists": True, "is_file": False}
        size = file_path.stat().st_size
        if size > MAX_FILE_BYTES:
            return None, {"exists": True, "is_file": True, "size": size, "oversized": True}
        try:
            content = file_path.read_text(encoding="utf-8")
            return content, {"exists": True, "is_file": True, "size": size, "text": True}
        except UnicodeDecodeError:
            return None, {"exists": True, "is_file": True, "size": size, "binary": True}
        except OSError:
            return None, {"exists": True, "is_file": True, "read_error": True}

    def _has_denied_workspace_part(parts) -> bool:
        return any(part in DENIED_FILE_NAMES or part in DENIED_DIR_NAMES for part in parts)

    def _safe_project_path_for_worker_export(project_root: Path, project_path: Path):
        try:
            project_rel = project_path.relative_to(project_root)
        except ValueError:
            return False, "project_path_escape"
        if _has_denied_workspace_part(project_rel.parts):
            return False, "project_sensitive_path"
        try:
            resolved = project_path.resolve()
            resolved_rel = resolved.relative_to(project_root)
        except OSError:
            return False, "project_path_resolve_error"
        except ValueError:
            return False, "project_symlink_escape"
        if _has_denied_workspace_part(resolved_rel.parts):
            return False, "project_sensitive_path"
        return True, ""

    def _append_worker_patch_if_bounded(patches, skipped, patch_entry, total_patch_bytes: int):
        patch_text = patch_entry.get("patch", "")
        patch_bytes = len(patch_text.encode("utf-8"))
        rel_posix = patch_entry.get("path", "")
        if patch_bytes > MAX_FILE_BYTES:
            skipped.append({"path": rel_posix, "reason": "patch_too_large"})
            return total_patch_bytes, False, False
        if total_patch_bytes + patch_bytes > MAX_FILE_BYTES:
            skipped.append({"path": rel_posix, "reason": "patch_budget_exceeded"})
            return total_patch_bytes, False, True
        patches.append(patch_entry)
        return total_patch_bytes + patch_bytes, True, False

    def _summarize_worker_workspace_changes_json(worker_id: str, task_id: str, max_files: int = 50) -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        try:
            max_files = max(1, min(int(max_files or 50), 200))
        except (ValueError, TypeError):
            return _json.dumps({"error": "max_files 必须是整数"}, ensure_ascii=False)
        ws_root = Path(lease.workspace_path).resolve()
        project_root = root.resolve()
        files = []
        try:
            for target in sorted(ws_root.rglob("*")):
                if len(files) >= max_files:
                    break
                if not target.is_file():
                    continue
                try:
                    resolved_target = target.resolve()
                except OSError:
                    continue
                try:
                    resolved_target.relative_to(ws_root)
                except ValueError:
                    continue
                rel = target.relative_to(ws_root)
                if _has_denied_workspace_part(rel.parts):
                    continue
                try:
                    resolved_rel = resolved_target.relative_to(ws_root)
                    if _has_denied_workspace_part(resolved_rel.parts):
                        continue
                except ValueError:
                    continue
                rel_posix = rel.as_posix()
                worker_content, worker_meta = _safe_read_file_content(target)
                if worker_meta.get("oversized") or worker_meta.get("binary") or worker_meta.get("read_error") or not worker_meta.get("text"):
                    if worker_meta.get("oversized"):
                        reason = "worker_oversized"
                    elif worker_meta.get("binary"):
                        reason = "worker_binary"
                    else:
                        reason = "worker_read_error"
                    files.append({
                        "path": rel_posix,
                        "status": "skipped",
                        "reason": reason,
                        "worker": worker_meta,
                    })
                    continue
                proj_path = project_root / rel
                project_safe, project_reason = _safe_project_path_for_worker_export(project_root, proj_path)
                if not project_safe:
                    files.append({
                        "path": rel_posix,
                        "status": "skipped",
                        "reason": project_reason,
                        "worker": worker_meta,
                    })
                    continue
                if not proj_path.exists():
                    files.append({
                        "path": rel_posix,
                        "status": "created",
                        "worker": worker_meta,
                        "project": {"exists": False},
                    })
                    continue
                if not proj_path.is_file():
                    files.append({
                        "path": rel_posix,
                        "status": "skipped",
                        "reason": "project_not_file",
                        "worker": worker_meta,
                    })
                    continue
                proj_size = proj_path.stat().st_size
                if proj_size > MAX_FILE_BYTES:
                    files.append({
                        "path": rel_posix,
                        "status": "skipped",
                        "reason": "project_oversized",
                        "worker": worker_meta,
                        "project": {"exists": True, "size": proj_size, "oversized": True},
                    })
                    continue
                try:
                    proj_content = proj_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    files.append({
                        "path": rel_posix,
                        "status": "skipped",
                        "reason": "project_binary",
                        "worker": worker_meta,
                        "project": {"exists": True, "size": proj_size, "binary": True},
                    })
                    continue
                except OSError:
                    files.append({
                        "path": rel_posix,
                        "status": "skipped",
                        "reason": "project_read_error",
                        "worker": worker_meta,
                    })
                    continue
                file_status = "same" if worker_content == proj_content else "modified"
                files.append({
                    "path": rel_posix,
                    "status": file_status,
                    "worker": {"exists": True, "size": len(worker_content.encode("utf-8")), "text": True},
                    "project": {"exists": True, "size": len(proj_content.encode("utf-8")), "text": True},
                })
        except OSError:
            return _json.dumps({"error": "workspace 目录读取失败"}, ensure_ascii=False)
        created = sum(1 for f in files if f.get("status") == "created")
        modified = sum(1 for f in files if f.get("status") == "modified")
        same = sum(1 for f in files if f.get("status") == "same")
        skipped = sum(1 for f in files if f.get("status") == "skipped")
        return _json.dumps({
            "files": files,
            "count": len(files),
            "created": created,
            "modified": modified,
            "same": same,
            "skipped": skipped,
            "workspace_path": lease.workspace_path,
            "lease_id": lease.lease_id,
            "worker_id": worker_id,
            "task_id": task_id,
        }, ensure_ascii=False)

    def _export_worker_workspace_patch_json(worker_id: str, task_id: str, path: str = "", max_files: int = 50, context_lines: int = 3) -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        ws_root = Path(lease.workspace_path).resolve()
        project_root = root.resolve()
        try:
            context_lines = max(0, min(int(context_lines or 3), 20))
        except (ValueError, TypeError):
            return _json.dumps({"error": "context_lines 必须是整数"}, ensure_ascii=False)
        if path.strip():
            resolved, err = _resolve_workspace_path(lease, path)
            if err:
                return _json.dumps(err, ensure_ascii=False)
            rel = resolved.relative_to(ws_root)
            rel_posix = rel.as_posix()
            worker_content, worker_meta = _safe_read_file_content(resolved)
            proj_path = project_root / rel
            project_safe, project_reason = _safe_project_path_for_worker_export(project_root, proj_path)
            if not project_safe:
                return _json.dumps({"error": f"project path 不安全: {project_reason}"}, ensure_ascii=False)
            proj_content, proj_meta = _safe_read_file_content(proj_path)
            if worker_meta.get("oversized"):
                return _json.dumps({"error": f"worker 文件过大: {rel_posix}"}, ensure_ascii=False)
            if worker_meta.get("binary"):
                return _json.dumps({"error": f"worker 文件是二进制: {rel_posix}"}, ensure_ascii=False)
            if worker_meta.get("read_error"):
                return _json.dumps({"error": f"worker 文件读取失败: {rel_posix}"}, ensure_ascii=False)
            if not worker_meta.get("exists"):
                return _json.dumps({"error": f"worker 文件不存在: {rel_posix}"}, ensure_ascii=False)
            if not worker_meta.get("text"):
                return _json.dumps({"error": f"worker 文件不可读: {rel_posix}"}, ensure_ascii=False)
            if proj_meta.get("oversized"):
                return _json.dumps({"error": f"project 文件过大: {rel_posix}"}, ensure_ascii=False)
            if proj_meta.get("binary"):
                return _json.dumps({"error": f"project 文件是二进制: {rel_posix}"}, ensure_ascii=False)
            if proj_meta.get("read_error"):
                return _json.dumps({"error": f"project 文件读取失败: {rel_posix}"}, ensure_ascii=False)
            if not proj_meta.get("exists"):
                old_lines = "".splitlines(keepends=True)
                new_lines = worker_content.splitlines(keepends=True)
                diff = list(difflib.unified_diff(
                    old_lines, new_lines,
                    fromfile=f"/dev/null", tofile=f"b/{rel_posix}",
                    n=context_lines,
                ))
                diff_text = "".join(diff)
                if len(diff_text.encode("utf-8")) > MAX_FILE_BYTES:
                    return _json.dumps({"error": f"patch 过大: {rel_posix}"}, ensure_ascii=False)
                return _json.dumps({
                    "patch": diff_text,
                    "path": rel_posix,
                    "status": "created",
                    "worker_bytes": len(worker_content.encode("utf-8")),
                    "project_bytes": 0,
                    "has_changes": True,
                    "workspace_path": lease.workspace_path,
                    "lease_id": lease.lease_id,
                    "worker_id": worker_id,
                    "task_id": task_id,
                }, ensure_ascii=False)
            if not proj_meta.get("text"):
                return _json.dumps({"error": f"project 文件不可读: {rel_posix}"}, ensure_ascii=False)
            old_lines = proj_content.splitlines(keepends=True)
            new_lines = worker_content.splitlines(keepends=True)
            diff = list(difflib.unified_diff(
                old_lines, new_lines,
                fromfile=f"a/{rel_posix}", tofile=f"b/{rel_posix}",
                n=context_lines,
            ))
            diff_text = "".join(diff)
            if len(diff_text.encode("utf-8")) > MAX_FILE_BYTES:
                return _json.dumps({"error": f"patch 过大: {rel_posix}"}, ensure_ascii=False)
            has_changes = worker_content != proj_content
            return _json.dumps({
                "patch": diff_text,
                "path": rel_posix,
                "status": "modified" if has_changes else "same",
                "worker_bytes": len(worker_content.encode("utf-8")),
                "project_bytes": len(proj_content.encode("utf-8")),
                "has_changes": has_changes,
                "workspace_path": lease.workspace_path,
                "lease_id": lease.lease_id,
                "worker_id": worker_id,
                "task_id": task_id,
            }, ensure_ascii=False)
        try:
            max_files = max(1, min(int(max_files or 50), 200))
        except (ValueError, TypeError):
            return _json.dumps({"error": "max_files 必须是整数"}, ensure_ascii=False)
        patches = []
        skipped = []
        total_patch_bytes = 0
        try:
            for target in sorted(ws_root.rglob("*")):
                if len(patches) >= max_files:
                    break
                if not target.is_file():
                    continue
                try:
                    resolved_target = target.resolve()
                except OSError:
                    continue
                try:
                    resolved_target.relative_to(ws_root)
                except ValueError:
                    continue
                rel = target.relative_to(ws_root)
                if _has_denied_workspace_part(rel.parts):
                    continue
                try:
                    resolved_rel = resolved_target.relative_to(ws_root)
                    if _has_denied_workspace_part(resolved_rel.parts):
                        continue
                except ValueError:
                    continue
                rel_posix = rel.as_posix()
                worker_content, worker_meta = _safe_read_file_content(target)
                if not worker_meta.get("text"):
                    skipped.append({"path": rel_posix, "reason": "worker_not_text"})
                    continue
                proj_path = project_root / rel
                project_safe, project_reason = _safe_project_path_for_worker_export(project_root, proj_path)
                if not project_safe:
                    skipped.append({"path": rel_posix, "reason": project_reason})
                    continue
                proj_content, proj_meta = _safe_read_file_content(proj_path)
                if not proj_meta.get("exists"):
                    old_lines = "".splitlines(keepends=True)
                    new_lines = worker_content.splitlines(keepends=True)
                    diff = list(difflib.unified_diff(
                        old_lines, new_lines,
                        fromfile=f"/dev/null", tofile=f"b/{rel_posix}",
                        n=context_lines,
                    ))
                    diff_text = "".join(diff)
                    if diff_text:
                        patch_entry = {
                            "patch": diff_text,
                            "path": rel_posix,
                            "status": "created",
                            "worker_bytes": len(worker_content.encode("utf-8")),
                            "project_bytes": 0,
                            "has_changes": True,
                        }
                        total_patch_bytes, _added, stop = _append_worker_patch_if_bounded(
                            patches, skipped, patch_entry, total_patch_bytes,
                        )
                        if stop:
                            break
                    continue
                if not proj_meta.get("text"):
                    skipped.append({"path": rel_posix, "reason": "project_not_text"})
                    continue
                if worker_content == proj_content:
                    continue
                old_lines = proj_content.splitlines(keepends=True)
                new_lines = worker_content.splitlines(keepends=True)
                diff = list(difflib.unified_diff(
                    old_lines, new_lines,
                    fromfile=f"a/{rel_posix}", tofile=f"b/{rel_posix}",
                    n=context_lines,
                ))
                diff_text = "".join(diff)
                if diff_text:
                    patch_entry = {
                        "patch": diff_text,
                        "path": rel_posix,
                        "status": "modified",
                        "worker_bytes": len(worker_content.encode("utf-8")),
                        "project_bytes": len(proj_content.encode("utf-8")),
                        "has_changes": True,
                    }
                    total_patch_bytes, _added, stop = _append_worker_patch_if_bounded(
                        patches, skipped, patch_entry, total_patch_bytes,
                    )
                    if stop:
                        break
        except OSError:
            return _json.dumps({"error": "workspace 目录读取失败"}, ensure_ascii=False)
        return _json.dumps({
            "patches": patches,
            "count": len(patches),
            "skipped": skipped,
            "skipped_count": len(skipped),
            "patch_bytes": total_patch_bytes,
            "workspace_path": lease.workspace_path,
            "lease_id": lease.lease_id,
            "worker_id": worker_id,
            "task_id": task_id,
        }, ensure_ascii=False)

    registry.register(
        "summarize_worker_workspace_changes",
        "对比 worker workspace 和 project root，返回每个文件的变更状态摘要。",
        _summarize_worker_workspace_changes_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "max_files": {"type": "integer", "description": "最大文件数，默认 50，上限 200"},
            },
            "required": ["worker_id", "task_id"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )
    registry.register(
        "export_worker_workspace_patch",
        "导出 worker workspace 相对于 project root 的 unified diff patch。",
        _export_worker_workspace_patch_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "path": {"type": "string", "description": "单文件路径（可选，不填则导出所有变更文件）"},
                "max_files": {"type": "integer", "description": "最大文件数，默认 50，上限 200"},
                "context_lines": {"type": "integer", "description": "diff 上下文行数，默认 3"},
            },
            "required": ["worker_id", "task_id"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )

    _VALID_DECISIONS = {"approved", "changes_requested", "blocked"}

    def _safe_review_gate_reviewer(reviewer: str) -> str:
        label = (reviewer or "").strip() or "codex_pm"
        if is_sensitive_text(label):
            return "[redacted]"
        if len(label) > 80:
            return label[:80] + "..."
        return label

    def _record_worker_workspace_review_gate_json(
        worker_id: str,
        task_id: str,
        decision: str,
        reviewer: str = "codex_pm",
        summary: str = "",
        checks_passed: bool = True,
        patch_exported: bool = True,
    ) -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        decision = decision.strip().lower()
        if decision not in _VALID_DECISIONS:
            return _json.dumps({
                "error": f"decision 必须是 {', '.join(sorted(_VALID_DECISIONS))} 之一",
                "decision": decision,
            }, ensure_ascii=False)
        summary_present = bool(summary.strip())
        summary_length = len(summary.strip()) if summary_present else 0
        safe_reviewer = _safe_review_gate_reviewer(reviewer)
        payload = {
            "worker_id": worker_id,
            "task_id": task_id,
            "lease_id": lease.lease_id,
            "decision": decision,
            "reviewer": safe_reviewer,
            "checks_passed": bool(checks_passed),
            "patch_exported": bool(patch_exported),
            "summary_present": summary_present,
            "summary_length": summary_length,
        }
        try:
            event = registry.durable_event_store.record(
                event_type=REVIEW_GATE_FINISHED,
                task_id=task_id,
                worker_id=worker_id,
                source="review_gate",
                summary=f"review gate: {decision} for {worker_id}/{task_id}",
                severity="info" if decision == "approved" else "warning",
                payload=payload,
            )
        except Exception:
            return _json.dumps({"error": "review gate 记录失败"}, ensure_ascii=False)
        return _json.dumps({
            "recorded": True,
            "event_id": event.event_id,
            "decision": decision,
            "reviewer": payload["reviewer"],
            "summary_present": summary_present,
            "summary_length": summary_length,
            "checks_passed": payload["checks_passed"],
            "patch_exported": payload["patch_exported"],
            "lease_id": lease.lease_id,
            "worker_id": worker_id,
            "task_id": task_id,
            "created_at": event.created_at,
        }, ensure_ascii=False)

    def _get_worker_workspace_review_gate_json(worker_id: str, task_id: str) -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        try:
            events = registry.durable_event_store.list_events(
                task_id=task_id,
                event_type=REVIEW_GATE_FINISHED,
                worker_id=worker_id,
                max_results=1,
            )
        except Exception:
            return _json.dumps({"error": "review gate 查询失败"}, ensure_ascii=False)
        if not events:
            return _json.dumps({
                "has_gate": False,
                "worker_id": worker_id,
                "task_id": task_id,
                "lease_id": lease.lease_id,
            }, ensure_ascii=False)
        event = events[0]
        payload = event.payload or {}
        return _json.dumps({
            "has_gate": True,
            "event_id": event.event_id,
            "decision": payload.get("decision", ""),
            "reviewer": payload.get("reviewer", ""),
            "summary_present": payload.get("summary_present", False),
            "summary_length": payload.get("summary_length", 0),
            "checks_passed": payload.get("checks_passed", True),
            "patch_exported": payload.get("patch_exported", True),
            "lease_id": lease.lease_id,
            "worker_id": worker_id,
            "task_id": task_id,
            "created_at": event.created_at,
        }, ensure_ascii=False)

    registry.register(
        "record_worker_workspace_review_gate",
        "记录 worker workspace 的 review gate 决策（approved/changes_requested/blocked）。",
        _record_worker_workspace_review_gate_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "decision": {"type": "string", "description": "审批决策: approved, changes_requested, blocked"},
                "reviewer": {"type": "string", "description": "审核人，默认 codex_pm"},
                "summary": {"type": "string", "description": "审核摘要（可选，不存储原文，只存预览）"},
                "checks_passed": {"type": "boolean", "description": "检查是否通过，默认 true"},
                "patch_exported": {"type": "boolean", "description": "patch 是否已导出，默认 true"},
            },
            "required": ["worker_id", "task_id", "decision"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "get_worker_workspace_review_gate",
        "查询 worker workspace 最新的 review gate 记录。",
        _get_worker_workspace_review_gate_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
            },
            "required": ["worker_id", "task_id"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )

    def _dry_run_worker_workspace_merge_json(worker_id: str, task_id: str, max_files: int = 50) -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        try:
            max_files_int = max(1, min(int(max_files or 50), 200))
        except (ValueError, TypeError):
            return _json.dumps({"error": "max_files 必须是整数"}, ensure_ascii=False)
        reasons = []
        summary_json = _summarize_worker_workspace_changes_json(worker_id, task_id, max_files_int)
        try:
            summary = _json.loads(summary_json)
        except Exception:
            return _json.dumps({"error": "change summary 获取失败"}, ensure_ascii=False)
        if "error" in summary:
            return _json.dumps({"error": f"change summary: {summary['error']}"}, ensure_ascii=False)
        patch_json = _export_worker_workspace_patch_json(worker_id, task_id, max_files=max_files_int)
        try:
            patch_result = _json.loads(patch_json)
        except Exception:
            return _json.dumps({"error": "patch export 获取失败"}, ensure_ascii=False)
        if "error" in patch_result:
            return _json.dumps({"error": f"patch export: {patch_result['error']}"}, ensure_ascii=False)
        gate_json = _get_worker_workspace_review_gate_json(worker_id, task_id)
        try:
            gate = _json.loads(gate_json)
        except Exception:
            return _json.dumps({"error": "review gate 查询失败"}, ensure_ascii=False)
        if "error" in gate:
            return _json.dumps({"error": f"review gate: {gate['error']}"}, ensure_ascii=False)
        has_gate = gate.get("has_gate", False)
        decision = gate.get("decision", "") if has_gate else ""
        created = summary.get("created", 0)
        modified = summary.get("modified", 0)
        same = summary.get("same", 0)
        skipped_summary = summary.get("skipped", 0)
        patches = patch_result.get("patches", [])
        patch_count = len(patches)
        skipped_patches = patch_result.get("skipped", [])
        skipped_patch_count = len(skipped_patches) if isinstance(skipped_patches, list) else 0
        patch_bytes = patch_result.get("patch_bytes")
        if not isinstance(patch_bytes, int):
            patch_bytes = sum(len(p.get("patch", "").encode("utf-8")) for p in patches)
        skipped_patch_reasons = {
            item.get("reason")
            for item in skipped_patches
            if isinstance(item, dict)
        }
        has_changes = (created + modified) > 0 or patch_count > 0
        if not has_gate:
            reasons.append("no_review_gate")
        elif decision != "approved":
            reasons.append(f"gate_{decision}")
        if not has_changes:
            reasons.append("no_changes")
        if skipped_summary > 0:
            reasons.append("summary_has_skipped")
        if skipped_patch_count > 0:
            reasons.append("patch_export_has_skipped")
        if patch_bytes > MAX_FILE_BYTES or skipped_patch_reasons & {"patch_budget_exceeded", "patch_too_large"}:
            reasons.append("patch_budget_exceeded")
        ready = len(reasons) == 0
        return _json.dumps({
            "ready": ready,
            "reasons": reasons,
            "has_review_gate": has_gate,
            "decision": decision,
            "requires_review": not has_gate,
            "created": created,
            "modified": modified,
            "same": same,
            "skipped_summary": skipped_summary,
            "patch_count": patch_count,
            "skipped_patch_count": skipped_patch_count,
            "patch_bytes": patch_bytes,
            "lease_id": lease.lease_id,
            "worker_id": worker_id,
            "task_id": task_id,
        }, ensure_ascii=False)

    registry.register(
        "dry_run_worker_workspace_merge",
        "预检 worker workspace 是否准备好合并（只读，不实际 merge）。",
        _dry_run_worker_workspace_merge_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "max_files": {"type": "integer", "description": "最大文件数，默认 50，上限 200"},
            },
            "required": ["worker_id", "task_id"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )

    def _apply_reviewed_worker_workspace_merge_json(worker_id: str, task_id: str, max_files: int = 50) -> str:
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps(err, ensure_ascii=False)
        try:
            max_files_int = max(1, min(int(max_files or 50), 200))
        except (ValueError, TypeError):
            return _json.dumps({"error": "max_files 必须是整数"}, ensure_ascii=False)
        dry_run_json = _dry_run_worker_workspace_merge_json(worker_id, task_id, max_files_int)
        try:
            dry_run = _json.loads(dry_run_json)
        except Exception:
            return _json.dumps({"error": "dry-run 获取失败"}, ensure_ascii=False)
        if "error" in dry_run:
            return _json.dumps({"error": f"dry-run: {dry_run['error']}"}, ensure_ascii=False)
        if not dry_run.get("ready", False):
            return _json.dumps({
                "applied": False,
                "reasons": dry_run.get("reasons", ["dry_run_not_ready"]),
                "dry_run": dry_run,
                "lease_id": lease.lease_id,
                "worker_id": worker_id,
                "task_id": task_id,
            }, ensure_ascii=False)
        summary_json = _summarize_worker_workspace_changes_json(worker_id, task_id, max_files_int)
        try:
            summary = _json.loads(summary_json)
        except Exception:
            return _json.dumps({"error": "change summary 获取失败"}, ensure_ascii=False)
        if "error" in summary:
            return _json.dumps({"error": f"change summary: {summary['error']}"}, ensure_ascii=False)
        if summary.get("skipped", 0) > 0:
            return _json.dumps({
                "applied": False,
                "reasons": ["summary_has_skipped"],
                "skipped_summary": summary.get("skipped", 0),
                "lease_id": lease.lease_id,
                "worker_id": worker_id,
                "task_id": task_id,
            }, ensure_ascii=False)
        patch_json = _export_worker_workspace_patch_json(worker_id, task_id, max_files=max_files_int)
        try:
            patch_result = _json.loads(patch_json)
        except Exception:
            return _json.dumps({"error": "patch export 获取失败"}, ensure_ascii=False)
        if "error" in patch_result:
            return _json.dumps({"error": f"patch export: {patch_result['error']}"}, ensure_ascii=False)
        skipped_patches = patch_result.get("skipped", [])
        skipped_patch_count = len(skipped_patches) if isinstance(skipped_patches, list) else 0
        patch_bytes = patch_result.get("patch_bytes")
        if not isinstance(patch_bytes, int):
            patch_bytes = sum(len(p.get("patch", "").encode("utf-8")) for p in patch_result.get("patches", []))
        skipped_patch_reasons = {
            item.get("reason")
            for item in skipped_patches
            if isinstance(item, dict)
        }
        apply_block_reasons = []
        if skipped_patch_count > 0:
            apply_block_reasons.append("patch_export_has_skipped")
        if patch_bytes > MAX_FILE_BYTES or skipped_patch_reasons & {"patch_budget_exceeded", "patch_too_large"}:
            apply_block_reasons.append("patch_budget_exceeded")
        if apply_block_reasons:
            return _json.dumps({
                "applied": False,
                "reasons": apply_block_reasons,
                "skipped_patch_count": skipped_patch_count,
                "patch_bytes": patch_bytes,
                "lease_id": lease.lease_id,
                "worker_id": worker_id,
                "task_id": task_id,
            }, ensure_ascii=False)
        ws_root = Path(lease.workspace_path).resolve()
        project_root = root.resolve()
        apply_list = []
        for entry in summary.get("files", []):
            if entry.get("status") in ("created", "modified"):
                apply_list.append(entry)
        if not apply_list:
            return _json.dumps({
                "applied": False,
                "reasons": ["no_applyable_files"],
                "lease_id": lease.lease_id,
                "worker_id": worker_id,
                "task_id": task_id,
            }, ensure_ascii=False)
        applied_files = []
        rollback_data = {}
        class _ApplyMergeError(Exception):
            def __init__(self, reason: str, path: str = ""):
                super().__init__(reason)
                self.reason = reason
                self.path = path

        try:
            for entry in apply_list:
                rel_posix = entry["path"]
                rel = Path(rel_posix)
                ws_file = ws_root / rel
                proj_file = project_root / rel
                ws_content, ws_meta = _safe_read_file_content(ws_file)
                if not ws_meta.get("text"):
                    raise _ApplyMergeError("worker_not_text", rel_posix)
                safe, reason = _safe_project_path_for_worker_export(project_root, proj_file)
                if not safe:
                    raise _ApplyMergeError(reason or "project_path_unsafe", rel_posix)
                if entry["status"] == "modified":
                    if not proj_file.exists():
                        raise _ApplyMergeError("project_missing", rel_posix)
                    if not proj_file.is_file():
                        raise _ApplyMergeError("project_not_file", rel_posix)
                    try:
                        if proj_file.stat().st_size > MAX_FILE_BYTES:
                            raise _ApplyMergeError("project_oversized", rel_posix)
                    except OSError:
                        raise _ApplyMergeError("project_stat_failed", rel_posix)
                    try:
                        original_content = proj_file.read_text(encoding="utf-8")
                    except (UnicodeDecodeError, OSError):
                        raise _ApplyMergeError("project_read_failed", rel_posix)
                    rollback_data[rel_posix] = {"status": "modified", "content": original_content}
                elif entry["status"] == "created":
                    if proj_file.exists():
                        raise _ApplyMergeError("project_created_exists", rel_posix)
                    rollback_data[rel_posix] = {"status": "created"}
                try:
                    proj_file.parent.mkdir(parents=True, exist_ok=True)
                    proj_file.write_text(ws_content, encoding="utf-8")
                except OSError:
                    raise _ApplyMergeError("project_write_failed", rel_posix)
                applied_files.append({
                    "path": rel_posix,
                    "status": entry["status"],
                    "bytes": len(ws_content.encode("utf-8")),
                })
        except _ApplyMergeError as write_err:
            rollback_errors = []
            for rel_posix, rdata in rollback_data.items():
                rpath = project_root / Path(rel_posix)
                try:
                    if rdata["status"] == "modified":
                        rpath.write_text(rdata["content"], encoding="utf-8")
                    elif rdata["status"] == "created":
                        if rpath.exists():
                            rpath.unlink()
                except OSError as rb_err:
                    rollback_errors.append({
                        "path": rel_posix,
                        "reason": "rollback_failed",
                    })
            result = {
                "applied": False,
                "reasons": ["write_failed", write_err.reason],
                "error": write_err.reason,
                "failed_path": write_err.path,
                "applied_before_failure": len(applied_files),
                "rollback": "failed" if rollback_errors else "ok",
            }
            if rollback_errors:
                result["rollback_errors"] = rollback_errors[:5]
            result["lease_id"] = lease.lease_id
            result["worker_id"] = worker_id
            result["task_id"] = task_id
            return _json.dumps(result, ensure_ascii=False)
        created_count = sum(1 for f in applied_files if f["status"] == "created")
        modified_count = sum(1 for f in applied_files if f["status"] == "modified")
        try:
            registry.durable_event_store.record(
                event_type=FILE_EDIT_FINISHED,
                task_id=task_id,
                worker_id=worker_id,
                source="workspace_merge",
                summary=f"workspace merge applied: {len(applied_files)} files for {worker_id}/{task_id}",
                severity="info",
                payload={
                    "operation": "workspace_merge_apply",
                    "worker_id": worker_id,
                    "task_id": task_id,
                    "lease_id": lease.lease_id,
                    "applied_count": len(applied_files),
                    "created_count": created_count,
                    "modified_count": modified_count,
                    "paths": [f["path"] for f in applied_files],
                },
            )
        except Exception:
            pass
        return _json.dumps({
            "applied": True,
            "applied_count": len(applied_files),
            "created_count": created_count,
            "modified_count": modified_count,
            "files": applied_files,
            "lease_id": lease.lease_id,
            "worker_id": worker_id,
            "task_id": task_id,
        }, ensure_ascii=False)

    registry.register(
        "apply_reviewed_worker_workspace_merge",
        "通过 dry-run 检查后，将 worker workspace 变更写入 project root。",
        _apply_reviewed_worker_workspace_merge_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "max_files": {"type": "integer", "description": "最大文件数，默认 50，上限 200"},
            },
            "required": ["worker_id", "task_id"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )

    def _is_workspace_merge_apply_for_lease(event, lease) -> bool:
        payload = event.payload or {}
        if payload.get("operation") != "workspace_merge_apply":
            return False
        if payload.get("lease_id") != lease.lease_id:
            return False
        event_created_at = event.created_at or ""
        lease_created_at = lease.created_at or ""
        if event_created_at and lease_created_at and event_created_at < lease_created_at:
            return False
        return True

    def _list_worker_workspace_merge_applies_json(worker_id: str = "", task_id: str = "", limit: int = 20) -> str:
        try:
            limit = max(1, min(int(limit or 20), 100))
        except (ValueError, TypeError):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        try:
            events = registry.durable_event_store.list_events(
                task_id=task_id or "",
                source="workspace_merge",
                worker_id=worker_id or "",
                max_results=100,
            )
        except Exception:
            return _json.dumps({"error": "event 查询失败"}, ensure_ascii=False)
        def _safe_audit_label(value, max_len: int = 120) -> str:
            if not isinstance(value, str):
                return ""
            if is_sensitive_text(value):
                return "[redacted]"
            if len(value) > max_len:
                return value[:max_len] + "..."
            return value

        def _safe_audit_path(value) -> str:
            if not isinstance(value, str) or value == "[redacted]" or len(value) > 240 or is_sensitive_text(value):
                return ""
            path = Path(value)
            if path.is_absolute() or ".." in path.parts or _has_denied_workspace_part(path.parts):
                return ""
            return value

        applies = []
        for event in events:
            payload = event.payload or {}
            if payload.get("operation") != "workspace_merge_apply":
                continue
            paths = payload.get("paths", [])
            if not isinstance(paths, list):
                paths = []
            safe_paths = []
            for p in paths:
                safe_path = _safe_audit_path(p)
                if safe_path:
                    safe_paths.append(safe_path)
            applies.append({
                "event_id": _safe_audit_label(event.event_id),
                "created_at": event.created_at,
                "worker_id": _safe_audit_label(event.worker_id or ""),
                "task_id": _safe_audit_label(event.task_id or ""),
                "lease_id": _safe_audit_label(payload.get("lease_id", "")),
                "applied_count": payload.get("applied_count", 0) if isinstance(payload.get("applied_count"), int) else 0,
                "created_count": payload.get("created_count", 0) if isinstance(payload.get("created_count"), int) else 0,
                "modified_count": payload.get("modified_count", 0) if isinstance(payload.get("modified_count"), int) else 0,
                "paths": safe_paths,
            })
            if len(applies) >= limit:
                break
        return _json.dumps({
            "applies": applies,
            "count": len(applies),
        }, ensure_ascii=False)

    registry.register(
        "list_worker_workspace_merge_applies",
        "列出 worker workspace merge apply 的审计记录。",
        _list_worker_workspace_merge_applies_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "按 worker_id 过滤（可选）"},
                "task_id": {"type": "string", "description": "按 task_id 过滤（可选）"},
                "limit": {"type": "integer", "description": "最大返回数，默认 20，上限 100"},
            },
            "required": [],
        },
        permission=ToolPermission(category="task", risk="read"),
    )

    def _finalize_worker_workspace_merge_json(worker_id: str, task_id: str, release_workspace: bool = True) -> str:
        if not isinstance(release_workspace, bool):
            return _json.dumps({"error": "release_workspace 必须是布尔值"}, ensure_ascii=False)
        worker_id = worker_id.strip()
        task_id = task_id.strip()
        if not worker_id:
            return _json.dumps({"error": "worker_id 不能为空"}, ensure_ascii=False)
        if not task_id:
            return _json.dumps({"error": "task_id 不能为空"}, ensure_ascii=False)
        worker = durable_worker_store.get_worker(worker_id)
        if worker is None:
            return _json.dumps({"error": f"未找到 worker: {worker_id}"}, ensure_ascii=False)
        task = durable_task_store.get_task(task_id)
        if task is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        if task.worker_id != worker_id:
            return _json.dumps({"error": f"task {task_id} 未分配给 worker {worker_id}"}, ensure_ascii=False)
        if task.status == "completed":
            return _json.dumps({
                "finalized": False,
                "reason": "already_finalized",
                "worker_id": worker_id,
                "task_id": task_id,
                "lease_id": "",
                "task_status_before": task.status,
                "task_status_after": task.status,
                "worker_status_before": worker.status,
                "worker_status_after": worker.status,
                "workspace_released": False,
            }, ensure_ascii=False)
        if worker.status == WorkerStatus.OFFLINE:
            return _json.dumps({"error": f"worker {worker_id} 已离线"}, ensure_ascii=False)
        if task.status != "running":
            return _json.dumps({
                "finalized": False,
                "reason": "task_not_running",
                "worker_id": worker_id,
                "task_id": task_id,
                "task_status": task.status,
            }, ensure_ascii=False)
        lease, err = _resolve_and_validate_lease(worker_id, task_id)
        if err:
            return _json.dumps({
                "finalized": False,
                "reason": "workspace_lease_invalid",
                "worker_id": worker_id,
                "task_id": task_id,
                "lease_id": "",
                "task_status_before": task.status,
                "task_status_after": task.status,
                "worker_status_before": worker.status,
                "worker_status_after": worker.status,
                "workspace_released": False,
            }, ensure_ascii=False)
        try:
            events = registry.durable_event_store.list_events(
                task_id=task_id,
                source="workspace_merge",
                worker_id=worker_id,
                max_results=100,
            )
        except Exception:
            return _json.dumps({"error": "event 查询失败"}, ensure_ascii=False)
        has_apply = any(_is_workspace_merge_apply_for_lease(e, lease) for e in events)
        if not has_apply:
            return _json.dumps({
                "finalized": False,
                "reason": "no_successful_apply",
                "worker_id": worker_id,
                "task_id": task_id,
                "lease_id": lease.lease_id,
                "task_status_before": task.status,
                "task_status_after": task.status,
                "worker_status_before": worker.status,
                "worker_status_after": worker.status,
                "workspace_released": False,
            }, ensure_ascii=False)
        task_status_before = task.status
        worker_status_before = worker.status
        try:
            updated_task = durable_task_store.update_status(task_id, "completed")
        except ValueError:
            return _json.dumps({"error": "task 状态更新失败"}, ensure_ascii=False)
        if updated_task is None:
            return _json.dumps({"error": "task 状态更新失败"}, ensure_ascii=False)
        updated_worker = durable_worker_store.update_status(worker_id, WorkerStatus.IDLE, current_task_id=None)
        if updated_worker is None:
            return _json.dumps({"error": "worker 状态更新失败"}, ensure_ascii=False)
        lease_id = lease.lease_id
        workspace_released = False
        if release_workspace:
            workspace_released = bool(workspace_lease_store.release_lease(lease_id))
            if workspace_released:
                try:
                    registry.durable_event_store.record(
                        event_type=WORKSPACE_RELEASED,
                        worker_id=worker_id,
                        task_id=task_id,
                        summary="workspace lease released after finalization",
                        payload={
                            "operation": "workspace_merge_finalize_release",
                            "lease_id": lease_id,
                            "worker_id": worker_id,
                            "task_id": task_id,
                        },
                        source="registry",
                        severity="info",
                    )
                except Exception:
                    pass
        try:
            registry.durable_event_store.record(
                event_type=TASK_STATUS_CHANGED,
                task_id=task_id,
                worker_id=worker_id,
                summary="task finalized after workspace merge",
                payload={
                    "operation": "workspace_merge_finalize",
                    "task_id": task_id,
                    "lease_id": lease_id,
                    "status": "completed",
                    "previous_status": task_status_before,
                    "worker_id": worker_id,
                    "workspace_released": workspace_released,
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass
        return _json.dumps({
            "finalized": True,
            "worker_id": worker_id,
            "task_id": task_id,
            "lease_id": lease_id,
            "task_status_before": task_status_before,
            "task_status_after": "completed",
            "worker_status_before": worker_status_before,
            "worker_status_after": WorkerStatus.IDLE,
            "workspace_released": workspace_released,
        }, ensure_ascii=False)

    registry.register(
        "finalize_worker_workspace_merge",
        "在成功 apply 后，完成 task/worker/lease 收尾。",
        _finalize_worker_workspace_merge_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "worker id"},
                "task_id": {"type": "string", "description": "durable task id"},
                "release_workspace": {"type": "boolean", "description": "是否释放 workspace lease，默认 true"},
            },
            "required": ["worker_id", "task_id"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )

    def _list_worker_workspace_merge_closeout_candidates_json(worker_id: str = "", task_id: str = "", limit: int = 20) -> str:
        try:
            limit = max(1, min(int(limit or 20), 100))
        except (ValueError, TypeError):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        worker_id = worker_id.strip()
        task_id = task_id.strip()

        pairs: list[tuple[str, str]] = []
        if worker_id and task_id:
            pairs.append((worker_id, task_id))
        elif worker_id:
            worker = durable_worker_store.get_worker(worker_id)
            if worker and worker.current_task_id:
                pairs.append((worker_id, worker.current_task_id))
        elif task_id:
            task = durable_task_store.get_task(task_id)
            if task and task.worker_id:
                pairs.append((task.worker_id, task_id))
        else:
            workers = durable_worker_store.list_workers(limit=500)
            for w in workers:
                if w.current_task_id:
                    pairs.append((w.worker_id, w.current_task_id))

        def _safe_label(value, max_len: int = 120) -> str:
            if not isinstance(value, str):
                return ""
            if is_sensitive_text(value):
                return "[redacted]"
            if len(value) > max_len:
                return value[:max_len] + "..."
            return value

        candidates = []
        for wid, tid in pairs:
            if len(candidates) >= limit:
                break
            worker = durable_worker_store.get_worker(wid)
            if worker is None:
                candidates.append({
                    "ready": False,
                    "reason": "worker_unavailable",
                    "worker_id": _safe_label(wid),
                    "task_id": _safe_label(tid),
                    "lease_id": "",
                    "task_status": "",
                    "worker_status": "",
                    "workspace_released": False,
                    "latest_apply_event_id": "",
                    "latest_apply_created_at": "",
                })
                continue
            task = durable_task_store.get_task(tid)
            if task is None:
                candidates.append({
                    "ready": False,
                    "reason": "worker_unavailable",
                    "worker_id": _safe_label(wid),
                    "task_id": _safe_label(tid),
                    "lease_id": "",
                    "task_status": "",
                    "worker_status": worker.status,
                    "workspace_released": False,
                    "latest_apply_event_id": "",
                    "latest_apply_created_at": "",
                })
                continue
            if task.worker_id != wid:
                candidates.append({
                    "ready": False,
                    "reason": "worker_task_mismatch",
                    "worker_id": _safe_label(wid),
                    "task_id": _safe_label(tid),
                    "lease_id": "",
                    "task_status": task.status,
                    "worker_status": worker.status,
                    "workspace_released": False,
                    "latest_apply_event_id": "",
                    "latest_apply_created_at": "",
                })
                continue
            if task.status == "completed":
                candidates.append({
                    "ready": False,
                    "reason": "already_finalized",
                    "worker_id": _safe_label(wid),
                    "task_id": _safe_label(tid),
                    "lease_id": "",
                    "task_status": task.status,
                    "worker_status": worker.status,
                    "workspace_released": False,
                    "latest_apply_event_id": "",
                    "latest_apply_created_at": "",
                })
                continue
            if worker.status == WorkerStatus.OFFLINE or worker.status == WorkerStatus.IDLE:
                candidates.append({
                    "ready": False,
                    "reason": "worker_unavailable",
                    "worker_id": _safe_label(wid),
                    "task_id": _safe_label(tid),
                    "lease_id": "",
                    "task_status": task.status,
                    "worker_status": worker.status,
                    "workspace_released": False,
                    "latest_apply_event_id": "",
                    "latest_apply_created_at": "",
                })
                continue
            if worker.current_task_id != tid:
                candidates.append({
                    "ready": False,
                    "reason": "worker_task_mismatch",
                    "worker_id": _safe_label(wid),
                    "task_id": _safe_label(tid),
                    "lease_id": "",
                    "task_status": task.status,
                    "worker_status": worker.status,
                    "workspace_released": False,
                    "latest_apply_event_id": "",
                    "latest_apply_created_at": "",
                })
                continue
            if task.status != "running":
                candidates.append({
                    "ready": False,
                    "reason": "task_not_running",
                    "worker_id": _safe_label(wid),
                    "task_id": _safe_label(tid),
                    "lease_id": "",
                    "task_status": task.status,
                    "worker_status": worker.status,
                    "workspace_released": False,
                    "latest_apply_event_id": "",
                    "latest_apply_created_at": "",
                })
                continue
            lease = workspace_lease_store.get_lease_by_worker(wid)
            if lease is None or lease.task_id != tid:
                candidates.append({
                    "ready": False,
                    "reason": "workspace_lease_invalid",
                    "worker_id": _safe_label(wid),
                    "task_id": _safe_label(tid),
                    "lease_id": "",
                    "task_status": task.status,
                    "worker_status": worker.status,
                    "workspace_released": False,
                    "latest_apply_event_id": "",
                    "latest_apply_created_at": "",
                })
                continue
            try:
                events = registry.durable_event_store.list_events(
                    task_id=tid,
                    source="workspace_merge",
                    worker_id=wid,
                    max_results=100,
                )
            except Exception:
                candidates.append({
                    "ready": False,
                    "reason": "no_successful_apply",
                    "worker_id": _safe_label(wid),
                    "task_id": _safe_label(tid),
                    "lease_id": _safe_label(lease.lease_id),
                    "task_status": task.status,
                    "worker_status": worker.status,
                    "workspace_released": False,
                    "latest_apply_event_id": "",
                    "latest_apply_created_at": "",
                })
                continue
            apply_event = None
            for e in events:
                if _is_workspace_merge_apply_for_lease(e, lease):
                    apply_event = e
                    break
            if apply_event is None:
                candidates.append({
                    "ready": False,
                    "reason": "no_successful_apply",
                    "worker_id": _safe_label(wid),
                    "task_id": _safe_label(tid),
                    "lease_id": _safe_label(lease.lease_id),
                    "task_status": task.status,
                    "worker_status": worker.status,
                    "workspace_released": False,
                    "latest_apply_event_id": "",
                    "latest_apply_created_at": "",
                })
                continue
            candidates.append({
                "ready": True,
                "reason": "ready_to_finalize",
                "worker_id": _safe_label(wid),
                "task_id": _safe_label(tid),
                "lease_id": _safe_label(lease.lease_id),
                "task_status": task.status,
                "worker_status": worker.status,
                "workspace_released": False,
                "latest_apply_event_id": _safe_label(apply_event.event_id),
                "latest_apply_created_at": apply_event.created_at or "",
            })
        return _json.dumps({
            "candidates": candidates,
            "count": len(candidates),
        }, ensure_ascii=False)

    registry.register(
        "list_worker_workspace_merge_closeout_candidates",
        "列出哪些 worker/task 已 ready 可以 finalize，哪些不能。",
        _list_worker_workspace_merge_closeout_candidates_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "按 worker_id 过滤（可选）"},
                "task_id": {"type": "string", "description": "按 task_id 过滤（可选）"},
                "limit": {"type": "integer", "description": "最大返回数，默认 20，上限 100"},
            },
            "required": [],
        },
        permission=ToolPermission(category="task", risk="read"),
    )

    def _finalize_ready_worker_workspace_merges_json(limit: int = 10, release_workspace: bool = True) -> str:
        try:
            limit = max(1, min(int(limit or 10), 100))
        except (ValueError, TypeError):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        if not isinstance(release_workspace, bool):
            return _json.dumps({"error": "release_workspace 必须是布尔值"}, ensure_ascii=False)
        ready_candidates = []
        for worker in durable_worker_store.list_workers(limit=500):
            if len(ready_candidates) >= limit:
                break
            if not worker.current_task_id:
                continue
            candidates_json = _list_worker_workspace_merge_closeout_candidates_json(
                worker_id=worker.worker_id,
                task_id=worker.current_task_id,
                limit=1,
            )
            try:
                candidates_data = _json.loads(candidates_json)
            except Exception:
                return _json.dumps({"error": "候选查询失败"}, ensure_ascii=False)
            if "error" in candidates_data:
                return _json.dumps({"error": f"候选查询: {candidates_data['error']}"}, ensure_ascii=False)
            for c in candidates_data.get("candidates", []):
                if c.get("ready") and c.get("reason") == "ready_to_finalize":
                    ready_candidates.append(c)
                    break
        results = []
        for c in ready_candidates:
            wid = c.get("worker_id", "")
            tid = c.get("task_id", "")
            result_json = _finalize_worker_workspace_merge_json(wid, tid, release_workspace=release_workspace)
            try:
                result = _json.loads(result_json)
            except Exception:
                result = {"finalized": False, "reason": "internal_error", "worker_id": wid, "task_id": tid}
            results.append(result)
        finalized_count = sum(1 for r in results if r.get("finalized"))
        return _json.dumps({
            "processed": len(results),
            "finalized_count": finalized_count,
            "results": results,
        }, ensure_ascii=False)

    registry.register(
        "finalize_ready_worker_workspace_merges",
        "批量 finalize 所有 ready 的 worker/task。逐个调用单任务 finalize 逻辑。",
        _finalize_ready_worker_workspace_merges_json,
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "最大处理数，默认 10，上限 100"},
                "release_workspace": {"type": "boolean", "description": "是否释放 workspace lease，默认 true"},
            },
            "required": [],
        },
        permission=ToolPermission(category="task", risk="write"),
    )

    def _plan_worker_lifecycle_actions_json(limit: int = 20) -> str:
        try:
            limit = max(1, min(int(limit or 20), 100))
        except (ValueError, TypeError):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        actions = []
        summary = {
            "ready_closeouts": 0,
            "not_ready_closeouts": 0,
            "idle_workers": 0,
            "pending_tasks": 0,
        }
        try:
            workers = durable_worker_store.list_workers(limit=500)
            tasks = durable_task_store.list_tasks(limit=500)
        except Exception:
            workers, tasks = [], []
        ready_actions = []
        wait_actions = []
        for worker in workers:
            if not worker.current_task_id:
                continue
            try:
                candidates_json = _list_worker_workspace_merge_closeout_candidates_json(
                    worker_id=worker.worker_id,
                    task_id=worker.current_task_id,
                    limit=1,
                )
                candidates_data = _json.loads(candidates_json)
            except Exception:
                continue
            for c in candidates_data.get("candidates", []):
                if c.get("ready") and c.get("reason") == "ready_to_finalize":
                    summary["ready_closeouts"] += 1
                    ready_actions.append({
                        "action": "finalize_ready_workspace_merge",
                        "worker_id": c.get("worker_id", ""),
                        "task_id": c.get("task_id", ""),
                        "lease_id": c.get("lease_id", ""),
                    })
                else:
                    summary["not_ready_closeouts"] += 1
                    reason = c.get("reason", "")
                    if reason == "no_successful_apply":
                        wait_actions.append({
                            "action": "wait_for_workspace_merge_apply",
                            "worker_id": c.get("worker_id", ""),
                            "task_id": c.get("task_id", ""),
                        })
                    elif reason == "workspace_lease_invalid":
                        wait_actions.append({
                            "action": "wait_for_workspace_lease",
                            "worker_id": c.get("worker_id", ""),
                            "task_id": c.get("task_id", ""),
                        })
                break
        for action in ready_actions + wait_actions:
            if len(actions) >= limit:
                break
            actions.append(action)
        idle_workers = [w for w in workers if w.status == WorkerStatus.IDLE]
        pending_tasks = [t for t in tasks if t.status == "pending" and not t.worker_id]
        summary["idle_workers"] = len(idle_workers)
        summary["pending_tasks"] = len(pending_tasks)
        # Retryable failed tasks: status=failed, retry_count < max_retries, no active worker
        failed_tasks = [t for t in tasks if t.status == "failed"]
        retryable_tasks = []
        retry_exhausted_count = 0
        retry_blocked_count = 0
        for t in failed_tasks:
            if t.retry_count >= t.max_retries:
                retry_exhausted_count += 1
                continue
            # Check if an active/running worker is still attached
            owner_worker = None
            for w in workers:
                if w.current_task_id == t.task_id and w.status in (WorkerStatus.RUNNING, WorkerStatus.ASSIGNED):
                    owner_worker = w
                    break
            if owner_worker:
                retry_blocked_count += 1
                continue
            retryable_tasks.append(t)
        summary["retryable_tasks"] = len(retryable_tasks)
        summary["retry_exhausted"] = retry_exhausted_count
        summary["retry_blocked_active_worker"] = retry_blocked_count
        # Retry actions come after closeouts, before dispatch
        for t in retryable_tasks:
            if len(actions) >= limit:
                break
            actions.append({
                "action": "retry_failed_task",
                "task_id": t.task_id,
                "retry_count": t.retry_count,
                "max_retries": t.max_retries,
                "reason": "retry_available",
            })
        if idle_workers and pending_tasks and len(actions) < limit:
            actions.append({
                "action": "dispatch_pending_task",
                "idle_worker_count": len(idle_workers),
                "pending_task_count": len(pending_tasks),
            })
        return _json.dumps({
            "actions": actions[:limit],
            "count": min(len(actions), limit),
            "summary": summary,
        }, ensure_ascii=False)

    registry.register(
        "plan_worker_lifecycle_actions",
        "为 PM 推荐下一步 worker 生命周期操作。只读，不自动执行。",
        _plan_worker_lifecycle_actions_json,
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "最大返回 action 数，默认 20，上限 100"},
            },
            "required": [],
        },
        permission=ToolPermission(category="task", risk="read"),
    )

    def _run_worker_lifecycle_once_json(limit: int = 5, dry_run: bool = True, release_workspace: bool = True) -> str:
        if limit is None:
            limit = 5
        elif isinstance(limit, bool):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        elif not isinstance(limit, int):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        limit = max(1, min(limit, 100))
        if not isinstance(dry_run, bool):
            return _json.dumps({"error": "dry_run 必须是布尔值"}, ensure_ascii=False)
        if not isinstance(release_workspace, bool):
            return _json.dumps({"error": "release_workspace 必须是布尔值"}, ensure_ascii=False)
        plan_json = _plan_worker_lifecycle_actions_json(limit=limit)
        try:
            plan = _json.loads(plan_json)
        except Exception:
            return _json.dumps({"error": "planner 查询失败"}, ensure_ascii=False)
        if "error" in plan:
            return _json.dumps({"error": f"planner: {plan['error']}"}, ensure_ascii=False)
        actions = plan.get("actions", [])
        summary = plan.get("summary", {})
        results = []
        executed_count = 0
        skipped_count = 0
        failed_count = 0
        for a in actions:
            action_type = a.get("action", "")
            if action_type == "finalize_ready_workspace_merge":
                if dry_run:
                    results.append({
                        "action": action_type,
                        "worker_id": a.get("worker_id", ""),
                        "task_id": a.get("task_id", ""),
                        "would_execute": True,
                    })
                else:
                    wid = a.get("worker_id", "")
                    tid = a.get("task_id", "")
                    result_json = _finalize_worker_workspace_merge_json(wid, tid, release_workspace=release_workspace)
                    try:
                        result = _json.loads(result_json)
                    except Exception:
                        result = {"finalized": False, "reason": "internal_error", "worker_id": wid, "task_id": tid}
                    result["action"] = action_type
                    results.append(result)
                    if result.get("finalized"):
                        executed_count += 1
                    else:
                        failed_count += 1
            elif action_type == "dispatch_pending_task":
                skipped_count += 1
                results.append({
                    "action": action_type,
                    "skipped": True,
                    "reason": "dispatch_not_supported",
                })
            else:
                skipped_count += 1
                results.append({
                    "action": action_type,
                    "worker_id": a.get("worker_id", ""),
                    "task_id": a.get("task_id", ""),
                    "skipped": True,
                    "reason": "wait_action",
                })
        return _json.dumps({
            "dry_run": dry_run,
            "planned_count": len(actions),
            "executed_count": executed_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "results": results,
            "summary": summary,
        }, ensure_ascii=False)

    registry.register(
        "run_worker_lifecycle_once",
        "执行一轮 worker 生命周期：dry-run 返回计划，非 dry-run 执行 ready closeout。",
        _run_worker_lifecycle_once_json,
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "最大处理 action 数，默认 5，上限 100"},
                "dry_run": {"type": "boolean", "description": "是否 dry-run，默认 true"},
                "release_workspace": {"type": "boolean", "description": "是否释放 workspace lease，默认 true"},
            },
            "required": [],
        },
        permission=ToolPermission(category="task", risk="write", requires_confirmation=True),
    )

    _scheduler_tick_counter = [0]

    def _run_worker_lifecycle_scheduler_tick_json(limit: int = 5, dry_run: bool = True, release_workspace: bool = True, record_event: bool = True) -> str:
        if limit is None:
            limit = 5
        elif isinstance(limit, bool):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        elif not isinstance(limit, int):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        limit = max(1, min(limit, 100))
        if not isinstance(dry_run, bool):
            return _json.dumps({"error": "dry_run 必须是布尔值"}, ensure_ascii=False)
        if not isinstance(release_workspace, bool):
            return _json.dumps({"error": "release_workspace 必须是布尔值"}, ensure_ascii=False)
        if not isinstance(record_event, bool):
            return _json.dumps({"error": "record_event 必须是布尔值"}, ensure_ascii=False)

        _scheduler_tick_counter[0] += 1
        tick_id = f"tick_{_scheduler_tick_counter[0]}"

        run_json = _run_worker_lifecycle_once_json(
            limit=limit,
            dry_run=dry_run,
            release_workspace=release_workspace,
        )
        try:
            run_result = _json.loads(run_json)
        except Exception:
            return _json.dumps({"error": "scheduler tick 执行失败"}, ensure_ascii=False)
        if "error" in run_result:
            return _json.dumps({"error": run_result["error"]}, ensure_ascii=False)

        results = run_result.get("results", [])
        blocked_count = 0
        scheduler_results = []
        event_actions = []
        for result in results:
            action_type = result.get("action", "")
            safe_result = dict(result)
            if action_type == "dispatch_pending_task":
                blocked_count += 1
                safe_result["skipped"] = True
                safe_result["reason"] = "dispatch_blocked_in_tick"
            scheduler_results.append(safe_result)
            event_actions.append({
                "action": safe_result.get("action", ""),
                "worker_id": safe_result.get("worker_id", ""),
                "task_id": safe_result.get("task_id", ""),
                "reason": safe_result.get("reason", ""),
                "skipped": bool(safe_result.get("skipped", False)),
                "would_execute": bool(safe_result.get("would_execute", False)),
                "finalized": bool(safe_result.get("finalized", False)),
            })
        skipped_count = max(0, int(run_result.get("skipped_count", 0)) - blocked_count)

        decision_event_recorded = False
        if record_event:
            try:
                durable_event_store.record(
                    event_type=SCHEDULER_DECISION,
                    summary="scheduler tick",
                    payload={
                        "scheduler": "worker_lifecycle",
                        "tick_id": tick_id,
                        "dry_run": dry_run,
                        "record_event": record_event,
                        "release_workspace": release_workspace,
                        "planned_count": run_result.get("planned_count", 0),
                        "executed_count": run_result.get("executed_count", 0),
                        "skipped_count": skipped_count,
                        "failed_count": run_result.get("failed_count", 0),
                        "blocked_count": blocked_count,
                        "action_labels": [r.get("action", "") for r in scheduler_results],
                        "actions": event_actions,
                    },
                    source="scheduler",
                    severity="info",
                )
                decision_event_recorded = True
            except Exception:
                pass

        return _json.dumps({
            "scheduler": "worker_lifecycle",
            "tick_id": tick_id,
            "dry_run": dry_run,
            "record_event": record_event,
            "planned_count": run_result.get("planned_count", 0),
            "executed_count": run_result.get("executed_count", 0),
            "skipped_count": skipped_count,
            "failed_count": run_result.get("failed_count", 0),
            "blocked_count": blocked_count,
            "results": scheduler_results,
            "summary": run_result.get("summary", {}),
            "decision_event_recorded": decision_event_recorded,
        }, ensure_ascii=False)

    registry.register(
        "run_worker_lifecycle_scheduler_tick",
        "执行一次 scheduler tick：dry-run 返回计划，非 dry-run 执行 ready closeout，记录 scheduler decision 事件。",
        _run_worker_lifecycle_scheduler_tick_json,
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "最大处理 action 数，默认 5，上限 100"},
                "dry_run": {"type": "boolean", "description": "是否 dry-run，默认 true"},
                "release_workspace": {"type": "boolean", "description": "是否释放 workspace lease，默认 true"},
                "record_event": {"type": "boolean", "description": "是否记录 scheduler decision 事件，默认 true"},
            },
            "required": [],
        },
        permission=ToolPermission(category="task", risk="write", requires_confirmation=True),
    )

    _scheduler_loop_counter = [0]

    def _run_worker_lifecycle_scheduler_loop_json(max_ticks: int = 3, limit: int = 5, dry_run: bool = True, release_workspace: bool = True, stop_when_idle: bool = True, record_event: bool = True) -> str:
        if max_ticks is None:
            max_ticks = 3
        elif isinstance(max_ticks, bool):
            return _json.dumps({"error": "max_ticks 必须是整数"}, ensure_ascii=False)
        elif not isinstance(max_ticks, int):
            return _json.dumps({"error": "max_ticks 必须是整数"}, ensure_ascii=False)
        max_ticks = max(1, min(max_ticks, 10))
        if limit is None:
            limit = 5
        elif isinstance(limit, bool):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        elif not isinstance(limit, int):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        limit = max(1, min(limit, 100))
        if not isinstance(dry_run, bool):
            return _json.dumps({"error": "dry_run 必须是布尔值"}, ensure_ascii=False)
        if not isinstance(release_workspace, bool):
            return _json.dumps({"error": "release_workspace 必须是布尔值"}, ensure_ascii=False)
        if not isinstance(stop_when_idle, bool):
            return _json.dumps({"error": "stop_when_idle 必须是布尔值"}, ensure_ascii=False)
        if not isinstance(record_event, bool):
            return _json.dumps({"error": "record_event 必须是布尔值"}, ensure_ascii=False)

        _scheduler_loop_counter[0] += 1
        loop_id = f"loop_{_scheduler_loop_counter[0]}"

        ticks = []
        total_planned = 0
        total_executed = 0
        total_skipped = 0
        total_failed = 0
        total_blocked = 0
        stopped_reason = "max_ticks_reached"

        for i in range(max_ticks):
            tick_json = _run_worker_lifecycle_scheduler_tick_json(
                limit=limit,
                dry_run=dry_run,
                release_workspace=release_workspace,
                record_event=record_event,
            )
            try:
                tick_result = _json.loads(tick_json)
            except Exception:
                ticks.append({"tick_index": i, "error": "tick 执行失败"})
                stopped_reason = "tick_error"
                break
            if "error" in tick_result:
                ticks.append({"tick_index": i, "error": tick_result["error"]})
                stopped_reason = "tick_error"
                break

            tick_summary = {
                "tick_index": i,
                "tick_id": tick_result.get("tick_id", ""),
                "planned_count": tick_result.get("planned_count", 0),
                "executed_count": tick_result.get("executed_count", 0),
                "skipped_count": tick_result.get("skipped_count", 0),
                "failed_count": tick_result.get("failed_count", 0),
                "blocked_count": tick_result.get("blocked_count", 0),
            }
            ticks.append(tick_summary)

            total_planned += tick_result.get("planned_count", 0)
            total_executed += tick_result.get("executed_count", 0)
            total_skipped += tick_result.get("skipped_count", 0)
            total_failed += tick_result.get("failed_count", 0)
            total_blocked += tick_result.get("blocked_count", 0)

            if stop_when_idle:
                tick_planned = tick_result.get("planned_count", 0)
                summary = tick_result.get("summary", {})
                has_pending = any([
                    summary.get("ready_closeouts", 0) > 0,
                    summary.get("not_ready_closeouts", 0) > 0,
                    summary.get("idle_workers", 0) > 0,
                    summary.get("pending_tasks", 0) > 0,
                ])
                if tick_planned == 0 and not has_pending:
                    stopped_reason = "idle"
                    break

        loop_event_recorded = False
        if record_event:
            try:
                durable_event_store.record(
                    event_type=SCHEDULER_DECISION,
                    summary="scheduler loop",
                    payload={
                        "scheduler": "worker_lifecycle",
                        "loop_id": loop_id,
                        "dry_run": dry_run,
                        "max_ticks": max_ticks,
                        "ticks_run": len(ticks),
                        "stopped_reason": stopped_reason,
                        "planned_count": total_planned,
                        "executed_count": total_executed,
                        "skipped_count": total_skipped,
                        "failed_count": total_failed,
                        "blocked_count": total_blocked,
                        "tick_ids": [t.get("tick_id", "") for t in ticks],
                        "release_workspace": release_workspace,
                        "stop_when_idle": stop_when_idle,
                        "record_event": record_event,
                    },
                    source="scheduler",
                    severity="info",
                )
                loop_event_recorded = True
            except Exception:
                pass

        return _json.dumps({
            "scheduler": "worker_lifecycle",
            "loop_id": loop_id,
            "dry_run": dry_run,
            "max_ticks": max_ticks,
            "ticks_run": len(ticks),
            "stopped_reason": stopped_reason,
            "planned_count": total_planned,
            "executed_count": total_executed,
            "skipped_count": total_skipped,
            "failed_count": total_failed,
            "blocked_count": total_blocked,
            "ticks": ticks,
            "summary": {
                "loop_id": loop_id,
                "ticks_run": len(ticks),
                "max_ticks": max_ticks,
                "stopped_reason": stopped_reason,
                "total_planned": total_planned,
                "total_executed": total_executed,
                "total_skipped": total_skipped,
                "total_failed": total_failed,
                "total_blocked": total_blocked,
                "dry_run": dry_run,
                "loop_event_recorded": loop_event_recorded,
            },
            "loop_event_recorded": loop_event_recorded,
        }, ensure_ascii=False)

    registry.register(
        "run_worker_lifecycle_scheduler_loop",
        "执行有限次 scheduler loop：运行最多 max_ticks 次 scheduler tick，支持 stop_when_idle 提前停止。",
        _run_worker_lifecycle_scheduler_loop_json,
        parameters={
            "type": "object",
            "properties": {
                "max_ticks": {"type": "integer", "description": "最大 tick 次数，默认 3，上限 10"},
                "limit": {"type": "integer", "description": "每个 tick 最大处理 action 数，默认 5，上限 100"},
                "dry_run": {"type": "boolean", "description": "是否 dry-run，默认 true"},
                "release_workspace": {"type": "boolean", "description": "是否释放 workspace lease，默认 true"},
                "stop_when_idle": {"type": "boolean", "description": "空闲时提前停止，默认 true"},
                "record_event": {"type": "boolean", "description": "是否记录 scheduler decision 事件，默认 true"},
            },
            "required": [],
        },
        permission=ToolPermission(category="task", risk="write", requires_confirmation=True),
    )

    def _explain_worker_lifecycle_scheduler_state_json(worker_id: str = "", task_id: str = "", limit: int = 20) -> str:
        if not isinstance(worker_id, str):
            return _json.dumps({"error": "worker_id 必须是字符串"}, ensure_ascii=False)
        if not isinstance(task_id, str):
            return _json.dumps({"error": "task_id 必须是字符串"}, ensure_ascii=False)
        if limit is None:
            limit = 20
        elif isinstance(limit, bool):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        elif not isinstance(limit, int):
            return _json.dumps({"error": "limit 必须是整数"}, ensure_ascii=False)
        limit = max(1, min(limit, 100))

        worker_id = worker_id.strip()
        task_id = task_id.strip()

        try:
            all_workers = durable_worker_store.list_workers(limit=500)
            all_tasks = durable_task_store.list_tasks(limit=500)
        except Exception:
            all_workers, all_tasks = [], []

        # Apply filters
        if worker_id:
            filtered_workers = [w for w in all_workers if w.worker_id == worker_id]
        else:
            filtered_workers = list(all_workers)
        if task_id:
            filtered_tasks = [t for t in all_tasks if t.task_id == task_id]
        elif worker_id:
            filtered_tasks = [t for t in all_tasks if t.worker_id == worker_id]
        else:
            filtered_tasks = list(all_tasks)
        # When task_id filter is set, also filter workers to those assigned to that task
        if task_id:
            filtered_workers = [w for w in filtered_workers if w.current_task_id == task_id]

        # Sort by worker_id / task_id for determinism
        filtered_workers.sort(key=lambda w: w.worker_id)
        filtered_tasks.sort(key=lambda t: t.task_id)

        workers_out = []
        for w in filtered_workers[:limit]:
            workers_out.append({
                "worker_id": w.worker_id,
                "status": w.status if isinstance(w.status, str) else w.status.value,
                "current_task_id": w.current_task_id or "",
            })

        tasks_out = []
        for t in filtered_tasks[:limit]:
            tasks_out.append({
                "task_id": t.task_id,
                "status": t.status,
                "worker_id": t.worker_id or "",
            })

        # Closeout candidates
        closeout_candidates = []
        try:
            cand_json = _list_worker_workspace_merge_closeout_candidates_json(
                worker_id=worker_id, task_id=task_id, limit=limit,
            )
            cand_data = _json.loads(cand_json)
            for c in cand_data.get("candidates", []):
                closeout_candidates.append({
                    "worker_id": c.get("worker_id", ""),
                    "task_id": c.get("task_id", ""),
                    "ready": bool(c.get("ready", False)),
                    "reason": c.get("reason", ""),
                    "task_status": c.get("task_status", ""),
                    "worker_status": c.get("worker_status", ""),
                    "lease_id": c.get("lease_id", ""),
                })
        except Exception:
            pass

        # Planned actions (reuse planner, apply filters)
        planned_actions = []
        try:
            plan_json = _plan_worker_lifecycle_actions_json(limit=limit)
            plan_data = _json.loads(plan_json)
            for a in plan_data.get("actions", []):
                a_worker_id = a.get("worker_id", "")
                a_task_id = a.get("task_id", "")
                # Apply filters: skip actions that don't match requested worker_id/task_id
                if worker_id and (not a_worker_id or a_worker_id != worker_id):
                    continue
                if task_id and (not a_task_id or a_task_id != task_id):
                    continue
                planned_actions.append({
                    "action": a.get("action", ""),
                    "worker_id": a_worker_id,
                    "task_id": a_task_id,
                })
        except Exception:
            pass

        # Build blocked_reasons and next_actions from state analysis
        blocked_reasons = []
        next_actions = []

        # Index workers by id for quick lookup
        worker_map = {w.worker_id: w for w in all_workers}
        task_map = {t.task_id: t for t in all_tasks}

        # Analyze each worker-task pair
        analyzed_pairs = set()
        for w in filtered_workers:
            wid = w.worker_id
            tid = w.current_task_id or ""
            if not tid:
                # Idle worker without task
                if w.status == WorkerStatus.IDLE:
                    pending_unassigned = [t for t in all_tasks if t.status == "pending" and not t.worker_id]
                    if pending_unassigned:
                        blocked_reasons.append({
                            "worker_id": wid, "task_id": "",
                            "reason": "dispatch_available",
                            "detail": "dispatch_blocked_in_scheduler",
                        })
                        next_actions.append({
                            "action": "dispatch_pending_task",
                            "worker_id": wid,
                            "task_id": "",
                            "reason": "dispatch_available_but_blocked",
                        })
                    else:
                        blocked_reasons.append({
                            "worker_id": wid, "task_id": "",
                            "reason": "no_pending_tasks",
                            "detail": "idle worker with no pending tasks to dispatch",
                        })
                elif w.status == WorkerStatus.OFFLINE:
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": "",
                        "reason": "worker_offline",
                        "detail": "no unsafe action",
                    })
                continue

            analyzed_pairs.add((wid, tid))
            task = task_map.get(tid)

            # Check closeout candidates for this pair
            pair_candidates = [c for c in closeout_candidates if c.get("worker_id") == wid and c.get("task_id") == tid]
            if pair_candidates:
                c = pair_candidates[0]
                if c.get("ready") and c.get("reason") == "ready_to_finalize":
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": tid,
                        "reason": "ready_closeout",
                        "detail": "workspace merge ready to finalize",
                    })
                    next_actions.append({
                        "action": "finalize_ready_workspace_merge",
                        "worker_id": wid, "task_id": tid,
                        "reason": "ready_closeout",
                    })
                elif c.get("reason") == "no_successful_apply":
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": tid,
                        "reason": "waiting_for_workspace_merge_apply",
                        "detail": "workspace merge not yet applied",
                    })
                elif c.get("reason") == "workspace_lease_invalid":
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": tid,
                        "reason": "missing_active_lease",
                        "detail": "workspace lease is invalid or missing",
                    })
                elif c.get("reason") == "already_finalized":
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": tid,
                        "reason": "already_finalized",
                        "detail": "workspace merge already finalized",
                    })
                elif c.get("reason") == "task_not_running":
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": tid,
                        "reason": "task_not_running",
                        "detail": "task is not in running state",
                    })
                elif c.get("reason") == "worker_task_mismatch":
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": tid,
                        "reason": "task_worker_mismatch",
                        "detail": "worker and task are not paired",
                    })
                elif c.get("reason") == "worker_unavailable":
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": tid,
                        "reason": "worker_offline",
                        "detail": "no unsafe action",
                    })
            else:
                # No closeout candidate - check basic state
                if w.status == WorkerStatus.OFFLINE:
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": tid,
                        "reason": "worker_offline",
                        "detail": "no unsafe action",
                    })
                elif task and task.status != "running":
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": tid,
                        "reason": "task_not_running",
                        "detail": f"task status is {task.status}",
                    })
                elif task and task.worker_id != wid:
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": tid,
                        "reason": "task_worker_mismatch",
                        "detail": "worker and task are not paired",
                    })
                elif w.status == WorkerStatus.RUNNING:
                    blocked_reasons.append({
                        "worker_id": wid, "task_id": tid,
                        "reason": "worker_running",
                        "detail": "worker is actively running, no closeout candidate yet",
                    })

        # For tasks without workers (pending unassigned)
        for t in filtered_tasks:
            if t.status == "pending" and not t.worker_id:
                idle_workers = [w for w in all_workers if w.status == WorkerStatus.IDLE and not w.current_task_id]
                if idle_workers:
                    blocked_reasons.append({
                        "worker_id": "", "task_id": t.task_id,
                        "reason": "pending_task_unassigned",
                        "detail": "dispatch_available_but_blocked",
                    })
                else:
                    blocked_reasons.append({
                        "worker_id": "", "task_id": t.task_id,
                        "reason": "pending_task_unassigned",
                        "detail": "no_idle_workers",
                    })

        # Retryable failed tasks
        for t in filtered_tasks:
            if t.status != "failed":
                continue
            if t.retry_count >= t.max_retries:
                blocked_reasons.append({
                    "worker_id": "", "task_id": t.task_id,
                    "reason": "retry_exhausted",
                    "detail": f"max retries ({t.max_retries}) reached",
                })
                continue
            # Check if active worker still attached
            owner_worker = None
            for w in all_workers:
                if w.current_task_id == t.task_id and w.status in (WorkerStatus.RUNNING, WorkerStatus.ASSIGNED):
                    owner_worker = w
                    break
            if owner_worker:
                blocked_reasons.append({
                    "worker_id": owner_worker.worker_id, "task_id": t.task_id,
                    "reason": "retry_blocked_active_worker",
                    "detail": "worker still active on this task",
                })
                continue
            # Retryable
            idle_workers = [w for w in all_workers if w.status == WorkerStatus.IDLE and not w.current_task_id]
            if idle_workers:
                blocked_reasons.append({
                    "worker_id": "", "task_id": t.task_id,
                    "reason": "retry_available",
                    "detail": f"retry {t.retry_count + 1}/{t.max_retries} available",
                })
                next_actions.append({
                    "action": "retry_failed_task",
                    "worker_id": "", "task_id": t.task_id,
                    "reason": "retry_available",
                })
            else:
                blocked_reasons.append({
                    "worker_id": "", "task_id": t.task_id,
                    "reason": "retry_blocked_missing_capacity",
                    "detail": "no idle workers available for retry",
                })

        # For explicitly filtered non-failed tasks, note retry_not_needed
        if task_id:
            for t in filtered_tasks:
                if t.status != "failed" and t.task_id == task_id:
                    blocked_reasons.append({
                        "worker_id": "", "task_id": t.task_id,
                        "reason": "retry_not_needed",
                        "detail": f"task status is {t.status}, not failed",
                    })

        # If nothing found at all
        if not filtered_workers and not filtered_tasks:
            blocked_reasons.append({
                "worker_id": "", "task_id": "",
                "reason": "no_action_needed",
                "detail": "no workers or tasks in system",
            })

        # Post-filter: when a specific filter is active, only keep entries
        # that match the requested filter value (or global no_action_needed).
        if task_id:
            blocked_reasons = [r for r in blocked_reasons if r.get("task_id") == task_id or r.get("reason") == "no_action_needed"]
            next_actions = [a for a in next_actions if a.get("task_id") == task_id]
        if worker_id:
            blocked_reasons = [r for r in blocked_reasons if r.get("worker_id") == worker_id or r.get("reason") == "no_action_needed"]
            next_actions = [a for a in next_actions if a.get("worker_id") == worker_id]

        # Summary
        idle_count = sum(1 for w in all_workers if w.status == WorkerStatus.IDLE)
        running_count = sum(1 for w in all_workers if w.status == WorkerStatus.RUNNING)
        offline_count = sum(1 for w in all_workers if w.status == WorkerStatus.OFFLINE)
        pending_count = sum(1 for t in all_tasks if t.status == "pending" and not t.worker_id)
        summary = {
            "total_workers": len(all_workers),
            "total_tasks": len(all_tasks),
            "idle_workers": idle_count,
            "running_workers": running_count,
            "offline_workers": offline_count,
            "pending_unassigned_tasks": pending_count,
            "ready_closeouts": sum(1 for c in closeout_candidates if c.get("ready")),
            "not_ready_closeouts": sum(1 for c in closeout_candidates if not c.get("ready")),
            "blocked_reason_count": len(blocked_reasons),
            "next_action_count": len(next_actions),
        }

        return _json.dumps({
            "scheduler": "worker_lifecycle",
            "filters": {"worker_id": worker_id, "task_id": task_id},
            "limit": limit,
            "summary": summary,
            "workers": workers_out,
            "tasks": tasks_out,
            "closeout_candidates": closeout_candidates,
            "planned_actions": planned_actions,
            "blocked_reasons": blocked_reasons,
            "next_actions": next_actions,
        }, ensure_ascii=False)

    registry.register(
        "explain_worker_lifecycle_scheduler_state",
        "解释 worker lifecycle scheduler 当前状态：为什么工作没有推进，下一步应该做什么。只读，不修改任何状态。",
        _explain_worker_lifecycle_scheduler_state_json,
        parameters={
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "按 worker_id 过滤，默认空（不过滤）"},
                "task_id": {"type": "string", "description": "按 task_id 过滤，默认空（不过滤）"},
                "limit": {"type": "integer", "description": "最大返回条数，默认 20，上限 100"},
            },
            "required": [],
        },
        permission=ToolPermission(category="task", risk="read"),
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

    def _plan_durable_recovery_json(task_id: str, checkpoint_id: str = "", step_id: str = "") -> str:
        task = durable_task_store.get_task(task_id)
        if task is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)

        # Parse step_id if provided
        parsed_step_id = None
        if step_id:
            try:
                parsed_step_id = max(0, int(step_id))
            except (TypeError, ValueError):
                return _json.dumps({"error": f"step_id 必须为整数: {step_id!r}"}, ensure_ascii=False)

        # Select checkpoint
        selected_cp = None
        reason = ""

        if checkpoint_id:
            for cp in task.checkpoints:
                if cp.checkpoint_id == checkpoint_id:
                    selected_cp = cp
                    break
            if selected_cp is None:
                return _json.dumps({"error": f"未找到 checkpoint: {checkpoint_id}"}, ensure_ascii=False)
            reason = "checkpoint_selected"
        elif parsed_step_id is not None:
            # Latest checkpoint for this step
            for cp in reversed(task.checkpoints):
                if cp.step_id == parsed_step_id:
                    selected_cp = cp
                    break
            reason = "checkpoint_selected" if selected_cp else "step_checkpoint_missing"
        else:
            # Latest checkpoint overall
            if task.checkpoints:
                selected_cp = task.checkpoints[-1]
                reason = "checkpoint_selected"
            else:
                reason = "no_checkpoint"

        # Terminal status check
        terminal_statuses = {"completed", "cancelled"}
        if task.status in terminal_statuses:
            can_resume = False
            reason = "terminal_status"
        else:
            can_resume = True

        # Compute next_step_id
        done_skipped = {StepStatus.DONE, StepStatus.SKIPPED}
        next_step_id = None

        if selected_cp:
            cp_step = next((s for s in task.steps if s.id == selected_cp.step_id), None)
            if cp_step and cp_step.status not in done_skipped:
                next_step_id = selected_cp.step_id

        if next_step_id is None:
            for step in task.steps:
                if step.status not in done_skipped:
                    next_step_id = step.id
                    break

        if next_step_id is None:
            # All steps done/skipped
            if can_resume:
                reason = "all_steps_done"
            next_step_id = task.current_step

        incomplete_count = sum(1 for s in task.steps if s.status not in done_skipped)

        if selected_cp:
            resume_policy = "from_checkpoint"
        else:
            resume_policy = task.resume_policy or "from_step"

        try:
            registry.durable_event_store.record(
                event_type=RECOVERY_PLANNED,
                task_id=task_id,
                checkpoint_id=selected_cp.checkpoint_id if selected_cp else "",
                summary="recovery planned",
                payload={
                    "operation": "plan_recovery",
                    "can_resume": can_resume,
                    "resume_policy": resume_policy,
                    "reason": reason,
                    "selected_checkpoint_present": selected_cp is not None,
                    "checkpoint_step_id": selected_cp.step_id if selected_cp else None,
                    "next_step_id": next_step_id,
                    "checkpoint_count": len(task.checkpoints),
                    "step_count": len(task.steps),
                    "incomplete_step_count": incomplete_count,
                    "trace_ref_count": len(task.trace_refs),
                    "worker_id_present": bool(task.worker_id),
                    "requested_checkpoint_id_present": bool(checkpoint_id),
                    "requested_step_id_present": parsed_step_id is not None,
                },
                source="registry",
                severity="info",
            )
        except Exception:
            pass

        return _json.dumps({
            "task_id": task.task_id,
            "status": task.status,
            "can_resume": can_resume,
            "resume_policy": resume_policy,
            "selected_checkpoint_id": selected_cp.checkpoint_id if selected_cp else None,
            "checkpoint_step_id": selected_cp.step_id if selected_cp else None,
            "next_step_id": next_step_id,
            "checkpoint_count": len(task.checkpoints),
            "step_count": len(task.steps),
            "incomplete_step_count": incomplete_count,
            "trace_ref_count": len(task.trace_refs),
            "worker_id_present": bool(task.worker_id),
            "reason": reason,
        }, ensure_ascii=False)

    registry.register(
        "plan_durable_recovery",
        "只读检查 durable task 状态和 checkpoint，返回安全的恢复计划。不修改 task 状态，不执行恢复。",
        _plan_durable_recovery_json,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "durable task id，例如 dtask_1",
                },
                "checkpoint_id": {
                    "type": "string",
                    "description": "可选，指定 checkpoint id；不指定则自动选择最新的",
                },
                "step_id": {
                    "type": "string",
                    "description": "可选，按步骤选择 checkpoint；不指定则选最新",
                },
            },
            "required": ["task_id"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )

    def _get_durable_task_timeline_json(task_id: str, limit: int = 50) -> str:
        task = durable_task_store.get_task(task_id)
        if task is None:
            return _json.dumps({"error": f"未找到 durable task: {task_id}"}, ensure_ascii=False)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            return _json.dumps({"error": f"limit 必须为整数: {limit!r}"}, ensure_ascii=False)
        limit = max(1, min(limit, 200))

        try:
            events = durable_event_store.list_events(task_id=task_id, max_results=500)
        except Exception:
            return _json.dumps({"error": "事件查询失败"}, ensure_ascii=False)

        # list_events returns newest first; reverse for chronological oldest-first
        events = list(reversed(events))
        total_count = len(events)
        events = events[:limit]

        event_summaries = []
        for ev in events:
            payload_keys = sorted(ev.payload.keys()) if ev.payload else []
            event_summaries.append({
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "created_at": ev.created_at,
                "source": ev.source,
                "severity": ev.severity,
                "checkpoint_id": ev.checkpoint_id,
                "checkpoint_id_present": bool(ev.checkpoint_id),
                "trace_id_present": bool(ev.trace_id),
                "worker_id_present": bool(ev.worker_id),
                "summary_present": bool(ev.summary),
                "payload_key_count": len(payload_keys),
                "payload_keys": payload_keys,
            })

        return _json.dumps({
            "task_id": task.task_id,
            "status": task.status,
            "event_count": total_count,
            "returned_event_count": len(event_summaries),
            "checkpoint_count": len(task.checkpoints),
            "trace_ref_count": len(task.trace_refs),
            "worker_id_present": bool(task.worker_id),
            "events": event_summaries,
        }, ensure_ascii=False)

    registry.register(
        "get_durable_task_timeline",
        "只读返回 durable task 的安全事件时间线（最旧在前），包含 bounded task 摘要和 event summaries。",
        _get_durable_task_timeline_json,
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "durable task id，例如 dtask_1",
                },
                "limit": {
                    "type": "integer",
                    "description": "最多返回事件数，默认 50，范围 1-200",
                },
            },
            "required": ["task_id"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )

    registry.register(
        "list_tool_permissions",
        "查看所有工具的权限分类和哪些工具需要确认。",
        registry.describe_permissions,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="local", risk="read"),
    )

    return registry
