from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from shared_core.models.mappings import AxisMapping, ButtonMapping, HatMapping
from shared_core.models.runtime import (
    InputStatus,
    OutputStatus,
    RuntimePreflightStatus,
    RuntimeTruth,
)
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.runtime_bridge import RuntimeBridge
from shared_core.runtime.setup_guidance import OFFICIAL_THRUSTMASTER_SUPPORT_PAGE
from v3_app.services.app_state import AppState
from v3_app.ui.status_chips import action_button, status_chip


OnDirty = Callable[[str], None]
OnStatus = Callable[[str], None]


class MappingPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        on_dirty: OnDirty | None = None,
        on_status: OnStatus | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("mappingPage")
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._on_dirty = on_dirty
        self._on_status = on_status
        self._snapshot = RuntimeBridge(
            preflight_status=self._runtime_status,
            deterministic_simulation=True,
        ).snapshot()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)

        root.addWidget(self._build_intro())
        root.addWidget(self._build_chip_row())

        top_cards = QHBoxLayout()
        top_cards.setSpacing(18)
        top_cards.addWidget(self._build_routing_overview_card(), 1)
        top_cards.addWidget(self._build_live_route_summary_card(), 1)
        root.addLayout(top_cards)

        root.addWidget(self._build_runtime_preflight_card())
        root.addWidget(self._build_axis_routing_card())

        lower_cards = QHBoxLayout()
        lower_cards.setSpacing(18)
        lower_cards.addWidget(self._build_button_routing_card(), 1)
        lower_cards.addWidget(self._build_hat_routing_card(), 1)
        root.addLayout(lower_cards)
        root.addStretch(1)

    def _build_intro(self) -> QWidget:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Mapping")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Map raw HOTAS axes, buttons, and hats to the bridge outputs that drive vJoy.")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        helper = QLabel(
            "This workspace controls the raw routing layer. The selected profile still owns the mappings, "
            "so any changes here follow the same safe draft flow as the rest of V3."
        )
        helper.setObjectName("pageBody")
        helper.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(helper)
        return block

    def _build_chip_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(status_chip("Current Workspace", tone="success"))
        layout.addWidget(status_chip(self._runtime_chip_label(), tone=self._state.runtime.tone))
        layout.addWidget(status_chip("Mapping Ready", tone="success"))
        if self._runtime_status.input.status is InputStatus.MISSING:
            layout.addWidget(status_chip("HOTAS Not Connected", tone="warning"))
        if self._runtime_status.output.status is OutputStatus.VJOY_DETECTED:
            layout.addWidget(status_chip("vJoy Detected", tone="caution"))
            layout.addWidget(status_chip("Output Unverified", tone="warning"))
        layout.addStretch(1)
        return row

    def _build_routing_overview_card(self) -> QWidget:
        card = self._card("routingOverviewCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Routing Overview")
        title.setObjectName("cardTitle")
        body = QLabel("Quick reading of the active route counts and any conflicts worth fixing.")
        body.setObjectName("cardBody")
        body.setWordWrap(True)

        counts = QGridLayout()
        counts.setHorizontalSpacing(18)
        counts.setVerticalSpacing(10)
        self._add_count_row(counts, 0, "Axis Routes", "axisRouteCount", len(self._workspace.mappings.axis_routes))
        self._add_count_row(counts, 1, "Button Routes", "buttonRouteCount", len(self._workspace.mappings.button_routes))
        self._add_count_row(counts, 2, "Hat Routes", "hatRouteCount", len(self._workspace.mappings.hat_routes))

        note = QLabel(
            "Axis, button, and hat routes are unique. "
            "Battlefield-safe runtime routing still remaps RX / RY / RZ / SL0 behind the scenes when needed."
        )
        note.setObjectName("routingOverviewNote")
        note.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addLayout(counts)
        layout.addStretch(1)
        layout.addWidget(note)
        return card

    def _build_live_route_summary_card(self) -> QWidget:
        card = self._card("liveRouteSummaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(12)

        title = QLabel("Live Route Summary")
        title.setObjectName("cardTitle")
        body = QLabel("See how the active workspace is currently landing on runtime vJoy outputs.")
        body.setObjectName("cardBody")
        body.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(body)

        rows = QGridLayout()
        rows.setHorizontalSpacing(18)
        rows.setVerticalSpacing(8)
        for index, route in enumerate(self._workspace.mappings.axis_routes):
            name = QLabel(route.function_name)
            name.setObjectName("tableMutedText")
            value = QLabel(_route_summary(route))
            value.setObjectName("routeSummaryValue")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            rows.addWidget(name, index, 0)
            rows.addWidget(value, index, 1)
        layout.addLayout(rows)

        note = QLabel(self._runtime_route_note())
        note.setObjectName("cardBody")
        note.setWordWrap(True)
        layout.addWidget(note)
        return card

    def _build_runtime_preflight_card(self) -> QWidget:
        card = self._card("runtimePreflightCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Runtime Setup / Preflight")
        title.setObjectName("cardTitle")
        header.addWidget(title)
        header.addStretch(1)
        preflight = action_button("Run Preflight Check", object_name="runPreflightButton")
        preflight.clicked.connect(
            lambda: self._status_message(
                f"Preflight status: {self._runtime_truth_label()}; output writes verified: "
                f"{str(self._runtime_status.live_output_writes_verified).lower()}."
            )
        )
        simulation = action_button("Use Simulation Mode", object_name="useSimulationModeButton")
        simulation.clicked.connect(
            lambda: self._status_message("Simulation mode remains available without HOTAS polling or vJoy writes.")
        )
        header.addWidget(preflight)
        header.addWidget(simulation)
        guide = action_button("Open Runtime Setup Guide", object_name="runtimeSetupGuideButton")
        guide.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(_project_root() / "docs" / "HelmForge" / "runtime-preflight-and-vjoy-setup.md"))
            )
        )
        thrustmaster = action_button(
            "Open Official Thrustmaster Support Page",
            object_name="openThrustmasterSupportButton",
        )
        thrustmaster.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(OFFICIAL_THRUSTMASTER_SUPPORT_PAGE)))
        header.addWidget(guide)
        header.addWidget(thrustmaster)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        rows = (
            ("Physical HOTAS target", "Thrustmaster T-Flight HOTAS One / Thrustmaster T.Flight Hotas One"),
            ("Input device status", self._input_status_label()),
            ("Output / vJoy status", self._output_status_label()),
            ("Runtime truth", self._runtime_truth_label()),
            ("Output verification", f"Output writes verified: {str(self._runtime_status.live_output_writes_verified).lower()}"),
        )
        for index, (label, value) in enumerate(rows):
            key = QLabel(label)
            key.setObjectName("tableMutedText")
            val = QLabel(value)
            val.setObjectName("routeSummaryValue")
            val.setWordWrap(True)
            grid.addWidget(key, index, 0)
            grid.addWidget(val, index, 1)

        caution = QLabel(
            "The UI can edit the mapping workspace while the future Bridge owns real-time input, processing, and output writes."
        )
        caution.setObjectName("cardBody")
        caution.setWordWrap(True)

        layout.addLayout(header)
        layout.addLayout(grid)
        layout.addWidget(caution)
        return card

    def _build_axis_routing_card(self) -> QWidget:
        card = self._card("axisRoutingCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Axis Routing")
        title.setObjectName("cardTitle")
        body = QLabel("Assign each control axis to the raw HOTAS channel it reads from and the logical vJoy axis it should drive.")
        body.setObjectName("cardBody")
        body.setWordWrap(True)

        table = QTableWidget(len(self._workspace.mappings.axis_routes), 7)
        table.setObjectName("axisRoutingTable")
        table.setHorizontalHeaderLabels(
            ("Function", "Raw Axis", "Logical Output", "Runtime vJoy", "Invert", "Live Raw", "Live Output")
        )
        table.verticalHeader().hide()
        table.setAlternatingRowColors(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(300)

        for row, route in enumerate(self._workspace.mappings.axis_routes):
            raw_value = self._snapshot.raw_axis_values.get(route.function_name, route.live_raw_value)
            output_value = self._snapshot.final_output_values.get(route.function_name, route.live_output_value)
            values = (
                route.function_name,
                route.raw_axis_channel,
                route.logical_output,
                route.runtime_vjoy_output,
                "",
                _signed(raw_value),
                _signed(output_value),
            )
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
            checkbox = QCheckBox()
            checkbox.setObjectName(f"invert_{route.function_name.lower().replace(' ', '_')}")
            checkbox.setChecked(route.invert)
            checkbox.stateChanged.connect(
                lambda _state, axis=route.function_name: self._mark_dirty(f"Mapping edit staged for {axis} invert.")
            )
            table.setCellWidget(row, 4, checkbox)

        table.resizeColumnsToContents()
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(table)
        return card

    def _build_button_routing_card(self) -> QWidget:
        card = self._card("buttonRoutingCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Button Routing")
        title.setObjectName("cardTitle")
        body = QLabel("Map each HOTAS button to the vJoy button that should fire on output.")
        body.setObjectName("cardBody")
        body.setWordWrap(True)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        for text, name in (
            ("Add Route", "addButtonRouteButton"),
            ("Remove Selected", "removeButtonRouteButton"),
            ("Reset 1:1", "resetButtonRoutesButton"),
        ):
            button = action_button(text, object_name=name)
            button.clicked.connect(lambda _checked=False, label=text: self._status_message(f"{label} is reserved for a later mapping edit phase."))
            actions.addWidget(button)
        actions.addStretch(1)

        table = QTableWidget(len(self._workspace.mappings.button_routes), 4)
        table.setObjectName("buttonRoutingTable")
        table.setHorizontalHeaderLabels(("HOTAS Button", "vJoy Button", "Raw", "Output"))
        table.verticalHeader().hide()
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(360)
        for row, route in enumerate(self._workspace.mappings.button_routes):
            for column, value in enumerate(_button_values(route)):
                table.setItem(row, column, QTableWidgetItem(value))
        table.resizeColumnsToContents()

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addLayout(actions)
        layout.addWidget(table)
        return card

    def _build_hat_routing_card(self) -> QWidget:
        card = self._card("hatRoutingCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Hat Routing")
        title.setObjectName("cardTitle")
        body = QLabel("Drive a vJoy POV and optional directional buttons from each HOTAS hat switch.")
        body.setObjectName("cardBody")
        body.setWordWrap(True)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        for text, name in (
            ("Add Hat", "addHatRouteButton"),
            ("Remove Selected", "removeHatRouteButton"),
        ):
            button = action_button(text, object_name=name)
            button.clicked.connect(lambda _checked=False, label=text: self._status_message(f"{label} is reserved for a later hat-routing edit phase."))
            actions.addWidget(button)
        actions.addStretch(1)

        table = QTableWidget(len(self._workspace.mappings.hat_routes), 7)
        table.setObjectName("hatRoutingTable")
        table.setHorizontalHeaderLabels(("HOTAS Hat", "vJoy POV", "Up", "Right", "Down", "Left", "Live"))
        table.verticalHeader().hide()
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(220)
        for row, route in enumerate(self._workspace.mappings.hat_routes):
            for column, value in enumerate(_hat_values(route, self._snapshot.hat_state)):
                table.setItem(row, column, QTableWidgetItem(value))
        table.resizeColumnsToContents()

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addLayout(actions)
        layout.addWidget(table)
        return card

    def _add_count_row(self, layout: QGridLayout, row: int, label: str, object_name: str, value: int) -> None:
        name = QLabel(label)
        name.setObjectName("tableMutedText")
        count = QLabel(str(value))
        count.setObjectName(object_name)
        count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(name, row, 0)
        layout.addWidget(count, row, 1)

    def _runtime_chip_label(self) -> str:
        if self._runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DEVICE:
            return "Runtime Simulated"
        if self._runtime_status.truth is RuntimeTruth.DETECTED_UNVERIFIED:
            return "Runtime Idle"
        return self._state.runtime.runtime_card_label

    def _runtime_route_note(self) -> str:
        if self._runtime_status.live_output_writes_verified:
            return "Output writes are verified by the runtime backend."
        if self._runtime_status.mode.value == "simulated":
            return (
                "Simulation mode is active. Live values are simulated and output writes are not verified. "
                "Runtime is not fully live; the Bridge will use this workspace when live runtime is available."
            )
        return (
            "Runtime is not fully live. You can still edit the mapping workspace, and the Bridge will use it when live runtime is available."
        )

    def _input_status_label(self) -> str:
        if self._runtime_status.input.status is InputStatus.DETECTED:
            return "T-Flight HOTAS One Detected"
        if self._runtime_status.input.status is InputStatus.ERROR:
            return "Input Error"
        if self._state.runtime.driver_detected:
            return "HOTAS Not Connected"
        return "Thrustmaster Driver Unknown"

    def _output_status_label(self) -> str:
        if self._runtime_status.output.status is OutputStatus.VJOY_MISSING:
            return "vJoy Missing"
        if self._runtime_status.output.status is OutputStatus.OUTPUT_ERROR:
            return "Output Error"
        if self._runtime_status.output.status is OutputStatus.OUTPUT_VERIFIED and self._runtime_status.live_output_writes_verified:
            return "vJoy Detected, output writes verified"
        if self._runtime_status.output.status is OutputStatus.VJOY_DETECTED:
            return "vJoy Detected, Output Unverified"
        return "Output Not Checked"

    def _runtime_truth_label(self) -> str:
        return {
            RuntimeTruth.SIMULATED: "simulated",
            RuntimeTruth.DETECTED_UNVERIFIED: "detected_unverified / Detected Unverified",
            RuntimeTruth.LIVE_VERIFIED: "live_verified",
            RuntimeTruth.BLOCKED_MISSING_DRIVER: "blocked_missing_driver",
            RuntimeTruth.BLOCKED_MISSING_DEVICE: "blocked_missing_device",
            RuntimeTruth.ERROR: "error",
        }[self._runtime_status.truth]

    def _mark_dirty(self, message: str) -> None:
        if self._on_dirty is not None:
            self._on_dirty(message)

    def _status_message(self, message: str) -> None:
        if self._on_status is not None:
            self._on_status(message)

    @staticmethod
    def _card(object_name: str) -> QFrame:
        card = QFrame()
        card.setObjectName(object_name)
        card.setFrameShape(QFrame.Shape.NoFrame)
        return card


def _route_summary(route: AxisMapping) -> str:
    raw = route.raw_axis_channel.lower()
    return f"Raw {raw} -> {route.logical_output} -> {route.runtime_vjoy_output}"


def _button_values(route: ButtonMapping) -> tuple[str, str, str, str]:
    raw = "Pressed" if route.raw_state else "Idle"
    output = "Pressed" if route.output_state else "Idle"
    return (f"B{route.hotas_button}", str(route.output_button), raw, output)


def _hat_values(route: HatMapping, live_state: str) -> tuple[str, str, str, str, str, str, str]:
    return (
        str(route.hotas_hat),
        str(route.vjoy_pov),
        "" if route.up_button is None else str(route.up_button),
        "" if route.right_button is None else str(route.right_button),
        "" if route.down_button is None else str(route.down_button),
        "" if route.left_button is None else str(route.left_button),
        live_state or route.live_hat_state,
    )


def _signed(value: float) -> str:
    return f"{value:+.2f}"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]
