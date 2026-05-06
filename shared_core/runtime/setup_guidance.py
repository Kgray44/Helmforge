from __future__ import annotations

from enum import Enum

from shared_core.models.runtime import InputStatus, OutputStatus, RuntimeMode, RuntimePreflightStatus


OFFICIAL_THRUSTMASTER_SUPPORT_PAGE = "https://support.thrustmaster.com/en/product/t-flight-hotas-one-en/"
CURRENT_THRUSTMASTER_DRIVER_PACKAGE_NOTE = "Drivers - Package 2025_TFHT_5 + Firmware"
CURRENT_THRUSTMASTER_SYSTEM_REQUIREMENT_NOTE = "Windows 10 / Windows 11"


class SetupStatusLabel(Enum):
    THRUSTMASTER_DRIVER_UNKNOWN = "Thrustmaster Driver Unknown"
    THRUSTMASTER_DRIVER_DETECTED = "Thrustmaster Driver Detected"
    THRUSTMASTER_DRIVER_MISSING = "Thrustmaster Driver Missing"
    HOTAS_NOT_CONNECTED = "HOTAS Not Connected"
    T_FLIGHT_HOTAS_ONE_DETECTED = "T-Flight HOTAS One Detected"
    INPUT_READY = "Input Ready"
    VJOY_MISSING = "vJoy Missing"
    VJOY_DETECTED = "vJoy Detected"
    SIMULATION_MODE_ACTIVE = "Simulation Mode Active"
    FULL_LIVE_RUNTIME_READY = "Full Live Runtime Ready"


def build_setup_status_labels(
    runtime_status: RuntimePreflightStatus,
    *,
    thrustmaster_driver_detected: bool | None = None,
) -> tuple[SetupStatusLabel, ...]:
    labels: list[SetupStatusLabel] = []

    if thrustmaster_driver_detected is True:
        labels.append(SetupStatusLabel.THRUSTMASTER_DRIVER_DETECTED)
    elif thrustmaster_driver_detected is False:
        labels.append(SetupStatusLabel.THRUSTMASTER_DRIVER_MISSING)
    else:
        labels.append(SetupStatusLabel.THRUSTMASTER_DRIVER_UNKNOWN)

    if runtime_status.input.status is InputStatus.DETECTED:
        labels.append(SetupStatusLabel.T_FLIGHT_HOTAS_ONE_DETECTED)
        labels.append(SetupStatusLabel.INPUT_READY)
    else:
        labels.append(SetupStatusLabel.HOTAS_NOT_CONNECTED)

    if runtime_status.output.status is OutputStatus.VJOY_MISSING:
        labels.append(SetupStatusLabel.VJOY_MISSING)
    elif runtime_status.output.status in {OutputStatus.VJOY_DETECTED, OutputStatus.OUTPUT_VERIFIED}:
        labels.append(SetupStatusLabel.VJOY_DETECTED)

    if runtime_status.mode is RuntimeMode.SIMULATED:
        labels.append(SetupStatusLabel.SIMULATION_MODE_ACTIVE)

    if runtime_status.mode is RuntimeMode.FULL_LIVE and runtime_status.live_output_writes_verified:
        labels.append(SetupStatusLabel.FULL_LIVE_RUNTIME_READY)

    return tuple(labels)


def thrustmaster_setup_article() -> str:
    return f"""# Runtime Setup: Thrustmaster T-Flight HOTAS One

HelmForge targets the Thrustmaster T-Flight HOTAS One, also written as Thrustmaster T.Flight Hotas One.

Use the official Thrustmaster support site only:

{OFFICIAL_THRUSTMASTER_SUPPORT_PAGE}

On the official support site, select Joysticks, then T.Flight Hotas One, then Drivers. Download and install the official Windows driver package listed there. At implementation time the package currently resembles `{CURRENT_THRUSTMASTER_DRIVER_PACKAGE_NOTE}` and lists `{CURRENT_THRUSTMASTER_SYSTEM_REQUIREMENT_NOTE}`, but always check the official support page for the newest package before installing.

After installing, connect or reconnect the HOTAS by USB, open the Thrustmaster Control Panel if installed, verify axes/buttons there, then return to HelmForge and run Preflight Check.

Thrustmaster driver/software and vJoy are separate. The Thrustmaster software handles the physical HOTAS input/control panel. vJoy or another virtual output backend creates the virtual joystick output that HelmForge may write to in a later phase.

Do not install drivers from mirrors, third-party driver sites, bundled archives, or unofficial downloads. Phase 1A does not install drivers, download installers, write vJoy output, or claim live runtime support.
"""
