from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QWidget

from shared_core.models.runtime import AXIS_NAMES
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.telemetry import BridgeTelemetrySnapshot
from v3_app.liquid.components import (
    LiquidAdvancedSection,
    LiquidDetailPanel,
    LiquidHeroPanel,
    LiquidInspectorPanel,
    LiquidPage,
    LiquidPageHeader,
    LiquidStatusRail,
)
from v3_app.liquid.flow_components import SignalPipelineStage
from v3_app.liquid.glass import action_button, glass_panel
from v3_app.liquid.instruments import AxisBarPair, ButtonIlluminationGrid, HatDirectionIndicator, LiveAxisTimeSeriesGraph
from v3_app.liquid.layout import grid_layout, horizontal_layout, vertical_layout
from v3_app.liquid.models.analysis_command_model import (
    AnalysisAxisMonitorModel,
    AnalysisCommandModel,
    AnalysisPipelineStageModel,
    build_analysis_command_model,
)
from v3_app.liquid.parameter_controls import AxisSelectorPills, LiveSnapshotBlock
from v3_app.liquid.status_components import MetricTile, StatusChip, TelemetryFreshnessRail, TruthBadge
from v3_app.services.app_state import AppState


AxisSelectedCallback = Callable[[str, str], None]
RouteCallback = Callable[[str], None]


class AnalysisCommandPage(LiquidPage):
    def __init__(
        self,
        *,
        route_key: str,
        state: AppState | None = None,
        workspace: WorkspaceConfig | None = None,
        telemetry: BridgeTelemetrySnapshot | None = None,
        selected_axis: str = "Roll",
        on_axis_selected: AxisSelectedCallback | None = None,
        on_route_requested: RouteCallback | None = None,
    ) -> None:
        self.route_key = route_key
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._telemetry = telemetry
        self._selected_axis = selected_axis if selected_axis in AXIS_NAMES else "Roll"
        self._on_axis_selected = on_axis_selected
        self._on_route_requested = on_route_requested
        self._axis_history: dict[str, list[tuple[float | None, float | None]]] = {axis: [] for axis in AXIS_NAMES}
        self._overlay_final_values = False
        self._monitor_paused = False
        self._last_signature: tuple[object, ...] | None = None
        self.render_count = 0
        self.model = build_analysis_command_model(
            route_key=route_key,
            workspace=self._workspace,
            state=self._state,
            telemetry=self._telemetry,
            selected_axis=self._selected_axis,
        )
        super().__init__(
            title=self.model.page_title,
            subtitle=self.model.page_question,
            helper_text="Passive Analysis visualization",
            object_name="liquidAnalysisCommandPage",
        )
        self.setProperty("routeKey", route_key)
        self.setProperty("modeId", "analysis")
        self.setProperty("lcdPhase", "LCD-7")
        self.setProperty("selectedAxis", self._selected_axis)
        if self.route_key == "analysis.live_monitor" and self._telemetry is not None:
            self._append_live_history(self.model)
        self._render(force=True)

    def select_axis(self, axis_name: str) -> None:
        if axis_name not in AXIS_NAMES or axis_name == self._selected_axis:
            return
        self._selected_axis = axis_name
        self.setProperty("selectedAxis", axis_name)
        if self._on_axis_selected is not None:
            self._on_axis_selected(self.route_key, axis_name)
            return
        self._refresh_model()
        self._render()

    def update_analysis_snapshot(
        self,
        *,
        state: AppState | None = None,
        workspace: WorkspaceConfig | None = None,
        telemetry: BridgeTelemetrySnapshot | None = None,
        selected_axis: str | None = None,
    ) -> None:
        self._state = state or self._state
        self._workspace = workspace or self._workspace
        self._telemetry = telemetry
        if selected_axis in AXIS_NAMES:
            self._selected_axis = str(selected_axis)
            self.setProperty("selectedAxis", self._selected_axis)
        previous_signature = self.model.signature
        self._refresh_model()
        if self.route_key == "analysis.live_monitor" and telemetry is not None and not self._monitor_paused:
            self._append_live_history(self.model)
            self._update_live_monitor_graph()
            return
        if self.model.signature == previous_signature:
            self._update_live_history_property()
            return
        self._render()

    def toggle_overlay(self) -> None:
        self._overlay_final_values = not self._overlay_final_values
        toggle = self.findChild(QPushButton, "liquidLiveMonitorOverlayToggle")
        if toggle is not None:
            toggle.setChecked(self._overlay_final_values)
            toggle.setProperty("overlayFinalValues", self._overlay_final_values)
        self._update_live_monitor_graph()

    def clear_live_history(self) -> None:
        for samples in self._axis_history.values():
            samples.clear()
        self.setProperty("liveMonitorHistoryLength", 0)
        self._update_live_monitor_graph()

    def toggle_monitor_pause(self) -> None:
        self._monitor_paused = not self._monitor_paused
        self._render(force=True)

    def _refresh_model(self) -> None:
        self.model = build_analysis_command_model(
            route_key=self.route_key,
            workspace=self._workspace,
            state=self._state,
            telemetry=self._telemetry,
            selected_axis=self._selected_axis,
        )

    def _render(self, *, force: bool = False) -> None:
        if not force and self.model.signature == self._last_signature:
            return
        self._last_signature = self.model.signature
        self.render_count += 1
        self.setProperty("selectedAxis", self.model.selected_axis)
        self.setProperty("liveMonitorHistoryLength", self._history_length())
        self.set_header(
            LiquidPageHeader(
                self.model.page_title,
                self.model.page_question,
                kicker="ANALYSIS / " + self.model.page_title.upper(),
                object_name="liquidAnalysisPageHeader",
            )
        )
        self.set_status_rail(_status_rail(self.model))
        if self.route_key == "analysis.effective_response_stack":
            self._render_effective_response_stack()
        else:
            self._render_live_monitor()
        self.set_advanced(_advanced_details(self.model))

    def _render_effective_response_stack(self) -> None:
        self.set_hero(_pipeline_hero(self, self.model))
        self.set_inspector(_axis_inspector(self.model, on_axis_selected=self.select_axis))
        self.set_detail(_pipeline_detail(self.model))

    def _render_live_monitor(self) -> None:
        self.set_hero(_live_monitor_hero(self, self.model))
        self.set_inspector(_live_axis_instruments(self.model))
        self.set_detail(_live_controls_detail(self, self.model))

    def _append_live_history(self, model: AnalysisCommandModel) -> None:
        for axis in model.axis_monitors:
            self._axis_history.setdefault(axis.axis_name, []).append((axis.raw_value, axis.final_value))
            if len(self._axis_history[axis.axis_name]) > 120:
                del self._axis_history[axis.axis_name][:-120]
        self._update_live_history_property()

    def _history_length(self) -> int:
        return max((len(samples) for samples in self._axis_history.values()), default=0)

    def _update_live_history_property(self) -> None:
        length = self._history_length()
        self.setProperty("liveMonitorHistoryLength", length)
        graph = self.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
        if graph is not None:
            graph.setProperty("historyLength", length)

    def _update_live_monitor_graph(self) -> None:
        graph = self.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
        if graph is not None and hasattr(graph, "update_history"):
            graph.update_history(self._axis_history, overlay_final_values=self._overlay_final_values)
        self._update_live_history_property()


def create_effective_response_stack_page(**kwargs) -> AnalysisCommandPage:
    return AnalysisCommandPage(route_key="analysis.effective_response_stack", **kwargs)


def create_live_monitor_page(**kwargs) -> AnalysisCommandPage:
    return AnalysisCommandPage(route_key="analysis.live_monitor", **kwargs)


def _status_rail(model: AnalysisCommandModel) -> LiquidStatusRail:
    rail = LiquidStatusRail(
        items=(
            (model.runtime_truth_label, "ready" if model.runtime_truth_label == "Live Verified" else model.telemetry_role),
            (model.telemetry_label, model.telemetry_role),
            (model.output_proof_label, model.output_proof_role),
        ),
        object_name="liquidAnalysisStatusRail",
    )
    rail.layout().addWidget(
        TelemetryFreshnessRail(
            model.telemetry_label,
            state_role=model.telemetry_role,
            source_label=model.source_label,
            object_name="liquidAnalysisFreshnessRail",
        )
    )
    return rail


def _pipeline_hero(page: AnalysisCommandPage, model: AnalysisCommandModel) -> QWidget:
    hero = LiquidHeroPanel(
        f"Axis: {model.selected_axis}",
        "Raw input is traced through workspace response stages into Final Output Intent. Output proof is shown separately.",
        object_name="liquidAnalysisPipelineHero",
        state_role=model.telemetry_role,
        minimum_height=260,
    )
    hero.setProperty("analysisHeroRole", "pipeline")
    layout = hero.layout()
    if layout is None:
        return hero
    chips = horizontal_layout(spacing=8)
    chips.addWidget(TruthBadge(model.sample_truth_label, state_role=model.telemetry_role, helper_text=model.freshness_label))
    chips.addWidget(TruthBadge(model.output_proof_label, state_role=model.output_proof_role, helper_text="Output intent is not proof."))
    layout.addLayout(chips)
    stage_chain = glass_panel("liquidAnalysisResponseStackChain", role="liquid_analysis_response_stack_chain")
    stage_chain.setProperty("componentRole", "AnalysisResponseStackChain")
    stage_chain.setProperty("liquidComponent", True)
    stage_chain.setProperty("chainOrder", tuple(stage.stage_name for stage in model.pipeline_stages))
    stage_row = horizontal_layout(stage_chain, margins=(0, 4, 0, 4), spacing=8)
    for stage in model.pipeline_stages:
        widget = _pipeline_stage_widget(stage)
        stage_row.addWidget(widget, 1)
        if stage is not model.pipeline_stages[-1]:
            connector = QLabel(">")
            connector.setObjectName(f"liquidAnalysisChainConnector_{stage.stage_id}")
            connector.setProperty("analysisChainConnector", True)
            connector.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stage_row.addWidget(connector)
    layout.addWidget(stage_chain)
    layout.addWidget(_analysis_stack_actions(page, model))
    return hero


def _pipeline_stage_widget(stage: AnalysisPipelineStageModel) -> SignalPipelineStage:
    widget = SignalPipelineStage(
        stage.stage_name,
        stage.stage_summary,
        selected_value=stage.value_text,
        status_role=stage.state_role,
        warning_text=stage.warning_text,
        object_name=f"liquidAnalysisStage_{stage.stage_id}",
    )
    widget.setProperty("analysisPipelineStage", True)
    widget.setProperty("stageId", stage.stage_id)
    widget.setProperty("stageName", stage.stage_name)
    widget.setProperty("selectableStage", True)
    widget.setToolTip(f"{stage.source_label}. {stage.stage_summary}")
    return widget


def _analysis_stack_actions(page: AnalysisCommandPage, model: AnalysisCommandModel) -> QFrame:
    actions = glass_panel("liquidAnalysisStackActions", role="liquid_analysis_stack_actions")
    actions.setProperty("componentRole", "AnalysisStackActions")
    actions.setProperty("liquidComponent", True)
    actions.setProperty("pageActionCluster", True)
    layout = horizontal_layout(actions, margins=(0, 6, 0, 4), spacing=8)
    layout.addWidget(_copy_button("Copy selected stage", "liquidAnalysisCopyStageButton", _stage_summary_text(model.pipeline_stages[0])))
    layout.addWidget(_copy_button("Copy response stack", "liquidAnalysisCopyStackButton", _stack_summary_text(model)))
    layout.addWidget(_analysis_nav_button("Open Base Tuning", "tuning.base_tuning", "liquidAnalysisOpenBaseTuningButton", page._on_route_requested))
    layout.addWidget(_analysis_nav_button("Open Filtering", "tuning.filtering", "liquidAnalysisOpenFilteringButton", page._on_route_requested))
    layout.addWidget(_analysis_nav_button("Open Combat Profile", "tuning.combat_profile", "liquidAnalysisOpenCombatButton", page._on_route_requested))
    layout.addWidget(_analysis_nav_button("Open Conditional Rules", "tuning.conditional_rules", "liquidAnalysisOpenRulesButton", page._on_route_requested))
    layout.addWidget(_analysis_nav_button("Open Live Monitor", "analysis.live_monitor", "liquidAnalysisOpenLiveMonitorButton", page._on_route_requested))
    layout.addStretch(1)
    return actions


def _axis_inspector(
    model: AnalysisCommandModel,
    *,
    on_axis_selected: Callable[[str], None],
) -> QWidget:
    panel = LiquidInspectorPanel(
        "Selected Axis Inspector",
        "Selection changes the Analysis view only. No workspace edit, output change, or runtime probe is performed.",
        object_name="liquidAnalysisAxisInspector",
        state_role=model.telemetry_role,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    selector_panel = QFrame()
    selector_panel.setObjectName("liquidAnalysisAxisSelectorPanel")
    selector_layout = vertical_layout(selector_panel, margins=(0, 0, 0, 0), spacing=8)
    selector_layout.addWidget(QLabel("Selected axis"))
    selector = AxisSelectorPills(selected_axis=model.selected_axis, object_name="liquidAnalysisAxisSelector")
    selector.selectionChanged.connect(on_axis_selected)
    selector_layout.addWidget(selector)
    layout.addWidget(selector_panel)
    snapshot_axis = _axis_by_name(model, model.selected_axis)
    layout.addWidget(
        LiveSnapshotBlock(
            selected_control=model.selected_axis,
            source_truth_label=model.sample_truth_label,
            raw_value=snapshot_axis.raw_text,
            output_intent_value=snapshot_axis.final_text,
            state_role=snapshot_axis.state_role,
            object_name="liquidAnalysisLiveSnapshot",
        )
    )
    for label, value, caption, role in model.metrics:
        layout.addWidget(MetricTile(label, value, caption, state_role=role, object_name=f"liquidAnalysisMetric_{_key(label)}"))
    return panel


def _pipeline_detail(model: AnalysisCommandModel) -> QWidget:
    panel = LiquidDetailPanel(
        "Stage Details",
        "Each stage reports the selected-axis value only when the passive snapshot or workspace preview can support it.",
        object_name="liquidAnalysisStageDetails",
        state_role=model.telemetry_role,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    for stage in model.pipeline_stages:
        row = QFrame()
        row.setObjectName(f"liquidAnalysisStageDetail_{stage.stage_id}")
        row.setProperty("analysisPipelineStage", True)
        row_layout = vertical_layout(row, margins=(10, 8, 10, 8), spacing=4)
        row_layout.addWidget(StatusChip(f"{stage.stage_name}: {stage.value_text}", state_role=stage.state_role))
        row_layout.addWidget(_label(stage.source_label, "liquidAnalysisStageSource"))
        row_layout.addWidget(_label(stage.stage_summary, "liquidAnalysisStageDetailText", wrap=True))
        layout.addWidget(row)
    return panel


def _live_monitor_hero(page: AnalysisCommandPage, model: AnalysisCommandModel) -> QWidget:
    hero = LiquidHeroPanel(
        "Live Monitor",
        "Instrument view of passive axis, button, and hat state. Stale or missing telemetry stays labeled.",
        object_name="liquidAnalysisLiveMonitorHero",
        state_role=model.telemetry_role,
        minimum_height=250,
    )
    hero.setProperty("analysisHeroRole", "live_monitor")
    layout = hero.layout()
    if layout is None:
        return hero
    row = horizontal_layout(spacing=10)
    row.addWidget(TruthBadge(model.telemetry_label, state_role=model.telemetry_role, helper_text=model.freshness_label), 2)
    row.addWidget(TruthBadge(model.sample_truth_label, state_role=model.telemetry_role, helper_text=model.source_label), 2)
    row.addWidget(TruthBadge(model.output_proof_label, state_role=model.output_proof_role, helper_text="Final values remain Output Intent unless proof is reported."), 2)
    layout.addLayout(row)
    metric_row = horizontal_layout(spacing=8)
    for label, value, caption, role in model.metrics:
        metric_row.addWidget(MetricTile(label, value, caption, state_role=role, object_name=f"liquidAnalysisHeroMetric_{_key(label)}"), 1)
    layout.addLayout(metric_row)
    layout.addWidget(
        LiveAxisTimeSeriesGraph(
            axis_history=page._axis_history,
            overlay_final_values=page._overlay_final_values,
            capacity=120,
            state_role=model.telemetry_role,
            object_name="liquidAnalysisLiveTimeSeriesGraph",
        )
    )
    layout.addWidget(_live_monitor_actions(page, model))
    return hero


def _live_axis_instruments(model: AnalysisCommandModel) -> QWidget:
    panel = LiquidInspectorPanel(
        "Axis Instruments",
        "Raw/current and Final Output Intent bars are read-only. Values do not prove a vJoy write.",
        object_name="liquidAnalysisAxisInstrumentPanel",
        state_role=model.telemetry_role,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    grid = grid_layout(margins=(0, 0, 0, 0), spacing=8)
    for index, axis in enumerate(model.axis_monitors):
        grid.addWidget(
            AxisBarPair(
                axis.axis_name,
                raw_value=_meter_value(axis.raw_value),
                output_intent_value=_meter_value(axis.final_value),
                state_role=axis.state_role,
                object_name=f"liquidAnalysisAxisPair_{_key(axis.axis_name)}",
            ),
            index // 2,
            index % 2,
        )
    layout.addLayout(grid)
    return panel


def _live_controls_detail(page: AnalysisCommandPage, model: AnalysisCommandModel) -> QWidget:
    panel = LiquidDetailPanel(
        "Buttons / Hat",
        "Button and hat state is passive telemetry only. Unavailable controls stay labeled.",
        object_name="liquidAnalysisControlsDetail",
        state_role=model.telemetry_role,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    layout.addWidget(
        ButtonIlluminationGrid(
            buttons=tuple(button.label for button in model.buttons),
            active_buttons=tuple(button.label for button in model.buttons if button.active),
            state_role=model.telemetry_role,
            object_name="liquidAnalysisButtonGrid",
        )
    )
    layout.addWidget(QLabel(model.hat_label))
    layout.addWidget(
        HatDirectionIndicator(
            selected_direction=model.hat_direction,
            state_role=model.hat_role,
            object_name="liquidAnalysisHatIndicator",
        )
    )
    for warning in model.warnings:
        layout.addWidget(StatusChip(warning, state_role="warning", object_name="liquidAnalysisWarningChip"))
    return panel


def _live_monitor_actions(page: AnalysisCommandPage, model: AnalysisCommandModel) -> QFrame:
    actions = glass_panel("liquidLiveMonitorActions", role="liquid_live_monitor_actions")
    actions.setProperty("componentRole", "LiveMonitorActions")
    actions.setProperty("liquidComponent", True)
    actions.setProperty("pageActionCluster", True)
    layout = horizontal_layout(actions, margins=(0, 6, 0, 4), spacing=8)
    overlay = action_button("Overlay raw/final", object_name="liquidLiveMonitorOverlayToggle", enabled=True)
    overlay.setCheckable(True)
    overlay.setChecked(page._overlay_final_values)
    overlay.setProperty("overlayFinalValues", page._overlay_final_values)
    overlay.setToolTip("Toggle final Output Intent values over raw input history. This is UI-only and does not change output.")
    overlay.clicked.connect(lambda _checked=False: page.toggle_overlay())
    layout.addWidget(overlay)
    pause = action_button("Pause visual monitor" if not page._monitor_paused else "Resume visual monitor", object_name="liquidLiveMonitorPauseButton", enabled=True)
    pause.setToolTip("Pause or resume local graph drawing only. This does not pause hardware, runtime, or Bridge.")
    pause.clicked.connect(lambda _checked=False: page.toggle_monitor_pause())
    layout.addWidget(pause)
    clear = action_button("Clear local graph history", object_name="liquidLiveMonitorClearHistoryButton", enabled=True)
    clear.setToolTip("Clear only the local Liquid graph history buffer.")
    clear.clicked.connect(lambda _checked=False: page.clear_live_history())
    layout.addWidget(clear)
    layout.addWidget(_copy_button("Copy current sample", "liquidLiveMonitorCopySampleButton", _current_sample_text(model)))
    layout.addWidget(_copy_button("Copy telemetry summary", "liquidLiveMonitorCopyTelemetryButton", _stack_summary_text(model)))
    layout.addWidget(_analysis_nav_button("Open Effective Response Stack", "analysis.effective_response_stack", "liquidLiveMonitorOpenStackButton", page._on_route_requested))
    layout.addStretch(1)
    return actions


def _advanced_details(model: AnalysisCommandModel) -> QWidget:
    panel = LiquidAdvancedSection(
        "Advanced Raw Telemetry",
        "Compact raw Analysis details. The normal page remains focused on the command answer, not debug dumps.",
        object_name="liquidAnalysisAdvancedDetails",
        state_role="info",
    )
    panel.setProperty("advancedSecondary", True)
    panel.setProperty("visualWeight", "subdued")
    layout = panel.layout()
    if layout is None:
        return panel
    for key, value in model.advanced_details:
        row = horizontal_layout(spacing=10)
        row.addWidget(_label(key, "liquidAnalysisAdvancedKey"), 1)
        row.addWidget(_label(value, "liquidAnalysisAdvancedValue", wrap=True), 2)
        layout.addLayout(row)
    for note in model.truth_source_notes:
        layout.addWidget(StatusChip(note, state_role="info", object_name="liquidAnalysisTruthNote"))
    return panel


def _copy_button(text: str, object_name: str, payload: str) -> QPushButton:
    button = action_button(text, object_name=object_name, enabled=True)
    button.setProperty("copyOnly", True)
    button.setToolTip("Copy Analysis information to the clipboard. This does not change runtime state.")
    button.setStatusTip(button.toolTip())
    button.setAccessibleDescription(button.toolTip())
    button.clicked.connect(lambda _checked=False, data=payload: _copy_to_clipboard(data))
    return button


def _analysis_nav_button(
    text: str,
    route_key: str,
    object_name: str,
    on_route_requested: RouteCallback | None = None,
) -> QPushButton:
    button = action_button(text, object_name=object_name, enabled=on_route_requested is not None)
    button.setProperty("navigationOnly", True)
    button.setProperty("routeTarget", route_key)
    reason = f"Navigate to {route_key}. This does not change runtime state."
    if on_route_requested is None:
        reason = f"{reason} Navigation callback unavailable in this context."
    button.setToolTip(reason)
    button.setStatusTip(reason)
    button.setAccessibleDescription(reason)
    if on_route_requested is not None:
        button.clicked.connect(lambda _checked=False, target=route_key: on_route_requested(target))
    return button


def _copy_to_clipboard(text: str) -> None:
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)


def _stage_summary_text(stage: AnalysisPipelineStageModel) -> str:
    return "\n".join(
        (
            f"Stage: {stage.stage_name}",
            f"Value: {stage.value_text}",
            f"Summary: {stage.stage_summary}",
            f"Source: {stage.source_label}",
            "Output intent remains separate from output proof.",
        )
    )


def _stack_summary_text(model: AnalysisCommandModel) -> str:
    lines = [
        f"Route: {model.route_key}",
        f"Selected axis: {model.selected_axis}",
        f"Telemetry: {model.telemetry_label}",
        f"Output proof: {model.output_proof_label}",
    ]
    lines.extend(f"{stage.stage_name}: {stage.value_text} - {stage.stage_summary}" for stage in model.pipeline_stages)
    lines.append("No runtime mutation performed by copy action.")
    return "\n".join(lines)


def _current_sample_text(model: AnalysisCommandModel) -> str:
    lines = [
        f"Telemetry: {model.telemetry_label}",
        f"Source: {model.source_label}",
    ]
    lines.extend(f"{axis.axis_name}: raw={axis.raw_text}, final={axis.final_text}" for axis in model.axis_monitors)
    return "\n".join(lines)


def _axis_by_name(model: AnalysisCommandModel, axis_name: str) -> AnalysisAxisMonitorModel:
    for axis in model.axis_monitors:
        if axis.axis_name == axis_name:
            return axis
    return model.axis_monitors[0]


def _label(text: str, object_name: str, *, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    return label


def _meter_value(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, (float(value) + 1.0) / 2.0))


def _key(value: str) -> str:
    return (
        value.strip()
        .casefold()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace(":", "")
    )
