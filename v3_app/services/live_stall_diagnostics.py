from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class UiStallSnapshot:
    last_ui_frame_delta_ms: float | None
    ui_stall_count: int
    last_ui_stall_duration_ms: float | None
    last_ui_stall_at: datetime | None
    threshold_ms: float
    live_frame_gap_count: int
    last_live_frame_gap_ms: float | None
    max_live_frame_gap_ms: float | None


class UiStallMonitor:
    def __init__(self, *, threshold_ms: float = 250.0, clock=None) -> None:
        self.threshold_ms = max(1.0, float(threshold_ms))
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._last_tick_at: datetime | None = None
        self.last_ui_frame_delta_ms: float | None = None
        self.ui_stall_count = 0
        self.last_ui_stall_duration_ms: float | None = None
        self.last_ui_stall_at: datetime | None = None
        self.max_live_frame_gap_ms: float | None = None

    def observe(self) -> UiStallSnapshot:
        now = _aware(self._clock())
        if self._last_tick_at is not None:
            delta_ms = max(0.0, (now - self._last_tick_at).total_seconds() * 1000.0)
            self.last_ui_frame_delta_ms = delta_ms
            if delta_ms > self.threshold_ms:
                self.ui_stall_count += 1
                self.last_ui_stall_duration_ms = delta_ms
                self.last_ui_stall_at = now
                self.max_live_frame_gap_ms = (
                    delta_ms
                    if self.max_live_frame_gap_ms is None
                    else max(self.max_live_frame_gap_ms, delta_ms)
                )
        self._last_tick_at = now
        return self.snapshot()

    def snapshot(self) -> UiStallSnapshot:
        return UiStallSnapshot(
            last_ui_frame_delta_ms=self.last_ui_frame_delta_ms,
            ui_stall_count=self.ui_stall_count,
            last_ui_stall_duration_ms=self.last_ui_stall_duration_ms,
            last_ui_stall_at=self.last_ui_stall_at,
            threshold_ms=self.threshold_ms,
            live_frame_gap_count=self.ui_stall_count,
            last_live_frame_gap_ms=self.last_ui_stall_duration_ms,
            max_live_frame_gap_ms=self.max_live_frame_gap_ms,
        )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
