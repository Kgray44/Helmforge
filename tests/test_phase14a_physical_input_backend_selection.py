from __future__ import annotations

import os
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
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
        messages=("Simulation mode remains available; output writes are not verified.",),
    )


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_phase14a_missing_backend_is_safe_and_reports_no_runtime_authority():
    from shared_core.runtime.hotas_input import (
        MissingPhysicalInputBackend,
        PhysicalInputSelectionStatus,
        build_physical_input_diagnostics,
        resolve_physical_input_selection,
    )

    backend = MissingPhysicalInputBackend()

    assert backend.enumerate_devices() == ()
    assert backend.get_capabilities().backend_available is False
    assert backend.get_capabilities().physical_sampling_available is False
    assert backend.get_backend_status().status == "backend_unavailable"

    selection = resolve_physical_input_selection(backend, selected_device_id=None)
    assert selection.selection_status is PhysicalInputSelectionStatus.BACKEND_UNAVAILABLE
    assert selection.selected_device_missing is False
    assert selection.no_device_selected is True

    diagnostics = build_physical_input_diagnostics(backend, selected_device_id=None)
    assert diagnostics.physical_input_backend == "Unavailable"
    assert diagnostics.supported_hotas == "Missing"
    assert diagnostics.selected_input_device == "None"
    assert diagnostics.input_sampling == "Not active"
    assert diagnostics.output_verified is False
    assert diagnostics.full_live_runtime_ready is False
    assert "no vJoy writes" in diagnostics.boundary_note


def test_phase14a_fake_backend_enumerates_supported_hotas_by_vid_pid_and_name():
    from shared_core.runtime.hotas_input import (
        FakePhysicalInputBackend,
        build_physical_input_device_info,
        is_supported_hotas_identity,
    )

    by_vid_pid = build_physical_input_device_info(
        device_id="usb\\vid_044f&pid_b68d",
        display_name="USB Input Device",
        manufacturer="Thrustmaster",
        vendor_id="044F",
        product_id="B68D",
        backend_name="fake",
        axis_count=5,
        button_count=14,
        hat_count=1,
    )
    by_name = build_physical_input_device_info(
        device_id="hid\\thrustmaster-tflight",
        display_name="Thrustmaster T.Flight Hotas One",
        manufacturer="Thrustmaster",
        backend_name="fake",
    )
    unsupported = build_physical_input_device_info(
        device_id="hid\\generic-stick",
        display_name="Generic USB Joystick",
        manufacturer="Generic",
        vendor_id="1234",
        product_id="abcd",
        backend_name="fake",
    )

    backend = FakePhysicalInputBackend((by_vid_pid, by_name, unsupported), backend_name="fake_input")
    devices = backend.enumerate_devices()

    assert is_supported_hotas_identity(vendor_id="044f", product_id="b68d", display_name="") is True
    assert is_supported_hotas_identity(vendor_id=None, product_id=None, display_name="T.Flight HOTAS One") is True
    assert devices[0].is_supported is True
    assert "VID 044f / PID b68d" in devices[0].support_reason
    assert devices[1].is_supported is True
    assert "name matched" in devices[1].support_reason
    assert devices[2].is_supported is False
    assert "not in Phase 14A supported list" in devices[2].support_reason
    assert backend.get_capabilities().backend_available is True
    assert backend.get_capabilities().physical_sampling_available is False


def test_phase14a_device_selection_statuses_are_truthful():
    from shared_core.runtime.hotas_input import (
        FakePhysicalInputBackend,
        PhysicalInputSelectionStatus,
        build_physical_input_device_info,
        resolve_physical_input_selection,
    )

    supported = build_physical_input_device_info(
        device_id="supported-hotas",
        display_name="Thrustmaster T-Flight HOTAS One",
        manufacturer="Thrustmaster",
        backend_name="fake",
    )
    unsupported = build_physical_input_device_info(
        device_id="unsupported-stick",
        display_name="Generic USB Joystick",
        manufacturer="Generic",
        backend_name="fake",
    )
    backend = FakePhysicalInputBackend((supported, unsupported), backend_name="fake_input")

    no_selection = resolve_physical_input_selection(backend, selected_device_id=None)
    assert no_selection.selection_status is PhysicalInputSelectionStatus.NO_DEVICE_SELECTED
    assert no_selection.no_device_selected is True

    selected = resolve_physical_input_selection(backend, selected_device_id="supported-hotas")
    assert selected.selection_status is PhysicalInputSelectionStatus.SELECTED_DEVICE_AVAILABLE
    assert selected.selected_device_available is True
    assert selected.selected_device_display_name == "Thrustmaster T-Flight HOTAS One"

    missing = resolve_physical_input_selection(backend, selected_device_id="missing-id")
    assert missing.selection_status is PhysicalInputSelectionStatus.SELECTED_DEVICE_MISSING
    assert missing.selected_device_missing is True

    unsupported_result = resolve_physical_input_selection(backend, selected_device_id="unsupported-stick")
    assert unsupported_result.selection_status is PhysicalInputSelectionStatus.UNSUPPORTED_DEVICE_SELECTED
    assert unsupported_result.unsupported_device_selected is True


def test_phase14a_perf_diagnostics_displays_physical_input_truth(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend, build_physical_input_device_info
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.app_state import AppState

    _app()
    device = build_physical_input_device_info(
        device_id="hotas-one",
        display_name="Thrustmaster T.Flight Hotas One",
        manufacturer="Thrustmaster",
        vendor_id="044f",
        product_id="b68d",
        backend_name="fake",
    )
    page = PerfDiagnosticsPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        physical_input_backend=FakePhysicalInputBackend((device,), backend_name="fake_input"),
        selected_physical_input_device_id="hotas-one",
    )
    text = _label_text(page)

    assert "Physical Input" in text
    assert "Physical input backend\nfake_input: Available" in text
    assert "Supported HOTAS\nDetected" in text
    assert "Selected input device\nThrustmaster T.Flight Hotas One" in text
    assert "Input sampling\nNot active" in text
    assert "Output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text
    assert "vJoy writes are not implemented in Phase 14A" in text


def test_phase14a_help_docs_explain_input_selection_without_output_authority():
    from v3_app.services.help_docs import get_article

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    diagnostics = get_article("Performance / Diagnostics").body

    assert "Phase 14A introduces physical input detection and device selection" in runtime_setup
    assert "simulation mode remains available" in runtime_setup
    assert "supported HOTAS detected does not mean vJoy output is active" in runtime_setup
    assert "Phase 15 is where virtual output and vJoy work begins" in runtime_setup
    assert "device selection does not write output" in runtime_setup
    assert "Full Live Runtime Ready remains false" in runtime_setup

    assert "Physical input backend" in indicators
    assert "Input sampling" in indicators
    assert "output_verified remains false" in indicators
    assert "Full Live Runtime Ready remains false" in diagnostics


def test_phase14a_boundary_scans_find_no_output_or_capture_authority():
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "shared_core" / "runtime" / "hotas_input.py",
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
