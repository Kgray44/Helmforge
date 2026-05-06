from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from shared_core.models.axes import all_axis_definitions
from shared_core.models.runtime import RuntimePreflightStatus


OnDirty = Callable[[str], None]
OnStatus = Callable[[str], None]


def page_container(object_name: str) -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    page.setObjectName(object_name)
    layout = QVBoxLayout(page)
    layout.setContentsMargins(24, 22, 24, 28)
    layout.setSpacing(18)
    return page, layout


def page_intro(title: str, subtitle: str, helper: str | None = None) -> QWidget:
    block = QWidget()
    layout = QVBoxLayout(block)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    title_label = QLabel(title)
    title_label.setObjectName("pageTitle")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("pageSubtitle")
    subtitle_label.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    if helper:
        helper_label = QLabel(helper)
        helper_label.setObjectName("pageBody")
        helper_label.setWordWrap(True)
        layout.addWidget(helper_label)
    return block


def card(object_name: str) -> QFrame:
    frame = QFrame()
    frame.setObjectName(object_name)
    frame.setProperty("cardRole", "pageCard")
    frame.setFrameShape(QFrame.Shape.NoFrame)
    return frame


def card_layout(frame: QFrame) -> QVBoxLayout:
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 22)
    layout.setSpacing(14)
    return layout


def card_header(title: str, body: str | None = None) -> QWidget:
    header = QWidget()
    layout = QVBoxLayout(header)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    title_label = QLabel(title)
    title_label.setObjectName("cardTitle")
    layout.addWidget(title_label)
    if body:
        body_label = QLabel(body)
        body_label.setObjectName("cardBody")
        body_label.setWordWrap(True)
        layout.addWidget(body_label)
    return header


def axis_list_card(*, selected_axis: str = "Roll") -> QFrame:
    frame = card("mappedAxesCard")
    layout = card_layout(frame)
    layout.addWidget(card_header("Mapped Axes", "Choose one axis to tune."))
    list_frame = QFrame()
    list_frame.setObjectName("axisListFrame")
    list_layout = QVBoxLayout(list_frame)
    list_layout.setContentsMargins(10, 10, 10, 10)
    list_layout.setSpacing(6)
    for axis in all_axis_definitions():
        label = QLabel(axis.display_name)
        label.setObjectName("axisListItem")
        label.setProperty("active", axis.display_name == selected_axis)
        list_layout.addWidget(label)
    layout.addWidget(list_frame)
    return frame


def value_grid(rows: Iterable[tuple[str, str]]) -> QGridLayout:
    grid = QGridLayout()
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(10)
    for index, (label, value) in enumerate(rows):
        key = QLabel(label)
        key.setObjectName("tableMutedText")
        val = QLabel(value)
        val.setObjectName("routeSummaryValue")
        val.setWordWrap(True)
        grid.addWidget(key, index, 0)
        grid.addWidget(val, index, 1)
    return grid


def field_row(
    layout: QGridLayout,
    row: int,
    label: str,
    value: str,
    *,
    object_name: str,
    on_dirty: OnDirty | None = None,
    dirty_message: str = "Workspace edit staged.",
) -> QLineEdit:
    key = QLabel(label)
    key.setObjectName("formLabel")
    field = QLineEdit(value)
    field.setObjectName(object_name)
    if on_dirty is not None:
        field.editingFinished.connect(lambda: on_dirty(dirty_message))
    layout.addWidget(key, row, 0)
    layout.addWidget(field, row, 1)
    return field


def runtime_truth_rows(runtime_status: RuntimePreflightStatus) -> tuple[tuple[str, str], ...]:
    return (
        ("Runtime truth", runtime_status.truth.value),
        ("Input", runtime_status.input.status.value),
        ("Output", runtime_status.output.status.value),
        ("Output verification", f"Output writes verified: {str(runtime_status.live_output_writes_verified).lower()}"),
    )


def format_buttons(buttons: tuple[int, ...]) -> str:
    if not buttons:
        return "Not configured"
    return ", ".join(str(button) for button in buttons)


def signed(value: float) -> str:
    return f"{value:+.2f}"
