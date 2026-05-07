from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status():
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )

    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
        messages=("Physical input may be sampled read-only; output writes are not verified.",),
    )


def _hotas_device():
    from shared_core.runtime.hotas_input import build_physical_input_device_info

    return build_physical_input_device_info(
        device_id="hotas-one",
        display_name="Thrustmaster T.Flight Hotas One",
        manufacturer="Thrustmaster",
        vendor_id="044f",
        product_id="b68d",
        axis_count=3,
        button_count=2,
        hat_count=1,
        backend_name="fake_input",
    )


def _frame():
    return {
        "axes": (
            {
                "raw_name": "X",
                "logical_name": "Roll",
                "raw_value": 32767,
                "raw_min": -32768,
                "raw_max": 32767,
            },
            {
                "raw_name": "Y",
                "logical_name": "Pitch",
                "raw_value": 32768,
                "raw_min": 0,
                "raw_max": 65535,
                "center": 32767.5,
            },
            {
                "raw_name": "Z",
                "logical_name": "Throttle",
                "raw_value": 65535,
                "raw_min": 0,
                "raw_max": 65535,
                "one_sided": True,
            },
        ),
        "buttons": {1: True, 2: False},
        "hats": {1: "North"},
    }


def test_phase14b_axis_normalization_handles_supported_ranges_and_invalid_values():
    from shared_core.runtime.input_normalization import normalize_axis_value

    assert normalize_axis_value(-32768, raw_min=-32768, raw_max=32767).normalized_value == -1.0
    assert normalize_axis_value(32767, raw_min=-32768, raw_max=32767).normalized_value == 1.0
    assert normalize_axis_value(32767.5, raw_min=0, raw_max=65535, center=32767.5).normalized_value == pytest.approx(0.0)
    assert normalize_axis_value(0.25, already_normalized=True).normalized_value == 0.25
    assert normalize_axis_value(2.5, already_normalized=True).normalized_value == 1.0
    assert normalize_axis_value(-10, raw_min=0, raw_max=65535, one_sided=True).normalized_value == 0.0
    assert normalize_axis_value(65535, raw_min=0, raw_max=65535, one_sided=True).normalized_value == 1.0

    invalid = normalize_axis_value(None, raw_min=0, raw_max=65535)
    assert invalid.valid is False
    assert invalid.normalized_value == 0.0
    assert "missing" in invalid.warning.lower()


def test_phase14b_missing_backend_cannot_sample_and_does_not_crash():
    from shared_core.runtime.hotas_input import (
        MissingPhysicalInputBackend,
        PhysicalInputSampler,
        PhysicalInputSamplingStatus,
    )

    sampler = PhysicalInputSampler(MissingPhysicalInputBackend(), selected_device_id="hotas-one")
    open_status = sampler.open()
    snapshot = sampler.read_once()

    assert open_status.status == PhysicalInputSamplingStatus.UNAVAILABLE.value
    assert snapshot.sampling_status is PhysicalInputSamplingStatus.UNAVAILABLE
    assert snapshot.sampling_active is False
    assert snapshot.sample_source == "unavailable"
    assert snapshot.axes == ()
    assert snapshot.errors


def test_phase14b_fake_backend_returns_deterministic_axis_button_hat_snapshot():
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend, PhysicalInputSamplingStatus

    timestamp = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        backend_name="fake_input",
        sample_frames=(_frame(),),
        clock=lambda: timestamp,
    )

    assert backend.get_capabilities().physical_sampling_available is True
    assert backend.open_device("hotas-one").status == PhysicalInputSamplingStatus.ACTIVE.value
    snapshot = backend.read_current_state()

    assert snapshot.device_id == "hotas-one"
    assert snapshot.device_name == "Thrustmaster T.Flight Hotas One"
    assert snapshot.backend_name == "fake_input"
    assert snapshot.sampled_at == timestamp
    assert snapshot.sequence == 1
    assert snapshot.sample_source == "fake"
    assert snapshot.sampling_status is PhysicalInputSamplingStatus.ACTIVE
    assert snapshot.sampling_active is True
    assert snapshot.axis_count == 3
    assert snapshot.button_count == 2
    assert snapshot.hat_count == 1
    assert snapshot.axis_by_logical_name("Roll").normalized_value == 1.0
    assert snapshot.axis_by_logical_name("Pitch").normalized_value == pytest.approx(0.0, abs=0.0001)
    assert snapshot.axis_by_logical_name("Throttle").normalized_value == 1.0
    assert snapshot.buttons[0].pressed is True
    assert snapshot.buttons[1].pressed is False
    assert snapshot.hats[0].normalized_direction == "North"


def test_phase14b_fake_backend_can_emulate_disconnect_and_error():
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend, PhysicalInputSamplingStatus

    disconnected = FakePhysicalInputBackend(
        (_hotas_device(),),
        backend_name="fake_input",
        sample_frames=(_frame(),),
        disconnected=True,
    )
    disconnected.open_device("hotas-one")
    disconnected_snapshot = disconnected.read_current_state()
    assert disconnected_snapshot.sampling_status is PhysicalInputSamplingStatus.DEVICE_MISSING
    assert disconnected_snapshot.sampling_active is False
    assert "disconnected" in disconnected_snapshot.errors[0].lower()

    errored = FakePhysicalInputBackend(
        (_hotas_device(),),
        backend_name="fake_input",
        sample_frames=(_frame(),),
        sampling_error="fake read failure",
    )
    errored.open_device("hotas-one")
    error_snapshot = errored.read_current_state()
    assert error_snapshot.sampling_status is PhysicalInputSamplingStatus.ERROR
    assert error_snapshot.sample_source == "fake"
    assert "fake read failure" in error_snapshot.errors


def test_phase14b_sampler_reads_one_sample_and_blocks_missing_selection_safely():
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend, PhysicalInputSampler, PhysicalInputSamplingStatus

    backend = FakePhysicalInputBackend((_hotas_device(),), backend_name="fake_input", sample_frames=(_frame(),))
    sampler = PhysicalInputSampler(backend, selected_device_id="hotas-one")

    assert sampler.open().status == PhysicalInputSamplingStatus.ACTIVE.value
    snapshot = sampler.read_once()
    assert snapshot.sampling_status is PhysicalInputSamplingStatus.ACTIVE
    assert sampler.latest_snapshot is snapshot

    missing_sampler = PhysicalInputSampler(backend, selected_device_id="missing-device")
    missing_snapshot = missing_sampler.read_once()
    assert missing_snapshot.sampling_status is PhysicalInputSamplingStatus.DEVICE_MISSING
    assert missing_snapshot.sampling_active is False
    assert "not currently discovered" in missing_snapshot.errors[0]


def test_phase14b_diagnostics_surface_sampling_truth_without_output_authority(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.app_state import AppState
    from v3_app.services.perf_diagnostics import DiagnosticsCollector, build_diagnostics_snapshot, build_diagnostics_text

    _app()
    backend = FakePhysicalInputBackend((_hotas_device(),), backend_name="fake_input", sample_frames=(_frame(),))
    backend.open_device("hotas-one")
    latest = backend.read_current_state()

    page = PerfDiagnosticsPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        physical_input_backend=backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=latest,
    )
    labels = _label_text(page)

    assert "Input sampling\nActive (read-only)" in labels
    assert "Sample source\nfake" in labels
    assert "Last sample" in labels
    assert "Axis/button/hat counts\n3 axes / 2 buttons / 1 hat" in labels
    assert "Output verified\nfalse" in labels
    assert "Full Live Runtime Ready\nfalse" in labels
    assert "physical input sampling is read-only" in labels.lower()

    snapshot = build_diagnostics_snapshot(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        telemetry_status="Missing",
        telemetry_age_seconds=None,
        process_hint="Unavailable",
        bridge_lifecycle="Simulated",
        hotas_discovery_status="supported_device_detected",
        last_command_status="none",
        last_command_request_id="none",
        collector=DiagnosticsCollector(),
        physical_input=page._current_physical_input_diagnostics(),
    )
    copy_text = build_diagnostics_text(snapshot)
    assert "Input sampling: Active (read-only)" in copy_text
    assert "Sample source: fake" in copy_text
    assert "Axis/button/hat counts: 3 axes / 2 buttons / 1 hat" in copy_text
    assert "Output verified: false" in copy_text
    assert "Full Live Runtime Ready: false" in copy_text


def test_phase14b_help_docs_explain_read_only_sampling_and_phase15_output_boundary():
    from v3_app.services.help_docs import get_article

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    diagnostics = get_article("Performance / Diagnostics").body

    assert "Phase 14B adds read-only physical input sampling and normalization" in runtime_setup
    assert "physical input sampling does not imply vJoy output" in runtime_setup
    assert "vJoy writes remain Phase 15 or later" in runtime_setup
    assert "output_verified remains false" in runtime_setup
    assert "input sampling errors or disconnects fall back safely" in runtime_setup
    assert "Physical input sampling active" in indicators
    assert "read-only" in diagnostics


def test_phase14b_boundary_scans_find_no_output_or_capture_authority():
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "shared_core" / "runtime" / "hotas_input.py",
            PROJECT_ROOT / "shared_core" / "runtime" / "input_normalization.py",
            PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
            PROJECT_ROOT / "v3_app" / "services" / "perf_diagnostics.py",
        )
    )

    for forbidden in (
        "SetAxis",
        "UpdateVJD",
        "AcquireVJD",
        "pyvjoy",
        "VerifyOutput",
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "mss",
        "dxcam",
        "VideoWriter",
        "ffmpeg",
        "keyboard.add_hotkey",
    ):
        assert forbidden not in sources

    ui_text = (
        (PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py").read_text(encoding="utf-8")
        + (PROJECT_ROOT / "v3_app" / "services" / "perf_diagnostics.py").read_text(encoding="utf-8")
    )
    assert "physical input sampling is read-only" in ui_text.lower()
    assert "Full Live Runtime Ready: true" not in ui_text
    assert "Output verified: true" not in ui_text


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))
