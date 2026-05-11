from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AXES = ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status():
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )

    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
        messages=("Simulation fallback remains available; live output is not verified.",),
    )


def _shell(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        state=AppState.from_runtime_status(_runtime_status()),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        runtime_status=_runtime_status(),
    )


def _page(shell, page_id: str):
    shell.switch_page(page_id)
    return shell.page_widgets[page_id].widget()


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    return "\n".join(
        [label.text() for label in widget.findChildren(QLabel)]
        + [button.text() for button in widget.findChildren(QPushButton)]
    )


def test_post_rc_4d_mapping_route_tables_are_polished_and_preflight_is_split(tmp_path):
    _app()

    from PySide6.QtWidgets import QFrame, QPushButton, QTableWidget

    shell = _shell(tmp_path)
    page = _page(shell, "mapping")

    preflight = _page(shell, "preflight").findChild(QFrame, "preflightDeviceDriverSection")
    assert preflight is not None
    assert preflight.property("uiRole") == "preflightDashboard"
    assert page.findChild(QFrame, "runtimePreflightCard") is None

    for object_name in ("axisRoutingTable", "buttonRoutingTable", "hatRoutingTable"):
        table = page.findChild(QTableWidget, object_name)
        assert table is not None
        assert table.property("polishedRouteTable") is True
        assert table.horizontalHeader().stretchLastSection()
        assert table.verticalHeader().defaultSectionSize() >= 48

    assert page.findChild(QFrame, "routeInspectorPanel") is not None
    assert page.findChild(QPushButton, "changeMappingButton") is not None
    assert "Change the target below" in _label_text(page)


def test_post_rc_4d_mapping_preserves_2c_editor_and_documents_absent_2d(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel, QPushButton

    page = _page(_shell(tmp_path), "mapping")
    page.findChild(QPushButton, "changeMappingButton").click()

    for object_name in ("routeEditorApplyButton", "routeEditorCancelButton", "routeEditorRevertButton"):
        assert page.findChild(QPushButton, object_name) is not None

    if (PROJECT_ROOT / "tests" / "test_post_rc_2d_advanced_mapping_editor.py").exists():
        text = _label_text(page)
        for expected in ("Mapping Draft Review", "Undo", "Redo", "Preset", "Search"):
            assert expected in text
    else:
        text = _label_text(page)
        assert page.findChild(QLabel, "mappingDraftReviewDeferredNotice") is None
        assert "Post-RC 2D" not in text


def test_post_rc_4d_profiles_selection_updates_detail_and_column_width(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel, QTreeWidget

    page = _page(_shell(tmp_path), "profiles")
    tree = page.findChild(QTreeWidget, "profileLibraryTree")
    title = page.findChild(QLabel, "selectedProfileName")

    assert tree is not None
    assert title is not None
    assert tree.columnWidth(0) >= 260
    assert page.property("selectedProfileId")

    built_in = tree.topLevelItem(0).child(2)
    tree.setCurrentItem(built_in)
    _app().processEvents()

    assert page.property("selectedProfileId") == "aggressive-combat"
    assert title.text() == "Aggressive Combat"
    assert "distinct preset" in page.findChild(QLabel, "selectedProfileDescription").text().casefold()


def test_post_rc_4d_modes_use_supported_dropdowns_and_content_sized_cards(tmp_path):
    _app()

    from PySide6.QtWidgets import QComboBox, QFrame

    page = _page(_shell(tmp_path), "modes")

    stack_mode = page.findChild(QComboBox, "stackModeField")
    assert stack_mode is not None
    assert stack_mode.count() > 0
    assert stack_mode.currentText().strip()

    for object_name in ("precisionModeCard", "combatModeCard", "liveModeStateCard", "modeNotesCard"):
        card = page.findChild(QFrame, object_name)
        assert card is not None
        assert card.property("cardSizing") == "content"
        assert card.property("controlPolish") == "post-rc-4d"


def test_post_rc_4d_tuning_pages_keep_selectable_axes_guidance_and_markers(tmp_path):
    _app()

    from PySide6.QtWidgets import QPushButton
    from v3_app.pages.graph_widgets import GraphPreview

    shell = _shell(tmp_path)
    cases = (
        ("base_tuning", "baseTuningGraph", {"Linear", "Adjusted"}),
        ("filtering", "filteringGraph", {"Input", "Filtered"}),
        ("combat_profile", "combatGraph", {"Linear", "Baseline", "Combat"}),
    )

    for page_id, graph_name, markers in cases:
        page = _page(shell, page_id)
        yaw = next(button for button in page.findChildren(QPushButton, "axisListItem") if button.text() == "Yaw")
        yaw.click()
        assert yaw.property("active") is True
        assert yaw.property("selectedAxisPolish") == "post-rc-4d"
        assert "Current feel" in _label_text(page)
        assert "Selected axis note" in _label_text(page)
        graph = page.findChild(GraphPreview, graph_name)
        assert graph is not None
        assert markers <= set(graph.live_marker_items)


def test_post_rc_4d_conditional_rules_logic_precedes_detail_and_supported_parameter_is_honest(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel, QComboBox, QFrame, QTableWidget

    page = _page(_shell(tmp_path), "conditional_rules")
    table = page.findChild(QTableWidget, "conditionalRuleList")
    logic = page.findChild(QFrame, "ruleLogicCard")
    detail = page.findChild(QFrame, "conditionalRuleDetailCard")
    parameter = page.findChild(QComboBox, "ruleParameterField")
    support = page.findChild(QLabel, "ruleParameterSupportNotice")

    assert table is not None
    assert table.property("polishedRuleTable") is True
    assert logic is not None and detail is not None
    assert logic.property("layoutOrder") == "before-detail"
    assert detail.property("layoutOrder") == "after-logic"
    assert parameter is not None
    assert parameter.count() == 1
    assert parameter.itemText(0) == "Output Scale"
    assert support is not None
    assert "Only evaluator-supported parameter target" in support.text()


def test_post_rc_4d_effective_stack_total_change_and_impact_are_deterministic(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel, QFrame

    page = _page(_shell(tmp_path), "effective_response_stack")
    total = page.findChild(QFrame, "stackTotalChangeCard")
    most = page.findChild(QLabel, "stackMostImpactfulStage")

    assert total is not None
    assert total.property("deterministicSummary") is True
    assert most is not None
    assert most.property("impactSource") in {"stage-delta", "unavailable"}
    assert "Output intent is not output write proof" in _label_text(page)


def test_post_rc_4d_matrix_updated_for_control_pages_and_no_runtime_authority():
    matrix = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-human-walkthrough-completion-matrix.md"
    assert matrix.exists()
    text = matrix.read_text(encoding="utf-8")
    assert "Fix included in 4D" in text
    for section in (
        "Mapping",
        "Profiles",
        "Modes",
        "Base Tuning",
        "Filtering",
        "Combat Profile",
        "Conditional Rules",
        "Effective Response Stack",
    ):
        assert f"## {section}" in text
    assert "Post-RC 4E" in text

    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "pages" / "mapping_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "profiles_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "modes_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "base_tuning_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "filtering_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "combat_profile_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "conditional_rules_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "effective_response_stack_page.py",
        )
    )
    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "keyboard.add_hotkey",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
        "UpdateVJD",
        "SetAxis",
        "SetBtn",
        "AcquireVJD",
        "PhysicalInputSampler",
        "VirtualOutputWriteLoop(",
        "CreateService",
        "SetWindowsHookEx",
    ):
        assert forbidden not in sources
