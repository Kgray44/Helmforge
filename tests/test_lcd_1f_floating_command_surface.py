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
    state.active_profile = "LCD-1F Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = False
    state.status_message = "LCD-1F floating command surface loaded; actions remain placeholders."
    return state


def test_lcd_1f_unified_command_surface_hosts_floating_layers():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())

    for object_name, role in (
        ("liquid_command_surface", "liquid_command_surface"),
        ("liquid_surface_glass_field", "liquid_surface_glass_field"),
        ("liquid_page_host", "liquid_page_host"),
        ("liquid_floating_mode_dock", "liquid_floating_mode_dock"),
        ("liquid_floating_footer_strip", "liquid_floating_footer_strip"),
    ):
        widget = shell.findChild(QWidget, object_name)
        assert widget is not None, object_name
        assert widget.property("liquidRole") == role


def test_lcd_1f_mode_dock_floats_and_preserves_full_mode_names():
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
    assert dock.maximumWidth() <= LiquidLayout.mode_dock_width
    assert dock.property("floatingLayer") is True
    assert [button.property("modeId") for button in buttons] == list(LIQUID_MODE_IDS)
    assert [button.accessibleName() for button in buttons] == list(REQUIRED_LIQUID_MODES)
    assert all(button.toolTip().startswith(button.accessibleName()) for button in buttons)
    assert all(button.property("dockDensity") == "floating_glyph" for button in buttons)
    assert all(1 <= len(button.text()) <= 2 for button in buttons)
    assert not any(button.text() in REQUIRED_LIQUID_MODES for button in buttons)


def test_lcd_1f_radial_anchor_orb_exists_without_menu_behavior():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    anchor = shell.findChild(QWidget, "liquid_radial_anchor_orb")

    assert anchor is not None
    assert anchor.property("liquidRole") == "liquid_radial_anchor_orb"
    assert anchor.property("futureOnly") is True
    assert "future quick switch anchor" in anchor.toolTip().casefold()
    assert not hasattr(anchor, "open_radial_menu")


def test_lcd_1f_footer_is_floating_hud_strip_with_disabled_actions():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    footer = shell.findChild(QWidget, "liquid_floating_footer_strip")
    buttons = {
        button.objectName(): button
        for button in shell.findChildren(QPushButton)
        if button.objectName().startswith("liquidFooter")
    }

    assert footer is not None
    assert footer.property("floatingLayer") is True
    assert set(buttons) == {
        "liquidFooterApplyButton",
        "liquidFooterSaveButton",
        "liquidFooterRevertButton",
    }
    assert all(not button.isEnabled() for button in buttons.values())


def test_lcd_1f_all_modes_keep_embedded_placeholder_regions():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.pages.placeholder_pages import LIQUID_PLACEHOLDER_PAGES

    shell = LiquidCommandShell(state=_state())

    assert {page.mode_id for page in LIQUID_PLACEHOLDER_PAGES} == {
        "preflight",
        "mapping",
        "tuning",
        "analysis",
        "recorder",
        "support",
    }

    for definition in LIQUID_PLACEHOLDER_PAGES:
        shell.switch_mode(definition.mode_id)
        page = shell.page_host.currentWidget()
        if definition.mode_id == "preflight":
            assert page.findChild(QWidget, "liquidPreflightHeroGoNoGo") is not None
            assert page.findChild(QWidget, "liquidPreflightSystemDetails") is not None
            assert page.findChild(QWidget, "liquidPreflightActionPanel") is not None
            continue
        if definition.mode_id == "mapping":
            assert page.findChild(QWidget, "liquidMappingHotasHero") is not None
            assert page.findChild(QWidget, "liquidMappingInspector") is not None
            assert page.findChild(QWidget, "liquidMappingRouteFlowPanel") is not None
            continue
        if definition.mode_id == "tuning":
            assert page.findChild(QWidget, "liquidTuningHero") is not None
            assert page.findChild(QWidget, "liquidTuningAxisSelectorPanel") is not None
            assert page.findChild(QWidget, "liquidTuningParameterInspector") is not None
            assert page.findChild(QWidget, "liquidTuningAdvancedDetails") is not None
            continue
        if definition.mode_id == "analysis":
            assert page.findChild(QWidget, "liquidAnalysisPipelineHero") is not None
            assert page.findChild(QWidget, "liquidAnalysisAxisInspector") is not None
            assert page.findChild(QWidget, "liquidAnalysisStageDetails") is not None
            assert page.findChild(QWidget, "liquidAnalysisAdvancedDetails") is not None
            continue
        if definition.mode_id == "recorder":
            assert page.findChild(QWidget, "liquidRecorderStatusHero") is not None
            assert page.findChild(QWidget, "liquidRecorderCapabilityPanel") is not None
            assert page.findChild(QWidget, "liquidRecorderActionPanel") is not None
            assert page.findChild(QWidget, "liquidRecorderAdvancedDetails") is not None
            continue
        for suffix in (
            "liquidHeroRegion",
            "liquidContextInspectorRegion",
            "liquidDetailActionRegion",
        ):
            region = page.findChild(QWidget, f"{suffix}_{definition.mode_id}")
            assert region is not None
            assert region.property("embeddedOnCommandSurface") is True


def test_lcd_1f_no_legacy_primary_stack_motion_blur_or_runtime_authority():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "v3_app" / "liquid").rglob("*.py")
    )

    assert shell.findChild(QWidget, "appSidebar") is None
    assert shell.findChild(QWidget, "pageStack") is None
    assert shell.findChild(QWidget, "appHeader") is None
    assert shell.findChild(QWidget, "appFooter") is None

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
        "Full Live Runtime Ready",
        "Live Output Active",
        "Output Verified",
        "vJoy Writing",
        "Recording Ready",
        "Capture active",
        "Bridge Managed",
        "Auto-save",
    ):
        assert forbidden.casefold() not in source_text.casefold()


def test_lcd_1f_report_documents_floating_surface_correction():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-1f-floating-command-surface-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-1F Floating Command Surface",
        "why this correction was needed",
        "still too sectioned/sidebar-like",
        "floating dock",
        "floating footer",
        "future radial navigation is prepared but not implemented",
        "no pages/features were removed",
        "LCD-2",
        "LCD-3",
        "runtime truth preservation",
    ):
        assert required in text
