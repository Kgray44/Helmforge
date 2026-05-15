from __future__ import annotations

from collections import deque
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
        self._samples: deque[OverlayTelemetrySample] = deque()
        self._samples_cache: tuple[OverlayTelemetrySample, ...] = ()
        self._version = 0
        self._cache_version = -1

    def append(self, sample: OverlayTelemetrySample) -> None:
        normalized = OverlayTelemetrySample(
            timestamp=float(sample.timestamp),
            axes={axis: _clamp(sample.axes.get(axis, 0.0)) for axis in AXIS_NAMES},
            source=sample.source,
        )
        self._samples.append(normalized)
        self._version += 1
        self.trim(now=normalized.timestamp)

    def trim(self, *, now: float) -> None:
        cutoff = float(now) - self.history_seconds
        changed = False
        while self._samples and self._samples[0].timestamp < cutoff:
            self._samples.popleft()
            changed = True
        if changed:
            self._version += 1

    def samples(self) -> tuple[OverlayTelemetrySample, ...]:
        if self._cache_version != self._version:
            self._samples_cache = tuple(self._samples)
            self._cache_version = self._version
        return self._samples_cache


def _clamp(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(-1.0, min(1.0, number))
