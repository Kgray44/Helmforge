from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy


def status_chip(text: str, *, tone: str = "neutral", object_name: str | None = None) -> QLabel:
    chip = QLabel(text)
    chip.setProperty("uiRole", "statusChip")
    chip.setProperty("chipTone", tone)
    chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    if object_name:
        chip.setObjectName(object_name)
    return chip


def action_button(text: str, *, object_name: str | None = None) -> QPushButton:
    button = QPushButton(text)
    button.setProperty("uiRole", "actionButton")
    if object_name:
        button.setObjectName(object_name)
    return button
