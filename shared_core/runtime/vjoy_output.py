from __future__ import annotations

import ctypes.util
import os
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Mapping

from shared_core.models.runtime import OutputBackendDetection, OutputStatus
from shared_core.models.workspace import WorkspaceConfig


@dataclass(frozen=True)
class OutputWriteResult:
    success: bool
    message: str


class VirtualOutputVerificationStatus(Enum):
    NOT_ATTEMPTED = "not_attempted"
    BACKEND_MISSING = "backend_missing"
    DEPENDENCY_MISSING = "dependency_missing"
    DEVICE_MISSING = "device_missing"
    DEVICE_BUSY = "device_busy"
    ACQUISITION_FAILED = "acquisition_failed"
    WRITE_FAILED = "write_failed"
    NEUTRAL_RESTORE_FAILED = "neutral_restore_failed"
    FAKE_VERIFIED = "fake_verified"
    REAL_VERIFIED = "real_verified"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class VirtualOutputWriteLoopState(Enum):
    DISABLED = "disabled"
    UNAVAILABLE_BACKEND_MISSING = "unavailable_backend_missing"
    UNAVAILABLE_DEVICE_MISSING = "unavailable_device_missing"
    UNAVAILABLE_UNVERIFIED = "unavailable_unverified"
    READY_VERIFIED = "ready_verified"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED_NEUTRAL = "stopped_neutral"
    ERROR_WRITE_FAILED = "error_write_failed"
    ERROR_RESTORE_FAILED = "error_restore_failed"
    SAFETY_STOPPED = "safety_stopped"


RECOVERED_AXIS_OUTPUT_ROUTES: dict[str, str] = {
    "Roll": "X",
    "Pitch": "Y",
    "Throttle": "Z",
    "Yaw": "RX",
    "Aux 1": "RY",
    "Aux 2": "RZ",
}

_VJOY_AXIS_USAGE = {
    "X": 0x30,
    "Y": 0x31,
    "Z": 0x32,
    "RX": 0x33,
    "RY": 0x34,
    "RZ": 0x35,
}
_VJOY_STATUS_OWN = 0
_VJOY_STATUS_FREE = 1
_VJOY_STATUS_BUSY = 2
_VJOY_STATUS_MISSING = 3
_VJOY_STATUS_UNKNOWN = 4


@dataclass(frozen=True)
class VirtualAxisOutput:
    axis_name: str
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _clamp_axis_value(self.value))

    def to_dict(self) -> dict[str, object]:
        return {"axis_name": self.axis_name, "value": self.value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "VirtualAxisOutput":
        return cls(axis_name=str(payload.get("axis_name") or ""), value=_safe_float(payload.get("value"), 0.0))


@dataclass(frozen=True)
class VirtualButtonOutput:
    button_name: str
    pressed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {"button_name": self.button_name, "pressed": self.pressed}

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "VirtualButtonOutput":
        return cls(button_name=str(payload.get("button_name") or ""), pressed=bool(payload.get("pressed", False)))


@dataclass(frozen=True)
class VirtualHatOutput:
    hat_name: str
    value: str = "Centered"

    def to_dict(self) -> dict[str, object]:
        return {"hat_name": self.hat_name, "value": self.value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "VirtualHatOutput":
        return cls(hat_name=str(payload.get("hat_name") or ""), value=str(payload.get("value") or "Centered"))


@dataclass(frozen=True)
class VirtualOutputIntent:
    timestamp: datetime
    source: str
    axes: tuple[VirtualAxisOutput, ...] = ()
    buttons: tuple[VirtualButtonOutput, ...] = ()
    hats: tuple[VirtualHatOutput, ...] = ()
    warnings: tuple[str, ...] = ()
    output_enabled: bool = False
    write_requested: bool = False

    @classmethod
    def defaults(
        cls,
        *,
        source: str = "simulation",
        timestamp: datetime | None = None,
    ) -> "VirtualOutputIntent":
        return cls(
            timestamp=timestamp or datetime.now(timezone.utc),
            source=source,
            axes=tuple(VirtualAxisOutput(axis, 0.0) for axis in ("X", "Y", "Z", "RX", "RY", "RZ")),
            buttons=tuple(VirtualButtonOutput(f"Out{index}", False) for index in range(1, 21)),
            hats=(VirtualHatOutput("POV1", "Centered"),),
            warnings=("output intent is not output write proof",),
            output_enabled=False,
            write_requested=False,
        )

    def axis_value(self, axis_name: str) -> float:
        for axis in self.axes:
            if axis.axis_name == axis_name:
                return axis.value
        return 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "axes": [axis.to_dict() for axis in self.axes],
            "buttons": [button.to_dict() for button in self.buttons],
            "hats": [hat.to_dict() for hat in self.hats],
            "warnings": list(self.warnings),
            "output_enabled": self.output_enabled,
            "write_requested": self.write_requested,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "VirtualOutputIntent":
        return cls(
            timestamp=_parse_timestamp(payload.get("timestamp")),
            source=str(payload.get("source") or "unknown"),
            axes=tuple(VirtualAxisOutput.from_dict(item) for item in _sequence_of_mappings(payload.get("axes"))),
            buttons=tuple(VirtualButtonOutput.from_dict(item) for item in _sequence_of_mappings(payload.get("buttons"))),
            hats=tuple(VirtualHatOutput.from_dict(item) for item in _sequence_of_mappings(payload.get("hats"))),
            warnings=tuple(str(item) for item in _sequence(payload.get("warnings"))),
            output_enabled=bool(payload.get("output_enabled", False)),
            write_requested=bool(payload.get("write_requested", False)),
        )


@dataclass(frozen=True)
class VirtualOutputBackendCapabilities:
    backend_name: str
    backend_kind: str
    backend_available: bool
    device_enumeration_available: bool = False
    real_output_writes_available: bool = False
    fake_output_available: bool = False
    output_verification_available: bool = False
    dependency_available: bool | None = None
    driver_detected: bool | None = None
    devices_enumerated: bool = False
    write_supported: bool = False
    verification_supported: bool = False
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class VirtualOutputBackendStatus:
    status: str
    backend_name: str
    message: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class VirtualOutputDeviceInfo:
    device_id: str
    display_name: str
    backend_name: str
    is_selected: bool = False
    is_supported: bool = True
    axis_support: tuple[str, ...] = ()
    button_count: int | None = None
    hat_support: str = "unknown"
    acquisition_status: str = "unknown"
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "device_id": self.device_id,
            "display_name": self.display_name,
            "backend_name": self.backend_name,
            "is_selected": self.is_selected,
            "is_supported": self.is_supported,
            "axis_support": list(self.axis_support),
            "button_count": self.button_count,
            "hat_support": self.hat_support,
            "acquisition_status": self.acquisition_status,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class VirtualOutputWriteResult:
    success: bool
    status: str
    message: str
    backend_name: str
    output_intent: VirtualOutputIntent | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class VirtualOutputVerificationResult:
    status: VirtualOutputVerificationStatus
    message: str
    output_verified: bool = False
    real_output_verified: bool = False
    fake_output_verified: bool = False
    source: str = "not attempted"
    backend_name: str = ""
    verified_at: datetime | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class VirtualOutputDiagnostics:
    virtual_output_backend: str
    virtual_output_backend_kind: str
    virtual_output_backend_status: str
    vjoy_dependency_status: str
    vjoy_device_status: str
    selected_output_device: str
    output_device_status: str
    output_write_status: str
    output_verification_status: str
    output_verification_source: str
    fake_output_verified: bool
    real_output_verified: bool
    output_verified: bool
    full_live_runtime_ready: bool
    last_verification_timestamp: str
    last_verification_error: str
    last_verification_warnings: str


@dataclass(frozen=True)
class VirtualOutputLoopConfig:
    write_rate_hz: float = 30.0
    restore_neutral_on_stop: bool = True
    allow_fake_backend: bool = True
    allow_real_backend: bool = True
    require_verification: bool = True
    max_consecutive_write_failures: int = 1
    safety_stop_on_write_failure: bool = True
    restore_neutral_on_safety_stop: bool = True

    @property
    def safe_write_rate_hz(self) -> float:
        return max(1.0, min(120.0, _safe_float(self.write_rate_hz, 30.0)))


@dataclass(frozen=True)
class VirtualOutputLoopSnapshot:
    state: VirtualOutputWriteLoopState
    enabled: bool
    backend_name: str
    selected_output_device: str
    verification_status: str
    output_write_status: str
    write_rate_hz: float
    last_write_timestamp: str = "Unavailable"
    last_write_result: str = "Unavailable"
    write_count: int = 0
    failure_count: int = 0
    actual_write_rate_hz: float | None = None
    tick_count: int = 0
    write_attempt_count: int = 0
    write_success_count: int = 0
    write_failure_count: int = 0
    write_skipped_count: int = 0
    write_skipped_rate_limited_count: int = 0
    write_skipped_disabled_count: int = 0
    write_skipped_unsafe_count: int = 0
    write_skipped_safety_count: int = 0
    consecutive_write_failures: int = 0
    last_write_duration_ms: float | None = None
    last_allowed_write_at: str | None = None
    last_skipped_write_reason: str = "None"
    last_error: str = "None"
    neutral_restore_status: str = "not_attempted"
    neutral_restore_attempted: bool = False
    neutral_restore_timestamp: str | None = None
    neutral_restore_message: str = ""
    neutral_restore_error: str = ""
    neutral_restore_duration_ms: float | None = None
    safety_stop_reason: str = "None"
    safety_stop_timestamp: str | None = None
    current_output_intent_source: str = "None"
    fake_output_loop: bool = False
    real_output_loop: bool = False
    full_live_runtime_ready: bool = False

    @property
    def last_write_status(self) -> str:
        return self.output_write_status


class OutputWriteRateLimiter:
    def __init__(self, *, write_rate_hz: float = 30.0) -> None:
        self._minimum_interval_seconds = 1.0 / max(1.0, min(120.0, _safe_float(write_rate_hz, 30.0)))
        self._last_allowed_at: datetime | None = None

    def allow(self, now: datetime) -> bool:
        if self._last_allowed_at is None:
            self._last_allowed_at = now
            return True
        elapsed = (now - self._last_allowed_at).total_seconds()
        if elapsed + 1e-9 < self._minimum_interval_seconds:
            return False
        self._last_allowed_at = now
        return True

    def reset(self) -> None:
        self._last_allowed_at = None


class VirtualOutputBackend:
    def get_capabilities(self) -> VirtualOutputBackendCapabilities:
        raise NotImplementedError

    def get_status(self) -> VirtualOutputBackendStatus:
        raise NotImplementedError

    def enumerate_output_devices(self) -> tuple[VirtualOutputDeviceInfo, ...]:
        raise NotImplementedError

    def select_output_device(self, device_id: str) -> VirtualOutputBackendStatus:
        raise NotImplementedError

    def write_output_intent(self, output_intent: VirtualOutputIntent) -> VirtualOutputWriteResult:
        raise NotImplementedError

    def verify_output_write(self, output_intent: VirtualOutputIntent) -> VirtualOutputVerificationResult:
        raise NotImplementedError

    def close(self) -> None:
        return None


class MissingVirtualOutputBackend(VirtualOutputBackend):
    backend_name = "Missing virtual output backend"

    def get_capabilities(self) -> VirtualOutputBackendCapabilities:
        return VirtualOutputBackendCapabilities(
            backend_name=self.backend_name,
            backend_kind="missing",
            backend_available=False,
            warnings=("Real vJoy writes are deferred; output intent is not output write proof.",),
        )

    def get_status(self) -> VirtualOutputBackendStatus:
        return VirtualOutputBackendStatus(
            status="backend_missing",
            backend_name=self.backend_name,
            message="Virtual output backend missing. Output writes are not active.",
        )

    def enumerate_output_devices(self) -> tuple[VirtualOutputDeviceInfo, ...]:
        return ()

    def select_output_device(self, device_id: str) -> VirtualOutputBackendStatus:
        _ = device_id
        return VirtualOutputBackendStatus(
            status="backend_missing",
            backend_name=self.backend_name,
            message="No virtual output backend is available for device selection.",
        )

    def write_output_intent(self, output_intent: VirtualOutputIntent) -> VirtualOutputWriteResult:
        return VirtualOutputWriteResult(
            success=False,
            status="backend_missing",
            message="Virtual output backend missing; no real vJoy write was attempted.",
            backend_name=self.backend_name,
            output_intent=output_intent,
        )

    def verify_output_write(self, output_intent: VirtualOutputIntent) -> VirtualOutputVerificationResult:
        _ = output_intent
        return VirtualOutputVerificationResult(
            status=VirtualOutputVerificationStatus.BACKEND_MISSING,
            message="Virtual output backend missing; output verification remains false.",
            output_verified=False,
            real_output_verified=False,
            fake_output_verified=False,
            source="backend missing",
            backend_name=self.backend_name,
        )


class FakeVirtualOutputBackend(VirtualOutputBackend):
    backend_name = "Fake output backend"

    def __init__(self, *, fail_writes: bool = False, fail_neutral_restore: bool = False) -> None:
        self.last_written_intent: VirtualOutputIntent | None = None
        self.written_intents: list[VirtualOutputIntent] = []
        self._selected_device_id = "fake-output-device"
        self._fail_writes = fail_writes
        self._fail_neutral_restore = fail_neutral_restore

    def get_capabilities(self) -> VirtualOutputBackendCapabilities:
        return VirtualOutputBackendCapabilities(
            backend_name=self.backend_name,
            backend_kind="fake",
            backend_available=True,
            device_enumeration_available=True,
            real_output_writes_available=False,
            fake_output_available=True,
            output_verification_available=True,
            warnings=("Fake output verification is mock-only. Not real vJoy.",),
        )

    def get_status(self) -> VirtualOutputBackendStatus:
        return VirtualOutputBackendStatus(
            status="fake_backend_available",
            backend_name=self.backend_name,
            message="Fake output backend available for deterministic tests only.",
        )

    def enumerate_output_devices(self) -> tuple[VirtualOutputDeviceInfo, ...]:
        return (
            VirtualOutputDeviceInfo(
                device_id="fake-output-device",
                display_name="Fake virtual output device - Not real vJoy",
                backend_name=self.backend_name,
                is_selected=self._selected_device_id == "fake-output-device",
            ),
        )

    def select_output_device(self, device_id: str) -> VirtualOutputBackendStatus:
        self._selected_device_id = str(device_id)
        return VirtualOutputBackendStatus(
            status="fake_device_selected",
            backend_name=self.backend_name,
            message=f"Fake output device selected: {self._selected_device_id}. Not real vJoy.",
        )

    def write_output_intent(self, output_intent: VirtualOutputIntent) -> VirtualOutputWriteResult:
        if self._fail_neutral_restore and output_intent.source == "neutral_restore":
            return VirtualOutputWriteResult(
                success=False,
                status="neutral_restore_failed",
                message="Mock neutral restore failed. Not real vJoy.",
                backend_name=self.backend_name,
                output_intent=output_intent,
                errors=("neutral restore failed",),
            )
        if self._fail_writes:
            return VirtualOutputWriteResult(
                success=False,
                status="write_failed",
                message="Mock output write failed. Not real vJoy.",
                backend_name=self.backend_name,
                output_intent=output_intent,
                errors=("mock write failed",),
            )
        self.last_written_intent = output_intent
        self.written_intents.append(output_intent)
        return VirtualOutputWriteResult(
            success=True,
            status="fake_write_recorded",
            message="Mock output write recorded in memory. Not real vJoy.",
            backend_name=self.backend_name,
            output_intent=output_intent,
        )

    def verify_output_write(self, output_intent: VirtualOutputIntent) -> VirtualOutputVerificationResult:
        if self.last_written_intent is None:
            self.last_written_intent = output_intent
        return VirtualOutputVerificationResult(
            status=VirtualOutputVerificationStatus.FAKE_VERIFIED,
            message="Fake output verified. Mock output write verified. Not real vJoy.",
            output_verified=False,
            real_output_verified=False,
            fake_output_verified=True,
            source="fake/mock - Not real vJoy",
            backend_name=self.backend_name,
            warnings=("Fake verification does not prove real output.",),
        )


@dataclass(frozen=True)
class VJoyProviderOperationResult:
    success: bool
    status: str
    message: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class _DefaultVJoyDetectionProvider:
    backend_name = "Real vJoy"
    write_supported = True
    verification_supported = True

    def __init__(self, *, dll_path: str | None = None) -> None:
        self.backend_path = dll_path or find_vjoy_backend_name()
        self._dll = None
        self.errors: tuple[str, ...] = ()
        if self.backend_path is not None:
            try:
                self._dll = ctypes.WinDLL(str(self.backend_path))
                self._bind()
            except Exception as exc:
                self._dll = None
                self.errors = (f"vJoyInterface load failed: {exc}",)
        self.dependency_available = self._dll is not None
        self.driver_detected = bool(self._dll is not None and self._enabled())
        self.warnings = () if self.driver_detected else ("vJoy DLL is present but vJoy is not enabled.",)

    def enumerate_devices(self) -> tuple[VirtualOutputDeviceInfo, ...]:
        if self._dll is None or not self.driver_detected:
            return ()
        devices: list[VirtualOutputDeviceInfo] = []
        for device_id in range(1, 17):
            status = int(self._dll.GetVJDStatus(device_id))
            if status == _VJOY_STATUS_MISSING:
                continue
            supported = status in {_VJOY_STATUS_OWN, _VJOY_STATUS_FREE}
            devices.append(
                VirtualOutputDeviceInfo(
                    device_id=str(device_id),
                    display_name=f"vJoy Device {device_id}",
                    backend_name=self.backend_name,
                    is_selected=device_id == 1,
                    is_supported=supported,
                    axis_support=tuple(_VJOY_AXIS_USAGE),
                    button_count=32,
                    hat_support="POV1",
                    acquisition_status=_vjoy_status_text(status),
                    warnings=() if supported else (f"vJoy device status is {_vjoy_status_text(status)}.",),
                )
            )
        return tuple(devices)

    def acquire(self, device_id: str) -> VJoyProviderOperationResult:
        if self._dll is None:
            return VJoyProviderOperationResult(False, "dependency_missing", "vJoyInterface.dll is unavailable.")
        rid = _device_number(device_id)
        status = int(self._dll.GetVJDStatus(rid))
        if status == _VJOY_STATUS_OWN:
            return VJoyProviderOperationResult(True, "already_acquired", f"vJoy device {rid} is already owned by this process.")
        if status != _VJOY_STATUS_FREE:
            return VJoyProviderOperationResult(False, _vjoy_status_text(status), f"vJoy device {rid} is {_vjoy_status_text(status)}.")
        if not bool(self._dll.AcquireVJD(rid)):
            return VJoyProviderOperationResult(False, "acquisition_failed", f"Could not acquire vJoy device {rid}.")
        return VJoyProviderOperationResult(True, "acquired", f"Acquired vJoy device {rid}.")

    def write_intent(self, device_id: str, intent: VirtualOutputIntent) -> VJoyProviderOperationResult:
        if self._dll is None:
            return VJoyProviderOperationResult(False, "dependency_missing", "vJoyInterface.dll is unavailable.")
        rid = _device_number(device_id)
        try:
            for axis in intent.axes:
                usage = _VJOY_AXIS_USAGE.get(axis.axis_name.upper())
                if usage is None:
                    continue
                value = _axis_to_vjoy_value(axis.value)
                if not bool(self._dll.SetAxis(value, rid, usage)):
                    return VJoyProviderOperationResult(False, "write_failed", f"SetAxis failed for {axis.axis_name}.")
            for index, button in enumerate(intent.buttons, start=1):
                if not bool(self._dll.SetBtn(bool(button.pressed), rid, index)):
                    return VJoyProviderOperationResult(False, "write_failed", f"SetBtn failed for button {index}.")
            for index, hat in enumerate(intent.hats, start=1):
                value = _hat_to_vjoy_value(hat.value)
                if not bool(self._dll.SetContPov(value, rid, index)):
                    return VJoyProviderOperationResult(False, "write_failed", f"SetContPov failed for POV {index}.")
        except Exception as exc:
            return VJoyProviderOperationResult(False, "write_failed", f"vJoy write failed: {exc}", errors=(str(exc),))
        return VJoyProviderOperationResult(True, "real_write_succeeded", f"Real vJoy write succeeded for device {rid}.")

    def restore_neutral(self, device_id: str) -> VJoyProviderOperationResult:
        if self._dll is None:
            return VJoyProviderOperationResult(False, "dependency_missing", "vJoyInterface.dll is unavailable.")
        rid = _device_number(device_id)
        if bool(self._dll.ResetVJD(rid)):
            return VJoyProviderOperationResult(True, "neutral_restored", f"vJoy device {rid} reset to neutral.")
        return VJoyProviderOperationResult(False, "neutral_restore_failed", f"Could not reset vJoy device {rid} to neutral.")

    def release(self, device_id: str) -> None:
        if self._dll is None:
            return
        self._dll.RelinquishVJD(_device_number(device_id))

    def _bind(self) -> None:
        assert self._dll is not None
        self._dll.vJoyEnabled.restype = ctypes.c_bool
        self._dll.GetVJDStatus.argtypes = [ctypes.c_uint]
        self._dll.GetVJDStatus.restype = ctypes.c_int
        self._dll.AcquireVJD.argtypes = [ctypes.c_uint]
        self._dll.AcquireVJD.restype = ctypes.c_bool
        self._dll.RelinquishVJD.argtypes = [ctypes.c_uint]
        self._dll.RelinquishVJD.restype = None
        self._dll.ResetVJD.argtypes = [ctypes.c_uint]
        self._dll.ResetVJD.restype = ctypes.c_bool
        self._dll.SetAxis.argtypes = [ctypes.c_long, ctypes.c_uint, ctypes.c_uint]
        self._dll.SetAxis.restype = ctypes.c_bool
        self._dll.SetBtn.argtypes = [ctypes.c_bool, ctypes.c_uint, ctypes.c_ubyte]
        self._dll.SetBtn.restype = ctypes.c_bool
        self._dll.SetContPov.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_ubyte]
        self._dll.SetContPov.restype = ctypes.c_bool

    def _enabled(self) -> bool:
        if self._dll is None:
            return False
        try:
            return bool(self._dll.vJoyEnabled())
        except Exception:
            return False


class RealVJoyOutputBackend(VirtualOutputBackend):
    backend_name = "Real vJoy"

    def __init__(
        self,
        *,
        provider: object | None = None,
        selected_device_id: str | None = None,
        clock: object | None = None,
    ) -> None:
        self._provider = provider or _DefaultVJoyDetectionProvider()
        self._selected_device_id = selected_device_id
        self._clock = clock

    def get_capabilities(self) -> VirtualOutputBackendCapabilities:
        dependency_available = self._dependency_available()
        driver_detected = self._driver_detected()
        devices = self.enumerate_output_devices()
        backend_available = dependency_available and driver_detected
        provider_write_supported = bool(_provider_attr(self._provider, "write_supported", hasattr(self._provider, "write_intent")))
        provider_verification_supported = bool(_provider_attr(self._provider, "verification_supported", hasattr(self._provider, "write_intent")))
        return VirtualOutputBackendCapabilities(
            backend_name=self.backend_name,
            backend_kind="real_vjoy",
            backend_available=backend_available,
            device_enumeration_available=backend_available,
            real_output_writes_available=backend_available and bool(devices) and provider_write_supported,
            fake_output_available=False,
            output_verification_available=backend_available and bool(devices) and provider_verification_supported,
            dependency_available=dependency_available,
            driver_detected=driver_detected,
            devices_enumerated=bool(devices),
            write_supported=provider_write_supported,
            verification_supported=provider_verification_supported,
            warnings=_provider_warnings(self._provider),
            errors=_provider_errors(self._provider),
        )

    def get_status(self) -> VirtualOutputBackendStatus:
        if not self._dependency_available():
            return VirtualOutputBackendStatus(
                status="dependency_missing",
                backend_name=self.backend_name,
                message="Real vJoy dependency is missing; output verification is unavailable.",
            )
        if not self._driver_detected():
            return VirtualOutputBackendStatus(
                status="backend_missing",
                backend_name=self.backend_name,
                message="Real vJoy driver/backend is missing; output verification is unavailable.",
            )
        devices = self.enumerate_output_devices()
        if not devices:
            return VirtualOutputBackendStatus(
                status="device_missing",
                backend_name=self.backend_name,
                message="No real vJoy output device is available for guarded verification.",
            )
        return VirtualOutputBackendStatus(
            status="backend_available",
            backend_name=self.backend_name,
            message="Real vJoy backend is detectable. Guarded verification is not automatic.",
        )

    def enumerate_output_devices(self) -> tuple[VirtualOutputDeviceInfo, ...]:
        if not self._dependency_available() or not self._driver_detected():
            return ()
        try:
            raw_devices = _provider_call(self._provider, "enumerate_devices")
        except Exception:
            return ()
        devices = tuple(_coerce_device_info(item, backend_name=self.backend_name) for item in _sequence(raw_devices))
        if not devices:
            return ()
        selected_id = self._selected_device_id or devices[0].device_id
        return tuple(_mark_device_selected(device, selected_id) for device in devices)

    def select_output_device(self, device_id: str) -> VirtualOutputBackendStatus:
        self._selected_device_id = str(device_id)
        if not any(device.device_id == self._selected_device_id for device in self.enumerate_output_devices()):
            return VirtualOutputBackendStatus(
                status="device_missing",
                backend_name=self.backend_name,
                message=f"Selected real vJoy device is not available: {self._selected_device_id}.",
            )
        return VirtualOutputBackendStatus(
            status="device_selected",
            backend_name=self.backend_name,
            message=f"Selected real vJoy device: {self._selected_device_id}.",
        )

    def write_output_intent(self, output_intent: VirtualOutputIntent) -> VirtualOutputWriteResult:
        if not self._dependency_available():
            return VirtualOutputWriteResult(
                success=False,
                status="dependency_missing",
                message="Real vJoy dependency is missing; output loop write was not attempted.",
                backend_name=self.backend_name,
                output_intent=output_intent,
            )
        if not self._driver_detected():
            return VirtualOutputWriteResult(
                success=False,
                status="backend_missing",
                message="Real vJoy backend is missing; output loop write was not attempted.",
                backend_name=self.backend_name,
                output_intent=output_intent,
            )
        devices = self.enumerate_output_devices()
        if not devices:
            return VirtualOutputWriteResult(
                success=False,
                status="device_missing",
                message="No real vJoy device is available; output loop write was not attempted.",
                backend_name=self.backend_name,
                output_intent=output_intent,
            )
        selected = next((device for device in devices if device.is_selected), devices[0])
        try:
            acquire = _coerce_operation_result(_provider_call(self._provider, "acquire", selected.device_id))
            if not acquire.success:
                return VirtualOutputWriteResult(
                    success=False,
                    status=acquire.status,
                    message=acquire.message,
                    backend_name=self.backend_name,
                    output_intent=output_intent,
                    warnings=acquire.warnings,
                    errors=acquire.errors,
                )
            write = _coerce_operation_result(_provider_call(self._provider, "write_intent", selected.device_id, output_intent))
            return VirtualOutputWriteResult(
                success=write.success,
                status=write.status,
                message=write.message,
                backend_name=self.backend_name,
                output_intent=output_intent,
                warnings=write.warnings,
                errors=write.errors,
            )
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            return VirtualOutputWriteResult(
                success=False,
                status="error",
                message=f"Real vJoy output loop write failed: {exc}",
                backend_name=self.backend_name,
                output_intent=output_intent,
                errors=(str(exc),),
            )
        finally:
            try:
                _provider_call(self._provider, "release", selected.device_id)
            except Exception:
                pass

    def verify_output_write(
        self,
        output_intent: VirtualOutputIntent,
        *,
        safety_mode: bool = True,
    ) -> VirtualOutputVerificationResult:
        if not safety_mode:
            return self._verification_result(
                VirtualOutputVerificationStatus.UNSUPPORTED,
                "Guarded verification requires safety_mode=True.",
            )
        if not self._dependency_available():
            return self._verification_result(
                VirtualOutputVerificationStatus.DEPENDENCY_MISSING,
                "Real vJoy dependency is missing; guarded output verification was not attempted.",
            )
        if not self._driver_detected():
            return self._verification_result(
                VirtualOutputVerificationStatus.BACKEND_MISSING,
                "Real vJoy backend is missing; guarded output verification was not attempted.",
            )

        devices = self.enumerate_output_devices()
        if not devices:
            return self._verification_result(
                VirtualOutputVerificationStatus.DEVICE_MISSING,
                "No real vJoy device is available; guarded output verification was not attempted.",
            )
        selected = next((device for device in devices if device.is_selected), devices[0])
        safe_intent = build_safe_vjoy_verification_intent(source=output_intent.source, timestamp=self._now())
        acquired = False
        try:
            acquire = _coerce_operation_result(_provider_call(self._provider, "acquire", selected.device_id))
            if not acquire.success:
                status = _verification_status_from_operation(acquire.status, acquire_default=VirtualOutputVerificationStatus.ACQUISITION_FAILED)
                return self._verification_result(
                    status,
                    acquire.message,
                    errors=acquire.errors,
                    warnings=acquire.warnings,
                )
            acquired = True
            write = _coerce_operation_result(_provider_call(self._provider, "write_intent", selected.device_id, safe_intent))
            if not write.success:
                return self._verification_result(
                    VirtualOutputVerificationStatus.WRITE_FAILED,
                    write.message,
                    errors=write.errors,
                    warnings=write.warnings,
                )
            restore = _coerce_operation_result(_provider_call(self._provider, "restore_neutral", selected.device_id))
            if not restore.success:
                return self._verification_result(
                    VirtualOutputVerificationStatus.NEUTRAL_RESTORE_FAILED,
                    restore.message,
                    errors=restore.errors,
                    warnings=restore.warnings,
                )
            return VirtualOutputVerificationResult(
                status=VirtualOutputVerificationStatus.REAL_VERIFIED,
                message="Real vJoy guarded bounded verification write succeeded and neutral restore succeeded.",
                output_verified=True,
                real_output_verified=True,
                fake_output_verified=False,
                source="real vJoy guarded write",
                backend_name=self.backend_name,
                verified_at=self._now(),
                warnings=(
                    "Verification was bounded and does not enable continuous output.",
                    "Full Live Runtime Ready remains false until Phase 16 end-to-end conditions are proven.",
                ),
            )
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            return self._verification_result(
                VirtualOutputVerificationStatus.ERROR,
                f"Real vJoy guarded verification failed: {exc}",
                errors=(str(exc),),
            )
        finally:
            try:
                _provider_call(self._provider, "release", selected.device_id)
            except Exception:
                pass
            _ = acquired

    def close(self) -> None:
        close = getattr(self._provider, "close", None)
        if callable(close):
            close()

    def _dependency_available(self) -> bool:
        return bool(_provider_attr(self._provider, "dependency_available", False))

    def _driver_detected(self) -> bool:
        return bool(_provider_attr(self._provider, "driver_detected", self._dependency_available()))

    def _now(self) -> datetime:
        if callable(self._clock):
            value = self._clock()
            if isinstance(value, datetime):
                return value
        return datetime.now(timezone.utc)

    def _verification_result(
        self,
        status: VirtualOutputVerificationStatus,
        message: str,
        *,
        errors: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
    ) -> VirtualOutputVerificationResult:
        return VirtualOutputVerificationResult(
            status=status,
            message=message,
            output_verified=False,
            real_output_verified=False,
            fake_output_verified=False,
            source="real vJoy guarded write",
            backend_name=self.backend_name,
            verified_at=self._now(),
            warnings=warnings,
            errors=errors,
        )


class VirtualOutputWriteLoop:
    def __init__(
        self,
        *,
        backend: VirtualOutputBackend | None = None,
        verification: VirtualOutputVerificationResult | None = None,
        config: VirtualOutputLoopConfig | None = None,
        clock: object | None = None,
    ) -> None:
        self._backend = backend or MissingVirtualOutputBackend()
        self._verification = verification
        self._config = config or VirtualOutputLoopConfig()
        self._clock = clock
        self._state = VirtualOutputWriteLoopState.DISABLED
        self._enabled = False
        self._rate_limiter = OutputWriteRateLimiter(write_rate_hz=self._config.safe_write_rate_hz)
        self._last_write_timestamp = "Unavailable"
        self._last_write_result = "Unavailable"
        self._last_write_status = "Not active"
        self._write_count = 0
        self._failure_count = 0
        self._tick_count = 0
        self._write_attempt_count = 0
        self._write_success_count = 0
        self._write_failure_count = 0
        self._write_skipped_count = 0
        self._write_skipped_rate_limited_count = 0
        self._write_skipped_disabled_count = 0
        self._write_skipped_unsafe_count = 0
        self._write_skipped_safety_count = 0
        self._consecutive_write_failures = 0
        self._last_write_duration_ms: float | None = None
        self._last_allowed_write_at: datetime | None = None
        self._accepted_write_times: deque[datetime] = deque(maxlen=30)
        self._last_skipped_write_reason = "None"
        self._last_error = "None"
        self._neutral_restore_status = "not_attempted"
        self._neutral_restore_attempted = False
        self._neutral_restore_timestamp: str | None = None
        self._neutral_restore_message = ""
        self._neutral_restore_error = ""
        self._neutral_restore_duration_ms: float | None = None
        self._safety_stop_reason = "None"
        self._safety_stop_timestamp: str | None = None
        self._current_output_intent_source = "None"

    def enable(self) -> VirtualOutputLoopSnapshot:
        gate = self._gate_state()
        if gate is not VirtualOutputWriteLoopState.READY_VERIFIED:
            self._enabled = False
            self._state = gate
            return self.snapshot()
        self._enabled = True
        self._state = VirtualOutputWriteLoopState.READY_VERIFIED
        self._last_error = "None"
        self._safety_stop_reason = "None"
        self._safety_stop_timestamp = None
        self._rate_limiter.reset()
        return self.snapshot()

    def disable(self) -> VirtualOutputLoopSnapshot:
        was_enabled = self._enabled
        had_writes = self._write_count > 0
        self._enabled = False
        self._state = VirtualOutputWriteLoopState.STOPPING
        if was_enabled and had_writes and self._config.restore_neutral_on_stop:
            restore = self._attempt_neutral_restore()
            if restore.success:
                self._last_write_timestamp = self._now().isoformat()
                self._state = VirtualOutputWriteLoopState.STOPPED_NEUTRAL
            else:
                self._failure_count += 1
                self._last_error = restore.message
                self._state = VirtualOutputWriteLoopState.ERROR_RESTORE_FAILED
            return self.snapshot()
        self._state = VirtualOutputWriteLoopState.DISABLED
        return self.snapshot()

    def tick(self, output_intent: VirtualOutputIntent) -> VirtualOutputLoopSnapshot:
        self._tick_count += 1
        if not self._enabled:
            if self._state is VirtualOutputWriteLoopState.SAFETY_STOPPED:
                self._record_skip("skipped_safety_stopped", safety=True)
            elif self._state in {
                VirtualOutputWriteLoopState.UNAVAILABLE_BACKEND_MISSING,
                VirtualOutputWriteLoopState.UNAVAILABLE_DEVICE_MISSING,
                VirtualOutputWriteLoopState.UNAVAILABLE_UNVERIFIED,
            }:
                reason = "skipped_unverified"
                if self._state is VirtualOutputWriteLoopState.UNAVAILABLE_BACKEND_MISSING:
                    reason = "backend_unavailable"
                elif self._state is VirtualOutputWriteLoopState.UNAVAILABLE_DEVICE_MISSING:
                    reason = "skipped_device_missing"
                self._record_skip(reason, unsafe=True)
            else:
                self._record_skip("skipped_disabled", disabled=True)
            return self.snapshot()
        gate = self._gate_state()
        if gate is not VirtualOutputWriteLoopState.READY_VERIFIED:
            self._enabled = False
            self._state = gate
            reason = "skipped_unverified"
            if gate is VirtualOutputWriteLoopState.UNAVAILABLE_BACKEND_MISSING:
                reason = "backend_unavailable"
            elif gate is VirtualOutputWriteLoopState.UNAVAILABLE_DEVICE_MISSING:
                reason = "skipped_device_missing"
            self._record_skip(reason, unsafe=True)
            return self.snapshot()
        now = self._now()
        if not self._rate_limiter.allow(now):
            self._record_skip("skipped_rate_limited", rate_limited=True)
            return self.snapshot()
        self._write_attempt_count += 1
        intent = _bounded_loop_intent(output_intent, timestamp=now)
        started = time.perf_counter()
        try:
            write = self._backend.write_output_intent(intent)
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            write = VirtualOutputWriteResult(
                success=False,
                status="error",
                message=str(exc),
                backend_name=self._backend.get_capabilities().backend_name,
                output_intent=intent,
                errors=(str(exc),),
            )
        self._last_write_duration_ms = _elapsed_ms(started)
        self._current_output_intent_source = intent.source
        self._last_write_result = write.message
        self._last_write_status = write.status
        if write.success:
            self._state = VirtualOutputWriteLoopState.RUNNING
            self._write_count += 1
            self._write_success_count += 1
            self._consecutive_write_failures = 0
            self._last_write_timestamp = now.isoformat()
            self._last_allowed_write_at = now
            self._accepted_write_times.append(now)
            self._last_skipped_write_reason = "None"
            return self.snapshot()
        self._record_write_failure(write)
        return self.snapshot()

    def snapshot(self) -> VirtualOutputLoopSnapshot:
        diagnostics = build_virtual_output_diagnostics(backend=self._backend, verification=self._verification)
        return VirtualOutputLoopSnapshot(
            state=self._state,
            enabled=self._enabled,
            backend_name=diagnostics.virtual_output_backend,
            selected_output_device=diagnostics.selected_output_device,
            verification_status=diagnostics.output_verification_status,
            output_write_status=self._last_write_status,
            write_rate_hz=self._config.safe_write_rate_hz,
            last_write_timestamp=self._last_write_timestamp,
            last_write_result=self._last_write_result,
            write_count=self._write_count,
            failure_count=self._failure_count,
            actual_write_rate_hz=self._actual_write_rate_hz(),
            tick_count=self._tick_count,
            write_attempt_count=self._write_attempt_count,
            write_success_count=self._write_success_count,
            write_failure_count=self._write_failure_count,
            write_skipped_count=self._write_skipped_count,
            write_skipped_rate_limited_count=self._write_skipped_rate_limited_count,
            write_skipped_disabled_count=self._write_skipped_disabled_count,
            write_skipped_unsafe_count=self._write_skipped_unsafe_count,
            write_skipped_safety_count=self._write_skipped_safety_count,
            consecutive_write_failures=self._consecutive_write_failures,
            last_write_duration_ms=self._last_write_duration_ms,
            last_allowed_write_at=self._last_allowed_write_at.isoformat() if self._last_allowed_write_at else None,
            last_skipped_write_reason=self._last_skipped_write_reason,
            last_error=self._last_error,
            neutral_restore_status=self._neutral_restore_status,
            neutral_restore_attempted=self._neutral_restore_attempted,
            neutral_restore_timestamp=self._neutral_restore_timestamp,
            neutral_restore_message=self._neutral_restore_message,
            neutral_restore_error=self._neutral_restore_error,
            neutral_restore_duration_ms=self._neutral_restore_duration_ms,
            safety_stop_reason=self._safety_stop_reason,
            safety_stop_timestamp=self._safety_stop_timestamp,
            current_output_intent_source=self._current_output_intent_source,
            fake_output_loop=self._is_fake_verified(),
            real_output_loop=self._is_real_verified(),
            full_live_runtime_ready=False,
        )

    def _record_skip(
        self,
        reason: str,
        *,
        rate_limited: bool = False,
        disabled: bool = False,
        unsafe: bool = False,
        safety: bool = False,
    ) -> None:
        self._write_skipped_count += 1
        if rate_limited:
            self._write_skipped_rate_limited_count += 1
        if disabled:
            self._write_skipped_disabled_count += 1
        if unsafe:
            self._write_skipped_unsafe_count += 1
        if safety:
            self._write_skipped_safety_count += 1
        self._last_skipped_write_reason = reason
        self._last_write_status = reason
        self._last_write_result = f"Output write skipped: {reason}."

    def _record_write_failure(self, write: VirtualOutputWriteResult) -> None:
        self._write_failure_count += 1
        self._failure_count += 1
        self._consecutive_write_failures += 1
        self._last_error = write.message
        if self._config.safety_stop_on_write_failure or self._consecutive_write_failures >= max(1, self._config.max_consecutive_write_failures):
            self._enabled = False
            self._state = VirtualOutputWriteLoopState.SAFETY_STOPPED
            self._safety_stop_reason = write.status or "write_failed"
            if self._safety_stop_reason not in {"write_failed", "error"}:
                self._safety_stop_reason = write.status
            self._safety_stop_timestamp = self._now().isoformat()
            if self._config.restore_neutral_on_safety_stop:
                self._attempt_neutral_restore()
            return
        self._state = VirtualOutputWriteLoopState.ERROR_WRITE_FAILED

    def _attempt_neutral_restore(self) -> VirtualOutputWriteResult:
        started = time.perf_counter()
        self._neutral_restore_attempted = True
        try:
            restore = self._backend.write_output_intent(build_neutral_virtual_output_intent(timestamp=self._now()))
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            restore = VirtualOutputWriteResult(
                success=False,
                status="neutral_restore_failed",
                message=str(exc),
                backend_name=self._backend.get_capabilities().backend_name,
                errors=(str(exc),),
            )
        self._neutral_restore_duration_ms = _elapsed_ms(started)
        self._neutral_restore_timestamp = self._now().isoformat()
        self._neutral_restore_message = restore.message
        self._last_write_result = restore.message
        self._last_write_status = restore.status
        if restore.success:
            self._neutral_restore_status = "restored"
            self._neutral_restore_error = ""
        else:
            self._neutral_restore_status = "failed"
            self._neutral_restore_error = restore.message
        return restore

    def _actual_write_rate_hz(self) -> float | None:
        if len(self._accepted_write_times) < 2:
            return None
        elapsed = (self._accepted_write_times[-1] - self._accepted_write_times[0]).total_seconds()
        if elapsed <= 0:
            return None
        return round((len(self._accepted_write_times) - 1) / elapsed, 3)

    def _gate_state(self) -> VirtualOutputWriteLoopState:
        capabilities = self._backend.get_capabilities()
        if not capabilities.backend_available:
            if capabilities.backend_kind == "missing":
                return VirtualOutputWriteLoopState.UNAVAILABLE_BACKEND_MISSING
            return VirtualOutputWriteLoopState.UNAVAILABLE_BACKEND_MISSING
        if capabilities.backend_kind != "fake" and not self._backend.enumerate_output_devices():
            return VirtualOutputWriteLoopState.UNAVAILABLE_DEVICE_MISSING
        if self._config.require_verification and not self._is_verified_for_backend(capabilities.backend_kind):
            return VirtualOutputWriteLoopState.UNAVAILABLE_UNVERIFIED
        if capabilities.backend_kind == "fake" and not self._config.allow_fake_backend:
            return VirtualOutputWriteLoopState.UNAVAILABLE_UNVERIFIED
        if capabilities.backend_kind == "real_vjoy" and not self._config.allow_real_backend:
            return VirtualOutputWriteLoopState.UNAVAILABLE_UNVERIFIED
        return VirtualOutputWriteLoopState.READY_VERIFIED

    def _is_verified_for_backend(self, backend_kind: str) -> bool:
        if self._verification is None:
            return False
        if backend_kind == "fake":
            return self._verification.fake_output_verified and self._verification.status is VirtualOutputVerificationStatus.FAKE_VERIFIED
        if backend_kind == "real_vjoy":
            return self._verification.real_output_verified and self._verification.status is VirtualOutputVerificationStatus.REAL_VERIFIED
        return False

    def _is_fake_verified(self) -> bool:
        return self._verification is not None and self._verification.fake_output_verified and not self._verification.real_output_verified

    def _is_real_verified(self) -> bool:
        return self._verification is not None and self._verification.real_output_verified

    def _now(self) -> datetime:
        if callable(self._clock):
            value = self._clock()
            if isinstance(value, datetime):
                return value
        return datetime.now(timezone.utc)


def build_neutral_virtual_output_intent(*, timestamp: datetime | None = None) -> VirtualOutputIntent:
    return VirtualOutputIntent(
        timestamp=timestamp or datetime.now(timezone.utc),
        source="neutral_restore",
        axes=tuple(VirtualAxisOutput(axis, 0.0) for axis in ("X", "Y", "Z", "RX", "RY", "RZ")),
        buttons=tuple(VirtualButtonOutput(f"Out{index}", False) for index in range(1, 21)),
        hats=(VirtualHatOutput("POV1", "Centered"),),
        warnings=(
            "neutral restore output intent",
            "axes set to zero, buttons released, hats centered",
            "throttle neutral uses zero until a later output policy proves another safe default",
        ),
        output_enabled=False,
        write_requested=True,
    )


def find_vjoy_backend_name() -> str | None:
    library_name = ctypes.util.find_library("vJoyInterface")
    if library_name:
        return library_name

    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if not root:
            continue
        candidate = Path(root) / "vJoy" / "x64" / "vJoyInterface.dll"
        if candidate.exists():
            return str(candidate)

    return None


def detect_vjoy_backend() -> OutputBackendDetection:
    try:
        backend_name = find_vjoy_backend_name()
    except Exception as exc:  # pragma: no cover - defensive boundary
        return OutputBackendDetection(
            status=OutputStatus.OUTPUT_ERROR,
            errors=(f"vJoy detection failed: {exc}",),
        )

    if backend_name is None:
        return OutputBackendDetection(
            status=OutputStatus.VJOY_MISSING,
            warnings=("vJoy output backend is missing; live output writes are unavailable.",),
        )

    return OutputBackendDetection(
        status=OutputStatus.VJOY_DETECTED,
        backend_name=backend_name,
        live_output_writes_verified=False,
        messages=("vJoy output backend was detected, but Phase 1 does not verify output writes.",),
        warnings=("No live vJoy output write has been verified.",),
    )


class VJoyOutputAdapter:
    def __init__(self, backend_name: str | None = None) -> None:
        self._backend_name = backend_name

    def detect(self) -> OutputBackendDetection:
        if self._backend_name is not None:
            return OutputBackendDetection(
                status=OutputStatus.VJOY_DETECTED,
                backend_name=self._backend_name,
                live_output_writes_verified=False,
                messages=("vJoy output backend was supplied but output writes are not verified.",),
                warnings=("Phase 1 does not implement real vJoy writes.",),
            )
        return detect_vjoy_backend()

    def verify_output_writes(self) -> bool:
        return False

    def write_outputs(self, axis_values: Mapping[str, float]) -> OutputWriteResult:
        _ = axis_values
        return OutputWriteResult(
            success=False,
            message="Real vJoy output writes are not implemented or verified in Phase 1.",
        )


def build_recovered_virtual_output_intent(
    raw_axes: Mapping[str, float],
    *,
    source: str = "shared_core_pipeline",
    timestamp: datetime | None = None,
) -> VirtualOutputIntent:
    axes = tuple(
        VirtualAxisOutput(axis_name=virtual_axis, value=_safe_float(raw_axes.get(logical_axis), 0.0))
        for logical_axis, virtual_axis in RECOVERED_AXIS_OUTPUT_ROUTES.items()
    )
    return VirtualOutputIntent(
        timestamp=timestamp or datetime.now(timezone.utc),
        source=source,
        axes=axes,
        buttons=tuple(VirtualButtonOutput(f"Out{index}", False) for index in range(1, 21)),
        hats=(VirtualHatOutput("POV1", "Centered"),),
        warnings=(
            "output intent is not output write proof",
            "Recovered route intent: Roll->X, Pitch->Y, Throttle->Z, Yaw->RX, Aux 1->RY, Aux 2->RZ.",
        ),
        output_enabled=False,
        write_requested=False,
    )


def build_workspace_virtual_output_intent(
    final_axes: Mapping[str, float],
    *,
    button_states: Mapping[str, bool] | None = None,
    hat_state: str = "Centered",
    workspace: WorkspaceConfig | None = None,
    source: str = "shared_core_pipeline",
    timestamp: datetime | None = None,
) -> VirtualOutputIntent:
    if workspace is None:
        return build_recovered_virtual_output_intent(final_axes, source=source, timestamp=timestamp)

    axis_values = {axis: 0.0 for axis in _VJOY_AXIS_USAGE}
    mapped_axes: list[str] = []
    for route in workspace.mappings.axis_routes:
        output_axis = _axis_label(route.runtime_vjoy_output or route.logical_output)
        if output_axis not in axis_values:
            continue
        axis_values[output_axis] = _safe_float(final_axes.get(route.function_name), 0.0)
        mapped_axes.append(f"{route.function_name}->{output_axis}")

    output_buttons = {index: False for index in range(1, 21)}
    for route in workspace.mappings.button_routes:
        if not 1 <= int(route.output_button) <= 128:
            continue
        pressed = _button_pressed(button_states or {}, route.hotas_button)
        if 1 <= int(route.output_button) <= 20:
            output_buttons[int(route.output_button)] = output_buttons[int(route.output_button)] or pressed

    normalized_hat_state = _normalize_hat_state(hat_state)
    for route in workspace.mappings.hat_routes:
        for output_button in _hat_button_targets(route, normalized_hat_state):
            output_buttons[output_button] = True

    return VirtualOutputIntent(
        timestamp=timestamp or datetime.now(timezone.utc),
        source=source,
        axes=tuple(VirtualAxisOutput(axis, axis_values[axis]) for axis in ("X", "Y", "Z", "RX", "RY", "RZ")),
        buttons=tuple(VirtualButtonOutput(f"Out{index}", output_buttons[index]) for index in range(1, 21)),
        hats=(VirtualHatOutput("POV1", normalized_hat_state),),
        warnings=(
            "output intent is not output write proof",
            "Workspace route intent: " + ", ".join(mapped_axes),
        ),
        output_enabled=False,
        write_requested=False,
    )


def build_safe_vjoy_verification_intent(
    *,
    source: str = "guarded_verification",
    timestamp: datetime | None = None,
) -> VirtualOutputIntent:
    return VirtualOutputIntent(
        timestamp=timestamp or datetime.now(timezone.utc),
        source=source,
        axes=(
            VirtualAxisOutput("X", 0.05),
            VirtualAxisOutput("Y", 0.0),
            VirtualAxisOutput("Z", 0.0),
            VirtualAxisOutput("RX", 0.0),
            VirtualAxisOutput("RY", 0.0),
            VirtualAxisOutput("RZ", 0.0),
        ),
        buttons=tuple(VirtualButtonOutput(f"Out{index}", False) for index in range(1, 21)),
        hats=(VirtualHatOutput("POV1", "Centered"),),
        warnings=(
            "bounded verification write only",
            "neutral restore is attempted after a real verification write",
            "output intent is not output write proof until guarded verification succeeds",
        ),
        output_enabled=False,
        write_requested=True,
    )


def _bounded_loop_intent(output_intent: VirtualOutputIntent, *, timestamp: datetime) -> VirtualOutputIntent:
    return VirtualOutputIntent(
        timestamp=timestamp,
        source=output_intent.source or "unknown",
        axes=tuple(VirtualAxisOutput(axis.axis_name, axis.value) for axis in output_intent.axes),
        buttons=tuple(VirtualButtonOutput(button.button_name, button.pressed) for button in output_intent.buttons),
        hats=tuple(VirtualHatOutput(hat.hat_name, hat.value) for hat in output_intent.hats),
        warnings=tuple(output_intent.warnings)
        + (
            "output loop write requires explicit enable and verified backend",
            "output loop intent values are clamped before write",
        ),
        output_enabled=True,
        write_requested=True,
    )


def _axis_label(runtime_vjoy_output: str) -> str:
    text = str(runtime_vjoy_output or "").strip()
    if "(" in text:
        text = text.split("(", 1)[0]
    return text.upper() or "X"


def _button_pressed(button_states: Mapping[str, bool], hotas_button: int) -> bool:
    direct = button_states.get(f"B{int(hotas_button)}")
    if direct is not None:
        return bool(direct)
    numeric = button_states.get(str(int(hotas_button)))
    if numeric is not None:
        return bool(numeric)
    return bool(button_states.get(int(hotas_button)))  # type: ignore[arg-type]


_VALID_HAT_STATES = {
    "centered": "Centered",
    "center": "Centered",
    "neutral": "Centered",
    "north": "Up",
    "up": "Up",
    "northeast": "UpRight",
    "north east": "UpRight",
    "upright": "UpRight",
    "up right": "UpRight",
    "east": "Right",
    "right": "Right",
    "southeast": "DownRight",
    "south east": "DownRight",
    "downright": "DownRight",
    "down right": "DownRight",
    "south": "Down",
    "down": "Down",
    "southwest": "DownLeft",
    "south west": "DownLeft",
    "downleft": "DownLeft",
    "down left": "DownLeft",
    "west": "Left",
    "left": "Left",
    "northwest": "UpLeft",
    "north west": "UpLeft",
    "upleft": "UpLeft",
    "up left": "UpLeft",
}


def _normalize_hat_state(hat_state: object) -> str:
    text = str(hat_state or "Centered").strip()
    normalized = text.replace("-", " ").replace("_", " ").casefold()
    compact = normalized.replace(" ", "")
    return _VALID_HAT_STATES.get(normalized) or _VALID_HAT_STATES.get(compact) or "Centered"


def _hat_button_targets(route: object, normalized_hat_state: str) -> tuple[int, ...]:
    directions = _hat_cardinal_directions(normalized_hat_state)
    targets: list[int] = []
    for direction in directions:
        target = _safe_output_button(getattr(route, f"{direction}_button", None))
        if target is not None:
            targets.append(target)
    return tuple(targets)


def _hat_cardinal_directions(normalized_hat_state: str) -> tuple[str, ...]:
    return {
        "Up": ("up",),
        "Right": ("right",),
        "Down": ("down",),
        "Left": ("left",),
        "UpRight": ("up", "right"),
        "DownRight": ("down", "right"),
        "DownLeft": ("down", "left"),
        "UpLeft": ("up", "left"),
    }.get(normalized_hat_state, ())


def _safe_output_button(value: object) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if 1 <= number <= 20:
        return number
    return None


def build_virtual_output_diagnostics(
    *,
    backend: VirtualOutputBackend | None = None,
    verification: VirtualOutputVerificationResult | None = None,
    write_result: VirtualOutputWriteResult | None = None,
) -> VirtualOutputDiagnostics:
    backend = backend or MissingVirtualOutputBackend()
    capabilities = backend.get_capabilities()
    status = backend.get_status()
    devices = backend.enumerate_output_devices()
    dependency_status = _availability_text(capabilities.dependency_available)
    vjoy_device_status = _vjoy_device_status(status.status, devices)
    selected_output_device = "None"
    device_status = "No virtual output device selected"
    if devices:
        selected = next((device for device in devices if device.is_selected), devices[0])
        selected_output_device = selected.display_name
        device_status = f"{selected.display_name}; unverified"
    write_status = "Not active"
    if write_result is not None:
        write_status = write_result.status
    if verification is None:
        verification_status = VirtualOutputVerificationStatus.NOT_ATTEMPTED.value
        verification_source = "not attempted"
        fake_verified = False
        real_verified = False
        verification_timestamp = "Unavailable"
        verification_error = "None"
        verification_warnings = "None"
    else:
        verification_status = verification.status.value
        verification_source = verification.source
        fake_verified = verification.fake_output_verified
        real_verified = verification.real_output_verified
        verification_timestamp = verification.verified_at.isoformat() if verification.verified_at is not None else "Unavailable"
        verification_error = "; ".join(verification.errors) if verification.errors else "None"
        verification_warnings = "; ".join(verification.warnings) if verification.warnings else "None"
    return VirtualOutputDiagnostics(
        virtual_output_backend=capabilities.backend_name,
        virtual_output_backend_kind=capabilities.backend_kind,
        virtual_output_backend_status=status.status,
        vjoy_dependency_status=dependency_status,
        vjoy_device_status=vjoy_device_status,
        selected_output_device=selected_output_device,
        output_device_status=device_status,
        output_write_status=write_status,
        output_verification_status=verification_status,
        output_verification_source=verification_source,
        fake_output_verified=fake_verified,
        real_output_verified=real_verified,
        output_verified=real_verified,
        full_live_runtime_ready=False,
        last_verification_timestamp=verification_timestamp,
        last_verification_error=verification_error,
        last_verification_warnings=verification_warnings,
    )


def _clamp_axis_value(value: object) -> float:
    return max(-1.0, min(1.0, _safe_float(value, 0.0)))


def _provider_attr(provider: object, name: str, default: object) -> object:
    value = getattr(provider, name, default)
    if callable(value):
        try:
            return value()
        except TypeError:
            return default
    return value


def _provider_call(provider: object, name: str, *args: object) -> object:
    method = getattr(provider, name, None)
    if not callable(method):
        raise RuntimeError(f"Real vJoy provider does not support {name}.")
    return method(*args)


def _provider_warnings(provider: object) -> tuple[str, ...]:
    return tuple(str(item) for item in _sequence(_provider_attr(provider, "warnings", ())))


def _provider_errors(provider: object) -> tuple[str, ...]:
    return tuple(str(item) for item in _sequence(_provider_attr(provider, "errors", ())))


def _device_number(device_id: str) -> int:
    try:
        return max(1, int(str(device_id).replace("vjoy:", "")))
    except ValueError:
        return 1


def _vjoy_status_text(status: int) -> str:
    return {
        _VJOY_STATUS_OWN: "own",
        _VJOY_STATUS_FREE: "free",
        _VJOY_STATUS_BUSY: "device_busy",
        _VJOY_STATUS_MISSING: "device_missing",
        _VJOY_STATUS_UNKNOWN: "unknown",
    }.get(int(status), "unknown")


def _axis_to_vjoy_value(value: float) -> int:
    clamped = max(-1.0, min(1.0, float(value)))
    return int(round(1 + ((clamped + 1.0) / 2.0) * 32767))


def _hat_to_vjoy_value(value: str) -> int:
    text = str(value or "Centered").strip().lower().replace("-", " ")
    if text in {"center", "centered", "neutral", "none"}:
        return 0xFFFFFFFF
    degrees = {
        "north": 0,
        "up": 0,
        "north east": 45,
        "east": 90,
        "right": 90,
        "south east": 135,
        "south": 180,
        "down": 180,
        "south west": 225,
        "west": 270,
        "left": 270,
        "north west": 315,
    }.get(text, 0)
    return int(degrees * 100)


def _coerce_device_info(value: object, *, backend_name: str) -> VirtualOutputDeviceInfo:
    if isinstance(value, VirtualOutputDeviceInfo):
        return value
    if isinstance(value, Mapping):
        return VirtualOutputDeviceInfo(
            device_id=str(value.get("device_id") or value.get("id") or "unknown"),
            display_name=str(value.get("display_name") or value.get("name") or "vJoy Device"),
            backend_name=str(value.get("backend_name") or backend_name),
            is_selected=bool(value.get("is_selected", False)),
            is_supported=bool(value.get("is_supported", True)),
            axis_support=tuple(str(item) for item in _sequence(value.get("axis_support"))),
            button_count=_safe_int(value.get("button_count")),
            hat_support=str(value.get("hat_support") or "unknown"),
            acquisition_status=str(value.get("acquisition_status") or "unknown"),
            warnings=tuple(str(item) for item in _sequence(value.get("warnings"))),
            errors=tuple(str(item) for item in _sequence(value.get("errors"))),
        )
    return VirtualOutputDeviceInfo(
        device_id=str(value),
        display_name=str(value),
        backend_name=backend_name,
    )


def _mark_device_selected(device: VirtualOutputDeviceInfo, selected_id: str) -> VirtualOutputDeviceInfo:
    return VirtualOutputDeviceInfo(
        device_id=device.device_id,
        display_name=device.display_name,
        backend_name=device.backend_name,
        is_selected=device.device_id == selected_id,
        is_supported=device.is_supported,
        axis_support=device.axis_support,
        button_count=device.button_count,
        hat_support=device.hat_support,
        acquisition_status=device.acquisition_status,
        warnings=device.warnings,
        errors=device.errors,
    )


def _coerce_operation_result(value: object) -> VJoyProviderOperationResult:
    if isinstance(value, VJoyProviderOperationResult):
        return value
    if isinstance(value, Mapping):
        return VJoyProviderOperationResult(
            success=bool(value.get("success", False)),
            status=str(value.get("status") or "error"),
            message=str(value.get("message") or value.get("status") or "Real vJoy operation failed."),
            warnings=tuple(str(item) for item in _sequence(value.get("warnings"))),
            errors=tuple(str(item) for item in _sequence(value.get("errors"))),
        )
    return VJoyProviderOperationResult(
        success=bool(getattr(value, "success", False)),
        status=str(getattr(value, "status", "error")),
        message=str(getattr(value, "message", "Real vJoy operation failed.")),
        warnings=tuple(str(item) for item in _sequence(getattr(value, "warnings", ()))),
        errors=tuple(str(item) for item in _sequence(getattr(value, "errors", ()))),
    )


def _verification_status_from_operation(
    status: str,
    *,
    acquire_default: VirtualOutputVerificationStatus,
) -> VirtualOutputVerificationStatus:
    if status == VirtualOutputVerificationStatus.DEVICE_BUSY.value:
        return VirtualOutputVerificationStatus.DEVICE_BUSY
    if status == VirtualOutputVerificationStatus.ACQUISITION_FAILED.value:
        return VirtualOutputVerificationStatus.ACQUISITION_FAILED
    if status == VirtualOutputVerificationStatus.DEVICE_MISSING.value:
        return VirtualOutputVerificationStatus.DEVICE_MISSING
    if status == VirtualOutputVerificationStatus.UNSUPPORTED.value:
        return VirtualOutputVerificationStatus.UNSUPPORTED
    return acquire_default


def _availability_text(value: bool | None) -> str:
    if value is True:
        return "Available"
    if value is False:
        return "Missing"
    return "Unknown"


def _vjoy_device_status(status: str, devices: tuple[VirtualOutputDeviceInfo, ...]) -> str:
    if devices:
        return "Detected"
    if status == "device_missing":
        return "Missing"
    if status in {"dependency_missing", "backend_missing"}:
        return "Unknown"
    return "Unknown"


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _elapsed_ms(started: float) -> float:
    return round(max(0.0, (time.perf_counter() - started) * 1000.0), 3)


def _safe_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _parse_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return datetime.fromtimestamp(0, tz=timezone.utc)
    return datetime.fromtimestamp(0, tz=timezone.utc)


def _sequence(value: object) -> tuple[object, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return ()


def _sequence_of_mappings(value: object) -> tuple[Mapping[str, object], ...]:
    return tuple(item for item in _sequence(value) if isinstance(item, Mapping))
