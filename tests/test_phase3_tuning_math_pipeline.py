from dataclasses import replace

import pytest

from shared_core.math.curves import (
    apply_centered_curve,
    apply_output_limits,
    linear_reference_points,
    s_curve_centered,
)
from shared_core.math.deadzone import apply_center_deadzone
from shared_core.math.filtering import FilterState, step_filter
from shared_core.math.stack import (
    EXPECTED_STAGE_NAMES,
    ModeState,
    process_axis_stack,
)
from shared_core.models.combat import AxisCombatProfile
from shared_core.models.filtering import AxisFiltering
from shared_core.models.modes import StackMode, default_mode_config
from shared_core.models.rules import yaw_roll_example_rule
from shared_core.models.tuning import AxisTuning
from shared_core.runtime.runtime_bridge import RuntimeBridge


def test_s_curve_is_odd_symmetric_and_preserves_sign():
    positive = s_curve_centered(0.6, curve_strength=0.7)
    negative = s_curve_centered(-0.6, curve_strength=0.7)

    assert positive > 0
    assert negative < 0
    assert positive == pytest.approx(-negative)


def test_curve_strength_zero_is_linear_and_curve_helper_clamps():
    assert s_curve_centered(0.42, curve_strength=0.0) == pytest.approx(0.42)
    assert apply_centered_curve(2.0, curve_strength=0.0, output_scale=2.0, max_output=0.75) == 0.75
    assert apply_output_limits(-2.0, output_scale=2.0, max_output=0.5) == -0.5


def test_linear_reference_points_are_true_y_equals_x():
    points = linear_reference_points(sample_count=5)

    assert points == (
        (-1.0, -1.0),
        (-0.5, -0.5),
        (0.0, 0.0),
        (0.5, 0.5),
        (1.0, 1.0),
    )


def test_deadzone_zeroes_center_and_remaps_remaining_range():
    assert apply_center_deadzone(0.05, deadzone=0.1).output == 0.0
    assert apply_center_deadzone(-0.05, deadzone=0.1).output == 0.0

    result = apply_center_deadzone(0.55, deadzone=0.10)

    assert result.output == pytest.approx(0.5)
    assert result.metadata["remapped"] is True


def test_anti_deadzone_creates_initial_output_after_deadzone():
    result = apply_center_deadzone(0.11, deadzone=0.10, anti_deadzone=0.20)

    assert result.output > 0.20
    assert result.metadata["anti_deadzone"] == 0.20


def test_deadzone_edge_cases_are_safe():
    assert apply_center_deadzone(1.0, deadzone=1.0).output == 0.0
    assert apply_center_deadzone(-1.0, deadzone=2.0).output == 0.0
    assert apply_center_deadzone(2.0, deadzone=-1.0).output == 1.0


def test_hysteresis_can_delay_exit_from_center_state():
    held = apply_center_deadzone(0.12, deadzone=0.10, hysteresis=0.05, previous_output=0.0)
    released = apply_center_deadzone(0.16, deadzone=0.10, hysteresis=0.05, previous_output=0.0)

    assert held.output == 0.0
    assert held.metadata["hysteresis_active"] is True
    assert released.output > 0.0


def test_filtering_same_direction_and_reverse_slew_limits():
    settings = AxisFiltering("Roll", center_alpha=1.0, edge_alpha=1.0, same_slew_limit=0.25, reverse_slew_limit=0.10)

    same = step_filter(target_value=1.0, state=FilterState(previous_output=0.0), settings=settings)
    reverse = step_filter(target_value=-1.0, state=FilterState(previous_output=0.8), settings=settings)

    assert same.output == pytest.approx(0.25)
    assert same.diagnostics["slew_path"] == "same-direction"
    assert reverse.output == pytest.approx(0.70)
    assert reverse.diagnostics["slew_path"] == "reverse-direction"


def test_filtering_uses_center_vs_edge_alpha_behavior():
    settings = AxisFiltering("Roll", center_alpha=0.20, edge_alpha=0.80, same_slew_limit=1.0, reverse_slew_limit=1.0)

    center = step_filter(target_value=0.10, state=FilterState(previous_output=0.0), settings=settings)
    edge = step_filter(target_value=1.0, state=FilterState(previous_output=0.0), settings=settings)

    assert center.diagnostics["alpha_region"] == "center"
    assert edge.diagnostics["alpha_region"] == "edge"
    assert center.output < edge.output
    assert edge.output == pytest.approx(0.8)


def _identity_filtering() -> AxisFiltering:
    return AxisFiltering("Roll", center_alpha=1.0, edge_alpha=1.0, same_slew_limit=10.0, reverse_slew_limit=10.0)


def _linear_tuning() -> AxisTuning:
    return AxisTuning(
        axis="Roll",
        curve_strength=0.0,
        deadzone=0.0,
        anti_deadzone=0.0,
        output_scale=1.0,
        max_output=1.0,
        precision_scale=0.5,
    )


def _combat_profile() -> AxisCombatProfile:
    return AxisCombatProfile(
        axis="Roll",
        combat_curve=0.0,
        combat_scale=0.5,
        combat_center_alpha=1.0,
        combat_edge_alpha=1.0,
        combat_same_slew=10.0,
        combat_reverse_slew=10.0,
    )


def test_precision_and_combat_modes_change_output_and_multiply_together():
    mode_config = default_mode_config()
    tuning = _linear_tuning()
    filtering = _identity_filtering()
    combat = _combat_profile()

    normal = process_axis_stack(0.8, tuning=tuning, filtering=filtering, combat=combat, mode_config=mode_config, mode_state=ModeState())
    precision = process_axis_stack(0.8, tuning=tuning, filtering=filtering, combat=combat, mode_config=mode_config, mode_state=ModeState(precision_active=True))
    combat_only = process_axis_stack(0.8, tuning=tuning, filtering=filtering, combat=combat, mode_config=mode_config, mode_state=ModeState(combat_active=True))
    both = process_axis_stack(0.8, tuning=tuning, filtering=filtering, combat=combat, mode_config=mode_config, mode_state=ModeState(precision_active=True, combat_active=True))

    assert mode_config.precision_combat_stack_mode is StackMode.MULTIPLY
    assert normal.final_output == pytest.approx(0.8)
    assert precision.final_output == pytest.approx(0.4)
    assert combat_only.final_output == pytest.approx(0.4)
    assert both.final_output == pytest.approx(0.2)


def test_stack_result_contains_expected_stages_and_clamped_final_output():
    result = process_axis_stack(
        2.0,
        tuning=replace(_linear_tuning(), output_scale=3.0, max_output=0.6),
        filtering=_identity_filtering(),
        combat=_combat_profile(),
        mode_config=default_mode_config(),
        mode_state=ModeState(),
    )

    assert tuple(stage.stage_name for stage in result.stages) == EXPECTED_STAGE_NAMES
    assert result.final_output == pytest.approx(0.6)
    assert result.stages[-1].stage_name == "Final Output"
    assert result.stages[-1].output_value == pytest.approx(result.final_output)


def test_disabled_rule_placeholder_does_not_affect_output_but_is_reported():
    rule = yaw_roll_example_rule()
    result = process_axis_stack(
        0.8,
        tuning=_linear_tuning(),
        filtering=_identity_filtering(),
        combat=_combat_profile(),
        mode_config=default_mode_config(),
        mode_state=ModeState(),
        rules=(rule,),
    )
    rule_stage = result.stage_by_name("Rule Injections")

    assert rule.enabled is False
    assert result.final_output == pytest.approx(0.8)
    assert rule_stage.active is False
    assert rule_stage.metadata["disabled_rules"] == ("Yaw 0.75 | Roll > 0.35",)


def test_runtime_bridge_keeps_truth_and_processes_simulated_outputs_through_stack():
    bridge = RuntimeBridge(deterministic_simulation=True)

    snapshot = bridge.snapshot()

    assert snapshot.runtime_status.mode.value == "simulated"
    assert snapshot.runtime_status.truth.value in {"simulated", "blocked_missing_driver", "blocked_missing_device", "detected_unverified"}
    assert snapshot.simulated is True
    assert snapshot.raw_axis_values["Pitch"] == pytest.approx(0.25)
    assert snapshot.final_output_values["Pitch"] != pytest.approx(snapshot.raw_axis_values["Pitch"])
