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

EXPECTED_SUBPAGES = {
    "preflight": (("command_readiness", "Command Readiness", "preflight.command_readiness"),),
    "mapping": (
        ("hotas_map", "HOTAS Map", "mapping.hotas_map"),
        ("route_details", "Route Details", "mapping.route_details"),
        ("advanced_route_tables", "Advanced Route Tables", "mapping.advanced_route_tables"),
    ),
    "tuning": (
        ("base_tuning", "Base Tuning", "tuning.base_tuning"),
        ("filtering", "Filtering", "tuning.filtering"),
        ("combat_profile", "Combat Profile", "tuning.combat_profile"),
        ("conditional_rules", "Conditional Rules", "tuning.conditional_rules"),
        ("profiles_library", "Profiles Library", "tuning.profiles_library"),
    ),
    "analysis": (
        ("effective_response_stack", "Effective Response Stack", "analysis.effective_response_stack"),
        ("live_monitor", "Live Monitor", "analysis.live_monitor"),
    ),
    "recorder": (
        ("flight_recorder", "Flight Recorder", "recorder.flight_recorder"),
        ("clip_library", "Clip Library / Artifacts", "recorder.clip_library"),
        ("capture_backend_truth", "Capture Backend Truth", "recorder.capture_backend_truth"),
    ),
    "support": (
        ("help_docs", "Help / Docs", "support.help_docs"),
        ("perf_diagnostics", "Perf / Diagnostics", "support.perf_diagnostics"),
        ("setup_runtime_check", "Setup / Runtime Check", "support.setup_runtime_check"),
    ),
}


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
    state.active_profile = "LCD-3 Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = False
    state.status_message = "LCD-3 navigation architecture loaded; route pages remain placeholders."
    return state


def _texts(widget) -> list[str]:
    from PySide6.QtWidgets import QLabel, QPushButton

    return [label.text() for label in widget.findChildren(QLabel)] + [
        button.text() for button in widget.findChildren(QPushButton)
    ]


def _text_blob(widget) -> str:
    return "\n".join(_texts(widget))


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


def test_lcd_3_navigation_model_contains_required_modes_subpages_and_unique_routes():
    from v3_app.liquid.models.nav_model import build_liquid_navigation_model
    from v3_app.liquid.pages.placeholder_pages import LIQUID_ROUTE_PAGE_FACTORIES

    model = build_liquid_navigation_model()

    assert tuple(mode.mode_id for mode in model.modes) == tuple(EXPECTED_SUBPAGES)
    assert tuple(mode.display_name for mode in model.modes) == (
        "Preflight",
        "Mapping",
        "Tuning",
        "Analysis",
        "Recorder",
        "Support",
    )

    route_keys = []
    for mode in model.modes:
        expected = EXPECTED_SUBPAGES[mode.mode_id]
        assert mode.default_subpage_id == expected[0][0]
        assert mode.default_subpage.route_key == expected[0][2]
        assert mode.glyph
        assert mode.short_description
        assert mode.accent_role
        assert mode.tooltip
        assert mode.accessibility_text

        seen_subpage_ids = set()
        for subpage, expected_tuple in zip(mode.subpages, expected, strict=True):
            subpage_id, display_name, route_key = expected_tuple
            assert subpage.subpage_id == subpage_id
            assert subpage.display_name == display_name
            assert subpage.route_key == route_key
            assert subpage.parent_mode_id == mode.mode_id
            assert subpage.purpose
            assert subpage.tooltip
            assert subpage.accessibility_text
            assert subpage.subpage_id not in seen_subpage_ids
            seen_subpage_ids.add(subpage.subpage_id)
            route_keys.append(subpage.route_key)

    assert len(route_keys) == len(set(route_keys))
    assert set(route_keys) == set(LIQUID_ROUTE_PAGE_FACTORIES)


def test_lcd_3_route_registry_exposes_distinct_route_factories():
    _app()

    from v3_app.liquid.models.nav_model import build_liquid_navigation_model
    from v3_app.liquid.pages.placeholder_pages import LIQUID_ROUTE_PAGE_FACTORIES

    model = build_liquid_navigation_model()
    for route in model.routes:
        factory = LIQUID_ROUTE_PAGE_FACTORIES[route.route_key]
        page = factory()
        text = _text_blob(page)

        assert route.mode_display_name in text
        assert route.subpage_display_name in text
        assert route.purpose in text
        if route.route_key == "preflight.command_readiness":
            assert page.objectName() == "liquidPreflightCommandPage"
            assert route.route_key not in text
            assert "Placeholder route" not in text
            assert "future page rebuild" not in text.casefold()
        elif route.route_key == "mapping.hotas_map":
            assert page.objectName() == "liquidMappingCommandPage"
            assert "What is each physical control doing?" in text
            assert "Placeholder route" not in text
            assert "future page rebuild" not in text.casefold()
        elif route.route_key == "mapping.route_details":
            assert page.objectName() == "liquidMappingRouteDetailsPage"
            assert "Draft mapping change" in text
            assert "Placeholder route" not in text
            assert "future page rebuild" not in text.casefold()
        elif route.route_key == "mapping.advanced_route_tables":
            assert page.objectName() == "liquidMappingAdvancedRouteTablesPage"
            assert "Compact editable rows" in text
            assert "Placeholder route" not in text
            assert "future page rebuild" not in text.casefold()
        elif route.route_key == "tuning.profiles_library":
            assert page.objectName() == "liquidTuningProfilesLibraryPage"
            assert "Profiles Library" in text
            assert "Placeholder route" not in text
            assert "future page rebuild" not in text.casefold()
        elif route.route_key.startswith("tuning."):
            assert page.objectName() == "liquidTuningCommandPage"
            assert "Placeholder route" not in text
            assert "future page rebuild" not in text.casefold()
        elif route.route_key.startswith("analysis."):
            assert page.objectName() == "liquidAnalysisCommandPage"
            assert route.purpose in text
            assert "Placeholder route" not in text
            assert "future page rebuild" not in text.casefold()
        elif route.route_key.startswith("recorder."):
            assert page.objectName() == "liquidRecorderCommandPage"
            assert route.purpose in text
            assert "Placeholder route" not in text
            assert "future page rebuild" not in text.casefold()
        else:
            assert route.route_key in text
            assert "Placeholder route" in text
            assert "future page rebuild" in text.casefold()


def test_lcd_3_liquid_shell_constructs_with_dock_selector_and_route_host():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.models.nav_model import build_liquid_navigation_model

    shell = LiquidCommandShell(state=_state())
    model = build_liquid_navigation_model()
    dock = shell.findChild(QWidget, "liquid_floating_mode_dock")
    selector = shell.findChild(QWidget, "liquid_subpage_selector")

    assert shell.objectName() == "liquidCommandShell"
    assert dock is not None
    assert selector is not None
    assert selector.property("liquidRole") == "liquid_subpage_selector"
    assert shell.findChild(QWidget, "liquid_page_host") is not None
    assert model.default_route.route_key == "preflight.command_readiness"
    assert shell.current_route_key == "mapping.hotas_map"
    assert shell.active_mode_id == "mapping"
    assert shell.active_subpage_id == "hotas_map"

    buttons = _dock_buttons(shell)
    assert tuple(buttons) == tuple(EXPECTED_SUBPAGES)
    for mode in model.modes:
        button = buttons[mode.mode_id]
        assert button.accessibleName() == mode.accessibility_text
        assert button.toolTip() == mode.tooltip
        assert button.property("dockDensity") == "floating_glyph"
        assert not button.text() == mode.display_name

    assert shell.findChild(QWidget, "appSidebar") is None
    assert shell.findChild(QWidget, "pageStack") is None


def test_lcd_3_dock_mode_selection_uses_default_route_and_selected_state():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    buttons = _dock_buttons(shell)

    buttons["tuning"].click()

    assert shell.active_mode_id == "tuning"
    assert shell.active_subpage_id == "base_tuning"
    assert shell.current_route_key == "tuning.base_tuning"
    assert buttons["tuning"].isChecked()
    assert buttons["tuning"].property("active") is True
    assert buttons["preflight"].property("active") is False
    assert "Tuning" in _text_blob(shell.page_host.currentWidget())
    assert "Base Tuning" in _text_blob(shell.page_host.currentWidget())
    assert "How does this axis respond and feel?" in _text_blob(shell.page_host.currentWidget())

    buttons["mapping"].click()

    assert shell.active_mode_id == "mapping"
    assert shell.active_subpage_id == "hotas_map"
    assert shell.current_route_key == "mapping.hotas_map"
    assert "Mapping" in _text_blob(shell.page_host.currentWidget())
    assert "HOTAS Map" in _text_blob(shell.page_host.currentWidget())
    assert "What is each physical control doing?" in _text_blob(shell.page_host.currentWidget())


def test_lcd_3_subpage_selector_filters_selected_mode_and_switches_routes():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    _dock_buttons(shell)["tuning"].click()

    buttons = _subpage_buttons(shell)
    assert [button.property("subpageId") for button in buttons] == [
        "base_tuning",
        "filtering",
        "combat_profile",
        "conditional_rules",
        "profiles_library",
    ]
    assert [button.property("routeKey") for button in buttons] == [
        "tuning.base_tuning",
        "tuning.filtering",
        "tuning.combat_profile",
        "tuning.conditional_rules",
        "tuning.profiles_library",
    ]
    assert buttons[0].property("active") is True
    assert all(button.accessibleName().startswith("Tuning / ") for button in buttons)
    assert all(button.toolTip() for button in buttons)

    buttons[1].click()

    assert shell.active_mode_id == "tuning"
    assert shell.active_subpage_id == "filtering"
    assert shell.current_route_key == "tuning.filtering"
    assert buttons[1].isChecked()
    assert buttons[1].property("active") is True
    assert "Filtering" in _text_blob(shell.page_host.currentWidget())
    assert "How should noisy input be smoothed?" in _text_blob(shell.page_host.currentWidget())


def test_lcd_3_per_mode_session_subpage_memory_restores_last_selected_route():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    _dock_buttons(shell)["tuning"].click()
    combat_button = [
        button for button in _subpage_buttons(shell) if button.property("subpageId") == "combat_profile"
    ][0]
    combat_button.click()
    assert shell.current_route_key == "tuning.combat_profile"

    _dock_buttons(shell)["support"].click()
    assert shell.current_route_key == "support.help_docs"

    _dock_buttons(shell)["tuning"].click()
    assert shell.active_subpage_id == "combat_profile"
    assert shell.current_route_key == "tuning.combat_profile"
    assert "Combat Profile" in _text_blob(shell.page_host.currentWidget())


def test_lcd_3_radial_anchor_future_only_and_forbidden_architecture_absent():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    anchor = shell.findChild(QWidget, "liquid_radial_anchor_orb")
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "v3_app" / "liquid").rglob("*.py")
    )
    visible_text = _text_blob(shell)

    assert anchor is not None
    assert anchor.property("futureOnly") is True
    assert "future" in anchor.toolTip().casefold()
    assert not hasattr(anchor, "open_radial_menu")

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
        "Full Live Runtime Ready",
        "Live Output Active",
        "Output Verified",
        "HOTAS connected",
        "vJoy writing",
        "Bridge managed",
        "Recording Ready",
        "Capture active",
        "Auto-save",
    ):
        assert forbidden_claim.casefold() not in visible_text.casefold()


def test_lcd_3_report_documents_scope_deferrals_and_truth_boundaries():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-3-navigation-mode-architecture-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-3 Navigation and Mode Architecture",
        "navigation model structure",
        "required major modes",
        "required subpages",
        "route key strategy",
        "dock selection behavior",
        "subpage selector behavior",
        "page host routing behavior",
        "session state behavior",
        "Legacy fallback/reference is preserved",
        "radial anchor remains future-only",
        "LCD-4 through LCD-9",
        "LCD-10 through LCD-12",
        "layout/overlap preservation",
        "demo truth consistency",
        "runtime truth preservation",
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
