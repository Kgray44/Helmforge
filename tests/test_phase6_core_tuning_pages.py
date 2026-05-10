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


def _runtime_status(truth: RuntimeTruth = RuntimeTruth.BLOCKED_MISSING_DEVICE) -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=truth,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
        messages=("Simulation mode selected because live output is not verified.",),
    )


def test_phase6_modes_page_constructs_and_shows_recovered_defaults():
    _app()

    from PySide6.QtWidgets import QLabel
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.modes_page import ModesPage
    from v3_app.services.app_state import AppState

    status = _runtime_status()
    page = ModesPage(
        state=AppState.from_runtime_status(status, driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=status,
    )
    text = " ".join(label.text() for label in page.findChildren(QLabel))

    assert page.objectName() == "modesPage"
    assert "Precision Hold Buttons" in text
    assert "0" in text
    assert "Combat Trigger Buttons" in text
    assert "Not configured" in text
    assert "Combat Zoom/Aim Buttons" in text
    assert "5" in text
    assert "Stack Mode" in text
    assert "multiply" in text
    assert "Output Verified" not in text
    assert "Full Live Runtime Ready" not in text


def test_phase6_base_tuning_page_constructs_axis_list_and_true_linear_reference():
    _app()

    from PySide6.QtWidgets import QLabel, QPushButton
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.base_tuning_page import BaseTuningPage
    from v3_app.pages.graph_data import base_response_preview_data
    from v3_app.services.app_state import AppState

    workspace = create_default_workspace()
    status = _runtime_status()
    page = BaseTuningPage(
        state=AppState.from_runtime_status(status, driver_detected=True),
        workspace=workspace,
        runtime_status=status,
    )
    text = " ".join(
        [label.text() for label in page.findChildren(QLabel)]
        + [button.text() for button in page.findChildren(QPushButton)]
    )
    data = base_response_preview_data(workspace.tuning.axes["roll"])

    assert page.objectName() == "baseTuningPage"
    for axis in ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2"):
        assert axis in text
    assert all(x == y for x, y in data.linear)
    assert data.adjusted != data.linear


def test_phase6_editing_base_tuning_field_marks_workspace_dirty():
    _app()

    from PySide6.QtWidgets import QLineEdit
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell()
    shell.switch_page("base_tuning")
    page = shell.page_widgets["base_tuning"].widget()
    field = page.findChild(QLineEdit, "curveStrengthField")

    assert shell.state.saved is True
    field.setText("0.41")
    field.editingFinished.emit()

    assert shell.state.saved is False
    assert "Base Tuning" in shell.state.status_message


def test_phase6_filtering_page_exposes_parameters_and_uses_phase3_filtering_math():
    _app()

    from PySide6.QtWidgets import QLabel
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.filtering_page import FilteringPage
    from v3_app.pages.graph_data import filtering_step_preview_data
    from v3_app.services.app_state import AppState

    workspace = create_default_workspace()
    status = _runtime_status()
    page = FilteringPage(
        state=AppState.from_runtime_status(status, driver_detected=True),
        workspace=workspace,
        runtime_status=status,
    )
    text = " ".join(label.text() for label in page.findChildren(QLabel))
    data = filtering_step_preview_data(workspace.filtering.axes["roll"])

    assert page.objectName() == "filteringPage"
    for expected in ("Center Alpha", "Edge Alpha", "Same Slew Limit", "Reverse Slew Limit"):
        assert expected in text
    assert data.raw != data.filtered
    assert len(data.raw) == len(data.filtered)


def test_phase6_combat_profile_page_exposes_recovered_parameters():
    _app()

    from PySide6.QtWidgets import QLabel
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.combat_profile_page import CombatProfilePage
    from v3_app.pages.graph_data import combat_response_preview_data
    from v3_app.services.app_state import AppState

    workspace = create_default_workspace()
    status = _runtime_status()
    page = CombatProfilePage(
        state=AppState.from_runtime_status(status, driver_detected=True),
        workspace=workspace,
        runtime_status=status,
    )
    text = " ".join(label.text() for label in page.findChildren(QLabel))
    data = combat_response_preview_data(workspace.tuning.axes["roll"], workspace.combat.axes["roll"])

    assert page.objectName() == "combatProfilePage"
    for expected in (
        "Combat Curve",
        "Combat Scale",
        "Combat Center Alpha",
        "Combat Edge Alpha",
        "Combat Same Slew",
        "Combat Reverse Slew",
    ):
        assert expected in text
    assert data.combat != data.baseline


def test_phase6_profiles_page_lists_recovered_profiles_and_setup_summary():
    _app()

    from PySide6.QtWidgets import QLabel, QTreeWidget
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.profiles_page import ProfilesPage
    from v3_app.services.app_state import AppState

    workspace = create_default_workspace()
    status = _runtime_status()
    page = ProfilesPage(
        state=AppState.from_runtime_status(status, driver_detected=True),
        workspace=workspace,
        runtime_status=status,
    )
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))
    tree_text: list[str] = []
    tree = page.findChild(QTreeWidget, "profileLibraryTree")
    for index in range(tree.topLevelItemCount()):
        parent = tree.topLevelItem(index)
        tree_text.append(parent.text(0))
        for child_index in range(parent.childCount()):
            child = parent.child(child_index)
            tree_text.extend(child.text(column) for column in range(tree.columnCount()))
    text = " ".join((*tree_text, labels_text))

    for expected in (
        "Balanced Flight",
        "Precision Tracking",
        "Aggressive Combat",
        "Smooth Cinematic",
        "Current Workspace",
        "Personal",
        "Active",
        "hotas_bridge_config_v3.json",
        "Mapped Axes",
        "6",
        "Stack Mode",
        "multiply",
    ):
        assert expected in text


def test_phase6_shell_registers_core_tuning_pages_and_preserves_mapping():
    _app()

    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell()
    expected_objects = {
        "mapping": "mappingPage",
        "modes": "modesPage",
        "base_tuning": "baseTuningPage",
        "filtering": "filteringPage",
        "combat_profile": "combatProfilePage",
        "profiles": "profilesPage",
    }

    for page_id, object_name in expected_objects.items():
        shell.switch_page(page_id)
        assert shell.page_widgets[page_id].widget().objectName() == object_name


def test_phase6_runtime_truth_surfaces_remain_unverified():
    _app()

    from PySide6.QtWidgets import QLabel
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell(AppState.from_runtime_status(_runtime_status(), driver_detected=True))
    for page_id in ("modes", "base_tuning", "filtering", "combat_profile", "profiles"):
        shell.switch_page(page_id)
        text = " ".join(label.text() for label in shell.page_widgets[page_id].widget().findChildren(QLabel))
        assert "Output writes verified: false" in text or "Output Unverified" in text
        assert "Full Live Runtime Ready" not in text
        assert "Output Verified" not in text


def test_phase6_shared_core_boundary_still_excludes_ui_imports():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    shared_core_sources = list((project_root / "shared_core").rglob("*.py"))
    joined = "\n".join(path.read_text(encoding="utf-8") for path in shared_core_sources)

    assert "from v3_app" not in joined
    assert "import v3_app" not in joined
    assert "PySide6" not in joined
