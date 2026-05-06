from __future__ import annotations

from dataclasses import replace

import pytest

from shared_core.math.pipeline import WorkspaceSignalPipeline
from shared_core.math.stack import ModeState, process_axis_stack
from shared_core.models.filtering import AxisFiltering
from shared_core.models.rules import yaw_roll_example_rule
from shared_core.models.workspace import create_default_workspace
from shared_core.models.combat import AxisCombatProfile
from shared_core.models.modes import default_mode_config
from shared_core.models.tuning import AxisTuning
from shared_core.rules.evaluator import (
    RuleEvaluationContext,
    RuleStatus,
    evaluate_rule,
    rule_detail_sentence,
    rule_preview_sentence,
)


def _context(roll_final: float) -> RuleEvaluationContext:
    return RuleEvaluationContext(
        values_by_stage={
            "Final Output": {
                "Roll": roll_final,
                "Yaw": 0.5,
            }
        }
    )


def test_phase7_disabled_rule_does_not_apply_and_reports_disabled():
    rule = yaw_roll_example_rule()

    result = evaluate_rule(rule, _context(0.8))

    assert result.status is RuleStatus.DISABLED
    assert result.applies is False
    assert result.blocked_reason is None
    assert result.injection_stage == "Base Output Limits"


def test_phase7_enabled_rule_applies_when_condition_true_and_inactive_when_false():
    rule = replace(yaw_roll_example_rule(), enabled=True)

    active = evaluate_rule(rule, _context(0.36))
    inactive = evaluate_rule(rule, _context(0.35))

    assert active.status is RuleStatus.ACTIVE
    assert active.applies is True
    assert active.metadata["measured_value"] == pytest.approx(0.36)
    assert active.metadata["effective_change"]["parameter"] == "Output Scale"
    assert inactive.status is RuleStatus.INACTIVE
    assert inactive.applies is False


def test_phase7_invalid_rule_reports_blocked_instead_of_crashing():
    rule = replace(yaw_roll_example_rule(), enabled=True, target_axis="Nope")

    result = evaluate_rule(rule, _context(0.8))

    assert result.status is RuleStatus.BLOCKED
    assert result.applies is False
    assert "target axis" in result.blocked_reason.lower()


def test_phase7_mode_and_button_gates_can_hold_rule_inactive():
    rule = replace(yaw_roll_example_rule(), enabled=True, mode_gate="Combat", buttons=(5,))

    inactive = evaluate_rule(rule, _context(0.8))
    active = evaluate_rule(
        rule,
        RuleEvaluationContext(
            values_by_stage={"Final Output": {"Roll": 0.8, "Yaw": 0.5}},
            active_modes=("Combat",),
            active_buttons=(5,),
        ),
    )

    assert inactive.status is RuleStatus.INACTIVE
    assert inactive.applies is False
    assert active.status is RuleStatus.ACTIVE


def test_phase7_rule_preview_and_detail_use_recovered_wording():
    rule = yaw_roll_example_rule()

    assert rule_detail_sentence(rule) == "Targets Yaw. Watches Roll Final Output > 0.35. Set Output Scale."
    assert rule_preview_sentence(rule) == (
        "Set Yaw Output Scale to 0.75 when absolute Roll final output is greater than 0.35."
    )


def test_phase7_stack_reports_rule_injection_metadata_without_affecting_disabled_rule():
    rule = yaw_roll_example_rule()
    tuning = AxisTuning(
        axis="Yaw",
        curve_strength=0.0,
        deadzone=0.0,
        output_scale=1.0,
        max_output=1.0,
    )
    filtering = AxisFiltering("Yaw", center_alpha=1.0, edge_alpha=1.0, same_slew_limit=10.0, reverse_slew_limit=10.0)
    combat = AxisCombatProfile("Yaw", combat_curve=0.0, combat_scale=1.0)

    result = process_axis_stack(
        0.8,
        tuning=tuning,
        filtering=filtering,
        combat=combat,
        mode_config=default_mode_config(),
        mode_state=ModeState(),
        rules=(rule,),
    )
    rule_stage = result.stage_by_name("Rule Injections")

    assert result.final_output == pytest.approx(0.8)
    assert rule_stage.metadata["disabled_rules"] == ("Yaw 0.75 | Roll > 0.35",)
    assert rule_stage.injected_rules == ()


def test_phase7_workspace_pipeline_enabled_example_can_scale_yaw_output():
    workspace = create_default_workspace()
    workspace = replace(
        workspace,
        rules=replace(workspace.rules, rules=(replace(yaw_roll_example_rule(), enabled=True),)),
    )
    pipeline = WorkspaceSignalPipeline(workspace)
    raw = {
        "Roll": 0.8,
        "Pitch": 0.0,
        "Throttle": 0.0,
        "Yaw": 0.8,
        "Aux 1": 0.0,
        "Aux 2": 0.0,
    }

    result = pipeline.process(raw, mode_state=ModeState())
    yaw = result.axis_results["Yaw"]

    assert result.final_output_values["Yaw"] < result.final_output_values["Roll"]
    assert yaw.stage_by_name("Base Output Limits").metadata["output_scale"] == pytest.approx(0.75)
    assert yaw.stage_by_name("Rule Injections").injected_rules == ("Yaw 0.75 | Roll > 0.35",)
