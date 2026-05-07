from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping


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
class RuntimeFrameTelemetryPayload:
    available: bool
    parse_status: str
    schema_version: str = ""
    frame_id: str = ""
    sequence: int | None = None
    generated_at: datetime | None = None
    input_source: str = "unavailable"
    input_status: str = "unavailable"
    input_device: str = "None"
    input_sample_age_ms: int | None = None
    input_stale: bool = False
    pipeline_status: str = "unavailable"
    active_modes: tuple[str, ...] = ()
    active_rule_count: int = 0
    active_rule_names: tuple[str, ...] = ()
    final_output_axes: Mapping[str, float] = field(default_factory=dict)
    output_intent_ready: bool = False
    output_backend: str = "Unavailable"
    output_verification_status: str = "not_attempted"
    output_loop_state: str = "disabled"
    last_output_write_status: str = "Not active"
    output_verified: bool = False
    full_live_runtime_ready: bool = False
    runtime_truth: str = "unavailable"
    blocked_reason: str = ""
    input_verified_for_runtime: bool = False
    output_verified_for_runtime: bool = False
    output_loop_enabled: bool = False
    output_loop_running: bool = False
    output_loop_safety_stopped: bool = False
    pipeline_ready: bool = False
    verified_runtime_candidate: bool = False
    input_proof: str = "unavailable"
    pipeline_proof: str = "unavailable"
    output_proof: str = "unavailable"
    ready_state: str = "unavailable"
    telemetry_proof: str = "unavailable"
    safety_proof: str = "unavailable"
    fake_or_real_path: str = "unavailable"
    evaluated_at: datetime | None = None
    proof_summary: str = ""
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @classmethod
    def unavailable(
        cls,
        *,
        parse_status: str = "missing",
        errors: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
    ) -> "RuntimeFrameTelemetryPayload":
        return cls(
            available=False,
            parse_status=parse_status,
            warnings=warnings,
            errors=errors,
        )


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
    runtime_frame: RuntimeFrameTelemetryPayload | None = None
    last_command: Mapping[str, Any] | None = None
    device_discovery: Mapping[str, Any] | None = None
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
    last_read_at: datetime | None = None
    telemetry_generated_at: datetime | None = None
    stale_threshold_seconds: float = DEFAULT_STALE_AFTER_SECONDS
    reason: str = ""
    source_label: str = "Simulation Fallback"
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def should_use_fallback(self) -> bool:
        return self.status is not BridgeTelemetryStatus.CONNECTED

    @property
    def telemetry_path(self) -> Path:
        return self.path


class BridgeTelemetryClient:
    def __init__(
        self,
        *,
        telemetry_path: str | Path = DEFAULT_BRIDGE_TELEMETRY_PATH,
        stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.telemetry_path = Path(telemetry_path)
        self.stale_after_seconds = max(0.1, float(stale_after_seconds))
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def read(self) -> BridgeTelemetryReadResult:
        path = self.telemetry_path
        read_at = self._now()
        if not path.exists():
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.MISSING,
                path=path,
                message=f"Bridge telemetry file is missing: {path}",
                last_read_at=read_at,
                stale_threshold_seconds=self.stale_after_seconds,
                reason=f"Bridge telemetry file not found: {path}",
            )

        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.ERROR,
                path=path,
                message=f"Bridge telemetry file could not be read: {exc}",
                last_read_at=read_at,
                stale_threshold_seconds=self.stale_after_seconds,
                reason=f"Bridge telemetry read error: {exc}",
                errors=(str(exc),),
            )

        if not raw_text.strip():
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.INVALID,
                path=path,
                message="Bridge telemetry file is empty.",
                last_read_at=read_at,
                stale_threshold_seconds=self.stale_after_seconds,
                reason="Bridge telemetry could not be parsed: file is empty.",
            )

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.INVALID,
                path=path,
                message=f"Invalid Bridge telemetry JSON: {exc}",
                last_read_at=read_at,
                stale_threshold_seconds=self.stale_after_seconds,
                reason=f"Bridge telemetry could not be parsed: {exc}",
                errors=(str(exc),),
            )

        if not isinstance(payload, dict):
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.INVALID,
                path=path,
                message="Bridge telemetry root must be a JSON object.",
                last_read_at=read_at,
                stale_threshold_seconds=self.stale_after_seconds,
                reason="Bridge telemetry could not be parsed: root must be an object.",
            )

        missing = tuple(field for field in REQUIRED_TELEMETRY_FIELDS if field not in payload)
        if missing:
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.INVALID,
                path=path,
                message=f"Bridge telemetry is missing required fields: {', '.join(missing)}",
                last_read_at=read_at,
                stale_threshold_seconds=self.stale_after_seconds,
                reason=f"Bridge telemetry could not be parsed: missing {', '.join(missing)}.",
            )

        try:
            telemetry = _parse_payload(path, payload)
        except (TypeError, ValueError) as exc:
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.INVALID,
                path=path,
                message=f"Bridge telemetry schema is invalid: {exc}",
                last_read_at=read_at,
                stale_threshold_seconds=self.stale_after_seconds,
                reason=f"Bridge telemetry could not be parsed: {exc}",
                errors=(str(exc),),
            )

        age_seconds = max(0.0, (read_at - telemetry.timestamp).total_seconds())
        if age_seconds > self.stale_after_seconds:
            telemetry = _with_stale_runtime_frame(telemetry)
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.STALE,
                path=path,
                telemetry=telemetry,
                message=(
                    f"Bridge telemetry is stale: {age_seconds:.2f}s old, "
                    f"threshold {self.stale_after_seconds:.2f}s."
                ),
                age_seconds=age_seconds,
                last_read_at=read_at,
                telemetry_generated_at=telemetry.timestamp,
                stale_threshold_seconds=self.stale_after_seconds,
                reason=(
                    f"Bridge telemetry is stale ({age_seconds:.1f}s old); "
                    "simulation fallback is active."
                ),
                warnings=("Bridge telemetry is stale; UI is using simulation fallback.",),
            )

        return BridgeTelemetryReadResult(
            status=BridgeTelemetryStatus.CONNECTED,
            path=path,
            telemetry=telemetry,
            message="Bridge telemetry connected.",
            age_seconds=age_seconds,
            last_read_at=read_at,
            telemetry_generated_at=telemetry.timestamp,
            stale_threshold_seconds=self.stale_after_seconds,
            reason="Bridge telemetry connected.",
            source_label="Bridge Telemetry",
        )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


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
        runtime_frame=_parse_runtime_frame(payload.get("runtime_frame")),
        last_command=_optional_mapping(payload.get("last_command"), "last_command"),
        device_discovery=_optional_mapping(payload.get("device_discovery"), "device_discovery"),
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


def _parse_optional_timestamp(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        return None
    try:
        return _parse_timestamp(value)
    except (TypeError, ValueError):
        return None


def _parse_runtime_frame(value: object) -> RuntimeFrameTelemetryPayload | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        return RuntimeFrameTelemetryPayload.unavailable(
            parse_status="invalid",
            errors=("runtime_frame must be an object",),
        )

    errors: list[str] = []
    final_output_axes: dict[str, float] = {}
    axes_value = value.get("final_output_axes", {})
    if isinstance(axes_value, Mapping):
        for key, item in axes_value.items():
            try:
                final_output_axes[str(key)] = float(item)
            except (TypeError, ValueError):
                errors.append(f"runtime_frame final_output_axes.{key} must be numeric")
    elif axes_value not in (None, {}):
        errors.append("runtime_frame final_output_axes must be an object")

    sequence = _optional_int(value.get("sequence"))
    generated_at = _parse_optional_timestamp(value.get("generated_at"))
    if value.get("generated_at") and generated_at is None:
        errors.append("runtime_frame generated_at must be an ISO string")

    evaluated_at = _parse_optional_timestamp(value.get("evaluated_at"))
    if value.get("evaluated_at") and evaluated_at is None:
        errors.append("runtime_frame evaluated_at must be an ISO string")

    has_readiness_proof = any(
        key in value
        for key in (
            "ready_state",
            "telemetry_proof",
            "safety_proof",
            "fake_or_real_path",
            "evaluated_at",
        )
    )
    ready_state = str(value.get("ready_state") or "unavailable") if has_readiness_proof else "unavailable"
    blocked_reason = str(value.get("blocked_reason") or "")
    if not has_readiness_proof:
        blocked_reason = "readiness_proof_missing"

    parse_status = "invalid" if errors else "ok"
    return RuntimeFrameTelemetryPayload(
        available=not errors,
        parse_status=parse_status,
        schema_version=str(value.get("schema_version") or ""),
        frame_id=str(value.get("frame_id") or ""),
        sequence=sequence,
        generated_at=generated_at,
        input_source=str(value.get("input_source") or "unavailable"),
        input_status=str(value.get("input_status") or "unavailable"),
        input_device=str(value.get("input_device") or "None"),
        input_sample_age_ms=_optional_int(value.get("input_sample_age_ms")),
        input_stale=bool(value.get("input_stale", False)),
        pipeline_status=str(value.get("pipeline_status") or "unavailable"),
        active_modes=tuple(str(item) for item in value.get("active_modes", ()) or ()),
        active_rule_count=_optional_int(value.get("active_rule_count")) or 0,
        active_rule_names=tuple(str(item) for item in value.get("active_rule_names", ()) or ()),
        final_output_axes=final_output_axes,
        output_intent_ready=bool(value.get("output_intent_ready", False)),
        output_backend=str(value.get("output_backend") or "Unavailable"),
        output_verification_status=str(value.get("output_verification_status") or "not_attempted"),
        output_loop_state=str(value.get("output_loop_state") or "disabled"),
        last_output_write_status=str(value.get("last_output_write_status") or "Not active"),
        output_verified=bool(value.get("output_verified", False)),
        full_live_runtime_ready=bool(value.get("full_live_runtime_ready", False)) if has_readiness_proof else False,
        runtime_truth=str(value.get("runtime_truth") or "unavailable"),
        blocked_reason=blocked_reason,
        input_verified_for_runtime=bool(value.get("input_verified_for_runtime", False)),
        output_verified_for_runtime=bool(value.get("output_verified_for_runtime", False)),
        output_loop_enabled=bool(value.get("output_loop_enabled", False)),
        output_loop_running=bool(value.get("output_loop_running", False)),
        output_loop_safety_stopped=bool(value.get("output_loop_safety_stopped", False)),
        pipeline_ready=bool(value.get("pipeline_ready", False)),
        verified_runtime_candidate=bool(value.get("verified_runtime_candidate", False)),
        input_proof=str(value.get("input_proof") or "unavailable"),
        pipeline_proof=str(value.get("pipeline_proof") or "unavailable"),
        output_proof=str(value.get("output_proof") or "unavailable"),
        ready_state=ready_state,
        telemetry_proof=str(value.get("telemetry_proof") or "unavailable") if has_readiness_proof else "unavailable",
        safety_proof=str(value.get("safety_proof") or "unavailable") if has_readiness_proof else "unavailable",
        fake_or_real_path=str(value.get("fake_or_real_path") or "unavailable") if has_readiness_proof else "unavailable",
        evaluated_at=evaluated_at if has_readiness_proof else None,
        proof_summary=str(value.get("proof_summary") or ""),
        warnings=tuple(str(item) for item in value.get("warnings", ()) or ()),
        errors=tuple(errors or tuple(str(item) for item in value.get("errors", ()) or ())),
    )


def _with_stale_runtime_frame(telemetry: BridgeTelemetryPayload) -> BridgeTelemetryPayload:
    runtime_frame = telemetry.runtime_frame
    if runtime_frame is None:
        return telemetry
    stale_summary = "Telemetry: stale; Ready: false; Blocked: blocked_telemetry_stale"
    summary = runtime_frame.proof_summary
    if summary:
        summary = f"{summary}; {stale_summary}"
    else:
        summary = stale_summary
    return replace(
        telemetry,
        runtime_frame=replace(
            runtime_frame,
            output_verified=False,
            full_live_runtime_ready=False,
            runtime_truth="blocked_telemetry_stale",
            blocked_reason="blocked_telemetry_stale",
            output_verified_for_runtime=False,
            verified_runtime_candidate=False,
            ready_state="blocked",
            telemetry_proof="stale",
            safety_proof="blocked",
            proof_summary=summary,
        ),
    )


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be an object")
    return value


def _optional_mapping(value: object, field_name: str) -> Mapping[str, Any] | None:
    if value is None:
        return None
    return dict(_mapping(value, field_name))


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_mapping(value: object, *, field_name: str) -> dict[str, float]:
    return {str(key): float(item) for key, item in _mapping(value, field_name).items()}


def _bool_mapping(value: object, *, field_name: str) -> dict[str, bool]:
    return {str(key): bool(item) for key, item in _mapping(value, field_name).items()}


def _int_mapping(value: object, *, field_name: str) -> dict[str, int]:
    return {str(key): int(item) for key, item in _mapping(value, field_name).items()}
