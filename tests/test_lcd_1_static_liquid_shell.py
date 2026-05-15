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
        messages=("Simulation mode selected because live output is not verified.",),
    )


def _state():
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(_runtime_status())
    state.active_profile = "LCD Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = False
    state.status_message = "LCD-1 shell host ready; actions are placeholders."
    return state


def test_lcd_1_liquid_command_shell_constructs_offscreen():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())

    assert shell.objectName() == "liquidCommandShell"
    assert shell.findChild(QWidget, "liquidTopCommandBar") is not None
    assert shell.findChild(QWidget, "liquid_floating_mode_dock") is not None
    assert shell.findChild(QWidget, "liquidCommandWorkspace") is not None
    assert shell.findChild(QWidget, "liquid_page_host") is not None
    assert shell.findChild(QWidget, "liquid_floating_footer_strip") is not None


def test_lcd_1_mode_dock_contains_required_modes_and_switches_placeholders():
    _app()

    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.navigation import LIQUID_MODE_IDS, REQUIRED_LIQUID_MODES

    shell = LiquidCommandShell(state=_state())
    dock_buttons = {
        button.property("modeId"): button
        for button in shell.findChildren(QPushButton)
        if button.property("uiRole") == "liquidModeDockButton"
    }

    assert tuple(dock_buttons) == LIQUID_MODE_IDS
    assert tuple(button.accessibleName() for button in dock_buttons.values()) == REQUIRED_LIQUID_MODES

    for mode_id, button in dock_buttons.items():
        button.click()
        page = shell.page_host.currentWidget()
        labels = "\n".join(label.text() for label in page.findChildren(QLabel))
        assert shell.active_mode_id == mode_id
        if mode_id == "preflight":
            assert "Command Readiness" in labels
            assert "Can I safely use live output right now?" in labels
            assert "Placeholder / static shell foundation" not in labels
        elif mode_id == "mapping":
            assert "HOTAS Map" in labels
            assert "What is each physical control doing?" in labels
            assert "Placeholder / static shell foundation" not in labels
        elif mode_id == "tuning":
            assert "Base Tuning" in labels
            assert "How does this axis respond and feel?" in labels
            assert "Placeholder / static shell foundation" not in labels
        elif mode_id == "analysis":
            assert "Effective Response Stack" in labels
            assert "How does raw input become final output?" in labels
            assert "Placeholder / static shell foundation" not in labels
        elif mode_id == "recorder":
            assert "Flight Recorder" in labels
            assert "What can I capture, buffer, and review?" in labels
            assert "Placeholder / static shell foundation" not in labels
        else:
            assert "Help / Docs" in labels
            assert "How do I understand and use HelmForge?" in labels
            assert "Placeholder / static shell foundation" not in labels
        assert button.property("active") is True


def test_lcd_1_top_bar_surfaces_truthful_workspace_status_without_live_claims():
    _app()

    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    labels = "\n".join(label.text() for label in shell.findChildren(QLabel))
    buttons = "\n".join(button.text() for button in shell.findChildren(QPushButton))
    text = f"{labels}\n{buttons}"

    for required in (
        "HelmForge",
        "LCD Test Workspace",
        "Unsaved",
        "Blocked Missing Device",
        "Source: hotas_bridge_config_v3.json",
        "Helm",
    ):
        assert required in text

    for forbidden in (
        "Live Output Active",
        "vJoy Writing",
        "Recording Ready",
        "Bridge Managed",
        "Auto-save",
    ):
        assert forbidden.casefold() not in text.casefold()


def test_lcd_1_footer_actions_are_static_disabled_placeholders():
    _app()

    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    footer = shell.findChild(QLabel, "liquidFooterStatusMessage")
    buttons = {
        button.objectName(): button
        for button in shell.findChildren(QPushButton)
        if button.objectName().startswith("liquidFooter")
    }

    assert footer is not None
    assert "placeholder" in footer.text()
    assert set(buttons) == {
        "liquidFooterApplyButton",
        "liquidFooterSaveButton",
        "liquidFooterRevertButton",
    }
    assert all(not button.isEnabled() for button in buttons.values())


def test_lcd_1_placeholder_page_registry_is_complete_and_truth_safe():
    _app()

    from v3_app.liquid.navigation import LIQUID_MODE_IDS
    from v3_app.liquid.pages.placeholder_pages import LIQUID_PLACEHOLDER_PAGES

    assert tuple(page.mode_id for page in LIQUID_PLACEHOLDER_PAGES) == LIQUID_MODE_IDS
    text = "\n".join(
        f"{page.title}\n{page.purpose}\n{page.placeholder_notice}"
        for page in LIQUID_PLACEHOLDER_PAGES
    )

    for required in ("Preflight", "Mapping", "Tuning", "Analysis", "Recorder", "Support"):
        assert required in text

    for forbidden in (
        "Recording Ready",
        "Capture active",
        "Bridge managed",
        "auto-save",
    ):
        assert forbidden.casefold() not in text.casefold()


def test_lcd_1_liquid_shell_does_not_instantiate_legacy_primary_layout():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())

    assert shell.findChild(QWidget, "appSidebar") is None
    assert shell.findChild(QWidget, "pageStack") is None
    assert shell.findChild(QWidget, "appHeader") is None
    assert shell.findChild(QWidget, "appFooter") is None
    assert not hasattr(shell, "sidebar")

    liquid_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "v3_app" / "liquid").rglob("*.py")
    )
    assert "from v3_app.ui.shell import HelmForgeShell" not in liquid_sources
    assert "from v3_app.pages.mapping_page" not in liquid_sources
    assert "from v3_app.pages.preflight_page" not in liquid_sources


def test_lcd_1_no_runtime_authority_or_forbidden_features_added_to_liquid_sources():
    liquid_dir = PROJECT_ROOT / "v3_app" / "liquid"
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in liquid_dir.rglob("*.py"))

    for forbidden in (
        "EmbeddedBridgeRuntime",
        "BridgeCommandClient",
        "save_workspace(",
        "build_runtime_preflight_status(",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
        "QPropertyAnimation",
        "QGraphicsBlurEffect",
        "open_radial",
        "radial_menu",
        "auto_save",
    ):
        assert forbidden.casefold() not in source_text.casefold()


def test_lcd_1_main_window_can_select_liquid_shell_and_keep_selector_available():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.app import LEGACY_UI_SHELL, LIQUID_UI_SHELL, build_window, resolve_ui_shell

    liquid_window = build_window(title="HelmForge Test", state=_state(), ui_shell="liquid")

    assert liquid_window.findChild(QWidget, "liquidCommandShell") is not None
    assert liquid_window.findChild(QWidget, "appSidebar") is None
    assert resolve_ui_shell("liquid") == LIQUID_UI_SHELL
    assert resolve_ui_shell("legacy") == LEGACY_UI_SHELL


def test_lcd_1_report_documents_scope_architecture_and_truth_boundaries():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-1-static-liquid-shell-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-1 Static Liquid Shell",
        "new module structure",
        "shell architecture",
        "Legacy fallback",
        "backend/data surfaces reused",
        "LCD-2",
        "runtime truth preservation",
        "No animations, real blur, distortion, radial menu",
        "No hardware polling changes",
        "No vJoy/output behavior changes",
        "No output verification changes",
        "No Bridge lifecycle management",
        "No recorder capture or encoding",
        "No cloud AI/LLM behavior",
        "No auto-save",
    ):
        assert required in text
