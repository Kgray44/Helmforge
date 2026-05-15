from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared_core.math.curves import apply_output_limits, clamp, finite_float, s_curve_centered
from shared_core.math.deadzone import apply_center_deadzone
from shared_core.math.filtering import FilterState, step_filter
from shared_core.models.combat import AxisCombatProfile
from shared_core.models.filtering import AxisFiltering
from shared_core.models.modes import ModeConfig, StackMode
from shared_core.models.rules import ConditionalRule
from shared_core.models.tuning import AxisTuning
from shared_core.rules.evaluator import RuleEvaluationResult, RuleStatus


EXPECTED_STAGE_NAMES = (
    "Raw Input",
    "Center Conditioning",
    "Curve / Shape",
    "Base Output Limits",
    "Filtering",
    "Mode Modifiers",
    "Rule Injections",
    "Final Output",
)


@dataclass(frozen=True)
class ModeState:
    precision_active: bool = False
    combat_active: bool = False
    trigger_active: bool = False
    zoom_active: bool = False
    extra_active: bool = False


@dataclass(frozen=True)
class StageResult:
    stage_name: str
    input_value: float
    output_value: float
    delta: float
    active: bool
    explanation: str
    metadata: dict[str, Any] = field(default_factory=dict)
    injected_rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class AxisStackResult:
    final_output: float
    filter_state: FilterState
    stages: tuple[StageResult, ...]

    def stage_by_name(self, stage_name: str) -> StageResult:
        for stage in self.stages:
            if stage.stage_name == stage_name:
                return stage
        raise KeyError(stage_name)


def _stage(
    name: str,
    input_value: float,
    output_value: float,
    *,
    active: bool,
    explanation: str,
    metadata: dict[str, Any] | None = None,
    injected_rules: tuple[str, ...] = (),
) -> StageResult:
    safe_input = finite_float(input_value, 0.0)
    safe_output = finite_float(output_value, 0.0)
    return StageResult(
        stage_name=name,
        input_value=safe_input,
        output_value=safe_output,
        delta=safe_output - safe_input,
        active=active,
        explanation=explanation,
        metadata=metadata or {},
        injected_rules=injected_rules,
    )


def _apply_mode_modifiers(
    value: float,
    *,
    tuning: AxisTuning,
    combat: AxisCombatProfile,
    mode_config: ModeConfig,
    mode_state: ModeState,
) -> tuple[float, bool, dict[str, Any]]:
    output = value
    metadata: dict[str, Any] = {
        "precision_active": mode_state.precision_active,
        "combat_active": mode_state.combat_active,
        "stack_mode": mode_config.precision_combat_stack_mode.value,
    }

    precision_scale = finite_float(tuning.precision_scale, 1.0) if mode_state.precision_active else 1.0
    combat_scale = finite_float(combat.combat_scale, 1.0) if mode_state.combat_active else 1.0

    if mode_config.precision_combat_stack_mode is StackMode.MULTIPLY:
        if mode_state.precision_active:
            output *= precision_scale
        if mode_state.combat_active:
            output = s_curve_centered(output, curve_strength=finite_float(combat.combat_curve, 0.0))
            output *= combat_scale

    metadata["precision_scale"] = precision_scale
    metadata["combat_scale"] = combat_scale
    return output, mode_state.precision_active or mode_state.combat_active, metadata


def _effective_filtering_for_mode(
    filtering: AxisFiltering,
    combat: AxisCombatProfile,
    mode_state: ModeState,
) -> tuple[AxisFiltering, dict[str, Any]]:
    base_center_alpha = clamp(finite_float(filtering.center_alpha, 0.35), 0.0, 1.0)
    base_edge_alpha = clamp(finite_float(filtering.edge_alpha, 0.70), 0.0, 1.0)
    base_same_slew = max(0.0, abs(finite_float(filtering.same_slew_limit, 1.0)))
    base_reverse_slew = max(0.0, abs(finite_float(filtering.reverse_slew_limit, 0.65)))

    combat_filter_active = mode_state.combat_active
    if combat_filter_active:
        effective_center_alpha = clamp(finite_float(combat.combat_center_alpha, base_center_alpha), 0.0, 1.0)
        effective_edge_alpha = clamp(finite_float(combat.combat_edge_alpha, base_edge_alpha), 0.0, 1.0)
        effective_same_slew = max(0.0, abs(finite_float(combat.combat_same_slew, base_same_slew)))
        effective_reverse_slew = max(0.0, abs(finite_float(combat.combat_reverse_slew, base_reverse_slew)))
    else:
        effective_center_alpha = base_center_alpha
        effective_edge_alpha = base_edge_alpha
        effective_same_slew = base_same_slew
        effective_reverse_slew = base_reverse_slew

    effective_filtering = AxisFiltering(
        axis=filtering.axis,
        center_alpha=effective_center_alpha,
        edge_alpha=effective_edge_alpha,
        same_slew_limit=effective_same_slew,
        reverse_slew_limit=effective_reverse_slew,
    )
    metadata: dict[str, Any] = {
        "center_alpha": base_center_alpha,
        "edge_alpha": base_edge_alpha,
        "same_slew_limit": base_same_slew,
        "reverse_slew_limit": base_reverse_slew,
        "effective_center_alpha": effective_center_alpha,
        "effective_edge_alpha": effective_edge_alpha,
        "effective_same_slew_limit": effective_same_slew,
        "effective_reverse_slew_limit": effective_reverse_slew,
        "combat_filter_active": combat_filter_active,
    }
    if combat_filter_active:
        metadata.update(
            {
                "combat_center_alpha": effective_center_alpha,
                "combat_edge_alpha": effective_edge_alpha,
                "combat_same_slew": effective_same_slew,
                "combat_reverse_slew": effective_reverse_slew,
            }
        )
    return effective_filtering, metadata


def process_axis_stack(
    raw_value: float,
    *,
    tuning: AxisTuning,
    filtering: AxisFiltering,
    combat: AxisCombatProfile,
    mode_config: ModeConfig,
    mode_state: ModeState,
    rules: tuple[ConditionalRule, ...] = (),
    rule_results: tuple[RuleEvaluationResult, ...] = (),
    previous_filter_state: FilterState | None = None,
) -> AxisStackResult:
    stages: list[StageResult] = []

    raw = clamp(raw_value)
    stages.append(
        _stage(
            "Raw Input",
            raw_value,
            raw,
            active=True,
            explanation="Raw axis sample clamped to the normalized -1..1 signal range.",
        )
    )

    centered_input = raw
    if tuning.invert:
        centered_input = -centered_input
    centered = apply_center_deadzone(
        centered_input,
        deadzone=tuning.deadzone,
        anti_deadzone=tuning.anti_deadzone,
        hysteresis=tuning.hysteresis,
        previous_output=(previous_filter_state.previous_output if previous_filter_state is not None else None),
    )
    stages.append(
        _stage(
            "Center Conditioning",
            raw,
            centered.output,
            active=centered.active or tuning.invert,
            explanation="Applies invert, centered deadzone, anti-deadzone, and records hysteresis configuration.",
            metadata=centered.metadata | {"invert": tuning.invert},
        )
    )

    curve_mode, curve_mode_metadata = _curve_mode_metadata(tuning.curve_mode)
    curve_strength = clamp(tuning.curve_strength, 0.0, 1.0)
    curved = s_curve_centered(centered.output, curve_strength=curve_strength)
    stages.append(
        _stage(
            "Curve / Shape",
            centered.output,
            curved,
            active=curve_strength != 0.0,
            explanation="Applies centered cubic-blend S-curve y = (1-k)x + kx^3.",
            metadata=curve_mode_metadata | {"curve_mode": curve_mode, "curve_strength": curve_strength},
        )
    )

    output_scale, applied_limit_rules = _apply_base_output_limit_rules(tuning.output_scale, rule_results)
    configured_max_output = finite_float(tuning.max_output, 1.0)
    limited = apply_output_limits(curved, output_scale=output_scale, max_output=configured_max_output)
    stages.append(
        _stage(
            "Base Output Limits",
            curved,
            limited,
            active=output_scale != 1.0 or configured_max_output < 1.0 or bool(applied_limit_rules),
            explanation="Applies output scale and max output clamp.",
            metadata={
                "output_scale": output_scale,
                "configured_output_scale": finite_float(tuning.output_scale, 1.0),
                "max_output": configured_max_output,
                "injected_rules": applied_limit_rules,
            },
        )
    )

    effective_filtering, filtering_metadata = _effective_filtering_for_mode(filtering, combat, mode_state)
    filter_result = step_filter(
        target_value=limited,
        state=previous_filter_state or FilterState(),
        settings=effective_filtering,
    )
    stages.append(
        _stage(
            "Filtering",
            limited,
            filter_result.output,
            active=True,
            explanation="Applies center/edge alpha smoothing and same/reverse-direction slew limits.",
            metadata=filter_result.diagnostics | filtering_metadata,
        )
    )

    mode_output, mode_active, mode_metadata = _apply_mode_modifiers(
        filter_result.output,
        tuning=tuning,
        combat=combat,
        mode_config=mode_config,
        mode_state=mode_state,
    )
    mode_output = apply_output_limits(mode_output, output_scale=1.0, max_output=configured_max_output)
    stages.append(
        _stage(
            "Mode Modifiers",
            filter_result.output,
            mode_output,
            active=mode_active,
            explanation="Applies precision scale and combat curve/scale. Overlap uses multiply mode.",
            metadata=mode_metadata,
        )
    )

    if rule_results:
        active_rules = tuple(result.rule_title for result in rule_results if result.status is RuleStatus.ACTIVE)
        inactive_rules = tuple(result.rule_title for result in rule_results if result.status is RuleStatus.INACTIVE)
        blocked_rules = tuple(result.rule_title for result in rule_results if result.status is RuleStatus.BLOCKED)
        disabled_rules = tuple(result.rule_title for result in rule_results if result.status is RuleStatus.DISABLED)
        metadata = {
            "active_rules": active_rules,
            "inactive_rules": inactive_rules,
            "blocked_rules": blocked_rules,
            "disabled_rules": disabled_rules,
            "evaluations": tuple(_rule_result_metadata(result) for result in rule_results),
        }
        explanation = "Evaluates conditional rule state and reports any inline injections for this axis."
    else:
        active_rules = ()
        disabled_rules = tuple(rule.title for rule in rules if not rule.enabled)
        enabled_rules = tuple(rule.title for rule in rules if rule.enabled)
        metadata = {"disabled_rules": disabled_rules, "enabled_rules_deferred": enabled_rules}
        explanation = "Rule evaluation is deferred; disabled rules are reported and do not affect output."
    stages.append(
        _stage(
            "Rule Injections",
            mode_output,
            mode_output,
            active=bool(active_rules),
            explanation=explanation,
            metadata=metadata,
            injected_rules=active_rules,
        )
    )

    max_output = abs(configured_max_output)
    final = clamp(mode_output, -max_output, max_output)
    stages.append(
        _stage(
            "Final Output",
            mode_output,
            final,
            active=True,
            explanation="Final normalized output after the recovered processing pipeline.",
        )
    )

    return AxisStackResult(
        final_output=final,
        filter_state=filter_result.state,
        stages=tuple(stages),
    )


def _curve_mode_metadata(curve_mode: object) -> tuple[str, dict[str, Any]]:
    requested = str(curve_mode or "s").strip()
    normalized = requested.casefold() or "s"
    if normalized == "s":
        return "s", {"requested_curve_mode": requested or "s", "curve_mode_supported": True}
    return "s", {"requested_curve_mode": requested, "curve_mode_supported": False}


def _apply_base_output_limit_rules(
    configured_output_scale: float,
    rule_results: tuple[RuleEvaluationResult, ...],
) -> tuple[float, tuple[str, ...]]:
    output_scale = finite_float(configured_output_scale, 1.0)
    applied_rules: list[str] = []
    for result in rule_results:
        if result.status is not RuleStatus.ACTIVE:
            continue
        if result.injection_stage != "Base Output Limits":
            continue
        if result.parameter != "Output Scale":
            continue
        if result.operation == "Set":
            output_scale = finite_float(result.value, output_scale)
        elif result.operation == "Add":
            output_scale += finite_float(result.value, 0.0)
        elif result.operation == "Multiply":
            output_scale *= finite_float(result.value, 1.0)
        else:
            continue
        applied_rules.append(result.rule_title)
    return output_scale, tuple(applied_rules)


def _rule_result_metadata(result: RuleEvaluationResult) -> dict[str, Any]:
    return {
        "rule_title": result.rule_title,
        "status": result.status.value,
        "applies": result.applies,
        "blocked_reason": result.blocked_reason,
        "target_axis": result.target_axis,
        "parameter": result.parameter,
        "operation": result.operation,
        "value": result.value,
        "injection_stage": result.injection_stage,
        "summary": result.summary,
        "metadata": dict(result.metadata),
    }
