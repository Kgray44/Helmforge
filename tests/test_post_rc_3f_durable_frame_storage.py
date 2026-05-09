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


def _frame_storage_manager(tmp_path, *, max_cache_mb: int = 4, max_sequence_frames: int = 12):
    from v3_app.recorder.frame_storage import FrameStorageManager, FrameStorageSettings

    return FrameStorageManager(
        tmp_path,
        settings=FrameStorageSettings(
            image_format="png",
            max_cache_mb=max_cache_mb,
            max_sequence_frames=max_sequence_frames,
            max_retained_temp_sequences=2,
            storage_enabled=True,
        ),
    )


@dataclass
class _FileBackedFrameBackend:
    calls: int = 0

    def capabilities(self):
        from v3_app.recorder.capture_backend import CaptureBackendCapabilities

        return CaptureBackendCapabilities(
            backend_name="deterministic_file_frame_source",
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
            warnings=("deterministic file-backed frame source; not real desktop capture",),
        )

    def refresh_status(self):
        from v3_app.recorder.capture_backend import CaptureBackendStatus

        return CaptureBackendStatus(
            capabilities=self.capabilities(),
            status="test_file_frame_source_available",
            message="Deterministic file-backed frame source is available for tests only.",
        )

    def display_sources(self):
        from v3_app.recorder.capture_backend import CaptureDisplaySource

        return (
            CaptureDisplaySource(
                display_id="test-display",
                display_label="Test Display",
                geometry=(0, 0, 640, 360),
                is_primary=True,
                capture_source="selected display",
            ),
        )

    def capture_frame(self, *, source=None):
        from v3_app.recorder.capture_backend import CaptureFrameResult

        selected = source or self.display_sources()[0]
        return CaptureFrameResult(True, "Compatibility frame metadata returned.", selected, frame=None)

    def capture_one_frame(self, *, source=None, artifact_folder=None, frame_storage_sequence=None, now=None):
        from v3_app.recorder.capture_backend import FrameCaptureResult

        del artifact_folder
        self.calls += 1
        selected = source or self.display_sources()[0]
        timestamp = float(now if now is not None else self.calls)
        stored = None
        if frame_storage_sequence is not None:
            stored = frame_storage_sequence.save_image_frame(
                frame_id=f"frame-{self.calls:06d}",
                timestamp=timestamp,
                backend_name="deterministic_file_frame_source",
                backend_kind="test",
                display_id=selected.display_id,
                display_label=selected.display_label,
                capture_source=selected.capture_source,
                width=640,
                height=360,
                pixel_format="test-rgba",
                image_bytes=b"deterministic png-like frame bytes",
                real_capture=False,
                simulated_capture=True,
            )
        return FrameCaptureResult(
            succeeded=True,
            message="Deterministic image frame saved for tests only.",
            backend_name="deterministic_file_frame_source",
            backend_kind="test",
            source=selected,
            timestamp=timestamp,
            width=640,
            height=360,
            pixel_format="test-rgba",
            artifact_path=None,
            artifact_kind="image_file" if stored and stored.file_exists else "metadata_only",
            image_path=stored.image_path if stored else None,
            image_format=stored.image_format if stored else None,
            image_size_bytes=stored.file_size_bytes if stored else 0,
            image_exists=bool(stored and stored.file_exists),
            checksum=stored.checksum if stored else None,
            encodable_frame_available=bool(stored and stored.encodable),
            frame_storage_mode="file_backed" if stored and stored.file_exists else "metadata_only",
            warnings=("simulated/test frame file; not real desktop capture",),
            errors=stored.errors if stored else (),
            truth_label="File-backed simulated/test image frame" if stored and stored.file_exists else "Metadata-only frame",
            real_capture=False,
            simulated_capture=True,
        )

    def create_simulated_artifact(self, *, settings, telemetry_samples, now, created_at=None):
        from v3_app.recorder.capture_backend import CaptureBackendResult

        return CaptureBackendResult(False, "This backend only supplies deterministic frame files.")


def test_post_rc_3f_frame_storage_writes_file_backed_sequence_manifest(tmp_path):
    manager = _frame_storage_manager(tmp_path)
    sequence = manager.create_sequence(
        session_id="session-a",
        sequence_id="sequence-session-a",
        created_at="2026-05-09T00:00:00Z",
        target_fps=30,
    )

    frame = sequence.save_image_frame(
        frame_id="frame-000001",
        timestamp=10.0,
        backend_name="deterministic_file_frame_source",
        backend_kind="test",
        display_id="test-display",
        display_label="Test Display",
        capture_source="selected display",
        width=640,
        height=360,
        pixel_format="test-rgba",
        image_bytes=b"deterministic frame bytes",
        real_capture=False,
        simulated_capture=True,
    )
    artifact = sequence.write_manifest(dropped_frame_count=0)

    assert frame.file_exists is True
    assert frame.file_size_bytes > 0
    assert frame.image_format == "png"
    assert frame.encodable is True
    assert artifact.storage_mode == "file_backed"
    assert artifact.not_encoded is True
    assert artifact.not_playable is True
    assert artifact.encoder_source_ready is True
    assert artifact.frame_count == 1
    assert artifact.manifest_path.exists()

    payload = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    assert payload["truth"] == "Image sequence artifact; not_encoded; not_playable; encoder source only when frame files exist."
    assert payload["sequence"]["not_encoded"] is True
    assert payload["sequence"]["not_playable"] is True
    assert payload["sequence"]["encoder_source_ready"] is True
    assert payload["frames"][0]["file_exists"] is True


def test_post_rc_3f_missing_image_file_is_reported_truthfully(tmp_path):
    manager = _frame_storage_manager(tmp_path)
    sequence = manager.create_sequence(session_id="session-missing", sequence_id="sequence-missing")
    frame = sequence.save_image_frame(
        frame_id="frame-000001",
        timestamp=1.0,
        backend_name="deterministic_file_frame_source",
        backend_kind="test",
        display_id="test-display",
        display_label="Test Display",
        capture_source="selected display",
        width=320,
        height=180,
        pixel_format="test-rgba",
        image_bytes=b"will disappear",
        real_capture=False,
        simulated_capture=True,
    )
    frame.image_path.unlink()
    artifact = sequence.write_manifest()

    assert artifact.encoder_source_ready is False
    assert artifact.frame_files_exist is False
    assert any("missing" in error.casefold() for error in artifact.errors)


def test_post_rc_3f_frame_references_preserve_metadata_only_and_file_backed_truth(tmp_path):
    from v3_app.recorder.encoding_backend import analyze_frame_source
    from v3_app.recorder.hindsight_buffer import RecorderFrameReference

    metadata_only = RecorderFrameReference(
        timestamp=1.0,
        backend_name="metadata",
        backend_kind="test",
        display_id="display",
        display_label="Display",
        capture_source="selected display",
        width=640,
        height=360,
        pixel_format="metadata",
        real_capture=False,
        simulated_capture=True,
        frame_storage_mode="metadata_only",
        encodable=False,
    )
    image_path = tmp_path / "frame.png"
    image_path.write_bytes(b"frame")
    file_backed = RecorderFrameReference(
        timestamp=2.0,
        backend_name="file",
        backend_kind="test",
        display_id="display",
        display_label="Display",
        capture_source="selected display",
        width=640,
        height=360,
        pixel_format="test-rgba",
        real_capture=False,
        simulated_capture=True,
        frame_storage_mode="file_backed",
        image_path=str(image_path),
        image_exists=True,
        image_size_bytes=image_path.stat().st_size,
        image_format="png",
        encodable=True,
    )

    metadata_source = analyze_frame_source((metadata_only,))
    file_source = analyze_frame_source((file_backed,))

    assert metadata_source.encodable is False
    assert "frame pixels not available" in " ".join(metadata_source.errors).casefold()
    assert file_source.encodable is True
    assert file_source.frame_paths == (image_path,)
    assert file_source.source_type == "simulated_test"


def test_post_rc_3f_controller_file_backed_buffer_feeds_3e_export_availability(tmp_path):
    from v3_app.recorder.encoding_backend import MissingEncoderBackend, SimulatedTestEncoderBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController

    manager = _frame_storage_manager(tmp_path)
    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        capture_backend=_FileBackedFrameBackend(),
        encoder_backend=MissingEncoderBackend(),
        frame_storage_manager=manager,
    )
    assert controller.start_frame_buffer(now=10.0).succeeded is True
    assert controller.capture_frame_buffer_sample(now=10.0).succeeded is True
    status = controller.frame_buffer_status()
    availability = controller.export_clip_availability()

    assert status.storage_mode == "file_backed"
    assert status.stored_image_frame_count == 1
    assert status.encoder_source_ready is True
    assert availability.source.encodable is True
    assert availability.available is False
    assert "encoder unavailable" in availability.message.casefold()

    controller.encoder_backend = SimulatedTestEncoderBackend()
    export = controller.export_clip(now=10.5, created_at="2026-05-09T00:01:00Z")

    assert export.succeeded is True
    assert export.encoded_clip is not None
    assert export.encoded_clip.playable_claim_allowed is True


def test_post_rc_3f_save_last_clip_writes_image_sequence_manifest(tmp_path):
    from v3_app.recorder.recorder_controller import FlightRecorderController

    manager = _frame_storage_manager(tmp_path)
    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        capture_backend=_FileBackedFrameBackend(),
        frame_storage_manager=manager,
    )
    controller.append_telemetry_sample(timestamp=10.0, axes={"Yaw": 0.5}, source="Final output")
    assert controller.start_frame_buffer(now=10.0).succeeded is True
    assert controller.capture_frame_buffer_sample(now=10.0).succeeded is True

    result = controller.save_last_clip(
        now=10.5,
        created_at="2026-05-09T00:02:00Z",
        runtime_status=_runtime_status(),
    )

    assert result.succeeded is True
    assert result.artifact is not None
    assert result.artifact.has_video is False
    assert result.artifact.status == "intermediate_frame_buffer"
    manifests = tuple((tmp_path / "frame_sequences").glob("*/manifest.json"))
    assert len(manifests) == 1
    payload = json.loads(result.artifact.path.read_text(encoding="utf-8"))
    assert payload["frame_buffer"]["frame_storage"] == "file_backed"
    assert payload["frame_sequence"]["not_encoded"] is True
    assert payload["frame_sequence"]["not_playable"] is True
    assert payload["frame_sequence"]["encoder_source_ready"] is True


def test_post_rc_3f_clip_library_lists_image_sequence_separately_from_encoded_clips(tmp_path):
    from v3_app.recorder.clip_library import ClipLibrary

    manager = _frame_storage_manager(tmp_path)
    sequence = manager.create_sequence(session_id="library", sequence_id="sequence-library")
    sequence.save_image_frame(
        frame_id="frame-000001",
        timestamp=1.0,
        backend_name="deterministic_file_frame_source",
        backend_kind="test",
        display_id="test-display",
        display_label="Test Display",
        capture_source="selected display",
        width=640,
        height=360,
        pixel_format="test-rgba",
        image_bytes=b"library frame",
        real_capture=False,
        simulated_capture=True,
    )
    sequence.write_manifest()

    clips = ClipLibrary(tmp_path).scan()
    image_sequences = [clip for clip in clips if clip.artifact_kind == "image_sequence"]

    assert len(image_sequences) == 1
    assert image_sequences[0].has_video is False
    assert image_sequences[0].opened == "Not playable / encoder source"
    assert "Image sequence artifact" in image_sequences[0].clip
    assert not [clip for clip in clips if clip.artifact_kind == "encoded_clip"]


def test_post_rc_3f_disk_budget_and_failed_sequence_cleanup(tmp_path):
    manager = _frame_storage_manager(tmp_path, max_cache_mb=1, max_sequence_frames=1)
    sequence = manager.create_sequence(session_id="budget", sequence_id="sequence-budget")

    first = sequence.save_image_frame(
        frame_id="frame-000001",
        timestamp=1.0,
        backend_name="deterministic_file_frame_source",
        backend_kind="test",
        display_id="test-display",
        display_label="Test Display",
        capture_source="selected display",
        width=10,
        height=10,
        pixel_format="test-rgba",
        image_bytes=b"ok",
        real_capture=False,
        simulated_capture=True,
    )
    second = sequence.save_image_frame(
        frame_id="frame-000002",
        timestamp=2.0,
        backend_name="deterministic_file_frame_source",
        backend_kind="test",
        display_id="test-display",
        display_label="Test Display",
        capture_source="selected display",
        width=10,
        height=10,
        pixel_format="test-rgba",
        image_bytes=b"blocked",
        real_capture=False,
        simulated_capture=True,
    )

    assert first.file_exists is True
    assert second.file_exists is False
    assert any("frame count" in error.casefold() for error in second.errors)
    assert manager.cleanup_failed_sequence(sequence) is True
    assert sequence.sequence_folder.exists() is False


def test_post_rc_3f_offscreen_qt_capture_remains_unavailable_safely(tmp_path):
    from v3_app.recorder.capture_backend import QtScreenCaptureBackend

    _app()
    manager = _frame_storage_manager(tmp_path)
    sequence = manager.create_sequence(session_id="offscreen", sequence_id="sequence-offscreen")
    backend = QtScreenCaptureBackend(dependency_available=True)
    result = backend.capture_one_frame(frame_storage_sequence=sequence, now=1.0)

    assert result.succeeded is False
    assert result.image_exists is False
    assert result.encodable_frame_available is False
    assert result.frame_storage_mode == "metadata_only"
    assert "offscreen" in result.truth_label.casefold() or "offscreen" in result.message.casefold()
    assert not any(sequence.frames_folder.glob("*.png"))


def test_post_rc_3f_flight_recorder_ui_shows_frame_storage_truth(tmp_path):
    _app()
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.services.app_state import AppState

    controller = FlightRecorderController(
        settings=_settings(tmp_path),
        capture_backend=_FileBackedFrameBackend(),
        frame_storage_manager=_frame_storage_manager(tmp_path),
    )
    page = FlightRecorderPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        recorder_controller=controller,
    )
    page.start_frame_buffer()
    controller.capture_frame_buffer_sample(now=20.0)
    page.refresh_frame_buffer_status()
    text = _label_text(page)

    assert "Frame Storage\nfile_backed" in text
    assert "Stored image frames\n1" in text
    assert "Encoder source readiness\nready" in text
    assert "Image sequence truth\nnot encoded / not playable" in text


def test_post_rc_3f_help_docs_and_report_document_storage_truth():
    from v3_app.services.help_docs import get_article, search_articles

    article = get_article("Recorder durable frame storage")
    text = article.search_text.casefold()

    assert "image sequence artifact" in text
    assert "metadata-only" in text
    assert "file-backed" in text
    assert "not encoded video" in text
    assert "no global hotkeys" in text
    assert "no game injection" in text
    assert "no graphics hooks" in text
    assert any(result.article.title == article.title for result in search_articles("frame storage budget image sequence"))

    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-3f-durable-frame-storage-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8").casefold()
    for required in (
        "frame storage model",
        "frame sequence folder",
        "qt image save behavior",
        "metadata-only fallback",
        "disk budget",
        "export availability integration",
        "clip library behavior",
        "runtime truth preservation",
    ):
        assert required in report_text


def test_post_rc_3f_static_boundaries_preserve_runtime_authority():
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
