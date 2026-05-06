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


def _payload(*, timestamp: datetime | None = None, output_verified: bool = False) -> dict:
    stamp = timestamp or datetime.now(timezone.utc)
    return {
        "product_name": "HelmForge",
        "technical_subtitle": "HOTAS Control Panel V3",
        "bridge_name": "HelmForge Bridge",
        "bridge_process": "bridge_app",
        "timestamp": stamp.isoformat(),
        "lifecycle_state": "Simulated",
        "runtime_truth": "blocked_missing_device",
        "input_status": "missing",
        "output_status": "vjoy_detected",
        "output_verified": output_verified,
        "active_profile": "Current Workspace",
        "raw_axes": {
            "Roll": 0.42,
            "Pitch": 0.1,
            "Throttle": 0.5,
            "Yaw": -0.25,
            "Aux 1": 0.0,
            "Aux 2": -0.5,
        },
        "final_axes": {
            "Roll": 0.21,
            "Pitch": 0.05,
            "Throttle": 0.25,
            "Yaw": -0.12,
            "Aux 1": 0.0,
            "Aux 2": -0.25,
        },
        "buttons": {f"B{index}": index == 1 for index in range(1, 16)},
        "hats": {"HOTAS Hat": "Up", "Output Hat": "Up"},
        "active_modes": {
            "precision_active": False,
            "combat_active": False,
            "zoom_active": False,
            "extra_active": False,
            "active_mode_names": [],
        },
        "rule_summary": {
            "active_count": 0,
            "blocked_count": 0,
            "disabled_count": 1,
        },
        "warnings": ("Bridge telemetry generated in simulation mode.",),
        "errors": (),
    }


def _write_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_phase9c_bridge_client_reads_valid_fresh_telemetry(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    telemetry_path = tmp_path / "bridge.json"
    _write_payload(telemetry_path, _payload())

    result = BridgeTelemetryClient(telemetry_path=telemetry_path, stale_after_seconds=5.0).read()

    assert result.status is BridgeTelemetryStatus.CONNECTED
    assert result.source_label == "Bridge Telemetry"
    assert result.should_use_fallback is False
    assert result.telemetry.raw_axes["Roll"] == 0.42
    assert result.telemetry.final_axes["Roll"] == 0.21
    assert result.telemetry.output_verified is False


def test_phase9c_bridge_client_handles_missing_telemetry_file(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    result = BridgeTelemetryClient(telemetry_path=tmp_path / "missing.json").read()

    assert result.status is BridgeTelemetryStatus.MISSING
    assert result.source_label == "Simulation Fallback"
    assert result.should_use_fallback is True
    assert result.telemetry is None


def test_phase9c_bridge_client_handles_corrupt_telemetry_json(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    telemetry_path = tmp_path / "bridge.json"
    telemetry_path.write_text("{not valid json", encoding="utf-8")

    result = BridgeTelemetryClient(telemetry_path=telemetry_path).read()

    assert result.status is BridgeTelemetryStatus.INVALID
    assert result.should_use_fallback is True
    assert "Invalid Bridge telemetry JSON" in result.message


def test_phase9c_bridge_client_handles_stale_telemetry_timestamp(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    telemetry_path = tmp_path / "bridge.json"
    _write_payload(telemetry_path, _payload(timestamp=datetime.now(timezone.utc) - timedelta(seconds=30)))

    result = BridgeTelemetryClient(telemetry_path=telemetry_path, stale_after_seconds=5.0).read()

    assert result.status is BridgeTelemetryStatus.STALE
    assert result.source_label == "Simulation Fallback"
    assert result.should_use_fallback is True
    assert "stale" in result.message.lower()


def test_phase9c_bridge_client_rejects_missing_required_fields(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    telemetry_path = tmp_path / "bridge.json"
    payload = _payload()
    payload.pop("raw_axes")
    _write_payload(telemetry_path, payload)

    result = BridgeTelemetryClient(telemetry_path=telemetry_path).read()

    assert result.status is BridgeTelemetryStatus.INVALID
    assert result.should_use_fallback is True
    assert "raw_axes" in result.message


def test_phase9c_live_monitor_uses_fresh_bridge_telemetry(tmp_path):
    from PySide6.QtWidgets import QLabel
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    telemetry_path = tmp_path / "bridge.json"
    _write_payload(telemetry_path, _payload())

    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=telemetry_path,
    )
    page.refresh_snapshot(force_new=True)

    assert page.telemetry_source_label == "Bridge Telemetry"
    assert page.findChild(QLabel, "liveMonitorTelemetrySourceChip").text() == "Bridge Telemetry"
    assert page.findChild(QLabel, "axisRawValue_Roll").text() == "R +0.42"
    assert page.findChild(QLabel, "axisFinalValue_Roll").text() == "F +0.21"
    assert page.findChild(QLabel, "hotasHatStateChip").text() == "HOTAS Hat: Up"


def test_phase9c_live_monitor_falls_back_when_bridge_missing(tmp_path):
    from PySide6.QtWidgets import QLabel
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=tmp_path / "missing.json",
    )
    page.refresh_snapshot(force_new=True)
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))

    assert page.telemetry_source_label == "Simulation Fallback"
    assert "Bridge Missing" in labels_text
    assert "Output writes verified: false" in labels_text
    assert "Output Verified" not in labels_text
    assert "Full Live Runtime Ready" not in labels_text


def test_phase9c_live_monitor_falls_back_when_bridge_stale(tmp_path):
    from PySide6.QtWidgets import QLabel
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    telemetry_path = tmp_path / "bridge.json"
    _write_payload(telemetry_path, _payload(timestamp=datetime.now(timezone.utc) - timedelta(seconds=30)))

    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=telemetry_path,
    )
    page.refresh_snapshot(force_new=True)

    assert page.telemetry_source_status == "Stale"
    assert page.telemetry_source_label == "Simulation Fallback"
    assert "Bridge Stale" in " ".join(label.text() for label in page.findChildren(QLabel))


def test_phase9c_bridge_and_shared_boundaries_remain_ui_independent():
    project_root = Path(__file__).resolve().parents[1]
    bridge_sources = "\n".join(path.read_text(encoding="utf-8") for path in (project_root / "bridge_app").rglob("*.py"))
    shared_sources = "\n".join(path.read_text(encoding="utf-8") for path in (project_root / "shared_core").rglob("*.py"))

    assert "from v3_app" not in bridge_sources
    assert "import v3_app" not in bridge_sources
    assert "PySide6" not in bridge_sources
    assert "from v3_app" not in shared_sources
    assert "import v3_app" not in shared_sources
    assert "PySide6" not in shared_sources
