from __future__ import annotations


LIVE_TRACE_SAMPLE_RATE_HZ = 60
LIVE_REFRESH_INTERVAL_MS = 16
LIVE_TRACE_HISTORY_SECONDS = 7.0


def samples_for_history(*, history_seconds: float = LIVE_TRACE_HISTORY_SECONDS, sample_rate_hz: int = LIVE_TRACE_SAMPLE_RATE_HZ) -> int:
    return max(1, int(round(float(history_seconds) * int(sample_rate_hz))))
