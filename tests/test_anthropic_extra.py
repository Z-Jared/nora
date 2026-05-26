import unittest

from mini_agent.providers.anthropic import (
    _to_anthropic_messages,
    _to_anthropic_tools,
    _parse_anthropic_response,
    _arguments,
    AnthropicClient,
)
from mini_agent.providers.base import LLMError, LLMResponse


class ToAnthropicMessagesTests(unittest.TestCase):
    def test_drops_system_messages(self):
        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]

        result = _to_anthropic_messages(messages)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "user")

    def test_converts_user_message(self):
        messages = [{"role": "user", "content": "hello"}]

        result = _to_anthropic_messages(messages)

        self.assertEqual(result[0], {"role": "user", "content": "hello"})

    def test_converts_tool_result_message(self):
        messages = [{"role": "tool", "tool_call_id": "tc_1", "content": "result"}]

        result = _to_anthropic_messages(messages)

        self.assertEqual(result[0]["role"], "user")
        self.assertEqual(result[0]["content"][0]["type"], "tool_result")
        self.assertEqual(result[0]["content"][0]["tool_use_id"], "tc_1")

    def test_converts_assistant_message_with_text_only(self):
        messages = [{"role": "assistant", "content": "thinking"}]

        result = _to_anthropic_messages(messages)

        self.assertEqual(result[0]["role"], "assistant")
        # text-only assistant messages get wrapped in a content block list
        content = result[0]["content"]
        if isinstance(content, list):
            self.assertEqual(content[0]["type"], "text")
            self.assertEqual(content[0]["text"], "thinking")
        else:
            self.assertEqual(content, "thinking")

    def test_converts_assistant_message_with_tool_calls(self):
        messages = [{
            "role": "assistant",
            "content": "I'll call a tool",
            "tool_calls": [
                {"id": "tc_1", "function": {"name": "calc", "arguments": '{"x": 1}'}},
            ],
        }]

        result = _to_anthropic_messages(messages)

        content = result[0]["content"]
        self.assertEqual(len(content), 2)
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[1]["type"], "tool_use")
        self.assertEqual(content[1]["name"], "calc")

    def test_converts_assistant_message_with_tool_calls_only(self):
        messages = [{
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "tc_1", "function": {"name": "calc", "arguments": {"x": 1}}},
            ],
        }]

        result = _to_anthropic_messages(messages)

        content = result[0]["content"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["type"], "tool_use")


class ToAnthropicToolsTests(unittest.TestCase):
    def test_converts_openai_tools_to_anthropic_format(self):
        tools = [{
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Do math",
                "parameters": {"type": "object", "properties": {"expr": {"type": "string"}}},
            },
        }]

        result = _to_anthropic_tools(tools)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "calculate")
        self.assertEqual(result[0]["description"], "Do math")
        self.assertEqual(result[0]["input_schema"]["properties"]["expr"]["type"], "string")

    def test_returns_empty_for_empty_tools(self):
        self.assertEqual(_to_anthropic_tools([]), [])


class ParseAnthropicResponseTests(unittest.TestCase):
    def test_parses_text_content(self):
        response = {"content": [{"type": "text", "text": "hello"}]}

        result = _parse_anthropic_response(response)

        self.assertEqual(result.content, "hello")
        self.assertEqual(result.tool_calls, [])

    def test_parses_tool_use(self):
        response = {"content": [
            {"type": "text", "text": "calling tool"},
            {"type": "tool_use", "id": "tu_1", "name": "calc", "input": {"x": 1}},
        ]}

        result = _parse_anthropic_response(response)

        self.assertEqual(result.content, "calling tool")
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].name, "calc")
        self.assertEqual(result.tool_calls[0].arguments, {"x": 1})

    def test_raises_on_empty_content(self):
        with self.assertRaises(LLMError):
            _parse_anthropic_response({"content": []})

    def test_joins_multiple_text_parts(self):
        response = {"content": [
            {"type": "text", "text": "part1"},
            {"type": "text", "text": "part2"},
        ]}

        result = _parse_anthropic_response(response)

        self.assertEqual(result.content, "part1\npart2")


class ArgumentsTests(unittest.TestCase):
    def test_passthrough_dict(self):
        self.assertEqual(_arguments({"x": 1}), {"x": 1})

    def test_returns_empty_for_none(self):
        self.assertEqual(_arguments(None), {})

    def test_returns_empty_for_empty_string(self):
        self.assertEqual(_arguments(""), {})

    def test_parses_json_string(self):
        self.assertEqual(_arguments('{"x": 1}'), {"x": 1})


class AnthropicClientTests(unittest.TestCase):
    def test_complete_returns_content(self):
        def fake_transport(url, headers, payload, timeout):
            return {"content": [{"type": "text", "text": "hi there"}]}

        client = AnthropicClient(
            base_url="https://api.anthropic.test/v1",
            api_key="key",
            model="claude-test",
            transport=fake_transport,
        )

        result = client.complete("hello")

        self.assertEqual(result, "hi there")

    def test_chat_sends_system_prompt(self):
        captured = {}

        def fake_transport(url, headers, payload, timeout):
            captured.update(payload)
            return {"content": [{"type": "text", "text": "ok"}]}

        client = AnthropicClient(
            base_url="https://api.anthropic.test/v1",
            api_key="key",
            model="claude-test",
            system_prompt="custom system",
            transport=fake_transport,
        )

        client.chat([{"role": "user", "content": "hi"}])

        self.assertEqual(captured["system"], "custom system")
        self.assertEqual(captured["model"], "claude-test")

    def test_chat_includes_tools_when_provided(self):
        captured = {}

        def fake_transport(url, headers, payload, timeout):
            captured.update(payload)
            return {"content": [{"type": "text", "text": "ok"}]}

        client = AnthropicClient(
            base_url="https://api.anthropic.test/v1",
            api_key="key",
            model="claude-test",
            transport=fake_transport,
        )

        tools = [{"type": "function", "function": {"name": "calc", "description": "math", "parameters": {}}}]
        client.chat([{"role": "user", "content": "hi"}], tools=tools)

        self.assertIn("tools", captured)
        self.assertEqual(captured["tools"][0]["name"], "calc")

    def test_chat_omits_tools_when_none_provided(self):
        captured = {}

        def fake_transport(url, headers, payload, timeout):
            captured.update(payload)
            return {"content": [{"type": "text", "text": "ok"}]}

        client = AnthropicClient(
            base_url="https://api.anthropic.test/v1",
            api_key="key",
            model="claude-test",
            transport=fake_transport,
        )

        client.chat([{"role": "user", "content": "hi"}])

        self.assertNotIn("tools", captured)


if __name__ == "__main__":
    unittest.main()
