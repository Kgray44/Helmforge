from __future__ import annotations

import os
from pathlib import Path

from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AXES = ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status() -> RuntimePreflightStatus:
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


def _state():
    from v3_app.services.app_state import AppState

    return AppState.from_runtime_status(_runtime_status())


def _workspace():
    from shared_core.models.workspace import create_default_workspace

    return create_default_workspace()


def _shell(tmp_path):
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        state=_state(),
        workspace=_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        runtime_status=_runtime_status(),
    )


def _page(shell, page_id: str):
    shell.switch_page(page_id)
    return shell.page_widgets[page_id].widget()


def _axis_buttons(page):
    from PySide6.QtWidgets import QPushButton

    return page.findChildren(QPushButton, "axisListItem")


def _text(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    return "\n".join(
        [label.text() for label in widget.findChildren(QLabel)]
        + [button.text() for button in widget.findChildren(QPushButton)]
    )


def _field_value(page, object_name: str) -> str:
    from PySide6.QtWidgets import QLineEdit

    field = page.findChild(QLineEdit, object_name)
    assert field is not None
    return field.text()


def test_post_rc_4a_mapped_axis_blocks_are_selectable_and_update_selected_state(tmp_path):
    _app()

    shell = _shell(tmp_path)
    cases = (
        ("base_tuning", "curveStrengthField", "0.58"),
        ("filtering", "centerAlphaField", "0.25"),
        ("combat_profile", "combatScaleField", "0.75"),
    )

    for page_id, representative_field, expected_yaw_value in cases:
        page = _page(shell, page_id)
        buttons = _axis_buttons(page)

        assert tuple(button.text() for button in buttons) == AXES
        assert all(button.isEnabled() for button in buttons)

        yaw = next(button for button in buttons if button.text() == "Yaw")
        yaw.click()

        assert shell.state.selected_axis == "Yaw"
        assert yaw.property("active") is True
        assert _field_value(page, representative_field) == expected_yaw_value
        assert "Selected Axis\nYaw" in _text(page)


def test_post_rc_4a_enum_parameters_use_supported_non_editable_dropdowns(tmp_path):
    _app()

    from PySide6.QtWidgets import QComboBox

    shell = _shell(tmp_path)
    page = _page(shell, "base_tuning")
    curve_mode = page.findChild(QComboBox, "curveModeField")

    assert curve_mode is not None
    assert not curve_mode.isEditable()
    assert [curve_mode.itemText(index) for index in range(curve_mode.count())] == ["s"]

    curve_mode.setCurrentText("unsupported")
    assert curve_mode.currentText() == "s"


def test_post_rc_4a_numeric_validators_reject_letters_and_clamp_workspace_values(tmp_path):
    _app()

    from PySide6.QtGui import QValidator
    from PySide6.QtWidgets import QLineEdit

    shell = _shell(tmp_path)
    representatives = (
        ("base_tuning", "deadzoneField", ("tuning", "deadzone"), 0.50),
        ("filtering", "centerAlphaField", ("filtering", "center_alpha"), 1.00),
        ("combat_profile", "combatScaleField", ("combat", "combat_scale"), 2.00),
    )

    for page_id, field_name, (section, attribute), expected_max in representatives:
        page = _page(shell, page_id)
        field = page.findChild(QLineEdit, field_name)
        assert field is not None
        validator = field.validator()
        assert validator is not None
        assert validator.validate("abc", 0)[0] == QValidator.State.Invalid
        assert validator.validate("999", 0)[0] != QValidator.State.Acceptable

        field.setText("999")
        field.editingFinished.emit()

        assert float(field.text()) == expected_max
        axis_object = getattr(
            page,
            {"tuning": "_tuning", "filtering": "_settings", "combat": "_combat"}[section],
        )
        assert getattr(axis_object, attribute) == expected_max

        field.setText("abc")
        field.editingFinished.emit()

        assert float(field.text()) == expected_max
        axis_object = getattr(
            page,
            {"tuning": "_tuning", "filtering": "_settings", "combat": "_combat"}[section],
        )
        assert getattr(axis_object, attribute) == expected_max


def test_post_rc_4a_live_snapshot_and_guidance_are_structured_for_scanning(tmp_path):
    _app()

    shell = _shell(tmp_path)
    for page_id in ("base_tuning", "filtering", "combat_profile"):
        page = _page(shell, page_id)
        text = _text(page)

        for required in (
            "Input Source",
            "Selected Axis",
            "Raw Value",
            "Output Intent",
            "Runtime Truth",
        ):
            assert required in text

        for required in (
            "Current feel",
            "What this setting affects",
            "Suggested range",
            "Caution",
            "Selected axis note",
        ):
            assert required in text


def test_post_rc_4a_live_graph_markers_are_exposed_and_reused(tmp_path):
    _app()

    from v3_app.pages.graph_widgets import GraphPreview

    shell = _shell(tmp_path)
    cases = (
        ("base_tuning", "baseTuningGraph", {"Linear", "Adjusted"}),
        ("filtering", "filteringGraph", {"Input", "Filtered"}),
        ("combat_profile", "combatGraph", {"Linear", "Baseline", "Combat"}),
    )

    for page_id, graph_name, expected_markers in cases:
        page = _page(shell, page_id)
        graph = page.findChild(GraphPreview, graph_name)
        assert graph is not None
        assert expected_markers <= set(graph.live_marker_items)

        first_series = dict(graph._series_items)
        first_markers = dict(graph.live_marker_items)
        first_count = len(graph.plot.listDataItems())

        page._refresh_live_sample(raw_axis_values={axis: 0.25 for axis in AXES})

        assert graph._series_items == first_series
        for name, marker in first_markers.items():
            assert graph.live_marker_items[name] is marker
        assert len(graph.plot.listDataItems()) == first_count


def test_post_rc_4a_does_not_introduce_runtime_authority():
    source_paths = (
        PROJECT_ROOT / "v3_app" / "pages" / "base_tuning_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "filtering_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "combat_profile_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "graph_widgets.py",
        PROJECT_ROOT / "v3_app" / "pages" / "page_helpers.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "keyboard.add_hotkey",
        "VideoWriter",
        "OpenAI(",
        "VirtualOutputWriteLoop",
        "write_output",
        "hardware_poll",
        "auto_save",
    ):
        assert forbidden not in sources
