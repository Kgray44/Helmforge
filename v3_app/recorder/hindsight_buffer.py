from __future__ import annotations

from dataclasses import dataclass

from shared_core.models.runtime import AXIS_NAMES
from v3_app.overlay.telemetry_buffer import OverlayTelemetrySample


@dataclass(frozen=True)
class RecorderFrameReference:
    timestamp: float
    backend_name: str
    backend_kind: str
    display_id: str
    display_label: str
    capture_source: str
    width: int | None
    height: int | None
    pixel_format: str
    real_capture: bool
    simulated_capture: bool
    artifact_path: str | None = None
    frame_storage_mode: str = "metadata_only"
    image_path: str | None = None
    image_exists: bool = False
    image_size_bytes: int = 0
    image_format: str | None = None
    checksum: str | None = None
    encodable: bool = False
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "backend_name": self.backend_name,
            "backend_kind": self.backend_kind,
            "display_id": self.display_id,
            "display_label": self.display_label,
            "capture_source": self.capture_source,
            "width": self.width,
            "height": self.height,
            "pixel_format": self.pixel_format,
            "real_capture": self.real_capture,
            "simulated_capture": self.simulated_capture,
            "artifact_path": self.artifact_path,
            "frame_storage_mode": self.frame_storage_mode,
            "image_path": self.image_path,
            "image_exists": self.image_exists,
            "image_size_bytes": self.image_size_bytes,
            "image_format": self.image_format,
            "checksum": self.checksum,
            "encodable": self.encodable,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class RecorderFrameBufferStatus:
    active: bool
    health: str
    max_duration_seconds: float
    target_fps: int
    max_frame_count: int
    stored_frame_count: int
    dropped_frame_count: int
    oldest_timestamp: float | None
    newest_timestamp: float | None
    buffer_duration_seconds: float
    display_id: str
    display_label: str
    capture_source: str
    frame_width: int | None
    frame_height: int | None
    pixel_format: str
    storage_mode: str = "metadata_only"
    stored_image_frame_count: int = 0
    frame_sequence_path: str | None = None
    frame_sequence_manifest_path: str | None = None
    total_image_size_bytes: int = 0
    encoder_source_ready: bool = False
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "active": self.active,
            "health": self.health,
            "max_duration_seconds": self.max_duration_seconds,
            "target_fps": self.target_fps,
            "max_frame_count": self.max_frame_count,
            "stored_frame_count": self.stored_frame_count,
            "dropped_frame_count": self.dropped_frame_count,
            "oldest_timestamp": self.oldest_timestamp,
            "newest_timestamp": self.newest_timestamp,
            "buffer_duration_seconds": self.buffer_duration_seconds,
            "display_id": self.display_id,
            "display_label": self.display_label,
            "capture_source": self.capture_source,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "pixel_format": self.pixel_format,
            "storage_mode": self.storage_mode,
            "stored_image_frame_count": self.stored_image_frame_count,
            "frame_sequence_path": self.frame_sequence_path,
            "frame_sequence_manifest_path": self.frame_sequence_manifest_path,
            "total_image_size_bytes": self.total_image_size_bytes,
            "encoder_source_ready": self.encoder_source_ready,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


class RecorderFrameHindsightBuffer:
    def __init__(self, *, max_duration_seconds: float, target_fps: int, max_frame_count: int) -> None:
        self.max_duration_seconds = max(1.0, float(max_duration_seconds))
        self.target_fps = max(1, int(target_fps))
        self.max_frame_count = max(1, int(max_frame_count))
        self.active = False
        self._frames: list[RecorderFrameReference] = []
        self._dropped_frame_count = 0
        self._warnings: list[str] = []
        self._errors: list[str] = []
        self._storage_mode = "metadata_only"
        self._frame_sequence_path: str | None = None
        self._frame_sequence_manifest_path: str | None = None

    def start(self) -> None:
        self.active = True
        self._errors = [error for error in self._errors if "stopped after repeated capture failures" not in error]

    def stop(self) -> None:
        self.active = False

    def clear(self) -> None:
        self._frames.clear()
        self._dropped_frame_count = 0
        self._warnings.clear()
        self._errors.clear()
        self.set_frame_storage_status(storage_mode="metadata_only")

    def record_drop(self, *, warning: str | None = None, error: str | None = None) -> None:
        self._dropped_frame_count += 1
        if warning:
            self._add_warning(warning)
        if error:
            self._add_error(error)

    def add_error(self, error: str) -> None:
        self._add_error(error)

    def add_frame(self, frame: RecorderFrameReference) -> bool:
        if self._frames and frame.timestamp <= self._frames[-1].timestamp:
            self.record_drop(warning="Dropped non-monotonic frame timestamp.")
            return False
        self._frames.append(frame)
        self._trim(now=frame.timestamp)
        return True

    def frames(self) -> tuple[RecorderFrameReference, ...]:
        return tuple(self._frames)

    def has_usable_frames(self) -> bool:
        return bool(self._frames)

    def set_frame_storage_status(
        self,
        *,
        storage_mode: str,
        sequence_folder: str | None = None,
        manifest_path: str | None = None,
    ) -> None:
        self._storage_mode = storage_mode or "metadata_only"
        self._frame_sequence_path = sequence_folder
        self._frame_sequence_manifest_path = manifest_path

    def status(self) -> RecorderFrameBufferStatus:
        oldest = self._frames[0].timestamp if self._frames else None
        newest = self._frames[-1].timestamp if self._frames else None
        latest = self._frames[-1] if self._frames else None
        health = "active" if self.active else "ready" if self._frames else "empty"
        if self._errors:
            health = "error"
        image_frames = [frame for frame in self._frames if frame.image_exists and frame.image_size_bytes > 0]
        encoder_ready = bool(self._frames) and len(image_frames) == len(self._frames) and all(frame.encodable for frame in self._frames)
        storage_mode = self._storage_mode
        if storage_mode == "metadata_only" and image_frames:
            storage_mode = "file_backed"
        return RecorderFrameBufferStatus(
            active=self.active,
            health=health,
            max_duration_seconds=self.max_duration_seconds,
            target_fps=self.target_fps,
            max_frame_count=self.max_frame_count,
            stored_frame_count=len(self._frames),
            dropped_frame_count=self._dropped_frame_count,
            oldest_timestamp=oldest,
            newest_timestamp=newest,
            buffer_duration_seconds=round((newest - oldest), 3) if oldest is not None and newest is not None else 0.0,
            display_id=latest.display_id if latest is not None else "unavailable",
            display_label=latest.display_label if latest is not None else "Unavailable",
            capture_source=latest.capture_source if latest is not None else "unavailable",
            frame_width=latest.width if latest is not None else None,
            frame_height=latest.height if latest is not None else None,
            pixel_format=latest.pixel_format if latest is not None else "unavailable",
            storage_mode=storage_mode,
            stored_image_frame_count=len(image_frames),
            frame_sequence_path=self._frame_sequence_path,
            frame_sequence_manifest_path=self._frame_sequence_manifest_path,
            total_image_size_bytes=sum(frame.image_size_bytes for frame in image_frames),
            encoder_source_ready=encoder_ready,
            warnings=tuple(self._warnings),
            errors=tuple(self._errors),
        )

    def _trim(self, *, now: float) -> None:
        cutoff = float(now) - self.max_duration_seconds
        self._frames = [frame for frame in self._frames if frame.timestamp >= cutoff]
        overflow = len(self._frames) - self.max_frame_count
        if overflow > 0:
            self._frames = self._frames[overflow:]

    def _add_warning(self, warning: str) -> None:
        if warning and warning not in self._warnings:
            self._warnings.append(warning)

    def _add_error(self, error: str) -> None:
        if error and error not in self._errors:
            self._errors.append(error)


class RecorderTelemetryHindsightBuffer:
    def __init__(self, *, history_seconds: float) -> None:
        self.history_seconds = max(1.0, float(history_seconds))
        self._samples: list[OverlayTelemetrySample] = []

    @property
    def status_label(self) -> str:
        return "Telemetry hindsight buffer available"

    @property
    def video_hindsight_status(self) -> str:
        return "Video hindsight buffering unavailable"

    def append(self, *, timestamp: float, axes: dict[str, float], source: str) -> None:
        sample = OverlayTelemetrySample(
            timestamp=float(timestamp),
            axes={axis: _clamp(axes.get(axis, 0.0)) for axis in AXIS_NAMES},
            source=source,
        )
        self._samples.append(sample)
        self.trim(now=sample.timestamp)

    def trim(self, *, now: float) -> None:
        cutoff = float(now) - self.history_seconds
        self._samples = [sample for sample in self._samples if sample.timestamp >= cutoff]

    def samples(self) -> tuple[OverlayTelemetrySample, ...]:
        return tuple(self._samples)

    def previous_seconds(self, *, seconds: float, now: float) -> tuple[OverlayTelemetrySample, ...]:
        cutoff = float(now) - max(0.0, float(seconds))
        return tuple(sample for sample in self._samples if cutoff <= sample.timestamp <= float(now))


def _clamp(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(-1.0, min(1.0, number))
