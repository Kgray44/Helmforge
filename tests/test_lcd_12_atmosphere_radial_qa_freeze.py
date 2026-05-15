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


def _state(*, active_page_id: str = "command_readiness", saved: bool = True):
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(_runtime_status(), active_page_id=active_page_id)
    state.active_profile = "LCD-12 Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = saved
    state.status_message = "LCD-12 atmosphere and quick navigation test state."
    return state


def test_lcd_12_motion_policy_and_atmosphere_specs_are_motion_aware():
    from v3_app.liquid.atmosphere import atmosphere_spec, mode_accent
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    off = MotionSettings(MotionIntensity.OFF)
    reduced = MotionSettings(MotionIntensity.REDUCED)
    standard = MotionSettings(MotionIntensity.STANDARD)
    cinematic = MotionSettings(MotionIntensity.CINEMATIC)

    assert off.atmosphere_enabled() is False
    assert off.atmosphere_drift_enabled() is False
    assert off.radial_motion_enabled() is False

    assert reduced.atmosphere_enabled() is True
    assert reduced.atmosphere_drift_enabled() is False
    assert reduced.radial_motion_enabled() is False

    assert standard.atmosphere_enabled() is True
    assert standard.atmosphere_drift_enabled() is False
    assert standard.radial_motion_enabled() is True

    assert cinematic.atmosphere_enabled() is True
    assert cinematic.atmosphere_drift_enabled() is True
    assert cinematic.safe_cinematic_polish_enabled() is True
    assert cinematic.cinematic_effects_enabled() is False

    assert atmosphere_spec(off).enabled is False
    assert atmosphere_spec(reduced).enabled is True
    assert atmosphere_spec(reduced).animated is False
    assert atmosphere_spec(standard).enabled is True
    assert atmosphere_spec(standard).animated is False
    assert atmosphere_spec(cinematic).animated is True
    assert atmosphere_spec(cinematic).cadence_ms >= 1000
    assert atmosphere_spec(cinematic).high_frequency is False
    assert atmosphere_spec(cinematic).uses_blur is False
    assert atmosphere_spec(cinematic).uses_distortion is False
    assert mode_accent("preflight").accent_id == "preflight"
    assert mode_accent("analysis").meaning == "live_truth"


def test_lcd_12_shell_atmosphere_is_optional_static_and_route_deterministic():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    off_shell = LiquidCommandShell(
        state=_state(active_page_id="mapping"),
        motion_settings=MotionSettings(MotionIntensity.OFF),
    )
    off_shell.switch_route("analysis.live_monitor")
    assert off_shell.current_route_key == "analysis.live_monitor"
    assert off_shell.property("atmosphereEnabled") is False
    assert off_shell.property("atmosphereAnimated") is False
    assert off_shell.property("atmosphereHighFrequency") is False

    reduced_shell = LiquidCommandShell(
        state=_state(active_page_id="preflight"),
        motion_settings=MotionSettings(MotionIntensity.REDUCED),
    )
    reduced_shell.switch_route("support.perf_diagnostics")
    assert reduced_shell.current_route_key == "support.perf_diagnostics"
    assert reduced_shell.property("atmosphereEnabled") is True
    assert reduced_shell.property("atmosphereAnimated") is False
    assert reduced_shell.property("atmosphereMode") == "static_reduced"
    assert reduced_shell.property("modeAccent") == "support"

    standard_shell = LiquidCommandShell(
        state=_state(active_page_id="preflight"),
        motion_settings=MotionSettings(MotionIntensity.STANDARD),
    )
    before = int(standard_shell.property("atmosphereUpdateCount") or 0)
    standard_shell.switch_route("recorder.flight_recorder")
    assert standard_shell.current_route_key == "recorder.flight_recorder"
    assert int(standard_shell.property("atmosphereUpdateCount") or 0) == before + 1
    assert standard_shell.property("atmosphereEnabled") is True
    assert standard_shell.property("atmosphereAnimated") is False
    assert standard_shell.property("modeAccent") == "recorder"
    assert standard_shell.property("atmosphereRuntimeMutation") is False


def test_lcd_12_quick_wheel_is_optional_navigation_only_and_not_required_for_dock_navigation():
    _app()

    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QPushButton
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.quick_switch_wheel import QUICK_WHEEL_MODE_IDS

    disabled_shell = LiquidCommandShell(state=_state(), quick_wheel_enabled=False)
    assert disabled_shell.property("quickWheelEnabled") is False
    assert disabled_shell.property("quickWheelRequiredForNavigation") is False
    disabled_shell.switch_mode("mapping")
    assert disabled_shell.current_route_key == "mapping.hotas_map"

    shell = LiquidCommandShell(state=_state(), quick_wheel_enabled=True)
    assert shell.property("quickWheelEnabled") is True
    assert shell.property("quickWheelRuntimeMutation") is False
    assert shell.property("quickWheelModeIds") == QUICK_WHEEL_MODE_IDS
    assert shell.quick_wheel.property("quickWheelFocusTrap") is False
    assert shell.quick_wheel.property("quickWheelNavigationOnly") is True
    assert shell.quick_wheel.mode_ids() == QUICK_WHEEL_MODE_IDS

    buttons = {
        button.property("modeId"): button
        for button in shell.quick_wheel.findChildren(QPushButton)
        if button.property("uiRole") == "liquidQuickWheelButton"
    }
    assert tuple(buttons) == QUICK_WHEEL_MODE_IDS

    assert shell.open_quick_wheel() is True
    assert shell.quick_wheel.isVisible() is True

    escape = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    shell.quick_wheel.keyPressEvent(escape)
    assert shell.quick_wheel.isVisible() is False

    shell.open_quick_wheel()
    buttons["analysis"].click()
    assert shell.current_route_key == "analysis.effective_response_stack"
    assert shell.active_mode_id == "analysis"
    assert shell.quick_wheel.isVisible() is False


def test_lcd_12_motion_off_and_reduced_leave_quick_wheel_usable_without_animation():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.motion import MotionIntensity, MotionSettings

    off_shell = LiquidCommandShell(
        state=_state(),
        motion_settings=MotionSettings(MotionIntensity.OFF),
        quick_wheel_enabled=True,
    )
    assert off_shell.open_quick_wheel() is True
    assert off_shell.quick_wheel.property("quickWheelMotionMode") == "instant"
    assert off_shell.quick_wheel.property("quickWheelAnimationActive") is False
    assert off_shell.switch_route("support.help_docs") is None
    assert off_shell.current_route_key == "support.help_docs"

    reduced_shell = LiquidCommandShell(
        state=_state(),
        motion_settings=MotionSettings(MotionIntensity.REDUCED),
        quick_wheel_enabled=True,
    )
    assert reduced_shell.open_quick_wheel() is True
    assert reduced_shell.quick_wheel.property("quickWheelMotionMode") == "minimal"
    assert reduced_shell.quick_wheel.property("quickWheelAnimationActive") is False


def test_lcd_12_all_routes_remain_routable_and_diagnostics_raw_panels_stay_calm():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.models.nav_model import build_liquid_navigation_model

    shell = LiquidCommandShell(state=_state(), quick_wheel_enabled=True)
    model = build_liquid_navigation_model()

    for route in model.routes:
        shell.switch_route(route.route_key)
        assert shell.current_route_key == route.route_key
        assert shell.active_mode_id == route.mode_id
        assert shell.page_host.currentWidget() is shell.page_widgets[route.route_key]

    raw_panels = [
        widget
        for widget in shell.findChildren(QWidget, "liquidSupportAdvancedDetails")
        if widget.property("rawDiagnosticSurface") is True
    ]
    assert raw_panels
    for raw in raw_panels:
        assert raw.property("pulseEnabled") is False
        assert raw.property("atmosphereHighFrequency") in {False, None}
        assert raw.property("atmosphereAnimated") in {False, None}


def test_lcd_12_live_monitor_discipline_and_source_boundaries_are_preserved():
    _app()

    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    page = AnalysisCommandPage(route_key="analysis.live_monitor", state=_state())
    page.set_live_monitor_active(True)
    full_render_count = page.full_render_count
    accepted_samples = int(page.property("liveMonitorAcceptedSampleCount") or 0)
    model_builds = page.model_build_count

    for _index in range(4):
        assert page.advance_live_monitor_visual_frame() is True

    assert page.full_render_count == full_render_count
    assert int(page.property("liveMonitorAcceptedSampleCount") or 0) == accepted_samples
    assert page.model_build_count == model_builds
    assert page.property("liveMonitorVisualRenderOnly") is True
    assert page.property("liveMotionChangesRuntimeTruth") is False

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


def test_lcd_12_freeze_docs_exist_and_capture_truth_boundaries():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-12-atmosphere-radial-qa-freeze-report.md"
    checklist = PROJECT_ROOT / "docs" / "HelmForge" / "liquid-command-deck-final-qa-checklist.md"

    assert report.exists()
    assert checklist.exists()

    report_text = report.read_text(encoding="utf-8")
    checklist_text = checklist.read_text(encoding="utf-8")

    for required in (
        "LCD-12 Atmosphere, Radial Menu, Accessibility, and QA Freeze",
        "atmosphere effects added",
        "radial menu status",
        "motion intensity behavior",
        "reduced-motion/accessibility behavior",
        "performance safeguards",
        "packaged smoke result",
        "physical HOTAS validation",
        "runtime truth preservation",
        "no runtime authority added",
        "no hardware polling changes",
        "no vJoy/output behavior changes",
        "no output verification changes",
        "no Full Live Runtime Ready shortcut",
        "no Bridge lifecycle management",
        "no recorder capture/encoding changes",
        "no cloud AI/LLM behavior",
        "no auto-save",
        "no fake readiness/recording/output claims",
    ):
        assert required in report_text

    for required in (
        "app launches into Liquid Command Deck primary experience",
        "Legacy pages are not the primary Liquid page compositions",
        "compact dock / mode selector clarity",
        "each major mode opens",
        "each subpage opens",
        "Preflight readiness truth",
        "Mapping output intent truth",
        "Analysis / Live Monitor live/stale truth",
        "Recorder capture truth / metadata-only truth",
        "Helm draft/apply/revert truth",
        "simulation fallback truth",
        "vJoy detected vs output proof distinction",
        "motion OFF",
        "reduced motion",
        "standard motion",
        "radial menu enabled/disabled",
        "atmosphere readability",
        "no large-container blur",
        "no broad layout mutation",
        "packaged smoke result",
        "physical HOTAS validation status",
    ):
        assert required in checklist_text
