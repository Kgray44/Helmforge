from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AxisId(str, Enum):
    ROLL = "roll"
    PITCH = "pitch"
    THROTTLE = "throttle"
    YAW = "yaw"
    AUX_1 = "aux_1"
    AUX_2 = "aux_2"


@dataclass(frozen=True)
class AxisDefinition:
    axis_id: AxisId
    display_name: str
    order: int


_AXES = (
    AxisDefinition(AxisId.ROLL, "Roll", 0),
    AxisDefinition(AxisId.PITCH, "Pitch", 1),
    AxisDefinition(AxisId.THROTTLE, "Throttle", 2),
    AxisDefinition(AxisId.YAW, "Yaw", 3),
    AxisDefinition(AxisId.AUX_1, "Aux 1", 4),
    AxisDefinition(AxisId.AUX_2, "Aux 2", 5),
)

AXIS_DISPLAY_NAMES = tuple(axis.display_name for axis in _AXES)
AXIS_IDS = tuple(axis.axis_id for axis in _AXES)


def all_axis_definitions() -> tuple[AxisDefinition, ...]:
    return _AXES


def all_axis_ids() -> tuple[AxisId, ...]:
    return AXIS_IDS


def axis_by_id(axis_id: AxisId | str) -> AxisDefinition:
    normalized = AxisId(axis_id)
    for axis in _AXES:
        if axis.axis_id is normalized:
            return axis
    raise KeyError(f"Unknown axis id: {axis_id}")


def axis_by_name(name: str) -> AxisDefinition:
    normalized = name.strip().casefold().replace("-", " ").replace("_", " ")
    for axis in _AXES:
        if axis.display_name.casefold() == normalized:
            return axis
        if axis.axis_id.value.replace("_", " ").casefold() == normalized:
            return axis
    raise KeyError(f"Unknown axis name: {name}")

