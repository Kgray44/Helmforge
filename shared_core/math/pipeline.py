from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from shared_core.math.filtering import FilterState
from shared_core.math.stack import AxisStackResult, ModeState, process_axis_stack
from shared_core.models.axes import all_axis_definitions
from shared_core.models.workspace import WorkspaceConfig


@dataclass(frozen=True)
class SignalPipelineState:
    filter_states: Mapping[str, FilterState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "filter_states", MappingProxyType(dict(self.filter_states)))

    def filter_state_for(self, axis_name: str) -> FilterState:
        return self.filter_states.get(axis_name, FilterState())


@dataclass(frozen=True)
class WorkspaceSignalPipelineResult:
    raw_axis_values: Mapping[str, float]
    final_output_values: Mapping[str, float]
    axis_results: Mapping[str, AxisStackResult]
    state: SignalPipelineState

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_axis_values", MappingProxyType(dict(self.raw_axis_values)))
        object.__setattr__(self, "final_output_values", MappingProxyType(dict(self.final_output_values)))
        object.__setattr__(self, "axis_results", MappingProxyType(dict(self.axis_results)))


class WorkspaceSignalPipeline:
    """UI-independent per-workspace axis processing seam for the future Bridge."""

    def __init__(self, workspace: WorkspaceConfig) -> None:
        self._workspace = workspace

    def initial_state(self) -> SignalPipelineState:
        return SignalPipelineState(
            {axis.display_name: FilterState() for axis in all_axis_definitions()}
        )

    def process(
        self,
        raw_axis_values: Mapping[str, float],
        *,
        mode_state: ModeState | None = None,
        state: SignalPipelineState | None = None,
    ) -> WorkspaceSignalPipelineResult:
        active_mode_state = mode_state or ModeState()
        current_state = state or self.initial_state()
        ordered_raw_values: dict[str, float] = {}
        final_output_values: dict[str, float] = {}
        axis_results: dict[str, AxisStackResult] = {}
        next_filter_states: dict[str, FilterState] = {}

        for axis in all_axis_definitions():
            axis_id = axis.axis_id.value
            axis_name = axis.display_name
            raw_value = float(raw_axis_values[axis_name])
            stack_result = process_axis_stack(
                raw_value,
                tuning=self._workspace.tuning.axes[axis_id],
                filtering=self._workspace.filtering.axes[axis_id],
                combat=self._workspace.combat.axes[axis_id],
                mode_config=self._workspace.modes,
                mode_state=active_mode_state,
                rules=self._workspace.rules.rules,
                previous_filter_state=current_state.filter_state_for(axis_name),
            )
            ordered_raw_values[axis_name] = raw_value
            final_output_values[axis_name] = stack_result.final_output
            axis_results[axis_name] = stack_result
            next_filter_states[axis_name] = stack_result.filter_state

        return WorkspaceSignalPipelineResult(
            raw_axis_values=ordered_raw_values,
            final_output_values=final_output_values,
            axis_results=axis_results,
            state=SignalPipelineState(next_filter_states),
        )
