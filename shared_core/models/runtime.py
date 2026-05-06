from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping


AXIS_NAMES = ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
BUTTON_NAMES = tuple(f"B{index}" for index in range(1, 16))
HAT_CENTERED = "Centered"


class RuntimeMode(Enum):
    SIMULATED = "simulated"
    HARDWARE_ONLY = "hardware_only"
    OUTPUT_ONLY = "output_only"
    FULL_LIVE = "full_live"
    UNAVAILABLE = "unavailable"


class InputStatus(Enum):
    NOT_CHECKED = "not_checked"
    MISSING = "missing"
    DETECTED = "detected"
    ERROR = "error"


class OutputStatus(Enum):
    NOT_CHECKED = "not_checked"
    VJOY_MISSING = "vjoy_missing"
    VJOY_DETECTED = "vjoy_detected"
    OUTPUT_VERIFIED = "output_verified"
    OUTPUT_ERROR = "output_error"


class RuntimeTruth(Enum):
    SIMULATED = "simulated"
    DETECTED_UNVERIFIED = "detected_unverified"
    LIVE_VERIFIED = "live_verified"
    BLOCKED_MISSING_DRIVER = "blocked_missing_driver"
    BLOCKED_MISSING_DEVICE = "blocked_missing_device"
    ERROR = "error"


@dataclass(frozen=True)
class TargetHardwareMetadata:
    primary_device_name: str = "Thrustmaster T-Flight HOTAS One"
    alternate_device_name: str = "Thrustmaster T.Flight Hotas One"
    vendor_hint: str = "Thrustmaster"
    device_role: str = "physical HOTAS input"


KNOWN_TARGET_HARDWARE = TargetHardwareMetadata()


@dataclass(frozen=True)
class InputDeviceDetection:
    status: InputStatus = InputStatus.NOT_CHECKED
    detected_device_names: tuple[str, ...] = ()
    target_hardware: TargetHardwareMetadata = KNOWN_TARGET_HARDWARE
    messages: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class OutputBackendDetection:
    status: OutputStatus = OutputStatus.NOT_CHECKED
    backend_name: str | None = None
    live_output_writes_verified: bool = False
    messages: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimePreflightStatus:
    mode: RuntimeMode
    truth: RuntimeTruth
    input: InputDeviceDetection = field(default_factory=InputDeviceDetection)
    output: OutputBackendDetection = field(default_factory=OutputBackendDetection)
    target_hardware: TargetHardwareMetadata = KNOWN_TARGET_HARDWARE
    messages: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def detected_device_names(self) -> tuple[str, ...]:
        return self.input.detected_device_names

    @property
    def detected_output_backend_name(self) -> str | None:
        return self.output.backend_name

    @property
    def live_output_writes_verified(self) -> bool:
        return self.output.live_output_writes_verified


@dataclass(frozen=True)
class RuntimeSnapshot:
    raw_axis_values: Mapping[str, float]
    final_output_values: Mapping[str, float]
    button_states: Mapping[str, bool]
    hat_state: str
    runtime_status: RuntimePreflightStatus
    simulated: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_axis_values", MappingProxyType(dict(self.raw_axis_values)))
        object.__setattr__(self, "final_output_values", MappingProxyType(dict(self.final_output_values)))
        object.__setattr__(self, "button_states", MappingProxyType(dict(self.button_states)))


def simulation_fallback_status(
    *,
    truth: RuntimeTruth = RuntimeTruth.SIMULATED,
    input_detection: InputDeviceDetection | None = None,
    output_detection: OutputBackendDetection | None = None,
    messages: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> RuntimePreflightStatus:
    default_message = "Simulation mode selected; no live HOTAS/vJoy output is active."
    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=truth,
        input=input_detection or InputDeviceDetection(),
        output=output_detection or OutputBackendDetection(),
        messages=(default_message, *messages),
        warnings=warnings,
    )

