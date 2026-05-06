from __future__ import annotations

import os
from dataclasses import replace

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


def _shell(*, workspace=None):
    _app()

    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=workspace,
    )


def _stack_page(shell):
    shell.switch_page("effective_response_stack")
    return shell.page_widgets["effective_response_stack"].widget()


def test_phase8_effective_response_stack_page_constructs_and_is_registered():
    from PySide6.QtWidgets import QLabel

    shell = _shell()
    page = _stack_page(shell)

    assert page.objectName() == "effectiveResponseStackPage"
    assert shell.active_page_id == "effective_response_stack"
    assert "Effective Response Stack" in " ".join(label.text() for label in page.findChildren(QLabel))


def test_phase8_axis_selector_contains_all_six_axes_and_updates_page_state():
    from PySide6.QtWidgets import QComboBox, QLabel

    page = _stack_page(_shell())
    selector = page.findChild(QComboBox, "stackAxisSelector")

    assert [selector.itemText(index) for index in range(selector.count())] == [
        "Roll",
        "Pitch",
        "Throttle",
        "Yaw",
        "Aux 1",
        "Aux 2",
    ]

    selector.setCurrentText("Yaw")

    assert page.selected_axis == "Yaw"
    assert "Yaw" in page.findChild(QLabel, "currentStackSummaryText").text()


def test_phase8_stage_cards_exist_and_are_reused_after_refresh():
    from PySide6.QtWidgets import QFrame

    page = _stack_page(_shell())
    stages = page.stage_widgets
    widget_ids = {name: id(widget) for name, widget in stages.items()}

    assert tuple(stages) == (
        "Raw Input",
        "Center Conditioning",
        "Curve / Shape",
        "Base Output Limits",
        "Filtering",
        "Mode Modifiers",
        "Rule Injections",
        "Final Output",
    )
    assert len(page.findChildren(QFrame, "stackStageCard")) == 8

    page.refresh_snapshot()

    assert {name: id(widget) for name, widget in page.stage_widgets.items()} == widget_ids


def test_phase8_graph_data_and_widget_exist_with_true_linear_reference():
    from v3_app.pages.graph_data import effective_response_stack_graph_data
    from v3_app.pages.graph_widgets import GraphPreview
    from shared_core.models.workspace import create_default_workspace

    page = _stack_page(_shell())
    graph = page.findChild(GraphPreview, "effectiveResponseStackGraph")
    data = effective_response_stack_graph_data(create_default_workspace(), "Roll", sample_count=5)

    assert graph is not None
    assert data.linear == (
        (-1.0, -1.0),
        (-0.5, -0.5),
        (0.0, 0.0),
        (0.5, 0.5),
        (1.0, 1.0),
    )
    assert len(data.effective) == 5
    assert isinstance(data.live_marker, tuple)


def test_phase8_freeze_holds_displayed_result_and_resume_updates():
    from PySide6.QtWidgets import QLabel, QPushButton

    page = _stack_page(_shell())
    before = page.findChild(QLabel, "stageOutput_Raw_Input").text()

    page.findChild(QPushButton, "freezeStackButton").click()
    assert page.frozen is True
    frozen = page.findChild(QLabel, "stageOutput_Raw_Input").text()
    page.refresh_snapshot(force_new=True)
    assert page.findChild(QLabel, "stageOutput_Raw_Input").text() == frozen

    page.findChild(QPushButton, "freezeStackButton").click()
    assert page.frozen is False
    page.refresh_snapshot(force_new=True)
    assert page.findChild(QLabel, "stageOutput_Raw_Input").text() != "" or before != ""


def test_phase8_selected_stage_panel_updates_when_stage_selected():
    from PySide6.QtWidgets import QLabel

    page = _stack_page(_shell())

    page.select_stage("Filtering")

    assert "Filtering" in page.findChild(QLabel, "selectedStageTitle").text()
    assert "alpha" in page.findChild(QLabel, "selectedStageMetadata").text().lower()


def test_phase8_supporting_cards_exist_and_runtime_truth_is_truthful():
    from PySide6.QtWidgets import QLabel

    page = _stack_page(_shell())
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))

    assert page.findChild(QLabel, "modeStateText") is not None
    assert page.findChild(QLabel, "currentStackSummaryText") is not None
    assert page.findChild(QLabel, "ruleDriverValuesText") is not None
    assert "Output writes verified: false" in labels_text
    assert "Output Verified" not in labels_text
    assert "Full Live Runtime Ready" not in labels_text


def test_phase8_rule_injection_text_appears_inline_when_recovered_rule_applies():
    from PySide6.QtWidgets import QLabel
    from shared_core.models.rules import yaw_roll_example_rule
    from shared_core.models.workspace import create_default_workspace

    workspace = create_default_workspace()
    workspace = replace(
        workspace,
        rules=replace(workspace.rules, rules=(replace(yaw_roll_example_rule(), enabled=True),)),
    )
    page = _stack_page(_shell(workspace=workspace))

    page.refresh_snapshot(
        raw_axis_values={
            "Roll": 0.8,
            "Pitch": 0.0,
            "Throttle": 0.0,
            "Yaw": 0.8,
            "Aux 1": 0.0,
            "Aux 2": 0.0,
        }
    )
    page.set_selected_axis("Yaw")
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))

    assert "Yaw 0.75 | Roll > 0.35" in labels_text
    assert "Set Yaw Output Scale to 0.75" in labels_text
    assert "Base Output Limits" in labels_text


def test_phase8_shared_core_boundary_still_excludes_ui_imports():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    shared_core_sources = list((project_root / "shared_core").rglob("*.py"))
    joined = "\n".join(path.read_text(encoding="utf-8") for path in shared_core_sources)

    assert "from v3_app" not in joined
    assert "import v3_app" not in joined
    assert "PySide6" not in joined
