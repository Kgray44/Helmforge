from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from shared_core.models.axes import all_axis_definitions
from shared_core.models.runtime import RuntimePreflightStatus
from v3_app.services.parameter_metadata import (
    PARAMETER_HELP,
    ParameterMetadata,
    ParameterValueType,
    format_parameter_tooltip,
)
from v3_app.widgets.info_icon import ParameterInfoIcon


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
    frame.setProperty("cardSizing", "content")
    frame.setFrameShape(QFrame.Shape.NoFrame)
    return frame


def add_card_to_grid(
    layout: QGridLayout,
    widget: QWidget,
    row: int,
    column: int,
    row_span: int = 1,
    column_span: int = 1,
) -> None:
    widget.setProperty("cardSizing", "content")
    layout.addWidget(widget, row, column, row_span, column_span, Qt.AlignmentFlag.AlignTop)


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


def axis_list_card(*, selected_axis: str = "Roll", on_axis_selected: Callable[[str], None] | None = None) -> QFrame:
    frame = card("mappedAxesCard")
    layout = card_layout(frame)
    layout.addWidget(card_header("Mapped Axes", "Choose one axis to tune."))
    list_frame = QFrame()
    list_frame.setObjectName("axisListFrame")
    list_layout = QVBoxLayout(list_frame)
    list_layout.setContentsMargins(10, 10, 10, 10)
    list_layout.setSpacing(6)
    for axis in all_axis_definitions():
        button = QPushButton(axis.display_name)
        button.setObjectName("axisListItem")
        button.setProperty("axisName", axis.display_name)
        button.setProperty("active", axis.display_name == selected_axis)
        button.setCheckable(True)
        button.setChecked(axis.display_name == selected_axis)
        if on_axis_selected is not None:
            button.clicked.connect(lambda _checked=False, name=axis.display_name: on_axis_selected(name))
        list_layout.addWidget(button)
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
    metadata_id: str | None = None,
    on_dirty: OnDirty | None = None,
    dirty_message: str = "Workspace edit staged.",
) -> QLineEdit:
    metadata = PARAMETER_HELP.get(metadata_id) if metadata_id else None
    key = parameter_label(label, metadata)
    field = QLineEdit(value)
    field.setObjectName(object_name)
    if metadata is not None:
        field.setProperty("metadataId", metadata.parameter_id)
        field.setToolTip(format_parameter_tooltip(metadata))
        apply_numeric_validator(field, metadata)
    if on_dirty is not None:
        field.editingFinished.connect(lambda: on_dirty(dirty_message))
    layout.addWidget(key, row, 0)
    layout.addWidget(field, row, 1)
    return field


def dropdown_field_row(
    layout: QGridLayout,
    row: int,
    label: str,
    value: str,
    *,
    object_name: str,
    metadata_id: str,
    options: tuple[str, ...] | None = None,
    on_dirty: OnDirty | None = None,
    dirty_message: str = "Workspace edit staged.",
) -> QComboBox:
    metadata = PARAMETER_HELP.require(metadata_id)
    dropdown_options = options or metadata.dropdown_options
    key = parameter_label(label, metadata)
    field = QComboBox()
    field.setObjectName(object_name)
    field.setProperty("metadataId", metadata.parameter_id)
    field.setToolTip(format_parameter_tooltip(metadata))
    field.addItems(dropdown_options)
    if value in dropdown_options:
        field.setCurrentText(value)
    elif metadata.default_value in dropdown_options:
        field.setCurrentText(str(metadata.default_value))
    elif dropdown_options:
        field.setCurrentIndex(0)
    if on_dirty is not None:
        field.currentTextChanged.connect(lambda _value: on_dirty(dirty_message))
    layout.addWidget(key, row, 0)
    layout.addWidget(field, row, 1)
    return field


def parameter_label(label: str, metadata: ParameterMetadata | None = None) -> QWidget:
    if metadata is None:
        key = QLabel(label)
        key.setObjectName("formLabel")
        return key

    wrapper = QWidget()
    wrapper.setObjectName("parameterLabel")
    wrapper.setProperty("metadataId", metadata.parameter_id)
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    key = QLabel(label)
    key.setObjectName("formLabel")
    key.setToolTip(format_parameter_tooltip(metadata))
    layout.addWidget(key)
    layout.addWidget(ParameterInfoIcon(metadata))
    layout.addStretch(1)
    return wrapper


def apply_numeric_validator(field: QLineEdit, metadata: ParameterMetadata) -> None:
    if metadata.value_type not in {ParameterValueType.NUMBER, ParameterValueType.INTEGER}:
        return
    if metadata.min_value is None or metadata.max_value is None:
        return

    if metadata.value_type is ParameterValueType.INTEGER:
        validator = QIntValidator(int(metadata.min_value), int(metadata.max_value), field)
    else:
        validator = QDoubleValidator(float(metadata.min_value), float(metadata.max_value), 3, field)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
    field.setValidator(validator)
    field.setProperty("numericParameter", True)
    field.setProperty("minValue", metadata.min_value)
    field.setProperty("maxValue", metadata.max_value)


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
