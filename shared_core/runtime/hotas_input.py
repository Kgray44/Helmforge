from __future__ import annotations

import re
import ctypes
import os
import struct
import threading
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from shared_core.models.runtime import InputDeviceDetection, KNOWN_TARGET_HARDWARE
from shared_core.runtime.device_discovery import (
    detect_input_devices,
    enumerate_input_device_names,
    is_likely_target_hotas_name,
)
from shared_core.runtime.input_normalization import normalize_axis_value


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_VID_RE = re.compile(r"vid[_&\\-]?([0-9a-f]{4})", re.IGNORECASE)
_PID_RE = re.compile(r"pid[_&\\-]?([0-9a-f]{4})", re.IGNORECASE)
_SUPPORTED_HOTAS_VENDOR_ID = "044f"
_SUPPORTED_HOTAS_PRODUCT_ID = "b68d"
_SUPPORTED_HOTAS_NAMES = (
    "Thrustmaster T-Flight HOTAS One",
    "Thrustmaster T.Flight Hotas One",
    "T.Flight HOTAS One",
)
SUPPORTED_HOTAS_AXIS_HINTS = ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
SUPPORTED_HOTAS_BUTTON_HINTS = tuple(f"B{index}" for index in range(1, 16))
SUPPORTED_HOTAS_HAT_HINTS = ("Hat 1",)

_JOY_RETURN_ALL = 0x000000FF
_JOYCAPS_HASPOV = 0x0010
_JOY_POVCENTERED = 0xFFFF

_RAW_INPUT_BACKEND_NAME = "windows_raw_input"
_RAW_INPUT_USAGE_PAGE_GENERIC_DESKTOP = 0x01
_RAW_INPUT_USAGE_JOYSTICK = 0x04
_RAW_INPUT_USAGE_GAMEPAD = 0x05
_RAW_INPUT_WM_INPUT = 0x00FF
_RAW_INPUT_RID_INPUT = 0x10000003
_RAW_INPUT_RIDI_DEVICENAME = 0x20000007
_RAW_INPUT_RIDEV_INPUTSINK = 0x00000100
_RAW_INPUT_RIM_TYPEHID = 2
_RAW_INPUT_HOTAS_AXIS_LAYOUT = (
    ("X", "Roll", False),
    ("Y", "Pitch", False),
    ("Z", "Throttle", True),
    ("R", "Yaw", False),
    ("U", "Aux 1", False),
    ("V", "Aux 2", False),
)
_RAW_INPUT_HAT_DIRECTIONS = {
    0: "Centered",
    1: "North",
    2: "East",
    3: "South",
    4: "West",
    5: "North East",
    6: "South East",
    7: "South West",
    8: "North West",
}
_DEFAULT_RAW_INPUT_PROVIDER = object()


class _JOYCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", ctypes.c_ushort),
        ("wPid", ctypes.c_ushort),
        ("szPname", ctypes.c_wchar * 32),
        ("wXmin", ctypes.c_uint),
        ("wXmax", ctypes.c_uint),
        ("wYmin", ctypes.c_uint),
        ("wYmax", ctypes.c_uint),
        ("wZmin", ctypes.c_uint),
        ("wZmax", ctypes.c_uint),
        ("wNumButtons", ctypes.c_uint),
        ("wPeriodMin", ctypes.c_uint),
        ("wPeriodMax", ctypes.c_uint),
        ("wRmin", ctypes.c_uint),
        ("wRmax", ctypes.c_uint),
        ("wUmin", ctypes.c_uint),
        ("wUmax", ctypes.c_uint),
        ("wVmin", ctypes.c_uint),
        ("wVmax", ctypes.c_uint),
        ("wCaps", ctypes.c_uint),
        ("wMaxAxes", ctypes.c_uint),
        ("wNumAxes", ctypes.c_uint),
        ("wMaxButtons", ctypes.c_uint),
        ("szRegKey", ctypes.c_wchar * 32),
        ("szOEMVxD", ctypes.c_wchar * 260),
    ]


class _JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_uint),
        ("dwFlags", ctypes.c_uint),
        ("dwXpos", ctypes.c_uint),
        ("dwYpos", ctypes.c_uint),
        ("dwZpos", ctypes.c_uint),
        ("dwRpos", ctypes.c_uint),
        ("dwUpos", ctypes.c_uint),
        ("dwVpos", ctypes.c_uint),
        ("dwButtons", ctypes.c_uint),
        ("dwButtonNumber", ctypes.c_uint),
        ("dwPOV", ctypes.c_uint),
        ("dwReserved1", ctypes.c_uint),
        ("dwReserved2", ctypes.c_uint),
    ]


class _RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", ctypes.c_ushort),
        ("usUsage", ctypes.c_ushort),
        ("dwFlags", ctypes.c_uint),
        ("hwndTarget", ctypes.c_void_p),
    ]


class _RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [
        ("hDevice", ctypes.c_void_p),
        ("dwType", ctypes.c_uint),
    ]


class _RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", ctypes.c_uint),
        ("dwSize", ctypes.c_uint),
        ("hDevice", ctypes.c_void_p),
        ("wParam", ctypes.c_void_p),
    ]


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_void_p),
        ("lParam", ctypes.c_void_p),
        ("time", ctypes.c_uint),
        ("pt", _POINT),
    ]


class PhysicalInputBackendError(RuntimeError):
    """Raised by guarded future sampling methods when input authority is unavailable."""


class PhysicalInputSelectionStatus(Enum):
    BACKEND_UNAVAILABLE = "backend_unavailable"
    NO_DEVICE_SELECTED = "no_device_selected"
    SELECTED_DEVICE_AVAILABLE = "selected_device_available"
    SELECTED_DEVICE_MISSING = "selected_device_missing"
    UNSUPPORTED_DEVICE_SELECTED = "unsupported_device_selected"


class PhysicalInputSamplingStatus(Enum):
    UNAVAILABLE = "unavailable"
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    DEVICE_MISSING = "selected_device_missing"
    NO_DEVICE_SELECTED = "no_device_selected"


@dataclass(frozen=True)
class PhysicalInputBackendCapabilities:
    backend_name: str
    backend_kind: str
    backend_available: bool
    device_enumeration_available: bool
    physical_sampling_available: bool = False
    backend_priority: int = 0
    raw_axis_values_available: bool = False
    normalized_axis_values_available: bool = False
    axis_range_available: bool = False
    button_sampling_available: bool = False
    hat_sampling_available: bool = False
    estimated_resolution_available: bool = False
    event_driven_available: bool = False
    polling_available: bool = False
    requires_message_loop: bool = False
    optional_dependency_name: str | None = None
    optional_dependency_available: bool = True
    packaging_risk: str = "low"
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "backend_name": self.backend_name,
            "backend_kind": self.backend_kind,
            "backend_available": self.backend_available,
            "device_enumeration_available": self.device_enumeration_available,
            "physical_sampling_available": self.physical_sampling_available,
            "backend_priority": self.backend_priority,
            "raw_axis_values_available": self.raw_axis_values_available,
            "normalized_axis_values_available": self.normalized_axis_values_available,
            "axis_range_available": self.axis_range_available,
            "button_sampling_available": self.button_sampling_available,
            "hat_sampling_available": self.hat_sampling_available,
            "estimated_resolution_available": self.estimated_resolution_available,
            "event_driven_available": self.event_driven_available,
            "polling_available": self.polling_available,
            "requires_message_loop": self.requires_message_loop,
            "optional_dependency_name": self.optional_dependency_name,
            "optional_dependency_available": self.optional_dependency_available,
            "packaging_risk": self.packaging_risk,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class PhysicalInputBackendStatus:
    status: str
    backend_name: str
    message: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class PhysicalInputAxisDiagnostics:
    logical_name: str
    raw_name: str
    raw_value: object
    normalized_value: float
    raw_min: float | None = None
    raw_max: float | None = None
    center: float | None = None
    inverted: bool = False
    one_sided: bool = False
    resolution_hint: str = "unavailable"
    last_delta_raw: float | None = None
    last_delta_normalized: float | None = None
    warning: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_name": self.logical_name,
            "raw_name": self.raw_name,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "raw_min": self.raw_min,
            "raw_max": self.raw_max,
            "center": self.center,
            "inverted": self.inverted,
            "one_sided": self.one_sided,
            "resolution_hint": self.resolution_hint,
            "last_delta_raw": self.last_delta_raw,
            "last_delta_normalized": self.last_delta_normalized,
            "warning": self.warning,
        }


@dataclass(frozen=True)
class PhysicalInputFidelitySnapshot:
    backend_name: str
    backend_kind: str
    device_id: str | None
    device_name: str
    sampled_at: datetime | None
    sequence: int
    sample_age_ms: float | None = None
    read_duration_ms: float | None = None
    estimated_sample_rate_hz: float | None = None
    axis_count: int = 0
    button_count: int = 0
    hat_count: int = 0
    axes: Mapping[str, PhysicalInputAxisDiagnostics] = None  # type: ignore[assignment]
    buttons: Mapping[str, bool] = None  # type: ignore[assignment]
    hats: Mapping[str, str] = None  # type: ignore[assignment]
    mapping_status: str = "unavailable"
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "axes", dict(self.axes or {}))
        object.__setattr__(self, "buttons", dict(self.buttons or {}))
        object.__setattr__(self, "hats", dict(self.hats or {}))

    def to_dict(self) -> dict[str, object]:
        return {
            "backend_name": self.backend_name,
            "backend_kind": self.backend_kind,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "sampled_at": self.sampled_at.isoformat() if self.sampled_at else None,
            "sequence": self.sequence,
            "sample_age_ms": self.sample_age_ms,
            "read_duration_ms": self.read_duration_ms,
            "estimated_sample_rate_hz": self.estimated_sample_rate_hz,
            "axis_count": self.axis_count,
            "button_count": self.button_count,
            "hat_count": self.hat_count,
            "axes": {name: axis.to_dict() for name, axis in self.axes.items()},
            "buttons": dict(self.buttons),
            "hats": dict(self.hats),
            "mapping_status": self.mapping_status,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class PhysicalInputBackendChoice:
    selected_backend_name: str
    selected_backend_kind: str
    selection_reason: str
    fallback_used: bool = False
    fallback_reason: str = ""
    candidate_backends: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_backend_name": self.selected_backend_name,
            "selected_backend_kind": self.selected_backend_kind,
            "selection_reason": self.selection_reason,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "candidate_backends": list(self.candidate_backends),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class PhysicalInputBackendSelectionResult:
    backend: "PhysicalInputBackend"
    choice: PhysicalInputBackendChoice


@dataclass(frozen=True)
class PhysicalInputDeviceInfo:
    device_id: str
    display_name: str
    manufacturer: str = ""
    vendor_id: str | None = None
    product_id: str | None = None
    serial_number: str | None = None
    axis_count: int | None = None
    button_count: int | None = None
    hat_count: int | None = None
    backend_name: str = "unknown"
    is_supported: bool = False
    support_reason: str = "Device has not been classified."
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RawInputDeviceRecord:
    device_id: str
    display_name: str
    vendor_id: str | None = None
    product_id: str | None = None
    handle: object | None = None
    report_size: int | None = None
    usage_page: int | None = None
    usage: int | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PhysicalInputSelectionResult:
    selected_device_id: str | None
    selected_device_display_name: str
    selected_backend: str
    selection_status: PhysicalInputSelectionStatus
    device: PhysicalInputDeviceInfo | None = None
    message: str = ""

    @property
    def selected_device_missing(self) -> bool:
        return self.selection_status is PhysicalInputSelectionStatus.SELECTED_DEVICE_MISSING

    @property
    def no_device_selected(self) -> bool:
        return self.selection_status in {
            PhysicalInputSelectionStatus.NO_DEVICE_SELECTED,
            PhysicalInputSelectionStatus.BACKEND_UNAVAILABLE,
        }

    @property
    def selected_device_available(self) -> bool:
        return self.selection_status is PhysicalInputSelectionStatus.SELECTED_DEVICE_AVAILABLE

    @property
    def unsupported_device_selected(self) -> bool:
        return self.selection_status is PhysicalInputSelectionStatus.UNSUPPORTED_DEVICE_SELECTED


@dataclass(frozen=True)
class PhysicalInputDiagnostics:
    physical_input_backend: str
    input_source: str
    supported_hotas: str
    selected_input_device: str
    input_sampling: str
    selection_status: str
    physical_input_read_only: bool = True
    simulation_fallback_state: str = "Simulation fallback active"
    last_sample: str = "Unavailable"
    sample_source: str = "unavailable"
    sample_counts: str = "0 axes / 0 buttons / 0 hats"
    sampling_warnings: str = "None"
    sampling_errors: str = "None"
    output_verified: bool = False
    full_live_runtime_ready: bool = False
    boundary_note: str = (
        "Phase 14B physical input sampling is read-only; no vJoy writes, "
        "output verification, or Full Live Runtime Ready claim is added."
    )


@dataclass(frozen=True)
class PhysicalAxisSample:
    raw_name: str
    logical_name: str | None
    raw_value: object
    normalized_value: float
    raw_min: float | None = None
    raw_max: float | None = None
    center: float | None = None
    inverted: bool = False
    one_sided: bool = False
    warning: str | None = None


@dataclass(frozen=True)
class PhysicalButtonSample:
    button_index: int
    pressed: bool


@dataclass(frozen=True)
class PhysicalHatSample:
    hat_index: int
    raw_value: object
    normalized_direction: str


@dataclass(frozen=True)
class PhysicalInputSnapshot:
    device_id: str | None
    device_name: str
    backend_name: str
    sampled_at: datetime | None
    sequence: int
    axes: tuple[PhysicalAxisSample, ...] = ()
    buttons: tuple[PhysicalButtonSample, ...] = ()
    hats: tuple[PhysicalHatSample, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    sampling_active: bool = False
    sample_source: str = "unavailable"
    sampling_status: PhysicalInputSamplingStatus = PhysicalInputSamplingStatus.UNAVAILABLE
    read_duration_ms: float | None = None
    estimated_sample_rate_hz: float | None = None

    @property
    def axis_count(self) -> int:
        return len(self.axes)

    @property
    def button_count(self) -> int:
        return len(self.buttons)

    @property
    def hat_count(self) -> int:
        return len(self.hats)

    def axis_by_logical_name(self, logical_name: str) -> PhysicalAxisSample:
        normalized = _compact(logical_name)
        for axis in self.axes:
            if _compact(axis.logical_name or axis.raw_name) == normalized:
                return axis
        raise KeyError(logical_name)


class PhysicalInputBackend:
    def enumerate_devices(self) -> tuple[PhysicalInputDeviceInfo, ...]:
        raise NotImplementedError

    def get_backend_status(self) -> PhysicalInputBackendStatus:
        raise NotImplementedError

    def get_capabilities(self) -> PhysicalInputBackendCapabilities:
        raise NotImplementedError

    def open_device(self, device_id: str) -> PhysicalInputBackendStatus:
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.UNAVAILABLE.value,
            backend_name=self.get_capabilities().backend_name,
            message=f"Device {device_id} was not opened; this backend does not provide sampling.",
            warnings=("Physical input sampling is unavailable for this backend.",),
        )

    def close_device(self) -> PhysicalInputBackendStatus:
        return PhysicalInputBackendStatus(
            status="closed",
            backend_name=self.get_capabilities().backend_name,
            message="No physical input device is open.",
        )

    def read_current_state(self) -> PhysicalInputSnapshot:
        return _empty_snapshot(
            backend_name=self.get_capabilities().backend_name,
            status=PhysicalInputSamplingStatus.UNAVAILABLE,
            sample_source="unavailable",
            errors=("Physical input sampling is unavailable for this backend.",),
        )

    def get_sampling_status(self) -> PhysicalInputBackendStatus:
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.UNAVAILABLE.value,
            backend_name=self.get_capabilities().backend_name,
            message="Physical input sampling is unavailable for this backend.",
        )


class MissingPhysicalInputBackend(PhysicalInputBackend):
    def __init__(self, *, reason: str = "No physical input backend is available.") -> None:
        self._reason = reason

    def enumerate_devices(self) -> tuple[PhysicalInputDeviceInfo, ...]:
        return ()

    def get_backend_status(self) -> PhysicalInputBackendStatus:
        return PhysicalInputBackendStatus(
            status="backend_unavailable",
            backend_name="missing_physical_input_backend",
            message=self._reason,
            warnings=("Simulation mode remains available.",),
        )

    def get_capabilities(self) -> PhysicalInputBackendCapabilities:
        return PhysicalInputBackendCapabilities(
            backend_name="missing_physical_input_backend",
            backend_kind="missing",
            backend_available=False,
            device_enumeration_available=False,
            physical_sampling_available=False,
            backend_priority=-100,
            optional_dependency_available=False,
            warnings=("No optional physical input dependency is required for app startup.",),
        )

    def open_device(self, device_id: str) -> PhysicalInputBackendStatus:
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.UNAVAILABLE.value,
            backend_name="missing_physical_input_backend",
            message=f"Cannot open {device_id}; physical input backend is unavailable.",
            warnings=("Simulation mode remains available.",),
        )

    def read_current_state(self) -> PhysicalInputSnapshot:
        return _empty_snapshot(
            backend_name="missing_physical_input_backend",
            status=PhysicalInputSamplingStatus.UNAVAILABLE,
            sample_source="unavailable",
            errors=("Physical input backend is unavailable.",),
        )


class FakePhysicalInputBackend(PhysicalInputBackend):
    def __init__(
        self,
        devices: Sequence[PhysicalInputDeviceInfo] = (),
        *,
        backend_name: str = "fake_physical_input_backend",
        backend_available: bool = True,
        sample_frames: Sequence[Mapping[str, object]] = (),
        clock=None,
        disconnected: bool = False,
        sampling_error: str | None = None,
        sample_source: str = "fake",
    ) -> None:
        self._devices = tuple(devices)
        self._backend_name = backend_name
        self._backend_available = backend_available
        self._sample_frames = tuple(sample_frames)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._disconnected = disconnected
        self._sampling_error = sampling_error
        self._sample_source = sample_source
        self._open_device_id: str | None = None
        self._sequence = 0

    def enumerate_devices(self) -> tuple[PhysicalInputDeviceInfo, ...]:
        if not self._backend_available:
            return ()
        return self._devices

    def get_backend_status(self) -> PhysicalInputBackendStatus:
        if not self._backend_available:
            return PhysicalInputBackendStatus(
                status="backend_unavailable",
                backend_name=self._backend_name,
                message="Fake physical input backend is configured unavailable.",
            )
        return PhysicalInputBackendStatus(
            status="available",
            backend_name=self._backend_name,
            message="Fake physical input backend is available for deterministic tests.",
        )

    def get_capabilities(self) -> PhysicalInputBackendCapabilities:
        return PhysicalInputBackendCapabilities(
            backend_name=self._backend_name,
            backend_kind="fake",
            backend_available=self._backend_available,
            device_enumeration_available=self._backend_available,
            physical_sampling_available=self._backend_available and bool(self._sample_frames),
            backend_priority=90,
            raw_axis_values_available=True,
            normalized_axis_values_available=True,
            axis_range_available=True,
            button_sampling_available=True,
            hat_sampling_available=True,
            estimated_resolution_available=True,
            polling_available=True,
            warnings=("Fake backend provides deterministic read-only samples for tests.",),
        )

    def open_device(self, device_id: str) -> PhysicalInputBackendStatus:
        if not self._backend_available:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.UNAVAILABLE.value,
                backend_name=self._backend_name,
                message="Fake physical input backend is unavailable.",
            )
        if not self._sample_frames:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.UNAVAILABLE.value,
                backend_name=self._backend_name,
                message="Fake physical input backend has no sample frames configured.",
            )
        device = self._device_by_id(device_id)
        if device is None:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.DEVICE_MISSING.value,
                backend_name=self._backend_name,
                message="Selected physical input device is not currently discovered.",
            )
        if not device.is_supported:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.UNAVAILABLE.value,
                backend_name=self._backend_name,
                message="Selected physical input device is unsupported.",
            )
        self._open_device_id = device_id
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.ACTIVE.value,
            backend_name=self._backend_name,
            message="Fake physical input sampling is active and read-only.",
        )

    def close_device(self) -> PhysicalInputBackendStatus:
        self._open_device_id = None
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.INACTIVE.value,
            backend_name=self._backend_name,
            message="Fake physical input sampling stopped.",
        )

    def get_sampling_status(self) -> PhysicalInputBackendStatus:
        if not self._backend_available:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.UNAVAILABLE.value,
                backend_name=self._backend_name,
                message="Fake physical input backend is unavailable.",
            )
        if self._sampling_error:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.ERROR.value,
                backend_name=self._backend_name,
                message=self._sampling_error,
                errors=(self._sampling_error,),
            )
        if self._disconnected:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.DEVICE_MISSING.value,
                backend_name=self._backend_name,
                message="Fake physical input device disconnected.",
                errors=("Fake physical input device disconnected.",),
            )
        if self._open_device_id:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.ACTIVE.value,
                backend_name=self._backend_name,
                message="Fake physical input sampling is active and read-only.",
            )
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.INACTIVE.value,
            backend_name=self._backend_name,
            message="Fake physical input backend is idle.",
        )

    def read_current_state(self) -> PhysicalInputSnapshot:
        started = time.perf_counter()
        if not self._backend_available:
            return _empty_snapshot(
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.UNAVAILABLE,
                sample_source="unavailable",
                errors=("Fake physical input backend is unavailable.",),
            )
        if self._open_device_id is None:
            return _empty_snapshot(
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.INACTIVE,
                sample_source=self._sample_source,
                errors=("No physical input device is open.",),
            )
        device = self._device_by_id(self._open_device_id)
        if device is None or self._disconnected:
            return _empty_snapshot(
                device_id=self._open_device_id,
                device_name=device.display_name if device else "Missing",
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.DEVICE_MISSING,
                sample_source=self._sample_source,
                errors=("Fake physical input device disconnected.",),
            )
        if self._sampling_error:
            return _empty_snapshot(
                device_id=device.device_id,
                device_name=device.display_name,
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.ERROR,
                sample_source=self._sample_source,
                errors=(self._sampling_error,),
            )

        frame = self._sample_frames[self._sequence % len(self._sample_frames)] if self._sample_frames else {}
        self._sequence += 1
        return _snapshot_from_frame(
            frame,
            device=device,
            backend_name=self._backend_name,
            sampled_at=self._clock(),
            sequence=self._sequence,
            sample_source=self._sample_source,
            read_duration_ms=_elapsed_ms(started),
        )

    def _device_by_id(self, device_id: str) -> PhysicalInputDeviceInfo | None:
        return next((device for device in self._devices if device.device_id == device_id), None)


class WindowsPhysicalInputDiscoveryBackend(PhysicalInputBackend):
    def __init__(self, *, backend_name: str = "windows_pnp_input_discovery") -> None:
        self._backend_name = backend_name
        self._cached_devices: tuple[PhysicalInputDeviceInfo, ...] | None = None

    def enumerate_devices(self) -> tuple[PhysicalInputDeviceInfo, ...]:
        if self._cached_devices is not None:
            return self._cached_devices
        devices: list[PhysicalInputDeviceInfo] = []
        for raw_name in enumerate_input_device_names():
            devices.append(_device_from_windows_pnp_line(raw_name, backend_name=self._backend_name))
        self._cached_devices = tuple(devices)
        return self._cached_devices

    def get_backend_status(self) -> PhysicalInputBackendStatus:
        return PhysicalInputBackendStatus(
            status="available",
            backend_name=self._backend_name,
            message="Windows PnP discovery is available for read-only physical input identity checks.",
        )

    def get_capabilities(self) -> PhysicalInputBackendCapabilities:
        return PhysicalInputBackendCapabilities(
            backend_name=self._backend_name,
            backend_kind="windows_pnp_discovery",
            backend_available=True,
            device_enumeration_available=True,
            physical_sampling_available=False,
            backend_priority=10,
            warnings=("Windows PnP discovery does not poll live HOTAS state.",),
        )


class WindowsJoystickInputBackend(PhysicalInputBackend):
    def __init__(self, *, backend_name: str = "windows_winmm_joystick") -> None:
        self._backend_name = backend_name
        self._open_device_id: str | None = None
        self._open_device_info: PhysicalInputDeviceInfo | None = None
        self._sequence = 0

    def enumerate_devices(self) -> tuple[PhysicalInputDeviceInfo, ...]:
        if os.name != "nt":
            return ()
        devices: list[PhysicalInputDeviceInfo] = []
        try:
            for device_index in range(int(_winmm().joyGetNumDevs())):
                caps = _JOYCAPSW()
                result = _winmm().joyGetDevCapsW(device_index, ctypes.byref(caps), ctypes.sizeof(caps))
                if result != 0:
                    continue
                name = str(caps.szPname).strip() or f"Joystick {device_index + 1}"
                devices.append(
                    build_physical_input_device_info(
                        device_id=f"winmm:{device_index}",
                        display_name=name,
                        manufacturer="Thrustmaster" if "thrustmaster" in name.lower() else "",
                        vendor_id=f"{int(caps.wMid):04x}" if caps.wMid else None,
                        product_id=f"{int(caps.wPid):04x}" if caps.wPid else None,
                        axis_count=int(caps.wNumAxes) if caps.wNumAxes else None,
                        button_count=int(caps.wNumButtons) if caps.wNumButtons else None,
                        hat_count=1 if caps.wCaps & _JOYCAPS_HASPOV else 0,
                        backend_name=self._backend_name,
                    )
                )
        except Exception:
            return ()
        return tuple(devices)

    def get_backend_status(self) -> PhysicalInputBackendStatus:
        if os.name != "nt":
            return PhysicalInputBackendStatus(
                status="backend_unavailable",
                backend_name=self._backend_name,
                message="Windows joystick sampling is only available on Windows.",
            )
        return PhysicalInputBackendStatus(
            status="available",
            backend_name=self._backend_name,
            message="Windows joystick sampling is available through winmm.",
        )

    def get_capabilities(self) -> PhysicalInputBackendCapabilities:
        available = os.name == "nt"
        return PhysicalInputBackendCapabilities(
            backend_name=self._backend_name,
            backend_kind="windows_winmm",
            backend_available=available,
            device_enumeration_available=available,
            physical_sampling_available=available,
            backend_priority=50,
            raw_axis_values_available=available,
            normalized_axis_values_available=available,
            axis_range_available=available,
            button_sampling_available=available,
            hat_sampling_available=available,
            estimated_resolution_available=available,
            polling_available=available,
            warnings=("Windows joystick sampling is read-only and does not write vJoy.",),
        )

    def open_device(self, device_id: str) -> PhysicalInputBackendStatus:
        device = next((device for device in self.enumerate_devices() if device.device_id == device_id), None)
        if device is None:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.DEVICE_MISSING.value,
                backend_name=self._backend_name,
                message=f"Selected joystick device is not available: {device_id}.",
            )
        self._open_device_id = device_id
        self._open_device_info = device
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.ACTIVE.value,
            backend_name=self._backend_name,
            message=f"Windows joystick sampling active for {device_id}.",
        )

    def close_device(self) -> PhysicalInputBackendStatus:
        self._open_device_id = None
        self._open_device_info = None
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.INACTIVE.value,
            backend_name=self._backend_name,
            message="Windows joystick sampling stopped.",
        )

    def get_sampling_status(self) -> PhysicalInputBackendStatus:
        if self._open_device_id is None:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.INACTIVE.value,
                backend_name=self._backend_name,
                message="Windows joystick backend is idle.",
            )
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.ACTIVE.value,
            backend_name=self._backend_name,
            message="Windows joystick sampling is active.",
        )

    def read_current_state(self) -> PhysicalInputSnapshot:
        started = time.perf_counter()
        if self._open_device_id is None:
            return _empty_snapshot(
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.INACTIVE,
                sample_source="winmm",
                errors=("No physical input device is open.",),
            )
        try:
            device_index = int(self._open_device_id.split(":", 1)[1])
        except (IndexError, ValueError):
            return _empty_snapshot(
                device_id=self._open_device_id,
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.DEVICE_MISSING,
                sample_source="winmm",
                errors=("Invalid Windows joystick device id.",),
            )
        device = self._open_device_info
        if device is None:
            return _empty_snapshot(
                device_id=self._open_device_id,
                device_name="Missing",
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.DEVICE_MISSING,
                sample_source="winmm",
                errors=("Selected Windows joystick is no longer present.",),
            )
        info = _JOYINFOEX()
        info.dwSize = ctypes.sizeof(_JOYINFOEX)
        info.dwFlags = _JOY_RETURN_ALL
        result = _winmm().joyGetPosEx(device_index, ctypes.byref(info))
        if result != 0:
            return _empty_snapshot(
                device_id=device.device_id,
                device_name=device.display_name,
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.ERROR,
                sample_source="winmm",
                errors=(f"joyGetPosEx failed with code {result}.",),
            )
        caps = _JOYCAPSW()
        _winmm().joyGetDevCapsW(device_index, ctypes.byref(caps), ctypes.sizeof(caps))
        self._sequence += 1
        frame = _winmm_frame(info, caps)
        return _snapshot_from_frame(
            frame,
            device=device,
            backend_name=self._backend_name,
            sampled_at=datetime.now(timezone.utc),
            sequence=self._sequence,
            sample_source="winmm",
            read_duration_ms=_elapsed_ms(started),
        )


class WindowsRawInputProvider:
    """Owns the Windows Raw Input window/message-loop boundary.

    The Bridge fast loop reads a thread-safe latest report cache through
    WindowsRawInputBackend; WM_INPUT processing stays on this provider thread.
    """

    provider_available = os.name == "nt"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._hwnd: int | None = None
        self._thread_id: int | None = None
        self._selected_device_id: str | None = None
        self._latest_report: bytes | Mapping[str, object] | None = None
        self._latest_device_handle: object | None = None
        self._errors: list[str] = []
        self._warnings: list[str] = []

    def enumerate_devices(self) -> tuple[RawInputDeviceRecord, ...]:
        if os.name != "nt":
            return ()
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.GetRawInputDeviceList.argtypes = [
                ctypes.POINTER(_RAWINPUTDEVICELIST),
                ctypes.POINTER(ctypes.c_uint),
                ctypes.c_uint,
            ]
            user32.GetRawInputDeviceList.restype = ctypes.c_uint
            user32.GetRawInputDeviceInfoW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
            user32.GetRawInputDeviceInfoW.restype = ctypes.c_uint
            count = ctypes.c_uint(0)
            result = user32.GetRawInputDeviceList(None, ctypes.byref(count), ctypes.sizeof(_RAWINPUTDEVICELIST))
            if result == ctypes.c_uint(-1).value or count.value <= 0:
                return ()
            raw_devices = (_RAWINPUTDEVICELIST * count.value)()
            result = user32.GetRawInputDeviceList(raw_devices, ctypes.byref(count), ctypes.sizeof(_RAWINPUTDEVICELIST))
            if result == ctypes.c_uint(-1).value:
                return ()
            records: list[RawInputDeviceRecord] = []
            for item in raw_devices[: count.value]:
                if int(item.dwType) != _RAW_INPUT_RIM_TYPEHID:
                    continue
                name = self._device_name(user32, item.hDevice)
                vendor = _extract_first(_VID_RE, name)
                product = _extract_first(_PID_RE, name)
                display = _display_name_for_raw_input_device(name, vendor, product)
                if not is_supported_hotas_identity(vendor_id=vendor, product_id=product, display_name=display):
                    continue
                records.append(
                    RawInputDeviceRecord(
                        device_id=f"raw:{name}",
                        display_name=display,
                        vendor_id=vendor,
                        product_id=product,
                        handle=item.hDevice,
                        warnings=("Raw Input HID report decoding is bounded to the supported HOTAS report layout.",),
                    )
                )
            return tuple(records)
        except Exception as exc:
            with self._lock:
                self._errors.append(f"Raw Input enumeration failed: {exc}")
            return ()

    def start(self, device_id: str | None = None) -> tuple[bool, str]:
        if os.name != "nt":
            return False, "Windows Raw Input is only available on Windows."
        self._selected_device_id = device_id
        if self._thread is not None and self._thread.is_alive():
            return True, "Raw Input message loop already running."
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._message_loop, name="HelmForgeRawInput", daemon=True)
        self._thread.start()
        return True, "Raw Input message loop starting."

    def stop(self) -> None:
        self._stop_event.set()
        if os.name == "nt" and self._thread_id:
            try:
                ctypes.WinDLL("user32", use_last_error=True).PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
            except Exception:
                pass
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def read_current_report(self) -> bytes | Mapping[str, object] | None:
        with self._lock:
            return self._latest_report

    @property
    def warnings(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(dict.fromkeys(self._warnings))

    @property
    def errors(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(dict.fromkeys(self._errors))

    def _device_name(self, user32, handle: object) -> str:
        size = ctypes.c_uint(0)
        user32.GetRawInputDeviceInfoW(ctypes.c_void_p(handle), _RAW_INPUT_RIDI_DEVICENAME, None, ctypes.byref(size))
        if size.value <= 0:
            return f"raw-device-{int(handle or 0):x}"
        buffer = ctypes.create_unicode_buffer(size.value + 1)
        result = user32.GetRawInputDeviceInfoW(ctypes.c_void_p(handle), _RAW_INPUT_RIDI_DEVICENAME, buffer, ctypes.byref(size))
        if result == ctypes.c_uint(-1).value:
            return f"raw-device-{int(handle or 0):x}"
        return str(buffer.value)

    def _message_loop(self) -> None:
        if os.name != "nt":
            return
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self._thread_id = int(kernel32.GetCurrentThreadId())
            hwnd = self._create_hidden_window(user32)
            if not hwnd:
                with self._lock:
                    self._errors.append("Raw Input hidden window could not be created.")
                return
            self._hwnd = int(hwnd)
            self._register_devices(user32, hwnd)
            msg = _MSG()
            while not self._stop_event.is_set():
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result in (0, -1):
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as exc:
            with self._lock:
                self._errors.append(f"Raw Input message loop failed: {exc}")

    def _create_hidden_window(self, user32) -> int:
        # A message-only HWND is not reliable for Raw Input across all Windows
        # versions, so this creates a hidden overlapped window with DefWindowProc.
        user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        user32.DefWindowProcW.restype = ctypes.c_ssize_t
        wndproc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)

        def _wndproc(hwnd, msg, wparam, lparam):
            if int(msg) == _RAW_INPUT_WM_INPUT and lparam:
                self._handle_wm_input(user32, int(lparam))
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc = wndproc_type(_wndproc)  # keep callback alive

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [
                ("style", ctypes.c_uint),
                ("lpfnWndProc", wndproc_type),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", ctypes.c_void_p),
                ("hIcon", ctypes.c_void_p),
                ("hCursor", ctypes.c_void_p),
                ("hbrBackground", ctypes.c_void_p),
                ("lpszMenuName", ctypes.c_wchar_p),
                ("lpszClassName", ctypes.c_wchar_p),
            ]

        class_name = "HelmForgeRawInputWindow"
        hinstance = ctypes.WinDLL("kernel32", use_last_error=True).GetModuleHandleW(None)
        wndclass = WNDCLASSW(0, self._wndproc, 0, 0, hinstance, None, None, None, None, class_name)
        user32.RegisterClassW(ctypes.byref(wndclass))
        hwnd = user32.CreateWindowExW(0, class_name, class_name, 0, 0, 0, 0, 0, None, None, hinstance, None)
        return int(hwnd or 0)

    def _register_devices(self, user32, hwnd: int) -> None:
        devices = (_RAWINPUTDEVICE * 2)(
            _RAWINPUTDEVICE(_RAW_INPUT_USAGE_PAGE_GENERIC_DESKTOP, _RAW_INPUT_USAGE_JOYSTICK, _RAW_INPUT_RIDEV_INPUTSINK, hwnd),
            _RAWINPUTDEVICE(_RAW_INPUT_USAGE_PAGE_GENERIC_DESKTOP, _RAW_INPUT_USAGE_GAMEPAD, _RAW_INPUT_RIDEV_INPUTSINK, hwnd),
        )
        if not user32.RegisterRawInputDevices(devices, 2, ctypes.sizeof(_RAWINPUTDEVICE)):
            with self._lock:
                self._errors.append("RegisterRawInputDevices failed for joystick/gamepad usage pages.")

    def _handle_wm_input(self, user32, lparam: int) -> None:
        size = ctypes.c_uint(0)
        result = user32.GetRawInputData(lparam, _RAW_INPUT_RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(_RAWINPUTHEADER))
        if result == ctypes.c_uint(-1).value or size.value <= 0:
            return
        buffer = ctypes.create_string_buffer(size.value)
        result = user32.GetRawInputData(lparam, _RAW_INPUT_RID_INPUT, buffer, ctypes.byref(size), ctypes.sizeof(_RAWINPUTHEADER))
        if result == ctypes.c_uint(-1).value:
            return
        data = bytes(buffer.raw[: size.value])
        header_size = ctypes.sizeof(_RAWINPUTHEADER)
        if len(data) < header_size + 8:
            return
        header = _RAWINPUTHEADER.from_buffer_copy(data[:header_size])
        if int(header.dwType) != _RAW_INPUT_RIM_TYPEHID:
            return
        hid_size, hid_count = struct.unpack_from("<II", data, header_size)
        start = header_size + 8
        payload = data[start : start + (hid_size * hid_count)]
        if not payload:
            return
        with self._lock:
            self._latest_device_handle = header.hDevice
            self._latest_report = payload


class WindowsRawInputBackend(PhysicalInputBackend):
    def __init__(
        self,
        *,
        provider: object | None = _DEFAULT_RAW_INPUT_PROVIDER,
        backend_name: str = _RAW_INPUT_BACKEND_NAME,
        clock=None,
    ) -> None:
        self._provider = (WindowsRawInputProvider() if os.name == "nt" else None) if provider is _DEFAULT_RAW_INPUT_PROVIDER else provider
        self._backend_name = backend_name
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._open_device: PhysicalInputDeviceInfo | None = None
        self._sequence = 0
        self._event_timestamps: list[float] = []

    def enumerate_devices(self) -> tuple[PhysicalInputDeviceInfo, ...]:
        if self._provider is None or not bool(getattr(self._provider, "provider_available", True)):
            return ()
        try:
            return tuple(
                raw_input_device_record_to_device_info(record, backend_name=self._backend_name)
                for record in self._provider.enumerate_devices()
            )
        except Exception:
            return ()

    def get_backend_status(self) -> PhysicalInputBackendStatus:
        caps = self.get_capabilities()
        if not caps.backend_available:
            return PhysicalInputBackendStatus(
                status="backend_unavailable",
                backend_name=self._backend_name,
                message="Windows Raw Input backend is unavailable; WinMM fallback remains available.",
                warnings=caps.warnings,
                errors=caps.errors,
            )
        return PhysicalInputBackendStatus(
            status="available",
            backend_name=self._backend_name,
            message="Windows Raw Input backend can own a hidden window/message loop for read-only HOTAS sampling.",
            warnings=caps.warnings,
            errors=caps.errors,
        )

    def get_capabilities(self) -> PhysicalInputBackendCapabilities:
        provider_available = self._provider is not None and bool(getattr(self._provider, "provider_available", True))
        devices = self.enumerate_devices() if provider_available else ()
        errors = tuple(getattr(self._provider, "errors", ())) if self._provider is not None else ()
        warnings = tuple(getattr(self._provider, "warnings", ())) if self._provider is not None else ()
        if provider_available and not devices:
            warnings = warnings + ("No supported Thrustmaster HOTAS One Raw Input device is currently enumerated.",)
        if self._provider is None:
            errors = errors + ("Windows Raw Input provider is unavailable on this platform.",)
        return PhysicalInputBackendCapabilities(
            backend_name=self._backend_name,
            backend_kind="windows_raw_input",
            backend_available=provider_available and bool(devices),
            device_enumeration_available=provider_available,
            physical_sampling_available=provider_available and bool(devices),
            backend_priority=120,
            raw_axis_values_available=True,
            normalized_axis_values_available=True,
            axis_range_available=True,
            button_sampling_available=True,
            hat_sampling_available=True,
            estimated_resolution_available=True,
            event_driven_available=True,
            polling_available=False,
            requires_message_loop=True,
            optional_dependency_name="Windows Raw Input",
            optional_dependency_available=provider_available,
            packaging_risk="medium",
            warnings=warnings + ("Raw Input is read-only here; it does not verify vJoy output.",),
            errors=errors,
        )

    def open_device(self, device_id: str) -> PhysicalInputBackendStatus:
        device = next((item for item in self.enumerate_devices() if item.device_id == device_id), None)
        if device is None:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.DEVICE_MISSING.value,
                backend_name=self._backend_name,
                message=f"Selected Raw Input device is not available: {device_id}.",
            )
        if self._provider is None:
            return self.get_backend_status()
        try:
            ok, message = self._provider.start(device_id)
        except Exception as exc:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.ERROR.value,
                backend_name=self._backend_name,
                message=f"Raw Input provider failed to start: {exc}",
                errors=(str(exc),),
            )
        if not ok:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.UNAVAILABLE.value,
                backend_name=self._backend_name,
                message=message,
                warnings=("WinMM fallback remains available when Raw Input cannot start.",),
            )
        self._open_device = device
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.ACTIVE.value,
            backend_name=self._backend_name,
            message=message,
            warnings=("Raw Input sampling is read-only; no output writes are implied.",),
        )

    def close_device(self) -> PhysicalInputBackendStatus:
        if self._provider is not None:
            try:
                self._provider.stop()
            except Exception:
                pass
        self._open_device = None
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.INACTIVE.value,
            backend_name=self._backend_name,
            message="Windows Raw Input sampling stopped.",
        )

    def get_sampling_status(self) -> PhysicalInputBackendStatus:
        if self._open_device is None:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.INACTIVE.value,
                backend_name=self._backend_name,
                message="Windows Raw Input backend is idle.",
            )
        return PhysicalInputBackendStatus(
            status=PhysicalInputSamplingStatus.ACTIVE.value,
            backend_name=self._backend_name,
            message="Windows Raw Input message loop is active.",
        )

    def read_current_state(self) -> PhysicalInputSnapshot:
        started = time.perf_counter()
        if self._open_device is None:
            return _empty_snapshot(
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.INACTIVE,
                sample_source="raw_input",
                errors=("No Raw Input device is open.",),
            )
        if self._provider is None:
            return _empty_snapshot(
                device_id=self._open_device.device_id,
                device_name=self._open_device.display_name,
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.UNAVAILABLE,
                sample_source="raw_input",
                errors=("Raw Input provider is unavailable.",),
            )
        report = self._provider.read_current_report()
        if report is None:
            return _empty_snapshot(
                device_id=self._open_device.device_id,
                device_name=self._open_device.display_name,
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.INACTIVE,
                sample_source="raw_input",
                warnings=("Raw Input message loop is running but no WM_INPUT sample has arrived yet.",),
            )
        frame, warnings = decode_thrustmaster_hotas_raw_input_report(report)
        self._sequence += 1
        self._record_event_time(time.monotonic())
        snapshot = _snapshot_from_frame(
            frame,
            device=self._open_device,
            backend_name=self._backend_name,
            sampled_at=self._clock(),
            sequence=self._sequence,
            sample_source="raw_input",
            read_duration_ms=_elapsed_ms(started),
            estimated_sample_rate_hz=self._estimated_rate_hz(),
        )
        return PhysicalInputSnapshot(
            device_id=snapshot.device_id,
            device_name=snapshot.device_name,
            backend_name=snapshot.backend_name,
            sampled_at=snapshot.sampled_at,
            sequence=snapshot.sequence,
            axes=snapshot.axes,
            buttons=snapshot.buttons,
            hats=snapshot.hats,
            warnings=tuple(snapshot.warnings) + tuple(warnings),
            errors=snapshot.errors,
            sampling_active=snapshot.sampling_active,
            sample_source=snapshot.sample_source,
            sampling_status=snapshot.sampling_status,
            read_duration_ms=snapshot.read_duration_ms,
            estimated_sample_rate_hz=snapshot.estimated_sample_rate_hz,
        )

    def _record_event_time(self, value: float) -> None:
        self._event_timestamps.append(value)
        if len(self._event_timestamps) > 30:
            del self._event_timestamps[: len(self._event_timestamps) - 30]

    def _estimated_rate_hz(self) -> float | None:
        if len(self._event_timestamps) < 2:
            return None
        elapsed = self._event_timestamps[-1] - self._event_timestamps[0]
        if elapsed <= 0:
            return None
        return round((len(self._event_timestamps) - 1) / elapsed, 2)


class WindowsRawInputCandidateBackend(PhysicalInputBackend):
    """Guarded Raw Input candidate seam.

    The real Windows Raw Input path needs a message loop/window registration.
    HF-LRDC-1B exposes the candidate and lets tests/providers prove the shape
    without making that platform dependency mandatory at app startup.
    """

    def __init__(self, *, provider: PhysicalInputBackend | None = None, backend_name: str = "windows_raw_input_candidate") -> None:
        self._provider = provider
        self._backend_name = backend_name

    def enumerate_devices(self) -> tuple[PhysicalInputDeviceInfo, ...]:
        if self._provider is None:
            return ()
        return self._provider.enumerate_devices()

    def get_backend_status(self) -> PhysicalInputBackendStatus:
        if self._provider is None:
            return PhysicalInputBackendStatus(
                status="backend_unavailable",
                backend_name=self._backend_name,
                message="Raw Input candidate requires a registered message-loop provider before it can sample.",
                warnings=("Raw Input candidate is guarded and unavailable; WinMM fallback remains available.",),
            )
        return PhysicalInputBackendStatus(
            status="available",
            backend_name=self._backend_name,
            message="Raw Input candidate provider is available for guarded read-only sampling.",
        )

    def get_capabilities(self) -> PhysicalInputBackendCapabilities:
        if self._provider is None:
            return PhysicalInputBackendCapabilities(
                backend_name=self._backend_name,
                backend_kind="windows_raw_input_candidate",
                backend_available=False,
                device_enumeration_available=False,
                physical_sampling_available=False,
                backend_priority=100,
                raw_axis_values_available=True,
                normalized_axis_values_available=True,
                axis_range_available=False,
                button_sampling_available=True,
                hat_sampling_available=True,
                event_driven_available=True,
                polling_available=False,
                requires_message_loop=True,
                optional_dependency_name="Windows Raw Input message loop",
                optional_dependency_available=False,
                packaging_risk="medium",
                warnings=("Raw Input candidate is not active until a message-loop provider is wired.",),
            )
        provider_caps = self._provider.get_capabilities()
        return PhysicalInputBackendCapabilities(
            backend_name=self._backend_name,
            backend_kind="windows_raw_input_candidate",
            backend_available=provider_caps.backend_available,
            device_enumeration_available=provider_caps.device_enumeration_available,
            physical_sampling_available=provider_caps.physical_sampling_available,
            backend_priority=100,
            raw_axis_values_available=True,
            normalized_axis_values_available=True,
            axis_range_available=provider_caps.axis_range_available,
            button_sampling_available=provider_caps.button_sampling_available,
            hat_sampling_available=provider_caps.hat_sampling_available,
            estimated_resolution_available=provider_caps.estimated_resolution_available,
            event_driven_available=True,
            polling_available=provider_caps.polling_available,
            requires_message_loop=True,
            optional_dependency_name="Windows Raw Input message loop",
            optional_dependency_available=True,
            packaging_risk="medium",
            warnings=("Raw Input candidate provider is guarded; no vJoy writes are implied.",),
        )

    def open_device(self, device_id: str) -> PhysicalInputBackendStatus:
        if self._provider is None:
            return self.get_backend_status()
        return self._provider.open_device(device_id)

    def close_device(self) -> PhysicalInputBackendStatus:
        if self._provider is None:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.INACTIVE.value,
                backend_name=self._backend_name,
                message="Raw Input candidate was not open.",
            )
        return self._provider.close_device()

    def read_current_state(self) -> PhysicalInputSnapshot:
        if self._provider is None:
            return _empty_snapshot(
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.UNAVAILABLE,
                sample_source="raw_input_candidate",
                errors=("Raw Input candidate provider is unavailable; simulation fallback remains available.",),
            )
        snapshot = self._provider.read_current_state()
        return PhysicalInputSnapshot(
            device_id=snapshot.device_id,
            device_name=snapshot.device_name,
            backend_name=self._backend_name,
            sampled_at=snapshot.sampled_at,
            sequence=snapshot.sequence,
            axes=snapshot.axes,
            buttons=snapshot.buttons,
            hats=snapshot.hats,
            warnings=snapshot.warnings,
            errors=snapshot.errors,
            sampling_active=snapshot.sampling_active,
            sample_source="raw_input_candidate",
            sampling_status=snapshot.sampling_status,
            read_duration_ms=snapshot.read_duration_ms,
            estimated_sample_rate_hz=snapshot.estimated_sample_rate_hz,
        )


class PhysicalInputBackendSelector:
    def __init__(self, candidates: Sequence[PhysicalInputBackend]) -> None:
        self._candidates = tuple(candidates)

    def select(self) -> PhysicalInputBackendSelectionResult:
        candidate_names: list[str] = []
        unavailable: list[str] = []
        for backend in sorted(self._candidates, key=lambda item: item.get_capabilities().backend_priority, reverse=True):
            caps = backend.get_capabilities()
            candidate_names.append(f"{caps.backend_name}:{caps.backend_kind}")
            if caps.backend_available and caps.device_enumeration_available and caps.physical_sampling_available:
                fallback_used = bool(unavailable)
                return PhysicalInputBackendSelectionResult(
                    backend=backend,
                    choice=PhysicalInputBackendChoice(
                        selected_backend_name=caps.backend_name,
                        selected_backend_kind=caps.backend_kind,
                        selection_reason="Selected highest-priority available physical input sampling backend.",
                        fallback_used=fallback_used,
                        fallback_reason="; ".join(unavailable),
                        candidate_backends=tuple(candidate_names),
                        warnings=caps.warnings,
                        errors=caps.errors,
                    ),
                )
            unavailable.append(f"{caps.backend_name} unavailable")

        missing = MissingPhysicalInputBackend(reason="No physical input sampling backend is available.")
        caps = missing.get_capabilities()
        return PhysicalInputBackendSelectionResult(
            backend=missing,
            choice=PhysicalInputBackendChoice(
                selected_backend_name=caps.backend_name,
                selected_backend_kind=caps.backend_kind,
                selection_reason="No candidate backend was available; simulation fallback remains active.",
                fallback_used=True,
                fallback_reason="; ".join(unavailable),
                candidate_backends=tuple(candidate_names),
                warnings=caps.warnings,
                errors=caps.errors,
            ),
        )


def enumerate_physical_input_backend_candidates() -> tuple[PhysicalInputBackend, ...]:
    return (
        WindowsRawInputBackend(),
        WindowsRawInputCandidateBackend(),
        WindowsJoystickInputBackend() if os.name == "nt" else MissingPhysicalInputBackend(reason="WinMM is Windows-only."),
        MissingPhysicalInputBackend(),
    )


def build_best_physical_input_backend() -> PhysicalInputBackendSelectionResult:
    return PhysicalInputBackendSelector(enumerate_physical_input_backend_candidates()).select()


def build_winmm_physical_input_fallback() -> PhysicalInputBackendSelectionResult:
    return PhysicalInputBackendSelector(
        (
            WindowsJoystickInputBackend() if os.name == "nt" else MissingPhysicalInputBackend(reason="WinMM is Windows-only."),
            MissingPhysicalInputBackend(),
        )
    ).select()


def build_default_physical_input_backend() -> PhysicalInputBackend:
    return build_best_physical_input_backend().backend


def build_physical_input_device_info(
    *,
    device_id: str,
    display_name: str,
    manufacturer: str = "",
    vendor_id: str | None = None,
    product_id: str | None = None,
    serial_number: str | None = None,
    axis_count: int | None = None,
    button_count: int | None = None,
    hat_count: int | None = None,
    backend_name: str = "unknown",
    warnings: Iterable[str] = (),
) -> PhysicalInputDeviceInfo:
    vendor = _normalize_usb_id(vendor_id)
    product = _normalize_usb_id(product_id)
    supported, reason = _support_result(vendor_id=vendor, product_id=product, display_name=display_name)
    return PhysicalInputDeviceInfo(
        device_id=device_id,
        display_name=display_name,
        manufacturer=manufacturer,
        vendor_id=vendor,
        product_id=product,
        serial_number=serial_number,
        axis_count=axis_count,
        button_count=button_count,
        hat_count=hat_count,
        backend_name=backend_name,
        is_supported=supported,
        support_reason=reason,
        warnings=tuple(warnings),
    )


def raw_input_device_record_to_device_info(
    record: RawInputDeviceRecord,
    *,
    backend_name: str = _RAW_INPUT_BACKEND_NAME,
) -> PhysicalInputDeviceInfo:
    return build_physical_input_device_info(
        device_id=record.device_id,
        display_name=record.display_name,
        manufacturer="Thrustmaster" if is_supported_hotas_identity(
            vendor_id=record.vendor_id,
            product_id=record.product_id,
            display_name=record.display_name,
        )
        else "",
        vendor_id=record.vendor_id,
        product_id=record.product_id,
        axis_count=6,
        button_count=15,
        hat_count=1,
        backend_name=backend_name,
        warnings=record.warnings,
    )


def decode_thrustmaster_hotas_raw_input_report(report: bytes | bytearray | Mapping[str, object]) -> tuple[dict[str, object], tuple[str, ...]]:
    """Decode a bounded HOTAS One Raw Input report into the existing frame shape.

    The byte decoder intentionally supports the observed/expected 6x u16 axes,
    15-bit button mask, and one hat nibble layout used by tests and probe
    diagnostics. Unknown shorter reports are not padded into fake channels.
    """

    if isinstance(report, Mapping):
        return dict(report), ()

    data = bytes(report)
    warnings: list[str] = []
    axes: list[dict[str, object]] = []
    offset = 0
    for raw_name, logical_name, one_sided in _RAW_INPUT_HOTAS_AXIS_LAYOUT:
        if len(data) < offset + 2:
            warnings.append(f"Raw Input report did not include {logical_name}; channel left unavailable.")
            break
        raw_value = int.from_bytes(data[offset : offset + 2], "little", signed=False)
        axes.append(
            {
                "raw_name": raw_name,
                "logical_name": logical_name,
                "raw_value": raw_value,
                "raw_min": 0,
                "raw_max": 65535,
                "center": 32767.5,
                "one_sided": one_sided,
            }
        )
        offset += 2

    buttons = {index: False for index in range(1, 16)}
    if len(data) >= offset + 2:
        button_mask = int.from_bytes(data[offset : offset + 2], "little", signed=False)
        buttons = {index: bool(button_mask & (1 << (index - 1))) for index in range(1, 16)}
        offset += 2
    else:
        warnings.append("Raw Input report did not include the B1-B15 button mask.")

    hats: dict[int, str] = {}
    if len(data) >= offset + 1:
        hats[1] = _RAW_INPUT_HAT_DIRECTIONS.get(int(data[offset]), f"Unknown({int(data[offset])})")
    else:
        warnings.append("Raw Input report did not include a hat/POV byte.")

    return {"axes": tuple(axes), "buttons": buttons, "hats": hats}, tuple(warnings)


def is_supported_hotas_identity(
    *,
    vendor_id: str | None,
    product_id: str | None,
    display_name: str,
) -> bool:
    return _support_result(
        vendor_id=_normalize_usb_id(vendor_id),
        product_id=_normalize_usb_id(product_id),
        display_name=display_name,
    )[0]


def resolve_physical_input_selection(
    backend: PhysicalInputBackend,
    *,
    selected_device_id: str | None,
) -> PhysicalInputSelectionResult:
    capabilities = backend.get_capabilities()
    if not capabilities.backend_available:
        return PhysicalInputSelectionResult(
            selected_device_id=selected_device_id,
            selected_device_display_name="None",
            selected_backend=capabilities.backend_name,
            selection_status=PhysicalInputSelectionStatus.BACKEND_UNAVAILABLE,
            message="Physical input backend unavailable; simulation mode remains available.",
        )

    devices = backend.enumerate_devices()
    if not selected_device_id:
        return PhysicalInputSelectionResult(
            selected_device_id=None,
            selected_device_display_name="None",
            selected_backend=capabilities.backend_name,
            selection_status=PhysicalInputSelectionStatus.NO_DEVICE_SELECTED,
            message="No physical input device is selected.",
        )

    selected = next((device for device in devices if device.device_id == selected_device_id), None)
    if selected is None:
        return PhysicalInputSelectionResult(
            selected_device_id=selected_device_id,
            selected_device_display_name="Missing",
            selected_backend=capabilities.backend_name,
            selection_status=PhysicalInputSelectionStatus.SELECTED_DEVICE_MISSING,
            message="The selected physical input device is not currently discovered.",
        )

    if not selected.is_supported:
        return PhysicalInputSelectionResult(
            selected_device_id=selected_device_id,
            selected_device_display_name=selected.display_name,
            selected_backend=capabilities.backend_name,
            selection_status=PhysicalInputSelectionStatus.UNSUPPORTED_DEVICE_SELECTED,
            device=selected,
            message="The selected device is not in the Phase 14A supported HOTAS list.",
        )

    return PhysicalInputSelectionResult(
        selected_device_id=selected_device_id,
        selected_device_display_name=selected.display_name,
        selected_backend=capabilities.backend_name,
        selection_status=PhysicalInputSelectionStatus.SELECTED_DEVICE_AVAILABLE,
        device=selected,
        message="Supported HOTAS selected. Input sampling is not active in Phase 14A.",
    )


def build_physical_input_diagnostics(
    backend: PhysicalInputBackend | None = None,
    *,
    selected_device_id: str | None = None,
    latest_snapshot: PhysicalInputSnapshot | None = None,
) -> PhysicalInputDiagnostics:
    backend = backend or build_default_physical_input_backend()
    capabilities = backend.get_capabilities()
    devices = backend.enumerate_devices() if capabilities.backend_available else ()
    selection = resolve_physical_input_selection(backend, selected_device_id=selected_device_id)
    supported_count = sum(1 for device in devices if device.is_supported)

    backend_text = (
        f"{capabilities.backend_name}: Available"
        if capabilities.backend_available
        else "Unavailable"
    )
    supported_text = "Detected" if supported_count else "Missing"
    if supported_count > 1:
        supported_text = f"Detected ({supported_count})"
    selected_text = selection.selected_device_display_name
    input_sampling = _sampling_text(latest_snapshot, selection, capabilities)
    input_source = "Physical input" if latest_snapshot is not None and latest_snapshot.sampling_status is PhysicalInputSamplingStatus.ACTIVE else "Simulation"
    simulation_fallback_state = "Simulation fallback active"
    sample_counts = "0 axes / 0 buttons / 0 hats"
    last_sample = "Unavailable"
    sample_source = "unavailable"
    sampling_warnings = "None"
    sampling_errors = "None"
    if latest_snapshot is not None:
        sample_counts = f"{latest_snapshot.axis_count} axes / {latest_snapshot.button_count} buttons / {latest_snapshot.hat_count} hat"
        if latest_snapshot.hat_count != 1:
            sample_counts += "s"
        sample_source = latest_snapshot.sample_source
        last_sample = latest_snapshot.sampled_at.isoformat() if latest_snapshot.sampled_at is not None else "Unavailable"
        sampling_warnings = "; ".join(latest_snapshot.warnings) if latest_snapshot.warnings else "None"
        sampling_errors = "; ".join(latest_snapshot.errors) if latest_snapshot.errors else "None"
        if latest_snapshot.sampling_status is PhysicalInputSamplingStatus.ACTIVE:
            simulation_fallback_state = "Simulation fallback remains available; read-only physical input sample displayed"
        elif latest_snapshot.sampling_status is PhysicalInputSamplingStatus.ERROR:
            simulation_fallback_state = "Simulation fallback active after physical input sample error"
        elif latest_snapshot.sampling_status is PhysicalInputSamplingStatus.DEVICE_MISSING:
            simulation_fallback_state = "Simulation fallback active because selected physical device is missing"
    return PhysicalInputDiagnostics(
        physical_input_backend=backend_text,
        input_source=input_source,
        supported_hotas=supported_text,
        selected_input_device=selected_text,
        input_sampling=input_sampling,
        selection_status=selection.selection_status.value,
        physical_input_read_only=True,
        simulation_fallback_state=simulation_fallback_state,
        last_sample=last_sample,
        sample_source=sample_source,
        sample_counts=sample_counts,
        sampling_warnings=sampling_warnings,
        sampling_errors=sampling_errors,
    )


def build_physical_input_fidelity(
    latest_snapshot: PhysicalInputSnapshot | None,
    *,
    backend: PhysicalInputBackend | None = None,
    backend_choice: PhysicalInputBackendChoice | None = None,
    sampled_at: datetime | None = None,
    read_duration_ms: float | None = None,
) -> PhysicalInputFidelitySnapshot:
    active_backend = backend or build_default_physical_input_backend()
    capabilities = active_backend.get_capabilities()
    if latest_snapshot is None:
        return PhysicalInputFidelitySnapshot(
            backend_name=capabilities.backend_name,
            backend_kind=capabilities.backend_kind,
            device_id=None,
            device_name="None",
            sampled_at=None,
            sequence=0,
            read_duration_ms=read_duration_ms,
            mapping_status="unavailable",
            warnings=("No physical input sample is available; simulation fallback remains available.",),
            errors=(),
        )

    now = sampled_at or datetime.now(timezone.utc)
    sample_age_ms = None
    if latest_snapshot.sampled_at is not None:
        sample_age_ms = max(0.0, (_ensure_aware(now) - _ensure_aware(latest_snapshot.sampled_at)).total_seconds() * 1000.0)
    axes = {
        axis.logical_name or axis.raw_name: PhysicalInputAxisDiagnostics(
            logical_name=axis.logical_name or axis.raw_name,
            raw_name=axis.raw_name,
            raw_value=axis.raw_value,
            normalized_value=axis.normalized_value,
            raw_min=axis.raw_min,
            raw_max=axis.raw_max,
            center=axis.center,
            inverted=axis.inverted,
            one_sided=axis.one_sided,
            resolution_hint=_resolution_hint(axis.raw_min, axis.raw_max),
            warning=axis.warning,
        )
        for axis in latest_snapshot.axes
    }
    buttons = {f"B{button.button_index}": bool(button.pressed) for button in latest_snapshot.buttons}
    hats = {f"Hat {hat.hat_index}": hat.normalized_direction for hat in latest_snapshot.hats}
    warnings = list(latest_snapshot.warnings)
    missing_axes = tuple(axis for axis in SUPPORTED_HOTAS_AXIS_HINTS if axis not in axes)
    missing_buttons = tuple(button for button in SUPPORTED_HOTAS_BUTTON_HINTS if button not in buttons)
    missing_hats = () if hats else SUPPORTED_HOTAS_HAT_HINTS
    mapping_status = "ok"
    if missing_axes or missing_buttons or missing_hats:
        mapping_status = "missing_expected_channels"
        if missing_axes:
            warnings.append(f"Missing expected HOTAS axes: {', '.join(missing_axes)}.")
        if missing_buttons:
            warnings.append(f"Missing expected HOTAS buttons: {', '.join(missing_buttons)}.")
        if missing_hats:
            warnings.append(f"Missing expected HOTAS hats: {', '.join(missing_hats)}.")
    if backend_choice and backend_choice.fallback_used:
        warnings.append(f"Physical input backend fallback used: {backend_choice.fallback_reason}")

    return PhysicalInputFidelitySnapshot(
        backend_name=capabilities.backend_name,
        backend_kind=capabilities.backend_kind,
        device_id=latest_snapshot.device_id,
        device_name=latest_snapshot.device_name,
        sampled_at=latest_snapshot.sampled_at,
        sequence=latest_snapshot.sequence,
        sample_age_ms=round(sample_age_ms, 3) if sample_age_ms is not None else None,
        read_duration_ms=read_duration_ms if read_duration_ms is not None else latest_snapshot.read_duration_ms,
        estimated_sample_rate_hz=latest_snapshot.estimated_sample_rate_hz,
        axis_count=latest_snapshot.axis_count,
        button_count=latest_snapshot.button_count,
        hat_count=latest_snapshot.hat_count,
        axes=axes,
        buttons=buttons,
        hats=hats,
        mapping_status=mapping_status,
        warnings=tuple(warnings),
        errors=latest_snapshot.errors,
    )


@dataclass
class PhysicalInputSampler:
    backend: PhysicalInputBackend
    selected_device_id: str | None = None
    latest_snapshot: PhysicalInputSnapshot | None = None
    validate_selection_on_read: bool = True

    def open(self) -> PhysicalInputBackendStatus:
        selection = resolve_physical_input_selection(self.backend, selected_device_id=self.selected_device_id)
        if selection.selection_status is PhysicalInputSelectionStatus.BACKEND_UNAVAILABLE:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.UNAVAILABLE.value,
                backend_name=selection.selected_backend,
                message="Physical input backend unavailable; sampling did not start.",
            )
        if selection.selection_status is PhysicalInputSelectionStatus.NO_DEVICE_SELECTED:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.NO_DEVICE_SELECTED.value,
                backend_name=selection.selected_backend,
                message="No physical input device selected; sampling did not start.",
            )
        if selection.selection_status is PhysicalInputSelectionStatus.SELECTED_DEVICE_MISSING:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.DEVICE_MISSING.value,
                backend_name=selection.selected_backend,
                message="Selected physical input device is not currently discovered.",
            )
        if selection.selection_status is PhysicalInputSelectionStatus.UNSUPPORTED_DEVICE_SELECTED:
            return PhysicalInputBackendStatus(
                status=PhysicalInputSamplingStatus.UNAVAILABLE.value,
                backend_name=selection.selected_backend,
                message="Selected physical input device is unsupported.",
            )
        return self.backend.open_device(selection.selected_device_id or "")

    def close(self) -> PhysicalInputBackendStatus:
        return self.backend.close_device()

    def read_once(self) -> PhysicalInputSnapshot:
        if not self.validate_selection_on_read:
            if not self.selected_device_id:
                self.latest_snapshot = _empty_snapshot(
                    backend_name=self.backend.get_capabilities().backend_name,
                    status=PhysicalInputSamplingStatus.NO_DEVICE_SELECTED,
                    sample_source="unavailable",
                    errors=("No physical input device selected; sampling did not start.",),
                )
                return self.latest_snapshot
            self.latest_snapshot = self.backend.read_current_state()
            return self.latest_snapshot
        selection = resolve_physical_input_selection(self.backend, selected_device_id=self.selected_device_id)
        if selection.selection_status is PhysicalInputSelectionStatus.BACKEND_UNAVAILABLE:
            self.latest_snapshot = _empty_snapshot(
                backend_name=selection.selected_backend,
                status=PhysicalInputSamplingStatus.UNAVAILABLE,
                sample_source="unavailable",
                errors=("Physical input backend unavailable; simulation mode remains available.",),
            )
            return self.latest_snapshot
        if selection.selection_status is PhysicalInputSelectionStatus.NO_DEVICE_SELECTED:
            self.latest_snapshot = _empty_snapshot(
                backend_name=selection.selected_backend,
                status=PhysicalInputSamplingStatus.NO_DEVICE_SELECTED,
                sample_source="unavailable",
                errors=("No physical input device selected; sampling did not start.",),
            )
            return self.latest_snapshot
        if selection.selection_status is PhysicalInputSelectionStatus.SELECTED_DEVICE_MISSING:
            self.latest_snapshot = _empty_snapshot(
                device_id=selection.selected_device_id,
                device_name="Missing",
                backend_name=selection.selected_backend,
                status=PhysicalInputSamplingStatus.DEVICE_MISSING,
                sample_source="unavailable",
                errors=("The selected physical input device is not currently discovered.",),
            )
            return self.latest_snapshot
        if selection.selection_status is PhysicalInputSelectionStatus.UNSUPPORTED_DEVICE_SELECTED:
            self.latest_snapshot = _empty_snapshot(
                device_id=selection.selected_device_id,
                device_name=selection.selected_device_display_name,
                backend_name=selection.selected_backend,
                status=PhysicalInputSamplingStatus.UNAVAILABLE,
                sample_source="unavailable",
                errors=("The selected physical input device is unsupported.",),
            )
            return self.latest_snapshot
        self.latest_snapshot = self.backend.read_current_state()
        return self.latest_snapshot


def supported_hotas_logical_mapping_hints() -> dict[str, tuple[str, ...]]:
    return {
        "axes": SUPPORTED_HOTAS_AXIS_HINTS,
        "buttons": SUPPORTED_HOTAS_BUTTON_HINTS,
        "hats": SUPPORTED_HOTAS_HAT_HINTS,
    }


def _sampling_text(
    latest_snapshot: PhysicalInputSnapshot | None,
    selection: PhysicalInputSelectionResult,
    capabilities: PhysicalInputBackendCapabilities,
) -> str:
    if latest_snapshot is not None:
        if latest_snapshot.sampling_status is PhysicalInputSamplingStatus.ACTIVE:
            return "Active (read-only)"
        if latest_snapshot.sampling_status is PhysicalInputSamplingStatus.ERROR:
            return "Error"
        if latest_snapshot.sampling_status is PhysicalInputSamplingStatus.DEVICE_MISSING:
            return "Unavailable - selected device missing"
        if latest_snapshot.sampling_status is PhysicalInputSamplingStatus.INACTIVE:
            return "Inactive"
        if latest_snapshot.sampling_status is PhysicalInputSamplingStatus.NO_DEVICE_SELECTED:
            return "Not active"
        return "Unavailable"
    if selection.no_device_selected:
        return "Not active"
    if selection.selected_device_missing:
        return "Unavailable - selected device missing"
    if selection.unsupported_device_selected:
        return "Unavailable - unsupported device"
    return "Inactive" if capabilities.physical_sampling_available else "Not active"


def _empty_snapshot(
    *,
    backend_name: str,
    status: PhysicalInputSamplingStatus,
    sample_source: str,
    device_id: str | None = None,
    device_name: str = "None",
    errors: Iterable[str] = (),
    warnings: Iterable[str] = (),
) -> PhysicalInputSnapshot:
    return PhysicalInputSnapshot(
        device_id=device_id,
        device_name=device_name,
        backend_name=backend_name,
        sampled_at=None,
        sequence=0,
        warnings=tuple(warnings),
        errors=tuple(errors),
        sampling_active=False,
        sample_source=sample_source,
        sampling_status=status,
    )


def _snapshot_from_frame(
    frame: Mapping[str, object],
    *,
    device: PhysicalInputDeviceInfo,
    backend_name: str,
    sampled_at: datetime,
    sequence: int,
    sample_source: str,
    read_duration_ms: float | None = None,
    estimated_sample_rate_hz: float | None = None,
) -> PhysicalInputSnapshot:
    axis_samples, warnings = _axis_samples_from_frame(frame.get("axes", ()))
    return PhysicalInputSnapshot(
        device_id=device.device_id,
        device_name=device.display_name,
        backend_name=backend_name,
        sampled_at=sampled_at,
        sequence=sequence,
        axes=axis_samples,
        buttons=_button_samples_from_frame(frame.get("buttons", ())),
        hats=_hat_samples_from_frame(frame.get("hats", ())),
        warnings=tuple(warnings),
        sampling_active=True,
        sample_source=sample_source,
        sampling_status=PhysicalInputSamplingStatus.ACTIVE,
        read_duration_ms=read_duration_ms,
        estimated_sample_rate_hz=estimated_sample_rate_hz,
    )


def _axis_samples_from_frame(raw_axes: object) -> tuple[tuple[PhysicalAxisSample, ...], tuple[str, ...]]:
    axis_frames: Iterable[object]
    if isinstance(raw_axes, Mapping):
        axis_frames = (
            {"raw_name": name, "raw_value": value, "logical_name": name}
            for name, value in raw_axes.items()
        )
    elif isinstance(raw_axes, Iterable) and not isinstance(raw_axes, (str, bytes)):
        axis_frames = raw_axes
    else:
        axis_frames = ()

    samples: list[PhysicalAxisSample] = []
    warnings: list[str] = []
    for index, item in enumerate(axis_frames):
        if isinstance(item, Mapping):
            raw_name = str(item.get("raw_name") or item.get("channel") or f"Axis {index + 1}")
            logical_name = item.get("logical_name")
            raw_value = item.get("raw_value")
            raw_min = _optional_float(item.get("raw_min"))
            raw_max = _optional_float(item.get("raw_max"))
            center = _optional_float(item.get("center"))
            inverted = bool(item.get("inverted", False))
            one_sided = bool(item.get("one_sided", False))
            already_normalized = bool(item.get("already_normalized", False))
        else:
            raw_name = f"Axis {index + 1}"
            logical_name = None
            raw_value = item
            raw_min = -1.0
            raw_max = 1.0
            center = 0.0
            inverted = False
            one_sided = False
            already_normalized = True

        normalized = normalize_axis_value(
            raw_value,
            raw_min=raw_min,
            raw_max=raw_max,
            center=center,
            already_normalized=already_normalized,
            one_sided=one_sided,
        )
        normalized_value = -normalized.normalized_value if inverted else normalized.normalized_value
        if normalized.warning:
            warnings.append(f"{raw_name}: {normalized.warning}")
        samples.append(
            PhysicalAxisSample(
                raw_name=raw_name,
                logical_name=str(logical_name) if logical_name is not None else None,
                raw_value=raw_value,
                normalized_value=normalized_value,
                raw_min=raw_min,
                raw_max=raw_max,
                center=center,
                inverted=inverted,
                one_sided=one_sided,
                warning=normalized.warning,
            )
        )
    return tuple(samples), tuple(warnings)


def _button_samples_from_frame(raw_buttons: object) -> tuple[PhysicalButtonSample, ...]:
    if isinstance(raw_buttons, Mapping):
        return tuple(
            PhysicalButtonSample(button_index=int(index), pressed=bool(pressed))
            for index, pressed in sorted(raw_buttons.items(), key=lambda item: int(item[0]))
        )
    if isinstance(raw_buttons, Iterable) and not isinstance(raw_buttons, (str, bytes)):
        samples: list[PhysicalButtonSample] = []
        for index, item in enumerate(raw_buttons, start=1):
            if isinstance(item, Mapping):
                button_index = int(item.get("button_index") or item.get("index") or index)
                pressed = bool(item.get("pressed", False))
            else:
                button_index = index
                pressed = bool(item)
            samples.append(PhysicalButtonSample(button_index=button_index, pressed=pressed))
        return tuple(samples)
    return ()


def _hat_samples_from_frame(raw_hats: object) -> tuple[PhysicalHatSample, ...]:
    if isinstance(raw_hats, Mapping):
        return tuple(
            PhysicalHatSample(hat_index=int(index), raw_value=value, normalized_direction=_hat_direction(value))
            for index, value in sorted(raw_hats.items(), key=lambda item: int(item[0]))
        )
    if isinstance(raw_hats, Iterable) and not isinstance(raw_hats, (str, bytes)):
        samples: list[PhysicalHatSample] = []
        for index, item in enumerate(raw_hats, start=1):
            if isinstance(item, Mapping):
                hat_index = int(item.get("hat_index") or item.get("index") or index)
                value = item.get("value") or item.get("direction") or "Centered"
            else:
                hat_index = index
                value = item
            samples.append(PhysicalHatSample(hat_index=hat_index, raw_value=value, normalized_direction=_hat_direction(value)))
        return tuple(samples)
    return ()


def _hat_direction(value: object) -> str:
    if value is None:
        return "Centered"
    text = str(value).strip()
    return text or "Centered"


def _winmm():
    dll = ctypes.WinDLL("winmm")
    dll.joyGetNumDevs.restype = ctypes.c_uint
    dll.joyGetDevCapsW.argtypes = [ctypes.c_uint, ctypes.POINTER(_JOYCAPSW), ctypes.c_uint]
    dll.joyGetDevCapsW.restype = ctypes.c_uint
    dll.joyGetPosEx.argtypes = [ctypes.c_uint, ctypes.POINTER(_JOYINFOEX)]
    dll.joyGetPosEx.restype = ctypes.c_uint
    return dll


def _winmm_frame(info: _JOYINFOEX, caps: _JOYCAPSW) -> dict[str, object]:
    axes = (
        _winmm_axis("X", "Roll", info.dwXpos, caps.wXmin, caps.wXmax),
        _winmm_axis("Y", "Pitch", info.dwYpos, caps.wYmin, caps.wYmax),
        _winmm_axis("Z", "Throttle", info.dwZpos, caps.wZmin, caps.wZmax, one_sided=True),
        _winmm_axis("R", "Yaw", info.dwRpos, caps.wRmin, caps.wRmax),
        _winmm_axis("U", "Aux 1", info.dwUpos, caps.wUmin, caps.wUmax),
        _winmm_axis("V", "Aux 2", info.dwVpos, caps.wVmin, caps.wVmax),
    )
    buttons = {index: bool(info.dwButtons & (1 << (index - 1))) for index in range(1, 16)}
    return {"axes": axes, "buttons": buttons, "hats": {1: _winmm_pov(info.dwPOV)}}


def _winmm_axis(raw_name: str, logical_name: str, value: int, raw_min: int, raw_max: int, *, one_sided: bool = False) -> dict[str, object]:
    return {
        "raw_name": raw_name,
        "logical_name": logical_name,
        "raw_value": int(value),
        "raw_min": int(raw_min),
        "raw_max": int(raw_max),
        "center": (float(raw_min) + float(raw_max)) / 2.0,
        "one_sided": one_sided,
    }


def _winmm_pov(value: int) -> str:
    if int(value) == _JOY_POVCENTERED:
        return "Centered"
    degrees = (int(value) % 36000) / 100.0
    if degrees >= 337.5 or degrees < 22.5:
        return "North"
    if degrees < 67.5:
        return "North East"
    if degrees < 112.5:
        return "East"
    if degrees < 157.5:
        return "South East"
    if degrees < 202.5:
        return "South"
    if degrees < 247.5:
        return "South West"
    if degrees < 292.5:
        return "West"
    return "North West"


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolution_hint(raw_min: float | None, raw_max: float | None) -> str:
    if raw_min is None or raw_max is None or raw_max <= raw_min:
        return "unavailable"
    span = int(round(float(raw_max) - float(raw_min)))
    if span >= 65000:
        return "16-bit-ish"
    if span >= 32000:
        return "15-bit-ish"
    if span >= 1000:
        return "10-bit-ish"
    return f"{span + 1} steps"


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _elapsed_ms(started: float) -> float:
    return round(max(0.0, (time.perf_counter() - started) * 1000.0), 3)


def _support_result(
    *,
    vendor_id: str | None,
    product_id: str | None,
    display_name: str,
) -> tuple[bool, str]:
    if vendor_id == _SUPPORTED_HOTAS_VENDOR_ID and product_id == _SUPPORTED_HOTAS_PRODUCT_ID:
        return True, "Supported Thrustmaster HOTAS One matched by VID 044f / PID b68d."
    if _matches_supported_name(display_name):
        return True, "Supported Thrustmaster HOTAS One name matched."
    return False, "Device is not in Phase 14A supported list."


def _matches_supported_name(display_name: str) -> bool:
    compact = _compact(display_name)
    if any(_compact(name) in compact or compact in _compact(name) for name in _SUPPORTED_HOTAS_NAMES):
        return True
    return is_likely_target_hotas_name(display_name)


def _compact(value: str) -> str:
    return _NON_ALNUM_RE.sub("", value.lower())


def _normalize_usb_id(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.lower().replace("0x", "")
    cleaned = re.sub(r"[^0-9a-f]", "", cleaned)
    if len(cleaned) >= 4:
        return cleaned[-4:]
    return cleaned or None


def _device_from_windows_pnp_line(line: str, *, backend_name: str) -> PhysicalInputDeviceInfo:
    vendor = _extract_first(_VID_RE, line)
    product = _extract_first(_PID_RE, line)
    manufacturer = "Thrustmaster" if "thrustmaster" in line.lower() else ""
    return build_physical_input_device_info(
        device_id=line,
        display_name=line,
        manufacturer=manufacturer,
        vendor_id=vendor,
        product_id=product,
        backend_name=backend_name,
    )


def _display_name_for_raw_input_device(device_name: str, vendor_id: str | None, product_id: str | None) -> str:
    if _normalize_usb_id(vendor_id) == _SUPPORTED_HOTAS_VENDOR_ID and _normalize_usb_id(product_id) == _SUPPORTED_HOTAS_PRODUCT_ID:
        return "Thrustmaster T.Flight HOTAS One"
    return device_name


def _extract_first(pattern: re.Pattern[str], value: str) -> str | None:
    match = pattern.search(value)
    return match.group(1).lower() if match else None


class HotasInputAdapter:
    def __init__(self, device_names: Iterable[str] | None = None) -> None:
        self._device_names = tuple(device_names) if device_names is not None else None
        self.target_hardware = KNOWN_TARGET_HARDWARE

    def enumerate_device_names(self) -> tuple[str, ...]:
        if self._device_names is not None:
            return self._device_names
        return enumerate_input_device_names()

    def detect(self) -> InputDeviceDetection:
        return detect_input_devices(self.enumerate_device_names())

    def enumerate_devices(self) -> tuple[PhysicalInputDeviceInfo, ...]:
        return tuple(
            build_physical_input_device_info(
                device_id=name,
                display_name=name,
                manufacturer="Thrustmaster" if "thrustmaster" in name.lower() else "",
                vendor_id=_extract_first(_VID_RE, name),
                product_id=_extract_first(_PID_RE, name),
                backend_name="legacy_hotas_input_adapter",
            )
            for name in self.enumerate_device_names()
        )
