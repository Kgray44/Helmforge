from shared_core.models.runtime import (
    HAT_CENTERED,
    AXIS_NAMES,
    BUTTON_NAMES,
    InputStatus,
    OutputStatus,
    RuntimeMode,
    RuntimeTruth,
)
from shared_core.runtime import vjoy_output
from shared_core.runtime.device_discovery import (
    build_runtime_preflight_status,
    detect_input_devices,
)
from shared_core.runtime.hotas_input import HotasInputAdapter
from shared_core.runtime.runtime_bridge import RuntimeBridge
from shared_core.runtime.simulated_runtime import SimulatedRuntime
from shared_core.runtime.vjoy_output import VJoyOutputAdapter


def test_missing_vjoy_does_not_crash_imports_and_reports_missing(monkeypatch):
    monkeypatch.setattr(vjoy_output, "find_vjoy_backend_name", lambda: None)

    adapter = VJoyOutputAdapter()
    status = adapter.detect()

    assert status.status is OutputStatus.VJOY_MISSING
    assert status.backend_name is None
    assert status.live_output_writes_verified is False


def test_missing_hotas_does_not_crash_and_reports_missing():
    adapter = HotasInputAdapter(device_names=[])

    status = adapter.detect()

    assert status.status is InputStatus.MISSING
    assert status.detected_device_names == ()


def test_simulation_runtime_returns_all_axes_buttons_and_hat_state():
    runtime = SimulatedRuntime(deterministic=True)

    snapshot = runtime.snapshot()

    assert tuple(snapshot.raw_axis_values) == AXIS_NAMES
    assert tuple(snapshot.final_output_values) == AXIS_NAMES
    assert tuple(snapshot.button_states) == BUTTON_NAMES
    assert snapshot.hat_state == HAT_CENTERED
    assert snapshot.simulated is True


def test_runtime_preflight_reports_simulation_fallback_when_runtime_missing():
    status = build_runtime_preflight_status(
        input_device_names=[],
        output_backend_names=[],
    )

    assert status.mode is RuntimeMode.SIMULATED
    assert status.truth is RuntimeTruth.SIMULATED
    assert status.input.status is InputStatus.MISSING
    assert status.output.status is OutputStatus.VJOY_MISSING
    assert status.live_output_writes_verified is False
    assert any("simulation" in message.lower() for message in status.messages)


def test_no_full_live_status_when_hotas_or_vjoy_are_missing():
    missing_both = build_runtime_preflight_status(input_device_names=[], output_backend_names=[])
    missing_vjoy = build_runtime_preflight_status(
        input_device_names=["Thrustmaster T.Flight HOTAS One"],
        output_backend_names=[],
    )
    missing_hotas = build_runtime_preflight_status(
        input_device_names=[],
        output_backend_names=["vJoy"],
    )

    assert missing_both.mode is not RuntimeMode.FULL_LIVE
    assert missing_vjoy.mode is not RuntimeMode.FULL_LIVE
    assert missing_hotas.mode is not RuntimeMode.FULL_LIVE


def test_fuzzy_detection_matches_thrustmaster_tflight_hotas_one_names():
    status = detect_input_devices(
        [
            "Generic USB Gamepad",
            "Thrustmaster T.Flight HOTAS One",
            "USB Input Device",
            "Thrustmaster T-Flight HOTAS One Controller",
        ]
    )

    assert status.status is InputStatus.DETECTED
    assert "Thrustmaster T.Flight HOTAS One" in status.detected_device_names
    assert "Thrustmaster T-Flight HOTAS One Controller" in status.detected_device_names


def test_no_fuzzy_device_match_returns_hotas_missing():
    status = detect_input_devices(["Generic USB Keyboard", "Xbox Wireless Controller"])

    assert status.status is InputStatus.MISSING
    assert status.detected_device_names == ()


def test_vjoy_missing_keeps_runtime_bridge_in_simulation_mode():
    status = build_runtime_preflight_status(
        input_device_names=["Thrustmaster T.Flight HOTAS One"],
        output_backend_names=[],
    )
    bridge = RuntimeBridge(preflight_status=status, deterministic_simulation=True)

    snapshot = bridge.snapshot()

    assert bridge.runtime_status.mode is RuntimeMode.SIMULATED
    assert bridge.runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DRIVER
    assert snapshot.runtime_status.mode is RuntimeMode.SIMULATED
    assert snapshot.simulated is True
    assert snapshot.raw_axis_values.keys() == snapshot.final_output_values.keys()
