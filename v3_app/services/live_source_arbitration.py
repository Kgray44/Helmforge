from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from v3_app.services.bridge_client import BridgeTelemetryReadResult, BridgeTelemetryStatus
from v3_app.services.bridge_stream_client import BridgeTelemetryStreamReadResult


EMBEDDED_BRIDGE_SOURCE_LABEL = "Embedded Bridge"


@dataclass(frozen=True)
class LiveSourceArbitrationSnapshot:
    current_source: str
    current_source_started_at: datetime | None
    last_source_switch_at: datetime | None
    last_embedded_frame_at: datetime | None
    last_stream_frame_at: datetime | None
    last_json_frame_at: datetime | None
    source_switch_count: int
    last_switch_reason: str
    fallback_reason: str
    source_locked_to_embedded: bool


class LiveTelemetrySourceSelector:
    def __init__(
        self,
        *,
        embedded_stale_after_seconds: float = 1.0,
        source_switch_cooldown_seconds: float = 0.5,
        clock=None,
    ) -> None:
        self.embedded_stale_after_seconds = max(0.1, float(embedded_stale_after_seconds))
        self.source_switch_cooldown_seconds = max(0.0, float(source_switch_cooldown_seconds))
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.current_source = ""
        self.current_source_started_at: datetime | None = None
        self.last_source_switch_at: datetime | None = None
        self.last_embedded_frame_at: datetime | None = None
        self.last_stream_frame_at: datetime | None = None
        self.last_json_frame_at: datetime | None = None
        self.source_switch_count = 0
        self.last_switch_reason = "none"
        self.fallback_reason = ""
        self.source_locked_to_embedded = False
        self._current_result: BridgeTelemetryReadResult | None = None

    def select(
        self,
        *,
        embedded_result: BridgeTelemetryReadResult | None,
        stream_result: BridgeTelemetryStreamReadResult | None = None,
        json_result: BridgeTelemetryReadResult | None = None,
    ) -> BridgeTelemetryReadResult:
        now = _aware(self._clock())
        if _bridge_result_connected(embedded_result):
            self.last_embedded_frame_at = now
            return self._accept(embedded_result, now=now, reason="embedded frame fresh", lock_to_embedded=True)

        if self._can_hold_embedded(now):
            self.fallback_reason = "holding Embedded Bridge during brief telemetry gap"
            return self._current_result  # type: ignore[return-value]

        if _stream_result_connected(stream_result):
            self.last_stream_frame_at = now
            fallback = _stream_to_bridge_result(stream_result, json_result)
            self.fallback_reason = "Embedded Bridge unavailable/stale; using Bridge Stream."
            return self._accept(fallback, now=now, reason=self.fallback_reason, lock_to_embedded=False)

        if _bridge_result_connected(json_result):
            self.last_json_frame_at = now
            self.fallback_reason = "Embedded Bridge unavailable/stale; using Bridge JSON Snapshot."
            return self._accept(_json_snapshot_result(json_result), now=now, reason=self.fallback_reason, lock_to_embedded=False)

        fallback = json_result or embedded_result
        if fallback is not None:
            self.fallback_reason = fallback.reason or fallback.message or "No fresh live telemetry source available."
            return self._accept(fallback, now=now, reason=self.fallback_reason, lock_to_embedded=False)
        raise ValueError("At least one telemetry source result is required.")

    def snapshot(self) -> LiveSourceArbitrationSnapshot:
        return LiveSourceArbitrationSnapshot(
            current_source=self.current_source,
            current_source_started_at=self.current_source_started_at,
            last_source_switch_at=self.last_source_switch_at,
            last_embedded_frame_at=self.last_embedded_frame_at,
            last_stream_frame_at=self.last_stream_frame_at,
            last_json_frame_at=self.last_json_frame_at,
            source_switch_count=self.source_switch_count,
            last_switch_reason=self.last_switch_reason,
            fallback_reason=self.fallback_reason,
            source_locked_to_embedded=self.source_locked_to_embedded,
        )

    def _accept(
        self,
        result: BridgeTelemetryReadResult,
        *,
        now: datetime,
        reason: str,
        lock_to_embedded: bool,
    ) -> BridgeTelemetryReadResult:
        label = result.source_label or result.status.value
        if self.current_source != label:
            self.source_switch_count += 1
            self.current_source = label
            self.current_source_started_at = now
            self.last_source_switch_at = now
            self.last_switch_reason = reason
        self.source_locked_to_embedded = lock_to_embedded
        self._current_result = result
        return result

    def _can_hold_embedded(self, now: datetime) -> bool:
        if self.current_source != EMBEDDED_BRIDGE_SOURCE_LABEL or self._current_result is None:
            return False
        if self.last_embedded_frame_at is None:
            return False
        age = max(0.0, (now - self.last_embedded_frame_at).total_seconds())
        return age <= self.embedded_stale_after_seconds


def _bridge_result_connected(result: BridgeTelemetryReadResult | None) -> bool:
    return result is not None and result.status is BridgeTelemetryStatus.CONNECTED and result.telemetry is not None


def _stream_result_connected(result: BridgeTelemetryStreamReadResult | None) -> bool:
    return result is not None and result.status == "connected" and result.telemetry is not None


def _stream_to_bridge_result(
    stream_result: BridgeTelemetryStreamReadResult,
    json_result: BridgeTelemetryReadResult | None,
) -> BridgeTelemetryReadResult:
    return BridgeTelemetryReadResult(
        status=BridgeTelemetryStatus.CONNECTED,
        path=json_result.path if json_result is not None else Path("<bridge-stream>"),
        telemetry=stream_result.telemetry,
        message=stream_result.message,
        age_seconds=stream_result.age_seconds,
        last_read_at=stream_result.last_read_at,
        telemetry_generated_at=getattr(stream_result.telemetry, "timestamp", None),
        stale_threshold_seconds=json_result.stale_threshold_seconds if json_result is not None else 5.0,
        reason="Bridge telemetry stream connected.",
        source_label="Bridge Stream",
    )


def _json_snapshot_result(result: BridgeTelemetryReadResult) -> BridgeTelemetryReadResult:
    return replace(
        result,
        source_label="Bridge JSON Snapshot",
        reason=result.reason or "Using Bridge JSON Snapshot because higher-priority live sources are unavailable.",
    )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
