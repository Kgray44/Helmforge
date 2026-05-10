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
from shared_core.runtime.bridge_contracts import BridgeCommandType


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
        "raw_axes": {axis: 0.0 for axis in ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")},
        "final_axes": {axis: 0.0 for axis in ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")},
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


def test_phase9k_safe_command_boundary_rejects_lifecycle_and_output_authority(tmp_path):
    from v3_app.services.bridge_commands import BridgeCommandClient, SAFE_UI_COMMANDS

    command_path = tmp_path / "bridge-command.json"
    client = BridgeCommandClient(command_path=command_path)

    assert {command.value for command in SAFE_UI_COMMANDS} == {
        "Status",
        "RunPreflight",
        "ReloadConfig",
        "SwitchToSimulation",
        "ClearError",
    }

    for command in (
        BridgeCommandType.START_BRIDGE,
        BridgeCommandType.STOP_BRIDGE,
        BridgeCommandType.RESTART_BRIDGE,
        BridgeCommandType.SUSPEND_BRIDGE,
        BridgeCommandType.VERIFY_OUTPUT,
        "VerifyOutput",
    ):
        result = client.write_command(command)
        assert result.success is False
        assert "not allowed" in result.message

    assert not command_path.exists()


def test_phase9k_live_monitor_has_no_process_control_buttons_and_manual_launch_is_text(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=tmp_path / "missing-telemetry.json",
        bridge_clock=lambda: datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    labels_text = "\n".join(label.text() for label in page.findChildren(QLabel))
    button_text = " ".join(button.text() for button in page.findChildren(QPushButton))

    assert "Manual launch\npython -m bridge_app.main --run-for-ms 250" in labels_text
    assert "Start Bridge" not in button_text
    assert "Stop Bridge" not in button_text
    assert "Restart Bridge" not in button_text
    assert "Install Service" not in button_text
    assert "Enable Auto Start" not in button_text
    assert "Verify Output" not in button_text
    assert "python -m bridge_app.main" not in button_text


def test_phase9k_diagnostics_keep_presence_and_discovery_out_of_runtime_truth(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.bridge_presence import (
        BridgeProcessPresenceHint,
        BridgeProcessPresenceState,
        build_live_monitor_diagnostic_rows,
        compose_bridge_lifecycle_diagnostics,
    )

    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    telemetry_path = tmp_path / "supported.json"
    _write_payload(
        telemetry_path,
        _payload(timestamp=now, discovery_status="supported_device_detected", matched=True),
    )
    telemetry = BridgeTelemetryClient(telemetry_path=telemetry_path, clock=lambda: now).read()
    diagnostics = compose_bridge_lifecycle_diagnostics(
        telemetry,
        BridgeProcessPresenceHint(state=BridgeProcessPresenceState.MAYBE_RUNNING, provider="fake"),
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )
    rows_text = "\n".join(row.value for row in build_live_monitor_diagnostic_rows(diagnostics))

    assert diagnostics.runtime_truth == "blocked_missing_device"
    assert diagnostics.full_live_runtime_ready is False
    assert diagnostics.output_verified is False
    assert diagnostics.process_hint.state is BridgeProcessPresenceState.FRESH_TELEMETRY_CONFIRMED
    assert "Supported HOTAS detected; polling not active" in rows_text
    assert "Discovery only; output verification false" in rows_text
    assert "connected and ready" not in rows_text.lower()
    assert "runtime active" not in rows_text.lower()
    assert "input live" not in rows_text.lower()
    assert "vjoy active" not in rows_text.lower()


def test_phase9k_stale_telemetry_and_unrelated_commands_do_not_become_fresh_truth(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus
    from v3_app.services.bridge_presence import (
        BridgeProcessPresenceHint,
        BridgeProcessPresenceState,
        build_live_monitor_diagnostic_rows,
        compose_bridge_lifecycle_diagnostics,
    )

    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    stale_path = tmp_path / "stale.json"
    _write_payload(
        stale_path,
        _payload(timestamp=now - timedelta(seconds=60), last_command_request_id="current-request"),
    )
    stale = BridgeTelemetryClient(telemetry_path=stale_path, stale_after_seconds=5, clock=lambda: now).read()
    stale_diag = compose_bridge_lifecycle_diagnostics(
        stale,
        BridgeProcessPresenceHint(state=BridgeProcessPresenceState.MAYBE_RUNNING, provider="fake"),
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )

    assert stale.status is BridgeTelemetryStatus.STALE
    assert stale_diag.process_hint.state is BridgeProcessPresenceState.SEEN_BUT_TELEMETRY_STALE
    stale_rows = build_live_monitor_diagnostic_rows(stale_diag, latest_request_id="current-request")
    assert next(row for row in stale_rows if row.label == "Telemetry").value == "Stale"
    assert next(row for row in stale_rows if row.label == "Last command").value == "Awaiting Bridge telemetry"

    fresh_path = tmp_path / "fresh.json"
    _write_payload(fresh_path, _payload(timestamp=now, last_command_request_id="old-request"))
    fresh = BridgeTelemetryClient(telemetry_path=fresh_path, clock=lambda: now).read()
    fresh_diag = compose_bridge_lifecycle_diagnostics(
        fresh,
        BridgeProcessPresenceHint(state=BridgeProcessPresenceState.MAYBE_RUNNING, provider="fake"),
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )
    unrelated_rows = build_live_monitor_diagnostic_rows(fresh_diag, latest_request_id="current-request")
    assert next(row for row in unrelated_rows if row.label == "Last command").value == "Awaiting Bridge telemetry"

    matching_rows = build_live_monitor_diagnostic_rows(fresh_diag, latest_request_id="old-request")
    assert next(row for row in matching_rows if row.label == "Last command").value == "Completed by Bridge"


def test_phase9k_live_monitor_diagnostic_labels_remain_stable(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.bridge_presence import (
        BridgeProcessPresenceHint,
        BridgeProcessPresenceState,
        build_live_monitor_diagnostic_rows,
        compose_bridge_lifecycle_diagnostics,
    )

    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    telemetry_path = tmp_path / "telemetry.json"
    _write_payload(telemetry_path, _payload(timestamp=now))
    telemetry = BridgeTelemetryClient(telemetry_path=telemetry_path, clock=lambda: now).read()
    diagnostics = compose_bridge_lifecycle_diagnostics(
        telemetry,
        BridgeProcessPresenceHint(state=BridgeProcessPresenceState.UNKNOWN, provider="fake"),
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )

    assert [row.label for row in build_live_monitor_diagnostic_rows(diagnostics)] == [
        "Telemetry",
        "Lifecycle",
        "Runtime",
        "Output verified",
        "HOTAS discovery",
        "Process hint",
        "Last command",
        "Diagnosis",
    ]


def test_phase9k_runtime_authority_static_boundaries_stay_frozen():
    production_sources = {
        path: path.read_text(encoding="utf-8")
        for root in ("bridge_app", "shared_core", "v3_app")
        for path in (PROJECT_ROOT / root).rglob("*.py")
    }
    combined = "\n".join(production_sources.values())
    bridge_sources = "\n".join(
        text for path, text in production_sources.items() if "bridge_app" in path.parts
    )
    ui_bridge_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
            PROJECT_ROOT / "v3_app" / "services" / "bridge_presence.py",
            PROJECT_ROOT / "v3_app" / "services" / "bridge_commands.py",
        )
    )

    shared_vjoy_source = (PROJECT_ROOT / "shared_core" / "runtime" / "vjoy_output.py").read_text(encoding="utf-8")
    for token in ("SetAxis", "SetBtn", "AcquireVJD"):
        assert token in shared_vjoy_source
        assert token not in bridge_sources
        assert token not in ui_bridge_sources
    assert "UpdateVJD" not in combined
    for token in ("subprocess.Popen", "QProcess", "startDetached", "Start-Process"):
        assert token not in ui_bridge_sources
    for token in ("win32serviceutil", "schtasks", "StartupApproved", "Shell_Startup", "pystray"):
        assert token not in combined
    assert "from v3_app" not in bridge_sources
    assert "import v3_app" not in bridge_sources
    assert "PySide6" not in bridge_sources


def test_phase9k_required_docs_state_the_same_boundary_contract():
    required_docs = (
        PROJECT_ROOT / "docs" / "HelmForge" / "phase-ledger.md",
        PROJECT_ROOT / "docs" / "HelmForge" / "bridge-service-design.md",
        PROJECT_ROOT / "docs" / "HelmForge" / "bridge-ui-architecture.md",
        PROJECT_ROOT / "docs" / "HelmForge" / "phase-9j-live-monitor-diagnostic-ux-polish-report.md",
        PROJECT_ROOT / "docs" / "HelmForge" / "phase-9k-phase-9-stabilization-boundary-freeze-report.md",
    )
    required_phrases = (
        "telemetry remains the truth surface",
        "command files are requests, not success proof",
        "matching request_id",
        "process presence is a hint",
        "HOTAS discovery is discovery-only",
        "supported_device_detected does not mean polling/live runtime/output verified",
        "manual Bridge launch remains the current lifecycle model",
        "UI does not start, stop, restart, spawn, install, or manage the Bridge",
        "output_verified remains false",
        "Full Live Runtime Ready remains false",
        "live device/runtime work remains deferred",
    )

    for path in required_docs:
        text = path.read_text(encoding="utf-8")
        normalized = " ".join(text.split()).lower()
        for phrase in required_phrases:
            assert phrase.lower() in normalized, f"{path} is missing {phrase!r}"
