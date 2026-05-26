import io
import json
import unittest
from unittest.mock import patch, MagicMock

from mini_agent.providers.base import LLMError
from mini_agent.providers.openai_compatible import OpenAICompatibleClient, _post_json


class StreamChatTests(unittest.TestCase):
    @patch("mini_agent.providers.openai_compatible.urllib.request.urlopen")
    def test_yields_content_deltas(self, mock_urlopen):
        sse_data = (
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":" World"}}]}\n\n'
            'data: [DONE]\n\n'
        )
        mock_response = MagicMock()
        mock_response.read.side_effect = [sse_data.encode("utf-8"), b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response

        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
        )
        chunks = list(client.stream_chat([{"role": "user", "content": "hi"}]))

        self.assertEqual(chunks, ["Hello", " World"])

    @patch("mini_agent.providers.openai_compatible.urllib.request.urlopen")
    def test_skips_malformed_sse_lines(self, mock_urlopen):
        sse_data = (
            'not json\n\n'
            'data: [DONE]\n\n'
        )
        mock_response = MagicMock()
        mock_response.read.side_effect = [sse_data.encode("utf-8"), b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response

        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
        )
        chunks = list(client.stream_chat([{"role": "user", "content": "hi"}]))

        self.assertEqual(chunks, [])

    @patch("mini_agent.providers.openai_compatible.urllib.request.urlopen")
    def test_handles_empty_delta_content(self, mock_urlopen):
        sse_data = (
            'data: {"choices":[{"delta":{}}]}\n\n'
            'data: {"choices":[{"delta":{"content":null}}]}\n\n'
            'data: [DONE]\n\n'
        )
        mock_response = MagicMock()
        mock_response.read.side_effect = [sse_data.encode("utf-8"), b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response

        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
        )
        chunks = list(client.stream_chat([{"role": "user", "content": "hi"}]))

        self.assertEqual(chunks, [])

    @patch("mini_agent.providers.openai_compatible.urllib.request.urlopen")
    def test_raises_on_http_error(self, mock_urlopen):
        from urllib.error import HTTPError

        error = HTTPError("https://example.com/v1/chat/completions", 429, "rate limited", {}, None)
        error.read = lambda: b'{"error":"rate limited"}'
        mock_urlopen.side_effect = error

        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
        )

        with self.assertRaises(LLMError) as ctx:
            list(client.stream_chat([{"role": "user", "content": "hi"}]))

        self.assertIn("429", str(ctx.exception))

    @patch("mini_agent.providers.openai_compatible.urllib.request.urlopen")
    def test_raises_on_url_error(self, mock_urlopen):
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("connection refused")

        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
        )

        with self.assertRaises(LLMError) as ctx:
            list(client.stream_chat([{"role": "user", "content": "hi"}]))

        self.assertIn("request failed", str(ctx.exception))

    @patch("mini_agent.providers.openai_compatible.urllib.request.urlopen")
    def test_sends_tools_in_stream_payload(self, mock_urlopen):
        sse_data = 'data: [DONE]\n\n'
        mock_response = MagicMock()
        mock_response.read.side_effect = [sse_data.encode("utf-8"), b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response

        client = OpenAICompatibleClient(
            base_url="https://example.com/v1", api_key="key", model="test",
        )
        tools = [{"type": "function", "function": {"name": "calc", "description": "math", "parameters": {}}}]
        list(client.stream_chat([{"role": "user", "content": "hi"}], tools=tools))

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertIn("tools", payload)
        self.assertTrue(payload["stream"])


class PostJsonTests(unittest.TestCase):
    @patch("mini_agent.providers.openai_compatible.urllib.request.urlopen")
    def test_returns_parsed_json(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response

        result = _post_json("https://example.com/api", {}, {"key": "value"}, 10)

        self.assertEqual(result, {"ok": True})

    @patch("mini_agent.providers.openai_compatible.urllib.request.urlopen")
    def test_raises_on_http_error(self, mock_urlopen):
        from urllib.error import HTTPError

        error = HTTPError("https://example.com/api", 500, "server error", {}, None)
        error.read = lambda: b'{"error":"internal"}'
        mock_urlopen.side_effect = error

        with self.assertRaises(LLMError) as ctx:
            _post_json("https://example.com/api", {}, {}, 10)

        self.assertIn("500", str(ctx.exception))

    @patch("mini_agent.providers.openai_compatible.urllib.request.urlopen")
    def test_raises_on_url_error(self, mock_urlopen):
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("dns fail")

        with self.assertRaises(LLMError):
            _post_json("https://example.com/api", {}, {}, 10)


if __name__ == "__main__":
    unittest.main()
