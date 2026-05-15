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


def _state():
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(_runtime_status())
    state.active_profile = "LCD-1R Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = False
    state.status_message = "LCD-1R static command deck loaded; actions remain placeholders."
    return state


def test_lcd_1r_compact_dock_is_glyph_first_not_sidebar_text_buttons():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.navigation import LIQUID_MODE_IDS, REQUIRED_LIQUID_MODES
    from v3_app.liquid.theme_tokens import LiquidLayout

    shell = LiquidCommandShell(state=_state())
    dock = shell.findChild(QWidget, "liquid_floating_mode_dock")
    buttons = [
        button
        for button in shell.findChildren(QPushButton)
        if button.property("uiRole") == "liquidModeDockButton"
    ]

    assert dock is not None
    assert dock.property("liquidRole") == "liquid_floating_mode_dock"
    assert dock.maximumWidth() <= LiquidLayout.mode_dock_width
    assert LiquidLayout.mode_dock_width <= 88
    assert [button.property("modeId") for button in buttons] == list(LIQUID_MODE_IDS)
    assert [button.accessibleName() for button in buttons] == list(REQUIRED_LIQUID_MODES)
    assert all(button.property("dockDensity") == "floating_glyph" for button in buttons)
    assert all(1 <= len(button.text()) <= 3 for button in buttons)
    assert not any(button.text() in REQUIRED_LIQUID_MODES for button in buttons)


def test_lcd_1r_workspace_uses_command_deck_regions_instead_of_one_empty_box():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())

    for object_name, role in (
        ("liquidCommandWorkspace", "liquid_command_workspace"),
        ("liquid_command_surface", "liquid_command_surface"),
        ("liquid_surface_glass_field", "liquid_surface_glass_field"),
        ("liquid_page_host", "liquid_page_host"),
    ):
        widget = shell.findChild(QWidget, object_name)
        assert widget is not None, object_name
        assert widget.property("liquidRole") == role


def test_lcd_1r_each_placeholder_exposes_future_page_composition_regions():
    _app()

    from PySide6.QtWidgets import QLabel, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.pages.placeholder_pages import LIQUID_PLACEHOLDER_PAGES

    shell = LiquidCommandShell(state=_state())
    expected_hero_titles = {
        "preflight": "Go / No-Go Readiness",
        "mapping": "HOTAS Visual Map",
        "tuning": "Response Instrument",
        "analysis": "Signal / Live Monitor Instrument",
        "recorder": "Capture Capability Deck",
        "support": "Diagnostics / Help Console",
    }

    assert {page.hero_title for page in LIQUID_PLACEHOLDER_PAGES} == set(expected_hero_titles.values())

    for definition in LIQUID_PLACEHOLDER_PAGES:
        shell.switch_mode(definition.mode_id)
        page = shell.page_host.currentWidget()
        labels = "\n".join(label.text() for label in page.findChildren(QLabel))
        if definition.mode_id == "preflight":
            for object_name, role in (
                ("liquidPreflightStatusRail", "liquid_status_rail"),
                ("liquidPreflightHeroGoNoGo", "liquid_hero_panel"),
                ("liquidPreflightSystemDetails", "liquid_context_inspector_region"),
                ("liquidPreflightActionPanel", "liquid_detail_action_region"),
                ("liquidPreflightAdvancedDiagnostics", "liquid_advanced_region"),
            ):
                widget = page.findChild(QWidget, object_name)
                assert widget is not None, object_name
                assert widget.property("liquidRole") == role

            assert "LIQUID COMMAND DECK" in labels
            assert "Command Readiness" in labels
            assert "Can I safely use live output right now?" in labels
            assert "placeholder / static shell foundation" not in labels.casefold()
            continue
        if definition.mode_id == "mapping":
            for object_name, role in (
                ("liquidMappingIntentRail", "liquid_mapping_intent_rail"),
                ("liquidMappingHotasHero", "liquid_hero_panel"),
                ("liquidMappingInspector", "liquid_context_inspector_region"),
                ("liquidMappingRouteFlowPanel", "liquid_detail_action_region"),
                ("liquidMappingAdvancedRouteDetails", "liquid_advanced_region"),
            ):
                widget = page.findChild(QWidget, object_name)
                assert widget is not None, object_name
                assert widget.property("liquidRole") == role

            assert "LIQUID COMMAND DECK" in labels
            assert "HOTAS Map" in labels
            assert "What is each physical control doing?" in labels
            assert "placeholder / static shell foundation" not in labels.casefold()
            continue
        if definition.mode_id == "tuning":
            for object_name, role in (
                ("liquidTuningStatusRail", "liquid_tuning_status_rail"),
                ("liquidTuningHero", "liquid_tuning_response_hero"),
                ("liquidTuningAxisSelectorPanel", "liquid_tuning_axis_context"),
                ("liquidTuningParameterInspector", "liquid_tuning_parameter_inspector"),
                ("liquidTuningAdvancedDetails", "liquid_tuning_advanced_details"),
            ):
                widget = page.findChild(QWidget, object_name)
                assert widget is not None, object_name
                assert widget.property("liquidRole") == role

            assert "TUNING COMMAND" in labels
            assert "Base Tuning" in labels
            assert "How does this axis respond and feel?" in labels
            assert "placeholder / static shell foundation" not in labels.casefold()
            continue
        if definition.mode_id == "analysis":
            for object_name, role in (
                ("liquidAnalysisStatusRail", "liquid_status_rail"),
                ("liquidAnalysisPipelineHero", "liquid_hero_panel"),
                ("liquidAnalysisAxisInspector", "liquid_inspector_panel"),
                ("liquidAnalysisStageDetails", "liquid_detail_panel"),
                ("liquidAnalysisAdvancedDetails", "liquid_advanced_section"),
            ):
                widget = page.findChild(QWidget, object_name)
                assert widget is not None, object_name
                assert widget.property("liquidRole") == role

            assert "ANALYSIS / EFFECTIVE RESPONSE STACK" in labels
            assert "Effective Response Stack" in labels
            assert "How does raw input become final output?" in labels
            assert "placeholder / static shell foundation" not in labels.casefold()
            continue
        if definition.mode_id == "recorder":
            for object_name, role in (
                ("liquidRecorderStatusRail", "liquid_status_rail"),
                ("liquidRecorderStatusHero", "liquid_hero_panel"),
                ("liquidRecorderCapabilityPanel", "liquid_inspector_panel"),
                ("liquidRecorderActionPanel", "liquid_detail_panel"),
                ("liquidRecorderAdvancedDetails", "liquid_advanced_section"),
            ):
                widget = page.findChild(QWidget, object_name)
                assert widget is not None, object_name
                assert widget.property("liquidRole") == role

            assert "RECORDER COMMAND" in labels
            assert "Flight Recorder" in labels
            assert "What can I capture, buffer, and review?" in labels
            assert "placeholder / static shell foundation" not in labels.casefold()
            continue
        if definition.mode_id == "support":
            for object_name, role in (
                ("liquidSupportStatusRail", "liquid_status_rail"),
                ("liquidSupportHero", "liquid_hero_panel"),
                ("liquidSupportHelpTopicsPanel", "liquid_inspector_panel"),
                ("liquidSupportParameterReference", "liquid_detail_panel"),
                ("liquidSupportAdvancedDetails", "liquid_advanced_section"),
            ):
                widget = page.findChild(QWidget, object_name)
                assert widget is not None, object_name
                assert widget.property("liquidRole") == role

            assert "SUPPORT / HELP / DOCS" in labels
            assert "Help / Docs" in labels
            assert "How do I understand and use HelmForge?" in labels
            assert "placeholder / static shell foundation" not in labels.casefold()
            continue
        for object_name, role in (
            (f"liquidModeStatusRail_{definition.mode_id}", "liquid_status_cluster"),
            (f"liquidHeroRegion_{definition.mode_id}", "liquid_hero_region"),
            (f"liquidContextInspectorRegion_{definition.mode_id}", "liquid_context_inspector_region"),
            (f"liquidDetailActionRegion_{definition.mode_id}", "liquid_detail_action_region"),
            (f"liquidAdvancedRegion_{definition.mode_id}", "liquid_advanced_region"),
        ):
            widget = page.findChild(QWidget, object_name)
            assert widget is not None, object_name
            assert widget.property("liquidRole") == role

        assert "LIQUID COMMAND DECK" in labels
        assert expected_hero_titles[definition.mode_id] in labels
        assert "placeholder / static shell foundation" in labels.casefold()


def test_lcd_1r_top_bar_is_command_deck_status_capsule():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())

    for object_name, role in (
        ("liquidCommandOrb", "liquid_command_orb"),
        ("liquidTopStatusCapsule", "liquid_status_cluster"),
        ("liquidTopCommandCluster", "liquid_command_cluster"),
        ("liquidTopStatusRail", "liquid_status_rail"),
    ):
        widget = shell.findChild(QWidget, object_name)
        assert widget is not None, object_name
        assert widget.property("liquidRole") == role


def test_lcd_1r_sources_exclude_motion_blur_runtime_authority_and_false_claims():
    liquid_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "v3_app" / "liquid").rglob("*.py")
    )

    for forbidden in (
        "QPropertyAnimation",
        "QGraphicsBlurEffect",
        "QTimer",
        "open_radial",
        "radial_menu",
        "EmbeddedBridgeRuntime",
        "BridgeCommandClient",
        "save_workspace(",
        "build_runtime_preflight_status(",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
    ):
        assert forbidden.casefold() not in liquid_sources.casefold()

    for forbidden_claim in (
        "Live Output Active",
        "vJoy Writing",
        "Recording Ready",
        "Capture active",
        "Bridge Managed",
        "Auto-save",
    ):
        assert forbidden_claim.casefold() not in liquid_sources.casefold()


def test_lcd_1r_report_documents_recomposition_and_deferred_scope():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-1r-static-shell-recomposition-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-1R Static Shell Recomposition",
        "why LCD-1R was needed",
        "too Legacy-like",
        "dock was corrected",
        "workspace composition was corrected",
        "placeholder pages now prepare",
        "runtime truth preservation",
        "no full page rebuilds were implemented",
        "no animations were added",
        "no radial menu was added",
        "no real blur/distortion was added",
        "no runtime authority was changed",
        "no hardware polling was changed",
        "no vJoy/output behavior was changed",
        "no output verification behavior was changed",
        "no Bridge lifecycle management was added",
        "no recorder capture/encoding was added",
        "no cloud AI/LLM behavior was added",
        "no auto-save was added",
    ):
        assert required in text
