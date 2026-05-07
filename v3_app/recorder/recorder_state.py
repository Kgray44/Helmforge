from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RecorderStatus(str, Enum):
    IDLE = "idle"
    READY = "ready"
    RECORDING_FORWARD_UNAVAILABLE = "recording_forward_unavailable"
    BUFFERING_UNAVAILABLE = "buffering_unavailable"
    SAVING_UNAVAILABLE = "saving_unavailable"
    CAPTURE_BACKEND_MISSING = "capture_backend_missing"
    COMPOSITOR_UNAVAILABLE = "compositor_unavailable"
    ERROR = "error"


_STATUS_LABELS = {
    RecorderStatus.IDLE: "UI Ready",
    RecorderStatus.READY: "UI Ready",
    RecorderStatus.RECORDING_FORWARD_UNAVAILABLE: "Recording unavailable",
    RecorderStatus.BUFFERING_UNAVAILABLE: "Buffering unavailable",
    RecorderStatus.SAVING_UNAVAILABLE: "Saving unavailable",
    RecorderStatus.CAPTURE_BACKEND_MISSING: "Capture backend missing",
    RecorderStatus.COMPOSITOR_UNAVAILABLE: "Compositor unavailable",
    RecorderStatus.ERROR: "Recorder error",
}


@dataclass(frozen=True)
class RecorderState:
    status: RecorderStatus
    message: str
    can_record: bool
    can_save_last_clip: bool

    @classmethod
    def default(cls) -> "RecorderState":
        return cls(
            status=RecorderStatus.CAPTURE_BACKEND_MISSING,
            message="Capture/export backend is not active yet.",
            can_record=False,
            can_save_last_clip=False,
        )

    @property
    def status_label(self) -> str:
        return _STATUS_LABELS[self.status]
