from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy

from v3_app.liquid.layout import horizontal_layout, vertical_layout
from v3_app.liquid.motion import (
    HoverRole,
    MicrointeractionRole,
    MotionSettings,
    apply_status_motion,
    refresh_motion_style,
)


_SUCCESS_ROLES = {"ready", "verified", "saved", "safe", "done"}
_WARNING_ROLES = {"waiting", "blocked", "attention", "unsaved", "warning", "missing-proof"}
_DANGER_ROLES = {"error", "unsafe", "failed"}
_INFO_ROLES = {"info", "simulation", "live-neutral", "neutral"}
_DISABLED_ROLES = {"disabled", "unavailable"}


def status_tone_for_role(state_role: str) -> str:
    role = _normalize_role(state_role)
    if role in _SUCCESS_ROLES:
        return "success"
    if role in _WARNING_ROLES:
        return "warning"
    if role in _DANGER_ROLES:
        return "danger"
    if role in _DISABLED_ROLES:
        return "disabled"
    return "info"


def _normalize_role(state_role: str) -> str:
    return state_role.strip().casefold()


def _set_status_props(
    widget,
    *,
    component_role: str,
    state_role: str,
    liquid_role: str | None = None,
    motion_settings: MotionSettings | None = None,
    focusable: bool = False,
) -> None:
    normalized = _normalize_role(state_role)
    widget.setProperty("componentRole", component_role)
    widget.setProperty("statusRole", normalized)
    widget.setProperty("toneRole", status_tone_for_role(normalized))
    widget.setProperty("liquidComponent", True)
    if liquid_role is not None:
        widget.setProperty("liquidRole", liquid_role)
    role = MicrointeractionRole.STATUS_CARD
    hover = HoverRole.STATUS_CARD if focusable else HoverRole.NONE
    if component_role == "StatusChip":
        role = MicrointeractionRole.STATUS_CHIP
        hover = HoverRole.CHIP
    elif component_role == "StatusLight":
        role = MicrointeractionRole.STATUS_LIGHT
    apply_status_motion(
        widget,
        state_role=normalized,
        component_role=role,
        motion_settings=motion_settings,
        focusable=focusable,
        hover_role=hover,
    )


def _label(text: str, object_name: str, *, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    return label


class StatusChip(QLabel):
    def __init__(
        self,
        text: str,
        *,
        state_role: str = "info",
        object_name: str = "liquidComponentStatusChip",
        motion_settings: MotionSettings | None = None,
    ) -> None:
        super().__init__(text)
        self.setObjectName(object_name)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setProperty("uiRole", "liquidStatusChip")
        self.setMinimumWidth(0)
        self.setMaximumWidth(240)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        _set_status_props(self, component_role="StatusChip", state_role=state_role, motion_settings=motion_settings)

    def set_state(self, text: str, state_role: str) -> None:
        self.setText(text)
        _set_status_props(self, component_role="StatusChip", state_role=state_role)
        refresh_motion_style(self)


class StatusLight(QFrame):
    def __init__(
        self,
        *,
        state_role: str = "info",
        object_name: str = "liquidStatusLight",
        motion_settings: MotionSettings | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setFixedSize(10, 10)
        self.setProperty("indicatorShape", "status-dot")
        self.setProperty("interactive", False)
        _set_status_props(
            self,
            component_role="StatusLight",
            state_role=state_role,
            liquid_role="status_light",
            motion_settings=motion_settings,
        )


class TruthBadge(QFrame):
    def __init__(
        self,
        text: str,
        *,
        state_role: str = "info",
        helper_text: str = "",
        object_name: str = "liquidTruthBadge",
        motion_settings: MotionSettings | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_status_props(
            self,
            component_role="TruthBadge",
            state_role=state_role,
            liquid_role="truth_badge",
            motion_settings=motion_settings,
            focusable=True,
        )
        layout = horizontal_layout(self, margins=(12, 9, 12, 9), spacing=8)
        layout.addWidget(StatusLight(state_role=state_role, motion_settings=motion_settings))
        label = _label(text, "liquidTruthBadgeText", wrap=True)
        layout.addWidget(label, 1)
        if helper_text:
            layout.addWidget(_label(helper_text, "liquidTruthBadgeHelper", wrap=True), 1)


class ReadinessGate(QFrame):
    def __init__(
        self,
        title: str,
        *,
        state_text: str,
        state_role: str = "waiting",
        detail: str = "",
        object_name: str = "liquidReadinessGate",
        motion_settings: MotionSettings | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_status_props(
            self,
            component_role="ReadinessGate",
            state_role=state_role,
            liquid_role="readiness_gate",
            motion_settings=motion_settings,
            focusable=True,
        )
        layout = vertical_layout(self, margins=(14, 12, 14, 12), spacing=7)
        top = horizontal_layout(spacing=8)
        top.addWidget(StatusLight(state_role=state_role, motion_settings=motion_settings))
        top.addWidget(_label(title, "liquidReadinessGateTitle"), 1)
        top.addWidget(StatusChip(state_text, state_role=state_role))
        layout.addLayout(top)
        if detail:
            layout.addWidget(_label(detail, "liquidReadinessGateDetail", wrap=True))


class MetricTile(QFrame):
    def __init__(
        self,
        label: str,
        value: str,
        caption: str = "",
        *,
        state_role: str = "info",
        object_name: str = "liquidMetricTile",
        motion_settings: MotionSettings | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_status_props(
            self,
            component_role="MetricTile",
            state_role=state_role,
            liquid_role="metric_tile",
            motion_settings=motion_settings,
        )
        layout = vertical_layout(self, margins=(14, 12, 14, 12), spacing=5)
        layout.addWidget(_label(label.upper(), "liquidMetricTileLabel"))
        layout.addWidget(_label(value, "liquidMetricTileValue"))
        if caption:
            layout.addWidget(_label(caption, "liquidMetricTileCaption", wrap=True))


class DraftStateIndicator(QFrame):
    def __init__(
        self,
        text: str = "Draft change staged",
        *,
        state_role: str = "unsaved",
        object_name: str = "liquidDraftStateIndicator",
        motion_settings: MotionSettings | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_status_props(
            self,
            component_role="DraftStateIndicator",
            state_role=state_role,
            liquid_role="draft_state_indicator",
            motion_settings=motion_settings,
            focusable=True,
        )
        self.setProperty("draftEmphasis", state_role.strip().casefold() == "unsaved")
        layout = horizontal_layout(self, margins=(12, 8, 12, 8), spacing=8)
        layout.addWidget(StatusLight(state_role=state_role, motion_settings=motion_settings))
        layout.addWidget(_label(text, "liquidDraftStateText", wrap=True), 1)


class TelemetryFreshnessRail(QFrame):
    def __init__(
        self,
        freshness_text: str,
        *,
        state_role: str = "waiting",
        source_label: str = "",
        object_name: str = "liquidTelemetryFreshnessRail",
        motion_settings: MotionSettings | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_status_props(
            self,
            component_role="TelemetryFreshnessRail",
            state_role=state_role,
            liquid_role="telemetry_freshness_rail",
            motion_settings=motion_settings,
            focusable=True,
        )
        layout = horizontal_layout(self, margins=(14, 10, 14, 10), spacing=8)
        layout.addWidget(StatusLight(state_role=state_role, motion_settings=motion_settings))
        layout.addWidget(_label(freshness_text, "liquidTelemetryFreshnessText", wrap=True), 1)
        if source_label:
            layout.addWidget(StatusChip(source_label, state_role="simulation"))
