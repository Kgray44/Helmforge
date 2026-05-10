from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from shared_core.models.runtime import AXIS_NAMES, BUTTON_NAMES, HAT_CENTERED, RuntimeSnapshot, RuntimeTruth
from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState
from shared_core.runtime.telemetry import (
    AxisTelemetrySnapshot,
    BridgeTelemetrySnapshot,
    ButtonHatTelemetrySnapshot,
    ModeStateTelemetrySnapshot,
    OutputVerificationState,
    RuleStateSummary,
)


OUTPUT_BUTTON_NAMES = tuple(f"Out{index}" for index in range(1, 21))


@dataclass(frozen=True)
class TelemetrySample:
    index: int
    raw_axes: Mapping[str, float]
    final_axes: Mapping[str, float]
    buttons: Mapping[str, bool]
    output_buttons: Mapping[str, bool]
    hat_state: str
    output_hat_state: str


@dataclass(frozen=True)
class BridgeFrameIdentity:
    source_type: str
    identity_key: str
    sequence: int | None = None
    frame_id: str = ""
    generated_at: datetime | None = None
    telemetry_timestamp: datetime | None = None
    bridge_tick_count: int | None = None
    warning: str = ""

    @property
    def label(self) -> str:
        if self.sequence is not None:
            return f"#{self.sequence}"
        if self.frame_id:
            return self.frame_id
        if self.generated_at is not None:
            return self.generated_at.isoformat()
        if self.telemetry_timestamp is not None:
            return self.telemetry_timestamp.isoformat()
        if self.bridge_tick_count is not None:
            return f"tick {self.bridge_tick_count}"
        return "unavailable"


@dataclass(frozen=True)
class BridgeFrameTrackerResult:
    identity: BridgeFrameIdentity
    is_new_frame: bool
    repeated_frame_count: int
    new_frame_count: int
    accepted_cadence_hz: float | None


class LiveTelemetryFrameTracker:
    def __init__(self, *, cadence_window: int = 30) -> None:
        self.last_bridge_frame_identity: BridgeFrameIdentity | None = None
        self.last_bridge_frame_received_at: datetime | None = None
        self.repeated_bridge_frame_count = 0
        self.new_bridge_frame_count = 0
        self._accepted_frame_times: deque[datetime] = deque(maxlen=max(2, int(cadence_window)))

    def observe(self, identity: BridgeFrameIdentity, *, received_at: datetime | None = None) -> BridgeFrameTrackerResult:
        received = _aware(received_at or datetime.now(timezone.utc))
        is_new = (
            self.last_bridge_frame_identity is None
            or identity.identity_key != self.last_bridge_frame_identity.identity_key
        )
        if is_new:
            self.last_bridge_frame_identity = identity
            self.last_bridge_frame_received_at = received
            self.new_bridge_frame_count += 1
            self._accepted_frame_times.append(received)
        else:
            self.repeated_bridge_frame_count += 1

        return BridgeFrameTrackerResult(
            identity=identity,
            is_new_frame=is_new,
            repeated_frame_count=self.repeated_bridge_frame_count,
            new_frame_count=self.new_bridge_frame_count,
            accepted_cadence_hz=self.accepted_cadence_hz,
        )

    @property
    def accepted_cadence_hz(self) -> float | None:
        if len(self._accepted_frame_times) < 2:
            return None
        elapsed = (self._accepted_frame_times[-1] - self._accepted_frame_times[0]).total_seconds()
        if elapsed <= 0:
            return None
        return round((len(self._accepted_frame_times) - 1) / elapsed, 3)


def extract_bridge_frame_identity(telemetry) -> BridgeFrameIdentity:
    runtime_frame = getattr(telemetry, "runtime_frame", None)
    bridge_timing = getattr(telemetry, "bridge_timing", None)
    sequence = getattr(runtime_frame, "sequence", None)
    frame_id = str(getattr(runtime_frame, "frame_id", "") or "")
    generated_at = getattr(runtime_frame, "generated_at", None)
    timestamp = getattr(telemetry, "timestamp", None)
    tick_count = _optional_int((bridge_timing or {}).get("tick_count")) if isinstance(bridge_timing, Mapping) else None

    if sequence is not None:
        key = f"sequence:{sequence}"
        warning = ""
    elif frame_id:
        key = f"frame_id:{frame_id}"
        warning = ""
    elif generated_at is not None:
        key = f"generated_at:{_aware(generated_at).isoformat()}"
        warning = "runtime_frame sequence/frame_id unavailable; using generated_at."
    elif timestamp is not None:
        key = f"timestamp:{_aware(timestamp).isoformat()}"
        warning = "runtime_frame identity unavailable; using telemetry timestamp."
    elif tick_count is not None:
        key = f"bridge_tick:{tick_count}"
        warning = "frame timestamp unavailable; using bridge tick count."
    else:
        key = "unavailable"
        warning = "Bridge frame identity unavailable."

    return BridgeFrameIdentity(
        source_type="bridge",
        identity_key=key,
        sequence=sequence,
        frame_id=frame_id,
        generated_at=_aware(generated_at) if generated_at is not None else None,
        telemetry_timestamp=_aware(timestamp) if timestamp is not None else None,
        bridge_tick_count=tick_count,
        warning=warning,
    )


class BoundedTelemetryHistory:
    def __init__(self, *, capacity: int = 240, sample_rate_hz: int = 60, right_anchor: bool = False) -> None:
        self.capacity = max(1, int(capacity))
        self.sample_rate_hz = max(1, int(sample_rate_hz))
        self.right_anchor = bool(right_anchor)
        self._samples: deque[TelemetrySample] = deque(maxlen=self.capacity)

    @classmethod
    def for_seconds(cls, *, history_seconds: float, sample_rate_hz: int) -> "BoundedTelemetryHistory":
        capacity = max(1, int(round(float(history_seconds) * int(sample_rate_hz))))
        return cls(capacity=capacity, sample_rate_hz=sample_rate_hz, right_anchor=True)

    def __len__(self) -> int:
        return len(self._samples)

    @property
    def latest(self) -> TelemetrySample | None:
        return self._samples[-1] if self._samples else None

    def append(self, sample: TelemetrySample) -> None:
        self._samples.append(
            TelemetrySample(
                index=sample.index,
                raw_axes={axis: clamp_axis_value(sample.raw_axes.get(axis, 0.0)) for axis in AXIS_NAMES},
                final_axes={axis: clamp_axis_value(sample.final_axes.get(axis, 0.0)) for axis in AXIS_NAMES},
                buttons={name: bool(sample.buttons.get(name, False)) for name in BUTTON_NAMES},
                output_buttons={name: bool(sample.output_buttons.get(name, False)) for name in OUTPUT_BUTTON_NAMES},
                hat_state=str(sample.hat_state or HAT_CENTERED),
                output_hat_state=str(sample.output_hat_state or HAT_CENTERED),
            )
        )

    def raw_points(self, axis_name: str) -> tuple[tuple[float, float], ...]:
        return tuple((x, sample.raw_axes.get(axis_name, 0.0)) for x, sample in self._right_anchored_samples())

    def final_points(self, axis_name: str) -> tuple[tuple[float, float], ...]:
        return tuple((x, sample.final_axes.get(axis_name, 0.0)) for x, sample in self._right_anchored_samples())

    def _right_anchored_samples(self) -> tuple[tuple[float, TelemetrySample], ...]:
        samples = tuple(self._samples)
        if not self.right_anchor:
            return tuple((float(sample.index), sample) for sample in samples)
        count = len(samples)
        return tuple(
            (((index - (count - 1)) / float(self.sample_rate_hz)), sample)
            for index, sample in enumerate(samples)
        )


def clamp_axis_value(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def telemetry_sample_from_runtime_snapshot(snapshot: RuntimeSnapshot, *, index: int) -> TelemetrySample:
    output_buttons = {
        f"Out{number}": bool(snapshot.button_states.get(f"B{number}", False)) if number <= 15 else False
        for number in range(1, 21)
    }
    return TelemetrySample(
        index=index,
        raw_axes={axis: snapshot.raw_axis_values.get(axis, 0.0) for axis in AXIS_NAMES},
        final_axes={axis: snapshot.final_output_values.get(axis, 0.0) for axis in AXIS_NAMES},
        buttons={name: bool(snapshot.button_states.get(name, False)) for name in BUTTON_NAMES},
        output_buttons=output_buttons,
        hat_state=snapshot.hat_state,
        output_hat_state=snapshot.hat_state,
    )


def telemetry_sample_from_bridge_payload(payload, *, index: int) -> TelemetrySample:
    output_buttons = {
        f"Out{number}": bool(payload.buttons.get(f"B{number}", False)) if number <= 15 else False
        for number in range(1, 21)
    }
    return TelemetrySample(
        index=index,
        raw_axes={axis: payload.raw_axes.get(axis, 0.0) for axis in AXIS_NAMES},
        final_axes={axis: payload.final_axes.get(axis, 0.0) for axis in AXIS_NAMES},
        buttons={name: bool(payload.buttons.get(name, False)) for name in BUTTON_NAMES},
        output_buttons=output_buttons,
        hat_state=payload.hats.get("HOTAS Hat", HAT_CENTERED),
        output_hat_state=payload.hats.get("Output Hat", HAT_CENTERED),
    )


def bridge_telemetry_from_runtime_snapshot(
    snapshot: RuntimeSnapshot,
    *,
    active_profile: str = "Current Workspace",
    rule_summary: RuleStateSummary | None = None,
) -> BridgeTelemetrySnapshot:
    status = snapshot.runtime_status
    return BridgeTelemetrySnapshot(
        runtime_truth=status.truth,
        lifecycle_state=_lifecycle_from_truth(status.truth),
        input_status=status.input.status,
        output_status=status.output.status,
        raw_axes=AxisTelemetrySnapshot(snapshot.raw_axis_values),
        final_axes=AxisTelemetrySnapshot(snapshot.final_output_values),
        controls=ButtonHatTelemetrySnapshot(
            buttons={name: bool(snapshot.button_states.get(name, False)) for name in BUTTON_NAMES},
            hats={"HOTAS Hat": snapshot.hat_state, "Output Hat": snapshot.hat_state},
        ),
        active_modes=ModeStateTelemetrySnapshot(),
        active_profile=active_profile,
        rule_summary=rule_summary or RuleStateSummary(),
        output_verification=OutputVerificationState(
            verified=status.live_output_writes_verified,
            backend_name=status.detected_output_backend_name,
            message=(
                "Output writes are verified."
                if status.live_output_writes_verified
                else "Output writes are not verified."
            ),
        ),
        warnings=status.warnings,
        errors=status.errors,
    )


def _lifecycle_from_truth(truth: RuntimeTruth) -> BridgeLifecycleState:
    if truth is RuntimeTruth.LIVE_VERIFIED:
        return BridgeLifecycleState.LIVE_VERIFIED
    if truth is RuntimeTruth.DETECTED_UNVERIFIED:
        return BridgeLifecycleState.LIVE_UNVERIFIED
    if truth is RuntimeTruth.BLOCKED_MISSING_DEVICE:
        return BridgeLifecycleState.WAITING_FOR_HOTAS
    if truth is RuntimeTruth.BLOCKED_MISSING_DRIVER:
        return BridgeLifecycleState.WAITING_FOR_OUTPUT
    if truth is RuntimeTruth.ERROR:
        return BridgeLifecycleState.ERROR
    return BridgeLifecycleState.SIMULATED
