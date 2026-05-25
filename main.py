from pathlib import Path

from mini_agent.cli import MiniAgentCLI
from mini_agent.controller import MiniAgent
from mini_agent.providers.factory import build_llm_client
from mini_agent.settings import load_settings
from mini_agent.tools import build_default_registry


def main() -> None:
    settings = load_settings()
    llm = build_llm_client(settings)
    registry = build_default_registry()
    agent = MiniAgent(registry, llm=llm)
    MiniAgentCLI(agent, registry, settings=settings, root=Path.cwd()).run()


if __name__ == "__main__":
    main()
