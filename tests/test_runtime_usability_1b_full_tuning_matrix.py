from __future__ import annotations

import ast
import math
import random
from dataclasses import replace
from itertools import combinations
from pathlib import Path

import pytest

from shared_core.math.curves import apply_output_limits, s_curve_centered
from shared_core.math.deadzone import apply_center_deadzone
from shared_core.math.filtering import FilterState, step_filter
from shared_core.math.pipeline import WorkspaceSignalPipeline
from shared_core.math.stack import EXPECTED_STAGE_NAMES, ModeState, process_axis_stack
from shared_core.models.axes import AXIS_DISPLAY_NAMES, all_axis_definitions
from shared_core.models.combat import AxisCombatProfile
from shared_core.models.filtering import AxisFiltering
from shared_core.models.mappings import AxisMapping, ButtonMapping, MappingConfig
from shared_core.models.modes import ModeConfig, StackMode
from shared_core.models.rules import ConditionalRule, RuleConfig, yaw_roll_example_rule
from shared_core.models.runtime import RuntimeSnapshot, simulation_fallback_status
from shared_core.models.tuning import AxisTuning
from shared_core.models.workspace import create_default_workspace
from shared_core.rules.evaluator import (
    SUPPORTED_COMPARATORS,
    SUPPORTED_INJECTION_STAGES,
    SUPPORTED_OPERATIONS,
    SUPPORTED_PARAMETERS,
    RuleEvaluationContext,
    RuleStatus,
    evaluate_rule,
)
from shared_core.runtime.runtime_orchestrator import RuntimeOrchestrator, RuntimeOrchestratorConfig
from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend, build_workspace_virtual_output_intent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VJOY_AXES = ("X", "Y", "Z", "RX", "RY", "RZ")
SUPPORTED_CURVE_MODES = ("s",)
NUMERIC_PARAMETERS = (
    "curve_strength",
    "deadzone",
    "anti_deadzone",
    "hysteresis",
    "output_scale",
    "max_output",
    "precision_scale",
    "center_alpha",
    "edge_alpha",
    "same_slew_limit",
    "reverse_slew_limit",
    "combat_curve",
    "combat_scale",
    "combat_center_alpha",
    "combat_edge_alpha",
    "combat_same_slew",
    "combat_reverse_slew",
)


def _linear_tuning(axis: str = "Roll", **overrides) -> AxisTuning:
    return AxisTuning(
        axis=axis,
        curve_mode=overrides.pop("curve_mode", "s"),
        curve_strength=overrides.pop("curve_strength", 0.0),
        deadzone=overrides.pop("deadzone", 0.0),
        anti_deadzone=overrides.pop("anti_deadzone", 0.0),
        hysteresis=overrides.pop("hysteresis", 0.0),
        output_scale=overrides.pop("output_scale", 1.0),
        max_output=overrides.pop("max_output", 1.0),
        precision_scale=overrides.pop("precision_scale", 1.0),
        invert=overrides.pop("invert", False),
    )


def _identity_filtering(axis: str = "Roll", **overrides) -> AxisFiltering:
    return AxisFiltering(
        axis=axis,
        center_alpha=overrides.pop("center_alpha", 1.0),
        edge_alpha=overrides.pop("edge_alpha", 1.0),
        same_slew_limit=overrides.pop("same_slew_limit", 10.0),
        reverse_slew_limit=overrides.pop("reverse_slew_limit", 10.0),
    )


def _combat(axis: str = "Roll", **overrides) -> AxisCombatProfile:
    return AxisCombatProfile(
        axis=axis,
        combat_curve=overrides.pop("combat_curve", 0.0),
        combat_scale=overrides.pop("combat_scale", 1.0),
        combat_center_alpha=overrides.pop("combat_center_alpha", 1.0),
        combat_edge_alpha=overrides.pop("combat_edge_alpha", 1.0),
        combat_same_slew=overrides.pop("combat_same_slew", 10.0),
        combat_reverse_slew=overrides.pop("combat_reverse_slew", 10.0),
    )


def _raw(**overrides: float) -> dict[str, float]:
    values = {axis: 0.0 for axis in AXIS_DISPLAY_NAMES}
    values.update({axis: float(value) for axis, value in overrides.items()})
    return values


def _buttons(*pressed: int) -> dict[str, bool]:
    active = set(pressed)
    return {f"B{index}": index in active for index in range(1, 16)}


def _workspace_for_axes(
    *,
    tuning_by_id: dict[str, AxisTuning] | None = None,
    filtering_by_id: dict[str, AxisFiltering] | None = None,
    combat_by_id: dict[str, AxisCombatProfile] | None = None,
    mappings: MappingConfig | None = None,
    modes: ModeConfig | None = None,
    rules: tuple[ConditionalRule, ...] | None = None,
):
    workspace = create_default_workspace()
    if tuning_by_id is not None:
        workspace = replace(workspace, tuning=replace(workspace.tuning, axes=tuning_by_id))
    if filtering_by_id is not None:
        workspace = replace(workspace, filtering=replace(workspace.filtering, axes=filtering_by_id))
    if combat_by_id is not None:
        workspace = replace(workspace, combat=replace(workspace.combat, axes=combat_by_id))
    if mappings is not None:
        workspace = replace(workspace, mappings=mappings)
    if modes is not None:
        workspace = replace(workspace, modes=modes)
    if rules is not None:
        workspace = replace(workspace, rules=RuleConfig(rules=rules))
    return workspace


def _all_axis_tuning(**kwargs) -> dict[str, AxisTuning]:
    return {axis.axis_id.value: _linear_tuning(axis.display_name, **kwargs) for axis in all_axis_definitions()}


def _all_axis_filtering(**kwargs) -> dict[str, AxisFiltering]:
    return {axis.axis_id.value: _identity_filtering(axis.display_name, **kwargs) for axis in all_axis_definitions()}


def _all_axis_combat(**kwargs) -> dict[str, AxisCombatProfile]:
    return {axis.axis_id.value: _combat(axis.display_name, **kwargs) for axis in all_axis_definitions()}


def _runtime_frame(workspace, raw_values, *, buttons=None, hat_state: str = "Centered"):
    status = simulation_fallback_status()
    orchestrator = RuntimeOrchestrator(
        workspace=workspace,
        runtime_status=status,
        config=RuntimeOrchestratorConfig(deterministic_simulation=True),
    )
    snapshot = RuntimeSnapshot(
        raw_axis_values=raw_values,
        final_output_values={axis: 0.0 for axis in AXIS_DISPLAY_NAMES},
        button_states=buttons or _buttons(),
        hat_state=hat_state,
        runtime_status=status,
        simulated=True,
    )
    return orchestrator.build_frame_from_runtime_snapshot(snapshot)


def _axis_value(intent, axis_name: str) -> float:
    return next(axis.value for axis in intent.axes if axis.axis_name == axis_name)


def _button_value(intent, button_name: str) -> bool:
    return next(button.pressed for button in intent.buttons if button.button_name == button_name)


def _hat_value(intent, hat_name: str = "POV1") -> str:
    return next(hat.value for hat in intent.hats if hat.hat_name == hat_name)


def test_1b_runtime_authority_boundary_does_not_import_ui_pages_or_widgets():
    scanned_roots = (
        PROJECT_ROOT / "shared_core" / "math",
        PROJECT_ROOT / "shared_core" / "runtime",
        PROJECT_ROOT / "shared_core" / "rules",
        PROJECT_ROOT / "bridge_app",
    )
    forbidden_prefixes = ("v3_app.pages", "v3_app.liquid", "v3_app.widgets", "PySide6")
    violations: list[str] = []
    for root in scanned_roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                imported = None
                if isinstance(node, ast.ImportFrom):
                    imported = node.module or ""
                elif isinstance(node, ast.Import):
                    imported = node.names[0].name
                if imported and imported.startswith(forbidden_prefixes):
                    violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")

    assert violations == []


def test_1b_parameter_inventory_matches_runtime_supported_surface():
    workspace = create_default_workspace()

    assert SUPPORTED_CURVE_MODES == ("s",)
    assert StackMode.MULTIPLY.value == "multiply"
    assert SUPPORTED_PARAMETERS == ("Output Scale",)
    assert SUPPORTED_OPERATIONS == ("Set", "Add", "Multiply")
    assert SUPPORTED_INJECTION_STAGES == ("Base Output Limits",)
    assert set(SUPPORTED_COMPARATORS) == {"greater than", "less than", "equal", "approximately", "between", "range"}
    assert tuple(route.runtime_vjoy_output for route in workspace.mappings.axis_routes) == (
        "X(axis1)",
        "Y(axis2)",
        "Z(axis3)",
        "RX(axis4)",
        "RY(axis5)",
        "RZ(axis6)",
    )
    assert tuple(route.output_button for route in workspace.mappings.button_routes) == tuple(range(1, 16))
    assert NUMERIC_PARAMETERS == (
        "curve_strength",
        "deadzone",
        "anti_deadzone",
        "hysteresis",
        "output_scale",
        "max_output",
        "precision_scale",
        "center_alpha",
        "edge_alpha",
        "same_slew_limit",
        "reverse_slew_limit",
        "combat_curve",
        "combat_scale",
        "combat_center_alpha",
        "combat_edge_alpha",
        "combat_same_slew",
        "combat_reverse_slew",
    )


def test_1b_golden_linear_pass_through_deadzone_antideadzone_scale_clamp():
    filtering = _identity_filtering()
    tuning = _linear_tuning()
    combat = _combat()
    for value in (-1.0, -0.5, 0.0, 0.5, 1.0):
        result = process_axis_stack(
            value,
            tuning=tuning,
            filtering=filtering,
            combat=combat,
            mode_config=ModeConfig(),
            mode_state=ModeState(),
        )
        assert result.final_output == pytest.approx(value)

    assert apply_center_deadzone(0.099, deadzone=0.1).output == 0.0
    assert apply_center_deadzone(0.1, deadzone=0.1).output == 0.0
    assert apply_center_deadzone(0.55, deadzone=0.1).output == pytest.approx(0.5)
    assert apply_center_deadzone(-0.55, deadzone=0.1).output == pytest.approx(-0.5)
    assert apply_center_deadzone(0.11, deadzone=0.1, anti_deadzone=0.2).output == pytest.approx(
        0.2 + ((0.11 - 0.1) / 0.9) * 0.8
    )
    assert apply_output_limits(0.5, output_scale=1.5, max_output=0.6) == pytest.approx(0.6)
    assert apply_output_limits(-0.5, output_scale=1.5, max_output=0.6) == pytest.approx(-0.6)


def test_1b_golden_filter_alpha_slew_and_hysteresis_sequence():
    filter_settings = AxisFiltering("Roll", center_alpha=0.25, edge_alpha=0.75, same_slew_limit=1.0, reverse_slew_limit=1.0)
    filtered = step_filter(target_value=0.4, state=FilterState(previous_output=0.2), settings=filter_settings)
    expected_alpha = 0.25 + (0.75 - 0.25) * 0.4

    assert filtered.output == pytest.approx(0.2 + expected_alpha * (0.4 - 0.2))
    assert filtered.diagnostics["alpha_region"] == "center"

    slew_settings = AxisFiltering("Roll", center_alpha=1.0, edge_alpha=1.0, same_slew_limit=0.2, reverse_slew_limit=0.05)
    same = step_filter(target_value=1.0, state=FilterState(previous_output=0.1), settings=slew_settings)
    reverse = step_filter(target_value=-1.0, state=FilterState(previous_output=0.5), settings=slew_settings)
    assert same.output == pytest.approx(0.3)
    assert same.diagnostics["slew_path"] == "same-direction"
    assert reverse.output == pytest.approx(0.45)
    assert reverse.diagnostics["slew_path"] == "reverse-direction"

    first = process_axis_stack(
        0.2,
        tuning=_linear_tuning(deadzone=0.1, hysteresis=0.05),
        filtering=_identity_filtering(),
        combat=_combat(),
        mode_config=ModeConfig(),
        mode_state=ModeState(),
    )
    second = process_axis_stack(
        0.08,
        tuning=_linear_tuning(deadzone=0.1, hysteresis=0.05),
        filtering=_identity_filtering(),
        combat=_combat(),
        mode_config=ModeConfig(),
        mode_state=ModeState(),
        previous_filter_state=first.filter_state,
    )
    assert second.stage_by_name("Center Conditioning").metadata["hysteresis_active"] is True


@pytest.mark.parametrize("curve_mode", SUPPORTED_CURVE_MODES)
def test_1b_curve_mode_matrix_is_finite_bounded_monotonic_and_telemetered(curve_mode):
    inputs = (-1.0, -0.75, -0.5, -0.25, -0.05, 0.0, 0.05, 0.25, 0.5, 0.75, 1.0)
    outputs = []
    for value in inputs:
        result = process_axis_stack(
            value,
            tuning=_linear_tuning(curve_mode=curve_mode, curve_strength=0.5),
            filtering=_identity_filtering(),
            combat=_combat(),
            mode_config=ModeConfig(),
            mode_state=ModeState(),
        )
        output = result.final_output
        outputs.append(output)
        assert math.isfinite(output)
        assert -1.0 <= output <= 1.0
        assert result.stage_by_name("Curve / Shape").metadata["curve_mode"] == curve_mode
        assert result.stage_by_name("Curve / Shape").metadata["curve_strength"] == pytest.approx(0.5)
        assert output == pytest.approx(s_curve_centered(value, curve_strength=0.5))

    assert outputs == sorted(outputs)
    assert outputs[0] == pytest.approx(-1.0)
    assert outputs[-1] == pytest.approx(1.0)
    assert outputs[1] == pytest.approx(-outputs[-2])


def test_1b_unsupported_curve_mode_defaults_safely_and_reports_requested_mode():
    result = process_axis_stack(
        0.5,
        tuning=_linear_tuning(curve_mode="unsupported", curve_strength=0.5),
        filtering=_identity_filtering(),
        combat=_combat(),
        mode_config=ModeConfig(),
        mode_state=ModeState(),
    )
    metadata = result.stage_by_name("Curve / Shape").metadata

    assert result.final_output == pytest.approx(s_curve_centered(0.5, curve_strength=0.5))
    assert metadata["curve_mode"] == "s"
    assert metadata["requested_curve_mode"] == "unsupported"
    assert metadata["curve_mode_supported"] is False


def test_1b_invalid_numeric_runtime_values_fail_safe_without_nan_or_crash():
    bad_tuning = AxisTuning(
        axis="Roll",
        curve_strength=float("nan"),
        deadzone="not-a-number",  # type: ignore[arg-type]
        anti_deadzone=float("inf"),
        hysteresis=None,  # type: ignore[arg-type]
        output_scale="2.0",  # type: ignore[arg-type]
        max_output=float("nan"),
        precision_scale="bad",  # type: ignore[arg-type]
    )
    bad_filtering = AxisFiltering(
        "Roll",
        center_alpha="bad",  # type: ignore[arg-type]
        edge_alpha=float("nan"),
        same_slew_limit="bad",  # type: ignore[arg-type]
        reverse_slew_limit=float("inf"),
    )
    bad_combat = AxisCombatProfile(
        "Roll",
        combat_curve=float("nan"),
        combat_scale="bad",  # type: ignore[arg-type]
    )

    result = process_axis_stack(
        "bad-raw",  # type: ignore[arg-type]
        tuning=bad_tuning,
        filtering=bad_filtering,
        combat=bad_combat,
        mode_config=ModeConfig(),
        mode_state=ModeState(precision_active=True, combat_active=True),
    )

    assert math.isfinite(result.final_output)
    assert -1.0 <= result.final_output <= 1.0
    for stage in result.stages:
        assert math.isfinite(stage.input_value)
        assert math.isfinite(stage.output_value)
        assert math.isfinite(stage.delta)


def test_1b_per_axis_independence_matrix_keeps_each_axis_own_parameters_and_mapping():
    tuning_by_id = {
        "roll": _linear_tuning("Roll", curve_strength=0.0, deadzone=0.0),
        "pitch": _linear_tuning("Pitch", curve_strength=0.25, deadzone=0.05, output_scale=0.8),
        "throttle": _linear_tuning("Throttle", curve_strength=0.5, max_output=0.6, output_scale=1.5),
        "yaw": _linear_tuning("Yaw", curve_strength=0.75, hysteresis=0.04),
        "aux_1": _linear_tuning("Aux 1", curve_strength=0.1, deadzone=0.12),
        "aux_2": _linear_tuning("Aux 2", curve_strength=0.9, anti_deadzone=0.2),
    }
    filtering_by_id = {
        "roll": _identity_filtering("Roll", center_alpha=1.0, edge_alpha=1.0),
        "pitch": _identity_filtering("Pitch", center_alpha=0.9, edge_alpha=0.95),
        "throttle": _identity_filtering("Throttle", center_alpha=0.8, edge_alpha=0.85),
        "yaw": _identity_filtering("Yaw", center_alpha=0.7, edge_alpha=0.75),
        "aux_1": _identity_filtering("Aux 1", center_alpha=0.6, edge_alpha=0.65),
        "aux_2": _identity_filtering("Aux 2", center_alpha=0.5, edge_alpha=0.55),
    }
    workspace = _workspace_for_axes(tuning_by_id=tuning_by_id, filtering_by_id=filtering_by_id)
    frame = _runtime_frame(
        workspace,
        _raw(Roll=0.7, Pitch=-0.5, Throttle=0.9, Yaw=-0.3, **{"Aux 1": 0.2, "Aux 2": -0.8}),
    )

    for axis in all_axis_definitions():
        result_stages = frame.pipeline.axis_stage_values[axis.display_name]
        center = next(stage for stage in result_stages if stage["stage_name"] == "Center Conditioning")
        curve = next(stage for stage in result_stages if stage["stage_name"] == "Curve / Shape")
        filtering = next(stage for stage in result_stages if stage["stage_name"] == "Filtering")
        expected_tuning = tuning_by_id[axis.axis_id.value]
        expected_filtering = filtering_by_id[axis.axis_id.value]

        assert curve["metadata"]["curve_strength"] == pytest.approx(expected_tuning.curve_strength)
        assert center["metadata"]["deadzone"] == pytest.approx(expected_tuning.deadzone)
        assert filtering["metadata"]["center_alpha"] == pytest.approx(expected_filtering.center_alpha)
        assert frame.pipeline.final_output_values[axis.display_name] == pytest.approx(result_stages[-1]["output_value"])

    assert tuple(axis.axis_name for axis in frame.output_intent.axes) == VJOY_AXES


def test_1b_axis_mapping_matrix_default_swaps_unmapped_duplicate_and_invalid_targets():
    final_axes = {"Roll": 0.11, "Pitch": 0.22, "Throttle": 0.33, "Yaw": 0.44, "Aux 1": 0.55, "Aux 2": 0.66}
    workspace = create_default_workspace()
    default = build_workspace_virtual_output_intent(final_axes, workspace=workspace)
    assert [_axis_value(default, axis) for axis in VJOY_AXES] == pytest.approx([0.11, 0.22, 0.33, 0.44, 0.55, 0.66])

    swapped = replace(
        workspace,
        mappings=replace(
            workspace.mappings,
            axis_routes=(
                AxisMapping("Roll", "Axis 1", "Y", "Y(axis2)"),
                AxisMapping("Pitch", "Axis 2", "X", "X(axis1)"),
                AxisMapping("Throttle", "Axis 3", "Z", "Z(axis3)"),
                AxisMapping("Yaw", "Axis 6", "RY", "RY(axis5)"),
                AxisMapping("Aux 1", "Axis 7", "RX", "RX(axis4)"),
                AxisMapping("Aux 2", "Axis 8", "RZ", "RZ(axis6)"),
            ),
        ),
    )
    swapped_intent = build_workspace_virtual_output_intent(final_axes, workspace=swapped)
    assert [_axis_value(swapped_intent, axis) for axis in VJOY_AXES] == pytest.approx([0.22, 0.11, 0.33, 0.55, 0.44, 0.66])

    unmapped = replace(workspace, mappings=replace(workspace.mappings, axis_routes=workspace.mappings.axis_routes[1:]))
    unmapped_intent = build_workspace_virtual_output_intent(final_axes, workspace=unmapped)
    assert _axis_value(unmapped_intent, "X") == 0.0

    duplicate = replace(
        workspace,
        mappings=replace(
            workspace.mappings,
            axis_routes=(
                AxisMapping("Roll", "Axis 1", "X", "X(axis1)"),
                AxisMapping("Pitch", "Axis 2", "X", "X(axis1)"),
            ),
        ),
    )
    duplicate_intent = build_workspace_virtual_output_intent(final_axes, workspace=duplicate)
    assert _axis_value(duplicate_intent, "X") == pytest.approx(0.22)

    invalid = replace(workspace, mappings=replace(workspace.mappings, axis_routes=(AxisMapping("Roll", "Axis 1", "NOPE", "NOPE"),)))
    invalid_intent = build_workspace_virtual_output_intent(final_axes, workspace=invalid)
    assert all(math.isfinite(axis.value) for axis in invalid_intent.axes)
    assert _axis_value(invalid_intent, "X") == 0.0


def test_1b_button_behavior_matrix_press_hold_release_tap_simultaneous_duplicate_and_writer_payload():
    workspace = create_default_workspace()
    final_axes = {axis: 0.0 for axis in AXIS_DISPLAY_NAMES}

    for button in range(1, 16):
        pressed = build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons(button))
        held = build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons(button))
        released = build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons())
        assert _button_value(pressed, f"Out{button}") is True
        assert _button_value(held, f"Out{button}") is True
        assert _button_value(released, f"Out{button}") is False
        assert [b.button_name for b in pressed.buttons if b.pressed] == [f"Out{button}"]

    rapid = [
        build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons()),
        build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons(3)),
        build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons()),
    ]
    assert [_button_value(intent, "Out3") for intent in rapid] == [False, True, False]

    simultaneous = build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons(1, 2, 3))
    assert [button.button_name for button in simultaneous.buttons if button.pressed] == ["Out1", "Out2", "Out3"]

    duplicate = replace(
        workspace,
        mappings=replace(workspace.mappings, button_routes=(ButtonMapping(1, 1), ButtonMapping(2, 1))),
    )
    duplicate_intent = build_workspace_virtual_output_intent(final_axes, workspace=duplicate, button_states=_buttons(1))
    assert _button_value(duplicate_intent, "Out1") is True

    backend = FakeVirtualOutputBackend()
    write = backend.write_output_intent(simultaneous)
    assert write.success is True
    assert backend.last_written_intent is simultaneous
    assert [button.button_name for button in backend.last_written_intent.buttons if button.pressed] == ["Out1", "Out2", "Out3"]


def test_1b_hat_pov_matrix_valid_states_and_invalid_state_are_safe():
    workspace = create_default_workspace()
    final_axes = {axis: 0.0 for axis in AXIS_DISPLAY_NAMES}
    valid_states = ("Centered", "Up", "UpRight", "Right", "DownRight", "Down", "DownLeft", "Left", "UpLeft")

    for state in valid_states:
        intent = build_workspace_virtual_output_intent(final_axes, workspace=workspace, hat_state=state)
        assert _hat_value(intent) == state

    invalid = build_workspace_virtual_output_intent(final_axes, workspace=workspace, hat_state="sideways-ish")
    assert _hat_value(invalid) == "Centered"


def test_1b_runtime_orchestrator_activates_precision_and_combat_modes_from_buttons():
    modes = ModeConfig(precision_hold_buttons=(1,), combat_zoom_aim_buttons=(5,), precision_combat_stack_mode=StackMode.MULTIPLY)
    workspace = _workspace_for_axes(
        tuning_by_id=_all_axis_tuning(precision_scale=0.5),
        filtering_by_id=_all_axis_filtering(),
        combat_by_id=_all_axis_combat(combat_curve=0.0, combat_scale=0.5),
        modes=modes,
    )

    normal = _runtime_frame(workspace, _raw(Roll=0.8), buttons=_buttons())
    precision = _runtime_frame(workspace, _raw(Roll=0.8), buttons=_buttons(1))
    combat = _runtime_frame(workspace, _raw(Roll=0.8), buttons=_buttons(5))
    both = _runtime_frame(workspace, _raw(Roll=0.8), buttons=_buttons(1, 5))

    assert normal.pipeline.final_output_values["Roll"] == pytest.approx(0.8)
    assert precision.pipeline.final_output_values["Roll"] == pytest.approx(0.4)
    assert combat.pipeline.final_output_values["Roll"] == pytest.approx(0.4)
    assert both.pipeline.final_output_values["Roll"] == pytest.approx(0.2)
    assert both.pipeline.axis_stage_values["Roll"][5]["metadata"]["precision_active"] is True
    assert both.pipeline.axis_stage_values["Roll"][5]["metadata"]["combat_active"] is True


def test_1b_conditional_rule_matrix_comparators_gates_operations_and_invalid_rules():
    base_context = RuleEvaluationContext(values_by_stage={"Final Output": {"Roll": 0.5, "Yaw": 0.25}})
    comparator_cases = {
        "greater than": True,
        "less than": False,
        "equal": True,
        "approximately": True,
        "between": True,
        "range": True,
    }
    for comparator, expected in comparator_cases.items():
        threshold = 0.5 if comparator in {"equal", "approximately"} else 0.4
        threshold_high = 0.6 if comparator in {"between", "range"} else None
        rule = replace(yaw_roll_example_rule(), enabled=True, comparator=comparator, threshold=threshold, threshold_high=threshold_high)
        result = evaluate_rule(rule, base_context)
        assert result.applies is expected

    disabled = evaluate_rule(yaw_roll_example_rule(), base_context)
    assert disabled.status is RuleStatus.DISABLED

    mode_button_rule = replace(yaw_roll_example_rule(), enabled=True, mode_gate="Combat", buttons=(5,))
    inactive = evaluate_rule(mode_button_rule, base_context)
    active = evaluate_rule(
        mode_button_rule,
        RuleEvaluationContext(
            values_by_stage={"Final Output": {"Roll": 0.5, "Yaw": 0.25}},
            active_modes=("Combat",),
            active_buttons=(5,),
        ),
    )
    assert inactive.status is RuleStatus.INACTIVE
    assert active.status is RuleStatus.ACTIVE

    blocked = evaluate_rule(replace(yaw_roll_example_rule(), enabled=True, parameter="Max Output"), base_context)
    assert blocked.status is RuleStatus.BLOCKED
    assert "Unsupported parameter" in blocked.blocked_reason

    workspace = _workspace_for_axes(
        tuning_by_id=_all_axis_tuning(),
        filtering_by_id=_all_axis_filtering(),
        combat_by_id=_all_axis_combat(),
        rules=(
            replace(yaw_roll_example_rule(), enabled=True, operation="Set", value=0.5, target_axis="Yaw"),
            replace(yaw_roll_example_rule(), enabled=True, operation="Add", value=0.25, target_axis="Pitch"),
            replace(yaw_roll_example_rule(), enabled=True, operation="Multiply", value=0.5, target_axis="Aux 1"),
        ),
    )
    result = WorkspaceSignalPipeline(workspace).process(_raw(Roll=0.8, Pitch=0.8, Yaw=0.8, **{"Aux 1": 0.8}))
    assert result.axis_results["Yaw"].stage_by_name("Base Output Limits").metadata["output_scale"] == pytest.approx(0.5)
    assert result.axis_results["Pitch"].stage_by_name("Base Output Limits").metadata["output_scale"] == pytest.approx(1.25)
    assert result.axis_results["Aux 1"].stage_by_name("Base Output Limits").metadata["output_scale"] == pytest.approx(0.5)


def test_1b_pipeline_rule_context_includes_mode_and_button_gates_from_runtime_state():
    gated_rule = replace(yaw_roll_example_rule(), enabled=True, mode_gate="Combat", buttons=(5,), target_axis="Yaw", value=0.25)
    workspace = _workspace_for_axes(
        tuning_by_id=_all_axis_tuning(),
        filtering_by_id=_all_axis_filtering(),
        combat_by_id=_all_axis_combat(),
        rules=(gated_rule,),
    )
    pipeline = WorkspaceSignalPipeline(workspace)

    inactive = pipeline.process(_raw(Roll=0.8, Yaw=0.8), mode_state=ModeState(combat_active=True), active_buttons=())
    active = pipeline.process(_raw(Roll=0.8, Yaw=0.8), mode_state=ModeState(combat_active=True), active_buttons=(5,))

    assert inactive.rule_evaluations[0].status is RuleStatus.INACTIVE
    assert active.rule_evaluations[0].status is RuleStatus.ACTIVE
    assert active.axis_results["Yaw"].stage_by_name("Base Output Limits").metadata["output_scale"] == pytest.approx(0.25)


def test_1b_stage_telemetry_consistency_final_mapping_and_writer_payload():
    workspace = create_default_workspace()
    frame = _runtime_frame(workspace, _raw(Roll=0.6, Pitch=-0.4, Throttle=0.5, Yaw=0.2, **{"Aux 1": -0.2, "Aux 2": 0.1}), buttons=_buttons(1, 4))

    for axis_name, stages in frame.pipeline.axis_stage_values.items():
        assert tuple(stage["stage_name"] for stage in stages) == EXPECTED_STAGE_NAMES
        for stage in stages:
            assert math.isfinite(stage["input_value"])
            assert math.isfinite(stage["output_value"])
            assert math.isfinite(stage["delta"])
        assert stages[-1]["output_value"] == pytest.approx(frame.pipeline.final_output_values[axis_name])

    backend = FakeVirtualOutputBackend()
    backend.write_output_intent(frame.output_intent)
    assert backend.last_written_intent is frame.output_intent
    assert _button_value(backend.last_written_intent, "Out1") is True
    assert _button_value(backend.last_written_intent, "Out4") is True


def _pairwise_cases() -> list[dict[str, object]]:
    families = {
        "curve_strength": (0.0, 0.7),
        "deadzone": (0.0, 0.12),
        "anti_deadzone": (0.0, 0.2),
        "hysteresis": (0.0, 0.04),
        "output_scale": (0.6, 1.3),
        "max_output": (0.5, 1.0),
        "center_alpha": (0.2, 1.0),
        "edge_alpha": (0.4, 1.0),
        "same_slew_limit": (0.15, 1.0),
        "reverse_slew_limit": (0.1, 1.0),
        "combat_scale": (0.5, 1.0),
        "mode": (False, True),
        "rule": (False, True),
    }
    cases: list[dict[str, object]] = []
    for left, right in combinations(families, 2):
        case: dict[str, object] = {key: values[0] for key, values in families.items()}
        case[left] = families[left][1]
        case[right] = families[right][1]
        case["pair"] = f"{left}+{right}"
        cases.append(case)
    return cases


def test_1b_pairwise_interaction_matrix_is_bounded_finite_and_stateful():
    cases = _pairwise_cases()
    assert len(cases) == 78

    for case in cases:
        rule = replace(yaw_roll_example_rule(), enabled=bool(case["rule"]), target_axis="Yaw", value=0.5)
        workspace = _workspace_for_axes(
            tuning_by_id=_all_axis_tuning(
                curve_strength=case["curve_strength"],
                deadzone=case["deadzone"],
                anti_deadzone=case["anti_deadzone"],
                hysteresis=case["hysteresis"],
                output_scale=case["output_scale"],
                max_output=case["max_output"],
                precision_scale=0.5,
            ),
            filtering_by_id=_all_axis_filtering(
                center_alpha=case["center_alpha"],
                edge_alpha=case["edge_alpha"],
                same_slew_limit=case["same_slew_limit"],
                reverse_slew_limit=case["reverse_slew_limit"],
            ),
            combat_by_id=_all_axis_combat(combat_scale=case["combat_scale"]),
            rules=(rule,),
        )
        mode_state = ModeState(precision_active=bool(case["mode"]))
        pipeline = WorkspaceSignalPipeline(workspace)
        state = pipeline.initial_state()
        for raw_roll in (0.0, 0.3, 0.8, -0.4):
            result = pipeline.process(_raw(Roll=raw_roll, Yaw=0.7), state=state, mode_state=mode_state)
            state = result.state
            assert result.rule_evaluations
            for value in result.final_output_values.values():
                assert math.isfinite(value)
                assert -1.0 <= value <= 1.0


@pytest.mark.parametrize("seed", (1337, 44044, 8675309))
def test_1b_seeded_fuzz_property_cases(seed):
    rng = random.Random(seed)
    case_count = 18
    for _ in range(case_count):
        routes = list(create_default_workspace().mappings.axis_routes)
        rng.shuffle(routes)
        vjoy_targets = list(VJOY_AXES)
        rng.shuffle(vjoy_targets)
        remapped_routes = tuple(
            replace(route, logical_output=vjoy_targets[index], runtime_vjoy_output=f"{vjoy_targets[index]}(axis{index + 1})")
            for index, route in enumerate(routes)
        )
        workspace = _workspace_for_axes(
            tuning_by_id=_all_axis_tuning(
                curve_strength=rng.random(),
                deadzone=rng.uniform(0.0, 0.2),
                anti_deadzone=rng.uniform(0.0, 0.25),
                hysteresis=rng.uniform(0.0, 0.05),
                output_scale=rng.uniform(0.5, 1.5),
                max_output=rng.uniform(0.4, 1.0),
                precision_scale=rng.uniform(0.4, 1.0),
            ),
            filtering_by_id=_all_axis_filtering(
                center_alpha=rng.uniform(0.1, 1.0),
                edge_alpha=rng.uniform(0.1, 1.0),
                same_slew_limit=rng.uniform(0.05, 1.0),
                reverse_slew_limit=rng.uniform(0.05, 1.0),
            ),
            combat_by_id=_all_axis_combat(combat_curve=rng.random(), combat_scale=rng.uniform(0.4, 1.0)),
            mappings=replace(create_default_workspace().mappings, axis_routes=remapped_routes),
            rules=(replace(yaw_roll_example_rule(), enabled=rng.choice((True, False)), value=rng.uniform(0.25, 1.25)),),
        )
        frame = _runtime_frame(
            workspace,
            {axis: rng.uniform(-1.0, 1.0) for axis in AXIS_DISPLAY_NAMES},
            buttons=_buttons(*(button for button in range(1, 16) if rng.random() < 0.2)),
            hat_state=rng.choice(("Centered", "Up", "Down", "Left", "Right")),
        )

        assert frame.runtime_orchestrator_rebuild_count == 1
        for value in frame.pipeline.final_output_values.values():
            assert math.isfinite(value)
            assert -1.0 <= value <= 1.0
        for output in frame.output_intent.axes:
            assert math.isfinite(output.value)
            assert -1.0 <= output.value <= 1.0
        backend = FakeVirtualOutputBackend()
        backend.write_output_intent(frame.output_intent)
        assert backend.last_written_intent == frame.output_intent

