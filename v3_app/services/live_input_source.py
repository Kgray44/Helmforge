from __future__ import annotations

import time
from dataclasses import replace
from datetime import datetime, timezone

from shared_core.models.runtime import AXIS_NAMES
from shared_core.runtime.runtime_bridge import RuntimeBridge
from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus
from v3_app.services.embedded_bridge_telemetry import read_embedded_bridge_telemetry
from v3_app.services.live_source_arbitration import LiveTelemetrySourceSelector
from v3_app.services.live_ui_scheduler import MultiCadenceScheduler


class LiveAxisSampleSource:
    def __init__(self, runtime_bridge: RuntimeBridge, bridge_client: BridgeTelemetryClient | None = None, *, clock=None) -> None:
        self._runtime_bridge = runtime_bridge
        self._bridge_client = bridge_client or BridgeTelemetryClient(stale_after_seconds=0.25)
        self._clock = clock
        self._scheduler = MultiCadenceScheduler()
        self._source_selector = LiveTelemetrySourceSelector(clock=clock)
        self._last_json_result = None
        self.last_source_label = "Simulation/fallback sample"
        self.last_runtime_truth = runtime_bridge.runtime_status.truth.value
        self.last_output_verified = runtime_bridge.runtime_status.live_output_writes_verified
        self.json_read_duration_ms: float | None = None
        self.json_read_skipped_due_to_embedded_fresh = False
        self.json_read_skipped_due_to_embedded_fresh_count = 0
        self.json_read_count = 0
        self.json_cache_reuse_count = 0

    def raw_axes(self) -> dict[str, float]:
        embedded_result = read_embedded_bridge_telemetry(stale_after_seconds=1.0, clock=self._clock)
        if embedded_result.status is BridgeTelemetryStatus.CONNECTED and embedded_result.telemetry is not None:
            self.json_read_skipped_due_to_embedded_fresh = True
            self.json_read_skipped_due_to_embedded_fresh_count += 1
            self.json_read_duration_ms = 0.0
            selected = self._source_selector.select(embedded_result=embedded_result, json_result=None)
        else:
            self.json_read_skipped_due_to_embedded_fresh = False
            if self._scheduler.run("telemetry_json") or self._last_json_result is None:
                started = time.perf_counter()
                bridge_result = self._bridge_client.read()
                self.json_read_duration_ms = (time.perf_counter() - started) * 1000.0
                self.json_read_count += 1
                self._last_json_result = bridge_result
            else:
                self.json_cache_reuse_count += 1
                bridge_result = self._cached_json_result()
                self.json_read_duration_ms = 0.0
            selected = self._source_selector.select(embedded_result=embedded_result, json_result=bridge_result)
        if selected.status is BridgeTelemetryStatus.CONNECTED and selected.telemetry is not None:
            telemetry = selected.telemetry
            self.last_source_label = selected.source_label or f"Bridge telemetry ({telemetry.runtime_truth})"
            self.last_runtime_truth = str(telemetry.runtime_truth)
            self.last_output_verified = bool(telemetry.output_verified)
            return {axis: float(telemetry.raw_axes.get(axis, 0.0)) for axis in AXIS_NAMES}
        snapshot = self._runtime_bridge.snapshot()
        self.last_source_label = "Simulation/fallback sample"
        self.last_runtime_truth = snapshot.runtime_status.truth.value
        self.last_output_verified = snapshot.runtime_status.live_output_writes_verified
        return {axis: float(snapshot.raw_axis_values.get(axis, 0.0)) for axis in AXIS_NAMES}

    def _cached_json_result(self):
        result = self._last_json_result
        if result is None or result.telemetry is None:
            return result
        now = _aware(self._clock() if self._clock is not None else datetime.now(timezone.utc))
        age = max(0.0, (now - _aware(result.telemetry.timestamp)).total_seconds())
        return replace(result, age_seconds=age, last_read_at=now)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
