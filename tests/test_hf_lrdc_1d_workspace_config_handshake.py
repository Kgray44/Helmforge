from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import datetime, timezone


NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status():
    from shared_core.models.runtime import InputDeviceDetection, InputStatus, OutputBackendDetection, OutputStatus, RuntimeMode, RuntimePreflightStatus, RuntimeTruth

    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )


def _write_telemetry(path, *, bridge_workspace: dict[str, object], last_command: dict[str, object] | None = None) -> None:
    payload = {
        "timestamp": NOW.isoformat(),
        "lifecycle_state": "LiveUnverified",
        "runtime_truth": "detected_unverified",
        "input_status": "detected",
        "output_status": "vjoy_detected",
        "output_verified": False,
        "active_profile": "Current Workspace",
        "raw_axes": {"Roll": 0, "Pitch": 0, "Throttle": 0, "Yaw": 0, "Aux 1": 0, "Aux 2": 0},
        "final_axes": {"Roll": 0, "Pitch": 0, "Throttle": 0, "Yaw": 0, "Aux 1": 0, "Aux 2": 0},
        "buttons": {f"B{index}": False for index in range(1, 16)},
        "hats": {"HOTAS Hat": "Centered", "Output Hat": "Centered"},
        "active_modes": {"active_mode_names": []},
        "rule_summary": {"active_count": 0, "blocked_count": 0, "disabled_count": 0},
        "runtime_frame": {
            "schema_version": "helmforge.runtime_frame.v1",
            "sequence": 1,
            "generated_at": NOW.isoformat(),
            "final_output_axes": {"Roll": 0},
            "output_verified": False,
            "full_live_runtime_ready": False,
            "runtime_truth": "blocked_unverified_output",
            "blocked_reason": "blocked_unverified_output",
            "ready_state": "blocked",
            "telemetry_proof": "fresh",
            "safety_proof": "ok",
            "fake_or_real_path": "real",
            "evaluated_at": NOW.isoformat(),
        },
        "bridge_timing": {"tick_count": 1, "last_tick_duration_ms": 1.2},
        "bridge_workspace": bridge_workspace,
        "last_command": last_command,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_hf_lrdc_1d_workspace_identity_is_stable_and_changes_on_meaningful_config():
    from shared_core.models.workspace import create_default_workspace
    from shared_core.persistence.schema import to_json_data, workspace_from_json_data
    from shared_core.persistence.workspace_identity import build_workspace_identity, compute_workspace_hash

    workspace = create_default_workspace()
    reordered = workspace_from_json_data(json.loads(json.dumps(to_json_data(workspace), sort_keys=True)))
    changed = replace(workspace, active_profile="alternate-profile")

    first_hash = compute_workspace_hash(workspace)
    second_hash = compute_workspace_hash(reordered)
    changed_hash = compute_workspace_hash(changed)
    identity = build_workspace_identity(workspace, path="hotas_bridge_config_v3.json", status="loaded", generated_at=NOW)

    assert first_hash == second_hash
    assert changed_hash != first_hash
    assert identity.schema_version == "3.0.0"
    assert identity.product_name == "HelmForge"
    assert identity.active_profile == "current-workspace"
    assert identity.workspace_revision == identity.workspace_hash[:12]
    assert identity.short_hash == identity.workspace_hash[:8]


def test_hf_lrdc_1d_bridge_config_telemetry_reports_loaded_missing_and_invalid(tmp_path):
    from bridge_app.config_loader import load_bridge_workspace
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.models.workspace import create_default_workspace
    from shared_core.persistence.workspace_store import save_workspace

    config_path = tmp_path / "hotas_bridge_config_v3.json"
    save_workspace(create_default_workspace(), config_path, overwrite=True)
    loaded = load_bridge_workspace(config_path)
    assert loaded.identity.source_status == "loaded"
    assert loaded.identity.config_path == str(config_path)

    missing = load_bridge_workspace(tmp_path / "missing.json")
    assert missing.identity.source_status == "missing_default"
    assert missing.using_default_workspace is True

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not-json", encoding="utf-8")
    invalid = load_bridge_workspace(invalid_path)
    assert invalid.identity.source_status == "invalid_default"
    assert invalid.using_default_workspace is True
    assert invalid.errors

    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            config_path=config_path,
            simulate=True,
        )
    )
    service.run_once()
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    assert payload["bridge_workspace"]["config_status"] == "loaded"
    assert payload["bridge_workspace"]["workspace_hash"] == loaded.identity.workspace_hash
    assert payload["bridge_workspace"]["workspace_revision"] == loaded.identity.workspace_revision
    assert payload["bridge_workspace"]["using_default_workspace"] is False


def test_hf_lrdc_1d_reload_command_compares_expected_and_loaded_hash(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.models.workspace import create_default_workspace
    from shared_core.persistence.workspace_identity import compute_workspace_hash
    from shared_core.persistence.workspace_store import save_workspace
    from v3_app.services.bridge_commands import BridgeCommandClient

    config_path = tmp_path / "hotas_bridge_config_v3.json"
    workspace = create_default_workspace()
    save_workspace(workspace, config_path, overwrite=True)
    expected_hash = compute_workspace_hash(workspace)
    command_path = tmp_path / "command.json"

    BridgeCommandClient(command_path=command_path, request_id_factory=lambda: "reload-match", clock=lambda: NOW).reload_config(
        config_path=config_path,
        expected_workspace_hash=expected_hash,
        expected_workspace_revision=expected_hash[:12],
    )
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=command_path,
            config_path=config_path,
            simulate=True,
            clock=lambda: NOW,
        )
    )
    service.run_once()
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    assert payload["last_command"]["config_match"] is True
    assert payload["last_command"]["expected_workspace_hash"] == expected_hash
    assert payload["last_command"]["loaded_workspace_hash"] == expected_hash

    BridgeCommandClient(command_path=command_path, request_id_factory=lambda: "reload-mismatch", clock=lambda: NOW).reload_config(
        config_path=config_path,
        expected_workspace_hash="0" * 64,
    )
    service.run_once()
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    assert payload["last_command"]["config_match"] is False
    assert payload["last_command"]["mismatch_reason"] == "workspace_hash_mismatch"


def test_hf_lrdc_1d_bridge_client_and_live_monitor_expose_config_sync_truth(tmp_path):
    from PySide6.QtWidgets import QLabel
    from shared_core.models.workspace import create_default_workspace
    from shared_core.persistence.workspace_identity import build_workspace_identity
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    _app()
    workspace = create_default_workspace()
    ui_identity = build_workspace_identity(workspace, path="ui-draft", status="ui_current", generated_at=NOW)
    bridge_workspace = ui_identity.to_bridge_workspace_dict(
        config_path="hotas_bridge_config_v3.json",
        config_status="loaded",
        using_default_workspace=False,
    )
    telemetry_path = tmp_path / "telemetry.json"
    _write_telemetry(
        telemetry_path,
        bridge_workspace=bridge_workspace,
        last_command={
            "request_id": "reload-1",
            "command": "ReloadConfig",
            "status": "completed",
            "received_at": NOW.isoformat(),
            "completed_at": NOW.isoformat(),
            "updated_at": NOW.isoformat(),
            "message": "ReloadConfig command completed by Bridge.",
            "expected_workspace_hash": ui_identity.workspace_hash,
            "loaded_workspace_hash": ui_identity.workspace_hash,
            "config_match": True,
            "mismatch_reason": "",
        },
    )

    parsed = BridgeTelemetryClient(telemetry_path=telemetry_path, clock=lambda: NOW).read()
    assert parsed.status is BridgeTelemetryStatus.CONNECTED
    assert parsed.telemetry is not None
    assert parsed.telemetry.bridge_workspace is not None

    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=workspace,
        runtime_status=_runtime_status(),
        telemetry_path=telemetry_path,
        bridge_clock=lambda: NOW,
    )
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))
    assert "Config sync: match" in labels_text
    assert "Bridge config: hotas_bridge_config_v3.json | loaded" in labels_text
    assert "Last reload: completed | expected hash matched" in labels_text
    assert "Full Live Runtime Ready true" not in labels_text
    assert "Output Verified" not in labels_text

    mismatched = dict(bridge_workspace)
    mismatched["workspace_hash"] = "1" * 64
    mismatched["workspace_revision"] = "1" * 12
    _write_telemetry(telemetry_path, bridge_workspace=mismatched)
    page.refresh_snapshot(force_new=True)
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))
    assert "Config sync: mismatch" in labels_text

    missing_default = dict(bridge_workspace)
    missing_default["config_status"] = "missing_default"
    missing_default["using_default_workspace"] = True
    _write_telemetry(telemetry_path, bridge_workspace=missing_default)
    page.refresh_snapshot(force_new=True)
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))
    assert "Bridge config: hotas_bridge_config_v3.json | missing_default | using default workspace" in labels_text


def test_hf_lrdc_1d_config_match_does_not_change_runtime_truth(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions

    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            simulate=True,
            enable_output_verification=False,
            enable_output_loop=False,
        )
    )
    telemetry = service.run_once().to_dict()
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))

    assert "bridge_workspace" in payload
    assert telemetry["output_verified"] is False
    assert telemetry["runtime_frame"]["full_live_runtime_ready"] is False
    assert "Full Live Runtime Ready" not in json.dumps(telemetry)
