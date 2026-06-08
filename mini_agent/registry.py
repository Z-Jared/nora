import re
from dataclasses import dataclass
from typing import Callable, Optional, Protocol

from mini_agent.durable_events import APPROVAL_DECIDED, APPROVAL_REQUESTED
from mini_agent.tools_common import confirm_in_terminal


class ToolLogger(Protocol):
    def record(self, tool: str, arguments: dict, status: str, result: str = "") -> None:
        ...


@dataclass(frozen=True)
class ToolPermission:
    category: str = "general"
    risk: str = "read"
    requires_confirmation: bool = False

    def label(self) -> str:
        suffix = ", 需要确认" if self.requires_confirmation else ""
        return f"{self.category}/{self.risk}{suffix}"


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[..., str]
    parameters: dict
    permission: ToolPermission


class ToolRegistry:
    def __init__(
        self,
        logger: Optional[ToolLogger] = None,
        confirm_action: Optional[Callable[[str], bool]] = None,
        disabled_tools: Optional[set[str]] = None,
        permission_overrides: Optional[dict[str, bool]] = None,
        event_store=None,
    ):
        self._tools: dict[str, Tool] = {}
        self.logger = logger
        self.confirm_action = confirm_action or confirm_in_terminal
        self.disabled_tools = disabled_tools or set()
        self.permission_overrides = permission_overrides or {}
        self.event_store = event_store

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., str],
        parameters: Optional[dict] = None,
        permission: Optional[ToolPermission] = None,
    ) -> None:
        if name in self.disabled_tools:
            return

        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")

        tool_permission = permission or ToolPermission()
        if name in self.permission_overrides:
            tool_permission = ToolPermission(
                category=tool_permission.category,
                risk=tool_permission.risk,
                requires_confirmation=self.permission_overrides[name],
            )

        self._tools[name] = Tool(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters or {"type": "object", "properties": {}},
            permission=tool_permission,
        )

    def call(self, tool_name: str, **kwargs) -> str:
        if tool_name not in self._tools:
            raise KeyError(f"Unknown tool: {tool_name}")

        tool = self._tools[tool_name]
        if tool.permission.requires_confirmation:
            self._record_approval_requested(tool, kwargs)
            approved = self.confirm_action(self._confirmation_prompt(tool, kwargs))
            self._record_approval_decided(tool, kwargs, approved)
            if not approved:
                if self.logger:
                    self.logger.record(tool_name, kwargs, "cancelled")
                return "已取消操作。"

        try:
            result = tool.handler(**kwargs)
        except Exception:
            if self.logger:
                self.logger.record(tool_name, kwargs, "error")
            raise

        if self.logger:
            self.logger.record(tool_name, kwargs, "ok", result)

        return result

    def _record_approval_requested(self, tool: Tool, arguments: dict) -> None:
        if not self.event_store:
            return
        try:
            self.event_store.record(
                event_type=APPROVAL_REQUESTED,
                source="registry",
                summary=f"approval requested: {tool.name}",
                severity="info",
                payload={
                    "tool_name": tool.name,
                    "category": tool.permission.category,
                    "risk": tool.permission.risk,
                    "requires_confirmation": tool.permission.requires_confirmation,
                    "argument_count": len(arguments),
                    "argument_keys": sorted(str(k) for k in arguments.keys()),
                    "reason_present": bool(str(arguments.get("reason") or "").strip()),
                },
            )
        except Exception:
            pass

    def _record_approval_decided(self, tool: Tool, arguments: dict, approved: bool) -> None:
        if not self.event_store:
            return
        try:
            status = "approved" if approved else "denied"
            self.event_store.record(
                event_type=APPROVAL_DECIDED,
                source="registry",
                summary=f"approval {status}: {tool.name}",
                severity="info" if approved else "warning",
                payload={
                    "tool_name": tool.name,
                    "category": tool.permission.category,
                    "risk": tool.permission.risk,
                    "requires_confirmation": tool.permission.requires_confirmation,
                    "status": status,
                    "argument_count": len(arguments),
                    "argument_keys": sorted(str(k) for k in arguments.keys()),
                    "reason_present": bool(str(arguments.get("reason") or "").strip()),
                },
            )
        except Exception:
            pass

    def describe(self) -> str:
        return "\n".join(
            f"- {tool.name}: {tool.description}" for tool in self._tools.values()
        )

    def describe_permissions(self) -> str:
        return "\n".join(
            f"- {tool.name}: {tool.permission.label()}"
            for tool in self._tools.values()
        )

    def permission_for(self, tool_name: str) -> Optional[ToolPermission]:
        tool = self._tools.get(tool_name)
        return tool.permission if tool else None

    def to_openai_tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def _confirmation_prompt(self, tool: Tool, arguments: dict) -> str:
        reason = str(arguments.get("reason") or "").strip() or "未提供"
        lines = [
            f"工具需要确认: {tool.name}",
            f"权限: {tool.permission.label()}",
        ]
        action = self._approval_action(arguments)
        if action:
            lines.append(f"动作: {action}")
        lines.extend([
            f"原因: {reason}",
            "是否继续? [y/N]: ",
        ])
        return "\n".join(lines)

    def _approval_action(self, arguments: dict) -> str:
        for key in (
            "command",
            "paths",
            "path",
            "message",
            "name",
            "profile",
            "process_id",
            "task_id",
            "worker_id",
            "trace_id",
            "history_id",
        ):
            if key in arguments:
                return f"{key}: {self._safe_action_value(key, arguments[key])}"
        hidden = [key for key in ("patch", "content", "old_text", "new_text", "output") if key in arguments]
        if hidden:
            return ", ".join(f"{key}: <{len(str(arguments[key]))} chars>" for key in hidden)
        return ""

    def _safe_action_value(self, key: str, value) -> str:
        if isinstance(value, (list, tuple)):
            text = ", ".join(str(item) for item in value[:5])
            if len(value) > 5:
                text += f", +{len(value) - 5} more"
        elif isinstance(value, dict):
            text = f"<{len(value)} fields>"
        else:
            text = str(value)
        text = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "sk-...", text)
        text = re.sub(r"(?i)(api[_-]?key|token|secret)=\\S+", r"\\1=...", text)
        return text[:160] + ("..." if len(text) > 160 else "")
