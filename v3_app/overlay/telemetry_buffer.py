from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from shared_core.models.runtime import AXIS_NAMES


@dataclass(frozen=True)
class OverlayTelemetrySample:
    timestamp: float
    axes: Mapping[str, float]
    source: str


class OverlayTelemetryBuffer:
    def __init__(self, *, history_seconds: float) -> None:
        self.history_seconds = max(0.5, float(history_seconds))
        self._samples: list[OverlayTelemetrySample] = []

    def append(self, sample: OverlayTelemetrySample) -> None:
        normalized = OverlayTelemetrySample(
            timestamp=float(sample.timestamp),
            axes={axis: _clamp(sample.axes.get(axis, 0.0)) for axis in AXIS_NAMES},
            source=sample.source,
        )
        self._samples.append(normalized)
        self.trim(now=normalized.timestamp)

    def trim(self, *, now: float) -> None:
        cutoff = float(now) - self.history_seconds
        self._samples = [sample for sample in self._samples if sample.timestamp >= cutoff]

    def samples(self) -> tuple[OverlayTelemetrySample, ...]:
        return tuple(self._samples)


def _clamp(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(-1.0, min(1.0, number))
