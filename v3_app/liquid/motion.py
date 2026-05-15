from __future__ import annotations

import os
import time
import weakref
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QWidget


class MotionIntensity(str, Enum):
    OFF = "off"
    REDUCED = "reduced"
    STANDARD = "standard"
    CINEMATIC = "cinematic"


class MicrointeractionRole(str, Enum):
    BUTTON = "button"
    NAVIGATION_BUTTON = "navigation_button"
    INTERACTIVE_CARD = "interactive_card"
    SELECTABLE_CARD = "selectable_card"
    STATUS_CARD = "status_card"
    STATUS_CHIP = "status_chip"
    STATUS_LIGHT = "status_light"
    RAW_DIAGNOSTIC = "raw_diagnostic"


class PulseRole(str, Enum):
    NONE = "none"
    VERIFIED = "verified"
    ATTENTION = "attention"
    ERROR = "error"
    INFO = "info"
    DRAFT = "draft"


class HoverRole(str, Enum):
    NONE = "none"
    BUTTON = "button"
    CARD = "card"
    STATUS_CARD = "status_card"
    DOCK = "dock"
    ROUTE_ROW = "route_row"
    CHIP = "chip"


class FocusRole(str, Enum):
    NONE = "none"
    RING = "ring"
    SUBTLE = "subtle"


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def ease_out_cubic(value: float) -> float:
    progress = _clamp01(value)
    return 1.0 - ((1.0 - progress) ** 3)


def ease_in_cubic(value: float) -> float:
    progress = _clamp01(value)
    return progress**3


def ease_in_out_cubic(value: float) -> float:
    progress = _clamp01(value)
    if progress < 0.5:
        return 4.0 * progress**3
    return 1.0 - ((-2.0 * progress + 2.0) ** 3) / 2.0


def smoothstep(value: float) -> float:
    progress = _clamp01(value)
    return progress * progress * (3.0 - (2.0 * progress))


class MotionClock:
    def __init__(self) -> None:
        self._last_now: float | None = None
        self._fps_samples: list[float] = []
        self.frame_count = 0
        self.last_delta_seconds = 0.0

    @property
    def estimated_fps(self) -> float:
        if not self._fps_samples:
            return 0.0
        average_delta = sum(self._fps_samples) / len(self._fps_samples)
        if average_delta <= 0:
            return 0.0
        return 1.0 / average_delta

    def tick(self, *, now_seconds: float | None = None) -> float:
        now = time.monotonic() if now_seconds is None else float(now_seconds)
        if self._last_now is None:
            self._last_now = now
            self.last_delta_seconds = 0.0
            return 0.0
        delta = max(0.0, min(0.1, now - self._last_now))
        self._last_now = now
        self.last_delta_seconds = delta
        if delta > 0:
            self.frame_count += 1
            self._fps_samples.append(delta)
            if len(self._fps_samples) > 30:
                del self._fps_samples[:-30]
        return delta

    def reset(self) -> None:
        self._last_now = None
        self._fps_samples.clear()
        self.frame_count = 0
        self.last_delta_seconds = 0.0


class AnimatedValue:
    def __init__(
        self,
        initial: float = 0.0,
        *,
        duration_ms: int = 180,
        easing: Callable[[float], float] = ease_out_cubic,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> None:
        self.duration_seconds = max(0.001, float(duration_ms) / 1000.0)
        self.easing = easing
        self.minimum = minimum
        self.maximum = maximum
        self.current = self._clamp(initial)
        self.source = self.current
        self.target = self.current
        self.elapsed_seconds = 0.0
        self.running = False

    def set_target(self, value: float, *, duration_ms: int | None = None, snap: bool = False) -> float:
        target = self._clamp(value)
        if duration_ms is not None:
            self.duration_seconds = max(0.001, float(duration_ms) / 1000.0)
        self.source = self.current
        self.target = target
        self.elapsed_seconds = 0.0
        self.running = not snap and abs(self.target - self.current) > 0.0001
        if snap or not self.running:
            self.current = target
            self.running = False
        return self.current

    def advance(self, delta_seconds: float) -> float:
        if not self.running:
            return self.current
        self.elapsed_seconds += max(0.0, float(delta_seconds))
        progress = _clamp01(self.elapsed_seconds / self.duration_seconds)
        eased = self.easing(progress)
        self.current = self._clamp(self.source + ((self.target - self.source) * eased))
        if progress >= 1.0 or abs(self.current - self.target) <= 0.0001:
            self.current = self.target
            self.running = False
        return self.current

    def snap(self, value: float | None = None) -> float:
        if value is not None:
            self.target = self._clamp(value)
        self.source = self.target
        self.current = self.target
        self.elapsed_seconds = 0.0
        self.running = False
        return self.current

    def _clamp(self, value: float) -> float:
        output = float(value)
        if self.minimum is not None:
            output = max(float(self.minimum), output)
        if self.maximum is not None:
            output = min(float(self.maximum), output)
        return output


@dataclass(frozen=True)
class MotionSettings:
    intensity: MotionIntensity = MotionIntensity.STANDARD

    def animations_enabled(self) -> bool:
        return self.intensity in {MotionIntensity.STANDARD, MotionIntensity.CINEMATIC}

    def pulses_enabled(self) -> bool:
        return self.intensity in {MotionIntensity.STANDARD, MotionIntensity.CINEMATIC}

    def hover_effects_enabled(self) -> bool:
        return self.intensity in {
            MotionIntensity.REDUCED,
            MotionIntensity.STANDARD,
            MotionIntensity.CINEMATIC,
        }

    def large_motion_allowed(self) -> bool:
        return False

    def cinematic_effects_enabled(self) -> bool:
        return False

    def page_motion_enabled(self) -> bool:
        return self.intensity in {
            MotionIntensity.REDUCED,
            MotionIntensity.STANDARD,
            MotionIntensity.CINEMATIC,
        }

    def panel_stagger_enabled(self) -> bool:
        return self.intensity in {MotionIntensity.STANDARD, MotionIntensity.CINEMATIC}

    def live_easing_enabled(self) -> bool:
        return self.intensity in {
            MotionIntensity.REDUCED,
            MotionIntensity.STANDARD,
            MotionIntensity.CINEMATIC,
        }

    def route_trace_enabled(self) -> bool:
        return self.intensity in {MotionIntensity.STANDARD, MotionIntensity.CINEMATIC}

    def recorder_timeline_sweep_enabled(self) -> bool:
        return False

    def atmosphere_enabled(self) -> bool:
        return self.intensity is not MotionIntensity.OFF

    def atmosphere_drift_enabled(self) -> bool:
        return self.intensity is MotionIntensity.CINEMATIC

    def shimmer_enabled(self) -> bool:
        return self.intensity is MotionIntensity.CINEMATIC

    def radial_motion_enabled(self) -> bool:
        return self.intensity in {MotionIntensity.STANDARD, MotionIntensity.CINEMATIC}

    def safe_cinematic_polish_enabled(self) -> bool:
        return self.intensity is MotionIntensity.CINEMATIC


@dataclass(frozen=True)
class MotionPolicy:
    settings: MotionSettings = MotionSettings()

    def allows_optional_motion(self) -> bool:
        return self.settings.animations_enabled()

    def allows_pulses(self) -> bool:
        return self.settings.pulses_enabled()

    def allows_hover(self) -> bool:
        return self.settings.hover_effects_enabled()

    def allows_large_motion(self) -> bool:
        return self.settings.large_motion_allowed()

    def allows_page_motion(self) -> bool:
        return self.settings.page_motion_enabled()

    def allows_live_easing(self) -> bool:
        return self.settings.live_easing_enabled()

    def allows_route_trace(self) -> bool:
        return self.settings.route_trace_enabled()


@dataclass(frozen=True)
class PageMotionSpec:
    mode: str
    enabled: bool
    duration_ms: int
    exit_ms: int
    enter_ms: int
    panel_stagger_ms: int
    slide_offset_px: int
    reduced: bool = False


def page_motion_spec(settings: MotionSettings | None = None) -> PageMotionSpec:
    active = settings or current_motion_settings()
    if active.intensity is MotionIntensity.OFF:
        return PageMotionSpec(
            mode="immediate",
            enabled=False,
            duration_ms=0,
            exit_ms=0,
            enter_ms=0,
            panel_stagger_ms=0,
            slide_offset_px=0,
        )
    if active.intensity is MotionIntensity.REDUCED:
        return PageMotionSpec(
            mode="minimal_fade",
            enabled=True,
            duration_ms=120,
            exit_ms=80,
            enter_ms=120,
            panel_stagger_ms=0,
            slide_offset_px=0,
            reduced=True,
        )
    return PageMotionSpec(
        mode="fade_slide",
        enabled=True,
        duration_ms=220 if active.intensity is MotionIntensity.STANDARD else 240,
        exit_ms=120,
        enter_ms=220 if active.intensity is MotionIntensity.STANDARD else 240,
        panel_stagger_ms=40 if active.intensity is MotionIntensity.STANDARD else 50,
        slide_offset_px=10,
    )


class EasedValue:
    def __init__(
        self,
        initial: float = 0.0,
        *,
        minimum: float = 0.0,
        maximum: float = 1.0,
        motion_settings: MotionSettings | None = None,
        smoothing: float | None = None,
    ) -> None:
        self.motion_settings = motion_settings or current_motion_settings()
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.smoothing = float(smoothing) if smoothing is not None else _smoothing_for(self.motion_settings)
        value = self._clamp(initial)
        self.source_value = value
        self.target_value = value
        self.display_value = value
        self.motion_state = "snapped" if not self.motion_settings.live_easing_enabled() else "settled"
        self._stale = False

    @property
    def enabled(self) -> bool:
        return self.motion_settings.live_easing_enabled()

    @property
    def stale(self) -> bool:
        return self._stale

    def set_target(self, value: float, *, stale: bool = False, snap: bool = False) -> float:
        clamped = self._clamp(value)
        self.source_value = clamped
        self.target_value = clamped
        self._stale = bool(stale)
        if self._stale:
            self.motion_state = "stale"
            return self.display_value
        if snap or not self.enabled:
            self.display_value = clamped
            self.motion_state = "snapped"
            return self.display_value
        self.motion_state = "target_pending"
        return self.display_value

    def advance(self, *, stale: bool = False) -> float:
        if stale or self._stale:
            self._stale = True
            self.motion_state = "stale"
            return self.display_value
        if not self.enabled:
            self.display_value = self.target_value
            self.motion_state = "snapped"
            return self.display_value
        delta = self.target_value - self.display_value
        if abs(delta) <= 0.001:
            self.display_value = self.target_value
            self.motion_state = "settled"
            return self.display_value
        self.display_value = self._clamp(self.display_value + delta * self.smoothing)
        self.motion_state = "settling"
        return self.display_value

    def snap(self) -> float:
        self._stale = False
        self.display_value = self.target_value
        self.motion_state = "snapped"
        return self.display_value

    def freeze(self) -> float:
        self._stale = True
        self.motion_state = "stale"
        return self.display_value

    def _clamp(self, value: float) -> float:
        low = min(self.minimum, self.maximum)
        high = max(self.minimum, self.maximum)
        return max(low, min(high, float(value)))


class EasedVectorValue:
    def __init__(
        self,
        initial: Mapping[str, float] | None = None,
        *,
        minimum: float = -1.0,
        maximum: float = 1.0,
        motion_settings: MotionSettings | None = None,
    ) -> None:
        self.motion_settings = motion_settings or current_motion_settings()
        self._values = {
            key: EasedValue(value, minimum=minimum, maximum=maximum, motion_settings=self.motion_settings)
            for key, value in (initial or {}).items()
        }

    def set_target(self, key: str, value: float, *, stale: bool = False, snap: bool = False) -> None:
        if key not in self._values:
            self._values[key] = EasedValue(
                value,
                minimum=-1.0,
                maximum=1.0,
                motion_settings=self.motion_settings,
            )
        self._values[key].set_target(value, stale=stale, snap=snap)

    def advance(self, *, stale: bool = False) -> dict[str, float]:
        return {key: eased.advance(stale=stale) for key, eased in self._values.items()}

    def display_values(self) -> dict[str, float]:
        return {key: eased.display_value for key, eased in self._values.items()}


class LiveMotionController:
    def __init__(self, motion_settings: MotionSettings | None = None) -> None:
        self.motion_settings = motion_settings or current_motion_settings()
        self._values: list[EasedValue] = []

    def value(self, initial: float = 0.0, *, minimum: float = 0.0, maximum: float = 1.0) -> EasedValue:
        eased = EasedValue(
            initial,
            minimum=minimum,
            maximum=maximum,
            motion_settings=self.motion_settings,
        )
        self._values.append(eased)
        return eased

    def advance_all(self, *, stale: bool = False) -> None:
        for eased in self._values:
            eased.advance(stale=stale)

    def freeze_all(self) -> None:
        for eased in self._values:
            eased.freeze()


def motion_settings_from_mapping(values: Mapping[str, str] | None = None) -> MotionSettings:
    source = values if values is not None else os.environ
    explicit = str(source.get("HELMFORGE_LIQUID_MOTION", "")).strip().casefold()
    if explicit:
        for intensity in MotionIntensity:
            if explicit == intensity.value:
                return MotionSettings(intensity)
    reduced = str(source.get("HELMFORGE_LIQUID_REDUCED_MOTION", "")).strip().casefold()
    if reduced in {"1", "true", "yes", "on", "reduced"}:
        return MotionSettings(MotionIntensity.REDUCED)
    return MotionSettings()


def current_motion_settings() -> MotionSettings:
    return motion_settings_from_mapping()


def apply_motion_property(
    widget: QWidget,
    role: MicrointeractionRole | str,
    *,
    enabled: bool = True,
    hover_role: HoverRole | str | None = None,
    focus_role: FocusRole | str | None = None,
    pulse_role: PulseRole | str | None = None,
    motion_settings: MotionSettings | None = None,
    interactive: bool | None = None,
    cursor: Qt.CursorShape | None = None,
    refresh: bool = False,
) -> QWidget:
    settings = motion_settings or current_motion_settings()
    active = bool(enabled and _widget_enabled(widget))
    role_value = _enum_value(role)
    hover_value = _enum_value(hover_role or HoverRole.NONE)
    focus_value = _enum_value(focus_role or FocusRole.NONE)
    pulse_value = _enum_value(pulse_role or PulseRole.NONE)
    hover_enabled = active and settings.hover_effects_enabled() and hover_value != HoverRole.NONE.value
    pulse_enabled = active and settings.pulses_enabled() and pulse_value != PulseRole.NONE.value
    focus_enabled = active and focus_value != FocusRole.NONE.value

    _set_if_changed(widget, "microinteractionRole", role_value)
    _set_if_changed(widget, "motionIntensity", settings.intensity.value)
    _set_if_changed(widget, "motionEnabled", active and settings.animations_enabled())
    _set_if_changed(widget, "activeInteraction", active)
    _set_if_changed(widget, "hoverRole", hover_value)
    _set_if_changed(widget, "hoverEffectsEnabled", hover_enabled)
    _set_if_changed(widget, "focusRole", focus_value)
    _set_if_changed(widget, "focusRingEnabled", focus_enabled)
    _set_if_changed(widget, "pulseRole", pulse_value)
    _set_if_changed(widget, "pulseEnabled", pulse_enabled)
    if interactive is not None:
        _set_if_changed(widget, "interactive", bool(interactive and active))
    if hover_enabled:
        widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
    if focus_enabled:
        widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    elif role_value in {MicrointeractionRole.INTERACTIVE_CARD.value, MicrointeractionRole.SELECTABLE_CARD.value}:
        widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    if cursor is not None:
        widget.setCursor(cursor if active else Qt.CursorShape.ArrowCursor)
    if pulse_enabled and role_value == MicrointeractionRole.STATUS_LIGHT.value:
        _STATUS_PULSE_CONTROLLER.register(widget)
    if refresh:
        refresh_motion_style(widget)
    return widget


def apply_panel_motion_hint(
    widget: QWidget,
    *,
    role: str,
    order: int = 0,
    motion_settings: MotionSettings | None = None,
) -> QWidget:
    settings = motion_settings or current_motion_settings()
    _set_if_changed(widget, "panelSettleRole", role)
    _set_if_changed(widget, "panelSettleOrder", int(order))
    _set_if_changed(widget, "panelSettleEnabled", settings.panel_stagger_enabled())
    _set_if_changed(widget, "panelSettleMotionMode", "settle" if settings.panel_stagger_enabled() else "static")
    _set_if_changed(widget, "motionIntensity", settings.intensity.value)
    return widget


def apply_route_signal_motion(
    widget: QWidget,
    *,
    motion_settings: MotionSettings | None = None,
    enabled: bool = True,
    role: str = "signal_path",
) -> QWidget:
    settings = motion_settings or current_motion_settings()
    active = bool(enabled and settings.route_trace_enabled() and _widget_enabled(widget))
    _set_if_changed(widget, "signalPathMotionRole", role)
    _set_if_changed(widget, "signalPathMotionAvailable", True)
    _set_if_changed(widget, "signalPathMotionEnabled", active)
    _set_if_changed(widget, "signalPathMotionMode", "signal_sweep" if active else "static")
    _set_if_changed(widget, "signalPathMotionRuntimeMutation", False)
    _set_if_changed(widget, "signalPathMotionProofClaim", False)
    _set_if_changed(widget, "motionIntensity", settings.intensity.value)
    return widget


def apply_button_motion(
    button: QWidget,
    *,
    action_kind: str,
    enabled: bool = True,
    motion_settings: MotionSettings | None = None,
    navigation: bool = False,
) -> QWidget:
    tone = button_tone_for_action(action_kind, enabled=enabled and _widget_enabled(button))
    role = MicrointeractionRole.NAVIGATION_BUTTON if navigation else MicrointeractionRole.BUTTON
    hover = HoverRole.DOCK if navigation else HoverRole.BUTTON
    _set_if_changed(button, "buttonTone", tone)
    _set_if_changed(button, "actionTone", tone)
    apply_motion_property(
        button,
        role,
        enabled=enabled and tone != "disabled",
        hover_role=hover,
        focus_role=FocusRole.RING,
        motion_settings=motion_settings,
        interactive=True,
        cursor=Qt.CursorShape.PointingHandCursor,
    )
    if tone == "disabled":
        _set_if_changed(button, "motionEnabled", False)
        _set_if_changed(button, "activeInteraction", False)
        _set_if_changed(button, "hoverEffectsEnabled", False)
        _set_if_changed(button, "pulseEnabled", False)
    return button


def apply_status_motion(
    widget: QWidget,
    *,
    state_role: str,
    component_role: MicrointeractionRole | str,
    motion_settings: MotionSettings | None = None,
    focusable: bool = False,
    hover_role: HoverRole | str | None = None,
) -> QWidget:
    pulse_role = pulse_role_for_status(state_role)
    focus = FocusRole.RING if focusable else FocusRole.NONE
    hover = hover_role or (HoverRole.STATUS_CARD if focusable else HoverRole.NONE)
    apply_motion_property(
        widget,
        component_role,
        enabled=True,
        hover_role=hover,
        focus_role=focus,
        pulse_role=pulse_role,
        motion_settings=motion_settings,
        interactive=focusable,
    )
    _set_if_changed(widget, "statusEmphasis", pulse_role.value)
    if pulse_role is PulseRole.DRAFT:
        _set_if_changed(widget, "draftEmphasis", True)
    return widget


def apply_interactive_card_motion(
    widget: QWidget,
    *,
    selectable: bool = False,
    selected: bool = False,
    motion_settings: MotionSettings | None = None,
    cursor: Qt.CursorShape = Qt.CursorShape.ArrowCursor,
) -> QWidget:
    role = MicrointeractionRole.SELECTABLE_CARD if selectable else MicrointeractionRole.INTERACTIVE_CARD
    _set_if_changed(widget, "selected", bool(selected))
    return apply_motion_property(
        widget,
        role,
        hover_role=HoverRole.CARD,
        focus_role=FocusRole.RING,
        motion_settings=motion_settings,
        interactive=cursor is Qt.CursorShape.PointingHandCursor,
        cursor=cursor,
    )


def apply_raw_diagnostic_motion(widget: QWidget) -> QWidget:
    _set_if_changed(widget, "rawDiagnosticSurface", True)
    return apply_motion_property(
        widget,
        MicrointeractionRole.RAW_DIAGNOSTIC,
        enabled=False,
        hover_role=HoverRole.NONE,
        focus_role=FocusRole.NONE,
        pulse_role=PulseRole.NONE,
        motion_settings=MotionSettings(MotionIntensity.OFF),
    )


def button_tone_for_action(action_kind: str, *, enabled: bool = True) -> str:
    if not enabled or action_kind == "disabled_deferred":
        return "disabled"
    normalized = action_kind.strip().casefold()
    if normalized in {"stage_draft", "apply", "validate", "open_panel"}:
        return "primary"
    if normalized in {"revert", "reset", "destructive", "danger"}:
        return "caution"
    return "secondary"


def pulse_role_for_status(state_role: str) -> PulseRole:
    normalized = state_role.strip().casefold()
    if normalized in {"ready", "verified", "saved", "safe", "done"}:
        return PulseRole.VERIFIED
    if normalized in {"waiting", "blocked", "attention", "unsaved", "warning", "missing-proof"}:
        return PulseRole.DRAFT if normalized == "unsaved" else PulseRole.ATTENTION
    if normalized in {"error", "unsafe", "failed"}:
        return PulseRole.ERROR
    if normalized in {"info", "simulation", "live-neutral", "neutral"}:
        return PulseRole.INFO
    return PulseRole.NONE


def refresh_motion_style(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def _set_if_changed(widget: QWidget, key: str, value: object) -> None:
    if widget.property(key) != value:
        widget.setProperty(key, value)


def _enum_value(value: Enum | str) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _widget_enabled(widget: QWidget) -> bool:
    return bool(widget.isEnabled()) if hasattr(widget, "isEnabled") else True


def _smoothing_for(settings: MotionSettings) -> float:
    if settings.intensity is MotionIntensity.REDUCED:
        return 0.62
    if settings.intensity is MotionIntensity.CINEMATIC:
        return 0.42
    return 0.35


class LiquidPulseController(QObject):
    def __init__(self, *, interval_ms: int = 1800) -> None:
        super().__init__()
        self.interval_ms = interval_ms
        self._timer_id = 0
        self._phase = 0
        self._widgets: set[weakref.ReferenceType[QWidget]] = set()

    def register(self, widget: QWidget) -> None:
        widget.setProperty("pulseTarget", "tiny_status_indicator")
        widget.setProperty("pulseIntervalMs", self.interval_ms)
        self._widgets.add(weakref.ref(widget))
        if self._timer_id == 0:
            self._timer_id = self.startTimer(self.interval_ms)

    def timerEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.timerId() != self._timer_id:
            super().timerEvent(event)
            return
        self._phase = 0 if self._phase else 1
        live_refs: set[weakref.ReferenceType[QWidget]] = set()
        visible_count = 0
        for ref in self._widgets:
            widget = ref()
            if widget is None:
                continue
            live_refs.add(ref)
            if not widget.isVisible() or widget.property("pulseEnabled") is not True:
                continue
            visible_count += 1
            widget.setProperty("pulsePhase", self._phase)
            refresh_motion_style(widget)
        self._widgets = live_refs
        if not self._widgets:
            self.killTimer(self._timer_id)
            self._timer_id = 0
        if visible_count == 0:
            return


_STATUS_PULSE_CONTROLLER = LiquidPulseController()
