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


def _settings(tmp_path):
    from v3_app.recorder.recorder_settings import FlightRecorderSettings

    return FlightRecorderSettings.from_dict(
        {**FlightRecorderSettings.defaults().to_dict(), "destination_folder": str(tmp_path)}
    )


def test_phase13c_missing_and_simulated_compositor_capabilities_are_truthful():
    from v3_app.recorder.compositor import MissingRecorderCompositor, SimulatedRecorderCompositor

    missing = MissingRecorderCompositor().refresh_status()
    assert missing.capabilities.real_video_compositing_available is False
    assert missing.capabilities.simulated_export_available is False
    assert missing.capabilities.overlay_trace_rendering_available is False
    assert "Compositor unavailable" in missing.message

    simulated = SimulatedRecorderCompositor().refresh_status()
    assert simulated.capabilities.real_video_compositing_available is False
    assert simulated.capabilities.simulated_export_available is True
    assert simulated.capabilities.overlay_trace_rendering_available is True
    assert simulated.capabilities.supports_preview_metadata is True
    assert "no real video compositing" in " ".join(simulated.capabilities.warnings).lower()


def test_phase13c_simulated_export_bundle_contains_manifest_trace_and_summary(tmp_path):
    from v3_app.overlay.axis_colors import DEFAULT_AXIS_COLORS
    from v3_app.recorder.compositor import SimulatedRecorderCompositor
    from v3_app.recorder.hindsight_buffer import RecorderTelemetryHindsightBuffer

    settings = _settings(tmp_path)
    buffer = RecorderTelemetryHindsightBuffer(history_seconds=settings.history_seconds)
    buffer.append(timestamp=1.0, axes={"Roll": 0.5, "Yaw": -0.25}, source="Final output")
    buffer.append(timestamp=2.0, axes={"Roll": 0.75, "Yaw": 0.25}, source="Final output")

    result = SimulatedRecorderCompositor().create_simulated_export(
        settings=settings,
        telemetry_samples=buffer.samples(),
        capture_backend_name="simulated_capture",
        now=2.0,
        created_at="2026-05-07T12:00:00Z",
    )

    assert result.succeeded is True
    assert result.metadata is not None
    assert result.metadata.artifact_kind == "simulated_export"
    assert result.metadata.is_simulated is True
    assert result.metadata.has_video is False
    assert result.metadata.has_real_capture is False
    assert result.metadata.has_overlay_trace is True
    assert result.metadata.telemetry_sample_count == 2
    assert result.metadata.path.is_dir()
    assert result.metadata.manifest_path.exists()
    assert (result.metadata.path / "overlay_trace.json").exists()
    assert (result.metadata.path / "summary.md").exists()
    assert (result.metadata.path / "preview_metadata.json").exists()
    assert not list(result.metadata.path.glob("*.mp4"))
    assert not list(result.metadata.path.glob("*.webm"))

    manifest = json.loads(result.metadata.manifest_path.read_text(encoding="utf-8"))
    assert manifest["export"]["is_simulated"] is True
    assert manifest["export"]["has_video"] is False
    assert manifest["export"]["has_real_capture"] is False
    assert "not real desktop capture" in manifest["truth"].lower()
    assert "no screen frames captured" in manifest["truth"].lower()
    assert "no video encoding performed" in manifest["truth"].lower()
    assert "output verified: false" in manifest["runtime_truth"].lower()
    assert "full live runtime ready: false" in manifest["runtime_truth"].lower()

    trace_payload = json.loads((result.metadata.path / "overlay_trace.json").read_text(encoding="utf-8"))
    colors = {series["axis"]: series["color"] for series in trace_payload["series"]}
    assert colors == DEFAULT_AXIS_COLORS
    assert trace_payload["sample_count"] == 2


def test_phase13c_export_metadata_round_trips_to_dict_and_json(tmp_path):
    from v3_app.recorder.recorder_artifacts import RecorderExportMetadata

    metadata = RecorderExportMetadata(
        export_id="simulated-export-1",
        clip_id="simulated-export-1",
        created_at="2026-05-07T12:00:00Z",
        artifact_kind="simulated_export",
        path=tmp_path / "simulated_export",
        manifest_path=tmp_path / "simulated_export" / "manifest.json",
        duration_seconds=20.0,
        frame_rate=30,
        overlay_source="Final output",
        capture_source="Current display",
        display_label="Current display",
        telemetry_sample_count=3,
        included_axes=("Roll", "Pitch"),
        is_simulated=True,
        has_video=False,
        has_real_capture=False,
        has_overlay_trace=True,
        compositor_backend="simulated_compositor",
        capture_backend="simulated_capture",
        warnings=("not real desktop capture",),
    )

    assert RecorderExportMetadata.from_dict(metadata.to_dict()) == metadata
    assert RecorderExportMetadata.from_json(metadata.to_json()) == metadata


def test_phase13c_controller_missing_backends_write_no_files_and_do_not_claim_clip_saved(tmp_path):
    from v3_app.recorder.capture_backend import MissingCaptureBackend
    from v3_app.recorder.compositor import MissingRecorderCompositor
    from v3_app.recorder.recorder_controller import FlightRecorderController

    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        capture_backend=MissingCaptureBackend(),
        compositor=MissingRecorderCompositor(),
    )

    record = controller.record_now(now=100.0)
    save = controller.save_last_clip(now=101.0)

    assert record.succeeded is False
    assert save.succeeded is False
    assert record.artifact is None
    assert save.artifact is None
    assert "Recording unavailable" in record.message
    assert "Hindsight video buffer unavailable" in save.message
    assert "Clip saved" not in f"{record.message} {save.message}"
    assert not any(tmp_path.iterdir())


def test_phase13c_controller_simulated_export_uses_telemetry_hindsight(tmp_path):
    from v3_app.recorder.capture_backend import SimulatedCaptureBackend
    from v3_app.recorder.compositor import SimulatedRecorderCompositor
    from v3_app.recorder.recorder_controller import FlightRecorderController

    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        capture_backend=SimulatedCaptureBackend(),
        compositor=SimulatedRecorderCompositor(),
    )
    controller.append_telemetry_sample(timestamp=8.0, axes={"Yaw": 0.1}, source="Final output")
    controller.append_telemetry_sample(timestamp=10.0, axes={"Yaw": 0.7}, source="Final output")

    result = controller.save_last_clip(now=10.0, created_at="2026-05-07T12:00:00Z")

    assert result.succeeded is True
    assert result.artifact is not None
    assert result.artifact.status == "simulated_export"
    assert result.artifact.has_video is False
    assert result.export_metadata is not None
    assert result.export_metadata.telemetry_sample_count == 2
    assert result.export_metadata.has_overlay_trace is True
    assert "Simulated export created" in result.message
    assert "Video exported" not in result.message
    assert "Clip saved" not in result.message


def test_phase13c_flight_recorder_page_labels_simulated_exports_as_metadata_only(tmp_path):
    _app()
    from PySide6.QtWidgets import QPushButton
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

    assert "Simulated export" in text
    assert "No video preview available" in text
    assert "Telemetry samples: 1" in text
    assert "Overlay source: Final output" in text
    assert "Included axes:" in text
    assert "Artifact path:" in text
    assert "simulated export bundle available" in text
    assert buttons["Play"].isEnabled() is False
    assert "Recording\n" not in text
    assert "Encoding" not in text
    assert "Video exported" not in text
    assert "Hotkey armed" not in text
    assert "Clip saved" not in text


def test_phase13c_static_boundaries_reject_real_capture_encoding_and_runtime_authority(tmp_path):
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
