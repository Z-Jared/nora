from pathlib import Path

from mini_agent.cli import MiniAgentCLI
from mini_agent.config import load_agent_config
from mini_agent.context_summary import ContextSummaryStore
from mini_agent.context_system import ContextSystem
from mini_agent.context_window import ContextWindow
from mini_agent.controller import MiniAgent
from mini_agent.database import NoraDB
from mini_agent.memory import LongTermMemory
from mini_agent.migration import migrate_jsonl_to_sqlite
from mini_agent.providers.factory import build_llm_client
from mini_agent.rag import ProjectRAG
from mini_agent.plugins import load_plugins
from mini_agent.session import SessionStore
from mini_agent.settings import load_settings, required_env_vars, env_alternatives
from mini_agent.tool_results import ToolResultStore
from mini_agent.tools import build_default_registry


def build_agent(root: Path = None):
    root = root or Path.cwd()
    config = load_agent_config(root / "agent.yaml")
    settings = config.apply_to_llm_settings(load_settings())
    llm = build_llm_client(settings)

    # Create database and run migration
    db_path = config.resolve_path(root, config.paths.database)
    db = NoraDB(db_path)
    data_dir = root / "data"
    logs_dir = root / "logs"
    migrated = migrate_jsonl_to_sqlite(db, data_dir, logs_dir)
    if migrated:
        print(f"Migrated to SQLite: {', '.join(migrated)}")

    registry = build_default_registry(
        workspace_root=root,
        notes_path=config.resolve_path(root, config.paths.notes),
        log_path=config.resolve_path(root, config.paths.tool_logs),
        long_term_memory_path=config.resolve_path(root, config.paths.long_term_memory),
        task_state_path=config.resolve_path(root, config.paths.task_state),
        task_history_path=config.resolve_path(root, config.paths.task_history),
        context_summary_path=config.resolve_path(root, config.paths.context_summaries),
        process_profiles=config.processes.profiles,
        disabled_tools=config.disabled_tools(),
        permission_overrides=config.permission_overrides(),
        rag_include_paths=config.rag.include_paths,
        rag_exclude_dirs=config.rag.exclude_dirs,
        rag_max_file_bytes=config.rag.max_file_bytes,
        rag_chunk_size=config.rag.chunk_size,
        rag_chunk_overlap=config.rag.chunk_overlap,
        db=db,
    )
    plugin_names = load_plugins(registry, root / "plugins")
    if plugin_names:
        print(f"Loaded plugins: {', '.join(plugin_names)}")
    tool_result_store = ToolResultStore(db=db)
    context_window = ContextWindow(
        max_tool_result_chars=config.context_window.max_tool_result_chars,
        head_chars=config.context_window.head_chars,
        tail_chars=config.context_window.tail_chars,
    )
    context_system = ContextSystem(
        rag=ProjectRAG(
            root,
            include_paths=config.rag.include_paths,
            exclude_dirs=config.rag.exclude_dirs,
            max_file_bytes=config.rag.max_file_bytes,
            chunk_size=config.rag.chunk_size,
            chunk_overlap=config.rag.chunk_overlap,
        ),
        long_term_memory=LongTermMemory(db=db),
        context_summaries=ContextSummaryStore(db=db),
        context_window=context_window,
    )
    agent = MiniAgent(
        registry,
        llm=llm,
        context_window=context_window,
        tool_result_store=tool_result_store,
        autonomous_disabled_tools=config.autonomous_disabled_tools(),
        context_system=context_system,
        max_tool_calls_per_turn=config.budgets.max_tool_calls_per_turn,
        system_prompt=config.system_prompt,
        trace_store=getattr(registry, "trace_store", None),
        event_store=getattr(registry, "durable_event_store", None),
    )
    agent.durable_task_store = getattr(registry, "durable_task_store", None)
    session_store = SessionStore(db=db)
    return agent, registry, settings, session_store, root


def main() -> None:
    agent, registry, settings, session_store, root = build_agent()
    MiniAgentCLI(agent, registry, settings=settings, root=root, session_store=session_store).run()


def serve(host: str = "", port: int = 0, api_token: str = "") -> None:
    import os
    from mini_agent.http_server import create_server

    host = host or os.environ.get("NORA_HOST", "127.0.0.1")
    port = port or int(os.environ.get("NORA_PORT", "8080"))
    api_token = api_token or os.environ.get("NORA_API_TOKEN", "")

    agent, _registry, _settings, session_store, root = build_agent()
    static_dir = Path(__file__).resolve().parent / "static"
    task_manager = getattr(_registry, "task_manager", None)
    long_term_memory = getattr(_registry, "long_term_memory", None)
    server = create_server(agent, host=host, port=port, session_store=session_store, task_manager=task_manager, long_term_memory=long_term_memory, api_token=api_token, static_dir=static_dir, llm_provider=_settings.provider, llm_model=_settings.model, workspace=str(root), llm_configured=_settings.is_llm_enabled, llm_has_api_key=bool(_settings.api_key), llm_required_env=required_env_vars(_settings.provider), llm_env_alternatives=env_alternatives(_settings.provider))
    print(f"Nora HTTP server started on http://{host}:{port}")
    print(f"Workspace: {root}")
    if api_token:
        print("Auth: Bearer token required")
    else:
        print("Auth: disabled (set NORA_API_TOKEN to enable)")
    print("Endpoints: /health /chat /chat/stream /tools /session/save /session/load /session/list /ws")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()
