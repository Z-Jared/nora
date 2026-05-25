import json
import urllib.error
import urllib.request
from typing import Callable, Optional

from mini_agent.providers.base import ChatMessage, LLMError, LLMResponse, ToolCall


DEFAULT_SYSTEM_PROMPT = (
    "你是一个简洁、可靠的中文 agent。"
    "优先直接回答用户问题；不知道时说明限制，不要编造。"
)


Transport = Callable[[str, dict[str, str], dict, int], dict]


class OpenAICompatibleClient:
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
        self._transport = transport or _post_json

    def complete(self, user_input: str) -> str:
        return self.chat([ChatMessage(role="user", content=user_input).to_dict()]).content

    def chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> LLMResponse:
        request_messages = self._with_system_message(messages)
        payload = {
            "model": self.model,
            "messages": request_messages,
            "temperature": 0.3,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = self._transport(
            f"{self.base_url}/chat/completions",
            headers,
            payload,
            self.timeout_seconds,
        )

        return self._parse_response(response)

    def _with_system_message(self, messages: list[dict]) -> list[dict]:
        if messages and messages[0].get("role") == "system":
            return messages

        return [ChatMessage(role="system", content=self.system_prompt).to_dict()] + messages

    def _parse_response(self, response: dict) -> LLMResponse:
        try:
            message = response["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise LLMError(f"Unexpected LLM response: {response}") from error

        content = message.get("content") or ""
        return LLMResponse(
            content=content.strip(),
            tool_calls=_parse_tool_calls(message.get("tool_calls") or []),
            reasoning_content=message.get("reasoning_content") or "",
        )


def _post_json(url: str, headers: dict[str, str], payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise LLMError(f"LLM HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise LLMError(f"LLM request failed: {error}") from error


def _parse_tool_calls(raw_tool_calls: list[dict]) -> list[ToolCall]:
    tool_calls = []
    for raw_tool_call in raw_tool_calls:
        function = raw_tool_call.get("function") or {}
        raw_arguments = function.get("arguments") or "{}"
        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as error:
                raise LLMError(f"Invalid tool arguments: {raw_arguments}") from error
        elif isinstance(raw_arguments, dict):
            arguments = raw_arguments
        else:
            raise LLMError(f"Invalid tool arguments: {raw_arguments}")

        tool_calls.append(
            ToolCall(
                call_id=raw_tool_call.get("id") or "",
                name=function.get("name") or "",
                arguments=arguments,
            )
        )

    return tool_calls
