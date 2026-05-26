from pathlib import Path

from mini_agent.cli import MiniAgentCLI
from mini_agent.config import load_agent_config
from mini_agent.context_summary import ContextSummaryStore
from mini_agent.context_system import ContextSystem
from mini_agent.context_window import ContextWindow
from mini_agent.controller import MiniAgent
from mini_agent.memory import LongTermMemory
from mini_agent.providers.factory import build_llm_client
from mini_agent.rag import ProjectRAG
from mini_agent.settings import load_settings
from mini_agent.tool_results import ToolResultStore
from mini_agent.tools import build_default_registry


def main() -> None:
    root = Path.cwd()
    config = load_agent_config(root / "agent.yaml")
    settings = config.apply_to_llm_settings(load_settings())
    llm = build_llm_client(settings)
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
    )
    tool_result_store = ToolResultStore(root / "data" / "tool_results.jsonl")
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
        long_term_memory=LongTermMemory(config.resolve_path(root, config.paths.long_term_memory)),
        context_summaries=ContextSummaryStore(config.resolve_path(root, config.paths.context_summaries)),
        context_window=context_window,
    )
    agent = MiniAgent(
        registry,
        llm=llm,
        context_window=context_window,
        tool_result_store=tool_result_store,
        autonomous_disabled_tools=config.autonomous_disabled_tools(),
        context_system=context_system,
    )
    MiniAgentCLI(agent, registry, settings=settings, root=root).run()
