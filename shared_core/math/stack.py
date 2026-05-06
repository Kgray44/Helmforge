from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared_core.math.curves import apply_output_limits, clamp, s_curve_centered
from shared_core.math.deadzone import apply_center_deadzone
from shared_core.math.filtering import FilterState, step_filter
from shared_core.models.combat import AxisCombatProfile
from shared_core.models.filtering import AxisFiltering
from shared_core.models.modes import ModeConfig, StackMode
from shared_core.models.rules import ConditionalRule
from shared_core.models.tuning import AxisTuning


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
    return StageResult(
        stage_name=name,
        input_value=input_value,
        output_value=output_value,
        delta=output_value - input_value,
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

    precision_scale = tuning.precision_scale if mode_state.precision_active else 1.0
    combat_scale = combat.combat_scale if mode_state.combat_active else 1.0

    if mode_config.precision_combat_stack_mode is StackMode.MULTIPLY:
        if mode_state.precision_active:
            output *= precision_scale
        if mode_state.combat_active:
            output = s_curve_centered(output, curve_strength=combat.combat_curve)
            output *= combat_scale

    metadata["precision_scale"] = precision_scale
    metadata["combat_scale"] = combat_scale
    return output, mode_state.precision_active or mode_state.combat_active, metadata


def process_axis_stack(
    raw_value: float,
    *,
    tuning: AxisTuning,
    filtering: AxisFiltering,
    combat: AxisCombatProfile,
    mode_config: ModeConfig,
    mode_state: ModeState,
    rules: tuple[ConditionalRule, ...] = (),
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

    curved = s_curve_centered(centered.output, curve_strength=tuning.curve_strength)
    stages.append(
        _stage(
            "Curve / Shape",
            centered.output,
            curved,
            active=tuning.curve_strength != 0.0,
            explanation="Applies centered cubic-blend S-curve y = (1-k)x + kx^3.",
            metadata={"curve_mode": tuning.curve_mode, "curve_strength": tuning.curve_strength},
        )
    )

    limited = apply_output_limits(curved, output_scale=tuning.output_scale, max_output=tuning.max_output)
    stages.append(
        _stage(
            "Base Output Limits",
            curved,
            limited,
            active=tuning.output_scale != 1.0 or tuning.max_output < 1.0,
            explanation="Applies output scale and max output clamp.",
            metadata={"output_scale": tuning.output_scale, "max_output": tuning.max_output},
        )
    )

    filter_result = step_filter(
        target_value=limited,
        state=previous_filter_state or FilterState(),
        settings=filtering,
    )
    stages.append(
        _stage(
            "Filtering",
            limited,
            filter_result.output,
            active=True,
            explanation="Applies center/edge alpha smoothing and same/reverse-direction slew limits.",
            metadata=filter_result.diagnostics,
        )
    )

    mode_output, mode_active, mode_metadata = _apply_mode_modifiers(
        filter_result.output,
        tuning=tuning,
        combat=combat,
        mode_config=mode_config,
        mode_state=mode_state,
    )
    mode_output = apply_output_limits(mode_output, output_scale=1.0, max_output=tuning.max_output)
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

    enabled_rules = tuple(rule.title for rule in rules if rule.enabled)
    disabled_rules = tuple(rule.title for rule in rules if not rule.enabled)
    stages.append(
        _stage(
            "Rule Injections",
            mode_output,
            mode_output,
            active=bool(enabled_rules),
            explanation="Rule evaluation is deferred; disabled rules are reported and do not affect output.",
            metadata={"disabled_rules": disabled_rules, "enabled_rules_deferred": enabled_rules},
            injected_rules=enabled_rules,
        )
    )

    final = clamp(mode_output, -abs(tuning.max_output), abs(tuning.max_output))
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
