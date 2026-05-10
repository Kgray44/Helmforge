from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TelemetryTransportKind(str, Enum):
    JSON_SNAPSHOT = "json_snapshot"
    LOCAL_WEBSOCKET = "local_websocket"
    LOCAL_TCP = "local_tcp"
    WINDOWS_NAMED_PIPE = "windows_named_pipe"
    SHARED_MEMORY_RING = "shared_memory_ring"
    SIMULATION = "simulation"


class TelemetrySourceKind(str, Enum):
    BRIDGE_STREAM = "bridge_stream"
    BRIDGE_JSON_SNAPSHOT = "bridge_json_snapshot"
    SIMULATION_FALLBACK = "simulation_fallback"


class TelemetryTransportState(str, Enum):
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    UNAVAILABLE = "unavailable"
    STALE = "stale"
    INVALID = "invalid"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class TelemetrySourceCandidate:
    source: TelemetrySourceKind
    state: TelemetryTransportState
    fresh: bool
    valid: bool
    reason: str = ""

    @property
    def usable(self) -> bool:
        if self.source is TelemetrySourceKind.SIMULATION_FALLBACK:
            return self.valid
        return self.valid and self.fresh and self.state is TelemetryTransportState.CONNECTED


SOURCE_PRIORITY: tuple[TelemetrySourceKind, ...] = (
    TelemetrySourceKind.BRIDGE_STREAM,
    TelemetrySourceKind.BRIDGE_JSON_SNAPSHOT,
    TelemetrySourceKind.SIMULATION_FALLBACK,
)


def select_telemetry_source(candidates: list[TelemetrySourceCandidate] | tuple[TelemetrySourceCandidate, ...]) -> TelemetrySourceCandidate | None:
    usable = [candidate for candidate in candidates if candidate.usable]
    for source in SOURCE_PRIORITY:
        for candidate in usable:
            if candidate.source is source:
                return candidate
    return None
