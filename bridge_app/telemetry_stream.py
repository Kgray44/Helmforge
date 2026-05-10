from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping


TELEMETRY_FRAME_SCHEMA_VERSION = "helmforge.telemetry_frame.v1"
TELEMETRY_PAYLOAD_VERSION = "helmforge.bridge_telemetry.v1"
DEFAULT_TELEMETRY_STREAM_HOST = "127.0.0.1"
DEFAULT_TELEMETRY_STREAM_PORT = 8765
DEFAULT_TELEMETRY_STREAM_RATE_HZ = 60.0
WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


@dataclass(frozen=True)
class TelemetryStreamOptions:
    enabled: bool = False
    host: str = DEFAULT_TELEMETRY_STREAM_HOST
    port: int = DEFAULT_TELEMETRY_STREAM_PORT
    rate_hz: float = DEFAULT_TELEMETRY_STREAM_RATE_HZ


@dataclass(frozen=True)
class TelemetryStreamStatus:
    enabled: bool = False
    transport_name: str = "local_websocket"
    host: str = DEFAULT_TELEMETRY_STREAM_HOST
    port: int = DEFAULT_TELEMETRY_STREAM_PORT
    server_started_at: str | None = None
    client_count: int = 0
    frames_sent: int = 0
    send_error_count: int = 0
    last_send_status: str = "disabled"
    last_send_at: str | None = None
    last_error: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "transport_name": self.transport_name,
            "host": self.host,
            "port": self.port,
            "pipe_name": None,
            "server_started_at": self.server_started_at,
            "client_count": self.client_count,
            "frames_sent": self.frames_sent,
            "send_error_count": self.send_error_count,
            "last_send_status": self.last_send_status,
            "last_send_at": self.last_send_at,
            "last_error": self.last_error,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


class TelemetryStreamServer:
    def __init__(self, options: TelemetryStreamOptions | None = None, *, clock=None) -> None:
        self.options = options or TelemetryStreamOptions()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._server_socket: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._clients: list[socket.socket] = []
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._started_at: datetime | None = None
        self._frames_sent = 0
        self._send_error_count = 0
        self._last_send_status = "disabled"
        self._last_send_at: datetime | None = None
        self._last_error = ""
        self._last_publish_monotonic: float | None = None

    def start(self) -> None:
        if not self.options.enabled:
            self._last_send_status = "disabled"
            return
        if self.options.host != "127.0.0.1":
            self._last_send_status = "error"
            self._last_error = "Telemetry stream must bind to 127.0.0.1 in HF-LRDC-3B."
            return
        with self._lock:
            if self._server_socket is not None:
                return
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind((self.options.host, int(self.options.port)))
                server.listen()
                server.settimeout(0.1)
            except OSError as exc:
                self._last_send_status = "error"
                self._last_error = str(exc)
                self._send_error_count += 1
                return
            self._server_socket = server
            bound_host, bound_port = server.getsockname()
            self.options = TelemetryStreamOptions(
                enabled=True,
                host=str(bound_host),
                port=int(bound_port),
                rate_hz=self.options.rate_hz,
            )
            self._started_at = self._aware(self._clock())
            self._last_send_status = "not_sent"
            self._stop_event.clear()
            self._accept_thread = threading.Thread(target=self._accept_loop, name="helmforge-telemetry-stream", daemon=True)
            self._accept_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            server = self._server_socket
            self._server_socket = None
            clients = tuple(self._clients)
            self._clients.clear()
        if server is not None:
            try:
                server.close()
            except OSError:
                pass
        for client in clients:
            _close_socket(client)
        if self._accept_thread is not None and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=0.5)
        self._accept_thread = None
        self._last_send_status = "disabled"

    def publish(self, payload: Mapping[str, object]) -> TelemetryStreamStatus:
        if not self.options.enabled or self._server_socket is None:
            self._last_send_status = "disabled"
            return self.status()
        now_monotonic = time.monotonic()
        min_interval = 1.0 / max(1.0, float(self.options.rate_hz))
        if self._last_publish_monotonic is not None and (now_monotonic - self._last_publish_monotonic) < min_interval:
            self._last_send_status = "rate_limited"
            return self.status()
        with self._lock:
            clients = tuple(self._clients)
        if not clients:
            self._last_send_status = "no_clients"
            return self.status()

        sent_at = self._aware(self._clock())
        sequence = self._frames_sent + 1
        bridge_timing = payload.get("bridge_timing") if isinstance(payload, Mapping) else {}
        bridge_pid = _safe_int((bridge_timing or {}).get("bridge_pid") if isinstance(bridge_timing, Mapping) else None, os.getpid())
        bridge_started_at = _safe_datetime(
            (bridge_timing or {}).get("bridge_started_at") if isinstance(bridge_timing, Mapping) else None,
            sent_at,
        )
        frame = build_telemetry_stream_frame(
            payload,
            sequence=sequence,
            server_started_at=self._started_at or sent_at,
            sent_at=sent_at,
            transport_name="local_websocket",
            bridge_pid=bridge_pid,
            bridge_started_at=bridge_started_at,
        )
        data = _encode_ws_text(json.dumps(frame, sort_keys=True))

        sent_any = False
        dead: list[socket.socket] = []
        for client in clients:
            try:
                client.settimeout(0.01)
                client.sendall(data)
                sent_any = True
            except OSError as exc:
                dead.append(client)
                self._send_error_count += 1
                self._last_error = str(exc)
        if dead:
            with self._lock:
                self._clients = [client for client in self._clients if client not in dead]
            for client in dead:
                _close_socket(client)
        if sent_any:
            self._frames_sent += 1
            self._last_publish_monotonic = now_monotonic
            self._last_send_at = sent_at
            self._last_send_status = "ok"
        else:
            self._last_send_status = "send_failed"
        return self.status()

    def status(self) -> TelemetryStreamStatus:
        with self._lock:
            client_count = len(self._clients)
        errors = (self._last_error,) if self._last_error and self._last_send_status == "error" else ()
        return TelemetryStreamStatus(
            enabled=bool(self.options.enabled and self._server_socket is not None),
            host=self.options.host,
            port=int(self.options.port),
            server_started_at=self._started_at.isoformat() if self._started_at else None,
            client_count=client_count,
            frames_sent=self._frames_sent,
            send_error_count=self._send_error_count,
            last_send_status=self._last_send_status,
            last_send_at=self._last_send_at.isoformat() if self._last_send_at else None,
            last_error=self._last_error,
            errors=errors,
        )

    def _accept_loop(self) -> None:
        while not self._stop_event.is_set():
            server = self._server_socket
            if server is None:
                return
            try:
                client, _addr = server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                client.settimeout(0.5)
                _server_handshake(client)
                client.settimeout(0.01)
            except OSError as exc:
                self._send_error_count += 1
                self._last_error = str(exc)
                _close_socket(client)
                continue
            with self._lock:
                self._clients.append(client)

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def build_telemetry_stream_frame(
    payload: Mapping[str, object],
    *,
    sequence: int,
    server_started_at: datetime,
    sent_at: datetime,
    transport_name: str,
    bridge_pid: int,
    bridge_started_at: datetime,
    heartbeat: bool = False,
) -> dict[str, object]:
    generated_at = payload.get("generated_at") or payload.get("timestamp") or sent_at.isoformat()
    return {
        "schema_version": TELEMETRY_FRAME_SCHEMA_VERSION,
        "payload_version": TELEMETRY_PAYLOAD_VERSION,
        "transport": {
            "transport_name": transport_name,
            "connection_id": "",
            "server_started_at": _iso(server_started_at),
            "sequence": int(sequence),
            "generated_at": str(generated_at),
            "sent_at": _iso(sent_at),
            "heartbeat": bool(heartbeat),
        },
        "bridge": {
            "bridge_pid": int(bridge_pid),
            "bridge_started_at": _iso(bridge_started_at),
            "lifecycle_state": str(payload.get("lifecycle_state") or "unavailable"),
            "runtime_truth": str(payload.get("runtime_truth") or "unavailable"),
        },
        "payload": dict(payload),
        "warnings": list(payload.get("warnings", ()) or ()),
        "errors": list(payload.get("errors", ()) or ()),
    }


def _server_handshake(client: socket.socket) -> None:
    request = b""
    while b"\r\n\r\n" not in request and len(request) < 8192:
        chunk = client.recv(1024)
        if not chunk:
            raise OSError("WebSocket handshake closed before headers.")
        request += chunk
    headers = request.decode("utf-8", errors="ignore").split("\r\n")
    key = ""
    for line in headers:
        if line.lower().startswith("sec-websocket-key:"):
            key = line.split(":", 1)[1].strip()
            break
    if not key:
        raise OSError("WebSocket handshake missing Sec-WebSocket-Key.")
    accept = base64.b64encode(hashlib.sha1((key + WEBSOCKET_GUID).encode("ascii")).digest()).decode("ascii")
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
        "\r\n"
    )
    client.sendall(response.encode("ascii"))


def _encode_ws_text(text: str) -> bytes:
    payload = text.encode("utf-8")
    length = len(payload)
    if length < 126:
        header = bytes((0x81, length))
    elif length <= 0xFFFF:
        header = bytes((0x81, 126)) + length.to_bytes(2, "big")
    else:
        header = bytes((0x81, 127)) + length.to_bytes(8, "big")
    return header + payload


def _close_socket(sock: socket.socket) -> None:
    try:
        sock.close()
    except OSError:
        pass


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _safe_int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _safe_datetime(value: object, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        return TelemetryStreamServer._aware(value)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value)
            return TelemetryStreamServer._aware(parsed)
        except ValueError:
            return fallback
    return fallback
