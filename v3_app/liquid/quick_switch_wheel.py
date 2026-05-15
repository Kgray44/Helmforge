from __future__ import annotations

import os
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton

from v3_app.liquid.glass import configure_command_action, refresh_style
from v3_app.liquid.layout import grid_layout, horizontal_layout, vertical_layout
from v3_app.liquid.motion import MotionIntensity, MotionSettings, current_motion_settings


QUICK_WHEEL_MODE_IDS = ("preflight", "mapping", "tuning", "analysis", "recorder", "support")


def _timers_allowed() -> bool:
    return os.environ.get("QT_QPA_PLATFORM", "").strip().casefold() != "offscreen"


class LiquidQuickSwitchWheel(QFrame):
    def __init__(
        self,
        *,
        model,
        active_mode_id: str,
        on_mode_selected: Callable[[str], None],
        motion_settings: MotionSettings | None = None,
        enabled: bool = False,
        object_name: str = "liquidQuickSwitchWheel",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self._model = model
        self._on_mode_selected = on_mode_selected
        self._motion_settings = motion_settings or current_motion_settings()
        self._enabled = bool(enabled)
        self._active_mode_id = active_mode_id
        self._buttons: dict[str, QPushButton] = {}
        self._animation_timer_id = 0
        self._animation_phase = 1.0
        self._animation_frame = 0
        self._animation_frames_total = 1
        self._animation_elapsed_seconds = 0.0
        self._animation_duration_seconds = 0.22
        self._external_clock_driven = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Liquid quick switch wheel")
        self.setAccessibleDescription("Navigation-only major mode selector. It does not apply, save, or change runtime state.")
        self.setProperty("quickWheel", True)
        self.setProperty("quickWheelEnabled", self._enabled)
        self.setProperty("quickWheelOpen", False)
        self.setProperty("quickWheelModeIds", QUICK_WHEEL_MODE_IDS)
        self.setProperty("quickWheelNavigationOnly", True)
        self.setProperty("quickWheelRuntimeMutation", False)
        self.setProperty("quickWheelFocusTrap", False)
        self.setProperty("quickWheelAnimationActive", False)
        self.setProperty("quickWheelVisualPhase", 1.0)
        self.setProperty("quickWheelAnimationUsesGeometry", False)
        self.setProperty("quickWheelMotionMode", _motion_mode(self._motion_settings))
        self.setProperty("motionIntensity", self._motion_settings.intensity.value)
        self._build()
        self.setVisible(False)

    def _build(self) -> None:
        root = vertical_layout(self, margins=(18, 16, 18, 16), spacing=12)
        header = horizontal_layout(spacing=8)
        title = QLabel("Quick Switch")
        title.setObjectName("liquidQuickWheelTitle")
        active = QLabel(_mode_label(self._model, self._active_mode_id))
        active.setObjectName("liquidQuickWheelActiveMode")
        active.setProperty("activeModeLabel", True)
        self._active_label = active
        header.addWidget(title, 1)
        header.addWidget(active)
        root.addLayout(header)

        grid = grid_layout(margins=(0, 0, 0, 0), spacing=9)
        for index, mode_id in enumerate(QUICK_WHEEL_MODE_IDS):
            mode = self._model.mode_by_id(mode_id)
            button = QPushButton(mode.display_name)
            button.setObjectName(f"liquidQuickWheel_{mode_id}")
            button.setProperty("uiRole", "liquidQuickWheelButton")
            button.setProperty("modeId", mode_id)
            button.setProperty("navigationOnly", True)
            button.setProperty("runtimeMutation", False)
            button.setCheckable(True)
            button.setChecked(mode_id == self._active_mode_id)
            button.setToolTip(mode.tooltip)
            button.setStatusTip("Switch Liquid mode only. Runtime, output, recording, and workspace state are unchanged.")
            button.setAccessibleName(f"Switch to {mode.display_name}")
            button.setAccessibleDescription(mode.accessibility_text)
            configure_command_action(button, action_kind="navigation")
            button.clicked.connect(lambda _checked=False, selected_mode=mode_id: self.select_mode(selected_mode))
            self._buttons[mode_id] = button
            grid.addWidget(button, index // 3, index % 3)
        root.addLayout(grid)

        hint = QLabel("Esc closes")
        hint.setObjectName("liquidQuickWheelHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(hint)
        self.update_active(self._active_mode_id)

    def mode_ids(self) -> tuple[str, ...]:
        return QUICK_WHEEL_MODE_IDS

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self.setProperty("quickWheelEnabled", self._enabled)
        if not self._enabled:
            self.set_open(False)
        refresh_style(self)

    def update_active(self, mode_id: str) -> None:
        self._active_mode_id = mode_id
        self.setProperty("activeModeId", mode_id)
        if hasattr(self, "_active_label"):
            self._active_label.setText(_mode_label(self._model, mode_id))
        for button_id, button in self._buttons.items():
            active = button_id == mode_id
            button.setChecked(active)
            button.setProperty("active", active)
            refresh_style(button)

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        self.setProperty("motionIntensity", motion_settings.intensity.value)
        self.setProperty("quickWheelMotionMode", _motion_mode(motion_settings))
        self.setProperty("quickWheelAnimationActive", False)
        self.setProperty("quickWheelVisualPhase", self._animation_phase)
        if not motion_settings.radial_motion_enabled():
            self._stop_animation()
        refresh_style(self)

    def set_external_clock_driven(self, enabled: bool) -> None:
        self._external_clock_driven = bool(enabled)
        if self._external_clock_driven:
            self._stop_animation(keep_phase=True)

    def set_open(self, open_: bool) -> bool:
        should_open = bool(open_) and self._enabled
        self.setProperty("quickWheelOpen", should_open)
        self.setVisible(should_open)
        if should_open:
            self.raise_()
            self.setFocus(Qt.FocusReason.ShortcutFocusReason)
            self._begin_open_animation()
        else:
            self._stop_animation()
            self._animation_phase = 0.0
            self.setProperty("quickWheelAnimationActive", False)
            self.setProperty("quickWheelVisualPhase", 0.0)
        refresh_style(self)
        return should_open

    def open_wheel(self) -> bool:
        return self.set_open(True)

    def close_wheel(self) -> bool:
        return self.set_open(False)

    def toggle_wheel(self) -> bool:
        return self.set_open(not self.isVisible())

    def select_mode(self, mode_id: str) -> None:
        if mode_id not in QUICK_WHEEL_MODE_IDS:
            raise KeyError(mode_id)
        self._on_mode_selected(mode_id)
        self.set_open(False)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.key() == Qt.Key.Key_Escape:
            self.close_wheel()
            event.accept()
            return
        super().keyPressEvent(event)

    def timerEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.timerId() != self._animation_timer_id:
            super().timerEvent(event)
            return
        self._advance_animation()
        event.accept()

    def advance_animation_for_test(self, *, frames: int = 1) -> None:
        for _index in range(max(0, int(frames))):
            if self.property("quickWheelAnimationActive") is True:
                self._advance_animation()

    def _begin_open_animation(self) -> None:
        if not self._motion_settings.radial_motion_enabled():
            self._stop_animation()
            self._animation_phase = 1.0
            self.setProperty("quickWheelAnimationActive", False)
            self.setProperty("quickWheelVisualPhase", 1.0)
            self._apply_segment_phase()
            return
        self._animation_phase = 0.0
        self._animation_frame = 0
        duration = 300 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 220
        self._animation_elapsed_seconds = 0.0
        self._animation_duration_seconds = max(0.001, duration / 1000.0)
        self._animation_frames_total = max(1, duration // 33)
        self.setProperty("quickWheelAnimationActive", True)
        self.setProperty("quickWheelVisualPhase", 0.0)
        self._apply_segment_phase()
        if self._animation_timer_id:
            self.killTimer(self._animation_timer_id)
        if _timers_allowed() and not self._external_clock_driven:
            self._animation_timer_id = self.startTimer(33)

    def advance_motion_frame(self, *, delta_seconds: float = 1.0 / 60.0) -> None:
        if self.property("quickWheelAnimationActive") is True:
            self._advance_animation(delta_seconds=delta_seconds)

    def _advance_animation(self, *, delta_seconds: float = 1.0 / 33.0) -> None:
        self._animation_frame += 1
        self._animation_elapsed_seconds += max(0.0, delta_seconds)
        progress = min(1.0, self._animation_elapsed_seconds / self._animation_duration_seconds)
        self._animation_phase = 1.0 - ((1.0 - progress) ** 3)
        self.setProperty("quickWheelVisualPhase", round(self._animation_phase, 3))
        self._apply_segment_phase()
        if progress >= 1.0:
            self._stop_animation(keep_phase=True)
        refresh_style(self)

    def _apply_segment_phase(self) -> None:
        for index, button in enumerate(self._buttons.values()):
            segment_threshold = min(1.0, self._animation_phase + (index * 0.04))
            button.setProperty("quickWheelSegmentPhase", round(segment_threshold, 3))
            button.setProperty("quickWheelSegmentActive", segment_threshold >= 0.18)
            refresh_style(button)

    def _stop_animation(self, *, keep_phase: bool = False) -> None:
        if self._animation_timer_id:
            self.killTimer(self._animation_timer_id)
            self._animation_timer_id = 0
        self.setProperty("quickWheelAnimationActive", False)
        if keep_phase:
            self.setProperty("quickWheelVisualPhase", round(self._animation_phase, 3))


def _motion_mode(motion_settings: MotionSettings) -> str:
    if motion_settings.intensity is MotionIntensity.OFF:
        return "instant"
    if motion_settings.intensity is MotionIntensity.REDUCED:
        return "minimal"
    if motion_settings.intensity is MotionIntensity.CINEMATIC:
        return "unfold"
    return "settle"


def _mode_label(model, mode_id: str) -> str:
    try:
        return model.mode_by_id(mode_id).display_name
    except KeyError:
        return "Liquid"
