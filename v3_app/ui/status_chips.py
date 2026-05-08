from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy


def status_chip(text: str, *, tone: str = "neutral", object_name: str | None = None) -> QLabel:
    chip = QLabel(text)
    chip.setProperty("uiRole", "statusChip")
    chip.setProperty("chipTone", tone)
    chip.setProperty("interactive", False)
    chip.setCursor(Qt.CursorShape.ArrowCursor)
    chip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    if object_name:
        chip.setObjectName(object_name)
    return chip


def action_button(text: str, *, object_name: str | None = None) -> QPushButton:
    button = QPushButton(text)
    button.setProperty("uiRole", "actionButton")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if object_name:
        button.setObjectName(object_name)
    return button
