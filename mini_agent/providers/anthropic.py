import json
import urllib.error
import urllib.request
from typing import Callable, Generator, Optional

from mini_agent.providers.base import ChatMessage, LLMError, LLMResponse, ToolCall
from mini_agent.providers.http import post_json, sanitize_error_detail
from mini_agent.providers.openai_compatible import DEFAULT_SYSTEM_PROMPT


ANTHROPIC_VERSION = "2023-06-01"
Transport = Callable[[str, dict[str, str], dict, int], dict]


class AnthropicClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        timeout_seconds: int = 60,
        transport: Optional[Transport] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.timeout_seconds = timeout_seconds
        self._transport = transport or post_json

    def complete(self, user_input: str) -> str:
        return self.chat([ChatMessage(role="user", content=user_input).to_dict()]).content

    def chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> LLMResponse:
        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "system": self.system_prompt,
            "messages": _to_anthropic_messages(messages),
        }
        converted_tools = _to_anthropic_tools(tools or [])
        if converted_tools:
            payload["tools"] = converted_tools

        response = self._transport(
            f"{self.base_url}/messages",
            {
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            payload,
            self.timeout_seconds,
        )
        return _parse_anthropic_response(response)

    def stream_chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> Generator[str, None, None]:
        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "system": self.system_prompt,
            "messages": _to_anthropic_messages(messages),
            "stream": True,
        }
        converted_tools = _to_anthropic_tools(tools or [])
        if converted_tools:
            payload["tools"] = converted_tools

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/messages",
            data=data,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                buffer = ""
                while True:
                    chunk = response.read(1024)
                    if not chunk:
                        break
                    buffer += chunk.decode("utf-8")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line or line.startswith("event:"):
                            continue
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        try:
                            event = json.loads(data_str)
                            if event.get("type") == "content_block_delta":
                                delta = event.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except json.JSONDecodeError:
                            continue
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise LLMError(f"Anthropic HTTP {error.code}: {sanitize_error_detail(detail)}") from error
        except urllib.error.URLError as error:
            raise LLMError(f"Anthropic request failed: {error}") from error


def _to_anthropic_messages(messages: list[dict]) -> list[dict]:
    converted = []
    for message in messages:
        role = message.get("role")
        if role == "system":
            continue

        if role == "tool":
            converted.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": message.get("tool_call_id", ""),
                            "content": message.get("content", ""),
                        }
                    ],
                }
            )
            continue

        if role == "assistant":
            content = []
            text = message.get("content") or ""
            if text:
                content.append({"type": "text", "text": text})
            for raw_tool_call in message.get("tool_calls") or []:
                function = raw_tool_call.get("function") or {}
                content.append(
                    {
                        "type": "tool_use",
                        "id": raw_tool_call.get("id") or "",
                        "name": function.get("name") or "",
                        "input": _arguments(function.get("arguments")),
                    }
                )
            converted.append({"role": "assistant", "content": content or text})
            continue

        converted.append({"role": "user", "content": message.get("content", "")})

    return converted


def _to_anthropic_tools(tools: list[dict]) -> list[dict]:
    converted = []
    for tool in tools:
        function = tool.get("function") or {}
        converted.append(
            {
                "name": function.get("name", ""),
                "description": function.get("description", ""),
                "input_schema": function.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return converted


def _parse_anthropic_response(response: dict) -> LLMResponse:
    content_parts = response.get("content") or []
    text_parts = []
    tool_calls = []
    for part in content_parts:
        if part.get("type") == "text":
            text_parts.append(part.get("text", ""))
        elif part.get("type") == "tool_use":
            tool_calls.append(
                ToolCall(
                    call_id=part.get("id", ""),
                    name=part.get("name", ""),
                    arguments=part.get("input") or {},
                )
            )

    if not text_parts and not tool_calls:
        raise LLMError(f"Unexpected Anthropic response: {response}")

    return LLMResponse(content="\n".join(text_parts).strip(), tool_calls=tool_calls)


def _arguments(raw_arguments):
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not raw_arguments:
        return {}

    import json

    return json.loads(raw_arguments)
