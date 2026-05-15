from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint

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
    state.active_profile = "LCD-3F Polish Workspace"
    state.source_config = (
        r"C:\Users\kkids\Documents\HOTAS-Control-Panel\profiles\hotas_bridge_config_v3.long.workspace.json"
    )
    state.saved = False
    state.status_message = "LCD-3F shell polish smoke; footer actions remain placeholders."
    return state


def _texts(widget) -> list[str]:
    from PySide6.QtWidgets import QLabel, QPushButton

    return [label.text() for label in widget.findChildren(QLabel)] + [
        button.text() for button in widget.findChildren(QPushButton)
    ]


def _text_blob(widget) -> str:
    return "\n".join(_texts(widget))


def _rect_in_shell(widget, shell):
    top_left = widget.mapTo(shell, QPoint(0, 0))
    return widget.geometry().translated(top_left - widget.geometry().topLeft())


def _dock_buttons(shell):
    from PySide6.QtWidgets import QPushButton

    return {
        button.property("modeId"): button
        for button in shell.findChildren(QPushButton)
        if button.property("uiRole") == "liquidModeDockButton"
    }


def _subpage_buttons(shell):
    from PySide6.QtWidgets import QPushButton

    return [
        button
        for button in shell.findChildren(QPushButton)
        if button.property("uiRole") == "liquidSubpageSelectorButton"
    ]


def test_lcd_3f_liquid_shell_has_styled_tooltip_and_scrollbar_contract():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    style_sheet = shell.styleSheet()

    assert shell.findChild(QWidget, "liquid_floating_mode_dock") is not None
    assert shell.findChild(QWidget, "liquid_subpage_selector") is not None
    assert shell.findChild(QWidget, "liquid_page_host") is not None
    assert shell.findChild(QWidget, "appSidebar") is None
    assert shell.findChild(QWidget, "pageStack") is None
    assert "QToolTip" in style_sheet
    assert "QScrollBar:vertical" in style_sheet
    assert "background: #fff" not in style_sheet.casefold()


def test_lcd_3f_dock_uses_short_liquid_hover_labels_and_fit_roles():
    app = _app()

    from PySide6.QtWidgets import QLabel, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.models.nav_model import build_liquid_navigation_model
    from v3_app.liquid.navigation import LIQUID_MODE_IDS

    shell = LiquidCommandShell(state=_state())
    dock = shell.findChild(QWidget, "liquid_floating_mode_dock")
    hover_label = shell.findChild(QLabel, "liquidDockHoverLabel")
    active_label = shell.findChild(QLabel, "liquidDockActiveLabel")
    buttons = _dock_buttons(shell)
    model = build_liquid_navigation_model()
    modes_by_id = {mode.mode_id: mode for mode in model.modes}

    assert dock is not None
    assert hover_label is not None
    assert hover_label.property("liquidRole") == "liquid_dock_hover_label"
    assert active_label is not None
    assert active_label.property("liquidRole") == "liquid_dock_active_label"
    assert tuple(buttons) == tuple(LIQUID_MODE_IDS)

    for mode_id, button in buttons.items():
        mode = modes_by_id[mode_id]
        assert button.accessibleName() == mode.display_name
        assert button.property("hoverLabel") == mode.display_name
        assert button.toolTip() == mode.display_name
        assert ":" not in button.toolTip()
        assert len(button.toolTip()) <= 10
        assert button.statusTip() == mode.short_description
        assert button.minimumWidth() >= 50
        assert button.minimumHeight() >= 44
        assert 1 <= len(button.text()) <= 2
        assert button.text() != mode.display_name

    app.sendEvent(buttons["analysis"], QEvent(QEvent.Type.Enter))
    app.processEvents()
    assert hover_label.text() == "Analysis"

    assert active_label.text() in {mode.display_name for mode in model.modes}
    assert not active_label.text().startswith((">", "/", "\\", "|"))
    assert active_label.minimumWidth() >= 68


def test_lcd_3f_top_status_source_and_helm_area_are_compact():
    _app()

    from PySide6.QtWidgets import QLabel, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    state = _state()
    shell = LiquidCommandShell(state=state)

    source_chip = shell.findChild(QLabel, "liquidSourceChip")
    helm_cluster = shell.findChild(QWidget, "liquidTopCommandCluster")
    helm_button = shell.findChild(QWidget, "liquidHelmButton")

    assert source_chip is not None
    assert source_chip.text().startswith("Source:")
    assert source_chip.text() != f"Source: {state.source_config}"
    assert len(source_chip.text()) <= 34
    assert "..." in source_chip.text() or "Bridge Config" in source_chip.text()
    assert state.source_config in source_chip.toolTip()
    assert state.source_config in source_chip.accessibleDescription()

    assert helm_cluster is not None
    assert helm_cluster.property("compactActionCluster") is True
    assert 0 < helm_cluster.maximumWidth() <= 180
    assert helm_button is not None
    assert helm_button.toolTip() == "Helm"
    assert "liquid helm assistant" in helm_button.statusTip().casefold()
    assert "workspace draft" in helm_button.statusTip().casefold()


def test_lcd_3f_page_header_selector_and_route_chips_are_product_facing():
    _app()

    from PySide6.QtWidgets import QLabel, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    shell.switch_mode("mapping")
    shell.switch_subpage("route_details")

    selector = shell.findChild(QWidget, "liquid_subpage_selector")
    selector_label = shell.findChild(QLabel, "liquidSubpageSelectorModeLabel")
    buttons = _subpage_buttons(shell)
    page = shell.page_host.currentWidget()
    edit_header = page.findChild(QWidget, "liquidMappingEditHeader_mapping_route_details")

    assert selector is not None
    assert selector.property("selectorStyle") == "segmented_route_strip"
    assert selector_label is not None
    assert selector_label.text() == "Mapping routes"
    assert [button.property("modeId") for button in buttons] == ["mapping", "mapping", "mapping"]
    assert [button.property("subpageId") for button in buttons] == [
        "hotas_map",
        "route_details",
        "advanced_route_tables",
    ]
    assert any(button.property("active") is True and button.text() == "Route Details" for button in buttons)

    page_text = _text_blob(page)
    assert edit_header is not None
    assert edit_header.property("componentRole") == "MappingEditPageHeader"
    assert "Mapping / Route Details" in page_text
    assert "Draft mapping change" in page_text
    assert "Output proof unchanged" in page_text
    assert "How does this physical control route through workspace intent?" in page_text
    assert "Placeholder route:" not in page_text
    assert "Future page rebuild placeholder" not in page_text
    assert "Static route" not in page_text


def test_lcd_3f_footer_strip_is_preserved_without_opaque_bottom_slab():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    shell.resize(1360, 800)
    shell.show()
    app.processEvents()

    footer = shell.findChild(QWidget, "liquid_floating_footer_strip")
    clearance = shell.findChild(QWidget, "liquid_footer_clearance")
    surface_field = shell.findChild(QWidget, "liquid_surface_glass_field")
    page_host = shell.findChild(QWidget, "liquid_page_host")

    assert footer is not None
    assert footer.property("floatingLayer") is True
    assert clearance is not None
    assert clearance.property("footerClearance") is True
    assert clearance.property("footerClearanceTransparent") is True
    assert clearance.property("footerScrim") == "none"
    assert 80 <= clearance.height() <= 92
    assert surface_field is not None
    assert surface_field.property("footerScrim") == "none"

    footer_rect = _rect_in_shell(footer, shell)
    page_host_rect = _rect_in_shell(page_host, shell)
    assert page_host_rect.bottom() <= footer_rect.top() + 4


def test_lcd_3f_preserves_routes_and_deferred_runtime_boundaries():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.models.nav_model import build_liquid_navigation_model

    shell = LiquidCommandShell(state=_state())
    model = build_liquid_navigation_model()
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "v3_app" / "liquid").rglob("*.py")
    )

    assert {route.route_key for route in model.routes} == {
        "preflight.command_readiness",
        "mapping.hotas_map",
        "mapping.route_details",
        "mapping.advanced_route_tables",
        "tuning.base_tuning",
        "tuning.filtering",
        "tuning.combat_profile",
        "tuning.conditional_rules",
        "tuning.profiles_library",
        "analysis.effective_response_stack",
        "analysis.live_monitor",
        "recorder.flight_recorder",
        "recorder.clip_library",
        "recorder.capture_backend_truth",
        "support.help_docs",
        "support.perf_diagnostics",
        "support.setup_runtime_check",
    }

    _dock_buttons(shell)["recorder"].click()
    assert shell.current_route_key == "recorder.flight_recorder"
    assert "Flight Recorder" in _text_blob(shell.page_host.currentWidget())
    assert "Capture backend unavailable" in _text_blob(shell.page_host.currentWidget())

    for forbidden in (
        "from v3_app.ui.shell import HelmForgeShell",
        "from v3_app.pages.mapping_page",
        "from v3_app.pages.preflight_page",
        "QPropertyAnimation",
        "QGraphicsBlurEffect",
        "QGraphicsOpacityEffect",
        "open_radial",
        "radial_menu",
        "EmbeddedBridgeRuntime",
        "BridgeCommandClient",
        "save_workspace(",
        "build_runtime_preflight_status(",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
    ):
        assert forbidden.casefold() not in source_text.casefold()

    for forbidden_claim in (
        "Live Output Active",
        "HOTAS connected",
        "vJoy writing",
        "Bridge managed",
        "Recording Ready",
        "Capture active",
        "Auto-save",
    ):
        assert forbidden_claim.casefold() not in _text_blob(shell).casefold()


def test_lcd_3f_report_documents_scope_polish_and_deferrals():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-3f-navigation-ui-fit-shell-polish-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-3F Navigation UI Fit",
        "why LCD-3F was needed",
        "dock hover/tooltip fix",
        "dock glyph/selected-label fit fix",
        "top status chip clipping fix",
        "Helm action area fix",
        "page header/subpage selector cleanup",
        "scrollbar styling fix",
        "oversized footer background slab/scrim fix",
        "footer clearance strategy",
        "route/demo chip wording cleanup",
        "demo truth consistency",
        "runtime truth preservation",
        "what remains for LCD-4",
        "no real page rebuilds were implemented",
        "no radial menu behavior was added",
        "no animations were added",
        "no page transitions were added",
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
