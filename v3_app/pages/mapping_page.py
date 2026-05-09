from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from shared_core.models.mappings import (
    AxisMapping,
    ButtonMapping,
    HatMapping,
    MappingConfig,
    default_button_mappings,
    default_hat_mappings,
)
from shared_core.models.runtime import (
    InputStatus,
    OutputStatus,
    RuntimePreflightStatus,
    RuntimeTruth,
)
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.hotas_input import (
    MissingPhysicalInputBackend,
    PhysicalInputBackend,
    PhysicalInputSnapshot,
    build_physical_input_diagnostics,
)
from shared_core.runtime.runtime_bridge import RuntimeBridge
from shared_core.runtime.setup_guidance import OFFICIAL_THRUSTMASTER_SUPPORT_PAGE
from shared_core.runtime.vjoy_output import (
    VirtualOutputBackend,
    VirtualOutputLoopSnapshot,
    VirtualOutputVerificationResult,
    VirtualOutputWriteLoop,
    build_virtual_output_diagnostics,
)
from v3_app.services.app_state import AppState
from v3_app.services.bridge_client import RuntimeFrameTelemetryPayload
from v3_app.services.hotas_diagram_model import (
    HotasDiagramControl,
    HotasDiagramModel,
    build_hotas_diagram_model,
    build_route_inspector,
    build_workspace_route_warnings,
    select_hotas_diagram_route,
)
from v3_app.services.physical_input_ui import (
    build_input_source_status,
    buttons_from_physical_snapshot,
    hat_from_physical_snapshot,
    raw_axes_from_physical_snapshot,
)
from v3_app.pages.page_helpers import apply_parameter_metadata, parameter_label, truth_notice
from v3_app.widgets.hotas_diagram import HotasDiagramWidget
from v3_app.ui.status_chips import action_button, status_chip


OnDirty = Callable[[str], None]
OnStatus = Callable[[str], None]
OnWorkspaceChanged = Callable[[WorkspaceConfig, str], None]

RAW_AXIS_OPTIONS = tuple(f"Axis {index}" for index in range(1, 9))
LOGICAL_OUTPUT_OPTIONS = ("X", "Y", "Z", "RX", "RY", "RZ", "SL0", "SL1")
RUNTIME_VJOY_OPTIONS = ("X(axis1)", "Y(axis2)", "Z(axis3)", "RX(axis4)", "RY(axis5)", "RZ(axis6)", "SL0", "SL1")
HOTAS_BUTTON_OPTIONS = tuple(f"B{index}" for index in range(1, 16))
VJOY_BUTTON_OPTIONS = tuple(str(index) for index in range(1, 21))
HAT_OPTIONS = ("1", "2")
POV_OPTIONS = ("1", "2", "3", "4")
DIRECTION_BUTTON_OPTIONS = ("None", *tuple(str(index) for index in range(0, 21)))


class MappingPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        on_dirty: OnDirty | None = None,
        on_status: OnStatus | None = None,
        on_workspace_changed: OnWorkspaceChanged | None = None,
        physical_input_backend: PhysicalInputBackend | None = None,
        selected_physical_input_device_id: str | None = None,
        physical_input_snapshot: PhysicalInputSnapshot | None = None,
        physical_input_clock: Callable[[], datetime] | None = None,
        physical_sample_stale_after_seconds: float = 2.0,
        virtual_output_backend: VirtualOutputBackend | None = None,
        virtual_output_verification: VirtualOutputVerificationResult | None = None,
        virtual_output_loop: VirtualOutputWriteLoop | VirtualOutputLoopSnapshot | None = None,
        runtime_frame: RuntimeFrameTelemetryPayload | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("mappingPage")
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._on_dirty = on_dirty
        self._on_status = on_status
        self._on_workspace_changed = on_workspace_changed
        self._physical_input_backend = physical_input_backend or MissingPhysicalInputBackend()
        self._physical_input_snapshot = physical_input_snapshot
        input_now = physical_input_clock() if physical_input_clock is not None else (
            physical_input_snapshot.sampled_at if physical_input_snapshot is not None else None
        )
        self._input_source_status = build_input_source_status(
            backend=self._physical_input_backend,
            selected_device_id=selected_physical_input_device_id,
            latest_snapshot=physical_input_snapshot,
            now=input_now,
            stale_after_seconds=physical_sample_stale_after_seconds,
        )
        self._physical_input_diagnostics = build_physical_input_diagnostics(
            self._physical_input_backend,
            selected_device_id=selected_physical_input_device_id,
            latest_snapshot=physical_input_snapshot,
        )
        self._virtual_output_diagnostics = build_virtual_output_diagnostics(
            backend=virtual_output_backend,
            verification=virtual_output_verification,
        )
        self._virtual_output_loop_snapshot = _virtual_output_loop_snapshot(virtual_output_loop)
        self._runtime_frame = runtime_frame
        self._physical_raw_axes = (
            raw_axes_from_physical_snapshot(physical_input_snapshot)
            if physical_input_snapshot is not None and self._input_source_status.is_fresh_physical_sample
            else None
        )
        self._snapshot = RuntimeBridge(
            preflight_status=self._runtime_status,
            deterministic_simulation=True,
        ).snapshot()
        self._axis_route_labels: list[QLabel] = []
        self._count_labels: dict[str, QLabel] = {}
        self._status_chips: dict[str, QLabel] = {}
        self._runtime_preflight_rows: dict[str, QLabel] = {}
        self._axis_table: QTableWidget | None = None
        self._button_table: QTableWidget | None = None
        self._hat_table: QTableWidget | None = None
        self._hotas_diagram_widget: HotasDiagramWidget | None = None
        self._hotas_diagram_model: HotasDiagramModel | None = None
        self._route_warnings = build_workspace_route_warnings(self._workspace)
        self._selected_route_control_id = "axis_roll"
        self._syncing_route_selection = False
        self._route_inspector_labels: dict[str, QLabel] = {}
        self._change_mapping_button: QPushButton | None = None
        self._route_editor_panel: QFrame | None = None
        self._route_editor_layout: QVBoxLayout | None = None
        self._route_editor_dirty_label: QLabel | None = None
        self._route_editor_preview_label: QLabel | None = None
        self._route_editor_route_type: str | None = None
        self._route_editor_route_row: int | None = None
        self._route_editor_baseline: AxisMapping | ButtonMapping | HatMapping | None = None
        self._route_filter = "All"
        self._route_filter_buttons: dict[str, QPushButton] = {}
        self.setProperty("routeFilter", self._route_filter)

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

        root.addWidget(self._build_hotas_diagram_card())
        root.addWidget(self._build_runtime_preflight_card())
        root.addWidget(self._build_axis_routing_card())

        lower_cards = QHBoxLayout()
        lower_cards.setSpacing(18)
        lower_cards.addWidget(self._build_button_routing_card(), 1)
        lower_cards.addWidget(self._build_hat_routing_card(), 1)
        root.addLayout(lower_cards)
        self._apply_route_selection(self._selected_route_control_id, update_table=True)
        root.addStretch(1)

    def _build_intro(self) -> QWidget:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Mapping")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Map raw HOTAS axes, buttons, and hats to the bridge output intent path.")
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
        layout.addWidget(
            truth_notice(
                "Diagram selection, table selection, and Change Mapping all reflect the same selected route. "
                "Mapping edits remain workspace/config draft only. Output intent is not output write proof; "
                "Save Workspace required before draft routes are persisted.",
                object_name="mappingPolishTruthNotice",
            )
        )
        return block

    def _build_chip_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(status_chip("Current Workspace", tone="success"))
        runtime = status_chip(self._runtime_chip_label(), tone=self._state.runtime.tone)
        hotas = status_chip("HOTAS Not Connected", tone="warning")
        vjoy = status_chip("vJoy Detected", tone="caution")
        output = status_chip("Output Unverified", tone="warning")
        self._status_chips = {
            "runtime": runtime,
            "hotas": hotas,
            "vjoy": vjoy,
            "output": output,
        }
        layout.addWidget(runtime)
        layout.addWidget(status_chip("Mapping Ready", tone="success"))
        layout.addWidget(hotas)
        layout.addWidget(vjoy)
        layout.addWidget(output)
        self._refresh_status_chips()
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
        body = QLabel("See how the active workspace is currently landing on intended virtual output routes.")
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
            self._axis_route_labels.append(value)
        layout.addLayout(rows)

        note = QLabel(self._runtime_route_note())
        note.setObjectName("cardBody")
        note.setWordWrap(True)
        layout.addWidget(note)
        return card

    def _build_hotas_diagram_card(self) -> QWidget:
        card = self._card("hotasDiagramCard")
        card.setProperty("controlPolish", "post-rc-4d")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)

        title = QLabel("HOTAS Diagram")
        title.setObjectName("cardTitle")
        body = QLabel(
            "See the physical controls, current mappings, and output intent targets in one visual layout, with safe workspace draft edits."
        )
        body.setObjectName("cardBody")
        body.setWordWrap(True)

        self._hotas_diagram_model = self._create_hotas_diagram_model()
        self._hotas_diagram_widget = HotasDiagramWidget(self._hotas_diagram_model)
        self._hotas_diagram_widget.control_selected.connect(self._select_route_by_control_id)
        note = QLabel(
            "Inspect Mode keeps click/hover/select read-only for live values. Editing workspace draft routes changes config intent only. "
            "Read-only visual/diagnostic diagram values remain display-only; Output intent only - not live output proof. "
            "Output intent is not output write proof. Save Workspace required to persist changes."
        )
        note.setObjectName("hotasDiagramLegend")
        note.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(self._build_route_filter_row())
        layout.addWidget(self._hotas_diagram_widget)
        layout.addWidget(self._build_route_inspector_panel())
        layout.addWidget(self._build_route_editor_panel())
        if not (_project_root() / "tests" / "test_post_rc_2d_advanced_mapping_editor.py").exists():
            deferred = QLabel(
                "Post-RC 2D Advanced Mapping Editor is not merged here; Draft Review, undo/redo, "
                "route search, and presets stay deferred."
            )
            deferred.setObjectName("mappingDraftReviewDeferredNotice")
            deferred.setWordWrap(True)
            layout.addWidget(deferred)
        layout.addWidget(note)
        return card

    def _build_route_filter_row(self) -> QWidget:
        row = QWidget()
        row.setObjectName("routeFilterChips")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QLabel("Diagram focus")
        label.setObjectName("sectionLabel")
        layout.addWidget(label)
        for filter_name in ("All", "Axes", "Buttons", "Hats", "Mapped", "Unmapped", "Warnings", "Selected Profile"):
            button = action_button(filter_name, object_name=f"routeFilterChip{_filter_key(filter_name)}")
            button.setCheckable(True)
            button.setChecked(filter_name == self._route_filter)
            button.setProperty("routeFilterChip", True)
            button.clicked.connect(lambda _checked=False, name=filter_name: self._set_route_filter(name))
            self._route_filter_buttons[filter_name] = button
            layout.addWidget(button)
        layout.addStretch(1)
        return row

    def _build_route_inspector_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("routeInspectorPanel")
        panel.setFrameShape(QFrame.Shape.NoFrame)
        layout = QGridLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(7)

        title = QLabel("Route Inspector")
        title.setObjectName("sectionLabel")
        layout.addWidget(title, 0, 0, 1, 2)

        rows = (
            ("Workspace mode", "routeInspectorModeValue"),
            ("Route type", "routeInspectorTypeValue"),
            ("Selected physical input", "routeInspectorPhysicalValue"),
            ("Mapped virtual output", "routeInspectorOutputValue"),
            ("Mode/profile context", "routeInspectorContextValue"),
            ("Source of truth", "routeInspectorTruthValue"),
            ("Editable here", "routeInspectorEditableValue"),
            ("Conflict / warning", "routeInspectorConflictValue"),
            ("Verification notice", "routeInspectorVerificationValue"),
        )
        for row, (label, object_name) in enumerate(rows, start=1):
            key = QLabel(label)
            key.setObjectName("tableMutedText")
            value = QLabel("Unavailable")
            value.setObjectName(object_name)
            value.setProperty("inspectorValue", True)
            value.setWordWrap(True)
            self._route_inspector_labels[object_name] = value
            layout.addWidget(key, row, 0)
            layout.addWidget(value, row, 1)
        self._change_mapping_button = action_button("Change Mapping", object_name="changeMappingButton")
        self._change_mapping_button.clicked.connect(self._open_route_editor)
        layout.addWidget(self._change_mapping_button, len(rows) + 1, 1, Qt.AlignmentFlag.AlignLeft)
        return panel

    def _build_route_editor_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("routeEditorPanel")
        panel.setFrameShape(QFrame.Shape.NoFrame)
        panel.setHidden(True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)
        self._route_editor_panel = panel
        self._route_editor_layout = layout
        return panel

    def _build_runtime_preflight_card(self) -> QWidget:
        card = self._card("runtimePreflightCard")
        card.setProperty("controlPolish", "post-rc-4d")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(12)
        dashboard = QFrame(card)
        dashboard.setObjectName("mappingPreflightDashboardCard")
        dashboard.setProperty("uiRole", "preflightDashboard")
        dashboard.setProperty("tabSplitDeferred", True)
        dashboard.hide()

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
            ("Input source", self._input_source_status.source_label),
            ("Physical input backend", self._physical_input_diagnostics.physical_input_backend),
            ("Selected input device", self._physical_input_diagnostics.selected_input_device),
            ("Supported HOTAS", self._physical_input_diagnostics.supported_hotas),
            ("Input sampling", self._input_source_status.source_status),
            ("Last sample", self._physical_input_diagnostics.last_sample),
            ("Sample source", self._input_source_status.sample_source),
            ("Axis count", str(self._input_source_status.axis_count)),
            ("Button count", str(self._input_source_status.button_count)),
            ("Hat count", str(self._input_source_status.hat_count)),
            ("Runtime frame", _runtime_frame_status(self._runtime_frame)),
            ("Runtime frame source", _runtime_frame_source(self._runtime_frame)),
            ("Pipeline status", _runtime_frame_pipeline_status(self._runtime_frame)),
            ("Output intent ready", _runtime_frame_output_intent_ready(self._runtime_frame)),
            ("Runtime frame output backend", _runtime_frame_output_backend(self._runtime_frame)),
            ("Runtime frame output loop state", _runtime_frame_output_loop_state(self._runtime_frame)),
            ("Runtime frame last output write", _runtime_frame_last_output_write(self._runtime_frame)),
            ("Input proof", _runtime_frame_input_proof(self._runtime_frame)),
            ("Pipeline proof", _runtime_frame_pipeline_proof(self._runtime_frame)),
            ("Output proof", _runtime_frame_output_proof(self._runtime_frame)),
            ("Full Live Runtime Ready gate", _runtime_frame_ready_gate(self._runtime_frame)),
            ("Ready state", _runtime_frame_ready_state(self._runtime_frame)),
            ("Telemetry proof", _runtime_frame_telemetry_proof(self._runtime_frame)),
            ("Safety proof", _runtime_frame_safety_proof(self._runtime_frame)),
            ("Fake/real path", _runtime_frame_fake_or_real_path(self._runtime_frame)),
            ("Readiness evaluated", _runtime_frame_evaluated_at(self._runtime_frame)),
            ("Runtime candidate", _runtime_frame_candidate(self._runtime_frame)),
            ("Proof summary", _runtime_frame_proof_summary(self._runtime_frame)),
            ("Input device status", self._input_status_label()),
            ("Output / vJoy status", self._output_status_label()),
            ("Virtual output backend", self._virtual_output_diagnostics.virtual_output_backend),
            ("vJoy dependency", self._virtual_output_diagnostics.vjoy_dependency_status),
            ("vJoy device", self._virtual_output_diagnostics.vjoy_device_status),
            ("Selected output device", self._virtual_output_diagnostics.selected_output_device),
            ("Output device status", self._virtual_output_diagnostics.output_device_status),
            ("Output write status", self._virtual_output_diagnostics.output_write_status),
            ("Output loop state", _output_loop_state(self._virtual_output_loop_snapshot)),
            ("Output loop write count", _output_loop_write_count(self._virtual_output_loop_snapshot)),
            ("Neutral restore status", _output_loop_neutral_restore(self._virtual_output_loop_snapshot)),
            ("Output verification status", self._virtual_output_diagnostics.output_verification_status),
            ("Output verification source", self._virtual_output_diagnostics.output_verification_source),
            ("Fake output verified", str(self._virtual_output_diagnostics.fake_output_verified).lower()),
            ("Real output verified", str(self._virtual_output_diagnostics.real_output_verified).lower()),
            ("Last verification timestamp", self._virtual_output_diagnostics.last_verification_timestamp),
            ("Runtime truth", self._runtime_truth_label()),
            ("Output verified", str(self._output_verified()).lower()),
            ("Output verification", f"Output writes verified: {str(self._output_verified()).lower()}"),
            ("Full Live Runtime Ready", "false"),
        )
        for index, (label, value) in enumerate(rows):
            key = QLabel(label)
            key.setObjectName("tableMutedText")
            val = QLabel(value)
            val.setObjectName("routeSummaryValue")
            val.setWordWrap(True)
            self._runtime_preflight_rows[label] = val
            grid.addWidget(key, index, 0)
            grid.addWidget(val, index, 1)

        caution = QLabel(
            "Physical input samples are read-only when present. The UI can edit the mapping workspace while the "
            "future Bridge owns real-time processing. Phase 15C output loops require explicit enable and a verified backend; "
            "Phase 16D shows input, pipeline, output, telemetry, and safety proof separately. vJoy detection alone is not enough, "
            "runtime_frame output intent is not a vJoy write, fake/test paths are not real readiness, and Full Live Runtime Ready "
            "opens only when the central readiness gate has every required proof."
        )
        caution.setObjectName("cardBody")
        caution.setWordWrap(True)

        layout.addLayout(header)
        layout.addLayout(grid)
        layout.addWidget(caution)
        return card

    def update_runtime_status(self, runtime_status: RuntimePreflightStatus) -> None:
        self._runtime_status = runtime_status
        self._snapshot = RuntimeBridge(
            preflight_status=self._runtime_status,
            deterministic_simulation=True,
        ).snapshot()
        self._refresh_status_chips()
        updates = {
            "Input device status": self._input_status_label(),
            "Output / vJoy status": self._output_status_label(),
            "Runtime truth": self._runtime_truth_label(),
            "Output verified": str(self._output_verified()).lower(),
            "Output verification": f"Output writes verified: {str(self._output_verified()).lower()}",
            "Full Live Runtime Ready": str(
                self._runtime_status.truth is RuntimeTruth.LIVE_VERIFIED
                and self._runtime_status.live_output_writes_verified
            ).lower(),
        }
        for label, value in updates.items():
            row = self._runtime_preflight_rows.get(label)
            if row is not None:
                row.setText(value)

    def _refresh_status_chips(self) -> None:
        runtime = self._status_chips.get("runtime")
        if runtime is not None:
            runtime.setText(self._runtime_chip_label())
            runtime.setProperty("chipTone", self._state.runtime.tone)
        hotas = self._status_chips.get("hotas")
        if hotas is not None:
            hotas.setVisible(self._runtime_status.input.status is InputStatus.MISSING)
        vjoy = self._status_chips.get("vjoy")
        if vjoy is not None:
            vjoy.setVisible(self._runtime_status.output.status in {OutputStatus.VJOY_DETECTED, OutputStatus.OUTPUT_VERIFIED})
            vjoy.setText("vJoy Verified" if self._runtime_status.output.status is OutputStatus.OUTPUT_VERIFIED else "vJoy Detected")
            vjoy.setProperty(
                "chipTone",
                "success" if self._runtime_status.output.status is OutputStatus.OUTPUT_VERIFIED else "caution",
            )
        output = self._status_chips.get("output")
        if output is not None:
            output.setVisible(not self._runtime_status.live_output_writes_verified)

    def _build_axis_routing_card(self) -> QWidget:
        card = self._card("axisRoutingCard")
        card.setProperty("controlPolish", "post-rc-4d")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Axis Routing")
        title.setObjectName("cardTitle")
        body = QLabel("Assign each control axis to the raw HOTAS channel it reads from and the logical virtual axis it intends to drive.")
        body.setObjectName("cardBody")
        body.setWordWrap(True)

        self._axis_table = QTableWidget(len(self._workspace.mappings.axis_routes), 7)
        table = self._axis_table
        table.setObjectName("axisRoutingTable")
        live_raw_label = "Live Raw (Physical input sample)" if self._physical_raw_axes is not None else "Live Raw"
        table.setHorizontalHeaderLabels(
            ("Function", "Raw Axis", "Logical Output", "Output Intent Axis", "Invert", live_raw_label, "Final Intent")
        )
        self._configure_table(table, minimum_height=320)
        self._populate_axis_table()
        table.currentCellChanged.connect(
            lambda row, _column, _old_row, _old_column: self._select_route_from_table("axisRoutingTable", row)
        )

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(table)
        return card

    def _build_button_routing_card(self) -> QWidget:
        card = self._card("buttonRoutingCard")
        card.setProperty("controlPolish", "post-rc-4d")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Button Routing")
        title.setObjectName("cardTitle")
        body = QLabel("Map each HOTAS button to the virtual button intended for output.")
        body.setObjectName("cardBody")
        body.setWordWrap(True)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        add_button = action_button("Add Route", object_name="addButtonRouteButton")
        remove_button = action_button("Remove Selected", object_name="removeButtonRouteButton")
        reset_button = action_button("Reset 1:1", object_name="resetButtonRoutesButton")
        add_button.clicked.connect(self._add_button_route)
        remove_button.clicked.connect(self._remove_selected_button_route)
        reset_button.clicked.connect(self._reset_button_routes)
        actions.addWidget(add_button)
        actions.addWidget(remove_button)
        actions.addWidget(reset_button)
        actions.addStretch(1)

        self._button_table = QTableWidget(len(self._workspace.mappings.button_routes), 4)
        table = self._button_table
        table.setObjectName("buttonRoutingTable")
        table.setHorizontalHeaderLabels(("HOTAS Button", "vJoy Button", "Raw", "Output"))
        self._configure_table(table, minimum_height=360)
        self._populate_button_table()
        table.currentCellChanged.connect(
            lambda row, _column, _old_row, _old_column: self._select_route_from_table("buttonRoutingTable", row)
        )

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addLayout(actions)
        layout.addWidget(table)
        return card

    def _build_hat_routing_card(self) -> QWidget:
        card = self._card("hatRoutingCard")
        card.setProperty("controlPolish", "post-rc-4d")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Hat Routing")
        title.setObjectName("cardTitle")
        body = QLabel("Map each HOTAS hat switch to an intended virtual POV and optional directional buttons.")
        body.setObjectName("cardBody")
        body.setWordWrap(True)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        add_button = action_button("Add Hat", object_name="addHatRouteButton")
        remove_button = action_button("Remove Selected", object_name="removeHatRouteButton")
        add_button.clicked.connect(self._add_hat_route)
        remove_button.clicked.connect(self._remove_selected_hat_route)
        actions.addWidget(add_button)
        actions.addWidget(remove_button)
        actions.addStretch(1)

        self._hat_table = QTableWidget(len(self._workspace.mappings.hat_routes), 7)
        table = self._hat_table
        table.setObjectName("hatRoutingTable")
        table.setHorizontalHeaderLabels(("HOTAS Hat", "vJoy POV", "Up", "Right", "Down", "Left", "Live"))
        self._configure_table(table, minimum_height=240)
        self._populate_hat_table()
        table.currentCellChanged.connect(
            lambda row, _column, _old_row, _old_column: self._select_route_from_table("hatRoutingTable", row)
        )

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addLayout(actions)
        layout.addWidget(table)
        return card

    def _populate_axis_table(self) -> None:
        if self._axis_table is None:
            return
        table = self._axis_table
        table.setRowCount(len(self._workspace.mappings.axis_routes))
        for row, route in enumerate(self._workspace.mappings.axis_routes):
            raw_value = (
                self._physical_raw_axes.get(route.function_name, route.live_raw_value)
                if self._physical_raw_axes is not None
                else self._snapshot.raw_axis_values.get(route.function_name, route.live_raw_value)
            )
            output_value = self._snapshot.final_output_values.get(route.function_name, route.live_output_value)
            self._set_text_item(table, row, 0, route.function_name)
            self._set_combo_cell(
                table,
                row,
                1,
                object_name=f"axisRaw_{_key(route.function_name)}",
                options=RAW_AXIS_OPTIONS,
                current=route.raw_axis_channel,
                on_changed=lambda value, index=row: self._update_axis_route(index, raw_axis_channel=value),
                metadata_id="mapping.raw_axis",
            )
            self._set_combo_cell(
                table,
                row,
                2,
                object_name=f"axisLogical_{_key(route.function_name)}",
                options=LOGICAL_OUTPUT_OPTIONS,
                current=route.logical_output,
                on_changed=lambda value, index=row: self._update_axis_route(index, logical_output=value),
                metadata_id="mapping.logical_output",
            )
            self._set_combo_cell(
                table,
                row,
                3,
                object_name=f"axisRuntime_{_key(route.function_name)}",
                options=RUNTIME_VJOY_OPTIONS,
                current=route.runtime_vjoy_output,
                on_changed=lambda value, index=row: self._update_axis_route(index, runtime_vjoy_output=value),
                metadata_id="mapping.runtime_output_axis",
            )
            checkbox = QCheckBox()
            checkbox.setObjectName(f"invert_{_key(route.function_name)}")
            apply_parameter_metadata(checkbox, "mapping.invert_axis")
            checkbox.setChecked(route.invert)
            checkbox.stateChanged.connect(
                lambda _state, index=row: self._update_axis_route(index, invert=bool(self._axis_table.cellWidget(index, 4).isChecked()))
            )
            table.setItem(row, 4, QTableWidgetItem("true" if route.invert else "false"))
            table.setCellWidget(row, 4, checkbox)
            self._set_text_item(table, row, 5, _signed(raw_value))
            self._set_text_item(table, row, 6, _signed(output_value))
        self._apply_table_warning_state(table)
        table.resizeColumnsToContents()

    def _populate_button_table(self) -> None:
        if self._button_table is None:
            return
        table = self._button_table
        table.setRowCount(len(self._workspace.mappings.button_routes))
        for row, route in enumerate(self._workspace.mappings.button_routes):
            self._set_combo_cell(
                table,
                row,
                0,
                object_name=f"buttonHotas_{row}",
                options=HOTAS_BUTTON_OPTIONS,
                current=f"B{route.hotas_button}",
                on_changed=lambda value, index=row: self._update_button_route(index, hotas_button=_parse_button(value)),
                metadata_id="mapping.hotas_button",
            )
            self._set_combo_cell(
                table,
                row,
                1,
                object_name=f"buttonVjoy_{row}",
                options=VJOY_BUTTON_OPTIONS,
                current=str(route.output_button),
                on_changed=lambda value, index=row: self._update_button_route(index, output_button=int(value)),
                metadata_id="mapping.output_button",
            )
            self._set_text_item(table, row, 2, "Pressed" if route.raw_state else "Idle")
            self._set_text_item(table, row, 3, "Pressed" if route.output_state else "Idle")
        self._apply_table_warning_state(table)
        table.resizeColumnsToContents()

    def _populate_hat_table(self) -> None:
        if self._hat_table is None:
            return
        table = self._hat_table
        table.setRowCount(len(self._workspace.mappings.hat_routes))
        for row, route in enumerate(self._workspace.mappings.hat_routes):
            self._set_combo_cell(
                table,
                row,
                0,
                object_name=f"hatHotas_{row}",
                options=HAT_OPTIONS,
                current=str(route.hotas_hat),
                on_changed=lambda value, index=row: self._update_hat_route(index, hotas_hat=int(value)),
                metadata_id="mapping.hotas_hat",
            )
            self._set_combo_cell(
                table,
                row,
                1,
                object_name=f"hatPov_{row}",
                options=POV_OPTIONS,
                current=str(route.vjoy_pov),
                on_changed=lambda value, index=row: self._update_hat_route(index, vjoy_pov=int(value)),
                metadata_id="mapping.output_pov",
            )
            for column, field_name, current in (
                (2, "up_button", route.up_button),
                (3, "right_button", route.right_button),
                (4, "down_button", route.down_button),
                (5, "left_button", route.left_button),
            ):
                self._set_combo_cell(
                    table,
                    row,
                    column,
                    object_name=f"hat{field_name.removesuffix('_button').title()}_{row}",
                    options=DIRECTION_BUTTON_OPTIONS,
                    current="None" if current is None else str(current),
                    on_changed=lambda value, index=row, field=field_name: self._update_hat_route(index, **{field: _parse_direction_button(value)}),
                    metadata_id="mapping.hat_direction_button",
                )
            self._set_text_item(table, row, 6, self._snapshot.hat_state or route.live_hat_state)
        self._apply_table_warning_state(table)
        table.resizeColumnsToContents()

    def _update_axis_route(self, row: int, **changes) -> None:
        routes = list(self._workspace.mappings.axis_routes)
        if not 0 <= row < len(routes):
            return
        routes[row] = replace(routes[row], **changes)
        self._set_mapping_config(
            replace(self._workspace.mappings, axis_routes=tuple(routes)),
            f"Mapping edit staged for {routes[row].function_name} axis route.",
        )
        if self._axis_table is not None:
            for field, column in (("raw_axis_channel", 1), ("logical_output", 2), ("runtime_vjoy_output", 3), ("invert", 4)):
                if field in changes:
                    value = changes[field]
                    self._set_text_item(self._axis_table, row, column, "true" if value is True else "false" if value is False else str(value))
        self._refresh_route_summary()

    def _update_button_route(self, row: int, **changes) -> None:
        routes = list(self._workspace.mappings.button_routes)
        if not 0 <= row < len(routes):
            return
        routes[row] = replace(routes[row], **changes)
        self._set_mapping_config(
            replace(self._workspace.mappings, button_routes=tuple(routes)),
            f"Mapping edit staged for button route {row + 1}.",
        )
        if self._button_table is not None:
            if "hotas_button" in changes:
                self._set_text_item(self._button_table, row, 0, f"B{changes['hotas_button']}")
            if "output_button" in changes:
                self._set_text_item(self._button_table, row, 1, str(changes["output_button"]))
        self._refresh_counts()

    def _update_hat_route(self, row: int, **changes) -> None:
        routes = list(self._workspace.mappings.hat_routes)
        if not 0 <= row < len(routes):
            return
        routes[row] = replace(routes[row], **changes)
        self._set_mapping_config(
            replace(self._workspace.mappings, hat_routes=tuple(routes)),
            f"Mapping edit staged for hat route {row + 1}.",
        )
        self._refresh_counts()

    def _add_button_route(self) -> None:
        routes = list(self._workspace.mappings.button_routes)
        used_hotas = {route.hotas_button for route in routes}
        used_outputs = {route.output_button for route in routes}
        hotas = next((index for index in range(1, 16) if index not in used_hotas), None)
        output = next((index for index in range(1, 21) if index not in used_outputs), None)
        if hotas is None or output is None:
            self._status_message("No unmapped HOTAS/vJoy button slot is available.")
            return
        routes.append(ButtonMapping(hotas, output))
        routes.sort(key=lambda route: route.hotas_button)
        self._set_mapping_config(
            replace(self._workspace.mappings, button_routes=tuple(routes)),
            f"Added button route B{hotas} -> {output}.",
        )
        self._populate_button_table()
        self._refresh_counts()

    def _remove_selected_button_route(self) -> None:
        if self._button_table is None:
            return
        row = _selected_row(self._button_table)
        if row is None:
            self._status_message("Select a button route before removing it.")
            return
        routes = list(self._workspace.mappings.button_routes)
        if not 0 <= row < len(routes):
            return
        removed = routes.pop(row)
        self._set_mapping_config(
            replace(self._workspace.mappings, button_routes=tuple(routes)),
            f"Removed button route B{removed.hotas_button} -> {removed.output_button}.",
        )
        self._populate_button_table()
        self._refresh_counts()

    def _reset_button_routes(self) -> None:
        self._set_mapping_config(
            replace(self._workspace.mappings, button_routes=default_button_mappings()),
            "Reset button routing to B1-B15 -> vJoy 1-15.",
        )
        self._populate_button_table()
        self._refresh_counts()

    def _add_hat_route(self) -> None:
        if self._workspace.mappings.hat_routes:
            self._status_message("Hat route 1 is already present; additional hats are deferred until the schema needs them.")
            return
        self._set_mapping_config(
            replace(self._workspace.mappings, hat_routes=default_hat_mappings()),
            "Added default HOTAS Hat 1 -> vJoy POV 1 route.",
        )
        self._populate_hat_table()
        self._refresh_counts()

    def _remove_selected_hat_route(self) -> None:
        if self._hat_table is None:
            return
        row = _selected_row(self._hat_table)
        if row is None:
            self._status_message("Select a hat route before removing it.")
            return
        routes = list(self._workspace.mappings.hat_routes)
        if not 0 <= row < len(routes):
            return
        removed = routes.pop(row)
        self._set_mapping_config(
            replace(self._workspace.mappings, hat_routes=tuple(routes)),
            f"Removed HOTAS Hat {removed.hotas_hat} route.",
        )
        self._populate_hat_table()
        self._refresh_counts()

    def _set_route_filter(self, filter_name: str) -> None:
        self._route_filter = filter_name
        self.setProperty("routeFilter", filter_name)
        for name, button in self._route_filter_buttons.items():
            button.blockSignals(True)
            button.setChecked(name == filter_name)
            button.blockSignals(False)
        self._apply_route_filter()

    def _apply_route_filter(self) -> None:
        if self._hotas_diagram_widget is not None:
            self._hotas_diagram_widget.set_filter(self._route_filter)
        model = self._hotas_diagram_model or self._create_hotas_diagram_model()
        for control in model.routed_controls:
            if control.table_object_name is None or control.route_row is None:
                continue
            table = self._table_by_object_name(control.table_object_name)
            if table is None or not 0 <= control.route_row < table.rowCount():
                continue
            table.setRowHidden(control.route_row, not _route_filter_matches_control(control, self._route_filter))

    def _apply_table_warning_state(self, table: QTableWidget) -> None:
        for row in range(table.rowCount()):
            control_id = self._control_id_for_table_row(table.objectName(), row)
            warnings = tuple(
                warning for warning in self._route_warnings if warning.control_id == control_id
            )
            message = "; ".join(warning.message for warning in warnings)
            for column in range(table.columnCount()):
                item = table.item(row, column)
                if item is None:
                    continue
                if warnings:
                    item.setData(Qt.ItemDataRole.UserRole, "workspace-config-warning")
                    item.setToolTip(message)
                else:
                    item.setData(Qt.ItemDataRole.UserRole, None)
                    item.setToolTip("")

    def _refresh_table_warning_states(self) -> None:
        for table in (self._axis_table, self._button_table, self._hat_table):
            if table is not None:
                self._apply_table_warning_state(table)

    def _open_route_editor(self) -> None:
        context = self._selected_route_context()
        if context is None:
            self._status_message("Selected route is not editable in the Mapping workspace draft.")
            return
        control, route_type, row, route = context
        if not control.editable:
            self._status_message("Selected route is read-only in this Mapping workspace.")
            return
        self._render_route_editor(control, route_type, row, route)

    def _selected_route_context(self):
        model = self._hotas_diagram_model or self._create_hotas_diagram_model()
        selection = select_hotas_diagram_route(model, self._selected_route_control_id)
        control = next(
            (item for item in model.routed_controls if item.control_id == self._selected_route_control_id),
            None,
        )
        if selection is None or control is None or selection.route_row is None:
            return None
        route = self._route_at(selection.route_type, selection.route_row)
        if route is None:
            return None
        return control, selection.route_type, selection.route_row, route

    def _route_at(self, route_type: str, row: int):
        routes = self._routes_for_type(route_type)
        if routes is None or not 0 <= row < len(routes):
            return None
        return routes[row]

    def _routes_for_type(self, route_type: str):
        if route_type == "axis":
            return self._workspace.mappings.axis_routes
        if route_type == "button":
            return self._workspace.mappings.button_routes
        if route_type == "hat":
            return self._workspace.mappings.hat_routes
        return None

    def _render_route_editor(self, control: HotasDiagramControl, route_type: str, row: int, route) -> None:
        if self._route_editor_panel is None or self._route_editor_layout is None:
            return
        _clear_layout(self._route_editor_layout)
        self._route_editor_route_type = route_type
        self._route_editor_route_row = row
        self._route_editor_baseline = route

        header = QHBoxLayout()
        mode = QLabel("Editing workspace draft")
        mode.setObjectName("routeEditorModeLabel")
        mode.setProperty("inspectorValue", True)
        truth = QLabel("Output intent only - not live output proof")
        truth.setObjectName("routeEditorTruthNotice")
        truth.setWordWrap(True)
        header.addWidget(mode)
        header.addStretch(1)
        header.addWidget(truth)
        self._route_editor_layout.addLayout(header)

        persist = QLabel("Save Workspace required to persist changes")
        persist.setObjectName("routeEditorPersistNotice")
        persist.setWordWrap(True)
        self._route_editor_layout.addWidget(persist)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        if route_type == "axis" and isinstance(route, AxisMapping):
            self._render_axis_editor(grid, route)
        elif route_type == "button" and isinstance(route, ButtonMapping):
            self._render_button_editor(grid, route)
        elif route_type == "hat" and isinstance(route, HatMapping):
            self._render_hat_editor(grid, route)
        else:
            self._add_editor_readonly(
                grid,
                0,
                "Route",
                "Read-only: unsupported route shape is deferred.",
                "routeEditorUnsupportedValue",
            )
        self._route_editor_layout.addLayout(grid)

        self._route_editor_preview_label = QLabel("")
        self._route_editor_preview_label.setObjectName("routeEditorConflictPreview")
        self._route_editor_preview_label.setWordWrap(True)
        self._route_editor_layout.addWidget(self._route_editor_preview_label)

        self._route_editor_dirty_label = QLabel("Workspace draft unchanged - Save Workspace required after Apply")
        self._route_editor_dirty_label.setObjectName("routeEditorDirtyStateValue")
        self._route_editor_dirty_label.setWordWrap(True)
        self._route_editor_layout.addWidget(self._route_editor_dirty_label)

        actions = QHBoxLayout()
        apply = action_button("Apply to Draft", object_name="routeEditorApplyButton")
        cancel = action_button("Cancel", object_name="routeEditorCancelButton")
        revert = action_button("Revert Route", object_name="routeEditorRevertButton")
        apply.clicked.connect(self._apply_route_editor)
        cancel.clicked.connect(self._cancel_route_editor)
        revert.clicked.connect(self._revert_route_editor)
        actions.addWidget(apply)
        actions.addWidget(cancel)
        actions.addWidget(revert)
        actions.addStretch(1)
        self._route_editor_layout.addLayout(actions)

        self._route_editor_panel.setHidden(False)
        self._refresh_route_editor_preview()
        self._refresh_route_inspector(control)

    def _render_axis_editor(self, grid: QGridLayout, route: AxisMapping) -> None:
        self._add_editor_readonly(grid, 0, "Selected physical input", route.raw_axis_channel, "routeEditorPhysicalValue")
        self._add_editor_readonly(grid, 1, "Mapped function", route.function_name, "routeEditorFunctionValue")
        self._add_editor_combo(
            grid,
            2,
            "Physical/raw axis",
            route.raw_axis_channel,
            "routeEditorAxisRawCombo",
            RAW_AXIS_OPTIONS,
            "mapping.raw_axis",
        )
        self._add_editor_combo(
            grid,
            3,
            "Logical output",
            route.logical_output,
            "routeEditorAxisLogicalCombo",
            LOGICAL_OUTPUT_OPTIONS,
            "mapping.logical_output",
        )
        self._add_editor_combo(
            grid,
            4,
            "Output intent axis",
            route.runtime_vjoy_output,
            "routeEditorAxisOutputCombo",
            RUNTIME_VJOY_OPTIONS,
            "mapping.runtime_output_axis",
        )
        self._add_editor_checkbox(grid, 5, "Invert", route.invert, "routeEditorAxisInvertCheckbox", "mapping.invert_axis")

    def _render_button_editor(self, grid: QGridLayout, route: ButtonMapping) -> None:
        self._add_editor_readonly(grid, 0, "Physical button", f"B{route.hotas_button}", "routeEditorPhysicalValue")
        self._add_editor_readonly(
            grid,
            1,
            "Mapped function",
            f"Virtual button {route.output_button}",
            "routeEditorFunctionValue",
        )
        self._add_editor_combo(
            grid,
            2,
            "Output virtual button",
            str(route.output_button),
            "routeEditorButtonOutputCombo",
            VJOY_BUTTON_OPTIONS,
            "mapping.output_button",
        )

    def _render_hat_editor(self, grid: QGridLayout, route: HatMapping) -> None:
        self._add_editor_readonly(grid, 0, "Physical hat", f"Hat {route.hotas_hat}", "routeEditorPhysicalValue")
        self._add_editor_combo(
            grid,
            1,
            "POV/output target",
            str(route.vjoy_pov),
            "routeEditorHatPovCombo",
            POV_OPTIONS,
            "mapping.output_pov",
        )
        for row, label, field, current, object_name in (
            (2, "Up direction button", "up_button", route.up_button, "routeEditorHatUpButtonCombo"),
            (3, "Right direction button", "right_button", route.right_button, "routeEditorHatRightButtonCombo"),
            (4, "Down direction button", "down_button", route.down_button, "routeEditorHatDownButtonCombo"),
            (5, "Left direction button", "left_button", route.left_button, "routeEditorHatLeftButtonCombo"),
        ):
            self._add_editor_combo(
                grid,
                row,
                label,
                "None" if current is None else str(current),
                object_name,
                DIRECTION_BUTTON_OPTIONS,
                "mapping.hat_direction_button",
            )

    def _add_editor_readonly(
        self,
        grid: QGridLayout,
        row: int,
        label: str,
        value: str,
        object_name: str,
        metadata_id: str | None = None,
    ) -> QLabel:
        grid.addWidget(parameter_label(label, metadata_id=metadata_id), row, 0)
        field = QLabel(value)
        field.setObjectName(object_name)
        field.setProperty("inspectorValue", True)
        field.setWordWrap(True)
        grid.addWidget(field, row, 1)
        return field

    def _add_editor_combo(
        self,
        grid: QGridLayout,
        row: int,
        label: str,
        current: str,
        object_name: str,
        options: tuple[str, ...],
        metadata_id: str,
    ) -> QComboBox:
        grid.addWidget(parameter_label(label, metadata_id=metadata_id), row, 0)
        combo = QComboBox()
        combo.setObjectName(object_name)
        values = list(options)
        if current not in values:
            values.append(current)
        combo.addItems(tuple(dict.fromkeys(values)))
        apply_parameter_metadata(combo, metadata_id)
        combo.setCurrentText(current)
        combo.currentTextChanged.connect(lambda _value: self._refresh_route_editor_preview())
        grid.addWidget(combo, row, 1)
        return combo

    def _add_editor_checkbox(
        self,
        grid: QGridLayout,
        row: int,
        label: str,
        checked: bool,
        object_name: str,
        metadata_id: str,
    ) -> QCheckBox:
        grid.addWidget(parameter_label(label, metadata_id=metadata_id), row, 0)
        checkbox = QCheckBox()
        checkbox.setObjectName(object_name)
        checkbox.setChecked(checked)
        apply_parameter_metadata(checkbox, metadata_id)
        checkbox.stateChanged.connect(lambda _state: self._refresh_route_editor_preview())
        grid.addWidget(checkbox, row, 1)
        return checkbox

    def _route_from_editor(self):
        if self._route_editor_baseline is None or self._route_editor_route_type is None:
            return None
        if self._route_editor_route_type == "axis" and isinstance(self._route_editor_baseline, AxisMapping):
            raw = self._editor_combo_text("routeEditorAxisRawCombo", self._route_editor_baseline.raw_axis_channel)
            logical = self._editor_combo_text("routeEditorAxisLogicalCombo", self._route_editor_baseline.logical_output)
            output = self._editor_combo_text("routeEditorAxisOutputCombo", self._route_editor_baseline.runtime_vjoy_output)
            invert = self._editor_checkbox_checked("routeEditorAxisInvertCheckbox", self._route_editor_baseline.invert)
            return replace(
                self._route_editor_baseline,
                raw_axis_channel=raw,
                logical_output=logical,
                runtime_vjoy_output=output,
                invert=invert,
            )
        if self._route_editor_route_type == "button" and isinstance(self._route_editor_baseline, ButtonMapping):
            output = int(self._editor_combo_text("routeEditorButtonOutputCombo", str(self._route_editor_baseline.output_button)))
            return replace(self._route_editor_baseline, output_button=output)
        if self._route_editor_route_type == "hat" and isinstance(self._route_editor_baseline, HatMapping):
            return replace(
                self._route_editor_baseline,
                vjoy_pov=int(self._editor_combo_text("routeEditorHatPovCombo", str(self._route_editor_baseline.vjoy_pov))),
                up_button=_parse_direction_button(self._editor_combo_text("routeEditorHatUpButtonCombo", _direction_text(self._route_editor_baseline.up_button))),
                right_button=_parse_direction_button(self._editor_combo_text("routeEditorHatRightButtonCombo", _direction_text(self._route_editor_baseline.right_button))),
                down_button=_parse_direction_button(self._editor_combo_text("routeEditorHatDownButtonCombo", _direction_text(self._route_editor_baseline.down_button))),
                left_button=_parse_direction_button(self._editor_combo_text("routeEditorHatLeftButtonCombo", _direction_text(self._route_editor_baseline.left_button))),
            )
        return None

    def _editor_combo_text(self, object_name: str, fallback: str) -> str:
        if self._route_editor_panel is None:
            return fallback
        combo = self._route_editor_panel.findChild(QComboBox, object_name)
        return combo.currentText() if combo is not None else fallback

    def _editor_checkbox_checked(self, object_name: str, fallback: bool) -> bool:
        if self._route_editor_panel is None:
            return fallback
        checkbox = self._route_editor_panel.findChild(QCheckBox, object_name)
        return checkbox.isChecked() if checkbox is not None else fallback

    def _refresh_route_editor_preview(self) -> None:
        if self._route_editor_preview_label is None:
            return
        route = self._route_from_editor()
        if route is None or self._route_editor_route_type is None or self._route_editor_route_row is None:
            self._route_editor_preview_label.setText("workspace/config conflict preview: route is read-only or unsupported.")
            return
        mapping_config = self._mapping_config_with_route(
            self._workspace.mappings,
            self._route_editor_route_type,
            self._route_editor_route_row,
            route,
        )
        if mapping_config is None:
            self._route_editor_preview_label.setText("workspace/config conflict preview: unsupported route shape.")
            return
        candidate_workspace = replace(self._workspace, mappings=mapping_config)
        warnings = build_workspace_route_warnings(candidate_workspace)
        control_id = self._control_id_for_route(self._route_editor_route_type, self._route_editor_route_row, candidate_workspace)
        selected_warnings = tuple(warning for warning in warnings if warning.control_id == control_id)
        if selected_warnings:
            text = "; ".join(warning.message for warning in selected_warnings)
        else:
            text = "No workspace/config conflicts previewed."
        self._route_editor_preview_label.setText(f"workspace/config conflict preview: {text}")

    def _apply_route_editor(self) -> None:
        route = self._route_from_editor()
        if route is None or self._route_editor_route_type is None or self._route_editor_route_row is None:
            self._status_message("Route edit is unsupported and was not applied.")
            return
        message = (
            f"Applied {self._route_editor_route_type} mapping to workspace draft. "
            "Save Workspace required to persist changes."
        )
        self._apply_route_to_workspace(self._route_editor_route_type, self._route_editor_route_row, route, message)
        if self._route_editor_dirty_label is not None:
            self._route_editor_dirty_label.setText("Workspace draft changed - Save Workspace required")
        self._refresh_route_editor_preview()

    def _cancel_route_editor(self) -> None:
        if self._route_editor_panel is not None:
            self._route_editor_panel.setHidden(True)
        self._route_editor_route_type = None
        self._route_editor_route_row = None
        self._route_editor_baseline = None
        self._route_editor_dirty_label = None
        self._route_editor_preview_label = None
        context = self._selected_route_context()
        if context is not None:
            self._refresh_route_inspector(context[0])
        self._status_message("Mapping edit canceled; workspace draft was not modified.")

    def _revert_route_editor(self) -> None:
        if self._route_editor_baseline is None or self._route_editor_route_type is None or self._route_editor_route_row is None:
            return
        route = self._route_editor_baseline
        route_type = self._route_editor_route_type
        row = self._route_editor_route_row
        self._apply_route_to_workspace(
            route_type,
            row,
            route,
            f"Reverted {route_type} route to pre-edit workspace draft value. Save Workspace required to persist changes.",
        )
        control = self._control_for_route(route_type, row)
        if control is not None:
            self._render_route_editor(control, route_type, row, route)
        if self._route_editor_dirty_label is not None:
            self._route_editor_dirty_label.setText("Workspace draft reverted - Save Workspace required")

    def _apply_route_to_workspace(self, route_type: str, row: int, route, message: str) -> None:
        mapping_config = self._mapping_config_with_route(self._workspace.mappings, route_type, row, route)
        if mapping_config is None:
            self._status_message("Route edit is unsupported and was not applied.")
            return
        self._set_mapping_config(mapping_config, message)
        if route_type == "axis":
            self._populate_axis_table()
            self._refresh_route_summary()
        elif route_type == "button":
            self._populate_button_table()
        elif route_type == "hat":
            self._populate_hat_table()
        self._refresh_counts()
        self._refresh_table_warning_states()
        self._apply_route_filter()

    def _mapping_config_with_route(self, mapping_config: MappingConfig, route_type: str, row: int, route) -> MappingConfig | None:
        if route_type == "axis" and isinstance(route, AxisMapping):
            routes = list(mapping_config.axis_routes)
            if not 0 <= row < len(routes):
                return None
            routes[row] = route
            return replace(mapping_config, axis_routes=tuple(routes))
        if route_type == "button" and isinstance(route, ButtonMapping):
            routes = list(mapping_config.button_routes)
            if not 0 <= row < len(routes):
                return None
            routes[row] = route
            return replace(mapping_config, button_routes=tuple(routes))
        if route_type == "hat" and isinstance(route, HatMapping):
            routes = list(mapping_config.hat_routes)
            if not 0 <= row < len(routes):
                return None
            routes[row] = route
            return replace(mapping_config, hat_routes=tuple(routes))
        return None

    def _control_id_for_route(self, route_type: str, row: int, workspace: WorkspaceConfig) -> str | None:
        model = build_hotas_diagram_model(
            workspace,
            raw_axis_values=self._diagram_raw_axis_values(),
            button_states=self._diagram_button_states(),
            hat_state=self._diagram_hat_state(),
            source_label=self._input_source_status.source_label,
        )
        for control in model.routed_controls:
            if control.route_type == route_type and control.route_row == row:
                return control.control_id
        return None

    def _control_for_route(self, route_type: str, row: int) -> HotasDiagramControl | None:
        model = self._hotas_diagram_model or self._create_hotas_diagram_model()
        return next(
            (control for control in model.routed_controls if control.route_type == route_type and control.route_row == row),
            None,
        )

    def _set_mapping_config(self, mapping_config: MappingConfig, message: str) -> None:
        self._workspace = replace(self._workspace, mappings=mapping_config)
        self._refresh_hotas_diagram()
        if self._on_workspace_changed is not None:
            self._on_workspace_changed(self._workspace, message)
        elif self._on_dirty is not None:
            self._on_dirty(message)

    def _create_hotas_diagram_model(self) -> HotasDiagramModel:
        return build_hotas_diagram_model(
            self._workspace,
            raw_axis_values=self._diagram_raw_axis_values(),
            button_states=self._diagram_button_states(),
            hat_state=self._diagram_hat_state(),
            source_label=self._input_source_status.source_label,
        )

    def _refresh_hotas_diagram(self) -> None:
        self._route_warnings = build_workspace_route_warnings(self._workspace)
        self._hotas_diagram_model = self._create_hotas_diagram_model()
        if self._hotas_diagram_widget is not None:
            self._hotas_diagram_widget.set_model(self._hotas_diagram_model)
            self._hotas_diagram_widget.set_filter(self._route_filter)
        self._refresh_table_warning_states()
        self._apply_route_filter()
        self._apply_route_selection(self._selected_route_control_id, update_table=False)

    def _select_route_by_control_id(self, control_id: str) -> None:
        self._apply_route_selection(control_id, update_table=True)

    def _select_route_from_table(self, table_object_name: str, row: int) -> None:
        if self._syncing_route_selection or row < 0:
            return
        control_id = self._control_id_for_table_row(table_object_name, row)
        if control_id is not None:
            self._apply_route_selection(control_id, update_table=False)

    def _apply_route_selection(self, control_id: str, *, update_table: bool) -> None:
        model = self._hotas_diagram_model or self._create_hotas_diagram_model()
        selection = select_hotas_diagram_route(model, control_id)
        control = next((item for item in model.routed_controls if item.control_id == control_id), None)
        if selection is None or control is None:
            return
        self._selected_route_control_id = control_id
        if self._hotas_diagram_widget is not None:
            self._hotas_diagram_widget.set_selected_control_id(control_id)
        if update_table:
            table = self._table_by_object_name(selection.table_object_name)
            if table is not None and 0 <= selection.route_row < table.rowCount():
                self._syncing_route_selection = True
                table.setCurrentCell(selection.route_row, 0)
                table.selectRow(selection.route_row)
                self._syncing_route_selection = False
        self._refresh_route_inspector(control)

    def _refresh_route_inspector(self, control) -> None:
        inspector = build_route_inspector(
            control,
            workspace=self._workspace,
            active_profile=self._workspace.active_profile,
            source_label=self._input_source_status.source_label,
            runtime_truth_label=self._runtime_truth_label(),
            telemetry_status=self._telemetry_status_label(),
            warnings=self._route_warnings,
        )
        values = {
            "routeInspectorModeValue": (
                "Editing workspace draft"
                if self._route_editor_panel is not None and not self._route_editor_panel.isHidden()
                else "Inspecting workspace route"
            ),
            "routeInspectorTypeValue": inspector.route_type,
            "routeInspectorPhysicalValue": inspector.selected_physical_input,
            "routeInspectorOutputValue": inspector.mapped_virtual_output,
            "routeInspectorContextValue": inspector.mode_profile_context,
            "routeInspectorTruthValue": inspector.source_of_truth,
            "routeInspectorEditableValue": inspector.editable_in_current_ui,
            "routeInspectorConflictValue": inspector.conflict_status,
            "routeInspectorVerificationValue": inspector.no_live_output_verification_notice,
        }
        for object_name, text in values.items():
            label = self._route_inspector_labels.get(object_name)
            if label is not None:
                label.setText(text)
        if self._change_mapping_button is not None:
            editable = control.editable and control.table_object_name is not None and control.route_row is not None
            self._change_mapping_button.setEnabled(editable)
            self._change_mapping_button.setToolTip(
                "Edit this workspace draft route. Apply does not write live output."
                if editable
                else "This route is read-only or unsupported in the Mapping editor."
            )

    def _control_id_for_table_row(self, table_object_name: str, row: int) -> str | None:
        model = self._hotas_diagram_model or self._create_hotas_diagram_model()
        for control in model.routed_controls:
            if control.table_object_name == table_object_name and control.route_row == row:
                return control.control_id
        return None

    def _table_by_object_name(self, table_object_name: str) -> QTableWidget | None:
        if table_object_name == "axisRoutingTable":
            return self._axis_table
        if table_object_name == "buttonRoutingTable":
            return self._button_table
        if table_object_name == "hatRoutingTable":
            return self._hat_table
        return None

    def _telemetry_status_label(self) -> str:
        if self._runtime_frame is None:
            return "Bridge telemetry unavailable"
        if not self._runtime_frame.available:
            return f"Bridge telemetry {self._runtime_frame.parse_status}"
        return "Bridge telemetry available"

    def _diagram_raw_axis_values(self):
        return self._physical_raw_axes or self._snapshot.raw_axis_values

    def _diagram_button_states(self):
        if self._physical_input_snapshot is not None and self._input_source_status.is_fresh_physical_sample:
            return buttons_from_physical_snapshot(self._physical_input_snapshot)
        return self._snapshot.button_states

    def _diagram_hat_state(self) -> str:
        if self._physical_input_snapshot is not None and self._input_source_status.is_fresh_physical_sample:
            return hat_from_physical_snapshot(self._physical_input_snapshot)
        return self._snapshot.hat_state

    def _refresh_counts(self) -> None:
        values = {
            "axisRouteCount": len(self._workspace.mappings.axis_routes),
            "buttonRouteCount": len(self._workspace.mappings.button_routes),
            "hatRouteCount": len(self._workspace.mappings.hat_routes),
        }
        for name, value in values.items():
            if name in self._count_labels:
                self._count_labels[name].setText(str(value))

    def _refresh_route_summary(self) -> None:
        for label, route in zip(self._axis_route_labels, self._workspace.mappings.axis_routes, strict=False):
            label.setText(_route_summary(route))

    def _set_combo_cell(
        self,
        table: QTableWidget,
        row: int,
        column: int,
        *,
        object_name: str,
        options: tuple[str, ...],
        current: str,
        on_changed: Callable[[str], None],
        metadata_id: str | None = None,
    ) -> None:
        combo = QComboBox()
        combo.setObjectName(object_name)
        available = list(options)
        if current not in available:
            available.append(current)
        combo.addItems(available)
        apply_parameter_metadata(combo, metadata_id)
        combo.setCurrentText(current)
        combo.currentTextChanged.connect(on_changed)
        self._set_text_item(table, row, column, current)
        table.setCellWidget(row, column, combo)

    def _set_text_item(self, table: QTableWidget, row: int, column: int, value: str) -> None:
        item = table.item(row, column)
        if item is None:
            item = QTableWidgetItem(value)
            table.setItem(row, column, item)
        else:
            item.setText(value)

    def _configure_table(self, table: QTableWidget, *, minimum_height: int) -> None:
        table.setProperty("polishedRouteTable", True)
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(42)
        table.setAlternatingRowColors(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(minimum_height)

    def _add_count_row(self, layout: QGridLayout, row: int, label: str, object_name: str, value: int) -> None:
        name = QLabel(label)
        name.setObjectName("tableMutedText")
        count = QLabel(str(value))
        count.setObjectName(object_name)
        count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._count_labels[object_name] = count
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

    def _output_verified(self) -> bool:
        return bool(self._runtime_status.live_output_writes_verified or self._virtual_output_diagnostics.output_verified)

    def _runtime_truth_label(self) -> str:
        return {
            RuntimeTruth.SIMULATED: "simulated",
            RuntimeTruth.DETECTED_UNVERIFIED: "detected_unverified / Detected Unverified",
            RuntimeTruth.LIVE_VERIFIED: "live_verified",
            RuntimeTruth.BLOCKED_MISSING_DRIVER: "blocked_missing_driver",
            RuntimeTruth.BLOCKED_MISSING_DEVICE: "blocked_missing_device",
            RuntimeTruth.ERROR: "error",
        }[self._runtime_status.truth]

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


def _output_loop_write_count(snapshot: VirtualOutputLoopSnapshot | None) -> str:
    return str(snapshot.write_count) if snapshot is not None else "0"


def _output_loop_neutral_restore(snapshot: VirtualOutputLoopSnapshot | None) -> str:
    return snapshot.neutral_restore_status if snapshot is not None else "not_attempted"


def _runtime_frame_status(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    if runtime_frame is None:
        return "unavailable"
    return "available" if runtime_frame.available else runtime_frame.parse_status


def _runtime_frame_source(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.input_source if runtime_frame is not None else "unavailable"


def _runtime_frame_pipeline_status(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.pipeline_status if runtime_frame is not None else "unavailable"


def _runtime_frame_output_intent_ready(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return str(bool(runtime_frame and runtime_frame.output_intent_ready)).lower()


def _runtime_frame_output_backend(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    return runtime_frame.output_backend if runtime_frame is not None else "Unavailable"


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


def _runtime_frame_ready_gate(runtime_frame: RuntimeFrameTelemetryPayload | None) -> str:
    if runtime_frame is None:
        return "unavailable"
    if runtime_frame.full_live_runtime_ready:
        return "ready"
    return runtime_frame.ready_state or "blocked"


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


def _parse_button(value: str) -> int:
    return int(value.removeprefix("B"))


def _parse_direction_button(value: str) -> int | None:
    return None if value == "None" else int(value)


def _selected_row(table: QTableWidget) -> int | None:
    row = table.currentRow()
    if row >= 0:
        return row
    indexes = table.selectedIndexes()
    if indexes:
        return indexes[0].row()
    return None


def _key(value: str) -> str:
    return value.casefold().replace(" ", "_").replace("/", "_")


def _filter_key(value: str) -> str:
    return "".join(part.title() for part in value.split())


def _route_filter_matches_control(control: HotasDiagramControl, filter_name: str) -> bool:
    if filter_name in {"All", "Selected Profile"}:
        return True
    if filter_name == "Axes":
        return control.route_type == "axis"
    if filter_name == "Buttons":
        return control.route_type == "button"
    if filter_name == "Hats":
        return control.route_type == "hat"
    if filter_name == "Mapped":
        return control.status == "mapped"
    if filter_name == "Unmapped":
        return control.status == "unmapped"
    if filter_name == "Warnings":
        return bool(control.warning)
    return True


def _clear_layout(layout) -> None:  # noqa: ANN001
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        child_layout = item.layout()
        if child_layout is not None:
            _clear_layout(child_layout)


def _direction_text(value: int | None) -> str:
    return "None" if value is None else str(value)


def _signed(value: float) -> str:
    return f"{value:+.2f}"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]
