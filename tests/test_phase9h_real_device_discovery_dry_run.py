from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _status() -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
        messages=("Simulation mode selected because live output is not verified.",),
    )


def _payload(*, discovery_status: str = "no_supported_device", matched: bool = False, output_verified: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "product_name": "HelmForge",
        "technical_subtitle": "HOTAS Control Panel V3",
        "bridge_name": "HelmForge Bridge",
        "bridge_process": "bridge_app",
        "timestamp": now.isoformat(),
        "lifecycle_state": "Simulated",
        "runtime_truth": "blocked_missing_device",
        "input_status": "missing",
        "output_status": "vjoy_detected",
        "output_verified": output_verified,
        "active_profile": "Current Workspace",
        "raw_axes": {
            "Roll": 0.0,
            "Pitch": 0.0,
            "Throttle": 0.0,
            "Yaw": 0.0,
            "Aux 1": 0.0,
            "Aux 2": 0.0,
        },
        "final_axes": {
            "Roll": 0.0,
            "Pitch": 0.0,
            "Throttle": 0.0,
            "Yaw": 0.0,
            "Aux 1": 0.0,
            "Aux 2": 0.0,
        },
        "buttons": {f"B{index}": False for index in range(1, 16)},
        "hats": {"HOTAS Hat": "Centered", "Output Hat": "Centered"},
        "active_modes": {
            "precision_active": False,
            "combat_active": False,
            "zoom_active": False,
            "extra_active": False,
            "active_mode_names": [],
        },
        "rule_summary": {"active_count": 0, "blocked_count": 0, "disabled_count": 1},
        "device_discovery": {
            "status": discovery_status,
            "available": matched,
            "matched": matched,
            "device_name": "Thrustmaster T.Flight Hotas One" if matched else None,
            "manufacturer": "Thrustmaster" if matched else None,
            "vendor_id": "044f" if matched else None,
            "product_id": "b68d" if matched else None,
            "serial_number": None,
            "backend": "fake",
            "checked_at": now.isoformat(),
            "error": None,
            "warnings": [],
        },
        "warnings": (),
        "errors": (),
    }


def test_phase9h_fake_backend_reports_no_supported_device():
    from shared_core.runtime.hotas_discovery import (
        DeviceDiscoveryState,
        FakeDeviceDiscoveryBackend,
        discover_supported_hotas,
    )

    result = discover_supported_hotas(backend=FakeDeviceDiscoveryBackend(devices=()))

    assert result.status is DeviceDiscoveryState.NO_SUPPORTED_DEVICE
    assert result.available is False
    assert result.matched is False
    assert result.device_name is None
    assert result.backend == "fake"


def test_phase9h_fake_backend_reports_supported_hotas():
    from shared_core.runtime.hotas_discovery import (
        DeviceDiscoveryState,
        FakeDeviceDiscoveryBackend,
        HotasDeviceInfo,
        discover_supported_hotas,
    )

    result = discover_supported_hotas(
        backend=FakeDeviceDiscoveryBackend(
            devices=(
                HotasDeviceInfo(
                    device_name="Thrustmaster T.Flight Hotas One",
                    manufacturer="Thrustmaster",
                    vendor_id="044f",
                    product_id="b68d",
                    backend="fake",
                ),
            )
        )
    )

    assert result.status is DeviceDiscoveryState.SUPPORTED_DEVICE_DETECTED
    assert result.available is True
    assert result.matched is True
    assert result.device_name == "Thrustmaster T.Flight Hotas One"
    assert result.vendor_id == "044f"
    assert result.product_id == "b68d"


def test_phase9h_fake_backend_ignores_unsupported_device():
    from shared_core.runtime.hotas_discovery import (
        DeviceDiscoveryState,
        FakeDeviceDiscoveryBackend,
        HotasDeviceInfo,
        discover_supported_hotas,
    )

    result = discover_supported_hotas(
        backend=FakeDeviceDiscoveryBackend(
            devices=(HotasDeviceInfo(device_name="Generic USB Gamepad", manufacturer="Other", backend="fake"),)
        )
    )

    assert result.status is DeviceDiscoveryState.NO_SUPPORTED_DEVICE
    assert result.available is False
    assert result.matched is False


def test_phase9h_backend_unavailable_and_error_are_truthful():
    from shared_core.runtime.hotas_discovery import (
        DeviceDiscoveryState,
        FakeDeviceDiscoveryBackend,
        discover_supported_hotas,
    )

    unavailable = discover_supported_hotas(backend=FakeDeviceDiscoveryBackend(available=False))
    assert unavailable.status is DeviceDiscoveryState.BACKEND_UNAVAILABLE
    assert unavailable.available is False
    assert unavailable.error is not None

    errored = discover_supported_hotas(backend=FakeDeviceDiscoveryBackend(error=RuntimeError("hid unavailable")))
    assert errored.status is DeviceDiscoveryState.DISCOVERY_ERROR
    assert errored.available is False
    assert "hid unavailable" in str(errored.error)


def test_phase9h_bridge_telemetry_includes_device_discovery_no_device(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_discovery import FakeDeviceDiscoveryBackend

    telemetry_path = tmp_path / "bridge-telemetry.json"
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=telemetry_path,
            discovery_backend=FakeDeviceDiscoveryBackend(devices=()),
        )
    )
    telemetry = service.run_once().to_dict()

    assert telemetry["device_discovery"]["status"] == "no_supported_device"
    assert telemetry["device_discovery"]["matched"] is False
    assert telemetry["runtime_truth"] == "blocked_missing_device"
    assert telemetry["output_verified"] is False

    payload = json.loads(telemetry_path.read_text(encoding="utf-8"))
    assert payload["device_discovery"]["status"] == "no_supported_device"


def test_phase9h_supported_device_does_not_verify_output(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_discovery import FakeDeviceDiscoveryBackend, HotasDeviceInfo

    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "bridge-telemetry.json",
            discovery_backend=FakeDeviceDiscoveryBackend(
                devices=(
                    HotasDeviceInfo(
                        device_name="Thrustmaster T-Flight HOTAS One",
                        manufacturer="Thrustmaster",
                        vendor_id="044f",
                        product_id="b68d",
                        backend="fake",
                    ),
                )
            ),
        )
    )
    telemetry = service.run_once().to_dict()

    assert telemetry["device_discovery"]["status"] == "supported_device_detected"
    assert telemetry["device_discovery"]["matched"] is True
    assert telemetry["output_verified"] is False
    assert "Full Live Runtime Ready" not in json.dumps(telemetry)


def test_phase9h_live_monitor_displays_discovery_without_live_claims(tmp_path):
    from PySide6.QtWidgets import QLabel
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    telemetry_path = tmp_path / "bridge-telemetry.json"
    telemetry_path.write_text(json.dumps(_payload(discovery_status="supported_device_detected", matched=True)), encoding="utf-8")

    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=telemetry_path,
    )

    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))
    assert "HOTAS discovery: supported device detected" in labels_text
    assert "Supported HOTAS detected; polling not active." in labels_text
    assert "Device discovery only; output verification false." in labels_text
    assert "Output Verified" not in labels_text
    assert "Full Live Runtime Ready" not in labels_text
    assert "writing to vJoy" not in labels_text


def test_phase9h_boundaries_do_not_introduce_vjoy_or_ui_runtime_dependencies():
    bridge_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "bridge_app").rglob("*.py"))
    shared_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "shared_core").rglob("*.py"))

    assert "from v3_app" not in bridge_sources
    assert "import v3_app" not in bridge_sources
    assert "PySide6" not in bridge_sources
    assert "SetAxis" not in bridge_sources
    assert "UpdateVJD" not in bridge_sources
    assert "from v3_app" not in shared_sources
    assert "import v3_app" not in shared_sources
    assert "PySide6" not in shared_sources
