from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLayout, QVBoxLayout, QWidget


def vertical_layout(
    parent: QWidget | None = None,
    *,
    margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    spacing: int = 0,
) -> QVBoxLayout:
    layout = QVBoxLayout(parent)
    _configure_layout(layout, margins=margins, spacing=spacing)
    return layout


def horizontal_layout(
    parent: QWidget | None = None,
    *,
    margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    spacing: int = 0,
) -> QHBoxLayout:
    layout = QHBoxLayout(parent)
    _configure_layout(layout, margins=margins, spacing=spacing)
    return layout


def grid_layout(
    parent: QWidget | None = None,
    *,
    margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    spacing: int = 0,
) -> QGridLayout:
    layout = QGridLayout(parent)
    _configure_layout(layout, margins=margins, spacing=spacing)
    return layout


def _configure_layout(
    layout: QLayout,
    *,
    margins: tuple[int, int, int, int],
    spacing: int,
) -> None:
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
