from mini_agent.controller import MiniAgent
from mini_agent.providers.factory import build_llm_client
from mini_agent.settings import load_settings
from mini_agent.tools import build_default_registry


def main() -> None:
    settings = load_settings()
    llm = build_llm_client(settings)
    agent = MiniAgent(build_default_registry(), llm=llm)
    print("Mini Agent 已启动。输入 exit 或 quit 退出。")
    if llm:
        print(f"LLM 已启用: {settings.base_url} / {settings.model}")
    else:
        print("LLM 未启用: 未检测到 LLM_API_KEY 或 OPENAI_API_KEY，当前使用本地规则。")

    while True:
        try:
            user_input = input("你: ").strip()
        except EOFError:
            print()
            break

        if user_input.lower() in {"exit", "quit"}:
            break

        if not user_input:
            continue

        print(f"Agent: {agent.run(user_input)}")


if __name__ == "__main__":
    main()
