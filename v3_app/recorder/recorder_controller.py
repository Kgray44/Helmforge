from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import time

from v3_app.overlay.telemetry_buffer import OverlayTelemetrySample
from v3_app.recorder.capture_backend import (
    CaptureBackend,
    CaptureBackendResult,
    CaptureBackendStatus,
    CaptureDisplaySource,
    FrameCaptureResult,
    MissingCaptureBackend,
)
from v3_app.recorder.compositor import (
    MissingRecorderCompositor,
    RecorderCompositor,
    build_overlay_composition_plan,
)
from v3_app.recorder.encoding_backend import (
    EncodableFrameSource,
    EncoderBackend,
    EncoderExportJob,
    EncoderResult,
    MissingEncoderBackend,
    analyze_frame_source,
    blocked_encoder_result,
)
from v3_app.recorder.hindsight_buffer import (
    RecorderFrameBufferStatus,
    RecorderFrameHindsightBuffer,
    RecorderFrameReference,
    RecorderTelemetryHindsightBuffer,
)
from v3_app.recorder.frame_storage import FrameSequenceArtifact, FrameStorageManager
from v3_app.recorder.recorder_artifacts import EncodedClipArtifact, RecorderArtifact, RecorderExportMetadata
from v3_app.recorder.recorder_settings import FlightRecorderSettings
from v3_app.recorder.recorder_state import RecorderState, RecorderStatus
from v3_app.recorder.session_review import (
    RecorderReviewExportResult,
    RecorderReviewSession,
    build_recorder_session_review,
    export_session_samples_csv,
    export_session_summary_json,
)


@dataclass(frozen=True)
class RecorderOperationResult:
    succeeded: bool
    message: str
    artifact: RecorderArtifact | None
    state: RecorderState
    export_metadata: RecorderExportMetadata | None = None


@dataclass(frozen=True)
class OneFrameProofAvailability:
    available: bool
    message: str
    status_label: str
    source: CaptureDisplaySource
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class FrameBufferAvailability:
    available: bool
    message: str
    source: CaptureDisplaySource
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class FrameBufferOperationResult:
    succeeded: bool
    message: str
    status: RecorderFrameBufferStatus


@dataclass(frozen=True)
class RecorderExportAvailability:
    available: bool
    message: str
    source: EncodableFrameSource
    encoder_name: str
    encoder_kind: str
    requested_format: str
    supported_formats: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    truth_label: str = "Export unavailable"


@dataclass(frozen=True)
class RecorderClipExportResult:
    succeeded: bool
    message: str
    export_job: EncoderExportJob | None
    encoder_result: EncoderResult | None
    encoded_clip: EncodedClipArtifact | None


class FlightRecorderController:
    def __init__(
        self,
        *,
        settings: FlightRecorderSettings | None = None,
        capture_backend: CaptureBackend | None = None,
        compositor: RecorderCompositor | None = None,
        encoder_backend: EncoderBackend | None = None,
        frame_storage_manager: FrameStorageManager | None = None,
        telemetry_buffer: RecorderTelemetryHindsightBuffer | None = None,
    ) -> None:
        self.settings = settings or FlightRecorderSettings.defaults()
        self.capture_backend = capture_backend or MissingCaptureBackend()
        self.compositor = compositor or MissingRecorderCompositor()
        self.encoder_backend = encoder_backend or MissingEncoderBackend()
        self.frame_storage_manager = frame_storage_manager
        self.telemetry_buffer = telemetry_buffer or RecorderTelemetryHindsightBuffer(
            history_seconds=self.settings.history_seconds
        )
        self.frame_buffer = RecorderFrameHindsightBuffer(
            max_duration_seconds=self.settings.history_seconds,
            target_fps=self.settings.frame_rate_fps,
            max_frame_count=_frame_count_budget(self.settings),
        )
        self.state = RecorderState.default()
        self.last_artifact: RecorderArtifact | None = None
        self.last_export_metadata: RecorderExportMetadata | None = None
        self.reviewed_session: RecorderReviewSession | None = None
        self.last_frame_capture_result: FrameCaptureResult | None = None
        self.last_encoder_result: EncoderResult | None = None
        self.last_export_job: EncoderExportJob | None = None
        self.last_encoded_clip: EncodedClipArtifact | None = None
        self.last_frame_sequence_artifact: FrameSequenceArtifact | None = None
        self._frame_buffer_source: CaptureDisplaySource | None = None
        self._frame_storage_sequence = None
        self._frame_buffer_failure_count = 0

    def refresh_status(self) -> CaptureBackendStatus:
        status = self.capture_backend.refresh_status()
        if status.capabilities.simulated_artifact_available:
            self.state = RecorderState(
                status=RecorderStatus.RECORDING_FORWARD_UNAVAILABLE,
                message=status.message,
                can_record=True,
                can_save_last_clip=True,
            )
        else:
            self.state = RecorderState.default()
        return status

    def append_telemetry_sample(self, *, timestamp: float, axes: dict[str, float], source: str) -> None:
        self.telemetry_buffer.append(timestamp=timestamp, axes=axes, source=source)

    def get_hindsight_telemetry_window(
        self, *, seconds: float | None = None, now: float | None = None
    ) -> tuple[OverlayTelemetrySample, ...]:
        current = time() if now is None else float(now)
        return self.telemetry_buffer.previous_seconds(
            seconds=self.settings.history_seconds if seconds is None else float(seconds),
            now=current,
        )

    def record_now(self, *, now: float | None = None, created_at: str | None = None) -> RecorderOperationResult:
        status = self.refresh_status()
        if not status.capabilities.simulated_artifact_available:
            return self._failed("Recording unavailable; capture backend missing.")
        return self._write_simulated_artifact(now=now, created_at=created_at)

    def save_last_clip(
        self,
        *,
        now: float | None = None,
        created_at: str | None = None,
        runtime_status=None,
    ) -> RecorderOperationResult:
        if self.frame_buffer.has_usable_frames():
            return self._write_intermediate_frame_buffer_artifact(
                now=now,
                created_at=created_at,
                runtime_status=runtime_status,
            )
        status = self.refresh_status()
        if not status.capabilities.simulated_artifact_available:
            return self._failed(
                "Video hindsight buffering unavailable. Hindsight video buffer unavailable; Save Last Clip cannot save real video until capture buffering exists."
            )
        return self._write_simulated_artifact(now=now, created_at=created_at)

    def build_status_summary(self) -> dict[str, str]:
        status = self.refresh_status()
        capabilities = status.capabilities
        return {
            "Capture backend": _capture_backend_label(capabilities),
            "Dependency status": "available" if capabilities.dependency_available else "unavailable",
            "Real capture supported": str(capabilities.real_capture_supported).lower(),
            "Frame capture": "available" if capabilities.frame_capture_available else "unavailable",
            "One-frame proof": "available" if capabilities.one_frame_capture_available else "unavailable",
            "Frame buffer": self.frame_buffer.status().health,
            "Frame storage": self.frame_buffer.status().storage_mode,
            "Cursor capture": "available" if capabilities.cursor_capture_available else "unavailable",
            "Display enumeration": "available" if capabilities.display_enumeration_available else "unavailable",
            "Video encoding": "available" if capabilities.video_encoding_available else "unavailable",
            "Encoder backend": self.encoder_backend.capabilities().encoder_name,
            "Encoder formats": ", ".join(self.encoder_backend.capabilities().supported_formats) or "none",
            "Compositor": (
                "simulated metadata exporter"
                if self.compositor.capabilities().simulated_export_available
                else "unavailable"
            ),
            "Recorder mode": (
                "metadata-only simulated artifacts"
                if capabilities.simulated_artifact_available
                else "candidate seam only / no capture active"
                if capabilities.backend_kind == "candidate"
                else "UI/backend foundation only"
            ),
            "Hotkey status": "Not registered",
            "Telemetry hindsight": self.telemetry_buffer.status_label,
            "Video hindsight": self.telemetry_buffer.video_hindsight_status,
        }

    def one_frame_proof_availability(self) -> OneFrameProofAvailability:
        status = self.refresh_status()
        capabilities = status.capabilities
        source = _first_display_source(self.capture_backend)
        warnings = _dedupe((*capabilities.warnings, *source.warnings))
        errors = _dedupe((*capabilities.errors, *source.errors))
        reasons: list[str] = []
        if not capabilities.dependency_available:
            reasons.append("backend dependency unavailable")
        if not capabilities.one_frame_capture_available:
            reasons.append("one-frame proof unsupported")
        if source.errors:
            reasons.append("display/source unavailable")
        available = not reasons
        if available:
            label = "available"
            message = "One-frame proof can be tried explicitly. This is not recording, encoding, or runtime readiness."
        else:
            label = "unavailable"
            message = f"One-frame proof unavailable: {', '.join(reasons)}."
        return OneFrameProofAvailability(
            available=available,
            message=message,
            status_label=label,
            source=source,
            warnings=warnings,
            errors=errors,
        )

    def try_one_frame_capture(self, *, now: float | None = None) -> FrameCaptureResult:
        availability = self.one_frame_proof_availability()
        timestamp = time() if now is None else float(now)
        if not availability.available:
            capabilities = self.capture_backend.capabilities()
            result = FrameCaptureResult(
                succeeded=False,
                message=availability.message,
                backend_name=capabilities.backend_name,
                backend_kind=capabilities.backend_kind,
                source=availability.source,
                timestamp=timestamp,
                width=None,
                height=None,
                pixel_format="unavailable",
                artifact_path=None,
                warnings=availability.warnings,
                errors=availability.errors,
                truth_label="One-frame capture unavailable",
                real_capture=False,
                simulated_capture=False,
            )
            self.last_frame_capture_result = result
            return result
        result = self.capture_backend.capture_one_frame(
            source=availability.source,
            artifact_folder=self.settings.destination_folder,
            now=timestamp,
        )
        self.last_frame_capture_result = result
        return result

    def frame_buffer_status(self) -> RecorderFrameBufferStatus:
        return self.frame_buffer.status()

    def frame_buffer_availability(self) -> FrameBufferAvailability:
        status = self.refresh_status()
        capabilities = status.capabilities
        source = _first_display_source(self.capture_backend)
        warnings = _dedupe((*capabilities.warnings, *source.warnings))
        errors = _dedupe((*capabilities.errors, *source.errors))
        reasons: list[str] = []
        if not capabilities.dependency_available:
            reasons.append("backend dependency unavailable")
        if not _frame_buffer_capable(capabilities):
            reasons.append("frame buffer capture unsupported")
        if source.errors:
            reasons.append("display/source unavailable")
        if reasons:
            return FrameBufferAvailability(
                available=False,
                message=f"Frame buffer unavailable: {', '.join(reasons)}.",
                source=source,
                warnings=warnings,
                errors=errors,
            )
        return FrameBufferAvailability(
            available=True,
            message="Frame buffer can start explicitly. Buffered frames are not encoded video or runtime readiness.",
            source=source,
            warnings=warnings,
            errors=errors,
        )

    def start_frame_buffer(self, *, now: float | None = None) -> FrameBufferOperationResult:
        availability = self.frame_buffer_availability()
        if not availability.available:
            return FrameBufferOperationResult(False, availability.message, self.frame_buffer.status())
        current = time() if now is None else float(now)
        created = datetime.fromtimestamp(current, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.frame_buffer.clear()
        self.frame_buffer.start()
        self._frame_buffer_source = availability.source
        self._frame_storage_sequence = None
        self.last_frame_sequence_artifact = None
        if self.frame_storage_manager is not None and self.frame_storage_manager.storage_available:
            try:
                self._frame_storage_sequence = self.frame_storage_manager.create_sequence(
                    session_id=f"frame-buffer-{_slug(created)}",
                    created_at=created,
                    target_fps=self.settings.frame_rate_fps,
                    warnings=("image sequence artifact is not encoded video", "image sequence artifact is not playable"),
                )
                self.frame_buffer.set_frame_storage_status(
                    storage_mode="file_backed",
                    sequence_folder=str(self._frame_storage_sequence.sequence_folder),
                    manifest_path=str(self._frame_storage_sequence.manifest_path),
                )
            except OSError as exc:
                self.frame_buffer.set_frame_storage_status(storage_mode="metadata_only")
                self.frame_buffer.add_error(f"Frame storage unavailable; metadata-only fallback active: {exc}")
        else:
            self.frame_buffer.set_frame_storage_status(storage_mode="metadata_only")
        self._frame_buffer_failure_count = 0
        return FrameBufferOperationResult(
            True,
            (
                "Frame buffer started explicitly with file-backed image storage; image sequences are not encoded video or playable clips."
                if self._frame_storage_sequence is not None
                else "Frame buffer started explicitly; no video recording, encoding, preview, or hotkey was started."
            ),
            self.frame_buffer.status(),
        )

    def stop_frame_buffer(self) -> FrameBufferOperationResult:
        self.frame_buffer.stop()
        return FrameBufferOperationResult(True, "Frame buffer stopped.", self.frame_buffer.status())

    def capture_frame_buffer_sample(self, *, now: float | None = None) -> FrameBufferOperationResult:
        if not self.frame_buffer.status().active:
            return FrameBufferOperationResult(
                False,
                "Frame buffer is inactive; start it explicitly before capturing frame metadata.",
                self.frame_buffer.status(),
            )
        source = self._frame_buffer_source or _first_display_source(self.capture_backend)
        timestamp = time() if now is None else float(now)
        result = _capture_one_frame_for_buffer(
            self.capture_backend,
            source=source,
            frame_storage_sequence=self._frame_storage_sequence,
            now=timestamp,
        )
        self.last_frame_capture_result = result
        if not result.succeeded:
            self._frame_buffer_failure_count += 1
            self.frame_buffer.record_drop(
                warning="Frame buffer capture attempt failed.",
                error="; ".join(result.errors) if result.errors else result.message,
            )
            if self._frame_buffer_failure_count >= 3:
                self.frame_buffer.stop()
                self.frame_buffer.add_error("Frame buffer stopped after repeated capture failures.")
            return FrameBufferOperationResult(False, result.message, self.frame_buffer.status())
        self._frame_buffer_failure_count = 0
        accepted = self.frame_buffer.add_frame(_frame_reference_from_result(result))
        if not accepted:
            return FrameBufferOperationResult(False, "Frame metadata was dropped because its timestamp was not monotonic.", self.frame_buffer.status())
        return FrameBufferOperationResult(
            True,
            (
                "Image frame captured into the explicit hindsight buffer; file-backed sequence is not encoded and not playable."
                if result.encodable_frame_available
                else "Frame metadata captured into the explicit hindsight buffer; not encoded and not playable."
            ),
            self.frame_buffer.status(),
        )

    def aligned_telemetry_for_frame_buffer(self) -> tuple[OverlayTelemetrySample, ...]:
        status = self.frame_buffer.status()
        if status.oldest_timestamp is None or status.newest_timestamp is None:
            return ()
        return tuple(
            sample
            for sample in self.telemetry_buffer.samples()
            if status.oldest_timestamp <= sample.timestamp <= status.newest_timestamp
        )

    def export_clip_availability(self, *, requested_format: str = "mp4") -> RecorderExportAvailability:
        capability = self.encoder_backend.capabilities()
        source = analyze_frame_source(self.frame_buffer.frames())
        requested = requested_format.casefold().strip(".")
        reasons: list[str] = []
        if not capability.dependency_available or not capability.can_encode_video:
            reasons.append("encoder unavailable")
        if requested not in capability.supported_formats:
            reasons.append(f"{requested} unsupported")
        if not source.encodable:
            reasons.append("frame pixels not available")
        warnings = _dedupe((*capability.warnings, *source.warnings))
        errors = _dedupe((*capability.errors, *source.errors))
        if reasons:
            return RecorderExportAvailability(
                available=False,
                message=f"Export unavailable: {', '.join(reasons)}.",
                source=source,
                encoder_name=capability.encoder_name,
                encoder_kind=capability.encoder_kind,
                requested_format=requested,
                supported_formats=capability.supported_formats,
                warnings=warnings,
                errors=errors,
                truth_label="Intermediate-only / encoded clip unavailable",
            )
        return RecorderExportAvailability(
            available=True,
            message="Export ready: encoder and encodable frame files are available.",
            source=source,
            encoder_name=capability.encoder_name,
            encoder_kind=capability.encoder_kind,
            requested_format=requested,
            supported_formats=capability.supported_formats,
            warnings=warnings,
            errors=errors,
            truth_label="Ready to encode local clip",
        )

    def export_clip(
        self,
        *,
        requested_format: str = "mp4",
        include_overlay: bool = True,
        include_telemetry_metadata: bool = True,
        now: float | None = None,
        created_at: str | None = None,
        runtime_status=None,
    ) -> RecorderClipExportResult:
        current = time() if now is None else float(now)
        created = created_at or datetime.fromtimestamp(current, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        requested = requested_format.casefold().strip(".")
        capability = self.encoder_backend.capabilities()
        availability = self.export_clip_availability(requested_format=requested)
        export_id = f"encoded-{_slug(created)}"
        export_dir = Path(self.settings.destination_folder) / f"encoded_clip_{_slug(created)}"
        output_path = _available_path(export_dir / f"clip.{requested}")
        source_artifact_path = Path(self.last_artifact.path) if self.last_artifact is not None else None
        if source_artifact_path is None and self.last_frame_sequence_artifact is not None:
            source_artifact_path = self.last_frame_sequence_artifact.manifest_path
        if not availability.available:
            encoder_result = blocked_encoder_result(
                capability=capability,
                requested_format=requested,
                message=availability.message,
                output_path=output_path,
                warnings=availability.warnings,
                errors=availability.errors,
            )
            job = EncoderExportJob(
                export_id=export_id,
                source_artifact_path=source_artifact_path,
                source_type=availability.source.source_type,
                requested_format=requested,
                output_path=output_path,
                include_overlay=include_overlay,
                include_telemetry_metadata=include_telemetry_metadata,
                encoder_backend=capability.encoder_name,
                status="unavailable",
                progress=0.0,
                warnings=availability.warnings,
                errors=availability.errors,
                truth_label=availability.truth_label,
            )
            self.last_encoder_result = encoder_result
            self.last_export_job = job
            return RecorderClipExportResult(False, availability.message, job, encoder_result, None)

        frames = self.frame_buffer.frames()
        aligned_samples = self.aligned_telemetry_for_frame_buffer()
        overlay_plan = build_overlay_composition_plan(
            frames=frames,
            telemetry_samples=aligned_samples,
            include_overlay=include_overlay,
            can_burn_overlay=capability.can_burn_overlay,
        )
        encoder_result = self.encoder_backend.encode(
            frame_paths=availability.source.frame_paths,
            output_path=output_path,
            requested_format=requested,
            frame_rate=self.settings.frame_rate_fps,
            duration_seconds=availability.source.duration_seconds,
            overlay_payload=overlay_plan.to_dict(),
        )
        job_status = "success" if encoder_result.success and encoder_result.playable_claim_allowed else "failed"
        job = EncoderExportJob(
            export_id=export_id,
            source_artifact_path=source_artifact_path,
            source_type=availability.source.source_type,
            requested_format=requested,
            output_path=output_path,
            include_overlay=include_overlay,
            include_telemetry_metadata=include_telemetry_metadata,
            encoder_backend=capability.encoder_name,
            status=job_status,
            progress=1.0,
            warnings=_dedupe((*availability.warnings, *encoder_result.warnings, *overlay_plan.warnings)),
            errors=_dedupe((*availability.errors, *encoder_result.errors, *overlay_plan.errors)),
            truth_label=encoder_result.truth_label,
        )
        self.last_encoder_result = encoder_result
        self.last_export_job = job
        if not encoder_result.success or not encoder_result.playable_claim_allowed or encoder_result.output_path is None:
            return RecorderClipExportResult(
                False,
                "Export failed verification; no playable clip claim is allowed.",
                job,
                encoder_result,
                None,
            )
        encoded_clip = _write_encoded_clip_manifest(
            export_id=export_id,
            created_at=created,
            export_dir=export_dir,
            source_artifact_path=source_artifact_path,
            source_type=availability.source.source_type,
            encoder_result=encoder_result,
            export_job=job,
            overlay_plan=overlay_plan.to_dict(),
            runtime_status=runtime_status,
        )
        self.last_encoded_clip = encoded_clip
        return RecorderClipExportResult(
            True,
            "Encoded clip created after local output verification; playable claim allowed for the exported file only.",
            job,
            encoder_result,
            encoded_clip,
        )

    def shutdown(self) -> None:
        self.frame_buffer.stop()

    def review_current_session(
        self,
        *,
        runtime_status,
        source_type: str | None = None,
        capture_mode: str = "immediate",
    ) -> RecorderReviewSession | None:
        samples = self.telemetry_buffer.samples()
        inferred_source = source_type or _review_source_type(
            self.last_artifact,
            self.last_export_metadata,
            self.capture_backend.capabilities(),
        )
        session = build_recorder_session_review(
            settings=self.settings,
            telemetry_samples=samples,
            runtime_status=runtime_status,
            source_type=inferred_source,
            capture_mode=capture_mode,
            artifact=self.last_artifact,
            export_metadata=self.last_export_metadata,
        )
        self.reviewed_session = session
        return session

    def clear_review_session(self) -> None:
        self.reviewed_session = None

    def export_review_summary_json(self, destination_folder=None) -> RecorderReviewExportResult:
        if self.reviewed_session is None:
            return RecorderReviewExportResult(False, "No reviewed recorder session is available to export.")
        destination = self.settings.destination_folder if destination_folder is None else destination_folder
        return export_session_summary_json(self.reviewed_session, destination)

    def export_review_samples_csv(self, destination_folder=None) -> RecorderReviewExportResult:
        if self.reviewed_session is None:
            return RecorderReviewExportResult(False, "No reviewed recorder session is available to export.")
        destination = self.settings.destination_folder if destination_folder is None else destination_folder
        return export_session_samples_csv(self.reviewed_session, destination)

    def _write_simulated_artifact(
        self, *, now: float | None = None, created_at: str | None = None
    ) -> RecorderOperationResult:
        current = time() if now is None else float(now)
        samples = self.get_hindsight_telemetry_window(now=current)
        if not samples:
            samples = self.telemetry_buffer.samples()
        compositor_status = self.compositor.refresh_status()
        if compositor_status.capabilities.simulated_export_available:
            export_result = self.compositor.create_simulated_export(
                settings=self.settings,
                telemetry_samples=samples,
                capture_backend_name=self.capture_backend.capabilities().backend_name,
                now=current,
                created_at=created_at,
            )
            if export_result.succeeded and export_result.metadata is not None:
                artifact = _artifact_from_export(export_result.metadata)
                self.last_artifact = artifact
                self.last_export_metadata = export_result.metadata
                self.state = RecorderState(
                    status=RecorderStatus.SAVING_UNAVAILABLE,
                    message=export_result.message,
                    can_record=True,
                    can_save_last_clip=True,
                )
                return RecorderOperationResult(True, export_result.message, artifact, self.state, export_result.metadata)
            return self._failed(export_result.message)
        backend_result: CaptureBackendResult = self.capture_backend.create_simulated_artifact(
            settings=self.settings,
            telemetry_samples=samples,
            now=current,
            created_at=created_at,
        )
        if backend_result.succeeded and backend_result.artifact is not None:
            self.last_artifact = backend_result.artifact
            self.state = RecorderState(
                status=RecorderStatus.SAVING_UNAVAILABLE,
                message=backend_result.message,
                can_record=True,
                can_save_last_clip=True,
            )
            return RecorderOperationResult(True, backend_result.message, backend_result.artifact, self.state)
        return self._failed(backend_result.message)

    def _write_intermediate_frame_buffer_artifact(
        self,
        *,
        now: float | None = None,
        created_at: str | None = None,
        runtime_status=None,
    ) -> RecorderOperationResult:
        status = self.frame_buffer.status()
        if not status.stored_frame_count:
            return self._failed("Frame buffer has no usable frame metadata to save.")
        current = time() if now is None else float(now)
        created = created_at or datetime.fromtimestamp(current, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        destination = Path(self.settings.destination_folder)
        destination.mkdir(parents=True, exist_ok=True)
        filename = f"intermediate_frame_buffer_{_slug(created)}.json"
        path = _available_path(destination / filename)
        frames = self.frame_buffer.frames()
        aligned_samples = self.aligned_telemetry_for_frame_buffer()
        runtime_truth = _runtime_truth_snapshot(runtime_status)
        frame_sequence_artifact = self._write_frame_sequence_manifest_if_available(
            telemetry_alignment_status="aligned" if aligned_samples else "no_telemetry_samples",
            dropped_frame_count=status.dropped_frame_count,
        )
        is_simulated = not any(frame.real_capture for frame in frames)
        source_type = "simulated" if is_simulated else "workspace"
        review_session = (
            build_recorder_session_review(
                settings=self.settings,
                telemetry_samples=aligned_samples,
                runtime_status=runtime_status,
                source_type=source_type,
                capture_mode="frame_buffer_intermediate",
                warnings=("Intermediate frame buffer artifact; not encoded and not playable.",),
            )
            if runtime_status is not None
            else None
        )
        artifact = RecorderArtifact(
            clip_id=f"intermediate-{_slug(created)}",
            filename=filename,
            path=path,
            created_at=created,
            duration_seconds=status.buffer_duration_seconds,
            frame_rate=status.target_fps,
            overlay_source=self.settings.overlay_source,
            capture_source=status.capture_source,
            display_label=status.display_label,
            is_simulated=is_simulated,
            has_video=False,
            has_overlay=bool(aligned_samples),
            backend_name=frames[-1].backend_name,
            status="intermediate_frame_buffer",
            notes=("intermediate frame buffer artifact", "not encoded", "not playable"),
            warnings=(
                "buffered frames are metadata/reference entries only"
                if frame_sequence_artifact is None
                else "buffered frames include file-backed image sequence references",
                "not encoded",
                "not playable",
                "not runtime readiness",
            ),
        )
        payload = {
            "truth": "Intermediate frame buffer artifact; not_encoded; not_playable; not a video recording.",
            "artifact": artifact.to_dict(),
            "frame_buffer": {
                **status.to_dict(),
                "not_encoded": True,
                "not_playable": True,
                "frame_storage": "file_backed" if frame_sequence_artifact is not None else "metadata/reference only",
            },
            "frame_sequence": frame_sequence_artifact.to_dict() if frame_sequence_artifact is not None else None,
            "frames": [frame.to_dict() for frame in frames],
            "telemetry": {
                "sample_count": len(aligned_samples),
                "source": self.settings.overlay_source,
                "samples": [_sample_to_dict(sample) for sample in aligned_samples],
            },
            "runtime_truth": runtime_truth,
            "timeline_summary": review_session.to_dict() if review_session is not None else None,
            "warnings": list(artifact.warnings),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self.last_artifact = artifact
        self.last_export_metadata = None
        self.state = RecorderState(
            status=RecorderStatus.SAVING_UNAVAILABLE,
            message="Intermediate frame buffer artifact saved; not encoded and not playable.",
            can_record=False,
            can_save_last_clip=True,
        )
        return RecorderOperationResult(True, self.state.message, artifact, self.state)

    def _write_frame_sequence_manifest_if_available(
        self,
        *,
        telemetry_alignment_status: str,
        dropped_frame_count: int,
    ) -> FrameSequenceArtifact | None:
        if self._frame_storage_sequence is None:
            return None
        artifact = self._frame_storage_sequence.write_manifest(
            telemetry_alignment_status=telemetry_alignment_status,
            dropped_frame_count=dropped_frame_count,
        )
        self.last_frame_sequence_artifact = artifact
        self.frame_buffer.set_frame_storage_status(
            storage_mode=artifact.storage_mode,
            sequence_folder=str(artifact.sequence_folder),
            manifest_path=str(artifact.manifest_path),
        )
        return artifact

    def _failed(self, message: str) -> RecorderOperationResult:
        self.state = RecorderState(
            status=RecorderStatus.CAPTURE_BACKEND_MISSING,
            message=message,
            can_record=False,
            can_save_last_clip=False,
        )
        return RecorderOperationResult(False, message, None, self.state)


def _artifact_from_export(metadata: RecorderExportMetadata) -> RecorderArtifact:
    return RecorderArtifact(
        clip_id=metadata.clip_id,
        filename=metadata.path.name,
        path=metadata.path,
        created_at=metadata.created_at,
        duration_seconds=metadata.duration_seconds,
        frame_rate=metadata.frame_rate,
        overlay_source=metadata.overlay_source,
        capture_source=metadata.capture_source,
        display_label=metadata.display_label,
        is_simulated=metadata.is_simulated,
        has_video=metadata.has_video,
        has_overlay=metadata.has_overlay_trace,
        backend_name=metadata.capture_backend,
        status=metadata.artifact_kind,
        notes=("simulated recorder export", "metadata and overlay trace only"),
        warnings=metadata.warnings,
    )


def _write_encoded_clip_manifest(
    *,
    export_id: str,
    created_at: str,
    export_dir: Path,
    source_artifact_path: Path | None,
    source_type: str,
    encoder_result: EncoderResult,
    export_job: EncoderExportJob,
    overlay_plan: dict[str, object],
    runtime_status,
) -> EncodedClipArtifact:
    export_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = export_dir / "manifest.json"
    clip = EncodedClipArtifact(
        export_id=export_id,
        created_at=created_at,
        output_path=encoder_result.output_path or export_job.output_path,
        manifest_path=manifest_path,
        source_artifact_path=source_artifact_path,
        source_artifact_type=source_type,
        encoder_backend=encoder_result.encoder_name,
        requested_format=encoder_result.requested_format,
        output_size_bytes=encoder_result.output_size_bytes,
        duration_seconds=encoder_result.duration_seconds,
        frame_count=encoder_result.frame_count,
        playable_claim_allowed=encoder_result.playable_claim_allowed,
        truth_label=encoder_result.truth_label,
        has_video=encoder_result.playable_claim_allowed,
        warnings=encoder_result.warnings,
        errors=encoder_result.errors,
    )
    payload = {
        "truth": "Encoded clip artifact; playable claim allowed only after local output verification.",
        "encoded_clip": clip.to_dict(),
        "export_job": {
            "export_id": export_job.export_id,
            "source_artifact_path": str(export_job.source_artifact_path) if export_job.source_artifact_path else None,
            "source_type": export_job.source_type,
            "requested_format": export_job.requested_format,
            "output_path": str(export_job.output_path),
            "include_overlay": export_job.include_overlay,
            "include_telemetry_metadata": export_job.include_telemetry_metadata,
            "encoder_backend": export_job.encoder_backend,
            "status": export_job.status,
            "progress": export_job.progress,
            "warnings": list(export_job.warnings),
            "errors": list(export_job.errors),
            "truth_label": export_job.truth_label,
        },
        "encoder_result": {
            "success": encoder_result.success,
            "encoder_name": encoder_result.encoder_name,
            "requested_format": encoder_result.requested_format,
            "output_path": str(encoder_result.output_path) if encoder_result.output_path else None,
            "output_exists": encoder_result.output_exists,
            "output_size_bytes": encoder_result.output_size_bytes,
            "duration_seconds": encoder_result.duration_seconds,
            "frame_count": encoder_result.frame_count,
            "playable_claim_allowed": encoder_result.playable_claim_allowed,
            "verification_summary": encoder_result.verification_summary,
            "warnings": list(encoder_result.warnings),
            "errors": list(encoder_result.errors),
            "truth_label": encoder_result.truth_label,
        },
        "overlay": overlay_plan,
        "runtime_truth": _runtime_truth_snapshot(runtime_status),
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return clip


def _frame_reference_from_result(result: FrameCaptureResult) -> RecorderFrameReference:
    return RecorderFrameReference(
        timestamp=result.timestamp,
        backend_name=result.backend_name,
        backend_kind=result.backend_kind,
        display_id=result.source.display_id,
        display_label=result.source.display_label,
        capture_source=result.source.capture_source,
        width=result.width,
        height=result.height,
        pixel_format=result.pixel_format,
        real_capture=result.real_capture,
        simulated_capture=result.simulated_capture,
        artifact_path=str(result.artifact_path) if result.artifact_path is not None else None,
        frame_storage_mode=result.frame_storage_mode,
        image_path=str(result.image_path) if result.image_path is not None else None,
        image_exists=result.image_exists,
        image_size_bytes=result.image_size_bytes,
        image_format=result.image_format,
        checksum=result.checksum,
        encodable=result.encodable_frame_available,
        warnings=result.warnings,
        errors=result.errors,
    )


def _capture_one_frame_for_buffer(
    capture_backend: CaptureBackend,
    *,
    source: CaptureDisplaySource,
    frame_storage_sequence,
    now: float,
) -> FrameCaptureResult:
    try:
        return capture_backend.capture_one_frame(
            source=source,
            artifact_folder=None,
            frame_storage_sequence=frame_storage_sequence,
            now=now,
        )
    except TypeError as exc:
        if "frame_storage_sequence" not in str(exc):
            raise
        return capture_backend.capture_one_frame(source=source, artifact_folder=None, now=now)


def _frame_buffer_capable(capabilities) -> bool:
    return bool(
        getattr(capabilities, "frame_buffer_capture_available", False)
        or getattr(capabilities, "one_frame_capture_available", False)
    )


def _frame_count_budget(settings: FlightRecorderSettings) -> int:
    requested = int(max(1.0, settings.history_seconds) * max(1, settings.frame_rate_fps))
    return max(1, min(600, requested))


def _capture_backend_label(capabilities) -> str:
    if capabilities.backend_kind == "simulated":
        return "Simulated"
    if capabilities.backend_kind == "candidate":
        return "Candidate available" if capabilities.dependency_available else "Candidate unavailable"
    if capabilities.backend_kind == "test":
        return "Test backend"
    return "Missing"


def _review_source_type(artifact: RecorderArtifact | None, metadata: RecorderExportMetadata | None, capabilities) -> str:
    if metadata is not None and metadata.is_simulated:
        return "simulated"
    if artifact is not None and artifact.is_simulated:
        return "simulated"
    if getattr(capabilities, "simulated_capture_supported", False) or getattr(
        capabilities, "simulated_artifact_available", False
    ):
        return "simulated"
    return "workspace"


def _sample_to_dict(sample: OverlayTelemetrySample) -> dict[str, object]:
    return {
        "timestamp": sample.timestamp,
        "source": sample.source,
        "axes": dict(sample.axes),
    }


def _runtime_truth_snapshot(runtime_status) -> dict[str, object]:
    if runtime_status is None:
        return {
            "mode": "unknown",
            "truth": "runtime_status_unavailable",
            "output_verified": False,
            "full_live_runtime_ready": False,
            "input_status": "unknown",
            "output_status": "unknown",
        }
    output_verified = bool(runtime_status.live_output_writes_verified)
    return {
        "mode": runtime_status.mode.value,
        "truth": runtime_status.truth.value,
        "output_verified": output_verified,
        "full_live_runtime_ready": bool(output_verified and runtime_status.truth.value == "live_verified"),
        "input_status": runtime_status.input.status.value,
        "output_status": runtime_status.output.status.value,
    }


def _first_display_source(capture_backend: CaptureBackend) -> CaptureDisplaySource:
    try:
        sources = capture_backend.display_sources()
    except Exception as exc:
        return CaptureDisplaySource(
            display_id="current",
            display_label="Current display",
            capture_source="current display",
            warnings=("Display/source enumeration failed safely.",),
            errors=(f"Display/source enumeration failed: {exc}",),
        )
    if sources:
        return sources[0]
    return CaptureDisplaySource(
        display_id="current",
        display_label="Current display",
        capture_source="current display",
        warnings=("Display/source enumeration returned no displays.",),
        errors=("Display/source unavailable.",),
    )


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return tuple(result)


def _available_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"No available recorder artifact filename for {path}")


def _slug(value: str) -> str:
    safe = "".join(character if character.isalnum() else "-" for character in value)
    return "-".join(part for part in safe.split("-") if part) or "artifact"
