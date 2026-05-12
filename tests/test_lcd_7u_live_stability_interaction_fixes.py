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


def _state(*, active_page_id: str = "base_tuning"):
    from shared_core.models.runtime import InputDeviceDetection, OutputBackendDetection
    from v3_app.services.app_state import AppState

    runtime_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )
    state = AppState.from_runtime_status(runtime_status, active_page_id=active_page_id)
    state.active_profile = "LCD-7U Stability Fixture"
    return state


def _telemetry(*, roll: float = 0.42, yaw: float = -0.57, final_scale: float = 0.23) -> BridgeTelemetrySnapshot:
    raw = {
        "Roll": roll,
        "Pitch": -0.14,
        "Throttle": 0.68,
        "Yaw": yaw,
        "Aux 1": 0.19,
        "Aux 2": -0.31,
    }
    final = {axis: max(-1.0, min(1.0, value * final_scale)) for axis, value in raw.items()}
    return BridgeTelemetrySnapshot(
        runtime_truth=RuntimeTruth.DETECTED_UNVERIFIED,
        lifecycle_state=BridgeLifecycleState.SIMULATED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        raw_axes=AxisTelemetrySnapshot(raw),
        final_axes=AxisTelemetrySnapshot(final),
        controls=ButtonHatTelemetrySnapshot(
            buttons={button: index in {0, 4, 14} for index, button in enumerate(BUTTON_NAMES)},
            hats={"POV": "Right"},
        ),
        active_modes=ModeStateTelemetrySnapshot(active_mode_names=("Combat",)),
        timestamp=datetime.now(timezone.utc),
        active_profile="LCD-7U Stability Fixture",
        rule_summary=RuleStateSummary(active_count=1, blocked_count=0, disabled_count=1),
        output_verification=OutputVerificationState(verified=False, backend_name="vJoy", message="Output proof missing."),
        runtime_frame={"telemetry_proof": "fresh", "input_stale": False, "output_proof": "missing"},
    )


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


def _marker(markers, label: str) -> tuple[float, float]:
    for marker in markers:
        if marker.label == label:
            return marker.point
    raise AssertionError(f"Missing marker {label}")


def _line(lines, label: str):
    for line in lines:
        if line.label == label:
            return line
    raise AssertionError(f"Missing line {label}")


def test_lcd_7u_base_tuning_output_intent_marker_lies_on_current_tuning_curve():
    _app()

    from v3_app.liquid.models.tuning_command_model import build_tuning_command_model

    model = build_tuning_command_model(
        route_key="tuning.base_tuning",
        workspace=create_default_workspace(),
        selected_axis="Roll",
        state=_state(),
        telemetry=_telemetry(roll=0.42, final_scale=0.05),
    )
    graph = model.preview_graph
    current_line = _line(graph.lines, "Current tuning")
    marker_x, marker_y = _marker(graph.markers, "Output intent")

    assert abs(marker_y - _interpolate(current_line.points, marker_x)) < 0.015
    assert "Output proof" not in graph.title


def test_lcd_7u_combat_markers_lie_on_their_displayed_curves():
    _app()

    from v3_app.liquid.models.tuning_command_model import build_tuning_command_model

    model = build_tuning_command_model(
        route_key="tuning.combat_profile",
        workspace=create_default_workspace(),
        selected_axis="Roll",
        state=_state(),
        telemetry=_telemetry(roll=0.42, final_scale=0.05),
    )
    graph = model.preview_graph
    current_x, current_y = _marker(graph.markers, "Current input")
    base_x, base_y = _marker(graph.markers, "Base tuning current")
    combat_x, combat_y = _marker(graph.markers, "Combat profile current")

    assert abs(current_y - _interpolate(_line(graph.lines, "Default").points, current_x)) < 0.001
    assert abs(base_y - _interpolate(_line(graph.lines, "Base tuning").points, base_x)) < 0.015
    assert abs(combat_y - _interpolate(_line(graph.lines, "Combat profile").points, combat_x)) < 0.015


def test_lcd_7u_telemetry_burst_does_not_blank_or_full_rebuild_tuning_pages():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    for route_key in ("tuning.base_tuning", "tuning.filtering", "tuning.combat_profile"):
        shell.switch_route(route_key)
        app.processEvents()
        page = shell.page_widgets[route_key].widget()
        assert hasattr(page, "render_count")
        initial_render_count = page.render_count
        graph = page.findChild(QWidget, "liquidTuningResponseGraph")

        for index in range(18):
            shell.apply_bridge_telemetry(_telemetry(roll=0.1 + index * 0.02, yaw=-0.4 + index * 0.01))
            app.processEvents()
            assert shell.page_host.currentWidget() is shell.page_widgets[route_key]
            assert shell.page_host.currentWidget().widget() is page
            assert page.findChild(QWidget, "liquidTuningResponseGraph") is graph
            assert page.findChildren(QWidget)

        assert page.render_count == initial_render_count


def test_lcd_7u_effective_response_stack_and_live_monitor_update_without_blanking():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="effective_response_stack"))
    shell.switch_route("analysis.effective_response_stack")
    stack_page = shell.page_widgets["analysis.effective_response_stack"].widget()
    stack_render_count = stack_page.render_count
    chain = stack_page.findChild(QWidget, "liquidAnalysisResponseStackChain")

    for index in range(18):
        shell.apply_bridge_telemetry(_telemetry(roll=0.12 + index * 0.02))
        app.processEvents()
        assert shell.page_host.currentWidget() is shell.page_widgets["analysis.effective_response_stack"]
        assert stack_page.findChild(QWidget, "liquidAnalysisResponseStackChain") is chain
        assert stack_page.findChildren(QWidget)

    assert stack_page.render_count == stack_render_count

    shell.switch_route("analysis.live_monitor")
    live_page = shell.page_widgets["analysis.live_monitor"].widget()
    live_render_count = live_page.render_count
    graph = live_page.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
    for index in range(24):
        shell.apply_bridge_telemetry(_telemetry(roll=-0.2 + index * 0.03))
        app.processEvents()
        assert shell.page_host.currentWidget() is shell.page_widgets["analysis.live_monitor"]
        assert live_page.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph") is graph
        assert graph.property("historyLength") <= graph.property("boundedHistoryCapacity")

    assert live_page.render_count == live_render_count


def test_lcd_7u_mapping_marker_and_close_preserve_scroll_position():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="mapping"))
    shell.switch_route("mapping.hotas_map")
    scroll = shell.page_widgets["mapping.hotas_map"]
    hotas = scroll.widget()
    scroll.verticalScrollBar().setValue(32)
    starting_scroll = scroll.verticalScrollBar().value()

    marker = hotas.findChild(QPushButton, "liquidMappingMarker_axis_yaw")
    marker.click()
    app.processEvents()

    assert scroll.verticalScrollBar().value() == starting_scroll
    editor = hotas.findChild(QWidget, "liquidMappingInlineEditorCard")
    assert editor is not None
    assert editor.property("mappingEditorOpen") is True

    editor.findChild(QPushButton, "liquidMappingInlineEditorCloseButton").click()
    app.processEvents()
    assert scroll.verticalScrollBar().value() == starting_scroll
    assert hotas.findChild(QWidget, "liquidMappingInlineEditorCard") is None


def test_lcd_7u_mapping_route_switching_and_factory_error_fallback_are_stable(monkeypatch):
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid import app_shell
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="mapping"))
    sequence = ("mapping.hotas_map", "mapping.route_details", "mapping.advanced_route_tables", "mapping.hotas_map") * 3
    for route_key in sequence:
        shell.switch_route(route_key)
        app.processEvents()
        assert shell.page_host.currentWidget() is shell.page_widgets[route_key]
        assert shell.page_host.currentWidget().widget().findChildren(QWidget)

    original_factory = app_shell.LIQUID_ROUTE_PAGE_FACTORIES["support.help_docs"]

    def broken_factory():
        raise RuntimeError("forced LCD-7U fallback")

    monkeypatch.setitem(app_shell.LIQUID_ROUTE_PAGE_FACTORIES, "support.help_docs", broken_factory)
    fallback_shell = LiquidCommandShell(state=_state())
    monkeypatch.setitem(app_shell.LIQUID_ROUTE_PAGE_FACTORIES, "support.help_docs", original_factory)
    fallback_shell.switch_route("support.help_docs")
    app.processEvents()
    fallback = fallback_shell.page_host.currentWidget().widget()
    assert fallback.objectName() == "liquidRouteErrorFallback"
    assert fallback.property("routeErrorFallback") is True


def test_lcd_7u_visual_qa_scripts_support_lcd_7u_and_editor_overlay_capture():
    capture = PROJECT_ROOT / "scripts" / "capture_liquid_ui_screenshots.py"
    report = PROJECT_ROOT / "scripts" / "build_liquid_visual_report.py"
    assert capture.exists()
    assert report.exists()
    capture_text = capture.read_text(encoding="utf-8")
    report_text = report.read_text(encoding="utf-8")
    assert "lcd-7u" in capture_text
    assert "mapping-editor-overlay-open.png" in capture_text
    assert "--phase" in report_text
