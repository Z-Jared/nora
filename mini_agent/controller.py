import re
from dataclasses import dataclass
from typing import Optional, Protocol

from mini_agent.context_window import ContextWindow
from mini_agent.memory import ConversationMemory
from mini_agent.providers.base import LLMError, LLMResponse
from mini_agent.registry import ToolRegistry
from mini_agent.tool_results import ToolResultStore


class LLMClient(Protocol):
    def complete(self, user_input: str) -> str:
        ...


@dataclass(frozen=True)
class AutonomousStepRecord:
    step: int
    action: str
    status: str
    result: str


class MiniAgent:
    max_tool_rounds = 4
    max_autonomous_steps = 6

    def __init__(
        self,
        tools: ToolRegistry,
        llm: Optional[LLMClient] = None,
        memory: Optional[ConversationMemory] = None,
        context_window: Optional[ContextWindow] = None,
        tool_result_store: Optional[ToolResultStore] = None,
        autonomous_disabled_tools: Optional[set[str]] = None,
    ):
        self.tools = tools
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.context_window = context_window or ContextWindow()
        self.tool_result_store = tool_result_store
        self.autonomous_disabled_tools = autonomous_disabled_tools or set()

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

    def run_autonomous(self, goal: str, max_steps: Optional[int] = None) -> str:
        goal = goal.strip()
        if not goal:
            return "请提供自主执行目标。"
        if not self.llm or not hasattr(self.llm, "chat"):
            return "受控自主执行需要配置支持工具调用的模型。"

        step_limit = self._autonomous_step_limit(max_steps)
        messages = self.memory.messages() + [{"role": "user", "content": self._autonomous_instruction(goal)}]
        tools = self._autonomous_tools()
        records = []
        final_status = "max_steps_reached"

        for step in range(1, step_limit + 1):
            try:
                response: LLMResponse = self.llm.chat(messages, tools=tools)
            except LLMError as error:
                final_status = "blocked"
                records.append(
                    AutonomousStepRecord(
                        step=step,
                        action="model",
                        status="blocked",
                        result=f"模型调用失败: {error}",
                    )
                )
                break
            if not response.tool_calls:
                final_status = self._autonomous_status_from_final(response.content)
                records.append(
                    AutonomousStepRecord(
                        step=step,
                        action="final_response",
                        status=final_status,
                        result=self._shorten_trace_result(response.content or self._help_message()),
                    )
                )
                break

            messages.append(response.to_assistant_message())
            tool_call = response.tool_calls[0]
            raw_result = self._call_tool(tool_call.name, tool_call.arguments)
            result = self._compact_tool_result(tool_call.name, raw_result)
            status = self._autonomous_status_from_result(raw_result)
            if len(response.tool_calls) > 1:
                result = result + "\n[自主模式每步只允许一个工具调用，其余 tool calls 已忽略。]"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.call_id,
                    "name": tool_call.name,
                    "content": result,
                }
            )
            records.append(
                AutonomousStepRecord(
                    step=step,
                    action=f"tool:{tool_call.name}",
                    status=status,
                    result=self._shorten_trace_result(result),
                )
            )
            if status == "blocked":
                final_status = "blocked"
                break
        else:
            final_status = "max_steps_reached"

        answer = self._format_autonomous_report(goal, final_status, records)
        return self._record_turn(f"/auto {goal}", answer)

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
                result = self._compact_tool_result(tool_call.name, result)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.call_id,
                        "name": tool_call.name,
                        "content": result,
                    }
                )

        messages.append(
            {
                "role": "user",
                "content": "工具调用轮数已用完。请只基于已有工具结果给出最终回答，不要再调用工具。",
            }
        )
        response = self.llm.chat(messages, tools=[])
        if response.tool_calls:
            raise LLMError("Tool call loop exceeded max rounds.")
        return response.content or self._help_message()

    def _autonomous_tools(self) -> list[dict]:
        tools = self.tools.to_openai_tools()
        if not self.autonomous_disabled_tools:
            return tools
        return [
            tool
            for tool in tools
            if (tool.get("function") or {}).get("name") not in self.autonomous_disabled_tools
        ]

    def _autonomous_step_limit(self, max_steps: Optional[int]) -> int:
        if max_steps is None:
            return self.max_autonomous_steps
        try:
            requested = int(max_steps)
        except (TypeError, ValueError):
            requested = self.max_autonomous_steps
        return max(1, min(requested, self.max_autonomous_steps))

    def _autonomous_instruction(self, goal: str) -> str:
        return "\n".join(
            [
                "受控自主执行请求。",
                f"目标: {goal}",
                "规则:",
                "- 在有限步骤内推进目标；每步最多调用一个必要工具，或直接给出最终结论。",
                "- 优先使用只读、预览和检查工具，再考虑写入、执行、Git、浏览器交互或进程工具。",
                "- 高风险工具可能需要用户确认；如果被取消、拒绝或失败，请停止并说明阻塞原因。",
                "- 不要尝试绕过权限确认，不要无限循环。",
                "- 完成时给出 done 总结；无法继续时给出 blocked 原因。",
            ]
        )

    def _autonomous_status_from_result(self, result: str) -> str:
        if result == "已取消操作。" or "工具调用失败" in result or "拒绝" in result:
            return "blocked"
        return "continue"

    def _autonomous_status_from_final(self, content: str) -> str:
        content = content or ""
        lowered = content.lower()
        if "blocked" in lowered or "阻塞" in content or "无法继续" in content:
            return "blocked"
        return "done"

    def _format_autonomous_report(self, goal: str, status: str, records: list[AutonomousStepRecord]) -> str:
        lines = [f"受控自主执行已停止: {status}", f"目标: {goal}", "步骤:"]
        if not records:
            lines.append("- 未执行任何步骤。")
            return "\n".join(lines)
        for record in records:
            lines.extend(
                [
                    f"{record.step}. action={record.action} status={record.status}",
                    f"   result: {record.result}",
                ]
            )
        return "\n".join(lines)

    def _shorten_trace_result(self, text: str, limit: int = 500) -> str:
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "\n..."

    def _record_turn(self, user_input: str, answer: str) -> str:
        self.memory.add_user(user_input)
        self.memory.add_assistant(answer)
        return answer

    def _compact_tool_result(self, tool_name: str, result: str) -> str:
        compacted = self.context_window.compact_tool_result(tool_name, result)
        if compacted == result or not self.tool_result_store:
            return compacted
        result_id = self.tool_result_store.save(tool_name, result)
        if not result_id:
            return compacted + "\n[result_id unavailable: sensitive result not cached]"
        return compacted + f"\n[result_id={result_id} use read_tool_result to inspect more]"

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
