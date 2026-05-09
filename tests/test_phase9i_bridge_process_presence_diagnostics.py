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
) -> dict:
    return {
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
        "last_command": {
            "schema_version": "helmforge.bridge_command_status.v1",
            "request_id": "cmd-diagnostics",
            "command": "Status",
            "status": "completed",
            "received_at": timestamp.isoformat(),
            "completed_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
            "message": "Status command completed by Bridge.",
            "error": None,
        },
        "warnings": (),
        "errors": (),
    }


def _write_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_phase9i_missing_telemetry_with_unavailable_process_provider_suggests_manual_launch(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.bridge_presence import (
        BridgeProcessPresenceState,
        UnavailableBridgeProcessPresenceProvider,
        compose_bridge_lifecycle_diagnostics,
    )

    telemetry = BridgeTelemetryClient(telemetry_path=tmp_path / "missing.json").read()
    hint = UnavailableBridgeProcessPresenceProvider().get_presence()
    diagnosis = compose_bridge_lifecycle_diagnostics(
        telemetry,
        hint,
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )

    assert hint.state is BridgeProcessPresenceState.UNAVAILABLE
    assert "Bridge telemetry missing" in diagnosis.diagnostic_text
    assert "manual Bridge launch may be required" in diagnosis.diagnostic_text
    assert "Manual Bridge launch expected: python -m bridge_app.main --run-for-ms 250" in diagnosis.diagnostic_text
    assert diagnosis.runtime_truth == "blocked_missing_device"
    assert diagnosis.output_verified is False
    assert diagnosis.full_live_runtime_ready is False
    assert "Bridge ready" not in diagnosis.diagnostic_text


def test_phase9i_maybe_running_process_hint_does_not_claim_runtime_ready(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.bridge_presence import (
        BridgeProcessPresenceHint,
        BridgeProcessPresenceState,
        compose_bridge_lifecycle_diagnostics,
    )

    telemetry = BridgeTelemetryClient(telemetry_path=tmp_path / "missing.json").read()
    diagnosis = compose_bridge_lifecycle_diagnostics(
        telemetry,
        BridgeProcessPresenceHint(
            state=BridgeProcessPresenceState.MAYBE_RUNNING,
            provider="fake",
            process_count=1,
            message="Matched a bridge_app command line.",
        ),
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )

    assert "Bridge process may be running, but telemetry is missing." in diagnosis.diagnostic_text
    assert diagnosis.process_hint_label == "Maybe running"
    assert diagnosis.runtime_truth == "blocked_missing_device"
    assert diagnosis.output_verified is False
    assert diagnosis.full_live_runtime_ready is False
    assert "Live runtime ready" not in diagnosis.diagnostic_text
    assert "Output verified" not in diagnosis.diagnostic_text


def test_phase9i_stale_invalid_and_fresh_telemetry_diagnostics_are_conservative(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus
    from v3_app.services.bridge_presence import (
        BridgeProcessPresenceHint,
        BridgeProcessPresenceState,
        compose_bridge_lifecycle_diagnostics,
    )

    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    stale_path = tmp_path / "stale.json"
    _write_payload(stale_path, _payload(timestamp=now - timedelta(seconds=30)))
    stale = BridgeTelemetryClient(telemetry_path=stale_path, stale_after_seconds=5, clock=lambda: now).read()
    stale_diagnosis = compose_bridge_lifecycle_diagnostics(
        stale,
        BridgeProcessPresenceHint(state=BridgeProcessPresenceState.MAYBE_RUNNING, provider="fake"),
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )
    assert stale.status is BridgeTelemetryStatus.STALE
    assert "Bridge process may be running, but telemetry is stale." in stale_diagnosis.diagnostic_text
    assert "simulation fallback active" in stale_diagnosis.diagnostic_text
    assert stale_diagnosis.full_live_runtime_ready is False

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not valid json", encoding="utf-8")
    invalid = BridgeTelemetryClient(telemetry_path=invalid_path, clock=lambda: now).read()
    invalid_diagnosis = compose_bridge_lifecycle_diagnostics(
        invalid,
        BridgeProcessPresenceHint(state=BridgeProcessPresenceState.UNKNOWN, provider="fake"),
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )
    assert invalid.status is BridgeTelemetryStatus.INVALID
    assert "Bridge telemetry invalid" in invalid_diagnosis.diagnostic_text
    assert "Live runtime ready" not in invalid_diagnosis.diagnostic_text

    fresh_path = tmp_path / "fresh.json"
    _write_payload(fresh_path, _payload(timestamp=now - timedelta(seconds=1)))
    fresh = BridgeTelemetryClient(telemetry_path=fresh_path, stale_after_seconds=5, clock=lambda: now).read()
    fresh_diagnosis = compose_bridge_lifecycle_diagnostics(
        fresh,
        BridgeProcessPresenceHint(state=BridgeProcessPresenceState.UNKNOWN, provider="fake"),
        fallback_runtime_truth="simulated",
        fallback_output_verified=False,
    )
    assert fresh.status is BridgeTelemetryStatus.CONNECTED
    assert "Bridge telemetry fresh." in fresh_diagnosis.diagnostic_text
    assert fresh_diagnosis.process_hint_label == "Fresh telemetry confirmed"
    assert fresh_diagnosis.runtime_truth == "blocked_missing_device"
    assert fresh_diagnosis.output_verified is False


def test_phase9i_supported_device_discovery_remains_discovery_only(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.bridge_presence import (
        BridgeProcessPresenceHint,
        BridgeProcessPresenceState,
        compose_bridge_lifecycle_diagnostics,
        build_bridge_diagnostic_copy_text,
    )

    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    telemetry_path = tmp_path / "supported.json"
    _write_payload(
        telemetry_path,
        _payload(timestamp=now, discovery_status="supported_device_detected", matched=True),
    )
    telemetry = BridgeTelemetryClient(telemetry_path=telemetry_path, clock=lambda: now).read()
    diagnosis = compose_bridge_lifecycle_diagnostics(
        telemetry,
        BridgeProcessPresenceHint(state=BridgeProcessPresenceState.MAYBE_RUNNING, provider="fake"),
        fallback_runtime_truth="blocked_missing_device",
        fallback_output_verified=False,
    )
    copy_text = build_bridge_diagnostic_copy_text(diagnosis)

    assert "Supported HOTAS detected; polling not active." in diagnosis.diagnostic_text
    assert "Device discovery only; output verification false." in diagnosis.diagnostic_text
    assert "device_discovery: supported_device_detected" in copy_text
    assert "Full Live Runtime Ready: false" in copy_text
    assert "writing to vJoy" not in diagnosis.diagnostic_text
    assert diagnosis.output_verified is False
    assert diagnosis.full_live_runtime_ready is False


def test_phase9i_live_monitor_displays_compact_process_diagnostics_without_lifecycle_controls(tmp_path):
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
    _write_payload(telemetry_path, _payload(timestamp=now))

    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=telemetry_path,
        bridge_clock=lambda: now,
        process_presence_provider=FakeBridgeProcessPresenceProvider(
            BridgeProcessPresenceHint(state=BridgeProcessPresenceState.MAYBE_RUNNING, provider="fake")
        ),
    )

    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))
    button_text = " ".join(button.text() for button in page.findChildren(QPushButton))
    assert "Bridge telemetry: Connected" in labels_text
    assert "Process hint: Fresh telemetry confirmed" in labels_text
    assert "Runtime truth: blocked_missing_device" in labels_text
    assert "Output verified: false" in labels_text
    assert "Device discovery: no_supported_device" in labels_text
    assert "Diagnosis: Bridge telemetry fresh." in labels_text
    assert "Start Bridge" not in button_text
    assert "Stop Bridge" not in button_text
    assert "Restart Bridge" not in button_text
    assert "Install Service" not in button_text
    assert "Enable Auto Start" not in button_text
    assert "Verify Output" not in button_text
    assert "Output Verified" not in labels_text
    assert "Full Live Runtime Ready false" in labels_text
    assert "Full Live Runtime Ready true" not in labels_text


def test_phase9i_unsafe_lifecycle_commands_remain_rejected(tmp_path):
    from v3_app.services.bridge_commands import BridgeCommandClient

    client = BridgeCommandClient(command_path=tmp_path / "bridge-command.json")
    for command in (
        BridgeCommandType.START_BRIDGE,
        BridgeCommandType.STOP_BRIDGE,
        BridgeCommandType.RESTART_BRIDGE,
        BridgeCommandType.SUSPEND_BRIDGE,
        BridgeCommandType.VERIFY_OUTPUT,
    ):
        result = client.write_command(command)
        assert result.success is False
        assert result.error in {"unsafe_command", "unsupported_command"}


def test_phase9i_boundaries_do_not_add_hardware_output_or_process_spawn_dependencies():
    bridge_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "bridge_app").rglob("*.py"))
    shared_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "shared_core").rglob("*.py"))
    phase9i_ui_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
            PROJECT_ROOT / "v3_app" / "services" / "bridge_presence.py",
        )
        if path.exists()
    )

    vjoy_provider = (PROJECT_ROOT / "shared_core" / "runtime" / "vjoy_output.py").read_text(encoding="utf-8")
    assert "SetAxis" in vjoy_provider
    for token in ("SetAxis", "UpdateVJD"):
        assert token not in bridge_sources
    assert "UpdateVJD" not in shared_sources

    for token in ("Start-Process", "subprocess.Popen", "CreateProcess", "QProcess", "startDetached"):
        assert token not in phase9i_ui_sources

    assert "from v3_app" not in bridge_sources
    assert "import v3_app" not in bridge_sources
    assert "PySide6" not in bridge_sources
    assert "from v3_app" not in shared_sources
    assert "import v3_app" not in shared_sources
    assert "PySide6" not in shared_sources
