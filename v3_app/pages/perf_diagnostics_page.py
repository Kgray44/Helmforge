from __future__ import annotations

from pathlib import Path
from typing import Mapping

from PySide6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.hotas_input import (
    PhysicalInputBackend,
    PhysicalInputSnapshot,
    build_default_physical_input_backend,
    build_physical_input_diagnostics,
)
from shared_core.runtime.vjoy_output import (
    VirtualOutputBackend,
    VirtualOutputLoopSnapshot,
    VirtualOutputVerificationResult,
    VirtualOutputWriteLoop,
    build_virtual_output_diagnostics,
)
from v3_app.pages.page_helpers import card, card_header, card_layout, page_intro
from v3_app.services.app_state import AppState, RuntimeUiState
from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryReadResult
from v3_app.services.perf_diagnostics import (
    DEFAULT_MANUAL_BRIDGE_COMMAND,
    DiagnosticsCollector,
    DiagnosticsSnapshot,
    PerfMetricSummary,
    build_diagnostics_snapshot,
    build_diagnostics_text,
    format_metric_summary,
)
from v3_app.ui.status_chips import action_button, status_chip


class PerfDiagnosticsPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        workspace_path: str | Path | None = None,
        telemetry_client: BridgeTelemetryClient | None = None,
        diagnostics_collector: DiagnosticsCollector | None = None,
        physical_input_backend: PhysicalInputBackend | None = None,
        selected_physical_input_device_id: str | None = None,
        physical_input_snapshot: PhysicalInputSnapshot | None = None,
        virtual_output_backend: VirtualOutputBackend | None = None,
        virtual_output_verification: VirtualOutputVerificationResult | None = None,
        virtual_output_loop: VirtualOutputWriteLoop | VirtualOutputLoopSnapshot | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("perfDiagnosticsPage")
        self._state = state
        self._workspace = workspace
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._workspace_path = Path(workspace_path or state.source_config)
        self._telemetry_client = telemetry_client or BridgeTelemetryClient()
        self._collector = diagnostics_collector or DiagnosticsCollector()
        self._physical_input_backend = physical_input_backend or build_default_physical_input_backend()
        self._selected_physical_input_device_id = selected_physical_input_device_id
        self._physical_input_snapshot = physical_input_snapshot
        self._virtual_output_backend = virtual_output_backend
        self._virtual_output_verification = virtual_output_verification
        self._virtual_output_loop = virtual_output_loop
        self._bridge_result: BridgeTelemetryReadResult | None = None
        self._last_preflight_message = "Runtime preflight has not been refreshed from this page yet."
        self._copy_text = ""
        self._rows: dict[str, QLabel] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)
        root.addWidget(
            page_intro(
                "Perf / Diagnostics",
                "Inspect app timing, runtime truth, Bridge telemetry, and diagnostic collection without changing runtime authority.",
                "Diagnostics are observational. Telemetry remains the truth surface and output verification stays false until a future verification phase proves writes.",
            )
        )

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        grid.addWidget(self._runtime_truth_card(), 0, 0)
        grid.addWidget(self._bridge_card(), 0, 1)
        grid.addWidget(self._workspace_card(), 1, 0)
        grid.addWidget(self._timing_card(), 1, 1)
        grid.addWidget(self._hidden_skips_card(), 2, 0)
        grid.addWidget(self._commands_card(), 2, 1)
        grid.addWidget(self._physical_input_card(), 3, 0, 1, 2)
        root.addLayout(grid)
        root.addWidget(self._actions_card())
        root.addStretch(1)

        self.refresh_diagnostics()

    def refresh_diagnostics(self) -> None:
        self._bridge_result = self._telemetry_client.read()
        snapshot = self._build_snapshot(self._bridge_result)
        self._apply_snapshot(snapshot)

    def _runtime_truth_card(self) -> QWidget:
        frame = card("perfRuntimeTruthCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Runtime Truth", "Current runtime state without live-output claims."))
        layout.addLayout(
            self._row_grid(
                (
                    "Runtime mode",
                    "Runtime truth",
                    "Input device status",
                    "Output/vJoy status",
                    "Virtual output backend",
                    "Virtual output backend kind",
                    "Virtual output backend status",
                    "vJoy dependency",
                    "vJoy device",
                    "Selected output device",
                    "Output device status",
                    "Output write status",
                    "Output verification status",
                    "Output verification source",
                    "Fake output verified",
                    "Real output verified",
                    "Last verification timestamp",
                    "Last verification error",
                    "Last verification warnings",
                    "Output loop",
                    "Output loop write rate",
                    "Output loop write count",
                    "Output loop failure count",
                    "Last output write",
                    "Last output write result",
                    "Last output error",
                    "Neutral restore status",
                    "Output loop safety stop",
                    "Runtime frame",
                    "Runtime frame sequence",
                    "Runtime frame source",
                    "Runtime frame pipeline status",
                    "Output intent ready",
                    "Runtime frame output backend",
                    "Runtime frame output loop state",
                    "Runtime frame last output write",
                    "Runtime frame output verified",
                    "Runtime frame Full Live Runtime Ready",
                    "Runtime frame truth",
                    "Runtime frame blocked reason",
                    "Input proof",
                    "Pipeline proof",
                    "Output proof",
                    "Runtime candidate",
                    "Proof summary",
                    "Input verified for runtime",
                    "Output verified for runtime",
                    "Output loop enabled",
                    "Output loop running",
                    "Output loop safety stopped",
                    "Pipeline ready",
                    "Runtime frame warnings",
                    "Runtime frame errors",
                    "Output verified",
                    "Full Live Runtime Ready",
                    "Runtime setup/preflight status",
                )
            )
        )
        layout.addWidget(
            _body(
                "Telemetry remains the truth surface. vJoy detected does not mean output verified. Output intent is not a write, "
                "fake/mock verification is not real vJoy verification, and the output loop requires explicit enable plus a verified backend. "
                "vJoy detected; output writes unverified until guarded output verification proves otherwise. "
                "Phase 16C runtime path proof separates input, pipeline, output verification, and output-loop state."
            )
        )
        return frame

    def _bridge_card(self) -> QWidget:
        frame = card("perfBridgeTelemetryCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Bridge / Telemetry", "Bridge presence and telemetry freshness are observational."))
        layout.addLayout(self._row_grid(("Bridge lifecycle", "Bridge telemetry status", "Telemetry age", "Process hint", "HOTAS discovery", "Last command status", "Last command request_id")))
        layout.addWidget(_body("Process presence is a hint only. HOTAS discovery is discovery-only. Manual Bridge launch remains text guidance only."))
        layout.addWidget(status_chip(f"Manual Bridge launch: {DEFAULT_MANUAL_BRIDGE_COMMAND}", tone="warning", object_name="manualBridgeLaunchGuidance"))
        return frame

    def _physical_input_card(self) -> QWidget:
        frame = card("perfPhysicalInputCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Physical Input", "Read-only Phase 14C device, source, and sample visibility truth."))
        layout.addLayout(
            self._row_grid(
                (
                    "Input source",
                    "Physical input backend",
                    "Physical input read-only",
                    "Supported HOTAS",
                    "Selected input device",
                    "Input sampling",
                    "Input selection status",
                    "Simulation fallback state",
                    "Last sample",
                    "Sample source",
                    "Axis/button/hat counts",
                    "Sampling warnings",
                    "Sampling errors",
                )
            )
        )
        layout.addWidget(
            _body(
                "Physical input sampling is read-only and on-demand. It does not write vJoy, verify output, or start the Bridge. "
                "vJoy writes are not implemented in Phase 14A, Phase 14B, or Phase 14C; output_verified remains false, and Full Live Runtime Ready remains false."
            )
        )
        return frame

    def _workspace_card(self) -> QWidget:
        frame = card("perfWorkspaceUiStateCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Workspace / UI State", "Current UI selection and workspace source."))
        layout.addLayout(self._row_grid(("Active page", "Selected axis", "Workspace/source file", "Diagnostics collection state")))
        layout.addWidget(_body("See Help / Docs -> Runtime Setup / vJoy Setup, Runtime Indicators, and Performance / Diagnostics for terminology."))
        return frame

    def _timing_card(self) -> QWidget:
        frame = card("perfTimingCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Performance Timings", "Lightweight UI/app timings. These are not hardware proof."))
        layout.addLayout(self._row_grid(("Page build/switch timings", "Heartbeat/update timing", "Graph draw/update timing", "Startup timing")))
        return frame

    def _hidden_skips_card(self) -> QWidget:
        frame = card("perfHiddenSkipsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Hidden Page Skips", "Visibility into expensive work skipped while pages are hidden."))
        layout.addLayout(self._row_grid(("Hidden page skips", "Live Monitor hidden-page skips", "Effective Response Stack hidden-page skips", "Flight Recorder hidden-page skips")))
        return frame

    def _commands_card(self) -> QWidget:
        frame = card("perfCommandsPreflightCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Commands / Preflight", "Safe checks only. No runtime activation or output verification."))
        layout.addWidget(
            _body(
                "Run Runtime Preflight is a safe check/request, not runtime activation. It refreshes the local runtime setup truth. "
                "It does not install drivers, launch installers, start the Bridge, poll live HOTAS input, write vJoy, or verify output."
            )
        )
        return frame

    def _actions_card(self) -> QWidget:
        frame = card("perfDiagnosticActionsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Diagnostic Actions", "Collect, clear, check, or prepare a text summary."))
        row = QHBoxLayout()
        row.setSpacing(10)
        self.collect_toggle = QCheckBox("Collect live timings")
        self.collect_toggle.setObjectName("collectLiveTimingsToggle")
        self.collect_toggle.setChecked(self._collector.collect_live_timings)
        self.collect_toggle.toggled.connect(self._set_collection_enabled)
        clear = action_button("Clear timings", object_name="clearTimingsButton")
        clear.clicked.connect(self.clear_timings)
        preflight = action_button("Run Runtime Preflight", object_name="runRuntimePreflightButton")
        preflight.clicked.connect(self.run_runtime_preflight)
        copy = action_button("Copy Diagnostics", object_name="copyDiagnosticsButton")
        copy.clicked.connect(self.prepare_copy_diagnostics)
        row.addWidget(self.collect_toggle)
        row.addWidget(clear)
        row.addWidget(preflight)
        row.addWidget(copy)
        row.addStretch(1)
        layout.addLayout(row)
        self.action_status = QLabel("Diagnostics collection is ready.")
        self.action_status.setObjectName("diagnosticsActionStatus")
        self.action_status.setWordWrap(True)
        self.copy_label = QLabel("")
        self.copy_label.setObjectName("diagnosticsCopyText")
        self.copy_label.setWordWrap(True)
        layout.addWidget(self.action_status)
        layout.addWidget(self.copy_label)
        return frame

    def _row_grid(self, labels: tuple[str, ...]) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(9)
        for row, label in enumerate(labels):
            key = QLabel(label)
            key.setObjectName("tableMutedText")
            value = QLabel("Unavailable")
            value.setObjectName("routeSummaryValue")
            value.setWordWrap(True)
            self._rows[label] = value
            grid.addWidget(key, row, 0)
            grid.addWidget(value, row, 1)
        return grid

    def _build_snapshot(self, bridge_result: BridgeTelemetryReadResult) -> DiagnosticsSnapshot:
        telemetry = bridge_result.telemetry
        last_command = telemetry.last_command if telemetry is not None else None
        discovery = telemetry.device_discovery if telemetry is not None else None
        return build_diagnostics_snapshot(
            state=self._state,
            runtime_status=self._runtime_status,
            workspace_path=self._workspace_path,
            telemetry_status=bridge_result.status.value,
            telemetry_age_seconds=bridge_result.age_seconds,
            process_hint="Unavailable",
            bridge_lifecycle=str(telemetry.lifecycle_state if telemetry is not None else "Simulated"),
            hotas_discovery_status=_discovery_status(discovery),
            last_command_status=_last_command_value(last_command, "status"),
            last_command_request_id=_last_command_value(last_command, "request_id"),
            collector=self._collector,
            physical_input=self._current_physical_input_diagnostics(),
            virtual_output=build_virtual_output_diagnostics(
                backend=self._virtual_output_backend,
                verification=self._virtual_output_verification,
            ),
            virtual_output_loop=self._current_virtual_output_loop_snapshot(),
            runtime_frame=telemetry.runtime_frame if telemetry is not None else None,
        )

    def _current_physical_input_diagnostics(self):
        return build_physical_input_diagnostics(
            self._physical_input_backend,
            selected_device_id=self._selected_physical_input_device_id,
            latest_snapshot=self._physical_input_snapshot,
        )

    def _current_virtual_output_loop_snapshot(self) -> VirtualOutputLoopSnapshot | None:
        if self._virtual_output_loop is None:
            return None
        if isinstance(self._virtual_output_loop, VirtualOutputLoopSnapshot):
            return self._virtual_output_loop
        return self._virtual_output_loop.snapshot()

    def _apply_snapshot(self, snapshot: DiagnosticsSnapshot) -> None:
        row_values = {
            "Runtime mode": snapshot.runtime_mode,
            "Runtime truth": snapshot.runtime_truth,
            "Input device status": snapshot.input_device_status,
            "Output/vJoy status": snapshot.output_status_detail,
            "Virtual output backend": snapshot.virtual_output_backend,
            "Virtual output backend kind": snapshot.virtual_output_backend_kind,
            "Virtual output backend status": snapshot.virtual_output_backend_status,
            "vJoy dependency": snapshot.vjoy_dependency_status,
            "vJoy device": snapshot.vjoy_device_status,
            "Selected output device": snapshot.selected_output_device,
            "Output device status": snapshot.output_device_status,
            "Output write status": snapshot.output_write_status,
            "Output verification status": snapshot.output_verification_status,
            "Output verification source": snapshot.output_verification_source,
            "Fake output verified": str(snapshot.fake_output_verified).lower(),
            "Real output verified": str(snapshot.real_output_verified).lower(),
            "Last verification timestamp": snapshot.last_verification_timestamp,
            "Last verification error": snapshot.last_verification_error,
            "Last verification warnings": snapshot.last_verification_warnings,
            "Output loop": snapshot.output_loop_state,
            "Output loop write rate": snapshot.output_loop_write_rate,
            "Output loop write count": str(snapshot.output_loop_write_count),
            "Output loop failure count": str(snapshot.output_loop_failure_count),
            "Last output write": snapshot.output_loop_last_write,
            "Last output write result": snapshot.output_loop_last_result,
            "Last output error": snapshot.output_loop_last_error,
            "Neutral restore status": snapshot.output_loop_neutral_restore_status,
            "Output loop safety stop": snapshot.output_loop_safety_stop_reason,
            "Runtime frame": snapshot.runtime_frame_status,
            "Runtime frame sequence": snapshot.runtime_frame_sequence,
            "Runtime frame source": snapshot.runtime_frame_source,
            "Runtime frame pipeline status": snapshot.runtime_frame_pipeline_status,
            "Output intent ready": str(snapshot.runtime_frame_output_intent_ready).lower(),
            "Runtime frame output backend": snapshot.runtime_frame_output_backend,
            "Runtime frame output loop state": snapshot.runtime_frame_output_loop_state,
            "Runtime frame last output write": snapshot.runtime_frame_last_output_write_status,
            "Runtime frame output verified": str(snapshot.runtime_frame_output_verified).lower(),
            "Runtime frame Full Live Runtime Ready": str(snapshot.runtime_frame_full_live_runtime_ready).lower(),
            "Runtime frame truth": snapshot.runtime_frame_truth,
            "Runtime frame blocked reason": snapshot.runtime_frame_blocked_reason or "None",
            "Input proof": snapshot.runtime_frame_input_proof,
            "Pipeline proof": snapshot.runtime_frame_pipeline_proof,
            "Output proof": snapshot.runtime_frame_output_proof,
            "Runtime candidate": snapshot.runtime_frame_candidate,
            "Proof summary": snapshot.runtime_frame_proof_summary,
            "Input verified for runtime": str(snapshot.runtime_frame_input_verified_for_runtime).lower(),
            "Output verified for runtime": str(snapshot.runtime_frame_output_verified_for_runtime).lower(),
            "Output loop enabled": str(snapshot.runtime_frame_output_loop_enabled).lower(),
            "Output loop running": str(snapshot.runtime_frame_output_loop_running).lower(),
            "Output loop safety stopped": str(snapshot.runtime_frame_output_loop_safety_stopped).lower(),
            "Pipeline ready": str(snapshot.runtime_frame_pipeline_ready).lower(),
            "Runtime frame warnings": snapshot.runtime_frame_warnings,
            "Runtime frame errors": snapshot.runtime_frame_errors,
            "Output verified": str(snapshot.output_verified).lower(),
            "Full Live Runtime Ready": str(snapshot.full_live_runtime_ready).lower(),
            "Runtime setup/preflight status": self._last_preflight_message,
            "Bridge lifecycle": snapshot.bridge_lifecycle,
            "Bridge telemetry status": snapshot.telemetry_status,
            "Telemetry age": _age_text(snapshot.telemetry_age_seconds),
            "Process hint": f"{snapshot.process_hint} - Process presence is a hint only",
            "HOTAS discovery": snapshot.hotas_discovery_status,
            "Input source": snapshot.physical_input_source,
            "Last command status": snapshot.last_command_status,
            "Last command request_id": snapshot.last_command_request_id,
            "Physical input backend": snapshot.physical_input_backend,
            "Physical input read-only": str(snapshot.physical_input_read_only).lower(),
            "Supported HOTAS": snapshot.supported_hotas,
            "Selected input device": snapshot.selected_input_device,
            "Input sampling": snapshot.input_sampling,
            "Input selection status": snapshot.physical_input_selection_status,
            "Simulation fallback state": snapshot.physical_input_simulation_fallback_state,
            "Last sample": snapshot.physical_input_last_sample,
            "Sample source": snapshot.physical_input_sample_source,
            "Axis/button/hat counts": snapshot.physical_input_sample_counts,
            "Sampling warnings": snapshot.physical_input_sampling_warnings,
            "Sampling errors": snapshot.physical_input_sampling_errors,
            "Active page": snapshot.active_page,
            "Selected axis": snapshot.selected_axis,
            "Workspace/source file": snapshot.workspace_path,
            "Diagnostics collection state": snapshot.diagnostics_collection_state,
            "Page build/switch timings": _page_switch_text(self._state.page_switch_timings_ms, snapshot),
            "Heartbeat/update timing": _timing_text("heartbeat", snapshot.timing_summaries),
            "Graph draw/update timing": _timing_text("graph", snapshot.timing_summaries),
            "Startup timing": _timing_text("startup", snapshot.timing_summaries),
            "Hidden page skips": "Counters are observational; unavailable means not instrumented yet.",
            "Live Monitor hidden-page skips": _hidden_skip_text("Live Monitor", snapshot.hidden_page_skips),
            "Effective Response Stack hidden-page skips": _hidden_skip_text("Effective Response Stack", snapshot.hidden_page_skips),
            "Flight Recorder hidden-page skips": "Not implemented yet",
        }
        for label, value in row_values.items():
            if label in self._rows:
                self._rows[label].setText(value)

    def _set_collection_enabled(self, enabled: bool) -> None:
        self._collector.collect_live_timings = bool(enabled)
        self.action_status.setText("Timing collection enabled." if enabled else "Timing collection paused.")
        self.refresh_diagnostics()

    def clear_timings(self) -> None:
        self._collector.clear()
        self.action_status.setText("Timings and hidden-page skip counters cleared.")
        self.refresh_diagnostics()

    def run_runtime_preflight(self) -> None:
        self._runtime_status = build_runtime_preflight_status()
        self._state.runtime = RuntimeUiState(
            truth=self._runtime_status.truth,
            input_status=self._runtime_status.input.status,
            output_status=self._runtime_status.output.status,
            output_verified=self._runtime_status.live_output_writes_verified,
            driver_detected=self._state.runtime.driver_detected,
            backend_name=self._runtime_status.detected_output_backend_name,
        )
        self._last_preflight_message = "Runtime preflight check refreshed. This check does not verify output writes."
        self.action_status.setText(self._last_preflight_message)
        self.refresh_diagnostics()

    def prepare_copy_diagnostics(self) -> str:
        snapshot = self._build_snapshot(self._bridge_result or self._telemetry_client.read())
        self._copy_text = build_diagnostics_text(snapshot)
        self.copy_label.setText(self._copy_text)
        self.action_status.setText("Copy Diagnostics text prepared; clipboard integration is not required for Phase 11B.")
        return self._copy_text


def _body(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("cardBody")
    label.setWordWrap(True)
    return label


def _discovery_status(discovery: Mapping[str, object] | None) -> str:
    if not isinstance(discovery, Mapping):
        return "no_supported_device"
    return str(discovery.get("status") or "no_supported_device")


def _last_command_value(command: Mapping[str, object] | None, field: str) -> str:
    if not isinstance(command, Mapping):
        return "none"
    return str(command.get(field) or "none")


def _age_text(age_seconds: float | None) -> str:
    if age_seconds is None:
        return "Unavailable"
    return f"{age_seconds:.1f}s"


def _page_switch_text(page_switch_timings_ms: dict[str, float], snapshot: DiagnosticsSnapshot) -> str:
    summary = snapshot.timing_summaries.get("page_switch", PerfMetricSummary(name="page_switch"))
    collector_text = f"page_switch: {format_metric_summary(summary)}"
    if not page_switch_timings_ms:
        return f"{collector_text}; shell switch timings unavailable"
    latest = ", ".join(f"{page}: {elapsed:.1f} ms" for page, elapsed in sorted(page_switch_timings_ms.items()))
    return f"{collector_text}; shell {latest}"


def _timing_text(name: str, summaries: Mapping[str, PerfMetricSummary]) -> str:
    return f"{name}: {format_metric_summary(summaries.get(name, PerfMetricSummary(name=name)))}"


def _hidden_skip_text(page_name: str, skips: Mapping[str, int]) -> str:
    value = skips.get(page_name)
    if value is None:
        return f"{page_name} hidden-page skips: Unavailable"
    return f"{page_name} hidden-page skips: {value}"
