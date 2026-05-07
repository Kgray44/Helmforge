from __future__ import annotations

from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class AxisNormalizationResult:
    raw_value: object
    normalized_value: float
    valid: bool = True
    warning: str | None = None


def normalize_axis_value(
    raw_value: object,
    *,
    raw_min: float | None = None,
    raw_max: float | None = None,
    center: float | None = None,
    already_normalized: bool = False,
    one_sided: bool = False,
) -> AxisNormalizationResult:
    if raw_value is None:
        return AxisNormalizationResult(raw_value=raw_value, normalized_value=0.0, valid=False, warning="Raw axis value is missing.")
    if not isinstance(raw_value, Real):
        return AxisNormalizationResult(raw_value=raw_value, normalized_value=0.0, valid=False, warning="Raw axis value is invalid.")

    value = float(raw_value)
    if already_normalized:
        return AxisNormalizationResult(raw_value=raw_value, normalized_value=_clamp(value))

    if raw_min is None or raw_max is None:
        return AxisNormalizationResult(raw_value=raw_value, normalized_value=_clamp(value), warning="Axis range unavailable; value was clamped as normalized.")

    low = float(raw_min)
    high = float(raw_max)
    if high <= low:
        return AxisNormalizationResult(raw_value=raw_value, normalized_value=0.0, valid=False, warning="Axis range is invalid.")

    clamped_raw = min(max(value, low), high)
    if one_sided:
        normalized = (clamped_raw - low) / (high - low)
        return AxisNormalizationResult(raw_value=raw_value, normalized_value=_clamp(normalized))

    axis_center = float(center) if center is not None else (low + high) / 2.0
    if clamped_raw >= axis_center:
        span = high - axis_center
        normalized = 0.0 if span <= 0 else (clamped_raw - axis_center) / span
    else:
        span = axis_center - low
        normalized = 0.0 if span <= 0 else -((axis_center - clamped_raw) / span)
    return AxisNormalizationResult(raw_value=raw_value, normalized_value=_clamp(normalized))


def _clamp(value: float) -> float:
    if value < -1.0:
        return -1.0
    if value > 1.0:
        return 1.0
    return round(value, 6)
