from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
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


def _payload(*, timestamp: datetime, output_verified: bool = False, request_id: str | None = None) -> dict:
    payload = {
        "product_name": "HelmForge",
        "technical_subtitle": "HOTAS Control Panel V3",
        "bridge_name": "HelmForge Bridge",
        "bridge_process": "bridge_app",
        "timestamp": timestamp.isoformat(),
        "lifecycle_state": "Simulated",
        "runtime_truth": "blocked_missing_device",
        "input_status": "missing",
        "output_status": "vjoy_detected",
        "output_verified": output_verified,
        "active_profile": "Current Workspace",
        "raw_axes": {
            "Roll": 0.25,
            "Pitch": 0.0,
            "Throttle": 0.0,
            "Yaw": 0.0,
            "Aux 1": 0.0,
            "Aux 2": 0.0,
        },
        "final_axes": {
            "Roll": 0.2,
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
        "warnings": (),
        "errors": (),
    }
    if request_id is not None:
        payload["last_command"] = {
            "schema_version": "helmforge.bridge_command_status.v1",
            "request_id": request_id,
            "command": "Status",
            "status": "completed",
            "received_at": timestamp.isoformat(),
            "completed_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
            "message": "Status command completed by Bridge.",
            "error": None,
        }
    return payload


def _write_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_phase9f_bridge_client_exposes_fresh_health_timing_details(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    now = datetime(2026, 5, 6, 12, 0, 5, tzinfo=timezone.utc)
    generated = now - timedelta(seconds=2.5)
    telemetry_path = tmp_path / "bridge-telemetry.json"
    _write_payload(telemetry_path, _payload(timestamp=generated))

    result = BridgeTelemetryClient(
        telemetry_path=telemetry_path,
        stale_after_seconds=5.0,
        clock=lambda: now,
    ).read()

    assert result.status is BridgeTelemetryStatus.CONNECTED
    assert result.telemetry_path == telemetry_path
    assert result.last_read_at == now
    assert result.telemetry_generated_at == generated
    assert result.age_seconds == 2.5
    assert result.stale_threshold_seconds == 5.0
    assert result.reason == "Bridge telemetry connected."


def test_phase9f_bridge_client_reports_missing_invalid_and_stale_health(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    missing = BridgeTelemetryClient(telemetry_path=tmp_path / "missing.json", clock=lambda: now).read()
    assert missing.status is BridgeTelemetryStatus.MISSING
    assert missing.last_read_at == now
    assert missing.telemetry_generated_at is None
    assert "missing" in missing.reason.lower()

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not valid json", encoding="utf-8")
    invalid = BridgeTelemetryClient(telemetry_path=invalid_path, clock=lambda: now).read()
    assert invalid.status is BridgeTelemetryStatus.INVALID
    assert "could not be parsed" in invalid.reason.lower()

    stale_path = tmp_path / "stale.json"
    _write_payload(stale_path, _payload(timestamp=now - timedelta(seconds=30)))
    stale = BridgeTelemetryClient(telemetry_path=stale_path, stale_after_seconds=5.0, clock=lambda: now).read()
    assert stale.status is BridgeTelemetryStatus.STALE
    assert stale.age_seconds == 30.0
    assert stale.stale_threshold_seconds == 5.0
    assert stale.should_use_fallback is True
    assert "simulation fallback" in stale.reason.lower()


def test_phase9f_live_monitor_shows_fresh_bridge_health_details(tmp_path):
    from PySide6.QtWidgets import QLabel
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    now = datetime(2026, 5, 6, 12, 0, 5, tzinfo=timezone.utc)
    telemetry_path = tmp_path / "bridge-telemetry.json"
    _write_payload(telemetry_path, _payload(timestamp=now - timedelta(seconds=1.25), request_id="cmd-health-1"))

    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=telemetry_path,
        bridge_stale_after_seconds=5.0,
        bridge_clock=lambda: now,
    )

    health_text = page.findChild(QLabel, "bridgeHealthText").text()
    assert "Bridge: Connected" in health_text
    assert "Telemetry age: 1.2s" in health_text
    assert "Runtime truth: blocked_missing_device" in health_text
    assert "Output verified: false" in health_text
    assert "Last command: completed" in health_text


def test_phase9f_live_monitor_shows_missing_stale_and_invalid_explanations(tmp_path):
    from PySide6.QtWidgets import QLabel
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)

    missing_page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=tmp_path / "missing.json",
        bridge_clock=lambda: now,
    )
    missing_text = missing_page.findChild(QLabel, "bridgeHealthText").text()
    assert "Bridge: Missing" in missing_text
    assert "telemetry file not found" in missing_text.lower()
    assert "Simulation fallback active" in missing_text

    stale_path = tmp_path / "stale.json"
    _write_payload(stale_path, _payload(timestamp=now - timedelta(seconds=30)))
    stale_page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=stale_path,
        bridge_stale_after_seconds=5.0,
        bridge_clock=lambda: now,
    )
    stale_text = stale_page.findChild(QLabel, "bridgeHealthText").text()
    assert "Bridge: Stale" in stale_text
    assert "Telemetry age: 30.0s" in stale_text
    assert "stale" in stale_text.lower()
    assert "Simulation fallback active" in stale_text
    assert "Bridge: Connected" not in stale_text

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not valid json", encoding="utf-8")
    invalid_page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=invalid_path,
        bridge_clock=lambda: now,
    )
    invalid_text = invalid_page.findChild(QLabel, "bridgeHealthText").text()
    assert "Bridge: Invalid" in invalid_text
    assert "could not be parsed" in invalid_text.lower()
    assert "Simulation fallback active" in invalid_text


def test_phase9f_live_monitor_preserves_phase9e_matching_request_behavior(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    telemetry_path = tmp_path / "bridge-telemetry.json"
    _write_payload(telemetry_path, _payload(timestamp=now, request_id="other-request"))
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=telemetry_path,
        command_path=tmp_path / "bridge-command.json",
        command_request_id_factory=lambda: "cmd-ui-health",
        bridge_clock=lambda: now,
    )

    page.findChild(QPushButton, "bridgeCommandStatusButton").click()
    page.refresh_snapshot(force_new=True)

    command_text = page.findChild(QLabel, "bridgeCommandStatusText").text().lower()
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))
    assert "awaiting bridge telemetry" in command_text
    assert "completed by bridge" not in command_text
    assert "Output Verified" not in labels_text
    assert "Full Live Runtime Ready" not in labels_text


def test_phase9f_no_hardware_or_ui_dependency_boundary_regression():
    bridge_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "bridge_app").rglob("*.py"))
    shared_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "shared_core").rglob("*.py"))

    assert "from v3_app" not in bridge_sources
    assert "import v3_app" not in bridge_sources
    assert "PySide6" not in bridge_sources
    assert "from v3_app" not in shared_sources
    assert "import v3_app" not in shared_sources
    assert "PySide6" not in shared_sources
