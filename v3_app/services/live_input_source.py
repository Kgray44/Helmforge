from __future__ import annotations

from shared_core.models.runtime import AXIS_NAMES
from shared_core.runtime.runtime_bridge import RuntimeBridge
from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryStatus


class LiveAxisSampleSource:
    def __init__(self, runtime_bridge: RuntimeBridge, bridge_client: BridgeTelemetryClient | None = None) -> None:
        self._runtime_bridge = runtime_bridge
        self._bridge_client = bridge_client or BridgeTelemetryClient(stale_after_seconds=0.25)
        self.last_source_label = "Simulation/fallback sample"
        self.last_runtime_truth = runtime_bridge.runtime_status.truth.value
        self.last_output_verified = runtime_bridge.runtime_status.live_output_writes_verified

    def raw_axes(self) -> dict[str, float]:
        bridge_result = self._bridge_client.read()
        if bridge_result.status is BridgeTelemetryStatus.CONNECTED and bridge_result.telemetry is not None:
            telemetry = bridge_result.telemetry
            self.last_source_label = f"Bridge telemetry ({telemetry.runtime_truth})"
            self.last_runtime_truth = str(telemetry.runtime_truth)
            self.last_output_verified = bool(telemetry.output_verified)
            return {axis: float(telemetry.raw_axes.get(axis, 0.0)) for axis in AXIS_NAMES}
        snapshot = self._runtime_bridge.snapshot()
        self.last_source_label = "Simulation/fallback sample"
        self.last_runtime_truth = snapshot.runtime_status.truth.value
        self.last_output_verified = snapshot.runtime_status.live_output_writes_verified
        return {axis: float(snapshot.raw_axis_values.get(axis, 0.0)) for axis in AXIS_NAMES}
