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


def _runtime_status(
    *,
    truth: RuntimeTruth,
    input_status: InputStatus = InputStatus.MISSING,
    output_status: OutputStatus = OutputStatus.VJOY_DETECTED,
    output_verified: bool = False,
) -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=truth,
        input=InputDeviceDetection(status=input_status),
        output=OutputBackendDetection(
            status=output_status,
            backend_name="vJoy" if output_status is not OutputStatus.VJOY_MISSING else None,
            live_output_writes_verified=output_verified,
        ),
        messages=("Simulation mode selected because live output is not verified.",),
    )


def _mapping_page(*, truth: RuntimeTruth = RuntimeTruth.BLOCKED_MISSING_DEVICE):
    _app()

    from v3_app.pages.mapping_page import MappingPage
    from v3_app.services.app_state import AppState

    runtime_status = _runtime_status(
        truth=truth,
        input_status=InputStatus.DETECTED if truth is RuntimeTruth.DETECTED_UNVERIFIED else InputStatus.MISSING,
        output_status=OutputStatus.VJOY_DETECTED,
        output_verified=False,
    )
    state = AppState.from_runtime_status(runtime_status, driver_detected=True)
    return MappingPage(state=state, runtime_status=runtime_status), state


def _table_text(table) -> str:
    text: list[str] = []
    for row in range(table.rowCount()):
        for column in range(table.columnCount()):
            item = table.item(row, column)
            if item is not None:
                text.append(item.text())
    return " ".join(text)


def test_phase5_mapping_page_constructs_and_replaces_shell_placeholder():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell()
    mapping_page = shell.page_widgets["mapping"].widget()

    assert mapping_page.objectName() == "mappingPage"
    assert mapping_page.findChild(QWidget, "routingOverviewCard") is not None
    assert mapping_page.findChild(QWidget, "liveRouteSummaryCard") is not None
    assert mapping_page.findChild(QWidget, "runtimePreflightCard") is None
    assert shell.page_widgets["preflight"].widget().objectName() == "preflightPage"


def test_phase5_routing_overview_counts_match_recovered_defaults():
    page, _state = _mapping_page()

    from PySide6.QtWidgets import QLabel

    count_labels = [label.text() for label in page.findChildren(QLabel, "routeCountBadge")]

    assert count_labels[:3] == ["6", "15", "1"]
    assert "Live output still depends on the runtime verification gate" in " ".join(
        label.text() for label in page.findChildren(QLabel)
    )


def test_phase5_axis_routing_table_contains_recovered_mappings():
    page, _state = _mapping_page()

    from PySide6.QtWidgets import QTableWidget

    table = page.findChild(QTableWidget, "axisRoutingTable")
    table_text = _table_text(table)

    assert table.rowCount() == 6
    for expected in (
        "Roll Axis 1 X Virtual X",
        "Pitch Axis 2 Y Virtual Y",
        "Throttle Axis 3 Z Virtual Z",
        "Yaw Axis 6 RZ Virtual RX",
        "Aux 1 Axis 7 SL0 Virtual RY",
        "Aux 2 Axis 8 RX Virtual RZ",
    ):
        assert expected in table_text


def test_phase5_live_route_summary_preserves_recovered_route_text():
    page, _state = _mapping_page()

    from PySide6.QtWidgets import QLabel

    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))

    for expected in (
        "Input 1 -> Roll -> Virtual X",
        "Input 2 -> Pitch -> Virtual Y",
        "Input 3 -> Throttle -> Virtual Z",
        "Input 6 -> Yaw -> Virtual RX",
        "Input 7 -> Aux 1 -> Virtual RY",
        "Input 8 -> Aux 2 -> Virtual RZ",
    ):
        assert expected in labels_text
    assert "Live output still depends" in labels_text or "Safe fallback" in labels_text


def test_phase5_preflight_page_is_truthful_for_missing_and_unverified_states():
    for truth, expected in (
        (RuntimeTruth.BLOCKED_MISSING_DEVICE, "Waiting for HOTAS input"),
        (RuntimeTruth.DETECTED_UNVERIFIED, "HOTAS input detected"),
    ):
        from v3_app.pages.preflight_page import PreflightPage
        from v3_app.services.app_state import AppState

        runtime_status = _runtime_status(
            truth=truth,
            input_status=InputStatus.DETECTED if truth is RuntimeTruth.DETECTED_UNVERIFIED else InputStatus.MISSING,
            output_status=OutputStatus.VJOY_DETECTED,
            output_verified=False,
        )
        page = PreflightPage(state=AppState.from_runtime_status(runtime_status), runtime_status=runtime_status)
        labels_text = " ".join(label.text() for label in page.findChildren(__import__("PySide6.QtWidgets").QtWidgets.QLabel))

        assert expected in labels_text
        assert "vJoy detected, output not verified" in labels_text
        assert "Proofs still required" in labels_text
        assert "Output Verified" not in labels_text


def test_phase5_button_and_hat_tables_use_recovered_defaults():
    page, _state = _mapping_page()

    from PySide6.QtWidgets import QTableWidget

    button_table = page.findChild(QTableWidget, "buttonRoutingTable")
    hat_table = page.findChild(QTableWidget, "hatRoutingTable")

    assert button_table.rowCount() == 15
    assert button_table.columnCount() == 2
    assert button_table.item(0, 0).text() in {"B1", "1"}
    assert button_table.item(14, 0).text() in {"B15", "15"}

    assert hat_table.rowCount() == 1
    assert "Hat 1 POV 1 7 18 19 0 Centered" in _table_text(hat_table)


def test_phase5_invert_edit_marks_workspace_dirty():
    _app()

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel, QCheckBox, QPushButton
    from v3_app.widgets.hotas_diagram import HotasDiagramWidget
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell()
    shell.show()
    mapping_page = shell.page_widgets["mapping"].widget()
    diagram = mapping_page.findChild(HotasDiagramWidget, "hotasDiagramWidget")
    marker = diagram.findChild(QLabel, "hotasMarker_axis_roll")

    assert shell.state.saved is True

    QTest.mouseClick(marker, Qt.MouseButton.LeftButton)
    _app().processEvents()
    invert_checkbox = mapping_page.findChild(QCheckBox, "routeEditorAxisInvertCheckbox")
    assert invert_checkbox is not None
    invert_checkbox.setChecked(not invert_checkbox.isChecked())
    apply = mapping_page.findChild(QPushButton, "routeEditorApplyButton")
    apply.click()

    assert shell.state.saved is False
    assert "mapping" in shell.state.status_message.lower()


def test_phase5_mapping_page_does_not_move_ui_into_shared_core():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    shared_core_sources = list((project_root / "shared_core").rglob("*.py"))
    joined = "\n".join(path.read_text(encoding="utf-8") for path in shared_core_sources)

    assert "from v3_app" not in joined
    assert "import v3_app" not in joined
    assert "PySide6" not in joined
