from __future__ import annotations

from typing import Mapping

from shared_core.models.runtime import RuntimePreflightStatus, RuntimeSnapshot
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.simulated_runtime import SimulatedRuntime


class RuntimeBridge:
    def __init__(
        self,
        *,
        preflight_status: RuntimePreflightStatus | None = None,
        deterministic_simulation: bool = False,
    ) -> None:
        self._runtime_status = preflight_status or build_runtime_preflight_status()
        self._simulated_runtime = SimulatedRuntime(deterministic=deterministic_simulation)

    @property
    def runtime_status(self) -> RuntimePreflightStatus:
        return self._runtime_status

    def snapshot(self) -> RuntimeSnapshot:
        return self._simulated_runtime.snapshot(runtime_status=self._runtime_status)

    def latest_raw_axis_values(self) -> Mapping[str, float]:
        return self.snapshot().raw_axis_values

    def latest_final_output_values(self) -> Mapping[str, float]:
        return self.snapshot().final_output_values

    def button_states(self) -> Mapping[str, bool]:
        return self.snapshot().button_states

    def hat_state(self) -> str:
        return self.snapshot().hat_state
