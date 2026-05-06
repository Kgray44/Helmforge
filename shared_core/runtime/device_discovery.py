from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Iterable

from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _compact(value: str) -> str:
    return _NON_ALNUM_RE.sub("", value.lower())


def is_likely_target_hotas_name(device_name: str) -> bool:
    raw = device_name.lower()
    compact = _compact(device_name)
    has_vendor = "thrustmaster" in compact
    has_tflight = (
        "t.flight" in raw
        or "t-flight" in raw
        or "t flight" in raw
        or "tflight" in compact
        or "flight" in compact
    )
    has_hotas_one = "hotasone" in compact or ("hotas" in compact and "one" in compact)
    return has_vendor and has_tflight and has_hotas_one


def enumerate_input_device_names() -> tuple[str, ...]:
    if os.name != "nt":
        return ()

    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-PnpDevice -PresentOnly | Where-Object { $_.FriendlyName } | Select-Object -ExpandProperty FriendlyName",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ()

    if completed.returncode != 0:
        return ()

    return tuple(line.strip() for line in completed.stdout.splitlines() if line.strip())


def detect_input_devices(device_names: Iterable[str] | None = None) -> InputDeviceDetection:
    names = tuple(device_names) if device_names is not None else enumerate_input_device_names()
    matches = tuple(name for name in names if is_likely_target_hotas_name(name))

    if matches:
        return InputDeviceDetection(
            status=InputStatus.DETECTED,
            detected_device_names=matches,
            messages=("Target HOTAS input device was detected.",),
        )

    return InputDeviceDetection(
        status=InputStatus.MISSING,
        warnings=(
            "Target HOTAS input device was not detected; HelmForge can continue in simulation mode.",
        ),
    )


def _detect_output_from_names(output_backend_names: Iterable[str]) -> OutputBackendDetection:
    for name in output_backend_names:
        if "vjoy" in name.lower():
            return OutputBackendDetection(
                status=OutputStatus.VJOY_DETECTED,
                backend_name=name,
                live_output_writes_verified=False,
                messages=("vJoy output backend was detected but output writes are not verified in Phase 1.",),
                warnings=("Live output writes are not implemented or verified yet.",),
            )

    return OutputBackendDetection(
        status=OutputStatus.VJOY_MISSING,
        warnings=("vJoy output backend was not detected; live output is unavailable.",),
    )


def detect_output_backends(output_backend_names: Iterable[str] | None = None) -> OutputBackendDetection:
    if output_backend_names is not None:
        return _detect_output_from_names(output_backend_names)

    from shared_core.runtime.vjoy_output import detect_vjoy_backend

    return detect_vjoy_backend()


def build_runtime_preflight_status(
    *,
    input_device_names: Iterable[str] | None = None,
    output_backend_names: Iterable[str] | None = None,
) -> RuntimePreflightStatus:
    input_detection = detect_input_devices(input_device_names)
    output_detection = detect_output_backends(output_backend_names)

    messages: list[str] = []
    warnings = [*input_detection.warnings, *output_detection.warnings]
    errors = [*input_detection.errors, *output_detection.errors]

    if input_detection.status is InputStatus.ERROR or output_detection.status is OutputStatus.OUTPUT_ERROR:
        return RuntimePreflightStatus(
            mode=RuntimeMode.UNAVAILABLE,
            truth=RuntimeTruth.ERROR,
            input=input_detection,
            output=output_detection,
            messages=tuple(messages),
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    input_detected = input_detection.status is InputStatus.DETECTED
    output_detected = output_detection.status in {
        OutputStatus.VJOY_DETECTED,
        OutputStatus.OUTPUT_VERIFIED,
    }
    output_verified = (
        output_detection.status is OutputStatus.OUTPUT_VERIFIED
        and output_detection.live_output_writes_verified
    )

    if input_detected and output_verified:
        messages.append("Physical HOTAS input and live output writes are verified.")
        return RuntimePreflightStatus(
            mode=RuntimeMode.FULL_LIVE,
            truth=RuntimeTruth.LIVE_VERIFIED,
            input=input_detection,
            output=output_detection,
            messages=tuple(messages),
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    messages.append("Simulation mode selected because live HOTAS/vJoy output is not fully verified.")

    if input_detected and output_detection.status is OutputStatus.VJOY_MISSING:
        truth = RuntimeTruth.BLOCKED_MISSING_DRIVER
        warnings.append("vJoy is missing, so detected HOTAS input cannot be used for live output.")
    elif not input_detected and output_detected:
        truth = RuntimeTruth.BLOCKED_MISSING_DEVICE
        warnings.append("vJoy is present or hinted, but the target HOTAS is missing.")
    elif input_detected and output_detected:
        truth = RuntimeTruth.DETECTED_UNVERIFIED
        warnings.append("Input/output pieces were detected, but live output writes are not verified.")
    else:
        truth = RuntimeTruth.SIMULATED
        warnings.append("Neither the target HOTAS nor verified vJoy output is available.")

    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=truth,
        input=input_detection,
        output=output_detection,
        messages=tuple(messages),
        warnings=tuple(warnings),
        errors=tuple(errors),
    )

