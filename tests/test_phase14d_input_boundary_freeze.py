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


def _sample(*, sampled_at: datetime | None = None, sampling_error: str | None = None):
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
        sampling_error=sampling_error,
    )
    backend.open_device("hotas-one")
    return backend, backend.read_current_state()


def _text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_phase14d_source_status_covers_backend_missing_selection_stale_and_error():
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend, MissingPhysicalInputBackend
    from v3_app.services.physical_input_ui import build_input_source_status

    now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)

    no_backend = build_input_source_status(backend=None, selected_device_id=None, latest_snapshot=None, now=now)
    assert no_backend.source_label == "Simulation"
    assert no_backend.source_status == "Simulation fallback"

    backend_unavailable = build_input_source_status(
        backend=MissingPhysicalInputBackend(),
        selected_device_id="hotas-one",
        latest_snapshot=None,
        now=now,
    )
    assert backend_unavailable.source_status == "Backend unavailable"
    assert "Simulation fallback" in backend_unavailable.fallback_behavior

    no_selection = build_input_source_status(
        backend=FakePhysicalInputBackend((_hotas_device(),), backend_name="fake_input"),
        selected_device_id=None,
        latest_snapshot=None,
        now=now,
    )
    assert no_selection.source_status == "No physical device selected"
    assert "Simulation fallback" in no_selection.fallback_behavior

    selected_missing = build_input_source_status(
        backend=FakePhysicalInputBackend((_hotas_device(),), backend_name="fake_input"),
        selected_device_id="missing-device",
        latest_snapshot=None,
        now=now,
    )
    assert selected_missing.source_status == "Selected physical device missing"
    assert selected_missing.source_label == "Physical unavailable"

    backend, snapshot = _sample(sampled_at=now)
    stale = build_input_source_status(
        backend=backend,
        selected_device_id="hotas-one",
        latest_snapshot=snapshot,
        now=now + timedelta(seconds=10),
        stale_after_seconds=2.0,
    )
    assert stale.source_status == "Physical sample stale"
    assert stale.sampling_active is False
    assert stale.is_fresh_physical_sample is False

    error_backend, error_snapshot = _sample(sampled_at=now, sampling_error="fake read failure")
    error = build_input_source_status(
        backend=error_backend,
        selected_device_id="hotas-one",
        latest_snapshot=error_snapshot,
        now=now,
    )
    assert error.source_status == "Physical sample error"
    assert error.sampling_active is False
    assert "fake read failure" in error.error_text


def test_phase14d_mapping_live_monitor_and_stack_keep_samples_read_only_and_fallback_safe(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.effective_response_stack_page import EffectiveResponseStackPage
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.pages.mapping_page import MappingPage
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.app_state import AppState

    _app()
    state = AppState.from_runtime_status(_runtime_status(), driver_detected=True)
    backend, fresh_snapshot = _sample()
    stale_now = fresh_snapshot.sampled_at + timedelta(seconds=20)

    mapping = MappingPage(
        state=state,
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        physical_input_backend=backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=fresh_snapshot,
    )
    mapping_text = _text(mapping)
    assert "Live Raw (Physical input sample)" in mapping.findChild(__import__("PySide6.QtWidgets").QtWidgets.QTableWidget, "axisRoutingTable").horizontalHeaderItem(5).text()
    assert "physical input samples are read-only" in mapping_text.lower()
    assert "Output verified\nfalse" in mapping_text
    assert "Full Live Runtime Ready\nfalse" in mapping_text

    live = LiveMonitorPage(
        state=state,
        runtime_status=_runtime_status(),
        physical_input_backend=backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=fresh_snapshot,
        physical_input_clock=lambda: fresh_snapshot.sampled_at,
    )
    live_text = _text(live)
    assert "Physical input sample: read-only" in live_text
    assert live.history.latest.raw_axes["Roll"] == 1.0
    assert "Output path remains unverified" in live_text
    assert "vJoy writes are not active" in live_text

    stale_live = LiveMonitorPage(
        state=state,
        runtime_status=_runtime_status(),
        physical_input_backend=backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=fresh_snapshot,
        physical_input_clock=lambda: stale_now,
        physical_sample_stale_after_seconds=2.0,
    )
    stale_text = _text(stale_live)
    assert "Sample status: Physical sample stale" in stale_text
    assert stale_live.history.latest.raw_axes["Roll"] != 1.0

    error_backend, error_snapshot = _sample(sampling_error="fake read failure")
    error_live = LiveMonitorPage(
        state=state,
        runtime_status=_runtime_status(),
        physical_input_backend=error_backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=error_snapshot,
        physical_input_clock=lambda: error_snapshot.sampled_at,
    )
    assert "Sample status: Physical sample error" in _text(error_live)

    stack = EffectiveResponseStackPage(
        state=state,
        runtime_status=_runtime_status(),
        physical_input_backend=backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=fresh_snapshot,
        physical_input_clock=lambda: fresh_snapshot.sampled_at,
    )
    stack_text = _text(stack)
    assert "diagnostic only" in stack_text.lower()
    assert "Output verified: false" in stack_text
    assert stack._current_raw_values["Roll"] == 1.0

    perf = PerfDiagnosticsPage(
        state=state,
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        physical_input_backend=backend,
        selected_physical_input_device_id="hotas-one",
        physical_input_snapshot=fresh_snapshot,
    )
    perf_text = _text(perf)
    copy_text = perf.prepare_copy_diagnostics()
    assert "Physical input read-only\ntrue" in perf_text
    assert "Simulation fallback" in copy_text
    assert "Output verified: false" in copy_text
    assert "Full Live Runtime Ready: false" in copy_text


def test_phase14d_docs_reports_and_phase15_readiness_are_explicit():
    from v3_app.services.help_docs import get_article

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    mapping = get_article("Mapping").body
    stack = get_article("Effective Response Stack").body
    diagnostics = get_article("Performance / Diagnostics").body
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "HelmForge" / "bridge-ui-architecture.md").read_text(encoding="utf-8")
    service_design = (PROJECT_ROOT / "docs" / "HelmForge" / "bridge-service-design.md").read_text(encoding="utf-8")
    report_path = PROJECT_ROOT / "docs" / "HelmForge" / "phase-14d-physical-input-boundary-freeze-report.md"

    assert "Phase 14 added physical input detection, selection, and read-only sampling" in runtime_setup
    assert "simulation mode remains available" in runtime_setup
    assert "physical input sampling is read-only" in runtime_setup
    assert "final output is not written to vJoy in Phase 14" in runtime_setup
    assert "virtual output is governed by Phase 15 backend, verification, and output-loop gates" in runtime_setup
    assert "output_verified remains false" in runtime_setup
    assert "Full Live Runtime Ready remains false" in runtime_setup
    assert "stale/error/unavailable physical input falls back safely" in runtime_setup
    assert "Physical input sample" in indicators
    assert "Read-only input sampling" in indicators
    assert "Mapping can label Live Raw values as physical input samples" in mapping
    assert "diagnostic only" in stack
    assert "simulation fallback state" in diagnostics

    for doc in (readme, architecture, service_design):
        assert "Phase 14 is now complete" in doc
        assert "Phase 15: vJoy / Virtual Output Integration" in doc
        assert "Full Live Runtime Ready must remain false until both input and output are verified" in doc

    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "Phase 15 Readiness" in report
    assert "Phase 15 may add virtual output/vJoy integration only with separate tests" in report
    assert "output verification must require real or mock write success" in report
    assert "simulation mode must remain available" in report


def test_phase14d_no_output_authority_or_capture_apis_were_introduced():
    source_paths = (
        PROJECT_ROOT / "shared_core" / "runtime" / "hotas_input.py",
        PROJECT_ROOT / "shared_core" / "runtime" / "input_normalization.py",
        PROJECT_ROOT / "v3_app" / "services" / "physical_input_ui.py",
        PROJECT_ROOT / "v3_app" / "pages" / "mapping_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "effective_response_stack_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths if path.exists())

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
        "vJoy output active",
        "writing to vJoy",
        "Output verified: true",
        "Full Live Runtime Ready true",
    ):
        assert forbidden not in sources
    assert "read-only" in sources.lower()
