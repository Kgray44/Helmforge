from __future__ import annotations

from dataclasses import dataclass
from time import time

from v3_app.overlay.telemetry_buffer import OverlayTelemetrySample
from v3_app.recorder.capture_backend import (
    CaptureBackend,
    CaptureBackendResult,
    CaptureBackendStatus,
    MissingCaptureBackend,
)
from v3_app.recorder.compositor import MissingRecorderCompositor, RecorderCompositor
from v3_app.recorder.hindsight_buffer import RecorderTelemetryHindsightBuffer
from v3_app.recorder.recorder_artifacts import RecorderArtifact, RecorderExportMetadata
from v3_app.recorder.recorder_settings import FlightRecorderSettings
from v3_app.recorder.recorder_state import RecorderState, RecorderStatus


@dataclass(frozen=True)
class RecorderOperationResult:
    succeeded: bool
    message: str
    artifact: RecorderArtifact | None
    state: RecorderState
    export_metadata: RecorderExportMetadata | None = None


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
        return {
            "Capture backend": "simulated backend" if status.capabilities.simulated_artifact_available else "missing",
            "Compositor": (
                "simulated metadata exporter"
                if self.compositor.capabilities().simulated_export_available
                else "unavailable"
            ),
            "Recorder mode": (
                "backend foundation only / simulated artifacts only"
                if status.capabilities.simulated_artifact_available
                else "UI/backend foundation only"
            ),
            "Hotkey status": "Not registered",
            "Telemetry hindsight": self.telemetry_buffer.status_label,
            "Video hindsight": self.telemetry_buffer.video_hindsight_status,
        }

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
