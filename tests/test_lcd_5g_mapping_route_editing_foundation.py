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
    state.active_profile = "LCD-5G Fixture"
    state.source_config = "C:/Users/kkids/Documents/HOTAS-Control-Panel/configs/lcd_5g_mapping_fixture.json"
    state.status_message = "Workspace ready."
    return state


def _text_blob(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join(labels + buttons)


def test_lcd_5g_edit_model_lists_routes_and_editable_metadata():
    from v3_app.liquid.models.mapping_edit_model import build_mapping_edit_model

    model = build_mapping_edit_model(workspace=create_default_workspace(), selected_route_id="axis:axis_roll")
    records = {record.route_id: record for record in model.route_records}

    assert model.selected_route.route_id == "axis:axis_roll"
    assert set(records) >= {"axis:axis_roll", "axis:axis_pitch", "button:button_b1", "button:button_b15", "hat:hat_pov"}
    assert records["axis:axis_roll"].physical_label == "Roll axis"
    assert records["axis:axis_roll"].output_intent_target == "vJoy X(axis1)"
    assert any(field.field_id == "output_intent_target" and field.editable for field in records["axis:axis_roll"].editable_fields)
    assert any(field.field_id == "logical_function" and field.editable for field in records["axis:axis_roll"].editable_fields)
    assert any(field.field_id == "raw_channel" and not field.editable for field in records["axis:axis_roll"].editable_fields)
    assert records["hat:hat_pov"].status in {"mapped", "unsupported"}


def test_lcd_5g_supported_edit_stages_workspace_draft_without_runtime_truth_change():
    from v3_app.liquid.models.mapping_edit_model import stage_mapping_route_edit

    workspace = create_default_workspace()
    result = stage_mapping_route_edit(
        workspace,
        "axis:axis_roll",
        "output_intent_target",
        "vJoy SL1(axis8)",
    )

    assert result.valid is True
    assert result.workspace is not None
    assert result.workspace is not workspace
    assert result.workspace.mappings.axis_routes[0].runtime_vjoy_output == "SL1(axis8)"
    assert result.workspace.state.dirty is True
    assert result.workspace.state.saved is False
    assert "Draft mapping change" in result.status_label
    assert "Output proof unchanged" in result.message


def test_lcd_5g_unsupported_and_invalid_edits_are_rejected():
    from v3_app.liquid.models.mapping_edit_model import stage_mapping_route_edit

    workspace = create_default_workspace()

    invalid_target = stage_mapping_route_edit(
        workspace,
        "axis:axis_roll",
        "output_intent_target",
        "vJoy INVALID",
    )
    invalid_function = stage_mapping_route_edit(
        workspace,
        "axis:axis_roll",
        "logical_function",
        "Afterburner",
    )
    read_only_channel = stage_mapping_route_edit(
        workspace,
        "axis:axis_roll",
        "raw_channel",
        "Axis 99",
    )
    duplicate_target = stage_mapping_route_edit(
        workspace,
        "axis:axis_roll",
        "output_intent_target",
        "vJoy Y(axis2)",
    )

    for result in (invalid_target, invalid_function, read_only_channel, duplicate_target):
        assert result.valid is False
        assert result.workspace == workspace
        assert result.validation_errors
        assert "not staged" in result.message


def test_lcd_5g_mapping_edit_routes_are_real_liquid_pages_not_placeholders():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    shell.switch_route("mapping.route_details")
    app.processEvents()
    route_details = shell.page_widgets["mapping.route_details"].widget()
    route_details_text = _text_blob(route_details)

    assert route_details.objectName() == "liquidMappingRouteDetailsPage"
    assert route_details.property("routeKey") == "mapping.route_details"
    assert route_details.findChild(QWidget, "liquidMappingRouteEditor") is not None
    assert "Liquid Command Deck placeholder" not in route_details_text
    assert "Draft mapping change" in route_details_text
    assert "Output proof unchanged" in route_details_text
    assert "Output Intent" in route_details_text

    shell.switch_route("mapping.advanced_route_tables")
    app.processEvents()
    advanced_tables = shell.page_widgets["mapping.advanced_route_tables"].widget()
    advanced_text = _text_blob(advanced_tables)

    assert advanced_tables.objectName() == "liquidMappingAdvancedRouteTablesPage"
    assert advanced_tables.property("routeKey") == "mapping.advanced_route_tables"
    assert advanced_tables.findChild(QWidget, "liquidMappingEditableRouteGroups") is not None
    assert "Liquid Command Deck placeholder" not in advanced_text
    assert "Axis routes" in advanced_text
    assert "Button routes" in advanced_text
    assert "Hat routes" in advanced_text
    assert "Output Intent" in advanced_text


def test_lcd_5g_shell_stage_edit_marks_unsaved_and_keeps_output_proof_unchanged():
    app = _app()

    from PySide6.QtWidgets import QLabel
    from v3_app.liquid.app_shell import LiquidCommandShell

    state = _state()
    original_runtime = state.runtime
    shell = LiquidCommandShell(state=state)
    shell.switch_route("mapping.route_details")
    app.processEvents()

    result = shell.stage_mapping_route_edit("axis:axis_roll", "output_intent_target", "vJoy SL1(axis8)")
    app.processEvents()

    saved_chip = shell.findChild(QLabel, "liquidSavedChip")
    route_details = shell.page_widgets["mapping.route_details"].widget()
    text = _text_blob(route_details).casefold()

    assert result.valid is True
    assert shell.workspace.mappings.axis_routes[0].runtime_vjoy_output == "SL1(axis8)"
    assert shell.state.saved is False
    assert shell.state.runtime == original_runtime
    assert saved_chip is not None and saved_chip.text() == "Unsaved"
    assert "draft mapping change" in text
    assert "output proof unchanged" in text
    assert "output verified" not in text


def test_lcd_5g_revert_clears_staged_mapping_draft_when_shell_owns_original_workspace():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    original_target = shell.workspace.mappings.axis_routes[0].runtime_vjoy_output

    staged = shell.stage_mapping_route_edit("axis:axis_roll", "output_intent_target", "vJoy SL1(axis8)")
    assert staged.valid is True
    assert shell.state.saved is False

    shell.revert_mapping_route_edits()

    assert shell.workspace.mappings.axis_routes[0].runtime_vjoy_output == original_target
    assert shell.state.saved is True
    assert "reverted" in shell.state.status_message.casefold()


def test_lcd_5g_hotas_map_links_to_editing_routes_and_stays_compact():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    shell.switch_route("mapping.hotas_map")
    app.processEvents()
    hotas_map = shell.page_widgets["mapping.hotas_map"].widget()
    advanced = hotas_map.findChild(QWidget, "liquidMappingAdvancedRouteDetails")
    preview_rows = [
        widget
        for widget in advanced.findChildren(QWidget)
        if widget.property("advancedRouteDetailRow") is True
    ]
    route_button = hotas_map.findChild(QPushButton, "liquidMappingOpenRouteDetailsButton")
    tables_button = hotas_map.findChild(QPushButton, "liquidMappingOpenAdvancedTablesButton")

    assert route_button is not None
    assert route_button.isEnabled() is True
    assert route_button.property("routeTarget") == "mapping.route_details"
    assert tables_button is not None
    assert tables_button.isEnabled() is True
    assert tables_button.property("routeTarget") == "mapping.advanced_route_tables"
    assert 1 <= len(preview_rows) <= 6

    route_button.click()
    app.processEvents()
    assert shell.current_route_key == "mapping.route_details"


def test_lcd_5g_advanced_route_tables_are_grouped_compact_editable_rows():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.mapping_edit_pages import MappingAdvancedRouteTablesPage

    page = MappingAdvancedRouteTablesPage(state=_state(), workspace=create_default_workspace())
    rows = [widget for widget in page.findChildren(QWidget) if widget.property("mappingEditableRouteRow") is True]
    groups = {widget.property("routeGroup") for widget in page.findChildren(QWidget) if widget.property("mappingRouteGroup") is True}
    text = _text_blob(page)

    assert len(rows) >= 22
    assert {"axis", "button", "hat"}.issubset(groups)
    assert "Compact editable rows" in text
    assert "Save workspace to persist" in text
    assert "Output proof unchanged" in text


def test_lcd_5g_preflight_route_and_lcd4f_freeze_protection_remain_intact(monkeypatch):
    app = _app()

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
    shell.switch_route("mapping.route_details")
    initial_preflight_renders = render_count["count"]

    telemetry = _telemetry(
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        output_verified=False,
    )
    for _ in range(8):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()

    assert shell.current_route_key == "mapping.route_details"
    assert render_count["count"] == initial_preflight_renders

    shell.switch_route("preflight.command_readiness")
    app.processEvents()
    preflight_page = shell.page_widgets["preflight.command_readiness"].widget()
    assert preflight_page.objectName() == "liquidPreflightCommandPage"
    assert "Can I safely use live output right now?" in _text_blob(preflight_page)


def test_lcd_5g_sources_preserve_runtime_boundaries_and_report_scope():
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "mapping_command_page.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "mapping_edit_pages.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "models" / "mapping_command_model.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "models" / "mapping_edit_model.py",
        )
        if path.exists()
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


def test_lcd_5g_report_documents_mapping_editing_foundation_scope():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-5g-mapping-route-editing-foundation-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-5G Mapping Route Editing Foundation",
        "route editing architecture",
        "routes implemented",
        "editable fields supported",
        "read-only fields",
        "validation behavior",
        "draft/staged edit behavior",
        "save/apply/revert relationship",
        "output intent is distinguished from output proof",
        "HOTAS Map links to editing routes",
        "Advanced Route Tables avoids the 22-card wall",
        "data surfaces used",
        "limitations/deferred editing features",
        "runtime truth preservation statement",
        "no hardware polling was added",
        "no vJoy/output behavior was changed",
        "no output verification behavior was changed",
        "no Bridge lifecycle management was added",
        "no recorder capture/encoding was added",
        "no cloud AI/LLM behavior was added",
        "no auto-save was added",
        "no animations/page transitions/radial menu/real blur were added",
        "route edits are workspace/draft mapping edits only",
    ):
        assert required in text
