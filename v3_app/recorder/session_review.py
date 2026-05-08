from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from shared_core.models.runtime import AXIS_NAMES, RuntimePreflightStatus, RuntimeTruth
from v3_app.overlay.telemetry_buffer import OverlayTelemetrySample
from v3_app.recorder.recorder_artifacts import RecorderArtifact, RecorderExportMetadata
from v3_app.recorder.recorder_settings import FlightRecorderSettings


@dataclass(frozen=True)
class RecorderTimelineEvent:
    timestamp: float
    relative_seconds: float
    channel: str
    event_type: str
    previous_value: float
    value: float
    description: str

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "relative_seconds": self.relative_seconds,
            "channel": self.channel,
            "event_type": self.event_type,
            "previous_value": self.previous_value,
            "value": self.value,
            "description": self.description,
        }


@dataclass(frozen=True)
class RecorderReviewSession:
    session_id: str
    source_type: str
    truth_label: str
    start_timestamp: float
    end_timestamp: float
    duration_seconds: float
    sample_count: int
    event_count: int
    axis_channels: tuple[str, ...]
    button_channels: tuple[str, ...]
    hat_channels: tuple[str, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    capture_mode: str
    capture_source: str
    display_label: str
    runtime_truth_snapshot: dict[str, object]
    timeline_events: tuple[RecorderTimelineEvent, ...]
    samples: tuple[OverlayTelemetrySample, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "source_type": self.source_type,
            "truth_label": self.truth_label,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "duration_seconds": self.duration_seconds,
            "sample_count": self.sample_count,
            "event_count": self.event_count,
            "axis_channels": list(self.axis_channels),
            "button_channels": list(self.button_channels),
            "hat_channels": list(self.hat_channels),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "capture_mode": self.capture_mode,
            "capture_source": self.capture_source,
            "display_label": self.display_label,
            "runtime_truth_snapshot": dict(self.runtime_truth_snapshot),
            "timeline_events": [event.to_dict() for event in self.timeline_events],
        }


@dataclass(frozen=True)
class RecorderReviewExportResult:
    succeeded: bool
    message: str
    path: Path | None = None


def build_recorder_session_review(
    *,
    settings: FlightRecorderSettings,
    telemetry_samples: tuple[OverlayTelemetrySample, ...],
    runtime_status: RuntimePreflightStatus,
    source_type: str = "workspace",
    capture_mode: str = "immediate",
    artifact: RecorderArtifact | None = None,
    export_metadata: RecorderExportMetadata | None = None,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> RecorderReviewSession | None:
    samples = tuple(sorted(telemetry_samples, key=lambda sample: sample.timestamp))
    if not samples and artifact is None and export_metadata is None:
        return None

    inferred_source = _source_type(source_type, artifact=artifact, export_metadata=export_metadata, samples=samples, runtime_status=runtime_status)
    start = samples[0].timestamp if samples else 0.0
    end = samples[-1].timestamp if samples else start
    duration = max(0.0, end - start)
    events = _timeline_events(samples)
    axis_channels = _axis_channels(samples)
    all_warnings = _dedupe((*warnings, *_artifact_warnings(artifact, export_metadata), *_truth_warnings(inferred_source, runtime_status)))
    all_errors = _dedupe(errors)
    session_id = f"recorder-session-{_slug(inferred_source)}-{_slug(f'{start:.3f}-{end:.3f}')}"
    return RecorderReviewSession(
        session_id=session_id,
        source_type=inferred_source,
        truth_label=_truth_label(inferred_source, runtime_status),
        start_timestamp=start,
        end_timestamp=end,
        duration_seconds=round(duration, 3),
        sample_count=len(samples),
        event_count=len(events),
        axis_channels=axis_channels,
        button_channels=(),
        hat_channels=(),
        warnings=all_warnings,
        errors=all_errors,
        capture_mode=capture_mode,
        capture_source=settings.capture_source,
        display_label=settings.display_label,
        runtime_truth_snapshot=_runtime_truth_snapshot(runtime_status),
        timeline_events=events,
        samples=samples,
    )


def export_session_summary_json(session: RecorderReviewSession, destination_folder: Path) -> RecorderReviewExportResult:
    destination = Path(destination_folder)
    destination.mkdir(parents=True, exist_ok=True)
    path = _available_path(destination / f"{session.session_id}_summary.json")
    payload = {
        "truth": "Recorder review export; local deterministic summary; not real capture proof.",
        "session": session.to_dict(),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return RecorderReviewExportResult(True, "Recorder review summary exported as local JSON.", path)


def export_session_samples_csv(session: RecorderReviewSession, destination_folder: Path) -> RecorderReviewExportResult:
    destination = Path(destination_folder)
    destination.mkdir(parents=True, exist_ok=True)
    path = _available_path(destination / f"{session.session_id}_samples.csv")
    fieldnames = (
        "sample_index",
        "timestamp",
        "relative_seconds",
        "source",
        "source_type",
        "runtime_truth",
        *AXIS_NAMES,
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        start = session.start_timestamp
        for index, sample in enumerate(session.samples):
            row: dict[str, object] = {
                "sample_index": index,
                "timestamp": f"{sample.timestamp:.6f}",
                "relative_seconds": f"{sample.timestamp - start:.6f}",
                "source": sample.source,
                "source_type": session.source_type,
                "runtime_truth": session.runtime_truth_snapshot["truth"],
            }
            for axis in AXIS_NAMES:
                row[axis] = f"{_axis_value(sample.axes, axis):.6f}"
            writer.writerow(row)
    return RecorderReviewExportResult(True, "Recorder review samples exported as local CSV.", path)


def _timeline_events(samples: tuple[OverlayTelemetrySample, ...]) -> tuple[RecorderTimelineEvent, ...]:
    if len(samples) < 2:
        return ()
    start = samples[0].timestamp
    previous_axes: dict[str, float] = {axis: _axis_value(samples[0].axes, axis) for axis in AXIS_NAMES}
    events: list[RecorderTimelineEvent] = []
    for sample in samples[1:]:
        for channel in _ordered_sample_channels(sample.axes, previous_axes):
            previous = previous_axes.get(channel, 0.0)
            current = _axis_value(sample.axes, channel)
            if abs(current - previous) <= 0.000001:
                continue
            relative = round(sample.timestamp - start, 3)
            events.append(
                RecorderTimelineEvent(
                    timestamp=sample.timestamp,
                    relative_seconds=relative,
                    channel=channel,
                    event_type="axis_change",
                    previous_value=previous,
                    value=current,
                    description=f"{channel} changed from {previous:.3f} to {current:.3f} at +{relative:.2f}s",
                )
            )
            previous_axes[channel] = current
    return tuple(events)


def _ordered_sample_channels(axes: Mapping[str, float], previous_axes: Mapping[str, float]) -> tuple[str, ...]:
    channels: list[str] = []
    for channel in axes:
        if channel in AXIS_NAMES and channel not in channels:
            channels.append(channel)
    for channel in AXIS_NAMES:
        if channel in previous_axes and channel not in channels:
            channels.append(channel)
    return tuple(channels)


def _axis_channels(samples: tuple[OverlayTelemetrySample, ...]) -> tuple[str, ...]:
    active: set[str] = set()
    for sample in samples:
        for axis in AXIS_NAMES:
            if abs(_axis_value(sample.axes, axis)) > 0.000001:
                active.add(axis)
    return tuple(axis for axis in AXIS_NAMES if axis in active)


def _axis_value(axes: Mapping[str, float], axis: str) -> float:
    try:
        return float(axes.get(axis, 0.0))
    except (TypeError, ValueError):
        return 0.0


def _runtime_truth_snapshot(runtime_status: RuntimePreflightStatus) -> dict[str, object]:
    output_verified = bool(runtime_status.live_output_writes_verified)
    truth = runtime_status.truth.value
    return {
        "mode": runtime_status.mode.value,
        "truth": truth,
        "output_verified": output_verified,
        "full_live_runtime_ready": bool(output_verified and runtime_status.truth is RuntimeTruth.LIVE_VERIFIED),
        "input_status": runtime_status.input.status.value,
        "output_status": runtime_status.output.status.value,
    }


def _source_type(
    requested: str,
    *,
    artifact: RecorderArtifact | None,
    export_metadata: RecorderExportMetadata | None,
    samples: tuple[OverlayTelemetrySample, ...],
    runtime_status: RuntimePreflightStatus,
) -> str:
    normalized = requested.strip().casefold().replace("_", " ") or "workspace"
    if export_metadata is not None and export_metadata.is_simulated:
        return "simulated"
    if artifact is not None and artifact.is_simulated:
        return "simulated"
    sample_sources = " ".join(sample.source for sample in samples).casefold()
    if "demo" in normalized or "demo" in sample_sources:
        return "demo"
    if "bridge" in normalized or "bridge" in sample_sources:
        return "Bridge telemetry"
    if normalized == "live" and runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and runtime_status.live_output_writes_verified:
        return "live"
    if normalized in {"simulated", "workspace"}:
        return normalized
    return "workspace"


def _truth_label(source_type: str, runtime_status: RuntimePreflightStatus) -> str:
    if source_type == "live" and runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and runtime_status.live_output_writes_verified:
        return "Live verified"
    if source_type == "Bridge telemetry":
        return "Bridge Telemetry Review"
    return "Simulated/Workspace Only"


def _truth_warnings(source_type: str, runtime_status: RuntimePreflightStatus) -> tuple[str, ...]:
    warnings: list[str] = []
    if source_type != "live":
        warnings.append("Simulated/workspace review only; not real capture proof.")
    if not runtime_status.live_output_writes_verified:
        warnings.append("Output verified: false.")
    if runtime_status.truth is not RuntimeTruth.LIVE_VERIFIED:
        warnings.append(f"Runtime truth: {runtime_status.truth.value}.")
    return tuple(warnings)


def _artifact_warnings(
    artifact: RecorderArtifact | None, export_metadata: RecorderExportMetadata | None
) -> tuple[str, ...]:
    warnings: list[str] = []
    if artifact is not None:
        warnings.extend(artifact.warnings)
    if export_metadata is not None:
        warnings.extend(export_metadata.warnings)
    return tuple(warnings)


def _available_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"No available export filename for {path}")


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


def _slug(value: str) -> str:
    safe = "".join(character if character.isalnum() else "-" for character in value)
    return "-".join(part for part in safe.split("-") if part) or "session"
