from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QButtonGroup, QComboBox, QFrame, QLabel, QLineEdit, QPushButton, QWidget

from v3_app.liquid.layout import horizontal_layout, vertical_layout
from v3_app.liquid.status_components import StatusChip, status_tone_for_role


AXIS_SELECTOR_OPTIONS = ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")


def _label(text: str, object_name: str, *, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    return label


def _set_parameter_props(widget, *, component_role: str, state_role: str = "info", liquid_role: str) -> None:
    widget.setProperty("componentRole", component_role)
    widget.setProperty("liquidRole", liquid_role)
    widget.setProperty("statusRole", state_role)
    widget.setProperty("toneRole", status_tone_for_role(state_role))
    widget.setProperty("liquidComponent", True)


class ParameterLabelWithInfo(QFrame):
    def __init__(
        self,
        label: str,
        *,
        help_text: str = "",
        metadata: Mapping[str, object] | None = None,
        object_name: str = "liquidParameterLabelWithInfo",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_parameter_props(self, component_role="ParameterLabelWithInfo", liquid_role="parameter_label")
        metadata = metadata or {}
        description = str(metadata.get("description") or metadata.get("help") or "")
        unit = str(metadata.get("unit") or "")
        tooltip_parts = [part for part in (help_text, description, f"Unit: {unit}" if unit else "") if part]
        tooltip = "\n".join(tooltip_parts)
        if tooltip:
            self.setToolTip(tooltip)
        layout = horizontal_layout(self, margins=(0, 0, 0, 0), spacing=6)
        text_label = _label(label, "liquidParameterLabel")
        if tooltip:
            text_label.setToolTip(tooltip)
        layout.addWidget(text_label, 1)
        info = _label("i", "liquidParameterInfo")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setToolTip(tooltip or "Parameter metadata unavailable.")
        layout.addWidget(info)


class NumericParameterControl(QLineEdit):
    def __init__(
        self,
        *,
        value: float | int | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        decimals: int = 3,
        object_name: str = "liquidNumericParameterControl",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self._min_value = min_value
        self._max_value = max_value
        self._decimals = decimals
        self.setProperty("componentRole", "NumericParameterControl")
        self.setProperty("liquidRole", "numeric_parameter_control")
        self.setProperty("validationState", "valid")
        bottom = min_value if min_value is not None else -1_000_000.0
        top = max_value if max_value is not None else 1_000_000.0
        validator = QDoubleValidator(bottom, top, decimals, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.setValidator(validator)
        if value is not None:
            self.set_numeric_value(float(value))

    def set_numeric_value(self, value: float) -> None:
        if self._min_value is not None and value < self._min_value:
            raise ValueError(f"{value} is below minimum {self._min_value}")
        if self._max_value is not None and value > self._max_value:
            raise ValueError(f"{value} is above maximum {self._max_value}")
        self.setText(f"{value:.{self._decimals}f}".rstrip("0").rstrip("."))
        self.setProperty("validationState", "valid")

    def numeric_value(self) -> float | None:
        try:
            value = float(self.text())
        except ValueError:
            self.setProperty("validationState", "invalid")
            return None
        if self._min_value is not None and value < self._min_value:
            self.setProperty("validationState", "invalid")
            return None
        if self._max_value is not None and value > self._max_value:
            self.setProperty("validationState", "invalid")
            return None
        self.setProperty("validationState", "valid")
        return value


class DropdownParameterControl(QComboBox):
    def __init__(
        self,
        *,
        options: Sequence[str],
        selected: str | None = None,
        object_name: str = "liquidDropdownParameterControl",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setEditable(False)
        self.setProperty("componentRole", "DropdownParameterControl")
        self.setProperty("liquidRole", "dropdown_parameter_control")
        self._options = tuple(options)
        self.addItems(self._options)
        if selected is not None:
            self.set_selected_value(selected)

    def selected_value(self) -> str:
        return self.currentText()

    def set_selected_value(self, value: str) -> None:
        if value not in self._options:
            raise ValueError(f"Unsupported dropdown option: {value}")
        self.setCurrentIndex(self._options.index(value))


class AxisSelectorPills(QFrame):
    selectionChanged = Signal(str)

    def __init__(
        self,
        *,
        selected_axis: str = "Roll",
        options: Sequence[str] = AXIS_SELECTOR_OPTIONS,
        object_name: str = "liquidAxisSelectorPills",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_parameter_props(self, component_role="AxisSelectorPills", liquid_role="axis_selector_pills")
        self._options = tuple(options)
        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        layout = horizontal_layout(self, margins=(0, 0, 0, 0), spacing=7)
        for axis in self._options:
            button = QPushButton(axis)
            button.setObjectName(f"liquidAxisPill_{axis.replace(' ', '_').lower()}")
            button.setProperty("uiRole", "liquidAxisPill")
            button.setProperty("axis", axis)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, selected=axis: self.set_selected_axis(selected))
            self._group.addButton(button)
            self._buttons[axis] = button
            layout.addWidget(button)
        self.set_selected_axis(selected_axis)

    def option_labels(self) -> tuple[str, ...]:
        return self._options

    def selected_axis(self) -> str:
        return str(self.property("selectedAxis") or "")

    def set_selected_axis(self, axis: str) -> None:
        if axis not in self._options:
            raise ValueError(f"Unsupported axis: {axis}")
        self.setProperty("selectedAxis", axis)
        for label, button in self._buttons.items():
            active = label == axis
            button.setChecked(active)
            button.setProperty("active", active)
        self.selectionChanged.emit(axis)


class ParameterRow(QFrame):
    def __init__(
        self,
        *,
        label: str,
        control: QWidget,
        help_text: str = "",
        unit_text: str = "",
        status_note: str = "",
        changed: bool = False,
        object_name: str = "liquidParameterRow",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("changed", changed)
        _set_parameter_props(
            self,
            component_role="ParameterRow",
            state_role="unsaved" if changed else "info",
            liquid_role="parameter_row",
        )
        layout = horizontal_layout(self, margins=(12, 9, 12, 9), spacing=10)
        layout.addWidget(ParameterLabelWithInfo(label, help_text=help_text), 1)
        layout.addWidget(control, 1)
        if unit_text:
            layout.addWidget(_label(unit_text, "liquidParameterUnit"))
        if status_note:
            layout.addWidget(StatusChip(status_note, state_role="unsaved" if changed else "info"))


class GuidanceBlock(QFrame):
    def __init__(
        self,
        *,
        current_feel: str = "",
        affects: str = "",
        suggested_range: str = "",
        caution: str = "",
        selected_axis_note: str = "",
        object_name: str = "liquidGuidanceBlock",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_parameter_props(self, component_role="GuidanceBlock", liquid_role="guidance_block")
        layout = vertical_layout(self, margins=(14, 12, 14, 12), spacing=8)
        for title, body in (
            ("Current feel", current_feel),
            ("What this affects", affects),
            ("Suggested range", suggested_range),
            ("Caution", caution),
            ("Selected axis note", selected_axis_note),
        ):
            layout.addWidget(_GuidanceSection(title=title, body=body or "Not available in this placeholder."))


class _GuidanceSection(QFrame):
    def __init__(self, *, title: str, body: str) -> None:
        super().__init__()
        _set_parameter_props(self, component_role="GuidanceSection", liquid_role="guidance_section")
        layout = vertical_layout(self, margins=(0, 0, 0, 0), spacing=3)
        layout.addWidget(_label(title, "liquidGuidanceTitle"))
        layout.addWidget(_label(body, "liquidGuidanceBody", wrap=True))


class LiveSnapshotBlock(QFrame):
    def __init__(
        self,
        *,
        selected_control: str,
        source_truth_label: str,
        raw_value: str,
        output_intent_value: str,
        state_role: str = "simulation",
        object_name: str = "liquidLiveSnapshotBlock",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_parameter_props(
            self,
            component_role="LiveSnapshotBlock",
            state_role=state_role,
            liquid_role="live_snapshot_block",
        )
        layout = vertical_layout(self, margins=(14, 12, 14, 12), spacing=7)
        layout.addWidget(StatusChip(source_truth_label, state_role=state_role))
        for title, value in (
            ("Selected control", selected_control),
            ("Raw/current value", raw_value),
            ("Final/output intent", output_intent_value),
        ):
            row = horizontal_layout(spacing=8)
            row.addWidget(_label(title, "liquidLiveSnapshotLabel"), 1)
            row.addWidget(_label(value, "liquidLiveSnapshotValue"), 1)
            layout.addLayout(row)
