from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping, Protocol

from v3_app.services.bridge_client import BridgeTelemetryReadResult, BridgeTelemetryStatus


MANUAL_BRIDGE_LAUNCH_COMMAND = "python -m bridge_app.main --run-for-ms 250"


class BridgeProcessPresenceState(str, Enum):
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    NOT_FOUND = "not_found"
    MAYBE_RUNNING = "maybe_running"
    SEEN_BUT_TELEMETRY_MISSING = "seen_but_telemetry_missing"
    SEEN_BUT_TELEMETRY_STALE = "seen_but_telemetry_stale"
    FRESH_TELEMETRY_CONFIRMED = "fresh_telemetry_confirmed"
    TELEMETRY_INVALID = "telemetry_invalid"
    TELEMETRY_ERROR = "telemetry_error"


@dataclass(frozen=True)
class BridgeProcessPresenceHint:
    state: BridgeProcessPresenceState = BridgeProcessPresenceState.UNKNOWN
    provider: str = "unknown"
    process_count: int = 0
    checked_at: datetime | None = None
    message: str = ""
    error: str | None = None

    @property
    def label(self) -> str:
        return _presence_label(self.state)


class BridgeProcessPresenceProvider(Protocol):
    def get_presence(self) -> BridgeProcessPresenceHint:
        ...


@dataclass(frozen=True)
class FakeBridgeProcessPresenceProvider:
    hint: BridgeProcessPresenceHint

    def get_presence(self) -> BridgeProcessPresenceHint:
        return self.hint


class UnavailableBridgeProcessPresenceProvider:
    def get_presence(self) -> BridgeProcessPresenceHint:
        return BridgeProcessPresenceHint(
            state=BridgeProcessPresenceState.UNAVAILABLE,
            provider="unavailable",
            checked_at=datetime.now(timezone.utc),
            message="Process inspection is unavailable in this Phase 9I build.",
        )


@dataclass(frozen=True)
class BridgeLifecycleDiagnostics:
    telemetry_status: BridgeTelemetryStatus
    telemetry_label: str
    telemetry_age_seconds: float | None
    lifecycle_state: str
    runtime_truth: str
    output_verified: bool
    full_live_runtime_ready: bool
    process_hint: BridgeProcessPresenceHint
    process_hint_label: str
    device_discovery_status: str
    last_command_status: str
    last_command_request_id: str | None
    last_command_command: str
    diagnostic_text: str
    manual_launch_hint: str | None = None


@dataclass(frozen=True)
class BridgeDiagnosticDisplayRow:
    label: str
    value: str
    severity: str = "info"
    detail: str = ""


def compose_bridge_lifecycle_diagnostics(
    telemetry_result: BridgeTelemetryReadResult,
    process_hint: BridgeProcessPresenceHint,
    *,
    fallback_runtime_truth: str,
    fallback_output_verified: bool,
) -> BridgeLifecycleDiagnostics:
    telemetry = telemetry_result.telemetry
    runtime_truth = _string_value(getattr(telemetry, "runtime_truth", None), fallback=fallback_runtime_truth)
    output_verified = bool(getattr(telemetry, "output_verified", fallback_output_verified))
    lifecycle_state = _string_value(getattr(telemetry, "lifecycle_state", None), fallback="Unknown")
    device_status = _device_discovery_status(getattr(telemetry, "device_discovery", None))
    last_command = getattr(telemetry, "last_command", None)
    last_command_status = _mapping_value(last_command, "status", fallback="none")
    last_command_request_id = _mapping_optional_value(last_command, "request_id")
    last_command_command = _mapping_value(last_command, "command", fallback="Bridge")

    effective_hint = _effective_presence_hint(telemetry_result.status, process_hint)
    diagnostic = _diagnostic_sentence(
        telemetry_result,
        effective_hint,
        lifecycle_state=lifecycle_state,
        output_verified=output_verified,
        device_discovery_status=device_status,
    )
    manual_hint = None
    if telemetry_result.status in {BridgeTelemetryStatus.MISSING, BridgeTelemetryStatus.STALE}:
        manual_hint = f"Manual Bridge launch expected: {MANUAL_BRIDGE_LAUNCH_COMMAND}"
        diagnostic = f"{diagnostic} {manual_hint}"

    return BridgeLifecycleDiagnostics(
        telemetry_status=telemetry_result.status,
        telemetry_label=telemetry_result.status.value,
        telemetry_age_seconds=telemetry_result.age_seconds,
        lifecycle_state=lifecycle_state,
        runtime_truth=runtime_truth,
        output_verified=output_verified,
        full_live_runtime_ready=runtime_truth == "live_verified" and output_verified,
        process_hint=effective_hint,
        process_hint_label=effective_hint.label,
        device_discovery_status=device_status,
        last_command_status=last_command_status,
        last_command_request_id=last_command_request_id,
        last_command_command=last_command_command,
        diagnostic_text=diagnostic,
        manual_launch_hint=manual_hint,
    )


def build_live_monitor_diagnostic_rows(
    diagnostics: BridgeLifecycleDiagnostics,
    *,
    latest_request_id: str | None = None,
    latest_command_name: str | None = None,
) -> tuple[BridgeDiagnosticDisplayRow, ...]:
    rows: list[BridgeDiagnosticDisplayRow] = [
        BridgeDiagnosticDisplayRow(
            "Telemetry",
            _telemetry_display_value(diagnostics.telemetry_status),
            _telemetry_severity(diagnostics.telemetry_status),
            _age_detail(diagnostics.telemetry_age_seconds),
        ),
        BridgeDiagnosticDisplayRow(
            "Lifecycle",
            diagnostics.lifecycle_state,
            "info" if diagnostics.lifecycle_state.lower() == "simulated" else "muted",
        ),
        BridgeDiagnosticDisplayRow(
            "Runtime",
            _runtime_display_value(diagnostics.runtime_truth),
            _runtime_severity(diagnostics.runtime_truth),
        ),
        BridgeDiagnosticDisplayRow(
            "Output verified",
            str(diagnostics.output_verified).lower(),
            "ok" if diagnostics.output_verified else "muted",
        ),
        BridgeDiagnosticDisplayRow(
            "HOTAS discovery",
            _discovery_display_value(
                diagnostics.device_discovery_status,
                output_verified=diagnostics.output_verified,
            ),
            _discovery_severity(diagnostics.device_discovery_status),
        ),
        BridgeDiagnosticDisplayRow(
            "Process hint",
            diagnostics.process_hint_label,
            _process_hint_severity(diagnostics.process_hint.state),
        ),
        _command_display_row(
            diagnostics,
            latest_request_id=latest_request_id,
            latest_command_name=latest_command_name,
        ),
        BridgeDiagnosticDisplayRow(
            "Diagnosis",
            diagnostics.diagnostic_text,
            _telemetry_severity(diagnostics.telemetry_status),
        ),
    ]
    if diagnostics.manual_launch_hint:
        rows.append(
            BridgeDiagnosticDisplayRow(
                "Manual launch",
                MANUAL_BRIDGE_LAUNCH_COMMAND,
                "warning",
                "Manual Bridge launch expected.",
            )
        )
    return tuple(rows)


def build_bridge_diagnostic_copy_text(diagnostics: BridgeLifecycleDiagnostics) -> str:
    age = "n/a" if diagnostics.telemetry_age_seconds is None else f"{diagnostics.telemetry_age_seconds:.1f}s"
    lines = (
        f"telemetry: {diagnostics.telemetry_label}",
        f"telemetry_age: {age}",
        f"lifecycle: {diagnostics.lifecycle_state}",
        f"runtime_truth: {diagnostics.runtime_truth}",
        f"output_verified: {str(diagnostics.output_verified).lower()}",
        f"Full Live Runtime Ready: {str(diagnostics.full_live_runtime_ready).lower()}",
        f"device_discovery: {diagnostics.device_discovery_status}",
        f"process_hint: {diagnostics.process_hint.state.value}",
        f"last_command: {diagnostics.last_command_status}",
    )
    if diagnostics.manual_launch_hint:
        lines = (*lines, diagnostics.manual_launch_hint)
    return "\n".join(lines)


def _effective_presence_hint(
    telemetry_status: BridgeTelemetryStatus,
    process_hint: BridgeProcessPresenceHint,
) -> BridgeProcessPresenceHint:
    if telemetry_status is BridgeTelemetryStatus.CONNECTED:
        return BridgeProcessPresenceHint(
            state=BridgeProcessPresenceState.FRESH_TELEMETRY_CONFIRMED,
            provider=process_hint.provider,
            process_count=process_hint.process_count,
            checked_at=process_hint.checked_at,
            message="Fresh telemetry is stronger than process presence hints.",
        )
    if telemetry_status is BridgeTelemetryStatus.INVALID:
        return BridgeProcessPresenceHint(
            state=BridgeProcessPresenceState.TELEMETRY_INVALID,
            provider=process_hint.provider,
            process_count=process_hint.process_count,
            checked_at=process_hint.checked_at,
            message="Telemetry exists but is invalid.",
        )
    if telemetry_status is BridgeTelemetryStatus.ERROR:
        return BridgeProcessPresenceHint(
            state=BridgeProcessPresenceState.TELEMETRY_ERROR,
            provider=process_hint.provider,
            process_count=process_hint.process_count,
            checked_at=process_hint.checked_at,
            message="Telemetry read failed.",
            error=process_hint.error,
        )
    if telemetry_status is BridgeTelemetryStatus.MISSING and process_hint.state is BridgeProcessPresenceState.MAYBE_RUNNING:
        return BridgeProcessPresenceHint(
            state=BridgeProcessPresenceState.SEEN_BUT_TELEMETRY_MISSING,
            provider=process_hint.provider,
            process_count=process_hint.process_count,
            checked_at=process_hint.checked_at,
            message=process_hint.message,
        )
    if telemetry_status is BridgeTelemetryStatus.STALE and process_hint.state is BridgeProcessPresenceState.MAYBE_RUNNING:
        return BridgeProcessPresenceHint(
            state=BridgeProcessPresenceState.SEEN_BUT_TELEMETRY_STALE,
            provider=process_hint.provider,
            process_count=process_hint.process_count,
            checked_at=process_hint.checked_at,
            message=process_hint.message,
        )
    return process_hint


def _diagnostic_sentence(
    telemetry_result: BridgeTelemetryReadResult,
    process_hint: BridgeProcessPresenceHint,
    *,
    lifecycle_state: str,
    output_verified: bool,
    device_discovery_status: str,
) -> str:
    if telemetry_result.status is BridgeTelemetryStatus.CONNECTED:
        parts = [
            "Bridge telemetry fresh.",
            f"Bridge {lifecycle_state.lower()}; output verification {str(output_verified).lower()}.",
            _discovery_sentence(device_discovery_status, output_verified=output_verified),
        ]
        return " ".join(part for part in parts if part)

    if telemetry_result.status is BridgeTelemetryStatus.MISSING:
        if process_hint.state is BridgeProcessPresenceState.SEEN_BUT_TELEMETRY_MISSING:
            return "Bridge process may be running, but telemetry is missing. Manual Bridge launch may be required."
        return "Bridge telemetry missing; manual Bridge launch may be required."

    if telemetry_result.status is BridgeTelemetryStatus.STALE:
        if process_hint.state is BridgeProcessPresenceState.SEEN_BUT_TELEMETRY_STALE:
            return "Bridge process may be running, but telemetry is stale. simulation fallback active."
        return "Bridge telemetry stale; simulation fallback active."

    if telemetry_result.status is BridgeTelemetryStatus.INVALID:
        return "Bridge telemetry invalid; simulation fallback active."

    if telemetry_result.status is BridgeTelemetryStatus.ERROR:
        return "Bridge telemetry error; simulation fallback active."

    return "Bridge telemetry state unknown; simulation fallback active."


def _discovery_sentence(device_discovery_status: str, *, output_verified: bool) -> str:
    if device_discovery_status == "supported_device_detected":
        return (
            "Supported HOTAS detected; polling not active. "
            f"Device discovery only; output verification {str(output_verified).lower()}."
        )
    if device_discovery_status == "no_supported_device":
        return "No supported HOTAS detected."
    if device_discovery_status == "backend_unavailable":
        return "HOTAS discovery backend unavailable."
    if device_discovery_status == "discovery_error":
        return "HOTAS discovery error."
    return "HOTAS discovery not checked."


def _device_discovery_status(device_discovery: object) -> str:
    if hasattr(device_discovery, "to_dict"):
        device_discovery = device_discovery.to_dict()
    if isinstance(device_discovery, Mapping):
        return str(device_discovery.get("status") or "not_checked")
    return "not_checked"


def _mapping_value(value: object, key: str, *, fallback: str) -> str:
    if isinstance(value, Mapping):
        return str(value.get(key) or fallback)
    return fallback


def _mapping_optional_value(value: object, key: str) -> str | None:
    if isinstance(value, Mapping) and value.get(key):
        return str(value.get(key))
    return None


def _string_value(value: object, *, fallback: str) -> str:
    if value is None:
        return fallback
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _presence_label(state: BridgeProcessPresenceState) -> str:
    return {
        BridgeProcessPresenceState.UNAVAILABLE: "Unavailable",
        BridgeProcessPresenceState.UNKNOWN: "Unknown",
        BridgeProcessPresenceState.NOT_FOUND: "Not found",
        BridgeProcessPresenceState.MAYBE_RUNNING: "Maybe running",
        BridgeProcessPresenceState.SEEN_BUT_TELEMETRY_MISSING: "Maybe running",
        BridgeProcessPresenceState.SEEN_BUT_TELEMETRY_STALE: "Maybe running",
        BridgeProcessPresenceState.FRESH_TELEMETRY_CONFIRMED: "Fresh telemetry confirmed",
        BridgeProcessPresenceState.TELEMETRY_INVALID: "Telemetry invalid",
        BridgeProcessPresenceState.TELEMETRY_ERROR: "Telemetry error",
    }[state]


def _telemetry_display_value(status: BridgeTelemetryStatus) -> str:
    return {
        BridgeTelemetryStatus.CONNECTED: "Fresh",
        BridgeTelemetryStatus.MISSING: "Missing",
        BridgeTelemetryStatus.STALE: "Stale",
        BridgeTelemetryStatus.INVALID: "Invalid",
        BridgeTelemetryStatus.ERROR: "Error",
    }[status]


def _telemetry_severity(status: BridgeTelemetryStatus) -> str:
    return {
        BridgeTelemetryStatus.CONNECTED: "ok",
        BridgeTelemetryStatus.MISSING: "warning",
        BridgeTelemetryStatus.STALE: "warning",
        BridgeTelemetryStatus.INVALID: "error",
        BridgeTelemetryStatus.ERROR: "error",
    }[status]


def _age_detail(age_seconds: float | None) -> str:
    if age_seconds is None:
        return "age n/a"
    return f"age {age_seconds:.1f}s"


def _runtime_display_value(runtime_truth: str) -> str:
    return {
        "blocked_missing_device": "Runtime blocked: missing device",
        "blocked_missing_driver": "Runtime blocked: missing output",
        "detected_unverified": "Detected unverified",
        "live_verified": "Live verified",
        "simulated": "Simulated",
        "error": "Runtime error",
    }.get(runtime_truth, runtime_truth)


def _runtime_severity(runtime_truth: str) -> str:
    if runtime_truth in {"blocked_missing_device", "blocked_missing_driver", "detected_unverified"}:
        return "warning"
    if runtime_truth == "error":
        return "error"
    if runtime_truth == "live_verified":
        return "ok"
    return "info"


def _discovery_display_value(device_discovery_status: str, *, output_verified: bool) -> str:
    if device_discovery_status == "supported_device_detected":
        return (
            "Supported HOTAS detected; polling not active. "
            f"Discovery only; output verification {str(output_verified).lower()}."
        )
    if device_discovery_status == "no_supported_device":
        return "No supported HOTAS detected"
    if device_discovery_status == "backend_unavailable":
        return "Discovery backend unavailable"
    if device_discovery_status == "discovery_error":
        return "Discovery error"
    return "Not checked"


def _discovery_severity(device_discovery_status: str) -> str:
    if device_discovery_status in {"discovery_error"}:
        return "error"
    if device_discovery_status in {"no_supported_device", "backend_unavailable"}:
        return "warning"
    if device_discovery_status == "supported_device_detected":
        return "info"
    return "muted"


def _process_hint_severity(state: BridgeProcessPresenceState) -> str:
    if state in {
        BridgeProcessPresenceState.SEEN_BUT_TELEMETRY_MISSING,
        BridgeProcessPresenceState.SEEN_BUT_TELEMETRY_STALE,
    }:
        return "warning"
    if state in {BridgeProcessPresenceState.TELEMETRY_INVALID, BridgeProcessPresenceState.TELEMETRY_ERROR}:
        return "error"
    if state is BridgeProcessPresenceState.FRESH_TELEMETRY_CONFIRMED:
        return "ok"
    if state is BridgeProcessPresenceState.MAYBE_RUNNING:
        return "info"
    return "muted"


def _command_display_row(
    diagnostics: BridgeLifecycleDiagnostics,
    *,
    latest_request_id: str | None,
    latest_command_name: str | None,
) -> BridgeDiagnosticDisplayRow:
    if latest_request_id:
        if diagnostics.telemetry_status is not BridgeTelemetryStatus.CONNECTED:
            return BridgeDiagnosticDisplayRow("Last command", "Awaiting Bridge telemetry", "warning")
        if diagnostics.last_command_request_id != latest_request_id:
            return BridgeDiagnosticDisplayRow(
                "Last command",
                "Awaiting Bridge telemetry",
                "warning",
                _unrelated_command_detail(diagnostics),
            )
        status = diagnostics.last_command_status
        if status == "completed":
            return BridgeDiagnosticDisplayRow("Last command", "Completed by Bridge", "ok")
        if status == "acknowledged":
            return BridgeDiagnosticDisplayRow("Last command", "Acknowledged by Bridge", "info")
        if status in {"failed", "rejected", "ignored_stale"}:
            return BridgeDiagnosticDisplayRow("Last command", f"{status.replace('_', ' ').title()} by Bridge", "error")
        return BridgeDiagnosticDisplayRow("Last command", f"{status} by Bridge", "info")

    if diagnostics.last_command_request_id:
        return BridgeDiagnosticDisplayRow(
            "Last command",
            "No UI command requested",
            "muted",
            _unrelated_command_detail(diagnostics),
        )
    return BridgeDiagnosticDisplayRow("Last command", "No command requested", "muted")


def _unrelated_command_detail(diagnostics: BridgeLifecycleDiagnostics) -> str:
    if not diagnostics.last_command_request_id:
        return ""
    return (
        "Unrelated Bridge command telemetry: "
        f"{diagnostics.last_command_status} for {diagnostics.last_command_request_id}."
    )
