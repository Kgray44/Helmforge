from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone


NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)


class _Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


class RaisingOutputBackend:
    def __init__(self) -> None:
        from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend

        self._backend = FakeVirtualOutputBackend()

    def get_capabilities(self):
        return self._backend.get_capabilities()

    def get_status(self):
        return self._backend.get_status()

    def enumerate_output_devices(self):
        return self._backend.enumerate_output_devices()

    def select_output_device(self, device_id: str):
        return self._backend.select_output_device(device_id)

    def verify_output_write(self, output_intent):
        return self._backend.verify_output_write(output_intent)

    def write_output_intent(self, output_intent):
        raise RuntimeError("boom write failed")


def _intent(source: str = "test"):
    from shared_core.runtime.vjoy_output import VirtualAxisOutput, VirtualOutputIntent

    return VirtualOutputIntent(
        timestamp=NOW,
        source=source,
        axes=(VirtualAxisOutput("X", 0.25),),
        output_enabled=True,
        write_requested=True,
    )


def _verified_fake_loop(*, clock: _Clock | None = None, fail_writes: bool = False, fail_neutral_restore: bool = False, rate_hz: float = 10.0):
    from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend, VirtualOutputIntent, VirtualOutputLoopConfig, VirtualOutputWriteLoop

    clock = clock or _Clock()
    backend = FakeVirtualOutputBackend(fail_writes=fail_writes, fail_neutral_restore=fail_neutral_restore)
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="verify", timestamp=clock()))
    loop = VirtualOutputWriteLoop(
        backend=backend,
        verification=verification,
        config=VirtualOutputLoopConfig(write_rate_hz=rate_hz),
        clock=clock,
    )
    return loop, backend, clock


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


def _service(tmp_path, *, backend=None):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend
    from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend

    clock = _Clock()
    physical = FakePhysicalInputBackend(
        (_hotas_device(),),
        sample_frames=(_frame(),),
        clock=clock,
        sample_source="physical",
    )
    output = backend or FakeVirtualOutputBackend()
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            physical_input_backend=physical,
            virtual_output_backend=output,
            simulate=False,
            enable_output_verification=True,
            enable_output_loop=True,
            enable_live_input=True,
            clock=clock,
        )
    )
    return service, clock, output


def test_hf_lrdc_2b_cadence_counts_rate_limited_skips_without_success(tmp_path):
    loop, backend, clock = _verified_fake_loop(rate_hz=10.0)
    loop.enable()

    first = loop.tick(_intent())
    second = loop.tick(_intent())
    clock.advance(0.11)
    third = loop.tick(_intent())

    assert first.write_success_count == 1
    assert second.write_success_count == 1
    assert second.write_skipped_count == 1
    assert second.write_skipped_rate_limited_count == 1
    assert second.last_write_status == "skipped_rate_limited"
    assert second.last_skipped_write_reason == "skipped_rate_limited"
    assert third.write_success_count == 2
    assert third.actual_write_rate_hz is not None
    assert len(backend.written_intents) == 2


def test_hf_lrdc_2b_disabled_and_unverified_skips_are_classified():
    from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend, VirtualOutputWriteLoop

    disabled_loop, _backend, _clock = _verified_fake_loop()
    disabled = disabled_loop.tick(_intent())
    assert disabled.write_skipped_disabled_count == 1
    assert disabled.last_write_status == "skipped_disabled"

    unverified_backend = FakeVirtualOutputBackend()
    unverified_loop = VirtualOutputWriteLoop(backend=unverified_backend)
    unverified_loop.enable()
    unverified = unverified_loop.tick(_intent())
    assert unverified.write_skipped_count >= 1
    assert unverified.write_skipped_unsafe_count >= 1
    assert unverified.last_write_status == "skipped_unverified"
    assert unverified.write_success_count == 0


def test_hf_lrdc_2b_failure_triggers_safety_stop_and_refuses_followup_writes():
    loop, _backend, _clock = _verified_fake_loop(fail_writes=True)
    loop.enable()

    failed = loop.tick(_intent())
    followup = loop.tick(_intent())

    assert failed.state.value == "safety_stopped"
    assert failed.write_failure_count == 1
    assert failed.consecutive_write_failures == 1
    assert failed.safety_stop_reason == "write_failed"
    assert failed.safety_stop_timestamp is not None
    assert followup.write_skipped_safety_count == 1
    assert followup.last_write_status == "skipped_safety_stopped"
    assert followup.write_success_count == 0


def test_hf_lrdc_2b_backend_exceptions_are_safety_stopped_not_crashed():
    from shared_core.runtime.vjoy_output import VirtualOutputIntent, VirtualOutputLoopConfig, VirtualOutputWriteLoop

    clock = _Clock()
    backend = RaisingOutputBackend()
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="verify", timestamp=clock()))
    loop = VirtualOutputWriteLoop(
        backend=backend,
        verification=verification,
        config=VirtualOutputLoopConfig(write_rate_hz=30.0),
        clock=clock,
    )
    loop.enable()

    snapshot = loop.tick(_intent())

    assert snapshot.state.value == "safety_stopped"
    assert snapshot.write_failure_count == 1
    assert snapshot.safety_stop_reason == "error"
    assert "boom" in snapshot.last_error


def test_hf_lrdc_2b_neutral_restore_success_failure_and_not_attempted_are_truthful():
    loop, backend, _clock = _verified_fake_loop()
    not_needed = loop.disable()
    assert not_needed.neutral_restore_attempted is False
    assert not_needed.neutral_restore_status == "not_attempted"

    loop.enable()
    loop.tick(_intent())
    restored = loop.disable()
    assert restored.neutral_restore_attempted is True
    assert restored.neutral_restore_status == "restored"
    assert restored.neutral_restore_timestamp is not None
    assert restored.neutral_restore_duration_ms is not None
    assert backend.written_intents[-1].source == "neutral_restore"

    failing_loop, _failing_backend, _clock = _verified_fake_loop(fail_neutral_restore=True)
    failing_loop.enable()
    failing_loop.tick(_intent())
    failed = failing_loop.disable()
    assert failed.neutral_restore_attempted is True
    assert failed.neutral_restore_status == "failed"
    assert failed.neutral_restore_error


def test_hf_lrdc_2b_bridge_telemetry_exposes_cadence_safety_and_timing(tmp_path):
    service, clock, _backend = _service(tmp_path)

    service.run_once()
    service.run_once()
    clock.advance(0.05)
    telemetry = service.run_once().to_dict()
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    runtime = payload["output_loop_runtime"]
    timing = payload["bridge_timing"]

    for field in (
        "actual_write_rate_hz",
        "tick_count",
        "write_attempt_count",
        "write_success_count",
        "write_failure_count",
        "write_skipped_count",
        "write_skipped_rate_limited_count",
        "write_skipped_disabled_count",
        "write_skipped_safety_count",
        "consecutive_write_failures",
        "last_skipped_write_reason",
        "neutral_restore_attempted",
        "neutral_restore_timestamp",
        "neutral_restore_duration_ms",
        "safety_stop_timestamp",
    ):
        assert field in runtime
    assert runtime["write_success_count"] >= 2
    assert runtime["write_skipped_rate_limited_count"] >= 1
    assert timing["last_output_loop_tick_duration_ms"] >= 0
    assert timing["last_output_loop_status"]
    assert timing["output_loop_rate_limited"] is False
    assert timing["output_loop_safety_stopped"] is False
    assert telemetry["runtime_frame"]["full_live_runtime_ready"] is False


def test_hf_lrdc_2b_bridge_client_and_live_monitor_show_output_safety_truth(tmp_path):
    from PySide6.QtWidgets import QApplication, QLabel
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QApplication.instance() or QApplication([])
    service, _clock, _backend = _service(tmp_path)
    service.run_once()
    service.run_once()

    parsed = BridgeTelemetryClient(telemetry_path=tmp_path / "telemetry.json", stale_after_seconds=3600).read()
    assert parsed.status is BridgeTelemetryStatus.CONNECTED
    assert parsed.telemetry is not None
    assert parsed.telemetry.output_loop_runtime is not None
    assert "write_skipped_count" in parsed.telemetry.output_loop_runtime

    page = LiveMonitorPage(
        state=AppState.from_runtime_status(service.runtime_status, driver_detected=True),
        runtime_status=service.runtime_status,
        telemetry_path=tmp_path / "telemetry.json",
        bridge_stale_after_seconds=3600,
    )
    labels = " ".join(label.text() for label in page.findChildren(QLabel))
    assert "Output loop runtime:" in labels
    assert "target 30.0 Hz" in labels
    assert "skipped" in labels
    assert "neutral" in labels
    assert "safety" in labels
    assert "Full Live Runtime Ready true" not in labels
