from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


NOW = datetime(2026, 5, 10, 16, 0, 0, tzinfo=timezone.utc)


def _hotas_device():
    from shared_core.runtime.hotas_input import build_physical_input_device_info

    return build_physical_input_device_info(
        device_id="hotas-one",
        display_name="Thrustmaster T.Flight HOTAS One",
        vendor_id="044f",
        product_id="b68d",
        axis_count=6,
        button_count=15,
        hat_count=1,
        backend_name="fake_physical",
    )


def _frame(roll: float = 0.73):
    return {
        "axes": (
            {"raw_name": "X", "logical_name": "Roll", "raw_value": roll, "raw_min": -1.0, "raw_max": 1.0, "already_normalized": True},
            {"raw_name": "Y", "logical_name": "Pitch", "raw_value": 0.0, "raw_min": -1.0, "raw_max": 1.0, "already_normalized": True},
            {"raw_name": "Z", "logical_name": "Throttle", "raw_value": 0.0, "raw_min": -1.0, "raw_max": 1.0, "already_normalized": True},
            {"raw_name": "R", "logical_name": "Yaw", "raw_value": 0.0, "raw_min": -1.0, "raw_max": 1.0, "already_normalized": True},
            {"raw_name": "U", "logical_name": "Aux 1", "raw_value": 0.0, "raw_min": -1.0, "raw_max": 1.0, "already_normalized": True},
            {"raw_name": "V", "logical_name": "Aux 2", "raw_value": 0.0, "raw_min": -1.0, "raw_max": 1.0, "already_normalized": True},
        ),
        "buttons": {index: False for index in range(1, 16)},
        "hats": {1: "Centered"},
    }


def _service(tmp_path, *, roll: float = 0.73):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend

    backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        sample_frames=(_frame(roll),),
        clock=lambda: NOW,
        sample_source="physical",
    )
    return BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            physical_input_backend=backend,
            simulate=False,
            enable_output_verification=False,
            enable_output_loop=False,
            clock=lambda: NOW,
        )
    )


def test_hf_lrdc_6b_json_publish_failure_is_nonfatal_for_bridge_run_once(monkeypatch, tmp_path):
    import bridge_app.service as service_module

    service = _service(tmp_path)

    def locked_writer(path, payload):
        raise PermissionError(5, "Access is denied", str(path))

    monkeypatch.setattr(service_module, "write_telemetry", locked_writer)

    telemetry = service.run_once()

    assert telemetry.raw_axes.to_dict()["Roll"] == 0.73
    assert any("telemetry JSON publish failed" in warning for warning in telemetry.warnings)
    assert service.telemetry_publish_status["json_success"] is False
    assert "Access is denied" in str(service.telemetry_publish_status["json_error"])


def test_hf_lrdc_6b_embedded_runtime_emits_in_memory_telemetry_when_json_locked(monkeypatch, tmp_path):
    import bridge_app.service as service_module
    from v3_app.services.embedded_bridge_runtime import EmbeddedBridgeRuntime
    from v3_app.services.embedded_bridge_telemetry import read_embedded_bridge_telemetry

    service = _service(tmp_path, roll=0.61)
    monkeypatch.setattr(service_module, "write_telemetry", lambda path, payload: (_ for _ in ()).throw(PermissionError(5, "Access is denied", str(path))))
    seen = []
    runtime = EmbeddedBridgeRuntime(on_telemetry=seen.append, service_factory=lambda: service)

    telemetry = runtime.tick()
    result = read_embedded_bridge_telemetry(clock=lambda: NOW)

    assert seen[-1] is telemetry
    assert result.status.value == "Connected"
    assert result.source_label == "Embedded Bridge"
    assert result.telemetry is not None
    assert result.telemetry.raw_axes["Roll"] == 0.61


def test_hf_lrdc_6b_atomic_write_retries_transient_permission_error(monkeypatch, tmp_path):
    from bridge_app import ipc

    calls = {"count": 0}
    real_replace = ipc.Path.replace

    def flaky_replace(self, target):
        calls["count"] += 1
        if calls["count"] < 3:
            raise PermissionError(5, "Access is denied", str(target))
        return real_replace(self, target)

    monkeypatch.setattr(ipc.Path, "replace", flaky_replace)

    path = ipc.atomic_write_json(tmp_path / "telemetry.json", {"ok": True}, replace_attempts=4, retry_sleep_seconds=0)

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True}
    assert calls["count"] == 3


def test_hf_lrdc_6b_atomic_write_cleans_temp_file_on_final_failure(monkeypatch, tmp_path):
    from bridge_app import ipc

    monkeypatch.setattr(ipc.Path, "replace", lambda self, target: (_ for _ in ()).throw(PermissionError(5, "Access is denied", str(target))))

    try:
        ipc.atomic_write_json(tmp_path / "telemetry.json", {"ok": True}, replace_attempts=2, retry_sleep_seconds=0)
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")

    assert list(tmp_path.glob(".telemetry.json.*.tmp")) == []


def test_hf_lrdc_6b_live_axis_source_prefers_fresh_embedded_over_missing_json(tmp_path):
    from shared_core.runtime.runtime_bridge import RuntimeBridge
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.embedded_bridge_telemetry import record_embedded_bridge_telemetry
    from v3_app.services.live_input_source import LiveAxisSampleSource

    telemetry = _service(tmp_path, roll=0.44).run_once()
    record_embedded_bridge_telemetry(telemetry, recorded_at=NOW)
    source = LiveAxisSampleSource(
        RuntimeBridge(preflight_status=_service(tmp_path).runtime_status),
        bridge_client=BridgeTelemetryClient(telemetry_path=tmp_path / "missing.json", clock=lambda: NOW),
        clock=lambda: NOW,
    )

    axes = source.raw_axes()

    assert axes["Roll"] == 0.44
    assert source.last_source_label == "Embedded Bridge"


def test_hf_lrdc_6b_embedded_source_goes_stale_then_simulation_fallback(tmp_path):
    from shared_core.runtime.runtime_bridge import RuntimeBridge
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.embedded_bridge_telemetry import record_embedded_bridge_telemetry
    from v3_app.services.live_input_source import LiveAxisSampleSource

    service = _service(tmp_path, roll=0.88)
    record_embedded_bridge_telemetry(service.run_once(), recorded_at=NOW - timedelta(seconds=10))
    source = LiveAxisSampleSource(
        RuntimeBridge(preflight_status=service.runtime_status),
        bridge_client=BridgeTelemetryClient(telemetry_path=tmp_path / "missing.json", clock=lambda: NOW),
        clock=lambda: NOW,
    )

    axes = source.raw_axes()

    assert axes["Roll"] != 0.88
    assert source.last_source_label == "Simulation/fallback sample"
