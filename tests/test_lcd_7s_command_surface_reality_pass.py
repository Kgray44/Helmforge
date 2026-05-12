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
    state.active_profile = "LCD-7T Fixture"
    state.status_message = "Workspace ready."
    return state


def _telemetry(*, offset: float = 0.0) -> BridgeTelemetrySnapshot:
    raw_axes = {axis: max(-1.0, min(1.0, ((index - 2) / 5) + offset)) for index, axis in enumerate(AXIS_NAMES)}
    final_axes = {axis: value * 0.65 for axis, value in raw_axes.items()}
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
        active_profile="LCD-7T Fixture",
        rule_summary=RuleStateSummary(active_count=0, blocked_count=0, disabled_count=1),
        output_verification=OutputVerificationState(verified=False, backend_name="vJoy", message="Output proof missing."),
        runtime_frame={"telemetry_proof": "fresh", "input_stale": False, "output_proof": "missing"},
    )


def _text_blob(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    return "\n".join([label.text() for label in widget.findChildren(QLabel)] + [button.text() for button in widget.findChildren(QPushButton)])


def test_lcd_7t_hotas_marker_opens_inline_mapping_editor_and_stages_draft_safely():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    shell.switch_route("mapping.hotas_map")
    hotas = shell.page_widgets["mapping.hotas_map"].widget()

    marker = hotas.findChild(QPushButton, "liquidMappingMarker_axis_yaw")
    marker.click()
    app.processEvents()

    editor = hotas.findChild(QWidget, "liquidMappingInlineEditorCard")
    assert editor is not None
    assert editor.property("mappingEditorOpen") is True
    assert editor.property("selectedControlId") == "axis_yaw"
    assert "Yaw" in _text_blob(editor)
    assert hotas.findChild(QWidget, "liquidMappingAdvancedRouteDetails").property("advancedSecondary") is True

    stage = editor.findChild(QPushButton, "liquidMappingInlineEditorStageButton")
    assert stage is not None
    assert stage.property("actionKind") == "stage_draft"
    before_truth = shell.state.runtime.header_truth_label
    stage.click()
    app.processEvents()
    assert shell.state.saved is False
    assert shell.state.runtime.header_truth_label == before_truth

    hotas = shell.page_widgets["mapping.hotas_map"].widget()
    editor = hotas.findChild(QWidget, "liquidMappingInlineEditorCard")
    assert editor is not None
    close = editor.findChild(QPushButton, "liquidMappingInlineEditorCloseButton")
    close.click()
    app.processEvents()
    assert hotas.findChild(QWidget, "liquidMappingInlineEditorCard") is None


def test_lcd_7t_mapping_routes_are_distinct_stable_and_control_oriented():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    for _index in range(4):
        for route_key in ("mapping.hotas_map", "mapping.route_details", "mapping.advanced_route_tables"):
            shell.switch_route(route_key)
            app.processEvents()
            assert shell.current_route_key == route_key
            assert shell.page_host.currentWidget() is shell.page_widgets[route_key]

    details = shell.page_widgets["mapping.route_details"].widget()
    tables = shell.page_widgets["mapping.advanced_route_tables"].widget()
    assert details.property("routeKey") == "mapping.route_details"
    assert tables.property("routeKey") == "mapping.advanced_route_tables"
    assert details.findChild(QWidget, "liquidMappingFocusedRouteEditor") is not None
    assert details.findChild(QWidget, "liquidMappingFullRouteTable") is None
    assert tables.findChild(QWidget, "liquidMappingFullRouteTable") is not None
    groups = {widget.property("routeGroup") for widget in tables.findChildren(QWidget) if widget.property("mappingRouteGroup") is True}
    assert {"axis", "button", "hat"}.issubset(groups)


def test_lcd_7t_tuning_graphs_are_large_central_and_filtering_reverses():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.models.tuning_command_model import build_tuning_command_model
    from v3_app.liquid.pages.tuning_command_pages import TuningCommandPage

    workspace = create_default_workspace()
    expectations = {
        "tuning.base_tuning": {"Default", "Current tuning"},
        "tuning.combat_profile": {"Default", "Base tuning", "Combat profile"},
    }
    for route_key, labels in expectations.items():
        page = TuningCommandPage(route_key=route_key, state=_state(active_page_id="base_tuning"), workspace=workspace)
        graph = page.findChild(QWidget, "liquidTuningResponseGraph")
        assert graph is not None
        assert graph.minimumHeight() >= 420
        assert set(graph.property("lineLabels")) >= labels
        assert graph.property("primaryGraph") is True

    filtering = TuningCommandPage(route_key="tuning.filtering", state=_state(active_page_id="filtering"), workspace=workspace)
    graph = filtering.findChild(QWidget, "liquidTuningResponseGraph")
    assert graph is not None
    assert graph.minimumHeight() >= 420
    assert set(graph.property("lineLabels")) >= {"Input step", "Filtered output"}
    assert graph.property("stepPattern") == "positive_hold_negative_hold_return"

    model = build_tuning_command_model(route_key="tuning.filtering", workspace=workspace, selected_axis="Roll", state=_state())
    assert model.preview_graph is not None
    filtered_line = next(line for line in model.preview_graph.lines if line.label == "Filtered output")
    input_line = next(line for line in model.preview_graph.lines if line.label == "Input step")
    assert min(y for _x, y in input_line.points) < 0.0
    assert min(y for _x, y in filtered_line.points) < 0.0


def test_lcd_7t_axis_selection_updates_tuning_dependent_sections():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.tuning_command_pages import TuningCommandPage

    page = TuningCommandPage(route_key="tuning.base_tuning", state=_state(active_page_id="base_tuning"), workspace=create_default_workspace())
    before_guidance = _text_blob(page.findChild(QWidget, "liquidTuningGuidance"))
    before_graph_axis = page.findChild(QWidget, "liquidTuningResponseGraph").property("selectedAxis")
    page.select_axis("Throttle")
    after_guidance = _text_blob(page.findChild(QWidget, "liquidTuningGuidance"))
    graph = page.findChild(QWidget, "liquidTuningResponseGraph")
    assert before_guidance != after_guidance
    assert before_graph_axis == "Roll"
    assert graph.property("selectedAxis") == "Throttle"
    assert "Throttle" in _text_blob(page.findChild(QWidget, "liquidTuningLiveSnapshot"))
    assert "Throttle" in _text_blob(page.findChild(QWidget, "liquidTuningAdvancedDetails"))


def test_lcd_7t_effective_response_stack_is_dominant_vertical_chain_with_stage_detail():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    page = AnalysisCommandPage(
        route_key="analysis.effective_response_stack",
        state=_state(active_page_id="effective_response_stack"),
        workspace=create_default_workspace(),
        telemetry=_telemetry(),
    )
    chain = page.findChild(QWidget, "liquidAnalysisResponseStackChain")
    assert chain is not None
    assert chain.property("chainOrientation") == "vertical"
    assert chain.property("dominantVisual") is True
    assert chain.minimumHeight() >= 520
    assert chain.property("chainOrder")[:6] == (
        "Raw Input",
        "Base Tuning",
        "Filtering",
        "Modes / Combat Profile",
        "Conditional Rules",
        "Final Output Intent",
    )
    first_stage = page.findChild(QWidget, "liquidAnalysisStage_raw")
    first_stage.findChild(QPushButton, "liquidAnalysisSelectStageButton_raw").click()
    detail = page.findChild(QWidget, "liquidAnalysisSelectedStageDetailPanel")
    assert detail is not None
    assert detail.property("selectedStageId") == "raw"
    assert "Raw Input" in _text_blob(detail)


def test_lcd_7t_live_monitor_is_large_right_to_left_timeseries_with_overlay_and_bounded_hidden_updates():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    shell.switch_route("analysis.live_monitor")
    monitor = shell.page_widgets["analysis.live_monitor"].widget()
    graph = monitor.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
    assert graph is not None
    assert graph.minimumHeight() >= 420
    assert graph.property("timeSeriesDirection") == "right_to_left"
    assert tuple(graph.property("axisLabels")) == tuple(AXIS_NAMES)

    for index in range(130):
        monitor.update_analysis_snapshot(
            state=shell.state,
            workspace=create_default_workspace(),
            telemetry=_telemetry(offset=index * 0.001),
            selected_axis="Roll",
        )
    graph = monitor.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
    assert int(graph.property("historyLength") or 0) <= int(graph.property("boundedHistoryCapacity"))

    overlay = monitor.findChild(QPushButton, "liquidLiveMonitorOverlayToggle")
    before = bool(graph.property("overlayFinalValues"))
    overlay.click()
    app.processEvents()
    graph = monitor.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
    assert bool(graph.property("overlayFinalValues")) is (not before)
    values = monitor.findChild(QWidget, "liquidAnalysisCurrentNumericValues")
    assert values is not None
    assert "Roll" in _text_blob(values)

    render_count = monitor.render_count
    shell.switch_route("mapping.hotas_map")
    for index in range(30):
        shell.apply_bridge_telemetry(_telemetry(offset=index * 0.002))
    assert monitor.render_count == render_count


def test_lcd_7t_no_checkbox_like_status_glyphs_and_no_runtime_authority_claims():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    for route_key in (
        "preflight.command_readiness",
        "mapping.hotas_map",
        "tuning.base_tuning",
        "analysis.effective_response_stack",
        "analysis.live_monitor",
    ):
        shell.switch_route(route_key)
        page = shell.page_widgets[route_key].widget()
        for marker in page.findChildren(QWidget):
            if marker.property("componentRole") == "StatusLight":
                assert marker.property("indicatorShape") != "checkbox-square"
        text = _text_blob(page).casefold()
        assert "write to vjoy" not in text
        assert "verify output" not in text
        assert "apply live" not in text
