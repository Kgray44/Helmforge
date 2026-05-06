from pathlib import Path
import os

from shared_core.models.runtime import InputStatus, OutputStatus, RuntimeMode
from shared_core.runtime.device_discovery import build_runtime_preflight_status, detect_input_devices
from shared_core.runtime.setup_guidance import (
    OFFICIAL_THRUSTMASTER_SUPPORT_PAGE,
    SetupStatusLabel,
    build_setup_status_labels,
    thrustmaster_setup_article,
)


def test_target_hardware_metadata_preserves_phase1a_names():
    status = build_runtime_preflight_status(input_device_names=[], output_backend_names=[])

    assert status.target_hardware.primary_device_name == "Thrustmaster T-Flight HOTAS One"
    assert status.target_hardware.alternate_name == "Thrustmaster T.Flight Hotas One"
    assert status.target_hardware.alternate_device_name == "Thrustmaster T.Flight Hotas One"
    assert status.target_hardware.vendor_hint == "Thrustmaster"
    assert status.target_hardware.device_role == "physical HOTAS input"


def test_phase1a_fuzzy_detection_handles_sample_windows_device_names():
    detection = detect_input_devices(
        [
            "USB Composite Device",
            "Thrustmaster T.Flight Hotas One HID",
            "Thrustmaster T-Flight HOTAS One Joystick",
        ]
    )

    assert detection.status is InputStatus.DETECTED
    assert detection.detected_device_names == (
        "Thrustmaster T.Flight Hotas One HID",
        "Thrustmaster T-Flight HOTAS One Joystick",
    )


def test_setup_status_does_not_claim_live_input_without_detection():
    status = build_runtime_preflight_status(input_device_names=[], output_backend_names=[])

    labels = build_setup_status_labels(status)

    assert SetupStatusLabel.HOTAS_NOT_CONNECTED in labels
    assert SetupStatusLabel.T_FLIGHT_HOTAS_ONE_DETECTED not in labels
    assert SetupStatusLabel.INPUT_READY not in labels
    assert SetupStatusLabel.FULL_LIVE_RUNTIME_READY not in labels
    assert SetupStatusLabel.SIMULATION_MODE_ACTIVE in labels


def test_vjoy_missing_status_keeps_setup_in_simulation_mode():
    status = build_runtime_preflight_status(
        input_device_names=["Thrustmaster T.Flight Hotas One HID"],
        output_backend_names=[],
    )

    labels = build_setup_status_labels(status)

    assert status.mode is RuntimeMode.SIMULATED
    assert status.output.status is OutputStatus.VJOY_MISSING
    assert SetupStatusLabel.T_FLIGHT_HOTAS_ONE_DETECTED in labels
    assert SetupStatusLabel.INPUT_READY in labels
    assert SetupStatusLabel.VJOY_MISSING in labels
    assert SetupStatusLabel.SIMULATION_MODE_ACTIVE in labels
    assert SetupStatusLabel.FULL_LIVE_RUNTIME_READY not in labels


def test_setup_guidance_uses_official_thrustmaster_support_only():
    article = thrustmaster_setup_article()

    assert OFFICIAL_THRUSTMASTER_SUPPORT_PAGE == "https://support.thrustmaster.com/en/product/t-flight-hotas-one-en/"
    assert OFFICIAL_THRUSTMASTER_SUPPORT_PAGE in article
    assert "official Thrustmaster support site" in article
    assert "Drivers - Package 2025_TFHT_5 + Firmware" in article
    assert "Windows 10 / Windows 11" in article
    assert "third-party" in article
    assert "Do not install drivers from mirrors" in article


def test_help_docs_contain_tflight_hotas_one_setup_article():
    project_root = Path(__file__).resolve().parents[1]
    article_path = project_root / "docs" / "HelmForge" / "help" / "runtime-setup-hotas-driver.md"

    assert article_path.exists()
    text = article_path.read_text(encoding="utf-8")
    assert "Thrustmaster T-Flight HOTAS One" in text
    assert "Open Official Thrustmaster Support Page" in text
    assert OFFICIAL_THRUSTMASTER_SUPPORT_PAGE in text
    assert "Thrustmaster driver/software and vJoy are separate" in text


def test_minimal_app_exposes_official_thrustmaster_support_button():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QPushButton
    from v3_app.main import build_main_window

    app = QApplication.instance() or QApplication([])
    window = build_main_window()
    buttons = window.findChildren(QPushButton)

    assert app is not None
    assert any(button.text() == "Open Official Thrustmaster Support Page" for button in buttons)
