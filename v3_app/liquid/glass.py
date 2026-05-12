from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy


def glass_panel(object_name: str, *, role: str | None = None) -> QFrame:
    panel = QFrame()
    panel.setObjectName(object_name)
    panel.setFrameShape(QFrame.Shape.NoFrame)
    if role is not None:
        panel.setProperty("liquidRole", role)
    return panel


def status_chip(text: str, *, tone: str = "neutral", object_name: str | None = None) -> QLabel:
    chip = QLabel(text)
    chip.setProperty("uiRole", "liquidStatusChip")
    chip.setProperty("chipTone", tone)
    chip.setWordWrap(True)
    chip.setCursor(Qt.CursorShape.ArrowCursor)
    chip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    chip.setMinimumWidth(0)
    chip.setMaximumWidth(220)
    chip.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    if object_name is not None:
        chip.setObjectName(object_name)
    return chip


def configure_command_action(
    button: QPushButton,
    *,
    action_kind: str,
    disabled_reason: str = "",
    route_target: str | None = None,
) -> QPushButton:
    button.setProperty("liquidCommandAction", True)
    button.setProperty("actionKind", action_kind)
    if route_target is not None:
        button.setProperty("routeTarget", route_target)
    if disabled_reason:
        button.setProperty("disabledReason", disabled_reason)
    if not button.isEnabled() and disabled_reason:
        if not button.toolTip():
            button.setToolTip(disabled_reason)
        if not button.statusTip():
            button.setStatusTip(disabled_reason)
        if not button.accessibleDescription():
            button.setAccessibleDescription(disabled_reason)
    return button


def mark_action_feedback(button: QPushButton, message: str) -> None:
    button.setProperty("lastActionStatus", message)
    button.setStatusTip(message)
    if message:
        button.setAccessibleDescription(message)
    refresh_style(button)


def action_button(
    text: str,
    *,
    object_name: str,
    enabled: bool = True,
    action_kind: str = "unclassified",
    disabled_reason: str = "",
    route_target: str | None = None,
) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName(object_name)
    button.setProperty("uiRole", "liquidActionButton")
    button.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
    button.setEnabled(enabled)
    configure_command_action(
        button,
        action_kind=action_kind,
        disabled_reason=disabled_reason,
        route_target=route_target,
    )
    return button


def refresh_style(widget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
