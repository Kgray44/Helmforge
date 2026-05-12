from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QFrame, QLabel

from v3_app.liquid.layout import horizontal_layout, vertical_layout
from v3_app.liquid.status_components import StatusChip, StatusLight, status_tone_for_role


def _label(text: str, object_name: str, *, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    return label


def _set_flow_props(widget, *, component_role: str, state_role: str, liquid_role: str) -> None:
    widget.setProperty("componentRole", component_role)
    widget.setProperty("liquidRole", liquid_role)
    widget.setProperty("statusRole", state_role)
    widget.setProperty("toneRole", status_tone_for_role(state_role))
    widget.setProperty("liquidComponent", True)


def _output_intent_label(target_label: str) -> str:
    if target_label.strip().casefold().startswith("output intent:"):
        return target_label
    return f"Output Intent: {target_label}"


class RouteFlowRow(QFrame):
    def __init__(
        self,
        *,
        source_label: str,
        function_label: str,
        target_label: str,
        status_role: str = "info",
        helper_text: str = "",
        object_name: str = "liquidRouteFlowRow",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_flow_props(
            self,
            component_role="RouteFlowRow",
            state_role=status_role,
            liquid_role="route_flow_row",
        )
        layout = vertical_layout(self, margins=(14, 12, 14, 12), spacing=8)
        row = horizontal_layout(spacing=10)
        for text, name in (
            (source_label, "liquidRouteFlowSource"),
            ("->", "liquidRouteFlowArrow"),
            (function_label, "liquidRouteFlowFunction"),
            ("->", "liquidRouteFlowArrow"),
            (_output_intent_label(target_label), "liquidRouteFlowTarget"),
        ):
            row.addWidget(_label(text, name, wrap=True))
        row.addStretch(1)
        row.addWidget(StatusChip(status_role.replace("-", " ").title(), state_role=status_role))
        layout.addLayout(row)
        if helper_text:
            layout.addWidget(_label(helper_text, "liquidRouteFlowHelper", wrap=True))


class SignalPipelineStage(QFrame):
    def __init__(
        self,
        stage_name: str,
        stage_summary: str,
        *,
        selected_value: str = "",
        status_role: str = "info",
        warning_text: str = "",
        object_name: str = "liquidSignalPipelineStage",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_flow_props(
            self,
            component_role="SignalPipelineStage",
            state_role=status_role,
            liquid_role="signal_pipeline_stage",
        )
        layout = vertical_layout(self, margins=(14, 12, 14, 12), spacing=7)
        header = horizontal_layout(spacing=8)
        header.addWidget(StatusLight(state_role=status_role))
        header.addWidget(_label(stage_name, "liquidSignalPipelineStageName"), 1)
        self._value_chip: StatusChip | None = None
        if selected_value:
            self._value_chip = StatusChip(selected_value, state_role=status_role)
            header.addWidget(self._value_chip)
        layout.addLayout(header)
        self._summary_label = _label(stage_summary, "liquidSignalPipelineStageSummary", wrap=True)
        layout.addWidget(self._summary_label)
        self._warning_chip: StatusChip | None = None
        if warning_text:
            self._warning_chip = StatusChip(warning_text, state_role="warning")
            layout.addWidget(self._warning_chip)

    def update_stage(
        self,
        *,
        stage_summary: str,
        selected_value: str,
        status_role: str,
        warning_text: str = "",
    ) -> None:
        _set_flow_props(
            self,
            component_role="SignalPipelineStage",
            state_role=status_role,
            liquid_role="signal_pipeline_stage",
        )
        self._summary_label.setText(stage_summary)
        if self._value_chip is not None:
            self._value_chip.set_state(selected_value, status_role)
        if self._warning_chip is not None:
            self._warning_chip.setText(warning_text)


class ChecklistPanel(QFrame):
    def __init__(
        self,
        title: str,
        *,
        items: Iterable[tuple[str, str, str]] = (),
        object_name: str = "liquidChecklistPanel",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_flow_props(
            self,
            component_role="ChecklistPanel",
            state_role="info",
            liquid_role="checklist_panel",
        )
        layout = vertical_layout(self, margins=(14, 12, 14, 12), spacing=8)
        layout.addWidget(_label(title, "liquidChecklistTitle"))
        for label, state, reason in items:
            layout.addWidget(_ChecklistItem(label=label, state=state, reason=reason))


class _ChecklistItem(QFrame):
    def __init__(self, *, label: str, state: str, reason: str) -> None:
        super().__init__()
        _set_flow_props(self, component_role="ChecklistItem", state_role=state, liquid_role="checklist_item")
        layout = horizontal_layout(self, margins=(0, 0, 0, 0), spacing=8)
        layout.addWidget(StatusLight(state_role=state))
        layout.addWidget(_label(label, "liquidChecklistItemLabel"), 1)
        if reason:
            layout.addWidget(_label(reason, "liquidChecklistItemReason", wrap=True), 2)
