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
    desktop_capture_available: bool
    frame_capture_available: bool
    cursor_capture_available: bool
    video_encoding_available: bool
    simulated_artifact_available: bool
    backend_name: str
    backend_kind: str


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


class CaptureBackend(Protocol):
    def capabilities(self) -> CaptureBackendCapabilities:
        ...

    def refresh_status(self) -> CaptureBackendStatus:
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
            desktop_capture_available=False,
            frame_capture_available=False,
            cursor_capture_available=False,
            video_encoding_available=False,
            simulated_artifact_available=False,
            backend_name="missing_capture_backend",
            backend_kind="missing",
        )

    def refresh_status(self) -> CaptureBackendStatus:
        return CaptureBackendStatus(
            capabilities=self.capabilities(),
            status="capture_backend_missing",
            message="Capture backend missing; recording unavailable.",
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
            desktop_capture_available=False,
            frame_capture_available=False,
            cursor_capture_available=False,
            video_encoding_available=False,
            simulated_artifact_available=True,
            backend_name=self.backend_name,
            backend_kind="simulated",
        )

    def refresh_status(self) -> CaptureBackendStatus:
        return CaptureBackendStatus(
            capabilities=self.capabilities(),
            status="simulated_backend",
            message="Simulated backend available for non-video recorder artifacts only.",
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


def _sample_to_dict(sample: OverlayTelemetrySample) -> dict[str, object]:
    return {
        "timestamp": sample.timestamp,
        "source": sample.source,
        "axes": dict(sample.axes),
    }


def _slug(value: str) -> str:
    safe = "".join(character for character in value if character.isalnum())
    return safe or "now"
