from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _state():
    from shared_core.models.runtime import InputDeviceDetection, InputStatus, OutputBackendDetection, OutputStatus, RuntimeMode, RuntimePreflightStatus, RuntimeTruth
    from v3_app.services.app_state import AppState

    status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )
    return AppState.from_runtime_status(status, active_page_id="live_monitor")


def _telemetry(*, timestamp: datetime, roll: float = 0.2):
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
        controls=ButtonHatTelemetrySnapshot(buttons={button: False for button in BUTTON_NAMES}, hats={"POV": "Up"}),
        active_modes=ModeStateTelemetrySnapshot(),
        timestamp=timestamp,
        active_profile="Perf 1A",
        rule_summary=RuleStateSummary(),
        output_verification=OutputVerificationState(verified=False, backend_name="vJoy", message="missing"),
        runtime_frame={"telemetry_proof": "fresh", "input_stale": False},
    )


def test_perf_1a_liquid_freshness_only_changes_do_not_force_full_render_or_model_build():
    from shared_core.models.workspace import create_default_workspace
    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    _app()
    first = _telemetry(timestamp=datetime.now(timezone.utc), roll=0.2)
    page = AnalysisCommandPage(
        route_key="analysis.effective_response_stack",
        state=_state(),
        workspace=create_default_workspace(),
        telemetry=first,
    )
    render_count = page.render_count
    model_build_count = page.model_build_count

    for index in range(20):
        page.update_analysis_snapshot(
            telemetry=_telemetry(timestamp=first.timestamp + timedelta(milliseconds=index + 1), roll=0.2)
        )

    assert page.render_count == render_count
    assert page.model_build_count == model_build_count
    assert page.freshness_update_count > 0


def test_perf_1a_liquid_live_monitor_repeated_telemetry_does_not_duplicate_history_or_rebuild_numeric_panel():
    from shared_core.models.workspace import create_default_workspace
    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    _app()
    telemetry = _telemetry(timestamp=datetime.now(timezone.utc), roll=0.2)
    page = AnalysisCommandPage(
        route_key="analysis.live_monitor",
        state=_state(),
        workspace=create_default_workspace(),
        telemetry=telemetry,
    )
    history = page.property("liveMonitorHistoryLength")
    numeric_rebuilds = page.numeric_panel_rebuild_count

    for index in range(10):
        page.update_analysis_snapshot(telemetry=_telemetry(timestamp=telemetry.timestamp + timedelta(milliseconds=index), roll=0.2))

    assert page.property("liveMonitorHistoryLength") == history
    assert page.numeric_panel_rebuild_count == numeric_rebuilds

    for index in range(5):
        page.update_analysis_snapshot(telemetry=_telemetry(timestamp=telemetry.timestamp + timedelta(seconds=index + 1), roll=0.25 + index * 0.01))

    assert page.numeric_panel_rebuild_count == numeric_rebuilds
    assert page.numeric_panel_update_count >= 1
