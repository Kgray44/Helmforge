from __future__ import annotations

from collections.abc import Iterable

from shared_core.models.runtime import InputDeviceDetection, KNOWN_TARGET_HARDWARE
from shared_core.runtime.device_discovery import detect_input_devices, enumerate_input_device_names


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

