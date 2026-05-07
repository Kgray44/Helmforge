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


def _shell(tmp_path):
    _app()
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell(
        AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )
    shell.switch_page("flight_recorder")
    return shell


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def _button_text(widget) -> str:
    from PySide6.QtWidgets import QPushButton

    return "\n".join(button.text() for button in widget.findChildren(QPushButton))


def test_phase13a_recorder_settings_defaults_roundtrip_restore_and_validation():
    from v3_app.overlay.axis_colors import DEFAULT_AXIS_COLORS
    from v3_app.recorder.recorder_settings import FlightRecorderSettings

    settings = FlightRecorderSettings.defaults()
    assert settings.destination_folder.name == "hotas_recordings_v3"
    assert settings.length_seconds == 20
    assert settings.frame_rate_fps == 30
    assert settings.history_seconds == 6.0
    assert settings.overlay_source == "Final output"
    assert settings.capture_source == "Current display"
    assert settings.display_label == "Current display"
    assert settings.hotkey == "Ctrl+Shift+F10"
    assert settings.record_cursor is True
    assert settings.trigger_mode == "Press to save previous interval"
    assert settings.hotkey_registered is False
    assert settings.capture_backend_available is False
    assert settings.encoder_available is False
    assert settings.compositor_available is False
    assert settings.hindsight_video_buffer_available is False
    assert {axis: axis_config.color for axis, axis_config in settings.axes.items()} == DEFAULT_AXIS_COLORS

    roundtrip = FlightRecorderSettings.from_dict(settings.to_dict())
    assert roundtrip == settings
    assert settings.restore_defaults() == FlightRecorderSettings.defaults()

    clamped = FlightRecorderSettings.from_dict(
        {
            **settings.to_dict(),
            "length_seconds": 999,
            "frame_rate_fps": 500,
            "history_seconds": -4,
        }
    )
    assert clamped.length_seconds == 120
    assert clamped.frame_rate_fps == 120
    assert clamped.history_seconds == 1.0


def test_phase13a_recorder_state_defaults_are_truthful():
    from v3_app.recorder.recorder_state import RecorderStatus, RecorderState

    state = RecorderState.default()
    assert state.status is RecorderStatus.CAPTURE_BACKEND_MISSING
    assert state.can_record is False
    assert state.can_save_last_clip is False
    assert state.status_label == "Capture backend missing"
    assert "Recording Ready" not in state.status_label
    assert "Hotkey armed" not in state.status_label


def test_phase13a_clip_library_shell_is_read_only_and_empty_by_default(tmp_path):
    from v3_app.recorder.clip_library import ClipLibrary, ClipMetadata

    library = ClipLibrary(tmp_path / "hotas_recordings_v3")
    assert library.scan() == ()
    assert library.empty_state_title == "No clips recorded yet."
    assert "Recording backend is not active in this phase." in library.empty_state_detail

    metadata = ClipMetadata.from_path(tmp_path / "demo.mp4")
    assert metadata.clip == "demo.mp4"
    assert metadata.duration == "Unavailable"
    assert metadata.opened == "Not opened"


def test_phase13a_flight_recorder_page_constructs_with_truthful_ui(tmp_path):
    from PySide6.QtWidgets import QTableWidget

    shell = _shell(tmp_path)
    page = shell.page_widgets["flight_recorder"].widget()
    text = _label_text(page)

    assert "Flight Recorder" in text
    assert "Capture the desktop on demand, then composite a time-matched axis trace overlay into the finished video." in text
    assert "Use the hotkey when you want a clean replay of what happened on-screen with the matched HOTAS signal history baked into the clip." in text
    assert "Capture/export backend is not active yet." in text

    for card in ("Recorder Settings", "Axis Overlay", "Recording Library", "Clip Preview"):
        assert card in text

    for truthful in (
        "UI Ready",
        "Capture backend missing",
        "Hotkey not registered",
        "Final output source",
        "Buffering unavailable",
        "Recording unavailable",
        "Runtime truth\nblocked_missing_device",
        "Output verified\nfalse",
        "Full Live Runtime Ready\nfalse",
    ):
        assert truthful in text

    for forbidden_claim in (
        "Hotkey armed",
        "Clip hotkey armed",
        "Recording\n",
        "Buffering\n",
        "Clip saved",
        "Recording Ready",
        "Output verified\ntrue",
        "Full Live Runtime Ready\ntrue",
    ):
        assert forbidden_claim not in text

    library = page.findChild(QTableWidget, "recordingLibraryTable")
    assert library is not None
    assert [library.horizontalHeaderItem(index).text() for index in range(library.columnCount())] == [
        "Clip",
        "Recorded",
        "Duration",
        "Opened",
    ]


def test_phase13a_recorder_actions_do_not_claim_recording_or_saved_clip(tmp_path):
    from PySide6.QtWidgets import QPushButton

    shell = _shell(tmp_path)
    page = shell.page_widgets["flight_recorder"].widget()

    buttons = {button.text(): button for button in page.findChildren(QPushButton)}
    assert "Record Now" in buttons
    assert "Save Last Clip" in buttons
    assert buttons["Record Now"].isEnabled() is False
    assert buttons["Save Last Clip"].isEnabled() is False

    page.record_now()
    page.save_last_clip()
    text = _label_text(page)
    assert "Recording unavailable; capture backend missing." in text
    assert "Hindsight video buffer unavailable; Save Last Clip cannot save real video until capture buffering exists." in text
    assert "recording started" not in text.lower()
    assert "clip saved" not in text.lower()


def test_phase13a_axis_overlay_uses_shared_phase12_colors(tmp_path):
    from PySide6.QtWidgets import QLabel
    from v3_app.overlay.axis_colors import DEFAULT_AXIS_COLORS

    shell = _shell(tmp_path)
    page = shell.page_widgets["flight_recorder"].widget()
    text = _label_text(page)

    assert "Axis colors are shared with Live Overlay so live telemetry and future recordings stay consistent." in text
    for axis, color in DEFAULT_AXIS_COLORS.items():
        assert axis in text
        color_label = page.findChild(QLabel, f"recorderAxisColor_{axis.replace(' ', '_')}")
        assert color_label is not None
        assert color_label.text() == color


def test_phase13a_clip_preview_shell_is_truthful_and_unavailable(tmp_path):
    from PySide6.QtWidgets import QPushButton, QSlider

    shell = _shell(tmp_path)
    page = shell.page_widgets["flight_recorder"].widget()
    text = _label_text(page)
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}
    scrubber = page.findChild(QSlider, "clipPreviewTimeline")

    assert "Select a recorded clip to preview." in text
    assert "Clip preview backend is not implemented yet." in text
    assert "Filename: none | Overlay source: Final output | Resolution: Unavailable | Length: Unavailable" in text
    assert scrubber is not None
    assert scrubber.isEnabled() is False
    assert buttons["Play"].isEnabled() is False
    assert buttons["Reveal File"].isEnabled() is False


def test_phase13a_help_docs_and_static_boundaries_freeze_recorder_scope(tmp_path):
    shell = _shell(tmp_path)
    page = shell.page_widgets["flight_recorder"].widget()
    button_text = _button_text(page)

    for forbidden_button in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Install Service",
        "Enable Auto Start",
        "VerifyOutput",
        "Verify Output",
    ):
        assert forbidden_button not in button_text

    help_docs = (PROJECT_ROOT / "v3_app" / "services" / "help_docs.py").read_text(encoding="utf-8")
    assert "Flight Recorder UI/state/settings/library/preview shell only" in help_docs
    assert "real capture and encoding are deferred" in help_docs
    assert "hindsight video buffering is deferred" in help_docs

    recorder_sources = []
    recorder_root = PROJECT_ROOT / "v3_app" / "recorder"
    if recorder_root.exists():
        recorder_sources.extend(recorder_root.rglob("*.py"))
    recorder_sources.append(PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py")
    sources = "\n".join(path.read_text(encoding="utf-8") for path in recorder_sources if path.exists())
    for token in (
        "mss",
        "dxcam",
        "pyautogui.screenshot",
        "ImageGrab",
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
        "DirectX",
        "Vulkan",
        "OpenGL hook",
        "pystray",
        "openai",
        "anthropic",
        "auto_save",
    ):
        assert token not in sources
