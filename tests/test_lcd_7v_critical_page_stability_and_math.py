from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

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


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _state(*, active_page_id: str = "effective_response_stack"):
    from shared_core.models.runtime import InputDeviceDetection, OutputBackendDetection
    from v3_app.services.app_state import AppState

    runtime_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )
    state = AppState.from_runtime_status(runtime_status, active_page_id=active_page_id)
    state.active_profile = "LCD-7V Fixture"
    return state


def _telemetry(*, roll: float = 0.25, yaw: float = -0.61) -> BridgeTelemetrySnapshot:
    raw = {
        "Roll": roll,
        "Pitch": -0.12,
        "Throttle": 0.73,
        "Yaw": yaw,
        "Aux 1": 0.18,
        "Aux 2": -0.22,
    }
    final = {axis: value * 0.72 for axis, value in raw.items()}
    return BridgeTelemetrySnapshot(
        runtime_truth=RuntimeTruth.DETECTED_UNVERIFIED,
        lifecycle_state=BridgeLifecycleState.SIMULATED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        raw_axes=AxisTelemetrySnapshot(raw),
        final_axes=AxisTelemetrySnapshot(final),
        controls=ButtonHatTelemetrySnapshot(
            buttons={button: index in {0, 7, 14} for index, button in enumerate(BUTTON_NAMES)},
            hats={"POV": "Right"},
        ),
        active_modes=ModeStateTelemetrySnapshot(active_mode_names=("Combat",)),
        timestamp=datetime.now(timezone.utc),
        active_profile="LCD-7V Fixture",
        rule_summary=RuleStateSummary(active_count=1, blocked_count=0, disabled_count=1),
        output_verification=OutputVerificationState(verified=False, backend_name="vJoy", message="Output proof missing."),
        runtime_frame={"telemetry_proof": "fresh", "input_stale": False, "output_proof": "missing"},
    )


def _text(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    return "\n".join([label.text() for label in widget.findChildren(QLabel)] + [button.text() for button in widget.findChildren(QPushButton)])


def _interpolate(points: tuple[tuple[float, float], ...], x: float) -> float:
    ordered = tuple(sorted(points))
    if x <= ordered[0][0]:
        return ordered[0][1]
    if x >= ordered[-1][0]:
        return ordered[-1][1]
    for (x0, y0), (x1, y1) in zip(ordered, ordered[1:]):
        if x0 <= x <= x1:
            ratio = (x - x0) / max(0.000001, x1 - x0)
            return y0 + ratio * (y1 - y0)
    raise AssertionError(f"x={x} was not inside graph line")


def test_lcd_7v_effective_response_stack_axis_selection_is_single_and_updates_all_sections():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    page = AnalysisCommandPage(
        route_key="analysis.effective_response_stack",
        state=_state(),
        workspace=create_default_workspace(),
        telemetry=_telemetry(),
    )
    page.select_axis("Yaw")
    app.processEvents()

    assert page.property("selectedAxis") == "Yaw"
    selectors = [widget for widget in page.findChildren(QWidget) if widget.property("componentRole") == "AxisSelectorPills"]
    assert selectors
    for selector in selectors:
        assert selector.property("selectedAxis") == "Yaw"
        active = [button for button in selector.findChildren(QPushButton) if button.property("active") is True or button.isChecked()]
        assert [button.text() for button in active] == ["Yaw"]

    assert "Yaw" in _text(page.findChild(QWidget, "liquidAnalysisLiveSnapshot"))
    assert "Selected axis key" in _text(page.findChild(QWidget, "liquidAnalysisAdvancedDetails"))
    assert "Yaw" in _text(page.findChild(QWidget, "liquidAnalysisAdvancedDetails"))
    assert "Yaw" in _text(page.findChild(QWidget, "liquidAnalysisStageDetails"))


def test_lcd_7v_effective_response_stack_sections_are_non_empty_and_burst_stable():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="effective_response_stack"))
    shell.switch_route("analysis.effective_response_stack")
    page = shell.page_widgets["analysis.effective_response_stack"].widget()
    page.select_axis("Yaw")
    render_count = page.render_count
    chain = page.findChild(QWidget, "liquidAnalysisResponseStackChain")
    stages = [widget for widget in page.findChildren(QWidget) if widget.property("analysisPipelineStage") is True]

    assert chain is not None
    assert stages
    for stage in stages:
        blob = _text(stage).strip()
        assert blob
        assert "Raw Input" in blob or "Base Tuning" in blob or "Filtering" in blob or "Modes / Combat Profile" in blob or "Conditional Rules" in blob or "Final Output Intent" in blob

    for index in range(24):
        shell.apply_bridge_telemetry(_telemetry(roll=0.15 + index * 0.01, yaw=-0.5 + index * 0.005))
        app.processEvents()
        assert shell.page_host.currentWidget() is shell.page_widgets["analysis.effective_response_stack"]
        assert page.findChild(QWidget, "liquidAnalysisResponseStackChain") is chain
        assert page.property("selectedAxis") == "Yaw"

    assert page.render_count == render_count


def test_lcd_7v_filtering_step_response_has_vertical_edges_and_high_resolution_contract():
    _app()

    from v3_app.liquid.models.tuning_command_model import build_tuning_command_model
    from v3_app.liquid.pages.tuning_command_pages import TuningCommandPage
    from PySide6.QtWidgets import QWidget

    model = build_tuning_command_model(
        route_key="tuning.filtering",
        workspace=create_default_workspace(),
        selected_axis="Roll",
        state=_state(active_page_id="filtering"),
        telemetry=_telemetry(),
    )
    input_step = next(line for line in model.preview_graph.lines if line.label == "Input step")
    filtered = next(line for line in model.preview_graph.lines if line.label == "Filtered output")
    duplicate_edges = [
        index
        for index, (point, previous) in enumerate(zip(input_step.points[1:], input_step.points), start=1)
        if point[0] == previous[0] and point[1] != previous[1]
    ]

    assert duplicate_edges
    assert len(filtered.points) >= 360
    assert len(filtered.points) > len(input_step.points) * 30
    assert any(y > 0.75 for _x, y in filtered.points)
    assert any(y < -0.55 for _x, y in filtered.points)

    page = TuningCommandPage(route_key="tuning.filtering", state=_state(active_page_id="filtering"), workspace=create_default_workspace())
    graph = page.findChild(QWidget, "liquidTuningResponseGraph")
    assert graph.property("stepResponseDetail") == "high_resolution_step_response"


def test_lcd_7v_combat_curve_is_monotonic_centered_and_marker_aligned():
    _app()

    from v3_app.liquid.models.tuning_command_model import build_tuning_command_model

    model = build_tuning_command_model(
        route_key="tuning.combat_profile",
        workspace=create_default_workspace(),
        selected_axis="Roll",
        state=_state(active_page_id="combat_profile"),
        telemetry=_telemetry(roll=0.37),
    )
    combat_line = next(line for line in model.preview_graph.lines if line.label == "Combat profile")
    base_line = next(line for line in model.preview_graph.lines if line.label == "Base tuning")
    default_line = next(line for line in model.preview_graph.lines if line.label == "Default")
    combat_points = combat_line.points
    combat_ys = [y for _x, y in combat_points]
    assert combat_ys == sorted(combat_ys)
    assert all(y <= 0.0001 for x, y in combat_points if x < -0.05)
    assert all(y >= -0.0001 for x, y in combat_points if x > 0.05)
    assert all(abs(x) <= 0.08 for x, y in combat_points if abs(y) <= 0.0001)

    markers = {marker.label: marker.point for marker in model.preview_graph.markers}
    assert abs(markers["Current input"][1] - _interpolate(default_line.points, markers["Current input"][0])) < 0.001
    assert abs(markers["Base tuning current"][1] - _interpolate(base_line.points, markers["Base tuning current"][0])) < 0.015
    assert abs(markers["Combat profile current"][1] - _interpolate(combat_line.points, markers["Combat profile current"][0])) < 0.015


def test_lcd_7v_profiles_library_route_is_non_empty_and_stable():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="profiles_library"))
    sequence = ("tuning.base_tuning", "tuning.profiles_library", "tuning.filtering", "tuning.profiles_library") * 3
    for route_key in sequence:
        shell.switch_route(route_key)
        app.processEvents()
        assert shell.page_host.currentWidget() is shell.page_widgets[route_key]
        widget = shell.page_host.currentWidget().widget()
        assert widget is not None
        assert widget.findChildren(QWidget)

    page = shell.page_widgets["tuning.profiles_library"].widget()
    render_count = page.render_count
    text = _text(page)
    assert "Active profile" in text
    assert "Base tuning axes" in text
    assert page.findChild(QWidget, "liquidTuningProfilesActionCluster") is not None
    assert page.findChild(QPushButton, "liquidTuningProfilesCopySummaryButton") is not None
    for name in ("liquidTuningProfilesImportButton", "liquidTuningProfilesExportButton", "liquidTuningProfilesMutateButton"):
        button = page.findChild(QPushButton, name)
        assert button is not None
        assert not button.isEnabled()
        assert button.toolTip()

    for index in range(12):
        shell.apply_bridge_telemetry(_telemetry(roll=0.2 + index * 0.01))
        app.processEvents()
        assert shell.page_host.currentWidget() is shell.page_widgets["tuning.profiles_library"]
    assert page.render_count == render_count


def test_lcd_7v_hotas_map_height_and_scroll_are_stable_around_editor_overlay():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="mapping"))
    shell.switch_route("mapping.hotas_map")
    scroll = shell.page_widgets["mapping.hotas_map"]
    hotas = scroll.widget()
    surface = hotas.findChild(QWidget, "liquidMappingEditorOverlaySurface")
    before_min_height = surface.minimumHeight()
    before_height = surface.height()
    scroll.verticalScrollBar().setValue(24)
    before_scroll = scroll.verticalScrollBar().value()

    marker = hotas.findChild(QPushButton, "liquidMappingMarker_axis_yaw")
    marker.click()
    app.processEvents()

    opened_surface = hotas.findChild(QWidget, "liquidMappingEditorOverlaySurface")
    assert opened_surface.minimumHeight() == before_min_height
    assert abs(opened_surface.height() - before_height) <= 2
    assert scroll.verticalScrollBar().value() == before_scroll

    editor = hotas.findChild(QWidget, "liquidMappingInlineEditorCard")
    editor.findChild(QPushButton, "liquidMappingInlineEditorCloseButton").click()
    app.processEvents()

    closed_surface = hotas.findChild(QWidget, "liquidMappingEditorOverlaySurface")
    assert closed_surface.minimumHeight() == before_min_height
    assert scroll.verticalScrollBar().value() == before_scroll


def test_lcd_7v_live_monitor_idle_and_identical_frames_do_not_rebuild_or_duplicate_history():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="live_monitor"))
    shell.switch_route("analysis.live_monitor")
    page = shell.page_widgets["analysis.live_monitor"].widget()
    graph = page.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
    render_count = page.render_count

    for _ in range(40):
        app.processEvents()
    assert page.render_count == render_count
    assert graph.property("historyLength") == 0

    telemetry = _telemetry(roll=0.22, yaw=-0.44)
    for _ in range(30):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()
    assert page.render_count == render_count
    assert graph.property("historyLength") <= 1

    overlay = page.findChild(QPushButton, "liquidLiveMonitorOverlayToggle")
    overlay.click()
    app.processEvents()
    assert page.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph") is graph
    assert graph.property("overlayFinalValues") is True

    shell.switch_route("mapping.hotas_map")
    hidden_render_count = page.render_count
    for index in range(20):
        shell.apply_bridge_telemetry(_telemetry(roll=0.1 + index * 0.01))
    assert page.render_count == hidden_render_count


def test_lcd_7v_route_switching_and_factory_error_fallback_never_blank(monkeypatch):
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid import app_shell
    from v3_app.liquid.navigation import DEFAULT_LIQUID_NAVIGATION_MODEL
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    route_keys = [route.route_key for route in DEFAULT_LIQUID_NAVIGATION_MODEL.routes]
    for _round in range(2):
        for route_key in route_keys:
            shell.switch_route(route_key)
            app.processEvents()
            current = shell.page_host.currentWidget()
            assert current is shell.page_widgets[route_key]
            assert current.widget() is not None
            assert current.widget().findChildren(QWidget)

    original_factory = app_shell.LIQUID_ROUTE_PAGE_FACTORIES["support.help_docs"]

    def broken_factory():
        raise RuntimeError("forced LCD-7V fallback")

    monkeypatch.setitem(app_shell.LIQUID_ROUTE_PAGE_FACTORIES, "support.help_docs", broken_factory)
    fallback_shell = LiquidCommandShell(state=_state())
    monkeypatch.setitem(app_shell.LIQUID_ROUTE_PAGE_FACTORIES, "support.help_docs", original_factory)
    fallback_shell.switch_route("support.help_docs")
    fallback = fallback_shell.page_host.currentWidget().widget()
    assert fallback.objectName() == "liquidRouteErrorFallback"
    assert fallback.property("routeErrorFallback") is True


def test_lcd_7v_visual_scripts_support_lcd_7v_phase():
    capture = PROJECT_ROOT / "scripts" / "capture_liquid_ui_screenshots.py"
    report = PROJECT_ROOT / "scripts" / "build_liquid_visual_report.py"
    assert capture.exists()
    assert report.exists()
    assert "lcd-7v" in capture.read_text(encoding="utf-8")
    assert "--phase" in report.read_text(encoding="utf-8")
