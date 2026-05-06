from __future__ import annotations

import json
import os
import subprocess
import sys
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


def _run_bridge(*args: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bridge_app.main", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _payload(*, request_id: str | None = None, command_status: str = "completed") -> dict:
    payload = {
        "product_name": "HelmForge",
        "technical_subtitle": "HOTAS Control Panel V3",
        "bridge_name": "HelmForge Bridge",
        "bridge_process": "bridge_app",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lifecycle_state": "Simulated",
        "runtime_truth": "blocked_missing_device",
        "input_status": "missing",
        "output_status": "vjoy_detected",
        "output_verified": False,
        "active_profile": "Current Workspace",
        "raw_axes": {
            "Roll": 0.1,
            "Pitch": 0.0,
            "Throttle": 0.0,
            "Yaw": 0.0,
            "Aux 1": 0.0,
            "Aux 2": 0.0,
        },
        "final_axes": {
            "Roll": 0.1,
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
            "status": command_status,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message": f"Status command {command_status} by Bridge.",
            "error": None,
        }
    return payload


def test_phase9e_command_json_has_schema_request_id_and_created_at(tmp_path):
    from v3_app.services.bridge_commands import BridgeCommandClient

    fixed_now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    command_path = tmp_path / "bridge-command.json"
    result = BridgeCommandClient(
        command_path=command_path,
        request_id_factory=lambda: "cmd-test-001",
        clock=lambda: fixed_now,
    ).request_status()

    payload = json.loads(command_path.read_text(encoding="utf-8"))
    assert result.success is True
    assert result.request_id == "cmd-test-001"
    assert payload["schema_version"] == "helmforge.bridge_command.v1"
    assert payload["request_id"] == "cmd-test-001"
    assert payload["command"] == "Status"
    assert payload["created_at"] == fixed_now.isoformat()
    assert payload["source"] == "v3_app"


def test_phase9e_unsafe_command_rejection_still_works(tmp_path):
    from v3_app.services.bridge_commands import BridgeCommandClient

    client = BridgeCommandClient(command_path=tmp_path / "bridge-command.json")

    for command in (
        BridgeCommandType.START_BRIDGE,
        BridgeCommandType.STOP_BRIDGE,
        BridgeCommandType.RESTART_BRIDGE,
        BridgeCommandType.SUSPEND_BRIDGE,
        BridgeCommandType.VERIFY_OUTPUT,
    ):
        assert client.write_command(command).success is False


def test_phase9e_bridge_echoes_consumed_command_status_in_telemetry(tmp_path):
    from v3_app.services.bridge_commands import BridgeCommandClient

    command_path = tmp_path / "bridge-command.json"
    telemetry_path = tmp_path / "bridge-telemetry.json"
    BridgeCommandClient(command_path=command_path, request_id_factory=lambda: "cmd-ack-001").run_preflight()

    result = _run_bridge(
        "--once",
        "--simulate",
        "--command-path",
        str(command_path),
        "--telemetry-path",
        str(telemetry_path),
    )

    telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
    assert result.returncode == 0, result.stderr
    assert telemetry["last_command"]["request_id"] == "cmd-ack-001"
    assert telemetry["last_command"]["command"] == "RunPreflight"
    assert telemetry["last_command"]["status"] == "completed"
    assert telemetry["last_command"]["received_at"]
    assert telemetry["last_command"]["completed_at"]
    assert telemetry["output_verified"] is False


def test_phase9e_bridge_ignores_stale_command_files(tmp_path):
    from v3_app.services.bridge_commands import BridgeCommandClient

    stale_created_at = datetime.now(timezone.utc) - timedelta(seconds=120)
    command_path = tmp_path / "bridge-command.json"
    telemetry_path = tmp_path / "bridge-telemetry.json"
    BridgeCommandClient(
        command_path=command_path,
        request_id_factory=lambda: "cmd-stale-001",
        clock=lambda: stale_created_at,
    ).run_preflight()

    result = _run_bridge(
        "--once",
        "--simulate",
        "--command-path",
        str(command_path),
        "--telemetry-path",
        str(telemetry_path),
    )

    telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
    assert result.returncode == 0, result.stderr
    assert telemetry["last_command"]["request_id"] == "cmd-stale-001"
    assert telemetry["last_command"]["status"] == "ignored_stale"
    assert "stale" in telemetry["last_command"]["message"].lower()
    assert telemetry["output_verified"] is False


def test_phase9e_bridge_does_not_execute_same_request_twice(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from v3_app.services.bridge_commands import BridgeCommandClient

    command_path = tmp_path / "bridge-command.json"
    telemetry_path = tmp_path / "bridge-telemetry.json"
    BridgeCommandClient(command_path=command_path, request_id_factory=lambda: "cmd-dup-001").run_preflight()
    service = BridgeService(
        BridgeServiceOptions(
            command_path=command_path,
            telemetry_path=telemetry_path,
            simulate=True,
        )
    )

    first = service.run_once()
    second = service.run_once()

    assert service.command_execution_count == 1
    assert first.to_dict()["last_command"]["status"] == "completed"
    assert second.to_dict()["last_command"]["request_id"] == "cmd-dup-001"
    assert second.to_dict()["last_command"]["status"] == "completed"


def test_phase9e_live_monitor_waits_before_matching_telemetry_arrives(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=tmp_path / "missing-telemetry.json",
        command_path=tmp_path / "bridge-command.json",
        command_request_id_factory=lambda: "cmd-ui-001",
    )

    page.findChild(QPushButton, "bridgeCommandStatusButton").click()

    status_text = page.findChild(QLabel, "bridgeCommandStatusText").text().lower()
    assert "command requested" in status_text
    assert "awaiting bridge telemetry" in status_text
    assert "completed" not in status_text


def test_phase9e_live_monitor_ignores_unrelated_last_command_telemetry(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    telemetry_path = tmp_path / "bridge-telemetry.json"
    telemetry_path.write_text(json.dumps(_payload(request_id="other-request")), encoding="utf-8")
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=telemetry_path,
        command_path=tmp_path / "bridge-command.json",
        command_request_id_factory=lambda: "cmd-ui-002",
    )

    page.findChild(QPushButton, "bridgeCommandStatusButton").click()
    page.refresh_snapshot(force_new=True)

    status_text = page.findChild(QLabel, "bridgeCommandStatusText").text().lower()
    assert "awaiting bridge telemetry" in status_text
    assert "completed by bridge" not in status_text


def test_phase9e_live_monitor_shows_completion_only_for_matching_request_id(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    telemetry_path = tmp_path / "bridge-telemetry.json"
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=telemetry_path,
        command_path=tmp_path / "bridge-command.json",
        command_request_id_factory=lambda: "cmd-ui-003",
    )

    page.findChild(QPushButton, "bridgeCommandStatusButton").click()
    telemetry_path.write_text(json.dumps(_payload(request_id="cmd-ui-003", command_status="completed")), encoding="utf-8")
    page.refresh_snapshot(force_new=True)

    status_text = page.findChild(QLabel, "bridgeCommandStatusText").text().lower()
    assert "completed by bridge" in status_text
    assert "cmd-ui-003" in status_text
    assert "Output Verified" not in " ".join(label.text() for label in page.findChildren(QLabel))


def test_phase9e_no_hardware_or_ui_dependency_boundary_regression():
    bridge_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "bridge_app").rglob("*.py"))
    shared_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "shared_core").rglob("*.py"))

    assert "from v3_app" not in bridge_sources
    assert "import v3_app" not in bridge_sources
    assert "PySide6" not in bridge_sources
    assert "from v3_app" not in shared_sources
    assert "import v3_app" not in shared_sources
    assert "PySide6" not in shared_sources
