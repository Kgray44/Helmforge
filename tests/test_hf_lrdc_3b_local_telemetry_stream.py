from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone


NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)


def _payload(*, timestamp: datetime = NOW, output_verified: bool = False) -> dict[str, object]:
    return {
        "timestamp": timestamp.isoformat(),
        "lifecycle_state": "LiveUnverified",
        "runtime_truth": "blocked_unverified_output",
        "input_status": "detected",
        "output_status": "vjoy_detected",
        "output_verified": output_verified,
        "active_profile": "Current Workspace",
        "raw_axes": {"Roll": 0.1, "Pitch": 0.0, "Throttle": 0.0, "Yaw": 0.0, "Aux 1": 0.0, "Aux 2": 0.0},
        "final_axes": {"Roll": 0.1, "Pitch": 0.0, "Throttle": 0.0, "Yaw": 0.0, "Aux 1": 0.0, "Aux 2": 0.0},
        "buttons": {f"B{index}": False for index in range(1, 16)},
        "hats": {"HOTAS Hat": "Centered", "Output Hat": "Centered"},
        "active_modes": {"active_mode_names": []},
        "rule_summary": {"active_count": 0, "blocked_count": 0, "disabled_count": 0},
        "runtime_frame": {
            "schema_version": "helmforge.runtime_frame.v1",
            "sequence": 1,
            "generated_at": timestamp.isoformat(),
            "output_verified": output_verified,
            "full_live_runtime_ready": False,
            "ready_state": "blocked",
            "telemetry_proof": "fresh",
            "safety_proof": "ok",
            "fake_or_real_path": "real",
        },
        "bridge_timing": {"bridge_pid": 1234, "bridge_started_at": timestamp.isoformat(), "tick_count": 1},
        "warnings": [],
        "errors": [],
    }


def test_hf_lrdc_3b_stream_frame_schema_preserves_full_payload_and_truth():
    from bridge_app.telemetry_stream import build_telemetry_stream_frame

    frame = build_telemetry_stream_frame(
        _payload(output_verified=False),
        sequence=7,
        server_started_at=NOW,
        sent_at=NOW + timedelta(milliseconds=1),
        transport_name="local_websocket",
        bridge_pid=1234,
        bridge_started_at=NOW,
    )

    assert frame["schema_version"] == "helmforge.telemetry_frame.v1"
    assert frame["transport"]["sequence"] == 7
    assert frame["transport"]["sent_at"] == (NOW + timedelta(milliseconds=1)).isoformat()
    assert frame["bridge"]["bridge_pid"] == 1234
    assert frame["payload"]["timestamp"] == NOW.isoformat()
    assert frame["payload"]["output_verified"] is False
    assert frame["payload"]["runtime_frame"]["full_live_runtime_ready"] is False


def test_hf_lrdc_3b_publisher_starts_stops_and_serves_local_websocket_frame():
    from bridge_app.telemetry_stream import TelemetryStreamOptions, TelemetryStreamServer
    from v3_app.services.bridge_stream_client import BridgeTelemetryStreamClient

    server = TelemetryStreamServer(TelemetryStreamOptions(enabled=True, host="127.0.0.1", port=0))
    server.start()
    try:
        assert server.status().enabled is True
        assert server.status().host == "127.0.0.1"
        assert server.status().port > 0

        client = BridgeTelemetryStreamClient(host="127.0.0.1", port=server.status().port, stale_after_seconds=5.0)
        first = client.read_latest()
        assert first.status in {"connected", "reconnecting"}

        server.publish(_payload())
        deadline = time.monotonic() + 2.0
        result = client.read_latest()
        while result.telemetry is None and time.monotonic() < deadline:
            result = client.read_latest()
            time.sleep(0.01)

        assert result.status == "connected"
        assert result.source_label == "Bridge Stream"
        assert result.stream_sequence == 1
        assert result.telemetry is not None
        assert result.telemetry.output_verified is False
        assert server.status().frames_sent >= 1
        assert server.status().client_count >= 1
    finally:
        server.stop()
    assert server.status().enabled is False


def test_hf_lrdc_3b_publish_with_no_clients_does_not_crash_or_claim_send():
    from bridge_app.telemetry_stream import TelemetryStreamOptions, TelemetryStreamServer

    server = TelemetryStreamServer(TelemetryStreamOptions(enabled=True, host="127.0.0.1", port=0))
    server.start()
    try:
        server.publish(_payload())
        status = server.status()
        assert status.client_count == 0
        assert status.frames_sent == 0
        assert status.last_send_status in {"no_clients", "not_sent"}
    finally:
        server.stop()


def test_hf_lrdc_3b_stream_client_rejects_malformed_frames_safely():
    from v3_app.services.bridge_stream_client import parse_telemetry_stream_frame

    result = parse_telemetry_stream_frame({"schema_version": "wrong", "payload": {}}, now=NOW)

    assert result.status == "invalid"
    assert result.telemetry is None
    assert result.errors


def test_hf_lrdc_3b_source_priority_prefers_fresh_stream_then_json_then_simulation(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.bridge_stream_client import BridgeTelemetryStreamReadResult, choose_bridge_telemetry_source

    json_path = tmp_path / "telemetry.json"
    json_path.write_text(json.dumps(_payload(timestamp=NOW)), encoding="utf-8")
    json_result = BridgeTelemetryClient(telemetry_path=json_path, clock=lambda: NOW).read()
    stream_result = BridgeTelemetryStreamReadResult.connected(
        telemetry=json_result.telemetry,
        frame={"transport": {"sequence": 1}},
        read_at=NOW,
        age_seconds=0.0,
        stream_sequence=1,
    )

    selected = choose_bridge_telemetry_source(stream_result, json_result)
    assert selected.source_label == "Bridge Stream"
    assert selected.telemetry is json_result.telemetry

    stale_stream = BridgeTelemetryStreamReadResult(
        status="stale",
        source_label="Bridge Stream Stale",
        message="stale",
        age_seconds=6.0,
    )
    selected = choose_bridge_telemetry_source(stale_stream, json_result)
    assert selected.source_label == "Bridge JSON Snapshot"
    assert selected.telemetry is json_result.telemetry

    missing_json = BridgeTelemetryClient(telemetry_path=tmp_path / "missing.json", clock=lambda: NOW).read()
    selected = choose_bridge_telemetry_source(stale_stream, missing_json)
    assert selected.source_label == "Simulation Fallback"


def test_hf_lrdc_3b_bridge_service_can_publish_stream_and_preserve_json(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions

    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            simulate=True,
            enable_telemetry_stream=True,
            telemetry_stream_port=0,
        )
    )
    try:
        telemetry = service.run_once()
        assert telemetry.output_verified is False
        assert (tmp_path / "telemetry.json").exists()
        payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
        assert payload["telemetry_stream"]["enabled"] is True
        assert payload["telemetry_stream"]["host"] == "127.0.0.1"
        assert payload["telemetry_stream"]["transport_name"] == "local_websocket"
        assert payload["output_verified"] is False
    finally:
        service.shutdown()


def test_hf_lrdc_3b_cli_supports_stream_options_and_existing_modes(tmp_path):
    from bridge_app.main import build_parser

    args = build_parser().parse_args(
        [
            "--once",
            "--telemetry-stream",
            "--telemetry-host",
            "127.0.0.1",
            "--telemetry-port",
            "0",
            "--telemetry-rate-hz",
            "60",
        ]
    )

    assert args.once is True
    assert args.telemetry_stream is True
    assert args.telemetry_host == "127.0.0.1"
    assert args.telemetry_port == 0
    assert args.telemetry_rate_hz == 60.0
