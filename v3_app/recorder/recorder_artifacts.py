from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class RecorderArtifact:
    clip_id: str
    filename: str
    path: Path
    created_at: str
    duration_seconds: float
    frame_rate: int
    overlay_source: str
    capture_source: str
    display_label: str
    is_simulated: bool
    has_video: bool
    has_overlay: bool
    backend_name: str
    status: str
    notes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "clip_id": self.clip_id,
            "filename": self.filename,
            "path": str(self.path),
            "created_at": self.created_at,
            "duration_seconds": self.duration_seconds,
            "frame_rate": self.frame_rate,
            "overlay_source": self.overlay_source,
            "capture_source": self.capture_source,
            "display_label": self.display_label,
            "is_simulated": self.is_simulated,
            "has_video": self.has_video,
            "has_overlay": self.has_overlay,
            "backend_name": self.backend_name,
            "status": self.status,
            "notes": list(self.notes),
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "RecorderArtifact":
        return cls(
            clip_id=str(payload.get("clip_id") or ""),
            filename=str(payload.get("filename") or ""),
            path=Path(str(payload.get("path") or "")),
            created_at=str(payload.get("created_at") or ""),
            duration_seconds=_float(payload.get("duration_seconds"), 0.0),
            frame_rate=_int(payload.get("frame_rate"), 0),
            overlay_source=str(payload.get("overlay_source") or "Final output"),
            capture_source=str(payload.get("capture_source") or "Current display"),
            display_label=str(payload.get("display_label") or "Current display"),
            is_simulated=bool(payload.get("is_simulated", False)),
            has_video=bool(payload.get("has_video", False)),
            has_overlay=bool(payload.get("has_overlay", False)),
            backend_name=str(payload.get("backend_name") or "unknown"),
            status=str(payload.get("status") or "unknown"),
            notes=_tuple(payload.get("notes")),
            warnings=_tuple(payload.get("warnings")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "RecorderArtifact":
        payload = json.loads(text)
        if not isinstance(payload, Mapping):
            raise ValueError("Recorder artifact JSON must be an object.")
        return cls.from_dict(payload)


def _tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    if value:
        return (str(value),)
    return ()


def _float(value: object, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def artifact_from_manifest(path: Path) -> RecorderArtifact | None:
    try:
        payload: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    artifact_payload = payload.get("artifact") if isinstance(payload, Mapping) else None
    if not isinstance(artifact_payload, Mapping):
        return None
    return RecorderArtifact.from_dict(artifact_payload)


@dataclass(frozen=True)
class RecorderExportMetadata:
    export_id: str
    clip_id: str
    created_at: str
    artifact_kind: str
    path: Path
    manifest_path: Path
    duration_seconds: float
    frame_rate: int
    overlay_source: str
    capture_source: str
    display_label: str
    telemetry_sample_count: int
    included_axes: tuple[str, ...]
    is_simulated: bool
    has_video: bool
    has_real_capture: bool
    has_overlay_trace: bool
    compositor_backend: str
    capture_backend: str
    warnings: tuple[str, ...] = ()
    display_name: str = "Simulated export"
    opened: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "export_id": self.export_id,
            "clip_id": self.clip_id,
            "created_at": self.created_at,
            "artifact_kind": self.artifact_kind,
            "path": str(self.path),
            "manifest_path": str(self.manifest_path),
            "duration_seconds": self.duration_seconds,
            "frame_rate": self.frame_rate,
            "overlay_source": self.overlay_source,
            "capture_source": self.capture_source,
            "display_label": self.display_label,
            "telemetry_sample_count": self.telemetry_sample_count,
            "included_axes": list(self.included_axes),
            "is_simulated": self.is_simulated,
            "has_video": self.has_video,
            "has_real_capture": self.has_real_capture,
            "has_overlay_trace": self.has_overlay_trace,
            "compositor_backend": self.compositor_backend,
            "capture_backend": self.capture_backend,
            "warnings": list(self.warnings),
            "display_name": self.display_name,
            "opened": self.opened,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "RecorderExportMetadata":
        return cls(
            export_id=str(payload.get("export_id") or ""),
            clip_id=str(payload.get("clip_id") or payload.get("export_id") or ""),
            created_at=str(payload.get("created_at") or ""),
            artifact_kind=str(payload.get("artifact_kind") or "simulated_export"),
            path=Path(str(payload.get("path") or "")),
            manifest_path=Path(str(payload.get("manifest_path") or "")),
            duration_seconds=_float(payload.get("duration_seconds"), 0.0),
            frame_rate=_int(payload.get("frame_rate"), 0),
            overlay_source=str(payload.get("overlay_source") or "Final output"),
            capture_source=str(payload.get("capture_source") or "Current display"),
            display_label=str(payload.get("display_label") or "Current display"),
            telemetry_sample_count=_int(payload.get("telemetry_sample_count"), 0),
            included_axes=_tuple(payload.get("included_axes")),
            is_simulated=bool(payload.get("is_simulated", False)),
            has_video=bool(payload.get("has_video", False)),
            has_real_capture=bool(payload.get("has_real_capture", False)),
            has_overlay_trace=bool(payload.get("has_overlay_trace", False)),
            compositor_backend=str(payload.get("compositor_backend") or "unknown"),
            capture_backend=str(payload.get("capture_backend") or "unknown"),
            warnings=_tuple(payload.get("warnings")),
            display_name=str(payload.get("display_name") or "Simulated export"),
            opened=bool(payload.get("opened", False)),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "RecorderExportMetadata":
        payload = json.loads(text)
        if not isinstance(payload, Mapping):
            raise ValueError("Recorder export metadata JSON must be an object.")
        return cls.from_dict(payload)


def export_metadata_from_manifest(path: Path) -> RecorderExportMetadata | None:
    try:
        payload: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    export_payload = payload.get("export") if isinstance(payload, Mapping) else None
    if not isinstance(export_payload, Mapping):
        return None
    return RecorderExportMetadata.from_dict(export_payload)
