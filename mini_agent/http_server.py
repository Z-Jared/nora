from __future__ import annotations

import json
import mimetypes
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

from mini_agent.controller import MiniAgent
from mini_agent.memory import LongTermMemory
from mini_agent.metrics import RequestMetrics
from mini_agent.rate_limit import TokenBucketRateLimiter
from mini_agent.session import SessionStore
from mini_agent.task_runner import TaskManager
from mini_agent.websocket_handler import WebSocketConnection

class NoraHTTPHandler(BaseHTTPRequestHandler):
    agent: MiniAgent
    session_store: Optional[SessionStore]
    task_manager: Optional[TaskManager]
    long_term_memory: Optional[LongTermMemory]
    api_token: str
    rate_limiter: TokenBucketRateLimiter
    metrics: RequestMetrics
    cors_origins: str = "*"
    static_dir: Optional[Path] = None

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

        if path in ("", "/") and self.static_dir:
            self._serve_file(self.static_dir / "index.html")
            self.metrics.record(path, self._last_status, time.monotonic() - start)
            return
        if path.startswith("/static/") and self.static_dir:
            rel = path[len("/static/"):]
            self._serve_file(self.static_dir / rel)
            self.metrics.record(path, self._last_status, time.monotonic() - start)
            return

        if path == "/health":
            self._handle_health()
        elif path == "/tools":
            self._handle_tools()
        elif path == "/task":
            self._handle_task_get()
        elif path == "/memory/list":
            self._handle_memory_list(parsed)
        elif path == "/memory/search":
            self._handle_memory_search(parsed)
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
        elif path == "/chat/clear":
            self._handle_chat_clear()
        elif path == "/task/start":
            self._handle_task_start(body)
        elif path == "/task/update":
            self._handle_task_update(body)
        elif path == "/task/finish":
            self._handle_task_finish(body)
        elif path == "/task/next":
            self._handle_task_next()
        elif path == "/memory/save":
            self._handle_memory_save(body)
        elif path == "/memory/delete":
            self._handle_memory_delete(body)
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
            elif msg_type == "chat_clear":
                self.agent.memory.clear()
                ws.write_frame(json.dumps({"type": "cleared", "result": "cleared"}))
            else:
                ws.write_frame(json.dumps({"error": f"unknown type: {msg_type}"}))

    def _ws_handle_chat(self, ws: WebSocketConnection, body: dict) -> None:
        message = body.get("message", "").strip()
        if not message:
            ws.write_frame(json.dumps({"error": "message is required"}))
            return

        try:
            for event in self.agent.run_events(message):
                ws.write_frame(json.dumps(event))
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

        for event in self.agent.run_events(message):
            payload = json.dumps(event, ensure_ascii=False)
            self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
            self.wfile.flush()

        self.close_connection = True

    def _handle_chat_clear(self) -> None:
        self.agent.memory.clear()
        self._json_response(200, {"result": "cleared"})

    def _handle_task_get(self) -> None:
        if not self._check_auth():
            return
        if not self.task_manager:
            self._json_response(500, {"error": "task manager not configured"})
            return
        task = self.task_manager.get_current_task()
        if not task or task.get("status") == "finished":
            self._json_response(200, {"task": None})
            return
        self._json_response(200, {"task": task})

    def _handle_task_start(self, body: dict) -> None:
        if not self.task_manager:
            self._json_response(500, {"error": "task manager not configured"})
            return
        goal = body.get("goal", "").strip()
        steps = body.get("steps", "")
        if isinstance(steps, list):
            steps = "\n".join(str(s) for s in steps)
        if not goal:
            self._json_response(400, {"error": "goal is required"})
            return
        if not steps.strip():
            self._json_response(400, {"error": "steps is required"})
            return
        result = self.task_manager.start(goal, steps)
        task = self.task_manager.get_current_task()
        self._json_response(200, {"result": result, "task": task})

    def _handle_task_update(self, body: dict) -> None:
        if not self.task_manager:
            self._json_response(500, {"error": "task manager not configured"})
            return
        step_id = body.get("step_id")
        status = body.get("status", "").strip()
        if step_id is None or not status:
            self._json_response(400, {"error": "step_id and status are required"})
            return
        try:
            step_id = int(step_id)
        except (ValueError, TypeError):
            self._json_response(400, {"error": "step_id must be an integer"})
            return
        note = body.get("note", "")
        summary = body.get("summary", "")
        result = self.task_manager.update_step(step_id, status, note=note, summary=summary)
        task = self.task_manager.get_current_task()
        self._json_response(200, {"result": result, "task": task})

    def _handle_task_finish(self, body: dict) -> None:
        if not self.task_manager:
            self._json_response(500, {"error": "task manager not configured"})
            return
        summary = body.get("summary", "").strip()
        if not summary:
            self._json_response(400, {"error": "summary is required"})
            return
        result = self.task_manager.finish(summary)
        self._json_response(200, {"result": result, "task": None})

    def _handle_task_next(self) -> None:
        if not self.task_manager:
            self._json_response(500, {"error": "task manager not configured"})
            return
        result = self.task_manager.run_once()
        task = self.task_manager.get_current_task()
        self._json_response(200, {"result": result, "task": task})

    def _handle_memory_list(self, parsed) -> None:
        if not self._check_auth():
            return
        if not self.long_term_memory:
            self._json_response(500, {"error": "memory not configured"})
            return
        qs = parse_qs(parsed.query)
        max_results = 20
        if "max" in qs:
            try:
                max_results = int(qs["max"][0])
            except (ValueError, IndexError):
                pass
        records = self.long_term_memory.list_records(max_results=max_results)
        self._json_response(200, {"memories": records})

    def _handle_memory_search(self, parsed) -> None:
        if not self._check_auth():
            return
        if not self.long_term_memory:
            self._json_response(500, {"error": "memory not configured"})
            return
        qs = parse_qs(parsed.query)
        query = qs.get("q", [""])[0].strip()
        if not query:
            self._json_response(400, {"error": "q parameter is required"})
            return
        max_results = 5
        if "max" in qs:
            try:
                max_results = int(qs["max"][0])
            except (ValueError, IndexError):
                pass
        records = self.long_term_memory.search_records(query, max_results=max_results)
        self._json_response(200, {"memories": records})

    def _handle_memory_save(self, body: dict) -> None:
        if not self.long_term_memory:
            self._json_response(500, {"error": "memory not configured"})
            return
        text = body.get("text", "").strip()
        if not text:
            self._json_response(400, {"error": "text is required"})
            return
        tags = body.get("tags", "")
        result = self.long_term_memory.save(text, tags=tags)
        if "拒绝" in result:
            self._json_response(400, {"error": result})
            return
        records = self.long_term_memory.list_records(max_results=1)
        self._json_response(200, {"result": result, "memory": records[0] if records else None})

    def _handle_memory_delete(self, body: dict) -> None:
        if not self.long_term_memory:
            self._json_response(500, {"error": "memory not configured"})
            return
        memory_id = body.get("memory_id", "").strip()
        if not memory_id:
            self._json_response(400, {"error": "memory_id is required"})
            return
        result = self.long_term_memory.delete(memory_id)
        if "没有找到" in result:
            self._json_response(404, {"error": result})
            return
        self._json_response(200, {"result": result})

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
        self._json_response(200, {"result": result, "messages": self.agent.memory.messages()})

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
                "/chat/clear": {"post": {"summary": "Clear current conversation memory", "description": "Clears all messages in the current conversation memory. Requires the same Authorization: Bearer <token> header as other POST endpoints when NORA_API_TOKEN is set.", "responses": {"200": {"description": "Cleared"}}}},
                "/tools": {"get": {"summary": "List available tools", "responses": {"200": {"description": "Tool list"}}}},
                "/session/save": {"post": {"summary": "Save current session", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"name": {"type": "string"}}}}}}, "responses": {"200": {"description": "Saved"}}}},
                "/session/load": {"post": {"summary": "Load a session", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}}}, "responses": {"200": {"description": "Loaded"}}}},
                "/session/list": {"get": {"summary": "List saved sessions", "responses": {"200": {"description": "Session list"}}}},
                "/task": {"get": {"summary": "Get current task", "responses": {"200": {"description": "Current task or null"}}}},
                "/task/start": {"post": {"summary": "Create a new task", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"goal": {"type": "string"}, "steps": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]}}, "required": ["goal", "steps"]}}}}, "responses": {"200": {"description": "Created"}}}},
                "/task/update": {"post": {"summary": "Update a task step", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"step_id": {"type": "integer"}, "status": {"type": "string"}, "note": {"type": "string"}, "summary": {"type": "string"}}, "required": ["step_id", "status"]}}}}, "responses": {"200": {"description": "Updated"}}}},
                "/task/finish": {"post": {"summary": "Finish current task", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}}}}, "responses": {"200": {"description": "Finished"}}}},
                "/task/next": {"post": {"summary": "Advance to next step", "responses": {"200": {"description": "Next step"}}}},
                "/memory/list": {"get": {"summary": "List long-term memories", "responses": {"200": {"description": "Memory list"}}}},
                "/memory/search": {"get": {"summary": "Search long-term memories", "responses": {"200": {"description": "Search results"}}}},
                "/memory/save": {"post": {"summary": "Save a long-term memory", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"text": {"type": "string"}, "tags": {"type": "string"}}, "required": ["text"]}}}}, "responses": {"200": {"description": "Saved"}}}},
                "/memory/delete": {"post": {"summary": "Delete a long-term memory", "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"memory_id": {"type": "string"}}, "required": ["memory_id"]}}}}, "responses": {"200": {"description": "Deleted"}}}},
                "/ws": {"get": {"summary": "WebSocket endpoint for bidirectional real-time chat", "description": "Upgrade to WebSocket. Send JSON messages with type=chat, ping, session_save, session_load."}},
                "/docs": {"get": {"summary": "This endpoint", "responses": {"200": {"description": "OpenAPI spec"}}}},
            },
        }
        self._json_response(200, spec)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", self.cors_origins)

    def _serve_file(self, file_path: Path) -> None:
        static_root = self.static_dir.resolve()
        target = file_path.resolve()
        if not (target == static_root or str(target).startswith(str(static_root) + "/")):
            self._json_response(404, {"error": "not found"})
            return
        if not target.is_file():
            self._json_response(404, {"error": "not found"})
            return
        content_type, _ = mimetypes.guess_type(str(target))
        data = target.read_bytes()
        self._last_status = 200
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(data)

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
    task_manager: Optional[TaskManager] = None,
    long_term_memory: Optional[LongTermMemory] = None,
    api_token: str = "",
    rate_limit: float = 10.0,
    rate_burst: int = 20,
    cors_origins: str = "*",
    static_dir: Optional[Path] = None,
) -> HTTPServer:
    NoraHTTPHandler.agent = agent
    NoraHTTPHandler.session_store = session_store
    NoraHTTPHandler.task_manager = task_manager
    NoraHTTPHandler.long_term_memory = long_term_memory
    NoraHTTPHandler.api_token = api_token
    NoraHTTPHandler.rate_limiter = TokenBucketRateLimiter(rate=rate_limit, burst=rate_burst)
    NoraHTTPHandler.metrics = RequestMetrics()
    NoraHTTPHandler.cors_origins = cors_origins
    NoraHTTPHandler.static_dir = static_dir
    return HTTPServer((host, port), NoraHTTPHandler)
