from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

from v3_app.recorder.hindsight_buffer import RecorderFrameReference


_IMAGE_FRAME_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}


@dataclass(frozen=True)
class EncoderCapability:
    encoder_name: str
    encoder_kind: str
    dependency_available: bool
    version: str | None
    supported_formats: tuple[str, ...]
    can_encode_video: bool
    can_mux_audio: bool
    can_burn_overlay: bool
    requires_external_binary: bool
    binary_path: Path | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class EncoderResult:
    success: bool
    encoder_name: str
    requested_format: str
    output_path: Path | None
    output_exists: bool
    output_size_bytes: int
    duration_seconds: float | None
    frame_count: int | None
    playable_claim_allowed: bool
    verification_summary: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    truth_label: str = "Encoding unavailable"


@dataclass(frozen=True)
class EncodableFrameSource:
    encodable: bool
    source_type: str
    frame_paths: tuple[Path, ...]
    frame_count: int
    duration_seconds: float
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    truth_label: str = "Frame pixels unavailable"


@dataclass(frozen=True)
class EncoderExportJob:
    export_id: str
    source_artifact_path: Path | None
    source_type: str
    requested_format: str
    output_path: Path
    include_overlay: bool
    include_telemetry_metadata: bool
    encoder_backend: str
    status: str
    progress: float | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    truth_label: str = "Export unavailable"


class EncoderBackend(Protocol):
    def capabilities(self) -> EncoderCapability:
        ...

    def encode(
        self,
        *,
        frame_paths: tuple[Path, ...],
        output_path: Path,
        requested_format: str,
        frame_rate: int,
        duration_seconds: float,
        overlay_payload: Mapping[str, object] | None = None,
    ) -> EncoderResult:
        ...


class MissingEncoderBackend:
    def capabilities(self) -> EncoderCapability:
        return EncoderCapability(
            encoder_name="missing_encoder_backend",
            encoder_kind="missing",
            dependency_available=False,
            version=None,
            supported_formats=(),
            can_encode_video=False,
            can_mux_audio=False,
            can_burn_overlay=False,
            requires_external_binary=False,
            warnings=("encoding/export unavailable; no encoder backend is active.",),
            errors=("Encoder unavailable.",),
        )

    def encode(
        self,
        *,
        frame_paths: tuple[Path, ...],
        output_path: Path,
        requested_format: str,
        frame_rate: int,
        duration_seconds: float,
        overlay_payload: Mapping[str, object] | None = None,
    ) -> EncoderResult:
        del frame_paths, output_path, frame_rate, duration_seconds, overlay_payload
        return blocked_encoder_result(
            capability=self.capabilities(),
            requested_format=requested_format,
            message="encoding unavailable; no encoder backend is active.",
        )


class SimulatedTestEncoderBackend:
    def __init__(
        self,
        *,
        encoder_name: str = "deterministic_test_encoder",
        output_bytes: bytes = b"HELMFORGE_TEST_ENCODED_CLIP\n",
    ) -> None:
        self.encoder_name = encoder_name
        self.output_bytes = output_bytes

    def capabilities(self) -> EncoderCapability:
        return EncoderCapability(
            encoder_name=self.encoder_name,
            encoder_kind="test",
            dependency_available=True,
            version="deterministic-test",
            supported_formats=("mp4",),
            can_encode_video=True,
            can_mux_audio=False,
            can_burn_overlay=True,
            requires_external_binary=False,
            warnings=("Deterministic test encoder; not real desktop capture.",),
        )

    def encode(
        self,
        *,
        frame_paths: tuple[Path, ...],
        output_path: Path,
        requested_format: str,
        frame_rate: int,
        duration_seconds: float,
        overlay_payload: Mapping[str, object] | None = None,
    ) -> EncoderResult:
        del frame_rate, overlay_payload
        capability = self.capabilities()
        warnings = capability.warnings
        errors: list[str] = []
        if not frame_paths:
            errors.append("No frame files were provided to the test encoder.")
        if requested_format.casefold() not in capability.supported_formats:
            errors.append(f"Requested format {requested_format!r} is unsupported by this encoder.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self.output_bytes)
        return verify_encoded_output(
            capability=capability,
            requested_format=requested_format,
            output_path=output_path,
            duration_seconds=duration_seconds,
            frame_count=len(frame_paths),
            warnings=warnings,
            errors=tuple(errors),
        )


def analyze_frame_source(frames: tuple[RecorderFrameReference, ...]) -> EncodableFrameSource:
    if not frames:
        return EncodableFrameSource(
            encodable=False,
            source_type="frame_buffer_intermediate",
            frame_paths=(),
            frame_count=0,
            duration_seconds=0.0,
            errors=("No frame-buffer frames are available.",),
            truth_label="No encodable frame source",
        )
    frame_paths: list[Path] = []
    warnings: list[str] = []
    errors: list[str] = []
    for frame in frames:
        path_text = frame.image_path or frame.artifact_path
        if not path_text:
            errors.append("Frame pixels not available; frame-buffer entry is metadata/reference only.")
            continue
        path = Path(path_text)
        if path.suffix.casefold() not in _IMAGE_FRAME_SUFFIXES:
            errors.append(f"Frame pixels not available from metadata artifact: {path.name}.")
            continue
        if not path.exists() or not path.is_file():
            errors.append(f"Frame file missing: {path}.")
            continue
        if getattr(frame, "image_path", None) and not getattr(frame, "encodable", False):
            errors.append(f"Frame file is present but not marked encodable: {path}.")
            continue
        frame_paths.append(path)
    if not frame_paths:
        return EncodableFrameSource(
            encodable=False,
            source_type="frame_buffer_intermediate",
            frame_paths=(),
            frame_count=len(frames),
            duration_seconds=_duration(frames),
            warnings=tuple(_dedupe(tuple(warnings))),
            errors=tuple(_dedupe(tuple(errors))),
            truth_label="Frame pixels not available",
        )
    source_type = "real_frames" if any(frame.real_capture for frame in frames) else "simulated_test"
    if source_type == "simulated_test":
        warnings.append("Source frames are simulated/test frames; not real desktop capture.")
    return EncodableFrameSource(
        encodable=True,
        source_type=source_type,
        frame_paths=tuple(frame_paths),
        frame_count=len(frame_paths),
        duration_seconds=_duration(frames),
        warnings=tuple(_dedupe(tuple(warnings))),
        errors=(),
        truth_label="Encodable frame files available",
    )


def blocked_encoder_result(
    *,
    capability: EncoderCapability,
    requested_format: str,
    message: str,
    output_path: Path | None = None,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> EncoderResult:
    output_exists = bool(output_path is not None and output_path.exists())
    output_size = output_path.stat().st_size if output_exists and output_path is not None else 0
    return EncoderResult(
        success=False,
        encoder_name=capability.encoder_name,
        requested_format=requested_format,
        output_path=output_path,
        output_exists=output_exists,
        output_size_bytes=output_size,
        duration_seconds=None,
        frame_count=None,
        playable_claim_allowed=False,
        verification_summary=message,
        warnings=tuple(_dedupe((*capability.warnings, *warnings))),
        errors=tuple(_dedupe((*capability.errors, *errors))) or (message,),
        truth_label="Encoded clip unavailable / not playable",
    )


def verify_encoded_output(
    *,
    capability: EncoderCapability,
    requested_format: str,
    output_path: Path,
    duration_seconds: float | None,
    frame_count: int | None,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> EncoderResult:
    requested = requested_format.casefold().strip(".")
    output_exists = output_path.exists() and output_path.is_file()
    output_size = output_path.stat().st_size if output_exists else 0
    verification_errors: list[str] = list(errors)
    if not output_exists:
        verification_errors.append("Output file does not exist.")
    if output_exists and output_size <= 0:
        verification_errors.append("Output file size is zero.")
    if output_path.suffix.casefold() != f".{requested}":
        verification_errors.append("Output file extension does not match requested format.")
    if requested not in capability.supported_formats:
        verification_errors.append("Requested format is not supported by the encoder.")
    if not capability.can_encode_video or not capability.dependency_available:
        verification_errors.append("Encoder capability does not permit video encoding.")
    playable = output_exists and output_size > 0 and not verification_errors
    summary = (
        "Output file exists, size is greater than zero, extension matches requested format, and encoder reported no errors."
        if playable
        else "Output verification incomplete or failed: " + "; ".join(_dedupe(tuple(verification_errors)))
    )
    return EncoderResult(
        success=playable,
        encoder_name=capability.encoder_name,
        requested_format=requested,
        output_path=output_path,
        output_exists=output_exists,
        output_size_bytes=output_size,
        duration_seconds=duration_seconds,
        frame_count=frame_count,
        playable_claim_allowed=playable,
        verification_summary=summary,
        warnings=tuple(_dedupe((*capability.warnings, *warnings))),
        errors=tuple(_dedupe(tuple(verification_errors))),
        truth_label="Encoded clip verified for local playback claim" if playable else "Encoded clip not playable",
    )


def _duration(frames: tuple[RecorderFrameReference, ...]) -> float:
    if len(frames) < 2:
        return 0.0
    return max(0.0, float(frames[-1].timestamp) - float(frames[0].timestamp))


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
