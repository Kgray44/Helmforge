from __future__ import annotations

import math
import time

from shared_core.models.runtime import (
    AXIS_NAMES,
    BUTTON_NAMES,
    HAT_CENTERED,
    RuntimePreflightStatus,
    RuntimeSnapshot,
    simulation_fallback_status,
)


class SimulatedRuntime:
    def __init__(self, *, deterministic: bool = False) -> None:
        self._deterministic = deterministic
        self._start_time = time.monotonic()

    def _axis_values(self) -> dict[str, float]:
        if self._deterministic:
            return {
                "Roll": 0.0,
                "Pitch": 0.25,
                "Throttle": 0.5,
                "Yaw": -0.25,
                "Aux 1": 0.75,
                "Aux 2": -0.75,
            }

        elapsed = time.monotonic() - self._start_time
        return {
            "Roll": math.sin(elapsed),
            "Pitch": math.sin(elapsed * 0.7) * 0.8,
            "Throttle": (math.sin(elapsed * 0.35) + 1.0) / 2.0,
            "Yaw": math.sin(elapsed * 1.3) * 0.5,
            "Aux 1": math.cos(elapsed * 0.45) * 0.6,
            "Aux 2": math.sin(elapsed * 0.55 + 1.5) * 0.6,
        }

    def _button_states(self) -> dict[str, bool]:
        if self._deterministic:
            return {name: False for name in BUTTON_NAMES}

        step = int((time.monotonic() - self._start_time) * 2)
        return {name: ((index + step) % 11 == 0) for index, name in enumerate(BUTTON_NAMES, start=1)}

    def _hat_state(self) -> str:
        if self._deterministic:
            return HAT_CENTERED

        states = (HAT_CENTERED, "Up", "Right", "Down", "Left")
        index = int((time.monotonic() - self._start_time) * 0.75) % len(states)
        return states[index]

    def snapshot(self, runtime_status: RuntimePreflightStatus | None = None) -> RuntimeSnapshot:
        raw_axis_values = self._axis_values()
        final_output_values = {axis: raw_axis_values[axis] for axis in AXIS_NAMES}
        return RuntimeSnapshot(
            raw_axis_values=raw_axis_values,
            final_output_values=final_output_values,
            button_states=self._button_states(),
            hat_state=self._hat_state(),
            runtime_status=runtime_status or simulation_fallback_status(),
            simulated=True,
        )

