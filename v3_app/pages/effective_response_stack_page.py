from __future__ import annotations

import time
from dataclasses import replace
from datetime import datetime
from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from shared_core.math.pipeline import WorkspaceSignalPipeline, WorkspaceSignalPipelineResult
from shared_core.math.stack import EXPECTED_STAGE_NAMES, ModeState, StageResult
from shared_core.models.axes import AXIS_DISPLAY_NAMES, axis_by_name
from shared_core.models.runtime import AXIS_NAMES, RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.hotas_input import MissingPhysicalInputBackend, PhysicalInputBackend, PhysicalInputSnapshot
from shared_core.runtime.runtime_bridge import RuntimeBridge
from shared_core.rules.evaluator import RuleStatus
from v3_app.pages.graph_data import effective_response_stack_graph_data
from v3_app.pages.graph_widgets import GraphPreview
from v3_app.pages.page_helpers import add_card_to_grid, card, card_header, card_layout, page_intro, signed, truth_notice, value_grid
from v3_app.services.app_state import AppState
from v3_app.services.perf_diagnostics import DiagnosticsCollector
from v3_app.services.live_refresh import LIVE_REFRESH_INTERVAL_MS
from v3_app.services.live_ui_scheduler import MultiCadenceScheduler
from v3_app.services.physical_input_ui import build_input_source_status, raw_axes_from_physical_snapshot
from v3_app.services.ui_dirty import (
    repolish_if_changed,
    set_bar_value_if_changed,
    set_chip_text_and_tone_if_changed,
    set_label_text_if_changed,
    set_widget_property_if_changed,
)
from v3_app.ui.status_chips import action_button, status_chip


class StageCard(QFrame):
    def __init__(self, stage_name: str, on_select) -> None:
        super().__init__()
        self.stage_name = stage_name
        self._on_select = on_select
        self.setObjectName("stackStageCard")
        self.setProperty("cardRole", "pageCard")
        self.setProperty("selected", False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.update_count = 0
        self.repolish_count = 0
        self._last_signature: tuple[object, ...] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self.title = QLabel(stage_name)
        self.title.setObjectName("cardTitle")
        self.status = status_chip("Inactive", tone="neutral", object_name=f"stageStatus_{_key(stage_name)}")
        header.addWidget(self.title)
        header.addStretch(1)
        header.addWidget(self.status)
        layout.addLayout(header)

        values = QGridLayout()
        values.setHorizontalSpacing(16)
        values.setVerticalSpacing(6)
        self.input_label = _value_pair(values, 0, "IN", f"stageInput_{_key(stage_name)}")
        self.output_label = _value_pair(values, 1, "OUT", f"stageOutput_{_key(stage_name)}")
        self.delta_label = _value_pair(values, 2, "DELTA", f"stageDelta_{_key(stage_name)}")
        layout.addLayout(values)

        self.input_bar = _bar("Input")
        self.output_bar = _bar("Output")
        layout.addWidget(self.input_bar)
        layout.addWidget(self.output_bar)

        self.explanation = QLabel("")
        self.explanation.setObjectName("cardBody")
        self.explanation.setWordWrap(True)
        layout.addWidget(self.explanation)

        self.rule_label = QLabel("")
        self.rule_label.setObjectName(f"stageRuleText_{_key(stage_name)}")
        self.rule_label.setWordWrap(True)
        layout.addWidget(self.rule_label)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._on_select(self.stage_name)
        super().mousePressEvent(event)

    def update_from_stage(self, stage: StageResult) -> None:
        signature = _stage_signature(stage)
        if signature == self._last_signature:
            return
        self._last_signature = signature
        self.update_count += 1
        set_label_text_if_changed(self.input_label, signed(stage.input_value))
        set_label_text_if_changed(self.output_label, signed(stage.output_value))
        set_label_text_if_changed(self.delta_label, signed(stage.delta))
        set_bar_value_if_changed(self.input_bar, _bar_value(stage.input_value))
        set_bar_value_if_changed(self.output_bar, _bar_value(stage.output_value))
        set_label_text_if_changed(self.explanation, stage.explanation)
        status_text, tone = _stage_status(stage)
        if set_chip_text_and_tone_if_changed(self.status, status_text, tone):
            self.repolish_count += 1
        set_label_text_if_changed(self.rule_label, _stage_rule_text(stage))

    def set_selected(self, selected: bool) -> None:
        changed = set_widget_property_if_changed(self, "selected", selected)
        if changed:
            self.repolish_count += 1
        repolish_if_changed(self, changed)


class EffectiveResponseStackPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        physical_input_backend: PhysicalInputBackend | None = None,
        selected_physical_input_device_id: str | None = None,
        physical_input_snapshot: PhysicalInputSnapshot | None = None,
        physical_input_clock: Any | None = None,
        physical_sample_stale_after_seconds: float = 2.0,
        diagnostics_collector: DiagnosticsCollector | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("effectiveResponseStackPage")
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._diagnostics_collector = diagnostics_collector
        self._physical_input_backend = physical_input_backend or MissingPhysicalInputBackend()
        self._selected_physical_input_device_id = selected_physical_input_device_id
        self._physical_input_snapshot = physical_input_snapshot
        self._physical_input_clock = physical_input_clock
        self._physical_sample_stale_after_seconds = physical_sample_stale_after_seconds
        self._input_source_status = build_input_source_status(
            backend=self._physical_input_backend,
            selected_device_id=self._selected_physical_input_device_id,
            latest_snapshot=self._physical_input_snapshot,
            now=self._physical_input_now(),
            stale_after_seconds=self._physical_sample_stale_after_seconds,
        )
        self.selected_axis = state.selected_axis
        self.selected_stage = "Raw Input"
        self.frozen = False
        self._frozen_result: WorkspaceSignalPipelineResult | None = None
        self._frozen_raw_values: dict[str, float] | None = None
        self._current_raw_values: dict[str, float] = {axis: 0.0 for axis in AXIS_NAMES}
        self._current_result: WorkspaceSignalPipelineResult | None = None
        self._pipeline = WorkspaceSignalPipeline(self._workspace)
        self._pipeline_state = self._pipeline.initial_state()
        self._runtime_bridge = RuntimeBridge(
            preflight_status=self._runtime_status,
            deterministic_simulation=False,
        )
        self._scheduler = MultiCadenceScheduler()
        self._last_compute_signature: tuple[object, ...] | None = None
        self._last_render_signature: tuple[object, ...] | None = None
        self._last_static_graph_signature: tuple[object, ...] | None = None
        self._last_marker_signature: tuple[object, ...] | None = None
        self._last_selected_stage_signature: tuple[object, ...] | None = None
        self._last_most_impactful_stage: str | None = None
        self.tick_count = 0
        self.input_sample_count = 0
        self.pipeline_compute_count = 0
        self.full_render_count = 0
        self.static_graph_rebuild_count = 0
        self.marker_update_count = 0
        self.stage_card_update_count = 0
        self.selected_stage_update_count = 0
        self.skipped_repeated_frame_count = 0
        self.stage_widgets: dict[str, StageCard] = {}
        self._stage_by_name: dict[str, StageResult] = {}
        self._total_change_labels: dict[str, QLabel] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)

        root.addWidget(
            page_intro(
                "Effective Response Stack",
                "Inspect one selected axis at a time from raw HOTAS input through shaping, filtering, mode modifiers, rule injections, and final output.",
            )
        )
        root.addWidget(
            truth_notice(
                "Raw input, tuning stages, and final output intent are visual diagnostics. Output intent is not output write proof.",
                object_name="stackPolishTruthNotice",
            )
        )
        root.addWidget(self._build_controls())

        main = QHBoxLayout()
        main.setSpacing(8)
        main.addWidget(self._build_signal_chain_card(), 1)
        main.addLayout(self._build_right_side(), 2)
        root.addLayout(main, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(LIVE_REFRESH_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self.refresh_snapshot()

    def _build_controls(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        axis_label = QLabel("Axis")
        axis_label.setObjectName("formLabel")
        self.axis_selector = QComboBox()
        self.axis_selector.setObjectName("stackAxisSelector")
        self.axis_selector.addItems(AXIS_DISPLAY_NAMES)
        self.axis_selector.setCurrentText(self.selected_axis)
        self.axis_selector.currentTextChanged.connect(self.set_selected_axis)
        self.runtime_chip = status_chip(self._state.runtime.header_truth_label, tone=self._state.runtime.tone)
        self.freeze_button = action_button("Freeze", object_name="freezeStackButton")
        self.freeze_button.clicked.connect(self.toggle_freeze)
        copy = action_button("Copy Snapshot", object_name="copyStackSnapshotButton")
        copy.clicked.connect(self.copy_snapshot)
        self.show_mode_chip = status_chip("Show All", tone="neutral")
        layout.addWidget(axis_label)
        layout.addWidget(self.axis_selector)
        layout.addStretch(1)
        layout.addWidget(self.runtime_chip)
        layout.addWidget(self.show_mode_chip)
        layout.addWidget(self.freeze_button)
        layout.addWidget(copy)
        return row

    def _build_signal_chain_card(self) -> QFrame:
        frame = card("signalChainCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Signal Chain", "Core stages and inline rule injections in execution order."))
        for stage_name in EXPECTED_STAGE_NAMES:
            stage_card = StageCard(stage_name, self.select_stage)
            self.stage_widgets[stage_name] = stage_card
            layout.addWidget(stage_card)
            if stage_name != EXPECTED_STAGE_NAMES[-1]:
                arrow = QLabel("v")
                arrow.setObjectName("sectionHint")
                arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(arrow)
        layout.addStretch(1)
        return frame

    def _build_right_side(self) -> QVBoxLayout:
        side = QVBoxLayout()
        side.setSpacing(18)
        side.addWidget(self._build_graph_card(), 2)
        lower = QGridLayout()
        lower.setHorizontalSpacing(18)
        lower.setVerticalSpacing(18)
        add_card_to_grid(lower, self._build_mode_state_card(), 0, 0)
        add_card_to_grid(lower, self._build_summary_card(), 0, 1)
        add_card_to_grid(lower, self._build_selected_stage_card(), 1, 0)
        add_card_to_grid(lower, self._build_rule_driver_card(), 1, 1)
        side.addLayout(lower, 2)
        return side

    def _build_graph_card(self) -> QFrame:
        frame = card("rawVsFinalCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Raw vs Final", "The live marker rides on the effective response line for the selected axis."))
        self.graph = GraphPreview(object_name="effectiveResponseStackGraph")
        layout.addWidget(self.graph)
        layout.addWidget(self._build_total_change_card())
        caption = QLabel("Raw input on X, effective output intent on Y. Center and marker states remain diagnostics only.")
        caption.setObjectName("cardBody")
        layout.addWidget(caption)
        return frame

    def _build_total_change_card(self) -> QFrame:
        frame = card("stackTotalChangeCard")
        frame.setProperty("deterministicSummary", True)
        layout = card_layout(frame)
        layout.addWidget(card_header("Total Change", "Deterministic before/after summary for the selected axis."))
        rows = QGridLayout()
        rows.setHorizontalSpacing(16)
        rows.setVerticalSpacing(8)
        for row, (label, object_name) in enumerate(
            (
                ("Before", "stackTotalBefore"),
                ("After", "stackTotalAfter"),
                ("Delta", "stackTotalDelta"),
                ("Most impact", "stackMostImpactfulStage"),
            )
        ):
            key = QLabel(label)
            key.setObjectName("tableMutedText")
            value = QLabel("unavailable")
            value.setObjectName(object_name)
            value.setProperty("metricValue", True)
            value.setWordWrap(True)
            rows.addWidget(key, row, 0)
            rows.addWidget(value, row, 1)
            self._total_change_labels[object_name] = value
        layout.addLayout(rows)
        return frame

    def _build_mode_state_card(self) -> QFrame:
        frame = card("modeStateCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Mode State"))
        self.mode_state = QLabel("")
        self.mode_state.setObjectName("modeStateText")
        self.mode_state.setWordWrap(True)
        layout.addWidget(self.mode_state)
        return frame

    def _build_summary_card(self) -> QFrame:
        frame = card("currentStackSummaryCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Current Stack Summary"))
        self.input_source_summary = QLabel("")
        self.input_source_summary.setObjectName("stackInputSourceSummary")
        self.input_source_summary.setWordWrap(True)
        layout.addWidget(self.input_source_summary)
        self.summary = QLabel("")
        self.summary.setObjectName("currentStackSummaryText")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        return frame

    def _build_selected_stage_card(self) -> QFrame:
        frame = card("selectedStageCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Selected Stage", "Click a stage or rule card to inspect it here."))
        self.selected_stage_status = status_chip("Live", tone="success", object_name="selectedStageStatus")
        self.selected_stage_title = QLabel("")
        self.selected_stage_title.setObjectName("selectedStageTitle")
        self.selected_stage_body = QLabel("")
        self.selected_stage_body.setObjectName("selectedStageBody")
        self.selected_stage_body.setWordWrap(True)
        self.selected_stage_metadata = QLabel("")
        self.selected_stage_metadata.setObjectName("selectedStageMetadata")
        self.selected_stage_metadata.setWordWrap(True)
        layout.addWidget(self.selected_stage_status, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.selected_stage_title)
        layout.addWidget(self.selected_stage_body)
        layout.addWidget(self.selected_stage_metadata)
        return frame

    def _build_rule_driver_card(self) -> QFrame:
        frame = card("ruleDriverValuesCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Rule Driver Values"))
        self.rule_drivers = QLabel("")
        self.rule_drivers.setObjectName("ruleDriverValuesText")
        self.rule_drivers.setWordWrap(True)
        layout.addWidget(self.rule_drivers)
        return frame

    def _tick(self) -> None:
        self.tick_count += 1
        if self.frozen:
            return
        if not self.isVisible():
            self._record_hidden_skip()
            return
        started_at = time.perf_counter()
        self.refresh_snapshot()
        self._record_timing("heartbeat", started_at)

    def _record_hidden_skip(self) -> None:
        if self._diagnostics_collector is not None:
            self._diagnostics_collector.record_hidden_skip("Effective Response Stack")

    def _record_timing(self, name: str, started_at: float) -> None:
        if self._diagnostics_collector is not None:
            self._diagnostics_collector.record_timing(name, (time.perf_counter() - started_at) * 1000.0)

    def set_selected_axis(self, axis_name: str) -> None:
        if axis_name not in AXIS_DISPLAY_NAMES:
            return
        self.selected_axis = axis_name
        if self.axis_selector.currentText() != axis_name:
            self.axis_selector.setCurrentText(axis_name)
        self._state.selected_axis = axis_name
        self._last_static_graph_signature = None
        self._last_marker_signature = None
        self.refresh_snapshot(raw_axis_values=self._current_raw_values)

    def refresh_snapshot(self, *, force_new: bool = False, raw_axis_values: dict[str, float] | None = None) -> None:
        if self.frozen and self._frozen_result is not None:
            self._render(self._frozen_result, self._frozen_raw_values or self._current_raw_values, force=force_new)
            return
        if force_new:
            self._scheduler.force_all()

        self._refresh_physical_input_source_status()
        if raw_axis_values is not None:
            current_raw = {axis: float(raw_axis_values.get(axis, 0.0)) for axis in AXIS_NAMES}
        elif self._physical_input_snapshot is not None and self._input_source_status.is_fresh_physical_sample:
            current_raw = raw_axes_from_physical_snapshot(self._physical_input_snapshot)
        else:
            snapshot = self._runtime_bridge.snapshot()
            current_raw = {axis: float(snapshot.raw_axis_values[axis]) for axis in AXIS_NAMES}
        self.input_sample_count += 1
        compute_signature = _raw_signature(current_raw)
        compute_due = raw_axis_values is not None or force_new or self._current_result is None
        compute_due = compute_due or self._scheduler.run("effective_stack_compute")
        if not compute_due and self._current_result is not None:
            self.skipped_repeated_frame_count += 1
            self._current_raw_values = current_raw
            self._update_graph(current_raw, result=self._current_result, marker_only=True)
            return

        started_at = time.perf_counter()
        result = self._pipeline.process(current_raw, mode_state=ModeState(), state=self._pipeline_state)
        self._pipeline_state = result.state
        self.pipeline_compute_count += 1
        self._record_timing("effective_stack_compute", started_at)
        self._last_compute_signature = compute_signature
        self._current_raw_values = current_raw
        self._current_result = result
        self._render(result, current_raw, force=force_new)

    def toggle_freeze(self) -> None:
        if self.frozen:
            self.frozen = False
            self._frozen_result = None
            self._frozen_raw_values = None
            self.freeze_button.setText("Freeze")
            self.refresh_snapshot(force_new=True)
            return

        self.frozen = True
        self._frozen_result = self._current_result
        self._frozen_raw_values = dict(self._current_raw_values)
        self.freeze_button.setText("Resume")
        self.runtime_chip.setText(f"Frozen / {self._state.runtime.header_truth_label}")

    def select_stage(self, stage_name: str) -> None:
        if stage_name not in EXPECTED_STAGE_NAMES:
            return
        self.selected_stage = stage_name
        self._apply_selected_stage(force=True)

    def _apply_selected_stage(self, *, force: bool = False) -> None:
        for name, widget in self.stage_widgets.items():
            widget.set_selected(name == self.selected_stage)
        self._update_selected_stage_panel(force=force)

    def copy_snapshot(self) -> None:
        result = self._current_result
        if result is None:
            return
        lines = [
            "HelmForge Effective Response Stack Snapshot",
            f"Axis: {self.selected_axis}",
            f"Runtime truth: {self._runtime_status.truth.value}",
            f"Output writes verified: {str(self._runtime_status.live_output_writes_verified).lower()}",
        ]
        for stage in result.axis_results[self.selected_axis].stages:
            lines.append(f"{stage.stage_name}: IN {signed(stage.input_value)} OUT {signed(stage.output_value)} DELTA {signed(stage.delta)}")
        QApplication.clipboard().setText("\n".join(lines))

    def _render(self, result: WorkspaceSignalPipelineResult, raw_axis_values: dict[str, float], *, force: bool = False) -> None:
        axis_result = result.axis_results[self.selected_axis]
        render_signature = (
            self.selected_axis,
            tuple(_stage_signature(stage) for stage in axis_result.stages),
            tuple((getattr(rule, "rule_title", ""), rule.status.value) for rule in result.rule_evaluations),
        )
        if render_signature == self._last_render_signature and not force:
            self._update_graph(raw_axis_values, result=result, marker_only=True)
            return
        self._last_render_signature = render_signature
        self.full_render_count += 1
        self._stage_by_name = {stage.stage_name: stage for stage in axis_result.stages}
        for stage in axis_result.stages:
            before = self.stage_widgets[stage.stage_name].update_count
            self.stage_widgets[stage.stage_name].update_from_stage(stage)
            if self.stage_widgets[stage.stage_name].update_count != before:
                self.stage_card_update_count += 1
        self._apply_selected_stage(force=force)
        self._update_graph(raw_axis_values, result=result, force=force)
        self._update_mode_state()
        self._update_summary(result)
        self._update_total_change(result)
        self._update_rule_driver_values(result)
        if not self.frozen:
            set_chip_text_and_tone_if_changed(self.runtime_chip, self._state.runtime.header_truth_label, self._state.runtime.tone)

    def _physical_input_now(self) -> datetime | None:
        if self._physical_input_clock is not None:
            return self._physical_input_clock()
        if self._physical_input_snapshot is not None:
            return self._physical_input_snapshot.sampled_at
        return None

    def _refresh_physical_input_source_status(self) -> None:
        self._input_source_status = build_input_source_status(
            backend=self._physical_input_backend,
            selected_device_id=self._selected_physical_input_device_id,
            latest_snapshot=self._physical_input_snapshot,
            now=self._physical_input_now(),
            stale_after_seconds=self._physical_sample_stale_after_seconds,
        )

    def _update_graph(
        self,
        raw_axis_values: dict[str, float],
        *,
        result: WorkspaceSignalPipelineResult | None = None,
        force: bool = False,
        marker_only: bool = False,
    ) -> None:
        raw = float(raw_axis_values.get(self.selected_axis, 0.0))
        marker_result = result or self._current_result
        final = raw
        if marker_result is not None:
            final = float(marker_result.final_output_values.get(self.selected_axis, raw))
        marker = (raw, final)
        static_signature = (
            self.selected_axis,
            id(self._workspace),
            _settings_signature(self._workspace, self.selected_axis),
        )
        if marker_only or static_signature == self._last_static_graph_signature:
            marker_signature = (self.selected_axis, round(marker[0], 5), round(marker[1], 5))
            if (force or marker_signature != self._last_marker_signature) and self._scheduler.run("effective_stack_marker", force=force):
                self.graph.update_marker(marker)
                self._last_marker_signature = marker_signature
                self.marker_update_count += 1
                self._record_timing("effective_stack_marker", time.perf_counter())
            return
        if not force and not self._scheduler.run("effective_stack_static_graph"):
            return
        started_at = time.perf_counter()
        data = effective_response_stack_graph_data(
            self._workspace,
            self.selected_axis,
            raw_axis_values=raw_axis_values,
        )
        self.graph.plot_series_with_marker(
            (
                ("Linear", data.linear, "#7e91a8"),
                ("Effective", data.effective, "#53b7ff"),
            ),
            marker=data.live_marker,
        )
        self._last_static_graph_signature = static_signature
        self._last_marker_signature = (self.selected_axis, round(data.live_marker[0], 5), round(data.live_marker[1], 5))
        self.static_graph_rebuild_count += 1
        self.marker_update_count += 1
        self._record_timing("effective_stack_static_graph", started_at)
        self._record_timing("graph", started_at)

    def _update_mode_state(self) -> None:
        set_label_text_if_changed(
            self.mode_state,
            "Precision off | Combat off | Trigger off | Zoom off | Extra off | "
            f"Stack {self._workspace.modes.precision_combat_stack_mode.value}",
        )

    def _update_summary(self, result: WorkspaceSignalPipelineResult) -> None:
        axis_result = result.axis_results[self.selected_axis]
        largest = max(axis_result.stages, key=lambda stage: abs(stage.delta))
        self._mark_most_impactful_stage(largest.stage_name)
        active_rules = sum(1 for rule in result.rule_evaluations if rule.status is RuleStatus.ACTIVE)
        source_note = (
            "Stack preview uses a read-only physical input sample; diagnostic only."
            if self._input_source_status.is_fresh_physical_sample
            else f"Stack preview is using simulation/fallback input; diagnostic only. {self._input_source_status.fallback_behavior}"
        )
        set_label_text_if_changed(
            self.input_source_summary,
            f"Input source: {self._input_source_status.source_label}. "
            f"{source_note} Output verified: {str(self._runtime_status.live_output_writes_verified).lower()}. "
        )
        set_label_text_if_changed(
            self.summary,
            f"{self.selected_axis}: raw {signed(result.raw_axis_values[self.selected_axis])}, "
            f"final {signed(result.final_output_values[self.selected_axis])}. "
            f"{largest.stage_name} is the largest live modifier right now. "
            f"Active rules: {active_rules}. Output writes verified: "
            f"{str(self._runtime_status.live_output_writes_verified).lower()}.",
        )

    def _update_total_change(self, result: WorkspaceSignalPipelineResult) -> None:
        axis_result = result.axis_results[self.selected_axis]
        first = axis_result.stages[0]
        final = axis_result.stages[-1]
        delta = final.output_value - first.input_value
        largest = max(axis_result.stages, key=lambda stage: abs(stage.delta), default=None)
        values = {
            "stackTotalBefore": signed(first.input_value),
            "stackTotalAfter": signed(final.output_value),
            "stackTotalDelta": signed(delta),
            "stackMostImpactfulStage": largest.stage_name if largest is not None else "impact unavailable",
        }
        for object_name, text in values.items():
            label = self._total_change_labels.get(object_name)
            if label is not None:
                set_label_text_if_changed(label, text)
        impact = self._total_change_labels.get("stackMostImpactfulStage")
        if impact is not None:
            set_widget_property_if_changed(impact, "impactSource", "stage-delta" if largest is not None else "unavailable")

    def _mark_most_impactful_stage(self, stage_name: str) -> None:
        if self._last_most_impactful_stage == stage_name:
            return
        self._last_most_impactful_stage = stage_name
        for name, widget in self.stage_widgets.items():
            changed = set_widget_property_if_changed(widget, "mostImpactful", name == stage_name)
            repolish_if_changed(widget, changed)

    def _update_selected_stage_panel(self, *, force: bool = False) -> None:
        stage = self._stage_by_name.get(self.selected_stage)
        if stage is None:
            return
        signature = (self.selected_stage, _stage_signature(stage))
        if signature == self._last_selected_stage_signature and not force:
            return
        self._last_selected_stage_signature = signature
        self.selected_stage_update_count += 1
        status_text, tone = _stage_status(stage)
        set_chip_text_and_tone_if_changed(self.selected_stage_status, status_text, tone)
        set_label_text_if_changed(self.selected_stage_title, stage.stage_name)
        set_label_text_if_changed(
            self.selected_stage_body,
            f"{stage.explanation}\nInput {signed(stage.input_value)} | Output {signed(stage.output_value)} | Delta {signed(stage.delta)}",
        )
        set_label_text_if_changed(self.selected_stage_metadata, _metadata_text(stage.metadata))

    def _update_rule_driver_values(self, result: WorkspaceSignalPipelineResult) -> None:
        relevant = [
            rule for rule in result.rule_evaluations
            if rule.target_axis == self.selected_axis or rule.status is RuleStatus.ACTIVE
        ]
        if not relevant:
            set_label_text_if_changed(self.rule_drivers, "No active rule drivers for the selected axis right now.")
            return
        lines: list[str] = []
        for rule in relevant:
            measured = rule.metadata.get("measured_value")
            reference = rule.metadata.get("reference_value")
            threshold = rule.metadata.get("threshold")
            comparator = rule.metadata.get("comparator", "")
            lines.append(
                f"{rule.rule_title}: {rule.status.value}. Reference {signed(float(reference or 0.0))}; "
                f"measured {signed(float(measured or 0.0))}; condition {comparator} {float(threshold or 0.0):.2f}."
            )
        set_label_text_if_changed(self.rule_drivers, "\n".join(lines))


def _value_pair(layout: QGridLayout, column: int, label: str, object_name: str) -> QLabel:
    key = QLabel(label)
    key.setObjectName("tableMutedText")
    value = QLabel("+0.00")
    value.setObjectName(object_name)
    value.setProperty("metricValue", True)
    layout.addWidget(key, 0, column)
    layout.addWidget(value, 1, column)
    return value


def _bar(label: str) -> QProgressBar:
    bar = QProgressBar()
    bar.setObjectName(f"stack{label}Bar")
    bar.setRange(0, 100)
    bar.setTextVisible(False)
    bar.setValue(50)
    return bar


def _bar_value(value: float) -> int:
    return max(0, min(100, int(round((float(value) + 1.0) * 50.0))))


def _raw_signature(raw_axis_values: dict[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple((axis, round(float(raw_axis_values.get(axis, 0.0)), 5)) for axis in AXIS_NAMES)


def _stage_signature(stage: StageResult) -> tuple[object, ...]:
    return (
        stage.stage_name,
        round(float(stage.input_value), 5),
        round(float(stage.output_value), 5),
        round(float(stage.delta), 5),
        bool(stage.active),
        stage.explanation,
        _stage_status(stage),
        _stage_rule_text(stage),
    )


def _settings_signature(workspace: WorkspaceConfig, axis_name: str) -> tuple[object, ...]:
    axis_id = axis_by_name(axis_name).axis_id.value
    tuning = workspace.tuning.axes[axis_id]
    filtering = workspace.filtering.axes[axis_id]
    combat = workspace.combat.axes[axis_id]
    return (
        tuning,
        filtering,
        combat,
        workspace.modes.precision_combat_stack_mode.value,
        tuple(getattr(rule, "rule_id", str(index)) for index, rule in enumerate(workspace.rules.rules)),
    )


def _key(value: str) -> str:
    return value.replace(" ", "_").replace("/", "_")


def _stage_status(stage: StageResult) -> tuple[str, str]:
    if stage.stage_name == "Raw Input":
        return "Simulated", "success"
    if stage.stage_name == "Rule Injections" and stage.injected_rules:
        return "Applied", "success"
    if stage.stage_name == "Rule Injections":
        if stage.metadata.get("blocked_rules"):
            return "Blocked", "warning"
        if stage.metadata.get("disabled_rules"):
            return "Disabled", "danger"
        return "Inactive", "neutral"
    if stage.active:
        return "Active", "success"
    return "Inactive", "neutral"


def _stage_rule_text(stage: StageResult) -> str:
    if stage.stage_name == "Base Output Limits":
        injected = stage.metadata.get("injected_rules", ())
        if injected:
            return "\n".join(f"{title}: Set Yaw Output Scale to {stage.metadata['output_scale']:.2f}" for title in injected)
    if stage.stage_name != "Rule Injections":
        return ""
    evaluations = stage.metadata.get("evaluations", ())
    lines = []
    for item in evaluations:
        title = item.get("rule_title", "")
        status = item.get("status", "")
        effect = item.get("metadata", {}).get("effective_change", {})
        if status == "Active":
            lines.append(f"{title}: Set {effect.get('target_axis')} {effect.get('parameter')} to {effect.get('value')}")
        elif status in {"Disabled", "Blocked", "Inactive"}:
            lines.append(f"{title}: {status}")
    return "\n".join(lines) if lines else "No active rule injections for this axis."


def _metadata_text(metadata: dict[str, Any]) -> str:
    if not metadata:
        return "No additional metadata for this stage."
    parts = []
    for key, value in metadata.items():
        if key == "evaluations":
            continue
        parts.append(f"{key}: {value}")
    return "\n".join(parts) or "No additional metadata for this stage."
