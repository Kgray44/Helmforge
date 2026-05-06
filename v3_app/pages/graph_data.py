from __future__ import annotations

from dataclasses import dataclass

from shared_core.math.curves import apply_output_limits, linear_reference_points, s_curve_centered
from shared_core.math.deadzone import apply_center_deadzone
from shared_core.math.filtering import FilterState, step_filter
from shared_core.math.pipeline import WorkspaceSignalPipeline
from shared_core.math.stack import ModeState
from shared_core.models.combat import AxisCombatProfile
from shared_core.models.filtering import AxisFiltering
from shared_core.models.runtime import AXIS_NAMES
from shared_core.models.tuning import AxisTuning
from shared_core.models.workspace import WorkspaceConfig


PointSeries = tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class BaseResponsePreviewData:
    linear: PointSeries
    adjusted: PointSeries


@dataclass(frozen=True)
class FilteringPreviewData:
    raw: PointSeries
    filtered: PointSeries


@dataclass(frozen=True)
class CombatPreviewData:
    linear: PointSeries
    baseline: PointSeries
    combat: PointSeries


@dataclass(frozen=True)
class EffectiveResponseStackGraphData:
    linear: PointSeries
    effective: PointSeries
    live_marker: tuple[float, float]


def _sample_values(sample_count: int = 101) -> tuple[float, ...]:
    if sample_count <= 1:
        return (0.0,)
    return tuple(-1.0 + (2.0 * index / (sample_count - 1)) for index in range(sample_count))


def base_response_preview_data(tuning: AxisTuning, *, sample_count: int = 101) -> BaseResponsePreviewData:
    linear = linear_reference_points(sample_count=sample_count)
    adjusted: list[tuple[float, float]] = []
    for raw in _sample_values(sample_count):
        centered = apply_center_deadzone(
            -raw if tuning.invert else raw,
            deadzone=tuning.deadzone,
            anti_deadzone=tuning.anti_deadzone,
            hysteresis=tuning.hysteresis,
        ).output
        curved = s_curve_centered(centered, curve_strength=tuning.curve_strength)
        limited = apply_output_limits(
            curved,
            output_scale=tuning.output_scale,
            max_output=tuning.max_output,
        )
        adjusted.append((raw, limited))
    return BaseResponsePreviewData(linear=linear, adjusted=tuple(adjusted))


def filtering_step_preview_data(settings: AxisFiltering) -> FilteringPreviewData:
    targets = (
        *(0.0 for _ in range(12)),
        *(0.70 for _ in range(28)),
        *(-0.40 for _ in range(28)),
        *(0.14 for _ in range(24)),
    )
    state = FilterState()
    raw: list[tuple[float, float]] = []
    filtered: list[tuple[float, float]] = []
    for index, target in enumerate(targets):
        x = index / 60.0
        result = step_filter(target_value=target, state=state, settings=settings)
        state = result.state
        raw.append((x, target))
        filtered.append((x, result.output))
    return FilteringPreviewData(raw=tuple(raw), filtered=tuple(filtered))


def combat_response_preview_data(
    tuning: AxisTuning,
    combat: AxisCombatProfile,
    *,
    sample_count: int = 101,
) -> CombatPreviewData:
    linear = linear_reference_points(sample_count=sample_count)
    baseline: list[tuple[float, float]] = []
    combat_points: list[tuple[float, float]] = []
    base = base_response_preview_data(tuning, sample_count=sample_count).adjusted
    for raw, base_y in base:
        combat_y = s_curve_centered(base_y, curve_strength=combat.combat_curve) * combat.combat_scale
        combat_points.append((raw, apply_output_limits(combat_y, output_scale=1.0, max_output=tuning.max_output)))
        baseline.append((raw, base_y))
    return CombatPreviewData(linear=linear, baseline=tuple(baseline), combat=tuple(combat_points))


def effective_response_stack_graph_data(
    workspace: WorkspaceConfig,
    selected_axis: str,
    *,
    raw_axis_values: dict[str, float] | None = None,
    sample_count: int = 101,
) -> EffectiveResponseStackGraphData:
    base_raw_values = {axis: 0.0 for axis in AXIS_NAMES}
    if raw_axis_values:
        base_raw_values.update({axis: float(value) for axis, value in raw_axis_values.items()})

    linear = linear_reference_points(sample_count=sample_count)
    effective: list[tuple[float, float]] = []
    for raw in _sample_values(sample_count):
        sample_values = dict(base_raw_values)
        sample_values[selected_axis] = raw
        pipeline = WorkspaceSignalPipeline(workspace)
        result = pipeline.process(
            sample_values,
            mode_state=ModeState(),
            state=pipeline.initial_state(),
        )
        effective.append((raw, result.final_output_values[selected_axis]))

    live_x = float(base_raw_values.get(selected_axis, 0.0))
    live_pipeline = WorkspaceSignalPipeline(workspace)
    live_result = live_pipeline.process(
        base_raw_values,
        mode_state=ModeState(),
        state=live_pipeline.initial_state(),
    )
    live_marker = (live_x, live_result.final_output_values[selected_axis])

    return EffectiveResponseStackGraphData(
        linear=linear,
        effective=tuple(effective),
        live_marker=live_marker,
    )
