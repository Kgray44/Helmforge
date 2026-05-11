from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from shared_core.models.runtime import InputStatus, OutputStatus, RuntimePreflightStatus, RuntimeTruth
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.runtime_bridge import RuntimeBridge
from shared_core.runtime.setup_guidance import OFFICIAL_THRUSTMASTER_SUPPORT_PAGE
from v3_app.pages.page_helpers import card, card_header, card_layout, page_intro, truth_notice
from v3_app.services.app_state import AppState
from v3_app.ui.status_chips import action_button, status_chip


OnStatus = Callable[[str], None]


class PreflightPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        on_status: OnStatus | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("preflightPage")
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._on_status = on_status
        self._rows: dict[str, QLabel] = {}
        self._section_rows: dict[str, dict[str, str]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)

        root.addWidget(
            page_intro(
                "Preflight",
                "Check the HOTAS, vJoy, Bridge pipeline, and readiness proofs before relying on live output.",
                "Use this page as the cockpit check: device evidence, output proof, workspace state, and safety gates stay separate.",
            )
        )
        root.addWidget(self._build_action_bar())
        root.addWidget(
            truth_notice(
                "Preflight can refresh checks and apply a draft workspace to the Bridge. Live output still waits for verified input, telemetry, output, and safety proof.",
                object_name="preflightTruthNotice",
            )
        )

        sections = QGridLayout()
        sections.setHorizontalSpacing(18)
        sections.setVerticalSpacing(18)
        section_widgets = (
            self._build_section(
                "preflightReadinessSection",
                "Readiness Summary",
                "Current go/no-go signals for this workspace.",
                self._readiness_rows(),
            ),
            self._build_section(
                "preflightDeviceDriverSection",
                "Device / Driver",
                "Hardware discovery, driver posture, and input freshness.",
                self._device_rows(),
            ),
            self._build_section(
                "preflightVjoyOutputSection",
                "vJoy / Output",
                "Virtual output backend and write-proof state.",
                self._output_rows(),
            ),
            self._build_section(
                "preflightBridgeTelemetrySection",
                "Bridge / Telemetry",
                "Bridge lifecycle, telemetry freshness, and command posture.",
                self._telemetry_rows(),
            ),
            self._build_section(
                "preflightWorkspaceConfigSection",
                "Workspace / Config",
                "The draft that will be applied or saved.",
                self._workspace_rows(),
            ),
            self._build_section(
                "preflightInputDataSection",
                "Input Data",
                "Mapping and input data available to the runtime.",
                self._input_data_rows(),
            ),
            self._build_section(
                "preflightSafetyGatesSection",
                "Pipeline / Safety Gates",
                "Proof gates that protect live output.",
                self._safety_rows(),
            ),
            self._build_section(
                "preflightWarningsActionsSection",
                "Warnings / Actions",
                "Readable next steps when a check is not ready.",
                self._warning_action_rows(),
            ),
            self._build_section(
                "preflightAdvancedDetailsSection",
                "Advanced Technical Details",
                "Raw values for diagnostics and support.",
                self._advanced_rows(),
                advanced=True,
            ),
        )
        for index, widget in enumerate(section_widgets):
            sections.addWidget(widget, index // 2, index % 2)
        root.addLayout(sections)
        root.addStretch(1)

    def update_runtime_status(self, runtime_status: RuntimePreflightStatus) -> None:
        self._runtime_status = runtime_status
        for rows in (
            self._readiness_rows(),
            self._device_rows(),
            self._output_rows(),
            self._telemetry_rows(),
            self._workspace_rows(),
            self._input_data_rows(),
            self._safety_rows(),
            self._warning_action_rows(),
            self._advanced_rows(),
        ):
            for key, value in rows.items():
                row = self._rows.get(key)
                if row is not None:
                    row.setText(value)

    def _build_action_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("preflightActionBar")
        bar.setProperty("uiRole", "preflightDashboard")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        run = action_button("Run Preflight Check", object_name="runPreflightButton")
        run.clicked.connect(lambda: self._status_message(self._preflight_status_sentence()))
        simulation = action_button("Use Simulation Mode", object_name="useSimulationModeButton")
        simulation.clicked.connect(lambda: self._status_message("Simulation mode is available for safe workspace testing."))
        guide = action_button("Open Runtime Setup Guide", object_name="runtimeSetupGuideButton")
        guide.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(_project_root() / "docs" / "HelmForge" / "runtime-preflight-and-vjoy-setup.md"))
            )
        )
        support = action_button("Open Thrustmaster Support", object_name="openThrustmasterSupportButton")
        support.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(OFFICIAL_THRUSTMASTER_SUPPORT_PAGE)))

        layout.addWidget(run)
        layout.addWidget(simulation)
        layout.addWidget(guide)
        layout.addWidget(support)
        layout.addStretch(1)
        layout.addWidget(status_chip(self._live_chip_text(), tone=self._live_chip_tone(), object_name="preflightLiveStatusChip"))
        return bar

    def _build_section(
        self,
        object_name: str,
        title: str,
        body: str,
        rows: dict[str, str],
        *,
        advanced: bool = False,
    ) -> QFrame:
        frame = card(object_name)
        frame.setProperty("uiRole", "preflightDashboard")
        frame.setProperty("preflightSection", title)
        if advanced:
            frame.setProperty("advancedDetails", True)
        layout = card_layout(frame)
        layout.addWidget(card_header(title, body))
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)
        for row_index, (label, value) in enumerate(rows.items()):
            key = QLabel(label)
            key.setObjectName("preflightDatumLabel")
            key.setProperty("uiRole", "preflightDatum")
            val = QLabel(value)
            val.setObjectName("preflightDatumValue")
            val.setProperty("uiRole", "preflightDatum")
            val.setWordWrap(True)
            self._rows[label] = val
            grid.addWidget(key, row_index, 0)
            grid.addWidget(val, row_index, 1)
        layout.addLayout(grid)
        return frame

    def _readiness_rows(self) -> dict[str, str]:
        ready = self._full_live_ready()
        return {
            "Overall readiness": "Ready for live output" if ready else "Checks still required",
            "Live verified": "Live checks passed" if self._runtime_status.truth is RuntimeTruth.LIVE_VERIFIED else "Waiting for live verification",
            "Output verification": "Output verified" if self._runtime_status.live_output_writes_verified else "Output verification pending",
            "Full live runtime": "Ready" if ready else "Not ready yet",
            "Active mode": _polish_mode(self._runtime_status.mode.value),
            "Current workspace": self._workspace.active_profile,
            "Saved / applied state": "Saved workspace" if self._state.saved else "Unsaved draft",
        }

    def _device_rows(self) -> dict[str, str]:
        names = self._runtime_status.detected_device_names
        return {
            "Target hardware": self._workspace.target_hardware.primary_device_name,
            "Detected hardware name": ", ".join(names) if names else "No supported HOTAS detected yet",
            "VID / PID": "Not reported by current telemetry",
            "Driver detected": "Driver tools detected" if self._state.runtime.driver_detected else "Driver check not confirmed",
            "Device connected": "Connected" if self._runtime_status.input.status is InputStatus.DETECTED else "Not connected",
            "Discovery status": self._input_status_label(),
            "Physical input freshness": "Fresh physical sample" if self._runtime_status.input.status is InputStatus.DETECTED else "No live sample yet",
            "Last input update": "No sample received in this UI session",
        }

    def _output_rows(self) -> dict[str, str]:
        return {
            "vJoy detected": "Detected" if self._runtime_status.output.status in {OutputStatus.VJOY_DETECTED, OutputStatus.OUTPUT_VERIFIED} else "Not detected",
            "vJoy device / status": self._output_status_label(),
            "Output backend": self._runtime_status.detected_output_backend_name or "Output backend not selected",
            "Output verified": "Verified" if self._runtime_status.live_output_writes_verified else "Waiting for guarded verification",
            "Last output write": "No live write proof yet",
            "Write proof": "Verified output write" if self._runtime_status.live_output_writes_verified else "No output write proof yet",
            "Draft vs actual output": "Draft mapping only until output proof is available",
        }

    def _telemetry_rows(self) -> dict[str, str]:
        return {
            "Bridge lifecycle": self._runtime_truth_display(),
            "Telemetry source": "Runtime preflight snapshot",
            "Telemetry freshness": "Live enough for status" if self._runtime_status.truth is RuntimeTruth.LIVE_VERIFIED else "No fresh Bridge telemetry in this view",
            "Last telemetry tick": "Not reported by current telemetry",
            "Telemetry age": "Not reported by current telemetry",
            "Command status": "Ready to send Apply Workspace command",
            "Last apply / reload command": "No apply command reported in this page session",
            "Telemetry state": self._telemetry_state_label(),
        }

    def _workspace_rows(self) -> dict[str, str]:
        return {
            "Workspace name": self._workspace.active_profile,
            "Saved state": "Saved" if self._state.saved else "Unsaved draft",
            "Workspace path": "Workspace configuration",
            "Active config source": "Current workspace draft",
            "Config match / applied": "Saved workspace matches current draft" if self._state.saved else "Draft has unapplied or unsaved changes",
            "Apply state": "Ready to apply draft" if not self._state.saved else "No unsaved draft changes",
            "Axis route count": str(len(self._workspace.mappings.axis_routes)),
            "Button route count": str(len(self._workspace.mappings.button_routes)),
            "Hat route count": str(len(self._workspace.mappings.hat_routes)),
        }

    def _input_data_rows(self) -> dict[str, str]:
        snapshot = RuntimeBridge(preflight_status=self._runtime_status, deterministic_simulation=True).snapshot()
        return {
            "Axis count": str(len(self._workspace.mappings.axis_routes)),
            "Button count": str(len(self._workspace.mappings.button_routes)),
            "Hat count": str(len(self._workspace.mappings.hat_routes)),
            "Raw axes available": str(len(snapshot.raw_axis_values)),
            "Final axes available": str(len(snapshot.final_output_values)),
            "Buttons available": str(len(snapshot.button_states)),
            "Hats available": "1" if snapshot.hat_state else "0",
            "Selected profile": self._workspace.active_profile,
            "Selected mode": _selected_mode_label(self._workspace),
            "Rules enabled": str(sum(1 for rule in self._workspace.rules.rules if rule.enabled)),
        }

    def _safety_rows(self) -> dict[str, str]:
        ready = self._full_live_ready()
        return {
            "Runtime truth": self._runtime_truth_display(),
            "Readiness gate": "Open" if ready else "Proofs still required",
            "Input proof": "Input detected" if self._runtime_status.input.status is InputStatus.DETECTED else "Input proof missing",
            "Output proof": "Output verified" if self._runtime_status.live_output_writes_verified else "Output proof missing",
            "Telemetry proof": "Telemetry available" if self._runtime_status.truth is RuntimeTruth.LIVE_VERIFIED else "Telemetry proof not available",
            "Safety proof": "Safety gate clear" if ready else "Safety gate waiting for full proof",
            "Simulation / fallback": "Live path active" if ready else "Safe fallback or setup mode",
        }

    def _warning_action_rows(self) -> dict[str, str]:
        return {
            "Warnings": _joined_polished(self._runtime_status.warnings, "No warnings reported"),
            "Errors": _joined_polished(self._runtime_status.errors, "No errors reported"),
            "Recommended next action": self._recommended_action(),
            "Runtime setup guide": "Open the setup guide from the action bar",
            "Support tools": "Open Thrustmaster support from the action bar",
        }

    def _advanced_rows(self) -> dict[str, str]:
        return {
            "Raw runtime truth": self._runtime_status.truth.value,
            "Raw runtime mode": self._runtime_status.mode.value,
            "Raw input status": self._runtime_status.input.status.value,
            "Raw output status": self._runtime_status.output.status.value,
            "Raw output verified": str(self._runtime_status.live_output_writes_verified).lower(),
            "Source configuration": self._state.source_config,
            "Detected backend name": self._runtime_status.detected_output_backend_name or "None",
            "Runtime messages": _joined_polished(self._runtime_status.messages, "No runtime messages reported"),
        }

    def _input_status_label(self) -> str:
        if self._runtime_status.input.status is InputStatus.DETECTED:
            return "HOTAS input detected"
        if self._runtime_status.input.status is InputStatus.ERROR:
            return "Input check needs attention"
        if self._runtime_status.input.status is InputStatus.MISSING:
            return "Waiting for HOTAS input"
        return "Input check pending"

    def _output_status_label(self) -> str:
        if self._runtime_status.output.status is OutputStatus.OUTPUT_VERIFIED:
            return "vJoy output verified"
        if self._runtime_status.output.status is OutputStatus.VJOY_DETECTED:
            return "vJoy detected, output not verified"
        if self._runtime_status.output.status is OutputStatus.VJOY_MISSING:
            return "vJoy not detected"
        if self._runtime_status.output.status is OutputStatus.OUTPUT_ERROR:
            return "Output check needs attention"
        return "Output check pending"

    def _runtime_truth_display(self) -> str:
        if self._runtime_status.truth is RuntimeTruth.LIVE_VERIFIED:
            return "Live checks passed"
        if self._runtime_status.truth is RuntimeTruth.DETECTED_UNVERIFIED:
            return "Device detected, output not verified"
        if self._runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DEVICE:
            return "Waiting for HOTAS input"
        if self._runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DRIVER:
            return "Driver or output setup needed"
        if self._runtime_status.truth is RuntimeTruth.ERROR:
            return "Runtime check needs attention"
        return "Simulation mode"

    def _telemetry_state_label(self) -> str:
        if self._runtime_status.errors:
            return "Telemetry error reported"
        if self._runtime_status.warnings:
            return "Telemetry warning reported"
        if self._runtime_status.truth is RuntimeTruth.LIVE_VERIFIED:
            return "Telemetry accepted"
        return "Telemetry not connected to live device proof"

    def _recommended_action(self) -> str:
        if self._full_live_ready():
            return "Review mappings, then apply or save when ready"
        if self._runtime_status.input.status is not InputStatus.DETECTED:
            return "Connect the HOTAS, then run preflight again"
        if not self._runtime_status.live_output_writes_verified:
            return "Verify vJoy output before relying on live control"
        return "Review runtime messages before live use"

    def _preflight_status_sentence(self) -> str:
        live = "Live checks passed" if self._runtime_status.truth is RuntimeTruth.LIVE_VERIFIED else "Live checks need attention"
        output = "output verified" if self._runtime_status.live_output_writes_verified else "output proof pending"
        return f"{live}; {output}."

    def _live_chip_text(self) -> str:
        return "Live Verified" if self._runtime_status.live_output_writes_verified else "Preflight Needed"

    def _live_chip_tone(self) -> str:
        return "success" if self._runtime_status.live_output_writes_verified else "caution"

    def _full_live_ready(self) -> bool:
        return bool(self._runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and self._runtime_status.live_output_writes_verified)

    def _status_message(self, message: str) -> None:
        if self._on_status is not None:
            self._on_status(message)


def _joined_polished(values: tuple[str, ...], fallback: str) -> str:
    if not values:
        return fallback
    return "; ".join(_polish_runtime_message(value) for value in values)


def _polish_runtime_message(value: str) -> str:
    return (
        value.replace("hotas_bridge_config_v3.json", "Workspace configuration")
        .replace("runtime truth", "runtime status")
        .replace("output_verified", "output verified")
        .replace("live_verified", "live checks passed")
        .replace("blocked_missing_device", "waiting for HOTAS input")
        .replace("no_supported_device", "no supported HOTAS detected")
    )


def _polish_mode(value: str) -> str:
    return {
        "simulated": "Simulation",
        "hardware_only": "Hardware only",
        "output_only": "Output only",
        "full_live": "Full live",
        "unavailable": "Unavailable",
    }.get(value, value.replace("_", " ").title())


def _selected_mode_label(workspace: WorkspaceConfig) -> str:
    active: list[str] = []
    if workspace.modes.precision_hold_buttons:
        active.append("Precision")
    if workspace.modes.combat_trigger_buttons or workspace.modes.combat_zoom_aim_buttons or workspace.modes.combat_extra_buttons:
        active.append("Combat")
    return ", ".join(active) if active else "No mode selected"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]
