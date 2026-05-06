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
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(
            status=InputStatus.DETECTED,
            detected_device_names=("Thrustmaster T.Flight Hotas One",),
        ),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
        messages=("Simulation mode selected because live output is not verified.",),
    )


def _shell():
    _app()

    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(AppState.from_runtime_status(_status(), driver_detected=True))


def _live_monitor_page(shell=None):
    shell = shell or _shell()
    shell.switch_page("live_monitor")
    return shell.page_widgets["live_monitor"].widget()


def test_phase9_live_monitor_page_constructs_and_is_registered():
    from PySide6.QtWidgets import QLabel

    shell = _shell()
    page = _live_monitor_page(shell)

    assert page.objectName() == "liveMonitorPage"
    assert shell.active_page_id == "live_monitor"
    assert "Live Monitor" in " ".join(label.text() for label in page.findChildren(QLabel))


def test_phase9_axis_selector_contains_all_six_axes_and_updates_graph_titles():
    from PySide6.QtWidgets import QComboBox, QLabel

    page = _live_monitor_page()
    selector = page.findChild(QComboBox, "liveMonitorAxisSelector")

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
    assert "Yaw" in page.findChild(QLabel, "rawTraceTitle").text()
    assert "Yaw" in page.findChild(QLabel, "overlayTraceTitle").text()


def test_phase9_graphs_controls_and_supporting_cards_exist():
    from PySide6.QtWidgets import QCheckBox, QLabel
    from v3_app.pages.graph_widgets import GraphPreview

    page = _live_monitor_page()

    assert page.findChild(GraphPreview, "liveRawTraceGraph") is not None
    assert page.findChild(GraphPreview, "liveRawFinalOverlayGraph") is not None
    assert page.findChild(QCheckBox, "showRawOutputTogetherCheckbox").isChecked()
    assert page.findChild(QLabel, "liveStateText") is not None
    assert page.findChild(QLabel, "buttonsHatsText") is not None


def test_phase9_overlay_checkbox_changes_page_state():
    from PySide6.QtWidgets import QCheckBox

    page = _live_monitor_page()
    checkbox = page.findChild(QCheckBox, "showRawOutputTogetherCheckbox")

    checkbox.setChecked(False)

    assert page.show_raw_and_output_together is False
    assert page.overlay_series_count == 1

    checkbox.setChecked(True)

    assert page.show_raw_and_output_together is True
    assert page.overlay_series_count == 2


def test_phase9_axis_levels_and_button_grids_cover_recovered_ranges():
    from PySide6.QtWidgets import QLabel

    page = _live_monitor_page()

    assert tuple(page.axis_level_widgets) == ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
    for axis in page.axis_level_widgets:
        assert page.findChild(QLabel, f"axisLevel_{axis.replace(' ', '_')}") is not None

    for index in range(1, 16):
        assert page.findChild(QLabel, f"hotasButton_B{index}") is not None

    for index in range(1, 21):
        assert page.findChild(QLabel, f"outputButton_Out{index}") is not None


def test_phase9_runtime_truth_does_not_claim_verified_output():
    from PySide6.QtWidgets import QLabel

    page = _live_monitor_page()
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))

    assert "Detected Unverified" in labels_text
    assert "Output writes verified: false" in labels_text
    assert "Output Verified" not in labels_text
    assert "Full Live Runtime Ready" not in labels_text


def test_phase9_refresh_updates_values_in_place_and_supports_hidden_skip():
    page = _live_monitor_page()
    roll_widget_id = id(page.axis_level_widgets["Roll"])
    raw_graph_id = id(page.raw_trace_graph)
    before_count = len(page.history)

    page.refresh_snapshot(force_new=True)

    assert id(page.axis_level_widgets["Roll"]) == roll_widget_id
    assert id(page.raw_trace_graph) == raw_graph_id
    assert len(page.history) >= before_count
    assert page.should_skip_timer_refresh() is True


def test_phase9_bounded_history_clamps_and_keeps_recent_values():
    from v3_app.pages.live_monitor_data import BoundedTelemetryHistory, TelemetrySample, clamp_axis_value

    history = BoundedTelemetryHistory(capacity=3)
    for index, raw_value in enumerate((-2.0, -0.25, 0.5, 2.0), start=1):
        history.append(
            TelemetrySample(
                index=index,
                raw_axes={"Roll": raw_value},
                final_axes={"Roll": raw_value / 2},
                buttons={"B1": False},
                output_buttons={"Out1": False},
                hat_state="Centered",
                output_hat_state="Centered",
            )
        )

    assert clamp_axis_value(2.5) == 1.0
    assert clamp_axis_value(-2.5) == -1.0
    assert len(history) == 3
    assert history.raw_points("Roll")[0] == (2.0, -0.25)
    assert history.raw_points("Roll")[-1] == (4.0, 1.0)


def test_phase9_runtime_snapshot_can_populate_telemetry_sample():
    from shared_core.runtime.simulated_runtime import SimulatedRuntime
    from v3_app.pages.live_monitor_data import telemetry_sample_from_runtime_snapshot

    snapshot = SimulatedRuntime(deterministic=True).snapshot(_status())
    sample = telemetry_sample_from_runtime_snapshot(snapshot, index=7)

    assert sample.index == 7
    assert set(sample.raw_axes) >= {"Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2"}
    assert set(sample.final_axes) >= {"Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2"}
    assert set(sample.buttons) >= {f"B{index}" for index in range(1, 16)}
    assert set(sample.output_buttons) >= {f"Out{index}" for index in range(1, 21)}


def test_phase9_live_monitor_shared_core_boundary_still_excludes_ui_imports():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    shared_core_sources = list((project_root / "shared_core").rglob("*.py"))
    joined = "\n".join(path.read_text(encoding="utf-8") for path in shared_core_sources)

    assert "from v3_app" not in joined
    assert "import v3_app" not in joined
    assert "PySide6" not in joined
