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


def test_post_rc_1b_metadata_registry_covers_core_parameter_groups():
    from v3_app.services.parameter_metadata import PARAMETER_HELP, ParameterValueType

    required_ids = {
        "base.curve_mode",
        "base.curve_strength",
        "base.deadzone",
        "base.anti_deadzone",
        "base.hysteresis",
        "base.output_scale",
        "base.max_output",
        "filtering.center_alpha",
        "filtering.edge_alpha",
        "filtering.same_slew_limit",
        "filtering.reverse_slew_limit",
        "combat.combat_curve",
        "combat.combat_scale",
        "combat.combat_center_alpha",
        "combat.combat_edge_alpha",
        "combat.combat_same_slew",
        "combat.combat_reverse_slew",
        "modes.precision_hold_buttons",
        "modes.stack_mode",
        "rules.target_axis",
        "rules.operation",
        "rules.comparator",
        "rules.threshold",
        "live_overlay.position",
        "live_overlay.opacity",
        "live_overlay.fps_cap",
        "flight_recorder.length",
        "flight_recorder.overlay_source",
        "flight_recorder.trigger_mode",
    }

    assert required_ids <= {metadata.parameter_id for metadata in PARAMETER_HELP.all()}
    assert PARAMETER_HELP.require("base.curve_strength").value_range is not None
    assert PARAMETER_HELP.require("filtering.center_alpha").value_range is not None
    assert PARAMETER_HELP.require("combat.combat_scale").value_range is not None
    assert PARAMETER_HELP.require("base.curve_mode").value_type is ParameterValueType.DROPDOWN
    assert PARAMETER_HELP.require("modes.stack_mode").dropdown_options == ("multiply",)
    assert "greater than" in PARAMETER_HELP.require("rules.comparator").dropdown_options
    assert "Bottom strip" in PARAMETER_HELP.require("live_overlay.position").dropdown_options


def test_post_rc_1b_tooltip_formatter_includes_range_options_examples_and_warnings():
    from v3_app.services.parameter_metadata import PARAMETER_HELP, format_parameter_tooltip

    numeric_tip = format_parameter_tooltip(PARAMETER_HELP.require("base.deadzone"))
    for expected in (
        "Deadzone",
        "What it does",
        "Range",
        "0.00",
        "0.50",
        "Examples",
        "Low",
        "High",
        "Notes",
    ):
        assert expected in numeric_tip

    dropdown_tip = format_parameter_tooltip(PARAMETER_HELP.require("base.curve_mode"))
    assert "Curve Mode" in dropdown_tip
    assert "Options" in dropdown_tip
    assert "s" in dropdown_tip
    assert "linear" not in dropdown_tip


def test_post_rc_1b_info_icon_widget_constructs_with_parameter_tooltip():
    _app()

    from v3_app.services.parameter_metadata import PARAMETER_HELP
    from v3_app.widgets.info_icon import ParameterInfoIcon

    icon = ParameterInfoIcon(PARAMETER_HELP.require("base.curve_strength"))

    assert icon.objectName() == "parameterInfoIcon"
    assert icon.property("metadataId") == "base.curve_strength"
    assert icon.toolTip()
    assert "Curve Strength" in icon.toolTip()


def test_post_rc_1b_representative_pages_expose_parameter_info_icons(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel

    shell = _shell(tmp_path)
    expected_by_page = {
        "base_tuning": {
            "base.curve_mode",
            "base.curve_strength",
            "base.deadzone",
            "base.max_output",
        },
        "filtering": {
            "filtering.center_alpha",
            "filtering.edge_alpha",
            "filtering.same_slew_limit",
            "filtering.reverse_slew_limit",
        },
        "combat_profile": {
            "combat.combat_curve",
            "combat.combat_scale",
            "combat.combat_center_alpha",
            "combat.combat_reverse_slew",
        },
    }

    for page_id, expected_ids in expected_by_page.items():
        shell.switch_page(page_id)
        page = shell.page_widgets[page_id].widget()
        found = {
            label.property("metadataId")
            for label in page.findChildren(QLabel, "parameterInfoIcon")
            if label.property("metadataId")
        }
        assert expected_ids <= found


def test_post_rc_1b_numeric_validators_reject_letters_and_out_of_range_values(tmp_path):
    _app()

    from PySide6.QtGui import QValidator
    from PySide6.QtWidgets import QLineEdit

    shell = _shell(tmp_path)
    for page_id, field_name in (
        ("base_tuning", "deadzoneField"),
        ("filtering", "centerAlphaField"),
        ("combat_profile", "combatScaleField"),
    ):
        shell.switch_page(page_id)
        field = shell.page_widgets[page_id].widget().findChild(QLineEdit, field_name)
        assert field is not None
        validator = field.validator()
        assert validator is not None
        assert validator.validate("abc", 0)[0] == QValidator.State.Invalid
        assert validator.validate("999", 0)[0] != QValidator.State.Acceptable


def test_post_rc_1b_dropdown_parameters_use_comboboxes_where_integrated(tmp_path):
    _app()

    from PySide6.QtWidgets import QComboBox

    shell = _shell(tmp_path)
    shell.switch_page("base_tuning")
    curve_mode = shell.page_widgets["base_tuning"].widget().findChild(QComboBox, "curveModeField")

    assert curve_mode is not None
    assert curve_mode.property("metadataId") == "base.curve_mode"
    assert curve_mode.count() >= 1
    assert "s" in [curve_mode.itemText(index) for index in range(curve_mode.count())]


def test_post_rc_1b_report_documents_scope_and_remaining_rollout():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-1b-parameter-metadata-info-icons-report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "Post-RC 1B",
        "metadata model overview",
        "parameters covered",
        "pages integrated",
        "info icon behavior",
        "validation behavior",
        "remaining pages still needing rollout",
        "Recommendation for Post-RC 1C",
        "no runtime behavior",
    ):
        assert required in text


def test_post_rc_1b_no_runtime_authority_introduced():
    source_paths = (
        PROJECT_ROOT / "v3_app" / "services" / "parameter_metadata.py",
        PROJECT_ROOT / "v3_app" / "widgets" / "info_icon.py",
        PROJECT_ROOT / "v3_app" / "pages" / "page_helpers.py",
    )
    existing_sources = [path for path in source_paths if path.exists()]
    sources = "\n".join(path.read_text(encoding="utf-8") for path in existing_sources)

    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "keyboard.add_hotkey",
        "VideoWriter",
        "OpenAI(",
        "vjoy",
    ):
        assert forbidden not in sources.lower() if forbidden == "vjoy" else forbidden not in sources
