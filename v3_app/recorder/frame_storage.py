from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class StoredFrameArtifact:
    frame_id: str
    timestamp: float
    backend_name: str
    backend_kind: str
    display_id: str
    display_label: str
    capture_source: str
    width: int | None
    height: int | None
    pixel_format: str
    image_path: Path
    image_format: str
    file_exists: bool
    file_size_bytes: int
    checksum: str | None
    real_capture: bool
    simulated_capture: bool
    encodable: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "backend_name": self.backend_name,
            "backend_kind": self.backend_kind,
            "display_id": self.display_id,
            "display_label": self.display_label,
            "capture_source": self.capture_source,
            "width": self.width,
            "height": self.height,
            "pixel_format": self.pixel_format,
            "image_path": str(self.image_path),
            "image_format": self.image_format,
            "file_exists": self.file_exists,
            "file_size_bytes": self.file_size_bytes,
            "checksum": self.checksum,
            "real_capture": self.real_capture,
            "simulated_capture": self.simulated_capture,
            "encodable": self.encodable,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "StoredFrameArtifact":
        path = Path(str(payload.get("image_path") or ""))
        exists = path.exists() and path.is_file()
        size = path.stat().st_size if exists else _int(payload.get("file_size_bytes"), 0)
        return cls(
            frame_id=str(payload.get("frame_id") or ""),
            timestamp=_float(payload.get("timestamp"), 0.0),
            backend_name=str(payload.get("backend_name") or "unknown"),
            backend_kind=str(payload.get("backend_kind") or "unknown"),
            display_id=str(payload.get("display_id") or "unknown"),
            display_label=str(payload.get("display_label") or "Unknown display"),
            capture_source=str(payload.get("capture_source") or "unknown"),
            width=_optional_int(payload.get("width")),
            height=_optional_int(payload.get("height")),
            pixel_format=str(payload.get("pixel_format") or "unknown"),
            image_path=path,
            image_format=str(payload.get("image_format") or path.suffix.lstrip(".") or "unknown"),
            file_exists=exists,
            file_size_bytes=size,
            checksum=str(payload.get("checksum") or "") or None,
            real_capture=bool(payload.get("real_capture", False)),
            simulated_capture=bool(payload.get("simulated_capture", False)),
            encodable=bool(payload.get("encodable", False)) and exists and size > 0,
            warnings=_tuple(payload.get("warnings")),
            errors=_tuple(payload.get("errors")),
        )


@dataclass(frozen=True)
class FrameSequenceArtifact:
    sequence_id: str
    session_id: str
    sequence_folder: Path
    frames_folder: Path
    manifest_path: Path
    frame_count: int
    start_timestamp: float | None
    end_timestamp: float | None
    target_fps: int
    actual_fps_estimate: float | None
    dropped_frame_count: int
    total_size_bytes: int
    storage_mode: str
    truth_label: str
    not_encoded: bool
    not_playable: bool
    frame_files_exist: bool
    encoder_source_ready: bool
    created_at: str
    frames: tuple[StoredFrameArtifact, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence_id": self.sequence_id,
            "session_id": self.session_id,
            "sequence_folder": str(self.sequence_folder),
            "frames_folder": str(self.frames_folder),
            "manifest_path": str(self.manifest_path),
            "frame_count": self.frame_count,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "target_fps": self.target_fps,
            "actual_fps_estimate": self.actual_fps_estimate,
            "dropped_frame_count": self.dropped_frame_count,
            "total_size_bytes": self.total_size_bytes,
            "storage_mode": self.storage_mode,
            "truth_label": self.truth_label,
            "not_encoded": self.not_encoded,
            "not_playable": self.not_playable,
            "frame_files_exist": self.frame_files_exist,
            "encoder_source_ready": self.encoder_source_ready,
            "created_at": self.created_at,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class FrameStorageSettings:
    image_format: str = "png"
    max_cache_mb: int = 256
    max_sequence_frames: int = 600
    max_retained_temp_sequences: int = 3
    jpeg_quality: int = 88
    storage_enabled: bool = False

    @property
    def normalized_image_format(self) -> str:
        value = self.image_format.casefold().strip(".")
        if value in {"jpg", "jpeg"}:
            return "jpg"
        return "png"

    @property
    def max_cache_bytes(self) -> int:
        return max(1, int(self.max_cache_mb)) * 1024 * 1024


class FrameStorageManager:
    def __init__(self, destination_folder: Path, *, settings: FrameStorageSettings | None = None) -> None:
        self.destination_folder = Path(destination_folder)
        self.settings = settings or FrameStorageSettings()
        self.root_folder = self.destination_folder / "frame_sequences"

    @property
    def storage_available(self) -> bool:
        return bool(self.settings.storage_enabled)

    def create_sequence(
        self,
        *,
        session_id: str,
        sequence_id: str | None = None,
        created_at: str | None = None,
        target_fps: int = 30,
        warnings: tuple[str, ...] = (),
    ) -> "FrameStorageSequence":
        created = created_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        sequence = sequence_id or f"sequence-{_slug(created)}"
        folder = _available_path(self.root_folder / _slug(sequence))
        frames_folder = folder / "frames"
        frames_folder.mkdir(parents=True, exist_ok=True)
        return FrameStorageSequence(
            manager=self,
            sequence_id=folder.name,
            session_id=session_id,
            created_at=created,
            target_fps=max(1, int(target_fps)),
            sequence_folder=folder,
            frames_folder=frames_folder,
            manifest_path=folder / "manifest.json",
            warnings=warnings,
        )

    def frame_cache_usage_bytes(self) -> int:
        if not self.root_folder.exists():
            return 0
        total = 0
        for path in self.root_folder.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def scan_sequence_manifests(self) -> tuple[FrameSequenceArtifact, ...]:
        if not self.root_folder.exists():
            return ()
        sequences = []
        for manifest in sorted(self.root_folder.glob("*/manifest.json"), key=lambda item: item.parent.name.lower()):
            artifact = frame_sequence_from_manifest(manifest)
            if artifact is not None:
                sequences.append(artifact)
        return tuple(sequences)

    def cleanup_failed_sequence(self, sequence: "FrameStorageSequence | FrameSequenceArtifact") -> bool:
        folder = sequence.sequence_folder
        try:
            root = self.root_folder.resolve()
            target = Path(folder).resolve()
        except OSError:
            return False
        if root != target and root not in target.parents:
            return False
        if not target.exists():
            return False
        shutil.rmtree(target)
        return True

    def _can_store_frame(self, sequence: "FrameStorageSequence", next_size: int) -> tuple[bool, tuple[str, ...]]:
        errors: list[str] = []
        if not self.settings.storage_enabled:
            errors.append("Frame storage is disabled.")
        if len(sequence.frames) >= max(1, int(self.settings.max_sequence_frames)):
            errors.append("Frame storage frame count budget reached.")
        if self.frame_cache_usage_bytes() + max(0, next_size) > self.settings.max_cache_bytes:
            errors.append("Frame storage cache budget reached.")
        return not errors, tuple(errors)


class FrameStorageSequence:
    def __init__(
        self,
        *,
        manager: FrameStorageManager,
        sequence_id: str,
        session_id: str,
        created_at: str,
        target_fps: int,
        sequence_folder: Path,
        frames_folder: Path,
        manifest_path: Path,
        warnings: tuple[str, ...] = (),
    ) -> None:
        self.manager = manager
        self.sequence_id = sequence_id
        self.session_id = session_id
        self.created_at = created_at
        self.target_fps = target_fps
        self.sequence_folder = sequence_folder
        self.frames_folder = frames_folder
        self.manifest_path = manifest_path
        self.warnings = warnings
        self._frames: list[StoredFrameArtifact] = []

    @property
    def frames(self) -> tuple[StoredFrameArtifact, ...]:
        return tuple(self._frames)

    def save_image_frame(
        self,
        *,
        frame_id: str,
        timestamp: float,
        backend_name: str,
        backend_kind: str,
        display_id: str,
        display_label: str,
        capture_source: str,
        width: int | None,
        height: int | None,
        pixel_format: str,
        image_bytes: bytes,
        real_capture: bool,
        simulated_capture: bool,
        warnings: tuple[str, ...] = (),
    ) -> StoredFrameArtifact:
        allowed, errors = self.manager._can_store_frame(self, len(image_bytes))
        path = self._frame_path(frame_id)
        if not allowed:
            return self._blocked_frame(
                frame_id=frame_id,
                timestamp=timestamp,
                backend_name=backend_name,
                backend_kind=backend_kind,
                display_id=display_id,
                display_label=display_label,
                capture_source=capture_source,
                width=width,
                height=height,
                pixel_format=pixel_format,
                image_path=path,
                real_capture=real_capture,
                simulated_capture=simulated_capture,
                warnings=warnings,
                errors=errors,
            )
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bytes(image_bytes))
        except OSError as exc:
            return self._blocked_frame(
                frame_id=frame_id,
                timestamp=timestamp,
                backend_name=backend_name,
                backend_kind=backend_kind,
                display_id=display_id,
                display_label=display_label,
                capture_source=capture_source,
                width=width,
                height=height,
                pixel_format=pixel_format,
                image_path=path,
                real_capture=real_capture,
                simulated_capture=simulated_capture,
                warnings=warnings,
                errors=(f"Image frame could not be saved: {exc}",),
            )
        artifact = _stored_frame_from_path(
            frame_id=frame_id,
            timestamp=timestamp,
            backend_name=backend_name,
            backend_kind=backend_kind,
            display_id=display_id,
            display_label=display_label,
            capture_source=capture_source,
            width=width,
            height=height,
            pixel_format=pixel_format,
            image_path=path,
            image_format=self.manager.settings.normalized_image_format,
            real_capture=real_capture,
            simulated_capture=simulated_capture,
            warnings=warnings,
            errors=(),
        )
        self._frames.append(artifact)
        return artifact

    def save_qimage_frame(
        self,
        *,
        frame_id: str,
        timestamp: float,
        backend_name: str,
        backend_kind: str,
        display_id: str,
        display_label: str,
        capture_source: str,
        width: int | None,
        height: int | None,
        pixel_format: str,
        qimage,
        real_capture: bool,
        simulated_capture: bool,
        warnings: tuple[str, ...] = (),
    ) -> StoredFrameArtifact:
        allowed, errors = self.manager._can_store_frame(self, 0)
        path = self._frame_path(frame_id)
        if not allowed:
            return self._blocked_frame(
                frame_id=frame_id,
                timestamp=timestamp,
                backend_name=backend_name,
                backend_kind=backend_kind,
                display_id=display_id,
                display_label=display_label,
                capture_source=capture_source,
                width=width,
                height=height,
                pixel_format=pixel_format,
                image_path=path,
                real_capture=real_capture,
                simulated_capture=simulated_capture,
                warnings=warnings,
                errors=errors,
            )
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            quality = self.manager.settings.jpeg_quality if self.manager.settings.normalized_image_format == "jpg" else -1
            saved = bool(qimage.save(str(path), self.manager.settings.normalized_image_format.upper(), int(quality)))
        except Exception as exc:
            saved = False
            errors = (f"Qt image frame could not be saved: {exc}",)
        if not saved:
            return self._blocked_frame(
                frame_id=frame_id,
                timestamp=timestamp,
                backend_name=backend_name,
                backend_kind=backend_kind,
                display_id=display_id,
                display_label=display_label,
                capture_source=capture_source,
                width=width,
                height=height,
                pixel_format=pixel_format,
                image_path=path,
                real_capture=real_capture,
                simulated_capture=simulated_capture,
                warnings=warnings,
                errors=errors or ("Qt image frame save returned false.",),
            )
        artifact = _stored_frame_from_path(
            frame_id=frame_id,
            timestamp=timestamp,
            backend_name=backend_name,
            backend_kind=backend_kind,
            display_id=display_id,
            display_label=display_label,
            capture_source=capture_source,
            width=width,
            height=height,
            pixel_format=pixel_format,
            image_path=path,
            image_format=self.manager.settings.normalized_image_format,
            real_capture=real_capture,
            simulated_capture=simulated_capture,
            warnings=warnings,
            errors=(),
        )
        self._frames.append(artifact)
        return artifact

    def write_manifest(
        self,
        *,
        telemetry_alignment_status: str = "not_requested",
        dropped_frame_count: int = 0,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
    ) -> FrameSequenceArtifact:
        frames = tuple(_refresh_frame_state(frame) for frame in self._frames)
        self._frames = list(frames)
        frame_errors: list[str] = list(errors)
        if not frames:
            frame_errors.append("Image sequence has no stored frames.")
        for frame in frames:
            frame_errors.extend(frame.errors)
            if not frame.file_exists:
                frame_errors.append(f"Frame file missing: {frame.image_path}.")
        total_size = sum(frame.file_size_bytes for frame in frames if frame.file_exists)
        start = frames[0].timestamp if frames else None
        end = frames[-1].timestamp if frames else None
        duration = max(0.0, float(end) - float(start)) if start is not None and end is not None else 0.0
        actual_fps = round((len(frames) - 1) / duration, 3) if len(frames) > 1 and duration > 0 else None
        files_exist = bool(frames) and all(frame.file_exists and frame.file_size_bytes > 0 for frame in frames)
        artifact = FrameSequenceArtifact(
            sequence_id=self.sequence_id,
            session_id=self.session_id,
            sequence_folder=self.sequence_folder,
            frames_folder=self.frames_folder,
            manifest_path=self.manifest_path,
            frame_count=len(frames),
            start_timestamp=start,
            end_timestamp=end,
            target_fps=self.target_fps,
            actual_fps_estimate=actual_fps,
            dropped_frame_count=int(dropped_frame_count),
            total_size_bytes=total_size,
            storage_mode="file_backed",
            truth_label="Image sequence artifact; not encoded video; not playable clip.",
            not_encoded=True,
            not_playable=True,
            frame_files_exist=files_exist,
            encoder_source_ready=files_exist,
            created_at=self.created_at,
            frames=frames,
            warnings=_dedupe((*self.warnings, *warnings)),
            errors=_dedupe(tuple(frame_errors)),
        )
        payload = {
            "truth": "Image sequence artifact; not_encoded; not_playable; encoder source only when frame files exist.",
            "sequence": artifact.to_dict(),
            "telemetry_alignment_status": telemetry_alignment_status,
            "frames": [frame.to_dict() for frame in frames],
        }
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return artifact

    def _frame_path(self, frame_id: str) -> Path:
        suffix = ".jpg" if self.manager.settings.normalized_image_format == "jpg" else ".png"
        return _available_path(self.frames_folder / f"{_slug(frame_id)}{suffix}")

    def _blocked_frame(
        self,
        *,
        frame_id: str,
        timestamp: float,
        backend_name: str,
        backend_kind: str,
        display_id: str,
        display_label: str,
        capture_source: str,
        width: int | None,
        height: int | None,
        pixel_format: str,
        image_path: Path,
        real_capture: bool,
        simulated_capture: bool,
        warnings: tuple[str, ...],
        errors: tuple[str, ...],
    ) -> StoredFrameArtifact:
        return StoredFrameArtifact(
            frame_id=frame_id,
            timestamp=float(timestamp),
            backend_name=backend_name,
            backend_kind=backend_kind,
            display_id=display_id,
            display_label=display_label,
            capture_source=capture_source,
            width=width,
            height=height,
            pixel_format=pixel_format,
            image_path=image_path,
            image_format=self.manager.settings.normalized_image_format,
            file_exists=False,
            file_size_bytes=0,
            checksum=None,
            real_capture=real_capture,
            simulated_capture=simulated_capture,
            encodable=False,
            warnings=warnings,
            errors=errors,
        )


def frame_sequence_from_manifest(path: Path) -> FrameSequenceArtifact | None:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    sequence_payload = payload.get("sequence")
    frames_payload = payload.get("frames")
    if not isinstance(sequence_payload, Mapping) or not isinstance(frames_payload, list):
        return None
    frames = tuple(
        StoredFrameArtifact.from_dict(frame)
        for frame in frames_payload
        if isinstance(frame, Mapping)
    )
    errors = list(_tuple(sequence_payload.get("errors")))
    for frame in frames:
        if not frame.file_exists:
            errors.append(f"Frame file missing: {frame.image_path}.")
    files_exist = bool(frames) and all(frame.file_exists and frame.file_size_bytes > 0 for frame in frames)
    return FrameSequenceArtifact(
        sequence_id=str(sequence_payload.get("sequence_id") or Path(path).parent.name),
        session_id=str(sequence_payload.get("session_id") or ""),
        sequence_folder=Path(str(sequence_payload.get("sequence_folder") or Path(path).parent)),
        frames_folder=Path(str(sequence_payload.get("frames_folder") or Path(path).parent / "frames")),
        manifest_path=Path(path),
        frame_count=len(frames),
        start_timestamp=_optional_float(sequence_payload.get("start_timestamp")),
        end_timestamp=_optional_float(sequence_payload.get("end_timestamp")),
        target_fps=_int(sequence_payload.get("target_fps"), 0),
        actual_fps_estimate=_optional_float(sequence_payload.get("actual_fps_estimate")),
        dropped_frame_count=_int(sequence_payload.get("dropped_frame_count"), 0),
        total_size_bytes=sum(frame.file_size_bytes for frame in frames if frame.file_exists),
        storage_mode="file_backed",
        truth_label=str(sequence_payload.get("truth_label") or "Image sequence artifact; not encoded video; not playable clip."),
        not_encoded=True,
        not_playable=True,
        frame_files_exist=files_exist,
        encoder_source_ready=files_exist,
        created_at=str(sequence_payload.get("created_at") or ""),
        frames=frames,
        warnings=_tuple(sequence_payload.get("warnings")),
        errors=_dedupe(tuple(errors)),
    )


def _stored_frame_from_path(
    *,
    frame_id: str,
    timestamp: float,
    backend_name: str,
    backend_kind: str,
    display_id: str,
    display_label: str,
    capture_source: str,
    width: int | None,
    height: int | None,
    pixel_format: str,
    image_path: Path,
    image_format: str,
    real_capture: bool,
    simulated_capture: bool,
    warnings: tuple[str, ...],
    errors: tuple[str, ...],
) -> StoredFrameArtifact:
    exists = image_path.exists() and image_path.is_file()
    size = image_path.stat().st_size if exists else 0
    return StoredFrameArtifact(
        frame_id=frame_id,
        timestamp=float(timestamp),
        backend_name=backend_name,
        backend_kind=backend_kind,
        display_id=display_id,
        display_label=display_label,
        capture_source=capture_source,
        width=width,
        height=height,
        pixel_format=pixel_format,
        image_path=image_path,
        image_format=image_format,
        file_exists=exists,
        file_size_bytes=size,
        checksum=_sha256(image_path) if exists else None,
        real_capture=real_capture,
        simulated_capture=simulated_capture,
        encodable=exists and size > 0,
        warnings=warnings,
        errors=errors,
    )


def _refresh_frame_state(frame: StoredFrameArtifact) -> StoredFrameArtifact:
    return _stored_frame_from_path(
        frame_id=frame.frame_id,
        timestamp=frame.timestamp,
        backend_name=frame.backend_name,
        backend_kind=frame.backend_kind,
        display_id=frame.display_id,
        display_label=frame.display_label,
        capture_source=frame.capture_source,
        width=frame.width,
        height=frame.height,
        pixel_format=frame.pixel_format,
        image_path=frame.image_path,
        image_format=frame.image_format,
        real_capture=frame.real_capture,
        simulated_capture=frame.simulated_capture,
        warnings=frame.warnings,
        errors=frame.errors,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _available_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"No available frame storage path for {path}")


def _slug(value: str) -> str:
    safe = "".join(character if character.isalnum() else "-" for character in value)
    return "-".join(part for part in safe.split("-") if part) or "sequence"


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


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return _float(value, 0.0)


def _int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return _int(value, 0)


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
