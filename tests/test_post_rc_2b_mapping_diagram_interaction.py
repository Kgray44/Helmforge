from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from shared_core.models.mappings import AxisMapping, ButtonMapping, MappingConfig
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _mapping_page(workspace: WorkspaceConfig | None = None):
    _app()

    from v3_app.pages.mapping_page import MappingPage
    from v3_app.services.app_state import build_initial_app_state

    return MappingPage(state=build_initial_app_state(), workspace=workspace or create_default_workspace())


def test_post_rc_2b_selection_model_maps_controls_to_tables_and_rows():
    from v3_app.services.hotas_diagram_model import (
        build_hotas_diagram_model,
        select_hotas_diagram_route,
    )

    model = build_hotas_diagram_model(create_default_workspace())

    axis = select_hotas_diagram_route(model, "axis_pitch")
    assert axis is not None
    assert axis.control_id == "axis_pitch"
    assert axis.route_type == "axis"
    assert axis.table_object_name == "axisRoutingTable"
    assert axis.route_row == 1
    assert axis.is_selectable

    button = select_hotas_diagram_route(model, "button_b5")
    assert button is not None
    assert button.route_type == "button"
    assert button.table_object_name == "buttonRoutingTable"
    assert button.route_row == 4

    hat = select_hotas_diagram_route(model, "hat_pov")
    assert hat is not None
    assert hat.route_type == "hat"
    assert hat.table_object_name == "hatRoutingTable"
    assert hat.route_row == 0


def test_post_rc_2b_route_inspector_data_is_truthful_and_editability_scoped():
    from v3_app.services.hotas_diagram_model import (
        build_hotas_diagram_model,
        build_route_inspector,
    )

    workspace = create_default_workspace()
    model = build_hotas_diagram_model(workspace, source_label="Simulation")
    control = next(control for control in model.controls if control.control_id == "axis_roll")

    inspector = build_route_inspector(
        control,
        workspace=workspace,
        active_profile=workspace.active_profile,
        source_label="Simulation",
        runtime_truth_label="simulated",
        telemetry_status="Bridge telemetry unavailable",
    )

    assert inspector.selected_physical_input == "Axis 1"
    assert inspector.mapped_virtual_output == "X(axis1)"
    assert inspector.route_type == "axis"
    assert inspector.mode_profile_context == "Profile: current-workspace"
    assert "workspace/config" in inspector.source_of_truth
    assert "Simulation" in inspector.source_of_truth
    assert inspector.editable_in_current_ui == "Editable in Mapping table"
    assert inspector.conflict_status == "No workspace conflicts detected"
    assert "No live output verification" in inspector.no_live_output_verification_notice
    assert "does not prove live output" in inspector.no_live_output_verification_notice


def test_post_rc_2b_workspace_warning_detection_is_conservative_and_config_only():
    from v3_app.services.hotas_diagram_model import build_workspace_route_warnings

    workspace = create_default_workspace()
    axis_routes = (
        AxisMapping("Roll", "Axis 1", "X", "X(axis1)"),
        AxisMapping("Pitch", "Axis 2", "Y", "X(axis1)"),
        AxisMapping("Throttle", "Axis 3", "Z", ""),
    )
    button_routes = (
        ButtonMapping(1, 1),
        ButtonMapping(2, 1),
        ButtonMapping(99, 2),
    )
    workspace = replace(
        workspace,
        mappings=MappingConfig(axis_routes=axis_routes, button_routes=button_routes, hat_routes=()),
    )

    warnings = build_workspace_route_warnings(workspace)
    codes = {warning.code for warning in warnings}
    text = "\n".join(warning.message for warning in warnings)

    assert "duplicate_output_intent" in codes
    assert "missing_output_target" in codes
    assert "invalid_route_shape" in codes
    assert "unmapped_important_control" in codes
    assert "workspace/config" in text
    assert "hardware" not in text.casefold()


def test_post_rc_2b_diagram_click_selects_related_table_row_and_inspector():
    _app()

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel, QTableWidget

    page = _mapping_page()
    marker = page.findChild(QLabel, "hotasMarker_button_b5")
    button_table = page.findChild(QTableWidget, "buttonRoutingTable")

    assert marker is not None
    assert button_table is not None

    QTest.mouseClick(marker, Qt.MouseButton.LeftButton)
    _app().processEvents()

    assert marker.property("selected") is True
    assert button_table.currentRow() == 4
    assert page.findChild(QLabel, "routeInspectorPhysicalValue").text() == "B5"
    assert page.findChild(QLabel, "routeInspectorOutputValue").text() == "Button 5"
    assert "Editable in Mapping table" in page.findChild(QLabel, "routeInspectorEditableValue").text()


def test_post_rc_2b_table_selection_selects_related_diagram_marker_and_inspector():
    _app()

    from PySide6.QtWidgets import QLabel, QTableWidget

    page = _mapping_page()
    axis_table = page.findChild(QTableWidget, "axisRoutingTable")
    marker = page.findChild(QLabel, "hotasMarker_axis_pitch")

    assert axis_table is not None
    assert marker is not None

    axis_table.setCurrentCell(1, 0)
    _app().processEvents()

    assert marker.property("selected") is True
    assert page.findChild(QLabel, "routeInspectorPhysicalValue").text() == "Axis 2"
    assert page.findChild(QLabel, "routeInspectorOutputValue").text() == "Y(axis2)"
    assert page.findChild(QLabel, "routeInspectorTypeValue").text() == "axis"


def test_post_rc_2b_blocked_missing_telemetry_wording_stays_workspace_focused():
    _app()

    from PySide6.QtWidgets import QLabel

    page = _mapping_page()
    labels_text = "\n".join(label.text() for label in page.findChildren(QLabel))

    assert "Bridge telemetry unavailable" in labels_text
    assert "workspace/config" in labels_text
    assert "No live output verification" in labels_text
    assert "Output intent does not prove live output" in labels_text
    assert "Full Live Runtime Ready" in labels_text
    assert "Full Live Runtime Ready true" not in labels_text


def test_post_rc_2b_report_documents_selection_inspector_and_truth_boundaries():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-2b-mapping-diagram-interaction-report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "Summary",
        "Files changed",
        "Selection model",
        "Inspector behavior",
        "Conflict/warning logic",
        "Truthfulness constraints",
        "Tests run",
        "Known limitations",
        "Recommended next phase notes",
        "No hardware polling",
        "No Bridge lifecycle",
        "No output write verification",
    ):
        assert required in text


def test_post_rc_2b_no_runtime_authority_added_to_diagram_sources():
    source_paths = (
        PROJECT_ROOT / "v3_app" / "services" / "hotas_diagram_model.py",
        PROJECT_ROOT / "v3_app" / "widgets" / "hotas_diagram.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "PhysicalInputSampler",
        "read_current_state(",
        "VirtualOutputWriteLoop",
        "OpenAI(",
        "VideoWriter",
        "auto_save",
        "autosave",
    ):
        assert forbidden not in sources
