from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _hotas_sample(*, sampled_at: datetime, error: str | None = None):
    from shared_core.runtime.hotas_input import (
        PhysicalAxisSample,
        PhysicalInputSamplingStatus,
        PhysicalInputSnapshot,
    )

    return PhysicalInputSnapshot(
        device_id="hotas-one",
        device_name="Thrustmaster T.Flight HOTAS One",
        backend_name="fake_input",
        sampled_at=sampled_at,
        sequence=1,
        axes=(
            PhysicalAxisSample("X", "Roll", 0.5, 0.5),
            PhysicalAxisSample("Y", "Pitch", -0.25, -0.25),
            PhysicalAxisSample("Z", "Throttle", 0.75, 0.75, one_sided=True),
            PhysicalAxisSample("RZ", "Yaw", 0.125, 0.125),
            PhysicalAxisSample("Slider 1", "Aux 1", -0.5, -0.5),
            PhysicalAxisSample("Slider 2", "Aux 2", 0.25, 0.25),
        ),
        sampling_active=error is None,
        sample_source="fake" if error is None else "unavailable",
        sampling_status=PhysicalInputSamplingStatus.ACTIVE if error is None else PhysicalInputSamplingStatus.ERROR,
        errors=(error,) if error else (),
    )


def test_phase16a_orchestrator_builds_deterministic_simulation_frame_without_hardware():
    from shared_core.runtime.runtime_orchestrator import (
        RuntimeFrameSource,
        RuntimeFrameStatus,
        RuntimeOrchestrator,
        RuntimeOrchestratorConfig,
    )

    now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    orchestrator = RuntimeOrchestrator(
        config=RuntimeOrchestratorConfig(deterministic_simulation=True),
        clock=lambda: now,
    )

    frame = orchestrator.build_frame()

    assert frame.status is RuntimeFrameStatus.SIMULATED_OUTPUT_INTENT_READY
    assert frame.input.source is RuntimeFrameSource.SIMULATION
    assert frame.input.device_name == "Simulation"
    assert frame.pipeline.raw_axis_values["Pitch"] == 0.25
    assert frame.pipeline.final_output_values["Pitch"] == frame.output_intent.axis_value("Y")
    assert frame.output_intent.axis_value("X") == frame.pipeline.final_output_values["Roll"]
    assert frame.output_intent.axis_value("Z") == frame.pipeline.final_output_values["Throttle"]
    assert frame.output_intent.write_requested is False
    assert frame.output_intent.output_enabled is False
    assert frame.output.output_verified is False
    assert frame.output.real_output_verified is False
    assert frame.safety.full_live_runtime_ready is False
    assert "output intent is not output write proof" in frame.output_intent.warnings


def test_phase16a_output_intent_does_not_write_until_fake_loop_is_explicitly_enabled():
    from shared_core.runtime.runtime_orchestrator import RuntimeOrchestrator, RuntimeOrchestratorConfig
    from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend, VirtualOutputIntent, VirtualOutputWriteLoop

    now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    backend = FakeVirtualOutputBackend()
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    loop = VirtualOutputWriteLoop(backend=backend, verification=verification)

    disabled_frame = RuntimeOrchestrator(
        config=RuntimeOrchestratorConfig(
            deterministic_simulation=True,
            allow_output_loop_tick=True,
        ),
        virtual_output_backend=backend,
        virtual_output_verification=verification,
        virtual_output_loop=loop,
        clock=lambda: now,
    ).build_frame()

    assert disabled_frame.output.output_loop_state == "disabled"
    assert disabled_frame.output.write_count == 0
    assert backend.written_intents == []

    enabled = loop.enable()
    assert enabled.enabled is True
    enabled_frame = RuntimeOrchestrator(
        config=RuntimeOrchestratorConfig(
            deterministic_simulation=True,
            allow_output_loop_tick=True,
        ),
        virtual_output_backend=backend,
        virtual_output_verification=verification,
        virtual_output_loop=loop,
        clock=lambda: now + timedelta(seconds=1),
    ).build_frame()

    assert enabled_frame.output.output_loop_state == "running"
    assert enabled_frame.output.write_count == 1
    assert enabled_frame.output.fake_output_verified is True
    assert enabled_frame.output.real_output_verified is False
    assert enabled_frame.safety.full_live_runtime_ready is False
    assert len(backend.written_intents) == 1
    assert backend.written_intents[0].source == "runtime_orchestrator_simulation"


def test_phase16a_physical_input_can_feed_pipeline_but_stale_or_error_input_falls_back():
    from shared_core.runtime.runtime_orchestrator import RuntimeFrameSource, RuntimeOrchestrator, RuntimeOrchestratorConfig

    now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    config = RuntimeOrchestratorConfig(
        preferred_input_source=RuntimeFrameSource.PHYSICAL,
        deterministic_simulation=True,
        physical_sample_stale_after_seconds=2.0,
    )

    fresh_frame = RuntimeOrchestrator(
        config=config,
        physical_input_snapshot=_hotas_sample(sampled_at=now),
        clock=lambda: now + timedelta(seconds=1),
    ).build_frame()

    assert fresh_frame.input.source is RuntimeFrameSource.PHYSICAL
    assert fresh_frame.pipeline.raw_axis_values["Roll"] == 0.5
    assert fresh_frame.output_intent.axis_value("X") == fresh_frame.pipeline.final_output_values["Roll"]
    assert fresh_frame.output.output_verified is False
    assert fresh_frame.safety.full_live_runtime_ready is False

    stale_frame = RuntimeOrchestrator(
        config=config,
        physical_input_snapshot=_hotas_sample(sampled_at=now),
        clock=lambda: now + timedelta(seconds=10),
    ).build_frame()

    assert stale_frame.input.source is RuntimeFrameSource.SIMULATION
    assert stale_frame.input.requested_source is RuntimeFrameSource.PHYSICAL
    assert stale_frame.input.stale is True
    assert stale_frame.safety.blocked_reason == "blocked_stale_input"
    assert "simulation fallback" in stale_frame.safety.fallback_reason.casefold()

    error_frame = RuntimeOrchestrator(
        config=config,
        physical_input_snapshot=_hotas_sample(sampled_at=now, error="fake read failure"),
        clock=lambda: now,
    ).build_frame()

    assert error_frame.input.source is RuntimeFrameSource.SIMULATION
    assert error_frame.input.error is True
    assert error_frame.safety.blocked_reason == "blocked_input_error"
    assert "fake read failure" in error_frame.safety.errors


def test_phase16a_frame_summary_is_compact_and_preserves_runtime_truth():
    from shared_core.runtime.runtime_orchestrator import RuntimeOrchestrator, RuntimeOrchestratorConfig

    frame = RuntimeOrchestrator(config=RuntimeOrchestratorConfig(deterministic_simulation=True)).build_frame()
    summary = frame.to_summary_dict()

    assert summary["input_source"] == "simulation"
    assert summary["output_intent_ready"] is True
    assert summary["output_verified"] is False
    assert summary["full_live_runtime_ready"] is False
    assert "axis_results" not in summary
    assert "raw_axis_values" not in summary
    assert summary["final_output_axes"] == ("X", "Y", "Z", "RX", "RY", "RZ")


def test_phase16a_docs_and_source_boundary():
    from v3_app.services.help_docs import get_article

    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-16a-runtime-orchestrator-simulation-path-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    assert "Phase 16A adds runtime orchestrator/simulation end-to-end path" in report_text
    assert "output intent is not output write proof" in report_text
    assert "Full Live Runtime Ready remains false" in report_text

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    assert "Phase 16 begins end-to-end runtime orchestration" in runtime_setup
    assert "simulation pipeline remains available" in runtime_setup
    assert "output intent is still separate from output write" in runtime_setup
    assert "output loop remains safety-gated" in runtime_setup
    assert "Full Live Runtime Ready requires both input and output proof" in runtime_setup
    assert "Runtime orchestrator" in indicators

    source_paths = (
        PROJECT_ROOT / "shared_core" / "runtime" / "runtime_orchestrator.py",
        PROJECT_ROOT / "v3_app" / "services" / "help_docs.py",
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
