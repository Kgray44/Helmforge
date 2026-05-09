from __future__ import annotations

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


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def _add_frame(controller, path: Path | None, *, timestamp: float = 10.0, simulated: bool = True) -> None:
    from v3_app.recorder.hindsight_buffer import RecorderFrameReference

    controller.frame_buffer.add_frame(
        RecorderFrameReference(
            timestamp=timestamp,
            backend_name="deterministic_frame_source",
            backend_kind="test",
            display_id="test-display",
            display_label="Test Display",
            capture_source="selected display",
            width=640,
            height=360,
            pixel_format="test-rgba",
            real_capture=not simulated,
            simulated_capture=simulated,
            artifact_path=str(path) if path is not None else None,
            warnings=("test frame source",),
        )
    )


def test_post_rc_3e_missing_encoder_reports_unavailable():
    from v3_app.recorder.encoding_backend import MissingEncoderBackend

    backend = MissingEncoderBackend()
    capability = backend.capabilities()

    assert capability.dependency_available is False
    assert capability.can_encode_video is False
    assert capability.supported_formats == ()
    assert capability.requires_external_binary is False
    assert capability.errors
    assert "unavailable" in capability.errors[0].casefold()


def test_post_rc_3e_metadata_only_frame_buffer_is_not_encodable_even_with_test_encoder(tmp_path):
    from v3_app.recorder.encoding_backend import SimulatedTestEncoderBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController

    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        encoder_backend=SimulatedTestEncoderBackend(),
    )
    _add_frame(controller, None)

    availability = controller.export_clip_availability()
    result = controller.export_clip(now=10.5, created_at="2026-05-08T23:00:00Z")

    assert availability.available is False
    assert "frame pixels not available" in availability.message.casefold()
    assert result.succeeded is False
    assert result.encoder_result is not None
    assert result.encoder_result.playable_claim_allowed is False
    assert "not playable" in result.encoder_result.truth_label.casefold()
    assert not any(tmp_path.glob("encoded_clip_*"))


def test_post_rc_3e_test_encoder_creates_verified_local_output_and_manifest(tmp_path):
    from v3_app.recorder.encoding_backend import SimulatedTestEncoderBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController

    frame_path = tmp_path / "frame-001.png"
    frame_path.write_bytes(b"deterministic frame bytes")
    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        encoder_backend=SimulatedTestEncoderBackend(),
    )
    controller.append_telemetry_sample(timestamp=10.0, axes={"Yaw": 0.25}, source="Final output")
    _add_frame(controller, frame_path)

    result = controller.export_clip(
        requested_format="mp4",
        include_overlay=True,
        now=11.0,
        created_at="2026-05-08T23:01:00Z",
    )

    assert result.succeeded is True
    assert result.encoder_result is not None
    assert result.encoder_result.output_path is not None
    assert result.encoder_result.output_path.suffix == ".mp4"
    assert result.encoder_result.output_exists is True
    assert result.encoder_result.output_size_bytes > 0
    assert result.encoder_result.playable_claim_allowed is True
    assert result.export_job is not None
    assert result.export_job.source_type == "simulated_test"
    assert result.export_job.status == "success"
    assert result.encoded_clip is not None
    assert result.encoded_clip.output_path.exists()
    assert result.encoded_clip.manifest_path.exists()

    payload = json.loads(result.encoded_clip.manifest_path.read_text(encoding="utf-8"))
    assert payload["truth"] == "Encoded clip artifact; playable claim allowed only after local output verification."
    assert payload["encoded_clip"]["playable_claim_allowed"] is True
    assert payload["encoded_clip"]["source_artifact_type"] == "simulated_test"
    assert payload["encoded_clip"]["has_video"] is True
    assert payload["runtime_truth"]["full_live_runtime_ready"] is False
    assert payload["overlay"]["telemetry_sample_count"] == 1


def test_post_rc_3e_output_verification_denies_playable_claim_for_empty_output(tmp_path):
    from v3_app.recorder.encoding_backend import SimulatedTestEncoderBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController

    frame_path = tmp_path / "frame-001.png"
    frame_path.write_bytes(b"deterministic frame bytes")
    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        encoder_backend=SimulatedTestEncoderBackend(output_bytes=b""),
    )
    _add_frame(controller, frame_path)

    result = controller.export_clip(now=11.0, created_at="2026-05-08T23:02:00Z")

    assert result.succeeded is False
    assert result.encoder_result is not None
    assert result.encoder_result.output_exists is True
    assert result.encoder_result.output_size_bytes == 0
    assert result.encoder_result.playable_claim_allowed is False
    assert "size" in result.encoder_result.verification_summary.casefold()
    assert result.encoded_clip is None


def test_post_rc_3e_clip_library_records_encoded_clip_only_after_successful_encode(tmp_path):
    from v3_app.recorder.clip_library import ClipLibrary
    from v3_app.recorder.encoding_backend import SimulatedTestEncoderBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController

    controller = FlightRecorderController(settings=_settings(tmp_path), encoder_backend=SimulatedTestEncoderBackend())
    _add_frame(controller, None)
    intermediate = controller.save_last_clip(now=11.0, created_at="2026-05-08T23:03:00Z", runtime_status=_runtime_status())
    assert intermediate.succeeded is True
    assert intermediate.artifact is not None

    clips = ClipLibrary(tmp_path).scan()
    assert clips
    assert all(not clip.has_video for clip in clips)
    assert all("Metadata" in clip.opened or "metadata" in clip.clip.casefold() for clip in clips)

    frame_path = tmp_path / "frame-001.png"
    frame_path.write_bytes(b"deterministic frame bytes")
    _add_frame(controller, frame_path, timestamp=12.0)
    export = controller.export_clip(now=12.5, created_at="2026-05-08T23:04:00Z")

    assert export.succeeded is True
    clips = ClipLibrary(tmp_path).scan()
    encoded = [clip for clip in clips if clip.artifact_kind == "encoded_clip"]
    assert len(encoded) == 1
    assert encoded[0].has_video is True
    assert encoded[0].opened == "Playable claim allowed"


def test_post_rc_3e_flight_recorder_ui_shows_encoding_status_and_button_states(tmp_path):
    _app()
    from PySide6.QtWidgets import QPushButton
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.recorder.encoding_backend import SimulatedTestEncoderBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.services.app_state import AppState

    controller = FlightRecorderController(settings=_settings(tmp_path), encoder_backend=SimulatedTestEncoderBackend())
    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        recorder_controller=controller,
    )
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}

    assert "Export / encoding" in _label_text(page)
    assert "frame pixels not available" in _label_text(page).casefold()
    assert buttons["Export Clip"].isEnabled() is False
    assert buttons["Preview Clip"].isEnabled() is False
    assert buttons["Reveal Export File"].isEnabled() is False

    frame_path = tmp_path / "frame-001.png"
    frame_path.write_bytes(b"deterministic frame bytes")
    _add_frame(controller, frame_path)
    page.refresh_encoding_export_status()

    assert buttons["Export Clip"].isEnabled() is True
    page.export_clip()
    text = _label_text(page)
    assert "Export status\nsuccess" in text
    assert "Playable claim allowed\ntrue" in text
    assert buttons["Reveal Export File"].isEnabled() is True
    assert buttons["Preview Clip"].isEnabled() is False


def test_post_rc_3e_help_docs_include_encoding_export_truth_notes():
    from v3_app.services.help_docs import get_article, search_articles

    article = get_article("Recorder encoding/export preview")
    text = article.search_text.casefold()

    assert "intermediate artifacts are not playable" in text
    assert "playable claim allowed" in text
    assert "no game injection" in text
    assert "no graphics hooks" in text
    assert "no global recorder hotkeys" in text
    assert any(result.article.title == article.title for result in search_articles("encoder dependency playable claim"))


def test_post_rc_3e_static_boundaries_preserve_runtime_authority():
    source_paths = [
        *(PROJECT_ROOT / "v3_app" / "recorder").glob("*.py"),
        PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py",
    ]
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
    for forbidden_token in (
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
        "pystray",
        "openai",
        "anthropic",
        "auto_save",
    ):
        assert forbidden_token not in source_text
    assert "full live runtime ready: true" not in source_text.casefold()


def test_post_rc_3e_report_documents_encoding_export_truth():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-3e-encoding-export-preview-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    for required in (
        "encoder backend model",
        "source frame truth",
        "export job model",
        "overlay compositor behavior",
        "output verification",
        "clip library integration",
        "runtime truth preservation",
    ):
        assert required in report_text.casefold()
