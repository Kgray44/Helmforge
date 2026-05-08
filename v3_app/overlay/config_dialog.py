from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from shared_core.models.runtime import AXIS_NAMES
from v3_app.overlay.overlay_config import LiveOverlayConfig, OverlayAxisConfig
from v3_app.pages.page_helpers import apply_parameter_metadata, card, card_header, card_layout, parameter_label


class LiveOverlayConfigDialog(QDialog):
    def __init__(
        self,
        *,
        config: LiveOverlayConfig,
        on_apply: Callable[[LiveOverlayConfig], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("liveOverlayConfigDialog")
        self.setWindowTitle("Live Overlay Configuration - HOTAS Control Panel V3")
        self.setMinimumSize(780, 620)
        self.setSizeGripEnabled(True)
        self._on_apply = on_apply
        self._draft = config
        self._axis_include_boxes: dict[str, QCheckBox] = {}
        self._axis_color_labels: dict[str, QLabel] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 22)
        root.setSpacing(14)
        intro = QLabel(
            "Fine-tune placement, appearance, and data behavior for the detached live telemetry overlay. "
            "Axis colors are shared with Flight Recorder so replays and live telemetry stay consistent."
        )
        intro.setObjectName("cardBody")
        intro.setWordWrap(True)
        root.addWidget(intro)
        root.addWidget(self._placement_card())
        root.addWidget(self._appearance_card())
        root.addWidget(self._behavior_card())
        root.addWidget(self._data_card())
        root.addWidget(self._axes_card())

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        self.buttons.setObjectName("overlayDialogButtons")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        restore = self.buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        if restore is not None:
            restore.clicked.connect(self.restore_defaults)
        root.addWidget(self.buttons)
        self._load_config(self._draft)

    def _placement_card(self) -> QWidget:
        frame = card("overlayPlacementCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Placement", "Where the detached strip sits."))
        grid = QGridLayout()
        self.position = QComboBox()
        self.position.addItem("Bottom strip")
        self.margin = QSpinBox()
        self.margin.setObjectName("overlayMarginField")
        self.margin.setRange(0, 96)
        self.margin.setSuffix(" px")
        self.attach = QComboBox()
        self.attach.addItem("Attach to display")
        self.width = QComboBox()
        self.width.addItem("Standard")
        self.height = QDoubleSpinBox()
        self.height.setObjectName("overlayHeightField")
        self.height.setRange(0.2, 1.0)
        self.height.setDecimals(2)
        self.height.setSingleStep(0.05)
        rows = (
            ("Position", self.position, "Bottom strip", "live_overlay.position"),
            ("Margin", self.margin, "18 px", "live_overlay.margin"),
            ("Attach", self.attach, "Attach to display", "live_overlay.attach"),
            ("Width", self.width, "Standard", "live_overlay.width"),
            ("Height", self.height, "0.60", "live_overlay.height"),
            ("Display", QLabel(self._draft.display_label), self._draft.display_label, "live_overlay.display"),
        )
        for row, (label, widget, value_text, metadata_id) in enumerate(rows):
            apply_parameter_metadata(widget, metadata_id)
            grid.addWidget(_label(label, metadata_id), row, 0)
            grid.addWidget(widget, row, 1)
            grid.addWidget(_value(value_text), row, 2)
        layout.addLayout(grid)
        return frame

    def _appearance_card(self) -> QWidget:
        frame = card("overlayAppearanceCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Appearance", "Visual density and trace readability."))
        grid = QGridLayout()
        self.opacity = _double_field("overlayOpacityField", 0.0, 1.0, 2, 0.01)
        self.background = _double_field("overlayBackgroundField", 0.0, 1.0, 2, 0.01)
        self.line_thickness = _double_field("overlayLineThicknessField", 1.0, 8.0, 2, 0.1)
        self.show_legend = QCheckBox("Show legend")
        self.show_legend.setObjectName("overlayShowLegendCheckbox")
        self.show_values = QCheckBox("Show live values")
        self.show_values.setObjectName("overlayShowValuesCheckbox")
        rows = (
            ("Opacity", self.opacity, "0.66", "live_overlay.opacity"),
            ("Background", self.background, "0.82", "live_overlay.background"),
            ("Line thickness", self.line_thickness, "2.80", "live_overlay.line_thickness"),
            ("Legend", self.show_legend, "Show legend", "live_overlay.show_legend"),
            ("Values", self.show_values, "Show live values", "live_overlay.show_values"),
        )
        for row, (label, widget, value_text, metadata_id) in enumerate(rows):
            apply_parameter_metadata(widget, metadata_id)
            grid.addWidget(_label(label, metadata_id), row, 0)
            grid.addWidget(widget, row, 1)
            grid.addWidget(_value(value_text), row, 2)
        layout.addLayout(grid)
        return frame

    def _behavior_card(self) -> QWidget:
        frame = card("overlayBehaviorCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Behavior", "Configured behavior only; hotkey registration and click-through are truth-labeled, not armed."))
        grid = QGridLayout()
        self.auto_hide = QCheckBox("Auto-hide when target loses focus")
        self.always_on_top = QCheckBox("Always on top")
        self.click_through = QCheckBox("Click-through")
        self.fps_cap = QSpinBox()
        self.fps_cap.setObjectName("overlayFpsCapField")
        self.fps_cap.setRange(15, 144)
        self.fps_cap.setSuffix(" fps")
        rows = (
            ("Auto-hide when target loses focus", self.auto_hide, "false", "live_overlay.auto_hide"),
            ("Always on top", self.always_on_top, "true", "live_overlay.always_on_top"),
            ("Click-through", self.click_through, "false", "live_overlay.click_through"),
            ("FPS cap", self.fps_cap, "60 fps", "live_overlay.fps_cap"),
            ("Toggle hotkey", QLabel(self._draft.toggle_hotkey), self._draft.toggle_hotkey, "live_overlay.toggle_hotkey"),
            ("Hotkey status", QLabel("Not registered"), "Not registered", None),
            ("Click-through support", QLabel("Not verified"), "Not verified", None),
        )
        for row, (label, widget, value_text, metadata_id) in enumerate(rows):
            apply_parameter_metadata(widget, metadata_id)
            grid.addWidget(_label(label, metadata_id), row, 0)
            grid.addWidget(widget, row, 1)
            grid.addWidget(_value(value_text), row, 2)
        layout.addLayout(grid)
        return frame

    def _data_card(self) -> QWidget:
        frame = card("overlayDataCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Data", "Source and history for overlay rendering."))
        grid = QGridLayout()
        self.source = QComboBox()
        self.source.addItem("Final output")
        self.history = _double_field("overlayHistoryField", 0.5, 60.0, 2, 0.5)
        rows = (
            ("Source", self.source, "Final output", "live_overlay.source"),
            ("History", self.history, "7.50 s", "live_overlay.history"),
        )
        for row, (label, widget, value_text, metadata_id) in enumerate(rows):
            apply_parameter_metadata(widget, metadata_id)
            grid.addWidget(_label(label, metadata_id), row, 0)
            grid.addWidget(widget, row, 1)
            grid.addWidget(_value(value_text), row, 2)
        layout.addLayout(grid)
        return frame

    def _axes_card(self) -> QWidget:
        frame = card("overlayAxesCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Axes", "Shared color model for Live Overlay and future Flight Recorder reuse."))
        grid = QGridLayout()
        for row, axis in enumerate(AXIS_NAMES):
            axis_config = self._draft.axes[axis]
            include = QCheckBox("Include")
            include.setObjectName(f"overlayAxisInclude_{axis.replace(' ', '_')}")
            color = QLabel(axis_config.color)
            color.setObjectName(f"overlayAxisColor_{axis.replace(' ', '_')}")
            color.setProperty("uiRole", "statusChip")
            color.setProperty("chipTone", "neutral")
            self._axis_include_boxes[axis] = include
            self._axis_color_labels[axis] = color
            grid.addWidget(_label(axis), row, 0)
            grid.addWidget(include, row, 1)
            grid.addWidget(color, row, 2)
        layout.addLayout(grid)
        return frame

    def restore_defaults(self) -> None:
        self._draft = LiveOverlayConfig.defaults()
        self._load_config(self._draft)

    def accept(self) -> None:
        self._on_apply(self._collect_config())
        super().accept()

    def _collect_config(self) -> LiveOverlayConfig:
        payload = self._draft.to_dict()
        payload.update(
            {
                "margin_px": self.margin.value(),
                "height": self.height.value(),
                "opacity": self.opacity.value(),
                "background": self.background.value(),
                "line_thickness": self.line_thickness.value(),
                "show_legend": self.show_legend.isChecked(),
                "show_live_values": self.show_values.isChecked(),
                "auto_hide_when_target_loses_focus": self.auto_hide.isChecked(),
                "always_on_top": self.always_on_top.isChecked(),
                "click_through": self.click_through.isChecked(),
                "fps_cap": self.fps_cap.value(),
                "history_seconds": self.history.value(),
                "axes": {
                    axis: OverlayAxisConfig(
                        include=box.isChecked(),
                        color=self._draft.axes[axis].color,
                    ).to_dict()
                    for axis, box in self._axis_include_boxes.items()
                },
            }
        )
        return LiveOverlayConfig.from_dict(payload)

    def _load_config(self, config: LiveOverlayConfig) -> None:
        self.margin.setValue(config.margin_px)
        self.height.setValue(config.height)
        self.opacity.setValue(config.opacity)
        self.background.setValue(config.background)
        self.line_thickness.setValue(config.line_thickness)
        self.show_legend.setChecked(config.show_legend)
        self.show_values.setChecked(config.show_live_values)
        self.auto_hide.setChecked(config.auto_hide_when_target_loses_focus)
        self.always_on_top.setChecked(config.always_on_top)
        self.click_through.setChecked(config.click_through)
        self.fps_cap.setValue(config.fps_cap)
        self.history.setValue(config.history_seconds)
        for axis, box in self._axis_include_boxes.items():
            box.setChecked(config.axes[axis].include)
            self._axis_color_labels[axis].setText(config.axes[axis].color)

    def showEvent(self, event) -> None:  # noqa: N802
        self._load_config(self._draft)
        super().showEvent(event)


def _label(text: str, metadata_id: str | None = None) -> QWidget:
    if metadata_id is not None:
        return parameter_label(text, metadata_id=metadata_id)
    label = QLabel(text)
    label.setObjectName("tableMutedText")
    return label


def _value(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("routeSummaryValue")
    label.setWordWrap(True)
    return label


def _double_field(object_name: str, minimum: float, maximum: float, decimals: int, step: float) -> QDoubleSpinBox:
    field = QDoubleSpinBox()
    field.setObjectName(object_name)
    field.setRange(minimum, maximum)
    field.setDecimals(decimals)
    field.setSingleStep(step)
    return field
