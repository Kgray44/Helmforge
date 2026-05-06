from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from shared_core.models.runtime import RuntimeTruth


class BridgeLifecycleState(str, Enum):
    NOT_INSTALLED = "NotInstalled"
    STOPPED = "Stopped"
    STARTING = "Starting"
    WAITING_FOR_HOTAS = "WaitingForHotas"
    HOTAS_DETECTED = "HotasDetected"
    WAITING_FOR_OUTPUT = "WaitingForOutput"
    SIMULATED = "Simulated"
    LIVE_UNVERIFIED = "LiveUnverified"
    LIVE_VERIFIED = "LiveVerified"
    SUSPENDED = "Suspended"
    STOPPING = "Stopping"
    ERROR = "Error"


@dataclass(frozen=True)
class BridgeLifecycleStatus:
    state: BridgeLifecycleState = BridgeLifecycleState.STOPPED
    runtime_truth: RuntimeTruth = RuntimeTruth.SIMULATED
    hotas_present: bool = False
    output_present: bool = False
    output_verified: bool = False
    started_at: datetime | None = None
    last_transition_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message: str = ""
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "runtime_truth": self.runtime_truth.value,
            "hotas_present": self.hotas_present,
            "output_present": self.output_present,
            "output_verified": self.output_verified,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_transition_at": self.last_transition_at.isoformat(),
            "message": self.message,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class BridgeLifecycleTransition:
    previous_state: BridgeLifecycleState
    next_state: BridgeLifecycleState
    reason: str = ""
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, object]:
        return {
            "previous_state": self.previous_state.value,
            "next_state": self.next_state.value,
            "reason": self.reason,
            "requested_at": self.requested_at.isoformat(),
        }
