from __future__ import annotations

import os
from dataclasses import dataclass
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
    )


def _text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


@dataclass
class _ProviderResult:
    success: bool
    status: str
    message: str


class _Provider:
    backend_name = "Injected real vJoy freeze provider"
    dependency_available = True
    driver_detected = True
    write_supported = True
    verification_supported = True

    def __init__(self, *, restore_success: bool = True) -> None:
        self.restore_success = restore_success
        self.write_calls = 0
        self.restore_calls = 0

    def enumerate_devices(self):
        from shared_core.runtime.vjoy_output import VirtualOutputDeviceInfo

        return (
            VirtualOutputDeviceInfo(
                device_id="1",
                display_name="vJoy Device 1",
                backend_name="Real vJoy",
                is_selected=True,
                axis_support=("X", "Y", "Z", "RX", "RY", "RZ"),
                button_count=20,
                hat_support="POV1",
                acquisition_status="available",
            ),
        )

    def acquire(self, device_id: str):
        _ = device_id
        return _ProviderResult(True, "acquired", "device acquired")

    def write_intent(self, device_id: str, intent):
        _ = device_id, intent
        self.write_calls += 1
        return _ProviderResult(True, "write_succeeded", "guarded write succeeded")

    def restore_neutral(self, device_id: str):
        _ = device_id
        self.restore_calls += 1
        if not self.restore_success:
            return _ProviderResult(False, "neutral_restore_failed", "neutral restore failed")
        return _ProviderResult(True, "neutral_restored", "neutral restored")

    def release(self, device_id: str) -> None:
        _ = device_id


def test_phase15d_backend_and_verification_truth_stays_distinct():
    from shared_core.runtime.vjoy_output import (
        FakeVirtualOutputBackend,
        RealVJoyOutputBackend,
        VirtualOutputIntent,
        VirtualOutputVerificationStatus,
        build_virtual_output_diagnostics,
    )

    detected_only = build_virtual_output_diagnostics()
    assert detected_only.output_verified is False
    assert detected_only.real_output_verified is False
    assert detected_only.virtual_output_backend_kind == "missing"
    assert detected_only.virtual_output_backend_status == "backend_missing"

    fake_backend = FakeVirtualOutputBackend()
    fake_verification = fake_backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    fake = build_virtual_output_diagnostics(backend=fake_backend, verification=fake_verification)
    assert fake.fake_output_verified is True
    assert fake.real_output_verified is False
    assert fake.output_verified is False
    assert fake.virtual_output_backend_kind == "fake"

    real_backend = RealVJoyOutputBackend(provider=_Provider())
    real_verification = real_backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    real = build_virtual_output_diagnostics(backend=real_backend, verification=real_verification)
    assert real_verification.status is VirtualOutputVerificationStatus.REAL_VERIFIED
    assert real.real_output_verified is True
    assert real.fake_output_verified is False
    assert real.output_verified is True
    assert real.virtual_output_backend_kind == "real_vjoy"

    failed_restore_backend = RealVJoyOutputBackend(provider=_Provider(restore_success=False))
    failed_restore = failed_restore_backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    assert failed_restore.status is VirtualOutputVerificationStatus.NEUTRAL_RESTORE_FAILED
    assert failed_restore.real_output_verified is False
    assert failed_restore.output_verified is False


def test_phase15d_output_loop_boundary_and_restore_failures_are_visible():
    from shared_core.runtime.vjoy_output import (
        FakeVirtualOutputBackend,
        VirtualOutputIntent,
        VirtualOutputWriteLoop,
        VirtualOutputWriteLoopState,
    )

    backend = FakeVirtualOutputBackend()
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    loop = VirtualOutputWriteLoop(backend=backend, verification=verification)

    assert loop.snapshot().state is VirtualOutputWriteLoopState.DISABLED
    assert loop.tick(VirtualOutputIntent.defaults(source="test")).write_count == 0

    unverified = VirtualOutputWriteLoop(backend=FakeVirtualOutputBackend())
    assert unverified.enable().state is VirtualOutputWriteLoopState.UNAVAILABLE_UNVERIFIED
    assert unverified.tick(VirtualOutputIntent.defaults(source="test")).write_count == 0

    failing_backend = FakeVirtualOutputBackend(fail_writes=True)
    failing_verification = failing_backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    failing_loop = VirtualOutputWriteLoop(backend=failing_backend, verification=failing_verification)
    failing_loop.enable()
    safety_stopped = failing_loop.tick(VirtualOutputIntent.defaults(source="test"))
    assert safety_stopped.state is VirtualOutputWriteLoopState.SAFETY_STOPPED
    assert safety_stopped.enabled is False
    assert safety_stopped.failure_count == 1

    restore_backend = FakeVirtualOutputBackend(fail_neutral_restore=True)
    restore_verification = restore_backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    restore_loop = VirtualOutputWriteLoop(backend=restore_backend, verification=restore_verification)
    restore_loop.enable()
    restore_loop.tick(VirtualOutputIntent.defaults(source="test"))
    restore_failure = restore_loop.disable()
    assert restore_failure.state is VirtualOutputWriteLoopState.ERROR_RESTORE_FAILED
    assert restore_failure.neutral_restore_status == "failed"
    assert "neutral" in restore_failure.last_error.casefold()


def test_phase15d_ui_diagnostics_and_docs_freeze_output_boundary(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend, VirtualOutputIntent, VirtualOutputWriteLoop
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.pages.mapping_page import MappingPage
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.app_state import AppState
    from v3_app.services.bridge_client import BridgeTelemetryClient
    from v3_app.services.help_docs import get_article

    _app()
    backend = FakeVirtualOutputBackend()
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    loop = VirtualOutputWriteLoop(backend=backend, verification=verification)
    state = AppState.from_runtime_status(_runtime_status(), driver_detected=True)

    mapping = MappingPage(
        state=state,
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        virtual_output_backend=backend,
        virtual_output_verification=verification,
        virtual_output_loop=loop,
    )
    live = LiveMonitorPage(
        state=state,
        runtime_status=_runtime_status(),
        virtual_output_backend=backend,
        virtual_output_verification=verification,
        virtual_output_loop=loop,
        telemetry_path=tmp_path / "missing-bridge-telemetry.json",
    )
    perf = PerfDiagnosticsPage(
        state=state,
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        virtual_output_backend=backend,
        virtual_output_verification=verification,
        virtual_output_loop=loop,
        telemetry_client=BridgeTelemetryClient(telemetry_path=tmp_path / "missing-perf-telemetry.json"),
    )

    mapping_text = _text(mapping)
    live_text = _text(live)
    perf_text = _text(perf)
    copy_text = perf.prepare_copy_diagnostics()

    assert "Virtual output backend kind\nfake" in perf_text
    assert "Virtual output backend status\nfake_backend_available" in perf_text
    assert "Output loop\n" in perf_text
    assert "Real output verified\nfalse" in perf_text
    assert "Fake output verified\ntrue" in perf_text
    assert "Full Live Runtime Ready\nfalse" in perf_text
    assert "Virtual output backend kind: fake" in copy_text
    assert "Virtual output backend status: fake_backend_available" in copy_text
    assert "Full Live Runtime Ready: false" in copy_text

    for text in (mapping_text, live_text, perf_text):
        assert "Full Live Runtime Ready\ntrue" not in text
        assert "runtime ready: true" not in text.casefold()
        assert "output active" not in text.casefold()

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    diagnostics = get_article("Performance / Diagnostics").body
    assert "Phase 15 is now complete" in runtime_setup
    assert "Phase 16: Runtime End-to-End Live Mode" in runtime_setup
    assert "output intent is not output write proof" in runtime_setup
    assert "fake/mock output is not real vJoy output" in runtime_setup
    assert "output loop must be explicitly enabled and safety-gated" in runtime_setup
    assert "Full Live Runtime Ready may remain Phase 16" in runtime_setup
    assert "Virtual output backend kind" in indicators
    assert "Output loop state" in diagnostics


def test_phase15d_report_and_source_boundary():
    report = (PROJECT_ROOT / "docs" / "HelmForge" / "phase-15d-output-boundary-freeze-report.md").read_text(encoding="utf-8")
    assert "Phase 15 is now complete" in report
    assert "Next prompt-book phase is Phase 16: Runtime End-to-End Live Mode" in report
    assert "simulation mode must remain available" in report
    assert "Full Live Runtime Ready must require both input and output proof" in report

    source_paths = (
        PROJECT_ROOT / "shared_core" / "runtime" / "vjoy_output.py",
        PROJECT_ROOT / "v3_app" / "pages" / "mapping_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
        PROJECT_ROOT / "v3_app" / "services" / "perf_diagnostics.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths if path.exists())
    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Enable Live Output",
        "Install Service",
        "Enable Auto Start",
        "keyboard.add_hotkey",
        "mss",
        "dxcam",
        "VideoWriter",
        "ffmpeg",
    ):
        assert forbidden not in sources
