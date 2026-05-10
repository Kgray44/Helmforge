from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)


class _Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


class CountingFakeOutputBackend:
    def __init__(self, *, fail_writes: bool = False) -> None:
        from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend

        self._backend = FakeVirtualOutputBackend(fail_writes=fail_writes)
        self.verify_calls = 0

    def get_capabilities(self):
        return self._backend.get_capabilities()

    def get_status(self):
        return self._backend.get_status()

    def enumerate_output_devices(self):
        return self._backend.enumerate_output_devices()

    def select_output_device(self, device_id: str):
        return self._backend.select_output_device(device_id)

    def write_output_intent(self, output_intent):
        return self._backend.write_output_intent(output_intent)

    def verify_output_write(self, output_intent):
        self.verify_calls += 1
        return self._backend.verify_output_write(output_intent)

    @property
    def written_intents(self):
        return self._backend.written_intents

    @property
    def last_written_intent(self):
        return self._backend.last_written_intent


def _hotas_device():
    from shared_core.runtime.hotas_input import build_physical_input_device_info

    return build_physical_input_device_info(
        device_id="hotas-one",
        display_name="Thrustmaster T.Flight HOTAS One",
        manufacturer="Thrustmaster",
        vendor_id="044f",
        product_id="b68d",
        axis_count=6,
        button_count=15,
        hat_count=1,
        backend_name="fake_physical",
    )


def _frame(value: int = 32768):
    return {
        "axes": (
            {"raw_name": "X", "logical_name": "Roll", "raw_value": value, "raw_min": 0, "raw_max": 65535},
            {"raw_name": "Y", "logical_name": "Pitch", "raw_value": value, "raw_min": 0, "raw_max": 65535},
            {"raw_name": "Z", "logical_name": "Throttle", "raw_value": value, "raw_min": 0, "raw_max": 65535},
            {"raw_name": "R", "logical_name": "Yaw", "raw_value": value, "raw_min": 0, "raw_max": 65535},
            {"raw_name": "U", "logical_name": "Aux 1", "raw_value": value, "raw_min": 0, "raw_max": 65535},
            {"raw_name": "V", "logical_name": "Aux 2", "raw_value": value, "raw_min": 0, "raw_max": 65535},
        ),
        "buttons": {index: False for index in range(1, 16)},
        "hats": {1: "Centered"},
    }


def _service(tmp_path, *, backend=None, simulate: bool = False, enable_verification: bool = True, enable_loop: bool = True):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend

    clock = _Clock()
    physical = FakePhysicalInputBackend(
        (_hotas_device(),),
        sample_frames=(_frame(),),
        clock=clock,
        sample_source="physical",
    )
    output = backend or CountingFakeOutputBackend()
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            physical_input_backend=physical,
            virtual_output_backend=output,
            simulate=simulate,
            enable_output_verification=enable_verification,
            enable_output_loop=enable_loop,
            enable_live_input=True,
            clock=clock,
        )
    )
    return service, clock, output


def test_hf_lrdc_2a_bridge_reuses_output_loop_and_preserves_write_state(tmp_path):
    service, clock, backend = _service(tmp_path)

    loop_id = id(service.virtual_output_loop)
    service.run_once()
    first_payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    first_write_count = first_payload["output_loop_runtime"]["write_count"]
    clock.advance(0.05)
    service.run_once()
    second_payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))

    assert id(service.virtual_output_loop) == loop_id
    assert second_payload["output_loop_runtime"]["write_count"] > first_write_count
    assert second_payload["output_loop_runtime"]["loop_recreated_count"] == 0
    assert backend.verify_calls == 1
    assert second_payload["runtime_frame"]["full_live_runtime_ready"] is False
    assert second_payload["runtime_frame"]["fake_or_real_path"] == "fake_test"


def test_hf_lrdc_2a_rate_limiter_is_not_reset_by_normal_fast_ticks(tmp_path):
    service, _clock, backend = _service(tmp_path)

    service.run_once()
    first_payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    service.run_once()
    second_payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))

    assert second_payload["output_loop_runtime"]["write_count"] == first_payload["output_loop_runtime"]["write_count"]
    assert len(backend.written_intents) == first_payload["output_loop_runtime"]["write_count"]
    assert second_payload["output_loop_runtime"]["state"] == "running"


def test_hf_lrdc_2a_run_preflight_can_refresh_cached_verification_without_per_tick_rerun(tmp_path):
    service, _clock, backend = _service(tmp_path)
    command_path = tmp_path / "command.json"

    service.run_once()
    assert backend.verify_calls == 1
    service.run_once()
    assert backend.verify_calls == 1

    command_path.write_text(
        json.dumps({"command": "RunPreflight", "request_id": "preflight-2a", "created_at": NOW.isoformat()}),
        encoding="utf-8",
    )
    service.run_once()
    assert backend.verify_calls == 2

    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    assert payload["output_loop_runtime"]["verification_cached"] is True
    assert payload["output_loop_runtime"]["verification_status"] == "fake_verified"
    assert payload["output_loop_runtime"]["verification_age_ms"] >= 0
    assert payload["output_loop_runtime"]["loop_recreated_count"] == 1
    assert payload["output_loop_runtime"]["last_recreate_reason"] == "verification_refreshed"


def test_hf_lrdc_2a_failed_or_disabled_verification_keeps_loop_disabled_and_truth_false(tmp_path):
    backend = CountingFakeOutputBackend()
    service, _clock, backend = _service(tmp_path, backend=backend, enable_verification=False)

    telemetry = service.run_once().to_dict()
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))

    assert backend.verify_calls == 0
    assert payload["output_loop_runtime"]["verification_status"] == "not_attempted"
    assert payload["output_loop_runtime"]["enabled"] is False
    assert payload["output_loop_runtime"]["write_count"] == 0
    assert telemetry["output_verified"] is False
    assert telemetry["runtime_frame"]["full_live_runtime_ready"] is False


def test_hf_lrdc_2a_switch_to_simulation_disables_persistent_loop_and_restores_neutral(tmp_path):
    service, clock, backend = _service(tmp_path)
    service.run_once()
    clock.advance(0.05)
    service.run_once()
    assert json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))["output_loop_runtime"]["write_count"] >= 2

    (tmp_path / "command.json").write_text(
        json.dumps({"command": "SwitchToSimulation", "request_id": "sim-2a", "created_at": NOW.isoformat()}),
        encoding="utf-8",
    )
    service.run_once()
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))

    assert payload["output_loop_runtime"]["enabled"] is False
    assert payload["output_loop_runtime"]["state"] in {"disabled", "stopped_neutral"}
    assert payload["output_loop_runtime"]["neutral_restore_status"] == "restored"
    assert backend.written_intents[-1].source == "neutral_restore"
    assert payload["output_verified"] is False


def test_hf_lrdc_2a_write_failure_safety_state_persists_in_telemetry(tmp_path):
    backend = CountingFakeOutputBackend(fail_writes=True)
    service, _clock, _backend = _service(tmp_path, backend=backend)

    service.run_once()
    service.run_once()
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))

    assert payload["output_loop_runtime"]["state"] == "safety_stopped"
    assert payload["output_loop_runtime"]["safety_stop_reason"] == "write_failed"
    assert payload["output_loop_runtime"]["failure_count"] == 1
    assert payload["runtime_frame"]["full_live_runtime_ready"] is False


def test_hf_lrdc_2a_bridge_client_passes_output_loop_runtime(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    service, _clock, _backend = _service(tmp_path)
    service.run_once()

    parsed = BridgeTelemetryClient(telemetry_path=tmp_path / "telemetry.json", stale_after_seconds=3600).read()

    assert parsed.status is BridgeTelemetryStatus.CONNECTED
    assert parsed.telemetry is not None
    assert parsed.telemetry.output_loop_runtime is not None
    assert parsed.telemetry.output_loop_runtime["backend_name"] == "Fake output backend"
    assert "output_loop_runtime" in json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
