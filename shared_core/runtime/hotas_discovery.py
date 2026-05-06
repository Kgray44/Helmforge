from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from shared_core.runtime.device_discovery import enumerate_input_device_names, is_likely_target_hotas_name


class DeviceDiscoveryState(str, Enum):
    NOT_CHECKED = "not_checked"
    NO_SUPPORTED_DEVICE = "no_supported_device"
    SUPPORTED_DEVICE_DETECTED = "supported_device_detected"
    DISCOVERY_ERROR = "discovery_error"
    BACKEND_UNAVAILABLE = "backend_unavailable"


@dataclass(frozen=True)
class HotasDeviceInfo:
    device_name: str
    manufacturer: str | None = None
    vendor_id: str | None = None
    product_id: str | None = None
    serial_number: str | None = None
    backend: str = "unknown"

    def to_dict(self) -> dict[str, object]:
        return {
            "device_name": self.device_name,
            "manufacturer": self.manufacturer,
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "serial_number": self.serial_number,
            "backend": self.backend,
        }


@dataclass(frozen=True)
class HotasDiscoveryResult:
    status: DeviceDiscoveryState = DeviceDiscoveryState.NOT_CHECKED
    available: bool = False
    matched: bool = False
    device_name: str | None = None
    manufacturer: str | None = None
    vendor_id: str | None = None
    product_id: str | None = None
    serial_number: str | None = None
    backend: str = "unknown"
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "available": self.available,
            "matched": self.matched,
            "device_name": self.device_name,
            "manufacturer": self.manufacturer,
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "serial_number": self.serial_number,
            "backend": self.backend,
            "checked_at": self.checked_at.isoformat(),
            "error": self.error,
            "warnings": list(self.warnings),
        }


class DeviceDiscoveryBackendUnavailable(RuntimeError):
    pass


class DeviceDiscoveryBackend(Protocol):
    backend_name: str

    def enumerate_devices(self) -> tuple[HotasDeviceInfo, ...]:
        ...


@dataclass(frozen=True)
class FakeDeviceDiscoveryBackend:
    devices: tuple[HotasDeviceInfo, ...] = ()
    backend_name: str = "fake"
    available: bool = True
    error: Exception | None = None

    def enumerate_devices(self) -> tuple[HotasDeviceInfo, ...]:
        if not self.available:
            raise DeviceDiscoveryBackendUnavailable("Fake discovery backend is unavailable.")
        if self.error is not None:
            raise self.error
        return self.devices


class WindowsPnpDeviceDiscoveryBackend:
    backend_name = "windows_pnp"

    def enumerate_devices(self) -> tuple[HotasDeviceInfo, ...]:
        names = enumerate_input_device_names()
        if not names:
            return ()
        return tuple(_device_from_pnp_name(name, backend=self.backend_name) for name in names)


def discover_supported_hotas(
    *,
    backend: DeviceDiscoveryBackend | None = None,
    clock=None,
) -> HotasDiscoveryResult:
    active_backend = backend or WindowsPnpDeviceDiscoveryBackend()
    checked_at = _now(clock)
    backend_name = getattr(active_backend, "backend_name", "unknown")
    try:
        devices = active_backend.enumerate_devices()
    except DeviceDiscoveryBackendUnavailable as exc:
        return HotasDiscoveryResult(
            status=DeviceDiscoveryState.BACKEND_UNAVAILABLE,
            backend=backend_name,
            checked_at=checked_at,
            error=str(exc),
            warnings=("HOTAS discovery backend is unavailable; discovery is read-only and non-fatal.",),
        )
    except Exception as exc:
        return HotasDiscoveryResult(
            status=DeviceDiscoveryState.DISCOVERY_ERROR,
            backend=backend_name,
            checked_at=checked_at,
            error=str(exc),
            warnings=("HOTAS discovery failed; HelmForge remains in simulation/fallback mode.",),
        )

    for device in devices:
        if is_supported_hotas_device(device):
            return HotasDiscoveryResult(
                status=DeviceDiscoveryState.SUPPORTED_DEVICE_DETECTED,
                available=True,
                matched=True,
                device_name=device.device_name,
                manufacturer=device.manufacturer,
                vendor_id=device.vendor_id,
                product_id=device.product_id,
                serial_number=device.serial_number,
                backend=device.backend or backend_name,
                checked_at=checked_at,
                warnings=("Supported HOTAS detected; polling is not active in Phase 9H.",),
            )

    return HotasDiscoveryResult(
        status=DeviceDiscoveryState.NO_SUPPORTED_DEVICE,
        backend=backend_name,
        checked_at=checked_at,
        warnings=("No supported HOTAS device was found during read-only discovery.",),
    )


def is_supported_hotas_device(device: HotasDeviceInfo) -> bool:
    vendor_id = _normalize_hex(device.vendor_id)
    product_id = _normalize_hex(device.product_id)
    if vendor_id == "044f" and product_id == "b68d":
        return True
    return is_likely_target_hotas_name(" ".join(part for part in (device.manufacturer, device.device_name) if part))


def _device_from_pnp_name(name: str, *, backend: str) -> HotasDeviceInfo:
    return HotasDeviceInfo(
        device_name=name,
        manufacturer="Thrustmaster" if "thrustmaster" in name.lower() else None,
        vendor_id=_extract_usb_part(name, "vid"),
        product_id=_extract_usb_part(name, "pid"),
        backend=backend,
    )


def _extract_usb_part(text: str, prefix: str) -> str | None:
    match = re.search(rf"{prefix}[_-]?([0-9a-fA-F]{{4}})", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None


def _normalize_hex(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9a-fA-F]", "", value).lower()
    return cleaned or None


def _now(clock) -> datetime:
    value = clock() if clock is not None else datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
