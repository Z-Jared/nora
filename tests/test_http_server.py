import json
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from urllib.request import Request, urlopen

from mini_agent.controller import MiniAgent
from mini_agent.database import NoraDB
from mini_agent.http_server import create_server
from mini_agent.memory import LongTermMemory
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
        self.assertIsInstance(body["sessions_structured"], list)
        self.assertTrue(any(s["name"] == "test" for s in body["sessions_structured"]))
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

    def test_session_save_two_and_list_order(self):
        self.agent.run("first message")
        status, _ = self._request("POST", "/session/save", {"name": "alpha"})
        self.assertEqual(status, 200)

        self.agent.run("second message")
        status, _ = self._request("POST", "/session/save", {"name": "beta"})
        self.assertEqual(status, 200)

        status, body = self._request("GET", "/session/list")
        self.assertEqual(status, 200)
        sessions = body["sessions_structured"]
        self.assertIsInstance(sessions, list)
        names = [s["name"] for s in sessions]
        self.assertIn("alpha", names)
        self.assertIn("beta", names)
        self.assertIn("alpha", body["sessions"])
        self.assertIn("beta", body["sessions"])

    def test_session_load_nonexistent_returns_error(self):
        status, body = self._request("POST", "/session/load", {"name": "does_not_exist"})

        self.assertEqual(status, 200)
        self.assertIn("未找到会话", body["result"])
        self.assertEqual(body["messages"], [])

    def test_session_name_with_spaces_sanitized(self):
        self.agent.run("hello")
        status, body = self._request("POST", "/session/save", {"name": "has spaces"})

        self.assertEqual(status, 200)
        self.assertIn("已保存", body["result"])
        self.assertIn("hasspaces", body["result"])

    def test_session_name_with_chinese_allowed(self):
        self.agent.run("hello")
        status, body = self._request("POST", "/session/save", {"name": "中文会话"})

        self.assertEqual(status, 200)
        self.assertIn("已保存", body["result"])
        self.assertIn("中文会话", body["result"])

    def test_session_name_with_quotes_sanitized(self):
        self.agent.run("hello")
        status, body = self._request("POST", "/session/save", {"name": "it's \"quoted\""})

        self.assertEqual(status, 200)
        self.assertIn("已保存", body["result"])
        self.assertIn("itsquoted", body["result"])

    def test_session_name_with_hyphens_and_underscores_allowed(self):
        self.agent.run("hello")
        status, body = self._request("POST", "/session/save", {"name": "my-session_v2"})

        self.assertEqual(status, 200)
        self.assertIn("已保存", body["result"])
        self.assertIn("my-session_v2", body["result"])

    def test_session_save_auto_generates_name(self):
        self.agent.run("hello")
        status, body = self._request("POST", "/session/save", {})

        self.assertEqual(status, 200)
        self.assertIn("已保存", body["result"])
        self.assertIn("session_", body["result"])

    def test_session_save_load_roundtrip_messages(self):
        self.agent.run("question one")
        self.agent.run("question two")
        self._request("POST", "/session/save", {"name": "roundtrip"})

        new_agent = MiniAgent(build_default_registry())
        self.server.__class__.agent = new_agent
        status, body = self._request("POST", "/session/load", {"name": "roundtrip"})

        self.assertEqual(status, 200)
        contents = [m["content"] for m in body["messages"]]
        self.assertIn("question one", contents)
        self.assertIn("question two", contents)

    def test_session_list_structured_fields(self):
        self.agent.run("hello")
        self._request("POST", "/session/save", {"name": "my-session"})

        status, body = self._request("GET", "/session/list")
        self.assertEqual(status, 200)
        self.assertIsInstance(body["sessions"], str)
        self.assertIn("my-session", body["sessions"])
        sessions = body["sessions_structured"]
        self.assertIsInstance(sessions, list)
        self.assertEqual(len(sessions), 1)
        session = sessions[0]
        self.assertEqual(session["name"], "my-session")
        self.assertIn("message_count", session)
        self.assertIn("saved_at", session)
        self.assertIsInstance(session["message_count"], int)
        self.assertGreater(session["message_count"], 0)
        self.assertTrue(session["saved_at"])

    def test_session_list_empty_returns_legacy_string(self):
        status, body = self._request("GET", "/session/list")
        self.assertEqual(status, 200)
        self.assertIsInstance(body["sessions"], str)
        self.assertIn("暂无", body["sessions"])
        self.assertEqual(body["sessions_structured"], [])

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
        self.assertIn(last_event["status"], ("done", "blocked", "error"))
        self.assertIsInstance(last_event["tool_calls"], int)
        self.assertIsInstance(last_event["message_count"], int)
        self.assertIn("steps_used", last_event)
        self.assertIn("failure", last_event)

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
        self.assertIn(last_event["status"], ("done", "blocked", "error"))
        self.assertIsInstance(last_event["tool_calls"], int)
        self.assertGreater(last_event.get("tool_calls", 0), 0)
        self.assertIsInstance(last_event["message_count"], int)
        self.assertEqual(last_event["message_count"], 2)
        self.assertIn("steps_used", last_event)
        self.assertIn("failure", last_event)

        tool_start = next(e for e in parsed if e["type"] == "tool_call_start")
        self.assertEqual(tool_start["name"], "calculate")
        self.assertIn("arguments", tool_start)
        self.assertIn("expression", tool_start["arguments"])

        tool_result = next(e for e in parsed if e["type"] == "tool_call_result")
        self.assertEqual(tool_result["name"], "calculate")
        self.assertIn(tool_result["status"], ("ok", "error", "blocked", "cancelled", "budget_exceeded"))
        self.assertIn("result", tool_result)

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

        done = events[done_idx]
        self.assertIn(done["status"], ("done", "blocked", "error"))
        self.assertIsInstance(done["tool_calls"], int)
        self.assertIsInstance(done["message_count"], int)
        self.assertIn("steps_used", done)
        self.assertIn("failure", done)

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

    def test_status_endpoint_returns_200(self):
        status, body = self._request("GET", "/status")

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_status_auth_required_false_without_token(self):
        _, body = self._request("GET", "/status")

        self.assertFalse(body["auth_required"])

    def test_status_contains_expected_keys(self):
        _, body = self._request("GET", "/status")

        self.assertIn("auth_required", body)
        self.assertIn("provider", body)
        self.assertIn("model", body)
        self.assertIn("workspace", body)
        self.assertIn("features", body)
        self.assertIn("sessions", body["features"])
        self.assertIn("tasks", body["features"])
        self.assertIn("memory", body["features"])
        self.assertIn("websocket", body["features"])

    def test_status_no_sensitive_data(self):
        _, body = self._request("GET", "/status")
        raw = json.dumps(body).lower()

        self.assertNotIn("api_key", raw)
        self.assertNotIn("api_token", raw)
        self.assertNotIn("secret", raw)
        self.assertNotIn("sk-", raw)

    def test_status_empty_provider_model_still_200(self):
        _, body = self._request("GET", "/status")

        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["provider"], "")
        self.assertEqual(body["model"], "")

    def test_status_config_warnings_all_missing(self):
        _, body = self._request("GET", "/status")

        self.assertIn("config_warnings", body)
        self.assertIn("missing provider", body["config_warnings"])
        self.assertIn("missing model", body["config_warnings"])
        self.assertIn("missing api key", body["config_warnings"])

    def test_status_required_env_field(self):
        _, body = self._request("GET", "/status")

        self.assertIn("required_env", body)
        self.assertIsInstance(body["required_env"], list)

    def test_status_accepted_env_alternatives_field(self):
        _, body = self._request("GET", "/status")

        self.assertIn("accepted_env_alternatives", body)
        self.assertIsInstance(body["accepted_env_alternatives"], dict)


class _StatusServerMixin:
    server_kwargs: dict = {}

    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        self.agent = MiniAgent(build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"))
        kwargs = dict(self.server_kwargs)
        if "llm_required_env" not in kwargs:
            from mini_agent.settings import required_env_vars
            kwargs["llm_required_env"] = required_env_vars(kwargs.get("llm_provider", ""))
        if "llm_env_alternatives" not in kwargs:
            from mini_agent.settings import env_alternatives
            kwargs["llm_env_alternatives"] = env_alternatives(kwargs.get("llm_provider", ""))
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            **kwargs,
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

    def get_status(self):
        return self._request("GET", "/status")


class HTTPServerStatusAuthTests(_StatusServerMixin, unittest.TestCase):
    server_kwargs = {
        "api_token": "test-secret",
        "llm_provider": "openai-compatible",
        "llm_model": "gpt-4.1-mini",
        "workspace": "/tmp/test",
    }

    def test_status_auth_required_true_with_token(self):
        status, body = self.get_status()

        self.assertEqual(status, 200)
        self.assertTrue(body["auth_required"])

    def test_status_no_auth_needed_even_with_token(self):
        status, body = self.get_status()

        self.assertEqual(status, 200)
        self.assertEqual(body["provider"], "openai-compatible")
        self.assertEqual(body["model"], "gpt-4.1-mini")
        self.assertEqual(body["workspace"], "/tmp/test")

    def test_status_does_not_leak_token(self):
        _, body = self.get_status()
        raw = json.dumps(body)

        self.assertNotIn("test-secret", raw)

    def test_status_features_false_when_unconfigured(self):
        _, body = self.get_status()

        self.assertFalse(body["features"]["sessions"])
        self.assertFalse(body["features"]["tasks"])
        self.assertFalse(body["features"]["memory"])
        self.assertTrue(body["features"]["websocket"])

    def test_status_runtime_present(self):
        _, body = self.get_status()

        self.assertIn("runtime", body)
        self.assertIn("python", body["runtime"])
        self.assertIn("platform", body["runtime"])
        self.assertTrue(len(body["runtime"]["python"]) > 0)
        self.assertTrue(len(body["runtime"]["platform"]) > 0)

    def test_status_runtime_no_sensitive_data(self):
        _, body = self.get_status()
        raw = json.dumps(body["runtime"]).lower()

        self.assertNotIn("api_key", raw)
        self.assertNotIn("api_token", raw)
        self.assertNotIn("token", raw)
        self.assertNotIn("secret", raw)
        self.assertNotIn("sk-", raw)

    def test_status_llm_configured_false_without_flag(self):
        _, body = self.get_status()

        self.assertIn("llm_configured", body)
        self.assertFalse(body["llm_configured"])

    def test_status_llm_configured_no_key_leak(self):
        _, body = self.get_status()
        raw = json.dumps(body).lower()

        self.assertNotIn("sk-", raw)
        self.assertNotIn("bearer", raw)
        self.assertNotIn("secret", raw)

    def test_status_config_warnings_missing_api_key(self):
        _, body = self.get_status()

        self.assertIn("config_warnings", body)
        self.assertIn("missing api key", body["config_warnings"])
        self.assertNotIn("missing provider", body["config_warnings"])
        self.assertNotIn("missing model", body["config_warnings"])

    def test_status_required_env_openai(self):
        _, body = self.get_status()

        self.assertEqual(body["required_env"], ["LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"])

    def test_status_accepted_env_alternatives_openai(self):
        _, body = self.get_status()

        self.assertEqual(body["accepted_env_alternatives"], {"LLM_API_KEY": "OPENAI_API_KEY"})


class HTTPServerStatusConfiguredTests(_StatusServerMixin, unittest.TestCase):
    server_kwargs = {
        "llm_provider": "openai-compatible",
        "llm_model": "gpt-4.1-mini",
        "llm_configured": True,
        "llm_has_api_key": True,
    }

    def test_status_llm_configured_true(self):
        status, body = self.get_status()

        self.assertEqual(status, 200)
        self.assertTrue(body["llm_configured"])

    def test_status_llm_configured_true_no_key_leak(self):
        _, body = self.get_status()
        raw = json.dumps(body).lower()

        self.assertNotIn("sk-", raw)
        self.assertNotIn("bearer", raw)
        self.assertNotIn("secret", raw)

    def test_status_config_warnings_empty_when_configured(self):
        _, body = self.get_status()

        self.assertEqual(body["config_warnings"], [])


class HTTPServerStatusAnthropicTests(_StatusServerMixin, unittest.TestCase):
    server_kwargs = {
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-5",
    }

    def test_status_required_env_anthropic(self):
        _, body = self.get_status()

        self.assertEqual(body["required_env"], ["LLM_PROVIDER", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"])

    def test_status_accepted_env_alternatives_anthropic(self):
        _, body = self.get_status()

        self.assertEqual(body["accepted_env_alternatives"], {})

    def test_status_config_warning_generic_for_anthropic(self):
        _, body = self.get_status()

        self.assertIn("missing api key", body["config_warnings"])


class HTTPServerStatusGeminiTests(_StatusServerMixin, unittest.TestCase):
    server_kwargs = {
        "llm_provider": "gemini",
        "llm_model": "gemini-2.5-pro",
    }

    def test_status_required_env_gemini(self):
        _, body = self.get_status()

        self.assertEqual(body["required_env"], ["LLM_PROVIDER", "GEMINI_API_KEY", "GEMINI_MODEL"])

    def test_status_accepted_env_alternatives_gemini(self):
        _, body = self.get_status()

        self.assertEqual(body["accepted_env_alternatives"], {})

    def test_status_config_warning_generic_for_gemini(self):
        _, body = self.get_status()

        self.assertIn("missing api key", body["config_warnings"])


class HTTPServerStatusFeaturesTests(_StatusServerMixin, unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        registry = build_default_registry(
            notes_path=Path(self.tmpdir) / "notes.txt",
            long_term_memory_path=Path(self.tmpdir) / "memory.jsonl",
            task_state_path=Path(self.tmpdir) / "task.json",
            task_history_path=Path(self.tmpdir) / "task_history.jsonl",
        )
        self.agent = MiniAgent(registry)
        self.session_store = SessionStore(Path(self.tmpdir) / "sessions")
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            session_store=self.session_store,
            task_manager=registry.task_manager,
            long_term_memory=registry.long_term_memory,
        )
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def test_status_features_true_when_configured(self):
        status, body = self.get_status()

        self.assertEqual(status, 200)
        self.assertTrue(body["features"]["sessions"])
        self.assertTrue(body["features"]["tasks"])
        self.assertTrue(body["features"]["memory"])
        self.assertTrue(body["features"]["websocket"])


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
        self.assertIn(b"stop-btn", body)
        self.assertIn(b"mobile-stop-btn", body)
        self.assertIn(b"mobile-token-area", body)
        self.assertIn(b"mobile-runtime-container", body)
        self.assertIn(b"task-panel", body)
        self.assertIn(b"mobile-task-container", body)
        self.assertIn(b"fetchTask", body)
        self.assertIn(b"/task/start", body)
        self.assertIn(b"/task/next", body)
        self.assertIn(b"/task/finish", body)
        self.assertIn(b"memory-panel", body)
        self.assertIn(b"mobile-memory-container", body)
        self.assertIn(b"fetchMemories", body)
        self.assertIn(b"/memory/list", body)
        self.assertIn(b"/memory/save", body)
        self.assertIn(b"/memory/delete", body)
        self.assertIn(b"memory_id", body)
        self.assertIn(b"JSON.stringify({memory_id: memoryId})", body)
        self.assertIn(b"AbortController", body)

    def test_stop_buttons_initially_disabled(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        desktop = re.search(r'id="stop-btn"[^>]*disabled', html)
        mobile = re.search(r'id="mobile-stop-btn"[^>]*disabled', html)
        self.assertIsNotNone(desktop, "desktop stop-btn must be initially disabled")
        self.assertIsNotNone(mobile, "mobile-stop-btn must be initially disabled")

    def test_save_button_initially_disabled(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        save = re.search(r'id="save-btn"[^>]*disabled', html)
        self.assertIsNotNone(save, "save-btn must be initially disabled")

    def test_mobile_auth_error_css_class(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn("mobile-token.auth-error", html)
        self.assertIn("mobile-token-area", html)

    def test_mobile_runtime_container_exists(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn('id="mobile-runtime-container"', html)

    def test_task_panel_and_mobile_container_exist(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn('id="task-panel"', html)
        self.assertIn('id="mobile-task-container"', html)
        self.assertIn("task-section", html)
        self.assertIn("No active task", html)
        self.assertIn("Start task", html)

    def test_task_finish_summary_copy_is_required(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn("Task summary (required)", html)
        self.assertNotIn("Task summary (optional)", html)

    def test_memory_panel_and_mobile_container_exist(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn('id="memory-panel"', html)
        self.assertIn('id="mobile-memory-container"', html)
        self.assertIn("memory-section", html)
        self.assertIn("No memories yet", html)
        self.assertIn("Save memory", html)

    def test_auth_recovery_retries_task_fetch(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn("function recoverAfterAuthInput", html)
        self.assertIn("loadSessions();", html)
        self.assertIn("fetchTask();", html)
        self.assertIn("fetchMemories();", html)

    def test_session_save_form_elements_exist(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn('id="session-save-form"', html)
        self.assertIn('id="session-name-input"', html)
        self.assertIn('id="session-save-confirm"', html)
        self.assertIn('id="session-save-cancel"', html)
        self.assertIn("session-save-form", html)
        self.assertIn("confirmSaveSession", html)
        self.assertIn("cancelSessionSave", html)
        self.assertIn("renderSessionSaveForm", html)
        self.assertIn("sessionSaveFormOpen", html)

    def test_session_endpoints_use_auth_headers(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        self.assertIsNotNone(re.search(r"fetch\('/session/list'[\s\S]*?headers:\s*authHeaders\(\)", html))
        self.assertIsNotNone(re.search(r"fetch\('/session/save'[\s\S]*?headers:\s*authHeaders\(\)", html))
        self.assertIsNotNone(re.search(r"fetch\('/session/load'[\s\S]*?headers:\s*authHeaders\(\)", html))

    def test_session_endpoints_handle_auth_error(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        self.assertIsNotNone(re.search(r"fetch\('/session/list'[\s\S]*?handleAuthError\(resp\)", html))
        self.assertIsNotNone(re.search(r"fetch\('/session/save'[\s\S]*?handleAuthError\(resp\)", html))
        self.assertIsNotNone(re.search(r"fetch\('/session/load'[\s\S]*?handleAuthError\(resp\)", html))

    def test_session_core_functions_exist(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn("function confirmSaveSession", html)
        self.assertIn("function loadSession", html)
        self.assertIn("function loadSessions", html)

    def test_handle_auth_error_sets_state(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function handleAuthError\([^)]*\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "handleAuthError function not found")
        body_text = match.group(1)
        self.assertIn("setState('error'", body_text)
        self.assertIn("Authorization token required or invalid", body_text)
        self.assertIn("authFailed = true", body_text)

    def test_send_btn_recovered_after_auth_error(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function sendMessage\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "sendMessage function not found")
        body_text = match.group(1)
        self.assertIn("sendBtn.disabled = true", body_text)
        self.assertIn("applyReadinessState()", body_text)
        self.assertIn("runBtn", body_text)

    def test_token_recovery_refreshes_session_task_memory(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function recoverAfterAuthInput\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "recoverAfterAuthInput function not found")
        body_text = match.group(1)
        self.assertIn("loadSessions()", body_text)
        self.assertIn("fetchTask()", body_text)
        self.assertIn("fetchMemories()", body_text)
        self.assertIn("setState('ready'", body_text)

    def test_auth_error_shows_in_mobile_status(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn("authFailed", html)
        self.assertIn("Auth required", html)
        self.assertIn("Enter a valid token", html)

    def test_fetch_status_on_page_load(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn("fetch('/status'", html)
        self.assertIn("fetchStatus()", html)

    def test_status_renders_provider_model_workspace(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn("renderServerPanel", html)
        self.assertIn("data.provider", html)
        self.assertIn("data.model", html)
        self.assertIn("data.workspace", html)

    def test_status_renders_features(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn("data.features", html)
        self.assertIn("sessions", html)
        self.assertIn("tasks", html)
        self.assertIn("memory", html)
        self.assertIn("websocket", html)
        self.assertIn("feature-tag", html)

    def test_status_failure_sets_error_state(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function fetchStatus\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "fetchStatus function not found")
        fn_body = match.group(1)
        self.assertIn("setState('error'", fn_body)
        self.assertIn("Failed to connect to server", fn_body)

    def test_status_auth_required_affects_prompt(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function fetchStatus\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "fetchStatus function not found")
        fn_body = match.group(1)
        self.assertIn("data.auth_required", fn_body)
        self.assertIn("Authorization token required or invalid", fn_body)

    def test_server_panel_element_exists(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn('id="server-panel"', html)
        self.assertIn("server-info", html)
        self.assertIn("server-row", html)
        self.assertIn("server-label", html)
        self.assertIn("server-value", html)

    def test_auth_required_disables_send_run(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function applyReadinessState\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "applyReadinessState function not found")
        fn_body = match.group(1)
        self.assertIn("sendBtn.disabled = !next.enabled", fn_body)
        self.assertIn("runBtn", fn_body)
        self.assertIn("updateComposerStatus(next.message", fn_body)

    def test_token_input_restores_send_run(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function recoverAfterAuthInput\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "recoverAfterAuthInput function not found")
        fn_body = match.group(1)
        self.assertIn("authFailed = false", fn_body)
        self.assertIn("applyReadinessState()", fn_body)

    def test_composer_status_element_exists(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn('id="composer-status"', html)
        self.assertIn("composer-status", html)
        self.assertIn("updateComposerStatus", html)

    def test_server_unreachable_shows_error(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function readinessState\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "readinessState function not found")
        fn_body = match.group(1)
        self.assertIn("Server unreachable", fn_body)
        self.assertIn("enabled:false", fn_body)

    def test_token_required_composer_status(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn("Token required", html)
        self.assertIn("'warning'", html)

    def test_llm_configured_false_disables_send(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function readinessState\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "readinessState function not found")
        fn_body = match.group(1)
        self.assertIn("serverStatus.llm_configured", fn_body)
        self.assertIn("Model not configured", fn_body)
        self.assertIn("enabled:false", fn_body)

    def test_llm_configured_shows_model_not_configured(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn("Model not configured", html)

    def test_llm_configured_true_enables_send(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function readinessState\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "readinessState function not found")
        fn_body = match.group(1)
        self.assertIn("enabled:true", fn_body)
        self.assertIn("message:'Ready'", fn_body)

    def test_server_panel_shows_model_config_missing(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function renderServerPanel\(data\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "renderServerPanel function not found")
        fn_body = match.group(1)
        self.assertIn("data.llm_configured", fn_body)
        self.assertIn("Model not configured", fn_body)
        self.assertIn("_envVarDisplay", fn_body)

    def test_provider_env_guide_function_exists(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function _providerEnvGuide\(provider\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "_providerEnvGuide function not found")
        fn_body = match.group(1)
        self.assertIn("openai-compatible", fn_body)
        self.assertIn("anthropic", fn_body)
        self.assertIn("gemini", fn_body)
        self.assertIn("LLM_API_KEY", fn_body)
        self.assertIn("ANTHROPIC_API_KEY", fn_body)
        self.assertIn("GEMINI_API_KEY", fn_body)
        self.assertIn("gpt-4.1-mini", fn_body)
        self.assertIn("claude-sonnet-4-5", fn_body)
        self.assertIn("gemini-2.5-pro", fn_body)

    def test_env_var_display_function_exists(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function _envVarDisplay\(requiredEnv, provider\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "_envVarDisplay function not found")
        fn_body = match.group(1)
        self.assertIn("requiredEnv", fn_body)
        self.assertIn("guideMap", fn_body)
        self.assertIn("_providerEnvGuide", fn_body)

    def test_env_alternatives_function_exists(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function _envAlternativesHtml\(alternatives\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "_envAlternativesHtml function not found")
        fn_body = match.group(1)
        self.assertIn("env-alternatives", fn_body)
        self.assertIn("can be replaced by", fn_body)
        self.assertIn("Object.keys", fn_body)

    def test_server_panel_shows_alternatives(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function renderServerPanel\(data\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "renderServerPanel function not found")
        fn_body = match.group(1)
        self.assertIn("accepted_env_alternatives", fn_body)
        self.assertIn("_envAlternativesHtml", fn_body)

    def test_mobile_shows_alternatives(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function renderMobileStatus\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "renderMobileStatus function not found")
        fn_body = match.group(1)
        self.assertIn("accepted_env_alternatives", fn_body)
        self.assertIn("_envAlternativesHtml", fn_body)

    def test_server_panel_shows_config_warnings(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function renderServerPanel\(data\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "renderServerPanel function not found")
        fn_body = match.group(1)
        self.assertIn("config_warnings", fn_body)
        self.assertIn("warn-list", fn_body)

    def test_server_panel_no_secret_form(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function renderServerPanel\(data\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "renderServerPanel function not found")
        fn_body = match.group(1)
        self.assertNotIn("POST", fn_body)
        self.assertNotIn("<form", fn_body)
        self.assertNotIn("type=\"password\"", fn_body)
        self.assertNotIn("type='password'", fn_body)

    def test_mobile_shows_setup_guidance(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function renderMobileStatus\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "renderMobileStatus function not found")
        fn_body = match.group(1)
        self.assertIn("llm_configured", fn_body)
        self.assertIn("_envVarDisplay", fn_body)
        self.assertIn("config_warnings", fn_body)

    def test_recover_auth_checks_server_status(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function recoverAfterAuthInput\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "recoverAfterAuthInput function not found")
        fn_body = match.group(1)
        self.assertIn("serverStatus", fn_body)
        self.assertIn("llm_configured", fn_body)

    def test_recover_auth_keeps_disabled_when_llm_not_configured(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        import re
        match = re.search(r"function recoverAfterAuthInput\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "recoverAfterAuthInput function not found")
        fn_body = match.group(1)
        self.assertIn("applyReadinessState()", fn_body)
        self.assertIn("serverStatus && !serverStatus.llm_configured", fn_body)

    def test_fetch_status_saves_server_status(self):
        _, _, body = self._get("/")
        html = body.decode("utf-8")
        self.assertIn("var serverStatus = null", html)
        import re
        match = re.search(r"function fetchStatus\(\)\{([\s\S]*?)\n  \}", html)
        self.assertIsNotNone(match, "fetchStatus function not found")
        fn_body = match.group(1)
        self.assertIn("serverStatus = data", fn_body)

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

        done = parsed[-1]
        self.assertIn(done["status"], ("done", "blocked", "error"))
        self.assertIsInstance(done["tool_calls"], int)
        self.assertIsInstance(done["message_count"], int)
        self.assertIn("steps_used", done)
        self.assertIn("failure", done)


class HTTPTaskTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        registry = build_default_registry(
            notes_path=Path(self.tmpdir) / "notes.txt",
            task_state_path=Path(self.tmpdir) / "task.json",
            task_history_path=Path(self.tmpdir) / "history.jsonl",
        )
        self.agent = MiniAgent(registry)
        self.task_manager = registry.task_manager
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            task_manager=self.task_manager,
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

    def test_get_task_empty(self):
        status, body = self._request("GET", "/task")

        self.assertEqual(status, 200)
        self.assertIsNone(body["task"])

    def test_start_task(self):
        status, body = self._request("POST", "/task/start", {
            "goal": "测试任务",
            "steps": "步骤一\n步骤二",
        })

        self.assertEqual(status, 200)
        self.assertIn("已创建", body["result"])
        self.assertEqual(body["task"]["goal"], "测试任务")
        self.assertEqual(body["task"]["status"], "active")
        self.assertEqual(len(body["task"]["steps"]), 2)

    def test_start_task_steps_as_list(self):
        status, body = self._request("POST", "/task/start", {
            "goal": "列表步骤",
            "steps": ["第一步", "第二步", "第三步"],
        })

        self.assertEqual(status, 200)
        self.assertEqual(len(body["task"]["steps"]), 3)

    def test_start_task_missing_goal(self):
        status, body = self._request("POST", "/task/start", {"steps": "步骤一"})

        self.assertEqual(status, 400)
        self.assertIn("goal", body["error"])

    def test_start_task_missing_steps(self):
        status, body = self._request("POST", "/task/start", {"goal": "目标"})

        self.assertEqual(status, 400)
        self.assertIn("steps", body["error"])

    def test_task_next(self):
        self._request("POST", "/task/start", {"goal": "测试", "steps": "步骤一\n步骤二"})

        status, body = self._request("POST", "/task/next")

        self.assertEqual(status, 200)
        self.assertIn("下一步", body["result"])
        self.assertEqual(body["task"]["steps"][0]["status"], "in_progress")

    def test_task_update(self):
        self._request("POST", "/task/start", {"goal": "测试", "steps": "步骤一\n步骤二"})

        status, body = self._request("POST", "/task/update", {
            "step_id": 1,
            "status": "done",
            "summary": "已完成",
        })

        self.assertEqual(status, 200)
        self.assertIn("已更新", body["result"])
        self.assertEqual(body["task"]["steps"][0]["status"], "done")
        self.assertEqual(body["task"]["steps"][0]["summary"], "已完成")

    def test_task_update_missing_fields(self):
        status, body = self._request("POST", "/task/update", {"step_id": 1})

        self.assertEqual(status, 400)
        self.assertIn("status", body["error"])

    def test_task_finish(self):
        self._request("POST", "/task/start", {"goal": "测试", "steps": "步骤一"})
        self._request("POST", "/task/update", {"step_id": 1, "status": "done", "summary": "完成"})

        status, body = self._request("POST", "/task/finish", {"summary": "全部完成"})

        self.assertEqual(status, 200)
        self.assertIn("已完成", body["result"])
        self.assertIsNone(body["task"])

    def test_task_finish_missing_summary(self):
        self._request("POST", "/task/start", {"goal": "测试", "steps": "步骤一"})

        status, body = self._request("POST", "/task/finish", {})

        self.assertEqual(status, 400)
        self.assertIn("summary", body["error"])

    def test_full_task_lifecycle(self):
        self._request("POST", "/task/start", {"goal": "完整流程", "steps": "步骤一\n步骤二"})

        self._request("POST", "/task/next")
        self._request("POST", "/task/update", {"step_id": 1, "status": "done", "summary": "ok"})
        self._request("POST", "/task/next")
        self._request("POST", "/task/update", {"step_id": 2, "status": "done", "summary": "ok"})

        status, body = self._request("POST", "/task/finish", {"summary": "流程结束"})
        self.assertEqual(status, 200)

        status, body = self._request("GET", "/task")
        self.assertEqual(status, 200)
        self.assertIsNone(body["task"])


class HTTPTaskAuthTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        registry = build_default_registry(
            notes_path=Path(self.tmpdir) / "notes.txt",
            task_state_path=Path(self.tmpdir) / "task.json",
            task_history_path=Path(self.tmpdir) / "history.jsonl",
        )
        self.agent = MiniAgent(registry)
        self.task_manager = registry.task_manager
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            task_manager=self.task_manager,
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

    def test_task_start_rejected_without_auth(self):
        status, body = self._request("POST", "/task/start", {
            "goal": "测试", "steps": "步骤一",
        })

        self.assertEqual(status, 401)
        self.assertIn("unauthorized", body["error"])

    def test_task_start_accepted_with_auth(self):
        status, body = self._request(
            "POST", "/task/start",
            {"goal": "测试", "steps": "步骤一"},
            headers={"Authorization": "Bearer test-secret"},
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["task"]["goal"], "测试")

    def test_get_task_rejected_without_auth(self):
        status, body = self._request("GET", "/task")

        self.assertEqual(status, 401)
        self.assertIn("unauthorized", body["error"])


class HTTPMemoryTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        registry = build_default_registry(
            notes_path=Path(self.tmpdir) / "notes.txt",
            long_term_memory_path=Path(self.tmpdir) / "memory.jsonl",
        )
        self.agent = MiniAgent(registry)
        self.long_term_memory = registry.long_term_memory
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            long_term_memory=self.long_term_memory,
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

    def test_memory_list_empty(self):
        status, body = self._request("GET", "/memory/list")

        self.assertEqual(status, 200)
        self.assertEqual(body["memories"], [])

    def test_memory_save(self):
        status, body = self._request("POST", "/memory/save", {
            "text": "测试记忆内容",
            "tags": "test,important",
        })

        self.assertEqual(status, 200)
        self.assertIn("已保存", body["result"])
        self.assertEqual(body["memory"]["text"], "测试记忆内容")
        self.assertIn("test", body["memory"]["tags"])
        self.assertIn("important", body["memory"]["tags"])

    def test_memory_save_missing_text(self):
        status, body = self._request("POST", "/memory/save", {})

        self.assertEqual(status, 400)
        self.assertIn("text", body["error"])

    def test_memory_save_rejects_sensitive(self):
        status, body = self._request("POST", "/memory/save", {
            "text": "my API_KEY is sk-abc123",
        })

        self.assertEqual(status, 400)
        self.assertIn("拒绝", body["error"])

    def test_memory_list_after_save(self):
        self._request("POST", "/memory/save", {"text": "第一条", "tags": "a"})
        self._request("POST", "/memory/save", {"text": "第二条", "tags": "b"})

        status, body = self._request("GET", "/memory/list")

        self.assertEqual(status, 200)
        self.assertEqual(len(body["memories"]), 2)
        texts = [m["text"] for m in body["memories"]]
        self.assertIn("第一条", texts)
        self.assertIn("第二条", texts)

    def test_memory_search(self):
        self._request("POST", "/memory/save", {"text": "Python 编程技巧", "tags": "python"})
        self._request("POST", "/memory/save", {"text": "JavaScript 框架", "tags": "js"})

        status, body = self._request("GET", "/memory/search?q=Python")

        self.assertEqual(status, 200)
        self.assertEqual(len(body["memories"]), 1)
        self.assertEqual(body["memories"][0]["text"], "Python 编程技巧")

    def test_memory_search_empty_query(self):
        status, body = self._request("GET", "/memory/search")

        self.assertEqual(status, 400)
        self.assertIn("q", body["error"])

    def test_memory_search_no_results(self):
        self._request("POST", "/memory/save", {"text": "Python 编程", "tags": ""})

        status, body = self._request("GET", "/memory/search?q=JavaScript")

        self.assertEqual(status, 200)
        self.assertEqual(body["memories"], [])

    def test_memory_delete(self):
        self._request("POST", "/memory/save", {"text": "要删除的记忆", "tags": ""})
        list_status, list_body = self._request("GET", "/memory/list")
        memory_id = list_body["memories"][0]["id"]

        status, body = self._request("POST", "/memory/delete", {"memory_id": memory_id})

        self.assertEqual(status, 200)
        self.assertIn("已删除", body["result"])

        list_status, list_body = self._request("GET", "/memory/list")
        self.assertEqual(len(list_body["memories"]), 0)

    def test_memory_delete_not_found(self):
        status, body = self._request("POST", "/memory/delete", {"memory_id": "mem_999"})

        self.assertEqual(status, 404)
        self.assertIn("没有找到", body["error"])

    def test_memory_delete_missing_id(self):
        status, body = self._request("POST", "/memory/delete", {})

        self.assertEqual(status, 400)
        self.assertIn("memory_id", body["error"])

    def test_memory_save_returns_correct_record_consecutive(self):
        status1, body1 = self._request("POST", "/memory/save", {
            "text": "first memory",
            "tags": "a",
        })
        self.assertEqual(status1, 200)
        self.assertEqual(body1["memory"]["text"], "first memory")

        status2, body2 = self._request("POST", "/memory/save", {
            "text": "second memory",
            "tags": "b",
        })
        self.assertEqual(status2, 200)
        self.assertEqual(body2["memory"]["text"], "second memory")
        self.assertNotEqual(body2["memory"]["id"], body1["memory"]["id"])

    def test_memory_save_returns_correct_record_consecutive_sqlite(self):
        db = NoraDB(Path(self.tmpdir) / "memory.db")
        try:
            self.server.__class__.long_term_memory = LongTermMemory(db=db)

            status1, body1 = self._request("POST", "/memory/save", {
                "text": "sqlite first memory",
                "tags": "a",
            })
            self.assertEqual(status1, 200)
            self.assertEqual(body1["memory"]["text"], "sqlite first memory")

            status2, body2 = self._request("POST", "/memory/save", {
                "text": "sqlite second memory",
                "tags": "b",
            })
            self.assertEqual(status2, 200)
            self.assertEqual(body2["memory"]["text"], "sqlite second memory")
            self.assertNotEqual(body2["memory"]["id"], body1["memory"]["id"])
        finally:
            db.close()


class HTTPMemoryAuthTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        registry = build_default_registry(
            notes_path=Path(self.tmpdir) / "notes.txt",
            long_term_memory_path=Path(self.tmpdir) / "memory.jsonl",
        )
        self.agent = MiniAgent(registry)
        self.long_term_memory = registry.long_term_memory
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            long_term_memory=self.long_term_memory,
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

    def test_memory_save_rejected_without_auth(self):
        status, body = self._request("POST", "/memory/save", {"text": "test"})

        self.assertEqual(status, 401)
        self.assertIn("unauthorized", body["error"])

    def test_memory_save_accepted_with_auth(self):
        status, body = self._request(
            "POST", "/memory/save",
            {"text": "authenticated save", "tags": "auth"},
            headers={"Authorization": "Bearer test-secret"},
        )

        self.assertEqual(status, 200)
        self.assertIn("已保存", body["result"])

    def test_memory_list_rejected_without_auth(self):
        status, body = self._request("GET", "/memory/list")

        self.assertEqual(status, 401)
        self.assertIn("unauthorized", body["error"])

    def test_memory_search_rejected_without_auth(self):
        status, body = self._request("GET", "/memory/search?q=test")

        self.assertEqual(status, 401)
        self.assertIn("unauthorized", body["error"])


class PetHTTPServerTests(unittest.TestCase):
    """Tests for pet HTTP API endpoints."""

    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        from mini_agent.database import NoraDB
        from mini_agent.pets import PetStore
        db = NoraDB(Path(self.tmpdir) / "test.db")
        self.pet_store = PetStore(db=db)
        self.agent = MiniAgent(build_default_registry(
            notes_path=Path(self.tmpdir) / "notes.txt",
            db=db,
        ))
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            pet_store=self.pet_store,
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

    def test_pet_current_creates_default(self):
        status, body = self._request("GET", "/pet/current")
        self.assertEqual(status, 200)
        self.assertEqual(body["identity"]["name"], "Nora-01")
        self.assertEqual(body["identity"]["species"], "robot_pet")
        self.assertEqual(body["pet_id"], "pet_1")
        self.assertIn("curious", body["identity"]["personality_traits"])
        self.assertIn("memory", body["identity"]["skills"])

    def test_pet_current_returns_existing(self):
        self.pet_store.create_pet(name="Mochi", species="cat")
        status, body = self._request("GET", "/pet/current")
        self.assertEqual(status, 200)
        self.assertEqual(body["identity"]["name"], "Mochi")

    def test_pet_create(self):
        status, body = self._request("POST", "/pet/create", {"name": "Luna", "species": "digital_bunny"})
        self.assertEqual(status, 200)
        self.assertEqual(body["identity"]["name"], "Luna")
        self.assertEqual(body["identity"]["species"], "digital_bunny")
        self.assertEqual(body["state"]["hunger"], 30)

    def test_pet_create_requires_name(self):
        status, body = self._request("POST", "/pet/create", {})
        self.assertEqual(status, 400)
        self.assertIn("name required", body["error"])

    def test_pet_create_rejects_sensitive_name(self):
        status, body = self._request("POST", "/pet/create", {"name": "sk-secret-key-12345"})
        self.assertEqual(status, 400)

    def test_pet_add_food(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/add-food", {"pet_id": "pet_1", "amount": 500, "reason": "demo"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["state"]["compute_food_balance"], 500)

    def test_pet_add_food_rejects_bad_amount(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/add-food", {"pet_id": "pet_1", "amount": -10})
        self.assertEqual(status, 400)

    def test_pet_add_food_requires_pet_id(self):
        status, body = self._request("POST", "/pet/add-food", {"amount": 100})
        self.assertEqual(status, 400)
        self.assertIn("pet_id required", body["error"])

    def test_pet_feed(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=500)
        status, body = self._request("POST", "/pet/feed", {"pet_id": "pet_1", "amount": 100})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["state"]["compute_food_balance"], 400)
        self.assertLess(body["state"]["hunger"], 30)

    def test_pet_feed_insufficient_balance(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/feed", {"pet_id": "pet_1", "amount": 100})
        self.assertEqual(status, 200)
        self.assertFalse(body["ok"])
        self.assertEqual(body["reason_label"], "insufficient_compute_food")

    def test_pet_care(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/care", {"pet_id": "pet_1", "action": "pat"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertGreater(body["state"]["mood"], 60)
        self.assertGreater(body["state"]["bond"], 0)

    def test_pet_care_invalid_action(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/care", {"pet_id": "pet_1", "action": "invalid"})
        self.assertEqual(status, 200)
        self.assertFalse(body["ok"])
        self.assertEqual(body["reason_label"], "invalid_care_action")

    def test_pet_activity(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.care_pet("pet_1", action="pat")
        self.pet_store.care_pet("pet_1", action="play")
        status, body = self._request("GET", "/pet/activity?pet_id=pet_1")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)
        self.assertTrue(len(body) >= 2)
        event_types = [e["event_type"] for e in body]
        self.assertIn("care", event_types)

    def test_pet_activity_requires_pet_id(self):
        status, body = self._request("GET", "/pet/activity")
        self.assertEqual(status, 400)
        self.assertIn("pet_id required", body["error"])

    def test_pet_activity_huge_limit_bounded(self):
        self.pet_store.create_pet(name="Mochi")
        for i in range(60):
            self.pet_store.care_pet("pet_1", action="pat")
        status, body = self._request("GET", "/pet/activity?pet_id=pet_1&limit=99999")
        self.assertEqual(status, 200)
        self.assertLessEqual(len(body), 50)

    def test_pet_activity_negative_limit_clamped(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.care_pet("pet_1", action="pat")
        status, body = self._request("GET", "/pet/activity?pet_id=pet_1&limit=-5")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)
        self.assertGreaterEqual(len(body), 1)

    def test_pet_activity_zero_limit_clamped(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.care_pet("pet_1", action="pat")
        status, body = self._request("GET", "/pet/activity?pet_id=pet_1&limit=0")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)

    def test_pet_activity_string_limit_no_crash(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.care_pet("pet_1", action="pat")
        status, body = self._request("GET", "/pet/activity?pet_id=pet_1&limit=abc")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)

    def test_status_shows_pet_feature(self):
        status, body = self._request("GET", "/status")
        self.assertEqual(status, 200)
        self.assertIn("pets", body["features"])
        self.assertTrue(body["features"]["pets"])

    def test_docs_includes_pet_endpoints(self):
        status, body = self._request("GET", "/docs")
        self.assertEqual(status, 200)
        self.assertIn("/pet/current", body["paths"])
        self.assertIn("/pet/create", body["paths"])
        self.assertIn("/pet/feed", body["paths"])
        self.assertIn("/pet/care", body["paths"])
        self.assertIn("/pet/activity", body["paths"])

    def test_pet_create_with_full_identity(self):
        status, body = self._request("POST", "/pet/create", {
            "name": "Luna",
            "species": "digital_bunny",
            "personality_traits": ["shy", "curious"],
            "relationship_role": "companion",
            "speech_style": "soft",
            "voice_profile": {"voice_id": "gentle_1", "speed": "slow"},
            "taste_profile": {"likes": ["carrots"], "dislikes": ["loud"]},
            "skills": ["hop", "snuggle"],
        })
        self.assertEqual(status, 200)
        self.assertEqual(body["identity"]["name"], "Luna")
        self.assertEqual(body["identity"]["voice_profile"]["voice_id"], "gentle_1")
        self.assertEqual(body["identity"]["taste_profile"]["likes"], ["carrots"])
        self.assertEqual(body["identity"]["skills"], ["hop", "snuggle"])

    def test_pet_create_rejects_sensitive_voice_profile(self):
        status, body = self._request("POST", "/pet/create", {
            "name": "Ok",
            "voice_profile": {"voice_id": "sk-secret-key-12345"},
        })
        self.assertEqual(status, 400)

    def test_pet_feed_rejects_string_amount(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=500)
        status, body = self._request("POST", "/pet/feed", {"pet_id": "pet_1", "amount": "100"})
        self.assertEqual(status, 400)
        self.assertIn("positive integer", body["error"])

    def test_pet_feed_rejects_zero_amount(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/feed", {"pet_id": "pet_1", "amount": 0})
        self.assertEqual(status, 400)

    def test_pet_feed_rejects_bool_amount(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=500)
        status, body = self._request("POST", "/pet/feed", {"pet_id": "pet_1", "amount": True})
        self.assertEqual(status, 400)
        self.assertIn("positive integer", body["error"])

    def test_pet_add_food_rejects_bool_amount(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/add-food", {"pet_id": "pet_1", "amount": True})
        self.assertEqual(status, 400)

    def test_pet_create_rejects_non_string_name(self):
        status, body = self._request("POST", "/pet/create", {"name": 123})
        self.assertEqual(status, 400)

    def test_pet_create_rejects_non_list_personality(self):
        status, body = self._request("POST", "/pet/create", {"name": "Ok", "personality_traits": "not-a-list"})
        self.assertEqual(status, 400)
        self.assertIn("personality_traits must be list", body["error"])

    def test_pet_create_rejects_non_dict_voice_profile(self):
        status, body = self._request("POST", "/pet/create", {"name": "Ok", "voice_profile": "not-a-dict"})
        self.assertEqual(status, 400)
        self.assertIn("voice_profile must be dict", body["error"])

    def test_pet_feed_rejects_non_string_pet_id(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/feed", {"pet_id": 123, "amount": 100})
        self.assertEqual(status, 400)

    def test_pet_care_rejects_non_string_action(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/care", {"pet_id": "pet_1", "action": 123})
        self.assertEqual(status, 400)
        self.assertIn("action must be string", body["error"])

    def test_pet_food_status_feed_sufficient(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=500)
        status, body = self._request("GET", "/pet/food-status?pet_id=pet_1&action=feed")
        self.assertEqual(status, 200)
        self.assertEqual(body["action"], "feed")
        self.assertEqual(body["balance"], 500)
        self.assertEqual(body["cost"], 100)
        self.assertTrue(body["can_run"])
        self.assertEqual(body["shortfall"], 0)
        self.assertEqual(body["reason_label"], "ok")

    def test_pet_food_status_feed_insufficient(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("GET", "/pet/food-status?pet_id=pet_1&action=feed")
        self.assertEqual(status, 200)
        self.assertEqual(body["balance"], 0)
        self.assertEqual(body["cost"], 100)
        self.assertFalse(body["can_run"])
        self.assertEqual(body["shortfall"], 100)
        self.assertEqual(body["reason_label"], "insufficient_compute_food")
        self.assertIn("100", body["message"])

    def test_pet_food_status_chat(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=30)
        status, body = self._request("GET", "/pet/food-status?pet_id=pet_1&action=chat")
        self.assertEqual(status, 200)
        self.assertEqual(body["cost"], 25)
        self.assertTrue(body["can_run"])

    def test_pet_food_status_voice_insufficient(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=50)
        status, body = self._request("GET", "/pet/food-status?pet_id=pet_1&action=voice")
        self.assertEqual(status, 200)
        self.assertEqual(body["cost"], 80)
        self.assertFalse(body["can_run"])
        self.assertEqual(body["shortfall"], 30)

    def test_pet_food_status_work(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=200)
        status, body = self._request("GET", "/pet/food-status?pet_id=pet_1&action=work")
        self.assertEqual(status, 200)
        self.assertEqual(body["cost"], 150)
        self.assertTrue(body["can_run"])

    def test_pet_food_status_default_action_is_feed(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=200)
        status, body = self._request("GET", "/pet/food-status?pet_id=pet_1")
        self.assertEqual(status, 200)
        self.assertEqual(body["action"], "feed")
        self.assertEqual(body["cost"], 100)

    def test_pet_food_status_invalid_action(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("GET", "/pet/food-status?pet_id=pet_1&action=invalid")
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "unknown action")
        self.assertIn("valid_actions", body)
        self.assertEqual(sorted(body["valid_actions"]), ["chat", "feed", "voice", "work"])

    def test_pet_food_status_secret_action_not_echoed(self):
        self.pet_store.create_pet(name="Mochi")
        secret = "sk-ant-secret-key-12345"
        status, body = self._request("GET", f"/pet/food-status?pet_id=pet_1&action={secret}")
        self.assertEqual(status, 400)
        resp = str(body)
        self.assertNotIn(secret, resp)
        self.assertEqual(body["error"], "unknown action")

    def test_pet_food_status_missing_pet_id(self):
        status, body = self._request("GET", "/pet/food-status?action=feed")
        self.assertEqual(status, 400)
        self.assertIn("pet_id required", body["error"])

    def test_pet_food_status_pet_not_found(self):
        status, body = self._request("GET", "/pet/food-status?pet_id=pet_999&action=feed")
        self.assertEqual(status, 404)

    def test_pet_food_status_read_only_no_mutation(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=50)
        # Check insufficient balance
        status, body = self._request("GET", "/pet/food-status?pet_id=pet_1&action=feed")
        self.assertFalse(body["can_run"])
        # Balance must not have changed
        pet = self.pet_store.get_pet("pet_1")
        self.assertEqual(pet.state.compute_food_balance, 50)

    def test_pet_food_status_in_docs(self):
        status, body = self._request("GET", "/docs")
        self.assertEqual(status, 200)
        self.assertIn("/pet/food-status", body["paths"])

    def test_relationship_memory_create_and_list(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/relationship-memory", {
            "pet_id": "pet_1", "kind": "shared_moment",
            "summary": "First time exploring the garden together",
            "source": "pet_room", "importance": 7,
        })
        self.assertEqual(status, 200)
        self.assertEqual(body["kind"], "shared_moment")
        self.assertEqual(body["importance"], 7)
        self.assertIn("garden", body["summary"])

        status, body = self._request("GET", "/pet/relationship-memory?pet_id=pet_1")
        self.assertEqual(status, 200)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["kind"], "shared_moment")

    def test_relationship_memory_create_preference(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/relationship-memory", {
            "pet_id": "pet_1", "kind": "preference",
            "summary": "Enjoys quiet morning chats",
        })
        self.assertEqual(status, 200)
        self.assertEqual(body["kind"], "preference")

    def test_relationship_memory_create_task_outcome(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/relationship-memory", {
            "pet_id": "pet_1", "kind": "task_outcome",
            "summary": "Successfully organized the workspace",
        })
        self.assertEqual(status, 200)
        self.assertEqual(body["kind"], "task_outcome")

    def test_relationship_memory_rejects_invalid_kind(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/relationship-memory", {
            "pet_id": "pet_1", "kind": "invalid_kind", "summary": "test",
        })
        self.assertEqual(status, 400)
        self.assertIn("invalid kind", body["error"])
        self.assertIn("valid_kinds", body)

    def test_relationship_memory_rejects_empty_summary(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/relationship-memory", {
            "pet_id": "pet_1", "kind": "shared_moment", "summary": "",
        })
        self.assertEqual(status, 400)

    def test_relationship_memory_rejects_secret_summary(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/relationship-memory", {
            "pet_id": "pet_1", "kind": "shared_moment",
            "summary": "sk-secret-key-12345",
        })
        self.assertEqual(status, 400)
        self.assertNotIn("sk-secret-key-12345", str(body))

    def test_relationship_memory_rejects_missing_pet_id(self):
        status, body = self._request("POST", "/pet/relationship-memory", {
            "kind": "shared_moment", "summary": "test",
        })
        self.assertEqual(status, 400)
        self.assertIn("pet_id required", body["error"])

    def test_relationship_memory_list_requires_pet_id(self):
        status, body = self._request("GET", "/pet/relationship-memory")
        self.assertEqual(status, 400)
        self.assertIn("pet_id required", body["error"])

    def test_relationship_memory_list_limit_bounded(self):
        self.pet_store.create_pet(name="Mochi")
        for i in range(60):
            self.pet_store.add_relationship_memory("pet_1", "shared_moment", f"moment {i}")
        status, body = self._request("GET", "/pet/relationship-memory?pet_id=pet_1&limit=999")
        self.assertEqual(status, 200)
        self.assertLessEqual(len(body), 50)

    def test_relationship_memory_in_docs(self):
        status, body = self._request("GET", "/docs")
        self.assertEqual(status, 200)
        self.assertIn("/pet/relationship-memory", body["paths"])

    def test_update_identity_name(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/update-identity", {"pet_id": "pet_1", "name": "Luna"})
        self.assertEqual(status, 200)
        self.assertEqual(body["identity"]["name"], "Luna")
        self.assertEqual(body["identity"]["species"], "digital_pet")  # unchanged default

    def test_update_identity_multiple_fields(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/update-identity", {
            "pet_id": "pet_1", "name": "Luna", "species": "cat_v2",
            "personality_traits": ["shy"], "skills": ["dance"],
        })
        self.assertEqual(status, 200)
        self.assertEqual(body["identity"]["name"], "Luna")
        self.assertEqual(body["identity"]["species"], "cat_v2")
        self.assertEqual(body["identity"]["personality_traits"], ["shy"])
        self.assertEqual(body["identity"]["skills"], ["dance"])

    def test_update_identity_preserves_state(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=500)
        self.pet_store.feed_pet("pet_1", amount=100)
        status, body = self._request("POST", "/pet/update-identity", {"pet_id": "pet_1", "name": "Luna"})
        self.assertEqual(status, 200)
        self.assertEqual(body["state"]["compute_food_balance"], 400)

    def test_update_identity_rejects_missing_pet_id(self):
        status, body = self._request("POST", "/pet/update-identity", {"name": "Luna"})
        self.assertEqual(status, 400)
        self.assertIn("pet_id required", body["error"])

    def test_update_identity_rejects_secret_name(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/update-identity", {"pet_id": "pet_1", "name": "sk-secret-key-12345"})
        self.assertEqual(status, 400)

    def test_update_identity_rejects_nonexistent_pet(self):
        status, body = self._request("POST", "/pet/update-identity", {"pet_id": "pet_999", "name": "Luna"})
        self.assertEqual(status, 400)
        self.assertIn("not found", body["error"])

    def test_update_identity_in_docs(self):
        status, body = self._request("GET", "/docs")
        self.assertEqual(status, 200)
        self.assertIn("/pet/update-identity", body["paths"])


class PetAuthHTTPServerTests(unittest.TestCase):
    """Tests for pet mutation auth when api_token is set."""

    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        from mini_agent.database import NoraDB
        from mini_agent.pets import PetStore
        db = NoraDB(Path(self.tmpdir) / "test.db")
        self.pet_store = PetStore(db=db)
        self.agent = MiniAgent(build_default_registry(
            notes_path=Path(self.tmpdir) / "notes.txt",
            db=db,
        ))
        self.server = create_server(
            self.agent,
            host="127.0.0.1",
            port=self.port,
            pet_store=self.pet_store,
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

    def test_pet_current_unauthenticated_ok(self):
        """GET /pet/current does not require auth."""
        status, body = self._request("GET", "/pet/current")
        self.assertEqual(status, 200)
        self.assertIn("pet_id", body)

    def test_pet_activity_unauthenticated_ok(self):
        """GET /pet/activity does not require auth."""
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("GET", "/pet/activity?pet_id=pet_1")
        self.assertEqual(status, 200)

    def test_pet_create_rejected_without_auth(self):
        status, body = self._request("POST", "/pet/create", {"name": "Luna"})
        self.assertEqual(status, 401)

    def test_pet_create_accepted_with_auth(self):
        status, body = self._request(
            "POST", "/pet/create", {"name": "Luna"},
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["identity"]["name"], "Luna")

    def test_pet_add_food_rejected_without_auth(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/add-food", {"pet_id": "pet_1", "amount": 100})
        self.assertEqual(status, 401)

    def test_pet_add_food_accepted_with_auth(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request(
            "POST", "/pet/add-food", {"pet_id": "pet_1", "amount": 100},
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_pet_feed_rejected_without_auth(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=500)
        status, body = self._request("POST", "/pet/feed", {"pet_id": "pet_1", "amount": 100})
        self.assertEqual(status, 401)

    def test_pet_feed_accepted_with_auth(self):
        self.pet_store.create_pet(name="Mochi")
        self.pet_store.add_food("pet_1", amount=500)
        status, body = self._request(
            "POST", "/pet/feed", {"pet_id": "pet_1", "amount": 100},
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_pet_care_rejected_without_auth(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request("POST", "/pet/care", {"pet_id": "pet_1", "action": "pat"})
        self.assertEqual(status, 401)

    def test_pet_care_accepted_with_auth(self):
        self.pet_store.create_pet(name="Mochi")
        status, body = self._request(
            "POST", "/pet/care", {"pet_id": "pet_1", "action": "pat"},
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])


if __name__ == "__main__":
    unittest.main()
