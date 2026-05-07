from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from v3_app.recorder.recorder_artifacts import (
    RecorderArtifact,
    RecorderExportMetadata,
    artifact_from_manifest,
    export_metadata_from_manifest,
)


@dataclass(frozen=True)
class ClipMetadata:
    path: Path
    clip: str
    recorded: str = "Unavailable"
    duration: str = "Unavailable"
    opened: str = "Not opened"
    overlay_source: str = "Final output"
    resolution: str = "Unavailable"
    length: str = "Unavailable"
    is_simulated: bool = False
    has_video: bool = False
    telemetry_sample_count: int = 0
    artifact_kind: str = "unknown"
    display_name: str = ""
    manifest_path: Path | None = None
    export_metadata: RecorderExportMetadata | None = None

    @classmethod
    def from_path(cls, path: Path) -> "ClipMetadata":
        return cls(path=Path(path), clip=Path(path).name)

    @classmethod
    def from_artifact(cls, artifact: RecorderArtifact, *, telemetry_sample_count: int = 0) -> "ClipMetadata":
        return cls(
            path=artifact.path,
            clip=f"{artifact.filename} (Simulated artifact)" if artifact.is_simulated else artifact.filename,
            recorded=artifact.created_at or "Unavailable",
            duration=f"{artifact.duration_seconds:.0f} s" if artifact.duration_seconds else "Unavailable",
            opened="Metadata only" if artifact.is_simulated else "Not opened",
            overlay_source=artifact.overlay_source,
            resolution="No video" if not artifact.has_video else "Unavailable",
            length=f"{artifact.duration_seconds:.2f} s" if artifact.duration_seconds else "Unavailable",
            is_simulated=artifact.is_simulated,
            has_video=artifact.has_video,
            telemetry_sample_count=telemetry_sample_count,
            artifact_kind=artifact.status,
            display_name="Simulated artifact" if artifact.is_simulated else artifact.filename,
            manifest_path=artifact.path,
        )

    @classmethod
    def from_export(cls, export: RecorderExportMetadata) -> "ClipMetadata":
        return cls(
            path=export.path,
            clip=f"{export.display_name}: {export.path.name} (Simulated export / No video / Metadata only)",
            recorded=export.created_at or "Unavailable",
            duration=f"{export.duration_seconds:.0f} s" if export.duration_seconds else "Unavailable",
            opened="Metadata only",
            overlay_source=export.overlay_source,
            resolution="No video",
            length=f"{export.duration_seconds:.2f} s" if export.duration_seconds else "Unavailable",
            is_simulated=export.is_simulated,
            has_video=export.has_video,
            telemetry_sample_count=export.telemetry_sample_count,
            artifact_kind=export.artifact_kind,
            display_name=export.display_name,
            manifest_path=export.manifest_path,
            export_metadata=export,
        )


class ClipLibrary:
    def __init__(self, destination_folder: Path) -> None:
        self.destination_folder = Path(destination_folder)

    @property
    def empty_state_title(self) -> str:
        return "No recorder artifacts yet."

    @property
    def empty_state_detail(self) -> str:
        return "Simulated exports will appear here as metadata-only artifacts. Real capture and encoding are not active."

    def scan(self) -> tuple[ClipMetadata, ...]:
        if not self.destination_folder.exists():
            return ()
        clips: list[ClipMetadata] = []
        for path in sorted(self.destination_folder.glob("simulated*_*.json"), key=lambda item: item.name.lower()):
            if not path.is_file():
                continue
            artifact = artifact_from_manifest(path)
            if artifact is None:
                continue
            clips.append(ClipMetadata.from_artifact(artifact, telemetry_sample_count=_telemetry_count(path)))
        for manifest in sorted(
            self.destination_folder.glob("simulated_export_*/manifest.json"),
            key=lambda item: item.parent.name.lower(),
        ):
            export = export_metadata_from_manifest(manifest)
            if export is None:
                continue
            clips.append(ClipMetadata.from_export(export))
        return tuple(sorted(clips, key=lambda clip: clip.recorded, reverse=True))


def _telemetry_count(path: Path) -> int:
    try:
        import json

        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        telemetry = payload.get("telemetry") if isinstance(payload, dict) else None
        sample_count = telemetry.get("sample_count") if isinstance(telemetry, dict) else 0
        return int(sample_count or 0)
    except (OSError, ValueError, TypeError):
        return 0
