from __future__ import annotations

from dataclasses import dataclass

from v3_app.overlay.overlay_config import LiveOverlayConfig
from v3_app.overlay.telemetry_buffer import OverlayTelemetrySample


@dataclass(frozen=True)
class OverlayTraceSeries:
    axis: str
    color: str
    points: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class OverlayTraceSet:
    source: str
    history_seconds: float
    series: tuple[OverlayTraceSeries, ...]


def build_overlay_traces(config: LiveOverlayConfig, samples: tuple[OverlayTelemetrySample, ...]) -> OverlayTraceSet:
    if not samples:
        return OverlayTraceSet(source=config.source, history_seconds=config.history_seconds, series=())
    latest_timestamp = samples[-1].timestamp
    source = samples[-1].source or config.source
    series: list[OverlayTraceSeries] = []
    for axis, axis_config in config.axes.items():
        if not axis_config.include:
            continue
        points = tuple(
            (round(sample.timestamp - latest_timestamp, 3), _clamp(sample.axes.get(axis, 0.0)))
            for sample in samples
        )
        series.append(OverlayTraceSeries(axis=axis, color=axis_config.color, points=points))
    return OverlayTraceSet(source=source, history_seconds=config.history_seconds, series=tuple(series))


def _clamp(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(-1.0, min(1.0, number))
