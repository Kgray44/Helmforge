from __future__ import annotations

from shared_core.models.runtime import AXIS_NAMES


DEFAULT_AXIS_COLORS: dict[str, str] = {
    "Roll": "#58B8FF",
    "Pitch": "#6FDB9F",
    "Throttle": "#F0C46A",
    "Yaw": "#CF95FF",
    "Aux 1": "#FF9B6B",
    "Aux 2": "#6ED9D0",
}


def color_for_axis(axis_name: str) -> str:
    return DEFAULT_AXIS_COLORS.get(axis_name, "#58B8FF")


def default_axis_color_items() -> tuple[tuple[str, str], ...]:
    return tuple((axis, DEFAULT_AXIS_COLORS[axis]) for axis in AXIS_NAMES)
