from __future__ import annotations

from dataclasses import dataclass, field

from shared_core.models.axes import all_axis_definitions


DEFAULT_TUNING_ASSUMPTIONS = (
    "Exact shipped tuning values are unknown. Defaults are conservative, recovered-field-aligned, "
    "and keep output scale/max at 1.0 while applying mild S-curve shaping."
)


@dataclass(frozen=True)
class AxisTuning:
    axis: str
    curve_mode: str = "s"
    curve_strength: float = 0.34
    deadzone: float = 0.03
    anti_deadzone: float = 0.0
    hysteresis: float = 0.0
    output_scale: float = 1.0
    max_output: float = 1.0
    precision_scale: float = 0.65
    invert: bool = False


@dataclass(frozen=True)
class TuningConfig:
    axes: dict[str, AxisTuning] = field(default_factory=dict)
    assumptions: str = DEFAULT_TUNING_ASSUMPTIONS


def default_axis_tuning(axis: str) -> AxisTuning:
    strengths = {
        "Roll": 0.34,
        "Pitch": 0.42,
        "Throttle": 0.10,
        "Yaw": 0.58,
        "Aux 1": 0.20,
        "Aux 2": 0.20,
    }
    deadzones = {
        "Roll": 0.03,
        "Pitch": 0.03,
        "Throttle": 0.02,
        "Yaw": 0.04,
        "Aux 1": 0.03,
        "Aux 2": 0.03,
    }
    return AxisTuning(
        axis=axis,
        curve_strength=strengths.get(axis, 0.34),
        deadzone=deadzones.get(axis, 0.03),
    )


def default_tuning_config() -> TuningConfig:
    return TuningConfig(
        axes={axis.axis_id.value: default_axis_tuning(axis.display_name) for axis in all_axis_definitions()}
    )
