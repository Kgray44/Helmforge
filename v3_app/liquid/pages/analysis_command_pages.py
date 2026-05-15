from __future__ import annotations

import math
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QWidget

from shared_core.math.pipeline import WorkspaceSignalPipeline
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
from v3_app.liquid.glass import action_button, glass_panel, mark_action_feedback
from v3_app.liquid.instruments import AxisBarPair, ButtonIlluminationGrid, HatDirectionIndicator, LiveAxisTimeSeriesGraph
from v3_app.liquid.layout import grid_layout, horizontal_layout, vertical_layout
from v3_app.liquid.motion import MotionIntensity, MotionSettings, apply_status_motion, current_motion_settings
from v3_app.liquid.models.analysis_command_model import (
    AnalysisAxisMonitorModel,
    AnalysisCommandModel,
    AnalysisPipelineStageModel,
    build_analysis_command_model,
)
from v3_app.liquid.parameter_controls import AxisSelectorPills, LiveSnapshotBlock
from v3_app.liquid.status_components import MetricTile, StatusChip, TelemetryFreshnessRail, TruthBadge, status_tone_for_role
from v3_app.services.app_state import AppState


AxisSelectedCallback = Callable[[str, str], None]
RouteCallback = Callable[[str], None]

LIQUID_LIVE_MONITOR_VISUAL_TARGET_FPS = 60
LIQUID_LIVE_MONITOR_VISUAL_INTERVAL_MS = 16
LIQUID_LIVE_MONITOR_DISPLAY_INTERVAL_MS = LIQUID_LIVE_MONITOR_VISUAL_INTERVAL_MS
LIQUID_LIVE_MONITOR_GRAPH_CADENCE_HZ = LIQUID_LIVE_MONITOR_VISUAL_TARGET_FPS
LIQUID_LIVE_MONITOR_HISTORY_CAPACITY = 120


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
        motion_settings: MotionSettings | None = None,
    ) -> None:
        self.route_key = route_key
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._telemetry = telemetry
        self._motion_settings = motion_settings or current_motion_settings()
        self._selected_axis = selected_axis if selected_axis in AXIS_NAMES else "Roll"
        self._on_axis_selected = on_axis_selected
        self._on_route_requested = on_route_requested
        self._axis_history: dict[str, list[tuple[float | None, float | None]]] = {axis: [] for axis in AXIS_NAMES}
        self._overlay_final_values = False
        self._monitor_paused = False
        self._live_monitor_active = False
        self._suppress_next_display_sample = False
        self._live_display_timer_id = 0
        self._last_live_sample_signature: tuple[object, ...] | None = None
        self._last_telemetry_data_signature: tuple[object, ...] | None = _telemetry_data_signature(telemetry)
        self._selected_stage_id = "raw"
        self._last_signature: tuple[object, ...] | None = None
        self._last_pipeline_detail_signature: tuple[object, ...] | None = None
        self._pipeline = WorkspaceSignalPipeline(self._workspace)
        self._pipeline_workspace_id = id(self._workspace)
        self.render_count = 0
        self.full_render_count = 0
        self.model_build_count = 0
        self.freshness_update_count = 0
        self.numeric_panel_rebuild_count = 0
        self.numeric_panel_update_count = 0
        self.display_timer_tick_count = 0
        self.visual_frame_tick_count = 0
        self.visual_graph_repaint_count = 0
        self.live_motion_frame_count = 0
        self.accepted_sample_count = 0
        self.duplicate_sample_skip_count = 0
        self.graph_update_count = 0
        self.status_surface_update_count = 0
        self.model = self._build_model()
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
        self.setProperty("liveMonitorDisplayIntervalMs", LIQUID_LIVE_MONITOR_DISPLAY_INTERVAL_MS)
        self.setProperty("liveMonitorGraphCadenceHz", LIQUID_LIVE_MONITOR_GRAPH_CADENCE_HZ)
        self.setProperty("liveMonitorVisualTargetFps", LIQUID_LIVE_MONITOR_VISUAL_TARGET_FPS)
        self.setProperty("liveMonitorVisualIntervalMs", LIQUID_LIVE_MONITOR_VISUAL_INTERVAL_MS)
        self.setProperty("liveMonitorVisualRenderOnly", True)
        self.setProperty("motionIntensity", self._motion_settings.intensity.value)
        self.setProperty("liveMonitorFallbackMotionTruthLabel", "Simulation/Fallback visual motion only")
        self.setProperty("liveMonitorFallbackMotionActive", False)
        self.setProperty("liveMonitorFallbackMotionPhase", 0.0)
        self.setProperty("liveMonitorVisualFrameTickCount", self.visual_frame_tick_count)
        self.setProperty("liveMonitorVisualGraphRepaintCount", self.visual_graph_repaint_count)
        self.setProperty("liveMonitorDisplayTimerTickCount", self.display_timer_tick_count)
        self.setProperty("liveMonitorAcceptedSampleCount", self.accepted_sample_count)
        self.setProperty("liveMonitorDuplicateSampleSkipCount", self.duplicate_sample_skip_count)
        self.setProperty("liveMonitorGraphUpdateCount", self.graph_update_count)
        self.setProperty("liveMonitorFullRenderCount", self.full_render_count)
        self.setProperty("liveMonitorStatusSurfaceUpdateCount", self.status_surface_update_count)
        self.setProperty("liveMotionFrameCount", self.live_motion_frame_count)
        self.setProperty("liveMotionState", "stale" if _live_motion_stale_role("blocked") else "live")
        self.setProperty("liveMotionChangesRuntimeTruth", False)
        self._render(force=True)

    def set_live_monitor_active(self, active: bool) -> None:
        if self.route_key != "analysis.live_monitor":
            return
        self._live_monitor_active = bool(active)
        self.setProperty("liveMonitorDisplayActive", self._live_monitor_active)
        if self._live_monitor_active and not self._monitor_paused:
            self._start_live_display_timer()
        else:
            self._stop_live_display_timer()

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        self.setProperty("motionIntensity", motion_settings.intensity.value)
        self.setProperty("liveMonitorFallbackMotionActive", self._fallback_visual_motion_enabled())

    def timerEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.timerId() == self._live_display_timer_id:
            self.advance_live_monitor_visual_frame()
            event.accept()
            return
        super().timerEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._stop_live_display_timer()
        super().hideEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        if self._live_monitor_active and not self._monitor_paused:
            self._start_live_display_timer()

    def advance_live_monitor_display_sample(self) -> bool:
        return self.advance_live_monitor_visual_frame()

    def advance_live_monitor_visual_frame(self) -> bool:
        if self.route_key != "analysis.live_monitor" or not self._live_monitor_active or self._monitor_paused:
            return False
        self.display_timer_tick_count += 1
        self.visual_frame_tick_count += 1
        self.live_motion_frame_count += 1
        self.setProperty("liveMonitorDisplayTimerTickCount", self.display_timer_tick_count)
        self.setProperty("liveMonitorVisualFrameTickCount", self.visual_frame_tick_count)
        stale = _live_motion_stale_role(self.model.telemetry_role)
        self.setProperty("liveMotionFrameCount", self.live_motion_frame_count)
        self.setProperty("liveMotionState", "stale" if stale else "live")
        self.setProperty("liveMotionActive", not stale)
        self.setProperty("staleMotionFrozen", stale)
        self.setProperty("liveMotionChangesRuntimeTruth", False)
        fallback_motion = self._fallback_visual_motion_enabled(stale=stale)
        fallback_phase = (self.live_motion_frame_count % 240) / 240.0 if fallback_motion else 0.0
        self.setProperty("liveMonitorFallbackMotionActive", fallback_motion)
        self.setProperty("liveMonitorFallbackMotionPhase", round(fallback_phase, 3))
        self.setProperty("liveMonitorFallbackMotionTruthLabel", "Simulation/Fallback visual motion only")
        if self._suppress_next_display_sample:
            self._suppress_next_display_sample = False
            self._update_live_history_property()
        self._update_live_axis_instruments_visual(stale=stale, fallback_phase=fallback_phase if fallback_motion else None)
        self._update_live_monitor_graph(repaint=True)
        self.setProperty("liveMonitorVisualSamplePaintCount", int(self.property("liveMonitorVisualSamplePaintCount") or 0) + 1)
        return True

    def axis_history_for_test(self, axis_name: str) -> tuple[tuple[float | None, float | None], ...]:
        return tuple(self._axis_history.get(axis_name, ()))

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
        previous_workspace = self._workspace
        self._state = state or self._state
        self._workspace = workspace or self._workspace
        workspace_changed = workspace is not None and workspace is not previous_workspace
        telemetry_data_signature = _telemetry_data_signature(telemetry)
        if selected_axis in AXIS_NAMES:
            self._selected_axis = str(selected_axis)
            self.setProperty("selectedAxis", self._selected_axis)
        axis_changed = selected_axis in AXIS_NAMES and str(selected_axis) != self.model.selected_axis
        same_structural_data = (
            telemetry_data_signature == self._last_telemetry_data_signature
            and not axis_changed
            and not workspace_changed
        )
        self._telemetry = telemetry
        if same_structural_data:
            self._update_freshness_display(telemetry)
            return
        self._last_telemetry_data_signature = telemetry_data_signature
        previous_model = self.model
        previous_signature = previous_model.signature
        self._refresh_model()
        if self.route_key == "analysis.effective_response_stack" and telemetry is not None:
            if self._update_pipeline_in_place():
                return
        if self.route_key == "analysis.live_monitor" and telemetry is not None and not self._monitor_paused:
            status_changed = _live_monitor_status_signature(previous_model) != _live_monitor_status_signature(self.model)
            sample_signature = _live_sample_signature(self.model)
            if sample_signature == self._last_live_sample_signature:
                self._last_signature = self.model.signature
                self.duplicate_sample_skip_count += 1
                self.setProperty("liveMonitorDuplicateSampleSkipCount", self.duplicate_sample_skip_count)
                self._update_live_history_property()
                if status_changed:
                    self._update_live_monitor_status_surfaces()
                    self._update_live_numeric_values()
                return
            self._last_live_sample_signature = sample_signature
            self._append_live_history(self.model)
            self._update_live_monitor_graph(repaint=False)
            if status_changed:
                self._update_live_monitor_status_surfaces()
                self._update_live_numeric_values()
            else:
                self._update_live_numeric_values()
            self._last_signature = self.model.signature
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
            mark_action_feedback(toggle, "Raw/final overlay toggled for local display only.")
        self._update_live_monitor_graph(repaint=True)

    def select_stage(self, stage_id: str) -> None:
        stage_ids = {stage.stage_id for stage in self.model.pipeline_stages}
        if stage_id not in stage_ids or stage_id == self._selected_stage_id:
            return
        self._selected_stage_id = stage_id
        self.setProperty("selectedStageId", stage_id)
        self.set_detail(_pipeline_detail(self.model, self._selected_stage_id))

    def clear_live_history(self) -> None:
        for samples in self._axis_history.values():
            samples.clear()
        self._suppress_next_display_sample = True
        self.setProperty("liveMonitorHistoryLength", 0)
        self._update_live_monitor_graph()
        clear = self.findChild(QPushButton, "liquidLiveMonitorClearHistoryButton")
        if clear is not None:
            mark_action_feedback(clear, "Cleared local monitor history; runtime unchanged.")

    def toggle_monitor_pause(self) -> None:
        self._monitor_paused = not self._monitor_paused
        if self._monitor_paused:
            self._stop_live_display_timer()
        elif self._live_monitor_active:
            self._start_live_display_timer()
        pause = self.findChild(QPushButton, "liquidLiveMonitorPauseButton")
        if pause is not None:
            pause.setText("Resume visual monitor" if self._monitor_paused else "Pause visual monitor")
            mark_action_feedback(pause, "Toggled visual monitor pause; runtime unchanged.")

    def _start_live_display_timer(self) -> None:
        if self._live_display_timer_id or self.route_key != "analysis.live_monitor":
            return
        self._live_display_timer_id = self.startTimer(LIQUID_LIVE_MONITOR_VISUAL_INTERVAL_MS)
        self.setProperty("liveMonitorDisplayIntervalMs", LIQUID_LIVE_MONITOR_DISPLAY_INTERVAL_MS)
        self.setProperty("liveMonitorGraphCadenceHz", LIQUID_LIVE_MONITOR_GRAPH_CADENCE_HZ)
        self.setProperty("liveMonitorVisualTargetFps", LIQUID_LIVE_MONITOR_VISUAL_TARGET_FPS)
        self.setProperty("liveMonitorVisualIntervalMs", LIQUID_LIVE_MONITOR_VISUAL_INTERVAL_MS)
        self.setProperty("liveMonitorVisualRenderOnly", True)
        self.setProperty("liveMonitorDisplayTimerActive", True)

    def _stop_live_display_timer(self) -> None:
        if not self._live_display_timer_id:
            self.setProperty("liveMonitorDisplayTimerActive", False)
            return
        self.killTimer(self._live_display_timer_id)
        self._live_display_timer_id = 0
        self.setProperty("liveMonitorDisplayTimerActive", False)

    def _build_model(self) -> AnalysisCommandModel:
        if id(self._workspace) != self._pipeline_workspace_id:
            self._pipeline = WorkspaceSignalPipeline(self._workspace)
            self._pipeline_workspace_id = id(self._workspace)
        self.model_build_count += 1
        return build_analysis_command_model(
            route_key=self.route_key,
            workspace=self._workspace,
            state=self._state,
            telemetry=self._telemetry,
            selected_axis=self._selected_axis,
            pipeline=self._pipeline,
        )

    def _refresh_model(self) -> None:
        self.model = self._build_model()

    def _render(self, *, force: bool = False) -> None:
        if not force and self.model.signature == self._last_signature:
            return
        self._last_signature = self.model.signature
        self.render_count += 1
        self.full_render_count = self.render_count
        self.setProperty("liveMonitorFullRenderCount", self.full_render_count)
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
        self.set_status_rail(_status_rail(self, self.model))
        if self.route_key == "analysis.effective_response_stack":
            self._render_effective_response_stack()
        else:
            self._render_live_monitor()
        self.set_advanced(_advanced_details(self.model))

    def _render_effective_response_stack(self) -> None:
        self.set_hero(_pipeline_hero(self, self.model))
        self.set_inspector(_axis_inspector(self.model, on_axis_selected=self.select_axis))
        self.set_detail(_pipeline_detail(self.model, self._selected_stage_id))

    def _render_live_monitor(self) -> None:
        self.set_hero(_live_monitor_hero(self, self.model))
        self.numeric_panel_rebuild_count += 1
        self.set_inspector(_live_axis_instruments(self, self.model))
        self.set_detail(_live_controls_detail(self, self.model))

    def _append_live_history(self, model: AnalysisCommandModel) -> None:
        for axis in model.axis_monitors:
            self._axis_history.setdefault(axis.axis_name, []).append((axis.raw_value, axis.final_value))
            if len(self._axis_history[axis.axis_name]) > LIQUID_LIVE_MONITOR_HISTORY_CAPACITY:
                del self._axis_history[axis.axis_name][:-LIQUID_LIVE_MONITOR_HISTORY_CAPACITY]
        self.accepted_sample_count += 1
        self.setProperty("liveMonitorAcceptedSampleCount", self.accepted_sample_count)
        self._update_live_history_property()

    def _history_length(self) -> int:
        return max((len(samples) for samples in self._axis_history.values()), default=0)

    def _update_live_history_property(self) -> None:
        length = self._history_length()
        self.setProperty("liveMonitorHistoryLength", length)
        graph = self.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
        if graph is not None:
            graph.setProperty("historyLength", length)

    def _update_live_monitor_graph(self, *, repaint: bool = True) -> None:
        graph = self.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
        if graph is not None and hasattr(graph, "update_history"):
            graph.update_history(self._axis_history, overlay_final_values=self._overlay_final_values, repaint=repaint)
            if hasattr(graph, "advance_marker_motion"):
                graph.advance_marker_motion(stale=_live_motion_stale_role(self.model.telemetry_role))
            if repaint:
                self.graph_update_count += 1
                self.visual_graph_repaint_count += 1
                self.setProperty("liveMonitorGraphUpdateCount", self.graph_update_count)
                self.setProperty("liveMonitorVisualGraphRepaintCount", self.visual_graph_repaint_count)
        self._update_live_history_property()

    def _update_live_axis_instruments_visual(self, *, stale: bool = False, fallback_phase: float | None = None) -> None:
        for index, axis in enumerate(self.model.axis_monitors):
            pair = self.findChild(AxisBarPair, f"liquidAnalysisAxisPair_{_key(axis.axis_name)}")
            if pair is not None and hasattr(pair, "update_values"):
                fallback = fallback_phase is not None
                if fallback:
                    raw_value, final_value = _fallback_meter_values(fallback_phase, index)
                else:
                    raw_value = _meter_value(axis.raw_value)
                    final_value = _meter_value(axis.final_value)
                pair.update_values(
                    raw_value=raw_value,
                    output_intent_value=final_value,
                    stale=stale and not fallback,
                )
                pair.setProperty("simulationFallbackMotionOnly", fallback)
                pair.setProperty("runtimeMutation", False)
                pair.setProperty("outputProofClaim", False)
                if hasattr(pair, "advance_motion_frame"):
                    pair.advance_motion_frame(stale=stale and not fallback)

    def _fallback_visual_motion_enabled(self, *, stale: bool | None = None) -> bool:
        if self.route_key != "analysis.live_monitor":
            return False
        if self._motion_settings.intensity not in {MotionIntensity.STANDARD, MotionIntensity.CINEMATIC}:
            return False
        stale_state = _live_motion_stale_role(self.model.telemetry_role) if stale is None else bool(stale)
        return stale_state and self.accepted_sample_count == 0

    def _update_live_numeric_values(self) -> None:
        panel = self.findChild(QWidget, "liquidAnalysisCurrentNumericValues")
        if panel is None:
            hero = self.findChild(QWidget, "liquidAnalysisLiveMonitorHero")
            layout = hero.layout() if hero is not None else None
            if layout is not None:
                insert_at = max(0, layout.count() - 2)
                layout.insertWidget(insert_at, _live_numeric_values(self.model))
                self.numeric_panel_rebuild_count += 1
            return
        changed = False
        for axis in self.model.axis_monitors:
            raw = panel.findChild(QLabel, f"liquidAnalysisCurrentRaw_{_key(axis.axis_name)}")
            final = panel.findChild(QLabel, f"liquidAnalysisCurrentFinal_{_key(axis.axis_name)}")
            raw_text = f"Raw {axis.raw_text}"
            final_text = f"Final intent {axis.final_text}"
            if raw is not None and raw.text() != raw_text:
                raw.setText(raw_text)
                changed = True
            if final is not None and final.text() != final_text:
                final.setText(final_text)
                changed = True
        if changed:
            self.numeric_panel_update_count += 1

    def _update_live_monitor_status_surfaces(self) -> None:
        self.set_status_rail(_status_rail(self, self.model))
        _update_truth_badge(
            self.findChild(TruthBadge, "liquidLiveMonitorTelemetryBadge"),
            text=self.model.telemetry_label,
            helper_text=self.model.freshness_label,
            state_role=self.model.telemetry_role,
        )
        _update_truth_badge(
            self.findChild(TruthBadge, "liquidLiveMonitorSampleBadge"),
            text=self.model.sample_truth_label,
            helper_text=self.model.source_label,
            state_role=self.model.telemetry_role,
        )
        _update_truth_badge(
            self.findChild(TruthBadge, "liquidLiveMonitorOutputProofBadge"),
            text=self.model.output_proof_label,
            helper_text="Final values remain Output Intent unless proof is reported.",
            state_role=self.model.output_proof_role,
        )
        for label, value, caption, role in self.model.metrics:
            _update_metric_tile(
                self.findChild(MetricTile, f"liquidAnalysisHeroMetric_{_key(label)}"),
                label=label,
                value=value,
                caption=caption,
                state_role=role,
            )
        self.status_surface_update_count += 1
        self.setProperty("liveMonitorStatusSurfaceUpdateCount", self.status_surface_update_count)

    def _update_freshness_display(self, telemetry: BridgeTelemetrySnapshot | None) -> None:
        timestamp = telemetry.timestamp.isoformat() if telemetry is not None and telemetry.timestamp is not None else "missing"
        self.setProperty("analysisFreshnessTimestamp", timestamp)
        self.freshness_update_count += 1

    def _update_pipeline_in_place(self) -> bool:
        chain = self.findChild(QWidget, "liquidAnalysisResponseStackChain")
        if chain is None:
            return False
        self.setProperty("selectedAxis", self.model.selected_axis)
        for selector in self.findChildren(AxisSelectorPills):
            previous = selector.blockSignals(True)
            selector.set_selected_axis(self.model.selected_axis)
            selector.blockSignals(previous)
        snapshot_axis = _axis_by_name(self.model, self.model.selected_axis)
        snapshot = self.findChild(LiveSnapshotBlock, "liquidAnalysisLiveSnapshot")
        if snapshot is not None:
            snapshot.update_values(
                selected_control=self.model.selected_axis,
                source_truth_label=self.model.sample_truth_label,
                raw_value=snapshot_axis.raw_text,
                output_intent_value=snapshot_axis.final_text,
                state_role=snapshot_axis.state_role,
            )
        for stage in self.model.pipeline_stages:
            widget = self.findChild(SignalPipelineStage, f"liquidAnalysisStage_{_stage_short_id(stage.stage_id)}")
            if widget is None or not hasattr(widget, "update_stage"):
                return False
            widget.update_stage(
                stage_summary=stage.stage_summary,
                selected_value=stage.value_text,
                status_role=stage.state_role,
                warning_text=stage.warning_text,
            )
            widget.setProperty("stageName", stage.stage_name)
            widget.setToolTip(f"{stage.source_label}. {stage.stage_summary}")
        detail_signature = (
            self._selected_stage_id,
            self.model.selected_axis,
            tuple((stage.stage_id, stage.value_text, stage.state_role, stage.warning_text) for stage in self.model.pipeline_stages),
        )
        if detail_signature != self._last_pipeline_detail_signature:
            self.set_detail(_pipeline_detail(self.model, self._selected_stage_id))
            self.set_advanced(_advanced_details(self.model))
            self._last_pipeline_detail_signature = detail_signature
        self._last_signature = self.model.signature
        return True


def create_effective_response_stack_page(**kwargs) -> AnalysisCommandPage:
    return AnalysisCommandPage(route_key="analysis.effective_response_stack", **kwargs)


def create_live_monitor_page(**kwargs) -> AnalysisCommandPage:
    return AnalysisCommandPage(route_key="analysis.live_monitor", **kwargs)


def _status_rail(page: AnalysisCommandPage, model: AnalysisCommandModel) -> LiquidStatusRail:
    rail = LiquidStatusRail(
        items=(
            (model.runtime_truth_label, "ready" if model.runtime_truth_label == "Live Verified" else model.telemetry_role),
            (model.telemetry_label, model.telemetry_role),
            (model.output_proof_label, model.output_proof_role),
        ),
        object_name="liquidAnalysisStatusRail",
    )
    selector = AxisSelectorPills(selected_axis=model.selected_axis, options=model.axis_options, object_name="liquidAnalysisTopAxisSelector")
    selector.setProperty("topLevelAxisSelector", True)
    selector.selectionChanged.connect(page.select_axis)
    rail.layout().insertWidget(0, selector)
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
        minimum_height=640,
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
    stage_chain.setProperty("chainOrientation", "vertical")
    stage_chain.setProperty("dominantVisual", True)
    stage_chain.setProperty("chainImplementation", "cached_lightweight_stage_widgets")
    stage_chain.setMinimumHeight(520)
    stage_row = vertical_layout(stage_chain, margins=(0, 4, 0, 4), spacing=8)
    for stage in model.pipeline_stages:
        widget = _pipeline_stage_widget(stage, on_select=page.select_stage)
        stage_row.addWidget(widget, 1)
        if stage is not model.pipeline_stages[-1]:
            connector = QLabel("v")
            connector.setObjectName(f"liquidAnalysisChainConnector_{stage.stage_id}")
            connector.setProperty("analysisChainConnector", True)
            connector.setProperty("connectorDirection", "down")
            connector.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stage_row.addWidget(connector)
    layout.addWidget(stage_chain)
    layout.addWidget(_analysis_stack_actions(page, model))
    return hero


def _pipeline_stage_widget(
    stage: AnalysisPipelineStageModel,
    *,
    on_select: Callable[[str], None],
) -> SignalPipelineStage:
    widget = SignalPipelineStage(
        stage.stage_name,
        stage.stage_summary,
        selected_value=stage.value_text,
        status_role=stage.state_role,
        warning_text=stage.warning_text,
        object_name=f"liquidAnalysisStage_{_stage_short_id(stage.stage_id)}",
    )
    widget.setProperty("analysisPipelineStage", True)
    widget.setProperty("stageId", stage.stage_id)
    widget.setProperty("stageName", stage.stage_name)
    widget.setProperty("selectableStage", True)
    widget.setToolTip(f"{stage.source_label}. {stage.stage_summary}")
    button = action_button(
        f"Select {stage.stage_name}",
        object_name=f"liquidAnalysisSelectStageButton_{_stage_short_id(stage.stage_id)}",
        enabled=True,
        action_kind="select_state",
    )
    button.setToolTip("Select this response-stack stage for details. This does not mutate runtime state.")
    button.clicked.connect(lambda _checked=False, selected=stage.stage_id: on_select(selected))
    layout = widget.layout()
    if layout is not None:
        layout.addWidget(button)
    return widget


def _analysis_stack_actions(page: AnalysisCommandPage, model: AnalysisCommandModel) -> QFrame:
    actions = glass_panel("liquidAnalysisStackActions", role="liquid_analysis_stack_actions")
    actions.setProperty("componentRole", "AnalysisStackActions")
    actions.setProperty("liquidComponent", True)
    actions.setProperty("pageActionCluster", True)
    layout = horizontal_layout(actions, margins=(0, 6, 0, 4), spacing=8)
    selected_stage = _stage_by_id(model, page._selected_stage_id)
    layout.addWidget(_copy_button("Copy selected stage", "liquidAnalysisCopyStageButton", _stage_summary_text(selected_stage)))
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


def _pipeline_detail(model: AnalysisCommandModel, selected_stage_id: str) -> QWidget:
    panel = LiquidDetailPanel(
        "Stage Details",
        "Each stage reports the selected-axis value only when the passive snapshot or workspace preview can support it.",
        object_name="liquidAnalysisStageDetails",
        state_role=model.telemetry_role,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    selected_stage = _stage_by_id(model, selected_stage_id)
    selected = QFrame()
    selected.setObjectName("liquidAnalysisSelectedStageDetailPanel")
    selected.setProperty("analysisSelectedStageDetail", True)
    selected.setProperty("selectedStageId", _stage_short_id(selected_stage.stage_id))
    selected_layout = vertical_layout(selected, margins=(10, 8, 10, 8), spacing=5)
    selected_layout.addWidget(StatusChip(f"Selected stage: {selected_stage.stage_name}", state_role=selected_stage.state_role))
    selected_layout.addWidget(_label(f"Selected axis: {model.selected_axis}", "liquidAnalysisSelectedStageAxis", wrap=True))
    selected_layout.addWidget(_label(f"Value: {selected_stage.value_text}", "liquidAnalysisSelectedStageValue", wrap=True))
    selected_layout.addWidget(_label(f"Source: {selected_stage.source_label}", "liquidAnalysisSelectedStageSource", wrap=True))
    selected_layout.addWidget(_label(selected_stage.stage_summary, "liquidAnalysisSelectedStageSummary", wrap=True))
    layout.addWidget(selected)
    for stage in model.pipeline_stages:
        row = QFrame()
        row.setObjectName(f"liquidAnalysisStageDetail_{stage.stage_id}")
        row.setProperty("analysisPipelineStage", True)
        row.setProperty("selected", stage.stage_id == selected_stage.stage_id)
        row_layout = vertical_layout(row, margins=(10, 8, 10, 8), spacing=4)
        row_layout.addWidget(StatusChip(f"{stage.stage_name}: {stage.value_text}", state_role=stage.state_role))
        row_layout.addWidget(_label(f"Selected axis: {model.selected_axis}", "liquidAnalysisStageAxis"))
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
        minimum_height=560,
    )
    hero.setProperty("analysisHeroRole", "live_monitor")
    layout = hero.layout()
    if layout is None:
        return hero
    row = horizontal_layout(spacing=10)
    row.addWidget(
        TruthBadge(
            model.telemetry_label,
            state_role=model.telemetry_role,
            helper_text=model.freshness_label,
            object_name="liquidLiveMonitorTelemetryBadge",
        ),
        2,
    )
    row.addWidget(
        TruthBadge(
            model.sample_truth_label,
            state_role=model.telemetry_role,
            helper_text=model.source_label,
            object_name="liquidLiveMonitorSampleBadge",
        ),
        2,
    )
    row.addWidget(
        TruthBadge(
            model.output_proof_label,
            state_role=model.output_proof_role,
            helper_text="Final values remain Output Intent unless proof is reported.",
            object_name="liquidLiveMonitorOutputProofBadge",
        ),
        2,
    )
    layout.addLayout(row)
    if _live_motion_stale_role(model.telemetry_role):
        layout.addWidget(
            StatusChip(
                "Simulation/Fallback visual motion only",
                state_role="simulation",
                object_name="liquidLiveMonitorFallbackMotionChip",
            )
        )
    metric_row = horizontal_layout(spacing=8)
    for label, value, caption, role in model.metrics:
        metric_row.addWidget(MetricTile(label, value, caption, state_role=role, object_name=f"liquidAnalysisHeroMetric_{_key(label)}"), 1)
    layout.addLayout(metric_row)
    layout.addWidget(
        LiveAxisTimeSeriesGraph(
            axis_history=page._axis_history,
            overlay_final_values=page._overlay_final_values,
            capacity=LIQUID_LIVE_MONITOR_HISTORY_CAPACITY,
            state_role=model.telemetry_role,
            object_name="liquidAnalysisLiveTimeSeriesGraph",
        )
    )
    layout.addWidget(_live_numeric_values(model))
    layout.addWidget(_live_monitor_actions(page, model))
    return hero


def _live_numeric_values(model: AnalysisCommandModel) -> QFrame:
    panel = glass_panel("liquidAnalysisCurrentNumericValues", role="liquid_analysis_current_values")
    panel.setProperty("componentRole", "AnalysisCurrentNumericValues")
    panel.setProperty("liquidComponent", True)
    panel.setProperty("currentNumericValues", True)
    layout = grid_layout(panel, margins=(10, 8, 10, 8), spacing=8)
    for index, axis in enumerate(model.axis_monitors):
        cell = glass_panel(f"liquidAnalysisCurrentValue_{_key(axis.axis_name)}", role="liquid_analysis_axis_value")
        cell_layout = vertical_layout(cell, margins=(8, 6, 8, 6), spacing=3)
        cell_layout.addWidget(StatusChip(axis.axis_name, state_role=axis.state_role))
        cell_layout.addWidget(_label(f"Raw {axis.raw_text}", f"liquidAnalysisCurrentRaw_{_key(axis.axis_name)}"))
        cell_layout.addWidget(_label(f"Final intent {axis.final_text}", f"liquidAnalysisCurrentFinal_{_key(axis.axis_name)}"))
        layout.addWidget(cell, index // 3, index % 3)
    return panel


def _live_axis_instruments(page: AnalysisCommandPage, model: AnalysisCommandModel) -> QWidget:
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
                motion_settings=page._motion_settings,
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
    overlay = action_button("Overlay raw/final", object_name="liquidLiveMonitorOverlayToggle", enabled=True, action_kind="toggle_ui")
    overlay.setCheckable(True)
    overlay.setChecked(page._overlay_final_values)
    overlay.setProperty("overlayFinalValues", page._overlay_final_values)
    overlay.setToolTip("Toggle final Output Intent values over raw input history. This is UI-only and does not change output.")
    overlay.clicked.connect(lambda _checked=False: page.toggle_overlay())
    layout.addWidget(overlay)
    pause = action_button(
        "Pause visual monitor" if not page._monitor_paused else "Resume visual monitor",
        object_name="liquidLiveMonitorPauseButton",
        enabled=True,
        action_kind="toggle_ui",
    )
    pause.setToolTip("Pause or resume local graph drawing only. This does not pause hardware, runtime, or Bridge.")
    pause.clicked.connect(lambda _checked=False: page.toggle_monitor_pause())
    layout.addWidget(pause)
    clear = action_button("Clear local graph history", object_name="liquidLiveMonitorClearHistoryButton", enabled=True, action_kind="toggle_ui")
    clear.setToolTip("Clear only the local Liquid graph history buffer.")
    clear.clicked.connect(lambda _checked=False: page.clear_live_history())
    layout.addWidget(clear)
    layout.addWidget(_copy_button("Copy current sample", "liquidLiveMonitorCopySampleButton", _current_sample_text(model)))
    layout.addWidget(_copy_button("Copy telemetry summary", "liquidLiveMonitorCopyTelemetryButton", _stack_summary_text(model)))
    layout.addWidget(_analysis_nav_button("Open Effective Response Stack", "analysis.effective_response_stack", "liquidLiveMonitorOpenStackButton", page._on_route_requested))
    layout.addStretch(1)
    return actions


def _set_component_state_props(widget: QWidget | None, state_role: str) -> None:
    if widget is None:
        return
    normalized = state_role.strip().casefold()
    widget.setProperty("statusRole", normalized)
    widget.setProperty("toneRole", status_tone_for_role(normalized))
    component_role = "status_light" if widget.property("componentRole") == "StatusLight" else "status_card"
    apply_status_motion(widget, state_role=normalized, component_role=component_role, focusable=component_role == "status_card")


def _update_truth_badge(
    badge: TruthBadge | None,
    *,
    text: str,
    helper_text: str,
    state_role: str,
) -> None:
    if badge is None:
        return
    _set_component_state_props(badge, state_role)
    for light in badge.findChildren(QWidget, "liquidStatusLight"):
        _set_component_state_props(light, state_role)
    text_label = badge.findChild(QLabel, "liquidTruthBadgeText")
    if text_label is not None and text_label.text() != text:
        text_label.setText(text)
    helper_label = badge.findChild(QLabel, "liquidTruthBadgeHelper")
    if helper_label is not None and helper_label.text() != helper_text:
        helper_label.setText(helper_text)


def _update_metric_tile(
    tile: MetricTile | None,
    *,
    label: str,
    value: str,
    caption: str,
    state_role: str,
) -> None:
    if tile is None:
        return
    _set_component_state_props(tile, state_role)
    for child in tile.findChildren(QLabel):
        if child.objectName() == "liquidMetricTileLabel" and child.text() != label.upper():
            child.setText(label.upper())
        elif child.objectName() == "liquidMetricTileValue" and child.text() != value:
            child.setText(value)
        elif child.objectName() == "liquidMetricTileCaption" and child.text() != caption:
            child.setText(caption)


def _live_sample_signature(model: AnalysisCommandModel) -> tuple[object, ...]:
    return (
        tuple((axis.axis_name, axis.raw_value, axis.final_value) for axis in model.axis_monitors),
        tuple((button.label, button.active) for button in model.buttons),
        model.hat_direction,
        model.telemetry_label,
    )


def _telemetry_data_signature(telemetry: BridgeTelemetrySnapshot | None) -> tuple[object, ...] | None:
    if telemetry is None:
        return None
    raw = getattr(getattr(telemetry, "raw_axes", None), "values", {}) or {}
    final = getattr(getattr(telemetry, "final_axes", None), "values", {}) or {}
    controls = getattr(telemetry, "controls", None)
    buttons = getattr(controls, "buttons", {}) if controls is not None else {}
    hats = getattr(controls, "hats", {}) if controls is not None else {}
    runtime_frame = dict(telemetry.runtime_frame or {}) if telemetry.runtime_frame is not None else {}
    return (
        telemetry.runtime_truth.value,
        telemetry.lifecycle_state.value,
        telemetry.input_status.value,
        telemetry.output_status.value,
        bool(telemetry.output_verified),
        telemetry.active_profile,
        tuple((axis, None if axis not in raw else round(float(raw.get(axis, 0.0)), 5)) for axis in AXIS_NAMES),
        tuple((axis, None if axis not in final else round(float(final.get(axis, 0.0)), 5)) for axis in AXIS_NAMES),
        tuple(sorted((str(key), bool(value)) for key, value in buttons.items())),
        tuple(sorted((str(key), str(value)) for key, value in hats.items())),
        str(runtime_frame.get("telemetry_proof") or ""),
        bool(runtime_frame.get("input_stale", False)),
    )


def _model_has_axis_sample(model: AnalysisCommandModel) -> bool:
    return any(axis.raw_value is not None or axis.final_value is not None for axis in model.axis_monitors)


def _live_monitor_status_signature(model: AnalysisCommandModel) -> tuple[object, ...]:
    available_axes = sum(1 for axis in model.axis_monitors if axis.raw_value is not None or axis.final_value is not None)
    active_buttons = sum(1 for button in model.buttons if button.active)
    return (
        model.runtime_truth_label,
        model.telemetry_label,
        model.telemetry_role,
        model.source_label,
        model.sample_truth_label,
        model.output_proof_label,
        model.output_proof_role,
        available_axes,
        len(model.axis_monitors),
        active_buttons,
        model.hat_direction,
        tuple(model.warnings),
    )


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
    button = action_button(text, object_name=object_name, enabled=True, action_kind="copy")
    button.setProperty("copyOnly", True)
    button.setToolTip("Copy Analysis information to the clipboard. This does not change runtime state.")
    button.setStatusTip(button.toolTip())
    button.setAccessibleDescription(button.toolTip())
    button.clicked.connect(lambda _checked=False, data=payload, target=button: _copy_to_clipboard(data, target))
    return button


def _analysis_nav_button(
    text: str,
    route_key: str,
    object_name: str,
    on_route_requested: RouteCallback | None = None,
) -> QPushButton:
    button = action_button(
        text,
        object_name=object_name,
        enabled=on_route_requested is not None,
        action_kind="navigation",
        disabled_reason=f"Disabled: navigation callback unavailable for {route_key}." if on_route_requested is None else "",
        route_target=route_key,
    )
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


def _copy_to_clipboard(text: str, button: QPushButton | None = None) -> None:
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)
        if button is not None:
            mark_action_feedback(button, "Copied Analysis information to clipboard.")
    elif button is not None:
        mark_action_feedback(button, "Clipboard unavailable; nothing was copied.")


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


def _stage_by_id(model: AnalysisCommandModel, stage_id: str) -> AnalysisPipelineStageModel:
    for stage in model.pipeline_stages:
        if stage.stage_id == stage_id or _stage_short_id(stage.stage_id) == stage_id:
            return stage
    return model.pipeline_stages[0]


def _stage_short_id(stage_id: str) -> str:
    return {
        "raw_input": "raw",
        "final_output_intent": "final_output",
        "modes_combat_profile": "combat_profile",
        "conditional_rules": "conditional_rules",
        "base_tuning": "base_tuning",
        "filtering": "filtering",
    }.get(stage_id, stage_id)


def _label(text: str, object_name: str, *, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    return label


def _meter_value(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, (float(value) + 1.0) / 2.0))


def _fallback_meter_values(phase: float, axis_index: int) -> tuple[float, float]:
    base = float(phase % 1.0) * math.tau
    offset = axis_index * 0.63
    raw_value = 0.5 + 0.34 * math.sin(base + offset)
    final_value = 0.5 + 0.24 * math.sin(base + offset + 0.9)
    return max(0.0, min(1.0, raw_value)), max(0.0, min(1.0, final_value))


def _live_motion_stale_role(state_role: str) -> bool:
    normalized = state_role.strip().casefold()
    return normalized in {"waiting", "blocked", "error", "failed", "unavailable", "disabled", "missing-proof"}


def _key(value: str) -> str:
    return (
        value.strip()
        .casefold()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace(":", "")
    )
