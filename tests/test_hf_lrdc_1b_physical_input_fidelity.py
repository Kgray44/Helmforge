from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


NOW = datetime(2026, 5, 9, 12, 0, 0, tzinfo=timezone.utc)


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
        backend_name="fake_hid_candidate",
    )


def _frame(value: int = 32768):
    return {
        "axes": (
            {"raw_name": "X", "logical_name": "Roll", "raw_value": value, "raw_min": 0, "raw_max": 65535},
            {"raw_name": "Y", "logical_name": "Pitch", "raw_value": 32768, "raw_min": 0, "raw_max": 65535},
            {"raw_name": "Z", "logical_name": "Throttle", "raw_value": 60000, "raw_min": 0, "raw_max": 65535, "one_sided": True},
            {"raw_name": "R", "logical_name": "Yaw", "raw_value": 30000, "raw_min": 0, "raw_max": 65535},
            {"raw_name": "U", "logical_name": "Aux 1", "raw_value": 10000, "raw_min": 0, "raw_max": 65535},
            {"raw_name": "V", "logical_name": "Aux 2", "raw_value": 50000, "raw_min": 0, "raw_max": 65535},
        ),
        "buttons": {index: index in {1, 15} for index in range(1, 16)},
        "hats": {1: "North"},
    }


def test_hf_lrdc_1b_snapshot_exposes_fidelity_axis_mapping_and_resolution():
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend, PhysicalInputSampler, build_physical_input_fidelity

    backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        backend_name="fake_hid_candidate",
        sample_frames=(_frame(),),
        clock=lambda: NOW,
        sample_source="physical",
    )
    sampler = PhysicalInputSampler(backend, selected_device_id="hotas-one")
    sampler.open()
    snapshot = sampler.read_once()

    fidelity = build_physical_input_fidelity(
        snapshot,
        backend=backend,
        sampled_at=NOW + timedelta(milliseconds=4),
        read_duration_ms=0.2,
    )

    assert fidelity.backend_name == "fake_hid_candidate"
    assert fidelity.device_name == "Thrustmaster T.Flight HOTAS One"
    assert fidelity.sample_age_ms == 4
    assert fidelity.read_duration_ms == 0.2
    assert fidelity.axis_count == 6
    assert fidelity.button_count == 15
    assert fidelity.hat_count == 1
    assert fidelity.mapping_status == "ok"
    roll = fidelity.axes["Roll"]
    assert roll.raw_name == "X"
    assert roll.raw_value == 32768
    assert roll.raw_min == 0
    assert roll.raw_max == 65535
    assert roll.resolution_hint == "16-bit-ish"
    assert isinstance(roll.normalized_value, float)


def test_hf_lrdc_1b_fidelity_reports_missing_logical_channels_without_fake_values():
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend, PhysicalInputSampler, build_physical_input_fidelity

    backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        sample_frames=({"axes": ({"raw_name": "X", "logical_name": "Roll", "raw_value": 1, "raw_min": 0, "raw_max": 10},)},),
        clock=lambda: NOW,
        sample_source="physical",
    )
    sampler = PhysicalInputSampler(backend, selected_device_id="hotas-one")
    sampler.open()

    fidelity = build_physical_input_fidelity(sampler.read_once(), backend=backend, sampled_at=NOW)

    assert fidelity.mapping_status == "missing_expected_channels"
    assert "Pitch" not in fidelity.axes
    assert any("Missing expected HOTAS axes" in warning for warning in fidelity.warnings)


def test_hf_lrdc_1b_backend_selector_prefers_guarded_candidate_then_falls_back():
    from shared_core.runtime.hotas_input import (
        FakePhysicalInputBackend,
        MissingPhysicalInputBackend,
        PhysicalInputBackendSelector,
        WindowsRawInputCandidateBackend,
    )

    high = WindowsRawInputCandidateBackend(provider=FakePhysicalInputBackend((_hotas_device(),), sample_frames=(_frame(),)))
    winmm = FakePhysicalInputBackend((_hotas_device(),), backend_name="fake_winmm", sample_frames=(_frame(),))
    selected = PhysicalInputBackendSelector((high, winmm)).select()
    assert selected.backend is high
    assert selected.choice.selected_backend_kind == "windows_raw_input_candidate"
    assert selected.choice.fallback_used is False

    unavailable_high = WindowsRawInputCandidateBackend(provider=None)
    fallback = PhysicalInputBackendSelector((unavailable_high, winmm)).select()
    assert fallback.backend is winmm
    assert fallback.choice.fallback_used is True
    assert fallback.choice.fallback_reason

    missing = PhysicalInputBackendSelector((unavailable_high, MissingPhysicalInputBackend())).select()
    assert missing.choice.selected_backend_kind == "missing"
    assert missing.choice.fallback_used is True


def test_hf_lrdc_1b_bridge_telemetry_includes_fidelity_without_runtime_overclaim(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus

    backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        backend_name="fake_hid_candidate",
        sample_frames=(_frame(),),
        clock=lambda: NOW,
        sample_source="physical",
    )
    service = BridgeService(
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

    telemetry = service.run_once().to_dict()
    payload = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    parsed = BridgeTelemetryClient(telemetry_path=tmp_path / "telemetry.json", clock=lambda: NOW).read()

    assert "physical_input_fidelity" in payload
    assert payload["physical_input_fidelity"]["backend_name"] == "fake_hid_candidate"
    assert payload["physical_input_fidelity"]["axes"]["Roll"]["raw_value"] == 32768
    assert payload["physical_input_backend_choice"]["selected_backend_name"] == "fake_hid_candidate"
    assert parsed.status is BridgeTelemetryStatus.CONNECTED
    assert parsed.telemetry is not None
    assert parsed.telemetry.physical_input_fidelity is not None
    assert telemetry["output_verified"] is False
    assert telemetry["runtime_frame"]["full_live_runtime_ready"] is False


def test_hf_lrdc_1b_raw_input_candidate_is_safe_when_provider_missing():
    from shared_core.runtime.hotas_input import WindowsRawInputCandidateBackend

    backend = WindowsRawInputCandidateBackend(provider=None)

    assert backend.enumerate_devices() == ()
    assert backend.get_capabilities().backend_available is False
    assert backend.get_capabilities().requires_message_loop is True
    assert backend.read_current_state().sampling_active is False
