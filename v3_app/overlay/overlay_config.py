from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from shared_core.models.runtime import AXIS_NAMES
from v3_app.overlay.axis_colors import color_for_axis


def _clamp_float(value: Any, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = minimum
    return round(max(minimum, min(maximum, number)), 2)


def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = minimum
    return max(minimum, min(maximum, number))


@dataclass(frozen=True)
class OverlayAxisConfig:
    include: bool
    color: str

    def to_dict(self) -> dict[str, object]:
        return {"include": self.include, "color": self.color}

    @classmethod
    def from_dict(cls, axis_name: str, payload: Mapping[str, object] | None = None) -> "OverlayAxisConfig":
        data = payload or {}
        color = str(data.get("color") or color_for_axis(axis_name))
        return cls(include=bool(data.get("include", True)), color=color)


@dataclass(frozen=True)
class LiveOverlayConfig:
    preset: str
    visible: bool
    source: str
    history_seconds: float
    position: str
    margin_px: int
    attach_mode: str
    width: str
    height: float
    display_label: str
    opacity: float
    background: float
    line_thickness: float
    show_legend: bool
    show_live_values: bool
    auto_hide_when_target_loses_focus: bool
    always_on_top: bool
    click_through: bool
    click_through_supported: str
    fps_cap: int
    toggle_hotkey: str
    hotkey_registered: bool
    axes: dict[str, OverlayAxisConfig]

    @classmethod
    def defaults(cls) -> "LiveOverlayConfig":
        return cls(
            preset="Custom",
            visible=False,
            source="Final output",
            history_seconds=7.5,
            position="Bottom strip",
            margin_px=18,
            attach_mode="Attach to display",
            width="Standard",
            height=0.6,
            display_label="Current display",
            opacity=0.66,
            background=0.82,
            line_thickness=2.8,
            show_legend=True,
            show_live_values=True,
            auto_hide_when_target_loses_focus=False,
            always_on_top=True,
            click_through=False,
            click_through_supported="unknown",
            fps_cap=60,
            toggle_hotkey="Ctrl+Shift+F9",
            hotkey_registered=False,
            axes={axis: OverlayAxisConfig(include=True, color=color_for_axis(axis)) for axis in AXIS_NAMES},
        )

    def restore_defaults(self) -> "LiveOverlayConfig":
        return self.defaults()

    def to_dict(self) -> dict[str, object]:
        return {
            "preset": self.preset,
            "visible": self.visible,
            "source": self.source,
            "history_seconds": self.history_seconds,
            "position": self.position,
            "margin_px": self.margin_px,
            "attach_mode": self.attach_mode,
            "width": self.width,
            "height": self.height,
            "display_label": self.display_label,
            "opacity": self.opacity,
            "background": self.background,
            "line_thickness": self.line_thickness,
            "show_legend": self.show_legend,
            "show_live_values": self.show_live_values,
            "auto_hide_when_target_loses_focus": self.auto_hide_when_target_loses_focus,
            "always_on_top": self.always_on_top,
            "click_through": self.click_through,
            "click_through_supported": self.click_through_supported,
            "fps_cap": self.fps_cap,
            "toggle_hotkey": self.toggle_hotkey,
            "hotkey_registered": self.hotkey_registered,
            "axes": {axis: config.to_dict() for axis, config in self.axes.items()},
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_json(cls, payload: str) -> "LiveOverlayConfig":
        return cls.from_dict(json.loads(payload))

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "LiveOverlayConfig":
        defaults = cls.defaults()
        raw_axes = payload.get("axes")
        axes_payload = raw_axes if isinstance(raw_axes, Mapping) else {}
        axes = {
            axis: OverlayAxisConfig.from_dict(axis, axes_payload.get(axis) if isinstance(axes_payload.get(axis), Mapping) else None)
            for axis in AXIS_NAMES
        }
        return cls(
            preset=str(payload.get("preset") or defaults.preset),
            visible=bool(payload.get("visible", defaults.visible)),
            source=str(payload.get("source") or defaults.source),
            history_seconds=_clamp_float(payload.get("history_seconds", defaults.history_seconds), 0.5, 60.0),
            position=str(payload.get("position") or defaults.position),
            margin_px=_clamp_int(payload.get("margin_px", defaults.margin_px), 0, 96),
            attach_mode=str(payload.get("attach_mode") or defaults.attach_mode),
            width=str(payload.get("width") or defaults.width),
            height=_clamp_float(payload.get("height", defaults.height), 0.2, 1.0),
            display_label=str(payload.get("display_label") or defaults.display_label),
            opacity=_clamp_float(payload.get("opacity", defaults.opacity), 0.0, 1.0),
            background=_clamp_float(payload.get("background", defaults.background), 0.0, 1.0),
            line_thickness=_clamp_float(payload.get("line_thickness", defaults.line_thickness), 1.0, 8.0),
            show_legend=bool(payload.get("show_legend", defaults.show_legend)),
            show_live_values=bool(payload.get("show_live_values", defaults.show_live_values)),
            auto_hide_when_target_loses_focus=bool(
                payload.get("auto_hide_when_target_loses_focus", defaults.auto_hide_when_target_loses_focus)
            ),
            always_on_top=bool(payload.get("always_on_top", defaults.always_on_top)),
            click_through=bool(payload.get("click_through", defaults.click_through)),
            click_through_supported=str(payload.get("click_through_supported") or defaults.click_through_supported),
            fps_cap=_clamp_int(payload.get("fps_cap", defaults.fps_cap), 15, 144),
            toggle_hotkey=str(payload.get("toggle_hotkey") or defaults.toggle_hotkey),
            hotkey_registered=bool(payload.get("hotkey_registered", defaults.hotkey_registered)),
            axes=axes,
        )
