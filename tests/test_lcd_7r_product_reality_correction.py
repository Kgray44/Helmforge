from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from shared_core.models.runtime import AXIS_NAMES, BUTTON_NAMES, InputStatus, OutputStatus, RuntimeMode, RuntimePreflightStatus, RuntimeTruth
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    state.active_profile = "LCD-7R Fixture"
    state.status_message = "Workspace ready."
    return state


def _telemetry(*, offset: float = 0.0) -> BridgeTelemetrySnapshot:
    raw_axes = {axis: max(-1.0, min(1.0, ((index - 2) / 5) + offset)) for index, axis in enumerate(AXIS_NAMES)}
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
        active_profile="LCD-7R Fixture",
        rule_summary=RuleStateSummary(active_count=0, blocked_count=0, disabled_count=1),
        output_verification=OutputVerificationState(verified=False, backend_name="vJoy", message="Output proof missing."),
        runtime_frame={"telemetry_proof": "fresh", "input_stale": False, "output_proof": "missing"},
    )


def _text_blob(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    return "\n".join([label.text() for label in widget.findChildren(QLabel)] + [button.text() for button in widget.findChildren(QPushButton)])


def test_lcd_7r_mapping_route_switching_marker_selection_and_command_actions_are_stable():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    sequence = (
        "mapping.hotas_map",
        "mapping.route_details",
        "mapping.advanced_route_tables",
        "mapping.hotas_map",
        "mapping.route_details",
        "mapping.hotas_map",
    )
    for route_key in sequence:
        shell.switch_route(route_key)
        app.processEvents()
        assert shell.current_route_key == route_key
        assert shell.page_host.currentWidget() is shell.page_widgets[route_key]

    shell.switch_route("mapping.advanced_route_tables")
    app.processEvents()
    advanced = shell.page_widgets["mapping.advanced_route_tables"].widget()
    render_count = advanced.property("mappingEditRenderCount")
    for index in range(12):
        shell.apply_bridge_telemetry(_telemetry(offset=index * 0.001))
        app.processEvents()
    assert shell.current_route_key == "mapping.advanced_route_tables"
    assert shell.page_host.currentWidget() is shell.page_widgets["mapping.advanced_route_tables"]
    assert advanced.property("mappingEditRenderCount") == render_count

    shell.switch_route("mapping.hotas_map")
    app.processEvents()
    hotas = shell.page_widgets["mapping.hotas_map"].widget()
    marker = hotas.findChild(QPushButton, "liquidMappingMarker_axis_yaw")
    assert marker is not None
    marker.click()
    app.processEvents()

    assert shell.current_route_key == "mapping.hotas_map"
    assert hotas.property("selectedControlId") == "axis_yaw"
    assert "Yaw" in _text_blob(hotas.findChild(QWidget, "liquidMappingInspector"))
    assert "Yaw" in _text_blob(hotas.findChild(QWidget, "liquidMappingRouteFlowPanel"))
    assert hotas.findChild(QWidget, "liquidMappingAdvancedRouteDetails").property("advancedSecondary") is True
    assert hotas.findChild(QPushButton, "liquidMappingEditSelectedRouteButton") is not None
    assert hotas.findChild(QPushButton, "liquidMappingCopySelectedRouteButton") is not None
    assert hotas.findChild(QPushButton, "liquidMappingCopySummaryButton") is not None
    reset = hotas.findChild(QPushButton, "liquidMappingResetSelectedRouteButton")
    assert reset is not None
    assert not reset.isEnabled()
    assert "not represented" in reset.toolTip().casefold() or "pending" in reset.toolTip().casefold()

    hotas.findChild(QPushButton, "liquidMappingEditSelectedRouteButton").click()
    app.processEvents()
    assert shell.current_route_key == "mapping.route_details"


def test_lcd_7r_mapping_edit_pages_expose_validate_copy_revert_and_grouped_edit_rows():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.pages.mapping_edit_pages import MappingAdvancedRouteTablesPage, MappingRouteDetailsPage

    details = MappingRouteDetailsPage(state=_state(), workspace=create_default_workspace())
    assert details.findChild(QPushButton, "liquidMappingValidateRouteButton") is not None
    assert details.findChild(QPushButton, "liquidMappingCopyRouteDetailsButton") is not None
    assert details.findChild(QPushButton, "liquidMappingRevertSelectedRouteButton") is not None
    assert details.findChild(QPushButton, "liquidMappingNavigate_mapping_hotas_map") is not None

    valid = details.stage_edit("axis:axis_roll", "output_intent_target", "vJoy SL1(axis8)")
    invalid = details.stage_edit("axis:axis_roll", "output_intent_target", "vJoy INVALID")
    assert valid.valid is True
    assert invalid.valid is False
    assert "Output proof unchanged" in valid.message

    tables = MappingAdvancedRouteTablesPage(state=_state(), workspace=create_default_workspace())
    groups = {widget.property("routeGroup") for widget in tables.findChildren(QWidget) if widget.property("mappingRouteGroup") is True}
    rows = [widget for widget in tables.findChildren(QWidget) if widget.property("mappingEditableRouteRow") is True]
    assert {"axis", "button", "hat"}.issubset(groups)
    assert len(rows) >= 22
    assert tables.findChild(QPushButton, "liquidMappingValidateAllRoutesButton") is not None
    assert tables.findChild(QPushButton, "liquidMappingCopyRouteTableSummaryButton") is not None
    add_route = tables.findChild(QPushButton, "liquidMappingAddRouteButton")
    assert add_route is not None and not add_route.isEnabled()
    assert "not represented" in add_route.toolTip().casefold() or "deferred" in add_route.toolTip().casefold()


def test_lcd_7r_preflight_exposes_safe_command_actions_and_non_checkbox_status_markers():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.pages.preflight_command_page import PreflightCommandPage

    page = PreflightCommandPage(state=_state(active_page_id="preflight"))
    actions = page.findChild(QWidget, "liquidPreflightCommandActions")
    assert actions is not None
    for name in (
        "liquidPreflightOpenSetupButton",
        "liquidPreflightOpenMappingButton",
        "liquidPreflightCopyStatusButton",
        "liquidPreflightCopyChecklistButton",
    ):
        assert page.findChild(QPushButton, name) is not None
    simulation = page.findChild(QPushButton, "liquidPreflightSimulationControlButton")
    assert simulation is not None
    assert not simulation.isEnabled()
    assert "pending" in simulation.toolTip().casefold() or "not available" in simulation.toolTip().casefold()

    status_markers = [widget for widget in page.findChildren(QWidget) if widget.property("componentRole") == "StatusLight"]
    assert status_markers
    assert all(marker.property("indicatorShape") != "checkbox-square" for marker in status_markers)


def test_lcd_7r_tuning_pages_have_prominent_graphs_axis_updates_and_command_actions():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.pages.tuning_command_pages import TuningCommandPage

    expectations = {
        "tuning.base_tuning": ("response_curve", ("Reference", "Current tuning")),
        "tuning.filtering": ("step_response", ("Input step", "Filtered response")),
        "tuning.combat_profile": ("combat_response", ("Reference", "Base tuning", "Combat profile")),
    }
    for route_key, (kind, line_labels) in expectations.items():
        page = TuningCommandPage(route_key=route_key, state=_state(active_page_id="base_tuning"), workspace=create_default_workspace())
        graph = page.findChild(QWidget, "liquidTuningResponseGraph")
        assert graph is not None
        assert graph.property("graphKind") == kind
        assert graph.property("prominentGraph") is True
        assert set(line_labels).issubset(set(graph.property("lineLabels")))
        assert graph.minimumHeight() >= 180
        assert page.findChild(QPushButton, "liquidTuningCopyParametersButton") is not None
        assert page.findChild(QPushButton, "liquidTuningCopyPreviewButton") is not None
        assert page.findChild(QPushButton, "liquidTuningResetAxisButton") is not None
        assert page.findChild(QPushButton, "liquidTuningRevertAxisButton") is not None
        before = _text_blob(page.findChild(QWidget, "liquidTuningGuidance"))
        page.select_axis("Yaw")
        after = _text_blob(page.findChild(QWidget, "liquidTuningGuidance"))
        updated_graph = page.findChild(QWidget, "liquidTuningResponseGraph")
        assert page.property("selectedAxis") == "Yaw"
        assert updated_graph.property("selectedAxis") == "Yaw"
        assert before != after
        assert "Yaw" in _text_blob(page.findChild(QWidget, "liquidTuningLiveSnapshot"))
        assert "Yaw" in _text_blob(page.findChild(QWidget, "liquidTuningAdvancedDetails"))


def test_lcd_7r_conditional_rules_has_real_system_structure_and_truthful_deferred_actions():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.pages.tuning_command_pages import TuningCommandPage

    page = TuningCommandPage(route_key="tuning.conditional_rules", state=_state(active_page_id="conditional_rules"), workspace=create_default_workspace())
    assert page.findChild(QWidget, "liquidTuningRuleStatusHero") is not None
    assert page.findChild(QWidget, "liquidTuningRuleList") is not None
    assert page.findChild(QWidget, "liquidTuningSelectedRuleInspector") is not None
    assert page.findChild(QWidget, "liquidTuningRuleValidationPanel") is not None
    assert page.findChild(QWidget, "liquidTuningRuleActionCluster") is not None
    for name in ("liquidTuningAddRuleButton", "liquidTuningEditRuleButton", "liquidTuningEnableRuleButton"):
        button = page.findChild(QPushButton, name)
        assert button is not None
        assert not button.isEnabled()
        assert button.toolTip()


def test_lcd_7r_effective_response_stack_is_visual_chain_with_stage_actions():
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
    connectors = [widget for widget in page.findChildren(QWidget) if widget.property("analysisChainConnector") is True]
    stages = [widget for widget in page.findChildren(QWidget) if widget.property("analysisPipelineStage") is True]
    assert chain is not None
    assert chain.property("chainOrder") == (
        "Raw Input",
        "Base Tuning",
        "Filtering",
        "Modes / Combat Profile",
        "Conditional Rules",
        "Final Output Intent",
    )
    assert len(connectors) >= 5
    assert len(stages) >= 6
    assert page.findChild(QPushButton, "liquidAnalysisCopyStageButton") is not None
    assert page.findChild(QPushButton, "liquidAnalysisCopyStackButton") is not None
    assert page.findChild(QPushButton, "liquidAnalysisOpenLiveMonitorButton") is not None
    assert page.findChild(QPushButton, "liquidAnalysisOpenFilteringButton") is not None


def test_lcd_7r_live_monitor_has_bounded_right_to_left_time_series_and_safe_actions():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="live_monitor"))
    shell.switch_route("analysis.live_monitor")
    app.processEvents()
    page = shell.page_widgets["analysis.live_monitor"].widget()
    graph = page.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
    assert graph is not None
    assert graph.property("timeSeriesDirection") == "right_to_left"
    assert graph.property("boundedHistoryCapacity") == 120
    assert graph.property("overlayFinalValues") is False

    for index in range(10):
        shell.apply_bridge_telemetry(_telemetry(offset=index * 0.01))
        app.processEvents()
    assert graph.property("historyLength") <= graph.property("boundedHistoryCapacity")
    assert graph.property("historyLength") > 0

    overlay = page.findChild(QPushButton, "liquidLiveMonitorOverlayToggle")
    clear = page.findChild(QPushButton, "liquidLiveMonitorClearHistoryButton")
    assert overlay is not None
    assert clear is not None
    overlay.click()
    app.processEvents()
    assert page.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph").property("overlayFinalValues") is True
    clear.click()
    app.processEvents()
    assert page.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph").property("historyLength") == 0
    assert page.findChild(QPushButton, "liquidLiveMonitorCopySampleButton") is not None
    assert page.findChild(QPushButton, "liquidLiveMonitorCopyTelemetryButton") is not None
    assert page.findChild(QPushButton, "liquidLiveMonitorOpenStackButton") is not None


def test_lcd_7r_hidden_live_monitor_does_not_consume_telemetry_bursts():
    app = _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="base_tuning"))
    shell.switch_route("tuning.base_tuning")
    live_page = shell.page_widgets["analysis.live_monitor"].widget()
    initial_history = live_page.property("liveMonitorHistoryLength") or 0
    initial_renders = live_page.render_count
    for index in range(12):
        shell.apply_bridge_telemetry(_telemetry(offset=index * 0.01))
        app.processEvents()
    assert shell.current_route_key == "tuning.base_tuning"
    assert (live_page.property("liveMonitorHistoryLength") or 0) == initial_history
    assert live_page.render_count == initial_renders


def test_lcd_7r_command_buttons_do_not_claim_runtime_authority_or_output_verification():
    app = _app()

    from PySide6.QtWidgets import QPushButton
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    for route_key in (
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
    ):
        shell.switch_route(route_key)
        app.processEvents()
        page = shell.page_widgets[route_key].widget()
        action_buttons = [button for button in page.findChildren(QPushButton) if button.property("uiRole") == "liquidActionButton"]
        assert action_buttons, route_key
        assert any(button.isEnabled() for button in action_buttons), route_key
        for button in action_buttons:
            combined = " ".join([button.text(), button.toolTip(), button.statusTip(), button.accessibleDescription()]).casefold()
            assert "write to vjoy" not in combined
            assert "output verified" not in combined
            assert "start bridge" not in combined
            assert "stop bridge" not in combined
            if not button.isEnabled():
                assert button.toolTip() or button.statusTip() or button.accessibleDescription()


def test_lcd_7r_report_documents_product_reality_and_command_actions():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-7r-product-reality-correction-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-7R Product Reality Correction",
        "Mapping editing fixes",
        "Mapping route stability fixes",
        "visual map selection behavior fix",
        "Preflight action buttons added",
        "square glyph replacement",
        "Base Tuning graph behavior",
        "Filtering step-response graph behavior",
        "Combat Profile graph behavior",
        "axis selection dependency update fix",
        "Conditional Rules system completion status",
        "Effective Response Stack chain redesign",
        "Live Monitor time-series redesign",
        "route/page freeze protections",
        "Command Actions Added",
        "enabled actions",
        "disabled/deferred actions",
        "workspace draft",
        "navigation-only",
        "copy/export-only",
        "runtime truth preservation statement",
        "no Recorder/Helm page was rebuilt",
        "no Support/Diagnostics page was rebuilt",
        "no radial menu behavior was added",
        "no animations/page transitions/real blur were added",
        "no hardware polling was added",
        "no vJoy/output behavior was changed",
        "no output verification behavior was changed",
        "no Bridge lifecycle management was added",
        "no cloud AI/LLM behavior was added",
        "no auto-save was added",
    ):
        assert required in text
