from __future__ import annotations

import os

from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _status() -> RuntimePreflightStatus:
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


def _shell(tmp_path=None):
    _app()

    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    workspace_path = None if tmp_path is None else tmp_path / "hotas_bridge_config_v3.json"
    return HelmForgeShell(
        AppState.from_runtime_status(_status(), driver_detected=True),
        workspace_path=workspace_path,
    )


def _rules_page(shell):
    shell.switch_page("conditional_rules")
    return shell.page_widgets["conditional_rules"].widget()


def test_phase7_conditional_rules_page_constructs_and_is_registered():
    from PySide6.QtWidgets import QLabel

    shell = _shell()
    page = _rules_page(shell)

    assert page.objectName() == "conditionalRulesPage"
    assert shell.active_page_id == "conditional_rules"
    assert "Conditional Rules" in " ".join(label.text() for label in page.findChildren(QLabel))


def test_phase7_default_chips_and_rule_detail_match_recovered_example():
    from PySide6.QtWidgets import QLabel, QTableWidget

    shell = _shell()
    page = _rules_page(shell)
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))
    rule_table = page.findChild(QTableWidget, "conditionalRuleList")

    assert "1 rules" in labels_text
    assert "0 active" in labels_text
    assert "0 blocked" in labels_text
    assert "1 disabled" in labels_text
    assert rule_table.rowCount() == 1
    assert rule_table.item(0, 0).text() == "Yaw 0.75 | Roll > 0.35"
    assert "Targets Yaw. Watches Roll Final Output > 0.35. Set Output Scale." in labels_text
    assert "Base Output Limits" in labels_text
    assert "Always" in labels_text


def test_phase7_plain_english_preview_contains_recovered_rule_parts():
    from PySide6.QtWidgets import QLabel

    page = _rules_page(_shell())
    preview = page.findChild(QLabel, "rulePreviewSentence")

    assert "Yaw" in preview.text()
    assert "Output Scale" in preview.text()
    assert "0.75" in preview.text()
    assert "Roll" in preview.text()
    assert "0.35" in preview.text()


def test_phase7_enable_duplicate_delete_and_add_are_functional_and_dirty():
    from PySide6.QtWidgets import QPushButton, QTableWidget

    shell = _shell()
    page = _rules_page(shell)
    table = page.findChild(QTableWidget, "conditionalRuleList")

    table.selectRow(0)
    page.findChild(QPushButton, "toggleRuleEnabledButton").click()
    assert shell.workspace.rules.rules[0].enabled is True
    assert shell.state.saved is False

    page.findChild(QPushButton, "duplicateRuleButton").click()
    assert table.rowCount() == 2
    assert len(shell.workspace.rules.rules) == 2
    assert shell.workspace.rules.rules[1].enabled is False

    table.selectRow(1)
    page.findChild(QPushButton, "deleteRuleButton").click()
    assert table.rowCount() == 1
    assert len(shell.workspace.rules.rules) == 1

    page.findChild(QPushButton, "addRuleButton").click()
    assert table.rowCount() == 2
    assert shell.workspace.rules.rules[-1].enabled is False


def test_phase7_editing_rule_field_marks_workspace_dirty():
    from PySide6.QtWidgets import QComboBox, QLineEdit

    shell = _shell()
    page = _rules_page(shell)
    target = page.findChild(QComboBox, "ruleTargetAxisField")
    value = page.findChild(QLineEdit, "ruleValueField")

    target.setCurrentText("Pitch")
    assert shell.workspace.rules.rules[0].target_axis == "Pitch"
    assert shell.state.saved is False

    value.setText("0.80")
    value.editingFinished.emit()
    assert shell.workspace.rules.rules[0].value == 0.8


def test_phase7_save_round_trips_rule_changes_and_revert_restores(tmp_path):
    from PySide6.QtWidgets import QPushButton, QLineEdit
    from shared_core.persistence.workspace_store import load_workspace

    shell = _shell(tmp_path)
    page = _rules_page(shell)
    value = page.findChild(QLineEdit, "ruleValueField")
    value.setText("0.80")
    value.editingFinished.emit()

    shell.footer.findChild(QPushButton, "saveWorkspaceButton").click()

    saved = load_workspace(tmp_path / "hotas_bridge_config_v3.json").workspace
    assert saved.rules.rules[0].value == 0.8
    assert shell.state.saved is True

    page = _rules_page(shell)
    page.findChild(QLineEdit, "ruleValueField").setText("0.55")
    page.findChild(QLineEdit, "ruleValueField").editingFinished.emit()
    shell.footer.findChild(QPushButton, "revertButton").click()

    assert shell.workspace.rules.rules[0].value == 0.8
    assert shell.state.saved is True
    assert _rules_page(shell).findChild(QLineEdit, "ruleValueField").text() == "0.8"


def test_phase7_conditional_rules_page_stays_truthful_about_runtime_output():
    from PySide6.QtWidgets import QLabel

    page = _rules_page(_shell())
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))

    assert "Output writes verified: false" in labels_text
    assert "Output Verified" not in labels_text
    assert "Full Live Runtime Ready" not in labels_text


def test_phase7_shared_core_boundary_still_excludes_ui_imports():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    shared_core_sources = list((project_root / "shared_core").rglob("*.py"))
    joined = "\n".join(path.read_text(encoding="utf-8") for path in shared_core_sources)

    assert "from v3_app" not in joined
    assert "import v3_app" not in joined
    assert "PySide6" not in joined
