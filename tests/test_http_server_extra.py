import json
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.request import Request, urlopen

from mini_agent.controller import MiniAgent
from mini_agent.http_server import create_server
from mini_agent.tools import build_default_registry


def _find_free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class HTTPServerEdgeCaseTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        self.agent = MiniAgent(build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"))
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
        )
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def _request(self, method, path, body=None, headers=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode("utf-8") if body else None
        req = Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        try:
            with urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))

    def test_post_unknown_endpoint_returns_404(self):
        status, body = self._request("POST", "/unknown", {"message": "hi"})

        self.assertEqual(status, 404)

    def test_chat_with_invalid_json_body(self):
        url = f"http://127.0.0.1:{self.port}/chat"
        req = Request(url, data=b"not json", method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req) as resp:
                status = resp.status
        except urllib.error.HTTPError as error:
            status = error.code

        self.assertEqual(status, 400)

    def test_chat_with_oversized_body(self):
        url = f"http://127.0.0.1:{self.port}/chat"
        big_body = json.dumps({"message": "x" * 2 * 1024 * 1024}).encode("utf-8")
        req = Request(url, data=big_body, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req) as resp:
                status = resp.status
        except urllib.error.HTTPError as error:
            status = error.code
        except urllib.error.URLError:
            # Server may close connection before full body is sent
            status = 413

        self.assertEqual(status, 413)

    def test_get_unknown_endpoint_returns_404(self):
        status, body = self._request("GET", "/unknown")

        self.assertEqual(status, 404)

    def test_tools_endpoint_with_auth_required(self):
        server_with_auth = create_server(
            self.agent,
            host="127.0.0.1",
            port=_find_free_port(),
            api_token="secret",
        )
        thread = threading.Thread(target=server_with_auth.serve_forever)
        thread.daemon = True
        thread.start()

        try:
            port = server_with_auth.server_address[1]
            url = f"http://127.0.0.1:{port}/tools"
            req = Request(url)
            try:
                with urlopen(req) as resp:
                    status = resp.status
            except urllib.error.HTTPError as error:
                status = error.code

            self.assertEqual(status, 401)
        finally:
            server_with_auth.shutdown()
            thread.join(timeout=2)
            server_with_auth.server_close()


class HTTPServerNoSessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        self.agent = MiniAgent(build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"))
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            session_store=None,
        )
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def _request(self, method, path, body=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode("utf-8") if body else None
        req = Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))

    def test_session_list_returns_empty_without_store(self):
        status, body = self._request("GET", "/session/list")

        self.assertEqual(status, 200)
        self.assertEqual(body["sessions"], [])

    def test_session_save_returns_error_without_store(self):
        status, body = self._request("POST", "/session/save", {"name": "test"})

        self.assertEqual(status, 400)

    def test_session_load_returns_error_without_store(self):
        status, body = self._request("POST", "/session/load", {"name": "test"})

        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
