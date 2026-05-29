import re
from dataclasses import dataclass
from typing import Generator, Optional, Protocol

from mini_agent.context_system import ContextSystem
from mini_agent.context_window import ContextWindow
from mini_agent.memory import ConversationMemory
from mini_agent.providers.base import LLMError, LLMResponse
from mini_agent.registry import ToolRegistry
from mini_agent.tool_cache import ToolResultCache
from mini_agent.tool_results import ToolResultStore
from mini_agent.traces import TraceStore, build_trace


class LLMClient(Protocol):
    def complete(self, user_input: str) -> str:
        ...


@dataclass(frozen=True)
class AutonomousStepRecord:
    step: int
    action: str
    status: str
    result: str


@dataclass(frozen=True)
class ToolRunRecord:
    name: str
    status: str
    result_preview: str


@dataclass(frozen=True)
class RunReport:
    status: str
    steps_used: int
    tool_calls: list[ToolRunRecord]
    tool_call_limit: int = 0
    remaining_tool_calls: int = 0
    failure: str = ""
    next_step: str = ""

    def format(self) -> str:
        tools = ", ".join(f"{record.name}({record.status})" for record in self.tool_calls) or "无"
        failure = self.failure or "无"
        next_step = self.next_step or "无"
        return "\n".join(
            [
                "运行报告:",
                f"- 状态: {self.status}",
                f"- 步骤: {self.steps_used}",
                f"- 工具预算: {len(self.tool_calls)}/{self.tool_call_limit}，剩余 {self.remaining_tool_calls}",
                f"- 工具: {tools}",
                f"- 失败: {failure}",
                f"- 下一步: {next_step}",
            ]
        )


@dataclass(frozen=True)
class AutonomousPreflight:
    goal: str
    max_steps: int
    available_tool_count: int
    hidden_tools: list[str]
    high_risk_tools: list[str]


class MiniAgent:
    max_tool_rounds = 4
    max_autonomous_steps = 6
    default_max_tool_calls_per_turn = 8

    def __init__(
        self,
        tools: ToolRegistry,
        llm: Optional[LLMClient] = None,
        memory: Optional[ConversationMemory] = None,
        context_window: Optional[ContextWindow] = None,
        tool_result_store: Optional[ToolResultStore] = None,
        autonomous_disabled_tools: Optional[set[str]] = None,
        context_system: Optional[ContextSystem] = None,
        max_tool_calls_per_turn: int = default_max_tool_calls_per_turn,
        system_prompt: str = "",
        tool_cache: Optional[ToolResultCache] = None,
        trace_store: Optional[TraceStore] = None,
    ):
        self.tools = tools
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.context_window = context_window or ContextWindow()
        self.tool_result_store = tool_result_store
        self.autonomous_disabled_tools = autonomous_disabled_tools or set()
        self.context_system = context_system
        self.system_prompt = system_prompt
        self.tool_cache = tool_cache or ToolResultCache()
        self.trace_store = trace_store
        self.max_tool_calls_per_turn = max(1, int(max_tool_calls_per_turn or self.default_max_tool_calls_per_turn))
        self.last_run_report = RunReport(
            status="idle",
            steps_used=0,
            tool_calls=[],
            tool_call_limit=self.max_tool_calls_per_turn,
            remaining_tool_calls=self.max_tool_calls_per_turn,
        )
        self._active_tool_records: list[ToolRunRecord] = []

    def run(self, user_input: str) -> str:
        answer = ""
        for event in self.run_events(user_input):
            if event["type"] == "delta":
                answer += event["content"]
            elif event["type"] == "error":
                answer = answer or event["error"]
        return answer

    def run_events(self, user_input: str) -> Generator[dict, None, None]:
        text = user_input.strip()
        self._start_run_report()
        trace_events: list[dict] = []

        yield from self._run_events_inner(text, trace_events)
        self._maybe_record_trace(text, trace_events)

    def _run_events_inner(self, text: str, trace_events: list[dict]) -> Generator[dict, None, None]:
        def _col(event: dict) -> Generator[dict, None, None]:
            trace_events.append(event)
            yield event

        def _collect(gen) -> Generator[dict, None, None]:
            for evt in gen:
                trace_events.append(evt)
                yield evt

        yield from _col({"type": "typing"})

        try:
            if self.llm and hasattr(self.llm, "chat"):
                try:
                    yield from _collect(self._emit_answer(text, self._run_with_llm_tools_events(text)))
                    return
                except LLMError as error:
                    if self._has_local_answer(text):
                        yield from _collect(self._emit_answer(text, self._run_local_events(text)))
                        return
                    yield from _collect(self._emit_blocked(text, f"模型调用失败: {error}"))
                    return

            if self._has_local_answer(text):
                yield from _collect(self._emit_answer(text, self._run_local_events(text)))
                return

            if self.llm:
                try:
                    yield from _collect(self._emit_answer(text, self.llm.complete(text)))
                    return
                except LLMError as error:
                    yield from _collect(self._emit_blocked(text, f"模型调用失败: {error}"))
                    return

            yield from _collect(self._emit_answer(text, self._help_message()))
        except Exception as error:
            error_msg = str(error)[:500]
            yield from _col({"type": "error", "error": error_msg})
            self._finish_turn(text, error_msg, status="blocked", failure=error_msg)
            yield from _col(self._done_event())

    def _emit_answer(self, user_input: str, answer_or_gen) -> Generator[dict, None, None]:
        if isinstance(answer_or_gen, str):
            yield {"type": "delta", "content": answer_or_gen}
            answer = answer_or_gen
        else:
            answer = ""
            for event in answer_or_gen:
                yield event
                if event["type"] == "delta":
                    answer += event["content"]
        answer = self._finish_turn(user_input, answer)
        yield self._done_event()

    def _maybe_record_trace(self, user_input: str, trace_events: list[dict]) -> None:
        if not self.trace_store:
            return
        report = self.last_run_report
        trace_id = self.trace_store.next_trace_id()
        trace = build_trace(
            trace_id=trace_id,
            user_input=user_input,
            status=report.status,
            events=trace_events,
            tool_records=report.tool_calls,
            failure=report.failure,
        )
        try:
            self.trace_store.record(trace)
        except Exception:
            return
        durable_store = getattr(self, "durable_task_store", None)
        if durable_store:
            try:
                durable_store.add_trace_ref(trace_id)
            except Exception:
                pass

    def _has_local_answer(self, text: str) -> bool:
        if self._looks_like_calculation(text):
            return True
        if any(keyword in text for keyword in ("现在几点", "当前时间", "时间")):
            return True
        if text.startswith("保存笔记"):
            return True
        if text in ("读取笔记", "查看笔记", "笔记"):
            return True
        return False

    def _emit_blocked(self, user_input: str, error_msg: str) -> Generator[dict, None, None]:
        yield {"type": "delta", "content": error_msg}
        self._finish_turn(user_input, error_msg, status="blocked", failure=error_msg)
        yield self._done_event()

    def _done_event(self) -> dict:
        report = self.last_run_report
        return {
            "type": "done",
            "status": report.status,
            "steps_used": report.steps_used,
            "tool_calls": len(report.tool_calls),
            "message_count": len(self.memory.messages()),
            "failure": report.failure or "",
        }

    def _run_with_llm_tools_events(self, text: str) -> Generator[dict, None, None]:
        messages = self._messages_for_user_input(text)
        tools = self.tools.to_openai_tools()
        tool_calls_seen = False

        for _ in range(self.max_tool_rounds):
            response: LLMResponse = self.llm.chat(messages, tools=tools)
            if not response.tool_calls:
                if tool_calls_seen and hasattr(self.llm, "stream_chat"):
                    yield from self._stream_answer(messages, [])
                    return
                yield {"type": "delta", "content": response.content or self._help_message()}
                return

            tool_calls_seen = True
            messages.append(response.to_assistant_message())
            for tool_call in response.tool_calls:
                yield {"type": "tool_call_start", "name": tool_call.name, "arguments": tool_call.arguments}
                result = self._call_tool(tool_call.name, tool_call.arguments)
                result = self._compact_tool_result(tool_call.name, result)
                last_record = self._active_tool_records[-1] if self._active_tool_records else None
                yield {
                    "type": "tool_call_result",
                    "name": tool_call.name,
                    "status": last_record.status if last_record else "ok",
                    "result": result,
                }
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
        _has_stream = hasattr(self.llm, "stream_chat")
        if _has_stream:
            yield from self._stream_answer(messages, [])
        else:
            response = self.llm.chat(messages, tools=[])
            if response.tool_calls:
                raise LLMError("Tool call loop exceeded max rounds.")
            yield {"type": "delta", "content": response.content or self._help_message()}

    def _stream_answer(self, messages: list[dict], tools: list[dict]) -> Generator[dict, None, None]:
        full_content = ""
        for chunk in self.llm.stream_chat(messages, tools=tools or None):
            yield {"type": "delta", "content": chunk}
            full_content += chunk
        if not full_content.strip():
            yield {"type": "delta", "content": self._help_message()}

    def _run_local_events(self, text: str) -> Generator[dict, None, None]:
        if self._looks_like_calculation(text):
            expression = self._extract_expression(text)
            yield {"type": "tool_call_start", "name": "calculate", "arguments": {"expression": expression}}
            result = self._call_tool("calculate", {"expression": expression})
            last_record = self._active_tool_records[-1] if self._active_tool_records else None
            yield {"type": "tool_call_result", "name": "calculate", "status": last_record.status if last_record else "ok", "result": result}
            yield {"type": "delta", "content": f"计算结果: {result}"}
            return

        if any(keyword in text for keyword in ("现在几点", "当前时间", "时间")):
            yield {"type": "tool_call_start", "name": "current_time", "arguments": {}}
            result = self._call_tool("current_time", {})
            last_record = self._active_tool_records[-1] if self._active_tool_records else None
            yield {"type": "tool_call_result", "name": "current_time", "status": last_record.status if last_record else "ok", "result": result}
            yield {"type": "delta", "content": f"当前时间: {result}"}
            return

        if text.startswith("保存笔记"):
            note = text.removeprefix("保存笔记").strip()
            if not note:
                yield {"type": "delta", "content": "请提供要保存的笔记内容。"}
                return
            yield {"type": "tool_call_start", "name": "save_note", "arguments": {"text": note}}
            result = self._call_tool("save_note", {"text": note})
            last_record = self._active_tool_records[-1] if self._active_tool_records else None
            yield {"type": "tool_call_result", "name": "save_note", "status": last_record.status if last_record else "ok", "result": result}
            yield {"type": "delta", "content": result}
            return

        if text in ("读取笔记", "查看笔记", "笔记"):
            yield {"type": "tool_call_start", "name": "read_notes", "arguments": {}}
            result = self._call_tool("read_notes", {})
            last_record = self._active_tool_records[-1] if self._active_tool_records else None
            yield {"type": "tool_call_result", "name": "read_notes", "status": last_record.status if last_record else "ok", "result": result}
            yield {"type": "delta", "content": result}
            return

    def run_autonomous(self, goal: str, max_steps: Optional[int] = None) -> str:
        goal = goal.strip()
        if not goal:
            return "请提供自主执行目标。"
        if not self.llm or not hasattr(self.llm, "chat"):
            return "受控自主执行需要配置支持工具调用的模型。"
        self._start_run_report()

        step_limit = self._autonomous_step_limit(max_steps)
        tools = self._autonomous_tools()
        preflight = self._autonomous_preflight(goal, step_limit, tools)
        messages = self._messages_for_user_input(goal, self._autonomous_instruction(goal, preflight))
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

        answer = self._format_autonomous_report(goal, final_status, records, preflight)
        tool_records = [
            ToolRunRecord(
                name=record.action.removeprefix("tool:"),
                status="ok" if record.status == "continue" else record.status,
                result_preview=record.result,
            )
            for record in records
            if record.action.startswith("tool:")
        ]
        failure = "" if final_status == "done" else _first_non_ok_tool_failure(tool_records) or final_status
        self.last_run_report = RunReport(
            status="done" if final_status == "done" else "blocked",
            steps_used=len(records),
            tool_calls=tool_records,
            tool_call_limit=self.max_tool_calls_per_turn,
            remaining_tool_calls=max(0, self.max_tool_calls_per_turn - len(tool_records)),
            failure=failure,
            next_step=_next_step_for_status("done" if final_status == "done" else "blocked"),
        )
        return self._record_turn(f"/auto {goal}", answer)

    def _run_with_llm_tools(self, text: str) -> str:
        messages = self._messages_for_user_input(text)
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

    def _messages_for_user_input(self, text: str, user_content: Optional[str] = None) -> list[dict]:
        messages = self.memory.messages()
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        content = user_content or text
        if self.context_system:
            context_pack = self.context_system.context_pack(text)
            if context_pack:
                messages.append({"role": "system", "content": context_pack})
        messages.append({"role": "user", "content": content})
        return messages

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

    def _autonomous_instruction(self, goal: str, preflight: AutonomousPreflight) -> str:
        return "\n".join(
            [
                "受控自主执行请求。",
                f"目标: {goal}",
                "",
                self._format_autonomous_preflight(preflight),
                "",
                "规则:",
                "- 在有限步骤内推进目标；每步最多调用一个必要工具，或直接给出最终结论。",
                "- 优先使用只读、预览和检查工具，再考虑写入、执行、Git、浏览器交互或进程工具。",
                "- 高风险工具可能需要用户确认；如果被取消、拒绝或失败，请停止并说明阻塞原因。",
                "- 不要调用隐藏工具；如果目标需要隐藏工具，请停止并说明 blocked。",
                "- 不要尝试绕过权限确认，不要无限循环。",
                "- 完成时给出 done 总结；无法继续时给出 blocked 原因。",
            ]
        )

    def _autonomous_preflight(self, goal: str, step_limit: int, tools: list[dict]) -> AutonomousPreflight:
        available_names = [_tool_name(tool) for tool in tools if _tool_name(tool)]
        high_risk_tools = sorted(
            name
            for name in available_names
            if _is_high_risk_autonomous_tool(name)
        )
        return AutonomousPreflight(
            goal=goal,
            max_steps=step_limit,
            available_tool_count=len(available_names),
            hidden_tools=sorted(self.autonomous_disabled_tools),
            high_risk_tools=high_risk_tools,
        )

    def _autonomous_status_from_result(self, result: str) -> str:
        if result == "已取消操作。" or "工具调用失败" in result or "拒绝" in result or "预算已用完" in result:
            return "blocked"
        return "continue"

    def _autonomous_status_from_final(self, content: str) -> str:
        content = content or ""
        lowered = content.lower()
        if "blocked" in lowered or "阻塞" in content or "无法继续" in content:
            return "blocked"
        return "done"

    def _format_autonomous_preflight(self, preflight: AutonomousPreflight) -> str:
        hidden = ", ".join(preflight.hidden_tools) if preflight.hidden_tools else "无"
        high_risk = ", ".join(preflight.high_risk_tools[:12]) if preflight.high_risk_tools else "无"
        if len(preflight.high_risk_tools) > 12:
            high_risk += f", ... (+{len(preflight.high_risk_tools) - 12})"
        return "\n".join(
            [
                "执行前计划:",
                "1. 先用只读工具收集必要上下文。",
                "2. 每步最多调用一个工具，并在达到目标或遇到阻塞时停止。",
                "3. 如需隐藏工具或被拒绝的高风险工具，返回 blocked 原因。",
                "确认摘要:",
                f"- 最大步数: {preflight.max_steps}",
                f"- 可用工具数: {preflight.available_tool_count}",
                f"- 隐藏工具: {hidden}",
                f"- 仍需确认的高风险工具: {high_risk}",
            ]
        )

    def _format_autonomous_report(
        self,
        goal: str,
        status: str,
        records: list[AutonomousStepRecord],
        preflight: AutonomousPreflight,
    ) -> str:
        lines = [
            f"受控自主执行已停止: {status}",
            f"目标: {goal}",
            self._format_autonomous_preflight(preflight),
            "步骤:",
        ]
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

    def _start_run_report(self) -> None:
        self._active_tool_records = []
        self.last_run_report = RunReport(
            status="running",
            steps_used=0,
            tool_calls=[],
            tool_call_limit=self.max_tool_calls_per_turn,
            remaining_tool_calls=self.max_tool_calls_per_turn,
        )

    def _finish_turn(
        self,
        user_input: str,
        answer: str,
        status: str = "done",
        failure: str = "",
    ) -> str:
        if status == "done":
            failure = failure or _first_non_ok_tool_failure(self._active_tool_records)
            if failure:
                status = "blocked"
        self.last_run_report = RunReport(
            status=status,
            steps_used=len(self._active_tool_records),
            tool_calls=list(self._active_tool_records),
            tool_call_limit=self.max_tool_calls_per_turn,
            remaining_tool_calls=max(0, self.max_tool_calls_per_turn - len(self._active_tool_records)),
            failure=failure,
            next_step=_next_step_for_status(status),
        )
        return self._record_turn(user_input, answer)

    def _compact_tool_result(self, tool_name: str, result: str) -> str:
        compacted = self.context_window.compact_tool_result(tool_name, result)
        if compacted == result or not self.tool_result_store:
            return compacted
        result_id = self.tool_result_store.save(tool_name, result)
        if not result_id:
            return compacted + "\n[result_id unavailable: sensitive result not cached]"
        return compacted + f"\n[result_id={result_id} use read_tool_result to inspect more]"

    def _call_tool(self, name: str, arguments: dict) -> str:
        if len(self._active_tool_records) >= self.max_tool_calls_per_turn:
            result = f"工具调用预算已用完: 本轮最多允许 {self.max_tool_calls_per_turn} 次工具调用。"
            self._active_tool_records.append(
                ToolRunRecord(name=name, status="budget_exceeded", result_preview=result)
            )
            return result

        permission = self.tools.permission_for(name) if hasattr(self.tools, "permission_for") else None
        if permission and permission.requires_confirmation and not str(arguments.get("reason") or "").strip():
            result = f"拒绝调用: 高风险工具需要提供 reason: {name}"
            self._active_tool_records.append(ToolRunRecord(name=name, status="blocked", result_preview=result))
            return result

        is_read_only = permission and permission.risk == "read"
        if is_read_only:
            cached = self.tool_cache.get(name, arguments)
            if cached is not None:
                self._active_tool_records.append(
                    ToolRunRecord(name=name, status="ok", result_preview=self._shorten_trace_result(cached, limit=120))
                )
                return cached

        try:
            result = self.tools.call(name, **arguments)
        except Exception as error:
            safe_error = str(error)[:500]
            result = f"工具调用失败: {safe_error}"
            self._active_tool_records.append(ToolRunRecord(name=name, status="error", result_preview=result))
            return result

        if is_read_only:
            self.tool_cache.put(name, arguments, result)

        self._active_tool_records.append(
            ToolRunRecord(
                name=name,
                status=_tool_status_from_result(result),
                result_preview=self._shorten_trace_result(result, limit=120),
            )
        )
        return result

    def _run_local(self, text: str) -> Optional[str]:
        if self._looks_like_calculation(text):
            expression = self._extract_expression(text)
            return f"计算结果: {self._call_tool('calculate', {'expression': expression})}"

        if any(keyword in text for keyword in ("现在几点", "当前时间", "时间")):
            return f"当前时间: {self._call_tool('current_time', {})}"

        if text.startswith("保存笔记"):
            note = text.removeprefix("保存笔记").strip()
            if not note:
                return "请提供要保存的笔记内容。"
            return self._call_tool("save_note", {"text": note})

        if text in ("读取笔记", "查看笔记", "笔记"):
            return self._call_tool("read_notes", {})

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


def _tool_name(tool: dict) -> str:
    return str((tool.get("function") or {}).get("name") or "")


def _is_high_risk_autonomous_tool(name: str) -> bool:
    return any(
        term in name
        for term in [
            "write",
            "replace",
            "apply",
            "delete",
            "shell",
            "test",
            "repair",
            "git_",
            "browser_click",
            "browser_fill",
            "background_process",
            "task",
        ]
    )


def _tool_status_from_result(result: str) -> str:
    if result == "已取消操作。":
        return "cancelled"
    if "工具调用失败" in result:
        return "error"
    if "拒绝" in result:
        return "blocked"
    return "ok"


def _first_non_ok_tool_failure(records: list[ToolRunRecord]) -> str:
    for record in records:
        if record.status != "ok":
            return f"{record.name}: {record.result_preview}"
    return ""


def _next_step_for_status(status: str) -> str:
    if status == "blocked":
        return "检查失败工具并决定是否调整请求、权限或参数。"
    return ""
