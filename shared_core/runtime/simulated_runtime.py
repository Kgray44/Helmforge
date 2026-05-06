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
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.math.filtering import FilterState
from shared_core.math.stack import ModeState, process_axis_stack


class SimulatedRuntime:
    def __init__(self, *, deterministic: bool = False, workspace: WorkspaceConfig | None = None) -> None:
        self._deterministic = deterministic
        self._start_time = time.monotonic()
        self._workspace = workspace or create_default_workspace()
        self._filter_states = {axis: FilterState() for axis in AXIS_NAMES}

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
        final_output_values: dict[str, float] = {}
        for axis_id, tuning in self._workspace.tuning.axes.items():
            axis_name = tuning.axis
            result = process_axis_stack(
                raw_axis_values[axis_name],
                tuning=tuning,
                filtering=self._workspace.filtering.axes[axis_id],
                combat=self._workspace.combat.axes[axis_id],
                mode_config=self._workspace.modes,
                mode_state=ModeState(),
                rules=self._workspace.rules.rules,
                previous_filter_state=self._filter_states[axis_name],
            )
            self._filter_states[axis_name] = result.filter_state
            final_output_values[axis_name] = result.final_output
        return RuntimeSnapshot(
            raw_axis_values=raw_axis_values,
            final_output_values=final_output_values,
            button_states=self._button_states(),
            hat_state=self._hat_state(),
            runtime_status=runtime_status or simulation_fallback_status(),
            simulated=True,
        )
