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


def _state(*, active_page_id: str = "command_readiness", saved: bool = False):
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(_runtime_status(), active_page_id=active_page_id)
    state.active_profile = "LCD-12A Motion Visibility Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = saved
    state.status_message = "LCD-12A motion visibility acceptance state."
    return state


def test_lcd_12a_motion_modes_are_visibly_distinct():
    from v3_app.liquid.motion import MotionIntensity, MotionSettings
    from v3_app.liquid.visible_motion import visible_motion_profile

    off = visible_motion_profile(MotionSettings(MotionIntensity.OFF))
    reduced = visible_motion_profile(MotionSettings(MotionIntensity.REDUCED))
    standard = visible_motion_profile(MotionSettings(MotionIntensity.STANDARD))
    cinematic = visible_motion_profile(MotionSettings(MotionIntensity.CINEMATIC))

    assert off.optional_motion_enabled is False
    assert off.atmosphere_drift is False
    assert off.status_breathing is False
    assert off.page_transition_overlay is False
    assert off.route_sweep is False

    assert reduced.optional_motion_enabled is False
    assert reduced.atmosphere_drift is False
    assert reduced.route_sweep is False

    assert standard.optional_motion_enabled is True
    assert standard.status_breathing is True
    assert standard.page_transition_overlay is True
    assert standard.live_easing_preview is True
    assert standard.route_sweep is True

    assert cinematic.optional_motion_enabled is True
    assert cinematic.atmosphere_drift is True
    assert cinematic.status_breathing is True
    assert cinematic.page_transition_overlay is True
    assert cinematic.route_sweep is True
    assert cinematic.quick_wheel_animation is True
    assert cinematic.visible_motion_type_count >= 5

    assert cinematic != standard
    assert standard != reduced
    assert reduced != off


def test_lcd_12a_shell_cinematic_enables_three_advancing_visual_controllers():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    shell = LiquidCommandShell(
        state=_state(active_page_id="mapping"),
        motion_settings=MotionSettings(MotionIntensity.CINEMATIC),
        quick_wheel_enabled=True,
    )
    shell.resize(1280, 820)
    shell.show()

    assert shell.property("motionIntensity") == "cinematic"
    assert shell.property("visibleMotionControllerCount") >= 3
    assert shell.property("atmosphereControllerRunning") is True
    assert shell.property("statusBreathControllerRunning") is True
    assert shell.property("routeSweepControllerRunning") is True
    assert shell.property("pageTransitionControllerEnabled") is True

    atmosphere_before = float(shell.atmosphere_layer.property("atmosphereVisualPhase") or 0.0)
    status_before = float(shell.status_breath_controller.property("statusBreathPhase") or 0.0)
    proof_before = float(shell.motion_proof_panel.property("motionProofPhase") or 0.0)

    shell.advance_visible_motion_for_test(frames=3)

    assert float(shell.atmosphere_layer.property("atmosphereVisualPhase") or 0.0) != atmosphere_before
    assert float(shell.status_breath_controller.property("statusBreathPhase") or 0.0) != status_before
    assert float(shell.motion_proof_panel.property("motionProofPhase") or 0.0) != proof_before


def test_lcd_12a_off_and_reduced_disable_optional_background_and_sweep_motion():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    off_shell = LiquidCommandShell(
        state=_state(active_page_id="mapping"),
        motion_settings=MotionSettings(MotionIntensity.OFF),
        quick_wheel_enabled=True,
    )
    off_shell.show()
    before = float(off_shell.motion_proof_panel.property("motionProofPhase") or 0.0)
    off_shell.advance_visible_motion_for_test(frames=3)
    assert off_shell.property("atmosphereControllerRunning") is False
    assert off_shell.property("statusBreathControllerRunning") is False
    assert off_shell.property("routeSweepControllerRunning") is False
    assert float(off_shell.motion_proof_panel.property("motionProofPhase") or 0.0) == before

    reduced_shell = LiquidCommandShell(
        state=_state(active_page_id="mapping"),
        motion_settings=MotionSettings(MotionIntensity.REDUCED),
        quick_wheel_enabled=True,
    )
    reduced_shell.show()
    assert reduced_shell.property("atmosphereControllerRunning") is False
    assert reduced_shell.property("routeSweepControllerRunning") is False
    assert reduced_shell.property("statusBreathControllerRunning") is False
    assert reduced_shell.property("pageTransitionControllerEnabled") is False


def test_lcd_12a_changing_motion_mode_updates_live_shell_policy_and_control():
    _app()

    from PySide6.QtWidgets import QComboBox
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    shell = LiquidCommandShell(
        state=_state(),
        motion_settings=MotionSettings(MotionIntensity.OFF),
        quick_wheel_enabled=True,
    )
    control = shell.findChild(QComboBox, "liquidMotionModeControl")
    assert control is not None
    assert control.currentData() == "off"
    assert shell.property("atmosphereControllerRunning") is False

    shell.set_motion_intensity(MotionIntensity.CINEMATIC)
    assert shell.motion_settings.intensity is MotionIntensity.CINEMATIC
    assert shell.property("motionIntensity") == "cinematic"
    assert control.currentData() == "cinematic"
    assert shell.property("atmosphereControllerRunning") is True
    assert shell.property("statusBreathControllerRunning") is True
    assert shell.quick_wheel.property("motionIntensity") == "cinematic"


def test_lcd_12a_page_transition_overlay_and_route_sweep_are_visible_in_cinematic():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    shell = LiquidCommandShell(
        state=_state(active_page_id="mapping"),
        motion_settings=MotionSettings(MotionIntensity.CINEMATIC),
    )
    shell.show()
    before_sweep = float(shell.route_sweep_controller.property("routeSweepPhase") or 0.0)
    shell.switch_route("analysis.effective_response_stack")

    assert shell.current_route_key == "analysis.effective_response_stack"
    assert shell.page_transition_overlay.property("pageTransitionOverlayActive") is True
    assert shell.page_transition_overlay.property("pageTransitionUsesGeometryAnimation") is False
    assert shell.page_transition_overlay.property("pageTransitionUsesOpacityEffect") is False

    phase_before = float(shell.page_transition_overlay.property("pageTransitionOverlayPhase") or 0.0)
    shell.advance_visible_motion_for_test(frames=2)
    assert float(shell.page_transition_overlay.property("pageTransitionOverlayPhase") or 0.0) != phase_before
    assert float(shell.route_sweep_controller.property("routeSweepPhase") or 0.0) != before_sweep


def test_lcd_12a_quick_wheel_animation_advances_only_when_motion_allows_it():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    off_shell = LiquidCommandShell(
        state=_state(),
        motion_settings=MotionSettings(MotionIntensity.OFF),
        quick_wheel_enabled=True,
    )
    assert off_shell.open_quick_wheel() is True
    assert off_shell.quick_wheel.property("quickWheelAnimationActive") is False
    assert off_shell.quick_wheel.property("quickWheelVisualPhase") == 1.0

    cinematic_shell = LiquidCommandShell(
        state=_state(),
        motion_settings=MotionSettings(MotionIntensity.CINEMATIC),
        quick_wheel_enabled=True,
    )
    assert cinematic_shell.open_quick_wheel() is True
    assert cinematic_shell.quick_wheel.property("quickWheelAnimationActive") is True
    before = float(cinematic_shell.quick_wheel.property("quickWheelVisualPhase") or 0.0)
    cinematic_shell.quick_wheel.advance_animation_for_test(frames=2)
    assert float(cinematic_shell.quick_wheel.property("quickWheelVisualPhase") or 0.0) > before


def test_lcd_12a_support_motion_proof_panel_constructs_and_animates_in_cinematic():
    _app()

    from v3_app.liquid.motion import MotionIntensity, MotionSettings
    from v3_app.liquid.pages.support_command_pages import create_perf_diagnostics_page
    from v3_app.liquid.visible_motion import MotionProofPanel

    page = create_perf_diagnostics_page(state=_state(), motion_settings=MotionSettings(MotionIntensity.CINEMATIC))
    panel = page.findChild(MotionProofPanel, "liquidMotionProofPanel")
    assert panel is not None
    assert panel.property("currentMotionMode") == "cinematic"
    assert panel.property("motionProofPreviewRunning") is True
    before = float(panel.property("motionProofPhase") or 0.0)
    panel.advance_for_test(frames=4)
    assert float(panel.property("motionProofPhase") or 0.0) != before


def test_lcd_12a_live_monitor_fallback_motion_is_visible_without_appending_samples():
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

    for _index in range(5):
        assert page.advance_live_monitor_visual_frame() is True

    assert page.full_render_count == full_render_count
    assert int(page.property("liveMonitorAcceptedSampleCount") or 0) == accepted_samples
    assert page.model_build_count == model_builds
    assert page.property("liveMonitorVisualRenderOnly") is True
    assert page.property("liveMotionChangesRuntimeTruth") is False
    assert page.property("liveMonitorFallbackMotionTruthLabel") == "Simulation/Fallback visual motion only"
    assert float(page.property("liveMonitorFallbackMotionPhase") or 0.0) != before_phase


def test_lcd_12a_no_risky_motion_or_runtime_authority_was_introduced():
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
        "auto_save",
        "recording supported",
    ):
        assert forbidden not in liquid_source
