from __future__ import annotations

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

from mini_agent.controller import MiniAgent
from mini_agent.rate_limit import TokenBucketRateLimiter
from mini_agent.session import SessionStore

STREAM_CHUNK_SIZE = 20


class NoraHTTPHandler(BaseHTTPRequestHandler):
    agent: MiniAgent
    session_store: Optional[SessionStore]
    api_token: str
    rate_limiter: TokenBucketRateLimiter

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/health":
            self._json_response(200, {"status": "ok"})
        elif path == "/tools":
            self._handle_tools()
        elif path == "/session/list":
            self._handle_session_list()
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if not self._check_auth():
            return

        if not self.rate_limiter.allow():
            self._json_response(429, {"error": "rate limit exceeded"})
            return

        body = self._read_body()
        if body is None:
            return

        if path == "/chat":
            self._handle_chat(body)
        elif path == "/chat/stream":
            self._handle_chat_stream(body)
        elif path == "/session/save":
            self._handle_session_save(body)
        elif path == "/session/load":
            self._handle_session_load(body)
        else:
            self._json_response(404, {"error": "not found"})

    def _handle_chat(self, body: dict) -> None:
        message = body.get("message", "").strip()
        if not message:
            self._json_response(400, {"error": "message is required"})
            return

        try:
            response = self.agent.run(message)
            report = getattr(self.agent, "last_run_report", None)
            result: dict[str, Any] = {"response": response}
            if report and hasattr(report, "status"):
                result["status"] = report.status
                result["tool_calls"] = len(report.tool_calls)
            self._json_response(200, result)
        except Exception as error:
            self._json_response(500, {"error": str(error)[:500]})

    def _handle_chat_stream(self, body: dict) -> None:
        message = body.get("message", "").strip()
        if not message:
            self._json_response(400, {"error": "message is required"})
            return

        try:
            response = self.agent.run(message)
        except Exception as error:
            self._json_response(500, {"error": str(error)[:500]})
            return

        report = getattr(self.agent, "last_run_report", None)
        meta: dict[str, Any] = {}
        if report and hasattr(report, "status"):
            meta["status"] = report.status
            meta["tool_calls"] = len(report.tool_calls)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        for i in range(0, len(response), STREAM_CHUNK_SIZE):
            chunk = response[i:i + STREAM_CHUNK_SIZE]
            event = json.dumps({"type": "delta", "content": chunk}, ensure_ascii=False)
            self.wfile.write(f"data: {event}\n\n".encode("utf-8"))
            self.wfile.flush()

        done_event = json.dumps({"type": "done", **meta}, ensure_ascii=False)
        self.wfile.write(f"data: {done_event}\n\n".encode("utf-8"))
        self.wfile.flush()
        self.close_connection = True

    def _handle_tools(self) -> None:
        if not self._check_auth():
            return
        try:
            tools = self.agent.tools.to_openai_tools()
            names = [
                tool.get("function", {}).get("name", "")
                for tool in tools
            ]
            self._json_response(200, {"tools": sorted(names)})
        except Exception as error:
            self._json_response(500, {"error": str(error)[:500]})

    def _handle_session_list(self) -> None:
        if not self._check_auth():
            return
        if not self.session_store:
            self._json_response(200, {"sessions": []})
            return
        result = self.session_store.list_sessions()
        self._json_response(200, {"sessions": result})

    def _handle_session_save(self, body: dict) -> None:
        if not self.session_store:
            self._json_response(400, {"error": "session store not configured"})
            return
        name = body.get("name", "")
        result = self.session_store.save(self.agent.memory, name=name)
        self._json_response(200, {"result": result})

    def _handle_session_load(self, body: dict) -> None:
        if not self.session_store:
            self._json_response(400, {"error": "session store not configured"})
            return
        name = body.get("name", "").strip()
        if not name:
            self._json_response(400, {"error": "name is required"})
            return
        result = self.session_store.load(name, self.agent.memory)
        self._json_response(200, {"result": result})

    def _check_auth(self) -> bool:
        if not self.api_token:
            return True
        auth_header = self.headers.get("Authorization", "")
        if auth_header == f"Bearer {self.api_token}":
            return True
        self._json_response(401, {"error": "unauthorized"})
        return False

    def _read_body(self) -> Optional[dict]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        if content_length > 1024 * 1024:
            self._json_response(413, {"error": "request body too large"})
            return None
        try:
            raw = self.rfile.read(content_length)
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            self._json_response(400, {"error": f"invalid JSON: {error}"})
            return None

    def _json_response(self, status: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def create_server(
    agent: MiniAgent,
    host: str = "127.0.0.1",
    port: int = 8080,
    session_store: Optional[SessionStore] = None,
    api_token: str = "",
    rate_limit: float = 10.0,
    rate_burst: int = 20,
) -> HTTPServer:
    NoraHTTPHandler.agent = agent
    NoraHTTPHandler.session_store = session_store
    NoraHTTPHandler.api_token = api_token
    NoraHTTPHandler.rate_limiter = TokenBucketRateLimiter(rate=rate_limit, burst=rate_burst)
    return HTTPServer((host, port), NoraHTTPHandler)
