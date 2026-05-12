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
    state.active_profile = "LCD-7U Fixture"
    return state


def _telemetry(*, roll: float = 0.25, yaw: float = -0.55) -> BridgeTelemetrySnapshot:
    raw = {
        "Roll": roll,
        "Pitch": -0.15,
        "Throttle": 0.72,
        "Yaw": yaw,
        "Aux 1": 0.12,
        "Aux 2": -0.28,
    }
    final = {axis: value * 0.70 for axis, value in raw.items()}
    return BridgeTelemetrySnapshot(
        runtime_truth=RuntimeTruth.DETECTED_UNVERIFIED,
        lifecycle_state=BridgeLifecycleState.SIMULATED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        raw_axes=AxisTelemetrySnapshot(raw),
        final_axes=AxisTelemetrySnapshot(final),
        controls=ButtonHatTelemetrySnapshot(
            buttons={button: index in {0, 3, 14} for index, button in enumerate(BUTTON_NAMES)},
            hats={"POV": "Right"},
        ),
        active_modes=ModeStateTelemetrySnapshot(active_mode_names=("Combat",)),
        timestamp=datetime.now(timezone.utc),
        active_profile="LCD-7U Fixture",
        rule_summary=RuleStateSummary(active_count=1, blocked_count=0, disabled_count=1),
        output_verification=OutputVerificationState(
            verified=False,
            backend_name="vJoy",
            message="Output proof missing.",
        ),
        runtime_frame={"telemetry_proof": "fresh", "input_stale": False, "output_proof": "missing"},
    )


def _text(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    return "\n".join([label.text() for label in widget.findChildren(QLabel)] + [button.text() for button in widget.findChildren(QPushButton)])


def test_lcd_7u_tuning_pages_receive_passive_telemetry_and_show_top_axis_selector():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.tuning_command_pages import TuningCommandPage

    page = TuningCommandPage(
        route_key="tuning.base_tuning",
        state=_state(),
        workspace=create_default_workspace(),
        telemetry=_telemetry(roll=0.42),
    )

    selector = page.findChild(QWidget, "liquidTuningTopAxisSelector")
    assert selector is not None
    assert selector.property("topLevelAxisSelector") is True

    graph = page.findChild(QWidget, "liquidTuningResponseGraph")
    assert graph is not None
    assert graph.property("currentValueDots") is True
    assert set(graph.property("markerLabels")) >= {"Current input", "Output intent"}

    snapshot = page.findChild(QWidget, "liquidTuningLiveSnapshot")
    assert "0.42" in _text(snapshot)
    assert "Passive live telemetry" in _text(snapshot)

    page.update_tuning_workspace(
        state=_state(),
        workspace=create_default_workspace(),
        base_workspace=create_default_workspace(),
        selected_axis="Yaw",
        last_edit_result=None,
        telemetry=_telemetry(yaw=-0.61),
    )
    graph = page.findChild(QWidget, "liquidTuningResponseGraph")
    assert graph.property("selectedAxis") == "Yaw"
    assert any(abs(point[0] + 0.61) < 0.02 for point in graph.property("markerPoints"))
    assert "Yaw" in _text(page.findChild(QWidget, "liquidTuningLiveSnapshot"))


def test_lcd_7u_combat_curve_is_monotonic_and_filtering_step_reference_has_corners():
    _app()

    from v3_app.liquid.models.tuning_command_model import build_tuning_command_model

    combat = build_tuning_command_model(
        route_key="tuning.combat_profile",
        workspace=create_default_workspace(),
        selected_axis="Roll",
        state=_state(),
        telemetry=_telemetry(),
    )
    combat_line = next(line for line in combat.preview_graph.lines if line.label == "Combat profile")
    ys = [y for _x, y in combat_line.points]
    assert ys == sorted(ys)

    filtering = build_tuning_command_model(
        route_key="tuning.filtering",
        workspace=create_default_workspace(),
        selected_axis="Roll",
        state=_state(),
        telemetry=_telemetry(),
    )
    input_step = next(line for line in filtering.preview_graph.lines if line.label == "Input step")
    filtered = next(line for line in filtering.preview_graph.lines if line.label == "Filtered output")
    assert len(filtered.points) >= 180
    duplicate_xs = [x for index, (x, _y) in enumerate(input_step.points[1:], start=1) if x == input_step.points[index - 1][0]]
    assert duplicate_xs
    assert any(y < 0 for _x, y in input_step.points)


def test_lcd_7u_live_monitor_dominant_lanes_buttons_hats_and_hidden_update_bounds():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="live_monitor"))
    shell.switch_route("analysis.live_monitor")
    shell.apply_bridge_telemetry(_telemetry(roll=0.33))
    app.processEvents()
    monitor = shell.page_widgets["analysis.live_monitor"].widget()

    graph = monitor.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
    assert graph.minimumHeight() >= 560
    assert graph.property("laneOrientation") == "stacked_vertical"
    assert graph.property("axisLaneCount") == 6
    assert tuple(graph.property("axisLabels")) == tuple(AXIS_NAMES)

    values = monitor.findChild(QWidget, "liquidAnalysisCurrentNumericValues")
    assert "Roll" in _text(values)
    assert "0.33" in _text(values)
    assert "Right" in _text(monitor.findChild(QWidget, "liquidAnalysisControlsDetail"))

    overlay = monitor.findChild(QPushButton, "liquidLiveMonitorOverlayToggle")
    overlay.click()
    app.processEvents()
    assert monitor.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph").property("overlayFinalValues") is True

    render_count = monitor.render_count
    shell.switch_route("mapping.hotas_map")
    for index in range(25):
        shell.apply_bridge_telemetry(_telemetry(roll=index / 100.0))
    assert monitor.render_count == render_count


def test_lcd_7u_hotas_marker_opens_frosted_editor_overlay_without_scroll_jump():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="mapping"))
    shell.switch_route("mapping.hotas_map")
    scroll = shell.page_widgets["mapping.hotas_map"]
    hotas = scroll.widget()
    scroll.verticalScrollBar().setValue(0)

    marker = hotas.findChild(QPushButton, "liquidMappingMarker_axis_yaw")
    marker.click()
    app.processEvents()

    assert scroll.verticalScrollBar().value() == 0
    overlay = hotas.findChild(QWidget, "liquidMappingEditorOverlaySurface")
    scrim = hotas.findChild(QWidget, "liquidMappingEditorFrostedScrim")
    editor = hotas.findChild(QWidget, "liquidMappingInlineEditorCard")
    assert overlay is not None
    assert scrim is not None
    assert scrim.property("frostedEditorOverlay") is True
    assert editor is not None
    assert editor.property("mappingEditorOpen") is True

    close = editor.findChild(QPushButton, "liquidMappingInlineEditorCloseButton")
    close.click()
    app.processEvents()
    assert scroll.verticalScrollBar().value() == 0
    assert hotas.findChild(QWidget, "liquidMappingInlineEditorCard") is None


def test_lcd_7u_profiles_library_route_and_blank_page_guard_exist():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.navigation import DEFAULT_LIQUID_NAVIGATION_MODEL

    route = DEFAULT_LIQUID_NAVIGATION_MODEL.route_by_key("tuning.profiles_library")
    assert route.subpage_display_name == "Profiles Library"

    shell = LiquidCommandShell(state=_state())
    route_keys = [route.route_key for route in DEFAULT_LIQUID_NAVIGATION_MODEL.routes]
    for _round in range(2):
        for route_key in route_keys:
            shell.switch_route(route_key)
            page = shell.page_host.currentWidget()
            assert page is not None
            assert page.widget() is not None
            assert page.widget().findChildren(QWidget)


def test_lcd_7u_visual_qa_scripts_exist():
    capture = PROJECT_ROOT / "scripts" / "capture_liquid_ui_screenshots.py"
    report = PROJECT_ROOT / "scripts" / "build_liquid_visual_report.py"
    assert capture.exists()
    assert report.exists()
