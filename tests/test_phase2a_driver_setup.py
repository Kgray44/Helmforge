from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from shared_core.models.runtime import OutputStatus, RuntimeMode
from shared_core.runtime.device_discovery import build_runtime_preflight_status, detect_input_devices
from shared_core.runtime.driver_setup import (
    OFFICIAL_THRUSTMASTER_SUPPORT_PAGE,
    VJOY_SETUP_SOURCE_URL,
    build_local_driver_setup_status,
    evaluate_installer_launch_request,
    is_likely_thrustmaster_driver_software_name,
    open_official_thrustmaster_support_page,
    open_vjoy_setup_source,
)
from shared_core.runtime.setup_guidance import SetupStatusLabel, build_setup_status_labels


def test_driver_setup_open_pages_are_noop_by_default():
    thrustmaster = open_official_thrustmaster_support_page()
    vjoy = open_vjoy_setup_source()

    assert thrustmaster.url == OFFICIAL_THRUSTMASTER_SUPPORT_PAGE
    assert thrustmaster.opened is False
    assert vjoy.url == VJOY_SETUP_SOURCE_URL
    assert vjoy.opened is False


def test_installer_launch_requires_explicit_flag_and_interactive_approval():
    default_decision = evaluate_installer_launch_request()
    flag_only = evaluate_installer_launch_request(launch_installers=True)
    approval_only = evaluate_installer_launch_request(user_confirmed=True)
    approved = evaluate_installer_launch_request(
        launch_installers=True,
        user_confirmed=True,
        installer_paths=("C:/Installers/example.exe",),
    )

    assert default_decision.launch_permitted is False
    assert default_decision.installer_launched is False
    assert default_decision.admin_permission_requested is False
    assert flag_only.launch_permitted is False
    assert approval_only.launch_permitted is False
    assert approved.launch_permitted is True
    assert approved.installer_launched is False
    assert approved.admin_permission_requested is False


def test_thrustmaster_driver_software_name_matcher_recognizes_installed_package_name():
    assert is_likely_thrustmaster_driver_software_name("T.Flight Hotas drivers") is True
    assert is_likely_thrustmaster_driver_software_name("Thrustmaster Flight Series") is True
    assert is_likely_thrustmaster_driver_software_name("Some unrelated joystick tool") is False


def test_missing_driver_or_device_state_is_nonfatal_and_simulation_first():
    preflight = build_runtime_preflight_status(input_device_names=[], output_backend_names=[])

    setup = build_local_driver_setup_status(preflight)

    assert setup.hotas_detected is False
    assert setup.vjoy_detected is False
    assert setup.simulation_mode_active is True
    assert setup.full_live_runtime_ready is False
    assert setup.fatal_errors == ()
    assert SetupStatusLabel.HOTAS_NOT_CONNECTED in setup.labels
    assert SetupStatusLabel.VJOY_MISSING in setup.labels
    assert SetupStatusLabel.SIMULATION_MODE_ACTIVE in setup.labels
    assert SetupStatusLabel.FULL_LIVE_RUNTIME_READY not in setup.labels


def test_thrustmaster_usb_signature_can_identify_generic_windows_hid_name():
    detection = detect_input_devices(
        [
            "HID-compliant game controller USB\\VID_044F&PID_B68D",
            "USB Input Device USB\\VID_044F&PID_B68D",
        ]
    )

    assert detection.status.name == "DETECTED"
    assert detection.detected_device_names == (
        "HID-compliant game controller USB\\VID_044F&PID_B68D",
        "USB Input Device USB\\VID_044F&PID_B68D",
    )


def test_vjoy_detected_label_does_not_claim_full_live_without_verified_output():
    preflight = build_runtime_preflight_status(
        input_device_names=["Thrustmaster T.Flight Hotas One HID"],
        output_backend_names=["vJoy Device"],
    )

    labels = build_setup_status_labels(preflight)

    assert preflight.mode is RuntimeMode.SIMULATED
    assert preflight.output.status is OutputStatus.VJOY_DETECTED
    assert SetupStatusLabel.VJOY_DETECTED in labels
    assert SetupStatusLabel.FULL_LIVE_RUNTIME_READY not in labels


def test_runtime_setup_check_script_dry_run_is_non_installing():
    powershell = shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required for the Windows runtime setup script.")

    project_root = Path(__file__).resolve().parents[1]
    script = project_root / "scripts" / "runtime_setup_check.ps1"

    completed = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-DryRun",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    output = f"{completed.stdout}\n{completed.stderr}"

    assert completed.returncode == 0, output
    assert "HelmForge Runtime Setup Check" in output
    assert "Thrustmaster" in output
    assert "vJoy" in output
    assert "Dry run only" in output
    assert "No installers launched" in output


def test_minimal_app_exposes_both_runtime_setup_source_buttons():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QPushButton
    from v3_app.main import build_main_window

    app = QApplication.instance() or QApplication([])
    window = build_main_window()
    button_texts = {button.text() for button in window.findChildren(QPushButton)}

    assert app is not None
    assert "Open Official Thrustmaster Support Page" in button_texts
    assert "Open vJoy Setup Source" in button_texts
