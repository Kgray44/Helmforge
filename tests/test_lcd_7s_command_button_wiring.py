from __future__ import annotations

import os
from datetime import datetime, timezone

from shared_core.models.runtime import (
    AXIS_NAMES,
    BUTTON_NAMES,
    InputStatus,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)
from shared_core.models.workspace import create_default_workspace
from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState
from shared_core.runtime.telemetry import (
    AxisTelemetrySnapshot,
    BridgeTelemetrySnapshot,
    ButtonHatTelemetrySnapshot,
    ModeStateTelemetrySnapshot,
    OutputVerificationState,
    RuleStateSummary,
)


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _state(*, active_page_id: str = "mapping"):
    from shared_core.models.runtime import InputDeviceDetection, OutputBackendDetection
    from v3_app.services.app_state import AppState

    runtime_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )
    state = AppState.from_runtime_status(runtime_status, active_page_id=active_page_id)
    state.active_profile = "LCD-7S Fixture"
    state.status_message = "Workspace ready."
    return state


def _telemetry() -> BridgeTelemetrySnapshot:
    raw_axes = {axis: (index - 2) / 5 for index, axis in enumerate(AXIS_NAMES)}
    final_axes = {axis: value * 0.75 for axis, value in raw_axes.items()}
    return BridgeTelemetrySnapshot(
        runtime_truth=RuntimeTruth.DETECTED_UNVERIFIED,
        lifecycle_state=BridgeLifecycleState.SIMULATED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        raw_axes=AxisTelemetrySnapshot(raw_axes),
        final_axes=AxisTelemetrySnapshot(final_axes),
        controls=ButtonHatTelemetrySnapshot(
            buttons={button: index in {0, 4, 14} for index, button in enumerate(BUTTON_NAMES)},
            hats={"POV": "Right"},
        ),
        active_modes=ModeStateTelemetrySnapshot(active_mode_names=("Combat",)),
        timestamp=datetime.now(timezone.utc),
        active_profile="LCD-7S Fixture",
        rule_summary=RuleStateSummary(active_count=0, blocked_count=0, disabled_count=1),
        output_verification=OutputVerificationState(
            verified=False,
            backend_name="vJoy",
            message="Output proof missing.",
        ),
        runtime_frame={"telemetry_proof": "fresh", "input_stale": False, "output_proof": "missing"},
    )


def _real_route_keys(shell) -> tuple[str, ...]:
    return (
        "preflight.command_readiness",
        "mapping.hotas_map",
        "mapping.route_details",
        "mapping.advanced_route_tables",
        "tuning.base_tuning",
        "tuning.filtering",
        "tuning.combat_profile",
        "tuning.conditional_rules",
        "analysis.effective_response_stack",
        "analysis.live_monitor",
        "recorder.flight_recorder",
        "recorder.clip_library",
        "recorder.capture_backend_truth",
    )


def _liquid_buttons(widget):
    from PySide6.QtWidgets import QPushButton

    return [
        button
        for button in widget.findChildren(QPushButton)
        if button.objectName().startswith("liquid")
    ]


def test_lcd_7s_every_real_liquid_page_button_is_classified_or_disabled_with_reason():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    allowed_action_kinds = {
        "navigation",
        "copy",
        "stage_draft",
        "validate",
        "revert",
        "reset",
        "toggle_ui",
        "select_state",
        "open_panel",
        "disabled_deferred",
    }
    unsafe_enabled_labels = (
        "write to vjoy",
        "verify output",
        "start bridge",
        "stop bridge",
        "restart bridge",
        "apply live",
    )

    shell_buttons = _liquid_buttons(shell)
    assert shell_buttons
    for button in shell_buttons:
        kind = button.property("actionKind")
        if button.isEnabled():
            assert kind in allowed_action_kinds, f"shell:{button.objectName()} lacks a safe action kind"
            assert kind not in {"noop", "unclassified"}
        else:
            reason = button.property("disabledReason") or button.toolTip() or button.statusTip() or button.accessibleDescription()
            assert kind in allowed_action_kinds, f"shell:{button.objectName()} disabled action is unclassified"
            assert reason, f"shell:{button.objectName()} is disabled without a reason"

    for route_key in _real_route_keys(shell):
        shell.switch_route(route_key)
        page = shell.page_widgets[route_key].widget()
        buttons = _liquid_buttons(page)
        assert buttons, f"{route_key} should expose command-capable buttons"
        enabled_count = 0
        for button in buttons:
            kind = button.property("actionKind")
            if button.isEnabled():
                enabled_count += 1
                assert kind in allowed_action_kinds, f"{route_key}:{button.objectName()} lacks a safe action kind"
                assert kind not in {"noop", "unclassified"}, f"{route_key}:{button.objectName()} is marked no-op"
                assert not any(label in button.text().casefold() for label in unsafe_enabled_labels)
            else:
                reason = button.property("disabledReason") or button.toolTip() or button.statusTip() or button.accessibleDescription()
                assert kind in allowed_action_kinds, f"{route_key}:{button.objectName()} disabled action is unclassified"
                assert reason, f"{route_key}:{button.objectName()} is disabled without a reason"
        assert enabled_count > 0, f"{route_key} should have at least one enabled safe action"


def test_lcd_7s_navigation_copy_validate_stage_and_toggle_buttons_have_visible_effects():
    app = _app()

    from PySide6.QtWidgets import QApplication, QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    clipboard = QApplication.clipboard()

    shell.switch_route("preflight.command_readiness")
    preflight = shell.page_widgets["preflight.command_readiness"].widget()
    copy_status = preflight.findChild(QPushButton, "liquidPreflightCopyStatusButton")
    assert copy_status.property("actionKind") == "copy"
    copy_status.click()
    app.processEvents()
    assert clipboard.text().strip()
    assert copy_status.property("lastActionStatus")

    open_mapping = preflight.findChild(QPushButton, "liquidPreflightOpenMappingButton")
    assert open_mapping.property("actionKind") == "navigation"
    open_mapping.click()
    app.processEvents()
    assert shell.current_route_key == "mapping.hotas_map"

    hotas = shell.page_widgets["mapping.hotas_map"].widget()
    marker = hotas.findChild(QPushButton, "liquidMappingMarker_axis_yaw")
    marker.click()
    app.processEvents()
    assert hotas.property("selectedControlId") == "axis_yaw"
    marker = hotas.findChild(QPushButton, "liquidMappingMarker_axis_yaw")
    assert marker.property("actionKind") == "select_state"

    route_details = hotas.findChild(QPushButton, "liquidMappingEditSelectedRouteButton")
    route_details.click()
    app.processEvents()
    assert shell.current_route_key == "mapping.route_details"

    details = shell.page_widgets["mapping.route_details"].widget()
    validate = details.findChild(QPushButton, "liquidMappingValidateRouteButton")
    validate.click()
    app.processEvents()
    assert validate.property("actionKind") == "validate"
    assert validate.property("lastActionStatus")

    stage_route = details.findChild(QPushButton, "liquidMappingStageButton_axis_axis_yaw_output_intent_target")
    assert stage_route.property("actionKind") == "stage_draft"
    before_runtime_truth = shell.state.runtime.header_truth_label
    stage_route.click()
    app.processEvents()
    assert shell.state.saved is False
    assert shell.state.runtime.header_truth_label == before_runtime_truth

    shell.switch_route("tuning.base_tuning")
    tuning = shell.page_widgets["tuning.base_tuning"].widget()
    stage_tuning = tuning.findChild(QPushButton, "liquidTuningStage_base_deadzone")
    assert stage_tuning.property("actionKind") == "stage_draft"
    stage_tuning.click()
    app.processEvents()
    assert shell.state.runtime.header_truth_label == before_runtime_truth
    assert shell.state.saved is False

    reset = tuning.findChild(QPushButton, "liquidTuningResetAxisButton")
    assert not reset.isEnabled()
    assert reset.property("disabledReason")

    shell.switch_route("analysis.live_monitor")
    monitor = shell.page_widgets["analysis.live_monitor"].widget()
    graph = monitor.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
    overlay = monitor.findChild(QPushButton, "liquidLiveMonitorOverlayToggle")
    overlay_before = bool(graph.property("overlayFinalValues"))
    overlay.click()
    app.processEvents()
    assert bool(graph.property("overlayFinalValues")) is (not overlay_before)

    monitor.update_analysis_snapshot(state=shell.state, workspace=create_default_workspace(), telemetry=_telemetry(), selected_axis="Roll")
    graph = monitor.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
    assert int(graph.property("historyLength") or 0) > 0
    clear = monitor.findChild(QPushButton, "liquidLiveMonitorClearHistoryButton")
    clear.click()
    app.processEvents()
    graph = monitor.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
    assert int(graph.property("historyLength") or 0) == 0
