from __future__ import annotations

from shared_core.models.runtime import AXIS_NAMES
from v3_app.overlay.telemetry_buffer import OverlayTelemetrySample


class RecorderTelemetryHindsightBuffer:
    def __init__(self, *, history_seconds: float) -> None:
        self.history_seconds = max(1.0, float(history_seconds))
        self._samples: list[OverlayTelemetrySample] = []

    @property
    def status_label(self) -> str:
        return "Telemetry hindsight buffer available"

    @property
    def video_hindsight_status(self) -> str:
        return "Video hindsight buffering unavailable"

    def append(self, *, timestamp: float, axes: dict[str, float], source: str) -> None:
        sample = OverlayTelemetrySample(
            timestamp=float(timestamp),
            axes={axis: _clamp(axes.get(axis, 0.0)) for axis in AXIS_NAMES},
            source=source,
        )
        self._samples.append(sample)
        self.trim(now=sample.timestamp)

    def trim(self, *, now: float) -> None:
        cutoff = float(now) - self.history_seconds
        self._samples = [sample for sample in self._samples if sample.timestamp >= cutoff]

    def samples(self) -> tuple[OverlayTelemetrySample, ...]:
        return tuple(self._samples)

    def previous_seconds(self, *, seconds: float, now: float) -> tuple[OverlayTelemetrySample, ...]:
        cutoff = float(now) - max(0.0, float(seconds))
        return tuple(sample for sample in self._samples if cutoff <= sample.timestamp <= float(now))


def _clamp(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(-1.0, min(1.0, number))
