from __future__ import annotations

import ast
from pathlib import Path

from shared_core.models.runtime import AXIS_NAMES, BUTTON_NAMES, InputStatus, OutputStatus, RuntimeTruth
from shared_core.runtime.bridge_contracts import (
    BridgeCommandRequest,
    BridgeCommandType,
    BridgeConfigurationReloadRequest,
    BridgeHealthSummary,
)
from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState, BridgeLifecycleStatus
from shared_core.runtime.telemetry import (
    AxisTelemetrySnapshot,
    BridgeTelemetrySnapshot,
    ButtonHatTelemetrySnapshot,
    ModeStateTelemetrySnapshot,
    OutputVerificationState,
    RuleStateSummary,
)


def test_bridge_lifecycle_states_preserve_phase2b_semantics():
    expected = {
        "NotInstalled",
        "Stopped",
        "Starting",
        "WaitingForHotas",
        "HotasDetected",
        "WaitingForOutput",
        "Simulated",
        "LiveUnverified",
        "LiveVerified",
        "Suspended",
        "Stopping",
        "Error",
    }

    assert expected.issubset({state.value for state in BridgeLifecycleState})


def test_bridge_command_models_exist_and_serialize_for_future_ipc():
    expected_commands = {
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "SuspendBridge",
        "ReloadConfig",
        "RunPreflight",
        "SwitchToSimulation",
        "VerifyOutput",
        "ClearError",
    }

    assert expected_commands.issubset({command.value for command in BridgeCommandType})

    request = BridgeCommandRequest(
        command=BridgeCommandType.RELOAD_CONFIG,
        request_id="phase-2b-test",
        config_path="hotas_bridge_config_v3.json",
        reason="test reload contract",
    )
    reload_request = BridgeConfigurationReloadRequest(
        request_id="phase-2b-reload",
        config_path="hotas_bridge_config_v3.json",
    )

    assert request.to_dict()["command"] == "ReloadConfig"
    assert request.to_dict()["config_path"] == "hotas_bridge_config_v3.json"
    assert reload_request.to_command_request().command is BridgeCommandType.RELOAD_CONFIG


def test_telemetry_snapshot_can_represent_simulated_state():
    raw_axes = {axis: 0.0 for axis in AXIS_NAMES}
    final_axes = {axis: 0.0 for axis in AXIS_NAMES}
    buttons = {button: False for button in BUTTON_NAMES}

    telemetry = BridgeTelemetrySnapshot(
        runtime_truth=RuntimeTruth.SIMULATED,
        lifecycle_state=BridgeLifecycleState.SIMULATED,
        input_status=InputStatus.MISSING,
        output_status=OutputStatus.VJOY_MISSING,
        raw_axes=AxisTelemetrySnapshot(raw_axes),
        final_axes=AxisTelemetrySnapshot(final_axes),
        controls=ButtonHatTelemetrySnapshot(buttons=buttons, hats={"Hat 1": "Centered"}),
        active_modes=ModeStateTelemetrySnapshot(),
        active_profile="Current Workspace",
        rule_summary=RuleStateSummary(disabled_count=1),
    )

    payload = telemetry.to_dict()

    assert payload["runtime_truth"] == "simulated"
    assert payload["lifecycle_state"] == "Simulated"
    assert payload["output_verified"] is False
    assert payload["raw_axes"]["Roll"] == 0.0
    assert payload["buttons"]["B15"] is False
    assert payload["hats"]["Hat 1"] == "Centered"
    assert payload["rule_summary"]["disabled_count"] == 1


def test_telemetry_snapshot_can_represent_detected_unverified_state():
    telemetry = BridgeTelemetrySnapshot(
        runtime_truth=RuntimeTruth.DETECTED_UNVERIFIED,
        lifecycle_state=BridgeLifecycleState.LIVE_UNVERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        raw_axes=AxisTelemetrySnapshot({axis: 0.1 for axis in AXIS_NAMES}),
        final_axes=AxisTelemetrySnapshot({axis: 0.05 for axis in AXIS_NAMES}),
        controls=ButtonHatTelemetrySnapshot(
            buttons={button: False for button in BUTTON_NAMES},
            hats={"Hat 1": "Centered"},
        ),
        active_modes=ModeStateTelemetrySnapshot(precision_active=True),
        output_verification=OutputVerificationState(backend_name="vJoy", verified=False),
        active_profile="Current Workspace",
        warnings=("Output backend detected but writes are not verified.",),
    )

    payload = telemetry.to_dict()

    assert payload["runtime_truth"] == "detected_unverified"
    assert payload["lifecycle_state"] == "LiveUnverified"
    assert payload["input_status"] == "detected"
    assert payload["output_status"] == "vjoy_detected"
    assert payload["output_verified"] is False
    assert payload["output_verification"]["backend_name"] == "vJoy"


def test_bridge_health_summary_defaults_to_unverified_output():
    health = BridgeHealthSummary(
        lifecycle=BridgeLifecycleStatus(state=BridgeLifecycleState.WAITING_FOR_OUTPUT),
        runtime_truth=RuntimeTruth.BLOCKED_MISSING_DRIVER,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_MISSING,
    )

    assert health.output_verified is False
    assert health.to_dict()["lifecycle"]["state"] == "WaitingForOutput"


def test_shared_core_does_not_import_v3_app_or_pyside6():
    project_root = Path(__file__).resolve().parents[1]
    shared_core = project_root / "shared_core"
    forbidden = {"v3_app", "PySide6"}
    violations: list[str] = []

    for path in shared_core.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module_name = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    if module_name in forbidden:
                        violations.append(f"{path}: imports {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_name = node.module.split(".")[0]
                if module_name in forbidden:
                    violations.append(f"{path}: imports from {node.module}")

    assert violations == []


def test_runtime_contract_modules_import_without_pyside6():
    import shared_core.runtime.bridge_contracts as bridge_contracts
    import shared_core.runtime.bridge_lifecycle as bridge_lifecycle
    import shared_core.runtime.device_discovery as device_discovery
    import shared_core.runtime.telemetry as telemetry
    import shared_core.runtime.vjoy_output as vjoy_output

    module_names = {
        bridge_contracts.__name__,
        bridge_lifecycle.__name__,
        device_discovery.__name__,
        telemetry.__name__,
        vjoy_output.__name__,
    }

    assert "shared_core.runtime.telemetry" in module_names
