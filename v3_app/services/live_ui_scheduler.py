from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Mapping


Clock = Callable[[], float]


class MonotonicClock:
    def __call__(self) -> float:
        return time.monotonic()


@dataclass(frozen=True)
class CadenceTarget:
    rate_hz: float

    @property
    def interval_seconds(self) -> float:
        return 1.0 / max(0.001, float(self.rate_hz))


DEFAULT_LIVE_UI_CADENCES: Mapping[str, CadenceTarget] = {
    "shell_chrome": CadenceTarget(10.0),
    "telemetry_embedded": CadenceTarget(120.0),
    "telemetry_stream": CadenceTarget(120.0),
    "telemetry_json": CadenceTarget(5.0),
    "values": CadenceTarget(30.0),
    "buttons_hats": CadenceTarget(30.0),
    "graphs": CadenceTarget(30.0),
    "live_monitor_visual_render": CadenceTarget(60.0),
    "diagnostics": CadenceTarget(4.0),
    "overlay_trace_build": CadenceTarget(24.0),
    "overlay_paint": CadenceTarget(30.0),
    "effective_stack_compute": CadenceTarget(18.0),
    "effective_stack_static_graph": CadenceTarget(1.0),
    "effective_stack_marker": CadenceTarget(30.0),
    "tuning_live_marker": CadenceTarget(30.0),
    "tuning_snapshot_text": CadenceTarget(12.0),
}


class CadenceGate:
    def __init__(
        self,
        *,
        interval_seconds: float | None = None,
        rate_hz: float | None = None,
    ) -> None:
        if interval_seconds is None:
            if rate_hz is None:
                raise ValueError("CadenceGate requires interval_seconds or rate_hz")
            interval_seconds = 1.0 / max(0.001, float(rate_hz))
        self.interval_seconds = max(0.0, float(interval_seconds))
        self._last_marked_at: float | None = None
        self._forced = True

    def due(self, now: float) -> bool:
        if self._forced or self._last_marked_at is None:
            return True
        return (float(now) - self._last_marked_at) >= (self.interval_seconds - 1e-9)

    def mark(self, now: float) -> None:
        self._last_marked_at = float(now)
        self._forced = False

    def force(self) -> None:
        self._forced = True

    def reset(self) -> None:
        self._last_marked_at = None
        self._forced = True


class MultiCadenceScheduler:
    def __init__(
        self,
        *,
        cadences: Mapping[str, CadenceTarget] | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or MonotonicClock()
        active = cadences or DEFAULT_LIVE_UI_CADENCES
        self._gates = {
            name: CadenceGate(interval_seconds=target.interval_seconds)
            for name, target in active.items()
        }

    def now(self) -> float:
        return float(self._clock())

    def gate(self, name: str) -> CadenceGate:
        if name not in self._gates:
            target = DEFAULT_LIVE_UI_CADENCES.get(name, CadenceTarget(30.0))
            self._gates[name] = CadenceGate(interval_seconds=target.interval_seconds)
        return self._gates[name]

    def due(self, name: str, *, now: float | None = None) -> bool:
        active_now = self.now() if now is None else float(now)
        return self.gate(name).due(active_now)

    def mark(self, name: str, *, now: float | None = None) -> None:
        active_now = self.now() if now is None else float(now)
        self.gate(name).mark(active_now)

    def run(self, name: str, *, now: float | None = None, force: bool = False) -> bool:
        active_now = self.now() if now is None else float(now)
        gate = self.gate(name)
        if force:
            gate.force()
        if not gate.due(active_now):
            return False
        gate.mark(active_now)
        return True

    def force(self, name: str) -> None:
        self.gate(name).force()

    def force_all(self) -> None:
        for gate in self._gates.values():
            gate.force()

    def reset(self, name: str) -> None:
        self.gate(name).reset()


@dataclass
class DirtyValueCache:
    _values: dict[str, object] = field(default_factory=dict)

    def changed(self, key: str, value: object) -> bool:
        if self._values.get(key) == value:
            return False
        self._values[key] = value
        return True

    def get(self, key: str) -> object | None:
        return self._values.get(key)

    def clear(self) -> None:
        self._values.clear()


@dataclass(frozen=True)
class TimingSummary:
    name: str
    count: int = 0
    average_ms: float = 0.0
    max_ms: float = 0.0
    last_ms: float = 0.0

    @property
    def available(self) -> bool:
        return self.count > 0


class BoundedTimingSeries:
    def __init__(self, *, max_samples: int = 300) -> None:
        self.max_samples = max(1, int(max_samples))
        self._values: deque[float] = deque(maxlen=self.max_samples)

    def append(self, elapsed_ms: float) -> None:
        self._values.append(max(0.0, float(elapsed_ms)))

    def clear(self) -> None:
        self._values.clear()

    def summary(self, name: str) -> TimingSummary:
        if not self._values:
            return TimingSummary(name=name)
        values = tuple(self._values)
        return TimingSummary(
            name=name,
            count=len(values),
            average_ms=round(sum(values) / len(values), 1),
            max_ms=round(max(values), 1),
            last_ms=round(values[-1], 1),
        )


class JankBucketCounter:
    _thresholds = (
        ("over_16ms", 16.0),
        ("over_33ms", 33.0),
        ("over_50ms", 50.0),
        ("over_100ms", 100.0),
        ("over_250ms", 250.0),
    )

    def __init__(self) -> None:
        self._counts = {name: 0 for name, _threshold in self._thresholds}

    def observe(self, elapsed_ms: float) -> None:
        value = max(0.0, float(elapsed_ms))
        for name, threshold in self._thresholds:
            if value > threshold:
                self._counts[name] += 1

    def snapshot(self) -> dict[str, int]:
        return dict(self._counts)

    def clear(self) -> None:
        for key in self._counts:
            self._counts[key] = 0


class LatestFrameCache:
    def __init__(self) -> None:
        self.signature: object | None = None
        self.value: object | None = None

    def update(self, signature: object, value: object) -> bool:
        changed = signature != self.signature
        self.signature = signature
        self.value = value
        return changed
