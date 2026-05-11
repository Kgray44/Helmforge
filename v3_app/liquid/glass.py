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


def action_button(text: str, *, object_name: str, enabled: bool = True) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName(object_name)
    button.setProperty("uiRole", "liquidActionButton")
    button.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
    button.setEnabled(enabled)
    return button


def refresh_style(widget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
