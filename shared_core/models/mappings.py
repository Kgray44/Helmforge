from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_BATTLEFIELD_ROUTING_NOTE = (
    "Battlefield-safe runtime routing may remap RX / RY / RZ / SL0 behind the scenes when needed."
)


@dataclass(frozen=True)
class AxisMapping:
    function_name: str
    raw_axis_channel: str
    logical_output: str
    runtime_vjoy_output: str
    invert: bool = False
    live_raw_value: float = 0.0
    live_output_value: float = 0.0


@dataclass(frozen=True)
class ButtonMapping:
    hotas_button: int
    output_button: int
    raw_state: bool = False
    output_state: bool = False


@dataclass(frozen=True)
class HatMapping:
    hotas_hat: int
    vjoy_pov: int
    up_button: int | None = None
    right_button: int | None = None
    down_button: int | None = None
    left_button: int | None = None
    live_hat_state: str = "Centered"


@dataclass(frozen=True)
class MappingConfig:
    axis_routes: tuple[AxisMapping, ...] = field(default_factory=tuple)
    button_routes: tuple[ButtonMapping, ...] = field(default_factory=tuple)
    hat_routes: tuple[HatMapping, ...] = field(default_factory=tuple)
    routing_note: str = DEFAULT_BATTLEFIELD_ROUTING_NOTE


def default_axis_mappings() -> tuple[AxisMapping, ...]:
    return (
        AxisMapping("Roll", "Axis 1", "X", "X(axis1)"),
        AxisMapping("Pitch", "Axis 2", "Y", "Y(axis2)"),
        AxisMapping("Throttle", "Axis 3", "Z", "Z(axis3)"),
        AxisMapping("Yaw", "Axis 6", "RZ", "RX(axis4)"),
        AxisMapping("Aux 1", "Axis 7", "SL0", "RY(axis5)"),
        AxisMapping("Aux 2", "Axis 8", "RX", "RZ(axis6)"),
    )


def default_button_mappings() -> tuple[ButtonMapping, ...]:
    return tuple(ButtonMapping(index, index) for index in range(1, 16))


def default_hat_mappings() -> tuple[HatMapping, ...]:
    return (
        HatMapping(
            hotas_hat=1,
            vjoy_pov=1,
            up_button=7,
            right_button=18,
            down_button=19,
            left_button=0,
        ),
    )


def default_mapping_config() -> MappingConfig:
    return MappingConfig(
        axis_routes=default_axis_mappings(),
        button_routes=default_button_mappings(),
        hat_routes=default_hat_mappings(),
    )

