import base64
import json
import socket
import struct
import tempfile
import threading
import time
import unittest
from pathlib import Path

from mini_agent.controller import MiniAgent
from mini_agent.http_server import create_server
from mini_agent.tools import build_default_registry
from mini_agent.websocket_handler import WebSocketConnection


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _ws_handshake(port, path="/ws", token=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", port))
    key = base64.b64encode(b"test_key_1234567").decode()
    url_path = path
    if token:
        url_path += f"?token={token}"
    request = (
        f"GET {url_path} HTTP/1.1\r\n"
        f"Host: 127.0.0.1:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n"
        f"\r\n"
    )
    sock.sendall(request.encode())
    response = b""
    while b"\r\n\r\n" not in response:
        response += sock.recv(4096)
    return sock, response


def _ws_send(sock, text):
    payload = text.encode("utf-8")
    header = bytearray()
    header.append(0x81)  # FIN + text
    mask_key = b"\x01\x02\x03\x04"
    header.append(0x80 | len(payload))  # masked
    header.extend(mask_key)
    masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    sock.sendall(bytes(header) + masked)


def _ws_recv(sock, timeout=5.0):
    sock.settimeout(timeout)
    try:
        header = sock.recv(2)
        if not header:
            return None
        opcode = header[0] & 0x0F
        length = header[1] & 0x7F
        if length == 126:
            length = struct.unpack("!H", sock.recv(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", sock.recv(8))[0]
        payload = b""
        while len(payload) < length:
            chunk = sock.recv(length - len(payload))
            if not chunk:
                return None
            payload += chunk
        if opcode == 0x1:
            return payload.decode("utf-8")
        elif opcode == 0x8:
            return None
        return None
    except socket.timeout:
        return None


class WebSocketHandshakeTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        self.agent = MiniAgent(build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"))
        self.server = create_server(self.agent, host="127.0.0.1", port=self.port)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def test_handshake_succeeds(self):
        sock, response = _ws_handshake(self.port)
        try:
            self.assertIn(b"101", response)
            self.assertIn(b"upgrade: websocket", response.lower())
            self.assertIn(b"sec-websocket-accept", response.lower())
        finally:
            sock.close()

    def test_chat_roundtrip(self):
        sock, _ = _ws_handshake(self.port)
        try:
            _ws_send(sock, json.dumps({"type": "chat", "message": "hello"}))
            messages = []
            for _ in range(10):
                msg = _ws_recv(sock, timeout=3.0)
                if msg is None:
                    break
                messages.append(json.loads(msg))
            types = [m.get("type") for m in messages]
            self.assertIn("typing", types)
            self.assertIn("done", types)
        finally:
            sock.close()

    def test_chat_emits_tool_events(self):
        sock, _ = _ws_handshake(self.port)
        try:
            _ws_send(sock, json.dumps({"type": "chat", "message": "计算 2 + 3"}))
            messages = []
            for _ in range(20):
                msg = _ws_recv(sock, timeout=3.0)
                if msg is None:
                    break
                messages.append(json.loads(msg))
            types = [m.get("type") for m in messages]
            self.assertIn("typing", types)
            self.assertIn("tool_call_start", types)
            self.assertIn("tool_call_result", types)
            self.assertIn("delta", types)
            self.assertIn("done", types)

            tool_start = next(m for m in messages if m.get("type") == "tool_call_start")
            self.assertEqual(tool_start["name"], "calculate")
            tool_result = next(m for m in messages if m.get("type") == "tool_call_result")
            self.assertEqual(tool_result["name"], "calculate")
            self.assertEqual(tool_result["status"], "ok")
        finally:
            sock.close()

    def test_ping_pong(self):
        sock, _ = _ws_handshake(self.port)
        try:
            _ws_send(sock, json.dumps({"type": "ping"}))
            msg = _ws_recv(sock, timeout=3.0)
            self.assertIsNotNone(msg)
            data = json.loads(msg)
            self.assertEqual(data.get("type"), "pong")
        finally:
            sock.close()

    def test_invalid_json(self):
        sock, _ = _ws_handshake(self.port)
        try:
            _ws_send(sock, "not json{{{")
            msg = _ws_recv(sock, timeout=3.0)
            self.assertIsNotNone(msg)
            data = json.loads(msg)
            self.assertIn("error", data)
        finally:
            sock.close()

    def test_unknown_type(self):
        sock, _ = _ws_handshake(self.port)
        try:
            _ws_send(sock, json.dumps({"type": "unknown_type"}))
            msg = _ws_recv(sock, timeout=3.0)
            self.assertIsNotNone(msg)
            data = json.loads(msg)
            self.assertIn("error", data)
        finally:
            sock.close()

    def test_close_frame(self):
        sock, _ = _ws_handshake(self.port)
        try:
            sock.sendall(bytes([0x88, 0x80, 0x01, 0x02, 0x03, 0x04]))
            time.sleep(0.2)
        finally:
            sock.close()


class WebSocketAuthTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        self.agent = MiniAgent(build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"))
        self.server = create_server(self.agent, host="127.0.0.1", port=self.port, api_token="secret")
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def test_auth_via_query_param(self):
        sock, response = _ws_handshake(self.port, token="secret")
        try:
            self.assertIn(b"101", response)
            _ws_send(sock, json.dumps({"type": "ping"}))
            msg = _ws_recv(sock, timeout=3.0)
            self.assertIsNotNone(msg)
            data = json.loads(msg)
            self.assertEqual(data["type"], "pong")
        finally:
            sock.close()

    def test_auth_via_first_message(self):
        sock, _ = _ws_handshake(self.port)
        try:
            _ws_send(sock, json.dumps({"type": "chat", "token": "secret", "message": "hi"}))
            msg = _ws_recv(sock, timeout=3.0)
            self.assertIsNotNone(msg)
            data = json.loads(msg)
            # Should get auth_ok or at least not unauthorized
            self.assertNotEqual(data.get("error"), "unauthorized")
        finally:
            sock.close()

    def test_unauth_rejected(self):
        sock, _ = _ws_handshake(self.port)
        try:
            _ws_send(sock, json.dumps({"type": "chat", "message": "hi"}))
            msg = _ws_recv(sock, timeout=3.0)
            self.assertIsNotNone(msg)
            data = json.loads(msg)
            self.assertEqual(data.get("error"), "unauthorized")
        finally:
            sock.close()


class WebSocketSessionTests(unittest.TestCase):
    def setUp(self):
        self.port = _find_free_port()
        self.tmpdir = tempfile.mkdtemp()
        self.agent = MiniAgent(build_default_registry(notes_path=Path(self.tmpdir) / "notes.txt"))
        from mini_agent.session import SessionStore
        self.session_store = SessionStore(directory=Path(self.tmpdir) / "sessions")
        self.server = create_server(self.agent, host="127.0.0.1", port=self.port, session_store=self.session_store)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def test_session_save_no_store_msg(self):
        """With session store configured, save should work."""
        sock, _ = _ws_handshake(self.port)
        try:
            _ws_send(sock, json.dumps({"type": "session_save", "name": "test_ws"}))
            msg = _ws_recv(sock, timeout=3.0)
            self.assertIsNotNone(msg)
            data = json.loads(msg)
            # Either session_saved or error about empty memory
            self.assertIn(data.get("type"), ["session_saved", "error"])
        finally:
            sock.close()


class WebSocketHandlerUnitTests(unittest.TestCase):
    def test_accept_upgrade_rejects_non_websocket(self):
        class FakeHandler:
            headers = {"Upgrade": "h2c"}
        result = WebSocketConnection.accept_upgrade(FakeHandler)
        self.assertIsNone(result)

    def test_accept_upgrade_rejects_missing_key(self):
        class FakeHandler:
            headers = {"Upgrade": "websocket"}
        result = WebSocketConnection.accept_upgrade(FakeHandler)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
