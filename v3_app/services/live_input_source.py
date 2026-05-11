from __future__ import annotations

import time

from shared_core.models.runtime import AXIS_NAMES
from shared_core.runtime.runtime_bridge import RuntimeBridge
from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus
from v3_app.services.embedded_bridge_telemetry import read_embedded_bridge_telemetry
from v3_app.services.live_source_arbitration import LiveTelemetrySourceSelector


class LiveAxisSampleSource:
    def __init__(self, runtime_bridge: RuntimeBridge, bridge_client: BridgeTelemetryClient | None = None, *, clock=None) -> None:
        self._runtime_bridge = runtime_bridge
        self._bridge_client = bridge_client or BridgeTelemetryClient(stale_after_seconds=0.25)
        self._clock = clock
        self._source_selector = LiveTelemetrySourceSelector(clock=clock)
        self.last_source_label = "Simulation/fallback sample"
        self.last_runtime_truth = runtime_bridge.runtime_status.truth.value
        self.last_output_verified = runtime_bridge.runtime_status.live_output_writes_verified
        self.json_read_duration_ms: float | None = None
        self.json_read_skipped_due_to_embedded_fresh = False
        self.json_read_skipped_due_to_embedded_fresh_count = 0

    def raw_axes(self) -> dict[str, float]:
        embedded_result = read_embedded_bridge_telemetry(stale_after_seconds=1.0, clock=self._clock)
        if embedded_result.status is BridgeTelemetryStatus.CONNECTED and embedded_result.telemetry is not None:
            self.json_read_skipped_due_to_embedded_fresh = True
            self.json_read_skipped_due_to_embedded_fresh_count += 1
            self.json_read_duration_ms = 0.0
            selected = self._source_selector.select(embedded_result=embedded_result, json_result=None)
        else:
            self.json_read_skipped_due_to_embedded_fresh = False
            started = time.perf_counter()
            bridge_result = self._bridge_client.read()
            self.json_read_duration_ms = (time.perf_counter() - started) * 1000.0
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
