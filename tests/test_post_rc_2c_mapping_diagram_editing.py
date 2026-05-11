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


def _mapping_page(
    workspace: WorkspaceConfig | None = None,
    *,
    dirty_messages: list[str] | None = None,
    workspace_events: list[tuple[WorkspaceConfig, str]] | None = None,
):
    _app()

    from v3_app.pages.mapping_page import MappingPage
    from v3_app.services.app_state import build_initial_app_state

    return MappingPage(
        state=build_initial_app_state(),
        workspace=workspace or create_default_workspace(),
        on_dirty=dirty_messages.append if dirty_messages is not None else None,
        on_workspace_changed=(
            (lambda changed_workspace, message: workspace_events.append((changed_workspace, message)))
            if workspace_events is not None
            else None
        ),
    )


def _click_change_mapping(page):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPushButton

    button = page.findChild(QPushButton, "changeMappingButton")
    assert button is not None
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    _app().processEvents()


def _select_marker(page, object_name: str):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel

    marker = page.findChild(QLabel, object_name)
    assert marker is not None
    QTest.mouseClick(marker, Qt.MouseButton.LeftButton)
    _app().processEvents()
    return marker


def test_post_rc_2c_inspector_exposes_change_mapping_for_editable_route():
    from PySide6.QtWidgets import QLabel, QPushButton

    page = _mapping_page()

    button = page.findChild(QPushButton, "changeMappingButton")
    assert button is not None
    assert button.isEnabled()
    assert button.text() == "Change Mapping"

    labels_text = "\n".join(label.text() for label in page.findChildren(QLabel))
    assert "Selected Control" in labels_text
    assert "Draft mapping only" in labels_text
    assert "Change the target below" in labels_text


def test_post_rc_2c_axis_edit_panel_opens_for_selected_axis_route():
    from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QLabel

    page = _mapping_page()
    _click_change_mapping(page)

    panel = page.findChild(QFrame, "routeEditorPanel")
    assert panel is not None
    assert not panel.isHidden()
    assert page.findChild(QComboBox, "routeEditorAxisRawCombo") is not None
    assert page.findChild(QComboBox, "routeEditorAxisLogicalCombo") is not None
    assert page.findChild(QComboBox, "routeEditorAxisOutputCombo") is not None
    assert page.findChild(QCheckBox, "routeEditorAxisInvertCheckbox") is not None
    assert page.findChild(QLabel, "routeEditorModeLabel").text() == "Editing workspace draft"


def test_post_rc_2c_axis_edit_options_populate_from_supported_workspace_outputs():
    from PySide6.QtWidgets import QComboBox

    page = _mapping_page()
    _click_change_mapping(page)

    raw = page.findChild(QComboBox, "routeEditorAxisRawCombo")
    logical = page.findChild(QComboBox, "routeEditorAxisLogicalCombo")
    output = page.findChild(QComboBox, "routeEditorAxisOutputCombo")
    assert raw is not None
    assert logical is not None
    assert output is not None

    assert [raw.itemText(index) for index in range(raw.count())] == [f"Axis {index}" for index in range(1, 9)]
    assert "SL1" in [logical.itemText(index) for index in range(logical.count())]
    assert "RZ(axis6)" in [output.itemText(index) for index in range(output.count())]
    assert output.property("metadataId") == "mapping.runtime_output_axis"


def test_post_rc_2c_button_edit_options_populate_for_selected_button_route():
    from PySide6.QtWidgets import QComboBox, QLabel

    page = _mapping_page()
    _select_marker(page, "hotasMarker_button_b5")
    _click_change_mapping(page)

    source = page.findChild(QLabel, "routeEditorPhysicalValue")
    output = page.findChild(QComboBox, "routeEditorButtonOutputCombo")
    assert source is not None
    assert output is not None
    assert source.text() == "B5"
    assert output.currentText() == "5"
    assert output.count() == 20
    assert output.property("metadataId") == "mapping.output_button"


def test_post_rc_2c_hat_edit_options_populate_for_supported_hat_route():
    from PySide6.QtWidgets import QComboBox, QLabel

    page = _mapping_page()
    _select_marker(page, "hotasMarker_hat_pov")
    _click_change_mapping(page)

    source = page.findChild(QLabel, "routeEditorPhysicalValue")
    pov = page.findChild(QComboBox, "routeEditorHatPovCombo")
    up = page.findChild(QComboBox, "routeEditorHatUpButtonCombo")
    assert source is not None
    assert pov is not None
    assert up is not None
    assert source.text() == "Hat 1"
    assert pov.currentText() == "1"
    assert "4" in [pov.itemText(index) for index in range(pov.count())]
    assert up.property("metadataId") == "mapping.hat_direction_button"


def test_post_rc_2c_apply_changes_workspace_draft_only_and_updates_dirty_state():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel, QPushButton, QComboBox

    events: list[tuple[WorkspaceConfig, str]] = []
    page = _mapping_page(workspace_events=events)
    _click_change_mapping(page)

    output = page.findChild(QComboBox, "routeEditorAxisOutputCombo")
    apply = page.findChild(QPushButton, "routeEditorApplyButton")
    assert output is not None
    assert apply is not None

    output.setCurrentText("RZ(axis6)")
    QTest.mouseClick(apply, Qt.MouseButton.LeftButton)
    _app().processEvents()

    assert page._workspace.mappings.axis_routes[0].runtime_vjoy_output == "RZ(axis6)"
    assert events
    assert "workspace draft" in events[-1][1]
    assert "vJoy" not in events[-1][1]
    assert "verified" not in events[-1][1].casefold()
    assert page.findChild(QLabel, "routeEditorDirtyStateValue").text() == "Draft changed"


def test_post_rc_2c_cancel_preserves_previous_draft_route():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPushButton, QComboBox

    page = _mapping_page()
    before = page._workspace.mappings.axis_routes[0]
    _click_change_mapping(page)

    output = page.findChild(QComboBox, "routeEditorAxisOutputCombo")
    cancel = page.findChild(QPushButton, "routeEditorCancelButton")
    assert output is not None
    assert cancel is not None

    output.setCurrentText("RZ(axis6)")
    QTest.mouseClick(cancel, Qt.MouseButton.LeftButton)
    _app().processEvents()

    assert page._workspace.mappings.axis_routes[0] == before


def test_post_rc_2c_revert_restores_pre_edit_draft_route_after_apply():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPushButton, QComboBox

    page = _mapping_page()
    before = page._workspace.mappings.axis_routes[0]
    _click_change_mapping(page)

    output = page.findChild(QComboBox, "routeEditorAxisOutputCombo")
    apply = page.findChild(QPushButton, "routeEditorApplyButton")
    revert = page.findChild(QPushButton, "routeEditorRevertButton")
    assert output is not None
    assert apply is not None
    assert revert is not None

    output.setCurrentText("RZ(axis6)")
    QTest.mouseClick(apply, Qt.MouseButton.LeftButton)
    _app().processEvents()
    assert page._workspace.mappings.axis_routes[0] != before

    QTest.mouseClick(revert, Qt.MouseButton.LeftButton)
    _app().processEvents()

    assert page._workspace.mappings.axis_routes[0] == before


def test_post_rc_2c_conflict_preview_detects_duplicate_and_missing_output_targets():
    from PySide6.QtWidgets import QLabel, QComboBox

    workspace = create_default_workspace()
    axis_routes = (
        AxisMapping("Roll", "Axis 1", "X", ""),
        AxisMapping("Pitch", "Axis 2", "Y", "Y(axis2)"),
        *workspace.mappings.axis_routes[2:],
    )
    workspace = replace(workspace, mappings=replace(workspace.mappings, axis_routes=axis_routes))
    page = _mapping_page(workspace)
    _click_change_mapping(page)

    preview = page.findChild(QLabel, "routeEditorConflictPreview")
    output = page.findChild(QComboBox, "routeEditorAxisOutputCombo")
    assert preview is not None
    assert output is not None
    assert "workspace/config warning" not in preview.text()
    assert "no output target" in preview.text()

    output.setCurrentText("Y(axis2)")
    _app().processEvents()

    assert "share output target Y(axis2)" in preview.text()
    assert "live runtime failure" not in preview.text().casefold()


def test_post_rc_2c_conflict_markers_and_table_warning_properties_appear():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QTableWidget

    workspace = create_default_workspace()
    axis_routes = (
        AxisMapping("Roll", "Axis 1", "X", "X(axis1)"),
        AxisMapping("Pitch", "Axis 2", "Y", "X(axis1)"),
        *workspace.mappings.axis_routes[2:],
    )
    workspace = replace(workspace, mappings=replace(workspace.mappings, axis_routes=axis_routes))
    page = _mapping_page(workspace)

    marker = page.findChild(QLabel, "hotasMarker_axis_roll")
    table = page.findChild(QTableWidget, "axisRoutingTable")
    assert marker is not None
    assert table is not None
    assert marker.property("hasWarning") is True
    assert table.item(0, 0).data(Qt.ItemDataRole.UserRole) == "workspace-config-warning"


def test_post_rc_2c_filter_chips_change_visual_filter_state_only():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel, QPushButton

    page = _mapping_page()
    before = page._workspace
    axes = page.findChild(QPushButton, "routeFilterChipAxes")
    button_marker = page.findChild(QLabel, "hotasMarker_button_b1")
    axis_marker = page.findChild(QLabel, "hotasMarker_axis_roll")
    assert axes is not None
    assert button_marker is not None
    assert axis_marker is not None

    QTest.mouseClick(axes, Qt.MouseButton.LeftButton)
    _app().processEvents()

    assert page._workspace == before
    assert page.property("routeFilter") == "Axes"
    assert axes.isChecked()
    assert axis_marker.property("filteredOut") is False
    assert button_marker.property("filteredOut") is True


def test_post_rc_2c_keyboard_focus_selects_marker_without_breaking_mouse_sync():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel

    page = _mapping_page()
    page.show()
    marker = page.findChild(QLabel, "hotasMarker_axis_pitch")
    assert marker is not None

    marker.setFocus(Qt.FocusReason.TabFocusReason)
    _app().processEvents()

    assert marker.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert marker.property("selected") is True
    assert page.findChild(QLabel, "routeInspectorPhysicalValue").text() == "Axis 2"

    QTest.keyClick(marker, Qt.Key.Key_Return)
    _app().processEvents()
    assert page.findChild(QLabel, "routeInspectorTypeValue").text() == "Axis"


def test_post_rc_2c_no_output_write_proof_or_runtime_authority_is_claimed():
    page = _mapping_page()
    _click_change_mapping(page)

    from PySide6.QtWidgets import QLabel

    labels_text = "\n".join(label.text() for label in page.findChildren(QLabel))
    lower_text = labels_text.casefold()
    assert "draft mapping only" in lower_text
    assert "apply to draft updates this workspace draft" in lower_text
    assert "no route conflicts previewed" in lower_text or "no output target" in lower_text
    assert "writing to vjoy" not in lower_text
    assert "live output changed" not in lower_text
    assert "full live runtime ready true" not in lower_text

    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "pages" / "mapping_page.py",
            PROJECT_ROOT / "v3_app" / "services" / "hotas_diagram_model.py",
            PROJECT_ROOT / "v3_app" / "widgets" / "hotas_diagram.py",
        )
    )
    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "PhysicalInputSampler",
        "read_current_state(",
        "VirtualOutputWriteLoop(",
        "OpenAI(",
        "VideoWriter",
        "auto_save",
        "autosave",
    ):
        assert forbidden not in sources


def test_post_rc_2c_report_documents_mapping_editing_scope():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-2c-mapping-diagram-editing-report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "Post-RC 2C",
        "edit workflow implemented",
        "supported editable route types",
        "deferred route types",
        "conflict preview behavior",
        "filter chip behavior",
        "keyboard/accessibility",
        "runtime truth preservation",
        "Output intent is not output write proof",
        "Save Workspace remains the explicit persistence action",
        "no hardware polling",
        "no vJoy writes",
    ):
        assert required in text
