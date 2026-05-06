from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


DEFAULT_BRIDGE_TELEMETRY_PATH = Path(tempfile.gettempdir()) / "helmforge_bridge_telemetry.json"
DEFAULT_STALE_AFTER_SECONDS = 5.0

REQUIRED_TELEMETRY_FIELDS = (
    "timestamp",
    "lifecycle_state",
    "runtime_truth",
    "input_status",
    "output_status",
    "output_verified",
    "active_profile",
    "raw_axes",
    "final_axes",
    "buttons",
    "hats",
    "active_modes",
    "rule_summary",
)


class BridgeTelemetryStatus(str, Enum):
    CONNECTED = "Connected"
    MISSING = "Missing"
    STALE = "Stale"
    INVALID = "Invalid"
    ERROR = "Error"


@dataclass(frozen=True)
class BridgeTelemetryPayload:
    path: Path
    timestamp: datetime
    lifecycle_state: str
    runtime_truth: str
    input_status: str
    output_status: str
    output_verified: bool
    active_profile: str
    raw_axes: Mapping[str, float]
    final_axes: Mapping[str, float]
    buttons: Mapping[str, bool]
    hats: Mapping[str, str]
    active_modes: Mapping[str, Any]
    rule_summary: Mapping[str, int]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    bridge_name: str = "HelmForge Bridge"
    product_name: str = "HelmForge"


@dataclass(frozen=True)
class BridgeTelemetryReadResult:
    status: BridgeTelemetryStatus
    path: Path
    telemetry: BridgeTelemetryPayload | None = None
    message: str = ""
    age_seconds: float | None = None
    source_label: str = "Simulation Fallback"
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def should_use_fallback(self) -> bool:
        return self.status is not BridgeTelemetryStatus.CONNECTED


class BridgeTelemetryClient:
    def __init__(
        self,
        *,
        telemetry_path: str | Path = DEFAULT_BRIDGE_TELEMETRY_PATH,
        stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    ) -> None:
        self.telemetry_path = Path(telemetry_path)
        self.stale_after_seconds = max(0.1, float(stale_after_seconds))

    def read(self) -> BridgeTelemetryReadResult:
        path = self.telemetry_path
        if not path.exists():
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.MISSING,
                path=path,
                message=f"Bridge telemetry file is missing: {path}",
            )

        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.ERROR,
                path=path,
                message=f"Bridge telemetry file could not be read: {exc}",
                errors=(str(exc),),
            )

        if not raw_text.strip():
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.INVALID,
                path=path,
                message="Bridge telemetry file is empty.",
            )

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.INVALID,
                path=path,
                message=f"Invalid Bridge telemetry JSON: {exc}",
                errors=(str(exc),),
            )

        if not isinstance(payload, dict):
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.INVALID,
                path=path,
                message="Bridge telemetry root must be a JSON object.",
            )

        missing = tuple(field for field in REQUIRED_TELEMETRY_FIELDS if field not in payload)
        if missing:
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.INVALID,
                path=path,
                message=f"Bridge telemetry is missing required fields: {', '.join(missing)}",
            )

        try:
            telemetry = _parse_payload(path, payload)
        except (TypeError, ValueError) as exc:
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.INVALID,
                path=path,
                message=f"Bridge telemetry schema is invalid: {exc}",
                errors=(str(exc),),
            )

        age_seconds = max(0.0, (datetime.now(timezone.utc) - telemetry.timestamp).total_seconds())
        if age_seconds > self.stale_after_seconds:
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.STALE,
                path=path,
                telemetry=telemetry,
                message=(
                    f"Bridge telemetry is stale: {age_seconds:.2f}s old, "
                    f"threshold {self.stale_after_seconds:.2f}s."
                ),
                age_seconds=age_seconds,
                warnings=("Bridge telemetry is stale; UI is using simulation fallback.",),
            )

        return BridgeTelemetryReadResult(
            status=BridgeTelemetryStatus.CONNECTED,
            path=path,
            telemetry=telemetry,
            message="Bridge telemetry connected.",
            age_seconds=age_seconds,
            source_label="Bridge Telemetry",
        )


def _parse_payload(path: Path, payload: Mapping[str, Any]) -> BridgeTelemetryPayload:
    timestamp = _parse_timestamp(payload["timestamp"])
    return BridgeTelemetryPayload(
        path=path,
        timestamp=timestamp,
        lifecycle_state=str(payload["lifecycle_state"]),
        runtime_truth=str(payload["runtime_truth"]),
        input_status=str(payload["input_status"]),
        output_status=str(payload["output_status"]),
        output_verified=bool(payload["output_verified"]),
        active_profile=str(payload["active_profile"]),
        raw_axes=_float_mapping(payload["raw_axes"], field_name="raw_axes"),
        final_axes=_float_mapping(payload["final_axes"], field_name="final_axes"),
        buttons=_bool_mapping(payload["buttons"], field_name="buttons"),
        hats={str(key): str(value) for key, value in _mapping(payload["hats"], "hats").items()},
        active_modes=dict(_mapping(payload["active_modes"], "active_modes")),
        rule_summary=_int_mapping(payload["rule_summary"], field_name="rule_summary"),
        warnings=tuple(str(item) for item in payload.get("warnings", ()) or ()),
        errors=tuple(str(item) for item in payload.get("errors", ()) or ()),
        bridge_name=str(payload.get("bridge_name") or "HelmForge Bridge"),
        product_name=str(payload.get("product_name") or "HelmForge"),
    )


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be an object")
    return value


def _float_mapping(value: object, *, field_name: str) -> dict[str, float]:
    return {str(key): float(item) for key, item in _mapping(value, field_name).items()}


def _bool_mapping(value: object, *, field_name: str) -> dict[str, bool]:
    return {str(key): bool(item) for key, item in _mapping(value, field_name).items()}


def _int_mapping(value: object, *, field_name: str) -> dict[str, int]:
    return {str(key): int(item) for key, item in _mapping(value, field_name).items()}
