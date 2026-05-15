from __future__ import annotations

import json
from datetime import datetime, timezone


NOW = datetime(2026, 5, 10, 15, 0, 0, tzinfo=timezone.utc)


def _raw_device():
    from shared_core.runtime.hotas_input import RawInputDeviceRecord

    return RawInputDeviceRecord(
        device_id="raw:HID#VID_044F&PID_B68D#7&abc",
        display_name="Thrustmaster T.Flight HOTAS One",
        vendor_id="044f",
        product_id="b68d",
        handle=1234,
        report_size=17,
    )


class FakeRawInputProvider:
    provider_available = True

    def __init__(self, reports=(), *, available=True, started=True):
        self.provider_available = available
        self._reports = list(reports)
        self._started = started
        self._sequence = 0
        self.started_device_id = None

    def enumerate_devices(self):
        return (_raw_device(),) if self.provider_available else ()

    def start(self, device_id=None):
        self.started_device_id = device_id
        if not self.provider_available:
            return False, "provider unavailable"
        self._started = True
        return True, "started"

    def stop(self):
        self._started = False

    def read_current_report(self):
        if not self._started or not self._reports:
            return None
        report = self._reports[min(self._sequence, len(self._reports) - 1)]
        self._sequence += 1
        return report


def _raw_report_bytes(*, roll=65535, pitch=0, throttle=32768, yaw=40000, aux1=1000, aux2=64000, buttons=0b100000000000011, hat=2):
    values = (roll, pitch, throttle, yaw, aux1, aux2)
    payload = b"".join(int(value).to_bytes(2, "little", signed=False) for value in values)
    payload += int(buttons).to_bytes(2, "little", signed=False)
    payload += bytes([hat])
    return payload


def test_hf_lrdc_6a_raw_input_backend_is_safe_when_provider_missing():
    from shared_core.runtime.hotas_input import WindowsRawInputBackend

    backend = WindowsRawInputBackend(provider=None)

    assert backend.enumerate_devices() == ()
    caps = backend.get_capabilities()
    assert caps.backend_kind == "windows_raw_input"
    assert caps.backend_available is False
    assert caps.requires_message_loop is True
    assert backend.read_current_state().sampling_active is False


def test_hf_lrdc_6a_device_record_maps_supported_vid_pid_to_device_info():
    from shared_core.runtime.hotas_input import raw_input_device_record_to_device_info

    device = raw_input_device_record_to_device_info(_raw_device(), backend_name="windows_raw_input")

    assert device.is_supported is True
    assert device.vendor_id == "044f"
    assert device.product_id == "b68d"
    assert device.axis_count == 6
    assert device.button_count == 15
    assert device.hat_count == 1


def test_hf_lrdc_6a_fake_raw_input_report_decodes_to_physical_snapshot():
    from shared_core.runtime.hotas_input import WindowsRawInputBackend

    backend = WindowsRawInputBackend(
        provider=FakeRawInputProvider((_raw_report_bytes(),)),
        clock=lambda: NOW,
    )
    device = backend.enumerate_devices()[0]
    backend.open_device(device.device_id)
    snapshot = backend.read_current_state()

    assert snapshot.sampling_active is True
    assert snapshot.backend_name == "windows_raw_input"
    assert snapshot.sample_source == "raw_input"
    assert snapshot.sequence == 1
    assert snapshot.estimated_sample_rate_hz is None
    assert snapshot.axis_by_logical_name("Roll").raw_value == 65535
    assert snapshot.axis_by_logical_name("Pitch").raw_value == 0
    assert snapshot.axis_by_logical_name("Throttle").raw_value == 32768
    assert [button.button_index for button in snapshot.buttons if button.pressed] == [1, 2, 15]
    assert snapshot.hats[0].normalized_direction == "East"


def test_hf_lrdc_6a_backend_selector_prefers_winmm_over_uncalibrated_raw_input_and_falls_back():
    from shared_core.runtime.hotas_input import (
        FakePhysicalInputBackend,
        PhysicalInputBackendSelector,
        WindowsRawInputBackend,
        build_physical_input_device_info,
    )

    raw = WindowsRawInputBackend(provider=FakeRawInputProvider((_raw_report_bytes(),)))
    winmm = FakePhysicalInputBackend(
        (
            build_physical_input_device_info(
                device_id="winmm:0",
                display_name="Thrustmaster T.Flight HOTAS One",
                vendor_id="044f",
                product_id="b68d",
                backend_name="fake_winmm",
            ),
        ),
        backend_name="fake_winmm",
        sample_frames=({"axes": {"Roll": 0.0}},),
    )

    selected = PhysicalInputBackendSelector((winmm, raw)).select()
    assert selected.backend is winmm
    assert selected.choice.selected_backend_kind == "fake"

    unavailable_winmm = FakePhysicalInputBackend(
        backend_name="fake_winmm",
        backend_available=False,
        sample_frames=({"axes": {"Roll": 0.0}},),
    )
    fallback = PhysicalInputBackendSelector((raw, unavailable_winmm)).select()
    assert fallback.backend is raw
    assert fallback.choice.fallback_used is True
    assert "fake_winmm" in fallback.choice.fallback_reason


def test_hf_lrdc_6a_telemetry_reports_raw_input_identity_without_readiness_overclaim(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_input import WindowsRawInputBackend

    backend = WindowsRawInputBackend(
        provider=FakeRawInputProvider((_raw_report_bytes(), _raw_report_bytes(roll=0, hat=4))),
        clock=lambda: NOW,
    )
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            physical_input_backend=backend,
            enable_output_verification=False,
            enable_output_loop=False,
            simulate=False,
            clock=lambda: NOW,
        )
    )

    telemetry = service.run_once().to_dict()
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    fidelity = payload["physical_input_fidelity"]

    assert fidelity["backend_name"] == "windows_raw_input"
    assert fidelity["backend_kind"] == "windows_raw_input"
    assert fidelity["device_id"].startswith("raw:")
    assert isinstance(fidelity["sample_age_ms"], (int, float))
    assert fidelity["axes"]["Roll"]["raw_value"] in {0, 65535}
    assert telemetry["output_verified"] is False
    assert telemetry["runtime_frame"]["full_live_runtime_ready"] is False


def test_hf_lrdc_6a_missing_axes_are_reported_not_faked():
    from shared_core.runtime.hotas_input import WindowsRawInputBackend, build_physical_input_fidelity

    backend = WindowsRawInputBackend(
        provider=FakeRawInputProvider(({"axes": [{"raw_name": "X", "logical_name": "Roll", "raw_value": 1, "raw_min": 0, "raw_max": 10}]},)),
        clock=lambda: NOW,
    )
    device = backend.enumerate_devices()[0]
    backend.open_device(device.device_id)
    fidelity = build_physical_input_fidelity(backend.read_current_state(), backend=backend, sampled_at=NOW)

    assert fidelity.mapping_status == "missing_expected_channels"
    assert "Pitch" not in fidelity.axes
    assert any("Missing expected HOTAS axes" in warning for warning in fidelity.warnings)
