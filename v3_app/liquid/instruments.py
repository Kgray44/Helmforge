from __future__ import annotations

from collections.abc import Iterable, Sequence

from PySide6.QtWidgets import QFrame, QLabel, QProgressBar

from v3_app.liquid.layout import grid_layout, horizontal_layout, vertical_layout
from v3_app.liquid.status_components import MetricTile, StatusChip, StatusLight, status_tone_for_role


def _label(text: str, object_name: str, *, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    return label


def _set_instrument_props(widget, *, component_role: str, state_role: str, liquid_role: str) -> None:
    widget.setProperty("componentRole", component_role)
    widget.setProperty("liquidRole", liquid_role)
    widget.setProperty("statusRole", state_role)
    widget.setProperty("toneRole", status_tone_for_role(state_role))
    widget.setProperty("liquidComponent", True)


def _percent(value: float) -> int:
    return max(0, min(100, int(round(value * 100))))


class AxisBar(QFrame):
    def __init__(
        self,
        label: str,
        *,
        value: float = 0.0,
        state_role: str = "simulation",
        object_name: str = "liquidAxisBar",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_instrument_props(self, component_role="AxisBar", state_role=state_role, liquid_role="axis_bar")
        layout = vertical_layout(self, margins=(12, 10, 12, 10), spacing=6)
        top = horizontal_layout(spacing=8)
        top.addWidget(StatusLight(state_role=state_role))
        top.addWidget(_label(label, "liquidAxisBarLabel"), 1)
        top.addWidget(StatusChip("Read-only visualization", state_role=state_role))
        layout.addLayout(top)
        bar = QProgressBar()
        bar.setObjectName("liquidAxisBarValue")
        bar.setRange(0, 100)
        bar.setValue(_percent(value))
        bar.setTextVisible(True)
        layout.addWidget(bar)


class AxisBarPair(QFrame):
    def __init__(
        self,
        label: str,
        *,
        raw_value: float = 0.0,
        output_intent_value: float = 0.0,
        state_role: str = "simulation",
        object_name: str = "liquidAxisBarPair",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_instrument_props(self, component_role="AxisBarPair", state_role=state_role, liquid_role="axis_bar_pair")
        layout = vertical_layout(self, margins=(12, 10, 12, 10), spacing=8)
        layout.addWidget(_label(label, "liquidAxisBarPairLabel"))
        layout.addWidget(AxisBar("Raw input", value=raw_value, state_role=state_role))
        layout.addWidget(AxisBar("Output intent", value=output_intent_value, state_role=state_role))


class ButtonIlluminationGrid(QFrame):
    def __init__(
        self,
        *,
        buttons: Sequence[str],
        active_buttons: Sequence[str] = (),
        state_role: str = "simulation",
        object_name: str = "liquidButtonIlluminationGrid",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_instrument_props(
            self,
            component_role="ButtonIlluminationGrid",
            state_role=state_role,
            liquid_role="button_illumination_grid",
        )
        active = set(active_buttons)
        layout = grid_layout(self, margins=(12, 10, 12, 10), spacing=6)
        for index, button in enumerate(buttons):
            chip = StatusChip(button, state_role="info" if button in active else "disabled")
            chip.setObjectName(f"liquidButtonLight_{index}")
            layout.addWidget(chip, index // 4, index % 4)


class HatDirectionIndicator(QFrame):
    def __init__(
        self,
        *,
        selected_direction: str = "Neutral",
        state_role: str = "unavailable",
        object_name: str = "liquidHatDirectionIndicator",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_instrument_props(
            self,
            component_role="HatDirectionIndicator",
            state_role=state_role,
            liquid_role="hat_direction_indicator",
        )
        layout = vertical_layout(self, margins=(12, 10, 12, 10), spacing=8)
        layout.addWidget(_label("Hat direction", "liquidHatTitle"))
        row = horizontal_layout(spacing=6)
        for direction in ("Up", "Left", "Neutral", "Right", "Down"):
            role = state_role if direction == selected_direction else "disabled"
            row.addWidget(StatusChip(direction, state_role=role))
        layout.addLayout(row)


class ControlMarker(QFrame):
    def __init__(
        self,
        label: str,
        summary: str = "",
        *,
        state_role: str = "info",
        object_name: str = "liquidControlMarker",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_instrument_props(self, component_role="ControlMarker", state_role=state_role, liquid_role="control_marker")
        layout = vertical_layout(self, margins=(12, 10, 12, 10), spacing=6)
        layout.addWidget(StatusChip(label, state_role=state_role))
        if summary:
            layout.addWidget(_label(summary, "liquidControlMarkerSummary", wrap=True))


class MiniCurvePreview(QFrame):
    def __init__(
        self,
        title: str = "Curve preview",
        *,
        state_role: str = "simulation",
        object_name: str = "liquidMiniCurvePreview",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_instrument_props(
            self,
            component_role="MiniCurvePreview",
            state_role=state_role,
            liquid_role="mini_curve_preview",
        )
        layout = vertical_layout(self, margins=(12, 10, 12, 10), spacing=6)
        layout.addWidget(_label(title, "liquidMiniCurveTitle"))
        layout.addWidget(_label("Static preview placeholder. No live graph or animation in LCD-2.", "liquidMiniCurveBody", wrap=True))
        layout.addWidget(StatusChip("Simulation mode", state_role=state_role))


class CapabilityRail(QFrame):
    def __init__(
        self,
        *,
        capabilities: Iterable[tuple[str, str, str]],
        object_name: str = "liquidCapabilityRail",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_instrument_props(self, component_role="CapabilityRail", state_role="info", liquid_role="capability_rail")
        layout = horizontal_layout(self, margins=(0, 0, 0, 0), spacing=10)
        for label, state_role, caption in capabilities:
            layout.addWidget(MetricTile(label, state_role.replace("-", " ").title(), caption, state_role=state_role), 1)
