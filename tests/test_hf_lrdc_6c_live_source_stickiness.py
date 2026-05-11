from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


NOW = datetime(2026, 5, 10, 17, 0, 0, tzinfo=timezone.utc)


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


def _frame(roll: float):
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


def _service(tmp_path, *, roll: float, clock=None):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend

    clock = clock or (lambda: NOW)
    backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        sample_frames=(_frame(roll),),
        clock=clock,
        sample_source="physical",
    )
    return BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / f"telemetry-{roll}.json",
            command_path=tmp_path / f"command-{roll}.json",
            physical_input_backend=backend,
            simulate=False,
            enable_output_verification=False,
            enable_output_loop=False,
            clock=clock,
        )
    )


def _json_result(tmp_path, *, roll: float, clock):
    from v3_app.services.bridge_client import BridgeTelemetryClient

    service = _service(tmp_path, roll=roll, clock=clock)
    service.run_once()
    return BridgeTelemetryClient(telemetry_path=service.options.telemetry_path, clock=clock).read()


def test_hf_lrdc_6c_selector_keeps_embedded_when_json_refreshes(tmp_path):
    from v3_app.services.embedded_bridge_telemetry import read_embedded_bridge_telemetry, record_embedded_bridge_telemetry
    from v3_app.services.live_source_arbitration import LiveTelemetrySourceSelector

    clock = FakeClock()
    selector = LiveTelemetrySourceSelector(clock=clock)
    embedded = _service(tmp_path, roll=0.55, clock=clock).run_once()
    record_embedded_bridge_telemetry(embedded, recorded_at=clock())
    selected = selector.select(
        embedded_result=read_embedded_bridge_telemetry(clock=clock),
        json_result=_json_result(tmp_path, roll=-0.9, clock=clock),
    )
    assert selected.source_label == "Embedded Bridge"
    assert selected.telemetry.raw_axes["Roll"] == 0.55
    assert selector.snapshot().source_switch_count == 1

    for value in (-0.7, -0.2, 0.1):
        clock.advance(0.2)
        selected = selector.select(
            embedded_result=read_embedded_bridge_telemetry(clock=clock),
            json_result=_json_result(tmp_path, roll=value, clock=clock),
        )
        assert selected.source_label == "Embedded Bridge"
        assert selected.telemetry.raw_axes["Roll"] == 0.55

    assert selector.snapshot().source_switch_count == 1
    assert selector.snapshot().source_locked_to_embedded is True


def test_hf_lrdc_6c_selector_falls_back_when_embedded_stale_then_returns(tmp_path):
    from v3_app.services.embedded_bridge_telemetry import read_embedded_bridge_telemetry, record_embedded_bridge_telemetry
    from v3_app.services.live_source_arbitration import LiveTelemetrySourceSelector

    clock = FakeClock()
    selector = LiveTelemetrySourceSelector(clock=clock, embedded_stale_after_seconds=1.0)
    record_embedded_bridge_telemetry(_service(tmp_path, roll=0.25, clock=clock).run_once(), recorded_at=clock())
    assert selector.select(embedded_result=read_embedded_bridge_telemetry(clock=clock), json_result=_json_result(tmp_path, roll=-0.1, clock=clock)).source_label == "Embedded Bridge"

    clock.advance(1.2)
    selected = selector.select(
        embedded_result=read_embedded_bridge_telemetry(clock=clock),
        json_result=_json_result(tmp_path, roll=-0.4, clock=clock),
    )
    assert selected.source_label == "Bridge JSON Snapshot"
    assert selected.telemetry.raw_axes["Roll"] == -0.4
    assert "Embedded Bridge unavailable/stale" in selector.snapshot().fallback_reason

    record_embedded_bridge_telemetry(_service(tmp_path, roll=0.77, clock=clock).run_once(), recorded_at=clock())
    selected = selector.select(
        embedded_result=read_embedded_bridge_telemetry(clock=clock),
        json_result=_json_result(tmp_path, roll=-0.8, clock=clock),
    )
    assert selected.source_label == "Embedded Bridge"
    assert selected.telemetry.raw_axes["Roll"] == 0.77
    assert selector.snapshot().last_switch_reason == "embedded frame fresh"


def test_hf_lrdc_6c_live_axis_source_does_not_alternate_to_json_or_simulation(tmp_path):
    from shared_core.runtime.runtime_bridge import RuntimeBridge
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.embedded_bridge_telemetry import record_embedded_bridge_telemetry
    from v3_app.services.live_input_source import LiveAxisSampleSource

    clock = FakeClock()
    embedded_service = _service(tmp_path, roll=0.66, clock=clock)
    record_embedded_bridge_telemetry(embedded_service.run_once(), recorded_at=clock())
    json_service = _service(tmp_path, roll=-0.66, clock=clock)
    source = LiveAxisSampleSource(
        RuntimeBridge(preflight_status=embedded_service.runtime_status),
        bridge_client=BridgeTelemetryClient(telemetry_path=json_service.options.telemetry_path, clock=clock),
        clock=clock,
    )

    for _ in range(3):
        json_service.run_once()
        axes = source.raw_axes()
        assert axes["Roll"] == 0.66
        assert source.last_source_label == "Embedded Bridge"
        clock.advance(0.2)


def test_hf_lrdc_6c_live_monitor_read_keeps_embedded_over_fresh_json(tmp_path):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from shared_core.models.workspace import create_default_workspace
    from shared_core.runtime.device_discovery import build_runtime_preflight_status
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState
    from v3_app.services.embedded_bridge_telemetry import record_embedded_bridge_telemetry

    app = QApplication.instance() or QApplication([])
    clock = FakeClock()
    embedded_service = _service(tmp_path, roll=0.31, clock=clock)
    json_service = _service(tmp_path, roll=-0.31, clock=clock)
    record_embedded_bridge_telemetry(embedded_service.run_once(), recorded_at=clock())
    json_service.run_once()

    page = LiveMonitorPage(
        state=AppState.from_runtime_status(build_runtime_preflight_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=build_runtime_preflight_status(),
        telemetry_path=json_service.options.telemetry_path,
        bridge_clock=clock,
    )

    first = page._read_bridge_telemetry()
    assert first.source_label == "Embedded Bridge"
    assert first.telemetry.raw_axes["Roll"] == 0.31

    clock.advance(0.4)
    json_service.run_once()
    second = page._read_bridge_telemetry()
    assert second.source_label == "Embedded Bridge"
    assert second.telemetry.raw_axes["Roll"] == 0.31
    app.processEvents()


def test_hf_lrdc_6c_source_freshness_does_not_create_runtime_proof(tmp_path):
    from v3_app.services.embedded_bridge_telemetry import read_embedded_bridge_telemetry, record_embedded_bridge_telemetry

    clock = FakeClock()
    telemetry = _service(tmp_path, roll=0.2, clock=clock).run_once()
    record_embedded_bridge_telemetry(telemetry, recorded_at=clock())
    result = read_embedded_bridge_telemetry(clock=clock)

    assert result.status.value == "Connected"
    assert result.telemetry.output_verified is False
    assert result.telemetry.runtime_frame.full_live_runtime_ready is False
