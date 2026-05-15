from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from shared_core.math.filtering import FilterState
from shared_core.math.stack import AxisStackResult, ModeState, process_axis_stack
from shared_core.models.axes import all_axis_definitions
from shared_core.models.workspace import WorkspaceConfig
from shared_core.rules.evaluator import RuleEvaluationContext, RuleEvaluationResult, evaluate_rules


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
    rule_evaluations: tuple[RuleEvaluationResult, ...] = ()

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
        active_buttons: tuple[int, ...] = (),
    ) -> WorkspaceSignalPipelineResult:
        active_mode_state = mode_state or ModeState()
        current_state = state or self.initial_state()
        rule_evaluations: tuple[RuleEvaluationResult, ...] = ()

        if self._workspace.rules.rules:
            baseline_results = self._process_axes(
                raw_axis_values,
                mode_state=active_mode_state,
                state=current_state,
                rule_evaluations=(),
                include_rules=False,
            )[2]
            rule_evaluations = evaluate_rules(
                self._workspace.rules.rules,
                _rule_context_from_axis_results(
                    baseline_results,
                    mode_state=active_mode_state,
                    active_buttons=active_buttons,
                ),
            )

        ordered_raw_values, final_output_values, axis_results, next_filter_states = self._process_axes(
            raw_axis_values,
            mode_state=active_mode_state,
            state=current_state,
            rule_evaluations=rule_evaluations,
            include_rules=True,
        )

        return WorkspaceSignalPipelineResult(
            raw_axis_values=ordered_raw_values,
            final_output_values=final_output_values,
            axis_results=axis_results,
            state=SignalPipelineState(next_filter_states),
            rule_evaluations=rule_evaluations,
        )

    def _process_axes(
        self,
        raw_axis_values: Mapping[str, float],
        *,
        mode_state: ModeState,
        state: SignalPipelineState,
        rule_evaluations: tuple[RuleEvaluationResult, ...],
        include_rules: bool,
    ) -> tuple[dict[str, float], dict[str, float], dict[str, AxisStackResult], dict[str, FilterState]]:
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
                mode_state=mode_state,
                rules=self._workspace.rules.rules if include_rules else (),
                rule_results=tuple(result for result in rule_evaluations if result.target_axis == axis_name),
                previous_filter_state=state.filter_state_for(axis_name),
            )
            ordered_raw_values[axis_name] = raw_value
            final_output_values[axis_name] = stack_result.final_output
            axis_results[axis_name] = stack_result
            next_filter_states[axis_name] = stack_result.filter_state

        return ordered_raw_values, final_output_values, axis_results, next_filter_states


def _rule_context_from_axis_results(
    axis_results: Mapping[str, AxisStackResult],
    *,
    mode_state: ModeState | None = None,
    active_buttons: tuple[int, ...] = (),
) -> RuleEvaluationContext:
    values_by_stage: dict[str, dict[str, float]] = {}
    for axis_name, result in axis_results.items():
        for stage in result.stages:
            values_by_stage.setdefault(stage.stage_name, {})[axis_name] = stage.output_value
        values_by_stage.setdefault("Final Output", {})[axis_name] = result.final_output
    active_modes: list[str] = []
    if mode_state is not None:
        if mode_state.precision_active:
            active_modes.append("Precision")
        if mode_state.combat_active:
            active_modes.append("Combat")
    return RuleEvaluationContext(
        values_by_stage=values_by_stage,
        active_modes=tuple(active_modes),
        active_buttons=tuple(int(button) for button in active_buttons),
    )
