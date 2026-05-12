from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)
from shared_core.runtime.telemetry import BridgeTelemetrySnapshot
from v3_app.services.app_state import AppState


@dataclass(frozen=True)
class PreflightReadinessGateModel:
    label: str
    state: str
    reason: str
    role: str
    detail: str = ""


@dataclass(frozen=True)
class PreflightSystemDetailModel:
    label: str
    value: str
    role: str = "info"
    detail: str = ""


@dataclass(frozen=True)
class PreflightChecklistItemModel:
    label: str
    state: str
    reason: str
    action_available: bool = False


@dataclass(frozen=True)
class PreflightReadinessModel:
    overall_state: str
    overall_label: str
    short_explanation: str
    next_recommended_action: str
    runtime_truth_label: str
    output_proof_label: str
    telemetry_label: str
    source_label: str
    readiness_gates: tuple[PreflightReadinessGateModel, ...]
    system_details: tuple[PreflightSystemDetailModel, ...]
    checklist_items: tuple[PreflightChecklistItemModel, ...]
    advanced_diagnostics: tuple[PreflightSystemDetailModel, ...]
    truth_source_notes: tuple[str, ...]


def build_preflight_readiness_model(
    *,
    state: AppState,
    runtime_status: RuntimePreflightStatus | None = None,
    telemetry: BridgeTelemetrySnapshot | None = None,
    telemetry_age_seconds: float | None = None,
) -> PreflightReadinessModel:
    runtime_status = runtime_status or runtime_status_from_app_state(state)
    telemetry_state = _telemetry_state(telemetry=telemetry, runtime_status=runtime_status, age_seconds=telemetry_age_seconds)
    overall_state, overall_label, explanation, next_action = _overall_status(
        state=state,
        runtime_status=runtime_status,
        telemetry_state=telemetry_state,
    )
    output_proof_label = "Output proof verified" if runtime_status.live_output_writes_verified else "Output proof missing"
    runtime_truth_label = _runtime_truth_label(runtime_status)
    source_label = _source_label(state)
    gates = _readiness_gates(
        state=state,
        runtime_status=runtime_status,
        telemetry_state=telemetry_state,
        overall_state=overall_state,
    )
    details = _system_details(
        state=state,
        runtime_status=runtime_status,
        telemetry=telemetry,
        telemetry_state=telemetry_state,
        source_label=source_label,
        output_proof_label=output_proof_label,
        runtime_truth_label=runtime_truth_label,
    )
    checklist = _checklist_items(state=state, runtime_status=runtime_status, telemetry_state=telemetry_state)
    diagnostics = _advanced_diagnostics(
        state=state,
        runtime_status=runtime_status,
        telemetry=telemetry,
        telemetry_state=telemetry_state,
        source_label=source_label,
        blocker=overall_label,
    )
    notes = (
        "Runtime truth comes from the existing AppState/RuntimePreflightStatus surface.",
        "vJoy detection is reported separately from output write proof.",
        "Bridge telemetry is passive input only; LCD-4 does not start, stop, poll, or verify runtime output.",
    )
    return PreflightReadinessModel(
        overall_state=overall_state,
        overall_label=overall_label,
        short_explanation=explanation,
        next_recommended_action=next_action,
        runtime_truth_label=runtime_truth_label,
        output_proof_label=output_proof_label,
        telemetry_label=telemetry_state.label,
        source_label=source_label,
        readiness_gates=gates,
        system_details=details,
        checklist_items=checklist,
        advanced_diagnostics=diagnostics,
        truth_source_notes=notes,
    )


def runtime_status_from_app_state(state: AppState) -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.FULL_LIVE
        if state.runtime.truth is RuntimeTruth.LIVE_VERIFIED and state.runtime.output_verified
        else RuntimeMode.SIMULATED,
        truth=state.runtime.truth,
        input=InputDeviceDetection(status=state.runtime.input_status),
        output=OutputBackendDetection(
            status=state.runtime.output_status,
            backend_name=state.runtime.backend_name,
            live_output_writes_verified=state.runtime.output_verified,
        ),
    )


@dataclass(frozen=True)
class _TelemetryState:
    state: str
    role: str
    label: str
    detail: str
    source: str
    age_label: str


def _overall_status(
    *,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    telemetry_state: _TelemetryState,
) -> tuple[str, str, str, str]:
    if runtime_status.truth is RuntimeTruth.ERROR or runtime_status.errors or _has_runtime_error(runtime_status):
        return (
            "error",
            "Hard error",
            _first(runtime_status.errors, "Runtime reported an error; live output remains gated."),
            "Review advanced diagnostics and resolve the runtime error before live use.",
        )
    if runtime_status.input.status is InputStatus.MISSING:
        return (
            "blocked",
            "HOTAS not connected",
            "The workspace can be reviewed, but physical HOTAS input proof is missing.",
            "Connect HOTAS controller.",
        )
    if runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DRIVER or runtime_status.output.status is OutputStatus.VJOY_MISSING:
        return (
            "blocked",
            "Runtime blocked",
            "The output backend is not ready for guarded live use.",
            "Confirm vJoy is detected before checking output proof.",
        )
    if telemetry_state.state == "waiting" and telemetry_state.label == "Telemetry stale":
        return (
            "waiting",
            "Telemetry stale",
            "The last telemetry truth is too old to treat as current live state.",
            "Confirm Bridge telemetry is fresh.",
        )
    if _output_proof_missing(runtime_status):
        return (
            "blocked",
            "Output proof missing",
            "vJoy detection or output intent is not the same as verified output write proof.",
            "Confirm output proof exists.",
        )
    if not state.saved:
        return (
            "attention",
            "Workspace unsaved",
            "The runtime may be available, but the workspace has draft changes.",
            "Save workspace changes.",
        )
    if runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and runtime_status.live_output_writes_verified:
        return (
            "ready",
            "Ready for live output",
            "Runtime truth and output proof both report a verified live path.",
            "Proceed with live use.",
        )
    if runtime_status.truth is RuntimeTruth.SIMULATED or runtime_status.mode is RuntimeMode.SIMULATED:
        return (
            "simulation",
            "Simulation mode",
            "Simulation mode is active; live output is not active.",
            "Continue in simulation mode or complete runtime checks.",
        )
    return (
        "waiting",
        "Runtime blocked",
        "Readiness proof is incomplete.",
        "Review the blocked readiness gate.",
    )


def _readiness_gates(
    *,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    telemetry_state: _TelemetryState,
    overall_state: str,
) -> tuple[PreflightReadinessGateModel, ...]:
    return (
        _input_gate(runtime_status),
        PreflightReadinessGateModel(
            "Telemetry",
            telemetry_state.state,
            telemetry_state.label,
            telemetry_state.role,
            telemetry_state.detail,
        ),
        _workspace_gate(state),
        _vjoy_gate(runtime_status),
        _output_proof_gate(runtime_status),
        _safety_gate(runtime_status=runtime_status, overall_state=overall_state),
    )


def _input_gate(runtime_status: RuntimePreflightStatus) -> PreflightReadinessGateModel:
    status = runtime_status.input.status
    if status is InputStatus.DETECTED:
        names = ", ".join(runtime_status.detected_device_names) or runtime_status.target_hardware.primary_device_name
        return PreflightReadinessGateModel("Input", "ready", "HOTAS input detected", "ready", names)
    if status is InputStatus.MISSING:
        return PreflightReadinessGateModel(
            "Input",
            "blocked",
            "HOTAS input proof missing",
            "blocked",
            "Connect HOTAS controller before live output.",
        )
    if status is InputStatus.ERROR:
        return PreflightReadinessGateModel("Input", "error", "Input detection error", "error", _joined(runtime_status.input.errors))
    return PreflightReadinessGateModel("Input", "waiting", "Input not checked", "waiting", "No live input sample is available.")


def _workspace_gate(state: AppState) -> PreflightReadinessGateModel:
    workspace = state.active_profile or "Workspace loaded"
    if state.saved:
        return PreflightReadinessGateModel("Workspace", "ready", "Workspace loaded and saved", "ready", workspace)
    return PreflightReadinessGateModel(
        "Workspace",
        "attention",
        "Workspace unsaved",
        "unsaved",
        "Draft changes are staged but not saved.",
    )


def _vjoy_gate(runtime_status: RuntimePreflightStatus) -> PreflightReadinessGateModel:
    status = runtime_status.output.status
    backend = runtime_status.detected_output_backend_name or "vJoy"
    if status in {OutputStatus.VJOY_DETECTED, OutputStatus.OUTPUT_VERIFIED}:
        return PreflightReadinessGateModel(
            "vJoy",
            "ready",
            "vJoy is detected",
            "ready",
            f"{backend} is present; output proof is checked separately.",
        )
    if status is OutputStatus.VJOY_MISSING:
        return PreflightReadinessGateModel("vJoy", "blocked", "vJoy missing", "blocked", "Install or enable vJoy before output proof.")
    if status is OutputStatus.OUTPUT_ERROR:
        return PreflightReadinessGateModel("vJoy", "error", "Output backend error", "error", _joined(runtime_status.output.errors))
    return PreflightReadinessGateModel("vJoy", "waiting", "vJoy not checked", "waiting", "Output backend proof is not available.")


def _output_proof_gate(runtime_status: RuntimePreflightStatus) -> PreflightReadinessGateModel:
    backend = runtime_status.detected_output_backend_name or "vJoy"
    if runtime_status.live_output_writes_verified:
        return PreflightReadinessGateModel(
            "Output Proof",
            "verified",
            "Output proof verified",
            "verified",
            f"{backend} write proof is reported by runtime truth.",
        )
    if runtime_status.output.status in {OutputStatus.VJOY_DETECTED, OutputStatus.OUTPUT_VERIFIED}:
        return PreflightReadinessGateModel(
            "Output Proof",
            "blocked",
            "Output proof missing",
            "blocked",
            "vJoy detected is not output write proof.",
        )
    return PreflightReadinessGateModel(
        "Output Proof",
        "unavailable",
        "Output proof unavailable",
        "unavailable",
        "Output backend must be detected before proof can exist.",
    )


def _safety_gate(*, runtime_status: RuntimePreflightStatus, overall_state: str) -> PreflightReadinessGateModel:
    if runtime_status.errors or _has_runtime_error(runtime_status):
        return PreflightReadinessGateModel("Safety", "error", "Safety blocked by runtime error", "error", _joined(runtime_status.errors))
    if overall_state == "ready":
        return PreflightReadinessGateModel(
            "Safety",
            "safe",
            "Live output gates satisfied",
            "safe",
            "Input, runtime truth, and output proof are all verified.",
        )
    if overall_state == "simulation":
        return PreflightReadinessGateModel(
            "Safety",
            "simulation",
            "Simulation mode",
            "simulation",
            "Live output remains inactive.",
        )
    if overall_state == "attention":
        return PreflightReadinessGateModel("Safety", "attention", "Workspace needs review", "attention", "Resolve draft state before relying on live setup.")
    return PreflightReadinessGateModel("Safety", "blocked", "Live output gated", "blocked", "One or more readiness gates are not ready.")


def _system_details(
    *,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    telemetry: BridgeTelemetrySnapshot | None,
    telemetry_state: _TelemetryState,
    source_label: str,
    output_proof_label: str,
    runtime_truth_label: str,
) -> tuple[PreflightSystemDetailModel, ...]:
    return (
        PreflightSystemDetailModel("HOTAS/device state", _input_detail(runtime_status), _input_role(runtime_status)),
        PreflightSystemDetailModel("Bridge telemetry state", telemetry_state.label, telemetry_state.role, telemetry_state.detail),
        PreflightSystemDetailModel("Telemetry freshness/source", telemetry_state.age_label, telemetry_state.role, telemetry_state.source),
        PreflightSystemDetailModel("Workspace state", state.active_profile or "Workspace loaded", "ready"),
        PreflightSystemDetailModel("Saved/unsaved state", "Saved" if state.saved else "Workspace unsaved", "saved" if state.saved else "unsaved"),
        PreflightSystemDetailModel("vJoy state", _output_backend_detail(runtime_status), _vjoy_gate(runtime_status).role),
        PreflightSystemDetailModel("Output proof state", output_proof_label, _output_proof_gate(runtime_status).role),
        PreflightSystemDetailModel("Runtime truth label", runtime_truth_label, _truth_role(runtime_status)),
        PreflightSystemDetailModel("Full live gate", _full_live_gate_label(telemetry), _full_live_gate_role(telemetry)),
        PreflightSystemDetailModel("Current data source/config", source_label, "info", state.source_config or "Workspace state"),
    )


def _checklist_items(
    *,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    telemetry_state: _TelemetryState,
) -> tuple[PreflightChecklistItemModel, ...]:
    input_detected = runtime_status.input.status is InputStatus.DETECTED
    vjoy_detected = runtime_status.output.status in {OutputStatus.VJOY_DETECTED, OutputStatus.OUTPUT_VERIFIED}
    output_verified = runtime_status.live_output_writes_verified
    simulation = runtime_status.truth is RuntimeTruth.SIMULATED or runtime_status.mode is RuntimeMode.SIMULATED
    return (
        PreflightChecklistItemModel(
            "Connect HOTAS controller",
            "done" if input_detected else "blocked",
            "Input proof present." if input_detected else "HOTAS input proof is missing.",
        ),
        PreflightChecklistItemModel(
            "Confirm Bridge telemetry is fresh",
            "done" if telemetry_state.state == "ready" else ("warning" if telemetry_state.label == "Telemetry stale" else "waiting"),
            telemetry_state.detail or telemetry_state.label,
        ),
        PreflightChecklistItemModel(
            "Load or verify workspace",
            "done" if state.active_profile else "waiting",
            state.active_profile or "Workspace name unavailable.",
        ),
        PreflightChecklistItemModel(
            "Save workspace changes",
            "done" if state.saved else "warning",
            "Workspace saved." if state.saved else "Workspace has unsaved draft changes.",
        ),
        PreflightChecklistItemModel(
            "Confirm vJoy is detected",
            "done" if vjoy_detected else "blocked",
            "vJoy detected." if vjoy_detected else "vJoy detection is unavailable.",
        ),
        PreflightChecklistItemModel(
            "Confirm output proof exists",
            "done" if output_verified else "blocked",
            "Output proof verified." if output_verified else "Output proof missing.",
        ),
        PreflightChecklistItemModel(
            "Continue in simulation mode",
            "done" if simulation and not output_verified else "unavailable",
            "Simulation mode is available for safe review." if simulation and not output_verified else "Live proof is current; simulation is optional.",
        ),
        PreflightChecklistItemModel(
            "Open setup/runtime check",
            "unavailable",
            "Support route exists; no new runtime action is wired in LCD-4.",
        ),
    )


def _advanced_diagnostics(
    *,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    telemetry: BridgeTelemetrySnapshot | None,
    telemetry_state: _TelemetryState,
    source_label: str,
    blocker: str,
) -> tuple[PreflightSystemDetailModel, ...]:
    runtime_frame = _runtime_frame(telemetry)
    return (
        PreflightSystemDetailModel("Raw runtime truth", runtime_status.truth.value, _truth_role(runtime_status)),
        PreflightSystemDetailModel("Raw runtime mode", runtime_status.mode.value, "info"),
        PreflightSystemDetailModel("Raw input status", runtime_status.input.status.value, _input_role(runtime_status)),
        PreflightSystemDetailModel("Raw output status", runtime_status.output.status.value, _vjoy_gate(runtime_status).role),
        PreflightSystemDetailModel("Output proof boolean", str(runtime_status.live_output_writes_verified).lower(), _output_proof_gate(runtime_status).role),
        PreflightSystemDetailModel("Telemetry source detail", telemetry_state.source, telemetry_state.role),
        PreflightSystemDetailModel("Telemetry freshness detail", telemetry_state.age_label, telemetry_state.role),
        PreflightSystemDetailModel("Config/source filename", state.source_config or source_label, "info"),
        PreflightSystemDetailModel("Bridge lifecycle state", _bridge_lifecycle_label(telemetry), "info"),
        PreflightSystemDetailModel("Runtime frame ready state", _runtime_frame_string(runtime_frame, "ready_state"), "info"),
        PreflightSystemDetailModel("Runtime frame output proof", _runtime_frame_string(runtime_frame, "output_proof"), "info"),
        PreflightSystemDetailModel("Runtime frame safety proof", _runtime_frame_string(runtime_frame, "safety_proof"), "info"),
        PreflightSystemDetailModel("Current blocker reason", blocker, "blocked" if blocker != "Ready for live output" else "ready"),
        PreflightSystemDetailModel("Warnings", _joined(runtime_status.warnings), "warning" if runtime_status.warnings else "info"),
        PreflightSystemDetailModel("Errors", _joined(runtime_status.errors), "error" if runtime_status.errors else "info"),
    )


def _telemetry_state(
    *,
    telemetry: BridgeTelemetrySnapshot | None,
    runtime_status: RuntimePreflightStatus,
    age_seconds: float | None,
) -> _TelemetryState:
    runtime_frame = _runtime_frame(telemetry)
    if telemetry is not None:
        stale = bool(runtime_frame.get("input_stale")) or str(runtime_frame.get("telemetry_proof", "")).casefold() == "stale"
        if str(runtime_frame.get("runtime_truth", "")).casefold() == "blocked_telemetry_stale":
            stale = True
        if age_seconds is not None and age_seconds > 5.0:
            stale = True
        age_label = _age_label(age_seconds, telemetry.timestamp)
        if stale:
            return _TelemetryState(
                "waiting",
                "waiting",
                "Telemetry stale",
                "Bridge telemetry is present but stale.",
                "Bridge telemetry",
                age_label,
            )
        return _TelemetryState("ready", "ready", "Telemetry fresh", "Bridge telemetry is fresh.", "Bridge telemetry", age_label)
    if runtime_status.truth is RuntimeTruth.LIVE_VERIFIED:
        return _TelemetryState(
            "ready",
            "ready",
            "Telemetry fresh",
            "Runtime truth reports current live verification.",
            "Runtime truth",
            "Runtime truth current",
        )
    if runtime_status.truth is RuntimeTruth.SIMULATED:
        return _TelemetryState(
            "simulation",
            "simulation",
            "Simulation mode",
            "No Bridge telemetry is required for simulation review.",
            "Simulation fallback",
            "No live telemetry",
        )
    return _TelemetryState("waiting", "waiting", "Telemetry missing", "No fresh Bridge telemetry is available.", "Workspace state", "Unavailable")


def _runtime_truth_label(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and runtime_status.live_output_writes_verified:
        return "Live Verified"
    if runtime_status.truth is RuntimeTruth.DETECTED_UNVERIFIED:
        return "Detected Unverified"
    if runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DEVICE:
        return "Runtime blocked"
    if runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DRIVER:
        return "Runtime blocked"
    if runtime_status.truth is RuntimeTruth.ERROR:
        return "Hard error"
    return "Simulation mode"


def _output_proof_missing(runtime_status: RuntimePreflightStatus) -> bool:
    if runtime_status.live_output_writes_verified:
        return False
    return runtime_status.truth is RuntimeTruth.DETECTED_UNVERIFIED or runtime_status.output.status in {
        OutputStatus.VJOY_DETECTED,
        OutputStatus.OUTPUT_VERIFIED,
    }


def _has_runtime_error(runtime_status: RuntimePreflightStatus) -> bool:
    return runtime_status.input.status is InputStatus.ERROR or runtime_status.output.status is OutputStatus.OUTPUT_ERROR


def _truth_role(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and runtime_status.live_output_writes_verified:
        return "ready"
    if runtime_status.truth is RuntimeTruth.ERROR:
        return "error"
    if runtime_status.truth is RuntimeTruth.SIMULATED:
        return "simulation"
    return "blocked"


def _input_role(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.input.status is InputStatus.DETECTED:
        return "ready"
    if runtime_status.input.status is InputStatus.ERROR:
        return "error"
    if runtime_status.input.status is InputStatus.MISSING:
        return "blocked"
    return "waiting"


def _input_detail(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.input.status is InputStatus.DETECTED:
        return "Detected"
    if runtime_status.input.status is InputStatus.MISSING:
        return "Not connected"
    if runtime_status.input.status is InputStatus.ERROR:
        return "Input error"
    return "Not checked"


def _output_backend_detail(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.output.status in {OutputStatus.VJOY_DETECTED, OutputStatus.OUTPUT_VERIFIED}:
        return "vJoy detected"
    if runtime_status.output.status is OutputStatus.VJOY_MISSING:
        return "vJoy missing"
    if runtime_status.output.status is OutputStatus.OUTPUT_ERROR:
        return "Output error"
    return "Not checked"


def _full_live_gate_label(telemetry: BridgeTelemetrySnapshot | None) -> str:
    runtime_frame = _runtime_frame(telemetry)
    if not runtime_frame:
        return "Not reported by current frame"
    if _truthy(runtime_frame.get("full_live_runtime_ready")):
        return "Ready"
    ready_state = str(runtime_frame.get("ready_state") or "blocked")
    blocked = str(runtime_frame.get("blocked_reason") or "")
    return f"{ready_state}{': ' + blocked if blocked else ''}"


def _full_live_gate_role(telemetry: BridgeTelemetrySnapshot | None) -> str:
    runtime_frame = _runtime_frame(telemetry)
    if _truthy(runtime_frame.get("full_live_runtime_ready")):
        return "ready"
    if runtime_frame:
        return "blocked"
    return "unavailable"


def _bridge_lifecycle_label(telemetry: BridgeTelemetrySnapshot | None) -> str:
    if telemetry is None:
        return "Unavailable"
    return telemetry.lifecycle_state.value


def _runtime_frame(telemetry: BridgeTelemetrySnapshot | None) -> Mapping[str, object]:
    if telemetry is None or telemetry.runtime_frame is None:
        return {}
    return telemetry.runtime_frame


def _runtime_frame_string(runtime_frame: Mapping[str, object], key: str) -> str:
    value = runtime_frame.get(key)
    if value in (None, ""):
        return "Unavailable"
    return str(value)


def _source_label(state: AppState) -> str:
    if not state.source_config:
        return "Workspace state"
    name = Path(str(state.source_config).replace("\\", "/")).name
    if name == "hotas_bridge_config_v3.json":
        return "Bridge Config"
    return name


def _age_label(age_seconds: float | None, timestamp: datetime | None) -> str:
    if age_seconds is not None:
        return f"{age_seconds:.1f}s old"
    if timestamp is None:
        return "Telemetry snapshot available"
    now = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age = max(0.0, (now - timestamp.astimezone(timezone.utc)).total_seconds())
    return f"{age:.1f}s old"


def _truthy(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() in {"true", "1", "yes", "ready"}
    return bool(value)


def _joined(values: tuple[str, ...]) -> str:
    return "; ".join(value for value in values if value) or "None"


def _first(values: tuple[str, ...], fallback: str) -> str:
    return next((value for value in values if value), fallback)
