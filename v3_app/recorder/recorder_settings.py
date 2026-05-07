from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from shared_core.models.runtime import AXIS_NAMES
from v3_app.overlay.axis_colors import color_for_axis
from v3_app.overlay.overlay_config import OverlayAxisConfig


def _default_destination() -> Path:
    return Path.home() / "Videos" / "hotas_recordings_v3"


def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = minimum
    return max(minimum, min(maximum, number))


def _clamp_float(value: Any, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = minimum
    return round(max(minimum, min(maximum, number)), 2)


@dataclass(frozen=True)
class FlightRecorderSettings:
    destination_folder: Path
    length_seconds: int
    frame_rate_fps: int
    history_seconds: float
    overlay_source: str
    capture_source: str
    display_label: str
    hotkey: str
    record_cursor: bool
    trigger_mode: str
    hotkey_registered: bool
    capture_backend_available: bool
    encoder_available: bool
    compositor_available: bool
    hindsight_video_buffer_available: bool
    axes: dict[str, OverlayAxisConfig]

    @classmethod
    def defaults(cls) -> "FlightRecorderSettings":
        return cls(
            destination_folder=_default_destination(),
            length_seconds=20,
            frame_rate_fps=30,
            history_seconds=6.0,
            overlay_source="Final output",
            capture_source="Current display",
            display_label="Current display",
            hotkey="Ctrl+Shift+F10",
            record_cursor=True,
            trigger_mode="Press to save previous interval",
            hotkey_registered=False,
            capture_backend_available=False,
            encoder_available=False,
            compositor_available=False,
            hindsight_video_buffer_available=False,
            axes={axis: OverlayAxisConfig(include=True, color=color_for_axis(axis)) for axis in AXIS_NAMES},
        )

    def restore_defaults(self) -> "FlightRecorderSettings":
        return self.defaults()

    def to_dict(self) -> dict[str, object]:
        return {
            "destination_folder": str(self.destination_folder),
            "length_seconds": self.length_seconds,
            "frame_rate_fps": self.frame_rate_fps,
            "history_seconds": self.history_seconds,
            "overlay_source": self.overlay_source,
            "capture_source": self.capture_source,
            "display_label": self.display_label,
            "hotkey": self.hotkey,
            "record_cursor": self.record_cursor,
            "trigger_mode": self.trigger_mode,
            "hotkey_registered": self.hotkey_registered,
            "capture_backend_available": self.capture_backend_available,
            "encoder_available": self.encoder_available,
            "compositor_available": self.compositor_available,
            "hindsight_video_buffer_available": self.hindsight_video_buffer_available,
            "axes": {axis: config.to_dict() for axis, config in self.axes.items()},
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "FlightRecorderSettings":
        defaults = cls.defaults()
        raw_axes = payload.get("axes")
        axes_payload = raw_axes if isinstance(raw_axes, Mapping) else {}
        axes = {
            axis: OverlayAxisConfig.from_dict(axis, axes_payload.get(axis) if isinstance(axes_payload.get(axis), Mapping) else None)
            for axis in AXIS_NAMES
        }
        destination = payload.get("destination_folder")
        return cls(
            destination_folder=Path(str(destination or defaults.destination_folder)),
            length_seconds=_clamp_int(payload.get("length_seconds", defaults.length_seconds), 1, 120),
            frame_rate_fps=_clamp_int(payload.get("frame_rate_fps", defaults.frame_rate_fps), 1, 120),
            history_seconds=_clamp_float(payload.get("history_seconds", defaults.history_seconds), 1.0, 60.0),
            overlay_source=str(payload.get("overlay_source") or defaults.overlay_source),
            capture_source=str(payload.get("capture_source") or defaults.capture_source),
            display_label=str(payload.get("display_label") or defaults.display_label),
            hotkey=str(payload.get("hotkey") or defaults.hotkey),
            record_cursor=bool(payload.get("record_cursor", defaults.record_cursor)),
            trigger_mode=str(payload.get("trigger_mode") or defaults.trigger_mode),
            hotkey_registered=bool(payload.get("hotkey_registered", defaults.hotkey_registered)),
            capture_backend_available=bool(payload.get("capture_backend_available", defaults.capture_backend_available)),
            encoder_available=bool(payload.get("encoder_available", defaults.encoder_available)),
            compositor_available=bool(payload.get("compositor_available", defaults.compositor_available)),
            hindsight_video_buffer_available=bool(
                payload.get("hindsight_video_buffer_available", defaults.hindsight_video_buffer_available)
            ),
            axes=axes,
        )
