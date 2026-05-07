from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@dataclass
class _ProviderResult:
    success: bool
    status: str
    message: str


class _InjectedVJoyProvider:
    backend_name = "Injected real vJoy provider"

    def __init__(
        self,
        *,
        dependency_available: bool = True,
        driver_detected: bool = True,
        devices=(),
        acquire_result: _ProviderResult | None = None,
        write_result: _ProviderResult | None = None,
        restore_result: _ProviderResult | None = None,
    ) -> None:
        self.dependency_available = dependency_available
        self.driver_detected = driver_detected
        self.devices = tuple(devices)
        self.acquire_result = acquire_result or _ProviderResult(True, "acquired", "device acquired")
        self.write_result = write_result or _ProviderResult(True, "write_succeeded", "guarded write succeeded")
        self.restore_result = restore_result or _ProviderResult(True, "neutral_restored", "neutral restored")
        self.acquire_calls = 0
        self.write_calls = 0
        self.restore_calls = 0
        self.release_calls = 0

    def enumerate_devices(self):
        return self.devices

    def acquire(self, device_id: str):
        _ = device_id
        self.acquire_calls += 1
        return self.acquire_result

    def write_intent(self, device_id: str, intent):
        _ = device_id, intent
        self.write_calls += 1
        return self.write_result

    def restore_neutral(self, device_id: str):
        _ = device_id
        self.restore_calls += 1
        return self.restore_result

    def release(self, device_id: str) -> None:
        _ = device_id
        self.release_calls += 1


def _device(device_id: str = "1"):
    from shared_core.runtime.vjoy_output import VirtualOutputDeviceInfo

    return VirtualOutputDeviceInfo(
        device_id=device_id,
        display_name=f"vJoy Device {device_id}",
        backend_name="Real vJoy",
        is_selected=True,
        axis_support=("X", "Y", "Z", "RX", "RY", "RZ"),
        button_count=20,
        hat_support="POV1",
        acquisition_status="available",
    )


def test_phase15b_real_backend_imports_without_dependency_and_reports_missing():
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend, VirtualOutputIntent, VirtualOutputVerificationStatus

    provider = _InjectedVJoyProvider(dependency_available=False, driver_detected=False)
    backend = RealVJoyOutputBackend(provider=provider)
    capabilities = backend.get_capabilities()
    status = backend.get_status()
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))

    assert capabilities.backend_name == "Real vJoy"
    assert capabilities.dependency_available is False
    assert capabilities.backend_available is False
    assert capabilities.real_output_writes_available is False
    assert status.status == "dependency_missing"
    assert verification.status is VirtualOutputVerificationStatus.DEPENDENCY_MISSING
    assert verification.output_verified is False
    assert verification.real_output_verified is False
    assert provider.acquire_calls == 0
    assert provider.write_calls == 0


def test_phase15b_real_backend_reports_device_missing_and_not_attempted_by_default():
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend, build_virtual_output_diagnostics

    provider = _InjectedVJoyProvider(devices=())
    backend = RealVJoyOutputBackend(provider=provider)
    diagnostics = build_virtual_output_diagnostics(backend=backend)

    assert backend.get_status().status == "device_missing"
    assert backend.enumerate_output_devices() == ()
    assert diagnostics.virtual_output_backend == "Real vJoy"
    assert diagnostics.vjoy_dependency_status == "Available"
    assert diagnostics.vjoy_device_status == "Missing"
    assert diagnostics.output_verification_status == "not_attempted"
    assert diagnostics.real_output_verified is False
    assert diagnostics.output_verified is False
    assert provider.acquire_calls == 0
    assert provider.write_calls == 0


def test_phase15b_guarded_verification_handles_busy_acquisition_failure():
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend, VirtualOutputIntent, VirtualOutputVerificationStatus

    provider = _InjectedVJoyProvider(
        devices=(_device(),),
        acquire_result=_ProviderResult(False, "device_busy", "device is busy"),
    )
    backend = RealVJoyOutputBackend(provider=provider)
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))

    assert verification.status is VirtualOutputVerificationStatus.DEVICE_BUSY
    assert verification.real_output_verified is False
    assert verification.output_verified is False
    assert provider.acquire_calls == 1
    assert provider.write_calls == 0
    assert provider.restore_calls == 0
    assert provider.release_calls == 1


def test_phase15b_guarded_verification_real_verified_only_after_write_and_neutral_restore():
    from shared_core.runtime.vjoy_output import (
        RealVJoyOutputBackend,
        VirtualAxisOutput,
        VirtualOutputIntent,
        VirtualOutputVerificationStatus,
    )

    provider = _InjectedVJoyProvider(devices=(_device(),))
    backend = RealVJoyOutputBackend(provider=provider)
    unsafe_intent = VirtualOutputIntent(
        timestamp=VirtualOutputIntent.defaults(source="test").timestamp,
        source="user_profile",
        axes=(VirtualAxisOutput("X", 1.0), VirtualAxisOutput("Y", -1.0)),
        output_enabled=True,
        write_requested=True,
    )
    verification = backend.verify_output_write(unsafe_intent)

    assert verification.status is VirtualOutputVerificationStatus.REAL_VERIFIED
    assert verification.real_output_verified is True
    assert verification.fake_output_verified is False
    assert verification.output_verified is True
    assert verification.source == "real vJoy guarded write"
    assert "bounded verification write" in verification.message
    assert provider.acquire_calls == 1
    assert provider.write_calls == 1
    assert provider.restore_calls == 1
    assert provider.release_calls == 1


def test_phase15b_neutral_restore_failure_keeps_real_output_unverified():
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend, VirtualOutputIntent, VirtualOutputVerificationStatus

    provider = _InjectedVJoyProvider(
        devices=(_device(),),
        restore_result=_ProviderResult(False, "neutral_restore_failed", "neutral restore failed"),
    )
    backend = RealVJoyOutputBackend(provider=provider)
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))

    assert verification.status is VirtualOutputVerificationStatus.NEUTRAL_RESTORE_FAILED
    assert verification.real_output_verified is False
    assert verification.output_verified is False
    assert "neutral restore failed" in verification.message


def test_phase15b_perf_diagnostics_and_help_docs_show_real_verification_truth(tmp_path):
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )
    from shared_core.models.workspace import create_default_workspace
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend, VirtualOutputIntent
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.app_state import AppState
    from v3_app.services.help_docs import get_article

    _app()
    runtime_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )
    backend = RealVJoyOutputBackend(provider=_InjectedVJoyProvider(devices=(_device(),)))
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    page = PerfDiagnosticsPage(
        state=AppState.from_runtime_status(runtime_status, driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=runtime_status,
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        virtual_output_backend=backend,
        virtual_output_verification=verification,
    )
    text = "\n".join(label.text() for label in page.findChildren(__import__("PySide6.QtWidgets").QtWidgets.QLabel))
    copy_text = page.prepare_copy_diagnostics()

    assert "Virtual output backend\nReal vJoy" in text
    assert "vJoy dependency\nAvailable" in text
    assert "vJoy device\nDetected" in text
    assert "Output verification status\nreal_verified" in text
    assert "Output verification source\nreal vJoy guarded write" in text
    assert "Real output verified\ntrue" in text
    assert "Output verified\ntrue" in text
    assert "Full Live Runtime Ready\nfalse" in text
    assert "Last verification timestamp:" in copy_text
    assert "Real output verified: true" in copy_text
    assert "Output verified: true" in copy_text
    assert "Full Live Runtime Ready: false" in copy_text

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    diagnostics = get_article("Performance / Diagnostics").body
    assert "vJoy detection is not output verification" in runtime_setup
    assert "real output verification requires guarded write success" in runtime_setup
    assert "continuous output is not active in Phase 15B" in runtime_setup
    assert "neutral restore is attempted" in runtime_setup
    assert "vJoy dependency" in indicators
    assert "Last verification timestamp" in diagnostics


def test_phase15b_no_continuous_loop_or_runtime_authority_was_added():
    source_paths = (
        PROJECT_ROOT / "shared_core" / "runtime" / "vjoy_output.py",
        PROJECT_ROOT / "v3_app" / "pages" / "mapping_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
        PROJECT_ROOT / "v3_app" / "services" / "perf_diagnostics.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths if path.exists())

    for forbidden in (
        "while True",
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Enable Live Output",
        "continuous vJoy output",
        "live output active",
        "runtime ready",
        "keyboard.add_hotkey",
        "mss",
        "dxcam",
        "VideoWriter",
        "ffmpeg",
    ):
        assert forbidden not in sources
    assert "fake_verified" in sources
    assert "real_verified" in sources
