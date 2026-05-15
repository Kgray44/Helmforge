from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from shared_core.models.runtime import AXIS_NAMES
from v3_app.overlay.overlay_config import LiveOverlayConfig, OverlayAxisConfig
from v3_app.pages.page_helpers import apply_parameter_metadata, card, card_header, card_layout, parameter_label


OVERLAY_PRESET_NAMES = ("Regular", "Compact", "High Contrast", "Telemetry Focus", "Minimal", "Custom")
_OVERLAY_PRESETS: dict[str, dict[str, object]] = {
    "Regular": {
        "history_seconds": 7.5,
        "height": 0.6,
        "opacity": 0.66,
        "background": 0.82,
        "line_thickness": 2.8,
        "show_legend": True,
        "show_live_values": True,
        "fps_cap": 30,
    },
    "Compact": {
        "history_seconds": 7.0,
        "height": 0.42,
        "opacity": 0.74,
        "background": 0.88,
        "line_thickness": 2.4,
        "show_legend": False,
        "show_live_values": True,
        "fps_cap": 30,
    },
    "High Contrast": {
        "history_seconds": 7.0,
        "height": 0.62,
        "opacity": 0.82,
        "background": 0.94,
        "line_thickness": 3.5,
        "show_legend": True,
        "show_live_values": True,
        "fps_cap": 60,
    },
    "Telemetry Focus": {
        "history_seconds": 10.0,
        "height": 0.68,
        "opacity": 0.70,
        "background": 0.86,
        "line_thickness": 2.6,
        "show_legend": True,
        "show_live_values": False,
        "fps_cap": 48,
    },
    "Minimal": {
        "history_seconds": 5.0,
        "height": 0.32,
        "opacity": 0.58,
        "background": 0.76,
        "line_thickness": 2.0,
        "show_legend": False,
        "show_live_values": False,
        "fps_cap": 30,
    },
}


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
        self.setProperty("postRc4eStyled", True)
        self.setWindowTitle("Live Overlay Configuration - HOTAS Control Panel V3")
        self.setMinimumSize(780, 520)
        self.resize(820, 560)
        self.setSizeGripEnabled(True)
        self._on_apply = on_apply
        self._draft = config
        self._axis_include_boxes: dict[str, QCheckBox] = {}
        self._axis_color_labels: dict[str, QLabel] = {}
        self._loading = False
        self._custom_counter = 0

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
        root.addWidget(self._preset_card())

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("liveOverlayConfigScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_content.setObjectName("liveOverlayConfigScrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(14)
        scroll_layout.addWidget(self._placement_card())
        scroll_layout.addWidget(self._appearance_card())
        scroll_layout.addWidget(self._behavior_card())
        scroll_layout.addWidget(self._data_card())
        scroll_layout.addWidget(self._axes_card())
        scroll_layout.addStretch(1)
        self.scroll_area.setWidget(scroll_content)
        root.addWidget(self.scroll_area, 1)

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

    def _preset_card(self) -> QWidget:
        frame = card("liveOverlayPresetCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Presets", "Preset changes update this local overlay configuration draft only."))
        row = QGridLayout()
        row.setHorizontalSpacing(10)
        row.setVerticalSpacing(8)
        self.preset_dropdown = QComboBox()
        self.preset_dropdown.setObjectName("liveOverlayPresetDropdown")
        self.preset_dropdown.addItems(OVERLAY_PRESET_NAMES)
        self.preset_dropdown.currentTextChanged.connect(self._apply_preset)
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setObjectName("liveOverlayPresetNameInput")
        self.preset_name_input.setPlaceholderText("Custom preset name")
        self.save_preset_button = QPushButton("Save Preset")
        self.save_preset_button.setObjectName("liveOverlaySavePresetButton")
        self.save_preset_button.setProperty("uiRole", "actionButton")
        self.save_preset_button.clicked.connect(self.save_custom_preset)
        row.addWidget(parameter_label("Presets", metadata_id="live_overlay.preset"), 0, 0)
        row.addWidget(self.preset_dropdown, 0, 1)
        row.addWidget(self.preset_name_input, 0, 2)
        row.addWidget(self.save_preset_button, 0, 3)
        layout.addLayout(row)
        return frame

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
            ("FPS cap", self.fps_cap, "30 fps default; raise only when needed", "live_overlay.fps_cap"),
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

    def save_custom_preset(self) -> None:
        name = self.preset_name_input.text().strip()
        if not name:
            self._custom_counter += 1
            name = f"Custom {self._custom_counter}"
        existing = {self.preset_dropdown.itemText(index) for index in range(self.preset_dropdown.count())}
        base = name
        suffix = 2
        while name in existing:
            name = f"{base} {suffix}"
            suffix += 1
        self.preset_dropdown.addItem(name)
        self.preset_dropdown.setCurrentText(name)
        self.setProperty("selectedPreset", name)

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
                "preset": self.preset_dropdown.currentText() or "Custom",
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
        self._loading = True
        if config.preset and self.preset_dropdown.findText(config.preset) < 0:
            self.preset_dropdown.addItem(config.preset)
        self.preset_dropdown.setCurrentText(config.preset or "Custom")
        self.setProperty("selectedPreset", self.preset_dropdown.currentText())
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
        self._connect_custom_markers()
        self._loading = False

    def _apply_preset(self, name: str) -> None:
        if self._loading:
            self.setProperty("selectedPreset", name)
            return
        preset = _OVERLAY_PRESETS.get(name)
        if preset is None:
            self.setProperty("selectedPreset", name or "Custom")
            return
        self._loading = True
        self.history.setValue(float(preset["history_seconds"]))
        self.height.setValue(float(preset["height"]))
        self.opacity.setValue(float(preset["opacity"]))
        self.background.setValue(float(preset["background"]))
        self.line_thickness.setValue(float(preset["line_thickness"]))
        self.show_legend.setChecked(bool(preset["show_legend"]))
        self.show_values.setChecked(bool(preset["show_live_values"]))
        self.fps_cap.setValue(int(preset["fps_cap"]))
        self._loading = False
        self.setProperty("selectedPreset", name)

    def _connect_custom_markers(self) -> None:
        for widget in (
            self.margin,
            self.height,
            self.opacity,
            self.background,
            self.line_thickness,
            self.show_legend,
            self.show_values,
            self.auto_hide,
            self.always_on_top,
            self.click_through,
            self.fps_cap,
            self.history,
            *self._axis_include_boxes.values(),
        ):
            if widget.property("customMarkerConnected"):
                continue
            if isinstance(widget, QCheckBox):
                widget.toggled.connect(self._mark_custom)
            else:
                widget.valueChanged.connect(self._mark_custom)
            widget.setProperty("customMarkerConnected", True)

    def _mark_custom(self) -> None:
        if self._loading:
            return
        if self.preset_dropdown.currentText() != "Custom":
            self.preset_dropdown.setCurrentText("Custom")
        self.setProperty("selectedPreset", "Custom")

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
