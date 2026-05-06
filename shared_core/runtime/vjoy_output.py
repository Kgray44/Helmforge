from __future__ import annotations

import ctypes.util
import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from shared_core.models.runtime import OutputBackendDetection, OutputStatus


@dataclass(frozen=True)
class OutputWriteResult:
    success: bool
    message: str


def find_vjoy_backend_name() -> str | None:
    for module_name in ("pyvjoy", "vjoy"):
        if importlib.util.find_spec(module_name) is not None:
            return module_name

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

