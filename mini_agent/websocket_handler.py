from __future__ import annotations

import base64
import hashlib
import struct
from typing import Optional

WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-5AB97D2E4773"


class WebSocketConnection:
    """Minimal WebSocket connection over a raw socket."""

    def __init__(self, handler):
        self.handler = handler
        self.rfile = handler.rfile
        self.wfile = handler.wfile
        self.closed = False

    @staticmethod
    def accept_upgrade(handler) -> Optional[WebSocketConnection]:
        upgrade = handler.headers.get("Upgrade", "").lower()
        if upgrade != "websocket":
            return None
        key = handler.headers.get("Sec-WebSocket-Key", "")
        if not key:
            return None
        accept = base64.b64encode(
            hashlib.sha1((key + WEBSOCKET_GUID).encode()).digest()
        ).decode()
        handler.send_response(101)
        handler.send_header("Upgrade", "websocket")
        handler.send_header("Connection", "Upgrade")
        handler.send_header("Sec-WebSocket-Accept", accept)
        handler.end_headers()
        return WebSocketConnection(handler)

    def read_frame(self) -> Optional[str]:
        try:
            header = self._read_bytes(2)
            if not header:
                return None
        except (ConnectionResetError, BrokenPipeError, OSError):
            return None

        opcode = header[0] & 0x0F
        masked = bool(header[1] & 0x80)
        length = header[1] & 0x7F

        if length == 126:
            length = struct.unpack("!H", self._read_bytes(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_bytes(8))[0]

        mask_key = self._read_bytes(4) if masked else None
        payload = self._read_bytes(length)

        if masked and mask_key:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

        if opcode == 0x1:  # text
            try:
                return payload.decode("utf-8")
            except UnicodeDecodeError:
                return None
        elif opcode == 0x8:  # close
            self._send_close()
            return None
        elif opcode == 0x9:  # ping
            self._send_pong(payload)
            return self.read_frame()
        elif opcode == 0xA:  # pong
            return self.read_frame()
        return None

    def write_frame(self, text: str) -> None:
        if self.closed:
            return
        payload = text.encode("utf-8")
        header = bytearray()
        header.append(0x81)  # FIN + text opcode

        if len(payload) < 126:
            header.append(len(payload))
        elif len(payload) < 65536:
            header.append(126)
            header.extend(struct.pack("!H", len(payload)))
        else:
            header.append(127)
            header.extend(struct.pack("!Q", len(payload)))

        try:
            self.wfile.write(bytes(header) + payload)
            self.wfile.flush()
        except (ConnectionResetError, BrokenPipeError, OSError):
            self.closed = True

    def close(self) -> None:
        if not self.closed:
            self._send_close()

    def _send_close(self) -> None:
        try:
            self.wfile.write(bytes([0x88, 0x00]))
            self.wfile.flush()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        self.closed = True

    def _send_pong(self, payload: bytes) -> None:
        try:
            header = bytearray([0x8A])
            if len(payload) < 126:
                header.append(len(payload))
            else:
                header.append(126)
                header.extend(struct.pack("!H", len(payload)))
            self.wfile.write(bytes(header) + payload)
            self.wfile.flush()
        except (ConnectionResetError, BrokenPipeError, OSError):
            self.closed = True

    def _read_bytes(self, n: int) -> bytes:
        data = b""
        while len(data) < n:
            chunk = self.rfile.read(n - len(data))
            if not chunk:
                raise ConnectionResetError("connection closed")
            data += chunk
        return data
