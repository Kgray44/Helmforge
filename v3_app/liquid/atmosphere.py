from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QWidget

from v3_app.liquid.glass import refresh_style
from v3_app.liquid.motion import MotionIntensity, MotionSettings, current_motion_settings


@dataclass(frozen=True)
class AtmosphereSpec:
    enabled: bool
    animated: bool
    mode: str
    cadence_ms: int
    shimmer: bool = False
    glare: bool = False
    high_frequency: bool = False
    uses_blur: bool = False
    uses_distortion: bool = False


@dataclass(frozen=True)
class ModeAccent:
    accent_id: str
    role: str
    meaning: str


_MODE_ACCENTS: dict[str, ModeAccent] = {
    "preflight": ModeAccent("preflight", "amber_cyan", "readiness_truth"),
    "mapping": ModeAccent("mapping", "cyan_blue", "mapping_intent"),
    "tuning": ModeAccent("tuning", "teal_violet", "response_shaping"),
    "analysis": ModeAccent("analysis", "green_cyan", "live_truth"),
    "recorder": ModeAccent("recorder", "red_amber", "capture_truth"),
    "support": ModeAccent("support", "blue_gray", "diagnostic_truth"),
    "helm": ModeAccent("helm", "teal_green", "draft_review"),
}
_FALLBACK_ACCENT = ModeAccent("support", "blue_gray", "diagnostic_truth")


def atmosphere_spec(
    motion_settings: MotionSettings | None = None,
    *,
    optional_enabled: bool = True,
) -> AtmosphereSpec:
    settings = motion_settings or current_motion_settings()
    if not optional_enabled or settings.intensity is MotionIntensity.OFF:
        return AtmosphereSpec(
            enabled=False,
            animated=False,
            mode="off",
            cadence_ms=0,
        )
    if settings.intensity is MotionIntensity.REDUCED:
        return AtmosphereSpec(
            enabled=True,
            animated=False,
            mode="static_reduced",
            cadence_ms=0,
        )
    if settings.intensity is MotionIntensity.CINEMATIC:
        return AtmosphereSpec(
            enabled=True,
            animated=True,
            mode="slow_drift",
            cadence_ms=2400,
            shimmer=True,
            glare=False,
        )
    return AtmosphereSpec(
        enabled=True,
        animated=False,
        mode="static_accent",
        cadence_ms=0,
    )


def mode_accent(mode_id: str | None) -> ModeAccent:
    return _MODE_ACCENTS.get(str(mode_id or ""), _FALLBACK_ACCENT)


def apply_atmosphere(
    widget: QWidget,
    *,
    mode_id: str | None,
    motion_settings: MotionSettings | None = None,
    optional_enabled: bool = True,
    diagnostic_surface: bool = False,
) -> AtmosphereSpec:
    spec = atmosphere_spec(motion_settings, optional_enabled=optional_enabled and not diagnostic_surface)
    accent = mode_accent(mode_id)
    widget.setProperty("atmosphereEnabled", spec.enabled)
    widget.setProperty("atmosphereAnimated", spec.animated)
    widget.setProperty("atmosphereMode", spec.mode)
    widget.setProperty("atmosphereCadenceMs", spec.cadence_ms)
    widget.setProperty("atmosphereShimmer", spec.shimmer)
    widget.setProperty("atmosphereGlare", spec.glare)
    widget.setProperty("atmosphereHighFrequency", spec.high_frequency)
    widget.setProperty("atmosphereUsesBlur", spec.uses_blur)
    widget.setProperty("atmosphereUsesDistortion", spec.uses_distortion)
    widget.setProperty("atmosphereRuntimeMutation", False)
    widget.setProperty("modeAccent", accent.accent_id)
    widget.setProperty("modeAccentRole", accent.role)
    widget.setProperty("modeAccentMeaning", accent.meaning)
    refresh_style(widget)
    return spec
