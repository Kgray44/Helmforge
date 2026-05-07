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


def _physical_snapshot(*, sampled_at: datetime = NOW, errors: tuple[str, ...] = (), source: str = "physical"):
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
        backend_name="Fake physical backend",
        sampled_at=sampled_at,
        sequence=7,
        axes=(
            PhysicalAxisSample("Axis X", "Roll", 100, 0.25),
            PhysicalAxisSample("Axis Y", "Pitch", 200, -0.1),
            PhysicalAxisSample("Axis Z", "Throttle", 300, 0.75),
            PhysicalAxisSample("Axis RX", "Yaw", 400, -0.3),
            PhysicalAxisSample("Axis RY", "Aux 1", 0, 0.0),
            PhysicalAxisSample("Axis RZ", "Aux 2", 0, 0.1),
        ),
        buttons=(PhysicalButtonSample(1, True), PhysicalButtonSample(2, False)),
        hats=(PhysicalHatSample(1, "North", "North"),),
        sampling_active=status is PhysicalInputSamplingStatus.ACTIVE,
        sample_source=source,
        sampling_status=status,
        errors=errors,
    )


class _SuccessfulRealVJoyProvider:
    backend_name = "Real vJoy"
    dependency_available = True
    driver_detected = True
    write_supported = True
    verification_supported = True

    def __init__(self) -> None:
        self.writes: list[object] = []
        self.restores = 0

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
        self.writes.append(intent)
        return {"success": True, "status": "real_write_succeeded", "message": "Injected real write succeeded."}

    def restore_neutral(self, device_id):
        _ = device_id
        self.restores += 1
        return {"success": True, "status": "neutral_restored", "message": "Injected neutral restore succeeded."}

    def release(self, device_id):
        _ = device_id


def _real_verified_loop():
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend, VirtualOutputWriteLoop, build_safe_vjoy_verification_intent

    provider = _SuccessfulRealVJoyProvider()
    backend = RealVJoyOutputBackend(provider=provider, selected_device_id="real-vjoy-1", clock=lambda: NOW)
    verification = backend.verify_output_write(build_safe_vjoy_verification_intent(timestamp=NOW))
    loop = VirtualOutputWriteLoop(backend=backend, verification=verification, clock=lambda: NOW + timedelta(seconds=1))
    enable = loop.enable()
    assert enable.state.value == "ready_verified"
    return backend, verification, loop, provider


def test_phase16c_verified_path_blocks_until_real_output_loop_is_enabled_and_verified():
    from shared_core.runtime.runtime_orchestrator import RuntimeFrameSource, RuntimeOrchestrator, RuntimeOrchestratorConfig

    frame = RuntimeOrchestrator(
        config=RuntimeOrchestratorConfig(
            preferred_input_source=RuntimeFrameSource.PHYSICAL,
            allow_simulation_fallback=False,
        ),
        physical_input_snapshot=_physical_snapshot(),
        runtime_status=_runtime_status(),
        clock=lambda: NOW,
    ).build_frame()

    telemetry = frame.to_telemetry_dict(sequence=1)
    assert frame.input.source is RuntimeFrameSource.PHYSICAL
    assert frame.safety.blocked_reason == "blocked_missing_output"
    assert telemetry["input_verified_for_runtime"] is True
    assert telemetry["pipeline_ready"] is True
    assert telemetry["output_verified_for_runtime"] is False
    assert telemetry["output_loop_enabled"] is False
    assert telemetry["verified_runtime_candidate"] is False
    assert telemetry["full_live_runtime_ready"] is False
    assert "output=unverified" in telemetry["proof_summary"]


def test_phase16c_stale_input_pipeline_error_and_output_safety_stop_block_candidate():
    from shared_core.runtime.runtime_orchestrator import RuntimeFrameSource, RuntimeOrchestrator, RuntimeOrchestratorConfig
    from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend, VirtualOutputWriteLoop

    backend, verification, loop, _provider = _real_verified_loop()
    stale_frame = RuntimeOrchestrator(
        config=RuntimeOrchestratorConfig(
            preferred_input_source=RuntimeFrameSource.PHYSICAL,
            allow_simulation_fallback=False,
            physical_sample_stale_after_seconds=1.0,
            allow_output_loop_tick=True,
        ),
        physical_input_snapshot=_physical_snapshot(sampled_at=NOW - timedelta(seconds=3)),
        virtual_output_backend=backend,
        virtual_output_verification=verification,
        virtual_output_loop=loop,
        runtime_status=_runtime_status(),
        clock=lambda: NOW,
    ).build_frame()
    assert stale_frame.safety.blocked_reason == "blocked_stale_input"
    assert stale_frame.proof.verified_runtime_candidate is False

    class ExplodingPipeline:
        def process(self, *args, **kwargs):
            _ = args, kwargs
            raise RuntimeError("pipeline exploded")

    exploding = RuntimeOrchestrator(
        config=RuntimeOrchestratorConfig(
            preferred_input_source=RuntimeFrameSource.PHYSICAL,
            allow_simulation_fallback=False,
        ),
        physical_input_snapshot=_physical_snapshot(),
        virtual_output_backend=backend,
        virtual_output_verification=verification,
        runtime_status=_runtime_status(),
        clock=lambda: NOW,
    )
    exploding._pipeline = ExplodingPipeline()
    pipeline_frame = exploding.build_frame()
    assert pipeline_frame.safety.blocked_reason == "blocked_pipeline_error"
    assert pipeline_frame.proof.pipeline_ready is False

    fake_backend = FakeVirtualOutputBackend(fail_writes=True)
    fake_verification = fake_backend.verify_output_write(fake_backend.last_written_intent or _physical_intent_placeholder())
    failing_loop = VirtualOutputWriteLoop(backend=fake_backend, verification=fake_verification, clock=lambda: NOW + timedelta(seconds=5))
    failing_loop.enable()
    safety_frame = RuntimeOrchestrator(
        config=RuntimeOrchestratorConfig(
            preferred_input_source=RuntimeFrameSource.PHYSICAL,
            allow_simulation_fallback=False,
            allow_output_loop_tick=True,
        ),
        physical_input_snapshot=_physical_snapshot(source="fake"),
        virtual_output_backend=fake_backend,
        virtual_output_verification=fake_verification,
        virtual_output_loop=failing_loop,
        runtime_status=_runtime_status(),
        clock=lambda: NOW,
    ).build_frame()
    assert safety_frame.output.output_loop_state == "safety_stopped"
    assert safety_frame.safety.blocked_reason == "blocked_output_safety_stop"
    assert safety_frame.proof.output_loop_safety_stopped is True


def _physical_intent_placeholder():
    from shared_core.runtime.vjoy_output import VirtualOutputIntent

    return VirtualOutputIntent.defaults(source="test", timestamp=NOW)


def test_phase16c_fake_path_is_test_only_and_injected_real_proof_becomes_candidate():
    from shared_core.runtime.runtime_orchestrator import RuntimeFrameSource, RuntimeOrchestrator, RuntimeOrchestratorConfig
    from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend, VirtualOutputWriteLoop

    fake_backend = FakeVirtualOutputBackend()
    fake_verification = fake_backend.verify_output_write(_physical_intent_placeholder())
    fake_loop = VirtualOutputWriteLoop(backend=fake_backend, verification=fake_verification, clock=lambda: NOW + timedelta(seconds=5))
    fake_loop.enable()
    fake_frame = RuntimeOrchestrator(
        config=RuntimeOrchestratorConfig(
            preferred_input_source=RuntimeFrameSource.PHYSICAL,
            allow_simulation_fallback=False,
            allow_output_loop_tick=True,
        ),
        physical_input_snapshot=_physical_snapshot(source="fake"),
        virtual_output_backend=fake_backend,
        virtual_output_verification=fake_verification,
        virtual_output_loop=fake_loop,
        runtime_status=_runtime_status(),
        clock=lambda: NOW,
    ).build_frame()
    fake_telemetry = fake_frame.to_telemetry_dict(sequence=2)
    assert fake_telemetry["output_loop_running"] is True
    assert fake_telemetry["output_verified_for_runtime"] is False
    assert fake_telemetry["verified_runtime_candidate"] is False
    assert fake_telemetry["full_live_runtime_ready"] is False
    assert "output=fake_verified_test_only" in fake_telemetry["proof_summary"]
    assert fake_frame.output.real_output_verified is False

    backend, verification, loop, provider = _real_verified_loop()
    real_frame = RuntimeOrchestrator(
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
    ).build_frame()
    real_telemetry = real_frame.to_telemetry_dict(sequence=3)
    assert provider.writes
    assert real_telemetry["input_verified_for_runtime"] is True
    assert real_telemetry["output_verified_for_runtime"] is True
    assert real_telemetry["output_loop_enabled"] is True
    assert real_telemetry["output_loop_running"] is True
    assert real_telemetry["verified_runtime_candidate"] is True
    assert real_telemetry["runtime_truth"] == "full_live_runtime_ready"
    assert real_telemetry["full_live_runtime_ready"] is True
    assert real_telemetry["ready_state"] == "ready"
    assert "Ready: true" in real_telemetry["proof_summary"]


def test_phase16c_ui_docs_and_boundary_text_show_runtime_proof_fields(tmp_path):
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
        "frame_id": "runtime-frame-16c",
        "sequence": 1603,
        "generated_at": fresh_now.isoformat(),
        "input_source": "physical",
        "input_status": "active",
        "input_device": "Thrustmaster T.Flight HOTAS One",
        "input_sample_age_ms": 12,
        "input_stale": False,
        "pipeline_status": "verified_runtime_candidate",
        "active_modes": [],
        "active_rule_count": 0,
        "active_rule_names": [],
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
        "ready_state": "blocked",
        "telemetry_proof": "fresh",
        "safety_proof": "ok",
        "fake_or_real_path": "real",
        "evaluated_at": fresh_now.isoformat(),
        "proof_summary": "input=fresh_physical_sample; pipeline=ok; output=real_verified; loop=disabled; ready=false; blocked=blocked_output_loop_disabled",
        "warnings": [],
        "errors": [],
    }
    payload = {
        "product_name": "HelmForge",
        "technical_subtitle": "HOTAS Control Panel V3",
        "bridge_name": "HelmForge Bridge",
        "bridge_process": "bridge_app",
        "timestamp": fresh_now.isoformat(),
        "lifecycle_state": "Simulated",
        "runtime_truth": "blocked_missing_device",
        "input_status": "missing",
        "output_status": "vjoy_detected",
        "output_verified": False,
        "active_profile": "Current Workspace",
        "raw_axes": {"Roll": 0.25, "Pitch": -0.1, "Throttle": 0.75, "Yaw": -0.3, "Aux 1": 0.0, "Aux 2": 0.1},
        "final_axes": {"Roll": 0.25, "Pitch": -0.1, "Throttle": 0.75, "Yaw": -0.3, "Aux 1": 0.0, "Aux 2": 0.1},
        "buttons": {f"B{index}": False for index in range(1, 16)},
        "hats": {"HOTAS Hat": "Centered", "Output Hat": "Centered"},
        "active_modes": {"active_mode_names": []},
        "rule_summary": {"active_count": 0, "blocked_count": 0, "disabled_count": 0},
        "runtime_frame": runtime_frame,
        "warnings": [],
        "errors": [],
    }
    telemetry_path = tmp_path / "runtime-frame-16c.json"
    telemetry_path.write_text(json.dumps(payload), encoding="utf-8")
    client = BridgeTelemetryClient(telemetry_path=telemetry_path)
    telemetry = client.read().telemetry
    parsed_frame = telemetry.runtime_frame
    state = AppState.from_runtime_status(_runtime_status(), driver_detected=True)

    mapping = MappingPage(state=state, workspace=create_default_workspace(), runtime_status=_runtime_status(), runtime_frame=parsed_frame)
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

    assert "Input proof\nfresh physical sample" in mapping_text
    assert "Pipeline proof\nok" in mapping_text
    assert "Output proof\nguarded real verification" in mapping_text
    assert "Runtime candidate\nblocked - blocked_output_loop_disabled" in mapping_text
    assert "Proof summary\ninput=fresh_physical_sample" in mapping_text
    assert "Input proof: fresh physical sample" in live_text
    assert "Output proof: guarded real verification" in live_text
    assert "Runtime candidate: blocked - blocked_output_loop_disabled" in live_text
    assert "Input proof\nfresh physical sample" in perf_text
    assert "Proof summary\ninput=fresh_physical_sample" in perf_text
    assert "Runtime candidate: blocked - blocked_output_loop_disabled" in copy_text
    assert "Full Live Runtime Ready: false" in copy_text

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    diagnostics = get_article("Performance / Diagnostics").body
    assert "Phase 16C connects the verified input/output path" in runtime_setup
    assert "physical input, pipeline, output verification, and output loop are separate proofs" in runtime_setup
    assert "fake/test path does not equal real hardware readiness" in indicators
    assert "Phase 16D owns the final readiness gate" in indicators
    assert "Runtime path proof" in diagnostics

    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-16c-verified-runtime-path-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    assert "Phase 16C connects verified input/output runtime path semantics" in report_text
    assert "Full Live Runtime Ready remains false" in report_text

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


def _widget_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))
