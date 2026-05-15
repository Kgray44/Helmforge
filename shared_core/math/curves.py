from __future__ import annotations

import math


def finite_float(value: object, default: float = 0.0) -> float:
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if not math.isfinite(numeric):
        return default
    return numeric


def clamp(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    safe_lower = finite_float(lower, -1.0)
    safe_upper = finite_float(upper, 1.0)
    if safe_lower > safe_upper:
        safe_lower, safe_upper = safe_upper, safe_lower
    safe_value = finite_float(value, 0.0)
    return max(safe_lower, min(safe_upper, safe_value))


def s_curve_centered(value: float, *, curve_strength: float) -> float:
    """Odd-symmetric cubic blend: y = (1-k)x + kx^3."""
    x = clamp(value)
    k = clamp(curve_strength, 0.0, 1.0)
    return (1.0 - k) * x + k * (x**3)


def one_sided_curve(value: float, *, curve_strength: float) -> float:
    """One-sided/J-curve helper for future throttle work; input/output are clamped to 0..1."""
    x = clamp(value, 0.0, 1.0)
    k = clamp(curve_strength, 0.0, 1.0)
    return (1.0 - k) * x + k * (x**3)


def apply_output_limits(value: float, *, output_scale: float, max_output: float) -> float:
    limit = abs(finite_float(max_output, 1.0))
    if limit <= 0.0:
        return 0.0
    return clamp(finite_float(value, 0.0) * finite_float(output_scale, 1.0), -limit, limit)


def apply_centered_curve(
    value: float,
    *,
    curve_strength: float,
    output_scale: float = 1.0,
    max_output: float = 1.0,
) -> float:
    curved = s_curve_centered(value, curve_strength=curve_strength)
    return apply_output_limits(curved, output_scale=output_scale, max_output=max_output)


def linear_reference_points(
    *,
    sample_count: int = 101,
    minimum: float = -1.0,
    maximum: float = 1.0,
) -> tuple[tuple[float, float], ...]:
    """Return a true y=x reference line that never reuses transformed curve data."""
    if sample_count <= 1:
        return ((minimum, minimum),)
    step = (maximum - minimum) / (sample_count - 1)
    return tuple((minimum + step * index, minimum + step * index) for index in range(sample_count))
