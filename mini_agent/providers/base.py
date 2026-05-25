import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict

    def to_openai_dict(self) -> dict:
        return {
            "id": self.call_id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments, ensure_ascii=False),
            },
        }


@dataclass(frozen=True)
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = None
    reasoning_content: str = ""

    def __post_init__(self):
        if self.tool_calls is None:
            object.__setattr__(self, "tool_calls", [])

    def to_assistant_message(self) -> dict:
        content = self.content if self.tool_calls else self.content or None
        message = {"role": "assistant", "content": content}
        if self.reasoning_content:
            message["reasoning_content"] = self.reasoning_content
        if self.tool_calls:
            message["tool_calls"] = [
                tool_call.to_openai_dict() for tool_call in self.tool_calls
            ]
        return message


class LLMError(RuntimeError):
    pass
