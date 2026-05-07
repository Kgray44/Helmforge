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

    status = _status()
    workspace_path = None if tmp_path is None else tmp_path / "hotas_bridge_config_v3.json"
    return HelmForgeShell(
        AppState.from_runtime_status(status, driver_detected=True),
        workspace_path=workspace_path,
    )


def _mapping_page(shell):
    shell.switch_page("mapping")
    return shell.page_widgets["mapping"].widget()


def test_phase6b_axis_route_editors_exist_and_update_workspace_dirty():
    from PySide6.QtWidgets import QComboBox

    shell = _shell()
    page = _mapping_page(shell)
    raw_combo = page.findChild(QComboBox, "axisRaw_roll")
    logical_combo = page.findChild(QComboBox, "axisLogical_roll")
    runtime_combo = page.findChild(QComboBox, "axisRuntime_roll")

    assert "Axis 8" in [raw_combo.itemText(index) for index in range(raw_combo.count())]
    assert "SL1" in [logical_combo.itemText(index) for index in range(logical_combo.count())]
    assert "RZ(axis6)" in [runtime_combo.itemText(index) for index in range(runtime_combo.count())]

    raw_combo.setCurrentText("Axis 4")

    assert shell.state.saved is False
    assert shell.workspace.mappings.axis_routes[0].raw_axis_channel == "Axis 4"


def test_phase6b_axis_invert_and_button_hat_edits_update_workspace_dirty():
    from PySide6.QtWidgets import QCheckBox, QComboBox

    shell = _shell()
    page = _mapping_page(shell)

    invert = page.findChild(QCheckBox, "invert_roll")
    invert.setChecked(True)
    assert shell.workspace.mappings.axis_routes[0].invert is True

    button_combo = page.findChild(QComboBox, "buttonHotas_0")
    button_combo.setCurrentText("B15")
    assert shell.workspace.mappings.button_routes[0].hotas_button == 15

    hat_combo = page.findChild(QComboBox, "hatRight_0")
    hat_combo.setCurrentText("20")
    assert shell.workspace.mappings.hat_routes[0].right_button == 20
    assert shell.state.saved is False


def test_phase6b_button_add_remove_reset_actions_are_functional():
    from PySide6.QtWidgets import QPushButton, QTableWidget

    shell = _shell()
    page = _mapping_page(shell)
    table = page.findChild(QTableWidget, "buttonRoutingTable")

    table.selectRow(0)
    page.findChild(QPushButton, "removeButtonRouteButton").click()

    assert table.rowCount() == 14
    assert len(shell.workspace.mappings.button_routes) == 14
    assert shell.state.saved is False

    page.findChild(QPushButton, "addButtonRouteButton").click()

    assert table.rowCount() == 15
    assert len(shell.workspace.mappings.button_routes) == 15

    table.cellWidget(0, 0).setCurrentText("B15")
    page.findChild(QPushButton, "resetButtonRoutesButton").click()

    assert [route.hotas_button for route in shell.workspace.mappings.button_routes] == list(range(1, 16))
    assert [route.output_button for route in shell.workspace.mappings.button_routes] == list(range(1, 16))


def test_phase6b_hat_add_remove_actions_are_functional():
    from PySide6.QtWidgets import QPushButton, QTableWidget

    shell = _shell()
    page = _mapping_page(shell)
    table = page.findChild(QTableWidget, "hatRoutingTable")

    table.selectRow(0)
    page.findChild(QPushButton, "removeHatRouteButton").click()

    assert table.rowCount() == 0
    assert shell.workspace.mappings.hat_routes == ()

    page.findChild(QPushButton, "addHatRouteButton").click()

    assert table.rowCount() == 1
    assert shell.workspace.mappings.hat_routes[0].hotas_hat == 1
    assert shell.workspace.mappings.hat_routes[0].right_button == 18


def test_phase6b_save_workspace_round_trips_mapping_edit_and_revert_restores(tmp_path):
    from PySide6.QtWidgets import QComboBox, QPushButton
    from shared_core.persistence.workspace_store import load_workspace

    shell = _shell(tmp_path)
    page = _mapping_page(shell)
    raw_combo = page.findChild(QComboBox, "axisRaw_roll")
    raw_combo.setCurrentText("Axis 4")

    shell.footer.findChild(QPushButton, "saveWorkspaceButton").click()

    saved = load_workspace(tmp_path / "hotas_bridge_config_v3.json").workspace
    assert saved.mappings.axis_routes[0].raw_axis_channel == "Axis 4"
    assert shell.state.saved is True

    page = _mapping_page(shell)
    page.findChild(QComboBox, "axisRaw_roll").setCurrentText("Axis 5")
    shell.footer.findChild(QPushButton, "revertButton").click()

    assert shell.workspace.mappings.axis_routes[0].raw_axis_channel == "Axis 4"
    assert shell.state.saved is True
    assert _mapping_page(shell).findChild(QComboBox, "axisRaw_roll").currentText() == "Axis 4"


def test_phase6b_mapping_page_stays_truthful_about_runtime_output():
    from PySide6.QtWidgets import QLabel

    shell = _shell()
    page = _mapping_page(shell)
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))

    assert "Output writes verified: false" in labels_text
    assert "Output Verified" not in labels_text
    assert "Full Live Runtime Ready false" in labels_text


def test_phase6b_shared_core_boundary_still_excludes_ui_imports():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    shared_core_sources = list((project_root / "shared_core").rglob("*.py"))
    joined = "\n".join(path.read_text(encoding="utf-8") for path in shared_core_sources)

    assert "from v3_app" not in joined
    assert "import v3_app" not in joined
    assert "PySide6" not in joined
