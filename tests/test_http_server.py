import json
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from urllib.request import Request, urlopen

from mini_agent.controller import MiniAgent
from mini_agent.http_server import create_server
from mini_agent.session import SessionStore
from mini_agent.tools import build_default_registry


def _find_free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class HTTPServerTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        self.agent = MiniAgent(build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"))
        self.session_store = SessionStore(Path(self.tmpdir) / "sessions")
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            session_store=self.session_store,
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

    def test_health_endpoint(self):
        status, body = self._request("GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_chat_endpoint(self):
        status, body = self._request("POST", "/chat", {"message": "计算 2 + 3"})

        self.assertEqual(status, 200)
        self.assertIn("计算结果", body["response"])

    def test_chat_rejects_empty_message(self):
        status, body = self._request("POST", "/chat", {"message": ""})

        self.assertEqual(status, 400)
        self.assertIn("required", body["error"])

    def test_tools_endpoint(self):
        status, body = self._request("GET", "/tools")

        self.assertEqual(status, 200)
        self.assertIn("calculate", body["tools"])
        self.assertIn("current_time", body["tools"])

    def test_session_save_and_list(self):
        self.agent.run("hello")
        status, body = self._request("POST", "/session/save", {"name": "test"})

        self.assertEqual(status, 200)
        self.assertIn("已保存", body["result"])

        status, body = self._request("GET", "/session/list")
        self.assertEqual(status, 200)
        self.assertIn("test", body["sessions"])

    def test_session_load(self):
        self.agent.run("hello")
        self._request("POST", "/session/save", {"name": "my_session"})

        new_agent = MiniAgent(build_default_registry())
        self.server.__class__.agent = new_agent
        status, body = self._request("POST", "/session/load", {"name": "my_session"})

        self.assertEqual(status, 200)
        self.assertIn("已恢复", body["result"])

    def test_session_load_requires_name(self):
        status, body = self._request("POST", "/session/load", {})

        self.assertEqual(status, 400)
        self.assertIn("required", body["error"])

    def test_not_found(self):
        status, body = self._request("GET", "/nonexistent")

        self.assertEqual(status, 404)

    def test_chat_stream_returns_sse_events(self):
        import socket
        url = f"http://127.0.0.1:{self.port}/chat/stream"
        data = json.dumps({"message": "计算 2 + 3"}).encode("utf-8")
        req = Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        with urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/event-stream", resp.headers.get("Content-Type", ""))
            chunks = []
            while True:
                try:
                    line = resp.readline()
                    if not line:
                        break
                    chunks.append(line.decode("utf-8"))
                except socket.timeout:
                    break

        raw = "".join(chunks)
        events = [line.removeprefix("data: ") for line in raw.strip().splitlines() if line.startswith("data: ")]
        self.assertGreater(len(events), 0)
        last_event = json.loads(events[-1])
        self.assertEqual(last_event["type"], "done")

    def test_chat_stream_rejects_empty_message(self):
        status, body = self._request("POST", "/chat/stream", {"message": ""})

        self.assertEqual(status, 400)
        self.assertIn("required", body["error"])

    def test_docs_endpoint_returns_openapi_spec(self):
        status, body = self._request("GET", "/docs")

        self.assertEqual(status, 200)
        self.assertEqual(body["openapi"], "3.0.0")
        self.assertIn("/chat", body["paths"])
        self.assertIn("/health", body["paths"])

    def test_cors_headers_present(self):
        url = f"http://127.0.0.1:{self.port}/health"
        req = Request(url)
        with urlopen(req) as resp:
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_options_returns_cors_headers(self):
        import urllib.request
        url = f"http://127.0.0.1:{self.port}/chat"
        req = urllib.request.Request(url, method="OPTIONS")
        req.add_header("Origin", "http://localhost:3000")
        req.add_header("Access-Control-Request-Method", "POST")
        try:
            with urlopen(req) as resp:
                self.assertEqual(resp.status, 204)
                self.assertIn("*", resp.headers.get("Access-Control-Allow-Origin", ""))
        except urllib.error.HTTPError:
            pass


class HTTPServerRateLimitTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        self.agent = MiniAgent(build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"))
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            rate_limit=2,
            rate_burst=2,
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

    def test_rate_limit_blocks_excessive_requests(self):
        status1, _ = self._request("POST", "/chat", {"message": "计算 1+1"})
        status2, _ = self._request("POST", "/chat", {"message": "计算 2+2"})
        status3, body = self._request("POST", "/chat", {"message": "计算 3+3"})

        self.assertEqual(status1, 200)
        self.assertEqual(status2, 200)
        self.assertEqual(status3, 429)
        self.assertIn("rate limit", body["error"])


class HTTPServerAuthTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        self.agent = MiniAgent(build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"))
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            api_token="test-secret",
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

    def test_rejects_unauthenticated_chat(self):
        status, body = self._request("POST", "/chat", {"message": "hello"})

        self.assertEqual(status, 401)
        self.assertIn("unauthorized", body["error"])

    def test_accepts_authenticated_chat(self):
        status, body = self._request(
            "POST", "/chat",
            {"message": "计算 1 + 1"},
            headers={"Authorization": "Bearer test-secret"},
        )

        self.assertEqual(status, 200)
        self.assertIn("response", body)

    def test_health_works_without_auth(self):
        status, body = self._request("GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")


if __name__ == "__main__":
    unittest.main()
