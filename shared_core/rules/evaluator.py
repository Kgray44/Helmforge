from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from shared_core.models.axes import axis_by_name
from shared_core.models.rules import ConditionalRule


class RuleStatus(str, Enum):
    DISABLED = "Disabled"
    INACTIVE = "Inactive"
    ACTIVE = "Active"
    BLOCKED = "Blocked"


SUPPORTED_PARAMETERS = ("Output Scale",)
SUPPORTED_OPERATIONS = ("Set", "Add", "Multiply")
SUPPORTED_INJECTION_STAGES = ("Base Output Limits",)
SUPPORTED_MEASURES = ("absolute", "signed", "raw")
SUPPORTED_MODE_GATES = ("Always", "Precision", "Combat")
SUPPORTED_BUTTON_TESTS = ("Any", "All")
SUPPORTED_COMPARATORS = (
    "greater than",
    "less than",
    "equal",
    "approximately",
    "between",
    "range",
)


@dataclass(frozen=True)
class RuleEvaluationContext:
    values_by_stage: Mapping[str, Mapping[str, float]]
    active_modes: tuple[str, ...] = ()
    active_buttons: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "values_by_stage",
            MappingProxyType(
                {
                    str(stage): MappingProxyType({str(axis): float(value) for axis, value in values.items()})
                    for stage, values in self.values_by_stage.items()
                }
            ),
        )


@dataclass(frozen=True)
class RuleEvaluationResult:
    rule_title: str
    status: RuleStatus
    applies: bool
    blocked_reason: str | None
    target_axis: str
    parameter: str
    operation: str
    value: float
    injection_stage: str
    summary: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def evaluate_rules(
    rules: tuple[ConditionalRule, ...],
    context: RuleEvaluationContext,
) -> tuple[RuleEvaluationResult, ...]:
    return tuple(evaluate_rule(rule, context) for rule in rules)


def evaluate_rule(rule: ConditionalRule, context: RuleEvaluationContext) -> RuleEvaluationResult:
    if not rule.enabled:
        return _result(rule, RuleStatus.DISABLED, applies=False, metadata={"enabled": False})

    blocked_reason = _validation_error(rule)
    if blocked_reason:
        return _result(rule, RuleStatus.BLOCKED, applies=False, blocked_reason=blocked_reason)

    mode_gate_match = _mode_gate_matches(rule, context)
    button_gate_match = _button_gate_matches(rule, context)
    if not mode_gate_match or not button_gate_match:
        return _result(
            rule,
            RuleStatus.INACTIVE,
            applies=False,
            metadata={
                "mode_gate_match": mode_gate_match,
                "button_gate_match": button_gate_match,
            },
        )

    try:
        reference_value = _reference_value(context, rule.stage, rule.reference_axis)
    except KeyError as exc:
        return _result(rule, RuleStatus.BLOCKED, applies=False, blocked_reason=str(exc).strip("'"))

    measured = _measure(reference_value, rule.measure)
    comparator_match = _compare(
        measured,
        comparator=rule.comparator,
        threshold=float(rule.threshold),
        threshold_high=rule.threshold_high,
    )
    if comparator_match is None:
        return _result(
            rule,
            RuleStatus.BLOCKED,
            applies=False,
            blocked_reason=f"Comparator {rule.comparator!r} requires threshold high.",
            metadata={"reference_value": reference_value, "measured_value": measured},
        )

    metadata = {
        "reference_value": reference_value,
        "measured_value": measured,
        "reference_axis": rule.reference_axis,
        "reference_stage": rule.stage,
        "measure": rule.measure,
        "comparator": rule.comparator,
        "threshold": float(rule.threshold),
        "threshold_high": None if rule.threshold_high is None else float(rule.threshold_high),
        "effective_change": {
            "target_axis": rule.target_axis,
            "parameter": rule.parameter,
            "operation": rule.operation,
            "value": float(rule.value),
            "injection_stage": rule.injection_stage,
        },
    }
    if comparator_match:
        return _result(rule, RuleStatus.ACTIVE, applies=True, metadata=metadata)
    return _result(rule, RuleStatus.INACTIVE, applies=False, metadata=metadata)


def status_counts(results: tuple[RuleEvaluationResult, ...]) -> dict[str, int]:
    return {
        "total": len(results),
        "active": sum(1 for result in results if result.status is RuleStatus.ACTIVE),
        "blocked": sum(1 for result in results if result.status is RuleStatus.BLOCKED),
        "disabled": sum(1 for result in results if result.status is RuleStatus.DISABLED),
        "inactive": sum(1 for result in results if result.status is RuleStatus.INACTIVE),
    }


def rule_preview_sentence(rule: ConditionalRule) -> str:
    return (
        f"{rule.operation} {rule.target_axis} {rule.parameter} to {_format_number(rule.value)} "
        f"when {rule.measure} {rule.reference_axis} {rule.stage.lower()} is "
        f"{rule.comparator} {_format_number(rule.threshold)}."
    )


def rule_detail_sentence(rule: ConditionalRule) -> str:
    comparator_symbol = {
        "greater than": ">",
        "less than": "<",
        "equal": "=",
        "approximately": "~",
        "between": "between",
        "range": "range",
    }.get(rule.comparator.casefold(), rule.comparator)
    if comparator_symbol in {"between", "range"} and rule.threshold_high is not None:
        condition = f"{_title_stage(rule.stage)} {comparator_symbol} {_format_number(rule.threshold)} and {_format_number(rule.threshold_high)}"
    else:
        condition = f"{_title_stage(rule.stage)} {comparator_symbol} {_format_number(rule.threshold)}"
    return f"Targets {rule.target_axis}. Watches {rule.reference_axis} {condition}. {rule.operation} {rule.parameter}."


def _result(
    rule: ConditionalRule,
    status: RuleStatus,
    *,
    applies: bool,
    blocked_reason: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> RuleEvaluationResult:
    return RuleEvaluationResult(
        rule_title=rule.title,
        status=status,
        applies=applies,
        blocked_reason=blocked_reason,
        target_axis=rule.target_axis,
        parameter=rule.parameter,
        operation=rule.operation,
        value=float(rule.value),
        injection_stage=rule.injection_stage,
        summary=rule_preview_sentence(rule),
        metadata=metadata or {},
    )


def _validation_error(rule: ConditionalRule) -> str | None:
    try:
        axis_by_name(rule.target_axis)
    except KeyError:
        return f"Unknown target axis: {rule.target_axis}"
    try:
        axis_by_name(rule.reference_axis)
    except KeyError:
        return f"Unknown reference axis: {rule.reference_axis}"
    if rule.parameter not in SUPPORTED_PARAMETERS:
        return f"Unsupported parameter: {rule.parameter}"
    if rule.operation not in SUPPORTED_OPERATIONS:
        return f"Unsupported operation: {rule.operation}"
    if rule.injection_stage not in SUPPORTED_INJECTION_STAGES:
        return f"Unsupported injection stage: {rule.injection_stage}"
    if rule.measure.casefold() not in SUPPORTED_MEASURES:
        return f"Unsupported measure: {rule.measure}"
    if rule.comparator.casefold() not in SUPPORTED_COMPARATORS:
        return f"Unsupported comparator: {rule.comparator}"
    if rule.mode_gate not in SUPPORTED_MODE_GATES:
        return f"Unsupported mode gate: {rule.mode_gate}"
    if rule.button_test not in SUPPORTED_BUTTON_TESTS:
        return f"Unsupported button test: {rule.button_test}"
    try:
        float(rule.value)
        float(rule.threshold)
    except (TypeError, ValueError):
        return "Rule value and threshold must be numeric."
    if rule.threshold_high is not None:
        try:
            float(rule.threshold_high)
        except (TypeError, ValueError):
            return "Threshold high must be numeric when provided."
    return None


def _mode_gate_matches(rule: ConditionalRule, context: RuleEvaluationContext) -> bool:
    if rule.mode_gate == "Always":
        return True
    active_modes = {mode.casefold() for mode in context.active_modes}
    return rule.mode_gate.casefold() in active_modes


def _button_gate_matches(rule: ConditionalRule, context: RuleEvaluationContext) -> bool:
    if not rule.buttons:
        return True
    active_buttons = set(context.active_buttons)
    required_buttons = set(rule.buttons)
    if rule.button_test == "All":
        return required_buttons <= active_buttons
    return bool(required_buttons & active_buttons)


def _reference_value(context: RuleEvaluationContext, stage: str, axis: str) -> float:
    for stage_name, values in context.values_by_stage.items():
        if stage_name.casefold() != stage.casefold():
            continue
        for axis_name, value in values.items():
            if axis_name.casefold() == axis.casefold():
                return float(value)
        raise KeyError(f"Reference axis {axis!r} was not present at stage {stage!r}.")
    raise KeyError(f"Reference stage {stage!r} was not present.")


def _measure(value: float, measure: str) -> float:
    if measure.casefold() == "absolute":
        return abs(value)
    return value


def _compare(
    measured: float,
    *,
    comparator: str,
    threshold: float,
    threshold_high: float | None,
) -> bool | None:
    normalized = comparator.casefold()
    if normalized == "greater than":
        return measured > threshold
    if normalized == "less than":
        return measured < threshold
    if normalized in {"equal", "approximately"}:
        return abs(measured - threshold) <= 0.001
    if normalized in {"between", "range"}:
        if threshold_high is None:
            return None
        low = min(threshold, float(threshold_high))
        high = max(threshold, float(threshold_high))
        return low <= measured <= high
    return False


def _format_number(value: float | int | None) -> str:
    if value is None:
        return "None"
    numeric = float(value)
    text = f"{numeric:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def _title_stage(stage: str) -> str:
    return " ".join(word.capitalize() for word in stage.split())
