from __future__ import annotations

from dataclasses import dataclass, field

from shared_core.models.axes import all_axis_definitions


DEFAULT_COMBAT_ASSUMPTIONS = (
    "Exact shipped combat-profile values are unknown. Defaults are conservative placeholders "
    "that reduce authority slightly during combat/zoom without implementing combat logic yet."
)


@dataclass(frozen=True)
class AxisCombatProfile:
    axis: str
    combat_curve: float = 0.45
    combat_scale: float = 0.85
    combat_center_alpha: float = 0.25
    combat_edge_alpha: float = 0.60
    combat_same_slew: float = 0.80
    combat_reverse_slew: float = 0.50


@dataclass(frozen=True)
class CombatProfileConfig:
    axes: dict[str, AxisCombatProfile] = field(default_factory=dict)
    assumptions: str = DEFAULT_COMBAT_ASSUMPTIONS


def default_axis_combat_profile(axis: str) -> AxisCombatProfile:
    if axis == "Throttle":
        return AxisCombatProfile(axis=axis, combat_curve=0.15, combat_scale=1.0, combat_center_alpha=0.55, combat_edge_alpha=0.80, combat_same_slew=1.0, combat_reverse_slew=0.85)
    if axis == "Yaw":
        return AxisCombatProfile(axis=axis, combat_curve=0.60, combat_scale=0.75, combat_center_alpha=0.20, combat_edge_alpha=0.55, combat_same_slew=0.65, combat_reverse_slew=0.40)
    if axis == "Pitch":
        return AxisCombatProfile(axis=axis, combat_curve=0.50, combat_scale=0.80)
    return AxisCombatProfile(axis=axis)


def default_combat_profile_config() -> CombatProfileConfig:
    return CombatProfileConfig(
        axes={axis.axis_id.value: default_axis_combat_profile(axis.display_name) for axis in all_axis_definitions()}
    )
