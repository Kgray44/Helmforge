from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from datetime import datetime
from typing import Callable, Mapping

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from shared_core.math.pipeline import WorkspaceSignalPipeline
from shared_core.math.stack import ModeState
from shared_core.models.axes import AXIS_DISPLAY_NAMES
from shared_core.models.runtime import AXIS_NAMES, BUTTON_NAMES, RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.persistence.workspace_identity import build_workspace_identity
from shared_core.rules.evaluator import RuleStatus, status_counts
from shared_core.runtime.bridge_contracts import BridgeCommandType
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.hotas_input import MissingPhysicalInputBackend, PhysicalInputBackend, PhysicalInputSnapshot
from shared_core.runtime.manual_bench_validation import (
    ManualValidationStepStatus,
    create_manual_validation_session,
    export_manual_validation_session,
)
from shared_core.runtime.simulated_runtime import SimulatedRuntime
from shared_core.runtime.vjoy_output import (
    VirtualOutputBackend,
    VirtualOutputLoopSnapshot,
    VirtualOutputVerificationResult,
    VirtualOutputWriteLoop,
    build_virtual_output_diagnostics,
)
from v3_app.pages.graph_widgets import GraphPreview
from v3_app.pages.live_monitor_data import (
    BoundedTelemetryHistory,
    BridgeFrameIdentity,
    LiveTelemetryFrameTracker,
    OUTPUT_BUTTON_NAMES,
    TelemetrySample,
    bridge_telemetry_from_runtime_snapshot,
    extract_bridge_frame_identity,
    telemetry_sample_from_bridge_payload,
    telemetry_sample_from_runtime_snapshot,
)
from v3_app.overlay.config_dialog import LiveOverlayConfigDialog
from v3_app.overlay.live_overlay_window import LiveOverlayWindow
from v3_app.overlay.overlay_config import LiveOverlayConfig
from v3_app.overlay.telemetry_buffer import OverlayTelemetryBuffer, OverlayTelemetrySample
from v3_app.overlay.trace_builder import build_overlay_traces
from v3_app.pages.page_helpers import add_card_to_grid, card, card_header, card_layout, page_intro, signed, truth_notice
from v3_app.services.app_state import AppState
from v3_app.services.bridge_client import (
    DEFAULT_BRIDGE_TELEMETRY_PATH,
    BridgeTelemetryClient,
    BridgeTelemetryReadResult,
    BridgeTelemetryStatus,
    RuntimeFrameTelemetryPayload,
)
from v3_app.services.bridge_stream_client import BridgeTelemetryStreamClient
from v3_app.services.embedded_bridge_telemetry import read_embedded_bridge_telemetry
from v3_app.services.live_source_arbitration import LiveTelemetrySourceSelector
from v3_app.services.bridge_commands import (
    DEFAULT_BRIDGE_COMMAND_PATH,
    BridgeCommandClient,
    BridgeCommandWriteResult,
)
from v3_app.services.bridge_presence import (
    BridgeProcessPresenceProvider,
    UnavailableBridgeProcessPresenceProvider,
    build_live_monitor_diagnostic_rows,
    compose_bridge_lifecycle_diagnostics,
)
from v3_app.services.live_refresh import LIVE_REFRESH_INTERVAL_MS, LIVE_TRACE_HISTORY_SECONDS, LIVE_TRACE_SAMPLE_RATE_HZ
from v3_app.services.perf_diagnostics import DiagnosticsCollector
from v3_app.services.physical_input_ui import (
    buttons_from_physical_snapshot,
    build_input_source_status,
    hat_from_physical_snapshot,
    raw_axes_from_physical_snapshot,
)
from v3_app.ui.status_chips import action_button, status_chip


class LiveMonitorPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        telemetry_path: str | Path | None = None,
        command_path: str | Path | None = None,
        command_request_id_factory: Callable[[], str] | None = None,
        command_clock: Callable[[], datetime] | None = None,
        bridge_clock: Callable[[], datetime] | None = None,
        bridge_stale_after_seconds: float = 5.0,
        telemetry_stream_enabled: bool = False,
        telemetry_stream_host: str = "127.0.0.1",
        telemetry_stream_port: int = 8765,
        process_presence_provider: BridgeProcessPresenceProvider | None = None,
        physical_input_backend: PhysicalInputBackend | None = None,
        selected_physical_input_device_id: str | None = None,
        physical_input_snapshot: PhysicalInputSnapshot | None = None,
        physical_input_clock: Callable[[], datetime] | None = None,
        physical_sample_stale_after_seconds: float = 2.0,
        virtual_output_backend: VirtualOutputBackend | None = None,
        virtual_output_verification: VirtualOutputVerificationResult | None = None,
        virtual_output_loop: VirtualOutputWriteLoop | VirtualOutputLoopSnapshot | None = None,
        diagnostics_collector: DiagnosticsCollector | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("liveMonitorPage")
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._diagnostics_collector = diagnostics_collector
        self._simulation = SimulatedRuntime(deterministic=False, workspace=self._workspace)
        self._bridge_clock = bridge_clock
        self._bridge_client = BridgeTelemetryClient(
            telemetry_path=telemetry_path or DEFAULT_BRIDGE_TELEMETRY_PATH,
            stale_after_seconds=bridge_stale_after_seconds,
            clock=bridge_clock,
        )
        self._bridge_stream_client = (
            BridgeTelemetryStreamClient(
                host=telemetry_stream_host,
                port=telemetry_stream_port,
                stale_after_seconds=bridge_stale_after_seconds,
                clock=bridge_clock,
                connect_timeout_seconds=0.01,
                read_timeout_seconds=0.01,
            )
            if telemetry_stream_enabled
            else None
        )
        self._command_client = BridgeCommandClient(
            command_path=command_path or DEFAULT_BRIDGE_COMMAND_PATH,
            request_id_factory=command_request_id_factory,
            clock=command_clock,
        )
        self._process_presence_provider = process_presence_provider or UnavailableBridgeProcessPresenceProvider()
        self._physical_input_backend = physical_input_backend or MissingPhysicalInputBackend()
        self._selected_physical_input_device_id = selected_physical_input_device_id
        self._physical_input_snapshot = physical_input_snapshot
        self._physical_input_clock = physical_input_clock
        self._physical_sample_stale_after_seconds = physical_sample_stale_after_seconds
        self._physical_input_source_status = build_input_source_status(
            backend=self._physical_input_backend,
            selected_device_id=self._selected_physical_input_device_id,
            latest_snapshot=self._physical_input_snapshot,
            now=self._physical_input_now(),
            stale_after_seconds=self._physical_sample_stale_after_seconds,
        )
        self._virtual_output_diagnostics = build_virtual_output_diagnostics(
            backend=virtual_output_backend,
            verification=virtual_output_verification,
        )
        self._virtual_output_loop_snapshot = _virtual_output_loop_snapshot(virtual_output_loop)
        self._pipeline = WorkspaceSignalPipeline(self._workspace)
        self._pipeline_state = self._pipeline.initial_state()
        self.selected_axis = state.selected_axis if state.selected_axis in AXIS_DISPLAY_NAMES else "Roll"
        self.show_raw_and_output_together = True
        self.overlay_series_count = 0
        self.telemetry_source_label = "Simulation Fallback"
        self.telemetry_source_status = "Missing"
        self._live_source_selector = LiveTelemetrySourceSelector(clock=bridge_clock)
        self.latest_bridge_diagnostics = None
        self._bridge_frame_tracker = LiveTelemetryFrameTracker()
        self.last_bridge_frame_identity: BridgeFrameIdentity | None = None
        self.last_bridge_frame_received_at: datetime | None = None
        self.repeated_bridge_frame_count = 0
        self.new_bridge_frame_count = 0
        self.latest_bridge_frame_age_ms: float | None = None
        self.latest_bridge_tick_duration_ms: float | None = None
        self.latest_bridge_tick_count: int | None = None
        self.latest_bridge_source_cadence_hz: float | None = None
        self.latest_bridge_frame_state = "unavailable"
        self.latest_physical_input_sample_age_ms: float | None = None
        self.latest_physical_input_read_duration_ms: float | None = None
        self.latest_physical_input_sample_rate_hz: float | None = None
        self.latest_physical_input_backend_name = "unavailable"
        self.latest_physical_input_backend_kind = "unavailable"
        self.latest_physical_input_mapping_status = "unavailable"
        self._ui_workspace_identity = build_workspace_identity(
            self._workspace,
            path=self._state.source_config,
            status="ui_current" if self._state.saved else "ui_dirty",
        )
        self.latest_bridge_workspace: Mapping[str, object] | None = None
        self.latest_bridge_config_match: bool | None = None
        self.latest_bridge_config_mismatch_reason = "bridge_workspace_unavailable"
        self.latest_output_loop_runtime: Mapping[str, object] | None = None
        self.manual_validation_session = None
        self._last_manual_validation_telemetry: Mapping[str, object] | None = None
        self._manual_validation_artifact_root = Path(".artifacts") / "hf-lrdc" / "manual-validation"
        self.last_command_result: BridgeCommandWriteResult | None = None
        self.latest_command_request_id: str | None = None
        self.latest_command_name: str | None = None
        self._sample_index = 0
        self.history = BoundedTelemetryHistory.for_seconds(
            history_seconds=LIVE_TRACE_HISTORY_SECONDS,
            sample_rate_hz=LIVE_TRACE_SAMPLE_RATE_HZ,
        )
        self.axis_level_widgets: dict[str, QWidget] = {}
        self._axis_value_labels: dict[str, tuple[QLabel, QLabel]] = {}
        self._axis_bars: dict[str, tuple[QProgressBar, QProgressBar]] = {}
        self._hotas_buttons: dict[str, QLabel] = {}
        self._output_buttons: dict[str, QLabel] = {}
        self._diagnostic_row_labels: dict[str, QLabel] = {}
        self.overlay_config = LiveOverlayConfig.defaults()
        self.overlay_buffer = OverlayTelemetryBuffer(history_seconds=self.overlay_config.history_seconds)
        self.live_overlay_window: LiveOverlayWindow | None = None
        self._live_overlay_rows: dict[str, QLabel] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)

        root.addWidget(
            page_intro(
                "Live Monitor",
                "Watch raw HOTAS input, final processed output intent, buttons, hats, and axis levels in one dedicated live workspace.",
                "Current values are simulation-backed or read-only input samples until a future Bridge phase verifies real output writes.",
            )
        )
        root.addWidget(
            truth_notice(
                "Telemetry remains the truth surface. Bridge presence is a hint only, command files are requests, and output intent is not output write proof.",
                object_name="liveMonitorTruthNotice",
            )
        )
        root.addWidget(self._build_controls_card())
        root.addWidget(self._build_manual_validation_card())
        root.addWidget(self._build_raw_trace_card())
        root.addWidget(self._build_overlay_card())
        root.addWidget(self._build_live_monitor_action_block())

        status_grid = QGridLayout()
        status_grid.setHorizontalSpacing(18)
        status_grid.setVerticalSpacing(18)
        add_card_to_grid(status_grid, self._build_live_state_card(), 0, 0)
        add_card_to_grid(status_grid, self._build_buttons_hats_card(), 0, 1)
        root.addLayout(status_grid)

        root.addWidget(self._build_axis_levels_card())
        root.addWidget(self._build_live_overlay_card())
        root.addStretch(1)

        self._timer = QTimer(self)
        self._timer.setInterval(LIVE_REFRESH_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self.refresh_snapshot(force_new=True)

    def _build_controls_card(self) -> QWidget:
        frame = card("liveMonitorControlsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Monitor Controls", "Pick which axis to graph in detail while the full HOTAS stays visible below."))

        row = QHBoxLayout()
        row.setSpacing(10)
        axis_label = QLabel("Axis")
        axis_label.setObjectName("formLabel")
        self.axis_selector = QComboBox()
        self.axis_selector.setObjectName("liveMonitorAxisSelector")
        self.axis_selector.addItems(AXIS_DISPLAY_NAMES)
        self.axis_selector.setCurrentText(self.selected_axis)
        self.axis_selector.currentTextChanged.connect(self.set_selected_axis)

        self.overlay_checkbox = QCheckBox("Show raw and output together")
        self.overlay_checkbox.setObjectName("showRawOutputTogetherCheckbox")
        self.overlay_checkbox.setChecked(True)
        self.overlay_checkbox.toggled.connect(self.set_overlay_visible)

        self.runtime_chip = status_chip(
            self._state.runtime.header_truth_label,
            tone=self._state.runtime.tone,
            object_name="liveMonitorRuntimeTruthChip",
        )
        self.source_chip = status_chip(
            "Simulation Fallback",
            tone="warning",
            object_name="liveMonitorTelemetrySourceChip",
        )
        output_chip = status_chip(
            f"Output writes verified: {str(self._output_verified()).lower()}",
            tone="success" if self._output_verified() else "warning",
            object_name="liveMonitorOutputTruthChip",
        )
        virtual_output_chip = status_chip(
            f"Virtual output backend: {self._virtual_output_diagnostics.virtual_output_backend}",
            tone="warning",
            object_name="liveMonitorVirtualOutputBackendChip",
        )
        output_loop_chip = status_chip(
            f"Output loop: {_output_loop_state(self._virtual_output_loop_snapshot)}",
            tone="warning",
            object_name="liveMonitorOutputLoopChip",
        )
        row.addWidget(axis_label)
        row.addWidget(self.axis_selector)
        row.addWidget(self.overlay_checkbox)
        row.addStretch(1)
        row.addWidget(self.source_chip)
        row.addWidget(self.runtime_chip)
        row.addWidget(output_chip)
        row.addWidget(virtual_output_chip)
        row.addWidget(output_loop_chip)
        layout.addLayout(row)
        return frame

    def _build_live_overlay_card(self) -> QWidget:
        frame = card("liveOverlayCard")
        layout = card_layout(frame)
        layout.addWidget(
            card_header(
                "Live Overlay",
                "Launch the detached telemetry strip, choose a preset, and adjust advanced behavior only when needed.",
            )
        )
        rows = (
            "Preset",
            "Status",
            "Attached display",
            "Toggle",
            "Summary",
            "Runtime truth",
            "Output verified",
            "Full Live Runtime Ready",
            "Hotkey status",
            "Click-through",
            "Source truth",
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(9)
        for index, label in enumerate(rows):
            key = QLabel(label)
            key.setObjectName("tableMutedText")
            value = QLabel("")
            value.setObjectName("routeSummaryValue")
            value.setWordWrap(True)
            self._live_overlay_rows[label] = value
            grid.addWidget(key, index, 0)
            grid.addWidget(value, index, 1)
        layout.addLayout(grid)
        layout.addWidget(
            _body(
                "The detached overlay is app-owned and renders simulation or Bridge telemetry already available to the UI. "
                "Hotkey registration and click-through support are not active in this phase."
            )
        )
        button_row = QHBoxLayout()
        self.show_overlay_button = action_button("Show Overlay", object_name="showLiveOverlayButton")
        self.show_overlay_button.clicked.connect(self.toggle_live_overlay)
        configure = action_button("Configure", object_name="configureLiveOverlayButton")
        configure.clicked.connect(self.open_live_overlay_config_dialog)
        button_row.addWidget(self.show_overlay_button)
        button_row.addWidget(configure)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        self._update_live_overlay_card()
        return frame

    def _build_raw_trace_card(self) -> QWidget:
        frame = card("rawInputTraceCard")
        layout = card_layout(frame)
        self.raw_trace_title = QLabel(f"Raw Input Trace · {self.selected_axis}")
        self.raw_trace_title.setObjectName("rawTraceTitle")
        self.raw_trace_title.setProperty("cardTitle", True)
        layout.addWidget(self.raw_trace_title)
        layout.addWidget(_body("Recent raw HOTAS input for the selected axis."))
        self.raw_trace_graph = GraphPreview(object_name="liveRawTraceGraph")
        layout.addWidget(self.raw_trace_graph)
        self.history_seconds_label = _body("History window: 7 seconds")
        self.history_seconds_label.setObjectName("liveMonitorHistorySecondsLabel")
        layout.addWidget(self.history_seconds_label)
        layout.addWidget(_body("Newest samples are on the right edge. The UI keeps the runtime source read-only."))
        return frame

    def _build_overlay_card(self) -> QWidget:
        frame = card("rawFinalOverlayCard")
        layout = card_layout(frame)
        self.overlay_title = QLabel(f"Raw vs Final Overlay · {self.selected_axis}")
        self.overlay_title.setObjectName("overlayTraceTitle")
        self.overlay_title.setProperty("cardTitle", True)
        layout.addWidget(self.overlay_title)
        layout.addWidget(_body("Recent processed output leaving the bridge for the selected axis."))
        self.overlay_graph = GraphPreview(object_name="liveRawFinalOverlayGraph")
        layout.addWidget(self.overlay_graph)
        self.graph_cadence_label = _body("UI cadence: 60 Hz refresh target; telemetry cadence is Bridge-owned.")
        self.graph_cadence_label.setObjectName("liveMonitorGraphCadenceLabel")
        layout.addWidget(self.graph_cadence_label)
        layout.addWidget(_body("Raw and final output are overlaid for direct comparison. Output intent is not output write proof."))
        return frame

    def _build_live_state_card(self) -> QWidget:
        frame = card("liveMonitorCompactState")
        frame.setProperty("legacyObjectName", "liveStateCard")
        frame.setProperty("postRc4ePolish", True)
        layout = card_layout(frame)
        layout.addWidget(card_header("Live State", "Compact runtime truth, source, and proof posture."))
        compact_grid = QGridLayout()
        compact_grid.setHorizontalSpacing(14)
        compact_grid.setVerticalSpacing(8)
        self.compact_runtime_truth = QLabel("")
        self.compact_runtime_truth.setObjectName("liveMonitorCompactRuntimeTruth")
        self.compact_output_truth = QLabel("")
        self.compact_output_truth.setObjectName("liveMonitorCompactOutputTruth")
        self.compact_source_truth = QLabel("")
        self.compact_source_truth.setObjectName("liveMonitorCompactSourceTruth")
        for row, (label, widget) in enumerate(
            (
                ("Runtime truth", self.compact_runtime_truth),
                ("Output proof", self.compact_output_truth),
                ("Telemetry source", self.compact_source_truth),
            )
        ):
            key = QLabel(label)
            key.setObjectName("tableMutedText")
            widget.setObjectName(widget.objectName())
            widget.setWordWrap(True)
            compact_grid.addWidget(key, row, 0)
            compact_grid.addWidget(widget, row, 1)
        layout.addLayout(compact_grid)
        self.live_state_label = QLabel("")
        self.live_state_label.setObjectName("liveStateText")
        self.live_state_label.setWordWrap(True)
        self.live_state_label.setProperty("detailDensity", "diagnostic")
        layout.addWidget(self.live_state_label)
        self.bridge_health_label = QLabel("")
        self.bridge_health_label.setObjectName("bridgeHealthText")
        self.bridge_health_label.setWordWrap(True)
        layout.addWidget(self.bridge_health_label)
        self.diagnostic_grid = QGridLayout()
        self.diagnostic_grid.setObjectName("bridgeDiagnosticGrid")
        self.diagnostic_grid.setHorizontalSpacing(12)
        self.diagnostic_grid.setVerticalSpacing(10)
        layout.addLayout(self.diagnostic_grid)
        self.command_status_label = QLabel("Bridge commands are requests; fresh telemetry confirms later.")
        self.command_status_label.setObjectName("bridgeCommandStatusText")
        self.command_status_label.setWordWrap(True)
        layout.addWidget(self.command_status_label)
        return frame

    def _build_live_monitor_action_block(self) -> QWidget:
        frame = card("liveMonitorActionBlock")
        frame.setProperty("postRc4ePolish", True)
        layout = card_layout(frame)
        layout.addWidget(card_header("Bridge Request Actions", "Request files only; telemetry must confirm later."))
        command_grid = QGridLayout()
        command_grid.setHorizontalSpacing(10)
        command_grid.setVerticalSpacing(10)
        commands = (
            ("Refresh Bridge Status", "bridgeCommandStatusButton", BridgeCommandType.STATUS),
            ("Run Bridge Preflight", "bridgeCommandPreflightButton", BridgeCommandType.RUN_PREFLIGHT),
            ("Reload Bridge Config", "bridgeCommandReloadButton", BridgeCommandType.RELOAD_CONFIG),
            ("Switch to Simulation", "bridgeCommandSimulationButton", BridgeCommandType.SWITCH_TO_SIMULATION),
            ("Clear Bridge Error", "bridgeCommandClearErrorButton", BridgeCommandType.CLEAR_ERROR),
        )
        for index, (label, object_name, command) in enumerate(commands):
            button = action_button(label, object_name=object_name)
            button.clicked.connect(lambda _checked=False, cmd=command, title=label: self.request_bridge_command(cmd, title))
            command_grid.addWidget(button, index // 2, index % 2)
        layout.addLayout(command_grid)
        return frame

    def _build_manual_validation_card(self) -> QWidget:
        frame = card("manualBenchValidationCard")
        layout = card_layout(frame)
        title = QLabel("Manual Bench Validation")
        title.setObjectName("manualBenchValidationTitle")
        title.setProperty("cardTitle", True)
        layout.addWidget(title)
        helper = QLabel(
            "Guided operator checklist for real HOTAS/vJoy bench validation. "
            "Manual confirmation is evidence, not output-write proof."
        )
        helper.setObjectName("cardBody")
        helper.setWordWrap(True)
        layout.addWidget(helper)
        self.manual_validation_status_label = QLabel("Session: not started")
        self.manual_validation_status_label.setObjectName("manualBenchStatus")
        self.manual_validation_status_label.setWordWrap(True)
        self.manual_validation_current_step_label = QLabel("Current step: unavailable")
        self.manual_validation_current_step_label.setObjectName("manualBenchCurrentStep")
        self.manual_validation_current_step_label.setWordWrap(True)
        self.manual_validation_instruction_label = QLabel("Press Start Validation to begin.")
        self.manual_validation_instruction_label.setObjectName("manualBenchInstruction")
        self.manual_validation_instruction_label.setWordWrap(True)
        self.manual_validation_evidence_label = QLabel("Evidence: unavailable")
        self.manual_validation_evidence_label.setObjectName("manualBenchEvidence")
        self.manual_validation_evidence_label.setWordWrap(True)
        layout.addWidget(self.manual_validation_status_label)
        layout.addWidget(self.manual_validation_current_step_label)
        layout.addWidget(self.manual_validation_instruction_label)
        layout.addWidget(self.manual_validation_evidence_label)
        buttons = QHBoxLayout()
        start = action_button("Start Validation", object_name="manualBenchStartButton")
        start.clicked.connect(self.start_manual_validation)
        next_step = action_button("Next Step", object_name="manualBenchNextButton")
        next_step.clicked.connect(self.next_manual_validation_step)
        passed = action_button("Mark Passed", object_name="manualBenchPassedButton")
        passed.clicked.connect(lambda: self.mark_manual_validation_step(ManualValidationStepStatus.PASSED))
        failed = action_button("Mark Failed", object_name="manualBenchFailedButton")
        failed.clicked.connect(lambda: self.mark_manual_validation_step(ManualValidationStepStatus.FAILED))
        skipped = action_button("Skip", object_name="manualBenchSkipButton")
        skipped.clicked.connect(lambda: self.mark_manual_validation_step(ManualValidationStepStatus.SKIPPED))
        export = action_button("Export Report", object_name="manualBenchExportButton")
        export.clicked.connect(self.export_manual_validation_report)
        for button in (start, next_step, passed, failed, skipped, export):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return frame

    def _build_buttons_hats_card(self) -> QWidget:
        frame = card("buttonsHatsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Buttons / Hats", "Raw HOTAS buttons and mapped output activity."))
        chip_row = QHBoxLayout()
        self.hotas_hat_chip = status_chip("HOTAS Hat: Centered", tone="neutral", object_name="hotasHatStateChip")
        self.output_hat_chip = status_chip("Output Hat: Centered", tone="neutral", object_name="outputHatStateChip")
        chip_row.addWidget(self.hotas_hat_chip)
        chip_row.addWidget(self.output_hat_chip)
        chip_row.addStretch(1)
        layout.addLayout(chip_row)
        self.buttons_hats_label = QLabel("")
        self.buttons_hats_label.setObjectName("buttonsHatsText")
        self.buttons_hats_label.setWordWrap(True)
        layout.addWidget(self.buttons_hats_label)
        compact_button_grid = QGridLayout()
        compact_button_grid.setHorizontalSpacing(8)
        compact_button_grid.setVerticalSpacing(8)
        hotas = self._build_hotas_buttons_card()
        output = self._build_output_buttons_card()
        compact_button_grid.addWidget(hotas, 0, 0)
        compact_button_grid.addWidget(output, 0, 1)
        layout.addLayout(compact_button_grid)
        return frame

    def _build_axis_levels_card(self) -> QWidget:
        frame = card("liveMonitorAxisLevelsVertical")
        frame.setProperty("legacyObjectName", "axisLevelsCard")
        frame.setProperty("axisLevelLayout", "vertical-bars")
        layout = card_layout(frame)
        layout.addWidget(card_header("Axis Levels", "Raw and final values for every mapped axis. Blue is raw input, green is final output."))
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)
        for row, axis_name in enumerate(AXIS_NAMES):
            axis_row = QWidget()
            axis_row.setObjectName(f"axisLevelRow_{_key(axis_name)}")
            axis_layout = QGridLayout(axis_row)
            axis_layout.setContentsMargins(0, 0, 0, 0)
            axis_layout.setHorizontalSpacing(10)
            axis_layout.setVerticalSpacing(4)
            title = QLabel(axis_name)
            title.setObjectName(f"axisLevel_{_key(axis_name)}")
            raw_label = QLabel("R +0.00")
            raw_label.setObjectName(f"axisRawValue_{_key(axis_name)}")
            final_label = QLabel("F +0.00")
            final_label.setObjectName(f"axisFinalValue_{_key(axis_name)}")
            raw_bar = _level_bar("raw")
            final_bar = _level_bar("final")
            axis_layout.addWidget(title, 0, 0)
            axis_layout.addWidget(raw_bar, 0, 1)
            axis_layout.addWidget(raw_label, 0, 2)
            axis_layout.addWidget(final_bar, 1, 1)
            axis_layout.addWidget(final_label, 1, 2)
            self.axis_level_widgets[axis_name] = axis_row
            self._axis_value_labels[axis_name] = (raw_label, final_label)
            self._axis_bars[axis_name] = (raw_bar, final_bar)
            grid.addWidget(axis_row, 0, row)
        layout.addLayout(grid)
        return frame

    def _build_hotas_buttons_card(self) -> QWidget:
        frame = card("hotasButtonsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("HOTAS Buttons", "Physical input samples when available; simulation fallback remains safe."))
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for index, button_name in enumerate(BUTTON_NAMES):
            chip = status_chip(button_name, tone="neutral", object_name=f"hotasButton_{button_name}")
            self._hotas_buttons[button_name] = chip
            grid.addWidget(chip, index // 5, index % 5)
        layout.addLayout(grid)
        return frame

    def _build_output_buttons_card(self) -> QWidget:
        frame = card("mappedOutputButtonsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Mapped Output Buttons", "Mapped button states from the current workspace path; no vJoy writes are verified yet."))
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for index, button_name in enumerate(OUTPUT_BUTTON_NAMES):
            chip = status_chip(button_name.replace("Out", "Out "), tone="neutral", object_name=f"outputButton_{button_name}")
            self._output_buttons[button_name] = chip
            grid.addWidget(chip, index // 5, index % 5)
        layout.addLayout(grid)
        return frame

    def _tick(self) -> None:
        if self.should_skip_timer_refresh():
            self._record_hidden_skip()
            return
        started_at = time.perf_counter()
        self.refresh_snapshot(force_new=True)
        self._record_timing("heartbeat", started_at)

    def should_skip_timer_refresh(self) -> bool:
        return not self.isVisible()

    def _record_hidden_skip(self) -> None:
        if self._diagnostics_collector is not None:
            self._diagnostics_collector.record_hidden_skip("Live Monitor")

    def _record_timing(self, name: str, started_at: float) -> None:
        if self._diagnostics_collector is not None:
            self._diagnostics_collector.record_timing(name, (time.perf_counter() - started_at) * 1000.0)

    def set_selected_axis(self, axis_name: str) -> None:
        if axis_name not in AXIS_DISPLAY_NAMES:
            return
        self.selected_axis = axis_name
        self._state.selected_axis = axis_name
        self.raw_trace_title.setText(f"Raw Input Trace · {axis_name}")
        self.overlay_title.setText(f"Raw vs Final Overlay · {axis_name}")
        self._update_graphs()

    def set_overlay_visible(self, checked: bool) -> None:
        self.show_raw_and_output_together = bool(checked)
        self._update_graphs()

    def create_live_overlay_config_dialog(self) -> LiveOverlayConfigDialog:
        return LiveOverlayConfigDialog(
            config=self.overlay_config,
            on_apply=self.apply_live_overlay_config,
            parent=self,
        )

    def open_live_overlay_config_dialog(self) -> None:
        self.create_live_overlay_config_dialog().exec()

    def apply_live_overlay_config(self, config: LiveOverlayConfig) -> None:
        self.overlay_config = config
        self.overlay_buffer.history_seconds = config.history_seconds
        if self.live_overlay_window is not None:
            self.live_overlay_window.apply_config(config)
            self._sync_live_overlay_window()
        self._update_live_overlay_card()

    def toggle_live_overlay(self) -> None:
        if self.live_overlay_window is not None and self.live_overlay_window.is_overlay_active():
            self.hide_live_overlay()
        else:
            self.show_live_overlay()

    def show_live_overlay(self) -> None:
        window = self._ensure_live_overlay_window()
        self._sync_live_overlay_window()
        window.show_overlay()
        self._update_live_overlay_card()

    def hide_live_overlay(self) -> None:
        if self.live_overlay_window is not None:
            self.live_overlay_window.hide_overlay()
        self._update_live_overlay_card()

    def _ensure_live_overlay_window(self) -> LiveOverlayWindow:
        if self.live_overlay_window is None:
            self.live_overlay_window = LiveOverlayWindow(
                config=self.overlay_config,
                runtime_truth=self._runtime_status.truth.value,
                output_verified=self._runtime_status.live_output_writes_verified,
                full_live_runtime_ready=_full_live_runtime_ready(self._runtime_status),
                parent=self,
            )
            self.live_overlay_window.visibility_changed.connect(self._handle_live_overlay_visibility_changed)
        return self.live_overlay_window

    def _handle_live_overlay_visibility_changed(self, _visible: bool) -> None:
        self._update_live_overlay_card()

    def _sync_live_overlay_window(self) -> None:
        if self.live_overlay_window is None:
            return
        self.live_overlay_window.set_runtime_truth(
            runtime_truth=self._runtime_status.truth.value,
            output_verified=self._runtime_status.live_output_writes_verified,
            full_live_runtime_ready=_full_live_runtime_ready(self._runtime_status),
        )
        traces = build_overlay_traces(self.overlay_config, self.overlay_buffer.samples())
        self.live_overlay_window.set_trace_set(traces)

    def _update_live_overlay_card(self) -> None:
        config = self.overlay_config
        full_ready = _full_live_runtime_ready(self._runtime_status)
        overlay_active = self.live_overlay_window is not None and self.live_overlay_window.is_overlay_active()
        self.show_overlay_button.setText("Hide Overlay" if overlay_active else "Show Overlay")
        click_through = (
            self.live_overlay_window.click_through_status_text()
            if self.live_overlay_window is not None
            else "Not enabled - not verified"
        )
        row_values = {
            "Preset": config.preset,
            "Status": "Active" if overlay_active else "Inactive",
            "Attached display": config.display_label,
            "Toggle": config.toggle_hotkey,
            "Summary": _overlay_summary(config),
            "Runtime truth": self._runtime_status.truth.value,
            "Output verified": str(self._runtime_status.live_output_writes_verified).lower(),
            "Full Live Runtime Ready": str(full_ready).lower(),
            "Hotkey status": "Not registered",
            "Click-through": click_through,
            "Source truth": "Final output stream uses simulation or Bridge telemetry already available to the UI; no live hardware runtime is created.",
        }
        for label, value in row_values.items():
            if label in self._live_overlay_rows:
                self._live_overlay_rows[label].setText(value)

    def request_bridge_command(self, command: BridgeCommandType, label: str | None = None) -> BridgeCommandWriteResult:
        if command is BridgeCommandType.RELOAD_CONFIG:
            result = self._command_client.reload_config(
                config_path=self._state.source_config,
                expected_workspace_hash=self._ui_workspace_identity.workspace_hash,
                expected_workspace_revision=self._ui_workspace_identity.workspace_revision,
            )
        else:
            result = self._command_client.write_command(command)
        self.last_command_result = result
        if result.success:
            self.latest_command_request_id = result.request_id
            self.latest_command_name = result.command
            command_label = label or result.command or command.value
            self.command_status_label.setText(f"{command_label} command requested. Awaiting Bridge telemetry.")
        else:
            self.command_status_label.setText(result.message)
        return result

    def refresh_snapshot(self, *, force_new: bool = False) -> None:
        self._sample_index += 1
        self._refresh_physical_input_source_status()
        bridge_result = self._read_bridge_telemetry()
        append_history = True
        if bridge_result.status is BridgeTelemetryStatus.CONNECTED and bridge_result.telemetry is not None:
            sample = telemetry_sample_from_bridge_payload(bridge_result.telemetry, index=self._sample_index)
            telemetry = bridge_result.telemetry
            frame_identity = extract_bridge_frame_identity(telemetry)
            tracker_result = self._bridge_frame_tracker.observe(
                frame_identity,
                received_at=bridge_result.last_read_at,
            )
            append_history = tracker_result.is_new_frame
            self.last_bridge_frame_identity = frame_identity
            self.last_bridge_frame_received_at = self._bridge_frame_tracker.last_bridge_frame_received_at
            self.repeated_bridge_frame_count = tracker_result.repeated_frame_count
            self.new_bridge_frame_count = tracker_result.new_frame_count
            self.latest_bridge_source_cadence_hz = tracker_result.accepted_cadence_hz
            self.latest_bridge_frame_state = "new frame" if tracker_result.is_new_frame else "repeated frame"
            self._update_live_telemetry_truth_state(telemetry, bridge_result)
            self._update_manual_validation_from_telemetry(telemetry, bridge_result)
        else:
            snapshot = self._simulation.snapshot(self._runtime_status)
            sample = telemetry_sample_from_runtime_snapshot(snapshot, index=self._sample_index)
            telemetry = bridge_telemetry_from_runtime_snapshot(
                snapshot,
                active_profile=self._state.active_profile,
                rule_summary=self._rule_summary(snapshot.raw_axis_values),
            )
            self.latest_bridge_frame_state = bridge_result.status.value.lower()
            self._update_manual_validation_from_telemetry(telemetry, bridge_result)
        sample = self._physical_sample_override(sample)
        if append_history:
            self.history.append(sample)
            self._append_overlay_sample(sample)
        self._update_from_sample(sample, telemetry, bridge_result)
        self._update_graphs()
        self._sync_live_overlay_window()

    def _update_live_telemetry_truth_state(self, telemetry, bridge_result: BridgeTelemetryReadResult) -> None:
        timing = getattr(telemetry, "bridge_timing", None)
        fidelity = getattr(telemetry, "physical_input_fidelity", None)
        bridge_workspace = getattr(telemetry, "bridge_workspace", None)
        output_loop_runtime = getattr(telemetry, "output_loop_runtime", None)
        if isinstance(timing, Mapping):
            self.latest_bridge_tick_duration_ms = _optional_float(timing.get("last_tick_duration_ms"))
            self.latest_bridge_tick_count = _optional_int(timing.get("tick_count"))
        else:
            self.latest_bridge_tick_duration_ms = None
            self.latest_bridge_tick_count = None
        self.latest_bridge_frame_age_ms = None
        if bridge_result.age_seconds is not None:
            self.latest_bridge_frame_age_ms = bridge_result.age_seconds * 1000.0
        if isinstance(fidelity, Mapping):
            self.latest_physical_input_backend_name = str(fidelity.get("backend_name") or "unavailable")
            self.latest_physical_input_backend_kind = str(fidelity.get("backend_kind") or "unavailable")
            self.latest_physical_input_sample_age_ms = _optional_float(fidelity.get("sample_age_ms"))
            self.latest_physical_input_read_duration_ms = _optional_float(fidelity.get("read_duration_ms"))
            self.latest_physical_input_sample_rate_hz = _optional_float(fidelity.get("estimated_sample_rate_hz"))
            self.latest_physical_input_mapping_status = str(fidelity.get("mapping_status") or "unavailable")
        else:
            self.latest_physical_input_backend_name = "unavailable"
            self.latest_physical_input_backend_kind = "unavailable"
            self.latest_physical_input_sample_age_ms = None
            self.latest_physical_input_read_duration_ms = None
            self.latest_physical_input_sample_rate_hz = None
            self.latest_physical_input_mapping_status = "unavailable"
        if isinstance(bridge_workspace, Mapping):
            self.latest_bridge_workspace = bridge_workspace
            bridge_hash = str(bridge_workspace.get("workspace_hash") or "")
            self.latest_bridge_config_match = bool(bridge_hash) and bridge_hash == self._ui_workspace_identity.workspace_hash
            if self.latest_bridge_config_match:
                self.latest_bridge_config_mismatch_reason = ""
            elif bool(bridge_workspace.get("using_default_workspace", False)):
                self.latest_bridge_config_mismatch_reason = str(bridge_workspace.get("config_status") or "using_default_workspace")
            elif not self._state.saved:
                self.latest_bridge_config_mismatch_reason = "ui_has_unsaved_or_different_workspace"
            else:
                self.latest_bridge_config_mismatch_reason = "workspace_hash_mismatch"
        else:
            self.latest_bridge_workspace = None
            self.latest_bridge_config_match = None
            self.latest_bridge_config_mismatch_reason = "bridge_workspace_unavailable"
        self.latest_output_loop_runtime = output_loop_runtime if isinstance(output_loop_runtime, Mapping) else None

    def _read_bridge_telemetry(self) -> BridgeTelemetryReadResult:
        embedded_result = read_embedded_bridge_telemetry(stale_after_seconds=1.0, clock=self._bridge_clock)
        json_result = self._bridge_client.read()
        stream_result = self._bridge_stream_client.read_latest() if self._bridge_stream_client is not None else None
        selected = self._live_source_selector.select(
            embedded_result=embedded_result,
            stream_result=stream_result,
            json_result=replace(json_result, source_label="Bridge JSON Snapshot")
            if json_result.status is BridgeTelemetryStatus.CONNECTED and json_result.telemetry is not None
            else json_result,
        )
        if selected.source_label == "Bridge JSON Snapshot" and selected.telemetry is not None:
            return replace(selected, reason="Embedded Bridge/stream unavailable or stale; using fresh JSON snapshot.")
        return selected

    def _append_overlay_sample(self, sample) -> None:
        axes = sample.final_axes if self.overlay_config.source == "Final output" else sample.raw_axes
        self.overlay_buffer.append(
            OverlayTelemetrySample(
                timestamp=float(sample.index),
                axes=axes,
                source=self.overlay_config.source,
            )
        )

    def _rule_summary(self, raw_axes) -> object:
        result = self._pipeline.process(raw_axes, mode_state=ModeState(), state=self._pipeline_state)
        self._pipeline_state = result.state
        counts = status_counts(result.rule_evaluations)
        from shared_core.runtime.telemetry import RuleStateSummary

        return RuleStateSummary(
            active_count=counts["active"],
            blocked_count=counts["blocked"],
            disabled_count=counts["disabled"],
        )

    def _update_from_sample(self, sample, telemetry, bridge_result: BridgeTelemetryReadResult) -> None:
        for axis_name in AXIS_NAMES:
            raw_value = sample.raw_axes.get(axis_name, 0.0)
            final_value = sample.final_axes.get(axis_name, 0.0)
            raw_label, final_label = self._axis_value_labels[axis_name]
            raw_bar, final_bar = self._axis_bars[axis_name]
            raw_label.setText(f"R {signed(raw_value)}")
            final_label.setText(f"F {signed(final_value)}")
            raw_bar.setValue(_bar_value(raw_value))
            final_bar.setValue(_bar_value(final_value))

        for button_name, chip in self._hotas_buttons.items():
            _set_chip_state(chip, button_name, sample.buttons.get(button_name, False))
        for output_name, chip in self._output_buttons.items():
            _set_chip_state(chip, output_name.replace("Out", "Out "), sample.output_buttons.get(output_name, False))

        self.hotas_hat_chip.setText(f"HOTAS Hat: {sample.hat_state}")
        self.output_hat_chip.setText(f"Output Hat: {sample.output_hat_state}")

        self._update_source_status(bridge_result)
        rule_summary = telemetry.rule_summary
        if isinstance(rule_summary, dict):
            active_count = int(rule_summary.get("active_count", 0))
            blocked_count = int(rule_summary.get("blocked_count", 0))
            disabled_count = int(rule_summary.get("disabled_count", 0))
        else:
            active_count = rule_summary.active_count
            blocked_count = rule_summary.blocked_count
            disabled_count = rule_summary.disabled_count
        output_verified = bool(telemetry.output_verified or self._virtual_output_diagnostics.output_verified)
        runtime_truth = telemetry.runtime_truth.value if hasattr(telemetry.runtime_truth, "value") else str(telemetry.runtime_truth)
        lifecycle_state = (
            telemetry.lifecycle_state.value
            if hasattr(telemetry.lifecycle_state, "value")
            else str(telemetry.lifecycle_state)
        )
        runtime_frame = getattr(telemetry, "runtime_frame", None)
        physical_fidelity = getattr(telemetry, "physical_input_fidelity", None)
        backend_choice = getattr(telemetry, "physical_input_backend_choice", None)
        self.live_state_label.setText(
            "Precision Off | Combat Off | Trigger Off | Zoom Off | Extra Off\n"
            f"Stack mode: {self._workspace.modes.precision_combat_stack_mode.value}. "
            f"Active rules: {active_count}; blocked: {blocked_count}; "
            f"disabled: {disabled_count}.\n"
            f"Telemetry source: {self.telemetry_source_label}. Bridge lifecycle: {lifecycle_state}. "
            f"Runtime truth: {runtime_truth}. "
            f"Output writes verified: {str(output_verified).lower()}.\n"
            f"Input source: {self._physical_input_source_status.source_label}. "
            f"Sample status: {self._physical_input_source_status.source_status}. "
            f"Selected device: {self._physical_input_source_status.selected_device_name}. "
            f"Sample age: {self._physical_input_source_status.sample_age_text}. "
            f"Sample source: {self._physical_input_source_status.sample_source}.\n"
            f"Physical fidelity: {_physical_fidelity_summary(physical_fidelity, backend_choice)}\n"
            f"{self._bridge_frame_truth_text()}\n"
            f"{self._physical_input_truth_text()}\n"
            f"{self._config_sync_truth_text()}\n"
            f"{self._bridge_config_truth_text()}\n"
            f"{self._last_reload_truth_text(getattr(telemetry, 'last_command', None))}\n"
            f"{self._output_loop_runtime_truth_text()}\n"
            f"Runtime frame: {_runtime_frame_status(runtime_frame)}. "
            f"Runtime frame source: {_runtime_frame_source(runtime_frame)}. "
            f"Pipeline status: {_runtime_frame_pipeline_status(runtime_frame)}. "
            f"Output intent ready: {_runtime_frame_output_intent_ready(runtime_frame)}. "
            f"Output loop state: {_runtime_frame_output_loop_state(runtime_frame)}. "
            f"Last output write: {_runtime_frame_last_output_write(runtime_frame)}. "
            f"Input proof: {_runtime_frame_input_proof(runtime_frame)}. "
            f"Pipeline proof: {_runtime_frame_pipeline_proof(runtime_frame)}. "
            f"Output proof: {_runtime_frame_output_proof(runtime_frame)}. "
            f"Ready state: {_runtime_frame_ready_state(runtime_frame)}. "
            f"Telemetry proof: {_runtime_frame_telemetry_proof(runtime_frame)}. "
            f"Safety proof: {_runtime_frame_safety_proof(runtime_frame)}. "
            f"Fake/real path: {_runtime_frame_fake_or_real_path(runtime_frame)}. "
            f"Readiness evaluated: {_runtime_frame_evaluated_at(runtime_frame)}. "
            f"Runtime candidate: {_runtime_frame_candidate(runtime_frame)}. "
            f"Proof summary: {_runtime_frame_proof_summary(runtime_frame)}. "
            "runtime_frame output intent is not output write proof.\n"
            f"Physical input sample: read-only. {self._physical_input_source_status.fallback_behavior} "
            f"Virtual output backend: {self._virtual_output_diagnostics.virtual_output_backend}. "
            f"vJoy dependency: {self._virtual_output_diagnostics.vjoy_dependency_status}. "
            f"vJoy device: {self._virtual_output_diagnostics.vjoy_device_status}. "
            f"Output write status: {self._virtual_output_diagnostics.output_write_status}. "
            f"Output verification status: {self._virtual_output_diagnostics.output_verification_status}. "
            f"Real output verified: {str(self._virtual_output_diagnostics.real_output_verified).lower()}. "
            f"Fake output verified: {str(self._virtual_output_diagnostics.fake_output_verified).lower()}. "
            f"Output loop: {_output_loop_state(self._virtual_output_loop_snapshot)}. "
            f"Last output write: {_output_loop_last_write(self._virtual_output_loop_snapshot)}. "
            f"Neutral restore status: {_output_loop_neutral_restore(self._virtual_output_loop_snapshot)}. "
            "Output path remains unverified. vJoy writes are not active unless the Phase 15C output loop is explicitly enabled with a verified backend. "
            f"Full Live Runtime Ready {_runtime_frame_full_ready(runtime_frame)}."
        )
        self.compact_runtime_truth.setText(runtime_truth)
        self.compact_output_truth.setText(
            f"Output verified: {str(output_verified).lower()} | Full Live Runtime Ready: {_runtime_frame_full_ready(runtime_frame)}"
        )
        self.compact_source_truth.setText(f"{self.telemetry_source_label} ({bridge_result.status.value})")
        self.bridge_health_label.setText(
            self._bridge_health_text(
                bridge_result,
                telemetry=telemetry,
                runtime_truth=runtime_truth,
                output_verified=output_verified,
                process_hint=self._process_presence_provider.get_presence(),
            )
        )
        self._update_command_status_from_telemetry(telemetry, bridge_result)
        self.buttons_hats_label.setText(
            "HOTAS buttons and hats show read-only physical input samples when available, otherwise simulation fallback. "
            "Mapped outputs reflect the current workspace pipeline only; no vJoy button writes are verified in this phase."
        )
        self.runtime_chip.setText(self._state.runtime.header_truth_label)

    def _physical_input_now(self) -> datetime | None:
        if self._physical_input_clock is not None:
            return self._physical_input_clock()
        if self._physical_input_snapshot is not None:
            return self._physical_input_snapshot.sampled_at
        return None

    def _refresh_physical_input_source_status(self) -> None:
        self._physical_input_source_status = build_input_source_status(
            backend=self._physical_input_backend,
            selected_device_id=self._selected_physical_input_device_id,
            latest_snapshot=self._physical_input_snapshot,
            now=self._physical_input_now(),
            stale_after_seconds=self._physical_sample_stale_after_seconds,
        )

    def _physical_sample_override(self, sample: TelemetrySample) -> TelemetrySample:
        snapshot = self._physical_input_snapshot
        if snapshot is None or not self._physical_input_source_status.is_fresh_physical_sample:
            return sample
        return replace(
            sample,
            raw_axes=raw_axes_from_physical_snapshot(snapshot),
            buttons=buttons_from_physical_snapshot(snapshot),
            hat_state=hat_from_physical_snapshot(snapshot),
        )

    def _bridge_frame_truth_text(self) -> str:
        identity = self.last_bridge_frame_identity
        frame_label = identity.label if identity is not None else "unavailable"
        age_text = _ms_text(self.latest_bridge_frame_age_ms)
        tick_text = _ms_text(self.latest_bridge_tick_duration_ms)
        cadence_text = _hz_text(self.latest_bridge_source_cadence_hz)
        return (
            f"Bridge frame: {frame_label} | age {age_text} | tick {tick_text}. "
            f"Telemetry cadence: {cadence_text} | {self.latest_bridge_frame_state}. "
            f"Repeated frames skipped: {self.repeated_bridge_frame_count}."
        )

    def _physical_input_truth_text(self) -> str:
        return (
            f"Physical input: {self.latest_physical_input_backend_name} "
            f"({self.latest_physical_input_backend_kind}) | sample age {_ms_text(self.latest_physical_input_sample_age_ms)} | "
            f"read {_ms_text(self.latest_physical_input_read_duration_ms)} | "
            f"rate {_hz_text(self.latest_physical_input_sample_rate_hz)} | "
            f"mapping {self.latest_physical_input_mapping_status}."
        )

    def _config_sync_truth_text(self) -> str:
        bridge_hash = _short_hash(_mapping_value(self.latest_bridge_workspace, "workspace_hash"))
        ui_hash = self._ui_workspace_identity.short_hash
        if self.latest_bridge_config_match is True:
            status = "match"
        elif self.latest_bridge_config_match is False:
            status = "mismatch"
        else:
            status = "unknown"
        reason = f" | {self.latest_bridge_config_mismatch_reason}" if status == "mismatch" and self.latest_bridge_config_mismatch_reason else ""
        return f"Config sync: {status} | Bridge {bridge_hash} | UI {ui_hash}{reason}"

    def _bridge_config_truth_text(self) -> str:
        workspace = self.latest_bridge_workspace
        if not isinstance(workspace, Mapping):
            return "Bridge config: unavailable | bridge_workspace telemetry missing"
        path_text = _compact_path(str(workspace.get("config_path") or "unavailable"))
        status = str(workspace.get("config_status") or workspace.get("source_status") or "unknown")
        default_text = " | using default workspace" if bool(workspace.get("using_default_workspace", False)) else ""
        return f"Bridge config: {path_text} | {status}{default_text}"

    def _last_reload_truth_text(self, last_command: object) -> str:
        if not isinstance(last_command, Mapping) or str(last_command.get("command") or "") != BridgeCommandType.RELOAD_CONFIG.value:
            return "Last reload: unavailable"
        status = str(last_command.get("status") or "unknown")
        config_match = last_command.get("config_match")
        if config_match is True:
            detail = "expected hash matched"
        elif config_match is False:
            detail = str(last_command.get("mismatch_reason") or "expected hash mismatch")
        else:
            detail = "no expected hash supplied"
        return f"Last reload: {status} | {detail}"

    def _output_loop_runtime_truth_text(self) -> str:
        runtime = self.latest_output_loop_runtime
        if not isinstance(runtime, Mapping):
            return "Output loop runtime: unavailable"
        success = runtime.get("write_success_count", runtime.get("write_count", 0))
        failed = runtime.get("write_failure_count", runtime.get("failure_count", 0))
        skipped = runtime.get("write_skipped_count", 0)
        rate_limited = runtime.get("write_skipped_rate_limited_count", 0)
        return (
            f"Output loop runtime: {runtime.get('state') or 'unknown'} | "
            f"target {_optional_float(runtime.get('write_rate_hz')) or 0.0:.1f} Hz | "
            f"actual {_hz_text(_optional_float(runtime.get('actual_write_rate_hz')))} | "
            f"writes {success} ok / {failed} failed / {skipped} skipped | "
            f"rate-limited {rate_limited} | "
            f"verification {runtime.get('verification_status') or 'unknown'} | "
            f"device {runtime.get('selected_output_device') or 'None'} | "
            f"last write {runtime.get('last_write_status') or 'Unavailable'} | "
            f"last skipped {runtime.get('last_skipped_write_reason') or 'None'} | "
            f"neutral {runtime.get('neutral_restore_status') or 'not_attempted'} | "
            f"safety {runtime.get('safety_stop_reason') or 'None'}."
        )

    def start_manual_validation(self) -> None:
        self.manual_validation_session = create_manual_validation_session()
        self.manual_validation_session.start_next()
        self._refresh_manual_validation_card()

    def next_manual_validation_step(self) -> None:
        session = self.manual_validation_session
        if session is None:
            self.start_manual_validation()
            return
        current = session.current_step
        if current is not None and current.status in {ManualValidationStepStatus.OBSERVING, ManualValidationStepStatus.WAITING_FOR_ACTION, ManualValidationStepStatus.NOT_STARTED}:
            session.mark_step(current.step_id, ManualValidationStepStatus.SKIPPED, observed_signal="Operator advanced to next step.")
        session.start_next()
        if self._last_manual_validation_telemetry is not None:
            session.evaluate_current_step(self._last_manual_validation_telemetry)
        self._refresh_manual_validation_card()

    def mark_manual_validation_step(self, status: ManualValidationStepStatus) -> None:
        session = self.manual_validation_session
        if session is None:
            self.start_manual_validation()
            session = self.manual_validation_session
        if session is None or session.current_step is None:
            return
        session.mark_step(session.current_step.step_id, status, observed_signal=f"Operator marked {status.value}.")
        self._refresh_manual_validation_card()

    def export_manual_validation_report(self) -> None:
        session = self.manual_validation_session
        if session is None:
            self.start_manual_validation()
            session = self.manual_validation_session
        if session is None:
            return
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        paths = export_manual_validation_session(session, self._manual_validation_artifact_root / stamp)
        self.manual_validation_evidence_label.setText(f"Exported: {paths['markdown_path']}")

    def _update_manual_validation_from_telemetry(self, telemetry, bridge_result: BridgeTelemetryReadResult) -> None:
        payload = self._manual_validation_payload(telemetry, bridge_result)
        self._last_manual_validation_telemetry = payload
        if self.manual_validation_session is not None:
            self.manual_validation_session.evaluate_current_step(payload)
            self._refresh_manual_validation_card()
        elif hasattr(self, "manual_validation_evidence_label"):
            self._refresh_manual_validation_card()

    def _manual_validation_payload(self, telemetry, bridge_result: BridgeTelemetryReadResult) -> dict[str, object]:
        return {
            "source_label": bridge_result.source_label if bridge_result.status is BridgeTelemetryStatus.CONNECTED else "Simulation Fallback",
            "age_seconds": bridge_result.age_seconds,
            "raw_axes": _object_mapping(getattr(telemetry, "raw_axes", {}) or {}),
            "final_axes": _object_mapping(getattr(telemetry, "final_axes", {}) or {}),
            "buttons": _object_mapping(getattr(telemetry, "buttons", {}) or {}),
            "hats": _object_mapping(getattr(telemetry, "hats", {}) or {}),
            "bridge_workspace": _object_mapping(getattr(telemetry, "bridge_workspace", {}) or {}),
            "ui_workspace_hash": self._ui_workspace_identity.workspace_hash,
            "device_discovery": _object_mapping(getattr(telemetry, "device_discovery", {}) or {}),
            "physical_input_fidelity": _object_mapping(getattr(telemetry, "physical_input_fidelity", {}) or {}),
            "physical_input_backend_choice": _object_mapping(getattr(telemetry, "physical_input_backend_choice", {}) or {}),
            "output_status": getattr(telemetry, "output_status", ""),
            "output_verified": bool(getattr(telemetry, "output_verified", False)),
            "output_loop_runtime": _object_mapping(getattr(telemetry, "output_loop_runtime", {}) or {}),
            "runtime_frame": _runtime_frame_mapping(getattr(telemetry, "runtime_frame", None)),
        }

    def _refresh_manual_validation_card(self) -> None:
        if not hasattr(self, "manual_validation_status_label"):
            return
        session = self.manual_validation_session
        if session is None:
            self.manual_validation_status_label.setText("Session: not started")
            self.manual_validation_current_step_label.setText("Current step: unavailable")
            self.manual_validation_instruction_label.setText("Press Start Validation to begin.")
            source = "unavailable"
            if self._last_manual_validation_telemetry is not None:
                source = str(self._last_manual_validation_telemetry.get("source_label") or "unavailable")
            self.manual_validation_evidence_label.setText(f"Evidence: latest source {source}.")
            return
        summary = session.summary()
        current = session.current_step
        self.manual_validation_status_label.setText(
            f"Session: {summary['overall_status']} | passed {summary['passed_count']} | "
            f"blocked {summary['blocked_count']} | failed {summary['failed_count']}"
        )
        if current is None:
            self.manual_validation_current_step_label.setText("Current step: complete")
            self.manual_validation_instruction_label.setText("Validation session complete. Export the report for bench records.")
            self.manual_validation_evidence_label.setText("Evidence: complete.")
            return
        self.manual_validation_current_step_label.setText(f"Current step: {current.title} ({current.status.value})")
        self.manual_validation_instruction_label.setText(current.instruction)
        evidence = current.observed_signal or current.failure_reason or "Waiting for accepted telemetry evidence."
        self.manual_validation_evidence_label.setText(f"Evidence: {evidence}")

    def _update_source_status(self, bridge_result: BridgeTelemetryReadResult) -> None:
        self.telemetry_source_status = bridge_result.status.value
        if bridge_result.status is BridgeTelemetryStatus.CONNECTED:
            self.telemetry_source_label = bridge_result.source_label or "Bridge Telemetry"
            chip_text = self.telemetry_source_label
            tone = "success"
        else:
            self.telemetry_source_label = "Simulation Fallback"
            reason = {
                BridgeTelemetryStatus.MISSING: "Bridge Missing",
                BridgeTelemetryStatus.STALE: "Bridge Stale",
                BridgeTelemetryStatus.INVALID: "Bridge Invalid",
                BridgeTelemetryStatus.ERROR: "Bridge Error",
            }.get(bridge_result.status, "Bridge Missing")
            chip_text = reason
            tone = "warning" if bridge_result.status is not BridgeTelemetryStatus.ERROR else "danger"
        self.source_chip.setText(chip_text)
        self.source_chip.setProperty("chipTone", tone)
        self.source_chip.style().unpolish(self.source_chip)
        self.source_chip.style().polish(self.source_chip)

    def _bridge_health_text(self, bridge_result: BridgeTelemetryReadResult, *, telemetry, runtime_truth: str, output_verified: bool, process_hint) -> str:
        age_text = "n/a"
        if bridge_result.age_seconds is not None:
            age_text = f"{bridge_result.age_seconds:.1f}s"

        last_command_text = "none"
        last_command = getattr(telemetry, "last_command", None)
        if isinstance(last_command, Mapping):
            last_command_text = str(last_command.get("status") or "unknown")
        if self.latest_command_request_id and bridge_result.status is not BridgeTelemetryStatus.CONNECTED:
            last_command_text = "awaiting telemetry"
        elif self.latest_command_request_id and isinstance(last_command, Mapping):
            if str(last_command.get("request_id") or "") != self.latest_command_request_id:
                last_command_text = "awaiting telemetry"

        detail = bridge_result.reason or bridge_result.message
        if bridge_result.status is not BridgeTelemetryStatus.CONNECTED:
            detail = f"{detail} Simulation fallback active."

        discovery_text = self._device_discovery_text(
            getattr(telemetry, "device_discovery", None),
            output_verified=output_verified,
        )
        diagnostics = compose_bridge_lifecycle_diagnostics(
            bridge_result,
            process_hint,
            fallback_runtime_truth=runtime_truth,
            fallback_output_verified=output_verified,
        )
        self.latest_bridge_diagnostics = diagnostics
        rows = build_live_monitor_diagnostic_rows(
            diagnostics,
            latest_request_id=self.latest_command_request_id,
            latest_command_name=self.latest_command_name,
        )
        self._render_diagnostic_rows(rows)

        return (
            f"Bridge: {bridge_result.status.value} | "
            f"Telemetry age: {age_text} | "
            f"Runtime truth: {runtime_truth} | "
            f"Output verified: {str(output_verified).lower()} | "
            f"Last command: {last_command_text}.\n"
            f"{detail}\n"
            f"{discovery_text}\n"
            f"Bridge telemetry: {diagnostics.telemetry_label} | "
            f"Bridge lifecycle: {diagnostics.lifecycle_state} | "
            f"Process hint: {diagnostics.process_hint_label}.\n"
            f"Device discovery: {diagnostics.device_discovery_status}. "
            f"Diagnosis: {diagnostics.diagnostic_text}"
        )

    def _output_verified(self) -> bool:
        return bool(self._runtime_status.live_output_writes_verified or self._virtual_output_diagnostics.output_verified)

    def _render_diagnostic_rows(self, rows) -> None:
        existing_labels = set(self._diagnostic_row_labels)
        for index, row in enumerate(rows):
            label = self._diagnostic_row_labels.get(row.label)
            if label is None:
                label = QLabel("")
                label.setObjectName(f"bridgeDiagnostic_{_key(row.label)}")
                label.setWordWrap(True)
                self._diagnostic_row_labels[row.label] = label
                self.diagnostic_grid.addWidget(label, index // 2, index % 2)
            label.setText(f"{row.label}\n{row.value}")
            label.setToolTip(row.detail)
            label.setProperty("diagnosticSeverity", row.severity)
            label.style().unpolish(label)
            label.style().polish(label)
            existing_labels.discard(row.label)

        for stale_label in existing_labels:
            label = self._diagnostic_row_labels.pop(stale_label)
            label.setParent(None)
            label.deleteLater()

    def _device_discovery_text(self, device_discovery: object, *, output_verified: bool) -> str:
        if hasattr(device_discovery, "to_dict"):
            device_discovery = device_discovery.to_dict()
        if not isinstance(device_discovery, Mapping):
            return "HOTAS discovery: not checked. Bridge-owned device discovery has not reported a result."

        status = str(device_discovery.get("status") or "not_checked")
        error = device_discovery.get("error")
        if status == "supported_device_detected":
            return (
                "HOTAS discovery: supported device detected. "
                "Supported HOTAS detected; polling not active. "
                f"Device discovery only; output verification {str(output_verified).lower()}."
            )
        if status == "no_supported_device":
            return (
                "HOTAS discovery: no supported device found. "
                "Read-only discovery did not find a supported HOTAS device."
            )
        if status == "discovery_error":
            error_text = f": {error}" if error else ""
            return f"HOTAS discovery: discovery error. Device discovery error{error_text}."
        if status == "backend_unavailable":
            return "HOTAS discovery: backend unavailable. Discovery backend is unavailable; the UI is not scanning hardware."
        return "HOTAS discovery: not checked. Bridge-owned device discovery has not reported a result."

    def _update_command_status_from_telemetry(self, telemetry, bridge_result: BridgeTelemetryReadResult) -> None:
        if not self.latest_command_request_id:
            return
        if bridge_result.status is not BridgeTelemetryStatus.CONNECTED:
            return

        last_command = getattr(telemetry, "last_command", None)
        if not isinstance(last_command, Mapping):
            return
        if str(last_command.get("request_id") or "") != self.latest_command_request_id:
            self.command_status_label.setText(
                f"{self.latest_command_name or 'Bridge'} command requested. Awaiting Bridge telemetry."
            )
            return

        status = str(last_command.get("status") or "unknown")
        message = str(last_command.get("message") or "")
        command = str(last_command.get("command") or self.latest_command_name or "Bridge")
        request_id = self.latest_command_request_id
        if status == "completed":
            text = f"{command} completed by Bridge for {request_id}. {message}".strip()
        elif status == "acknowledged":
            text = f"{command} acknowledged by Bridge for {request_id}. {message}".strip()
        elif status in {"failed", "rejected", "ignored_stale"}:
            text = f"{command} {status.replace('_', ' ')} by Bridge for {request_id}. {message}".strip()
        else:
            text = f"{command} status from Bridge for {request_id}: {status}. {message}".strip()
        self.command_status_label.setText(text)

    def _update_graphs(self) -> None:
        started_at = time.perf_counter()
        raw_points = self.history.raw_points(self.selected_axis)
        final_points = self.history.final_points(self.selected_axis)
        latest = self.history.latest
        marker = None
        if latest is not None:
            marker = (0.0, latest.raw_axes.get(self.selected_axis, 0.0))
        self.raw_trace_graph.plot_series_with_marker(
            (("Raw", raw_points, "#53b7ff"),),
            marker=marker,
        )
        self.raw_trace_graph.plot.setXRange(-LIVE_TRACE_HISTORY_SECONDS, 0.0, padding=0)

        overlay_series = []
        if self.show_raw_and_output_together:
            overlay_series.append(("Raw", raw_points, "#53b7ff"))
        overlay_series.append(("Final", final_points, "#76d39b"))
        self.overlay_series_count = len(overlay_series)
        final_marker = None
        if latest is not None:
            final_marker = (0.0, latest.final_axes.get(self.selected_axis, 0.0))
        self.overlay_graph.plot_series_with_marker(tuple(overlay_series), marker=final_marker)
        self.overlay_graph.plot.setXRange(-LIVE_TRACE_HISTORY_SECONDS, 0.0, padding=0)
        self._record_timing("graph", started_at)


def _body(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("cardBody")
    label.setWordWrap(True)
    return label


def _level_bar(kind: str) -> QProgressBar:
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setTextVisible(False)
    bar.setProperty("levelKind", kind)
    return bar


def _bar_value(value: float) -> int:
    return int(round((max(-1.0, min(1.0, float(value))) + 1.0) * 50.0))


def _virtual_output_loop_snapshot(
    loop: VirtualOutputWriteLoop | VirtualOutputLoopSnapshot | None,
) -> VirtualOutputLoopSnapshot | None:
    if loop is None:
        return None
    if isinstance(loop, VirtualOutputLoopSnapshot):
        return loop
    return loop.snapshot()


def _output_loop_state(snapshot: VirtualOutputLoopSnapshot | None) -> str:
    return snapshot.state.value if snapshot is not None else "disabled"


def _output_loop_last_write(snapshot: VirtualOutputLoopSnapshot | None) -> str:
    return snapshot.last_write_timestamp if snapshot is not None else "Unavailable"


def _output_loop_neutral_restore(snapshot: VirtualOutputLoopSnapshot | None) -> str:
    return snapshot.neutral_restore_status if snapshot is not None else "not_attempted"


def _runtime_frame_status(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    if runtime_frame is None:
        return "unavailable"
    return "available" if runtime_frame.available else runtime_frame.parse_status


def _physical_fidelity_summary(fidelity: Mapping[str, object] | None, backend_choice: Mapping[str, object] | None) -> str:
    if not isinstance(fidelity, Mapping):
        return "unavailable"
    backend = str(fidelity.get("backend_name") or "unknown")
    age = fidelity.get("sample_age_ms")
    read = fidelity.get("read_duration_ms")
    rate = fidelity.get("estimated_sample_rate_hz")
    mapping = str(fidelity.get("mapping_status") or "unavailable")
    fallback = False
    if isinstance(backend_choice, Mapping):
        fallback = bool(backend_choice.get("fallback_used", False))
    age_text = "n/a" if age is None else f"{float(age):.1f} ms"
    read_text = "n/a" if read is None else f"{float(read):.3f} ms"
    rate_text = "n/a" if rate is None else f"{float(rate):.1f} Hz"
    return f"{backend}; age {age_text}; read {read_text}; rate {rate_text}; mapping {mapping}; fallback {str(fallback).lower()}"


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ms_text(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"{float(value):.1f} ms"


def _hz_text(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"{float(value):.1f} Hz"


def _mapping_value(mapping: Mapping[str, object] | None, key: str) -> object:
    if not isinstance(mapping, Mapping):
        return None
    return mapping.get(key)


def _object_mapping(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        mapped = value.to_dict()
        return dict(mapped) if isinstance(mapped, Mapping) else {}
    if hasattr(value, "values") and isinstance(getattr(value, "values"), Mapping):
        return dict(getattr(value, "values"))
    return {}


def _short_hash(value: object) -> str:
    if not value:
        return "unavailable"
    return str(value)[:8]


def _compact_path(value: str) -> str:
    if not value or value == "unavailable":
        return "unavailable"
    return Path(value).name or value


def _runtime_frame_source(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.input_source if runtime_frame is not None else "unavailable"


def _runtime_frame_pipeline_status(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.pipeline_status if runtime_frame is not None else "unavailable"


def _runtime_frame_output_intent_ready(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return str(bool(runtime_frame and runtime_frame.output_intent_ready)).lower()


def _runtime_frame_output_loop_state(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.output_loop_state if runtime_frame is not None else "disabled"


def _runtime_frame_last_output_write(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.last_output_write_status if runtime_frame is not None else "Not active"


def _runtime_frame_input_proof(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.input_proof if runtime_frame is not None else "unavailable"


def _runtime_frame_pipeline_proof(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.pipeline_proof if runtime_frame is not None else "unavailable"


def _runtime_frame_output_proof(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.output_proof if runtime_frame is not None else "unavailable"


def _runtime_frame_ready_state(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.ready_state if runtime_frame is not None else "unavailable"


def _runtime_frame_telemetry_proof(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.telemetry_proof if runtime_frame is not None else "unavailable"


def _runtime_frame_safety_proof(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.safety_proof if runtime_frame is not None else "unavailable"


def _runtime_frame_fake_or_real_path(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.fake_or_real_path if runtime_frame is not None else "unavailable"


def _runtime_frame_evaluated_at(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    if runtime_frame is None or runtime_frame.evaluated_at is None:
        return "Unavailable"
    return runtime_frame.evaluated_at.isoformat()


def _runtime_frame_full_ready(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return str(bool(runtime_frame and runtime_frame.full_live_runtime_ready)).lower()


def _runtime_frame_candidate(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    if runtime_frame is None:
        return "unavailable"
    if runtime_frame.full_live_runtime_ready:
        return "ready - full gate open"
    if runtime_frame.ready_state == "fake_test":
        return "fake/test only - not real readiness"
    if runtime_frame.verified_runtime_candidate:
        return "candidate - final gate proof incomplete"
    reason = runtime_frame.blocked_reason or "proof incomplete"
    return f"blocked - {reason}"


def _runtime_frame_proof_summary(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.proof_summary if runtime_frame is not None and runtime_frame.proof_summary else "unavailable"


def _runtime_frame_mapping(runtime_frame: RuntimeFrameTelemetryPayload | None) -> dict[str, object]:
    if runtime_frame is None:
        return {}
    return {
        "full_live_runtime_ready": runtime_frame.full_live_runtime_ready,
        "ready_state": runtime_frame.ready_state,
        "blocked_reason": runtime_frame.blocked_reason,
        "fake_or_real_path": runtime_frame.fake_or_real_path,
        "proof_summary": runtime_frame.proof_summary,
        "output_intent_ready": runtime_frame.output_intent_ready,
        "final_output_axes": dict(runtime_frame.final_output_axes),
    }


def _set_chip_state(chip: QLabel, text: str, active: bool) -> None:
    chip.setText(text)
    chip.setProperty("chipTone", "success" if active else "neutral")
    chip.style().unpolish(chip)
    chip.style().polish(chip)


def _key(axis_name: str) -> str:
    return axis_name.replace(" ", "_")


def _overlay_summary(config: LiveOverlayConfig) -> str:
    opacity_percent = int(round(config.opacity * 100))
    return f"{config.preset} | {config.position} | {opacity_percent}% opacity | {config.source}"


def _full_live_runtime_ready(runtime_status: RuntimePreflightStatus) -> bool:
    return bool(runtime_status.live_output_writes_verified and runtime_status.truth.value == "live_verified")
