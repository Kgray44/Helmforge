from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


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
        messages=("Physical input sampling is read-only; output writes are not verified.",),
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


def _sample(*, sampled_at: datetime | None = None):
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend

    timestamp = sampled_at or datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        backend_name="fake_input",
        sample_frames=(
            {
                "axes": (
                    {"raw_name": "X", "logical_name": "Roll", "raw_value": 32767, "raw_min": -32768, "raw_max": 32767},
                    {"raw_name": "Y", "logical_name": "Pitch", "raw_value": -32768, "raw_min": -32768, "raw_max": 32767},
                    {"raw_name": "Z", "logical_name": "Throttle", "raw_value": 65535, "raw_min": 0, "raw_max": 65535, "one_sided": True},
                ),
                "buttons": {1: True, 2: False},
                "hats": {1: "North"},
            },
        ),
        clock=lambda: timestamp,
    )
    backend.open_device("hotas-one")
    return backend, backend.read_current_state()


def _text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_phase14c_input_source_model_distinguishes_simulation_active_stale_and_error():
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend
    from v3_app.services.physical_input_ui import build_input_source_status

    now = datetime(2026, 5, 7, 12, 0, 5, tzinfo=timezone.utc)
    backend, snapshot = _sample(sampled_at=now)

    no_sample = build_input_source_status(backend=None, selected_device_id=None, latest_snapshot=None, now=now)
    assert no_sample.source_label == "Simulation"
    assert no_sample.source_status == "Simulation fallback"
    assert no_sample.fallback_behavior == "Using simulation/fallback input values."

    active = build_input_source_status(backend=backend, selected_device_id="hotas-one", latest_snapshot=snapshot, now=now)
    assert active.source_label == "Physical input"
    assert active.source_status == "Physical input sampling active"
    assert active.sampling_active is True
    assert active.sample_age_text == "0.0s"
    assert active.is_fresh_physical_sample is True

    stale = build_input_source_status(
        backend=backend,
        selected_device_id="hotas-one",
        latest_snapshot=snapshot,
        now=now + timedelta(seconds=10),
        stale_after_seconds=2.0,
    )
    assert stale.source_status == "Physical sample stale"
    assert stale.sampling_active is False
    assert stale.is_stale is True
    assert "falling back" in stale.fallback_behavior

    error_backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        backend_name="fake_input",
        sample_frames=({"axes": (), "buttons": {}, "hats": {}},),
        sampling_error="fake read failure",
    )
    error_backend.open_device("hotas-one")
    error_status = build_input_source_status(
        backend=error_backend,
        selected_device_id="hotas-one",
        latest_snapshot=error_backend.read_current_state(),
        now=now,
    )
    assert error_status.source_status == "Physical sample error"
    assert "fake read failure" in error_status.error_text


def test_phase14c_mapping_page_displays_physical_sample_truth_and_values(tmp_path):
    from PySide6.QtWidgets import QTableWidget
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.mapping_page import MappingPage
    from v3_app.services.app_state import AppState

    _app()
    backend, snapshot = _sample()
    page = MappingPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        physical_input_backend=backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=snapshot,
    )
    text = _text(page)
    axis_table = page.findChild(QTableWidget, "axisRoutingTable")

    assert "Physical input backend\nfake_input: Available" in text
    assert "Selected input device\nThrustmaster T.Flight Hotas One" in text
    assert "Input source\nPhysical input" in text
    assert "Input sampling\nPhysical input sampling active" in text
    assert "Sample source\nfake" in text
    assert "Axis count\n3" in text
    assert "Button count\n2" in text
    assert "Hat count\n1" in text
    assert "Output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text
    assert "physical input samples are read-only" in text.lower()
    assert axis_table.item(0, 5).text() == "+1.00"
    assert axis_table.horizontalHeaderItem(5).text() == "Live Raw (Physical input sample)"
    assert "vJoy output active" not in text


def test_phase14c_mapping_page_falls_back_when_physical_input_unavailable():
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.mapping_page import MappingPage
    from v3_app.services.app_state import AppState

    _app()
    page = MappingPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
    )
    text = _text(page)

    assert "Input source\nSimulation" in text
    assert "Input sampling\nSimulation fallback" in text
    assert "Output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text


def test_phase14c_live_monitor_displays_physical_input_sample_read_only(tmp_path):
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    backend, snapshot = _sample()
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        runtime_status=_runtime_status(),
        physical_input_backend=backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=snapshot,
        physical_input_clock=lambda: snapshot.sampled_at,
        telemetry_path=tmp_path / "missing-bridge-telemetry.json",
    )
    text = _text(page)

    assert "Input source: Physical input" in text
    assert "Sample status: Physical input sampling active" in text
    assert "Physical input sample: read-only" in text
    assert "Output path remains unverified" in text
    assert "vJoy writes are not active" in text
    assert "Output writes verified: false" in text
    assert "Full Live Runtime Ready false" in text
    assert page.history.latest.raw_axes["Roll"] == 1.0
    assert page.findChild(type(page._hotas_buttons["B1"]), "hotasButton_B1").property("chipTone") == "success"
    assert page.hotas_hat_chip.text() == "HOTAS Hat: North"
    assert "vJoy output active" not in text


def test_phase14c_live_monitor_uses_simulation_or_stale_fallback():
    from datetime import timedelta
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    simulation_page = LiveMonitorPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        runtime_status=_runtime_status(),
    )
    assert "Input source: Simulation" in _text(simulation_page)

    backend, snapshot = _sample()
    stale_page = LiveMonitorPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        runtime_status=_runtime_status(),
        physical_input_backend=backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=snapshot,
        physical_input_clock=lambda: snapshot.sampled_at + timedelta(seconds=20),
        physical_sample_stale_after_seconds=2.0,
    )
    stale_text = _text(stale_page)
    assert "Sample status: Physical sample stale" in stale_text
    assert "stale; falling back" in stale_text


def test_phase14c_effective_response_stack_uses_physical_sample_or_reports_fallback():
    from v3_app.pages.effective_response_stack_page import EffectiveResponseStackPage
    from v3_app.services.app_state import AppState

    _app()
    backend, snapshot = _sample()
    page = EffectiveResponseStackPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        runtime_status=_runtime_status(),
        physical_input_backend=backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=snapshot,
        physical_input_clock=lambda: snapshot.sampled_at,
    )
    text = _text(page)

    assert "Input source: Physical input" in text
    assert "physical input sample" in text.lower()
    assert "diagnostic only" in text.lower()
    assert "Output verified: false" in text
    assert page._current_raw_values["Roll"] == 1.0

    fallback_page = EffectiveResponseStackPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        runtime_status=_runtime_status(),
    )
    assert "Input source: Simulation" in _text(fallback_page)


def test_phase14c_perf_diagnostics_and_copy_text_include_sampling_truth(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.app_state import AppState

    _app()
    backend, snapshot = _sample()
    page = PerfDiagnosticsPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        physical_input_backend=backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=snapshot,
    )
    text = _text(page)
    copy_text = page.prepare_copy_diagnostics()

    assert "Input source" in text
    assert "Physical input backend\nfake_input: Available" in text
    assert "Input sampling\nActive (read-only)" in text
    assert "Physical input read-only\ntrue" in text
    assert "Axis/button/hat counts\n3 axes / 2 buttons / 1 hat" in text
    assert "Input source: Physical input" in copy_text
    assert "Physical input read-only: true" in copy_text
    assert "Output verified: false" in copy_text
    assert "Full Live Runtime Ready: false" in copy_text


def test_phase14c_help_docs_and_boundary_wording_are_safe():
    from v3_app.services.help_docs import get_article

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    mapping = get_article("Mapping").body
    stack = get_article("Effective Response Stack").body

    assert "physical samples may appear in Mapping and Live Monitor" in runtime_setup
    assert "final output is not written to vJoy in Phase 14" in runtime_setup
    assert "sample stale or error states fall back safely" in runtime_setup
    assert "Physical input read-only" in indicators
    assert "Mapping can label Live Raw values as physical input samples" in mapping
    assert "diagnostic only" in stack

    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "pages" / "mapping_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "effective_response_stack_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
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
        "Full Live Runtime Ready true",
        "Output verified: true",
    ):
        assert forbidden not in sources
    assert "read-only" in sources.lower()
