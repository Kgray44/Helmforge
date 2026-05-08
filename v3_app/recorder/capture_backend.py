from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import time
from typing import Protocol

from v3_app.overlay.telemetry_buffer import OverlayTelemetrySample
from v3_app.recorder.recorder_artifacts import RecorderArtifact
from v3_app.recorder.recorder_settings import FlightRecorderSettings


@dataclass(frozen=True)
class CaptureBackendCapabilities:
    backend_name: str
    backend_kind: str
    dependency_available: bool
    screen_capture_available: bool
    frame_capture_available: bool
    cursor_capture_available: bool
    display_enumeration_available: bool
    real_capture_supported: bool
    simulated_capture_supported: bool
    requires_admin: bool
    uses_game_injection: bool
    uses_graphics_hooking: bool
    video_encoding_available: bool
    simulated_artifact_available: bool = False
    one_frame_capture_available: bool = False
    one_frame_real_capture_supported: bool = False
    frame_buffer_capture_available: bool = False
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def desktop_capture_available(self) -> bool:
        return self.screen_capture_available


@dataclass(frozen=True)
class CaptureDisplaySource:
    display_id: str
    display_label: str
    geometry: tuple[int, int, int, int] | None = None
    is_primary: bool | None = None
    capture_source: str = "current display"
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class CaptureBackendStatus:
    capabilities: CaptureBackendCapabilities
    status: str
    message: str


@dataclass(frozen=True)
class CaptureBackendResult:
    succeeded: bool
    message: str
    artifact: RecorderArtifact | None = None


@dataclass(frozen=True)
class CaptureFrameResult:
    succeeded: bool
    message: str
    source: CaptureDisplaySource
    frame: object | None = None


@dataclass(frozen=True)
class FrameCaptureResult:
    succeeded: bool
    message: str
    backend_name: str
    backend_kind: str
    source: CaptureDisplaySource
    timestamp: float
    width: int | None = None
    height: int | None = None
    pixel_format: str = "unknown"
    artifact_path: Path | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    truth_label: str = "One-frame capture unavailable"
    real_capture: bool = False
    simulated_capture: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "succeeded": self.succeeded,
            "message": self.message,
            "backend_name": self.backend_name,
            "backend_kind": self.backend_kind,
            "display_id": self.source.display_id,
            "display_label": self.source.display_label,
            "capture_source": self.source.capture_source,
            "timestamp": self.timestamp,
            "width": self.width,
            "height": self.height,
            "pixel_format": self.pixel_format,
            "artifact_path": str(self.artifact_path) if self.artifact_path is not None else None,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "truth_label": self.truth_label,
            "real_capture": self.real_capture,
            "simulated_capture": self.simulated_capture,
        }


class CaptureBackend(Protocol):
    def capabilities(self) -> CaptureBackendCapabilities:
        ...

    def refresh_status(self) -> CaptureBackendStatus:
        ...

    def display_sources(self) -> tuple[CaptureDisplaySource, ...]:
        ...

    def capture_frame(self, *, source: CaptureDisplaySource | None = None) -> CaptureFrameResult:
        ...

    def capture_one_frame(
        self,
        *,
        source: CaptureDisplaySource | None = None,
        artifact_folder: Path | None = None,
        now: float | None = None,
    ) -> FrameCaptureResult:
        ...

    def create_simulated_artifact(
        self,
        *,
        settings: FlightRecorderSettings,
        telemetry_samples: tuple[OverlayTelemetrySample, ...],
        now: float,
        created_at: str | None = None,
    ) -> CaptureBackendResult:
        ...


class MissingCaptureBackend:
    def capabilities(self) -> CaptureBackendCapabilities:
        return CaptureBackendCapabilities(
            backend_name="missing_capture_backend",
            backend_kind="missing",
            dependency_available=False,
            screen_capture_available=False,
            frame_capture_available=False,
            cursor_capture_available=False,
            display_enumeration_available=False,
            real_capture_supported=False,
            simulated_capture_supported=False,
            requires_admin=False,
            uses_game_injection=False,
            uses_graphics_hooking=False,
            video_encoding_available=False,
            simulated_artifact_available=False,
            warnings=("Capture backend missing; recorder remains metadata-only unless a simulated backend is injected.",),
            errors=("No capture backend is active.",),
        )

    def refresh_status(self) -> CaptureBackendStatus:
        return CaptureBackendStatus(
            capabilities=self.capabilities(),
            status="capture_backend_missing",
            message="Capture backend missing; recording unavailable.",
        )

    def display_sources(self) -> tuple[CaptureDisplaySource, ...]:
        return (_default_display_source(errors=("Capture backend missing; display enumeration unavailable.",)),)

    def capture_frame(self, *, source: CaptureDisplaySource | None = None) -> CaptureFrameResult:
        selected = source or self.display_sources()[0]
        return CaptureFrameResult(
            succeeded=False,
            message="Frame capture unavailable; capture backend missing.",
            source=selected,
        )

    def capture_one_frame(
        self,
        *,
        source: CaptureDisplaySource | None = None,
        artifact_folder: Path | None = None,
        now: float | None = None,
    ) -> FrameCaptureResult:
        del artifact_folder
        selected = source or self.display_sources()[0]
        return _unavailable_frame_result(
            capabilities=self.capabilities(),
            source=selected,
            timestamp=_timestamp(now),
            message="One-frame capture unavailable; capture backend missing.",
            truth_label="One-frame capture unavailable",
            errors=("No capture backend is active.", *selected.errors),
            warnings=selected.warnings,
        )

    def create_simulated_artifact(
        self,
        *,
        settings: FlightRecorderSettings,
        telemetry_samples: tuple[OverlayTelemetrySample, ...],
        now: float,
        created_at: str | None = None,
    ) -> CaptureBackendResult:
        return CaptureBackendResult(
            succeeded=False,
            message="Recording unavailable; capture backend missing.",
        )


class SimulatedCaptureBackend:
    def __init__(self, *, backend_name: str = "simulated_capture") -> None:
        self.backend_name = backend_name

    def capabilities(self) -> CaptureBackendCapabilities:
        return CaptureBackendCapabilities(
            backend_name=self.backend_name,
            backend_kind="simulated",
            dependency_available=True,
            screen_capture_available=False,
            frame_capture_available=False,
            cursor_capture_available=False,
            display_enumeration_available=False,
            real_capture_supported=False,
            simulated_capture_supported=True,
            requires_admin=False,
            uses_game_injection=False,
            uses_graphics_hooking=False,
            video_encoding_available=False,
            simulated_artifact_available=True,
            warnings=(
                "metadata-only simulated artifacts",
                "no desktop frames captured",
                "no video encoding performed",
            ),
        )

    def refresh_status(self) -> CaptureBackendStatus:
        return CaptureBackendStatus(
            capabilities=self.capabilities(),
            status="simulated_backend",
            message="Simulated backend available for non-video recorder artifacts only.",
        )

    def display_sources(self) -> tuple[CaptureDisplaySource, ...]:
        return (_default_display_source(warnings=("Simulated backend has no real display enumeration.",)),)

    def capture_frame(self, *, source: CaptureDisplaySource | None = None) -> CaptureFrameResult:
        selected = source or self.display_sources()[0]
        return CaptureFrameResult(
            succeeded=False,
            message="Frame capture unavailable; simulated backend writes metadata-only artifacts.",
            source=selected,
        )

    def capture_one_frame(
        self,
        *,
        source: CaptureDisplaySource | None = None,
        artifact_folder: Path | None = None,
        now: float | None = None,
    ) -> FrameCaptureResult:
        del artifact_folder
        selected = source or self.display_sources()[0]
        return _unavailable_frame_result(
            capabilities=self.capabilities(),
            source=selected,
            timestamp=_timestamp(now),
            message="One-frame capture unavailable; default simulated backend writes metadata-only recorder artifacts.",
            truth_label="One-frame capture unavailable",
            warnings=("simulated backend is not real desktop capture", *selected.warnings),
            errors=("Simulated backend has no deterministic one-frame proof enabled.", *selected.errors),
            simulated_capture=True,
        )

    def create_simulated_artifact(
        self,
        *,
        settings: FlightRecorderSettings,
        telemetry_samples: tuple[OverlayTelemetrySample, ...],
        now: float,
        created_at: str | None = None,
    ) -> CaptureBackendResult:
        created = created_at or datetime.fromtimestamp(float(now), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        clip_id = f"simulated-{_slug(created)}"
        filename = f"simulated_recorder_artifact_{_slug(created)}.json"
        destination = Path(settings.destination_folder)
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / filename
        artifact = RecorderArtifact(
            clip_id=clip_id,
            filename=filename,
            path=path,
            created_at=created,
            duration_seconds=float(settings.length_seconds),
            frame_rate=int(settings.frame_rate_fps),
            overlay_source=settings.overlay_source,
            capture_source=settings.capture_source,
            display_label=settings.display_label,
            is_simulated=True,
            has_video=False,
            has_overlay=bool(telemetry_samples),
            backend_name=self.backend_name,
            status="simulated_artifact",
            notes=("simulated recorder artifact", "no video frames captured", "no encoding performed"),
            warnings=("not real desktop capture", "actual playable clip export is not implemented"),
        )
        manifest = {
            "truth": (
                "Simulated recorder artifact; not real desktop capture; "
                "no video frames captured; no encoding performed."
            ),
            "artifact": artifact.to_dict(),
            "telemetry": {
                "sample_count": len(telemetry_samples),
                "source": settings.overlay_source,
                "samples": [_sample_to_dict(sample) for sample in telemetry_samples],
            },
        }
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return CaptureBackendResult(
            succeeded=True,
            message="Simulated artifact saved; metadata-only manifest was written.",
            artifact=artifact,
        )


class QtScreenCaptureBackend:
    def __init__(
        self,
        *,
        backend_name: str = "qt_screen_capture_candidate",
        dependency_available: bool | None = None,
        display_sources: tuple[CaptureDisplaySource, ...] | None = None,
    ) -> None:
        self.backend_name = backend_name
        self._dependency_available = _qt_dependency_available() if dependency_available is None else bool(dependency_available)
        self._display_sources = display_sources

    def capabilities(self) -> CaptureBackendCapabilities:
        dependency_note = "Qt dependency available." if self._dependency_available else "Qt dependency unavailable."
        errors = () if self._dependency_available else ("Qt candidate dependency unavailable.",)
        one_frame_available = self._one_frame_context_available()
        return CaptureBackendCapabilities(
            backend_name=self.backend_name,
            backend_kind="candidate",
            dependency_available=self._dependency_available,
            screen_capture_available=False,
            frame_capture_available=False,
            cursor_capture_available=False,
            display_enumeration_available=self._dependency_available,
            real_capture_supported=False,
            simulated_capture_supported=False,
            requires_admin=False,
            uses_game_injection=False,
            uses_graphics_hooking=False,
            video_encoding_available=False,
            simulated_artifact_available=False,
            one_frame_capture_available=one_frame_available,
            one_frame_real_capture_supported=one_frame_available,
            frame_buffer_capture_available=one_frame_available,
            warnings=(
                dependency_note,
                "Post-RC 3C allows only explicit one-frame proof when a safe Qt display context exists."
                if one_frame_available
                else "Post-RC 3C/3D capture proof and frame buffering are unavailable in this Qt context.",
                "No video recording, encoding, hotkey registration, game injection, or graphics hooking is active.",
            ),
            errors=errors,
        )

    def refresh_status(self) -> CaptureBackendStatus:
        capabilities = self.capabilities()
        if capabilities.one_frame_capture_available:
            message = "Qt capture candidate can attempt one explicit still-frame proof; no recording or encoding is active."
            status = "one_frame_candidate_available"
        elif capabilities.dependency_available:
            message = "Qt capture candidate available as a design seam; one-frame proof is unavailable in this context."
            status = "candidate_unavailable"
        else:
            message = "Qt capture candidate unavailable; dependency is not available and no capture is active."
            status = "candidate_unavailable"
        return CaptureBackendStatus(
            capabilities=capabilities,
            status=status,
            message=message,
        )

    def display_sources(self) -> tuple[CaptureDisplaySource, ...]:
        if self._display_sources is not None:
            return self._display_sources
        if not self._dependency_available:
            return (
                _default_display_source(
                    warnings=("Qt candidate dependency unavailable; using current display placeholder.",),
                    errors=("Real display enumeration unavailable.",),
                ),
            )
        try:
            from PySide6.QtGui import QGuiApplication
        except Exception:
            return (
                _default_display_source(
                    warnings=("Qt dependency import failed; using current display placeholder.",),
                    errors=("Real display enumeration unavailable.",),
                ),
            )
        app = QGuiApplication.instance()
        if app is None:
            return (_default_display_source(warnings=("Qt application unavailable; using current display placeholder.",)),)
        primary = app.primaryScreen()
        sources: list[CaptureDisplaySource] = []
        for index, screen in enumerate(app.screens(), start=1):
            geometry = screen.geometry()
            label = screen.name() or f"Display {index}"
            sources.append(
                CaptureDisplaySource(
                    display_id=str(index),
                    display_label=label,
                    geometry=(geometry.x(), geometry.y(), geometry.width(), geometry.height()),
                    is_primary=screen == primary,
                    capture_source="current display" if screen == primary else "selected display",
                    warnings=("Frame buffering is explicit-start metadata/reference buffering only.",),
                )
            )
        return tuple(sources) or (_default_display_source(warnings=("No Qt displays reported.",)),)

    def capture_frame(self, *, source: CaptureDisplaySource | None = None) -> CaptureFrameResult:
        selected = source or self.display_sources()[0]
        return CaptureFrameResult(
            succeeded=False,
            message="Post-RC 3A defines the capture backend seam only; no desktop frames are captured.",
            source=selected,
        )

    def capture_one_frame(
        self,
        *,
        source: CaptureDisplaySource | None = None,
        artifact_folder: Path | None = None,
        now: float | None = None,
    ) -> FrameCaptureResult:
        timestamp = _timestamp(now)
        selected = source or self.display_sources()[0]
        capabilities = self.capabilities()
        if not capabilities.dependency_available:
            return _unavailable_frame_result(
                capabilities=capabilities,
                source=selected,
                timestamp=timestamp,
                message="One-frame capture unavailable; Qt candidate dependency is unavailable.",
                truth_label="One-frame capture unavailable",
                warnings=selected.warnings,
                errors=("Qt candidate dependency unavailable.", *selected.errors),
            )
        if _qt_offscreen_context():
            return _unavailable_frame_result(
                capabilities=capabilities,
                source=selected,
                timestamp=timestamp,
                message="One-frame capture unavailable in offscreen/test Qt context.",
                truth_label="Offscreen/test context unavailable",
                warnings=("offscreen/test context cannot prove real desktop capture", *selected.warnings),
                errors=selected.errors,
            )
        if selected.errors:
            return _unavailable_frame_result(
                capabilities=capabilities,
                source=selected,
                timestamp=timestamp,
                message="One-frame capture unavailable; selected display/source is unavailable.",
                truth_label="One-frame capture unavailable",
                warnings=selected.warnings,
                errors=selected.errors,
            )
        screen = _qt_screen_for_source(selected)
        if screen is None:
            return _unavailable_frame_result(
                capabilities=capabilities,
                source=selected,
                timestamp=timestamp,
                message="One-frame capture unavailable; no Qt screen is available for the selected source.",
                truth_label="One-frame capture unavailable",
                warnings=selected.warnings,
                errors=("No Qt screen is available for the selected source.",),
            )
        try:
            pixmap = screen.grabWindow(0)
        except Exception as exc:
            return _unavailable_frame_result(
                capabilities=capabilities,
                source=selected,
                timestamp=timestamp,
                message="One-frame capture failed safely; Qt screen grab raised an error.",
                truth_label="One-frame capture unavailable",
                warnings=selected.warnings,
                errors=(f"Qt screen grab failed: {exc}",),
            )
        if pixmap.isNull():
            return _unavailable_frame_result(
                capabilities=capabilities,
                source=selected,
                timestamp=timestamp,
                message="One-frame capture failed safely; Qt returned an empty frame.",
                truth_label="One-frame capture unavailable",
                warnings=selected.warnings,
                errors=("Qt returned an empty frame.",),
            )
        width = int(pixmap.width())
        height = int(pixmap.height())
        pixel_format = _qt_pixel_format_label(pixmap)
        artifact_path, artifact_errors = _write_one_frame_metadata_artifact(
            artifact_folder=artifact_folder,
            timestamp=timestamp,
            backend_name=capabilities.backend_name,
            backend_kind=capabilities.backend_kind,
            source=selected,
            width=width,
            height=height,
            pixel_format=pixel_format,
        )
        return FrameCaptureResult(
            succeeded=True,
            message="One-frame still proof captured; no video recording, encoding, preview, or hotkey was started.",
            backend_name=capabilities.backend_name,
            backend_kind=capabilities.backend_kind,
            source=selected,
            timestamp=timestamp,
            width=width,
            height=height,
            pixel_format=pixel_format,
            artifact_path=artifact_path,
            warnings=(
                "still-frame proof only; not video recording",
                "capture proof is not runtime readiness",
                *selected.warnings,
            ),
            errors=artifact_errors,
            truth_label="Real still-frame proof",
            real_capture=True,
            simulated_capture=False,
        )

    def create_simulated_artifact(
        self,
        *,
        settings: FlightRecorderSettings,
        telemetry_samples: tuple[OverlayTelemetrySample, ...],
        now: float,
        created_at: str | None = None,
    ) -> CaptureBackendResult:
        return CaptureBackendResult(
            succeeded=False,
            message="Simulated artifact export is not provided by the Qt capture candidate.",
        )

    def _one_frame_context_available(self) -> bool:
        return bool(self._dependency_available and not _qt_offscreen_context() and _qt_app_available())


def _sample_to_dict(sample: OverlayTelemetrySample) -> dict[str, object]:
    return {
        "timestamp": sample.timestamp,
        "source": sample.source,
        "axes": dict(sample.axes),
    }


def _slug(value: str) -> str:
    safe = "".join(character for character in value if character.isalnum())
    return safe or "now"


def _timestamp(now: float | None) -> float:
    return time() if now is None else float(now)


def _unavailable_frame_result(
    *,
    capabilities: CaptureBackendCapabilities,
    source: CaptureDisplaySource,
    timestamp: float,
    message: str,
    truth_label: str,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
    simulated_capture: bool = False,
) -> FrameCaptureResult:
    return FrameCaptureResult(
        succeeded=False,
        message=message,
        backend_name=capabilities.backend_name,
        backend_kind=capabilities.backend_kind,
        source=source,
        timestamp=timestamp,
        width=None,
        height=None,
        pixel_format="unavailable",
        artifact_path=None,
        warnings=_dedupe((*capabilities.warnings, *warnings)),
        errors=_dedupe((*capabilities.errors, *errors)),
        truth_label=truth_label,
        real_capture=False,
        simulated_capture=simulated_capture,
    )


def _default_display_source(
    *,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> CaptureDisplaySource:
    return CaptureDisplaySource(
        display_id="current",
        display_label="Current display",
        geometry=None,
        is_primary=None,
        capture_source="current display",
        warnings=warnings,
        errors=errors,
    )


def _qt_dependency_available() -> bool:
    try:
        import PySide6.QtGui  # noqa: F401
    except Exception:
        return False
    return True


def _qt_app_available() -> bool:
    try:
        from PySide6.QtGui import QGuiApplication
    except Exception:
        return False
    return QGuiApplication.instance() is not None


def _qt_offscreen_context() -> bool:
    try:
        from PySide6.QtGui import QGuiApplication
    except Exception:
        return True
    app = QGuiApplication.instance()
    if app is None:
        return True
    try:
        return str(QGuiApplication.platformName()).casefold() == "offscreen"
    except Exception:
        return True


def _qt_screen_for_source(source: CaptureDisplaySource):
    try:
        from PySide6.QtGui import QGuiApplication
    except Exception:
        return None
    app = QGuiApplication.instance()
    if app is None:
        return None
    screens = list(app.screens())
    if not screens:
        return None
    if source.is_primary:
        return app.primaryScreen() or screens[0]
    try:
        index = int(source.display_id) - 1
    except ValueError:
        index = -1
    if 0 <= index < len(screens):
        return screens[index]
    return app.primaryScreen() or screens[0]


def _qt_pixel_format_label(pixmap) -> str:
    try:
        image_format = pixmap.toImage().format()
        return getattr(image_format, "name", str(image_format))
    except Exception:
        return "unknown"


def _write_one_frame_metadata_artifact(
    *,
    artifact_folder: Path | None,
    timestamp: float,
    backend_name: str,
    backend_kind: str,
    source: CaptureDisplaySource,
    width: int,
    height: int,
    pixel_format: str,
) -> tuple[Path | None, tuple[str, ...]]:
    if artifact_folder is None:
        return None, ()
    try:
        destination = Path(artifact_folder)
        destination.mkdir(parents=True, exist_ok=True)
        created = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        filename = f"one_frame_capture_proof_{_slug(created)}.json"
        path = _available_path(destination / filename)
        payload = {
            "truth": "Still-frame proof metadata; not video recording; not encoded; not previewable video.",
            "proof": {
                "backend_name": backend_name,
                "backend_kind": backend_kind,
                "display_id": source.display_id,
                "display_label": source.display_label,
                "capture_source": source.capture_source,
                "timestamp": timestamp,
                "created_at": created,
                "width": width,
                "height": height,
                "pixel_format": pixel_format,
                "real_capture": True,
                "simulated_capture": False,
            },
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path, ()
    except OSError as exc:
        return None, (f"Still-frame proof metadata artifact could not be saved: {exc}",)


def _available_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"No available one-frame proof filename for {path}")


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
