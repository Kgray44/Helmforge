from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from shared_core.models.runtime import RuntimePreflightStatus, RuntimeTruth
from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState, BridgeLifecycleStatus


@dataclass(frozen=True)
class BridgeProcessState:
    lifecycle: BridgeLifecycleStatus
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    tick_count: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def starting(cls) -> "BridgeProcessState":
        return cls(
            lifecycle=BridgeLifecycleStatus(
                state=BridgeLifecycleState.STARTING,
                runtime_truth=RuntimeTruth.SIMULATED,
                message="Bridge process starting in simulation-only mode.",
            )
        )

    def with_lifecycle(
        self,
        lifecycle_state: BridgeLifecycleState,
        runtime_status: RuntimePreflightStatus,
        *,
        message: str = "",
    ) -> "BridgeProcessState":
        return BridgeProcessState(
            lifecycle=BridgeLifecycleStatus(
                state=lifecycle_state,
                runtime_truth=runtime_status.truth,
                hotas_present=bool(runtime_status.detected_device_names),
                output_present=runtime_status.detected_output_backend_name is not None,
                output_verified=runtime_status.live_output_writes_verified,
                started_at=self.started_at,
                message=message,
                warnings=self.warnings,
                errors=self.errors,
            ),
            warnings=self.warnings,
            errors=self.errors,
            tick_count=self.tick_count,
            started_at=self.started_at,
        )

    def with_messages(
        self,
        *,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
    ) -> "BridgeProcessState":
        return BridgeProcessState(
            lifecycle=self.lifecycle,
            warnings=(*self.warnings, *warnings),
            errors=(*self.errors, *errors),
            tick_count=self.tick_count,
            started_at=self.started_at,
        )

    def next_tick(self) -> "BridgeProcessState":
        return BridgeProcessState(
            lifecycle=self.lifecycle,
            warnings=self.warnings,
            errors=self.errors,
            tick_count=self.tick_count + 1,
            started_at=self.started_at,
        )


def lifecycle_for_preflight(
    status: RuntimePreflightStatus,
    *,
    simulate: bool,
) -> BridgeLifecycleState:
    if status.live_output_writes_verified:
        return BridgeLifecycleState.LIVE_VERIFIED
    if simulate:
        return BridgeLifecycleState.SIMULATED
    if status.truth is RuntimeTruth.DETECTED_UNVERIFIED:
        return BridgeLifecycleState.LIVE_UNVERIFIED
    if status.truth is RuntimeTruth.BLOCKED_MISSING_DEVICE:
        return BridgeLifecycleState.WAITING_FOR_HOTAS
    if status.truth is RuntimeTruth.BLOCKED_MISSING_DRIVER:
        return BridgeLifecycleState.WAITING_FOR_OUTPUT
    if status.truth is RuntimeTruth.ERROR:
        return BridgeLifecycleState.ERROR
    return BridgeLifecycleState.SIMULATED
