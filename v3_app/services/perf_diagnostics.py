from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from shared_core.models.runtime import RuntimePreflightStatus, RuntimeTruth
from shared_core.runtime.hotas_input import PhysicalInputDiagnostics
from shared_core.runtime.vjoy_output import (
    VirtualOutputDiagnostics,
    VirtualOutputLoopSnapshot,
    VirtualOutputWriteLoopState,
    build_virtual_output_diagnostics,
)
from v3_app.services.app_state import AppState
from v3_app.services.bridge_client import RuntimeFrameTelemetryPayload


DEFAULT_MANUAL_BRIDGE_COMMAND = "python -m bridge_app.main --run-for-ms 250"


@dataclass(frozen=True)
class PerfMetricSummary:
    name: str
    count: int = 0
    average_ms: float = 0.0
    max_ms: float = 0.0
    last_ms: float = 0.0

    @property
    def available(self) -> bool:
        return self.count > 0


@dataclass
class DiagnosticsCollector:
    collect_live_timings: bool = True
    _timings: dict[str, list[float]] = field(default_factory=dict)
    _hidden_skips: dict[str, int] = field(default_factory=dict)
    _last_hidden_skip_at: dict[str, datetime] = field(default_factory=dict)

    def record_timing(self, name: str, elapsed_ms: float) -> None:
        if not self.collect_live_timings:
            return
        self._timings.setdefault(name, []).append(max(0.0, float(elapsed_ms)))

    def summary(self, name: str) -> PerfMetricSummary:
        values = self._timings.get(name, ())
        if not values:
            return PerfMetricSummary(name=name)
        return PerfMetricSummary(
            name=name,
            count=len(values),
            average_ms=round(sum(values) / len(values), 1),
            max_ms=round(max(values), 1),
            last_ms=round(values[-1], 1),
        )

    def record_hidden_skip(self, page_name: str) -> None:
        self._hidden_skips[page_name] = self._hidden_skips.get(page_name, 0) + 1
        self._last_hidden_skip_at[page_name] = datetime.now(timezone.utc)

    def hidden_skip_counts(self) -> dict[str, int]:
        return dict(self._hidden_skips)

    def clear(self) -> None:
        self._timings.clear()
        self._hidden_skips.clear()
        self._last_hidden_skip_at.clear()


@dataclass(frozen=True)
class DiagnosticsSnapshot:
    active_page: str
    runtime_mode: str
    runtime_truth: str
    bridge_lifecycle: str
    telemetry_status: str
    telemetry_age_seconds: float | None
    process_hint: str
    hotas_discovery_status: str
    input_device_status: str
    output_status: str
    output_status_detail: str
    output_verified: bool
    full_live_runtime_ready: bool
    selected_axis: str
    workspace_path: str
    last_command_status: str
    last_command_request_id: str
    runtime_preflight_status: str
    diagnostics_collection_state: str
    timing_summaries: Mapping[str, PerfMetricSummary]
    hidden_page_skips: Mapping[str, int]
    physical_input_backend: str = "Unavailable"
    physical_input_source: str = "Simulation"
    supported_hotas: str = "Missing"
    selected_input_device: str = "None"
    input_sampling: str = "Not active"
    physical_input_selection_status: str = "backend_unavailable"
    physical_input_read_only: bool = True
    physical_input_simulation_fallback_state: str = "Simulation fallback active"
    physical_input_last_sample: str = "Unavailable"
    physical_input_sample_source: str = "unavailable"
    physical_input_sample_counts: str = "0 axes / 0 buttons / 0 hats"
    physical_input_sampling_warnings: str = "None"
    physical_input_sampling_errors: str = "None"
    virtual_output_backend: str = "Missing virtual output backend"
    virtual_output_backend_kind: str = "missing"
    virtual_output_backend_status: str = "backend_missing"
    vjoy_dependency_status: str = "Unknown"
    vjoy_device_status: str = "Unknown"
    selected_output_device: str = "None"
    output_device_status: str = "No virtual output device selected"
    output_write_status: str = "Not active"
    output_verification_status: str = "not_attempted"
    output_verification_source: str = "not attempted"
    fake_output_verified: bool = False
    real_output_verified: bool = False
    last_verification_timestamp: str = "Unavailable"
    last_verification_error: str = "None"
    last_verification_warnings: str = "None"
    output_loop_state: str = "disabled"
    output_loop_write_rate: str = "Unavailable"
    output_loop_write_count: int = 0
    output_loop_failure_count: int = 0
    output_loop_last_write: str = "Unavailable"
    output_loop_last_result: str = "Unavailable"
    output_loop_last_error: str = "None"
    output_loop_neutral_restore_status: str = "not_attempted"
    output_loop_safety_stop_reason: str = "None"
    runtime_frame_status: str = "unavailable"
    runtime_frame_sequence: str = "Unavailable"
    runtime_frame_source: str = "unavailable"
    runtime_frame_pipeline_status: str = "unavailable"
    runtime_frame_output_intent_ready: bool = False
    runtime_frame_output_backend: str = "Unavailable"
    runtime_frame_output_loop_state: str = "disabled"
    runtime_frame_last_output_write_status: str = "Not active"
    runtime_frame_output_verified: bool = False
    runtime_frame_full_live_runtime_ready: bool = False
    runtime_frame_truth: str = "unavailable"
    runtime_frame_blocked_reason: str = ""
    runtime_frame_input_proof: str = "unavailable"
    runtime_frame_pipeline_proof: str = "unavailable"
    runtime_frame_output_proof: str = "unavailable"
    runtime_frame_full_live_gate: str = "unavailable"
    runtime_frame_ready_state: str = "unavailable"
    runtime_frame_telemetry_proof: str = "unavailable"
    runtime_frame_safety_proof: str = "unavailable"
    runtime_frame_fake_or_real_path: str = "unavailable"
    runtime_frame_readiness_evaluated_at: str = "Unavailable"
    runtime_frame_candidate: str = "unavailable"
    runtime_frame_proof_summary: str = "unavailable"
    runtime_frame_input_verified_for_runtime: bool = False
    runtime_frame_output_verified_for_runtime: bool = False
    runtime_frame_output_loop_enabled: bool = False
    runtime_frame_output_loop_running: bool = False
    runtime_frame_output_loop_safety_stopped: bool = False
    runtime_frame_pipeline_ready: bool = False
    runtime_frame_warnings: str = "None"
    runtime_frame_errors: str = "None"
    manual_bridge_launch_command: str = DEFAULT_MANUAL_BRIDGE_COMMAND


def build_diagnostics_snapshot(
    *,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    workspace_path: str | Path,
    telemetry_status: str,
    telemetry_age_seconds: float | None,
    process_hint: str,
    bridge_lifecycle: str,
    hotas_discovery_status: str,
    last_command_status: str,
    last_command_request_id: str,
    collector: DiagnosticsCollector,
    physical_input: PhysicalInputDiagnostics | None = None,
    virtual_output: VirtualOutputDiagnostics | None = None,
    virtual_output_loop: VirtualOutputLoopSnapshot | None = None,
    runtime_frame: RuntimeFrameTelemetryPayload | None = None,
) -> DiagnosticsSnapshot:
    physical_input = physical_input or PhysicalInputDiagnostics(
        physical_input_backend="Unavailable",
        input_source="Simulation",
        supported_hotas="Missing",
        selected_input_device="None",
        input_sampling="Not active",
        selection_status="backend_unavailable",
        physical_input_read_only=True,
        simulation_fallback_state="Simulation fallback active",
    )
    virtual_output = virtual_output or build_virtual_output_diagnostics()
    virtual_output_loop = virtual_output_loop or _default_output_loop_snapshot(virtual_output)
    runtime_frame_fields = _runtime_frame_fields(runtime_frame)
    output_verified = bool(runtime_status.live_output_writes_verified or virtual_output.output_verified)
    full_ready = runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and output_verified
    return DiagnosticsSnapshot(
        active_page=state.active_page_id,
        runtime_mode=runtime_status.mode.value,
        runtime_truth=runtime_status.truth.value,
        bridge_lifecycle=bridge_lifecycle,
        telemetry_status=telemetry_status,
        telemetry_age_seconds=telemetry_age_seconds,
        process_hint=process_hint,
        hotas_discovery_status=hotas_discovery_status,
        input_device_status=runtime_status.input.status.value,
        output_status=runtime_status.output.status.value,
        output_status_detail=_output_detail(runtime_status),
        output_verified=output_verified,
        full_live_runtime_ready=full_ready,
        selected_axis=state.selected_axis,
        workspace_path=str(workspace_path),
        last_command_status=last_command_status,
        last_command_request_id=last_command_request_id,
        runtime_preflight_status=_preflight_summary(runtime_status),
        diagnostics_collection_state="Collecting" if collector.collect_live_timings else "Paused",
        timing_summaries={
            "page_switch": collector.summary("page_switch"),
            "heartbeat": collector.summary("heartbeat"),
            "graph": collector.summary("graph"),
            "startup": collector.summary("startup"),
        },
        hidden_page_skips=collector.hidden_skip_counts(),
        physical_input_backend=physical_input.physical_input_backend,
        physical_input_source=physical_input.input_source,
        supported_hotas=physical_input.supported_hotas,
        selected_input_device=physical_input.selected_input_device,
        input_sampling=physical_input.input_sampling,
        physical_input_selection_status=physical_input.selection_status,
        physical_input_read_only=physical_input.physical_input_read_only,
        physical_input_simulation_fallback_state=physical_input.simulation_fallback_state,
        physical_input_last_sample=physical_input.last_sample,
        physical_input_sample_source=physical_input.sample_source,
        physical_input_sample_counts=physical_input.sample_counts,
        physical_input_sampling_warnings=physical_input.sampling_warnings,
        physical_input_sampling_errors=physical_input.sampling_errors,
        virtual_output_backend=virtual_output.virtual_output_backend,
        virtual_output_backend_kind=virtual_output.virtual_output_backend_kind,
        virtual_output_backend_status=virtual_output.virtual_output_backend_status,
        vjoy_dependency_status=virtual_output.vjoy_dependency_status,
        vjoy_device_status=virtual_output.vjoy_device_status,
        selected_output_device=virtual_output.selected_output_device,
        output_device_status=virtual_output.output_device_status,
        output_write_status=virtual_output.output_write_status,
        output_verification_status=virtual_output.output_verification_status,
        output_verification_source=virtual_output.output_verification_source,
        fake_output_verified=virtual_output.fake_output_verified,
        real_output_verified=virtual_output.real_output_verified,
        last_verification_timestamp=virtual_output.last_verification_timestamp,
        last_verification_error=virtual_output.last_verification_error,
        last_verification_warnings=virtual_output.last_verification_warnings,
        output_loop_state=virtual_output_loop.state.value,
        output_loop_write_rate=f"{virtual_output_loop.write_rate_hz:.1f} hz",
        output_loop_write_count=virtual_output_loop.write_count,
        output_loop_failure_count=virtual_output_loop.failure_count,
        output_loop_last_write=virtual_output_loop.last_write_timestamp,
        output_loop_last_result=virtual_output_loop.last_write_result,
        output_loop_last_error=virtual_output_loop.last_error,
        output_loop_neutral_restore_status=virtual_output_loop.neutral_restore_status,
        output_loop_safety_stop_reason=virtual_output_loop.safety_stop_reason,
        **runtime_frame_fields,
    )


def format_metric_summary(summary: PerfMetricSummary) -> str:
    if not summary.available:
        return f"{summary.name}: unavailable"
    return f"count {summary.count} | avg {summary.average_ms:.1f} ms | max {summary.max_ms:.1f} ms"


def build_diagnostics_text(snapshot: DiagnosticsSnapshot) -> str:
    lines = [
        "HelmForge - HOTAS Control Panel V3",
        f"Active page: {snapshot.active_page}",
        f"Runtime truth: {snapshot.runtime_truth}",
        f"Bridge lifecycle: {snapshot.bridge_lifecycle}",
        f"Bridge telemetry status: {snapshot.telemetry_status}",
        f"Telemetry age: {_age_text(snapshot.telemetry_age_seconds)}",
        f"HOTAS discovery: {snapshot.hotas_discovery_status}",
        f"Input source: {snapshot.physical_input_source}",
        f"Physical input backend: {snapshot.physical_input_backend}",
        f"Physical input read-only: {str(snapshot.physical_input_read_only).lower()}",
        f"Simulation fallback: {snapshot.physical_input_simulation_fallback_state}",
        f"Supported HOTAS: {snapshot.supported_hotas}",
        f"Selected input device: {snapshot.selected_input_device}",
        f"Input sampling: {snapshot.input_sampling}",
        f"Last sample: {snapshot.physical_input_last_sample}",
        f"Sample source: {snapshot.physical_input_sample_source}",
        f"Axis/button/hat counts: {snapshot.physical_input_sample_counts}",
        f"Sampling warnings: {snapshot.physical_input_sampling_warnings}",
        f"Sampling errors: {snapshot.physical_input_sampling_errors}",
        f"Input device status: {snapshot.input_device_status}",
        f"Output/vJoy status: {snapshot.output_status}",
        f"Virtual output backend: {snapshot.virtual_output_backend}",
        f"Virtual output backend kind: {snapshot.virtual_output_backend_kind}",
        f"Virtual output backend status: {snapshot.virtual_output_backend_status}",
        f"vJoy dependency: {snapshot.vjoy_dependency_status}",
        f"vJoy device: {snapshot.vjoy_device_status}",
        f"Selected output device: {snapshot.selected_output_device}",
        f"Output device status: {snapshot.output_device_status}",
        f"Output write status: {snapshot.output_write_status}",
        f"Output verification status: {snapshot.output_verification_status}",
        f"Output verification source: {snapshot.output_verification_source}",
        f"Fake output verified: {str(snapshot.fake_output_verified).lower()}",
        f"Real output verified: {str(snapshot.real_output_verified).lower()}",
        f"Last verification timestamp: {snapshot.last_verification_timestamp}",
        f"Last verification error: {snapshot.last_verification_error}",
        f"Last verification warnings: {snapshot.last_verification_warnings}",
        f"Output loop: {snapshot.output_loop_state}",
        f"Output loop write rate: {snapshot.output_loop_write_rate}",
        f"Output loop write count: {snapshot.output_loop_write_count}",
        f"Output loop failure count: {snapshot.output_loop_failure_count}",
        f"Last output write: {snapshot.output_loop_last_write}",
        f"Last output write result: {snapshot.output_loop_last_result}",
        f"Last output error: {snapshot.output_loop_last_error}",
        f"Neutral restore status: {snapshot.output_loop_neutral_restore_status}",
        f"Output loop safety stop: {snapshot.output_loop_safety_stop_reason}",
        f"Runtime frame: {snapshot.runtime_frame_status}",
        f"Runtime frame sequence: {snapshot.runtime_frame_sequence}",
        f"Runtime frame source: {snapshot.runtime_frame_source}",
        f"Runtime frame pipeline status: {snapshot.runtime_frame_pipeline_status}",
        f"Output intent ready: {str(snapshot.runtime_frame_output_intent_ready).lower()}",
        f"Runtime frame output backend: {snapshot.runtime_frame_output_backend}",
        f"Runtime frame output loop state: {snapshot.runtime_frame_output_loop_state}",
        f"Runtime frame last output write: {snapshot.runtime_frame_last_output_write_status}",
        f"Runtime frame output verified: {str(snapshot.runtime_frame_output_verified).lower()}",
        f"Runtime frame Full Live Runtime Ready: {str(snapshot.runtime_frame_full_live_runtime_ready).lower()}",
        f"Runtime frame truth: {snapshot.runtime_frame_truth}",
        f"Runtime frame blocked reason: {snapshot.runtime_frame_blocked_reason or 'None'}",
        f"Input proof: {snapshot.runtime_frame_input_proof}",
        f"Pipeline proof: {snapshot.runtime_frame_pipeline_proof}",
        f"Output proof: {snapshot.runtime_frame_output_proof}",
        f"Full Live Runtime Ready gate: {snapshot.runtime_frame_full_live_gate}",
        f"Ready state: {snapshot.runtime_frame_ready_state}",
        f"Telemetry proof: {snapshot.runtime_frame_telemetry_proof}",
        f"Safety proof: {snapshot.runtime_frame_safety_proof}",
        f"Fake/real path: {snapshot.runtime_frame_fake_or_real_path}",
        f"Readiness evaluated: {snapshot.runtime_frame_readiness_evaluated_at}",
        f"Runtime candidate: {snapshot.runtime_frame_candidate}",
        f"Proof summary: {snapshot.runtime_frame_proof_summary}",
        f"Input verified for runtime: {str(snapshot.runtime_frame_input_verified_for_runtime).lower()}",
        f"Output verified for runtime: {str(snapshot.runtime_frame_output_verified_for_runtime).lower()}",
        f"Output loop enabled: {str(snapshot.runtime_frame_output_loop_enabled).lower()}",
        f"Output loop running: {str(snapshot.runtime_frame_output_loop_running).lower()}",
        f"Output loop safety stopped: {str(snapshot.runtime_frame_output_loop_safety_stopped).lower()}",
        f"Pipeline ready: {str(snapshot.runtime_frame_pipeline_ready).lower()}",
        f"Runtime frame warnings: {snapshot.runtime_frame_warnings}",
        f"Runtime frame errors: {snapshot.runtime_frame_errors}",
        f"Output verified: {str(snapshot.output_verified).lower()}",
        f"Full Live Runtime Ready: {str(snapshot.full_live_runtime_ready).lower()}",
        f"Process hint: {snapshot.process_hint}",
        f"Last command status: {snapshot.last_command_status}",
        f"Last command request_id: {snapshot.last_command_request_id}",
        f"Selected axis: {snapshot.selected_axis}",
        f"Workspace/source file: {snapshot.workspace_path}",
        f"Runtime setup/preflight status: {snapshot.runtime_preflight_status}",
        f"Diagnostics collection state: {snapshot.diagnostics_collection_state}",
    ]
    for name in ("page_switch", "heartbeat", "graph", "startup"):
        summary = snapshot.timing_summaries.get(name, PerfMetricSummary(name=name))
        lines.append(f"{name}: {format_metric_summary(summary)}")
    for page in ("Live Monitor", "Effective Response Stack", "Flight Recorder"):
        if page == "Flight Recorder":
            lines.append("Flight Recorder hidden-page skips: Not implemented yet")
        else:
            value = snapshot.hidden_page_skips.get(page)
            lines.append(f"{page} hidden-page skips: {value if value is not None else 'Unavailable'}")
    lines.append("Telemetry remains the truth surface.")
    lines.append("Process presence is a hint only.")
    lines.append(f"Manual Bridge launch: {snapshot.manual_bridge_launch_command}")
    return "\n".join(lines)


def _age_text(age_seconds: float | None) -> str:
    if age_seconds is None:
        return "Unavailable"
    return f"{age_seconds:.1f}s"


def _output_detail(runtime_status: RuntimePreflightStatus) -> str:
    backend = runtime_status.detected_output_backend_name or runtime_status.output.backend_name or "vJoy"
    verified = runtime_status.live_output_writes_verified
    if verified:
        return f"{backend} detected; output writes verified"
    return f"{backend} detected; output writes unverified"


def _preflight_summary(runtime_status: RuntimePreflightStatus) -> str:
    return (
        f"Input {runtime_status.input.status.value}; "
        f"output {runtime_status.output.status.value}; "
        f"truth {runtime_status.truth.value}; "
        f"output_verified {str(runtime_status.live_output_writes_verified).lower()}"
    )


def _default_output_loop_snapshot(virtual_output: VirtualOutputDiagnostics) -> VirtualOutputLoopSnapshot:
    return VirtualOutputLoopSnapshot(
        state=VirtualOutputWriteLoopState.DISABLED,
        enabled=False,
        backend_name=virtual_output.virtual_output_backend,
        selected_output_device=virtual_output.selected_output_device,
        verification_status=virtual_output.output_verification_status,
        output_write_status=virtual_output.output_write_status,
        write_rate_hz=30.0,
    )


def _runtime_frame_fields(runtime_frame: RuntimeFrameTelemetryPayload | None) -> dict[str, object]:
    if runtime_frame is None:
        return {}
    status = "available" if runtime_frame.available else runtime_frame.parse_status or "unavailable"
    return {
        "runtime_frame_status": status,
        "runtime_frame_sequence": str(runtime_frame.sequence) if runtime_frame.sequence is not None else "Unavailable",
        "runtime_frame_source": runtime_frame.input_source,
        "runtime_frame_pipeline_status": runtime_frame.pipeline_status,
        "runtime_frame_output_intent_ready": runtime_frame.output_intent_ready,
        "runtime_frame_output_backend": runtime_frame.output_backend,
        "runtime_frame_output_loop_state": runtime_frame.output_loop_state,
        "runtime_frame_last_output_write_status": runtime_frame.last_output_write_status,
        "runtime_frame_output_verified": runtime_frame.output_verified,
        "runtime_frame_full_live_runtime_ready": runtime_frame.full_live_runtime_ready,
        "runtime_frame_truth": runtime_frame.runtime_truth,
        "runtime_frame_blocked_reason": runtime_frame.blocked_reason,
        "runtime_frame_input_proof": runtime_frame.input_proof,
        "runtime_frame_pipeline_proof": runtime_frame.pipeline_proof,
        "runtime_frame_output_proof": runtime_frame.output_proof,
        "runtime_frame_full_live_gate": _runtime_frame_full_live_gate(runtime_frame),
        "runtime_frame_ready_state": runtime_frame.ready_state,
        "runtime_frame_telemetry_proof": runtime_frame.telemetry_proof,
        "runtime_frame_safety_proof": runtime_frame.safety_proof,
        "runtime_frame_fake_or_real_path": runtime_frame.fake_or_real_path,
        "runtime_frame_readiness_evaluated_at": runtime_frame.evaluated_at.isoformat() if runtime_frame.evaluated_at else "Unavailable",
        "runtime_frame_candidate": _runtime_frame_candidate(runtime_frame),
        "runtime_frame_proof_summary": runtime_frame.proof_summary or "unavailable",
        "runtime_frame_input_verified_for_runtime": runtime_frame.input_verified_for_runtime,
        "runtime_frame_output_verified_for_runtime": runtime_frame.output_verified_for_runtime,
        "runtime_frame_output_loop_enabled": runtime_frame.output_loop_enabled,
        "runtime_frame_output_loop_running": runtime_frame.output_loop_running,
        "runtime_frame_output_loop_safety_stopped": runtime_frame.output_loop_safety_stopped,
        "runtime_frame_pipeline_ready": runtime_frame.pipeline_ready,
        "runtime_frame_warnings": _joined(runtime_frame.warnings),
        "runtime_frame_errors": _joined(runtime_frame.errors),
    }


def _runtime_frame_candidate(runtime_frame: RuntimeFrameTelemetryPayload) -> str:
    if runtime_frame.full_live_runtime_ready:
        return "ready - full gate open"
    if runtime_frame.ready_state == "fake_test":
        return "fake/test only - not real readiness"
    if runtime_frame.verified_runtime_candidate:
        return "candidate - final gate proof incomplete"
    reason = runtime_frame.blocked_reason or "proof incomplete"
    return f"blocked - {reason}"


def _runtime_frame_full_live_gate(runtime_frame: RuntimeFrameTelemetryPayload) -> str:
    if runtime_frame.full_live_runtime_ready:
        return "ready"
    return runtime_frame.ready_state or "blocked"


def _joined(values: tuple[str, ...]) -> str:
    return ", ".join(value for value in values if value) or "None"
