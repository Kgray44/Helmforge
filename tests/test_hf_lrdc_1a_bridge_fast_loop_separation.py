from __future__ import annotations

import json
from datetime import datetime, timezone


class CountingDiscoveryBackend:
    backend_name = "counting_fake"

    def __init__(self) -> None:
        self.calls = 0

    def enumerate_devices(self):
        from shared_core.runtime.hotas_discovery import HotasDeviceInfo

        self.calls += 1
        return (
            HotasDeviceInfo(
                device_name="Thrustmaster T.Flight HOTAS One",
                manufacturer="Thrustmaster",
                vendor_id="044f",
                product_id="b68d",
                backend=self.backend_name,
            ),
        )


def _command_payload(command: str, request_id: str) -> dict[str, object]:
    return {
        "command": command,
        "request_id": request_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def test_hf_lrdc_1a_cli_keeps_bounded_modes_and_adds_run_mode():
    from bridge_app.main import build_parser

    parser = build_parser()

    assert parser.parse_args(["--run"]).run is True
    assert parser.parse_args(["--run-for-ms", "10"]).run_for_ms == 10
    assert parser.parse_args(["--once"]).once is True
    assert parser.parse_args(["--status"]).status is True


def test_hf_lrdc_1a_discovery_runs_at_startup_and_is_not_repeated_every_fast_tick(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions

    backend = CountingDiscoveryBackend()
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            discovery_backend=backend,
            discovery_refresh_interval_seconds=60.0,
            simulate=True,
        )
    )

    assert backend.calls == 1

    service.run_once()
    service.run_once()
    service.run_once()

    assert backend.calls == 1
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    timing = payload["bridge_timing"]
    assert timing["last_discovery_duration_ms"] >= 0
    assert timing["last_discovery_age_ms"] >= 0
    assert timing["slow_lane_status"] in {"cached", "refreshed"}


def test_hf_lrdc_1a_run_preflight_forces_slow_discovery_without_rearming_every_tick(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions

    backend = CountingDiscoveryBackend()
    command_path = tmp_path / "command.json"
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=command_path,
            discovery_backend=backend,
            discovery_refresh_interval_seconds=60.0,
            simulate=True,
        )
    )
    command_path.write_text(json.dumps(_command_payload("RunPreflight", "preflight-1")), encoding="utf-8")

    service.run_once()
    service.run_once()

    assert backend.calls == 2
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    assert payload["last_command"]["command"] == "RunPreflight"
    assert payload["bridge_timing"]["last_command_duration_ms"] >= 0
    assert payload["bridge_timing"]["slow_lane_status"] == "cached"


def test_hf_lrdc_1a_timing_telemetry_and_truth_gates_are_preserved(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend

    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            discovery_backend=CountingDiscoveryBackend(),
            physical_input_backend=FakePhysicalInputBackend(devices=()),
            enable_live_input=True,
            enable_output_verification=False,
            enable_output_loop=False,
            simulate=False,
        )
    )

    first = service.run_once().to_dict()
    second = service.run_once().to_dict()
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    parsed = BridgeTelemetryClient(telemetry_path=tmp_path / "telemetry.json").read()

    assert payload["tick_count"] == 1
    assert parsed.status is BridgeTelemetryStatus.CONNECTED
    assert parsed.telemetry is not None
    assert parsed.telemetry.bridge_timing is not None
    assert second["output_verified"] is False
    assert second["runtime_frame"]["full_live_runtime_ready"] is False
    assert "Full Live Runtime Ready" not in json.dumps(second)

    timing = payload["bridge_timing"]
    for field in (
        "bridge_pid",
        "bridge_started_at",
        "tick_count",
        "tick_interval_target_ms",
        "last_tick_duration_ms",
        "last_input_read_duration_ms",
        "last_pipeline_duration_ms",
        "last_output_write_duration_ms",
        "last_telemetry_publish_duration_ms",
        "last_discovery_duration_ms",
        "last_discovery_age_ms",
        "fast_loop_status",
        "slow_lane_status",
    ):
        assert field in timing
    assert timing["tick_count"] == 2
    assert isinstance(timing["last_tick_duration_ms"], (int, float))
    assert isinstance(timing["last_telemetry_publish_duration_ms"], (int, float))
    assert timing["fast_loop_status"] in {"ok", "stopping"}
    assert timing["slow_lane_status"] in {"cached", "refreshed"}
