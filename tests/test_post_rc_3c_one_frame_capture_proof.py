from __future__ import annotations

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
class _DeterministicProofBackend:
    calls: int = 0

    def capabilities(self):
        from v3_app.recorder.capture_backend import CaptureBackendCapabilities

        return CaptureBackendCapabilities(
            backend_name="deterministic_test_frame",
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
            warnings=("deterministic simulated still-frame proof only",),
        )

    def refresh_status(self):
        from v3_app.recorder.capture_backend import CaptureBackendStatus

        return CaptureBackendStatus(
            capabilities=self.capabilities(),
            status="test_one_frame_available",
            message="Deterministic one-frame proof metadata is available for tests only.",
        )

    def display_sources(self):
        from v3_app.recorder.capture_backend import CaptureDisplaySource

        return (
            CaptureDisplaySource(
                display_id="test-primary",
                display_label="Test Primary Display",
                geometry=(0, 0, 640, 360),
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
        return FrameCaptureResult(
            succeeded=True,
            message="Deterministic simulated still-frame proof metadata returned.",
            backend_name="deterministic_test_frame",
            backend_kind="test",
            source=selected,
            timestamp=1234.5 if now is None else float(now),
            width=640,
            height=360,
            pixel_format="deterministic-rgba",
            artifact_path=None,
            warnings=("simulated still-frame proof only", "not real desktop capture"),
            errors=(),
            truth_label="Simulated still-frame proof only",
            real_capture=False,
            simulated_capture=True,
        )

    def create_simulated_artifact(self, *, settings, telemetry_samples, now, created_at=None):
        from v3_app.recorder.capture_backend import CaptureBackendResult

        return CaptureBackendResult(False, "This test backend does not write recorder artifacts.")


def test_post_rc_3c_capture_backend_exposes_one_frame_capability_truth():
    from v3_app.recorder.capture_backend import MissingCaptureBackend, QtScreenCaptureBackend, SimulatedCaptureBackend

    missing = MissingCaptureBackend().capabilities()
    assert missing.one_frame_capture_available is False
    assert missing.one_frame_real_capture_supported is False

    simulated = SimulatedCaptureBackend().capabilities()
    assert simulated.one_frame_capture_available is False
    assert simulated.one_frame_real_capture_supported is False
    assert simulated.simulated_capture_supported is True

    candidate = QtScreenCaptureBackend(dependency_available=False).capabilities()
    assert candidate.backend_kind == "candidate"
    assert candidate.one_frame_capture_available is False
    assert candidate.one_frame_real_capture_supported is False
    assert candidate.requires_admin is False
    assert candidate.uses_game_injection is False
    assert candidate.uses_graphics_hooking is False
    assert candidate.video_encoding_available is False


def test_post_rc_3c_unavailable_backend_returns_typed_unavailable_result(tmp_path):
    from v3_app.recorder.capture_backend import MissingCaptureBackend

    backend = MissingCaptureBackend()
    result = backend.capture_one_frame(artifact_folder=tmp_path, now=50.0)

    assert result.succeeded is False
    assert result.backend_name == "missing_capture_backend"
    assert result.backend_kind == "missing"
    assert result.source.display_id == "current"
    assert result.source.display_label == "Current display"
    assert result.timestamp == 50.0
    assert result.width is None
    assert result.height is None
    assert result.pixel_format == "unavailable"
    assert result.artifact_path is None
    assert result.real_capture is False
    assert result.simulated_capture is False
    assert result.truth_label == "One-frame capture unavailable"
    assert result.errors
    assert not any(tmp_path.iterdir())


def test_post_rc_3c_offscreen_candidate_does_not_crash_or_start_capture(tmp_path):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    _app()
    from v3_app.recorder.capture_backend import QtScreenCaptureBackend

    backend = QtScreenCaptureBackend(dependency_available=True)
    before = tuple(tmp_path.iterdir())
    result = backend.capture_one_frame(artifact_folder=tmp_path, now=75.0)

    assert result.succeeded is False
    assert result.backend_kind == "candidate"
    assert result.real_capture is False
    assert result.simulated_capture is False
    assert result.truth_label in {"One-frame capture unavailable", "Offscreen/test context unavailable"}
    assert "video" not in result.message.casefold()
    assert before == tuple(tmp_path.iterdir())


def test_post_rc_3c_no_capture_starts_automatically_and_controller_stores_last_result(tmp_path):
    from v3_app.recorder.recorder_controller import FlightRecorderController

    backend = _DeterministicProofBackend()
    controller = FlightRecorderController(settings=_settings(tmp_path), capture_backend=backend)

    availability = controller.one_frame_proof_availability()
    assert availability.available is True
    assert backend.calls == 0
    assert controller.last_frame_capture_result is None

    result = controller.try_one_frame_capture(now=88.0)

    assert backend.calls == 1
    assert result.succeeded is True
    assert result.width == 640
    assert result.height == 360
    assert result.pixel_format == "deterministic-rgba"
    assert result.real_capture is False
    assert result.simulated_capture is True
    assert controller.last_frame_capture_result == result


def test_post_rc_3c_controller_blocks_unsupported_backend_and_preserves_review_state(tmp_path):
    from v3_app.recorder.recorder_controller import FlightRecorderController

    controller = FlightRecorderController(settings=_settings(tmp_path))
    controller.append_telemetry_sample(timestamp=10.0, axes={"Yaw": 0.2}, source="Final output")
    session = controller.review_current_session(runtime_status=_runtime_status())

    blocked = controller.try_one_frame_capture(now=90.0)

    assert session is not None
    assert controller.reviewed_session == session
    assert blocked.succeeded is False
    assert blocked.truth_label == "One-frame capture unavailable"
    assert blocked.real_capture is False
    assert blocked.simulated_capture is False


def test_post_rc_3c_flight_recorder_page_displays_capture_proof_state(tmp_path):
    _app()
    from PySide6.QtWidgets import QPushButton
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.services.app_state import AppState

    controller = FlightRecorderController(settings=_settings(tmp_path), capture_backend=_DeterministicProofBackend())
    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        recorder_controller=controller,
    )
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}

    assert "Capture Proof" in _label_text(page)
    assert "Still-frame proof" in _label_text(page)
    assert "Not video recording" in _label_text(page)
    assert "Not encoded" in _label_text(page)
    assert "Not previewable video" in _label_text(page)
    assert "No global hotkey registered" in _label_text(page)
    assert "One-frame proof availability\navailable" in _label_text(page)
    assert buttons["Try One-Frame Capture"].isEnabled() is True

    page.try_one_frame_capture()
    text = _label_text(page)
    assert "Simulated still-frame proof only" in text
    assert "Frame dimensions\n640 x 360" in text
    assert "Pixel format\ndeterministic-rgba" in text
    assert "Real capture\nfalse" in text
    assert "Simulated capture\ntrue" in text


def test_post_rc_3c_try_button_unavailable_when_backend_unsupported(tmp_path):
    _app()
    from PySide6.QtWidgets import QPushButton
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.services.app_state import AppState

    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        settings=_settings(tmp_path),
    )
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}
    text = _label_text(page)

    assert buttons["Try One-Frame Capture"].isEnabled() is False
    assert "One-frame proof availability\nunavailable" in text
    assert "Capture backend missing" in text


def test_post_rc_3c_ui_does_not_claim_recording_encoding_or_preview(tmp_path):
    _app()
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.services.app_state import AppState

    controller = FlightRecorderController(settings=_settings(tmp_path), capture_backend=_DeterministicProofBackend())
    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        recorder_controller=controller,
    )
    page.try_one_frame_capture()
    text = _label_text(page)

    assert "Still-frame proof" in text
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


def test_post_rc_3c_report_and_static_boundaries_preserve_runtime_authority():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-3c-one-frame-capture-proof-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    for required in (
        "Backend interface changes",
        "One-frame proof behavior",
        "Unavailable/offscreen behavior",
        "Diagnostic artifact behavior",
        "UI proof behavior",
        "Preserved 3B review/export behavior",
        "What remains for 3D frame buffering",
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
