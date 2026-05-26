import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from mini_agent.llm import ChatMessage
from mini_agent.providers.anthropic import AnthropicClient
from mini_agent.providers.factory import build_llm_client
from mini_agent.providers.gemini import GeminiClient
from mini_agent.providers.http import post_json
from mini_agent.providers.openai_compatible import OpenAICompatibleClient
from mini_agent.settings import load_settings


class ProviderFactoryTests(unittest.TestCase):
    def test_builds_openai_compatible_provider(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "LLM_PROVIDER=openai-compatible",
                        "LLM_BASE_URL=https://example.com/v1",
                        "LLM_API_KEY=test-key",
                        "LLM_MODEL=test-model",
                    ]
                ),
                encoding="utf-8",
            )
            settings = load_settings(env_path=env_path, environ={})

        client = build_llm_client(settings)

        self.assertIsInstance(client, OpenAICompatibleClient)

    def test_builds_anthropic_provider(self):
        settings = load_settings(
            environ={
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "anthropic-key",
                "ANTHROPIC_MODEL": "claude-test",
            }
        )

        client = build_llm_client(settings)

        self.assertIsInstance(client, AnthropicClient)

    def test_builds_gemini_provider(self):
        settings = load_settings(
            environ={
                "LLM_PROVIDER": "gemini",
                "GEMINI_API_KEY": "gemini-key",
                "GEMINI_MODEL": "gemini-test",
            }
        )

        client = build_llm_client(settings)

        self.assertIsInstance(client, GeminiClient)


class AnthropicClientTests(unittest.TestCase):
    def test_posts_messages_request_and_parses_tool_use(self):
        requests = []

        def fake_transport(url, headers, payload, timeout):
            requests.append(
                {
                    "url": url,
                    "headers": headers,
                    "payload": payload,
                    "timeout": timeout,
                }
            )
            return {
                "content": [
                    {"type": "text", "text": "我需要计算。"},
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "calculate",
                        "input": {"expression": "1 + 2"},
                    },
                ]
            }

        client = AnthropicClient(
            base_url="https://api.anthropic.test/v1",
            api_key="anthropic-key",
            model="claude-test",
            transport=fake_transport,
        )

        result = client.chat(
            [{"role": "user", "content": "算一下 1 + 2"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "description": "计算数学表达式",
                        "parameters": {
                            "type": "object",
                            "properties": {"expression": {"type": "string"}},
                            "required": ["expression"],
                        },
                    },
                }
            ],
        )

        self.assertEqual(requests[0]["url"], "https://api.anthropic.test/v1/messages")
        self.assertEqual(requests[0]["headers"]["x-api-key"], "anthropic-key")
        self.assertEqual(requests[0]["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(requests[0]["payload"]["model"], "claude-test")
        self.assertEqual(requests[0]["payload"]["tools"][0]["name"], "calculate")
        self.assertEqual(result.content, "我需要计算。")
        self.assertEqual(result.tool_calls[0].call_id, "toolu_1")
        self.assertEqual(result.tool_calls[0].name, "calculate")
        self.assertEqual(result.tool_calls[0].arguments, {"expression": "1 + 2"})


class GeminiClientTests(unittest.TestCase):
    def test_posts_generate_content_request_and_parses_function_call(self):
        requests = []

        def fake_transport(url, headers, payload, timeout):
            requests.append(
                {
                    "url": url,
                    "headers": headers,
                    "payload": payload,
                    "timeout": timeout,
                }
            )
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "我需要计算。"},
                                {
                                    "functionCall": {
                                        "name": "calculate",
                                        "args": {"expression": "1 + 2"},
                                    }
                                },
                            ]
                        }
                    }
                ]
            }

        client = GeminiClient(
            base_url="https://generativelanguage.googleapis.test/v1beta",
            api_key="gemini-key",
            model="gemini-test",
            transport=fake_transport,
        )

        result = client.chat(
            [{"role": "user", "content": "算一下 1 + 2"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "description": "计算数学表达式",
                        "parameters": {
                            "type": "object",
                            "properties": {"expression": {"type": "string"}},
                            "required": ["expression"],
                        },
                    },
                }
            ],
        )

        self.assertEqual(
            requests[0]["url"],
            "https://generativelanguage.googleapis.test/v1beta/models/gemini-test:generateContent",
        )
        self.assertEqual(requests[0]["headers"]["x-goog-api-key"], "gemini-key")
        self.assertEqual(
            requests[0]["payload"]["tools"][0]["functionDeclarations"][0]["name"],
            "calculate",
        )
        self.assertEqual(result.content, "我需要计算。")
        self.assertEqual(result.tool_calls[0].name, "calculate")
        self.assertEqual(result.tool_calls[0].arguments, {"expression": "1 + 2"})


class OpenAICompatibleClientTests(unittest.TestCase):
    def test_posts_chat_completion_request(self):
        requests = []

        def fake_transport(url, headers, payload, timeout):
            requests.append(
                {
                    "url": url,
                    "headers": headers,
                    "payload": payload,
                    "timeout": timeout,
                }
            )
            return {"choices": [{"message": {"content": "模型回复"}}]}

        client = OpenAICompatibleClient(
            base_url="https://relay.example.com/v1",
            api_key="relay-key",
            model="gpt-test",
            transport=fake_transport,
        )

        result = client.complete("你好")

        self.assertEqual(result, "模型回复")
        self.assertEqual(requests[0]["url"], "https://relay.example.com/v1/chat/completions")
        self.assertEqual(requests[0]["headers"]["Authorization"], "Bearer relay-key")
        self.assertEqual(requests[0]["payload"]["model"], "gpt-test")
        self.assertEqual(
            requests[0]["payload"]["messages"],
            [
                ChatMessage(role="system", content=client.system_prompt).to_dict(),
                ChatMessage(role="user", content="你好").to_dict(),
            ],
        )

    def test_posts_tools_and_parses_tool_calls(self):
        requests = []

        def fake_transport(url, headers, payload, timeout):
            requests.append(payload)
            return {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "reasoning_content": "需要计算。",
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {
                                        "name": "calculate",
                                        "arguments": '{"expression": "1 + 2"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            }

        client = OpenAICompatibleClient(
            base_url="https://relay.example.com/v1",
            api_key="relay-key",
            model="gpt-test",
            transport=fake_transport,
        )

        result = client.chat(
            [{"role": "user", "content": "算一下 1 + 2"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "description": "计算数学表达式",
                        "parameters": {
                            "type": "object",
                            "properties": {"expression": {"type": "string"}},
                            "required": ["expression"],
                        },
                    },
                }
            ],
        )

        self.assertEqual(requests[0]["tools"][0]["function"]["name"], "calculate")
        self.assertEqual(result.tool_calls[0].call_id, "call_123")
        self.assertEqual(result.tool_calls[0].name, "calculate")
        self.assertEqual(result.tool_calls[0].arguments, {"expression": "1 + 2"})
        self.assertEqual(result.reasoning_content, "需要计算。")
        self.assertEqual(result.to_assistant_message()["reasoning_content"], "需要计算。")
        self.assertEqual(result.to_assistant_message()["content"], "")

    def test_http_error_details_are_redacted(self):
        class FakeHTTPError(HTTPError):
            def read(self):
                return b'{"error":"bad","prompt":"OPENAI_API_KEY=secret","token":"sk-secret"}'

        def fake_urlopen(request, timeout):
            raise FakeHTTPError(request.full_url, 400, "Bad Request", {}, None)

        with patch("urllib.request.urlopen", fake_urlopen):
            with self.assertRaises(Exception) as context:
                post_json("https://relay.example.com/v1/messages", {}, {"prompt": "hello"}, 10)

        message = str(context.exception)
        self.assertIn("LLM HTTP 400", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("OPENAI_API_KEY", message)
        self.assertNotIn("sk-secret", message)


if __name__ == "__main__":
    unittest.main()
