from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


NOW = datetime(2026, 5, 10, 19, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _clear_embedded_telemetry_cache():
    from v3_app.services.embedded_bridge_telemetry import clear_embedded_bridge_telemetry

    clear_embedded_bridge_telemetry()
    yield
    clear_embedded_bridge_telemetry()


class FakeClock:
    def __init__(self, value: datetime = NOW) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value = self.value + timedelta(seconds=seconds)


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


def _frame(roll: float = 0.5):
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


def _fake_backend(*, roll: float = 0.5, clock=None):
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend

    return FakePhysicalInputBackend(
        (_hotas_device(),),
        sample_frames=(_frame(roll),),
        clock=clock or (lambda: NOW),
        sample_source="physical",
    )


def _service(tmp_path: Path, *, roll: float = 0.5, clock=None, discovery_backend=None):
    from bridge_app.service import BridgeService, BridgeServiceOptions

    return BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            discovery_backend=discovery_backend,
            physical_input_backend=_fake_backend(roll=roll, clock=clock),
            simulate=False,
            enable_output_verification=False,
            enable_output_loop=False,
            clock=clock or (lambda: NOW),
        )
    )


def test_hf_lrdc_6d_bridge_run_once_can_skip_json_publish_and_periodic_discovery(monkeypatch, tmp_path):
    import bridge_app.service as service_module
    from bridge_app.service import BridgeService, BridgeServiceOptions

    class CountingDiscovery:
        backend_name = "counting"

        def __init__(self) -> None:
            self.calls = 0

        def enumerate_devices(self):
            self.calls += 1
            return ()

    discovery = CountingDiscovery()
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            discovery_backend=discovery,
            physical_input_backend=_fake_backend(),
            simulate=False,
            enable_output_verification=False,
            enable_output_loop=False,
            discovery_refresh_interval_seconds=0.01,
            enable_periodic_discovery_refresh=False,
            clock=lambda: NOW,
        )
    )
    assert discovery.calls == 1

    def locked_writer(path, payload):
        raise AssertionError("JSON telemetry publish should not run for an embedded in-memory tick")

    monkeypatch.setattr(service_module, "write_telemetry", locked_writer)
    time.sleep(0.02)
    telemetry = service.run_once(publish_telemetry=False)

    assert telemetry.raw_axes.to_dict()["Roll"] == 0.5
    assert discovery.calls == 1
    assert service.timing.slow_lane_status in {"cached_periodic_disabled", "cached_sampler_active"}
    assert service.timing.last_telemetry_publish_duration_ms == 0.0


def test_hf_lrdc_6d_embedded_runtime_worker_does_not_block_qt_timers(tmp_path):
    from PySide6.QtCore import QCoreApplication, QTimer
    from v3_app.services.embedded_bridge_runtime import EmbeddedBridgeRuntime

    app = QCoreApplication.instance() or QCoreApplication([])
    main_thread_id = threading.get_ident()

    class SlowService:
        def __init__(self) -> None:
            self.options = SimpleNamespace(telemetry_path=tmp_path / "telemetry.json")
            self.thread_ids: list[int] = []
            self.timing = SimpleNamespace(last_worker_tick_duration_ms=0.0, embedded_worker_late_tick_count=0)

        def run_once(self, *, publish_telemetry=True):
            self.thread_ids.append(threading.get_ident())
            time.sleep(0.2)
            return _service(tmp_path, roll=0.42).run_once(publish_telemetry=False)

        def build_telemetry_payload(self, telemetry):
            return telemetry.to_dict()

    service = SlowService()
    seen = []
    ui_ticks = {"count": 0}
    timer = QTimer()
    timer.setInterval(20)
    timer.timeout.connect(lambda: ui_ticks.__setitem__("count", ui_ticks["count"] + 1))
    runtime = EmbeddedBridgeRuntime(
        on_telemetry=seen.append,
        service_factory=lambda: service,
        interval_ms=50,
        threaded=True,
        publish_diagnostic_json=False,
    )

    timer.start()
    runtime.start()
    deadline = time.monotonic() + 0.35
    while time.monotonic() < deadline and not seen:
        app.processEvents()
        time.sleep(0.005)
    runtime.stop()
    timer.stop()
    app.processEvents()

    assert seen
    assert ui_ticks["count"] >= 3
    assert service.thread_ids
    assert service.thread_ids[0] != main_thread_id


def test_hf_lrdc_6d_async_json_publisher_does_not_block_submit(tmp_path):
    from v3_app.services.embedded_bridge_runtime import AsyncTelemetryJsonPublisher

    writes = []
    write_started = threading.Event()

    def slow_writer(path, payload):
        write_started.set()
        time.sleep(0.2)
        writes.append((path, payload))

    publisher = AsyncTelemetryJsonPublisher(writer=slow_writer)
    started = time.perf_counter()
    publisher.start()
    publisher.submit(tmp_path / "telemetry.json", {"ok": True})
    submit_ms = (time.perf_counter() - started) * 1000.0

    assert submit_ms < 50.0
    assert write_started.wait(1.0)
    publisher.stop(timeout_ms=1000)
    assert writes == [(tmp_path / "telemetry.json", {"ok": True})]
    assert publisher.status()["last_status"] == "ok"


def test_hf_lrdc_6d_live_axis_source_skips_json_read_when_embedded_is_fresh(tmp_path):
    from shared_core.runtime.runtime_bridge import RuntimeBridge
    from v3_app.services.bridge_client import BridgeTelemetryReadResult, BridgeTelemetryStatus
    from v3_app.services.embedded_bridge_telemetry import clear_embedded_bridge_telemetry, record_embedded_bridge_telemetry
    from v3_app.services.live_input_source import LiveAxisSampleSource

    clear_embedded_bridge_telemetry()
    clock = FakeClock()
    telemetry = _service(tmp_path, roll=0.64, clock=clock).run_once(publish_telemetry=False)
    record_embedded_bridge_telemetry(telemetry, recorded_at=clock())

    class CountingBridgeClient:
        def __init__(self) -> None:
            self.read_count = 0

        def read(self):
            self.read_count += 1
            return BridgeTelemetryReadResult(
                status=BridgeTelemetryStatus.MISSING,
                path=tmp_path / "missing.json",
                message="missing",
                last_read_at=clock(),
                source_label="Bridge Missing",
            )

    bridge_client = CountingBridgeClient()
    source = LiveAxisSampleSource(
        RuntimeBridge(preflight_status=_service(tmp_path, clock=clock).runtime_status),
        bridge_client=bridge_client,
        clock=clock,
    )

    axes = source.raw_axes()

    assert axes["Roll"] == 0.64
    assert source.last_source_label == "Embedded Bridge"
    assert bridge_client.read_count == 0


def test_hf_lrdc_6d_embedded_memory_frame_keeps_full_bridge_payload(tmp_path):
    from v3_app.services.embedded_bridge_telemetry import (
        clear_embedded_bridge_telemetry,
        read_embedded_bridge_telemetry,
        record_embedded_bridge_telemetry,
    )

    clear_embedded_bridge_telemetry()
    clock = FakeClock()
    service = _service(tmp_path, roll=0.25, clock=clock)
    telemetry = service.run_once(publish_telemetry=False)
    payload = service.build_telemetry_payload(telemetry)

    record_embedded_bridge_telemetry(telemetry, recorded_at=clock(), payload=payload)
    result = read_embedded_bridge_telemetry(clock=clock)

    assert result.telemetry is not None
    assert result.telemetry.raw_axes["Roll"] == 0.25
    assert isinstance(result.telemetry.bridge_timing, dict)
    assert result.telemetry.bridge_timing["tick_count"] == service.state.tick_count
    assert isinstance(result.telemetry.physical_input_fidelity, dict)


def test_hf_lrdc_6d_ui_stall_monitor_records_only_large_frame_gaps():
    from v3_app.services.live_stall_diagnostics import UiStallMonitor

    clock = FakeClock()
    monitor = UiStallMonitor(clock=clock, threshold_ms=250.0)

    monitor.observe()
    clock.advance(0.016)
    monitor.observe()
    assert monitor.snapshot().ui_stall_count == 0
    assert monitor.snapshot().last_ui_frame_delta_ms == 16.0

    clock.advance(0.42)
    snapshot = monitor.observe()

    assert snapshot.ui_stall_count == 1
    assert snapshot.last_ui_stall_duration_ms == 420.0
    assert snapshot.last_ui_stall_at == clock()
