import urllib.parse
from typing import Callable, Optional

from mini_agent.providers.base import ChatMessage, LLMError, LLMResponse, ToolCall
from mini_agent.providers.http import post_json
from mini_agent.providers.openai_compatible import DEFAULT_SYSTEM_PROMPT


Transport = Callable[[str, dict[str, str], dict, int], dict]


class GeminiClient:
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
            "systemInstruction": {"parts": [{"text": self.system_prompt}]},
            "contents": _to_gemini_contents(messages),
        }
        converted_tools = _to_gemini_tools(tools or [])
        if converted_tools:
            payload["tools"] = converted_tools

        model = urllib.parse.quote(self.model, safe="")
        response = self._transport(
            f"{self.base_url}/models/{model}:generateContent",
            {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            payload,
            self.timeout_seconds,
        )
        return _parse_gemini_response(response)


def _to_gemini_contents(messages: list[dict]) -> list[dict]:
    converted = []
    for message in messages:
        role = message.get("role")
        if role == "system":
            continue

        if role == "tool":
            converted.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": message.get("name", ""),
                                "response": {"result": message.get("content", "")},
                            }
                        }
                    ],
                }
            )
            continue

        if role == "assistant":
            parts = []
            text = message.get("content") or ""
            if text:
                parts.append({"text": text})
            for raw_tool_call in message.get("tool_calls") or []:
                function = raw_tool_call.get("function") or {}
                parts.append(
                    {
                        "functionCall": {
                            "name": function.get("name", ""),
                            "args": _arguments(function.get("arguments")),
                        }
                    }
                )
            converted.append({"role": "model", "parts": parts or [{"text": ""}]})
            continue

        converted.append({"role": "user", "parts": [{"text": message.get("content", "")}]})

    return converted


def _to_gemini_tools(tools: list[dict]) -> list[dict]:
    declarations = []
    for tool in tools:
        function = tool.get("function") or {}
        declarations.append(
            {
                "name": function.get("name", ""),
                "description": function.get("description", ""),
                "parameters": function.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return [{"functionDeclarations": declarations}] if declarations else []


def _parse_gemini_response(response: dict) -> LLMResponse:
    try:
        parts = response["candidates"][0]["content"].get("parts", [])
    except (KeyError, IndexError, TypeError) as error:
        raise LLMError(f"Unexpected Gemini response: {response}") from error

    text_parts = []
    tool_calls = []
    for index, part in enumerate(parts):
        if "text" in part:
            text_parts.append(part.get("text", ""))
        elif "functionCall" in part:
            function_call = part["functionCall"]
            tool_calls.append(
                ToolCall(
                    call_id=f"gemini_call_{index + 1}",
                    name=function_call.get("name", ""),
                    arguments=function_call.get("args") or {},
                )
            )

    return LLMResponse(content="\n".join(text_parts).strip(), tool_calls=tool_calls)


def _arguments(raw_arguments):
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not raw_arguments:
        return {}

    import json

    return json.loads(raw_arguments)
