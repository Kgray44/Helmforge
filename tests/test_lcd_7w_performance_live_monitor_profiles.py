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
    state.active_profile = "LCD-7W Fixture"
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
        active_profile="LCD-7W Fixture",
        rule_summary=RuleStateSummary(active_count=1, blocked_count=0, disabled_count=1),
        output_verification=OutputVerificationState(verified=False, backend_name="vJoy", message="Output proof missing."),
        runtime_frame={"telemetry_proof": "fresh", "input_stale": False, "output_proof": "missing"},
    )


def _text(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    if widget is None:
        return ""
    return "\n".join([label.text() for label in widget.findChildren(QLabel)] + [button.text() for button in widget.findChildren(QPushButton)])


def _tree_texts(tree) -> tuple[str, ...]:
    labels: list[str] = []
    for category_index in range(tree.topLevelItemCount()):
        category = tree.topLevelItem(category_index)
        labels.append(category.text(0))
        for child_index in range(category.childCount()):
            labels.append(category.child(child_index).text(0))
    return tuple(labels)


def _assert_page_not_blank(shell, route_key: str) -> None:
    from PySide6.QtWidgets import QWidget

    current = shell.page_host.currentWidget()
    assert current is shell.page_widgets[route_key]
    assert current.widget() is not None
    assert current.widget().findChildren(QWidget)


def test_lcd_7w_effective_response_stack_is_lightweight_non_empty_and_axis_updates():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="effective_response_stack"))
    shell.switch_route("analysis.effective_response_stack")
    shell.apply_bridge_telemetry(_telemetry())
    app.processEvents()
    page = shell.page_widgets["analysis.effective_response_stack"].widget()
    chain = page.findChild(QWidget, "liquidAnalysisResponseStackChain")

    assert chain is not None
    assert chain.property("chainImplementation") == "cached_lightweight_stage_widgets"
    assert tuple(chain.property("chainOrder"))[:6] == (
        "Raw Input",
        "Base Tuning",
        "Filtering",
        "Modes / Combat Profile",
        "Conditional Rules",
        "Final Output Intent",
    )

    stage_widgets = [stage for stage in chain.findChildren(QWidget) if stage.property("analysisPipelineStage") is True]
    assert len(stage_widgets) >= 6
    assert all(_text(stage).strip() for stage in stage_widgets)

    start_renders = page.render_count
    for axis_name in ("Yaw", "Throttle"):
        page.select_axis(axis_name)
        app.processEvents()
        assert page.property("selectedAxis") == axis_name
        assert axis_name in _text(page.findChild(QWidget, "liquidAnalysisStageDetails"))
        assert axis_name in _text(page.findChild(QWidget, "liquidAnalysisAdvancedDetails"))
        selectors = [widget for widget in page.findChildren(QWidget) if widget.property("componentRole") == "AxisSelectorPills"]
        assert selectors
        for selector in selectors:
            active = [button.text() for button in selector.findChildren(QPushButton) if button.isChecked() or button.property("active") is True]
            assert active == [axis_name]

    assert page.render_count <= start_renders + 2

    burst_start = page.render_count
    for index in range(30):
        shell.apply_bridge_telemetry(_telemetry(roll=0.1 + index * 0.01, yaw=-0.5 + index * 0.004))
        app.processEvents()
        _assert_page_not_blank(shell, "analysis.effective_response_stack")
        assert shell.page_widgets["analysis.effective_response_stack"].widget() is page
    assert page.render_count == burst_start


def test_lcd_7w_live_monitor_stationary_trace_advances_flatly_and_hidden_page_stops():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="live_monitor"))
    shell.switch_route("analysis.live_monitor")
    page = shell.page_widgets["analysis.live_monitor"].widget()
    graph = page.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph")
    render_count = page.render_count

    for _ in range(8):
        assert page.advance_live_monitor_display_sample() is False
        app.processEvents()
    assert page.render_count == render_count
    assert int(graph.property("historyLength") or 0) == 0

    constant = _telemetry(roll=0.42, yaw=-0.42)
    shell.apply_bridge_telemetry(constant)
    app.processEvents()
    start_history = int(graph.property("historyLength") or 0)
    for _ in range(12):
        assert page.advance_live_monitor_display_sample() is True
        app.processEvents()

    assert page.render_count == render_count
    assert page.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph") is graph
    assert int(graph.property("historyLength") or 0) > start_history
    assert int(graph.property("historyLength") or 0) <= int(graph.property("boundedHistoryCapacity"))
    roll_samples = tuple(page.axis_history_for_test("Roll"))
    assert len(roll_samples) >= 8
    assert {sample[0] for sample in roll_samples[-8:]} == {0.42}

    overlay = page.findChild(QPushButton, "liquidLiveMonitorOverlayToggle")
    overlay.click()
    app.processEvents()
    assert page.findChild(QWidget, "liquidAnalysisLiveTimeSeriesGraph") is graph
    assert graph.property("overlayFinalValues") is True

    controls = page.findChild(QWidget, "liquidAnalysisControlsDetail")
    assert "B1" in _text(controls)
    assert "Right" in _text(controls)

    shell.switch_route("mapping.hotas_map")
    hidden_history = int(graph.property("historyLength") or 0)
    for _ in range(10):
        assert page.advance_live_monitor_display_sample() is False
        app.processEvents()
    assert int(graph.property("historyLength") or 0) == hidden_history


def test_lcd_7w_profiles_library_has_tree_presets_preview_and_truthful_actions():
    app = _app()

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QPushButton, QTreeWidget, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="profiles_library"))
    shell.switch_route("tuning.profiles_library")
    app.processEvents()
    page = shell.page_widgets["tuning.profiles_library"].widget()

    tree = page.findChild(QTreeWidget, "liquidTuningProfilesPresetTree")
    assert tree is not None
    assert tree.property("profilesPresetTree") is True
    tree_text = _tree_texts(tree)
    for expected in (
        "Active Workspace",
        "Current Workspace",
        "Built-in Presets",
        "Balanced Default",
        "Precision Aim",
        "Smooth Flight",
        "Combat Response",
        "Imported Profiles",
        "Empty / import pending",
    ):
        assert expected in tree_text

    combat_item = None
    for category_index in range(tree.topLevelItemCount()):
        category = tree.topLevelItem(category_index)
        for child_index in range(category.childCount()):
            child = category.child(child_index)
            if child.text(0) == "Combat Response":
                combat_item = child
    assert combat_item is not None
    tree.setCurrentItem(combat_item)
    app.processEvents()

    preview = page.findChild(QWidget, "liquidTuningProfilesPresetPreview")
    assert preview is not None
    assert preview.property("selectedPresetName") == "Combat Response"
    assert "faster response" in _text(preview).casefold()

    apply_button = page.findChild(QPushButton, "liquidTuningProfilesApplyPresetButton")
    assert apply_button is not None
    if apply_button.isEnabled():
        assert apply_button.property("draftOnly") is True
    else:
        assert "draft" in (apply_button.toolTip() + apply_button.accessibleDescription()).casefold()

    copy_button = page.findChild(QPushButton, "liquidTuningProfilesCopyPresetButton")
    copy_button.click()
    assert "Combat Response" in _app().clipboard().text()


def test_lcd_7w_route_cycling_stays_non_blank_and_visual_scripts_support_phase():
    app = _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.navigation import DEFAULT_LIQUID_NAVIGATION_MODEL

    shell = LiquidCommandShell(state=_state())
    route_keys = [route.route_key for route in DEFAULT_LIQUID_NAVIGATION_MODEL.routes]
    for _round in range(2):
        for route_key in route_keys:
            shell.switch_route(route_key)
            shell.apply_bridge_telemetry(_telemetry())
            app.processEvents()
            _assert_page_not_blank(shell, route_key)

    capture = PROJECT_ROOT / "scripts" / "capture_liquid_ui_screenshots.py"
    report = PROJECT_ROOT / "scripts" / "build_liquid_visual_report.py"
    assert capture.exists()
    assert report.exists()
    assert "lcd-7w" in capture.read_text(encoding="utf-8")
    assert "--phase" in report.read_text(encoding="utf-8")


def test_lcd_7w_sources_preserve_runtime_boundaries():
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "analysis_command_pages.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "tuning_command_pages.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "models" / "analysis_command_model.py",
        )
        if path.exists()
    )

    for forbidden in (
        "BridgeCommandClient",
        "EmbeddedBridgeRuntime",
        "PhysicalInputBackend",
        "VirtualOutputWriteLoop",
        "verify_output_write",
        "write_output",
        "start_bridge",
        "restart_bridge",
        "auto_save",
        "OpenAI(",
        "from v3_app.pages.live_monitor_page",
        "from v3_app.pages.effective_response_stack_page",
    ):
        assert forbidden.casefold() not in source_text.casefold()
