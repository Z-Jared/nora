import re
from typing import Optional, Protocol

from mini_agent.context_window import ContextWindow
from mini_agent.memory import ConversationMemory
from mini_agent.providers.base import LLMError, LLMResponse
from mini_agent.registry import ToolRegistry


class LLMClient(Protocol):
    def complete(self, user_input: str) -> str:
        ...


class MiniAgent:
    max_tool_rounds = 4

    def __init__(
        self,
        tools: ToolRegistry,
        llm: Optional[LLMClient] = None,
        memory: Optional[ConversationMemory] = None,
        context_window: Optional[ContextWindow] = None,
    ):
        self.tools = tools
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.context_window = context_window or ContextWindow()

    def run(self, user_input: str) -> str:
        text = user_input.strip()

        if self.llm and hasattr(self.llm, "chat"):
            try:
                return self._record_turn(text, self._run_with_llm_tools(text))
            except LLMError as error:
                local_answer = self._run_local(text)
                if local_answer:
                    return self._record_turn(text, local_answer)
                return self._record_turn(text, f"模型调用失败: {error}")

        local_answer = self._run_local(text)
        if local_answer:
            return self._record_turn(text, local_answer)

        if self.llm:
            try:
                return self._record_turn(text, self.llm.complete(text))
            except LLMError as error:
                return self._record_turn(text, f"模型调用失败: {error}")

        return self._record_turn(text, self._help_message())

    def _run_with_llm_tools(self, text: str) -> str:
        messages = self.memory.messages() + [{"role": "user", "content": text}]
        tools = self.tools.to_openai_tools()

        for _ in range(self.max_tool_rounds):
            response: LLMResponse = self.llm.chat(messages, tools=tools)
            if not response.tool_calls:
                return response.content or self._help_message()

            messages.append(response.to_assistant_message())
            for tool_call in response.tool_calls:
                result = self._call_tool(tool_call.name, tool_call.arguments)
                result = self.context_window.compact_tool_result(tool_call.name, result)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.call_id,
                        "name": tool_call.name,
                        "content": result,
                    }
                )

        raise LLMError("Tool call loop exceeded max rounds.")

    def _record_turn(self, user_input: str, answer: str) -> str:
        self.memory.add_user(user_input)
        self.memory.add_assistant(answer)
        return answer

    def _call_tool(self, name: str, arguments: dict) -> str:
        try:
            return self.tools.call(name, **arguments)
        except Exception as error:
            return f"工具调用失败: {error}"

    def _run_local(self, text: str) -> Optional[str]:
        if self._looks_like_calculation(text):
            expression = self._extract_expression(text)
            return f"计算结果: {self.tools.call('calculate', expression=expression)}"

        if any(keyword in text for keyword in ("现在几点", "当前时间", "时间")):
            return f"当前时间: {self.tools.call('current_time')}"

        if text.startswith("保存笔记"):
            note = text.removeprefix("保存笔记").strip()
            if not note:
                return "请提供要保存的笔记内容。"
            return self.tools.call("save_note", text=note)

        if text in ("读取笔记", "查看笔记", "笔记"):
            return self.tools.call("read_notes")

        return None

    def _help_message(self) -> str:
        return (
            "我还不会处理这个任务。你可以试试: "
            "计算 2 + 3 * 4、现在几点、保存笔记 内容、读取笔记。"
        )

    def _looks_like_calculation(self, text: str) -> bool:
        return text.startswith(("计算", "算一下", "帮我算")) or bool(
            re.fullmatch(r"[0-9+\-*/(). %]+", text)
        )

    def _extract_expression(self, text: str) -> str:
        cleaned = text
        for prefix in ("帮我算一下", "帮我算", "算一下", "计算"):
            if cleaned.startswith(prefix):
                cleaned = cleaned.removeprefix(prefix)
                break

        return cleaned.strip()
