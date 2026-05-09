from __future__ import annotations

import os
from datetime import datetime, timezone
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
        messages=("vJoy detected, output writes unverified.",),
    )


def _text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_phase15a_missing_backend_is_safe_and_never_verifies_output():
    from shared_core.runtime.vjoy_output import (
        MissingVirtualOutputBackend,
        VirtualOutputIntent,
        VirtualOutputVerificationStatus,
    )

    backend = MissingVirtualOutputBackend()
    intent = VirtualOutputIntent.defaults(source="test")
    capabilities = backend.get_capabilities()
    status = backend.get_status()
    write_result = backend.write_output_intent(intent)
    verification = backend.verify_output_write(intent)

    assert capabilities.backend_available is False
    assert capabilities.real_output_writes_available is False
    assert status.status == "backend_missing"
    assert backend.enumerate_output_devices() == ()
    assert write_result.success is False
    assert write_result.status == "backend_missing"
    assert verification.status is VirtualOutputVerificationStatus.BACKEND_MISSING
    assert verification.output_verified is False
    assert verification.real_output_verified is False
    assert verification.fake_output_verified is False


def test_phase15a_fake_backend_records_intent_and_only_fake_verifies():
    from shared_core.runtime.vjoy_output import (
        FakeVirtualOutputBackend,
        VirtualAxisOutput,
        VirtualButtonOutput,
        VirtualHatOutput,
        VirtualOutputIntent,
        VirtualOutputVerificationStatus,
    )

    timestamp = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    intent = VirtualOutputIntent(
        timestamp=timestamp,
        source="test",
        axes=(VirtualAxisOutput("X", 0.25), VirtualAxisOutput("Y", -0.5)),
        buttons=(VirtualButtonOutput("Out1", True),),
        hats=(VirtualHatOutput("POV1", "North"),),
        output_enabled=True,
        write_requested=True,
    )
    backend = FakeVirtualOutputBackend()
    write_result = backend.write_output_intent(intent)
    verification = backend.verify_output_write(intent)

    assert write_result.success is True
    assert write_result.status == "fake_write_recorded"
    assert backend.last_written_intent == intent
    assert verification.status is VirtualOutputVerificationStatus.FAKE_VERIFIED
    assert verification.output_verified is False
    assert verification.fake_output_verified is True
    assert verification.real_output_verified is False
    assert "Not real vJoy" in verification.message


def test_phase15a_output_intent_round_trip_and_recovered_axis_mapping():
    from shared_core.runtime.vjoy_output import (
        RECOVERED_AXIS_OUTPUT_ROUTES,
        VirtualOutputIntent,
        build_recovered_virtual_output_intent,
    )

    raw_axes = {
        "Roll": 0.1,
        "Pitch": -0.2,
        "Throttle": 0.3,
        "Yaw": -0.4,
        "Aux 1": 0.5,
        "Aux 2": -0.6,
    }
    intent = build_recovered_virtual_output_intent(
        raw_axes,
        source="shared_core_pipeline",
        timestamp=datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc),
    )
    round_trip = VirtualOutputIntent.from_dict(intent.to_dict())

    assert RECOVERED_AXIS_OUTPUT_ROUTES == {
        "Roll": "X",
        "Pitch": "Y",
        "Throttle": "Z",
        "Yaw": "RX",
        "Aux 1": "RY",
        "Aux 2": "RZ",
    }
    assert round_trip == intent
    assert intent.axis_value("X") == 0.1
    assert intent.axis_value("Y") == -0.2
    assert intent.axis_value("Z") == 0.3
    assert intent.axis_value("RX") == -0.4
    assert intent.axis_value("RY") == 0.5
    assert intent.axis_value("RZ") == -0.6
    assert intent.write_requested is False
    assert "output intent is not output write proof" in " ".join(intent.warnings)


def test_phase15a_perf_diagnostics_and_help_docs_preserve_output_truth(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend, VirtualOutputIntent
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.app_state import AppState
    from v3_app.services.help_docs import get_article

    _app()
    missing_page = PerfDiagnosticsPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )
    missing_text = _text(missing_page)
    missing_copy = missing_page.prepare_copy_diagnostics()

    assert "Virtual output backend\nMissing virtual output backend" in missing_text
    assert "Output write status\nNot active" in missing_text
    assert "Output verification status\nnot_attempted" in missing_text
    assert "Real output verified\nfalse" in missing_text
    assert "Fake output verified\nfalse" in missing_text
    assert "Output verified\nfalse" in missing_text
    assert "Full Live Runtime Ready\nfalse" in missing_text
    assert "Virtual output backend: Missing virtual output backend" in missing_copy
    assert "Real output verified: false" in missing_copy

    fake_backend = FakeVirtualOutputBackend()
    fake_verification = fake_backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    fake_page = PerfDiagnosticsPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "fake_config.json",
        virtual_output_backend=fake_backend,
        virtual_output_verification=fake_verification,
    )
    fake_text = _text(fake_page)
    assert "Virtual output backend\nFake output backend" in fake_text
    assert "Output verification status\nfake_verified" in fake_text
    assert "Output verification source\nfake/mock - Not real vJoy" in fake_text
    assert "Fake output verified\ntrue" in fake_text
    assert "Real output verified\nfalse" in fake_text
    assert "Output verified\nfalse" in fake_text
    assert "Full Live Runtime Ready\nfalse" in fake_text

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    diagnostics = get_article("Performance / Diagnostics").body
    assert "Phase 15A adds output backend contracts" in runtime_setup
    assert "output intent is not a write" in runtime_setup
    assert "fake/mock verification is not real vJoy verification" in runtime_setup
    assert "vJoy detected does not equal output verified" in runtime_setup
    assert "real output writes are not part of Phase 15A" in runtime_setup
    assert "Full Live Runtime Ready remains false" in runtime_setup
    assert "Virtual output backend" in indicators
    assert "Fake output verified" in diagnostics


def test_phase15a_real_output_authority_stays_inside_shared_provider():
    source_paths = (
        PROJECT_ROOT / "v3_app" / "pages" / "mapping_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
        PROJECT_ROOT / "v3_app" / "services" / "perf_diagnostics.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths if path.exists())
    vjoy_provider = (PROJECT_ROOT / "shared_core" / "runtime" / "vjoy_output.py").read_text(encoding="utf-8")

    for required in ("SetAxis", "SetBtn", "AcquireVJD"):
        assert required in vjoy_provider

    for forbidden in (
        "SetAxis",
        "UpdateVJD",
        "AcquireVJD",
        "VerifyOutput",
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "mss",
        "dxcam",
        "VideoWriter",
        "ffmpeg",
        "keyboard.add_hotkey",
        "real output verified: true",
        "Output verified: true",
        "Full Live Runtime Ready true",
        "writing to vJoy",
        "vJoy output active",
    ):
        assert forbidden not in sources
    assert "pyvjoy" not in sources.lower()
