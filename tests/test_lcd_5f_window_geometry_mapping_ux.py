from __future__ import annotations

import os
from pathlib import Path

from shared_core.models.workspace import create_default_workspace


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _state(*, active_page_id: str = "mapping"):
    from shared_core.models.runtime import (
        InputDeviceDetection,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )
    from v3_app.services.app_state import AppState

    runtime_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )
    state = AppState.from_runtime_status(runtime_status, active_page_id=active_page_id)
    state.active_profile = "LCD-5F Fixture"
    state.status_message = "Workspace ready."
    return state


def _text_blob(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join(labels + buttons)


def test_lcd_5f_safe_initial_window_geometry_clamps_to_available_screen():
    from PySide6.QtCore import QPoint, QRect, QSize
    from v3_app.app import safe_initial_window_geometry

    available = QRect(48, 72, 1280, 720)
    geometry = safe_initial_window_geometry(
        available,
        QSize(1800, 1100),
        preferred_top_left=QPoint(-500, -240),
    )

    assert available.contains(geometry)
    assert geometry.top() >= available.top()
    assert geometry.left() >= available.left()
    assert geometry.width() <= available.width()
    assert geometry.height() <= available.height()


def test_lcd_5f_safe_initial_window_geometry_centers_without_valid_saved_position():
    from PySide6.QtCore import QRect, QSize
    from v3_app.app import safe_initial_window_geometry

    available = QRect(100, 50, 1600, 900)
    geometry = safe_initial_window_geometry(available, QSize(1000, 620))

    assert available.contains(geometry)
    assert abs(geometry.center().x() - available.center().x()) <= 1
    assert abs(geometry.center().y() - available.center().y()) <= 1


def test_lcd_5f_liquid_launch_constructs_with_reset_geometry_flag():
    app = _app()

    from PySide6.QtGui import QGuiApplication
    from v3_app.app import build_window

    window = build_window(
        title="LCD-5F Geometry",
        state=_state(),
        ui_shell="liquid",
        reset_window_geometry=True,
    )
    app.processEvents()
    available = QGuiApplication.primaryScreen().availableGeometry()

    assert window.ui_shell == "liquid"
    assert window.property("resetWindowGeometry") is True
    assert window.property("safeWindowGeometryApplied") is True
    assert window.geometry().top() >= available.top()
    assert window.geometry().left() >= available.left()
    assert window.geometry().width() <= available.width()
    assert window.geometry().height() <= available.height()


def test_lcd_5f_reset_window_geometry_cli_is_forwarded(monkeypatch):
    from v3_app import main as main_module

    received: dict[str, object] = {}

    def fake_run_app(*, smoke_exit_ms=None, ui_shell=None, reset_window_geometry=False):
        received["smoke_exit_ms"] = smoke_exit_ms
        received["ui_shell"] = ui_shell
        received["reset_window_geometry"] = reset_window_geometry
        return 0

    monkeypatch.setattr(main_module, "run_app", fake_run_app)

    assert main_module.main(["--ui-shell", "liquid", "--reset-window-geometry", "--smoke-exit-ms", "1"]) == 0
    assert received == {
        "smoke_exit_ms": 1,
        "ui_shell": "liquid",
        "reset_window_geometry": True,
    }


def test_lcd_5f_mapping_page_explains_read_only_selection_mode():
    _app()

    from PySide6.QtWidgets import QPushButton
    from v3_app.liquid.pages.mapping_command_page import MappingCommandPage

    page = MappingCommandPage(state=_state(), workspace=create_default_workspace())
    text = _text_blob(page)

    assert "Read-only map: select controls to inspect routes." in text
    assert "Selection only" in text
    assert "workspace routes are not edited on this page" in text
    assert "Editing arrives in Mapping / Route Details." in text
    assert "Output Intent shown; no vJoy write is performed here." in text

    enabled_fake_edits = [
        button.text()
        for button in page.findChildren(QPushButton)
        if button.isEnabled()
        and any(word in button.text().casefold() for word in ("edit", "remap", "apply", "save"))
    ]
    assert enabled_fake_edits == []

    route_button = page.findChild(QPushButton, "liquidMappingOpenRouteDetailsButton")
    assert route_button is not None
    assert route_button.isEnabled() is False
    assert route_button.property("routeTarget") == "mapping.route_details"
    assert route_button.property("navigationOnly") is True


def test_lcd_5f_selected_control_selection_updates_without_workspace_mutation():
    _app()

    from v3_app.liquid.pages.mapping_command_page import MappingCommandPage

    workspace = create_default_workspace()
    before_routes = workspace.mappings
    page = MappingCommandPage(state=_state(), workspace=workspace)

    page.select_control("button_b6")
    inspector_text = _text_blob(page.findChild(object, "liquidMappingInspector"))
    route_text = _text_blob(page.findChild(object, "liquidMappingRouteFlowPanel"))

    assert page.selected_control_id == "button_b6"
    assert "B6" in inspector_text
    assert "Selection only" in inspector_text
    assert "Output Intent" in inspector_text
    assert "Button 6" in route_text
    assert "Output Intent: Button 6" in route_text
    assert workspace.mappings == before_routes


def test_lcd_5f_advanced_route_details_are_summary_preview_not_full_route_flood():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.models.mapping_command_model import build_mapping_command_model
    from v3_app.liquid.pages.mapping_command_page import MappingCommandPage

    workspace = create_default_workspace()
    model = build_mapping_command_model(state=_state(), workspace=workspace)
    page = MappingCommandPage(state=_state(), workspace=workspace)
    advanced = page.findChild(QWidget, "liquidMappingAdvancedRouteDetails")
    detail_rows = [
        widget
        for widget in advanced.findChildren(QWidget)
        if widget.property("advancedRouteDetailRow") is True
    ]
    text = _text_blob(advanced)

    assert len(model.advanced_route_details) >= 22
    assert 1 <= len(detail_rows) <= 6
    assert advanced.findChild(QWidget, "liquidMappingAdvancedCounts") is not None
    assert advanced.findChild(QWidget, "liquidMappingAdvancedPreviewList") is not None
    assert "Selected route detail" in text
    assert "Preview routes" in text
    assert "Full route table belongs in Mapping / Advanced Route Tables." in text
    assert "Open Advanced Route Tables" in text


def test_lcd_5f_mapping_truth_and_preflight_freeze_boundaries_remain_intact(monkeypatch):
    app = _app()

    from PySide6.QtWidgets import QWidget
    from shared_core.models.runtime import InputStatus, OutputStatus, RuntimeTruth
    from tests.test_lcd_4f_interactive_startup_freeze import _telemetry
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.pages.preflight_command_page import PreflightCommandPage

    render_count = {"count": 0}
    original_render = PreflightCommandPage._render

    def counted_render(self, *args, **kwargs):
        render_count["count"] += 1
        return original_render(self, *args, **kwargs)

    monkeypatch.setattr(PreflightCommandPage, "_render", counted_render)
    shell = LiquidCommandShell(state=_state(active_page_id="mapping"))
    shell.switch_route("mapping.hotas_map")
    mapping_page = shell.page_widgets["mapping.hotas_map"].widget()
    initial_preflight_renders = render_count["count"]
    initial_mapping_routes = _text_blob(mapping_page)

    telemetry = _telemetry(
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        output_verified=False,
    )
    for _ in range(12):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()

    assert shell.current_route_key == "mapping.hotas_map"
    assert render_count["count"] == initial_preflight_renders
    assert "Output Intent" in initial_mapping_routes
    assert "output verified" not in _text_blob(mapping_page).casefold()

    shell.switch_route("preflight.command_readiness")
    app.processEvents()
    preflight_page = shell.page_widgets["preflight.command_readiness"].widget()
    assert preflight_page.objectName() == "liquidPreflightCommandPage"
    assert preflight_page.findChild(QWidget, "liquidPreflightHeroGoNoGo") is not None


def test_lcd_5f_no_new_runtime_authority_or_hardware_paths_in_mapping_sources():
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "mapping_command_page.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "models" / "mapping_command_model.py",
        )
    )

    for forbidden in (
        "from v3_app.pages.mapping_page",
        "HotasDiagramWidget",
        "BridgeCommandClient",
        "EmbeddedBridgeRuntime",
        "build_runtime_preflight_status(",
        "verify_output_write",
        "write_output_intent",
        "QPropertyAnimation",
        "QGraphicsBlurEffect",
        "auto_save",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
    ):
        assert forbidden.casefold() not in source_text.casefold()
