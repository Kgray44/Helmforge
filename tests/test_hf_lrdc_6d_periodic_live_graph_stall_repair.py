from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


NOW = datetime(2026, 5, 10, 20, 0, 0, tzinfo=timezone.utc)


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


class CountingDiscoveryBackend:
    backend_name = "counting_discovery"

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


def _physical_backend(*, roll: float = 0.5, clock=None):
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend

    class CountingPhysicalInputBackend(FakePhysicalInputBackend):
        def __init__(self) -> None:
            super().__init__(
                (_hotas_device(),),
                sample_frames=(_frame(roll),),
                clock=clock or (lambda: NOW),
                sample_source="physical",
            )
            self.enumerate_calls = 0

        def enumerate_devices(self):
            self.enumerate_calls += 1
            return super().enumerate_devices()

    return CountingPhysicalInputBackend()


def _service(tmp_path: Path, *, discovery_backend=None, physical_backend=None, clock=None):
    from bridge_app.service import BridgeService, BridgeServiceOptions

    return BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            discovery_backend=discovery_backend or CountingDiscoveryBackend(),
            physical_input_backend=physical_backend or _physical_backend(clock=clock),
            simulate=False,
            enable_output_verification=False,
            enable_output_loop=False,
            discovery_refresh_interval_seconds=0.01,
            clock=clock or (lambda: NOW),
        )
    )


def test_hf_lrdc_6e_run_once_skips_slow_discovery_while_sampler_is_healthy(tmp_path):
    discovery = CountingDiscoveryBackend()
    service = _service(tmp_path, discovery_backend=discovery)
    assert discovery.calls == 1
    assert service.physical_sampler is not None

    time.sleep(0.02)
    service.run_once(publish_telemetry=False)
    service.run_once(publish_telemetry=False)

    assert discovery.calls == 1
    assert service.timing.discovery_skipped_reason == "active_sampler_healthy"
    assert service.timing.discovery_running is False


def test_hf_lrdc_6e_run_preflight_still_forces_discovery(tmp_path):
    from shared_core.runtime.bridge_contracts import BridgeCommandRequest, BridgeCommandType

    discovery = CountingDiscoveryBackend()
    service = _service(tmp_path, discovery_backend=discovery)
    service.handle_command(BridgeCommandRequest(command=BridgeCommandType.RUN_PREFLIGHT, request_id="preflight-6e"))

    assert discovery.calls == 2
    assert service.timing.last_discovery_refresh_reason == "forced"


def test_hf_lrdc_6e_active_sampler_uses_cached_selected_device_id(tmp_path):
    backend = _physical_backend()
    service = _service(tmp_path, physical_backend=backend)
    startup_enumerations = backend.enumerate_calls

    service.run_once(publish_telemetry=False)
    service.run_once(publish_telemetry=False)
    service.run_once(publish_telemetry=False)

    assert backend.enumerate_calls == startup_enumerations
    assert service.timing.selected_physical_device_id == "hotas-one"
    assert service.timing.selected_physical_device_source == "cached"
    assert service.timing.device_enumeration_skipped_cached_count >= 3


def test_hf_lrdc_6e_live_axis_source_reads_json_only_when_embedded_is_not_fresh(tmp_path):
    from shared_core.runtime.runtime_bridge import RuntimeBridge
    from v3_app.services.bridge_client import BridgeTelemetryReadResult, BridgeTelemetryStatus
    from v3_app.services.embedded_bridge_telemetry import clear_embedded_bridge_telemetry, record_embedded_bridge_telemetry
    from v3_app.services.live_input_source import LiveAxisSampleSource

    clock = FakeClock()
    service = _service(tmp_path, clock=clock)
    clear_embedded_bridge_telemetry()
    record_embedded_bridge_telemetry(service.run_once(publish_telemetry=False), recorded_at=clock())

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

    client = CountingBridgeClient()
    source = LiveAxisSampleSource(RuntimeBridge(preflight_status=service.runtime_status), bridge_client=client, clock=clock)

    assert source.raw_axes()["Roll"] == 0.5
    assert client.read_count == 0
    assert source.json_read_skipped_due_to_embedded_fresh is True

    clock.advance(1.4)
    source.raw_axes()
    assert client.read_count == 1
    assert source.json_read_duration_ms is not None


def test_hf_lrdc_6e_live_monitor_does_not_read_json_when_embedded_is_fresh(tmp_path):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from shared_core.models.workspace import create_default_workspace
    from shared_core.runtime.device_discovery import build_runtime_preflight_status
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState
    from v3_app.services.embedded_bridge_telemetry import clear_embedded_bridge_telemetry, record_embedded_bridge_telemetry

    app = QApplication.instance() or QApplication([])
    clock = FakeClock()
    service = _service(tmp_path, clock=clock)
    clear_embedded_bridge_telemetry()
    record_embedded_bridge_telemetry(service.run_once(publish_telemetry=False), recorded_at=clock())
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(build_runtime_preflight_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=build_runtime_preflight_status(),
        telemetry_path=tmp_path / "missing.json",
        bridge_clock=clock,
    )

    class FailingJsonClient:
        def read(self):
            raise AssertionError("fresh Embedded Bridge telemetry should bypass JSON fallback reads")

    page._bridge_client = FailingJsonClient()
    result = page._read_bridge_telemetry()

    assert result.source_label == "Embedded Bridge"
    assert page.json_read_skipped_due_to_embedded_fresh is True
    app.processEvents()


def test_hf_lrdc_6e_publish_telemetry_writes_json_once(monkeypatch, tmp_path):
    import bridge_app.service as service_module

    writes = []
    service = _service(tmp_path)
    telemetry = service.run_once(publish_telemetry=False)

    def counting_writer(path, payload):
        writes.append((path, payload))
        return path

    monkeypatch.setattr(service_module, "write_telemetry", counting_writer)
    status = service._publish_telemetry(telemetry)

    assert status["json_success"] is True
    assert len(writes) == 1
