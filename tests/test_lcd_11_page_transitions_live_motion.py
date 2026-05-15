from __future__ import annotations

import os
from pathlib import Path

from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status(*, truth: RuntimeTruth = RuntimeTruth.BLOCKED_MISSING_DEVICE) -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=truth,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
    )


def _state(*, active_page_id: str = "live_monitor", saved: bool = True):
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(_runtime_status(), active_page_id=active_page_id)
    state.active_profile = "LCD-11 Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = saved
    state.status_message = "LCD-11 page motion and live display test state."
    return state


def test_lcd_11_motion_policy_extends_lcd_10_without_lcd_12_effects():
    from v3_app.liquid.motion import MotionIntensity, MotionSettings, page_motion_spec

    off = MotionSettings(MotionIntensity.OFF)
    reduced = MotionSettings(MotionIntensity.REDUCED)
    standard = MotionSettings(MotionIntensity.STANDARD)
    cinematic = MotionSettings(MotionIntensity.CINEMATIC)

    assert off.page_motion_enabled() is False
    assert off.live_easing_enabled() is False
    assert off.panel_stagger_enabled() is False
    assert off.route_trace_enabled() is False

    assert reduced.page_motion_enabled() is True
    assert reduced.live_easing_enabled() is True
    assert reduced.panel_stagger_enabled() is False
    assert reduced.route_trace_enabled() is False

    assert standard.page_motion_enabled() is True
    assert standard.live_easing_enabled() is True
    assert standard.panel_stagger_enabled() is True
    assert standard.route_trace_enabled() is True

    assert cinematic.page_motion_enabled() is True
    assert cinematic.live_easing_enabled() is True
    assert cinematic.route_trace_enabled() is True
    assert cinematic.cinematic_effects_enabled() is False
    assert cinematic.recorder_timeline_sweep_enabled() is False

    assert page_motion_spec(off).mode == "immediate"
    assert page_motion_spec(off).duration_ms == 0
    assert page_motion_spec(reduced).mode == "minimal_fade"
    assert page_motion_spec(reduced).panel_stagger_ms == 0
    assert 180 <= page_motion_spec(standard).duration_ms <= 260
    assert 30 <= page_motion_spec(standard).panel_stagger_ms <= 60


def test_lcd_11_shell_route_motion_updates_route_state_without_risky_effects():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    off_shell = LiquidCommandShell(
        state=_state(active_page_id="mapping"),
        motion_settings=MotionSettings(MotionIntensity.OFF),
    )
    off_shell.switch_route("analysis.live_monitor")
    assert off_shell.current_route_key == "analysis.live_monitor"
    assert off_shell.active_mode_id == "analysis"
    assert off_shell.active_subpage_id == "live_monitor"
    assert off_shell.page_host.currentWidget() is off_shell.page_widgets["analysis.live_monitor"]
    assert off_shell.page_host.property("pageMotionMode") == "immediate"
    assert off_shell.page_host.property("pageMotionActive") is False

    shell = LiquidCommandShell(
        state=_state(active_page_id="mapping"),
        motion_settings=MotionSettings(MotionIntensity.STANDARD),
    )
    before_count = int(shell.page_host.property("pageMotionCount") or 0)
    shell.switch_route("analysis.live_monitor")
    assert shell.current_route_key == "analysis.live_monitor"
    assert shell.page_host.currentWidget() is shell.page_widgets["analysis.live_monitor"]
    assert int(shell.page_host.property("pageMotionCount") or 0) == before_count + 1
    assert shell.page_host.property("pageMotionMode") == "fade_slide"
    assert shell.page_host.property("pageMotionActive") is True
    assert shell.page_host.property("pageMotionFrom") == "mapping.hotas_map"
    assert shell.page_host.property("pageMotionTo") == "analysis.live_monitor"
    assert shell.page_host.property("pageMotionUsesDynamicReparenting") is False
    assert shell.findChildren(QWidget, "liquid_page_host")


def test_lcd_11_live_easing_values_are_display_only_and_freeze_on_stale():
    from v3_app.liquid.motion import EasedValue, MotionIntensity, MotionSettings

    off = EasedValue(0.0, minimum=-1.0, maximum=1.0, motion_settings=MotionSettings(MotionIntensity.OFF))
    off.set_target(0.75)
    assert off.source_value == 0.75
    assert off.target_value == 0.75
    assert off.display_value == 0.75

    eased = EasedValue(0.0, minimum=-1.0, maximum=1.0, motion_settings=MotionSettings(MotionIntensity.STANDARD))
    eased.set_target(1.0)
    first_display = eased.display_value
    assert eased.source_value == 1.0
    assert eased.target_value == 1.0
    assert first_display == 0.0
    eased.advance()
    assert 0.0 < eased.display_value < 1.0
    assert eased.source_value == 1.0

    frozen = eased.display_value
    eased.set_target(-1.0, stale=True)
    eased.advance()
    assert eased.display_value == frozen
    assert eased.motion_state == "stale"
    eased.set_target(2.0, snap=True)
    assert eased.display_value == 1.0
    assert eased.target_value == 1.0


def test_lcd_11_axis_meters_and_graph_markers_ease_without_appending_samples():
    _app()

    from v3_app.liquid.instruments import AxisBarPair, LiveAxisTimeSeriesGraph

    pair = AxisBarPair("Roll", raw_value=0.0, output_intent_value=0.0, state_role="info")
    pair.update_values(raw_value=1.0, output_intent_value=0.25)
    assert pair.property("targetPercents") == (100, 25)
    assert pair.property("axisMeterMotionEnabled") is True
    pair.advance_motion_frame()
    assert pair.property("displayPercents")[0] <= 100

    history = {"Roll": [(-0.5, -0.25), (0.75, 0.5)]}
    graph = LiveAxisTimeSeriesGraph(axis_history=history, overlay_final_values=True, state_role="info")
    original_length = graph.property("historyLength")
    graph.update_history(history, overlay_final_values=True, repaint=False)
    graph.advance_marker_motion()
    assert graph.property("historyLength") == original_length
    assert graph.property("markerMotionEnabled") is True
    assert graph.property("markerMotionState") in {"live", "settling"}
    graph.advance_marker_motion(stale=True)
    assert graph.property("markerMotionState") == "stale"
    assert graph.property("staleMotionFrozen") is True


def test_lcd_11_live_monitor_visual_motion_preserves_lcd_9_cadence():
    _app()

    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    page = AnalysisCommandPage(route_key="analysis.live_monitor", state=_state())
    page.set_live_monitor_active(True)
    full_render_count = page.full_render_count
    accepted_samples = int(page.property("liveMonitorAcceptedSampleCount") or 0)
    model_builds = page.model_build_count

    for _index in range(5):
        assert page.advance_live_monitor_visual_frame() is True

    assert page.full_render_count == full_render_count
    assert int(page.property("liveMonitorAcceptedSampleCount") or 0) == accepted_samples
    assert page.model_build_count == model_builds
    assert page.property("liveMonitorVisualRenderOnly") is True
    assert int(page.property("liveMotionFrameCount") or 0) == 5
    assert page.property("liveMotionState") in {"live", "stale"}
    assert page.property("liveMotionChangesRuntimeTruth") is False


def test_lcd_11_button_hat_and_route_signal_motion_hooks_are_truthful():
    _app()

    from v3_app.liquid.flow_components import RouteFlowRow, SignalPipelineStage
    from v3_app.liquid.instruments import ButtonIlluminationGrid, HatDirectionIndicator
    from v3_app.liquid.motion import MotionIntensity, MotionSettings, apply_route_signal_motion

    grid = ButtonIlluminationGrid(buttons=("A", "B", "C"), active_buttons=("A",), state_role="info")
    assert grid.property("activeButtons") == ("A",)
    assert grid.property("buttonMotionPreservesTruth") is True
    assert grid.findChild(type(grid), "doesNotExist") is None

    hat = HatDirectionIndicator(selected_direction="Left", state_role="info")
    assert hat.property("selectedDirection") == "Left"
    assert hat.property("hatMotionPreservesTruth") is True
    assert hat.property("intermediateDirectionsInvented") is False

    row = RouteFlowRow(source_label="Stick X", function_label="Roll", target_label="vJoy X", status_role="info")
    stage = SignalPipelineStage("Final Output Intent", "Read-only intent stage.", selected_value="0.12", status_role="simulation")
    apply_route_signal_motion(row, motion_settings=MotionSettings(MotionIntensity.OFF))
    apply_route_signal_motion(stage, motion_settings=MotionSettings(MotionIntensity.REDUCED))
    assert row.property("signalPathMotionEnabled") is False
    assert stage.property("signalPathMotionEnabled") is False
    apply_route_signal_motion(stage, motion_settings=MotionSettings(MotionIntensity.STANDARD))
    assert stage.property("signalPathMotionEnabled") is True
    assert stage.property("signalPathMotionRuntimeMutation") is False


def test_lcd_11_recorder_helm_and_source_boundaries_are_phase_fenced():
    _app()

    from v3_app.liquid.pages.helm_command_deck import HelmAssistantDeck
    from v3_app.liquid.pages.recorder_command_pages import create_flight_recorder_page

    recorder = create_flight_recorder_page(state=_state())
    assert recorder.property("recorderTimelineSweepEnabled") is False
    assert recorder.property("recorderTimelineStatus") == "deferred_metadata_only"
    assert recorder.property("recorderMotionClaimsCapture") is False

    helm = HelmAssistantDeck(state=_state())
    assert helm.property("helmMotionStatus") == "local_draft_only"
    assert helm.property("helmMotionAddsCloudAi") is False
    assert helm.property("helmMotionAutoApply") is False

    liquid_source = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "v3_app" / "liquid").rglob("*.py"))
    for forbidden in (
        "QGraphicsBlurEffect",
        "QGraphicsOpacityEffect",
        "QPropertyAnimation",
        "full_live_runtime_ready = True",
        "live_output_writes_verified=True",
        "start_bridge",
        "stop_bridge",
        "EmbeddedBridgeRuntime",
        "BridgeCommandClient",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
    ):
        assert forbidden.casefold() not in liquid_source.casefold()


def test_lcd_11_report_documents_scope_status_and_deferrals():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-11-page-transitions-live-motion-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-11 Page Transitions and Live Data Motion",
        "page transition approach",
        "motion intensity behavior",
        "live data easing primitives",
        "stale telemetry behavior",
        "route trace status",
        "recorder timeline status",
        "Helm motion status",
        "performance safeguards",
        "deferred to LCD-12",
        "packaged smoke status",
        "physical HOTAS validation status",
        "runtime truth preservation",
        "no radial command wheel added",
        "no background/atmosphere drift added",
        "no real blur/distortion added",
        "no layout geometry animation added",
        "no runtime authority added",
        "no hardware polling changes",
        "no vJoy/output behavior changes",
        "no output verification changes",
        "no Bridge lifecycle management",
        "no recorder capture/encoding changes",
        "no cloud AI/LLM behavior",
        "no auto-save",
    ):
        assert required in text
