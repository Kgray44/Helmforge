from __future__ import annotations


def test_perf_1a_bridge_cli_enables_local_telemetry_stream_by_default_and_keeps_opt_out():
    from bridge_app.main import build_parser

    default_args = build_parser().parse_args(["--once"])
    disabled_args = build_parser().parse_args(["--once", "--no-telemetry-stream"])

    assert default_args.telemetry_stream is True
    assert disabled_args.telemetry_stream is False
    assert default_args.telemetry_host == "127.0.0.1"


def test_perf_1a_bridge_tick_uses_runtime_frame_pipeline_for_rule_summary(monkeypatch, tmp_path):
    import shared_core.runtime.runtime_orchestrator as orchestrator_module
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.math.pipeline import WorkspaceSignalPipeline as RealPipeline

    calls = {"process": 0}

    class CountingPipeline(RealPipeline):
        def process(self, *args, **kwargs):
            calls["process"] += 1
            return super().process(*args, **kwargs)

    monkeypatch.setattr(orchestrator_module, "WorkspaceSignalPipeline", CountingPipeline)
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            simulate=True,
            enable_telemetry_stream=False,
        )
    )
    telemetry = service.run_once(publish_telemetry=False)

    assert calls["process"] == 1
    assert telemetry.output_verified is False
    assert telemetry.runtime_frame is not None
    assert telemetry.runtime_frame["full_live_runtime_ready"] is False
    service.shutdown()


def test_perf_1a_runtime_orchestrator_is_not_rebuilt_every_simulated_tick(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions

    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            simulate=True,
            enable_telemetry_stream=False,
        )
    )
    before = service.timing.runtime_orchestrator_rebuild_count
    for _ in range(5):
        service.run_once(publish_telemetry=False)

    assert service.timing.runtime_orchestrator_rebuild_count == before
    assert service.timing.last_runtime_orchestrator_rebuild_reason in {"startup", "unchanged"}
    service.shutdown()
