from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConditionalRule:
    title: str
    enabled: bool
    target_axis: str
    parameter: str
    operation: str
    value: float
    injection_stage: str
    mode_gate: str
    buttons: tuple[int, ...] = ()
    button_test: str = "Any"
    reference_axis: str = "Roll"
    stage: str = "Final Output"
    measure: str = "absolute"
    comparator: str = "greater than"
    threshold: float = 0.35
    threshold_high: float | None = None


@dataclass(frozen=True)
class RuleConfig:
    rules: tuple[ConditionalRule, ...] = field(default_factory=tuple)


def yaw_roll_example_rule() -> ConditionalRule:
    return ConditionalRule(
        title="Yaw 0.75 | Roll > 0.35",
        enabled=False,
        target_axis="Yaw",
        parameter="Output Scale",
        operation="Set",
        value=0.75,
        injection_stage="Base Output Limits",
        mode_gate="Always",
        reference_axis="Roll",
        stage="Final Output",
        measure="absolute",
        comparator="greater than",
        threshold=0.35,
    )


def default_conditional_rules() -> tuple[ConditionalRule, ...]:
    return (yaw_roll_example_rule(),)


def default_rule_config() -> RuleConfig:
    return RuleConfig(rules=default_conditional_rules())

