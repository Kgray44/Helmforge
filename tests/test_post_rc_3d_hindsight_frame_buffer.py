from __future__ import annotations

import json
import os
from dataclasses import dataclass
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


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


@dataclass
class _FrameBufferTestBackend:
    calls: int = 0
    fail_after: int | None = None

    def capabilities(self):
        from v3_app.recorder.capture_backend import CaptureBackendCapabilities

        return CaptureBackendCapabilities(
            backend_name="deterministic_buffer_test",
            backend_kind="test",
            dependency_available=True,
            screen_capture_available=False,
            frame_capture_available=False,
            cursor_capture_available=False,
            display_enumeration_available=True,
            real_capture_supported=False,
            simulated_capture_supported=True,
            requires_admin=False,
            uses_game_injection=False,
            uses_graphics_hooking=False,
            video_encoding_available=False,
            simulated_artifact_available=False,
            one_frame_capture_available=True,
            one_frame_real_capture_supported=False,
            frame_buffer_capture_available=True,
            warnings=("deterministic simulated frame-buffer proof only",),
        )

    def refresh_status(self):
        from v3_app.recorder.capture_backend import CaptureBackendStatus

        return CaptureBackendStatus(
            capabilities=self.capabilities(),
            status="test_frame_buffer_available",
            message="Deterministic frame-buffer capture metadata is available for tests only.",
        )

    def display_sources(self):
        from v3_app.recorder.capture_backend import CaptureDisplaySource

        return (
            CaptureDisplaySource(
                display_id="test-display",
                display_label="Test Display",
                geometry=(0, 0, 800, 450),
                is_primary=True,
                capture_source="selected display",
            ),
        )

    def capture_frame(self, *, source=None):
        from v3_app.recorder.capture_backend import CaptureFrameResult

        selected = source or self.display_sources()[0]
        return CaptureFrameResult(True, "Compatibility frame metadata returned.", selected, frame=None)

    def capture_one_frame(self, *, source=None, artifact_folder=None, now=None):
        from v3_app.recorder.capture_backend import FrameCaptureResult

        self.calls += 1
        selected = source or self.display_sources()[0]
        timestamp = float(now if now is not None else self.calls)
        if self.fail_after is not None and self.calls > self.fail_after:
            return FrameCaptureResult(
                succeeded=False,
                message="Deterministic frame failure.",
                backend_name="deterministic_buffer_test",
                backend_kind="test",
                source=selected,
                timestamp=timestamp,
                pixel_format="unavailable",
                warnings=("simulated backend failure",),
                errors=("deterministic failure",),
                truth_label="Frame buffer capture unavailable",
                real_capture=False,
                simulated_capture=True,
            )
        return FrameCaptureResult(
            succeeded=True,
            message="Deterministic frame-buffer metadata returned.",
            backend_name="deterministic_buffer_test",
            backend_kind="test",
            source=selected,
            timestamp=timestamp,
            width=800,
            height=450,
            pixel_format="deterministic-rgba",
            artifact_path=None,
            warnings=("simulated frame metadata only", "not real desktop capture"),
            errors=(),
            truth_label="Simulated frame-buffer proof only",
            real_capture=False,
            simulated_capture=True,
        )

    def create_simulated_artifact(self, *, settings, telemetry_samples, now, created_at=None):
        from v3_app.recorder.capture_backend import CaptureBackendResult

        return CaptureBackendResult(False, "This backend writes only frame-buffer metadata through the controller.")


def test_post_rc_3d_ring_buffer_retains_only_max_duration_and_count():
    from v3_app.recorder.hindsight_buffer import RecorderFrameHindsightBuffer, RecorderFrameReference

    buffer = RecorderFrameHindsightBuffer(max_duration_seconds=2.0, target_fps=30, max_frame_count=3)
    source = {"display_id": "display-1", "display_label": "Primary"}
    for timestamp in (1.0, 2.0, 3.0, 4.0):
        accepted = buffer.add_frame(
            RecorderFrameReference(
                timestamp=timestamp,
                backend_name="test",
                backend_kind="test",
                display_id=source["display_id"],
                display_label=source["display_label"],
                capture_source="selected display",
                width=640,
                height=360,
                pixel_format="rgba",
                real_capture=False,
                simulated_capture=True,
            )
        )
        assert accepted is True

    status = buffer.status()
    assert [frame.timestamp for frame in buffer.frames()] == [2.0, 3.0, 4.0]
    assert status.stored_frame_count == 3
    assert status.oldest_timestamp == 2.0
    assert status.newest_timestamp == 4.0
    assert status.buffer_duration_seconds == 2.0
    assert status.max_frame_count == 3
    assert status.target_fps == 30
    assert status.health == "ready"


def test_post_rc_3d_timestamps_are_monotonic_and_dropped_tracking_works():
    from v3_app.recorder.hindsight_buffer import RecorderFrameHindsightBuffer, RecorderFrameReference

    buffer = RecorderFrameHindsightBuffer(max_duration_seconds=10.0, target_fps=30, max_frame_count=10)
    first = RecorderFrameReference(
        timestamp=10.0,
        backend_name="test",
        backend_kind="test",
        display_id="display-1",
        display_label="Primary",
        capture_source="selected display",
        width=640,
        height=360,
        pixel_format="rgba",
        real_capture=False,
        simulated_capture=True,
    )
    older = RecorderFrameReference(
        timestamp=9.5,
        backend_name="test",
        backend_kind="test",
        display_id="display-1",
        display_label="Primary",
        capture_source="selected display",
        width=640,
        height=360,
        pixel_format="rgba",
        real_capture=False,
        simulated_capture=True,
    )

    assert buffer.add_frame(first) is True
    assert buffer.add_frame(older) is False

    status = buffer.status()
    assert [frame.timestamp for frame in buffer.frames()] == [10.0]
    assert status.dropped_frame_count == 1
    assert "non-monotonic" in " ".join(status.warnings)


def test_post_rc_3d_buffer_does_not_start_automatically_and_unavailable_backend_reports_unavailable(tmp_path):
    from v3_app.recorder.recorder_controller import FlightRecorderController

    controller = FlightRecorderController(settings=_settings(tmp_path))

    assert controller.frame_buffer_status().active is False
    assert controller.frame_buffer_status().stored_frame_count == 0
    assert controller.frame_buffer_availability().available is False

    start = controller.start_frame_buffer(now=1.0)

    assert start.succeeded is False
    assert "unavailable" in start.message.casefold()
    assert controller.frame_buffer_status().active is False
    assert not any(tmp_path.iterdir())


def test_post_rc_3d_explicit_start_stop_and_capture_state_work_with_fake_backend(tmp_path):
    from v3_app.recorder.recorder_controller import FlightRecorderController

    backend = _FrameBufferTestBackend()
    controller = FlightRecorderController(settings=_settings(tmp_path), capture_backend=backend)

    assert backend.calls == 0
    start = controller.start_frame_buffer(now=10.0)
    assert start.succeeded is True
    assert backend.calls == 0
    assert controller.frame_buffer_status().active is True

    first = controller.capture_frame_buffer_sample(now=10.0)
    second = controller.capture_frame_buffer_sample(now=10.5)
    stop = controller.stop_frame_buffer()

    assert first.succeeded is True
    assert second.succeeded is True
    assert backend.calls == 2
    assert stop.succeeded is True
    assert controller.frame_buffer_status().active is False
    assert controller.frame_buffer_status().stored_frame_count == 2
    assert controller.frame_buffer_status().frame_width == 800
    assert controller.frame_buffer_status().frame_height == 450
    assert controller.frame_buffer_status().pixel_format == "deterministic-rgba"


def test_post_rc_3d_repeated_backend_failures_stop_buffer_safely(tmp_path):
    from v3_app.recorder.recorder_controller import FlightRecorderController

    backend = _FrameBufferTestBackend(fail_after=0)
    controller = FlightRecorderController(settings=_settings(tmp_path), capture_backend=backend)
    assert controller.start_frame_buffer(now=1.0).succeeded is True

    for timestamp in (1.0, 1.1, 1.2):
        result = controller.capture_frame_buffer_sample(now=timestamp)
        assert result.succeeded is False

    status = controller.frame_buffer_status()
    assert status.active is False
    assert status.dropped_frame_count == 3
    assert status.health == "error"
    assert "stopped after repeated capture failures" in " ".join(status.errors)


def test_post_rc_3d_save_last_clip_creates_not_encoded_intermediate_artifact(tmp_path):
    from v3_app.recorder.recorder_controller import FlightRecorderController

    controller = FlightRecorderController(settings=_settings(tmp_path), capture_backend=_FrameBufferTestBackend())
    controller.append_telemetry_sample(timestamp=9.0, axes={"Yaw": -0.2}, source="Final output")
    controller.append_telemetry_sample(timestamp=10.1, axes={"Yaw": 0.3}, source="Final output")
    controller.append_telemetry_sample(timestamp=10.4, axes={"Pitch": -0.5}, source="Final output")
    controller.append_telemetry_sample(timestamp=11.0, axes={"Roll": 0.9}, source="Final output")
    assert controller.start_frame_buffer(now=10.0).succeeded is True
    assert controller.capture_frame_buffer_sample(now=10.0).succeeded is True
    assert controller.capture_frame_buffer_sample(now=10.5).succeeded is True

    result = controller.save_last_clip(
        now=11.0,
        created_at="2026-05-08T22:00:00Z",
        runtime_status=_runtime_status(),
    )

    assert result.succeeded is True
    assert result.artifact is not None
    assert result.artifact.has_video is False
    assert result.artifact.status == "intermediate_frame_buffer"
    assert result.artifact.path.suffix == ".json"
    assert "not encoded" in result.message.casefold()
    assert "playable" not in result.message.casefold().replace("not playable", "")

    payload = json.loads(result.artifact.path.read_text(encoding="utf-8"))
    assert payload["truth"] == "Intermediate frame buffer artifact; not_encoded; not_playable; not a video recording."
    assert payload["artifact"]["has_video"] is False
    assert payload["frame_buffer"]["stored_frame_count"] == 2
    assert payload["frame_buffer"]["not_encoded"] is True
    assert payload["frame_buffer"]["not_playable"] is True
    assert payload["telemetry"]["sample_count"] == 2
    assert [sample["timestamp"] for sample in payload["telemetry"]["samples"]] == [10.1, 10.4]
    assert payload["runtime_truth"]["truth"] == "blocked_missing_device"
    assert payload["runtime_truth"]["output_verified"] is False
    assert payload["runtime_truth"]["full_live_runtime_ready"] is False


def test_post_rc_3d_telemetry_alignment_selects_samples_in_frame_interval(tmp_path):
    from v3_app.recorder.recorder_controller import FlightRecorderController

    controller = FlightRecorderController(settings=_settings(tmp_path), capture_backend=_FrameBufferTestBackend())
    for timestamp, axes in (
        (1.0, {"Yaw": -1.0}),
        (2.0, {"Yaw": -0.5}),
        (2.5, {"Yaw": 0.0}),
        (3.0, {"Yaw": 0.5}),
        (4.0, {"Yaw": 1.0}),
    ):
        controller.append_telemetry_sample(timestamp=timestamp, axes=axes, source="Final output")
    assert controller.start_frame_buffer(now=2.0).succeeded is True
    assert controller.capture_frame_buffer_sample(now=2.0).succeeded is True
    assert controller.capture_frame_buffer_sample(now=3.0).succeeded is True

    samples = controller.aligned_telemetry_for_frame_buffer()

    assert [sample.timestamp for sample in samples] == [2.0, 2.5, 3.0]


def test_post_rc_3d_flight_recorder_page_exposes_buffer_status_and_buttons(tmp_path):
    _app()
    from PySide6.QtWidgets import QPushButton
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.services.app_state import AppState

    controller = FlightRecorderController(settings=_settings(tmp_path), capture_backend=_FrameBufferTestBackend())
    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        recorder_controller=controller,
    )
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}

    assert "Frame Buffer" in _label_text(page)
    assert "Buffer state\ninactive" in _label_text(page)
    assert "Stored frames\n0" in _label_text(page)
    assert buttons["Start Buffer"].isEnabled() is True
    assert buttons["Stop Buffer"].isEnabled() is False
    assert buttons["Save Last Clip"].isEnabled() is False

    page.start_frame_buffer()
    controller.capture_frame_buffer_sample(now=20.0)
    page.refresh_frame_buffer_status()
    text = _label_text(page)

    assert "Buffer state\nactive" in text
    assert "Stored frames\n1" in text
    assert "Frame budget" in text
    assert "Not encoded / not playable" in text
    assert buttons["Stop Buffer"].isEnabled() is True
    assert buttons["Save Last Clip"].isEnabled() is True


def test_post_rc_3d_ui_does_not_claim_video_recording_encoding_or_preview(tmp_path):
    _app()
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.services.app_state import AppState

    controller = FlightRecorderController(settings=_settings(tmp_path), capture_backend=_FrameBufferTestBackend())
    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        recorder_controller=controller,
    )
    page.start_frame_buffer()
    controller.capture_frame_buffer_sample(now=30.0)
    page.refresh_frame_buffer_status()
    page.save_last_clip()
    text = _label_text(page)

    for forbidden in (
        "Recording ready",
        "Recording complete",
        "Video exported",
        "Encoding complete",
        "Playable video",
        "Hotkey armed",
        "Full Live Runtime Ready\ntrue",
    ):
        assert forbidden not in text
    assert "not encoded" in text.casefold()
    assert "not playable" in text.casefold()


def test_post_rc_3d_report_and_static_boundaries_preserve_runtime_authority():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-3d-hindsight-frame-buffer-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    for required in (
        "Buffer model",
        "Capture pipeline behavior",
        "Start/stop behavior",
        "Telemetry sync",
        "Intermediate artifact format",
        "UI changes",
        "Preserved 3B/3C behavior",
        "What remains for 3E encoding",
        "Runtime truth preservation",
    ):
        assert required in report_text

    source_paths = [
        *(PROJECT_ROOT / "v3_app" / "recorder").glob("*.py"),
        PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py",
    ]
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
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
    assert "full live runtime ready: true" not in source_text.casefold()
