from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _shell(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import build_initial_app_state
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        state=build_initial_app_state(),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )


def _metadata_ids(widget):
    from PySide6.QtWidgets import QLabel

    return {
        label.property("metadataId")
        for label in widget.findChildren(QLabel, "parameterInfoIcon")
        if label.property("metadataId")
    }


def test_post_rc_1c_metadata_has_scope_and_expanded_page_coverage():
    from v3_app.services.parameter_metadata import PARAMETER_HELP, ParameterSupportScope

    required_ids = {
        "base.precision_scale",
        "mapping.raw_axis",
        "mapping.logical_output",
        "mapping.runtime_output_axis",
        "mapping.invert_axis",
        "mapping.hotas_button",
        "mapping.output_button",
        "mapping.hotas_hat",
        "mapping.output_pov",
        "mapping.hat_direction_button",
        "rules.title",
        "rules.buttons",
        "rules.button_test",
        "rules.measure",
        "live_overlay.display",
        "live_overlay.show_legend",
        "live_overlay.show_values",
        "live_overlay.auto_hide",
        "flight_recorder.library_sort",
        "diagnostics.runtime_preflight_dry_run",
    }
    registry_ids = {metadata.parameter_id for metadata in PARAMETER_HELP.all()}

    assert required_ids <= registry_ids
    assert all(metadata.support_scope is not None for metadata in PARAMETER_HELP.all())
    assert PARAMETER_HELP.require("base.deadzone").support_scope is ParameterSupportScope.WORKSPACE_ONLY
    assert PARAMETER_HELP.require("live_overlay.opacity").support_scope is ParameterSupportScope.APP_RUNTIME_CONFIG
    assert PARAMETER_HELP.require("flight_recorder.length").support_scope is ParameterSupportScope.SIMULATED_WORKSPACE_ONLY
    assert PARAMETER_HELP.require("diagnostics.runtime_preflight_dry_run").support_scope is ParameterSupportScope.DIAGNOSTIC_ONLY


def test_post_rc_1c_tooltip_includes_default_scope_units_and_stays_compact():
    from v3_app.services.parameter_metadata import PARAMETER_HELP, format_parameter_tooltip

    tooltip = format_parameter_tooltip(PARAMETER_HELP.require("live_overlay.fps_cap"))

    for expected in ("FPS Cap", "Range", "15 to 144 fps", "Default", "60", "Scope", "app runtime config", "Examples"):
        assert expected in tooltip
    assert len(tooltip) < 1500
    assert "Full Live Runtime Ready" not in tooltip


def test_post_rc_1c_numeric_text_validation_rejects_letters_and_clamps_range():
    from v3_app.services.parameter_metadata import PARAMETER_HELP, validate_numeric_text

    deadzone = PARAMETER_HELP.require("base.deadzone")
    valid = validate_numeric_text(deadzone, "0.05")
    letters = validate_numeric_text(deadzone, "abc")
    high = validate_numeric_text(deadzone, "9.5")

    assert valid.acceptable
    assert valid.value == 0.05
    assert not letters.acceptable
    assert letters.error == "not_numeric"
    assert not high.acceptable
    assert high.error == "above_max"
    assert high.clamped_value == deadzone.max_value

    fps = PARAMETER_HELP.require("live_overlay.fps_cap")
    fractional = validate_numeric_text(fps, "60.5")
    assert not fractional.acceptable
    assert fractional.error == "not_integer"


def test_post_rc_1c_helper_paths_fallback_when_metadata_is_missing():
    _app()

    from PySide6.QtWidgets import QComboBox, QGridLayout, QLabel, QLineEdit, QWidget
    from v3_app.pages.page_helpers import dropdown_field_row, field_row, parameter_label

    container = QWidget()
    grid = QGridLayout(container)

    label = parameter_label("Unknown Parameter", metadata_id="missing.parameter")
    text = field_row(grid, 0, "Unknown Number", "1.0", object_name="unknownNumber", metadata_id="missing.number")
    combo = dropdown_field_row(
        grid,
        1,
        "Unknown Dropdown",
        "A",
        object_name="unknownDropdown",
        metadata_id="missing.dropdown",
        options=("A", "B"),
    )

    assert isinstance(text, QLineEdit)
    assert isinstance(combo, QComboBox)
    assert combo.count() == 2
    assert isinstance(label.findChild(QLabel, "parameterInfoIcon"), type(None))


def test_post_rc_1c_apply_metadata_to_spinboxes_checkboxes_and_labels():
    _app()

    from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QLabel, QSpinBox
    from v3_app.pages.page_helpers import apply_parameter_metadata

    fps = QSpinBox()
    opacity = QDoubleSpinBox()
    checkbox = QCheckBox("Always on top")
    label = QLabel("Opacity")

    assert apply_parameter_metadata(fps, "live_overlay.fps_cap")
    assert apply_parameter_metadata(opacity, "live_overlay.opacity")
    assert apply_parameter_metadata(checkbox, "live_overlay.always_on_top")
    assert apply_parameter_metadata(label, "live_overlay.opacity")

    assert fps.minimum() == 15
    assert fps.maximum() == 144
    assert opacity.minimum() == 0.0
    assert opacity.maximum() == 1.0
    assert checkbox.property("metadataId") == "live_overlay.always_on_top"
    assert "Opacity" in label.toolTip()


def test_post_rc_1c_modes_and_rules_pages_expose_broader_metadata_help(tmp_path):
    _app()

    from PySide6.QtGui import QValidator
    from PySide6.QtWidgets import QComboBox, QLineEdit

    shell = _shell(tmp_path)
    shell.switch_page("modes")
    modes = shell.page_widgets["modes"].widget()
    assert {
        "modes.precision_hold_buttons",
        "modes.combat_trigger_buttons",
        "modes.combat_zoom_aim_buttons",
        "modes.combat_extra_buttons",
        "modes.stack_mode",
    } <= _metadata_ids(modes)
    stack = modes.findChild(QComboBox, "stackModeField")
    assert stack is not None
    assert stack.property("metadataId") == "modes.stack_mode"

    shell.switch_page("conditional_rules")
    rules = shell.page_widgets["conditional_rules"].widget()
    assert {"rules.operation", "rules.value", "rules.comparator", "rules.threshold"} <= _metadata_ids(rules)
    threshold = rules.findChild(QLineEdit, "ruleThresholdField")
    assert threshold is not None
    assert threshold.validator() is not None
    assert threshold.validator().validate("abc", 0)[0] == QValidator.State.Invalid


def test_post_rc_1c_overlay_and_recorder_surfaces_apply_metadata_help():
    _app()

    from PySide6.QtWidgets import QCheckBox
    from v3_app.overlay.config_dialog import LiveOverlayConfigDialog
    from v3_app.overlay.overlay_config import LiveOverlayConfig
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.services.app_state import build_initial_app_state

    dialog = LiveOverlayConfigDialog(config=LiveOverlayConfig.defaults(), on_apply=lambda _config: None)
    assert {"live_overlay.opacity", "live_overlay.fps_cap", "live_overlay.source"} <= _metadata_ids(dialog)
    assert dialog.fps_cap.property("metadataId") == "live_overlay.fps_cap"
    assert dialog.opacity.property("metadataId") == "live_overlay.opacity"

    recorder = FlightRecorderPage(state=build_initial_app_state())
    assert {"flight_recorder.length", "flight_recorder.frame_rate", "flight_recorder.overlay_source"} <= _metadata_ids(recorder)
    cursor = recorder.findChild(QCheckBox, "recordCursorCheckbox")
    assert cursor is not None
    assert cursor.property("metadataId") == "flight_recorder.record_cursor"


def test_post_rc_1c_mapping_combo_cells_are_metadata_backed(tmp_path):
    _app()

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel, QComboBox, QPushButton

    shell = _shell(tmp_path)
    shell.switch_page("mapping")
    page = shell.page_widgets["mapping"].widget()

    page.findChild(QPushButton, "changeMappingButton").click()
    expected_axis = {
        "routeEditorAxisRawCombo": "mapping.raw_axis",
        "routeEditorAxisLogicalCombo": "mapping.logical_output",
        "routeEditorAxisOutputCombo": "mapping.runtime_output_axis",
    }
    for object_name, metadata_id in expected_axis.items():
        combo = page.findChild(QComboBox, object_name)
        assert combo is not None, object_name
        assert combo.property("metadataId") == metadata_id
        assert combo.toolTip()

    marker = page.findChild(QLabel, "hotasMarker_button_b1")
    QTest.mouseClick(marker, Qt.MouseButton.LeftButton)
    page.findChild(QPushButton, "changeMappingButton").click()
    combo = page.findChild(QComboBox, "routeEditorButtonOutputCombo")
    assert combo is not None
    assert combo.property("metadataId") == "mapping.output_button"
    assert combo.toolTip()

    marker = page.findChild(QLabel, "hotasMarker_hat_pov")
    QTest.mouseClick(marker, Qt.MouseButton.LeftButton)
    page.findChild(QPushButton, "changeMappingButton").click()
    expected_hat = {
        "routeEditorHatPovCombo": "mapping.output_pov",
        "routeEditorHatUpButtonCombo": "mapping.hat_direction_button",
    }
    for object_name, metadata_id in expected_hat.items():
        combo = page.findChild(QComboBox, object_name)
        assert combo is not None, object_name
        assert combo.property("metadataId") == metadata_id
        assert combo.toolTip()


def test_post_rc_1c_report_documents_runtime_non_goals_and_next_notes():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-1c-parameter-help-coverage-report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "Post-RC 1C",
        "Metadata categories added",
        "UI/helper changes",
        "Runtime truth/non-goals",
        "Known limitations",
        "Recommended next phase notes",
        "No hardware polling",
        "No Bridge lifecycle",
    ):
        assert required in text


def test_post_rc_1c_no_runtime_authority_introduced():
    source_paths = (
        PROJECT_ROOT / "v3_app" / "services" / "parameter_metadata.py",
        PROJECT_ROOT / "v3_app" / "widgets" / "info_icon.py",
        PROJECT_ROOT / "v3_app" / "pages" / "page_helpers.py",
        PROJECT_ROOT / "v3_app" / "overlay" / "config_dialog.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "keyboard.add_hotkey",
        "VideoWriter",
        "OpenAI(",
        "Full Live Runtime Ready: true",
    ):
        assert forbidden not in sources
