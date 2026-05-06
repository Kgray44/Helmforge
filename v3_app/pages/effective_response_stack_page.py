from __future__ import annotations

from dataclasses import replace
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
from shared_core.models.axes import AXIS_DISPLAY_NAMES
from shared_core.models.runtime import AXIS_NAMES, RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.runtime_bridge import RuntimeBridge
from shared_core.rules.evaluator import RuleStatus
from v3_app.pages.graph_data import effective_response_stack_graph_data
from v3_app.pages.graph_widgets import GraphPreview
from v3_app.pages.page_helpers import card, card_header, card_layout, page_intro, signed, value_grid
from v3_app.services.app_state import AppState
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
        self.input_label.setText(signed(stage.input_value))
        self.output_label.setText(signed(stage.output_value))
        self.delta_label.setText(signed(stage.delta))
        self.input_bar.setValue(_bar_value(stage.input_value))
        self.output_bar.setValue(_bar_value(stage.output_value))
        self.explanation.setText(stage.explanation)
        status_text, tone = _stage_status(stage)
        self.status.setText(status_text)
        self.status.setProperty("chipTone", tone)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.rule_label.setText(_stage_rule_text(stage))

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)


class EffectiveResponseStackPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("effectiveResponseStackPage")
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self.selected_axis = state.selected_axis
        self.selected_stage = "Raw Input"
        self.frozen = False
        self._frozen_result: WorkspaceSignalPipelineResult | None = None
        self._frozen_raw_values: dict[str, float] | None = None
        self._current_raw_values: dict[str, float] = {axis: 0.0 for axis in AXIS_NAMES}
        self._current_result: WorkspaceSignalPipelineResult | None = None
        self.stage_widgets: dict[str, StageCard] = {}
        self._stage_by_name: dict[str, StageResult] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)

        root.addWidget(
            page_intro(
                "Effective Response Stack",
                "Inspect one selected axis at a time from raw HOTAS input through shaping, filtering, mode modifiers, rule injections, and final output.",
            )
        )
        root.addWidget(self._build_controls())

        main = QHBoxLayout()
        main.setSpacing(8)
        main.addWidget(self._build_signal_chain_card(), 1)
        main.addLayout(self._build_right_side(), 2)
        root.addLayout(main, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(1200)
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
        lower.addWidget(self._build_mode_state_card(), 0, 0)
        lower.addWidget(self._build_summary_card(), 0, 1)
        lower.addWidget(self._build_selected_stage_card(), 1, 0)
        lower.addWidget(self._build_rule_driver_card(), 1, 1)
        side.addLayout(lower, 2)
        return side

    def _build_graph_card(self) -> QFrame:
        frame = card("rawVsFinalCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Raw vs Final", "The live marker rides on the effective response line for the selected axis."))
        self.graph = GraphPreview(object_name="effectiveResponseStackGraph")
        layout.addWidget(self.graph)
        caption = QLabel("Raw input on X, effective output on Y. Center")
        caption.setObjectName("cardBody")
        layout.addWidget(caption)
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
        if self.frozen or not self.isVisible():
            return
        self.refresh_snapshot()

    def set_selected_axis(self, axis_name: str) -> None:
        if axis_name not in AXIS_DISPLAY_NAMES:
            return
        self.selected_axis = axis_name
        if self.axis_selector.currentText() != axis_name:
            self.axis_selector.setCurrentText(axis_name)
        self._state.selected_axis = axis_name
        self.refresh_snapshot(raw_axis_values=self._current_raw_values)

    def refresh_snapshot(self, *, force_new: bool = False, raw_axis_values: dict[str, float] | None = None) -> None:
        if self.frozen and self._frozen_result is not None:
            self._render(self._frozen_result, self._frozen_raw_values or self._current_raw_values)
            return

        if raw_axis_values is not None:
            current_raw = {axis: float(raw_axis_values.get(axis, 0.0)) for axis in AXIS_NAMES}
        else:
            deterministic = not force_new
            snapshot = RuntimeBridge(
                preflight_status=self._runtime_status,
                deterministic_simulation=deterministic,
            ).snapshot()
            current_raw = {axis: float(snapshot.raw_axis_values[axis]) for axis in AXIS_NAMES}

        pipeline = WorkspaceSignalPipeline(self._workspace)
        result = pipeline.process(current_raw, mode_state=ModeState(), state=pipeline.initial_state())
        self._current_raw_values = current_raw
        self._current_result = result
        self._render(result, current_raw)

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
        for name, widget in self.stage_widgets.items():
            widget.set_selected(name == stage_name)
        self._update_selected_stage_panel()

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

    def _render(self, result: WorkspaceSignalPipelineResult, raw_axis_values: dict[str, float]) -> None:
        axis_result = result.axis_results[self.selected_axis]
        self._stage_by_name = {stage.stage_name: stage for stage in axis_result.stages}
        for stage in axis_result.stages:
            self.stage_widgets[stage.stage_name].update_from_stage(stage)
        self.select_stage(self.selected_stage)
        self._update_graph(raw_axis_values)
        self._update_mode_state()
        self._update_summary(result)
        self._update_rule_driver_values(result)
        if not self.frozen:
            self.runtime_chip.setText(self._state.runtime.header_truth_label)

    def _update_graph(self, raw_axis_values: dict[str, float]) -> None:
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

    def _update_mode_state(self) -> None:
        self.mode_state.setText(
            "Precision off | Combat off | Trigger off | Zoom off | Extra off | "
            f"Stack {self._workspace.modes.precision_combat_stack_mode.value}"
        )

    def _update_summary(self, result: WorkspaceSignalPipelineResult) -> None:
        axis_result = result.axis_results[self.selected_axis]
        largest = max(axis_result.stages, key=lambda stage: abs(stage.delta))
        active_rules = sum(1 for rule in result.rule_evaluations if rule.status is RuleStatus.ACTIVE)
        self.summary.setText(
            f"{self.selected_axis}: raw {signed(result.raw_axis_values[self.selected_axis])}, "
            f"final {signed(result.final_output_values[self.selected_axis])}. "
            f"{largest.stage_name} is the largest live modifier right now. "
            f"Active rules: {active_rules}. Output writes verified: "
            f"{str(self._runtime_status.live_output_writes_verified).lower()}."
        )

    def _update_selected_stage_panel(self) -> None:
        stage = self._stage_by_name.get(self.selected_stage)
        if stage is None:
            return
        status_text, tone = _stage_status(stage)
        self.selected_stage_status.setText(status_text)
        self.selected_stage_status.setProperty("chipTone", tone)
        self.selected_stage_status.style().unpolish(self.selected_stage_status)
        self.selected_stage_status.style().polish(self.selected_stage_status)
        self.selected_stage_title.setText(stage.stage_name)
        self.selected_stage_body.setText(
            f"{stage.explanation}\nInput {signed(stage.input_value)} | Output {signed(stage.output_value)} | Delta {signed(stage.delta)}"
        )
        self.selected_stage_metadata.setText(_metadata_text(stage.metadata))

    def _update_rule_driver_values(self, result: WorkspaceSignalPipelineResult) -> None:
        relevant = [
            rule for rule in result.rule_evaluations
            if rule.target_axis == self.selected_axis or rule.status is RuleStatus.ACTIVE
        ]
        if not relevant:
            self.rule_drivers.setText("No active rule drivers for the selected axis right now.")
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
        self.rule_drivers.setText("\n".join(lines))


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
