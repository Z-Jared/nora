from __future__ import annotations

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

from mini_agent.controller import MiniAgent
from mini_agent.metrics import RequestMetrics
from mini_agent.rate_limit import TokenBucketRateLimiter
from mini_agent.session import SessionStore
from mini_agent.websocket_handler import WebSocketConnection

STREAM_CHUNK_SIZE = 20


class NoraHTTPHandler(BaseHTTPRequestHandler):
    agent: MiniAgent
    session_store: Optional[SessionStore]
    api_token: str
    rate_limiter: TokenBucketRateLimiter
    metrics: RequestMetrics
    cors_origins: str = "*"

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        start = time.monotonic()
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if self.headers.get("Upgrade", "").lower() == "websocket":
            self._handle_websocket()
            return

        if path == "/health":
            self._handle_health()
        elif path == "/tools":
            self._handle_tools()
        elif path == "/session/list":
            self._handle_session_list()
        elif path == "/docs":
            self._handle_docs()
        else:
            self._json_response(404, {"error": "not found"})

        self.metrics.record(path, self._last_status, time.monotonic() - start)

    def do_POST(self):
        start = time.monotonic()
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if not self._check_auth():
            self.metrics.record(path, 401, time.monotonic() - start)
            return

        if not self.rate_limiter.allow():
            self._json_response(429, {"error": "rate limit exceeded"})
            self.metrics.record(path, 429, time.monotonic() - start)
            return

        body = self._read_body()
        if body is None:
            self.metrics.record(path, self._last_status, time.monotonic() - start)
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

        self.metrics.record(path, self._last_status, time.monotonic() - start)

    def _handle_websocket(self) -> None:
        ws = WebSocketConnection.accept_upgrade(self)
        if not ws:
            self._json_response(400, {"error": "WebSocket upgrade failed"})
            return

        # Check auth via query param or first message
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        token_param = qs.get("token", [None])[0]
        if self.api_token and token_param != self.api_token:
            # Will check auth on first message instead
            auth_pending = True
        else:
            auth_pending = False

        try:
            self._ws_message_loop(ws, auth_pending)
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        finally:
            ws.close()

    def _ws_message_loop(self, ws: WebSocketConnection, auth_pending: bool) -> None:
        while not ws.closed:
            message = ws.read_frame()
            if message is None:
                break

            try:
                body = json.loads(message)
            except json.JSONDecodeError:
                ws.write_frame(json.dumps({"error": "invalid JSON"}))
                continue

            # Auth check on first message
            if auth_pending:
                token = body.get("token", "")
                if token != self.api_token:
                    ws.write_frame(json.dumps({"error": "unauthorized"}))
                    break
                auth_pending = False
                ws.write_frame(json.dumps({"type": "auth_ok"}))
                continue

            msg_type = body.get("type", "chat")

            if msg_type == "chat":
                self._ws_handle_chat(ws, body)
            elif msg_type == "ping":
                ws.write_frame(json.dumps({"type": "pong"}))
            elif msg_type == "session_save":
                self._ws_handle_session_save(ws, body)
            elif msg_type == "session_load":
                self._ws_handle_session_load(ws, body)
            else:
                ws.write_frame(json.dumps({"error": f"unknown type: {msg_type}"}))

    def _ws_handle_chat(self, ws: WebSocketConnection, body: dict) -> None:
        message = body.get("message", "").strip()
        if not message:
            ws.write_frame(json.dumps({"error": "message is required"}))
            return

        ws.write_frame(json.dumps({"type": "typing"}))

        try:
            response = self.agent.run(message)
            for i in range(0, len(response), STREAM_CHUNK_SIZE):
                chunk = response[i:i + STREAM_CHUNK_SIZE]
                ws.write_frame(json.dumps({"type": "delta", "content": chunk}))

            report = getattr(self.agent, "last_run_report", None)
            meta: dict[str, Any] = {}
            if report and hasattr(report, "status"):
                meta["status"] = report.status
                meta["tool_calls"] = len(report.tool_calls)
            ws.write_frame(json.dumps({"type": "done", **meta}))
        except Exception as error:
            ws.write_frame(json.dumps({"type": "error", "error": str(error)[:500]}))

    def _ws_handle_session_save(self, ws: WebSocketConnection, body: dict) -> None:
        if not self.session_store:
            ws.write_frame(json.dumps({"error": "session store not configured"}))
            return
        name = body.get("name", "")
        result = self.session_store.save(self.agent.memory, name=name)
        ws.write_frame(json.dumps({"type": "session_saved", "result": result}))

    def _ws_handle_session_load(self, ws: WebSocketConnection, body: dict) -> None:
        if not self.session_store:
            ws.write_frame(json.dumps({"error": "session store not configured"}))
            return
        name = body.get("name", "").strip()
        if not name:
            ws.write_frame(json.dumps({"error": "name is required"}))
            return
        result = self.session_store.load(name, self.agent.memory)
        ws.write_frame(json.dumps({"type": "session_loaded", "result": result}))

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

        self._last_status = 200
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        self._stream_simulated(message)

        self.close_connection = True

    def _stream_simulated(self, message: str) -> None:
        try:
            response = self.agent.run(message)
        except Exception as error:
            event = json.dumps({"type": "error", "error": str(error)[:500]}, ensure_ascii=False)
            self.wfile.write(f"data: {event}\n\n".encode("utf-8"))
            self.wfile.flush()
            return

        for i in range(0, len(response), STREAM_CHUNK_SIZE):
            chunk = response[i:i + STREAM_CHUNK_SIZE]
            event = json.dumps({"type": "delta", "content": chunk}, ensure_ascii=False)
            self.wfile.write(f"data: {event}\n\n".encode("utf-8"))
            self.wfile.flush()

        report = getattr(self.agent, "last_run_report", None)
        meta: dict[str, Any] = {}
        if report and hasattr(report, "status"):
            meta["status"] = report.status
            meta["tool_calls"] = len(report.tool_calls)
        done_event = json.dumps({"type": "done", **meta}, ensure_ascii=False)
        self.wfile.write(f"data: {done_event}\n\n".encode("utf-8"))
        self.wfile.flush()

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

    def _handle_health(self) -> None:
        data = {"status": "ok", "metrics": self.metrics.summary()}
        self._json_response(200, data)

    def _handle_docs(self) -> None:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Nora API", "version": "0.2.0", "description": "Nora local AI assistant HTTP API"},
            "paths": {
                "/health": {"get": {"summary": "Health check with metrics", "responses": {"200": {"description": "OK"}}}},
                "/chat": {"post": {"summary": "Send a message", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}}}}, "responses": {"200": {"description": "Response"}}}},
                "/chat/stream": {"post": {"summary": "SSE streaming chat", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}}}}, "responses": {"200": {"description": "SSE stream"}}}},
                "/tools": {"get": {"summary": "List available tools", "responses": {"200": {"description": "Tool list"}}}},
                "/session/save": {"post": {"summary": "Save current session", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"name": {"type": "string"}}}}}}, "responses": {"200": {"description": "Saved"}}}},
                "/session/load": {"post": {"summary": "Load a session", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}}}, "responses": {"200": {"description": "Loaded"}}}},
                "/session/list": {"get": {"summary": "List saved sessions", "responses": {"200": {"description": "Session list"}}}},
                "/ws": {"get": {"summary": "WebSocket endpoint for bidirectional real-time chat", "description": "Upgrade to WebSocket. Send JSON messages with type=chat, ping, session_save, session_load."}},
                "/docs": {"get": {"summary": "This endpoint", "responses": {"200": {"description": "OpenAPI spec"}}}},
            },
        }
        self._json_response(200, spec)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", self.cors_origins)

    def _json_response(self, status: int, data: dict) -> None:
        self._last_status = status
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
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
    cors_origins: str = "*",
) -> HTTPServer:
    NoraHTTPHandler.agent = agent
    NoraHTTPHandler.session_store = session_store
    NoraHTTPHandler.api_token = api_token
    NoraHTTPHandler.rate_limiter = TokenBucketRateLimiter(rate=rate_limit, burst=rate_burst)
    NoraHTTPHandler.metrics = RequestMetrics()
    NoraHTTPHandler.cors_origins = cors_origins
    return HTTPServer((host, port), NoraHTTPHandler)
