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


def _state(*, saved: bool = False):
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(_runtime_status())
    state.active_profile = "LCD-10 Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = saved
    state.status_message = "LCD-10 microinteraction test state."
    return state


def _texts(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join(labels + buttons)


def test_lcd_10_motion_intensity_policy_is_small_and_phase_fenced():
    from v3_app.liquid.motion import MotionIntensity, MotionSettings
    from v3_app.liquid.reduced_motion import motion_settings_from_environment

    assert [item.value for item in MotionIntensity] == ["off", "reduced", "standard", "cinematic"]

    default = MotionSettings()
    assert default.intensity is MotionIntensity.STANDARD
    assert default.animations_enabled() is True
    assert default.hover_effects_enabled() is True
    assert default.pulses_enabled() is True
    assert default.large_motion_allowed() is False
    assert default.cinematic_effects_enabled() is False

    off = MotionSettings(MotionIntensity.OFF)
    assert off.animations_enabled() is False
    assert off.hover_effects_enabled() is False
    assert off.pulses_enabled() is False
    assert off.large_motion_allowed() is False

    reduced = MotionSettings(MotionIntensity.REDUCED)
    assert reduced.animations_enabled() is False
    assert reduced.hover_effects_enabled() is True
    assert reduced.pulses_enabled() is False
    assert reduced.large_motion_allowed() is False

    cinematic = MotionSettings(MotionIntensity.CINEMATIC)
    assert cinematic.hover_effects_enabled() is True
    assert cinematic.pulses_enabled() is True
    assert cinematic.large_motion_allowed() is False
    assert cinematic.cinematic_effects_enabled() is False

    assert motion_settings_from_environment({"HELMFORGE_LIQUID_MOTION": "off"}).intensity is MotionIntensity.OFF
    assert motion_settings_from_environment({"HELMFORGE_LIQUID_REDUCED_MOTION": "1"}).intensity is MotionIntensity.REDUCED
    assert motion_settings_from_environment({"HELMFORGE_LIQUID_MOTION": "cinematic"}).large_motion_allowed() is False


def test_lcd_10_buttons_expose_tactile_style_hooks_without_breaking_disabled_state():
    _app()

    from PySide6.QtCore import Qt
    from v3_app.liquid.glass import action_button

    primary = action_button("Apply draft", object_name="lcd10Primary", action_kind="stage_draft")
    secondary = action_button("Copy", object_name="lcd10Secondary", action_kind="copy")
    caution = action_button("Revert", object_name="lcd10Caution", action_kind="revert")
    disabled = action_button(
        "Deferred",
        object_name="lcd10Disabled",
        enabled=False,
        action_kind="disabled_deferred",
        disabled_reason="Disabled for LCD-10 test.",
    )
    checked = action_button("Overlay", object_name="lcd10Checked", action_kind="toggle_ui")
    checked.setCheckable(True)
    checked.setChecked(True)

    assert primary.property("buttonTone") == "primary"
    assert secondary.property("buttonTone") == "secondary"
    assert caution.property("buttonTone") == "caution"
    assert disabled.property("buttonTone") == "disabled"
    assert checked.property("buttonTone") == "secondary"
    assert primary.property("microinteractionRole") == "button"
    assert primary.property("hoverEffectsEnabled") is True
    assert primary.property("focusRingEnabled") is True
    assert primary.focusPolicy() in {Qt.FocusPolicy.StrongFocus, Qt.FocusPolicy.TabFocus}
    assert disabled.isEnabled() is False
    assert disabled.property("motionEnabled") is False
    assert disabled.property("activeInteraction") is False
    assert disabled.toolTip() == "Disabled for LCD-10 test."


def test_lcd_10_status_components_support_motion_off_and_standard_pulse_hooks():
    _app()

    from v3_app.liquid.motion import MotionIntensity, MotionSettings
    from v3_app.liquid.status_components import DraftStateIndicator, StatusChip, StatusLight, TruthBadge

    off = MotionSettings(MotionIntensity.OFF)
    standard = MotionSettings(MotionIntensity.STANDARD)

    static_chip = StatusChip("Unsaved draft", state_role="unsaved", motion_settings=off)
    pulsing_light = StatusLight(state_role="verified", motion_settings=standard)
    static_light = StatusLight(state_role="waiting", motion_settings=off)
    draft = DraftStateIndicator("Workspace draft staged", state_role="unsaved", motion_settings=standard)
    badge = TruthBadge("Output proof missing", state_role="blocked", helper_text="No vJoy write proof.", motion_settings=off)

    assert static_chip.property("pulseEnabled") is False
    assert static_chip.property("motionIntensity") == "off"
    assert static_chip.text() == "Unsaved draft"
    assert pulsing_light.property("pulseEnabled") is True
    assert pulsing_light.property("pulseRole") == "verified"
    assert pulsing_light.property("pulseTarget") == "tiny_status_indicator"
    assert static_light.property("pulseEnabled") is False
    assert draft.property("draftEmphasis") is True
    assert draft.property("pulseRole") == "draft"
    assert "Output proof missing" in _texts(badge)
    assert "No vJoy write proof." in _texts(badge)


def test_lcd_10_interactive_cards_focus_hooks_construct_offscreen():
    _app()

    from PySide6.QtCore import Qt
    from v3_app.liquid.flow_components import RouteFlowRow, SignalPipelineStage
    from v3_app.liquid.motion import FocusRole, HoverRole, MicrointeractionRole, apply_motion_property
    from v3_app.liquid.status_components import ReadinessGate

    gate = ReadinessGate("Output proof", state_text="Proof missing", state_role="blocked")
    row = RouteFlowRow(
        source_label="Stick X",
        function_label="Roll",
        target_label="vJoy X",
        status_role="info",
    )
    stage = SignalPipelineStage(
        "Base tuning",
        "Transforms the selected axis.",
        selected_value="Roll 0.20",
        status_role="simulation",
    )

    apply_motion_property(stage, MicrointeractionRole.SELECTABLE_CARD, hover_role=HoverRole.CARD, focus_role=FocusRole.RING)
    stage.setProperty("selected", True)

    for widget in (gate, row, stage):
        assert widget.property("microinteractionRole") in {"status_card", "selectable_card", "interactive_card"}
        assert widget.property("hoverRole") in {"status_card", "route_row", "card"}
        assert widget.property("focusRingEnabled") is True
        assert widget.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert stage.property("selected") is True


def test_lcd_10_shell_save_state_and_navigation_microinteraction_hooks():
    _app()

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(saved=False))
    saved_chip = shell.findChild(QLabel, "liquidSavedChip")
    footer = shell.findChild(QWidget, "liquid_floating_footer_strip")
    save_button = shell.findChild(QPushButton, "liquidFooterSaveButton")
    dock_button = shell.findChild(QPushButton, "liquidMode_preflight")

    assert saved_chip is not None
    assert saved_chip.text() == "Unsaved"
    assert saved_chip.property("statusRole") == "unsaved"
    assert saved_chip.property("draftEmphasis") is True
    assert footer is not None
    assert footer.property("draftEmphasis") is True
    assert save_button is not None
    assert save_button.isEnabled() is False
    assert save_button.property("draftEmphasis") is True
    assert save_button.property("activeInteraction") is False
    assert dock_button is not None
    assert dock_button.property("microinteractionRole") == "navigation_button"
    assert dock_button.property("hoverRole") == "dock"
    assert dock_button.property("focusRingEnabled") is True
    assert dock_button.focusPolicy() == Qt.FocusPolicy.StrongFocus

    clean_state = _state(saved=True)
    shell.top_bar.update_state(clean_state)
    shell.footer.update_state(clean_state)
    assert saved_chip.text() == "Saved"
    assert saved_chip.property("statusRole") == "saved"
    assert saved_chip.property("draftEmphasis") is False
    assert footer.property("draftEmphasis") is False
    assert save_button.property("draftEmphasis") is False


def test_lcd_10_support_topic_cards_are_focusable_and_raw_diagnostics_do_not_pulse():
    _app()

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.support_command_pages import create_help_docs_page, create_perf_diagnostics_page

    help_page = create_help_docs_page(state=_state(), runtime_status=_runtime_status())
    card = help_page.findChild(QWidget, "liquidSupportTopicCard_preflight_and_readiness")
    assert card is not None
    assert card.property("microinteractionRole") == "interactive_card"
    assert card.property("hoverRole") == "card"
    assert card.property("focusRingEnabled") is True
    assert card.focusPolicy() == Qt.FocusPolicy.StrongFocus

    diagnostics = create_perf_diagnostics_page(state=_state(), runtime_status=_runtime_status())
    raw = diagnostics.findChild(QWidget, "liquidSupportAdvancedDetails")
    assert raw is not None
    assert raw.property("rawDiagnosticSurface") is True
    assert raw.property("pulseEnabled") is False
    assert raw.property("hoverEffectsEnabled") is False


def test_lcd_10_live_monitor_microinteractions_do_not_expand_visual_lane_or_rebuild_models():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.analysis_command_pages import (
        LIQUID_LIVE_MONITOR_VISUAL_TARGET_FPS,
        AnalysisCommandPage,
    )

    page = AnalysisCommandPage(route_key="analysis.live_monitor", state=_state())
    page.set_live_monitor_active(True)
    full_render_count = page.full_render_count
    accepted_samples = int(page.property("liveMonitorAcceptedSampleCount") or 0)
    model_builds = page.model_build_count

    for _index in range(4):
        assert page.advance_live_monitor_visual_frame() is True

    assert page.property("liveMonitorVisualTargetFps") == LIQUID_LIVE_MONITOR_VISUAL_TARGET_FPS
    assert page.property("liveMonitorVisualRenderOnly") is True
    assert page.full_render_count == full_render_count
    assert int(page.property("liveMonitorAcceptedSampleCount") or 0) == accepted_samples
    assert page.model_build_count == model_builds

    telemetry_badge = page.findChild(QWidget, "liquidLiveMonitorTelemetryBadge")
    assert telemetry_badge is not None
    assert telemetry_badge.property("microinteractionRole") == "status_card"


def test_lcd_10_sources_preserve_runtime_authority_and_forbidden_motion_boundaries():
    liquid_dir = PROJECT_ROOT / "v3_app" / "liquid"
    liquid_source = "\n".join(path.read_text(encoding="utf-8") for path in liquid_dir.rglob("*.py"))
    lcd10_source = "\n".join(
        (PROJECT_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "v3_app/liquid/motion.py",
            "v3_app/liquid/reduced_motion.py",
            "v3_app/liquid/glass.py",
            "v3_app/liquid/status_components.py",
        )
    )

    for forbidden in (
        "QGraphicsBlurEffect",
        "QGraphicsOpacityEffect",
        "QPropertyAnimation",
        "radial_menu",
        "open_radial",
        "save_workspace(",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
    ):
        assert forbidden.casefold() not in liquid_source.casefold()

    for forbidden in (
        "setGeometry(",
        "move(",
        "resize(",
        "full_live_runtime_ready = True",
        "live_output_writes_verified=True",
        "start_bridge",
        "stop_bridge",
        "EmbeddedBridgeRuntime",
        "BridgeCommandClient",
    ):
        assert forbidden.casefold() not in lcd10_source.casefold()

    assert "build_analysis_command_model(" not in (PROJECT_ROOT / "v3_app" / "liquid" / "motion.py").read_text(encoding="utf-8")


def test_lcd_10_report_documents_scope_deferrals_and_packaged_smoke_status():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-10-microinteractions-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-10 Microinteractions",
        "motion intensity model",
        "OFF",
        "REDUCED",
        "STANDARD",
        "CINEMATIC",
        "button interaction changes",
        "card/focus interaction changes",
        "status chip/light",
        "save/unsaved emphasis",
        "accessibility/focus",
        "performance safety",
        "deferred to LCD-11",
        "deferred to LCD-12",
        "runtime truth preservation",
        "packaged smoke",
        "no page transitions added",
        "no radial command wheel added",
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
