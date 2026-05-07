from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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

    @classmethod
    def from_path(cls, path: Path) -> "ClipMetadata":
        return cls(path=Path(path), clip=Path(path).name)


class ClipLibrary:
    def __init__(self, destination_folder: Path) -> None:
        self.destination_folder = Path(destination_folder)

    @property
    def empty_state_title(self) -> str:
        return "No clips recorded yet."

    @property
    def empty_state_detail(self) -> str:
        return "Recording backend is not active in this phase."

    def scan(self) -> tuple[ClipMetadata, ...]:
        if not self.destination_folder.exists():
            return ()
        clips = [
            ClipMetadata.from_path(path)
            for path in sorted(self.destination_folder.glob("*.mp4"), key=lambda item: item.name.lower())
            if path.is_file()
        ]
        return tuple(reversed(clips))
