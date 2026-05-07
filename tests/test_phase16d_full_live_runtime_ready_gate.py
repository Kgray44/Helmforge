from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)


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


def _physical_snapshot(*, sampled_at: datetime = NOW, errors: tuple[str, ...] = (), sample_source: str = "physical"):
    from shared_core.runtime.hotas_input import (
        PhysicalAxisSample,
        PhysicalButtonSample,
        PhysicalHatSample,
        PhysicalInputSamplingStatus,
        PhysicalInputSnapshot,
    )

    status = PhysicalInputSamplingStatus.ERROR if errors else PhysicalInputSamplingStatus.ACTIVE
    return PhysicalInputSnapshot(
        device_id="hotas-one",
        device_name="Thrustmaster T.Flight HOTAS One",
        backend_name="Injected physical backend",
        sampled_at=sampled_at,
        sequence=16,
        axes=(
            PhysicalAxisSample("Axis X", "Roll", 100, 0.25),
            PhysicalAxisSample("Axis Y", "Pitch", 200, -0.1),
            PhysicalAxisSample("Axis Z", "Throttle", 300, 0.75),
            PhysicalAxisSample("Axis RX", "Yaw", 400, -0.3),
            PhysicalAxisSample("Axis RY", "Aux 1", 0, 0.0),
            PhysicalAxisSample("Axis RZ", "Aux 2", 0, 0.1),
        ),
        buttons=(PhysicalButtonSample(1, True),),
        hats=(PhysicalHatSample(1, "North", "North"),),
        sampling_active=status.value == "active",
        sample_source=sample_source,
        sampling_status=status,
        errors=errors,
    )


class _SuccessfulRealVJoyProvider:
    backend_name = "Real vJoy"
    dependency_available = True
    driver_detected = True
    write_supported = True
    verification_supported = True

    def __init__(self, *, fail_loop_write: bool = False) -> None:
        self.writes: list[object] = []
        self.restores = 0
        self.fail_loop_write = fail_loop_write

    def enumerate_devices(self):
        return (
            {
                "device_id": "real-vjoy-1",
                "display_name": "Injected real vJoy device",
                "backend_name": "Real vJoy",
                "is_selected": True,
            },
        )

    def acquire(self, device_id):
        _ = device_id
        return {"success": True, "status": "acquired", "message": "Injected acquire succeeded."}

    def write_intent(self, device_id, intent):
        _ = device_id
        if self.fail_loop_write and self.writes:
            return {"success": False, "status": "write_failed", "message": "Injected loop write failed."}
        self.writes.append(intent)
        return {"success": True, "status": "real_write_succeeded", "message": "Injected real write succeeded."}

    def restore_neutral(self, device_id):
        _ = device_id
        self.restores += 1
        return {"success": True, "status": "neutral_restored", "message": "Injected neutral restore succeeded."}

    def release(self, device_id):
        _ = device_id


def _real_verified_loop(*, fail_loop_write: bool = False):
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend, VirtualOutputWriteLoop, build_safe_vjoy_verification_intent

    provider = _SuccessfulRealVJoyProvider(fail_loop_write=fail_loop_write)
    backend = RealVJoyOutputBackend(provider=provider, selected_device_id="real-vjoy-1", clock=lambda: NOW)
    verification = backend.verify_output_write(build_safe_vjoy_verification_intent(timestamp=NOW))
    loop = VirtualOutputWriteLoop(backend=backend, verification=verification, clock=lambda: NOW + timedelta(seconds=1))
    assert loop.enable().state.value == "ready_verified"
    return backend, verification, loop, provider


def _orchestrator_frame(*, physical=None, backend=None, verification=None, loop=None, allow_tick=True, now=NOW):
    from shared_core.runtime.runtime_orchestrator import RuntimeFrameSource, RuntimeOrchestrator, RuntimeOrchestratorConfig

    return RuntimeOrchestrator(
        config=RuntimeOrchestratorConfig(
            preferred_input_source=RuntimeFrameSource.PHYSICAL,
            allow_simulation_fallback=False,
            physical_sample_stale_after_seconds=1.0,
            allow_output_loop_tick=allow_tick,
        ),
        physical_input_snapshot=physical,
        virtual_output_backend=backend,
        virtual_output_verification=verification,
        virtual_output_loop=loop,
        runtime_status=_runtime_status(),
        clock=lambda: now,
    ).build_frame()


def test_phase16d_all_real_proofs_can_open_full_live_runtime_ready_gate():
    backend, verification, loop, provider = _real_verified_loop()
    frame = _orchestrator_frame(
        physical=_physical_snapshot(),
        backend=backend,
        verification=verification,
        loop=loop,
    )
    telemetry = frame.to_telemetry_dict(sequence=1604)

    assert provider.writes
    assert frame.readiness.full_live_runtime_ready is True
    assert frame.safety.full_live_runtime_ready is True
    assert frame.safety.runtime_truth == "full_live_runtime_ready"
    assert telemetry["full_live_runtime_ready"] is True
    assert telemetry["ready_state"] == "ready"
    assert telemetry["blocked_reason"] == ""
    assert telemetry["input_proof"] == "fresh physical sample"
    assert telemetry["pipeline_proof"] == "ok"
    assert telemetry["output_proof"] == "guarded real verification"
    assert telemetry["telemetry_proof"] == "fresh"
    assert telemetry["safety_proof"] == "ok"
    assert telemetry["fake_or_real_path"] == "real"
    assert "Ready: true" in telemetry["proof_summary"]


def test_phase16d_gate_blocks_missing_stale_pipeline_unverified_loop_safety_and_fake_paths():
    from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend, VirtualOutputWriteLoop

    missing = _orchestrator_frame(physical=None)
    assert missing.readiness.full_live_runtime_ready is False
    assert missing.readiness.blocked_reason == "blocked_missing_input"

    backend, verification, loop, _provider = _real_verified_loop()
    stale = _orchestrator_frame(
        physical=_physical_snapshot(sampled_at=NOW - timedelta(seconds=3)),
        backend=backend,
        verification=verification,
        loop=loop,
    )
    assert stale.readiness.blocked_reason == "blocked_stale_input"

    class ExplodingPipeline:
        def process(self, *args, **kwargs):
            _ = args, kwargs
            raise RuntimeError("pipeline exploded")

    from shared_core.runtime.runtime_orchestrator import RuntimeFrameSource, RuntimeOrchestrator, RuntimeOrchestratorConfig

    exploding = RuntimeOrchestrator(
        config=RuntimeOrchestratorConfig(
            preferred_input_source=RuntimeFrameSource.PHYSICAL,
            allow_simulation_fallback=False,
            allow_output_loop_tick=True,
        ),
        physical_input_snapshot=_physical_snapshot(),
        virtual_output_backend=backend,
        virtual_output_verification=verification,
        virtual_output_loop=loop,
        runtime_status=_runtime_status(),
        clock=lambda: NOW,
    )
    exploding._pipeline = ExplodingPipeline()
    pipeline = exploding.build_frame()
    assert pipeline.readiness.blocked_reason == "blocked_pipeline_error"

    unverified = _orchestrator_frame(physical=_physical_snapshot())
    assert unverified.readiness.blocked_reason in {"blocked_missing_output", "blocked_unverified_output"}
    assert unverified.readiness.full_live_runtime_ready is False

    disabled = _orchestrator_frame(
        physical=_physical_snapshot(),
        backend=backend,
        verification=verification,
        loop=loop,
        allow_tick=False,
    )
    assert disabled.readiness.blocked_reason == "blocked_output_loop_disabled"

    failing_backend, failing_verification, failing_loop, _failing_provider = _real_verified_loop(fail_loop_write=True)
    safety = _orchestrator_frame(
        physical=_physical_snapshot(),
        backend=failing_backend,
        verification=failing_verification,
        loop=failing_loop,
    )
    assert safety.output.output_loop_state == "safety_stopped"
    assert safety.readiness.blocked_reason == "blocked_output_safety_stop"

    fake_backend = FakeVirtualOutputBackend()
    fake_verification = fake_backend.verify_output_write(fake_backend.last_written_intent or _fake_intent())
    fake_loop = VirtualOutputWriteLoop(backend=fake_backend, verification=fake_verification, clock=lambda: NOW + timedelta(seconds=5))
    fake_loop.enable()
    fake = _orchestrator_frame(
        physical=_physical_snapshot(sample_source="fake"),
        backend=fake_backend,
        verification=fake_verification,
        loop=fake_loop,
    )
    assert fake.readiness.ready_state == "fake_test"
    assert fake.readiness.blocked_reason == "blocked_fake_path_only"
    assert fake.readiness.full_live_runtime_ready is False
    assert fake.output.real_output_verified is False


def _fake_intent():
    from shared_core.runtime.vjoy_output import VirtualOutputIntent

    return VirtualOutputIntent.defaults(source="test", timestamp=NOW)


def test_phase16d_stale_telemetry_and_missing_readiness_proof_are_never_ready(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    stale_payload = _telemetry_payload(
        timestamp=NOW,
        runtime_frame={
            "schema_version": "helmforge.runtime_frame.v1",
            "generated_at": NOW.isoformat(),
            "final_output_axes": {"X": 0.0},
            "full_live_runtime_ready": True,
            "ready_state": "ready",
            "blocked_reason": "",
            "proof_summary": "Ready: true",
        },
    )
    stale_path = tmp_path / "stale-ready.json"
    stale_path.write_text(json.dumps(stale_payload), encoding="utf-8")
    stale = BridgeTelemetryClient(
        telemetry_path=stale_path,
        stale_after_seconds=1.0,
        clock=lambda: NOW + timedelta(seconds=10),
    ).read()
    assert stale.status is BridgeTelemetryStatus.STALE
    assert stale.telemetry.runtime_frame.full_live_runtime_ready is False
    assert stale.telemetry.runtime_frame.ready_state == "blocked"
    assert stale.telemetry.runtime_frame.blocked_reason == "blocked_telemetry_stale"

    old_shape_payload = _telemetry_payload(
        timestamp=datetime.now(timezone.utc),
        runtime_frame={
            "schema_version": "helmforge.runtime_frame.v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "final_output_axes": {"X": 0.0},
        },
    )
    old_shape_path = tmp_path / "old-shape.json"
    old_shape_path.write_text(json.dumps(old_shape_payload), encoding="utf-8")
    old_shape = BridgeTelemetryClient(telemetry_path=old_shape_path).read()
    assert old_shape.telemetry.runtime_frame.full_live_runtime_ready is False
    assert old_shape.telemetry.runtime_frame.ready_state == "unavailable"
    assert old_shape.telemetry.runtime_frame.blocked_reason == "readiness_proof_missing"


def test_phase16d_ui_docs_report_and_boundary_text_show_final_readiness_gate(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.pages.mapping_page import MappingPage
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.app_state import AppState
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.help_docs import get_article

    _app()
    fresh_now = datetime.now(timezone.utc)
    runtime_frame = {
        "schema_version": "helmforge.runtime_frame.v1",
        "frame_id": "runtime-frame-16d",
        "sequence": 1604,
        "generated_at": fresh_now.isoformat(),
        "input_source": "physical",
        "input_status": "active",
        "input_device": "Thrustmaster T.Flight HOTAS One",
        "input_sample_age_ms": 12,
        "input_stale": False,
        "pipeline_status": "blocked_output_loop_disabled",
        "final_output_axes": {"X": 0.25, "Y": -0.1, "Z": 0.75, "RX": -0.3, "RY": 0.0, "RZ": 0.1},
        "output_intent_ready": True,
        "output_backend": "Real vJoy",
        "output_verification_status": "real_verified",
        "output_loop_state": "disabled",
        "last_output_write_status": "Not active",
        "output_verified": True,
        "full_live_runtime_ready": False,
        "runtime_truth": "blocked_output_loop_disabled",
        "blocked_reason": "blocked_output_loop_disabled",
        "input_verified_for_runtime": True,
        "output_verified_for_runtime": True,
        "output_loop_enabled": False,
        "output_loop_running": False,
        "output_loop_safety_stopped": False,
        "pipeline_ready": True,
        "verified_runtime_candidate": False,
        "input_proof": "fresh physical sample",
        "pipeline_proof": "ok",
        "output_proof": "guarded real verification",
        "telemetry_proof": "fresh",
        "safety_proof": "ok",
        "ready_state": "blocked",
        "fake_or_real_path": "real",
        "evaluated_at": fresh_now.isoformat(),
        "proof_summary": "Input: fresh physical sample; Pipeline: ok; Output: guarded real verification; Output loop: disabled; Telemetry: fresh; Safety: ok; Ready: false; Blocked: blocked_output_loop_disabled",
        "warnings": [],
        "errors": [],
    }
    telemetry_path = tmp_path / "runtime-frame-16d.json"
    telemetry_path.write_text(json.dumps(_telemetry_payload(timestamp=fresh_now, runtime_frame=runtime_frame)), encoding="utf-8")
    client = BridgeTelemetryClient(telemetry_path=telemetry_path)
    runtime_frame_payload = client.read().telemetry.runtime_frame
    state = AppState.from_runtime_status(_runtime_status(), driver_detected=True)

    mapping = MappingPage(state=state, workspace=create_default_workspace(), runtime_status=_runtime_status(), runtime_frame=runtime_frame_payload)
    live = LiveMonitorPage(state=state, workspace=create_default_workspace(), runtime_status=_runtime_status(), telemetry_path=telemetry_path)
    live.refresh_snapshot(force_new=True)
    perf = PerfDiagnosticsPage(
        state=state,
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        telemetry_client=client,
    )

    mapping_text = _widget_text(mapping)
    live_text = _widget_text(live)
    perf_text = _widget_text(perf)
    copy_text = perf.prepare_copy_diagnostics()

    assert "Full Live Runtime Ready gate\nblocked" in mapping_text
    assert "Ready state\nblocked" in mapping_text
    assert "Telemetry proof\nfresh" in mapping_text
    assert "Safety proof\nok" in mapping_text
    assert "Fake/real path\nreal" in mapping_text
    assert "Readiness evaluated" in mapping_text
    assert "Ready state: blocked" in live_text
    assert "Telemetry proof: fresh" in live_text
    assert "Proof summary: Input: fresh physical sample" in live_text
    assert "Full Live Runtime Ready gate\nblocked" in perf_text
    assert "Telemetry proof\nfresh" in perf_text
    assert "Full Live Runtime Ready gate: blocked" in copy_text
    assert "Safety proof: ok" in copy_text

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    live_monitor = get_article("Live Monitor").body
    diagnostics = get_article("Performance / Diagnostics").body
    assert "Full Live Runtime Ready requires fresh physical input" in runtime_setup
    assert "physical input alone is not enough" in indicators
    assert "fake/test paths are not real readiness" in indicators
    assert "stale telemetry blocks readiness" in live_monitor
    assert "Full Live Runtime Ready gate" in diagnostics

    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-16d-full-live-runtime-ready-boundary-freeze-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    assert "Phase 16 is now complete" in report_text
    assert "Next prompt-book phase is Phase 17: Product Polish, Layout QA, and Motion" in report_text

    source_paths = (
        PROJECT_ROOT / "shared_core" / "runtime" / "runtime_orchestrator.py",
        PROJECT_ROOT / "v3_app" / "services" / "bridge_client.py",
        PROJECT_ROOT / "v3_app" / "pages" / "mapping_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
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


def _telemetry_payload(*, timestamp: datetime, runtime_frame: dict) -> dict:
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
        "output_verified": False,
        "active_profile": "Current Workspace",
        "raw_axes": {"Roll": 0.0, "Pitch": 0.0, "Throttle": 0.0, "Yaw": 0.0, "Aux 1": 0.0, "Aux 2": 0.0},
        "final_axes": {"Roll": 0.0, "Pitch": 0.0, "Throttle": 0.0, "Yaw": 0.0, "Aux 1": 0.0, "Aux 2": 0.0},
        "buttons": {f"B{index}": False for index in range(1, 16)},
        "hats": {"HOTAS Hat": "Centered", "Output Hat": "Centered"},
        "active_modes": {"active_mode_names": []},
        "rule_summary": {"active_count": 0, "blocked_count": 0, "disabled_count": 0},
        "runtime_frame": runtime_frame,
        "warnings": [],
        "errors": [],
    }


def _widget_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))
