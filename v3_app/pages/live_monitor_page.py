from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Callable, Mapping

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
from shared_core.rules.evaluator import RuleStatus, status_counts
from shared_core.runtime.bridge_contracts import BridgeCommandType
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.simulated_runtime import SimulatedRuntime
from v3_app.pages.graph_widgets import GraphPreview
from v3_app.pages.live_monitor_data import (
    BoundedTelemetryHistory,
    OUTPUT_BUTTON_NAMES,
    bridge_telemetry_from_runtime_snapshot,
    telemetry_sample_from_bridge_payload,
    telemetry_sample_from_runtime_snapshot,
)
from v3_app.pages.page_helpers import card, card_header, card_layout, page_intro, signed
from v3_app.services.app_state import AppState
from v3_app.services.bridge_client import (
    DEFAULT_BRIDGE_TELEMETRY_PATH,
    BridgeTelemetryClient,
    BridgeTelemetryReadResult,
    BridgeTelemetryStatus,
)
from v3_app.services.bridge_commands import (
    DEFAULT_BRIDGE_COMMAND_PATH,
    BridgeCommandClient,
    BridgeCommandWriteResult,
)
from v3_app.services.bridge_presence import (
    BridgeProcessPresenceProvider,
    UnavailableBridgeProcessPresenceProvider,
    compose_bridge_lifecycle_diagnostics,
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
        process_presence_provider: BridgeProcessPresenceProvider | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("liveMonitorPage")
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._simulation = SimulatedRuntime(deterministic=False, workspace=self._workspace)
        self._bridge_client = BridgeTelemetryClient(
            telemetry_path=telemetry_path or DEFAULT_BRIDGE_TELEMETRY_PATH,
            stale_after_seconds=bridge_stale_after_seconds,
            clock=bridge_clock,
        )
        self._command_client = BridgeCommandClient(
            command_path=command_path or DEFAULT_BRIDGE_COMMAND_PATH,
            request_id_factory=command_request_id_factory,
            clock=command_clock,
        )
        self._process_presence_provider = process_presence_provider or UnavailableBridgeProcessPresenceProvider()
        self._pipeline = WorkspaceSignalPipeline(self._workspace)
        self._pipeline_state = self._pipeline.initial_state()
        self.selected_axis = state.selected_axis if state.selected_axis in AXIS_DISPLAY_NAMES else "Roll"
        self.show_raw_and_output_together = True
        self.overlay_series_count = 0
        self.telemetry_source_label = "Simulation Fallback"
        self.telemetry_source_status = "Missing"
        self.latest_bridge_diagnostics = None
        self.last_command_result: BridgeCommandWriteResult | None = None
        self.latest_command_request_id: str | None = None
        self.latest_command_name: str | None = None
        self._sample_index = 0
        self.history = BoundedTelemetryHistory(capacity=240)
        self.axis_level_widgets: dict[str, QWidget] = {}
        self._axis_value_labels: dict[str, tuple[QLabel, QLabel]] = {}
        self._axis_bars: dict[str, tuple[QProgressBar, QProgressBar]] = {}
        self._hotas_buttons: dict[str, QLabel] = {}
        self._output_buttons: dict[str, QLabel] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)

        root.addWidget(
            page_intro(
                "Live Monitor",
                "Watch raw HOTAS input, final vJoy output, buttons, hats, and axis levels in one dedicated live workspace.",
                "Current values are simulation-backed until the future Bridge verifies live output writes.",
            )
        )
        root.addWidget(self._build_controls_card())
        root.addWidget(self._build_raw_trace_card())
        root.addWidget(self._build_overlay_card())

        status_grid = QGridLayout()
        status_grid.setHorizontalSpacing(18)
        status_grid.setVerticalSpacing(18)
        status_grid.addWidget(self._build_live_state_card(), 0, 0)
        status_grid.addWidget(self._build_buttons_hats_card(), 0, 1)
        root.addLayout(status_grid)

        root.addWidget(self._build_axis_levels_card())

        button_grid = QGridLayout()
        button_grid.setHorizontalSpacing(18)
        button_grid.setVerticalSpacing(18)
        button_grid.addWidget(self._build_hotas_buttons_card(), 0, 0)
        button_grid.addWidget(self._build_output_buttons_card(), 0, 1)
        root.addLayout(button_grid)
        root.addStretch(1)

        self._timer = QTimer(self)
        self._timer.setInterval(750)
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
            f"Output writes verified: {str(self._runtime_status.live_output_writes_verified).lower()}",
            tone="success" if self._runtime_status.live_output_writes_verified else "warning",
            object_name="liveMonitorOutputTruthChip",
        )
        row.addWidget(axis_label)
        row.addWidget(self.axis_selector)
        row.addWidget(self.overlay_checkbox)
        row.addStretch(1)
        row.addWidget(self.source_chip)
        row.addWidget(self.runtime_chip)
        row.addWidget(output_chip)
        layout.addLayout(row)
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
        layout.addWidget(_body("Newest samples are on the right edge."))
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
        layout.addWidget(_body("Raw and final output are overlaid for direct comparison."))
        return frame

    def _build_live_state_card(self) -> QWidget:
        frame = card("liveStateCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Live State", "Current mode state and bridge activity."))
        self.live_state_label = QLabel("")
        self.live_state_label.setObjectName("liveStateText")
        self.live_state_label.setWordWrap(True)
        layout.addWidget(self.live_state_label)
        self.bridge_health_label = QLabel("")
        self.bridge_health_label.setObjectName("bridgeHealthText")
        self.bridge_health_label.setWordWrap(True)
        layout.addWidget(self.bridge_health_label)
        self.command_status_label = QLabel("Bridge commands are requests; fresh telemetry confirms later.")
        self.command_status_label.setObjectName("bridgeCommandStatusText")
        self.command_status_label.setWordWrap(True)
        layout.addWidget(self.command_status_label)

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
        return frame

    def _build_axis_levels_card(self) -> QWidget:
        frame = card("axisLevelsCard")
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
            grid.addWidget(axis_row, row // 2, row % 2)
        layout.addLayout(grid)
        return frame

    def _build_hotas_buttons_card(self) -> QWidget:
        frame = card("hotasButtonsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("HOTAS Buttons", "Simulation-backed button states until Bridge polling is implemented."))
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
            return
        self.refresh_snapshot(force_new=True)

    def should_skip_timer_refresh(self) -> bool:
        return not self.isVisible()

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

    def request_bridge_command(self, command: BridgeCommandType, label: str | None = None) -> BridgeCommandWriteResult:
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
        bridge_result = self._bridge_client.read()
        if bridge_result.status is BridgeTelemetryStatus.CONNECTED and bridge_result.telemetry is not None:
            sample = telemetry_sample_from_bridge_payload(bridge_result.telemetry, index=self._sample_index)
            telemetry = bridge_result.telemetry
        else:
            snapshot = self._simulation.snapshot(self._runtime_status)
            sample = telemetry_sample_from_runtime_snapshot(snapshot, index=self._sample_index)
            telemetry = bridge_telemetry_from_runtime_snapshot(
                snapshot,
                active_profile=self._state.active_profile,
                rule_summary=self._rule_summary(snapshot.raw_axis_values),
            )
        self.history.append(sample)
        self._update_from_sample(sample, telemetry, bridge_result)
        self._update_graphs()

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
        output_verified = bool(telemetry.output_verified)
        runtime_truth = telemetry.runtime_truth.value if hasattr(telemetry.runtime_truth, "value") else str(telemetry.runtime_truth)
        lifecycle_state = (
            telemetry.lifecycle_state.value
            if hasattr(telemetry.lifecycle_state, "value")
            else str(telemetry.lifecycle_state)
        )
        self.live_state_label.setText(
            "Precision Off | Combat Off | Trigger Off | Zoom Off | Extra Off\n"
            f"Stack mode: {self._workspace.modes.precision_combat_stack_mode.value}. "
            f"Active rules: {active_count}; blocked: {blocked_count}; "
            f"disabled: {disabled_count}.\n"
            f"Telemetry source: {self.telemetry_source_label}. Bridge lifecycle: {lifecycle_state}. "
            f"Runtime truth: {runtime_truth}. "
            f"Output writes verified: {str(output_verified).lower()}."
        )
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
            "In Simulation Mode, HOTAS buttons and hats are generated by the simulation runtime while mapped outputs "
            "reflect the current workspace pipeline. No real vJoy button writes are verified in this phase."
        )
        self.runtime_chip.setText(self._state.runtime.header_truth_label)

    def _update_source_status(self, bridge_result: BridgeTelemetryReadResult) -> None:
        self.telemetry_source_status = bridge_result.status.value
        if bridge_result.status is BridgeTelemetryStatus.CONNECTED:
            self.telemetry_source_label = "Bridge Telemetry"
            chip_text = "Bridge Telemetry"
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
        raw_points = self.history.raw_points(self.selected_axis)
        final_points = self.history.final_points(self.selected_axis)
        latest = self.history.latest
        marker = None
        if latest is not None:
            marker = (float(latest.index), latest.raw_axes.get(self.selected_axis, 0.0))
        self.raw_trace_graph.plot_series_with_marker(
            (("Raw", raw_points, "#53b7ff"),),
            marker=marker,
        )

        overlay_series = []
        if self.show_raw_and_output_together:
            overlay_series.append(("Raw", raw_points, "#53b7ff"))
        overlay_series.append(("Final", final_points, "#76d39b"))
        self.overlay_series_count = len(overlay_series)
        final_marker = None
        if latest is not None:
            final_marker = (float(latest.index), latest.final_axes.get(self.selected_axis, 0.0))
        self.overlay_graph.plot_series_with_marker(tuple(overlay_series), marker=final_marker)


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


def _set_chip_state(chip: QLabel, text: str, active: bool) -> None:
    chip.setText(text)
    chip.setProperty("chipTone", "success" if active else "neutral")
    chip.style().unpolish(chip)
    chip.style().polish(chip)


def _key(axis_name: str) -> str:
    return axis_name.replace(" ", "_")
