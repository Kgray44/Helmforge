from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _status():
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


def _create_simulated_export(tmp_path, *, timestamp: float, created_at: str):
    from v3_app.recorder.capture_backend import SimulatedCaptureBackend
    from v3_app.recorder.compositor import SimulatedRecorderCompositor
    from v3_app.recorder.recorder_controller import FlightRecorderController

    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        capture_backend=SimulatedCaptureBackend(),
        compositor=SimulatedRecorderCompositor(),
    )
    controller.append_telemetry_sample(timestamp=timestamp - 1.0, axes={"Yaw": 0.2}, source="Final output")
    controller.append_telemetry_sample(timestamp=timestamp, axes={"Yaw": 0.7, "Roll": -0.1}, source="Final output")
    result = controller.save_last_clip(now=timestamp, created_at=created_at)
    assert result.export_metadata is not None
    return result.export_metadata


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def _button_text(widget) -> str:
    from PySide6.QtWidgets import QPushButton

    return "\n".join(button.text() for button in widget.findChildren(QPushButton))


def test_phase13d_clip_library_indexes_simulated_exports_and_ignores_unknown_files(tmp_path):
    from v3_app.recorder.clip_library import ClipLibrary

    first = _create_simulated_export(tmp_path, timestamp=10.0, created_at="2026-05-07T12:00:00Z")
    second = _create_simulated_export(tmp_path, timestamp=20.0, created_at="2026-05-07T12:05:00Z")
    (tmp_path / "random.txt").write_text("ignore me", encoding="utf-8")
    (tmp_path / "broken.mp4").write_text("not indexed as a simulated artifact", encoding="utf-8")
    (tmp_path / "simulated_export_broken").mkdir()
    (tmp_path / "simulated_export_broken" / "manifest.json").write_text("{not json", encoding="utf-8")

    rows = ClipLibrary(tmp_path).scan()

    assert [row.export_metadata.created_at for row in rows] == [second.created_at, first.created_at]
    assert len(rows) == 2
    for row in rows:
        assert row.export_metadata is not None
        assert row.artifact_kind == "simulated_export"
        assert row.display_name.startswith("Simulated export")
        assert "No video" in row.clip
        assert row.opened == "Metadata only"
        assert row.has_video is False
        assert row.is_simulated is True


def test_phase13d_clip_library_missing_destination_is_empty_and_safe(tmp_path):
    from v3_app.recorder.clip_library import ClipLibrary

    missing = tmp_path / "does-not-exist"
    library = ClipLibrary(missing)

    assert library.scan() == ()
    assert library.empty_state_title == "No recorder artifacts yet."
    assert "Simulated exports will appear here as metadata-only artifacts." in library.empty_state_detail


def test_phase13d_export_metadata_tolerates_missing_optional_fields(tmp_path):
    from v3_app.recorder.recorder_artifacts import RecorderExportMetadata

    metadata = RecorderExportMetadata.from_dict(
        {
            "export_id": "simulated-export-minimal",
            "path": str(tmp_path / "simulated_export_minimal"),
            "manifest_path": str(tmp_path / "simulated_export_minimal" / "manifest.json"),
            "created_at": "2026-05-07T12:00:00Z",
        }
    )

    assert metadata.clip_id == "simulated-export-minimal"
    assert metadata.artifact_kind == "simulated_export"
    assert metadata.display_name == "Simulated export"
    assert metadata.has_video is False
    assert metadata.has_real_capture is False
    assert metadata.opened is False
    assert RecorderExportMetadata.from_json(metadata.to_json()) == metadata


def test_phase13d_flight_recorder_library_preview_is_metadata_only(tmp_path):
    _app()
    from PySide6.QtWidgets import QTableWidget, QPushButton, QSlider
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.services.app_state import AppState

    export = _create_simulated_export(tmp_path, timestamp=10.0, created_at="2026-05-07T12:00:00Z")
    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_status(),
        settings=_settings(tmp_path),
    )
    table = page.findChild(QTableWidget, "recordingLibraryTable")
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}
    timeline = page.findChild(QSlider, "clipPreviewTimeline")

    assert table is not None
    assert [table.horizontalHeaderItem(index).text() for index in range(table.columnCount())] == [
        "Artifact or Clip",
        "Created/Recorded",
        "Duration",
        "Opened",
    ]
    assert table.rowCount() == 1

    page.show_library_item_preview(0)
    text = _label_text(page)

    assert "Simulated export" in text
    assert "Metadata-only preview" in text
    assert "No video preview available" in text
    assert "No desktop frames were captured." in text
    assert "No encoding was performed." in text
    assert "Telemetry samples: 2" in text
    assert "Overlay source: Final output" in text
    assert "Included axes:" in text
    assert f"Artifact path: {export.path}" in text
    assert f"Manifest path: {export.manifest_path}" in text
    assert "Warnings:" in text
    assert buttons["Play"].isEnabled() is False
    assert timeline is not None
    assert timeline.isEnabled() is False


def test_phase13d_actions_and_status_copy_remain_truthful_with_missing_backend(tmp_path):
    _app()
    from PySide6.QtWidgets import QPushButton
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.services.app_state import AppState

    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_status(),
        settings=_settings(tmp_path),
    )
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}
    assert buttons["Record Now"].isEnabled() is False
    assert buttons["Save Last Clip"].isEnabled() is False

    page.record_now()
    page.save_last_clip()
    text = _label_text(page)

    assert "Capture backend missing" in text
    assert "Recording unavailable; capture backend missing." in text
    assert "Video hindsight buffering unavailable" in text
    assert "Save Last Clip cannot save real video until capture buffering exists." in text
    assert "Hotkey not registered" in text
    assert "Output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text
    forbidden_claims = (
        "Hotkey armed",
        "Capture ready",
        "Encoding complete",
        "Video exported",
        "Real clip saved",
        "Clip saved",
        "Recording complete",
    )
    for forbidden in forbidden_claims:
        assert forbidden not in text


def test_phase13d_help_docs_and_report_freeze_phase13_boundaries():
    help_docs = (PROJECT_ROOT / "v3_app" / "services" / "help_docs.py").read_text(encoding="utf-8")
    report = (
        PROJECT_ROOT / "docs" / "HelmForge" / "phase-13d-flight-recorder-library-preview-boundary-freeze-report.md"
    ).read_text(encoding="utf-8")

    assert "simulated exports are not real recordings" in help_docs
    assert "no screen capture or video encoding is implemented" in help_docs
    assert "telemetry hindsight is separate from video hindsight" in help_docs
    assert "Ctrl+Shift+F10 is configured as recorder hotkey text but not registered" in help_docs
    assert "Phase 14 is real HOTAS input, not recorder capture" in help_docs
    assert "Phase 13 is now complete." in report
    assert "Next prompt-book phase is Phase 14: Real HOTAS Input Integration." in report
    assert "Phase 14 must preserve simulation mode." in report
    assert "Phase 14 must not add vJoy writes/output verification" in report


def test_phase13d_static_boundaries_reject_real_capture_encoding_hotkeys_and_runtime_authority(tmp_path):
    sources = []
    for root in (PROJECT_ROOT / "v3_app" / "recorder", PROJECT_ROOT / "v3_app" / "pages"):
        sources.extend(root.glob("*.py"))
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in sources)

    for forbidden_token in (
        "import mss",
        "import dxcam",
        "pyautogui.screenshot",
        "ImageGrab.grab",
        "cv2.VideoWriter",
        "ffmpeg",
        "moviepy",
        "RegisterHotKey",
        "SetWindowLong",
        "UpdateVJD",
        "SetAxis",
        "SetBtn",
        "AcquireVJD",
        "subprocess.Popen",
        "QProcess",
        "startDetached",
        "Start-Process",
        "DirectX hook",
        "Vulkan hook",
        "OpenGL hook",
        "screen capture API",
        "pystray",
        "openai",
        "anthropic",
        "auto_save",
    ):
        assert forbidden_token not in source_text

    _app()
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.services.app_state import AppState

    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_status(),
        settings=_settings(tmp_path),
    )
    labels = _label_text(page)
    buttons = _button_text(page)
    assert "Hotkey not registered" in labels
    assert "Capture ready" not in labels
    assert "Hotkey armed" not in labels
    assert "Encoding" not in labels
    assert "Video exported" not in labels
    assert "StartBridge" not in buttons
    assert "StopBridge" not in buttons
    assert "RestartBridge" not in buttons
    assert "VerifyOutput" not in buttons
