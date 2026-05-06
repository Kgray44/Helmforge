from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_bridge(*args: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bridge_app.main", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_phase9b_bridge_app_imports_without_ui_dependencies():
    import bridge_app

    assert bridge_app.PRODUCT_NAME == "HelmForge"

    bridge_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "bridge_app").rglob("*.py"))
    assert "PySide6" not in bridge_sources
    assert "from v3_app" not in bridge_sources
    assert "import v3_app" not in bridge_sources


def test_phase9b_bridge_once_mode_writes_simulated_telemetry(tmp_path):
    telemetry_path = tmp_path / "bridge-telemetry.json"

    result = _run_bridge("--once", "--simulate", "--telemetry-path", str(telemetry_path))

    assert result.returncode == 0, result.stderr
    telemetry = _read_json(telemetry_path)
    assert telemetry["product_name"] == "HelmForge"
    assert telemetry["bridge_name"] == "HelmForge Bridge"
    assert telemetry["technical_subtitle"] == "HOTAS Control Panel V3"
    assert telemetry["lifecycle_state"] in {"Simulated", "LiveUnverified", "WaitingForHotas"}
    assert telemetry["runtime_truth"] in {"simulated", "detected_unverified", "blocked_missing_device"}
    assert telemetry["output_verified"] is False
    assert "Full Live Runtime Ready" not in json.dumps(telemetry)


def test_phase9b_bridge_run_for_ms_exits_cleanly_and_writes_axes(tmp_path):
    telemetry_path = tmp_path / "bridge-telemetry.json"

    result = _run_bridge("--run-for-ms", "250", "--simulate", "--telemetry-path", str(telemetry_path))

    assert result.returncode == 0, result.stderr
    telemetry = _read_json(telemetry_path)
    assert set(telemetry["raw_axes"]) >= {"Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2"}
    assert set(telemetry["final_axes"]) >= {"Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2"}
    assert telemetry["buttons"]["B1"] in {True, False}
    assert "HOTAS Hat" in telemetry["hats"]


def test_phase9b_bridge_status_prints_truth_without_output_verified_claim(tmp_path):
    telemetry_path = tmp_path / "bridge-status.json"

    result = _run_bridge("--status", "--simulate", "--telemetry-path", str(telemetry_path))

    assert result.returncode == 0, result.stderr
    assert "HelmForge Bridge" in result.stdout
    assert "output_verified=False" in result.stdout
    assert "Full Live Runtime Ready" not in result.stdout


def test_phase9b_missing_config_falls_back_safely(tmp_path):
    telemetry_path = tmp_path / "bridge-telemetry.json"
    missing_config = tmp_path / "missing-hotas_bridge_config_v3.json"

    result = _run_bridge(
        "--once",
        "--simulate",
        "--telemetry-path",
        str(telemetry_path),
        "--config-path",
        str(missing_config),
    )

    assert result.returncode == 0, result.stderr
    telemetry = _read_json(telemetry_path)
    warnings = " ".join(telemetry["warnings"])
    assert telemetry["active_profile"] == "Current Workspace"
    assert "missing" in warnings.lower()


def test_phase9b_corrupt_config_reports_error_without_overwriting(tmp_path):
    telemetry_path = tmp_path / "bridge-telemetry.json"
    corrupt_config = tmp_path / "hotas_bridge_config_v3.json"
    corrupt_config.write_text("{not valid json", encoding="utf-8")

    result = _run_bridge(
        "--once",
        "--simulate",
        "--telemetry-path",
        str(telemetry_path),
        "--config-path",
        str(corrupt_config),
    )

    assert result.returncode == 0, result.stderr
    assert corrupt_config.read_text(encoding="utf-8") == "{not valid json"
    telemetry = _read_json(telemetry_path)
    combined = " ".join(telemetry["warnings"] + telemetry["errors"])
    assert "invalid workspace json" in combined.lower()


def test_phase9b_command_parser_handles_initial_command_set(tmp_path):
    from bridge_app.ipc import parse_command_payload
    from shared_core.runtime.bridge_contracts import BridgeCommandType

    for command in (
        "ReloadConfig",
        "RunPreflight",
        "SwitchToSimulation",
        "ClearError",
        "Status",
    ):
        request = parse_command_payload({"command": command, "request_id": f"req-{command}"})
        assert request.command is BridgeCommandType(command)


def test_phase9b_stop_command_exits_bounded_loop(tmp_path):
    telemetry_path = tmp_path / "bridge-telemetry.json"
    command_path = tmp_path / "bridge-command.json"
    command_path.write_text(json.dumps({"command": "StopBridge", "request_id": "stop-now"}), encoding="utf-8")

    result = _run_bridge(
        "--run-for-ms",
        "1000",
        "--simulate",
        "--telemetry-path",
        str(telemetry_path),
        "--command-path",
        str(command_path),
    )

    assert result.returncode == 0, result.stderr
    telemetry = _read_json(telemetry_path)
    assert telemetry["lifecycle_state"] == "Stopping"


def test_phase9b_shared_core_boundary_still_excludes_ui_imports():
    shared_core_sources = list((PROJECT_ROOT / "shared_core").rglob("*.py"))
    joined = "\n".join(path.read_text(encoding="utf-8") for path in shared_core_sources)

    assert "from v3_app" not in joined
    assert "import v3_app" not in joined
    assert "PySide6" not in joined
