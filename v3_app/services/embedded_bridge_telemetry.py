from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Mapping

from shared_core.runtime.telemetry import BridgeTelemetrySnapshot
from v3_app.services.bridge_client import (
    BridgeTelemetryPayload,
    BridgeTelemetryReadResult,
    BridgeTelemetryStatus,
    parse_bridge_telemetry_payload,
)


@dataclass(frozen=True)
class EmbeddedBridgeTelemetryFrame:
    telemetry: BridgeTelemetrySnapshot
    recorded_at: datetime
    producer_id: str
    payload: Mapping[str, object] | None = None


_LOCK = RLock()
_LATEST: EmbeddedBridgeTelemetryFrame | None = None


def record_embedded_bridge_telemetry(
    telemetry: BridgeTelemetrySnapshot,
    *,
    recorded_at: datetime | None = None,
    producer_id: str = "embedded_bridge",
    payload: Mapping[str, object] | None = None,
) -> None:
    global _LATEST
    with _LOCK:
        _LATEST = EmbeddedBridgeTelemetryFrame(
            telemetry=telemetry,
            recorded_at=_aware(recorded_at or datetime.now(timezone.utc)),
            producer_id=producer_id,
            payload=dict(payload) if payload is not None else None,
        )


def read_embedded_bridge_telemetry(
    *,
    stale_after_seconds: float = 1.0,
    clock=None,
) -> BridgeTelemetryReadResult:
    now = _aware((clock or (lambda: datetime.now(timezone.utc)))())
    with _LOCK:
        latest = _LATEST
    path = Path("<embedded-bridge>")
    if latest is None:
        return BridgeTelemetryReadResult(
            status=BridgeTelemetryStatus.MISSING,
            path=path,
            message="Embedded Bridge telemetry has not produced a frame yet.",
            last_read_at=now,
            stale_threshold_seconds=stale_after_seconds,
            reason="Embedded Bridge telemetry missing.",
            source_label="Embedded Bridge Missing",
        )

    age_seconds = max(0.0, (now - latest.recorded_at).total_seconds())
    try:
        if latest.payload is None and isinstance(latest.telemetry, BridgeTelemetryPayload):
            telemetry = latest.telemetry
        else:
            payload = latest.payload
            if payload is None:
                if hasattr(latest.telemetry, "to_dict"):
                    payload = latest.telemetry.to_dict()
                elif is_dataclass(latest.telemetry):
                    payload = asdict(latest.telemetry)
                else:
                    payload = dict(latest.telemetry)  # type: ignore[arg-type]
            telemetry = parse_bridge_telemetry_payload(path, payload)
    except (TypeError, ValueError) as exc:
        return BridgeTelemetryReadResult(
            status=BridgeTelemetryStatus.INVALID,
            path=path,
            message=f"Embedded Bridge telemetry is invalid: {exc}",
            age_seconds=age_seconds,
            last_read_at=now,
            stale_threshold_seconds=stale_after_seconds,
            reason=f"Embedded Bridge telemetry invalid: {exc}",
            source_label="Embedded Bridge Invalid",
            errors=(str(exc),),
        )

    if age_seconds > max(0.1, float(stale_after_seconds)):
        return BridgeTelemetryReadResult(
            status=BridgeTelemetryStatus.STALE,
            path=path,
            telemetry=telemetry,
            message="Embedded Bridge telemetry is stale.",
            age_seconds=age_seconds,
            last_read_at=now,
            telemetry_generated_at=telemetry.timestamp,
            stale_threshold_seconds=stale_after_seconds,
            reason="Embedded Bridge telemetry is stale; simulation fallback may be used.",
            source_label="Embedded Bridge Stale",
            warnings=("Embedded Bridge telemetry is stale.",),
        )

    return BridgeTelemetryReadResult(
        status=BridgeTelemetryStatus.CONNECTED,
        path=path,
        telemetry=telemetry,
        message="Embedded Bridge telemetry connected.",
        age_seconds=age_seconds,
        last_read_at=now,
        telemetry_generated_at=telemetry.timestamp,
        stale_threshold_seconds=stale_after_seconds,
        reason="Fresh embedded Bridge telemetry is available in memory.",
        source_label="Embedded Bridge",
    )


def clear_embedded_bridge_telemetry() -> None:
    global _LATEST
    with _LOCK:
        _LATEST = None


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
