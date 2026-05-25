from dataclasses import dataclass
from typing import Callable, Optional, Protocol

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
    ):
        self._tools: dict[str, Tool] = {}
        self.logger = logger
        self.confirm_action = confirm_action or confirm_in_terminal
        self.disabled_tools = disabled_tools or set()

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

        self._tools[name] = Tool(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters or {"type": "object", "properties": {}},
            permission=permission or ToolPermission(),
        )

    def call(self, tool_name: str, **kwargs) -> str:
        if tool_name not in self._tools:
            raise KeyError(f"Unknown tool: {tool_name}")

        tool = self._tools[tool_name]
        if tool.permission.requires_confirmation:
            if not self.confirm_action(self._confirmation_prompt(tool, kwargs)):
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

    def describe(self) -> str:
        return "\n".join(
            f"- {tool.name}: {tool.description}" for tool in self._tools.values()
        )

    def describe_permissions(self) -> str:
        return "\n".join(
            f"- {tool.name}: {tool.permission.label()}"
            for tool in self._tools.values()
        )

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
        return "\n".join(
            [
                f"工具需要确认: {tool.name}",
                f"权限: {tool.permission.label()}",
                f"原因: {reason}",
                "是否继续? [y/N]: ",
            ]
        )
