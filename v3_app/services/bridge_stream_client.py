from __future__ import annotations

import base64
import json
import os
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from bridge_app.telemetry_stream import (
    DEFAULT_TELEMETRY_STREAM_HOST,
    DEFAULT_TELEMETRY_STREAM_PORT,
    TELEMETRY_FRAME_SCHEMA_VERSION,
)
from v3_app.services.bridge_client import (
    BridgeTelemetryReadResult,
    BridgeTelemetryStatus,
    parse_bridge_telemetry_payload,
)


@dataclass(frozen=True)
class BridgeTelemetryStreamReadResult:
    status: str
    source_label: str
    message: str = ""
    telemetry: object | None = None
    frame: Mapping[str, object] | None = None
    age_seconds: float | None = None
    last_read_at: datetime | None = None
    stream_sequence: int | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def connected(
        cls,
        *,
        telemetry: object,
        frame: Mapping[str, object],
        read_at: datetime,
        age_seconds: float,
        stream_sequence: int | None,
    ) -> "BridgeTelemetryStreamReadResult":
        return cls(
            status="connected",
            source_label="Bridge Stream",
            message="Bridge telemetry stream connected.",
            telemetry=telemetry,
            frame=frame,
            age_seconds=age_seconds,
            last_read_at=read_at,
            stream_sequence=stream_sequence,
        )


@dataclass(frozen=True)
class SelectedTelemetrySource:
    source_label: str
    telemetry: object | None
    status: str
    reason: str = ""
    stream_result: BridgeTelemetryStreamReadResult | None = None
    json_result: BridgeTelemetryReadResult | None = None


class BridgeTelemetryStreamClient:
    def __init__(
        self,
        *,
        host: str = DEFAULT_TELEMETRY_STREAM_HOST,
        port: int = DEFAULT_TELEMETRY_STREAM_PORT,
        stale_after_seconds: float = 5.0,
        connect_timeout_seconds: float = 0.05,
        read_timeout_seconds: float = 0.05,
        clock=None,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.stale_after_seconds = max(0.1, float(stale_after_seconds))
        self.connect_timeout_seconds = max(0.001, float(connect_timeout_seconds))
        self.read_timeout_seconds = max(0.001, float(read_timeout_seconds))
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._socket: socket.socket | None = None
        self._latest: BridgeTelemetryStreamReadResult | None = None
        self._last_error = ""

    def close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
        self._socket = None

    def read_latest(self) -> BridgeTelemetryStreamReadResult:
        read_at = _aware(self._clock())
        if self._socket is None:
            try:
                self._connect()
            except OSError as exc:
                self._last_error = str(exc)
                return BridgeTelemetryStreamReadResult(
                    status="reconnecting",
                    source_label="Bridge Stream Reconnecting",
                    message=f"Bridge telemetry stream unavailable: {exc}",
                    last_read_at=read_at,
                    errors=(str(exc),),
                )

        try:
            text = _read_ws_text(self._socket, timeout=self.read_timeout_seconds)
        except TimeoutError:
            if self._latest is not None and self._latest.telemetry is not None:
                age = _result_age_seconds(self._latest, read_at)
                if age is not None and age > self.stale_after_seconds:
                    return BridgeTelemetryStreamReadResult(
                        status="stale",
                        source_label="Bridge Stream Stale",
                        message="Bridge telemetry stream frame is stale.",
                        telemetry=self._latest.telemetry,
                        frame=self._latest.frame,
                        age_seconds=age,
                        last_read_at=read_at,
                        stream_sequence=self._latest.stream_sequence,
                        warnings=("Bridge telemetry stream is stale.",),
                    )
                return self._latest
            return BridgeTelemetryStreamReadResult(
                status="connected",
                source_label="Bridge Stream",
                message="Bridge telemetry stream connected; awaiting first frame.",
                last_read_at=read_at,
            )
        except OSError as exc:
            self.close()
            self._last_error = str(exc)
            return BridgeTelemetryStreamReadResult(
                status="reconnecting",
                source_label="Bridge Stream Reconnecting",
                message=f"Bridge telemetry stream disconnected: {exc}",
                last_read_at=read_at,
                errors=(str(exc),),
            )

        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            return BridgeTelemetryStreamReadResult(
                status="invalid",
                source_label="Bridge Stream Invalid",
                message=f"Invalid Bridge telemetry stream JSON: {exc}",
                last_read_at=read_at,
                errors=(str(exc),),
            )
        result = parse_telemetry_stream_frame(raw, now=read_at, stale_after_seconds=self.stale_after_seconds)
        self._latest = result if result.telemetry is not None else self._latest
        return result

    def _connect(self) -> None:
        if self.host != "127.0.0.1":
            raise OSError("Bridge telemetry stream client only connects to 127.0.0.1 in HF-LRDC-3B.")
        sock = socket.create_connection((self.host, self.port), timeout=self.connect_timeout_seconds)
        sock.settimeout(self.connect_timeout_seconds)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET /helmforge/telemetry HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response and len(response) < 8192:
            chunk = sock.recv(1024)
            if not chunk:
                raise OSError("WebSocket handshake closed.")
            response += chunk
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise OSError("WebSocket handshake failed.")
        sock.settimeout(self.read_timeout_seconds)
        self._socket = sock


def parse_telemetry_stream_frame(
    frame: Mapping[str, object],
    *,
    now: datetime | None = None,
    stale_after_seconds: float = 5.0,
) -> BridgeTelemetryStreamReadResult:
    read_at = _aware(now or datetime.now(timezone.utc))
    errors: list[str] = []
    if frame.get("schema_version") != TELEMETRY_FRAME_SCHEMA_VERSION:
        errors.append("unsupported telemetry stream schema_version")
    payload = frame.get("payload")
    if not isinstance(payload, Mapping):
        errors.append("telemetry stream payload must be an object")
    transport = frame.get("transport")
    if not isinstance(transport, Mapping):
        errors.append("telemetry stream transport must be an object")
        transport = {}
    sequence = _optional_int(transport.get("sequence"))
    sent_at = _parse_datetime(transport.get("sent_at"))
    timestamp = _parse_datetime(payload.get("timestamp")) if isinstance(payload, Mapping) else None
    age_anchor = sent_at or timestamp or read_at
    age_seconds = max(0.0, (read_at - age_anchor).total_seconds())

    if errors:
        return BridgeTelemetryStreamReadResult(
            status="invalid",
            source_label="Bridge Stream Invalid",
            message="Bridge telemetry stream frame is invalid.",
            frame=frame,
            age_seconds=age_seconds,
            last_read_at=read_at,
            stream_sequence=sequence,
            errors=tuple(errors),
        )

    try:
        telemetry = parse_bridge_telemetry_payload(Path("<bridge-stream>"), payload)
    except (TypeError, ValueError) as exc:
        return BridgeTelemetryStreamReadResult(
            status="invalid",
            source_label="Bridge Stream Invalid",
            message=f"Bridge telemetry stream payload is invalid: {exc}",
            frame=frame,
            age_seconds=age_seconds,
            last_read_at=read_at,
            stream_sequence=sequence,
            errors=(str(exc),),
        )
    if age_seconds > stale_after_seconds:
        return BridgeTelemetryStreamReadResult(
            status="stale",
            source_label="Bridge Stream Stale",
            message="Bridge telemetry stream frame is stale.",
            telemetry=telemetry,
            frame=frame,
            age_seconds=age_seconds,
            last_read_at=read_at,
            stream_sequence=sequence,
            warnings=("Bridge telemetry stream is stale; fallback should be used.",),
        )
    return BridgeTelemetryStreamReadResult.connected(
        telemetry=telemetry,
        frame=frame,
        read_at=read_at,
        age_seconds=age_seconds,
        stream_sequence=sequence,
    )


def choose_bridge_telemetry_source(
    stream_result: BridgeTelemetryStreamReadResult | None,
    json_result: BridgeTelemetryReadResult,
) -> SelectedTelemetrySource:
    if stream_result is not None and stream_result.status == "connected" and stream_result.telemetry is not None:
        return SelectedTelemetrySource(
            source_label="Bridge Stream",
            telemetry=stream_result.telemetry,
            status=stream_result.status,
            reason=stream_result.message,
            stream_result=stream_result,
            json_result=json_result,
        )
    if json_result.status is BridgeTelemetryStatus.CONNECTED and json_result.telemetry is not None:
        return SelectedTelemetrySource(
            source_label="Bridge JSON Snapshot",
            telemetry=json_result.telemetry,
            status=json_result.status.value,
            reason=json_result.reason,
            stream_result=stream_result,
            json_result=json_result,
        )
    return SelectedTelemetrySource(
        source_label="Simulation Fallback",
        telemetry=None,
        status="fallback",
        reason=(stream_result.message if stream_result is not None else "") or json_result.reason,
        stream_result=stream_result,
        json_result=json_result,
    )


def _read_ws_text(sock: socket.socket, *, timeout: float) -> str:
    previous = sock.gettimeout()
    sock.settimeout(timeout)
    try:
        first = sock.recv(2)
        if not first:
            raise OSError("WebSocket stream closed.")
        if len(first) < 2:
            first += sock.recv(2 - len(first))
        opcode = first[0] & 0x0F
        if opcode == 0x8:
            raise OSError("WebSocket close frame received.")
        if opcode != 0x1:
            raise OSError(f"Unsupported WebSocket opcode {opcode}.")
        masked = bool(first[1] & 0x80)
        length = first[1] & 0x7F
        if length == 126:
            length = int.from_bytes(_recv_exact(sock, 2), "big")
        elif length == 127:
            length = int.from_bytes(_recv_exact(sock, 8), "big")
        mask_key = _recv_exact(sock, 4) if masked else b""
        payload = _recv_exact(sock, length)
        if masked:
            payload = bytes(byte ^ mask_key[index % 4] for index, byte in enumerate(payload))
        return payload.decode("utf-8")
    except socket.timeout as exc:
        raise TimeoutError("No Bridge telemetry stream frame available.") from exc
    finally:
        sock.settimeout(previous)


def _recv_exact(sock: socket.socket, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise OSError("WebSocket stream closed mid-frame.")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return _aware(datetime.fromisoformat(value))
    except ValueError:
        return None


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _result_age_seconds(result: BridgeTelemetryStreamReadResult, now: datetime) -> float | None:
    if result.last_read_at is None:
        return result.age_seconds
    return max(0.0, (now - _aware(result.last_read_at)).total_seconds())
