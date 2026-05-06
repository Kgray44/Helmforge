from __future__ import annotations

from dataclasses import dataclass

from shared_core.math.curves import clamp
from shared_core.models.filtering import AxisFiltering


@dataclass(frozen=True)
class FilterState:
    previous_output: float = 0.0


@dataclass(frozen=True)
class FilterStepResult:
    output: float
    state: FilterState
    diagnostics: dict[str, float | str | bool]


def _alpha_for_target(target_value: float, settings: AxisFiltering) -> tuple[float, str]:
    magnitude = abs(clamp(target_value))
    center = clamp(settings.center_alpha, 0.0, 1.0)
    edge = clamp(settings.edge_alpha, 0.0, 1.0)
    alpha = center + (edge - center) * magnitude
    region = "center" if magnitude < 0.5 else "edge"
    return alpha, region


def _is_reverse(previous: float, delta: float) -> bool:
    if previous == 0.0 or delta == 0.0:
        return False
    return (previous > 0.0 and delta < 0.0) or (previous < 0.0 and delta > 0.0)


def step_filter(
    *,
    target_value: float,
    state: FilterState,
    settings: AxisFiltering,
) -> FilterStepResult:
    target = clamp(target_value)
    previous = clamp(state.previous_output)
    alpha, region = _alpha_for_target(target, settings)
    smoothed = previous + (target - previous) * alpha
    requested_delta = smoothed - previous

    reverse = _is_reverse(previous, requested_delta)
    limit = settings.reverse_slew_limit if reverse else settings.same_slew_limit
    limit = max(0.0, abs(limit))

    if limit == 0.0:
        limited_delta = 0.0
        slew_limited = requested_delta != 0.0
    elif abs(requested_delta) > limit:
        limited_delta = limit if requested_delta > 0.0 else -limit
        slew_limited = True
    else:
        limited_delta = requested_delta
        slew_limited = False

    output = clamp(previous + limited_delta)
    diagnostics: dict[str, float | str | bool] = {
        "alpha": alpha,
        "alpha_region": region,
        "slew_path": "reverse-direction" if reverse else "same-direction",
        "slew_limit": limit,
        "slew_limited": slew_limited,
        "target": target,
        "smoothed": smoothed,
        "previous_output": previous,
    }
    return FilterStepResult(output=output, state=FilterState(previous_output=output), diagnostics=diagnostics)

