from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status():
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )

    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
    )


def _payload(*, timestamp: datetime | None = None, runtime_frame: object | None = None) -> dict:
    stamp = timestamp or datetime.now(timezone.utc)
    payload = {
        "product_name": "HelmForge",
        "technical_subtitle": "HOTAS Control Panel V3",
        "bridge_name": "HelmForge Bridge",
        "bridge_process": "bridge_app",
        "timestamp": stamp.isoformat(),
        "lifecycle_state": "Simulated",
        "runtime_truth": "blocked_missing_device",
        "input_status": "missing",
        "output_status": "vjoy_detected",
        "output_verified": False,
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
        "buttons": {f"B{index}": False for index in range(1, 16)},
        "hats": {"HOTAS Hat": "Centered", "Output Hat": "Centered"},
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
            "disabled_count": 0,
        },
        "warnings": (),
        "errors": (),
    }
    if runtime_frame is not None:
        payload["runtime_frame"] = runtime_frame
    return payload


def _runtime_frame(*, generated_at: datetime | None = None) -> dict:
    stamp = generated_at or datetime.now(timezone.utc)
    return {
        "schema_version": "helmforge.runtime_frame.v1",
        "frame_id": "runtime-frame-42",
        "sequence": 42,
        "generated_at": stamp.isoformat(),
        "input_source": "simulation",
        "input_status": "simulation",
        "input_device": "Simulation",
        "input_sample_age_ms": None,
        "input_stale": False,
        "pipeline_status": "simulated_output_intent_ready",
        "active_modes": [],
        "active_rule_count": 0,
        "active_rule_names": [],
        "final_output_axes": {"X": 0.21, "Y": 0.05, "Z": 0.25, "RX": -0.12, "RY": 0.0, "RZ": -0.25},
        "output_intent_ready": True,
        "output_backend": "Missing virtual output backend",
        "output_verification_status": "not_attempted",
        "output_loop_state": "disabled",
        "last_output_write_status": "Not active",
        "output_verified": False,
        "full_live_runtime_ready": False,
        "runtime_truth": "simulated_output_intent_ready",
        "blocked_reason": "",
        "warnings": [],
        "errors": [],
    }


def _write_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_phase16b_bridge_telemetry_includes_compact_runtime_frame(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions

    telemetry_path = tmp_path / "bridge-runtime-frame.json"
    service = BridgeService(BridgeServiceOptions(telemetry_path=telemetry_path, simulate=True))

    service.run_once()

    payload = json.loads(telemetry_path.read_text(encoding="utf-8"))
    runtime_frame = payload["runtime_frame"]
    assert runtime_frame["schema_version"] == "helmforge.runtime_frame.v1"
    assert runtime_frame["input_source"] == "simulation"
    assert runtime_frame["pipeline_status"] == "simulated_output_intent_ready"
    assert runtime_frame["output_intent_ready"] is True
    assert runtime_frame["output_loop_state"] == "disabled"
    assert runtime_frame["output_verified"] is False
    assert runtime_frame["full_live_runtime_ready"] is False
    assert set(runtime_frame["final_output_axes"]) == {"X", "Y", "Z", "RX", "RY", "RZ"}
    assert "axis_results" not in runtime_frame
    assert "raw_axis_values" not in runtime_frame
    assert "stage_names_by_axis" not in runtime_frame


def test_phase16b_runtime_frame_exposes_axis_stage_values_without_extra_pipeline_pass(tmp_path, monkeypatch):
    import shared_core.runtime.runtime_orchestrator as runtime_orchestrator
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.math.pipeline import WorkspaceSignalPipeline
    from shared_core.math.stack import EXPECTED_STAGE_NAMES

    process_calls = 0

    class CountingPipeline(WorkspaceSignalPipeline):
        def process(self, *args, **kwargs):
            nonlocal process_calls
            process_calls += 1
            return super().process(*args, **kwargs)

    monkeypatch.setattr(runtime_orchestrator, "WorkspaceSignalPipeline", CountingPipeline)
    telemetry_path = tmp_path / "stage-values-runtime-frame.json"
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=telemetry_path,
            command_path=tmp_path / "command.json",
            simulate=True,
            enable_telemetry_stream=False,
        )
    )

    try:
        payload = service.run_once().to_dict()
    finally:
        service.shutdown()

    runtime_frame = payload["runtime_frame"]
    roll_stages = runtime_frame["axis_stage_values"]["Roll"]

    assert process_calls == 1
    assert [stage["stage_name"] for stage in roll_stages] == list(EXPECTED_STAGE_NAMES)
    assert roll_stages[0]["stage_name"] == "Raw Input"
    assert set(roll_stages[0]) >= {"input_value", "output_value", "delta", "active", "metadata"}
    assert roll_stages[-1]["stage_name"] == "Final Output"
    assert roll_stages[-1]["output_value"] == pytest.approx(payload["final_axes"]["Roll"])


def test_phase16b_bridge_client_parses_missing_and_malformed_runtime_frame_safely(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    missing_path = tmp_path / "missing-runtime-frame.json"
    _write_payload(missing_path, _payload())
    missing = BridgeTelemetryClient(telemetry_path=missing_path).read()
    assert missing.status is BridgeTelemetryStatus.CONNECTED
    assert missing.telemetry is not None
    assert missing.telemetry.runtime_frame is None

    malformed_path = tmp_path / "malformed-runtime-frame.json"
    _write_payload(malformed_path, _payload(runtime_frame=["not", "an", "object"]))
    malformed = BridgeTelemetryClient(telemetry_path=malformed_path).read()
    assert malformed.status is BridgeTelemetryStatus.CONNECTED
    assert malformed.telemetry is not None
    assert malformed.telemetry.runtime_frame is not None
    assert malformed.telemetry.runtime_frame.available is False
    assert malformed.telemetry.runtime_frame.parse_status == "invalid"
    assert "runtime_frame must be an object" in malformed.telemetry.runtime_frame.errors

    stale_path = tmp_path / "stale-runtime-frame.json"
    _write_payload(stale_path, _payload(timestamp=datetime.now(timezone.utc) - timedelta(seconds=30), runtime_frame=_runtime_frame()))
    stale = BridgeTelemetryClient(telemetry_path=stale_path, stale_after_seconds=5.0).read()
    assert stale.status is BridgeTelemetryStatus.STALE
    assert stale.should_use_fallback is True


def test_phase16b_bridge_client_preserves_axis_stage_values(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient

    runtime_frame = _runtime_frame()
    runtime_frame["axis_stage_values"] = {
        "Roll": [
            {
                "stage_name": "Raw Input",
                "input_value": 0.42,
                "output_value": 0.42,
                "delta": 0.0,
                "active": True,
                "metadata": {},
                "injected_rules": [],
            },
            {
                "stage_name": "Final Output",
                "input_value": 0.21,
                "output_value": 0.21,
                "delta": 0.0,
                "active": True,
                "metadata": {},
                "injected_rules": [],
            },
        ]
    }
    telemetry_path = tmp_path / "stage-values-client.json"
    _write_payload(telemetry_path, _payload(runtime_frame=runtime_frame))

    result = BridgeTelemetryClient(telemetry_path=telemetry_path).read()

    assert result.telemetry.runtime_frame.axis_stage_values["Roll"][-1]["output_value"] == 0.21


def test_phase16b_mapping_live_monitor_and_diagnostics_show_runtime_frame_truth(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.pages.mapping_page import MappingPage
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.app_state import AppState
    from v3_app.services.bridge_client import BridgeTelemetryClient

    _app()
    telemetry_path = tmp_path / "runtime-frame-ui.json"
    _write_payload(telemetry_path, _payload(runtime_frame=_runtime_frame()))
    telemetry_result = BridgeTelemetryClient(telemetry_path=telemetry_path).read()
    runtime_frame = telemetry_result.telemetry.runtime_frame
    state = AppState.from_runtime_status(_runtime_status(), driver_detected=True)

    mapping = MappingPage(
        state=state,
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        runtime_frame=runtime_frame,
    )
    live = LiveMonitorPage(
        state=state,
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        telemetry_path=telemetry_path,
    )
    live.refresh_snapshot(force_new=True)
    perf = PerfDiagnosticsPage(
        state=state,
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        telemetry_client=BridgeTelemetryClient(telemetry_path=telemetry_path),
    )

    mapping_text = _text(mapping)
    live_text = _text(live)
    perf_text = _text(perf)
    copy_text = perf.prepare_copy_diagnostics()

    assert "Runtime frame\navailable" not in mapping_text
    assert "Runtime frame source\nsimulation" not in mapping_text
    assert "Draft mapping only" in mapping_text
    assert "Runtime frame: available" in live_text
    assert "Runtime frame source: simulation" in live_text
    assert "Output intent ready: true" in live_text
    assert "Output loop state: disabled" in live_text
    assert "Runtime frame\navailable" in perf_text
    assert "Runtime frame sequence\n42" in perf_text
    assert "Runtime frame source\nsimulation" in perf_text
    assert "Output intent ready\ntrue" in perf_text
    assert "Runtime frame: available" in copy_text
    assert "Runtime frame sequence: 42" in copy_text
    for text in (mapping_text, live_text, perf_text, copy_text):
        assert "Output verified\ntrue" not in text
        assert "Output verified: true" not in text
        assert "Full Live Runtime Ready\ntrue" not in text
        assert "Full Live Runtime Ready: true" not in text


def test_phase16b_help_docs_and_source_boundary():
    from v3_app.services.help_docs import get_article

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    live_monitor = get_article("Live Monitor").body
    mapping = get_article("Mapping").body
    diagnostics = get_article("Performance / Diagnostics").body

    assert "runtime_frame is the compact telemetry summary of the orchestrated runtime path" in runtime_setup
    assert "runtime_frame can be simulation-backed" in runtime_setup
    assert "output intent is not necessarily an output write" in runtime_setup
    assert "stale/missing runtime_frame falls back safely" in runtime_setup
    assert "Runtime frame" in indicators
    assert "Live Monitor can display runtime_frame input source" in live_monitor
    assert "Mapping can show runtime frame source" in mapping
    assert "Runtime frame diagnostics" in diagnostics

    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-16b-runtime-frame-telemetry-ui-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    assert "Phase 16B adds runtime_frame telemetry and UI surfaces" in report_text
    assert "output intent is not output write proof" in report_text

    source_paths = (
        PROJECT_ROOT / "shared_core" / "runtime" / "telemetry.py",
        PROJECT_ROOT / "bridge_app" / "service.py",
        PROJECT_ROOT / "v3_app" / "services" / "bridge_client.py",
        PROJECT_ROOT / "v3_app" / "pages" / "mapping_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths if path.exists())
    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Install Service",
        "Enable Auto Start",
        "keyboard.add_hotkey",
        "mss",
        "dxcam",
        "VideoWriter",
        "ffmpeg",
    ):
        assert forbidden not in sources
