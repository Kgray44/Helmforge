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


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_post_rc_3a_capture_backend_capabilities_include_safety_fields():
    from v3_app.recorder.capture_backend import MissingCaptureBackend, SimulatedCaptureBackend

    missing = MissingCaptureBackend().capabilities()
    assert missing.backend_kind == "missing"
    assert missing.dependency_available is False
    assert missing.screen_capture_available is False
    assert missing.desktop_capture_available is False
    assert missing.frame_capture_available is False
    assert missing.cursor_capture_available is False
    assert missing.display_enumeration_available is False
    assert missing.real_capture_supported is False
    assert missing.simulated_capture_supported is False
    assert missing.simulated_artifact_available is False
    assert missing.video_encoding_available is False
    assert missing.requires_admin is False
    assert missing.uses_game_injection is False
    assert missing.uses_graphics_hooking is False
    assert missing.errors

    simulated = SimulatedCaptureBackend().capabilities()
    assert simulated.backend_kind == "simulated"
    assert simulated.dependency_available is True
    assert simulated.screen_capture_available is False
    assert simulated.frame_capture_available is False
    assert simulated.display_enumeration_available is False
    assert simulated.real_capture_supported is False
    assert simulated.simulated_capture_supported is True
    assert simulated.simulated_artifact_available is True
    assert simulated.video_encoding_available is False
    assert simulated.requires_admin is False
    assert simulated.uses_game_injection is False
    assert simulated.uses_graphics_hooking is False
    assert "metadata-only" in " ".join(simulated.warnings)


def test_post_rc_3a_candidate_backend_is_safe_to_import_and_reports_unavailable_without_dependency():
    from v3_app.recorder.capture_backend import QtScreenCaptureBackend

    backend = QtScreenCaptureBackend(dependency_available=False)
    status = backend.refresh_status()
    frame = backend.capture_frame()

    assert status.status == "candidate_unavailable"
    assert status.capabilities.backend_kind == "candidate"
    assert status.capabilities.dependency_available is False
    assert status.capabilities.real_capture_supported is False
    assert status.capabilities.frame_capture_available is False
    assert status.capabilities.video_encoding_available is False
    assert status.capabilities.requires_admin is False
    assert status.capabilities.uses_game_injection is False
    assert status.capabilities.uses_graphics_hooking is False
    assert backend.display_sources()
    assert backend.display_sources()[0].capture_source == "current display"
    assert frame.succeeded is False
    assert frame.frame is None
    assert "Post-RC 3A" in frame.message


def test_post_rc_3a_candidate_backend_does_not_start_capture_or_write_files(tmp_path):
    from v3_app.recorder.capture_backend import QtScreenCaptureBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController

    backend = QtScreenCaptureBackend(dependency_available=True)
    controller = FlightRecorderController(settings=_settings(tmp_path), capture_backend=backend)

    status = controller.refresh_status()
    record = controller.record_now(now=100.0)
    save = controller.save_last_clip(now=101.0)

    assert status.capabilities.real_capture_supported is False
    assert status.capabilities.simulated_capture_supported is False
    assert record.succeeded is False
    assert save.succeeded is False
    assert "Recording unavailable" in record.message
    assert "Hindsight video buffer unavailable" in save.message
    assert not any(tmp_path.iterdir())


def test_post_rc_3a_flight_recorder_page_displays_candidate_backend_truth(tmp_path):
    _app()
    from PySide6.QtWidgets import QPushButton
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.recorder.capture_backend import QtScreenCaptureBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.services.app_state import AppState

    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        capture_backend=QtScreenCaptureBackend(dependency_available=False),
    )
    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_status(),
        recorder_controller=controller,
    )

    text = _label_text(page)
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}

    assert "Candidate unavailable" in text
    assert "Dependency status\nunavailable" in text
    assert "Real capture supported\nfalse" in text
    assert "Frame capture\nunavailable" in text
    assert "Cursor capture\nunavailable" in text
    assert "Video encoding\nunavailable" in text
    assert "Hindsight video buffering\nunavailable" in text
    assert "Hotkey status\nNot registered" in text
    assert "Video hindsight unavailable" in text
    assert buttons["Record Now"].isEnabled() is False
    assert buttons["Save Last Clip"].isEnabled() is False
    for forbidden in (
        "Recording ready",
        "Capture ready",
        "Recording active",
        "Video encoding ready",
    ):
        assert forbidden not in text


def test_post_rc_3a_help_docs_and_reports_explain_simulated_artifacts_are_not_recordings():
    from v3_app.services.help_docs import get_article

    article = get_article("Flight Recorder")
    body = article.body
    design = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-3a-flight-recorder-capture-backend-design.md"
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-3a-recorder-capture-seam-report.md"

    assert "real backend design seam" in body
    assert "simulated artifacts are not real recordings" in body
    assert "does not inject into games" in body
    assert "does not use graphics hooks" in body
    assert "video encoding and hindsight video buffering remain later phases" in body
    assert design.exists()
    assert report.exists()
    design_text = design.read_text(encoding="utf-8")
    report_text = report.read_text(encoding="utf-8")
    for option in (
        "Qt screen grab",
        "PIL/ImageGrab",
        "mss",
        "Windows Graphics Capture",
        "dxcam",
        "ffmpeg",
    ):
        assert option in design_text
    lower_report = report_text.casefold()
    for required in (
        "backend options reviewed",
        "chosen next implementation path",
        "capability model changes",
        "UI truth changes",
        "Post-RC 3B",
        "runtime truth preservation",
    ):
        assert required.casefold() in lower_report


def test_post_rc_3a_static_boundaries_reject_runtime_authority_and_capture_claims():
    source_paths = [
        *(PROJECT_ROOT / "v3_app" / "recorder").glob("*.py"),
        PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py",
    ]
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for forbidden_token in (
        "import mss",
        "import dxcam",
        "ImageGrab.grab",
        "pyautogui.screenshot",
        "cv2.VideoWriter",
        "moviepy",
        "RegisterHotKey",
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
        "openai",
        "anthropic",
        "auto_save",
    ):
        assert forbidden_token not in source_text

    lower_source = source_text.casefold()
    for forbidden_claim in (
        "recording ready",
        "capture ready",
        "recording active",
        "video encoding ready",
        "full live runtime ready: true",
    ):
        assert forbidden_claim not in lower_source
