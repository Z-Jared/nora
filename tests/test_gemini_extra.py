import unittest

from mini_agent.providers.gemini import (
    _to_gemini_contents,
    _to_gemini_tools,
    _parse_gemini_response,
    _arguments,
    GeminiClient,
)
from mini_agent.providers.base import LLMError, LLMResponse


class ToGeminiContentsTests(unittest.TestCase):
    def test_drops_system_messages(self):
        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]

        result = _to_gemini_contents(messages)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "user")

    def test_converts_user_message(self):
        messages = [{"role": "user", "content": "hello"}]

        result = _to_gemini_contents(messages)

        self.assertEqual(result[0], {"role": "user", "parts": [{"text": "hello"}]})

    def test_converts_tool_result_message(self):
        messages = [{"role": "tool", "name": "calc", "content": "42"}]

        result = _to_gemini_contents(messages)

        self.assertEqual(result[0]["role"], "user")
        fr = result[0]["parts"][0]["functionResponse"]
        self.assertEqual(fr["name"], "calc")
        self.assertEqual(fr["response"]["result"], "42")

    def test_converts_assistant_message_with_text_only(self):
        messages = [{"role": "assistant", "content": "thinking"}]

        result = _to_gemini_contents(messages)

        self.assertEqual(result[0]["role"], "model")
        self.assertEqual(result[0]["parts"], [{"text": "thinking"}])

    def test_converts_assistant_message_with_tool_calls(self):
        messages = [{
            "role": "assistant",
            "content": "calling",
            "tool_calls": [
                {"function": {"name": "calc", "arguments": '{"x": 1}'}},
            ],
        }]

        result = _to_gemini_contents(messages)

        parts = result[0]["parts"]
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0]["text"], "calling")
        self.assertEqual(parts[1]["functionCall"]["name"], "calc")

    def test_converts_assistant_with_tool_calls_only(self):
        messages = [{
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"function": {"name": "calc", "arguments": {"x": 1}}},
            ],
        }]

        result = _to_gemini_contents(messages)

        parts = result[0]["parts"]
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["functionCall"]["name"], "calc")


class ToGeminiToolsTests(unittest.TestCase):
    def test_converts_openai_tools_to_gemini_format(self):
        tools = [{
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Do math",
                "parameters": {"type": "object", "properties": {"expr": {"type": "string"}}},
            },
        }]

        result = _to_gemini_tools(tools)

        self.assertEqual(len(result), 1)
        decl = result[0]["functionDeclarations"][0]
        self.assertEqual(decl["name"], "calculate")
        self.assertEqual(decl["description"], "Do math")

    def test_returns_empty_for_empty_tools(self):
        self.assertEqual(_to_gemini_tools([]), [])


class ParseGeminiResponseTests(unittest.TestCase):
    def test_parses_text_content(self):
        response = {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]}

        result = _parse_gemini_response(response)

        self.assertEqual(result.content, "hello")
        self.assertEqual(result.tool_calls, [])

    def test_parses_function_call(self):
        response = {"candidates": [{"content": {"parts": [
            {"text": "calling"},
            {"functionCall": {"name": "calc", "args": {"x": 1}}},
        ]}}]}

        result = _parse_gemini_response(response)

        self.assertEqual(result.content, "calling")
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].name, "calc")
        self.assertEqual(result.tool_calls[0].call_id, "gemini_call_2")

    def test_raises_on_malformed_response(self):
        with self.assertRaises(LLMError):
            _parse_gemini_response({})

    def test_raises_on_empty_candidates(self):
        with self.assertRaises(LLMError):
            _parse_gemini_response({"candidates": []})

    def test_joins_multiple_text_parts(self):
        response = {"candidates": [{"content": {"parts": [
            {"text": "part1"},
            {"text": "part2"},
        ]}}]}

        result = _parse_gemini_response(response)

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


class GeminiClientTests(unittest.TestCase):
    def test_complete_returns_content(self):
        def fake_transport(url, headers, payload, timeout):
            return {"candidates": [{"content": {"parts": [{"text": "hi there"}]}}]}

        client = GeminiClient(
            base_url="https://generativelanguage.googleapis.test/v1beta",
            api_key="key",
            model="gemini-test",
            transport=fake_transport,
        )

        result = client.complete("hello")

        self.assertEqual(result, "hi there")

    def test_chat_sends_system_instruction(self):
        captured = {}

        def fake_transport(url, headers, payload, timeout):
            captured.update(payload)
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

        client = GeminiClient(
            base_url="https://generativelanguage.googleapis.test/v1beta",
            api_key="key",
            model="gemini-test",
            system_prompt="custom system",
            transport=fake_transport,
        )

        client.chat([{"role": "user", "content": "hi"}])

        self.assertEqual(captured["systemInstruction"]["parts"][0]["text"], "custom system")

    def test_chat_includes_tools_when_provided(self):
        captured = {}

        def fake_transport(url, headers, payload, timeout):
            captured.update(payload)
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

        client = GeminiClient(
            base_url="https://generativelanguage.googleapis.test/v1beta",
            api_key="key",
            model="gemini-test",
            transport=fake_transport,
        )

        tools = [{"type": "function", "function": {"name": "calc", "description": "math", "parameters": {}}}]
        client.chat([{"role": "user", "content": "hi"}], tools=tools)

        self.assertIn("tools", captured)
        self.assertEqual(captured["tools"][0]["functionDeclarations"][0]["name"], "calc")

    def test_chat_omits_tools_when_none_provided(self):
        captured = {}

        def fake_transport(url, headers, payload, timeout):
            captured.update(payload)
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

        client = GeminiClient(
            base_url="https://generativelanguage.googleapis.test/v1beta",
            api_key="key",
            model="gemini-test",
            transport=fake_transport,
        )

        client.chat([{"role": "user", "content": "hi"}])

        self.assertNotIn("tools", captured)


if __name__ == "__main__":
    unittest.main()
