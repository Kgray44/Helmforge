from __future__ import annotations

import os
from dataclasses import dataclass
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
    )


@dataclass
class _ProviderResult:
    success: bool
    status: str
    message: str


class _InjectedLoopProvider:
    backend_name = "Injected real vJoy loop provider"
    dependency_available = True
    driver_detected = True
    write_supported = True
    verification_supported = True

    def __init__(self) -> None:
        self.write_calls = 0
        self.restore_calls = 0
        self.devices = ()

    def enumerate_devices(self):
        return self.devices

    def acquire(self, device_id: str):
        _ = device_id
        return _ProviderResult(True, "acquired", "device acquired")

    def write_intent(self, device_id: str, intent):
        _ = device_id, intent
        self.write_calls += 1
        return _ProviderResult(True, "write_succeeded", "bounded write succeeded")

    def restore_neutral(self, device_id: str):
        _ = device_id
        self.restore_calls += 1
        return _ProviderResult(True, "neutral_restored", "neutral restored")

    def release(self, device_id: str) -> None:
        _ = device_id


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


class _Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


def test_phase15c_loop_starts_disabled_and_refuses_missing_or_unverified_backend():
    from shared_core.runtime.vjoy_output import (
        FakeVirtualOutputBackend,
        MissingVirtualOutputBackend,
        VirtualOutputIntent,
        VirtualOutputWriteLoop,
        VirtualOutputWriteLoopState,
    )

    missing_loop = VirtualOutputWriteLoop(backend=MissingVirtualOutputBackend())
    assert missing_loop.snapshot().state is VirtualOutputWriteLoopState.DISABLED

    missing_enable = missing_loop.enable()
    assert missing_enable.state is VirtualOutputWriteLoopState.UNAVAILABLE_BACKEND_MISSING
    missing_tick = missing_loop.tick(VirtualOutputIntent.defaults(source="test"))
    assert missing_tick.write_count == 0

    fake_backend = FakeVirtualOutputBackend()
    fake_loop = VirtualOutputWriteLoop(backend=fake_backend)
    unverified = fake_loop.enable()
    assert unverified.state is VirtualOutputWriteLoopState.UNAVAILABLE_UNVERIFIED
    assert fake_loop.tick(VirtualOutputIntent.defaults(source="test")).write_count == 0
    assert fake_backend.last_written_intent is None


def test_phase15c_fake_loop_requires_fake_verification_explicit_enable_and_rate_limits():
    from shared_core.runtime.vjoy_output import (
        FakeVirtualOutputBackend,
        VirtualAxisOutput,
        VirtualOutputIntent,
        VirtualOutputLoopConfig,
        VirtualOutputVerificationStatus,
        VirtualOutputWriteLoop,
        VirtualOutputWriteLoopState,
    )

    clock = _Clock()
    backend = FakeVirtualOutputBackend()
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test", timestamp=clock()))
    loop = VirtualOutputWriteLoop(
        backend=backend,
        verification=verification,
        config=VirtualOutputLoopConfig(write_rate_hz=10.0),
        clock=clock,
    )

    assert verification.status is VirtualOutputVerificationStatus.FAKE_VERIFIED
    assert loop.snapshot().fake_output_loop is True
    assert loop.snapshot().real_output_loop is False

    enabled = loop.enable()
    assert enabled.state is VirtualOutputWriteLoopState.READY_VERIFIED
    intent = VirtualOutputIntent(
        timestamp=clock(),
        source="test",
        axes=(VirtualAxisOutput("X", 0.25), VirtualAxisOutput("Y", 2.0)),
        output_enabled=True,
        write_requested=True,
    )

    first = loop.tick(intent)
    assert first.state is VirtualOutputWriteLoopState.RUNNING
    assert first.write_count == 1
    assert backend.last_written_intent is not None
    assert backend.last_written_intent.axis_value("Y") == 1.0

    rate_limited = loop.tick(intent)
    assert rate_limited.write_count == 1
    clock.advance(0.11)
    second = loop.tick(intent)
    assert second.write_count == 2
    assert "fake" in second.output_write_status
    assert second.real_output_loop is False
    assert second.full_live_runtime_ready is False


def test_phase15c_stop_sends_neutral_restore_and_surfaces_restore_failure():
    from shared_core.runtime.vjoy_output import (
        FakeVirtualOutputBackend,
        VirtualOutputIntent,
        VirtualOutputWriteLoop,
        VirtualOutputWriteLoopState,
    )

    clock = _Clock()
    backend = FakeVirtualOutputBackend()
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test", timestamp=clock()))
    loop = VirtualOutputWriteLoop(backend=backend, verification=verification, clock=clock)
    loop.enable()
    loop.tick(VirtualOutputIntent.defaults(source="test", timestamp=clock()))

    stopped = loop.disable()
    assert stopped.state is VirtualOutputWriteLoopState.STOPPED_NEUTRAL
    assert stopped.neutral_restore_status == "restored"
    assert backend.written_intents[-1].source == "neutral_restore"

    failing_backend = FakeVirtualOutputBackend(fail_neutral_restore=True)
    failing_verification = failing_backend.verify_output_write(VirtualOutputIntent.defaults(source="test", timestamp=clock()))
    failing_loop = VirtualOutputWriteLoop(backend=failing_backend, verification=failing_verification, clock=clock)
    failing_loop.enable()
    failing_loop.tick(VirtualOutputIntent.defaults(source="test", timestamp=clock()))
    restore_failed = failing_loop.disable()

    assert restore_failed.state is VirtualOutputWriteLoopState.ERROR_RESTORE_FAILED
    assert restore_failed.neutral_restore_status == "failed"
    assert "neutral" in restore_failed.last_error.casefold()


def test_phase15c_write_failure_safety_stops_loop_without_hiding_error():
    from shared_core.runtime.vjoy_output import (
        FakeVirtualOutputBackend,
        VirtualOutputIntent,
        VirtualOutputWriteLoop,
        VirtualOutputWriteLoopState,
    )

    backend = FakeVirtualOutputBackend(fail_writes=True)
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    loop = VirtualOutputWriteLoop(backend=backend, verification=verification)
    loop.enable()
    snapshot = loop.tick(VirtualOutputIntent.defaults(source="test"))

    assert snapshot.state is VirtualOutputWriteLoopState.SAFETY_STOPPED
    assert snapshot.enabled is False
    assert snapshot.write_count == 0
    assert snapshot.failure_count == 1
    assert snapshot.safety_stop_reason == "write_failed"
    assert "failed" in snapshot.last_error.casefold()


def test_phase15c_real_backend_loop_requires_real_verification_before_any_real_write():
    from shared_core.runtime.vjoy_output import (
        RealVJoyOutputBackend,
        VirtualOutputIntent,
        VirtualOutputWriteLoop,
        VirtualOutputWriteLoopState,
    )

    provider = _InjectedLoopProvider()
    provider.devices = (_device(),)
    backend = RealVJoyOutputBackend(provider=provider)
    loop = VirtualOutputWriteLoop(backend=backend)
    unverified = loop.enable()

    assert unverified.state is VirtualOutputWriteLoopState.UNAVAILABLE_UNVERIFIED
    assert loop.tick(VirtualOutputIntent.defaults(source="test")).write_count == 0
    assert provider.write_calls == 0

    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    verified_loop = VirtualOutputWriteLoop(backend=backend, verification=verification)
    assert verified_loop.enable().state is VirtualOutputWriteLoopState.READY_VERIFIED
    written = verified_loop.tick(VirtualOutputIntent.defaults(source="test"))

    assert written.state is VirtualOutputWriteLoopState.RUNNING
    assert written.real_output_loop is True
    assert written.fake_output_loop is False
    assert written.full_live_runtime_ready is False
    assert provider.write_calls >= 2


def test_phase15c_perf_diagnostics_and_help_docs_show_output_loop_truth(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from shared_core.runtime.vjoy_output import (
        FakeVirtualOutputBackend,
        VirtualOutputIntent,
        VirtualOutputWriteLoop,
    )
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.app_state import AppState
    from v3_app.services.help_docs import get_article

    _app()
    backend = FakeVirtualOutputBackend()
    verification = backend.verify_output_write(VirtualOutputIntent.defaults(source="test"))
    loop = VirtualOutputWriteLoop(backend=backend, verification=verification)
    loop.enable()
    loop.tick(VirtualOutputIntent.defaults(source="test"))

    page = PerfDiagnosticsPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        virtual_output_backend=backend,
        virtual_output_verification=verification,
        virtual_output_loop=loop,
    )
    text = "\n".join(label.text() for label in page.findChildren(__import__("PySide6.QtWidgets").QtWidgets.QLabel))
    copy_text = page.prepare_copy_diagnostics()

    assert "Output loop\nrunning" in text
    assert "Output loop write count\n1" in text
    assert "Neutral restore status\nnot_attempted" in text
    assert "Fake output verified\ntrue" in text
    assert "Real output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text
    assert "Output loop: running" in copy_text
    assert "Output loop write count: 1" in copy_text
    assert "Neutral restore status: not_attempted" in copy_text

    runtime_setup = get_article("Runtime Setup / vJoy Setup").body
    indicators = get_article("Runtime Indicators").body
    diagnostics = get_article("Performance / Diagnostics").body
    assert "Phase 15C adds controlled output write-loop integration" in runtime_setup
    assert "output loop requires verified backend" in runtime_setup
    assert "vJoy detection alone is not enough" in runtime_setup
    assert "fake output loop is test/dev only" in runtime_setup
    assert "neutral restore is attempted on stop" in runtime_setup
    assert "write failures safety-stop the loop" in runtime_setup
    assert "Output loop" in indicators
    assert "output loop fields" in diagnostics


def test_phase15c_no_automatic_loop_or_bridge_lifecycle_authority_was_added():
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
        "Full Live button",
        "Install vJoy",
        "Install Service",
        "Enable Auto Start",
        "keyboard.add_hotkey",
        "mss",
        "dxcam",
        "VideoWriter",
        "ffmpeg",
    ):
        assert forbidden not in sources
    assert "VirtualOutputWriteLoop" in sources
    assert "Full Live Runtime Ready remains false" in sources
