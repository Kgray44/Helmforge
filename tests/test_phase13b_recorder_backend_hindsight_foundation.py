from __future__ import annotations

import json
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


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def _button_text(widget) -> str:
    from PySide6.QtWidgets import QPushButton

    return "\n".join(button.text() for button in widget.findChildren(QPushButton))


def test_phase13b_missing_capture_backend_is_truthful_and_does_not_write_files(tmp_path):
    from v3_app.recorder.capture_backend import MissingCaptureBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.recorder.recorder_settings import FlightRecorderSettings

    settings = FlightRecorderSettings.from_dict(
        {**FlightRecorderSettings.defaults().to_dict(), "destination_folder": str(tmp_path)}
    )
    controller = FlightRecorderController(settings=settings, capture_backend=MissingCaptureBackend())

    status = controller.refresh_status()
    assert status.capabilities.desktop_capture_available is False
    assert status.capabilities.video_encoding_available is False
    assert "Capture backend missing" in status.message

    record = controller.record_now(now=100.0)
    save = controller.save_last_clip(now=101.0)

    assert record.succeeded is False
    assert save.succeeded is False
    assert record.artifact is None
    assert save.artifact is None
    assert "Recording unavailable" in record.message
    assert "Hindsight video buffer unavailable" in save.message
    assert not any(tmp_path.iterdir())


def test_phase13b_simulated_backend_creates_labeled_non_video_manifest(tmp_path):
    from v3_app.recorder.capture_backend import SimulatedCaptureBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.recorder.recorder_settings import FlightRecorderSettings

    settings = FlightRecorderSettings.from_dict(
        {**FlightRecorderSettings.defaults().to_dict(), "destination_folder": str(tmp_path)}
    )
    controller = FlightRecorderController(settings=settings, capture_backend=SimulatedCaptureBackend())
    controller.append_telemetry_sample(timestamp=98.5, axes={"Yaw": 0.25}, source="Final output")
    controller.append_telemetry_sample(timestamp=100.0, axes={"Yaw": 0.5, "Pitch": -0.25}, source="Final output")

    result = controller.save_last_clip(now=100.0, created_at="2026-05-07T12:00:00Z")

    assert result.succeeded is True
    assert result.artifact is not None
    assert result.artifact.is_simulated is True
    assert result.artifact.has_video is False
    assert result.artifact.has_overlay is True
    assert result.artifact.path.suffix == ".json"
    assert "simulated" in result.artifact.filename
    assert "Simulated artifact saved" in result.message
    assert "Clip saved" not in result.message

    manifest = json.loads(result.artifact.path.read_text(encoding="utf-8"))
    assert manifest["artifact"]["is_simulated"] is True
    assert manifest["artifact"]["has_video"] is False
    assert "simulated recorder artifact" in manifest["truth"].lower()
    assert "not real desktop capture" in manifest["truth"].lower()
    assert "no video frames captured" in manifest["truth"].lower()
    assert "no encoding performed" in manifest["truth"].lower()
    assert manifest["telemetry"]["sample_count"] == 2


def test_phase13b_artifact_model_round_trips_to_dict_and_json(tmp_path):
    from v3_app.recorder.recorder_artifacts import RecorderArtifact

    artifact = RecorderArtifact(
        clip_id="simulated-1",
        filename="simulated_recorder_artifact_1.json",
        path=tmp_path / "simulated_recorder_artifact_1.json",
        created_at="2026-05-07T12:00:00Z",
        duration_seconds=20.0,
        frame_rate=30,
        overlay_source="Final output",
        capture_source="Current display",
        display_label="Current display",
        is_simulated=True,
        has_video=False,
        has_overlay=True,
        backend_name="simulated_capture",
        status="simulated_artifact",
        notes=("simulated recorder artifact",),
        warnings=("not real desktop capture",),
    )

    payload = artifact.to_dict()
    assert RecorderArtifact.from_dict(payload) == artifact
    assert RecorderArtifact.from_json(artifact.to_json()) == artifact


def test_phase13b_telemetry_hindsight_buffer_returns_previous_interval_and_trims():
    from v3_app.recorder.hindsight_buffer import RecorderTelemetryHindsightBuffer

    buffer = RecorderTelemetryHindsightBuffer(history_seconds=3.0)
    buffer.append(timestamp=1.0, axes={"Yaw": -2.0}, source="Final output")
    buffer.append(timestamp=3.0, axes={"Yaw": 0.25}, source="Final output")
    buffer.append(timestamp=5.0, axes={"Yaw": 0.75}, source="Final output")

    samples = buffer.samples()
    assert [sample.timestamp for sample in samples] == [3.0, 5.0]
    assert samples[-1].axes["Yaw"] == 0.75
    assert samples[0].axes["Yaw"] == 0.25

    previous = buffer.previous_seconds(seconds=2.5, now=5.0)
    assert [sample.timestamp for sample in previous] == [3.0, 5.0]
    assert buffer.status_label == "Telemetry hindsight buffer available"
    assert buffer.video_hindsight_status == "Video hindsight buffering unavailable"


def test_phase13b_flight_recorder_page_uses_controller_missing_backend_truthfully(tmp_path):
    _app()
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.recorder.capture_backend import MissingCaptureBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.recorder.recorder_settings import FlightRecorderSettings
    from v3_app.services.app_state import AppState

    settings = FlightRecorderSettings.from_dict(
        {**FlightRecorderSettings.defaults().to_dict(), "destination_folder": str(tmp_path)}
    )
    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_status(),
        recorder_controller=FlightRecorderController(settings=settings, capture_backend=MissingCaptureBackend()),
    )

    page.record_now()
    page.save_last_clip()
    text = _label_text(page)

    assert "Capture backend missing" in text
    assert "Recording unavailable; capture backend missing." in text
    assert "Hindsight video buffer unavailable; Save Last Clip cannot save real video until capture buffering exists." in text
    assert "Telemetry hindsight buffer available." in text
    assert "Video hindsight buffering is not implemented yet." in text
    assert "Runtime truth\nblocked_missing_device" in text
    assert "Output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text
    assert "Clip saved" not in text
    assert "recording started" not in text.lower()


def test_phase13b_flight_recorder_page_labels_simulated_artifacts_and_metadata_preview(tmp_path):
    _app()
    from PySide6.QtWidgets import QPushButton
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.recorder.capture_backend import SimulatedCaptureBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.recorder.recorder_settings import FlightRecorderSettings
    from v3_app.services.app_state import AppState

    settings = FlightRecorderSettings.from_dict(
        {**FlightRecorderSettings.defaults().to_dict(), "destination_folder": str(tmp_path)}
    )
    controller = FlightRecorderController(settings=settings, capture_backend=SimulatedCaptureBackend())
    controller.append_telemetry_sample(timestamp=10.0, axes={"Roll": 0.4}, source="Final output")
    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_status(),
        recorder_controller=controller,
    )

    page.save_last_clip()
    text = _label_text(page)
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}

    assert "Simulated backend" in text
    assert "Simulated artifact saved" in text
    assert "Simulated artifact" in text
    assert "No video preview available" in text
    assert "Telemetry samples: 1" in text
    assert "real desktop capture" not in text.lower()
    assert buttons["Play"].isEnabled() is False
    assert "Clip saved" not in text


def test_phase13b_static_boundaries_reject_real_capture_and_runtime_authority(tmp_path):
    from v3_app.recorder.capture_backend import SimulatedCaptureBackend

    assert SimulatedCaptureBackend().capabilities().simulated_artifact_available is True

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
    )
    labels = _label_text(page)
    buttons = _button_text(page)
    assert "Hotkey not registered" in labels
    assert "Capture ready" not in labels
    assert "Hotkey armed" not in labels
    assert "Encoding" not in labels
    assert "Recording\n" not in labels
    assert "StartBridge" not in buttons
    assert "StopBridge" not in buttons
    assert "RestartBridge" not in buttons
    assert "VerifyOutput" not in buttons
