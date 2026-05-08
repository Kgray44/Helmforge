from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
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


class CaptureBackend(Protocol):
    def capabilities(self) -> CaptureBackendCapabilities:
        ...

    def refresh_status(self) -> CaptureBackendStatus:
        ...

    def display_sources(self) -> tuple[CaptureDisplaySource, ...]:
        ...

    def capture_frame(self, *, source: CaptureDisplaySource | None = None) -> CaptureFrameResult:
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
            warnings=(
                dependency_note,
                "Post-RC 3A candidate seam only; frame capture is not implemented.",
                "No video recording, encoding, hotkey registration, game injection, or graphics hooking is active.",
            ),
            errors=errors,
        )

    def refresh_status(self) -> CaptureBackendStatus:
        capabilities = self.capabilities()
        if capabilities.dependency_available:
            message = "Qt capture candidate available as a design seam; real frame capture is not implemented in Post-RC 3A."
        else:
            message = "Qt capture candidate unavailable; dependency is not available and no capture is active."
        return CaptureBackendStatus(
            capabilities=capabilities,
            status="candidate_unavailable",
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
                    warnings=("Capture candidate only; frame buffering begins in a later phase.",),
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


def _sample_to_dict(sample: OverlayTelemetrySample) -> dict[str, object]:
    return {
        "timestamp": sample.timestamp,
        "source": sample.source,
        "axes": dict(sample.axes),
    }


def _slug(value: str) -> str:
    safe = "".join(character for character in value if character.isalnum())
    return safe or "now"


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
