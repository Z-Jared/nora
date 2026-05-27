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

    def test_chat_clear_resets_memory(self):
        self.agent.run("hello")
        self.assertGreater(len(self.agent.memory.messages()), 0)

        status, body = self._request("POST", "/chat/clear", {})

        self.assertEqual(status, 200)
        self.assertEqual(body["result"], "cleared")
        self.assertEqual(len(self.agent.memory.messages()), 0)

    def test_chat_clear_allows_new_save_without_old_messages(self):
        self.agent.run("first message")
        self._request("POST", "/chat/clear", {})

        self.agent.run("second message")
        status, body = self._request("POST", "/session/save", {"name": "after_clear"})

        self.assertEqual(status, 200)
        self.assertIn("已保存", body["result"])

        status, body = self._request("POST", "/session/load", {"name": "after_clear"})
        self.assertEqual(status, 200)
        contents = [m["content"] for m in body["messages"]]
        self.assertNotIn("first message", contents)
        self.assertIn("second message", contents)

    def test_chat_clear_returns_json(self):
        status, body = self._request("POST", "/chat/clear", {})

        self.assertEqual(status, 200)
        self.assertIsInstance(body, dict)
        self.assertIn("result", body)

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
        self.assertIn("messages", body)
        self.assertTrue(any(message["role"] == "user" and message["content"] == "hello" for message in body["messages"]))

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

    def test_chat_stream_executes_tools_and_reports(self):
        import socket
        url = f"http://127.0.0.1:{self.port}/chat/stream"
        data = json.dumps({"message": "计算 2 + 3"}).encode("utf-8")
        req = Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        with urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
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
        parsed = [json.loads(e) for e in events]
        types = [e["type"] for e in parsed]
        self.assertIn("tool_call_start", types)
        self.assertIn("tool_call_result", types)
        self.assertIn("delta", types)
        self.assertEqual(types[-1], "done")

        last_event = parsed[-1]
        self.assertEqual(last_event["status"], "done")
        self.assertGreater(last_event.get("tool_calls", 0), 0)

        all_content = "".join(
            e.get("content", "") for e in parsed if e["type"] == "delta"
        )
        self.assertIn("计算结果", all_content)

    def test_chat_stream_realtime_events(self):
        import socket
        url = f"http://127.0.0.1:{self.port}/chat/stream"
        data = json.dumps({"message": "计算 1 + 1"}).encode("utf-8")
        req = Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        with urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
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
        events = [json.loads(line.removeprefix("data: ")) for line in raw.strip().splitlines() if line.startswith("data: ")]
        types = [e["type"] for e in events]

        self.assertEqual(types[0], "typing")
        self.assertIn("tool_call_start", types)
        self.assertIn("tool_call_result", types)
        self.assertIn("delta", types)
        self.assertEqual(types[-1], "done")

        start_idx = types.index("tool_call_start")
        result_idx = types.index("tool_call_result")
        delta_idx = types.index("delta")
        done_idx = types.index("done")
        self.assertLess(start_idx, result_idx)
        self.assertLess(result_idx, delta_idx)
        self.assertLess(delta_idx, done_idx)

        tool_start = events[start_idx]
        self.assertEqual(tool_start["name"], "calculate")
        self.assertIn("expression", tool_start["arguments"])

    def test_chat_stream_rejects_empty_message(self):
        status, body = self._request("POST", "/chat/stream", {"message": ""})

        self.assertEqual(status, 400)
        self.assertIn("required", body["error"])

    def test_docs_endpoint_returns_openapi_spec(self):
        status, body = self._request("GET", "/docs")

        self.assertEqual(status, 200)
        self.assertEqual(body["openapi"], "3.0.0")
        self.assertIn("/chat", body["paths"])
        self.assertIn("/chat/clear", body["paths"])
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

    def test_rejects_unauthenticated_clear(self):
        status, body = self._request("POST", "/chat/clear", {})

        self.assertEqual(status, 401)
        self.assertIn("unauthorized", body["error"])

    def test_accepts_authenticated_clear(self):
        self.agent.run("hello")
        status, body = self._request(
            "POST", "/chat/clear",
            {},
            headers={"Authorization": "Bearer test-secret"},
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["result"], "cleared")

    def test_health_works_without_auth(self):
        status, body = self._request("GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")


class HTTPServerStaticTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        self.agent = MiniAgent(build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"))
        static_dir = Path(__file__).resolve().parent.parent / "mini_agent" / "static"
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            static_dir=static_dir,
        )
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def _get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        req = Request(url)
        try:
            with urlopen(req) as resp:
                return resp.status, resp.headers.get("Content-Type", ""), resp.read()
        except urllib.error.HTTPError as error:
            return error.code, "", error.read()

    def test_root_returns_html(self):
        status, content_type, body = self._get("/")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn(b"Nora", body)

    def test_root_contains_event_stream_js(self):
        _, _, body = self._get("/")

        self.assertIn(b"/chat/stream", body)
        self.assertIn(b"tool_call_start", body)
        self.assertIn(b"tool_call_result", body)
        self.assertIn(b"Authorization", body)
        self.assertIn(b"nora_token", body)
        self.assertIn(b"/chat/clear", body)
        self.assertIn(b"new-chat-btn", body)
        self.assertIn(b"mobile-new-btn", body)

    def test_missing_static_returns_404(self):
        status, _, _ = self._get("/static/nonexistent.txt")

        self.assertEqual(status, 404)

    def test_path_traversal_dot_dot_returns_404(self):
        status, _, _ = self._get("/static/../settings.py")

        self.assertEqual(status, 404)

    def test_path_traversal_encoded_returns_404(self):
        status, _, _ = self._get("/static/%2e%2e/settings.py")

        self.assertEqual(status, 404)

    def test_static_index_html_accessible(self):
        status, content_type, body = self._get("/static/index.html")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn(b"Nora", body)

    def test_without_static_dir_root_returns_404(self):
        port = _find_free_port()
        agent = MiniAgent(build_default_registry())
        server = create_server(agent, host="127.0.0.1", port=port)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            url = f"http://127.0.0.1:{port}/"
            req = Request(url)
            try:
                with urlopen(req) as resp:
                    status = resp.status
            except urllib.error.HTTPError as error:
                status = error.code
            self.assertEqual(status, 404)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()


class HTTPServerStreamFormatTests(unittest.TestCase):
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

    def test_chat_stream_sse_format_preserved(self):
        import socket
        url = f"http://127.0.0.1:{self.port}/chat/stream"
        data = json.dumps({"message": "计算 2 + 3"}).encode("utf-8")
        req = Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        with urlopen(req, timeout=10) as resp:
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
        parsed = [json.loads(e) for e in events]
        types = [e["type"] for e in parsed]

        self.assertEqual(types[0], "typing")
        self.assertIn("tool_call_start", types)
        self.assertIn("tool_call_result", types)
        self.assertIn("delta", types)
        self.assertEqual(types[-1], "done")


if __name__ == "__main__":
    unittest.main()
