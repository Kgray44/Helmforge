from __future__ import annotations


def clamp(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


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
    limit = abs(max_output)
    if limit <= 0.0:
        return 0.0
    return clamp(value * output_scale, -limit, limit)


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

