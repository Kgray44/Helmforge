from __future__ import annotations

import math
import os
import weakref
from dataclasses import dataclass
from typing import Iterable

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QAbstractButton, QFrame, QLabel, QPushButton, QWidget

from v3_app.liquid.layout import horizontal_layout, vertical_layout
from v3_app.liquid.motion import (
    AnimatedValue,
    MotionClock,
    MotionIntensity,
    MotionSettings,
    current_motion_settings,
    ease_in_out_cubic,
    ease_out_cubic,
    page_motion_spec,
    refresh_motion_style,
    smoothstep,
)
from v3_app.liquid.status_components import StatusChip


def _timers_allowed() -> bool:
    return os.environ.get("QT_QPA_PLATFORM", "").strip().casefold() != "offscreen"


@dataclass(frozen=True)
class VisibleMotionProfile:
    intensity: MotionIntensity
    optional_motion_enabled: bool
    atmosphere_drift: bool
    status_breathing: bool
    page_transition_overlay: bool
    route_sweep: bool
    quick_wheel_animation: bool
    live_easing_preview: bool
    frame_interval_ms: int
    visible_motion_type_count: int
    active_interactions: bool = False
    passive_motion_enabled: bool = False
    component_glint: bool = False
    motion_richness_score: int = 0


def visible_motion_profile(settings: MotionSettings | None = None) -> VisibleMotionProfile:
    active = settings or current_motion_settings()
    intensity = active.intensity
    if intensity is MotionIntensity.OFF:
        return VisibleMotionProfile(intensity, False, False, False, False, False, False, False, 0, 0, False, False, False, 0)
    if intensity is MotionIntensity.REDUCED:
        return VisibleMotionProfile(intensity, False, False, False, False, False, False, False, 0, 0, False, False, False, 1)
    if intensity is MotionIntensity.CINEMATIC:
        return VisibleMotionProfile(intensity, True, True, True, True, True, True, True, 16, 8, True, True, True, 9)
    return VisibleMotionProfile(intensity, True, True, True, True, True, True, True, 16, 6, True, True, True, 6)


def _advance_phase(phase: float, delta_seconds: float, period_seconds: float) -> float:
    if period_seconds <= 0:
        return phase
    return (phase + (max(0.0, delta_seconds) / period_seconds)) % 1.0


@dataclass
class ComponentMotionBinding:
    widget_ref: weakref.ReferenceType[QWidget]
    hover: AnimatedValue
    press: AnimatedValue
    focus: AnimatedValue
    selection: AnimatedValue
    state_change: AnimatedValue
    glint: AnimatedValue
    last_style_step: tuple[int, int, int, int, int, int] = (-1, -1, -1, -1, -1, -1)
    last_activity_timestamp: int = 0

    @classmethod
    def create(cls, widget: QWidget) -> ComponentMotionBinding:
        return cls(
            widget_ref=weakref.ref(widget),
            hover=AnimatedValue(0.0, duration_ms=160, easing=ease_out_cubic, minimum=0.0, maximum=1.0),
            press=AnimatedValue(0.0, duration_ms=110, easing=ease_out_cubic, minimum=0.0, maximum=1.0),
            focus=AnimatedValue(0.0, duration_ms=160, easing=ease_out_cubic, minimum=0.0, maximum=1.0),
            selection=AnimatedValue(0.0, duration_ms=210, easing=ease_in_out_cubic, minimum=0.0, maximum=1.0),
            state_change=AnimatedValue(0.0, duration_ms=420, easing=ease_out_cubic, minimum=0.0, maximum=1.0),
            glint=AnimatedValue(0.0, duration_ms=520, easing=smoothstep, minimum=0.0, maximum=1.0),
        )


class LiquidMotionCoordinator(QObject):
    def __init__(self, *, motion_settings: MotionSettings | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._motion_settings = motion_settings or current_motion_settings()
        self._clock = MotionClock()
        self._timer_id = 0
        self._runtime_active = False
        self._bindings: dict[int, ComponentMotionBinding] = {}
        self._passive_drivers: dict[str, weakref.ReferenceType[QObject]] = {}
        self._atmosphere_phase = 0.0
        self._status_phase = 0.0
        self._route_phase = 0.0
        self._page_transition_timestamp = 0
        self._interaction_timestamp = 0
        self._frame_serial = 0
        self.setProperty("singleCentralMotionClock", True)
        self.set_motion_settings(self._motion_settings)

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        profile = visible_motion_profile(motion_settings)
        self.setProperty("motionIntensity", motion_settings.intensity.value)
        self.setProperty("activeInteractionsEnabled", profile.active_interactions)
        self.setProperty("passiveMotionEnabled", profile.passive_motion_enabled)
        self.setProperty("pageTransitionEnabled", profile.page_transition_overlay)
        self.setProperty("routeSweepEnabled", profile.route_sweep)
        self.setProperty("componentGlintEnabled", profile.component_glint)
        self.setProperty("motionRichnessScore", profile.motion_richness_score)
        self.setProperty("activeAnimationControllerCount", self._active_controller_count(profile))
        self.setProperty("passiveAnimationCount", self._passive_count(profile))
        if not profile.optional_motion_enabled:
            self._stop_timer()
            self._reset_optional_values()

    def set_runtime_active(self, active: bool) -> None:
        self._runtime_active = bool(active)
        profile = visible_motion_profile(self._motion_settings)
        if self._runtime_active and profile.optional_motion_enabled and _timers_allowed():
            self._ensure_timer(profile.frame_interval_ms or 16)
        else:
            self._stop_timer()

    def register_passive_driver(self, name: str, driver: QObject | None) -> None:
        if driver is None:
            return
        self._passive_drivers[name] = weakref.ref(driver)
        if hasattr(driver, "set_external_clock_driven"):
            driver.set_external_clock_driven(True)

    def register_interaction_targets(self, widgets: Iterable[QWidget]) -> None:
        live_ids: set[int] = set()
        for widget in widgets:
            if widget is None or widget.property("rawDiagnosticSurface") is True:
                continue
            key = id(widget)
            live_ids.add(key)
            binding = self._bindings.get(key)
            if binding is None or binding.widget_ref() is None:
                binding = ComponentMotionBinding.create(widget)
                self._bindings[key] = binding
                widget.installEventFilter(self)
                widget.setProperty("motionBindingRegistered", True)
                widget.setProperty("motionUsesLayoutGeometry", False)
                widget.setProperty("motionCoordinatorDriven", True)
            if widget.property("motionProofDemo") == "button":
                binding.hover.set_target(1.0, duration_ms=260)
            elif widget.property("motionProofDemo") == "card":
                binding.selection.set_target(1.0, duration_ms=320)
            elif widget.property("motionProofDemo") == "chip" and binding.state_change.target <= 0.0:
                binding.state_change.set_target(1.0, duration_ms=420)
        for key in tuple(self._bindings):
            widget = self._bindings[key].widget_ref()
            if widget is None:
                del self._bindings[key]
        self._sync_selection_targets()
        self.setProperty("motionBindingTargetCount", len(self._bindings))

    def set_interaction_state(
        self,
        widget: QWidget,
        *,
        hovered: bool | None = None,
        pressed: bool | None = None,
        focused: bool | None = None,
        selected: bool | None = None,
    ) -> None:
        binding = self._binding_for(widget)
        profile = visible_motion_profile(self._motion_settings)
        if not profile.active_interactions or not widget.isEnabled():
            self._apply_binding(widget, binding, force_static=True)
            return
        duration = 220 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 170
        if hovered is not None:
            binding.hover.set_target(1.0 if hovered else 0.0, duration_ms=duration)
        if pressed is not None:
            binding.press.set_target(1.0 if pressed else 0.0, duration_ms=95)
        if focused is not None:
            binding.focus.set_target(1.0 if focused else 0.0, duration_ms=duration)
        if selected is not None:
            widget.setProperty("motionManualSelectedTarget", bool(selected))
            binding.selection.set_target(1.0 if selected else 0.0, duration_ms=240)
            if selected:
                binding.glint.snap(0.0)
                binding.glint.set_target(1.0, duration_ms=520)
        self._interaction_timestamp += 1
        binding.last_activity_timestamp = self._interaction_timestamp
        self.setProperty("lastInteractionAnimationTimestamp", self._interaction_timestamp)

    def trigger_status_transition(self, widget: QWidget, *, role: str = "info") -> None:
        binding = self._binding_for(widget)
        widget.setProperty("stateChangeMotionRole", role)
        widget.setProperty("stateChangeMotionActive", visible_motion_profile(self._motion_settings).active_interactions)
        binding.state_change.snap(0.0)
        binding.state_change.set_target(1.0, duration_ms=460)
        binding.glint.snap(0.0)
        binding.glint.set_target(1.0, duration_ms=520)
        self._interaction_timestamp += 1
        binding.last_activity_timestamp = self._interaction_timestamp
        self.setProperty("lastInteractionAnimationTimestamp", self._interaction_timestamp)

    def trigger_page_transition(self, root: QWidget | None) -> None:
        self._page_transition_timestamp += 1
        self.setProperty("lastPageTransitionTimestamp", self._page_transition_timestamp)
        if root is None:
            return
        preferred_roles = {
            "LiquidHeroPanel",
            "LiquidInstrumentPanel",
            "LiquidInspectorPanel",
            "LiquidDetailPanel",
            "LiquidPageHeader",
            "AnalysisResponseStackChain",
            "AnalysisStackActions",
            "RouteFlowRow",
            "SignalPipelineStage",
            "MappingRouteHero",
            "TuningAxisHero",
        }
        candidates = []
        fallback = []
        for widget in root.findChildren(QWidget):
            if widget.property("rawDiagnosticSurface") is True:
                continue
            component_role = str(widget.property("componentRole") or "")
            if component_role in preferred_roles:
                candidates.append(widget)
            elif component_role and widget.property("liquidComponent") is True:
                fallback.append(widget)
        if not candidates:
            candidates = fallback
        for order, widget in enumerate(candidates[:12]):
            widget.setProperty("panelSettleOrder", order)
            widget.setProperty("panelSettleEnabled", visible_motion_profile(self._motion_settings).active_interactions)
            widget.setProperty("panelSettleValue", 0.0)
            binding = self._binding_for(widget)
            binding.selection.snap(0.0)
            binding.selection.set_target(1.0, duration_ms=280 + (order * 24))

    def advance_for_test(self, *, frames: int = 1, delta_seconds: float = 1.0 / 60.0) -> None:
        for _index in range(max(0, int(frames))):
            self._advance_frame(delta_seconds)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if isinstance(watched, QWidget) and id(watched) in self._bindings:
            event_type = event.type()
            if event_type == QEvent.Type.Enter:
                self.set_interaction_state(watched, hovered=True)
            elif event_type == QEvent.Type.Leave:
                self.set_interaction_state(watched, hovered=False, pressed=False)
            elif event_type == QEvent.Type.FocusIn:
                self.set_interaction_state(watched, focused=True)
            elif event_type == QEvent.Type.FocusOut:
                self.set_interaction_state(watched, focused=False, pressed=False)
            elif event_type == QEvent.Type.MouseButtonPress:
                self.set_interaction_state(watched, pressed=True)
            elif event_type == QEvent.Type.MouseButtonRelease:
                selected = _widget_selected(watched)
                self.set_interaction_state(watched, pressed=False, selected=selected)
        return super().eventFilter(watched, event)

    def timerEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.timerId() != self._timer_id:
            super().timerEvent(event)
            return
        delta = self._clock.tick()
        self._advance_frame(delta if delta > 0 else 1.0 / 60.0)
        event.accept()

    def _advance_frame(self, delta_seconds: float) -> None:
        profile = visible_motion_profile(self._motion_settings)
        self._frame_serial += 1
        if not profile.optional_motion_enabled:
            self._reset_optional_values()
            return

        atmosphere_period = 38.0 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 56.0
        status_period = 2.9 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 3.7
        route_period = 1.5 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 2.2
        if profile.atmosphere_drift:
            self._atmosphere_phase = _advance_phase(self._atmosphere_phase, delta_seconds, atmosphere_period)
        if profile.status_breathing:
            self._status_phase = _advance_phase(self._status_phase, delta_seconds, status_period)
        if profile.route_sweep:
            self._route_phase = _advance_phase(self._route_phase, delta_seconds, route_period)

        self.setProperty("atmospherePhase", round(self._atmosphere_phase, 4))
        self.setProperty("statusPulsePhase", round(self._status_phase, 4))
        self.setProperty("routeSweepPhase", round(self._route_phase, 4))
        self.setProperty("motionFrameSerial", self._frame_serial)
        self.setProperty("motionFpsEstimate", round(self._clock.estimated_fps or (1.0 / max(delta_seconds, 0.001)), 1))
        self._advance_passive_drivers(delta_seconds)
        self._sync_selection_targets()
        active_count = self._advance_bindings(delta_seconds)
        self.setProperty("activeAnimationCount", active_count)
        self.setProperty("passiveAnimationCount", self._passive_count(profile))
        self._update_proof_panels(active_count, self._passive_count(profile))

    def _advance_bindings(self, delta_seconds: float) -> int:
        active_count = 0
        for key in tuple(self._bindings):
            binding = self._bindings[key]
            widget = binding.widget_ref()
            if widget is None:
                del self._bindings[key]
                continue
            running_before = _binding_running(binding)
            for value in (binding.hover, binding.press, binding.focus, binding.selection, binding.state_change, binding.glint):
                value.advance(delta_seconds)
            if binding.state_change.current >= 0.995 and not binding.state_change.running:
                binding.state_change.set_target(0.0, duration_ms=640)
            if binding.glint.current >= 0.995 and not binding.glint.running:
                binding.glint.set_target(0.0, duration_ms=680)
            if running_before or _binding_running(binding):
                active_count += 1
            self._apply_binding(widget, binding)
        return active_count

    def _advance_passive_drivers(self, delta_seconds: float) -> None:
        for name, ref in tuple(self._passive_drivers.items()):
            driver = ref()
            if driver is None:
                del self._passive_drivers[name]
                continue
            if hasattr(driver, "advance_motion_frame"):
                driver.advance_motion_frame(delta_seconds=delta_seconds)
            elif hasattr(driver, "advance_for_test"):
                driver.advance_for_test(1)

    def _update_proof_panels(self, active_count: int, passive_count: int) -> None:
        for ref in self._passive_drivers.values():
            driver = ref()
            if driver is None or not hasattr(driver, "update_motion_metrics"):
                continue
            driver.update_motion_metrics(
                fps=float(self.property("motionFpsEstimate") or 0.0),
                active_count=active_count,
                passive_count=passive_count,
                atmosphere_phase=self._atmosphere_phase,
                status_phase=self._status_phase,
                route_phase=self._route_phase,
                last_page_transition=self._page_transition_timestamp,
                last_interaction=self._interaction_timestamp,
            )

    def _binding_for(self, widget: QWidget) -> ComponentMotionBinding:
        key = id(widget)
        binding = self._bindings.get(key)
        if binding is None or binding.widget_ref() is None:
            binding = ComponentMotionBinding.create(widget)
            self._bindings[key] = binding
            widget.installEventFilter(self)
            widget.setProperty("motionBindingRegistered", True)
            widget.setProperty("motionUsesLayoutGeometry", False)
            widget.setProperty("motionCoordinatorDriven", True)
        return binding

    def _sync_selection_targets(self) -> None:
        if not visible_motion_profile(self._motion_settings).active_interactions:
            return
        for binding in self._bindings.values():
            widget = binding.widget_ref()
            if widget is None:
                continue
            if widget.property("panelSettleEnabled") is True:
                continue
            selected = _widget_selected(widget)
            if abs(binding.selection.target - (1.0 if selected else 0.0)) > 0.001:
                binding.selection.set_target(1.0 if selected else 0.0, duration_ms=240)

    def _apply_binding(self, widget: QWidget, binding: ComponentMotionBinding, *, force_static: bool = False) -> None:
        if force_static or not visible_motion_profile(self._motion_settings).active_interactions:
            values = (0, 0, 0, 0, 0, 0)
            widget.setProperty("hoverMotionValue", 0.0)
            widget.setProperty("pressMotionValue", 0.0)
            widget.setProperty("focusMotionValue", 0.0)
            widget.setProperty("selectionMotionValue", 0.0)
            widget.setProperty("stateChangeMotionValue", 0.0)
            widget.setProperty("glintMotionValue", 0.0)
        else:
            values = (
                _motion_step(binding.hover.current),
                _motion_step(binding.press.current),
                _motion_step(binding.focus.current),
                _motion_step(binding.selection.current),
                _motion_step(binding.state_change.current),
                _motion_step(binding.glint.current),
            )
            widget.setProperty("hoverMotionValue", round(binding.hover.current, 3))
            widget.setProperty("pressMotionValue", round(binding.press.current, 3))
            widget.setProperty("focusMotionValue", round(binding.focus.current, 3))
            widget.setProperty("selectionMotionValue", round(binding.selection.current, 3))
            widget.setProperty("stateChangeMotionValue", round(binding.state_change.current, 3))
            widget.setProperty("glintMotionValue", round(binding.glint.current, 3))
        widget.setProperty("hoverGlowStep", values[0])
        widget.setProperty("pressMotionStep", values[1])
        widget.setProperty("focusMotionStep", values[2])
        widget.setProperty("selectionMotionStep", values[3])
        widget.setProperty("stateChangeMotionStep", values[4])
        widget.setProperty("glintMotionStep", values[5])
        if widget.property("panelSettleEnabled") is True:
            widget.setProperty("panelSettleValue", round(binding.selection.current, 3))
            widget.setProperty("panelSettleStep", values[3])
        if binding.last_style_step != values:
            binding.last_style_step = values
            refresh_motion_style(widget)

    def _reset_optional_values(self) -> None:
        self._atmosphere_phase = 0.0
        self._status_phase = 0.0
        self._route_phase = 0.0
        self.setProperty("atmospherePhase", 0.0)
        self.setProperty("statusPulsePhase", 0.0)
        self.setProperty("routeSweepPhase", 0.0)
        self.setProperty("activeAnimationCount", 0)
        for binding in self._bindings.values():
            widget = binding.widget_ref()
            if widget is not None:
                self._apply_binding(widget, binding, force_static=True)

    def _ensure_timer(self, interval_ms: int) -> None:
        if self._timer_id:
            self.killTimer(self._timer_id)
        self._clock.reset()
        self._timer_id = self.startTimer(max(12, int(interval_ms)))

    def _stop_timer(self) -> None:
        if self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = 0

    @staticmethod
    def _active_controller_count(profile: VisibleMotionProfile) -> int:
        return sum(
            1
            for enabled in (
                profile.active_interactions,
                profile.page_transition_overlay,
                profile.route_sweep,
                profile.live_easing_preview,
                profile.quick_wheel_animation,
                profile.component_glint,
            )
            if enabled
        )

    @staticmethod
    def _passive_count(profile: VisibleMotionProfile) -> int:
        return sum(1 for enabled in (profile.atmosphere_drift, profile.status_breathing, profile.component_glint) if enabled)


def _binding_running(binding: ComponentMotionBinding) -> bool:
    return any(
        value.running
        for value in (binding.hover, binding.press, binding.focus, binding.selection, binding.state_change, binding.glint)
    )


def _widget_selected(widget: QWidget) -> bool:
    if widget.property("motionManualSelectedTarget") is not None:
        return bool(widget.property("motionManualSelectedTarget"))
    if isinstance(widget, QAbstractButton):
        return bool(widget.isChecked() or widget.property("active") is True or widget.property("selected") is True)
    return bool(widget.property("active") is True or widget.property("selected") is True or widget.property("draftEmphasis") is True)


def _motion_step(value: float) -> int:
    return max(0, min(8, int(round(float(value) * 8))))


class LiquidAtmosphereLayer(QFrame):
    def __init__(
        self,
        *,
        motion_settings: MotionSettings | None = None,
        object_name: str = "liquidVisibleAtmosphereLayer",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self._motion_settings = motion_settings or current_motion_settings()
        self._timer_id = 0
        self._phase = 0.0
        self._tick_count = 0
        self._runtime_active = False
        self._external_clock_driven = False
        self.setProperty("atmosphereUsesBlur", False)
        self.setProperty("atmosphereUsesDistortion", False)
        self.setProperty("atmosphereBlocksInput", False)
        self.set_motion_settings(self._motion_settings)

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        profile = visible_motion_profile(motion_settings)
        running = profile.atmosphere_drift
        self.setProperty("motionIntensity", motion_settings.intensity.value)
        self.setProperty("atmosphereControllerRunning", running)
        self.setProperty("atmosphereVisualMotionTypes", ("gradient_drift", "glow_field", "reflection_sweep") if running else ())
        self.setProperty("atmosphereVisualPhase", round(self._phase, 3))
        self.setProperty("atmosphereVisualTickCount", self._tick_count)
        self.setVisible(running)
        if running and self._runtime_active and not self._external_clock_driven:
            self._ensure_timer(profile.frame_interval_ms)
        else:
            self._stop_timer()
            self._phase = 0.0
            self.setProperty("atmosphereVisualPhase", 0.0)
        refresh_motion_style(self)

    def set_runtime_active(self, active: bool) -> None:
        self._runtime_active = bool(active)
        profile = visible_motion_profile(self._motion_settings)
        if self._runtime_active and profile.atmosphere_drift and not self._external_clock_driven:
            self._ensure_timer(profile.frame_interval_ms)
        else:
            self._stop_timer()

    def set_external_clock_driven(self, enabled: bool) -> None:
        self._external_clock_driven = bool(enabled)
        if self._external_clock_driven:
            self._stop_timer()

    def advance_for_test(self, frames: int = 1) -> None:
        for _index in range(max(0, int(frames))):
            if visible_motion_profile(self._motion_settings).atmosphere_drift:
                self._advance(1.0 / 60.0)

    def advance_motion_frame(self, *, delta_seconds: float = 1.0 / 60.0) -> None:
        if visible_motion_profile(self._motion_settings).atmosphere_drift:
            self._advance(delta_seconds)

    def timerEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.timerId() != self._timer_id:
            super().timerEvent(event)
            return
        if not self.isVisible():
            event.accept()
            return
        self._advance()
        event.accept()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().paintEvent(event)
        if not visible_motion_profile(self._motion_settings).atmosphere_drift:
            return
        rect = QRectF(self.rect())
        if rect.width() <= 1 or rect.height() <= 1:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        phase = self._phase
        cinematic = self._motion_settings.intensity is MotionIntensity.CINEMATIC
        glow_x = rect.width() * (0.34 + 0.28 * math.sin(phase * math.tau))
        glow_y = rect.height() * (0.42 + 0.12 * math.cos((phase + 0.18) * math.tau))
        glow = QRadialGradient(glow_x, glow_y, max(rect.width(), rect.height()) * (0.42 if cinematic else 0.32))
        glow.setColorAt(0.0, QColor(86, 220, 255, 28 if cinematic else 14))
        glow.setColorAt(0.42, QColor(41, 122, 169, 12 if cinematic else 6))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, glow)

        sweep_offset = (phase * (0.65 if cinematic else 0.38)) % 1.0
        x0 = rect.left() + (rect.width() * sweep_offset) - rect.width() * 0.25
        band = QLinearGradient(x0, rect.top(), x0 + rect.width() * 0.24, rect.bottom())
        band.setColorAt(0.0, QColor(255, 255, 255, 0))
        band.setColorAt(0.46, QColor(200, 247, 255, 9 if cinematic else 4))
        band.setColorAt(0.5, QColor(255, 255, 255, 14 if cinematic else 6))
        band.setColorAt(0.54, QColor(106, 226, 255, 8 if cinematic else 3))
        band.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(rect, band)

        edge_pen = QPen(QColor(126, 224, 255, 10 + int((7 if cinematic else 3) * math.sin(phase * math.tau) ** 2)), 1)
        painter.setPen(edge_pen)
        painter.drawRoundedRect(rect.adjusted(5, 5, -6, -6), 18, 18)

    def _advance(self, delta_seconds: float = 1.0 / 60.0) -> None:
        profile = visible_motion_profile(self._motion_settings)
        period = 38.0 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 56.0
        self._phase = _advance_phase(self._phase, delta_seconds, period)
        self._tick_count += 1
        self.setProperty("atmosphereVisualPhase", round(self._phase, 3))
        self.setProperty("atmosphereVisualTickCount", self._tick_count)
        self.setProperty("atmosphereControllerRunning", profile.atmosphere_drift)
        self.update()

    def _ensure_timer(self, interval_ms: int) -> None:
        if not _timers_allowed():
            self._stop_timer()
            return
        interval = max(50, int(interval_ms or 80))
        if self._timer_id:
            self.killTimer(self._timer_id)
        self._timer_id = self.startTimer(interval)

    def _stop_timer(self) -> None:
        if self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = 0


class LiquidPageTransitionOverlay(QFrame):
    def __init__(
        self,
        *,
        motion_settings: MotionSettings | None = None,
        object_name: str = "liquidPageTransitionOverlay",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._motion_settings = motion_settings or current_motion_settings()
        self._timer_id = 0
        self._phase = 1.0
        self._frames_total = 1
        self._frame = 0
        self._elapsed_seconds = 0.0
        self._duration_seconds = 0.22
        self._external_clock_driven = False
        self._previous_snapshot = QPixmap()
        self._current_snapshot = QPixmap()
        self._glide_offset_px = 18
        self._enter_alpha = 1.0
        self._exit_alpha = 0.0
        self._enter_offset_px = 0.0
        self._exit_offset_px = 0.0
        self.setProperty("pageTransitionUsesGeometryAnimation", False)
        self.setProperty("pageTransitionUsesOpacityEffect", False)
        self.setProperty("pageTransitionUsesBlurEffect", False)
        self.setProperty("pageTransitionAnimationKind", "snapshot_crossfade_glide")
        self.setProperty("pageTransitionHasPreviousSnapshot", False)
        self.setProperty("pageTransitionHasCurrentSnapshot", False)
        self.setProperty("pageTransitionGlideOffsetPx", self._glide_offset_px)
        self.setProperty("pageTransitionEnterAlpha", 1.0)
        self.setProperty("pageTransitionExitAlpha", 0.0)
        self.setProperty("pageTransitionEnterOffsetPx", 0.0)
        self.setProperty("pageTransitionExitOffsetPx", 0.0)
        self.setVisible(False)
        self.set_motion_settings(self._motion_settings)

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        profile = visible_motion_profile(motion_settings)
        spec = page_motion_spec(motion_settings)
        self.setProperty("motionIntensity", motion_settings.intensity.value)
        self.setProperty("pageTransitionControllerEnabled", profile.page_transition_overlay)
        self.setProperty("pageTransitionOverlayDurationMs", spec.duration_ms if profile.page_transition_overlay else 0)
        if not profile.page_transition_overlay:
            self._clear()
        refresh_motion_style(self)

    def set_external_clock_driven(self, enabled: bool) -> None:
        self._external_clock_driven = bool(enabled)
        if self._external_clock_driven and self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = 0

    def begin(
        self,
        *,
        from_route: str,
        to_route: str,
        previous_snapshot: QPixmap | None = None,
        current_snapshot: QPixmap | None = None,
    ) -> bool:
        profile = visible_motion_profile(self._motion_settings)
        if not profile.page_transition_overlay or from_route == to_route:
            self._clear()
            return False
        spec = page_motion_spec(self._motion_settings)
        self._previous_snapshot = previous_snapshot if previous_snapshot is not None else QPixmap()
        self._current_snapshot = current_snapshot if current_snapshot is not None else QPixmap()
        if self._motion_settings.intensity is MotionIntensity.CINEMATIC:
            self._glide_offset_px = 28
        elif self._motion_settings.intensity is MotionIntensity.STANDARD:
            self._glide_offset_px = 18
        else:
            self._glide_offset_px = 6
        self._phase = 0.0
        self._frame = 0
        self._elapsed_seconds = 0.0
        self._duration_seconds = max(0.001, float(spec.duration_ms or 220) / 1000.0)
        self._frames_total = max(1, int(spec.duration_ms or 220) // 33)
        self._apply_crossfade_state(raw_progress=0.0)
        self.setProperty("pageTransitionAnimationKind", "snapshot_crossfade_glide")
        self.setProperty("pageTransitionHasPreviousSnapshot", not self._previous_snapshot.isNull())
        self.setProperty("pageTransitionHasCurrentSnapshot", not self._current_snapshot.isNull())
        self.setProperty("pageTransitionGlideOffsetPx", self._glide_offset_px)
        self.setProperty("pageTransitionOverlayActive", True)
        self.setProperty("pageTransitionOverlayPhase", 0.0)
        self.setProperty("pageTransitionFrom", from_route)
        self.setProperty("pageTransitionTo", to_route)
        self.setVisible(True)
        self.raise_()
        if self._timer_id:
            self.killTimer(self._timer_id)
        if _timers_allowed() and not self._external_clock_driven:
            self._timer_id = self.startTimer(33)
        refresh_motion_style(self)
        return True

    def advance_for_test(self, frames: int = 1) -> None:
        for _index in range(max(0, int(frames))):
            if self.property("pageTransitionOverlayActive") is True:
                self._advance(1.0 / 60.0)

    def advance_motion_frame(self, *, delta_seconds: float = 1.0 / 60.0) -> None:
        if self.property("pageTransitionOverlayActive") is True:
            self._advance(delta_seconds)

    def timerEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.timerId() != self._timer_id:
            super().timerEvent(event)
            return
        self._advance(1.0 / 33.0)
        event.accept()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().paintEvent(event)
        if self.property("pageTransitionOverlayActive") is not True:
            return
        rect = QRectF(self.rect())
        if rect.width() <= 1 or rect.height() <= 1:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        target_rect = self._snapshot_target_rect(rect)
        if not self._previous_snapshot.isNull() or not self._current_snapshot.isNull():
            if not self._previous_snapshot.isNull() and self._exit_alpha > 0.0:
                painter.setOpacity(self._exit_alpha)
                painter.drawPixmap(target_rect.translated(self._exit_offset_px, 0.0), self._previous_snapshot, QRectF(self._previous_snapshot.rect()))
            if not self._current_snapshot.isNull() and self._enter_alpha > 0.0:
                painter.setOpacity(self._enter_alpha)
                painter.drawPixmap(target_rect.translated(self._enter_offset_px, 0.0), self._current_snapshot, QRectF(self._current_snapshot.rect()))
            painter.setOpacity(1.0)
        else:
            painter.fillRect(rect, QColor(7, 20, 33, int(40 * max(0.0, 1.0 - self._phase))))

        alpha = max(0.0, 1.0 - self._phase)
        sweep_x = target_rect.left() + target_rect.width() * min(1.0, self._phase * 1.15)
        band = QLinearGradient(sweep_x - target_rect.width() * 0.18, target_rect.top(), sweep_x + target_rect.width() * 0.14, target_rect.bottom())
        band.setColorAt(0.0, QColor(60, 185, 255, 0))
        band.setColorAt(0.48, QColor(118, 217, 255, int(22 * alpha)))
        band.setColorAt(0.52, QColor(255, 255, 255, int(14 * alpha)))
        band.setColorAt(1.0, QColor(60, 185, 255, 0))
        painter.fillRect(target_rect, band)
        painter.setPen(QPen(QColor(126, 224, 255, int(42 * alpha)), 1))
        painter.drawRoundedRect(target_rect.adjusted(3, 3, -4, -4), 18, 18)

    def _advance(self, delta_seconds: float = 1.0 / 60.0) -> None:
        self._frame += 1
        self._elapsed_seconds += max(0.0, delta_seconds)
        raw_progress = min(1.0, self._elapsed_seconds / self._duration_seconds)
        self._phase = ease_out_cubic(raw_progress)
        self._apply_crossfade_state(raw_progress=raw_progress)
        self.setProperty("pageTransitionOverlayPhase", round(self._phase, 3))
        self.update()
        if raw_progress >= 1.0:
            self._clear()

    def _apply_crossfade_state(self, *, raw_progress: float) -> None:
        enter = ease_out_cubic(raw_progress)
        exit_ = 1.0 - smoothstep(raw_progress)
        glide = 1.0 - enter
        self._enter_alpha = enter
        self._exit_alpha = exit_
        self._enter_offset_px = self._glide_offset_px * glide
        self._exit_offset_px = -self._glide_offset_px * smoothstep(raw_progress)
        self.setProperty("pageTransitionEnterAlpha", round(self._enter_alpha, 3))
        self.setProperty("pageTransitionExitAlpha", round(self._exit_alpha, 3))
        self.setProperty("pageTransitionEnterOffsetPx", round(self._enter_offset_px, 3))
        self.setProperty("pageTransitionExitOffsetPx", round(self._exit_offset_px, 3))

    def _snapshot_target_rect(self, rect: QRectF) -> QRectF:
        if self._current_snapshot.isNull() and self._previous_snapshot.isNull():
            return rect
        snapshot = self._current_snapshot if not self._current_snapshot.isNull() else self._previous_snapshot
        width = min(rect.width(), max(1, snapshot.width()))
        height = min(rect.height(), max(1, snapshot.height()))
        return QRectF(rect.left() + (rect.width() - width) * 0.5, rect.top() + (rect.height() - height) * 0.5, width, height)

    def _clear(self) -> None:
        if self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = 0
        self._phase = 1.0
        self._enter_alpha = 1.0
        self._exit_alpha = 0.0
        self._enter_offset_px = 0.0
        self._exit_offset_px = 0.0
        self.setProperty("pageTransitionOverlayActive", False)
        self.setProperty("pageTransitionOverlayPhase", 1.0)
        self.setProperty("pageTransitionEnterAlpha", 1.0)
        self.setProperty("pageTransitionExitAlpha", 0.0)
        self.setProperty("pageTransitionEnterOffsetPx", 0.0)
        self.setProperty("pageTransitionExitOffsetPx", 0.0)
        self.setVisible(False)
        refresh_motion_style(self)


class MotionProofRail(QFrame):
    def __init__(
        self,
        *,
        motion_settings: MotionSettings | None = None,
        object_name: str = "liquidMotionProofRail",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setMinimumHeight(24)
        self.setProperty("motionProofRail", True)
        self._motion_settings = motion_settings or current_motion_settings()
        self._timer_id = 0
        self._phase = 0.0
        self._tick_count = 0
        self._external_clock_driven = False
        self.set_motion_settings(self._motion_settings)

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        running = visible_motion_profile(motion_settings).live_easing_preview
        self.setProperty("currentMotionMode", motion_settings.intensity.value)
        self.setProperty("motionProofPreviewRunning", running)
        self.setProperty("motionProofPhase", round(self._phase, 3) if running else 0.0)
        self.setProperty("motionProofTickCount", self._tick_count)
        if running and self.isVisible() and not self._external_clock_driven:
            self._ensure_timer(50 if motion_settings.intensity is MotionIntensity.CINEMATIC else 90)
        else:
            self._stop_timer()
            self._phase = 0.0
        refresh_motion_style(self)

    def advance_for_test(self, frames: int = 1) -> None:
        for _index in range(max(0, int(frames))):
            if visible_motion_profile(self._motion_settings).live_easing_preview:
                self._advance(1.0 / 60.0)

    def set_external_clock_driven(self, enabled: bool) -> None:
        self._external_clock_driven = bool(enabled)
        if self._external_clock_driven:
            self._stop_timer()

    def advance_motion_frame(self, *, delta_seconds: float = 1.0 / 60.0) -> None:
        if visible_motion_profile(self._motion_settings).live_easing_preview:
            self._advance(delta_seconds)

    def timerEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.timerId() != self._timer_id:
            super().timerEvent(event)
            return
        self._advance(1.0 / 50.0)
        event.accept()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        if visible_motion_profile(self._motion_settings).live_easing_preview and not self._timer_id and not self._external_clock_driven:
            self._ensure_timer(50 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 90)

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._stop_timer()
        super().hideEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().paintEvent(event)
        rect = QRectF(self.rect()).adjusted(10, 8, -10, -8)
        if rect.width() <= 1 or rect.height() <= 1:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor(72, 112, 140, 150), 2))
        y = rect.center().y()
        painter.drawLine(rect.left(), y, rect.right(), y)
        running = visible_motion_profile(self._motion_settings).live_easing_preview
        phase = self._phase if running else 0.0
        x = rect.left() + rect.width() * phase
        color = QColor(126, 224, 255, 230 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 185)
        painter.setBrush(color)
        painter.setPen(QPen(QColor(255, 255, 255, 150), 1))
        painter.drawEllipse(QRectF(x - 5, y - 5, 10, 10))

    def _advance(self, delta_seconds: float = 1.0 / 60.0) -> None:
        period = 1.8 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 2.5
        self._phase = _advance_phase(self._phase, delta_seconds, period)
        self._tick_count += 1
        self.setProperty("motionProofPhase", round(self._phase, 3))
        self.setProperty("motionProofTickCount", self._tick_count)
        parent = self.parentWidget()
        if parent is not None and parent.property("motionProofPanel") is True:
            parent.setProperty("motionProofPhase", round(self._phase, 3))
            parent.setProperty("motionProofTickCount", self._tick_count)
            parent.update()
        self.update()

    def _ensure_timer(self, interval_ms: int) -> None:
        if not _timers_allowed():
            self._stop_timer()
            return
        if self._timer_id:
            self.killTimer(self._timer_id)
        self._timer_id = self.startTimer(max(50, int(interval_ms)))

    def _stop_timer(self) -> None:
        if self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = 0


class MotionProofPanel(QFrame):
    def __init__(
        self,
        *,
        motion_settings: MotionSettings | None = None,
        object_name: str = "liquidMotionProofPanel",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("componentRole", "MotionProofPanel")
        self.setProperty("motionProofPanel", True)
        self._motion_settings = motion_settings or current_motion_settings()
        layout = vertical_layout(self, margins=(12, 10, 12, 10), spacing=7)
        header = horizontal_layout(spacing=8)
        title = QLabel("Motion Proof")
        title.setObjectName("liquidMotionProofTitle")
        self._mode_chip = StatusChip("Mode: standard", state_role="info", object_name="liquidMotionProofModeChip")
        header.addWidget(title, 1)
        header.addWidget(self._mode_chip)
        layout.addLayout(header)
        self._summary = QLabel()
        self._summary.setObjectName("liquidMotionProofSummary")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)
        self._rail = MotionProofRail(motion_settings=self._motion_settings)
        layout.addWidget(self._rail)
        self._demo_button = QPushButton("Demo button")
        self._demo_button.setObjectName("liquidMotionProofDemoButton")
        self._demo_button.setProperty("uiRole", "liquidActionButton")
        self._demo_button.setProperty("buttonTone", "primary")
        self._demo_button.setProperty("motionProofDemo", "button")
        self._demo_button.setProperty("liquidCommandAction", True)
        self._demo_button.setProperty("actionKind", "toggle_ui")
        self._demo_button.setProperty("runtimeMutation", False)
        self._demo_button.setAccessibleDescription("Animated UI-only proof control. It does not change runtime state.")
        self._demo_button.setStatusTip("Animated UI-only proof control. Runtime state is unchanged.")
        layout.addWidget(self._demo_button)
        self._demo_card = QFrame()
        self._demo_card.setObjectName("liquidMotionProofDemoCard")
        self._demo_card.setProperty("microinteractionRole", "interactive_card")
        self._demo_card.setProperty("motionProofDemo", "card")
        card_layout = vertical_layout(self._demo_card, margins=(10, 8, 10, 8), spacing=3)
        card_layout.addWidget(QLabel("Demo card"))
        layout.addWidget(self._demo_card)
        self._demo_chip = StatusChip("Demo chip", state_role="info", object_name="liquidMotionProofDemoChip")
        self._demo_chip.setProperty("motionProofDemo", "chip")
        layout.addWidget(self._demo_chip)
        self.set_motion_settings(self._motion_settings)

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        profile = visible_motion_profile(motion_settings)
        self._rail.set_motion_settings(motion_settings)
        self._mode_chip.setText(f"Mode: {motion_settings.intensity.value.title()}")
        self._summary.setText(_proof_summary(profile))
        self.setProperty("currentMotionMode", motion_settings.intensity.value)
        self.setProperty("motionProofPreviewRunning", profile.live_easing_preview)
        self.setProperty("motionProofPhase", self._rail.property("motionProofPhase"))
        self.setProperty("atmosphereControllerExpected", profile.atmosphere_drift)
        self.setProperty("statusPulseControllerExpected", profile.status_breathing)
        self.setProperty("pageTransitionControllerExpected", profile.page_transition_overlay)
        self.setProperty("liveEasingControllerExpected", profile.live_easing_preview)
        self.setProperty("radialAnimationExpected", profile.quick_wheel_animation)
        self.setProperty("routeSweepExpected", profile.route_sweep)
        for key, value in (
            ("motionProofActiveAnimationCount", 0),
            ("motionProofPassiveAnimationCount", 0),
            ("motionProofFpsEstimate", 0.0),
            ("motionProofDemoButtonValue", 0.0),
            ("motionProofDemoCardValue", 0.0),
            ("motionProofDemoChipValue", 0.0),
            ("motionProofRouteSweepPhase", 0.0),
        ):
            if self.property(key) is None:
                self.setProperty(key, value)
        refresh_motion_style(self)

    def advance_for_test(self, frames: int = 1) -> None:
        self._rail.advance_for_test(frames)
        self.setProperty("motionProofPhase", self._rail.property("motionProofPhase"))
        self.setProperty("motionProofTickCount", self._rail.property("motionProofTickCount"))
        self.update()

    def set_external_clock_driven(self, enabled: bool) -> None:
        self._rail.set_external_clock_driven(enabled)

    def advance_motion_frame(self, *, delta_seconds: float = 1.0 / 60.0) -> None:
        self._rail.advance_motion_frame(delta_seconds=delta_seconds)
        self.setProperty("motionProofPhase", self._rail.property("motionProofPhase"))
        self.setProperty("motionProofTickCount", self._rail.property("motionProofTickCount"))

    def demo_widgets(self) -> tuple[QWidget, ...]:
        return (self._demo_button, self._demo_card, self._demo_chip)

    def update_motion_metrics(
        self,
        *,
        fps: float,
        active_count: int,
        passive_count: int,
        atmosphere_phase: float,
        status_phase: float,
        route_phase: float,
        last_page_transition: int,
        last_interaction: int,
    ) -> None:
        self.setProperty("motionProofFpsEstimate", round(float(fps), 1))
        self.setProperty("motionProofActiveAnimationCount", int(active_count))
        self.setProperty("motionProofPassiveAnimationCount", int(passive_count))
        self.setProperty("motionProofAtmospherePhase", round(float(atmosphere_phase), 4))
        self.setProperty("motionProofStatusPulsePhase", round(float(status_phase), 4))
        self.setProperty("motionProofRouteSweepPhase", round(float(route_phase), 4))
        self.setProperty("motionProofLastPageTransitionTimestamp", int(last_page_transition))
        self.setProperty("motionProofLastInteractionAnimationTimestamp", int(last_interaction))
        self.setProperty("motionProofDemoButtonValue", self._demo_button.property("hoverMotionValue") or 0.0)
        self.setProperty("motionProofDemoCardValue", self._demo_card.property("selectionMotionValue") or 0.0)
        self.setProperty("motionProofDemoChipValue", self._demo_chip.property("stateChangeMotionValue") or 0.0)
        self._summary.setText(
            f"{_proof_summary(visible_motion_profile(self._motion_settings))} "
            f"FPS {round(float(fps), 1)} / active {int(active_count)} / passive {int(passive_count)}."
        )
        self.update()


class LiquidStatusBreathController(QObject):
    def __init__(self, *, motion_settings: MotionSettings | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._motion_settings = motion_settings or current_motion_settings()
        self._timer_id = 0
        self._phase = 0.0
        self._tick_count = 0
        self._targets: set[weakref.ReferenceType[QWidget]] = set()
        self._runtime_active = False
        self._external_clock_driven = False
        self.setProperty("statusBreathPhase", 0.0)
        self.set_motion_settings(self._motion_settings)

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        running = visible_motion_profile(motion_settings).status_breathing
        self.setProperty("motionIntensity", motion_settings.intensity.value)
        self.setProperty("statusBreathControllerRunning", running)
        if running and self._runtime_active and not self._external_clock_driven:
            self._ensure_timer(140 if motion_settings.intensity is MotionIntensity.CINEMATIC else 220)
        else:
            self._stop_timer()
            self._phase = 0.0
            self._apply_to_targets(active=False)
        self.setProperty("statusBreathPhase", round(self._phase, 3))

    def set_runtime_active(self, active: bool) -> None:
        self._runtime_active = bool(active)
        running = visible_motion_profile(self._motion_settings).status_breathing
        if self._runtime_active and running and not self._external_clock_driven:
            self._ensure_timer(140 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 220)
        else:
            self._stop_timer()

    def set_external_clock_driven(self, enabled: bool) -> None:
        self._external_clock_driven = bool(enabled)
        if self._external_clock_driven:
            self._stop_timer()

    def register_targets(self, widgets: Iterable[QWidget]) -> None:
        self._targets = {weakref.ref(widget) for widget in widgets if widget is not None and not widget.property("rawDiagnosticSurface")}
        self.setProperty("statusBreathTargetCount", len(self._targets))
        self._apply_to_targets(active=visible_motion_profile(self._motion_settings).status_breathing)

    def advance_for_test(self, frames: int = 1) -> None:
        for _index in range(max(0, int(frames))):
            if visible_motion_profile(self._motion_settings).status_breathing:
                self._advance(1.0 / 60.0)

    def advance_motion_frame(self, *, delta_seconds: float = 1.0 / 60.0) -> None:
        if visible_motion_profile(self._motion_settings).status_breathing:
            self._advance(delta_seconds)

    def timerEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.timerId() != self._timer_id:
            super().timerEvent(event)
            return
        self._advance(1.0 / 60.0)
        event.accept()

    def _advance(self, delta_seconds: float = 1.0 / 60.0) -> None:
        period = 2.9 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 3.7
        self._phase = _advance_phase(self._phase, delta_seconds, period)
        self._tick_count += 1
        self.setProperty("statusBreathPhase", round(self._phase, 3))
        self.setProperty("statusBreathTickCount", self._tick_count)
        self._apply_to_targets(active=True)

    def _apply_to_targets(self, *, active: bool) -> None:
        step = int((self._phase * 4) % 4)
        live_refs: set[weakref.ReferenceType[QWidget]] = set()
        for ref in self._targets:
            widget = ref()
            if widget is None:
                continue
            live_refs.add(ref)
            widget.setProperty("statusBreathActive", bool(active))
            widget.setProperty("statusBreathPhase", round(self._phase, 3) if active else 0.0)
            widget.setProperty("statusBreathStep", step if active else 0)
            widget.setProperty("statusBreathMode", "cinematic" if self._motion_settings.intensity is MotionIntensity.CINEMATIC else "standard")
            refresh_motion_style(widget)
        self._targets = live_refs
        self.setProperty("statusBreathTargetCount", len(self._targets))

    def _ensure_timer(self, interval_ms: int) -> None:
        if not _timers_allowed():
            self._stop_timer()
            return
        if self._timer_id:
            self.killTimer(self._timer_id)
        self._timer_id = self.startTimer(max(120, int(interval_ms)))

    def _stop_timer(self) -> None:
        if self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = 0


class LiquidRouteSweepController(QObject):
    def __init__(self, *, motion_settings: MotionSettings | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._motion_settings = motion_settings or current_motion_settings()
        self._timer_id = 0
        self._phase = 0.0
        self._tick_count = 0
        self._targets: set[weakref.ReferenceType[QWidget]] = set()
        self._runtime_active = False
        self._external_clock_driven = False
        self.setProperty("routeSweepPhase", 0.0)
        self.set_motion_settings(self._motion_settings)

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        running = visible_motion_profile(motion_settings).route_sweep
        self.setProperty("motionIntensity", motion_settings.intensity.value)
        self.setProperty("routeSweepControllerRunning", running)
        if running and self._runtime_active and not self._external_clock_driven:
            self._ensure_timer(90 if motion_settings.intensity is MotionIntensity.CINEMATIC else 150)
        else:
            self._stop_timer()
            self._phase = 0.0
            self._apply_to_targets(active=False)
        self.setProperty("routeSweepPhase", round(self._phase, 3))

    def set_runtime_active(self, active: bool) -> None:
        self._runtime_active = bool(active)
        running = visible_motion_profile(self._motion_settings).route_sweep
        if self._runtime_active and running and not self._external_clock_driven:
            self._ensure_timer(90 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 150)
        else:
            self._stop_timer()

    def set_external_clock_driven(self, enabled: bool) -> None:
        self._external_clock_driven = bool(enabled)
        if self._external_clock_driven:
            self._stop_timer()

    def register_targets(self, widgets: Iterable[QWidget]) -> None:
        self._targets = {weakref.ref(widget) for widget in widgets if widget is not None and widget.property("signalPathMotionAvailable") is True}
        self.setProperty("routeSweepTargetCount", len(self._targets))
        self._apply_to_targets(active=visible_motion_profile(self._motion_settings).route_sweep)

    def advance_for_test(self, frames: int = 1) -> None:
        for _index in range(max(0, int(frames))):
            if visible_motion_profile(self._motion_settings).route_sweep:
                self._advance(1.0 / 60.0)

    def advance_motion_frame(self, *, delta_seconds: float = 1.0 / 60.0) -> None:
        if visible_motion_profile(self._motion_settings).route_sweep:
            self._advance(delta_seconds)

    def timerEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.timerId() != self._timer_id:
            super().timerEvent(event)
            return
        self._advance(1.0 / 60.0)
        event.accept()

    def _advance(self, delta_seconds: float = 1.0 / 60.0) -> None:
        period = 1.5 if self._motion_settings.intensity is MotionIntensity.CINEMATIC else 2.2
        self._phase = _advance_phase(self._phase, delta_seconds, period)
        self._tick_count += 1
        self.setProperty("routeSweepPhase", round(self._phase, 3))
        self.setProperty("routeSweepTickCount", self._tick_count)
        self._apply_to_targets(active=True)

    def _apply_to_targets(self, *, active: bool) -> None:
        step = int((self._phase * 5) % 5)
        live_refs: set[weakref.ReferenceType[QWidget]] = set()
        for ref in self._targets:
            widget = ref()
            if widget is None:
                continue
            live_refs.add(ref)
            widget.setProperty("signalSweepActive", bool(active))
            widget.setProperty("signalSweepPhase", round(self._phase, 3) if active else 0.0)
            widget.setProperty("signalSweepStep", step if active else 0)
            refresh_motion_style(widget)
        self._targets = live_refs
        self.setProperty("routeSweepTargetCount", len(self._targets))

    def _ensure_timer(self, interval_ms: int) -> None:
        if not _timers_allowed():
            self._stop_timer()
            return
        if self._timer_id:
            self.killTimer(self._timer_id)
        self._timer_id = self.startTimer(max(80, int(interval_ms)))

    def _stop_timer(self) -> None:
        if self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = 0


def _proof_summary(profile: VisibleMotionProfile) -> str:
    if profile.intensity is MotionIntensity.OFF:
        return "Optional motion is off. Navigation and status truth remain usable."
    if profile.intensity is MotionIntensity.REDUCED:
        return "Reduced motion keeps static emphasis and suppresses drift, sweep, and proof animation."
    if profile.intensity is MotionIntensity.CINEMATIC:
        return "Cinematic runs atmosphere, status breathing, transitions, route sweep, radial unfold, and live preview motion."
    return "Standard runs restrained status breathing, transitions, route sweep, and live preview motion."
