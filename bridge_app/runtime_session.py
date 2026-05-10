from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from shared_core.runtime.vjoy_output import (
    MissingVirtualOutputBackend,
    VirtualOutputBackend,
    VirtualOutputLoopConfig,
    VirtualOutputLoopSnapshot,
    VirtualOutputVerificationResult,
    VirtualOutputVerificationStatus,
    VirtualOutputWriteLoop,
    build_safe_vjoy_verification_intent,
)


@dataclass(frozen=True)
class OutputLoopRuntimeTelemetry:
    backend_name: str
    backend_kind: str
    selected_output_device: str
    verification_status: str
    verification_cached: bool
    verification_age_ms: float | None
    verification_source: str
    verification_real: bool
    verification_fake: bool
    enabled: bool
    running: bool
    state: str
    write_rate_hz: float
    actual_write_rate_hz: float | None
    tick_count: int
    write_attempt_count: int
    write_success_count: int
    write_failure_count: int
    write_skipped_count: int
    write_skipped_rate_limited_count: int
    write_skipped_disabled_count: int
    write_skipped_safety_count: int
    write_skipped_unsafe_count: int
    consecutive_write_failures: int
    write_count: int
    failure_count: int
    last_write_timestamp: str
    last_write_status: str
    last_write_duration_ms: float | None
    last_skipped_write_reason: str
    neutral_restore_attempted: bool
    neutral_restore_status: str
    neutral_restore_timestamp: str | None
    neutral_restore_message: str
    neutral_restore_error: str
    neutral_restore_duration_ms: float | None
    safety_stop_reason: str
    safety_stop_timestamp: str | None
    loop_recreated_count: int
    last_recreate_reason: str
    current_output_intent_source: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "backend_name": self.backend_name,
            "backend_kind": self.backend_kind,
            "selected_output_device": self.selected_output_device,
            "verification_status": self.verification_status,
            "verification_cached": self.verification_cached,
            "verification_age_ms": self.verification_age_ms,
            "verification_source": self.verification_source,
            "verification_real": self.verification_real,
            "verification_fake": self.verification_fake,
            "enabled": self.enabled,
            "running": self.running,
            "state": self.state,
            "write_rate_hz": self.write_rate_hz,
            "actual_write_rate_hz": self.actual_write_rate_hz,
            "tick_count": self.tick_count,
            "write_attempt_count": self.write_attempt_count,
            "write_success_count": self.write_success_count,
            "write_failure_count": self.write_failure_count,
            "write_skipped_count": self.write_skipped_count,
            "write_skipped_rate_limited_count": self.write_skipped_rate_limited_count,
            "write_skipped_disabled_count": self.write_skipped_disabled_count,
            "write_skipped_safety_count": self.write_skipped_safety_count,
            "write_skipped_unsafe_count": self.write_skipped_unsafe_count,
            "consecutive_write_failures": self.consecutive_write_failures,
            "write_count": self.write_count,
            "failure_count": self.failure_count,
            "last_write_timestamp": self.last_write_timestamp,
            "last_write_status": self.last_write_status,
            "last_write_duration_ms": self.last_write_duration_ms,
            "last_skipped_write_reason": self.last_skipped_write_reason,
            "neutral_restore_attempted": self.neutral_restore_attempted,
            "neutral_restore_status": self.neutral_restore_status,
            "neutral_restore_timestamp": self.neutral_restore_timestamp,
            "neutral_restore_message": self.neutral_restore_message,
            "neutral_restore_error": self.neutral_restore_error,
            "neutral_restore_duration_ms": self.neutral_restore_duration_ms,
            "safety_stop_reason": self.safety_stop_reason,
            "safety_stop_timestamp": self.safety_stop_timestamp,
            "loop_recreated_count": self.loop_recreated_count,
            "last_recreate_reason": self.last_recreate_reason,
            "current_output_intent_source": self.current_output_intent_source,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


class BridgeOutputRuntimeSession:
    def __init__(
        self,
        *,
        backend: VirtualOutputBackend | None = None,
        verification_enabled: bool = True,
        loop_config: VirtualOutputLoopConfig | None = None,
        clock: object | None = None,
    ) -> None:
        self.backend = backend or MissingVirtualOutputBackend()
        self.verification_enabled = verification_enabled
        self.loop_config = loop_config or VirtualOutputLoopConfig()
        self.clock = clock
        self.verification: VirtualOutputVerificationResult | None = None
        self.verification_cached_at: datetime | None = None
        self.output_loop = VirtualOutputWriteLoop(
            backend=self.backend,
            verification=self.verification,
            config=self.loop_config,
            clock=self.clock,
        )
        self.loop_recreated_count = 0
        self.last_recreate_reason = "startup"
        self.refresh_verification(reason="startup")

    def refresh_verification(self, *, force: bool = False, reason: str = "refresh") -> VirtualOutputVerificationResult | None:
        if not self.verification_enabled:
            self.verification = None
            self.verification_cached_at = None
            return None
        if self.verification is not None and not force:
            return self.verification
        self.verification = self.backend.verify_output_write(build_safe_vjoy_verification_intent(timestamp=self._now()))
        self.verification_cached_at = self._now()
        self._rebuild_loop(reason="verification_refreshed" if reason != "startup" else "startup")
        return self.verification

    def set_output_allowed(self, allowed: bool) -> VirtualOutputLoopSnapshot:
        snapshot = self.output_loop.snapshot()
        if allowed:
            if not snapshot.enabled and snapshot.state.value != "safety_stopped":
                return self.output_loop.enable()
            return snapshot
        if snapshot.enabled:
            return self.output_loop.disable()
        return snapshot

    def disable(self) -> VirtualOutputLoopSnapshot:
        return self.set_output_allowed(False)

    def telemetry(self) -> OutputLoopRuntimeTelemetry:
        snapshot = self.output_loop.snapshot()
        caps = self.backend.get_capabilities()
        verification = self.verification
        verification_status = VirtualOutputVerificationStatus.NOT_ATTEMPTED.value
        verification_source = "not attempted"
        verification_real = False
        verification_fake = False
        warnings: tuple[str, ...] = ()
        errors: tuple[str, ...] = ()
        if verification is not None:
            verification_status = verification.status.value
            verification_source = verification.source
            verification_real = verification.real_output_verified
            verification_fake = verification.fake_output_verified
            warnings = verification.warnings
            errors = verification.errors
        return OutputLoopRuntimeTelemetry(
            backend_name=caps.backend_name,
            backend_kind=caps.backend_kind,
            selected_output_device=snapshot.selected_output_device,
            verification_status=verification_status,
            verification_cached=verification is not None,
            verification_age_ms=self.verification_age_ms(),
            verification_source=verification_source,
            verification_real=verification_real,
            verification_fake=verification_fake,
            enabled=snapshot.enabled,
            running=snapshot.state.value == "running",
            state=snapshot.state.value,
            write_rate_hz=snapshot.write_rate_hz,
            actual_write_rate_hz=snapshot.actual_write_rate_hz,
            tick_count=snapshot.tick_count,
            write_attempt_count=snapshot.write_attempt_count,
            write_success_count=snapshot.write_success_count,
            write_failure_count=snapshot.write_failure_count,
            write_skipped_count=snapshot.write_skipped_count,
            write_skipped_rate_limited_count=snapshot.write_skipped_rate_limited_count,
            write_skipped_disabled_count=snapshot.write_skipped_disabled_count,
            write_skipped_safety_count=snapshot.write_skipped_safety_count,
            write_skipped_unsafe_count=snapshot.write_skipped_unsafe_count,
            consecutive_write_failures=snapshot.consecutive_write_failures,
            write_count=snapshot.write_count,
            failure_count=snapshot.failure_count,
            last_write_timestamp=snapshot.last_write_timestamp,
            last_write_status=snapshot.output_write_status,
            last_write_duration_ms=snapshot.last_write_duration_ms,
            last_skipped_write_reason=snapshot.last_skipped_write_reason,
            neutral_restore_attempted=snapshot.neutral_restore_attempted,
            neutral_restore_status=snapshot.neutral_restore_status,
            neutral_restore_timestamp=snapshot.neutral_restore_timestamp,
            neutral_restore_message=snapshot.neutral_restore_message,
            neutral_restore_error=snapshot.neutral_restore_error,
            neutral_restore_duration_ms=snapshot.neutral_restore_duration_ms,
            safety_stop_reason=snapshot.safety_stop_reason,
            safety_stop_timestamp=snapshot.safety_stop_timestamp,
            loop_recreated_count=self.loop_recreated_count,
            last_recreate_reason=self.last_recreate_reason,
            current_output_intent_source=snapshot.current_output_intent_source,
            warnings=warnings,
            errors=errors,
        )

    def verification_age_ms(self) -> float | None:
        if self.verification_cached_at is None:
            return None
        return round(max(0.0, (self._now() - self.verification_cached_at).total_seconds() * 1000.0), 3)

    def _rebuild_loop(self, *, reason: str) -> None:
        old_loop_exists = self.output_loop is not None
        self.output_loop = VirtualOutputWriteLoop(
            backend=self.backend,
            verification=self.verification,
            config=self.loop_config,
            clock=self.clock,
        )
        if old_loop_exists and reason != "startup":
            self.loop_recreated_count += 1
        self.last_recreate_reason = reason

    def _now(self) -> datetime:
        if callable(self.clock):
            value = self.clock()
            if isinstance(value, datetime):
                return _aware(value)
        return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
