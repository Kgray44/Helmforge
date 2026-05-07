from __future__ import annotations

import re
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
    optional_dependency_available: bool = True
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PhysicalInputBackendStatus:
    status: str
    backend_name: str
    message: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


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
    ) -> None:
        self._devices = tuple(devices)
        self._backend_name = backend_name
        self._backend_available = backend_available
        self._sample_frames = tuple(sample_frames)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._disconnected = disconnected
        self._sampling_error = sampling_error
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
                sample_source="fake",
                errors=("No physical input device is open.",),
            )
        device = self._device_by_id(self._open_device_id)
        if device is None or self._disconnected:
            return _empty_snapshot(
                device_id=self._open_device_id,
                device_name=device.display_name if device else "Missing",
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.DEVICE_MISSING,
                sample_source="fake",
                errors=("Fake physical input device disconnected.",),
            )
        if self._sampling_error:
            return _empty_snapshot(
                device_id=device.device_id,
                device_name=device.display_name,
                backend_name=self._backend_name,
                status=PhysicalInputSamplingStatus.ERROR,
                sample_source="fake",
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
            sample_source="fake",
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
            warnings=("Windows PnP discovery does not poll live HOTAS state.",),
        )


def build_default_physical_input_backend() -> PhysicalInputBackend:
    import os

    if os.name == "nt":
        return WindowsPhysicalInputDiscoveryBackend()
    return MissingPhysicalInputBackend(reason="Physical input discovery is not available on this platform yet.")


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


@dataclass
class PhysicalInputSampler:
    backend: PhysicalInputBackend
    selected_device_id: str | None = None
    latest_snapshot: PhysicalInputSnapshot | None = None

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


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
