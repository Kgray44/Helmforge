from __future__ import annotations

import os
from collections.abc import Callable

from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QSizePolicy, QWidget

from shared_core.models.runtime import (
    InputDeviceDetection,
    OutputBackendDetection,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)
from shared_core.runtime.telemetry import BridgeTelemetrySnapshot
from v3_app.liquid.components import (
    LiquidAdvancedSection,
    LiquidDetailPanel,
    LiquidHeroPanel,
    LiquidInspectorPanel,
    LiquidPage,
    LiquidStatusRail,
)
from v3_app.liquid.glass import action_button, glass_panel
from v3_app.liquid.layout import grid_layout, horizontal_layout, vertical_layout
from v3_app.liquid.models.preflight_readiness_model import (
    PreflightChecklistItemModel,
    PreflightReadinessModel,
    PreflightSystemDetailModel,
    build_preflight_readiness_model,
    runtime_status_from_app_state,
)
from v3_app.liquid.status_components import ReadinessGate, StatusChip, StatusLight, status_tone_for_role
from v3_app.services.app_state import AppState


def _lcd4f_trace(message: str) -> None:
    if os.environ.get("HELMFORGE_LCD4F_TRACE") == "1":
        print(f"LCD4F_TRACE: {message}", flush=True)


class PreflightCommandPage(LiquidPage):
    def __init__(
        self,
        *,
        state: AppState | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        telemetry: BridgeTelemetrySnapshot | None = None,
        on_route_requested: Callable[[str], None] | None = None,
    ) -> None:
        _lcd4f_trace("constructing preflight page")
        self._state = state or _default_state()
        self._runtime_status = runtime_status or runtime_status_from_app_state(self._state)
        self._telemetry = telemetry
        self._on_route_requested = on_route_requested
        self._last_render_signature: tuple[object, ...] | None = None
        self._render_count = 0
        super().__init__(
            title="Preflight",
            subtitle="Can I safely use live output right now?",
            helper_text="COMMAND READINESS",
            object_name="liquidPreflightCommandPage",
        )
        self.setProperty("componentRole", "PreflightCommandPage")
        self.setProperty("liquidRole", "liquid_preflight_command_page")
        self.setProperty("routeKey", "preflight.command_readiness")
        self.setProperty("modeId", "preflight")
        self.setProperty("subpageId", "command_readiness")
        self._render()

    def update_runtime_status(
        self,
        runtime_status: RuntimePreflightStatus,
        *,
        telemetry: BridgeTelemetrySnapshot | None = None,
        state: AppState | None = None,
    ) -> None:
        next_state = state or self._state
        next_signature = _render_signature(next_state, runtime_status, telemetry)
        if next_signature == self._last_render_signature:
            self._state = next_state
            self._runtime_status = runtime_status
            self._telemetry = telemetry
            _lcd4f_trace("skipped preflight rebuild for unchanged readiness truth")
            return
        if state is not None:
            self._state = state
        self._runtime_status = runtime_status
        self._telemetry = telemetry
        self._render(next_signature)

    def update_state(self, state: AppState) -> None:
        runtime_status = runtime_status_from_app_state(state)
        next_signature = _render_signature(state, runtime_status, self._telemetry)
        if next_signature == self._last_render_signature:
            self._state = state
            self._runtime_status = runtime_status
            _lcd4f_trace("skipped preflight state rebuild for unchanged readiness truth")
            return
        self._state = state
        self._runtime_status = runtime_status
        self._render(next_signature)

    def _render(self, signature: tuple[object, ...] | None = None) -> None:
        _lcd4f_trace("deriving readiness model")
        model = build_preflight_readiness_model(
            state=self._state,
            runtime_status=self._runtime_status,
            telemetry=self._telemetry,
        )
        self._last_render_signature = signature or _render_signature(self._state, self._runtime_status, self._telemetry)
        self._render_count += 1
        self.setProperty("preflightRenderCount", self._render_count)
        self.set_header(_preflight_header(model))
        _lcd4f_trace("constructing preflight hero")
        self.set_status_rail(_status_rail(model))
        self.set_hero(_hero_panel(model, self._on_route_requested))
        _lcd4f_trace("constructing preflight system details")
        self.set_inspector(_system_details_panel(model))
        _lcd4f_trace("constructing preflight checklist")
        self.set_detail(_checklist_panel(model))
        _lcd4f_trace("constructing preflight advanced diagnostics")
        self.set_advanced(_advanced_panel(model))


def create_preflight_command_page(
    *,
    state: AppState | None = None,
    runtime_status: RuntimePreflightStatus | None = None,
    telemetry: BridgeTelemetrySnapshot | None = None,
    on_route_requested: Callable[[str], None] | None = None,
) -> PreflightCommandPage:
    return PreflightCommandPage(
        state=state,
        runtime_status=runtime_status,
        telemetry=telemetry,
        on_route_requested=on_route_requested,
    )


def _render_signature(
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    telemetry: BridgeTelemetrySnapshot | None,
) -> tuple[object, ...]:
    runtime_frame = telemetry.runtime_frame if telemetry is not None and telemetry.runtime_frame is not None else {}
    frame_keys = (
        "runtime_truth",
        "telemetry_proof",
        "input_stale",
        "blocked_reason",
        "output_proof",
        "safety_proof",
        "ready_state",
        "full_live_runtime_ready",
    )
    telemetry_signature: tuple[object, ...]
    if telemetry is None:
        telemetry_signature = ("telemetry", None)
    else:
        telemetry_signature = (
            "telemetry",
            _enum_value(telemetry.runtime_truth),
            _enum_value(telemetry.lifecycle_state),
            _enum_value(telemetry.input_status),
            _enum_value(telemetry.output_status),
            bool(telemetry.output_verified),
            telemetry.active_profile,
            tuple(telemetry.warnings),
            tuple(telemetry.errors),
            tuple((key, _stable_value(runtime_frame.get(key))) for key in frame_keys),
        )
    return (
        "state",
        state.active_profile,
        state.source_config,
        bool(state.saved),
        "runtime",
        _enum_value(runtime_status.mode),
        _enum_value(runtime_status.truth),
        _enum_value(runtime_status.input.status),
        tuple(runtime_status.input.detected_device_names),
        tuple(runtime_status.input.warnings),
        tuple(runtime_status.input.errors),
        _enum_value(runtime_status.output.status),
        runtime_status.output.backend_name,
        bool(runtime_status.output.live_output_writes_verified),
        tuple(runtime_status.output.warnings),
        tuple(runtime_status.output.errors),
        tuple(runtime_status.warnings),
        tuple(runtime_status.errors),
        telemetry_signature,
    )


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _stable_value(value: object) -> object:
    if isinstance(value, dict):
        return tuple(sorted((str(key), _stable_value(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_stable_value(item) for item in value)
    return _enum_value(value)


def _status_rail(model: PreflightReadinessModel) -> LiquidStatusRail:
    rail = LiquidStatusRail(
        items=(),
        object_name="liquidPreflightStatusRail",
    )
    rail.setProperty("preflightStatusRail", True)
    rail.setProperty("mergedIntoHero", True)
    rail.setProperty("visualWeight", "none")
    rail.setFixedHeight(0)
    rail.setMaximumHeight(0)
    return rail


def _preflight_header(model: PreflightReadinessModel) -> QFrame:
    header = glass_panel("liquidPreflightPageHeader", role="liquid_page_header")
    header.setProperty("componentRole", "LiquidPageHeader")
    header.setProperty("liquidComponent", True)
    header.setProperty("preflightHeader", True)
    header.setProperty("visualWeight", "subtle")
    layout = horizontal_layout(header, margins=(14, 9, 14, 9), spacing=12)
    title_column = vertical_layout(spacing=3)
    kicker = QLabel("LIQUID COMMAND DECK")
    kicker.setObjectName("liquidComponentKicker")
    title = QLabel("Preflight")
    title.setObjectName("liquidComponentTitle")
    subtitle = QLabel("Command Readiness / Can I safely use live output right now?")
    subtitle.setObjectName("liquidComponentSubtitle")
    subtitle.setWordWrap(True)
    title_column.addWidget(kicker)
    title_column.addWidget(title)
    title_column.addWidget(subtitle)
    route_chip = StatusChip("Preflight / Command Readiness", state_role="info", object_name="liquidPreflightRouteChip")
    route_chip.setProperty("routeChip", True)
    route_chip.setToolTip("Route: preflight.command_readiness")
    route_chip.setAccessibleName("Preflight Command Readiness route")
    source_chip = StatusChip(f"Source: {model.source_label}", state_role="info", object_name="liquidPreflightHeaderSourceChip")
    source_chip.setMaximumWidth(210)
    layout.addLayout(title_column, 1)
    layout.addWidget(route_chip)
    layout.addWidget(source_chip)
    return header


def _hero_panel(model: PreflightReadinessModel, on_route_requested: Callable[[str], None] | None) -> LiquidHeroPanel:
    hero = LiquidHeroPanel(
        model.overall_label,
        model.short_explanation,
        object_name="liquidPreflightHeroGoNoGo",
        kicker="GO / NO-GO STATUS",
        state_role=model.overall_state,
        minimum_height=366,
    )
    hero.setProperty("preflightHero", True)
    hero.setProperty("preflightVisualRole", "primary_go_no_go")
    hero.setProperty("primaryInstrument", True)
    hero.setProperty("heroDensity", "dominant")
    _append_to_panel(hero, _question_label())
    _append_to_panel(hero, _next_action_label(model.next_recommended_action))
    _append_to_panel(hero, _truth_chip_row(model))
    _append_to_panel(hero, _preflight_command_actions(model, on_route_requested))
    _append_to_panel(hero, _gate_grid(model))
    return hero


def _preflight_command_actions(
    model: PreflightReadinessModel,
    on_route_requested: Callable[[str], None] | None,
) -> QFrame:
    actions = glass_panel("liquidPreflightCommandActions", role="liquid_preflight_command_actions")
    actions.setProperty("componentRole", "PreflightCommandActions")
    actions.setProperty("liquidComponent", True)
    actions.setProperty("pageActionCluster", True)
    layout = horizontal_layout(actions, margins=(0, 6, 0, 4), spacing=8)
    layout.addWidget(
        _route_button(
            "Open Setup / Runtime Check",
            "support.setup_runtime_check",
            "liquidPreflightOpenSetupButton",
            on_route_requested,
        )
    )
    layout.addWidget(
        _route_button(
            "Open Mapping / HOTAS Map",
            "mapping.hotas_map",
            "liquidPreflightOpenMappingButton",
            on_route_requested,
        )
    )
    layout.addWidget(
        _route_button(
            "Open Help / Docs",
            "support.help_docs",
            "liquidPreflightOpenHelpButton",
            on_route_requested,
        )
    )
    layout.addWidget(
        _copy_button(
            "Copy preflight status",
            "liquidPreflightCopyStatusButton",
            _preflight_status_text(model),
        )
    )
    layout.addWidget(
        _copy_button(
            "Copy setup checklist",
            "liquidPreflightCopyChecklistButton",
            _preflight_checklist_text(model),
        )
    )
    simulation = action_button(
        "Simulation mode control pending",
        object_name="liquidPreflightSimulationControlButton",
        enabled=False,
    )
    simulation.setToolTip("Simulation mode control is pending because LCD-7R does not add runtime authority or mode toggles.")
    simulation.setAccessibleDescription(simulation.toolTip())
    layout.addWidget(simulation)
    layout.addStretch(1)
    return actions


def _question_label() -> QLabel:
    label = QLabel("Can I safely use live output right now?")
    label.setObjectName("liquidPreflightHeroQuestion")
    label.setWordWrap(True)
    return label


def _next_action_label(text: str) -> QLabel:
    label = QLabel(f"Next: {text}")
    label.setObjectName("liquidPreflightNextRecommendedAction")
    label.setWordWrap(True)
    label.setProperty("preflightNextAction", True)
    return label


def _truth_chip_row(model: PreflightReadinessModel) -> QFrame:
    row = glass_panel("liquidPreflightHeroTruthChips", role="liquid_preflight_truth_chips")
    row.setProperty("liquidComponent", True)
    row.setProperty("componentRole", "PreflightTruthChipRow")
    row.setProperty("proofGroupLocation", "hero")
    row.setProperty("visualWeight", "integrated")
    layout = horizontal_layout(row, margins=(0, 4, 0, 4), spacing=8)
    layout.addWidget(StatusChip(model.runtime_truth_label, state_role=model.overall_state))
    layout.addWidget(StatusChip(model.output_proof_label, state_role=_gate_role(model, "Output Proof")))
    layout.addWidget(StatusChip(model.telemetry_label, state_role=_gate_role(model, "Telemetry")))
    layout.addWidget(StatusChip(f"Source: {model.source_label}", state_role="info"))
    layout.addStretch(1)
    return row


def _gate_grid(model: PreflightReadinessModel) -> QFrame:
    grid = glass_panel("liquidPreflightReadinessGates", role="liquid_preflight_readiness_gates")
    grid.setProperty("componentRole", "PreflightReadinessGateGrid")
    grid.setProperty("liquidComponent", True)
    grid.setProperty("visualWeight", "integrated")
    layout = grid_layout(grid, margins=(0, 4, 0, 0), spacing=12)
    for index, gate in enumerate(model.readiness_gates):
        widget = ReadinessGate(
            gate.label,
            state_text=_display_state(gate.state),
            state_role=gate.role,
            detail=f"{gate.reason}. {gate.detail}".strip(),
            object_name=f"liquidPreflightGate_{_object_slug(gate.label)}",
        )
        widget.setProperty("preflightGateLabel", gate.label)
        widget.setProperty("preflightGateState", gate.state)
        widget.setProperty("preflightGateVisual", "compact_scan")
        widget.setProperty("gateEmphasis", "subtle" if gate.role in {"ready", "safe", "verified"} else "active")
        widget.setMinimumHeight(86)
        row, column = divmod(index, 3)
        layout.addWidget(widget, row, column)
    return grid


def _system_details_panel(model: PreflightReadinessModel) -> LiquidInspectorPanel:
    panel = LiquidInspectorPanel(
        "System Map / Details",
        "Compact runtime, workspace, source, and proof state.",
        object_name="liquidPreflightSystemDetails",
        liquid_role="liquid_context_inspector_region",
        minimum_height=260,
    )
    panel.setProperty("preflightSystemDetails", True)
    panel.setProperty("detailStructure", "grouped_system_map")
    for group_name, details in _system_detail_groups(model.system_details):
        _append_to_panel(panel, _system_detail_group(group_name, details))
    return panel


def _checklist_panel(model: PreflightReadinessModel) -> LiquidDetailPanel:
    panel = LiquidDetailPanel(
        "Next Actions",
        "Only informational or already-safe actions are shown here.",
        object_name="liquidPreflightActionPanel",
        liquid_role="liquid_detail_action_region",
        minimum_height=260,
    )
    checklist = _preflight_checklist(model.checklist_items)
    checklist.setProperty("preflightChecklist", True)
    _append_to_panel(panel, checklist)
    return panel


def _advanced_panel(model: PreflightReadinessModel) -> LiquidAdvancedSection:
    panel = LiquidAdvancedSection(
        "Advanced Diagnostics",
        "Raw values are kept secondary so normal readiness remains readable.",
        object_name="liquidPreflightAdvancedDiagnostics",
        liquid_role="liquid_advanced_region",
        minimum_height=190,
    )
    panel.setProperty("advancedSecondary", True)
    panel.setProperty("preflightAdvancedDiagnostics", True)
    panel.setProperty("visualWeight", "subdued")
    panel.setProperty("collapsibleTreatment", "static_subdued")
    summary = glass_panel("liquidPreflightAdvancedSummary", role="liquid_preflight_advanced_summary")
    summary.setProperty("componentRole", "PreflightAdvancedSummary")
    summary.setProperty("liquidComponent", True)
    summary.setProperty("visualWeight", "subdued")
    summary_layout = horizontal_layout(summary, margins=(12, 8, 12, 8), spacing=8)
    summary_layout.addWidget(StatusLight(state_role=model.overall_state))
    summary_label = QLabel("Diagnostics are secondary; raw runtime values remain available below.")
    summary_label.setObjectName("liquidPreflightAdvancedSummaryText")
    summary_label.setWordWrap(True)
    summary_layout.addWidget(summary_label, 1)
    _append_to_panel(panel, summary)
    diagnostics_grid = glass_panel("liquidPreflightAdvancedDiagnosticsGrid", role="liquid_preflight_advanced_grid")
    diagnostics_grid.setProperty("componentRole", "PreflightAdvancedDiagnosticsGrid")
    diagnostics_grid.setProperty("liquidComponent", True)
    diagnostics_grid.setProperty("diagnosticsDensity", "subdued")
    layout = grid_layout(diagnostics_grid, margins=(0, 0, 0, 0), spacing=8)
    for index, detail in enumerate(model.advanced_diagnostics):
        layout.addWidget(
            _detail_row(detail, object_name=f"liquidPreflightDiagnostic_{_object_slug(detail.label)}"),
            index // 3,
            index % 3,
        )
    _append_to_panel(panel, diagnostics_grid)
    for note in model.truth_source_notes:
        note_label = QLabel(note)
        note_label.setObjectName("liquidPreflightTruthSourceNote")
        note_label.setWordWrap(True)
        _append_to_panel(panel, note_label)
    return panel


def _system_detail_groups(
    details: tuple[PreflightSystemDetailModel, ...],
) -> tuple[tuple[str, tuple[PreflightSystemDetailModel, ...]], ...]:
    by_label = {detail.label: detail for detail in details}

    def pick(*labels: str) -> tuple[PreflightSystemDetailModel, ...]:
        return tuple(by_label[label] for label in labels if label in by_label)

    return (
        ("Input / Device", pick("HOTAS/device state")),
        ("Telemetry / Bridge", pick("Bridge telemetry state", "Telemetry freshness/source")),
        ("Workspace / Config", pick("Workspace state", "Saved/unsaved state", "Current data source/config")),
        ("Output / vJoy", pick("vJoy state", "Output proof state")),
        ("Runtime / Safety", pick("Runtime truth label", "Full live gate")),
    )


def _system_detail_group(group_name: str, details: tuple[PreflightSystemDetailModel, ...]) -> QFrame:
    group = glass_panel(f"liquidPreflightSystemGroup_{_object_slug(group_name)}", role="liquid_preflight_system_group")
    group.setProperty("componentRole", "PreflightSystemDetailGroup")
    group.setProperty("liquidComponent", True)
    group.setProperty("systemDetailGroup", True)
    group.setProperty("systemGroupName", group_name)
    layout = vertical_layout(group, margins=(12, 10, 12, 10), spacing=7)
    title = QLabel(group_name)
    title.setObjectName("liquidPreflightSystemGroupTitle")
    layout.addWidget(title)
    for detail in details:
        layout.addWidget(_detail_row(detail, object_name=f"liquidPreflightSystemDetail_{_object_slug(detail.label)}"))
    return group


def _preflight_checklist(items: tuple[PreflightChecklistItemModel, ...]) -> QFrame:
    panel = glass_panel("liquidPreflightNextActions", role="liquid_preflight_checklist")
    panel.setProperty("componentRole", "ChecklistPanel")
    panel.setProperty("preflightComponentRole", "PreflightChecklistPanel")
    panel.setProperty("liquidComponent", True)
    panel.setProperty("preflightChecklist", True)
    panel.setProperty("checklistStructure", "action_rows")
    layout = vertical_layout(panel, margins=(14, 12, 14, 12), spacing=9)
    title = QLabel("Next-action checklist")
    title.setObjectName("liquidChecklistTitle")
    layout.addWidget(title)
    for item in items:
        layout.addWidget(_checklist_action_row(item))
    return panel


def _checklist_action_row(item: PreflightChecklistItemModel) -> QFrame:
    row = glass_panel(f"liquidPreflightActionItem_{_object_slug(item.label)}", role="liquid_preflight_action_item")
    row.setProperty("componentRole", "PreflightChecklistItem")
    row.setProperty("liquidComponent", True)
    row.setProperty("preflightChecklistItem", True)
    row.setProperty("actionRowStyle", "breathing")
    row.setProperty("statusRole", item.state)
    row.setProperty("toneRole", status_tone_for_role(item.state))
    layout = horizontal_layout(row, margins=(12, 10, 12, 10), spacing=10)
    layout.addWidget(StatusLight(state_role=item.state))
    text_column = vertical_layout(spacing=3)
    label = QLabel(item.label)
    label.setObjectName("liquidPreflightChecklistLabel")
    label.setWordWrap(True)
    reason = QLabel(item.reason)
    reason.setObjectName("liquidPreflightChecklistReason")
    reason.setWordWrap(True)
    text_column.addWidget(label)
    text_column.addWidget(reason)
    layout.addLayout(text_column, 1)
    layout.addWidget(StatusChip(_display_state(item.state), state_role=item.state))
    return row


def _detail_row(detail: PreflightSystemDetailModel, *, object_name: str) -> QFrame:
    row = glass_panel(object_name, role="liquid_preflight_detail_row")
    row.setProperty("componentRole", "PreflightDetailRow")
    row.setProperty("liquidComponent", True)
    row.setProperty("detailRowStyle", "soft")
    row.setProperty("statusRole", detail.role)
    row.setProperty("toneRole", status_tone_for_role(detail.role))
    row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    layout = horizontal_layout(row, margins=(12, 8, 12, 8), spacing=8)
    label = QLabel(detail.label)
    label.setObjectName("liquidPreflightDetailLabel")
    label.setWordWrap(True)
    value = QLabel(detail.value)
    value.setObjectName("liquidPreflightDetailValue")
    value.setWordWrap(True)
    layout.addWidget(label, 1)
    layout.addWidget(value, 2)
    if detail.detail:
        badge = StatusChip(detail.detail, state_role=detail.role)
        badge.setMaximumWidth(260)
        layout.addWidget(badge, 1)
    return row


def _route_button(
    text: str,
    route_key: str,
    object_name: str,
    on_route_requested: Callable[[str], None] | None,
) -> QPushButton:
    button = action_button(text, object_name=object_name, enabled=on_route_requested is not None)
    button.setProperty("routeTarget", route_key)
    button.setProperty("navigationOnly", True)
    reason = f"Navigate to {route_key}. This does not change runtime authority."
    if on_route_requested is None:
        reason = f"{reason} Navigation callback is unavailable in this context."
    button.setToolTip(reason)
    button.setStatusTip(reason)
    button.setAccessibleDescription(reason)
    if on_route_requested is not None:
        button.clicked.connect(lambda _checked=False, target=route_key: on_route_requested(target))
    return button


def _copy_button(text: str, object_name: str, payload: str) -> QPushButton:
    button = action_button(text, object_name=object_name, enabled=True)
    button.setProperty("copyOnly", True)
    button.setToolTip("Copy this Preflight information to the clipboard. This does not change runtime state.")
    button.setStatusTip(button.toolTip())
    button.setAccessibleDescription(button.toolTip())
    button.clicked.connect(lambda _checked=False, data=payload: _copy_to_clipboard(data))
    return button


def _copy_to_clipboard(text: str) -> None:
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)


def _preflight_status_text(model: PreflightReadinessModel) -> str:
    return "\n".join(
        (
            f"Readiness: {model.overall_label}",
            f"Explanation: {model.short_explanation}",
            f"Next: {model.next_recommended_action}",
            f"Runtime truth: {model.runtime_truth_label}",
            f"Output proof: {model.output_proof_label}",
            f"Telemetry: {model.telemetry_label}",
            "Output proof unchanged by copy action.",
        )
    )


def _preflight_checklist_text(model: PreflightReadinessModel) -> str:
    lines = ["Preflight setup checklist:"]
    lines.extend(f"- {item.label}: {item.state} - {item.reason}" for item in model.checklist_items)
    return "\n".join(lines)


def _append_to_panel(panel: QWidget, widget: QWidget) -> None:
    layout = panel.layout()
    if layout is None:
        return
    insert_at = max(0, layout.count() - 1)
    layout.insertWidget(insert_at, widget)


def _gate_role(model: PreflightReadinessModel, label: str) -> str:
    for gate in model.readiness_gates:
        if gate.label == label:
            return gate.role
    return "info"


def _display_state(state: str) -> str:
    return state.replace("-", " ").title()


def _object_slug(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value).strip("_")


def _default_state() -> AppState:
    runtime_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.SIMULATED,
        input=InputDeviceDetection(),
        output=OutputBackendDetection(),
        messages=("Simulation mode selected; no live HOTAS/vJoy output is active.",),
    )
    state = AppState.from_runtime_status(runtime_status, active_page_id="preflight")
    state.status_message = "LCD-4 Preflight command page default fixture."
    return state
