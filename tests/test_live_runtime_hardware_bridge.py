from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


NOW = datetime(2026, 5, 9, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _clear_embedded_telemetry_cache():
    from v3_app.services.embedded_bridge_telemetry import clear_embedded_bridge_telemetry

    clear_embedded_bridge_telemetry()
    yield
    clear_embedded_bridge_telemetry()


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
        backend_name="fake_live_input",
    )


def _sample(value: float = 0.25):
    return {
        "axes": (
            {"raw_name": "X", "logical_name": "Roll", "raw_value": value, "raw_min": -1, "raw_max": 1},
            {"raw_name": "Y", "logical_name": "Pitch", "raw_value": -value, "raw_min": -1, "raw_max": 1},
            {"raw_name": "Z", "logical_name": "Throttle", "raw_value": 0.75, "raw_min": 0, "raw_max": 1, "one_sided": True},
            {"raw_name": "R", "logical_name": "Yaw", "raw_value": 0.10, "raw_min": -1, "raw_max": 1},
            {"raw_name": "U", "logical_name": "Aux 1", "raw_value": 0.0, "raw_min": -1, "raw_max": 1},
            {"raw_name": "V", "logical_name": "Aux 2", "raw_value": -0.10, "raw_min": -1, "raw_max": 1},
        ),
        "buttons": {1: True, 2: False},
        "hats": {1: "North"},
    }


class _Provider:
    backend_name = "Real vJoy"
    dependency_available = True
    driver_detected = True
    write_supported = True
    verification_supported = True

    def __init__(self) -> None:
        self.writes = []
        self.restores = 0

    def enumerate_devices(self):
        return ({"device_id": "1", "display_name": "vJoy Device 1", "backend_name": "Real vJoy"},)

    def acquire(self, device_id):
        return {"success": True, "status": "acquired", "message": f"acquired {device_id}"}

    def write_intent(self, device_id, intent):
        self.writes.append(intent)
        return {"success": True, "status": "real_write_succeeded", "message": f"wrote {device_id}"}

    def restore_neutral(self, device_id):
        self.restores += 1
        return {"success": True, "status": "neutral_restored", "message": f"neutral {device_id}"}

    def release(self, device_id):
        _ = device_id


def test_bridge_auto_connects_physical_input_and_runs_real_output_loop_when_available(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend
    from shared_core.runtime.runtime_bridge import RuntimeBridge
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend

    input_backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        backend_name="fake_live_input",
        sample_frames=(_sample(0.35),),
        clock=lambda: NOW,
        sample_source="physical",
    )
    provider = _Provider()
    output_backend = RealVJoyOutputBackend(provider=provider, clock=lambda: NOW)
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            physical_input_backend=input_backend,
            virtual_output_backend=output_backend,
            enable_live_input=True,
            enable_output_verification=True,
            enable_output_loop=True,
            simulate=False,
            clock=lambda: NOW + timedelta(milliseconds=len(provider.writes) * 20),
        )
    )

    telemetry = service.run_once()
    frame = telemetry.runtime_frame

    assert telemetry.input_status.value == "detected"
    assert telemetry.runtime_truth.value == "live_verified"
    assert telemetry.output_verified is True
    assert frame["input_source"] == "physical"
    assert frame["input_device"] == "Thrustmaster T.Flight HOTAS One"
    assert frame["output_backend"] == "Real vJoy"
    assert frame["output_verification_status"] == "real_verified"
    assert frame["output_loop_state"] == "running"
    assert frame["full_live_runtime_ready"] is True
    assert provider.writes


def test_bridge_disconnect_falls_back_without_leaving_output_loop_enabled(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend
    from shared_core.runtime.runtime_bridge import RuntimeBridge
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend

    input_backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        backend_name="fake_live_input",
        sample_frames=(_sample(),),
        disconnected=True,
        clock=lambda: NOW,
        sample_source="physical",
    )
    output_backend = RealVJoyOutputBackend(provider=_Provider(), clock=lambda: NOW)
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            physical_input_backend=input_backend,
            virtual_output_backend=output_backend,
            enable_live_input=True,
            enable_output_verification=True,
            enable_output_loop=True,
            simulate=False,
            clock=lambda: NOW,
        )
    )

    telemetry = service.run_once()
    frame = telemetry.runtime_frame

    assert telemetry.output_verified is True
    assert telemetry.runtime_truth.value != "live_verified"
    assert frame["input_source"] == "simulation"
    assert frame["output_loop_enabled"] is False
    assert frame["output_loop_running"] is False
    assert frame["full_live_runtime_ready"] is False
    assert "disconnect" in " ".join(telemetry.warnings).lower() or frame["blocked_reason"]


def test_live_ui_timing_contract_uses_60hz_and_right_anchored_history():
    from v3_app.pages.live_monitor_data import BoundedTelemetryHistory, TelemetrySample
    from v3_app.services.live_refresh import LIVE_REFRESH_INTERVAL_MS, LIVE_TRACE_HISTORY_SECONDS, LIVE_TRACE_SAMPLE_RATE_HZ

    history = BoundedTelemetryHistory.for_seconds(
        history_seconds=LIVE_TRACE_HISTORY_SECONDS,
        sample_rate_hz=LIVE_TRACE_SAMPLE_RATE_HZ,
    )
    assert LIVE_REFRESH_INTERVAL_MS <= 17
    assert LIVE_TRACE_SAMPLE_RATE_HZ >= 60
    assert history.capacity >= 420

    history.append(
        TelemetrySample(
            index=1,
            raw_axes={"Roll": 0.1},
            final_axes={"Roll": 0.2},
            buttons={},
            output_buttons={},
            hat_state="Centered",
            output_hat_state="Centered",
        )
    )
    assert history.raw_points("Roll") == ((0.0, 0.1),)

    for index in range(2, 430):
        history.append(
            TelemetrySample(
                index=index,
                raw_axes={"Roll": 0.3},
                final_axes={"Roll": 0.4},
                buttons={},
                output_buttons={},
                hat_state="Centered",
                output_hat_state="Centered",
            )
        )
    points = history.raw_points("Roll")
    assert points[-1][0] == 0.0
    assert points[0][0] >= -LIVE_TRACE_HISTORY_SECONDS


def test_embedded_app_bridge_ticks_live_telemetry_for_ui_consumers(tmp_path):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend
    from shared_core.runtime.runtime_bridge import RuntimeBridge
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus
    from v3_app.services.embedded_bridge_runtime import EmbeddedBridgeRuntime
    from v3_app.services.live_input_source import LiveAxisSampleSource

    input_backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        backend_name="fake_live_input",
        sample_frames=(_sample(0.42),),
        clock=lambda: NOW,
        sample_source="physical",
    )
    provider = _Provider()
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            physical_input_backend=input_backend,
            virtual_output_backend=RealVJoyOutputBackend(provider=provider, clock=lambda: NOW),
            simulate=False,
            clock=lambda: NOW,
        )
    )
    seen = []
    runtime = EmbeddedBridgeRuntime(on_telemetry=seen.append, service_factory=lambda: service)

    runtime.tick()
    result = BridgeTelemetryClient(telemetry_path=tmp_path / "telemetry.json", clock=lambda: NOW).read()
    axes = LiveAxisSampleSource(
        RuntimeBridge(preflight_status=service.runtime_status),
        bridge_client=BridgeTelemetryClient(telemetry_path=tmp_path / "telemetry.json", clock=lambda: NOW),
    ).raw_axes()

    assert seen[-1].runtime_truth.value == "live_verified"
    assert result.status is BridgeTelemetryStatus.CONNECTED
    assert result.telemetry is not None
    assert result.telemetry.runtime_frame.input_source == "physical"
    assert axes["Roll"] == 0.42


def test_shell_runtime_header_updates_from_embedded_bridge_telemetry(tmp_path):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from bridge_app.service import BridgeService, BridgeServiceOptions
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
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    QApplication.instance() or QApplication([])
    stale_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )
    shell = HelmForgeShell(
        AppState.from_runtime_status(stale_status, driver_detected=True),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            physical_input_backend=FakePhysicalInputBackend(
                (_hotas_device(),),
                backend_name="fake_live_input",
                sample_frames=(_sample(0.50),),
                clock=lambda: NOW,
                sample_source="physical",
            ),
            virtual_output_backend=RealVJoyOutputBackend(provider=_Provider(), clock=lambda: NOW),
            simulate=False,
            clock=lambda: NOW,
        )
    )

    shell.apply_bridge_telemetry(service.run_once())

    assert shell.state.runtime.header_truth_label == "Live Verified"
    assert shell.runtime_status.truth is RuntimeTruth.LIVE_VERIFIED
    assert shell.runtime_status.live_output_writes_verified is True


def test_mapping_page_status_chips_follow_live_runtime_updates(tmp_path):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QLabel
    from bridge_app.service import BridgeService, BridgeServiceOptions
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
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend
    from shared_core.runtime.vjoy_output import RealVJoyOutputBackend
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    QApplication.instance() or QApplication([])
    stale_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )
    shell = HelmForgeShell(
        AppState.from_runtime_status(stale_status, driver_detected=True),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            physical_input_backend=FakePhysicalInputBackend(
                (_hotas_device(),),
                backend_name="fake_live_input",
                sample_frames=(_sample(0.50),),
                clock=lambda: NOW,
                sample_source="physical",
            ),
            virtual_output_backend=RealVJoyOutputBackend(provider=_Provider(), clock=lambda: NOW),
            simulate=False,
            clock=lambda: NOW,
        )
    )

    shell.apply_bridge_telemetry(service.run_once())
    labels = shell.page_widgets["mapping"].widget().findChildren(QLabel)
    visible_text = "\n".join(label.text() for label in labels if not label.isHidden())

    assert "Live Verified" in visible_text
    assert "vJoy Verified" in visible_text
    assert "Output Unverified" not in visible_text


def test_default_embedded_bridge_runtime_uses_worker_thread():
    from v3_app.services.embedded_bridge_runtime import EmbeddedBridgeRuntime

    runtime = EmbeddedBridgeRuntime(on_telemetry=lambda telemetry: None)
    try:
        assert runtime._threaded is True
        try:
            runtime.tick()
        except RuntimeError as exc:
            assert "threaded embedded bridge runtime" in str(exc)
        else:
            raise AssertionError("threaded runtime should not tick on the UI thread")
    finally:
        runtime.stop()
