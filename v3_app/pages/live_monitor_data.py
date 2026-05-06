from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass

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


class BoundedTelemetryHistory:
    def __init__(self, *, capacity: int = 240) -> None:
        self.capacity = max(1, int(capacity))
        self._samples: deque[TelemetrySample] = deque(maxlen=self.capacity)

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
        return tuple((float(sample.index), sample.raw_axes.get(axis_name, 0.0)) for sample in self._samples)

    def final_points(self, axis_name: str) -> tuple[tuple[float, float], ...]:
        return tuple((float(sample.index), sample.final_axes.get(axis_name, 0.0)) for sample in self._samples)


def clamp_axis_value(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


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
                "Live output writes are verified."
                if status.live_output_writes_verified
                else "Live output writes are not verified."
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
