import unittest
from unittest.mock import patch, MagicMock
import urllib.error
import io

from mini_agent.providers.http import post_json
from mini_agent.providers.base import LLMError


def _make_http_error(code: int, body: str = "error") -> urllib.error.HTTPError:
    fp = io.BytesIO(body.encode("utf-8"))
    return urllib.error.HTTPError(
        url="http://test", code=code, msg="Error",
        hdrs=MagicMock(), fp=fp,
    )


class PostJsonRetryTests(unittest.TestCase):
    @patch("mini_agent.providers.http.time.sleep")
    @patch("mini_agent.providers.http.urllib.request.urlopen")
    def test_retries_on_429(self, mock_urlopen, mock_sleep):
        error = _make_http_error(429, "rate limited")
        error.headers = MagicMock()
        error.headers.get.return_value = None
        mock_urlopen.side_effect = [error, MagicMock(__enter__=lambda s: s, __exit__=MagicMock(), read=lambda: b'{"ok": true}')]

        result = post_json("http://test", {}, {}, 10)

        self.assertEqual(result, {"ok": True})
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("mini_agent.providers.http.time.sleep")
    @patch("mini_agent.providers.http.urllib.request.urlopen")
    def test_retries_on_500(self, mock_urlopen, mock_sleep):
        error = _make_http_error(500, "server error")
        error.headers = MagicMock()
        error.headers.get.return_value = None
        mock_urlopen.side_effect = [error, MagicMock(__enter__=lambda s: s, __exit__=MagicMock(), read=lambda: b'{"ok": true}')]

        result = post_json("http://test", {}, {}, 10)

        self.assertEqual(result, {"ok": True})

    @patch("mini_agent.providers.http.time.sleep")
    @patch("mini_agent.providers.http.urllib.request.urlopen")
    def test_does_not_retry_on_400(self, mock_urlopen, mock_sleep):
        error = _make_http_error(400, "bad request")
        error.headers = MagicMock()
        mock_urlopen.side_effect = error

        with self.assertRaises(LLMError) as ctx:
            post_json("http://test", {}, {}, 10)

        self.assertIn("400", str(ctx.exception))
        mock_sleep.assert_not_called()

    @patch("mini_agent.providers.http.time.sleep")
    @patch("mini_agent.providers.http.urllib.request.urlopen")
    def test_gives_up_after_max_retries(self, mock_urlopen, mock_sleep):
        error = _make_http_error(429, "rate limited")
        error.headers = MagicMock()
        error.headers.get.return_value = None
        mock_urlopen.side_effect = error

        with self.assertRaises(LLMError) as ctx:
            post_json("http://test", {}, {}, 10)

        self.assertIn("429", str(ctx.exception))
        self.assertEqual(mock_urlopen.call_count, 4)

    @patch("mini_agent.providers.http.time.sleep")
    @patch("mini_agent.providers.http.urllib.request.urlopen")
    def test_respects_retry_after_header(self, mock_urlopen, mock_sleep):
        error = _make_http_error(429, "rate limited")
        error.headers = MagicMock()
        error.headers.get.return_value = "5"
        mock_urlopen.side_effect = [error, MagicMock(__enter__=lambda s: s, __exit__=MagicMock(), read=lambda: b'{"ok": true}')]

        post_json("http://test", {}, {}, 10)

        sleep_args = mock_sleep.call_args[0][0]
        self.assertGreaterEqual(sleep_args, 5.0)

    @patch("mini_agent.providers.http.time.sleep")
    @patch("mini_agent.providers.http.urllib.request.urlopen")
    def test_retries_on_url_error(self, mock_urlopen, mock_sleep):
        import urllib.error
        url_error = urllib.error.URLError("connection refused")
        mock_urlopen.side_effect = [url_error, MagicMock(__enter__=lambda s: s, __exit__=MagicMock(), read=lambda: b'{"ok": true}')]

        result = post_json("http://test", {}, {}, 10)

        self.assertEqual(result, {"ok": True})
        mock_sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
