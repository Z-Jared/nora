from pathlib import Path

from mini_agent.cli import MiniAgentCLI
from mini_agent.config import load_agent_config
from mini_agent.context_window import ContextWindow
from mini_agent.controller import MiniAgent
from mini_agent.providers.factory import build_llm_client
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
        context_summary_path=config.resolve_path(root, config.paths.context_summaries),
        process_profiles=config.processes.profiles,
        disabled_tools=config.disabled_tools(),
        permission_overrides=config.permission_overrides(),
    )
    tool_result_store = ToolResultStore(root / "data" / "tool_results.jsonl")
    context_window = ContextWindow(
        max_tool_result_chars=config.context_window.max_tool_result_chars,
        head_chars=config.context_window.head_chars,
        tail_chars=config.context_window.tail_chars,
    )
    agent = MiniAgent(
        registry,
        llm=llm,
        context_window=context_window,
        tool_result_store=tool_result_store,
    )
    MiniAgentCLI(agent, registry, settings=settings, root=root).run()


if __name__ == "__main__":
    main()
