from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from v3_app.overlay.overlay_config import LiveOverlayConfig
from v3_app.overlay.telemetry_buffer import OverlayTelemetrySample
from v3_app.overlay.trace_builder import build_overlay_traces
from v3_app.recorder.hindsight_buffer import RecorderFrameReference
from v3_app.recorder.recorder_artifacts import RecorderExportMetadata
from v3_app.recorder.recorder_settings import FlightRecorderSettings


@dataclass(frozen=True)
class RecorderCompositorCapabilities:
    real_video_compositing_available: bool
    simulated_export_available: bool
    overlay_trace_rendering_available: bool
    supports_preview_metadata: bool
    backend_name: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecorderCompositorStatus:
    capabilities: RecorderCompositorCapabilities
    status: str
    message: str


@dataclass(frozen=True)
class SimulatedExportResult:
    succeeded: bool
    message: str
    metadata: RecorderExportMetadata | None = None


@dataclass(frozen=True)
class RecorderOverlayCompositionPlan:
    status: str
    frame_count: int
    telemetry_sample_count: int
    include_overlay: bool
    can_burn_overlay: bool
    truth_label: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "frame_count": self.frame_count,
            "telemetry_sample_count": self.telemetry_sample_count,
            "include_overlay": self.include_overlay,
            "can_burn_overlay": self.can_burn_overlay,
            "truth_label": self.truth_label,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


class RecorderCompositor(Protocol):
    def capabilities(self) -> RecorderCompositorCapabilities:
        ...

    def refresh_status(self) -> RecorderCompositorStatus:
        ...

    def create_simulated_export(
        self,
        *,
        settings: FlightRecorderSettings,
        telemetry_samples: tuple[OverlayTelemetrySample, ...],
        capture_backend_name: str,
        now: float,
        created_at: str | None = None,
    ) -> SimulatedExportResult:
        ...


class MissingRecorderCompositor:
    def capabilities(self) -> RecorderCompositorCapabilities:
        return RecorderCompositorCapabilities(
            real_video_compositing_available=False,
            simulated_export_available=False,
            overlay_trace_rendering_available=False,
            supports_preview_metadata=False,
            backend_name="missing_compositor",
            warnings=("Compositor unavailable",),
        )

    def refresh_status(self) -> RecorderCompositorStatus:
        return RecorderCompositorStatus(
            capabilities=self.capabilities(),
            status="compositor_unavailable",
            message="Compositor unavailable; simulated export unavailable.",
        )

    def create_simulated_export(
        self,
        *,
        settings: FlightRecorderSettings,
        telemetry_samples: tuple[OverlayTelemetrySample, ...],
        capture_backend_name: str,
        now: float,
        created_at: str | None = None,
    ) -> SimulatedExportResult:
        return SimulatedExportResult(False, "Compositor unavailable; simulated export unavailable.")


class SimulatedRecorderCompositor:
    def __init__(self, *, backend_name: str = "simulated_compositor") -> None:
        self.backend_name = backend_name

    def capabilities(self) -> RecorderCompositorCapabilities:
        return RecorderCompositorCapabilities(
            real_video_compositing_available=False,
            simulated_export_available=True,
            overlay_trace_rendering_available=True,
            supports_preview_metadata=True,
            backend_name=self.backend_name,
            warnings=("Simulated export only; no real video compositing.",),
        )

    def refresh_status(self) -> RecorderCompositorStatus:
        return RecorderCompositorStatus(
            capabilities=self.capabilities(),
            status="simulated_compositor",
            message="Simulated compositor available for metadata and overlay trace export only.",
        )

    def create_simulated_export(
        self,
        *,
        settings: FlightRecorderSettings,
        telemetry_samples: tuple[OverlayTelemetrySample, ...],
        capture_backend_name: str,
        now: float,
        created_at: str | None = None,
    ) -> SimulatedExportResult:
        created = created_at or datetime.fromtimestamp(float(now), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        export_id = f"simulated-export-{_slug(created)}"
        export_dir = Path(settings.destination_folder) / f"simulated_export_{_slug(created)}"
        export_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = export_dir / "manifest.json"
        trace_path = export_dir / "overlay_trace.json"
        summary_path = export_dir / "summary.md"
        preview_path = export_dir / "preview_metadata.json"

        overlay_config = _overlay_config_from_settings(settings)
        traces = build_overlay_traces(overlay_config, telemetry_samples)
        included_axes = tuple(series.axis for series in traces.series)
        metadata = RecorderExportMetadata(
            export_id=export_id,
            clip_id=export_id,
            created_at=created,
            artifact_kind="simulated_export",
            path=export_dir,
            manifest_path=manifest_path,
            duration_seconds=float(settings.length_seconds),
            frame_rate=int(settings.frame_rate_fps),
            overlay_source=settings.overlay_source,
            capture_source=settings.capture_source,
            display_label=settings.display_label,
            telemetry_sample_count=len(telemetry_samples),
            included_axes=included_axes,
            is_simulated=True,
            has_video=False,
            has_real_capture=False,
            has_overlay_trace=bool(traces.series),
            compositor_backend=self.backend_name,
            capture_backend=capture_backend_name,
            warnings=(
                "not real desktop capture",
                "no screen frames captured",
                "no video encoding performed",
                "output verified: false",
                "Full Live Runtime Ready: false",
            ),
            display_name="Simulated export",
            opened=False,
        )
        trace_payload = {
            "source": traces.source,
            "history_seconds": traces.history_seconds,
            "sample_count": len(telemetry_samples),
            "series": [
                {"axis": series.axis, "color": series.color, "points": list(series.points)}
                for series in traces.series
            ],
        }
        manifest = {
            "truth": (
                "Simulated recorder export; not real desktop capture; no screen frames captured; "
                "no video encoding performed; overlay trace data generated from telemetry samples; "
                "no vJoy/output verification; no Full Live Runtime Ready claim."
            ),
            "runtime_truth": "Runtime truth: blocked_missing_device; Output verified: false; Full Live Runtime Ready: false.",
            "export": metadata.to_dict(),
            "files": {
                "overlay_trace": str(trace_path),
                "summary": str(summary_path),
                "preview_metadata": str(preview_path),
            },
        }
        preview = {
            "title": "Simulated export",
            "has_video": False,
            "preview": "metadata only",
            "telemetry_sample_count": len(telemetry_samples),
            "included_axes": list(included_axes),
            "overlay_source": settings.overlay_source,
        }
        summary = "\n".join(
            (
                "# Simulated Recorder Export",
                "",
                "This is a simulated recorder export, not a desktop recording.",
                "",
                "- No screen frames captured.",
                "- No video encoding performed.",
                "- Overlay trace data was generated from telemetry samples.",
                "- Output verified: false.",
                "- Full Live Runtime Ready: false.",
            )
        )
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        trace_path.write_text(json.dumps(trace_payload, indent=2, sort_keys=True), encoding="utf-8")
        preview_path.write_text(json.dumps(preview, indent=2, sort_keys=True), encoding="utf-8")
        summary_path.write_text(summary, encoding="utf-8")
        return SimulatedExportResult(
            succeeded=True,
            message="Simulated export created; no video was captured or encoded.",
            metadata=metadata,
        )


def build_overlay_composition_plan(
    *,
    frames: tuple[RecorderFrameReference, ...],
    telemetry_samples: tuple[OverlayTelemetrySample, ...],
    include_overlay: bool,
    can_burn_overlay: bool,
) -> RecorderOverlayCompositionPlan:
    if not include_overlay:
        return RecorderOverlayCompositionPlan(
            status="not_applicable",
            frame_count=len(frames),
            telemetry_sample_count=0,
            include_overlay=False,
            can_burn_overlay=can_burn_overlay,
            truth_label="Overlay burn-in not requested.",
        )
    if not frames:
        return RecorderOverlayCompositionPlan(
            status="unavailable",
            frame_count=0,
            telemetry_sample_count=0,
            include_overlay=True,
            can_burn_overlay=can_burn_overlay,
            truth_label="Overlay unavailable; no frames are available.",
            errors=("No frame source exists for overlay composition.",),
        )
    if not can_burn_overlay:
        return RecorderOverlayCompositionPlan(
            status="not_applicable",
            frame_count=len(frames),
            telemetry_sample_count=0,
            include_overlay=True,
            can_burn_overlay=False,
            truth_label="Overlay burn-in unavailable for selected encoder.",
            warnings=("Encoder cannot burn overlay; telemetry metadata can still be stored.",),
        )
    oldest = frames[0].timestamp
    newest = frames[-1].timestamp
    aligned = tuple(sample for sample in telemetry_samples if oldest <= sample.timestamp <= newest)
    return RecorderOverlayCompositionPlan(
        status="ready" if aligned else "metadata_only",
        frame_count=len(frames),
        telemetry_sample_count=len(aligned),
        include_overlay=True,
        can_burn_overlay=True,
        truth_label=(
            "Overlay telemetry aligned to frame interval."
            if aligned
            else "Overlay requested, but no telemetry samples aligned to the frame interval."
        ),
        warnings=() if aligned else ("No telemetry samples were available for overlay burn-in.",),
    )


def _overlay_config_from_settings(settings: FlightRecorderSettings) -> LiveOverlayConfig:
    defaults = LiveOverlayConfig.defaults()
    return LiveOverlayConfig(
        preset=defaults.preset,
        visible=False,
        source=settings.overlay_source,
        history_seconds=settings.history_seconds,
        position=defaults.position,
        margin_px=defaults.margin_px,
        attach_mode=defaults.attach_mode,
        width=defaults.width,
        height=defaults.height,
        display_label=settings.display_label,
        opacity=defaults.opacity,
        background=defaults.background,
        line_thickness=defaults.line_thickness,
        show_legend=defaults.show_legend,
        show_live_values=defaults.show_live_values,
        auto_hide_when_target_loses_focus=defaults.auto_hide_when_target_loses_focus,
        always_on_top=defaults.always_on_top,
        click_through=defaults.click_through,
        click_through_supported=defaults.click_through_supported,
        fps_cap=defaults.fps_cap,
        toggle_hotkey=defaults.toggle_hotkey,
        hotkey_registered=False,
        axes=settings.axes,
    )


def _slug(value: str) -> str:
    safe = "".join(character for character in value if character.isalnum())
    return safe or "now"
