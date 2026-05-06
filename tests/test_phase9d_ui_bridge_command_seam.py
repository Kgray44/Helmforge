from __future__ import annotations

import json
import os
import subprocess
import sys
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


def test_phase9d_ui_command_client_writes_valid_safe_command_json(tmp_path):
    from v3_app.services.bridge_commands import BridgeCommandClient

    command_path = tmp_path / "bridge-command.json"
    result = BridgeCommandClient(command_path=command_path).write_command(BridgeCommandType.STATUS)

    payload = json.loads(command_path.read_text(encoding="utf-8"))
    assert result.success is True
    assert result.command == "Status"
    assert result.path == command_path
    assert payload["command"] == "Status"
    assert payload["source"] == "v3_app"
    assert payload["product_name"] == "HelmForge"
    assert payload["technical_subtitle"] == "HOTAS Control Panel V3"
    assert payload["request_id"] == result.request_id
    assert payload["created_at"]


def test_phase9d_ui_command_client_rejects_unsafe_commands(tmp_path):
    from v3_app.services.bridge_commands import BridgeCommandClient

    command_path = tmp_path / "bridge-command.json"
    client = BridgeCommandClient(command_path=command_path)

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


def test_phase9d_ui_command_client_handles_unwritable_path_gracefully(tmp_path):
    from v3_app.services.bridge_commands import BridgeCommandClient

    directory_path = tmp_path / "command-directory"
    directory_path.mkdir()

    result = BridgeCommandClient(command_path=directory_path).write_command(BridgeCommandType.STATUS)

    assert result.success is False
    assert result.path == directory_path
    assert result.error


def test_phase9d_bridge_app_reads_safe_commands_written_by_ui_client(tmp_path):
    from bridge_app.ipc import read_command
    from v3_app.services.bridge_commands import BridgeCommandClient

    command_path = tmp_path / "bridge-command.json"
    client = BridgeCommandClient(command_path=command_path)

    for command in (
        BridgeCommandType.STATUS,
        BridgeCommandType.RUN_PREFLIGHT,
        BridgeCommandType.RELOAD_CONFIG,
        BridgeCommandType.SWITCH_TO_SIMULATION,
        BridgeCommandType.CLEAR_ERROR,
    ):
        write_result = client.write_command(command)
        request = read_command(command_path)
        assert write_result.success is True
        assert request is not None
        assert request.command is command
        assert request.request_id == write_result.request_id


def test_phase9d_bridge_once_parses_ui_command_and_keeps_output_unverified(tmp_path):
    from v3_app.services.bridge_commands import BridgeCommandClient

    command_path = tmp_path / "bridge-command.json"
    telemetry_path = tmp_path / "bridge-telemetry.json"
    BridgeCommandClient(command_path=command_path).run_preflight()

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
    assert telemetry["output_verified"] is False
    assert "Full Live Runtime Ready" not in json.dumps(telemetry)


def test_phase9d_live_monitor_can_request_bridge_status_without_completion_claim(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    command_path = tmp_path / "bridge-command.json"
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=tmp_path / "missing-telemetry.json",
        command_path=command_path,
    )

    page.findChild(QPushButton, "bridgeCommandStatusButton").click()

    payload = json.loads(command_path.read_text(encoding="utf-8"))
    status_text = page.findChild(QLabel, "bridgeCommandStatusText").text()
    assert payload["command"] == "Status"
    assert "command requested" in status_text.lower()
    assert "awaiting bridge telemetry" in status_text.lower()
    assert "completed" not in status_text.lower()
    assert "Output Verified" not in " ".join(label.text() for label in page.findChildren(QLabel))


def test_phase9d_live_monitor_safe_command_buttons_exist_and_send_allowed_commands(tmp_path):
    from PySide6.QtWidgets import QPushButton
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    command_path = tmp_path / "bridge-command.json"
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        runtime_status=_status(),
        telemetry_path=tmp_path / "missing-telemetry.json",
        command_path=command_path,
    )

    expected = {
        "bridgeCommandStatusButton": "Status",
        "bridgeCommandPreflightButton": "RunPreflight",
        "bridgeCommandReloadButton": "ReloadConfig",
        "bridgeCommandSimulationButton": "SwitchToSimulation",
        "bridgeCommandClearErrorButton": "ClearError",
    }
    for object_name, command in expected.items():
        page.findChild(QPushButton, object_name).click()
        payload = json.loads(command_path.read_text(encoding="utf-8"))
        assert payload["command"] == command


def test_phase9d_boundaries_remain_separate():
    bridge_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "bridge_app").rglob("*.py"))
    shared_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "shared_core").rglob("*.py"))

    assert "from v3_app" not in bridge_sources
    assert "import v3_app" not in bridge_sources
    assert "PySide6" not in bridge_sources
    assert "from v3_app" not in shared_sources
    assert "import v3_app" not in shared_sources
    assert "PySide6" not in shared_sources
