from __future__ import annotations

import csv
import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
        messages=("Simulation mode selected because live output is not verified.",),
    )


def _settings(tmp_path):
    from v3_app.recorder.recorder_settings import FlightRecorderSettings

    return FlightRecorderSettings.from_dict(
        {**FlightRecorderSettings.defaults().to_dict(), "destination_folder": str(tmp_path)}
    )


def _samples():
    from v3_app.overlay.telemetry_buffer import OverlayTelemetrySample

    return (
        OverlayTelemetrySample(timestamp=10.0, axes={"Yaw": 0.0, "Pitch": 0.0}, source="Final output"),
        OverlayTelemetrySample(timestamp=10.5, axes={"Yaw": 0.4, "Pitch": 0.0}, source="Final output"),
        OverlayTelemetrySample(timestamp=11.0, axes={"Yaw": 0.4, "Pitch": -0.3}, source="Final output"),
        OverlayTelemetrySample(timestamp=12.0, axes={"Yaw": 0.0, "Pitch": -0.3, "Roll": 0.2}, source="Final output"),
    )


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_post_rc_3b_session_summary_and_timeline_are_generated_from_existing_samples(tmp_path):
    from v3_app.recorder.session_review import build_recorder_session_review

    session = build_recorder_session_review(
        settings=_settings(tmp_path),
        telemetry_samples=_samples(),
        runtime_status=_runtime_status(),
        source_type="workspace",
        capture_mode="buffered",
        warnings=("workspace/demo data only",),
    )

    assert session is not None
    assert session.session_id.startswith("recorder-session-")
    assert session.source_type == "workspace"
    assert session.truth_label == "Simulated/Workspace Only"
    assert session.capture_source == "Current display"
    assert session.capture_mode == "buffered"
    assert session.start_timestamp == 10.0
    assert session.end_timestamp == 12.0
    assert session.duration_seconds == 2.0
    assert session.sample_count == 4
    assert session.event_count == 4
    assert session.axis_channels == ("Roll", "Pitch", "Yaw")
    assert session.button_channels == ()
    assert session.hat_channels == ()
    assert session.runtime_truth_snapshot["truth"] == "blocked_missing_device"
    assert session.runtime_truth_snapshot["output_verified"] is False
    assert session.runtime_truth_snapshot["full_live_runtime_ready"] is False
    assert "workspace/demo data only" in session.warnings
    assert [event.channel for event in session.timeline_events] == ["Yaw", "Pitch", "Yaw", "Roll"]
    assert session.timeline_events[0].description == "Yaw changed from 0.000 to 0.400 at +0.50s"


def test_post_rc_3b_empty_review_state_is_safe_and_clear_does_not_delete_files(tmp_path):
    from v3_app.recorder.recorder_controller import FlightRecorderController

    existing = tmp_path / "keep.txt"
    existing.write_text("do not delete", encoding="utf-8")
    controller = FlightRecorderController(settings=_settings(tmp_path))

    assert controller.review_current_session(runtime_status=_runtime_status()) is None
    assert controller.reviewed_session is None
    controller.clear_review_session()

    assert controller.reviewed_session is None
    assert existing.read_text(encoding="utf-8") == "do not delete"


def test_post_rc_3b_export_summary_json_and_samples_csv_are_truth_labeled_and_do_not_overwrite(tmp_path):
    from v3_app.recorder.session_review import (
        build_recorder_session_review,
        export_session_samples_csv,
        export_session_summary_json,
    )

    session = build_recorder_session_review(
        settings=_settings(tmp_path),
        telemetry_samples=_samples(),
        runtime_status=_runtime_status(),
        source_type="simulated",
        capture_mode="buffered",
    )
    assert session is not None
    first_target = tmp_path / f"{session.session_id}_summary.json"
    first_target.write_text("existing", encoding="utf-8")

    json_result = export_session_summary_json(session, tmp_path)
    csv_result = export_session_samples_csv(session, tmp_path)

    assert json_result.succeeded is True
    assert csv_result.succeeded is True
    assert json_result.path is not None
    assert csv_result.path is not None
    assert json_result.path.name.endswith("_summary_2.json")
    assert first_target.read_text(encoding="utf-8") == "existing"

    payload = json.loads(json_result.path.read_text(encoding="utf-8"))
    assert payload["truth"] == "Recorder review export; local deterministic summary; not real capture proof."
    assert payload["session"]["source_type"] == "simulated"
    assert payload["session"]["truth_label"] == "Simulated/Workspace Only"
    assert payload["session"]["runtime_truth_snapshot"]["truth"] == "blocked_missing_device"
    assert payload["session"]["runtime_truth_snapshot"]["output_verified"] is False
    assert payload["session"]["runtime_truth_snapshot"]["full_live_runtime_ready"] is False

    rows = list(csv.DictReader(csv_result.path.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 4
    assert rows[0]["source_type"] == "simulated"
    assert rows[0]["runtime_truth"] == "blocked_missing_device"
    assert rows[1]["Yaw"] == "0.400000"
    assert rows[3]["Roll"] == "0.200000"


def test_post_rc_3b_controller_builds_latest_review_from_simulated_export_metadata(tmp_path):
    from v3_app.recorder.capture_backend import SimulatedCaptureBackend
    from v3_app.recorder.compositor import SimulatedRecorderCompositor
    from v3_app.recorder.recorder_controller import FlightRecorderController

    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        capture_backend=SimulatedCaptureBackend(),
        compositor=SimulatedRecorderCompositor(),
    )
    for sample in _samples():
        controller.append_telemetry_sample(timestamp=sample.timestamp, axes=dict(sample.axes), source=sample.source)
    result = controller.save_last_clip(now=12.0, created_at="2026-05-08T15:00:00Z")

    session = controller.review_current_session(runtime_status=_runtime_status(), capture_mode="buffered")

    assert result.export_metadata is not None
    assert session is not None
    assert session.source_type == "simulated"
    assert session.capture_mode == "buffered"
    assert session.sample_count == 4
    assert session.event_count == 4
    assert "not real desktop capture" in " ".join(session.warnings)
    assert controller.export_review_summary_json().succeeded is True
    assert controller.export_review_samples_csv().succeeded is True


def test_post_rc_3b_flight_recorder_page_displays_review_and_export_truth(tmp_path):
    _app()
    from PySide6.QtWidgets import QPushButton, QTableWidget
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.recorder.capture_backend import SimulatedCaptureBackend
    from v3_app.recorder.compositor import SimulatedRecorderCompositor
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.services.app_state import AppState

    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        capture_backend=SimulatedCaptureBackend(),
        compositor=SimulatedRecorderCompositor(),
    )
    for sample in _samples():
        controller.append_telemetry_sample(timestamp=sample.timestamp, axes=dict(sample.axes), source=sample.source)
    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        recorder_controller=controller,
    )
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}

    assert "Recorder Review" in _label_text(page)
    assert "No reviewed recorder session yet." in _label_text(page)
    assert buttons["Export Summary JSON"].isEnabled() is False
    assert buttons["Export Samples CSV"].isEnabled() is False

    page.review_current_session()
    text = _label_text(page)
    timeline = page.findChild(QTableWidget, "recorderTimelineTable")

    assert "Latest Session Summary" in text
    assert "Simulated/Workspace Only" in text
    assert "Source type\nsimulated" in text
    assert "Duration\n2.00 s" in text
    assert "Samples\n4" in text
    assert "Events\n4" in text
    assert "Axis channels\nRoll, Pitch, Yaw" in text
    assert "Runtime truth\nblocked_missing_device" in text
    assert "Output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text
    assert timeline is not None
    assert timeline.rowCount() == 4
    assert buttons["Export Summary JSON"].isEnabled() is True
    assert buttons["Export Samples CSV"].isEnabled() is True

    page.export_review_summary_json()
    page.export_review_samples_csv()
    assert list(tmp_path.glob("*_summary.json"))
    assert list(tmp_path.glob("*_samples.csv"))

    page.clear_review_session()
    assert page.controller.reviewed_session is None
    assert "No reviewed recorder session yet." in _label_text(page)


def test_post_rc_3b_report_and_static_boundaries_preserve_runtime_truth():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-3b-flight-recorder-review-export-report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    for required in (
        "Session model",
        "Timeline/review behavior",
        "Export behavior",
        "Truthfulness boundaries",
        "No hardware polling",
        "No Bridge lifecycle management",
        "No output write verification",
    ):
        assert required in text

    source_paths = [
        *(PROJECT_ROOT / "v3_app" / "recorder").glob("*.py"),
        PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py",
    ]
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
    for forbidden_token in (
        "UpdateVJD",
        "SetAxis",
        "SetBtn",
        "AcquireVJD",
        "RegisterHotKey",
        "subprocess.Popen",
        "QProcess",
        "startDetached",
        "Start-Process",
        "DirectX hook",
        "Vulkan hook",
        "OpenGL hook",
        "openai",
        "anthropic",
        "auto_save",
    ):
        assert forbidden_token not in source_text
    assert "full live runtime ready: true" not in source_text.casefold()
