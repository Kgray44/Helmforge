from __future__ import annotations

import os
from datetime import datetime, timezone

import shiboken6


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _state(*, active_page_id: str = "live_monitor"):
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )
    from v3_app.services.app_state import AppState

    status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )
    return AppState.from_runtime_status(status, active_page_id=active_page_id)


def _telemetry(*, roll: float = 0.2):
    from shared_core.models.runtime import AXIS_NAMES, BUTTON_NAMES, InputStatus, OutputStatus, RuntimeTruth
    from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState
    from shared_core.runtime.telemetry import (
        AxisTelemetrySnapshot,
        BridgeTelemetrySnapshot,
        ButtonHatTelemetrySnapshot,
        ModeStateTelemetrySnapshot,
        OutputVerificationState,
        RuleStateSummary,
    )

    raw = {axis: 0.0 for axis in AXIS_NAMES}
    raw["Roll"] = roll
    final = {axis: value * 0.5 for axis, value in raw.items()}
    return BridgeTelemetrySnapshot(
        runtime_truth=RuntimeTruth.DETECTED_UNVERIFIED,
        lifecycle_state=BridgeLifecycleState.SIMULATED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        raw_axes=AxisTelemetrySnapshot(raw),
        final_axes=AxisTelemetrySnapshot(final),
        controls=ButtonHatTelemetrySnapshot(buttons={button: False for button in BUTTON_NAMES}, hats={"POV": "Right"}),
        active_modes=ModeStateTelemetrySnapshot(),
        timestamp=datetime.now(timezone.utc),
        active_profile="Perf 1A.1",
        rule_summary=RuleStateSummary(),
        output_verification=OutputVerificationState(verified=False, backend_name="vJoy", message="missing"),
        runtime_frame={"telemetry_proof": "fresh", "input_stale": False},
    )


def _text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_perf_1a1_profiles_preset_selection_does_not_delete_tree_during_selection_signal():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTreeWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    app = _app()
    shell = LiquidCommandShell(state=_state(active_page_id="profiles_library"))
    shell.switch_route("tuning.profiles_library")
    app.processEvents()
    page = shell.page_widgets["tuning.profiles_library"].widget()
    tree = page.findChild(QTreeWidget, "liquidTuningProfilesPresetTree")
    assert tree is not None

    selected = None
    for category_index in range(tree.topLevelItemCount()):
        category = tree.topLevelItem(category_index)
        for child_index in range(category.childCount()):
            child = category.child(child_index)
            if child.text(0) == "Balanced Default":
                selected = child
    assert selected is not None

    tree.setCurrentItem(selected)

    assert shiboken6.isValid(tree)
    assert page.property("profilesLibraryRenderQueued") is True
    assert page.property("selectedPresetId") == "balanced_default"

    app.processEvents()
    refreshed_tree = page.findChild(QTreeWidget, "liquidTuningProfilesPresetTree")
    assert refreshed_tree is not None
    assert page.property("selectedPresetName") == "Balanced Default"
    assert page.property("deferredPresetRenderCount") == 1


def test_perf_1a1_liquid_live_monitor_uses_visual_timer_without_restarting_heavy_lanes():
    from shared_core.models.workspace import create_default_workspace
    from v3_app.liquid.pages.analysis_command_pages import (
        LIQUID_LIVE_MONITOR_DISPLAY_INTERVAL_MS,
        LIQUID_LIVE_MONITOR_VISUAL_TARGET_FPS,
        AnalysisCommandPage,
    )

    _app()
    page = AnalysisCommandPage(
        route_key="analysis.live_monitor",
        state=_state(),
        workspace=create_default_workspace(),
        telemetry=_telemetry(roll=0.1),
    )
    page.set_live_monitor_active(True)

    assert LIQUID_LIVE_MONITOR_VISUAL_TARGET_FPS == 60
    assert 15 <= LIQUID_LIVE_MONITOR_DISPLAY_INTERVAL_MS <= 17
    assert page.property("liveMonitorDisplayIntervalMs") == LIQUID_LIVE_MONITOR_DISPLAY_INTERVAL_MS
    assert page.property("liveMonitorDisplayTimerActive") is True
    assert page.property("liveMonitorGraphCadenceHz") == 60
    assert page.property("liveMonitorVisualRenderOnly") is True


def test_perf_1a1_live_monitor_status_cards_refresh_when_telemetry_arrives_after_missing_state():
    from shared_core.models.runtime import AXIS_NAMES
    from shared_core.models.workspace import create_default_workspace
    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    _app()
    page = AnalysisCommandPage(
        route_key="analysis.live_monitor",
        state=_state(),
        workspace=create_default_workspace(),
        telemetry=None,
    )
    for axis in AXIS_NAMES:
        page._axis_history[axis] = [(0.0, 0.0), (0.1, 0.05)]
    assert "Telemetry missing" in _text(page)

    page.update_analysis_snapshot(telemetry=_telemetry(roll=0.45))

    page_text = _text(page)
    assert "Telemetry fresh" in page_text
    assert "Telemetry missing" not in page_text
    assert page.property("liveMonitorStatusSurfaceUpdateCount") >= 1
    assert page.property("liveMonitorAcceptedSampleCount") >= 0


def test_perf_1a1_liquid_telemetry_burst_does_not_paint_graph_every_frame():
    from shared_core.models.workspace import create_default_workspace
    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    _app()
    page = AnalysisCommandPage(
        route_key="analysis.live_monitor",
        state=_state(),
        workspace=create_default_workspace(),
        telemetry=_telemetry(roll=0.1),
    )
    page.set_live_monitor_active(True)
    initial_graphs = int(page.property("liveMonitorGraphUpdateCount") or 0)

    for index in range(60):
        page.update_analysis_snapshot(telemetry=_telemetry(roll=-0.8 + index * 0.02))

    graph_updates_from_telemetry = int(page.property("liveMonitorGraphUpdateCount") or 0) - initial_graphs
    assert graph_updates_from_telemetry < 10

    timer_graphs_before = int(page.property("liveMonitorGraphUpdateCount") or 0)
    accepted_before = int(page.property("liveMonitorAcceptedSampleCount") or 0)
    for _ in range(6):
        assert page.advance_live_monitor_display_sample() is True

    assert int(page.property("liveMonitorGraphUpdateCount") or 0) - timer_graphs_before == 6
    assert int(page.property("liveMonitorAcceptedSampleCount") or 0) == accepted_before


def test_perf_1a1_analysis_actions_and_route_switch_stop_hidden_live_timer():
    from PySide6.QtWidgets import QPushButton
    from v3_app.liquid.app_shell import LiquidCommandShell

    app = _app()
    shell = LiquidCommandShell(state=_state())
    shell.switch_route("analysis.live_monitor")
    shell.apply_bridge_telemetry(_telemetry(roll=0.2))
    app.processEvents()
    page = shell.page_widgets["analysis.live_monitor"].widget()
    assert page.property("liveMonitorDisplayTimerActive") is True

    for object_name in (
        "liquidLiveMonitorOverlayToggle",
        "liquidLiveMonitorPauseButton",
        "liquidLiveMonitorPauseButton",
        "liquidLiveMonitorClearHistoryButton",
    ):
        button = page.findChild(QPushButton, object_name)
        assert button is not None
        button.click()
        app.processEvents()

    stack_button = page.findChild(QPushButton, "liquidLiveMonitorOpenStackButton")
    assert stack_button is not None
    stack_button.click()
    shell.apply_bridge_telemetry(_telemetry(roll=0.35))
    app.processEvents()

    assert shell.current_route_key == "analysis.effective_response_stack"
    assert page.property("liveMonitorDisplayTimerActive") is False
    assert page.property("liveMonitorDisplayActive") is False
    assert shell.property("recursiveRouteSyncGuardCount") == 0
