import json
import unittest

from mini_agent.providers.base import LLMError, LLMResponse
from mini_agent.providers.openai_compatible import (
    OpenAICompatibleClient,
    _parse_tool_calls,
)


class WithSystemMessageTests(unittest.TestCase):
    def test_prepends_system_prompt_when_missing(self):
        client = OpenAICompatibleClient(
            base_url="https://example.com/v1",
            api_key="key",
            model="test",
            system_prompt="custom system",
            transport=lambda url, headers, payload, timeout: {"choices": [{"message": {"content": "ok"}}]},
        )

        result = client._with_system_message([{"role": "user", "content": "hi"}])

        self.assertEqual(result[0]["role"], "system")
        self.assertEqual(result[0]["content"], "custom system")
        self.assertEqual(result[1]["role"], "user")

    def test_does_not_duplicate_system_message(self):
        client = OpenAICompatibleClient(
            base_url="https://example.com/v1",
            api_key="key",
            model="test",
            system_prompt="custom system",
            transport=lambda url, headers, payload, timeout: {"choices": [{"message": {"content": "ok"}}]},
        )

        messages = [{"role": "system", "content": "already there"}, {"role": "user", "content": "hi"}]
        result = client._with_system_message(messages)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["content"], "already there")


class ParseResponseTests(unittest.TestCase):
    def test_parses_content_only(self):
        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
            transport=lambda url, headers, payload, timeout: {},
        )

        response = client._parse_response({"choices": [{"message": {"content": "hello"}}]})

        self.assertEqual(response.content, "hello")
        self.assertEqual(response.tool_calls, [])

    def test_parses_empty_content(self):
        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
            transport=lambda url, headers, payload, timeout: {},
        )

        response = client._parse_response({"choices": [{"message": {"content": None}}]})

        self.assertEqual(response.content, "")

    def test_raises_on_malformed_response(self):
        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
            transport=lambda url, headers, payload, timeout: {},
        )

        with self.assertRaises(LLMError):
            client._parse_response({})

    def test_raises_on_empty_choices(self):
        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
            transport=lambda url, headers, payload, timeout: {},
        )

        with self.assertRaises(LLMError):
            client._parse_response({"choices": []})


class ParseToolCallsTests(unittest.TestCase):
    def test_parses_tool_calls_with_string_args(self):
        raw = [
            {"id": "call_1", "function": {"name": "calc", "arguments": '{"x": 1}'}},
        ]

        result = _parse_tool_calls(raw)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].call_id, "call_1")
        self.assertEqual(result[0].name, "calc")
        self.assertEqual(result[0].arguments, {"x": 1})

    def test_parses_tool_calls_with_dict_args(self):
        raw = [
            {"id": "call_2", "function": {"name": "read", "arguments": {"path": "test.py"}}},
        ]

        result = _parse_tool_calls(raw)

        self.assertEqual(result[0].arguments, {"path": "test.py"})

    def test_handles_missing_function_fields(self):
        raw = [{"id": None, "function": None}]

        result = _parse_tool_calls(raw)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "")

    def test_raises_on_invalid_string_arguments(self):
        raw = [{"id": "call_1", "function": {"name": "x", "arguments": "not json"}}]

        with self.assertRaises(LLMError):
            _parse_tool_calls(raw)

    def test_raises_on_invalid_argument_type(self):
        raw = [{"id": "call_1", "function": {"name": "x", "arguments": 42}}]

        with self.assertRaises(LLMError):
            _parse_tool_calls(raw)

    def test_returns_empty_list_for_empty_input(self):
        self.assertEqual(_parse_tool_calls([]), [])


class ChatMethodTests(unittest.TestCase):
    def test_chat_sends_tools_in_payload(self):
        captured = {}

        def fake_transport(url, headers, payload, timeout):
            captured.update(payload)
            return {"choices": [{"message": {"content": "ok"}}]}

        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
            transport=fake_transport,
        )

        tools = [{"type": "function", "function": {"name": "calc", "description": "calc", "parameters": {}}}]
        client.chat([{"role": "user", "content": "hi"}], tools=tools)

        self.assertIn("tools", captured)
        self.assertEqual(captured["tool_choice"], "auto")

    def test_chat_without_tools_omits_tool_fields(self):
        captured = {}

        def fake_transport(url, headers, payload, timeout):
            captured.update(payload)
            return {"choices": [{"message": {"content": "ok"}}]}

        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
            transport=fake_transport,
        )

        client.chat([{"role": "user", "content": "hi"}])

        self.assertNotIn("tools", captured)
        self.assertNotIn("tool_choice", captured)

    def test_complete_returns_content_string(self):
        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
            transport=lambda url, headers, payload, timeout: {"choices": [{"message": {"content": "  hello  "}}]},
        )

        result = client.complete("hi")

        self.assertEqual(result, "hello")


if __name__ == "__main__":
    unittest.main()
