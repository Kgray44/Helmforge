from __future__ import annotations

from dataclasses import dataclass
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
from v3_app.recorder.compositor import MissingRecorderCompositor, RecorderCompositor
from v3_app.recorder.hindsight_buffer import RecorderTelemetryHindsightBuffer
from v3_app.recorder.recorder_artifacts import RecorderArtifact, RecorderExportMetadata
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


class FlightRecorderController:
    def __init__(
        self,
        *,
        settings: FlightRecorderSettings | None = None,
        capture_backend: CaptureBackend | None = None,
        compositor: RecorderCompositor | None = None,
        telemetry_buffer: RecorderTelemetryHindsightBuffer | None = None,
    ) -> None:
        self.settings = settings or FlightRecorderSettings.defaults()
        self.capture_backend = capture_backend or MissingCaptureBackend()
        self.compositor = compositor or MissingRecorderCompositor()
        self.telemetry_buffer = telemetry_buffer or RecorderTelemetryHindsightBuffer(
            history_seconds=self.settings.history_seconds
        )
        self.state = RecorderState.default()
        self.last_artifact: RecorderArtifact | None = None
        self.last_export_metadata: RecorderExportMetadata | None = None
        self.reviewed_session: RecorderReviewSession | None = None
        self.last_frame_capture_result: FrameCaptureResult | None = None

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

    def save_last_clip(self, *, now: float | None = None, created_at: str | None = None) -> RecorderOperationResult:
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
            "Cursor capture": "available" if capabilities.cursor_capture_available else "unavailable",
            "Display enumeration": "available" if capabilities.display_enumeration_available else "unavailable",
            "Video encoding": "available" if capabilities.video_encoding_available else "unavailable",
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
