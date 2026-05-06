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


def _payload(
    *,
    timestamp: datetime,
    discovery_status: str = "no_supported_device",
    matched: bool = False,
    output_verified: bool = False,
    last_command_request_id: str | None = None,
    last_command_status: str = "completed",
) -> dict:
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
            "checked_at": timestamp.isoformat(),
            "error": None,
            "warnings": [],
        },
        "warnings": (),
        "errors": (),
    }
    if last_command_request_id is not None:
        payload["last_command"] = {
            "schema_version": "helmforge.bridge_command_status.v1",
            "request_id": last_command_request_id,
            "command": "Status",
            "status": last_command_status,
            "received_at": timestamp.isoformat(),
            "completed_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
            "message": "Status command completed by Bridge.",
            "error": None,
        }
    return payload


def _write_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_phase9j_diagnostic_rows_have_stable_order_and_severity(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.bridge_presence import (
        BridgeProcessPresenceHint,
        BridgeProcessPresenceState,
        build_live_monitor_diagnostic_rows,
        compose_bridge_lifecycle_diagnostics,
    )

    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    telemetry_path = tmp_path / "telemetry.json"
    _write_payload(telemetry_path, _payload(timestamp=now, last_command_request_id="cmd-ui-1"))
    telemetry = BridgeTelemetryClient(telemetry_path=telemetry_path, clock=lambda: now).read()
    diagnostics = compose_bridge_lifecycle_diagnostics(
        telemetry,
        BridgeProcessPresenceHint(state=BridgeProcessPresenceState.MAYBE_RUNNING, provider="fake"),
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )

    rows = build_live_monitor_diagnostic_rows(diagnostics, latest_request_id="cmd-ui-1")

    assert [row.label for row in rows] == [
        "Telemetry",
        "Lifecycle",
        "Runtime",
        "Output verified",
        "HOTAS discovery",
        "Process hint",
        "Last command",
        "Diagnosis",
    ]
    assert rows[0].value == "Fresh"
    assert rows[0].severity in {"ok", "info"}
    assert rows[3].value == "false"
    assert rows[3].severity in {"muted", "info"}
    assert rows[4].value == "No supported HOTAS detected"
    assert rows[4].severity in {"warning", "info"}
    assert rows[6].value == "Completed by Bridge"


def test_phase9j_missing_stale_invalid_and_fresh_manual_launch_guidance(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.bridge_presence import (
        BridgeProcessPresenceHint,
        BridgeProcessPresenceState,
        build_live_monitor_diagnostic_rows,
        compose_bridge_lifecycle_diagnostics,
    )

    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    hint = BridgeProcessPresenceHint(state=BridgeProcessPresenceState.MAYBE_RUNNING, provider="fake")

    missing = BridgeTelemetryClient(telemetry_path=tmp_path / "missing.json", clock=lambda: now).read()
    missing_diag = compose_bridge_lifecycle_diagnostics(
        missing,
        hint,
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )
    missing_rows = build_live_monitor_diagnostic_rows(missing_diag)
    assert any(row.label == "Manual launch" for row in missing_rows)
    assert "manual bridge launch may be required" in missing_diag.diagnostic_text.lower()

    stale_path = tmp_path / "stale.json"
    _write_payload(stale_path, _payload(timestamp=now - timedelta(seconds=30)))
    stale = BridgeTelemetryClient(telemetry_path=stale_path, stale_after_seconds=5, clock=lambda: now).read()
    stale_diag = compose_bridge_lifecycle_diagnostics(
        stale,
        hint,
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )
    stale_rows = build_live_monitor_diagnostic_rows(stale_diag)
    assert any(row.label == "Manual launch" for row in stale_rows)
    assert "telemetry is stale" in stale_diag.diagnostic_text
    assert "simulation fallback active" in stale_diag.diagnostic_text

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not valid json", encoding="utf-8")
    invalid = BridgeTelemetryClient(telemetry_path=invalid_path, clock=lambda: now).read()
    invalid_diag = compose_bridge_lifecycle_diagnostics(
        invalid,
        hint,
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )
    invalid_rows = build_live_monitor_diagnostic_rows(invalid_diag)
    assert invalid_rows[0].value == "Invalid"
    assert invalid_rows[0].severity == "error"
    assert not any(row.label == "Manual launch" for row in invalid_rows)
    assert "runtime ready" not in invalid_diag.diagnostic_text.lower()

    fresh_path = tmp_path / "fresh.json"
    _write_payload(fresh_path, _payload(timestamp=now))
    fresh = BridgeTelemetryClient(telemetry_path=fresh_path, clock=lambda: now).read()
    fresh_diag = compose_bridge_lifecycle_diagnostics(
        fresh,
        hint,
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )
    assert not any(row.label == "Manual launch" for row in build_live_monitor_diagnostic_rows(fresh_diag))


def test_phase9j_discovery_wording_is_unambiguous(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.bridge_presence import (
        BridgeProcessPresenceHint,
        BridgeProcessPresenceState,
        build_live_monitor_diagnostic_rows,
        compose_bridge_lifecycle_diagnostics,
    )

    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    supported_path = tmp_path / "supported.json"
    _write_payload(
        supported_path,
        _payload(timestamp=now, discovery_status="supported_device_detected", matched=True),
    )
    supported = BridgeTelemetryClient(telemetry_path=supported_path, clock=lambda: now).read()
    supported_diag = compose_bridge_lifecycle_diagnostics(
        supported,
        BridgeProcessPresenceHint(state=BridgeProcessPresenceState.MAYBE_RUNNING, provider="fake"),
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )
    supported_text = "\n".join(row.value for row in build_live_monitor_diagnostic_rows(supported_diag))

    assert "Supported HOTAS detected; polling not active" in supported_text
    assert "Discovery only; output verification false" in supported_text
    assert "HOTAS active" not in supported_text
    assert "input live" not in supported_text
    assert "polling active" not in supported_text
    assert "connected and ready" not in supported_text

    missing_path = tmp_path / "missing-device.json"
    _write_payload(missing_path, _payload(timestamp=now, discovery_status="no_supported_device"))
    missing = BridgeTelemetryClient(telemetry_path=missing_path, clock=lambda: now).read()
    missing_diag = compose_bridge_lifecycle_diagnostics(
        missing,
        BridgeProcessPresenceHint(state=BridgeProcessPresenceState.UNKNOWN, provider="fake"),
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )
    missing_text = "\n".join(row.value for row in build_live_monitor_diagnostic_rows(missing_diag))
    assert "No supported HOTAS detected" in missing_text
    assert "Runtime blocked: missing device" in missing_text


def test_phase9j_live_monitor_renders_compact_rows_and_command_matching(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState
    from v3_app.services.bridge_presence import (
        BridgeProcessPresenceHint,
        BridgeProcessPresenceState,
        FakeBridgeProcessPresenceProvider,
    )

    _app()
    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    telemetry_path = tmp_path / "bridge-telemetry.json"
    command_path = tmp_path / "bridge-command.json"
    _write_payload(telemetry_path, _payload(timestamp=now, last_command_request_id="old-request"))

    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=telemetry_path,
        command_path=command_path,
        command_request_id_factory=lambda: "current-request",
        bridge_clock=lambda: now,
        process_presence_provider=FakeBridgeProcessPresenceProvider(
            BridgeProcessPresenceHint(state=BridgeProcessPresenceState.MAYBE_RUNNING, provider="fake")
        ),
    )
    page.findChild(QPushButton, "bridgeCommandStatusButton").click()
    page.refresh_snapshot(force_new=True)

    labels_text = "\n".join(label.text() for label in page.findChildren(QLabel))
    assert "Telemetry\nFresh" in labels_text
    assert "Lifecycle\nSimulated" in labels_text
    assert "Runtime\nRuntime blocked: missing device" in labels_text
    assert "Output verified\nfalse" in labels_text
    assert "HOTAS discovery\nNo supported HOTAS detected" in labels_text
    assert "Process hint\nFresh telemetry confirmed" in labels_text
    assert "Last command\nAwaiting Bridge telemetry" in labels_text
    assert "Manual launch expected:" not in labels_text
    assert "completed by Bridge for current-request" not in labels_text
    assert "Output Verified" not in labels_text
    assert "Full Live Runtime Ready" not in labels_text

    _write_payload(telemetry_path, _payload(timestamp=now, last_command_request_id="current-request"))
    page.refresh_snapshot(force_new=True)
    updated_text = "\n".join(label.text() for label in page.findChildren(QLabel))
    assert "Last command\nCompleted by Bridge" in updated_text
    assert "completed by Bridge for current-request" in updated_text


def test_phase9j_missing_telemetry_live_monitor_shows_manual_launch_without_control_buttons(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=tmp_path / "missing.json",
        bridge_clock=lambda: datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    labels_text = "\n".join(label.text() for label in page.findChildren(QLabel))
    button_text = " ".join(button.text() for button in page.findChildren(QPushButton))

    assert "Telemetry\nMissing" in labels_text
    assert "Manual launch\npython -m bridge_app.main --run-for-ms 250" in labels_text
    assert "Start Bridge" not in button_text
    assert "Stop Bridge" not in button_text
    assert "Restart Bridge" not in button_text
    assert "Install Service" not in button_text
    assert "Enable Auto Start" not in button_text
    assert "Verify Output" not in button_text


def test_phase9j_boundaries_do_not_add_runtime_activation_dependencies():
    bridge_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "bridge_app").rglob("*.py"))
    shared_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "shared_core").rglob("*.py"))
    phase9j_ui_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
            PROJECT_ROOT / "v3_app" / "services" / "bridge_presence.py",
        )
    )

    for token in ("SetAxis", "UpdateVJD"):
        assert token not in bridge_sources
        assert token not in shared_sources
    for token in ("Start-Process", "subprocess.Popen", "CreateProcess", "QProcess", "startDetached"):
        assert token not in phase9j_ui_sources
    assert "from v3_app" not in bridge_sources
    assert "import v3_app" not in bridge_sources
    assert "PySide6" not in bridge_sources
    assert "from v3_app" not in shared_sources
    assert "import v3_app" not in shared_sources
    assert "PySide6" not in shared_sources
