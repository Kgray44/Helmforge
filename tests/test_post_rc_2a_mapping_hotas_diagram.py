from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_post_rc_2a_model_includes_required_hotas_controls():
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.hotas_diagram_model import build_hotas_diagram_model

    model = build_hotas_diagram_model(create_default_workspace())
    by_label = {control.display_label: control for control in model.controls}

    for label in (
        "Roll axis",
        "Pitch axis",
        "Throttle axis",
        "Yaw axis",
        "Aux 1",
        "Aux 2",
        "Hat / POV",
    ):
        assert label in by_label

    for index in range(1, 16):
        assert f"B{index}" in by_label

    for control in model.controls:
        assert control.control_id
        assert control.display_label
        assert control.control_type in {"axis", "button", "hat", "throttle", "stick", "base"}
        assert 0.0 <= control.anchor_x <= 1.0
        assert 0.0 <= control.anchor_y <= 1.0


def test_post_rc_2a_model_uses_default_workspace_mapping_data():
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.hotas_diagram_model import build_hotas_diagram_model

    model = build_hotas_diagram_model(
        create_default_workspace(),
        raw_axis_values={"Roll": 0.25, "Pitch": -0.5},
        button_states={"B1": True},
        hat_state="Right",
    )
    by_id = {control.control_id: control for control in model.controls}

    roll = by_id["axis_roll"]
    assert roll.raw_input_channel == "Axis 1"
    assert roll.mapped_function == "Roll -> X"
    assert roll.output_intent_target == "Output intent: X(axis1)"
    assert roll.current_value_state == "+0.25"

    pitch = by_id["axis_pitch"]
    assert pitch.raw_input_channel == "Axis 2"
    assert pitch.current_value_state == "-0.50"

    button = by_id["button_b1"]
    assert button.raw_input_channel == "B1"
    assert button.mapped_function == "Virtual button 1"
    assert button.output_intent_target == "Output intent: Button 1"
    assert button.current_value_state == "Pressed"

    hat = by_id["hat_pov"]
    assert hat.raw_input_channel == "Hat 1"
    assert hat.mapped_function == "POV 1"
    assert "Right" in hat.current_value_state


def test_post_rc_2a_output_intent_labels_do_not_claim_writes_or_verification():
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.hotas_diagram_model import build_hotas_diagram_model, format_hotas_control_tooltip

    model = build_hotas_diagram_model(create_default_workspace())
    details = "\n".join(format_hotas_control_tooltip(control) for control in model.routed_controls)
    lower_details = details.casefold()

    assert "Output intent:" in details
    assert "read-only visual/diagnostic" in lower_details
    assert "output intent is not output write proof" in lower_details

    for forbidden in (
        "output verified",
        "live output active",
        "writing to vjoy",
        "write to vjoy",
        "full live runtime ready",
    ):
        assert forbidden not in lower_details


def test_post_rc_2a_mapping_page_includes_hotas_diagram_card():
    _app()

    from PySide6.QtWidgets import QLabel, QWidget
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.mapping_page import MappingPage
    from v3_app.services.app_state import build_initial_app_state

    page = MappingPage(state=build_initial_app_state(), workspace=create_default_workspace())

    assert page.findChild(QWidget, "hotasDiagramCard") is not None
    assert page.findChild(QWidget, "hotasDiagramWidget") is not None

    labels_text = "\n".join(label.text() for label in page.findChildren(QLabel))
    assert "HOTAS Diagram" in labels_text
    assert "physical controls, current mappings, and output intent targets" in labels_text
    assert "Read-only visual/diagnostic diagram" in labels_text
    assert "Output intent is not output write proof" in labels_text


def test_post_rc_2a_diagram_widget_constructs_offscreen_with_marker_tooltips():
    _app()

    from PySide6.QtWidgets import QLabel
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.hotas_diagram_model import build_hotas_diagram_model
    from v3_app.widgets.hotas_diagram import HotasDiagramWidget

    widget = HotasDiagramWidget(build_hotas_diagram_model(create_default_workspace()))
    widget.resize(980, 520)
    widget.show()
    _app().processEvents()

    markers = [
        marker
        for marker in widget.findChildren(QLabel)
        if marker.property("hotasDiagramMarker") is True
    ]
    assert len(markers) >= 22

    roll_marker = widget.findChild(QLabel, "hotasMarker_axis_roll")
    assert roll_marker is not None
    assert "Roll axis" in roll_marker.text()
    assert "Raw channel: Axis 1" in roll_marker.toolTip()
    assert "Mapped function: Roll -> X" in roll_marker.toolTip()
    assert "Output intent: X(axis1)" in roll_marker.toolTip()
    assert "Read-only visual/diagnostic only" in roll_marker.toolTip()


def test_post_rc_2a_report_documents_scope_and_runtime_truth():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-2a-mapping-hotas-diagram-report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "Post-RC 2A",
        "diagram approach chosen",
        "controls represented",
        "mapping data used",
        "UI placement",
        "deferred to Post-RC 2B",
        "runtime truth preservation",
        "output intent is not output write proof",
        "no hardware polling",
        "no vJoy writes",
        "simulation mode remains available",
    ):
        assert required in text


def test_post_rc_2a_no_runtime_authority_introduced():
    source_paths = (
        PROJECT_ROOT / "v3_app" / "services" / "hotas_diagram_model.py",
        PROJECT_ROOT / "v3_app" / "widgets" / "hotas_diagram.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths if path.exists())

    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "PhysicalInputSampler",
        "VirtualOutputWriteLoop",
        "read_current_state(",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
        "autosave",
    ):
        assert forbidden not in sources
