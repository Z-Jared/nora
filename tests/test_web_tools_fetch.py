import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

from mini_agent.web_tools import _fetch_url, _SafeRedirectHandler


class FetchUrlTests(unittest.TestCase):
    @patch("mini_agent.web_tools._fetch_url")
    @patch("mini_agent.web_tools.is_public_http_url", return_value=True)
    def test_returns_decoded_content(self, mock_check, mock_fetch):
        mock_fetch.return_value = "<html>hello</html>"

        from mini_agent.web_tools import WebTools
        tools = WebTools(fetcher=mock_fetch)
        result = tools.fetch_url("https://example.com")

        self.assertIn("hello", result)

    @patch("mini_agent.web_tools._fetch_url")
    @patch("mini_agent.web_tools.is_public_http_url", return_value=True)
    def test_accepts_json_content_type(self, mock_check, mock_fetch):
        mock_fetch.return_value = '{"ok":true}'

        from mini_agent.web_tools import WebTools
        tools = WebTools(fetcher=mock_fetch)
        result = tools.fetch_url("https://api.example.com/data")

        self.assertIn("ok", result)

    @patch("mini_agent.web_tools._fetch_url")
    @patch("mini_agent.web_tools.is_public_http_url", return_value=True)
    def test_rejects_unsupported_content_type(self, mock_check, mock_fetch):
        mock_fetch.side_effect = ValueError("unsupported content type: image/png")

        from mini_agent.web_tools import WebTools
        tools = WebTools(fetcher=mock_fetch)
        result = tools.fetch_url("https://example.com/img.png")

        self.assertIn("网页读取失败", result)

    @patch("mini_agent.web_tools.is_public_http_url", return_value=False)
    def test_rejects_private_url(self, mock_check):
        with self.assertRaises(ValueError) as ctx:
            _fetch_url("http://127.0.0.1:8000", 10)

        self.assertIn("private", str(ctx.exception))

    @patch("mini_agent.web_tools._opener.open")
    @patch("mini_agent.web_tools.is_public_http_url", return_value=True)
    def test_handles_http_error(self, mock_check, mock_open):
        mock_open.side_effect = HTTPError(
            "https://example.com", 404, "Not Found", {}, None
        )

        with self.assertRaises(HTTPError):
            _fetch_url("https://example.com", 10)

    @patch("mini_agent.web_tools._opener.open")
    @patch("mini_agent.web_tools.is_public_http_url", return_value=True)
    def test_handles_url_error(self, mock_check, mock_open):
        mock_open.side_effect = URLError("connection refused")

        with self.assertRaises(URLError):
            _fetch_url("https://example.com", 10)


class SafeRedirectHandlerTests(unittest.TestCase):
    def test_blocks_redirect_to_private_url(self):
        handler = _SafeRedirectHandler()
        req = MagicMock()

        with self.assertRaises(ValueError) as ctx:
            handler.redirect_request(req, None, 302, "Found", {}, "http://127.0.0.1:8000")

        self.assertIn("non-public", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
