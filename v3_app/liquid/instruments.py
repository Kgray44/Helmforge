from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QSizePolicy

from v3_app.liquid.layout import grid_layout, horizontal_layout, vertical_layout
from v3_app.liquid.motion import EasedValue, MotionSettings, current_motion_settings
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
        motion_settings: MotionSettings | None = None,
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
        self._bar = bar
        self._motion_settings = motion_settings or current_motion_settings()
        initial_percent = _percent(value)
        self._eased_percent = EasedValue(
            initial_percent,
            minimum=0.0,
            maximum=100.0,
            motion_settings=self._motion_settings,
        )
        self._set_motion_props(target=initial_percent, display=initial_percent, stale=False)

    def update_value(self, value: float, *, stale: bool = False, snap: bool = False) -> None:
        target = _percent(value)
        self._eased_percent.set_target(target, stale=stale, snap=snap)
        if not stale and self._motion_settings.live_easing_enabled() and not snap:
            self._eased_percent.advance()
        self._apply_display(stale=stale)

    def advance_motion_frame(self, *, stale: bool = False) -> bool:
        before = self._eased_percent.display_value
        self._eased_percent.advance(stale=stale)
        self._apply_display(stale=stale)
        return before != self._eased_percent.display_value

    def display_percent(self) -> int:
        return int(round(self._eased_percent.display_value))

    def target_percent(self) -> int:
        return int(round(self._eased_percent.target_value))

    def _apply_display(self, *, stale: bool) -> None:
        display = self.display_percent()
        self._bar.setValue(display)
        self._set_motion_props(target=self.target_percent(), display=display, stale=stale or self._eased_percent.stale)

    def _set_motion_props(self, *, target: int, display: int, stale: bool) -> None:
        self.setProperty("axisMeterMotionEnabled", self._motion_settings.live_easing_enabled())
        self.setProperty("targetPercent", int(target))
        self.setProperty("displayPercent", int(display))
        self.setProperty("motionState", "stale" if stale else self._eased_percent.motion_state)
        self.setProperty("staleMotionFrozen", bool(stale))


class AxisBarPair(QFrame):
    def __init__(
        self,
        label: str,
        *,
        raw_value: float = 0.0,
        output_intent_value: float = 0.0,
        state_role: str = "simulation",
        motion_settings: MotionSettings | None = None,
        object_name: str = "liquidAxisBarPair",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_instrument_props(self, component_role="AxisBarPair", state_role=state_role, liquid_role="axis_bar_pair")
        layout = vertical_layout(self, margins=(12, 10, 12, 10), spacing=8)
        layout.addWidget(_label(label, "liquidAxisBarPairLabel"))
        self._motion_settings = motion_settings or current_motion_settings()
        self._raw_bar = AxisBar("Raw input", value=raw_value, state_role=state_role, motion_settings=self._motion_settings)
        self._output_bar = AxisBar("Output intent", value=output_intent_value, state_role=state_role, motion_settings=self._motion_settings)
        layout.addWidget(self._raw_bar)
        layout.addWidget(self._output_bar)
        self.setProperty("axisMeterMotionEnabled", self._motion_settings.live_easing_enabled())
        self._set_pair_props()

    def update_values(self, *, raw_value: float, output_intent_value: float, stale: bool = False, snap: bool = False) -> None:
        self._raw_bar.update_value(raw_value, stale=stale, snap=snap)
        self._output_bar.update_value(output_intent_value, stale=stale, snap=snap)
        self._set_pair_props(stale=stale)

    def advance_motion_frame(self, *, stale: bool = False) -> bool:
        changed = self._raw_bar.advance_motion_frame(stale=stale)
        changed = self._output_bar.advance_motion_frame(stale=stale) or changed
        self._set_pair_props(stale=stale)
        return changed

    def _set_pair_props(self, *, stale: bool = False) -> None:
        self.setProperty("targetPercents", (self._raw_bar.target_percent(), self._output_bar.target_percent()))
        self.setProperty("displayPercents", (self._raw_bar.display_percent(), self._output_bar.display_percent()))
        self.setProperty("axisMeterMotionEnabled", self._motion_settings.live_easing_enabled())
        self.setProperty("motionState", "stale" if stale else "live")
        self.setProperty("staleMotionFrozen", bool(stale))


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
        self._buttons = tuple(buttons)
        self._active = tuple(button for button in buttons if button in active)
        self.setProperty("activeButtons", self._active)
        self.setProperty("buttonMotionEnabled", current_motion_settings().live_easing_enabled())
        self.setProperty("buttonMotionPreservesTruth", True)
        self.setProperty("buttonReleaseFadeVisualOnly", True)
        layout = grid_layout(self, margins=(12, 10, 12, 10), spacing=6)
        for index, button in enumerate(buttons):
            chip = StatusChip(button, state_role="info" if button in active else "disabled")
            chip.setObjectName(f"liquidButtonLight_{index}")
            chip.setProperty("buttonActive", button in active)
            chip.setProperty("buttonTruthState", "pressed" if button in active else "released")
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
        self.setProperty("selectedDirection", selected_direction)
        self.setProperty("hatMotionEnabled", current_motion_settings().live_easing_enabled())
        self.setProperty("hatMotionPreservesTruth", True)
        self.setProperty("intermediateDirectionsInvented", False)
        layout.addWidget(_label("Hat direction", "liquidHatTitle"))
        row = horizontal_layout(spacing=6)
        for direction in ("Up", "Left", "Neutral", "Right", "Down"):
            role = state_role if direction == selected_direction else "disabled"
            chip = StatusChip(direction, state_role=role)
            chip.setProperty("hatDirectionActive", direction == selected_direction)
            row.addWidget(chip)
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


class ResponseCurveGraph(QFrame):
    def __init__(
        self,
        *,
        title: str,
        graph_kind: str,
        lines: Sequence[tuple[str, Sequence[tuple[float, float]], str]],
        markers: Sequence[tuple[str, tuple[float, float], str]] = (),
        selected_axis: str,
        x_range: tuple[float, float] = (-1.0, 1.0),
        y_range: tuple[float, float] = (-1.0, 1.0),
        state_role: str = "simulation",
        object_name: str = "liquidResponseCurveGraph",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setMinimumHeight(420)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._title = title
        self._lines = tuple((label, tuple(points), role) for label, points, role in lines)
        self._markers = tuple((label, point, role) for label, point, role in markers)
        self._display_markers = self._markers
        self._motion_settings = current_motion_settings()
        self._marker_easing: dict[str, tuple[EasedValue, EasedValue]] = {}
        self._x_range = x_range
        self._y_range = y_range
        _set_instrument_props(self, component_role="ResponseCurveGraph", state_role=state_role, liquid_role="response_curve_graph")
        self.setProperty("graphKind", graph_kind)
        self.setProperty("prominentGraph", True)
        self.setProperty("selectedAxis", selected_axis)
        self.setProperty("lineLabels", _line_label_aliases(tuple(label for label, _points, _role in self._lines)))
        self.setProperty("markerLabels", tuple(label for label, _point, _role in self._markers))
        self.setProperty("markerPoints", tuple(point for _label, point, _role in self._markers))
        self.setProperty("currentValueDots", bool(self._markers))
        self.setProperty("primaryGraph", True)
        if graph_kind == "step_response":
            self.setProperty("stepPattern", "positive_hold_negative_hold_return")
            self.setProperty("stepResponseDetail", "high_resolution_step_response")
        self.setProperty("xMin", x_range[0])
        self.setProperty("xMax", x_range[1])
        self.setProperty("yMin", y_range[0])
        self.setProperty("yMax", y_range[1])
        self.setProperty("markerMotionEnabled", self._motion_settings.live_easing_enabled())
        self.setProperty("markerMotionState", "live" if self._markers else "none")
        self._set_response_marker_targets(self._markers, snap=True)

    def update_model(
        self,
        *,
        title: str,
        graph_kind: str,
        lines: Sequence[tuple[str, Sequence[tuple[float, float]], str]],
        markers: Sequence[tuple[str, tuple[float, float], str]] = (),
        selected_axis: str,
        x_range: tuple[float, float] = (-1.0, 1.0),
        y_range: tuple[float, float] = (-1.0, 1.0),
        state_role: str = "simulation",
    ) -> None:
        self._title = title
        self._lines = tuple((label, tuple(points), role) for label, points, role in lines)
        self._markers = tuple((label, point, role) for label, point, role in markers)
        self._x_range = x_range
        self._y_range = y_range
        _set_instrument_props(self, component_role="ResponseCurveGraph", state_role=state_role, liquid_role="response_curve_graph")
        self.setProperty("graphKind", graph_kind)
        self.setProperty("selectedAxis", selected_axis)
        self.setProperty("lineLabels", _line_label_aliases(tuple(label for label, _points, _role in self._lines)))
        self.setProperty("markerLabels", tuple(label for label, _point, _role in self._markers))
        self.setProperty("markerPoints", tuple(point for _label, point, _role in self._markers))
        self.setProperty("currentValueDots", bool(self._markers))
        if graph_kind == "step_response":
            self.setProperty("stepPattern", "positive_hold_negative_hold_return")
            self.setProperty("stepResponseDetail", "high_resolution_step_response")
        self.setProperty("xMin", x_range[0])
        self.setProperty("xMax", x_range[1])
        self.setProperty("yMin", y_range[0])
        self.setProperty("yMax", y_range[1])
        self._set_response_marker_targets(self._markers)
        self.advance_marker_motion()
        self.update()

    def advance_marker_motion(self, *, stale: bool = False) -> bool:
        changed = False
        display: list[tuple[str, tuple[float, float], str]] = []
        for label, _point, role in self._markers:
            if label not in self._marker_easing:
                continue
            x_eased, y_eased = self._marker_easing[label]
            before = (x_eased.display_value, y_eased.display_value)
            x_eased.advance(stale=stale)
            y_eased.advance(stale=stale)
            after = (x_eased.display_value, y_eased.display_value)
            changed = changed or before != after
            display.append((label, after, role))
        self._display_markers = tuple(display)
        self.setProperty("markerDisplayPoints", tuple(point for _label, point, _role in self._display_markers))
        self.setProperty("markerMotionState", "stale" if stale else ("settling" if changed else "live"))
        self.setProperty("staleMotionFrozen", bool(stale))
        if changed:
            self.update()
        return changed

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(14, 14, -14, -14)
        painter.fillRect(rect, QColor(5, 15, 25, 120))
        plot = rect.adjusted(42, 28, -18, -34)
        painter.setPen(QPen(QColor(72, 112, 140, 130), 1))
        painter.drawRect(plot)
        painter.drawLine(QPointF(plot.left(), self._map_y(0.0, plot)), QPointF(plot.right(), self._map_y(0.0, plot)))
        painter.drawLine(QPointF(self._map_x(0.0, plot), plot.top()), QPointF(self._map_x(0.0, plot), plot.bottom()))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.setPen(QColor(247, 251, 255, 220))
        painter.drawText(rect.adjusted(8, 4, -8, -4), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, self._title)
        for index, (label, points, role) in enumerate(self._lines):
            color = _role_color(role, index)
            painter.setPen(QPen(color, 2.3 if index else 1.5, Qt.PenStyle.SolidLine if index != 0 else Qt.PenStyle.DashLine))
            path = QPainterPath()
            for point_index, (x, y) in enumerate(points):
                mapped = QPointF(self._map_x(x, plot), self._map_y(y, plot))
                if point_index == 0:
                    path.moveTo(mapped)
                else:
                    path.lineTo(mapped)
            painter.drawPath(path)
            painter.setPen(color)
            painter.drawText(
                QRectF(plot.left() + 8 + index * 170, plot.bottom() + 8, 160, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label,
            )
        for label, (x, y), role in self._display_markers:
            color = _role_color(role, 0)
            point = QPointF(self._map_x(x, plot), self._map_y(y, plot))
            painter.setPen(QPen(color, 2.2))
            painter.setBrush(color)
            painter.drawEllipse(point, 5.5, 5.5)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawText(
                QRectF(point.x() + 7, point.y() - 10, 130, 20),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

    def _map_x(self, value: float, rect: QRectF) -> float:
        low, high = self._x_range
        ratio = (value - low) / max(0.001, high - low)
        return rect.left() + rect.width() * max(0.0, min(1.0, ratio))

    def _map_y(self, value: float, rect: QRectF) -> float:
        low, high = self._y_range
        ratio = (value - low) / max(0.001, high - low)
        return rect.bottom() - rect.height() * max(0.0, min(1.0, ratio))

    def _set_response_marker_targets(
        self,
        markers: Sequence[tuple[str, tuple[float, float], str]],
        *,
        snap: bool = False,
    ) -> None:
        active_labels = {label for label, _point, _role in markers}
        self._marker_easing = {
            label: easing
            for label, easing in self._marker_easing.items()
            if label in active_labels
        }
        for label, (x, y), _role in markers:
            if label not in self._marker_easing:
                self._marker_easing[label] = (
                    EasedValue(x, minimum=self._x_range[0], maximum=self._x_range[1], motion_settings=self._motion_settings),
                    EasedValue(y, minimum=self._y_range[0], maximum=self._y_range[1], motion_settings=self._motion_settings),
                )
            x_eased, y_eased = self._marker_easing[label]
            x_eased.set_target(x, snap=snap or not self._motion_settings.live_easing_enabled())
            y_eased.set_target(y, snap=snap or not self._motion_settings.live_easing_enabled())
        self.setProperty("markerMotionEnabled", self._motion_settings.live_easing_enabled())
        self.setProperty("markerTargetPoints", tuple(point for _label, point, _role in markers))


class LiveAxisTimeSeriesGraph(QFrame):
    def __init__(
        self,
        *,
        axis_history: Mapping[str, Sequence[tuple[float | None, float | None]]],
        overlay_final_values: bool = False,
        capacity: int = 120,
        state_role: str = "simulation",
        object_name: str = "liquidAnalysisLiveTimeSeriesGraph",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setMinimumHeight(560)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._axis_history = {axis: tuple(samples)[-capacity:] for axis, samples in axis_history.items()}
        self._overlay_final_values = overlay_final_values
        self._capacity = capacity
        self._motion_settings = current_motion_settings()
        self._marker_easing: dict[str, tuple[EasedValue, EasedValue]] = {}
        _set_instrument_props(self, component_role="LiveAxisTimeSeriesGraph", state_role=state_role, liquid_role="live_axis_time_series")
        self.setProperty("timeSeriesDirection", "right_to_left")
        self.setProperty("boundedHistoryCapacity", capacity)
        self.setProperty("overlayFinalValues", overlay_final_values)
        self.setProperty("primaryGraph", True)
        self.setProperty("rawFinalOverlaySupported", True)
        self.setProperty("laneOrientation", "stacked_vertical")
        self.setProperty("axisLaneCount", len(self._axis_history))
        self.setProperty("historyLength", max((len(samples) for samples in self._axis_history.values()), default=0))
        self.setProperty("axisLabels", tuple(self._axis_history.keys()))
        self.setProperty("markerMotionEnabled", self._motion_settings.live_easing_enabled())
        self.setProperty("markerMotionState", "live" if self._motion_settings.live_easing_enabled() else "snapped")
        self.setProperty("staleMotionFrozen", False)
        self._refresh_marker_targets(snap=True)

    def update_history(
        self,
        axis_history: Mapping[str, Sequence[tuple[float | None, float | None]]],
        *,
        overlay_final_values: bool,
        repaint: bool = True,
    ) -> None:
        self._axis_history = {axis: tuple(samples)[-self._capacity:] for axis, samples in axis_history.items()}
        self._overlay_final_values = overlay_final_values
        self.setProperty("overlayFinalValues", overlay_final_values)
        self.setProperty("laneOrientation", "stacked_vertical")
        self.setProperty("axisLaneCount", len(self._axis_history))
        self.setProperty("historyLength", max((len(samples) for samples in self._axis_history.values()), default=0))
        self.setProperty("axisLabels", tuple(self._axis_history.keys()))
        self._refresh_marker_targets()
        if repaint:
            self.update()

    def advance_marker_motion(self, *, stale: bool = False) -> bool:
        changed = False
        for raw_eased, final_eased in self._marker_easing.values():
            before = (raw_eased.display_value, final_eased.display_value)
            raw_eased.advance(stale=stale)
            final_eased.advance(stale=stale)
            changed = changed or before != (raw_eased.display_value, final_eased.display_value)
        self.setProperty("markerMotionEnabled", self._motion_settings.live_easing_enabled())
        self.setProperty("markerMotionState", "stale" if stale else ("settling" if changed else "live"))
        self.setProperty("staleMotionFrozen", bool(stale))
        self.setProperty("markerDisplayValues", self._marker_display_values())
        if changed:
            self.update()
        return changed

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(14, 14, -14, -14)
        painter.fillRect(rect, QColor(5, 15, 25, 120))
        painter.setPen(QPen(QColor(72, 112, 140, 110), 1))
        painter.drawRect(rect)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.setPen(QColor(247, 251, 255, 220))
        painter.drawText(rect.adjusted(8, 4, -8, -4), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, "Right-to-left passive axis history")
        plot = rect.adjusted(18, 30, -18, -28)
        axis_count = max(1, len(self._axis_history))
        band_height = plot.height() / axis_count
        for axis_index, (axis, samples) in enumerate(self._axis_history.items()):
            band = QRectF(plot.left(), plot.top() + axis_index * band_height, plot.width(), band_height - 5)
            painter.setPen(QPen(QColor(72, 112, 140, 70), 1))
            painter.drawRect(band)
            painter.setPen(QColor(159, 185, 207, 180))
            painter.drawText(band.adjusted(6, 2, -6, -2), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, axis)
            self._draw_series(painter, band, samples, value_index=0, color=_role_color("info", axis_index))
            if self._overlay_final_values:
                self._draw_series(painter, band, samples, value_index=1, color=_role_color("ready", axis_index), dashed=True)
            self._draw_latest_markers(painter, band, axis, axis_index)

    def _draw_series(
        self,
        painter: QPainter,
        band: QRectF,
        samples: Sequence[tuple[float | None, float | None]],
        *,
        value_index: int,
        color: QColor,
        dashed: bool = False,
    ) -> None:
        if not samples:
            return
        painter.setPen(QPen(color, 1.8, Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine))
        path = QPainterPath()
        usable = band.adjusted(42, 8, -8, -8)
        for sample_index, sample in enumerate(reversed(samples[-self._capacity :])):
            value = sample[value_index]
            if value is None:
                continue
            x_ratio = sample_index / max(1, self._capacity - 1)
            x = usable.right() - usable.width() * x_ratio
            y = usable.center().y() - (max(-1.0, min(1.0, value)) * usable.height() / 2)
            point = QPointF(x, y)
            if path.elementCount() == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        painter.drawPath(path)

    def _draw_latest_markers(self, painter: QPainter, band: QRectF, axis: str, axis_index: int) -> None:
        if axis not in self._marker_easing:
            return
        raw_eased, final_eased = self._marker_easing[axis]
        usable = band.adjusted(42, 8, -8, -8)
        x = usable.right()
        for value, role, offset in (
            (raw_eased.display_value, "info", -4.0),
            (final_eased.display_value, "ready", 4.0),
        ):
            color = _role_color(role, axis_index)
            y = usable.center().y() - (max(-1.0, min(1.0, value)) * usable.height() / 2) + offset
            painter.setPen(QPen(color, 1.8))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x, y), 4.0, 4.0)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    def _refresh_marker_targets(self, *, snap: bool = False) -> None:
        for axis, samples in self._axis_history.items():
            raw_value, final_value = _latest_sample_values(samples)
            if axis not in self._marker_easing:
                self._marker_easing[axis] = (
                    EasedValue(raw_value, minimum=-1.0, maximum=1.0, motion_settings=self._motion_settings),
                    EasedValue(final_value, minimum=-1.0, maximum=1.0, motion_settings=self._motion_settings),
                )
            raw_eased, final_eased = self._marker_easing[axis]
            raw_eased.set_target(raw_value, snap=snap or not self._motion_settings.live_easing_enabled())
            final_eased.set_target(final_value, snap=snap or not self._motion_settings.live_easing_enabled())
        self.setProperty("markerTargetValues", self._marker_target_values())
        self.setProperty("markerDisplayValues", self._marker_display_values())

    def _marker_target_values(self) -> tuple[tuple[str, float, float], ...]:
        return tuple(
            (axis, raw.target_value, final.target_value)
            for axis, (raw, final) in self._marker_easing.items()
        )

    def _marker_display_values(self) -> tuple[tuple[str, float, float], ...]:
        return tuple(
            (axis, raw.display_value, final.display_value)
            for axis, (raw, final) in self._marker_easing.items()
        )


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


def _role_color(role: str, index: int) -> QColor:
    palette = {
        "ready": QColor(126, 224, 166, 210),
        "verified": QColor(126, 224, 166, 210),
        "info": QColor(118, 217, 255, 210),
        "simulation": QColor(159, 185, 207, 210),
        "warning": QColor(242, 198, 109, 220),
        "blocked": QColor(242, 198, 109, 220),
        "error": QColor(255, 113, 113, 220),
        "unavailable": QColor(102, 135, 159, 180),
    }
    if role in palette:
        return palette[role]
    fallback = (
        QColor(118, 217, 255, 210),
        QColor(126, 224, 166, 210),
        QColor(242, 198, 109, 220),
        QColor(194, 153, 255, 210),
        QColor(255, 163, 113, 210),
        QColor(159, 185, 207, 210),
    )
    return fallback[index % len(fallback)]


def _latest_sample_values(samples: Sequence[tuple[float | None, float | None]]) -> tuple[float, float]:
    for raw, final in reversed(samples):
        raw_value = 0.0 if raw is None else max(-1.0, min(1.0, float(raw)))
        final_value = raw_value if final is None else max(-1.0, min(1.0, float(final)))
        return raw_value, final_value
    return 0.0, 0.0


def _line_label_aliases(labels: tuple[str, ...]) -> tuple[str, ...]:
    aliases: list[str] = []
    for label in labels:
        if label not in aliases:
            aliases.append(label)
        if label == "Default" and "Reference" not in aliases:
            aliases.append("Reference")
        elif label == "Reference" and "Default" not in aliases:
            aliases.append("Default")
        elif label == "Filtered output" and "Filtered response" not in aliases:
            aliases.append("Filtered response")
        elif label == "Filtered response" and "Filtered output" not in aliases:
            aliases.append("Filtered output")
    return tuple(aliases)
