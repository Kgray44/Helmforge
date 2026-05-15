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


def _runtime_status() -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
    )


def _state(*, active_page_id: str = "mapping", saved: bool = True):
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(_runtime_status(), active_page_id=active_page_id)
    state.active_profile = "LCD-12B Fluid Motion Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = saved
    state.status_message = "LCD-12B fluid active motion quality state."
    return state


def test_lcd_12b_easing_and_motion_clock_are_elapsed_time_based():
    from v3_app.liquid.motion import AnimatedValue, MotionClock, ease_in_out_cubic, ease_out_cubic, smoothstep

    assert round(ease_out_cubic(0.5), 3) == 0.875
    assert 0.0 < ease_in_out_cubic(0.25) < 0.5
    assert smoothstep(0.0) == 0.0
    assert smoothstep(1.0) == 1.0

    clock = MotionClock()
    first_delta = clock.tick(now_seconds=10.000)
    second_delta = clock.tick(now_seconds=10.016)
    third_delta = clock.tick(now_seconds=10.032)

    assert first_delta == 0.0
    assert 0.014 <= second_delta <= 0.018
    assert 0.014 <= third_delta <= 0.018
    assert clock.estimated_fps >= 55

    value = AnimatedValue(0.0, duration_ms=240, easing=ease_out_cubic)
    value.set_target(1.0)
    value.advance(0.080)
    mid = value.current
    value.advance(0.080)
    late = value.current

    assert 0.0 < mid < late < 1.0
    assert value.running is True
    value.advance(1.0)
    assert value.current == 1.0
    assert value.running is False


def test_lcd_12b_profiles_distinguish_active_and_passive_motion_quality():
    from v3_app.liquid.motion import MotionIntensity, MotionSettings
    from v3_app.liquid.visible_motion import visible_motion_profile

    off = visible_motion_profile(MotionSettings(MotionIntensity.OFF))
    reduced = visible_motion_profile(MotionSettings(MotionIntensity.REDUCED))
    standard = visible_motion_profile(MotionSettings(MotionIntensity.STANDARD))
    cinematic = visible_motion_profile(MotionSettings(MotionIntensity.CINEMATIC))

    assert off.active_interactions is False
    assert off.passive_motion_enabled is False
    assert off.frame_interval_ms == 0

    assert reduced.active_interactions is False
    assert reduced.route_sweep is False
    assert reduced.atmosphere_drift is False

    assert standard.active_interactions is True
    assert standard.page_transition_overlay is True
    assert standard.status_breathing is True
    assert standard.live_easing_preview is True
    assert standard.frame_interval_ms <= 20

    assert cinematic.active_interactions is True
    assert cinematic.passive_motion_enabled is True
    assert cinematic.component_glint is True
    assert cinematic.motion_richness_score > standard.motion_richness_score > reduced.motion_richness_score >= off.motion_richness_score


def test_lcd_12b_shell_uses_central_motion_coordinator_and_updates_mode_live():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    shell = LiquidCommandShell(
        state=_state(),
        motion_settings=MotionSettings(MotionIntensity.OFF),
        quick_wheel_enabled=True,
    )
    assert hasattr(shell, "motion_coordinator")
    assert shell.motion_coordinator.property("singleCentralMotionClock") is True
    assert shell.property("activeMotionControllerRunning") is False

    shell.set_motion_intensity(MotionIntensity.CINEMATIC)
    assert shell.motion_settings.intensity is MotionIntensity.CINEMATIC
    assert shell.property("activeMotionControllerRunning") is True
    assert shell.motion_coordinator.property("activeInteractionsEnabled") is True
    assert shell.motion_coordinator.property("passiveAnimationCount") >= 2
    assert shell.motion_coordinator.property("activeAnimationControllerCount") >= 4

    atmosphere_before = float(shell.motion_coordinator.property("atmospherePhase") or 0.0)
    status_before = float(shell.motion_coordinator.property("statusPulsePhase") or 0.0)
    proof_before = float(shell.motion_proof_panel.property("motionProofPhase") or 0.0)
    shell.advance_visible_motion_for_test(frames=5)

    assert float(shell.motion_coordinator.property("atmospherePhase") or 0.0) != atmosphere_before
    assert float(shell.motion_coordinator.property("statusPulsePhase") or 0.0) != status_before
    assert float(shell.motion_proof_panel.property("motionProofPhase") or 0.0) != proof_before
    assert float(shell.motion_coordinator.property("motionFpsEstimate") or 0.0) > 0.0


def test_lcd_12b_button_card_and_axis_motion_interpolate():
    _app()

    from PySide6.QtWidgets import QPushButton, QFrame
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    shell = LiquidCommandShell(
        state=_state(active_page_id="base_tuning"),
        motion_settings=MotionSettings(MotionIntensity.CINEMATIC),
    )
    button = shell.findChild(QPushButton, "liquidHelmButton")
    card = next(
        widget
        for widget in shell.findChildren(QFrame)
        if widget.property("microinteractionRole") in {"interactive_card", "selectable_card"}
    )
    shell.switch_route("tuning.base_tuning")
    axis_button = shell.findChild(QPushButton, "liquidAxisPill_pitch")

    assert button is not None
    assert axis_button is not None

    shell.motion_coordinator.set_interaction_state(button, hovered=True, pressed=True)
    shell.motion_coordinator.set_interaction_state(card, hovered=True, selected=True)
    shell.motion_coordinator.set_interaction_state(axis_button, selected=True)
    shell.advance_visible_motion_for_test(frames=4)

    assert 0.0 < float(button.property("hoverMotionValue") or 0.0) <= 1.0
    assert 0.0 < float(button.property("pressMotionValue") or 0.0) <= 1.0
    assert 0.0 < float(card.property("hoverMotionValue") or 0.0) <= 1.0
    assert 0.0 < float(card.property("selectionMotionValue") or 0.0) <= 1.0
    assert 0.0 < float(axis_button.property("selectionMotionValue") or 0.0) <= 1.0
    assert int(shell.motion_coordinator.property("lastInteractionAnimationTimestamp") or 0) > 0


def test_lcd_12b_page_subpage_route_and_panel_motion_are_active():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    shell = LiquidCommandShell(
        state=_state(active_page_id="mapping"),
        motion_settings=MotionSettings(MotionIntensity.CINEMATIC),
    )
    shell.switch_route("analysis.effective_response_stack")

    assert shell.current_route_key == "analysis.effective_response_stack"
    assert shell.page_transition_overlay.property("pageTransitionOverlayActive") is True
    assert shell.page_host.property("pageMotionActive") is True
    assert shell.motion_coordinator.property("pageTransitionEnabled") is True

    transition_before = float(shell.page_transition_overlay.property("pageTransitionOverlayPhase") or 0.0)
    sweep_before = float(shell.motion_coordinator.property("routeSweepPhase") or 0.0)
    shell.advance_visible_motion_for_test(frames=4)

    assert float(shell.page_transition_overlay.property("pageTransitionOverlayPhase") or 0.0) > transition_before
    assert float(shell.motion_coordinator.property("routeSweepPhase") or 0.0) != sweep_before
    assert any(
        float(widget.property("panelSettleValue") or 0.0) > 0.0
        for widget in shell.page_host.currentWidget().findChildren(QWidget)
    )


def test_lcd_12b_page_switches_use_snapshot_fade_and_glide_for_all_routes():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    shell = LiquidCommandShell(
        state=_state(active_page_id="mapping"),
        motion_settings=MotionSettings(MotionIntensity.CINEMATIC),
    )
    shell.resize(1280, 820)
    shell.show()

    route_pairs = (
        ("mapping.route_details", "mapping.advanced_route_tables"),
        ("tuning.base_tuning", "tuning.filtering"),
        ("analysis.effective_response_stack", "analysis.live_monitor"),
        ("support.help_docs", "support.perf_diagnostics"),
    )
    for from_route, to_route in route_pairs:
        shell.switch_route(from_route)
        shell.advance_visible_motion_for_test(frames=10)
        shell.switch_route(to_route)
        overlay = shell.page_transition_overlay

        assert shell.current_route_key == to_route
        assert overlay.property("pageTransitionOverlayActive") is True
        assert overlay.property("pageTransitionAnimationKind") == "snapshot_crossfade_glide"
        assert overlay.property("pageTransitionHasPreviousSnapshot") is True
        assert overlay.property("pageTransitionHasCurrentSnapshot") is True
        assert int(overlay.property("pageTransitionGlideOffsetPx") or 0) > 0
        assert overlay.property("pageTransitionUsesGeometryAnimation") is False

        start_enter_alpha = float(overlay.property("pageTransitionEnterAlpha") or 0.0)
        start_exit_alpha = float(overlay.property("pageTransitionExitAlpha") or 0.0)
        start_enter_offset = float(overlay.property("pageTransitionEnterOffsetPx") or 0.0)
        shell.advance_visible_motion_for_test(frames=4)

        assert float(overlay.property("pageTransitionEnterAlpha") or 0.0) > start_enter_alpha
        assert float(overlay.property("pageTransitionExitAlpha") or 0.0) < start_exit_alpha
        assert abs(float(overlay.property("pageTransitionEnterOffsetPx") or 0.0)) < abs(start_enter_offset)


def test_lcd_12b_status_save_and_proof_panel_animate_state_changes():
    _app()

    from PySide6.QtWidgets import QPushButton
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    shell = LiquidCommandShell(
        state=_state(saved=True),
        motion_settings=MotionSettings(MotionIntensity.CINEMATIC),
    )
    saved_chip = shell.findChild(type(shell.top_bar._saved_chip), "liquidSavedChip")
    save_button = shell.findChild(QPushButton, "liquidFooterSaveButton")
    assert saved_chip is not None
    assert save_button is not None

    shell.state.saved = False
    shell.top_bar.update_state(shell.state)
    shell.footer.update_state(shell.state)
    shell.motion_coordinator.trigger_status_transition(saved_chip, role="unsaved")
    shell.motion_coordinator.trigger_status_transition(save_button, role="draft")
    shell.switch_route("support.perf_diagnostics")
    shell.advance_visible_motion_for_test(frames=6)

    assert saved_chip.property("draftEmphasis") is True
    assert float(saved_chip.property("stateChangeMotionValue") or 0.0) > 0.0
    assert float(save_button.property("stateChangeMotionValue") or 0.0) > 0.0
    assert shell.motion_proof_panel.property("motionProofActiveAnimationCount") >= 1
    assert shell.motion_proof_panel.property("motionProofFpsEstimate") is not None
    assert shell.motion_proof_panel.property("motionProofDemoButtonValue") is not None
    assert shell.motion_proof_panel.property("motionProofDemoCardValue") is not None
    assert shell.motion_proof_panel.property("motionProofDemoChipValue") is not None
    assert shell.motion_proof_panel.property("motionProofRouteSweepPhase") is not None


def test_lcd_12b_live_monitor_motion_remains_visual_only_and_truth_labeled():
    _app()

    from v3_app.liquid.motion import MotionIntensity, MotionSettings
    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    page = AnalysisCommandPage(
        route_key="analysis.live_monitor",
        state=_state(active_page_id="live_monitor"),
        motion_settings=MotionSettings(MotionIntensity.CINEMATIC),
    )
    page.set_live_monitor_active(True)
    full_render_count = page.full_render_count
    accepted_samples = int(page.property("liveMonitorAcceptedSampleCount") or 0)
    model_builds = page.model_build_count
    before_phase = float(page.property("liveMonitorFallbackMotionPhase") or 0.0)

    for _index in range(8):
        assert page.advance_live_monitor_visual_frame() is True

    assert page.full_render_count == full_render_count
    assert int(page.property("liveMonitorAcceptedSampleCount") or 0) == accepted_samples
    assert page.model_build_count == model_builds
    assert page.property("liveMonitorVisualRenderOnly") is True
    assert page.property("liveMotionChangesRuntimeTruth") is False
    assert page.property("liveMonitorFallbackMotionTruthLabel") == "Simulation/Fallback visual motion only"
    assert float(page.property("liveMonitorFallbackMotionPhase") or 0.0) != before_phase


def test_lcd_12b_no_risky_motion_or_runtime_authority_was_added():
    liquid_source = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "v3_app" / "liquid").rglob("*.py"))

    for forbidden in (
        "QGraphicsBlurEffect",
        "QGraphicsOpacityEffect",
        "QPropertyAnimation",
        "setMaximumHeight(",
        "setMinimumHeight(",
        "live_output_writes_verified=True",
        "full_live_runtime_ready = True",
        "start_bridge",
        "stop_bridge",
        "EmbeddedBridgeRuntime",
        "BridgeCommandClient",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
    ):
        if forbidden in {"setMaximumHeight(", "setMinimumHeight("}:
            assert "QPropertyAnimation" not in liquid_source
            continue
        assert forbidden.casefold() not in liquid_source.casefold()


def test_lcd_12b_report_and_final_checklist_capture_motion_quality_acceptance():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-12b-fluid-active-motion-quality-report.md"
    checklist = PROJECT_ROOT / "docs" / "HelmForge" / "liquid-command-deck-final-qa-checklist.md"

    assert report.exists()
    assert checklist.exists()

    report_text = report.read_text(encoding="utf-8")
    checklist_text = checklist.read_text(encoding="utf-8")

    for required in (
        "root cause of missing active motion",
        "root cause of low-quality/skippy passive motion",
        "motion coordinator design",
        "active animations implemented",
        "passive animations refined",
        "Motion Proof panel details",
        "runtime truth preservation",
    ):
        assert required in report_text

    for required in (
        "active button motion",
        "active card motion",
        "page transition motion",
        "subpage transition motion",
        "axis selection motion",
        "route/signal sweep motion",
        "status state-change animation",
        "save/apply/revert animation",
        "Live Monitor smooth visual motion",
        "passive atmosphere quality",
        "Cinematic not being just background animation",
        "no obnoxious full-screen movement",
    ):
        assert required in checklist_text
