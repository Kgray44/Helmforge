from __future__ import annotations

from dataclasses import dataclass, field

from shared_core.models.axes import all_axis_definitions


DEFAULT_FILTERING_ASSUMPTIONS = (
    "Exact shipped filtering values are unknown. Defaults are mild and simulation-safe: "
    "more smoothing near center, lighter smoothing at the edge, and bounded slew placeholders."
)


@dataclass(frozen=True)
class AxisFiltering:
    axis: str
    center_alpha: float = 0.35
    edge_alpha: float = 0.70
    same_slew_limit: float = 1.0
    reverse_slew_limit: float = 0.65


@dataclass(frozen=True)
class FilteringConfig:
    axes: dict[str, AxisFiltering] = field(default_factory=dict)
    assumptions: str = DEFAULT_FILTERING_ASSUMPTIONS


def default_axis_filtering(axis: str) -> AxisFiltering:
    if axis == "Throttle":
        return AxisFiltering(axis=axis, center_alpha=0.55, edge_alpha=0.80, reverse_slew_limit=0.80)
    if axis == "Yaw":
        return AxisFiltering(axis=axis, center_alpha=0.25, edge_alpha=0.60, reverse_slew_limit=0.50)
    return AxisFiltering(axis=axis)


def default_filtering_config() -> FilteringConfig:
    return FilteringConfig(
        axes={axis.axis_id.value: default_axis_filtering(axis.display_name) for axis in all_axis_definitions()}
    )
