import json
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import io

from mini_agent.providers.anthropic import AnthropicClient
from mini_agent.providers.gemini import GeminiClient
from mini_agent.providers.base import LLMError


class AnthropicStreamChatTests(unittest.TestCase):
    @patch("mini_agent.providers.anthropic.urllib.request.urlopen")
    def test_yields_text_deltas(self, mock_urlopen):
        sse_data = (
            'event: message_start\ndata: {"type":"message_start"}\n\n'
            'event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Hello"}}\n\n'
            'event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":" World"}}\n\n'
            'event: message_stop\ndata: {"type":"message_stop"}\n\n'
        )
        mock_response = MagicMock()
        mock_response.read.side_effect = [sse_data.encode("utf-8"), b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response

        client = AnthropicClient(base_url="https://api.anthropic.com/v1", api_key="test", model="claude-3")
        chunks = list(client.stream_chat([{"role": "user", "content": "hi"}]))

        self.assertEqual(chunks, ["Hello", " World"])


class GeminiStreamChatTests(unittest.TestCase):
    @patch("mini_agent.providers.gemini.urllib.request.urlopen")
    def test_yields_text_parts(self, mock_urlopen):
        sse_data = (
            'data: {"candidates":[{"content":{"parts":[{"text":"Hi"}]}}]}\n\n'
            'data: {"candidates":[{"content":{"parts":[{"text":" there"}]}}]}\n\n'
        )
        mock_response = MagicMock()
        mock_response.read.side_effect = [sse_data.encode("utf-8"), b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response

        client = GeminiClient(base_url="https://generativelanguage.googleapis.com/v1beta", api_key="test", model="gemini-pro")
        chunks = list(client.stream_chat([{"role": "user", "content": "hi"}]))

        self.assertEqual(chunks, ["Hi", " there"])


if __name__ == "__main__":
    unittest.main()
