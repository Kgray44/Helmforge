from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from shared_core.models.runtime import RuntimePreflightStatus, RuntimeTruth
from v3_app.services.app_state import AppState


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
) -> DiagnosticsSnapshot:
    output_verified = bool(runtime_status.live_output_writes_verified)
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
        f"Input device status: {snapshot.input_device_status}",
        f"Output/vJoy status: {snapshot.output_status}",
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
