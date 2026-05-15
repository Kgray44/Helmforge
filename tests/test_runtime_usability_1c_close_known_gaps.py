from __future__ import annotations

import ast
import math
from dataclasses import replace
from pathlib import Path

import pytest

from shared_core.math.pipeline import WorkspaceSignalPipeline
from shared_core.math.stack import ModeState, process_axis_stack
from shared_core.models.axes import AXIS_DISPLAY_NAMES, all_axis_definitions
from shared_core.models.combat import AxisCombatProfile
from shared_core.models.filtering import AxisFiltering
from shared_core.models.mappings import ButtonMapping, HatMapping, MappingConfig
from shared_core.models.modes import ModeConfig
from shared_core.models.runtime import RuntimeSnapshot, simulation_fallback_status
from shared_core.models.tuning import AxisTuning
from shared_core.models.workspace import create_default_workspace
from shared_core.runtime.runtime_orchestrator import RuntimeOrchestrator, RuntimeOrchestratorConfig
from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend, build_workspace_virtual_output_intent


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _linear_tuning(axis: str = "Roll", **overrides: object) -> AxisTuning:
    return AxisTuning(
        axis=axis,
        curve_mode=overrides.pop("curve_mode", "s"),  # type: ignore[arg-type]
        curve_strength=overrides.pop("curve_strength", 0.0),  # type: ignore[arg-type]
        deadzone=overrides.pop("deadzone", 0.0),  # type: ignore[arg-type]
        anti_deadzone=overrides.pop("anti_deadzone", 0.0),  # type: ignore[arg-type]
        hysteresis=overrides.pop("hysteresis", 0.0),  # type: ignore[arg-type]
        output_scale=overrides.pop("output_scale", 1.0),  # type: ignore[arg-type]
        max_output=overrides.pop("max_output", 1.0),  # type: ignore[arg-type]
        precision_scale=overrides.pop("precision_scale", 1.0),  # type: ignore[arg-type]
        invert=bool(overrides.pop("invert", False)),
    )


def _filtering(axis: str = "Roll", **overrides: object) -> AxisFiltering:
    return AxisFiltering(
        axis=axis,
        center_alpha=overrides.pop("center_alpha", 1.0),  # type: ignore[arg-type]
        edge_alpha=overrides.pop("edge_alpha", 1.0),  # type: ignore[arg-type]
        same_slew_limit=overrides.pop("same_slew_limit", 10.0),  # type: ignore[arg-type]
        reverse_slew_limit=overrides.pop("reverse_slew_limit", 10.0),  # type: ignore[arg-type]
    )


def _combat(axis: str = "Roll", **overrides: object) -> AxisCombatProfile:
    return AxisCombatProfile(
        axis=axis,
        combat_curve=overrides.pop("combat_curve", 0.0),  # type: ignore[arg-type]
        combat_scale=overrides.pop("combat_scale", 1.0),  # type: ignore[arg-type]
        combat_center_alpha=overrides.pop("combat_center_alpha", 1.0),  # type: ignore[arg-type]
        combat_edge_alpha=overrides.pop("combat_edge_alpha", 1.0),  # type: ignore[arg-type]
        combat_same_slew=overrides.pop("combat_same_slew", 10.0),  # type: ignore[arg-type]
        combat_reverse_slew=overrides.pop("combat_reverse_slew", 10.0),  # type: ignore[arg-type]
    )


def _raw(**overrides: float) -> dict[str, float]:
    values = {axis: 0.0 for axis in AXIS_DISPLAY_NAMES}
    values.update({axis: float(value) for axis, value in overrides.items()})
    return values


def _buttons(*pressed: int) -> dict[str, bool]:
    active = set(pressed)
    return {f"B{index}": index in active for index in range(1, 16)}


def _all_axis_tuning(**kwargs: object) -> dict[str, AxisTuning]:
    return {axis.axis_id.value: _linear_tuning(axis.display_name, **kwargs) for axis in all_axis_definitions()}


def _all_axis_filtering(**kwargs: object) -> dict[str, AxisFiltering]:
    return {axis.axis_id.value: _filtering(axis.display_name, **kwargs) for axis in all_axis_definitions()}


def _all_axis_combat(**kwargs: object) -> dict[str, AxisCombatProfile]:
    return {axis.axis_id.value: _combat(axis.display_name, **kwargs) for axis in all_axis_definitions()}


def _workspace_for_axes(
    *,
    filtering_by_id: dict[str, AxisFiltering] | None = None,
    combat_by_id: dict[str, AxisCombatProfile] | None = None,
    mappings: MappingConfig | None = None,
):
    workspace = create_default_workspace()
    workspace = replace(workspace, tuning=replace(workspace.tuning, axes=_all_axis_tuning()))
    if filtering_by_id is not None:
        workspace = replace(workspace, filtering=replace(workspace.filtering, axes=filtering_by_id))
    if combat_by_id is not None:
        workspace = replace(workspace, combat=replace(workspace.combat, axes=combat_by_id))
    if mappings is not None:
        workspace = replace(workspace, mappings=mappings)
    return workspace


def _button_value(intent, button_name: str) -> bool:
    return next(button.pressed for button in intent.buttons if button.button_name == button_name)


def _hat_value(intent, hat_name: str = "POV1") -> str:
    return next(hat.value for hat in intent.hats if hat.hat_name == hat_name)


def _output_button_names(intent) -> tuple[str, ...]:
    return tuple(button.button_name for button in intent.buttons if button.pressed)


def _filter_stage(result):
    return result.stage_by_name("Filtering")


def test_combat_filter_params_inactive_do_not_affect_runtime_output():
    filtering = _filtering(center_alpha=0.20, edge_alpha=0.20, same_slew_limit=10.0, reverse_slew_limit=10.0)
    combat = _combat(combat_center_alpha=1.0, combat_edge_alpha=1.0, combat_same_slew=0.01, combat_reverse_slew=0.01)

    result = process_axis_stack(
        0.40,
        tuning=_linear_tuning(),
        filtering=filtering,
        combat=combat,
        mode_config=ModeConfig(),
        mode_state=ModeState(),
    )

    filtering_stage = _filter_stage(result)
    assert filtering_stage.output_value == pytest.approx(0.08)
    assert result.final_output == pytest.approx(0.08)
    assert filtering_stage.metadata["combat_filter_active"] is False
    assert filtering_stage.metadata["effective_center_alpha"] == pytest.approx(0.20)
    assert filtering_stage.metadata["effective_edge_alpha"] == pytest.approx(0.20)
    assert filtering_stage.metadata["effective_same_slew_limit"] == pytest.approx(10.0)
    assert filtering_stage.metadata["effective_reverse_slew_limit"] == pytest.approx(10.0)


def test_combat_filter_alpha_params_apply_only_when_combat_active():
    filtering = _filtering(center_alpha=0.05, edge_alpha=0.05, same_slew_limit=10.0, reverse_slew_limit=10.0)
    combat = _combat(combat_center_alpha=0.80, combat_edge_alpha=0.80, combat_same_slew=10.0, combat_reverse_slew=10.0)
    result = process_axis_stack(
        0.25,
        tuning=_linear_tuning(),
        filtering=filtering,
        combat=combat,
        mode_config=ModeConfig(),
        mode_state=ModeState(combat_active=True),
    )
    filtering_stage = _filter_stage(result)

    assert filtering_stage.output_value == pytest.approx(0.20)
    assert filtering_stage.metadata["combat_filter_active"] is True
    assert filtering_stage.metadata["center_alpha"] == pytest.approx(0.05)
    assert filtering_stage.metadata["combat_center_alpha"] == pytest.approx(0.80)
    assert filtering_stage.metadata["effective_center_alpha"] == pytest.approx(0.80)
    assert filtering_stage.metadata["alpha_region"] == "center"
    assert filtering_stage.metadata["alpha"] == pytest.approx(0.80)

    edge_combat = _combat(combat_center_alpha=0.20, combat_edge_alpha=1.0, combat_same_slew=10.0, combat_reverse_slew=10.0)
    edge_result = process_axis_stack(
        0.75,
        tuning=_linear_tuning(),
        filtering=filtering,
        combat=edge_combat,
        mode_config=ModeConfig(),
        mode_state=ModeState(combat_active=True),
    )
    edge_stage = _filter_stage(edge_result)
    expected_alpha = 0.20 + (1.0 - 0.20) * 0.75
    assert edge_stage.metadata["alpha_region"] == "edge"
    assert edge_stage.metadata["effective_edge_alpha"] == pytest.approx(1.0)
    assert edge_stage.metadata["alpha"] == pytest.approx(expected_alpha)
    assert edge_stage.output_value == pytest.approx(0.75 * expected_alpha)


def test_combat_filter_slew_params_apply_only_when_combat_active():
    filtering = _filtering(center_alpha=1.0, edge_alpha=1.0, same_slew_limit=10.0, reverse_slew_limit=10.0)
    combat = _combat(combat_center_alpha=1.0, combat_edge_alpha=1.0, combat_same_slew=0.10, combat_reverse_slew=0.05)

    first = process_axis_stack(
        1.0,
        tuning=_linear_tuning(),
        filtering=filtering,
        combat=combat,
        mode_config=ModeConfig(),
        mode_state=ModeState(combat_active=True),
    )
    first_stage = _filter_stage(first)
    assert first_stage.output_value == pytest.approx(0.10)
    assert first_stage.metadata["slew_path"] == "same-direction"
    assert first_stage.metadata["effective_same_slew_limit"] == pytest.approx(0.10)
    assert first_stage.metadata["slew_limit"] == pytest.approx(0.10)

    second = process_axis_stack(
        -1.0,
        tuning=_linear_tuning(),
        filtering=filtering,
        combat=combat,
        mode_config=ModeConfig(),
        mode_state=ModeState(combat_active=True),
        previous_filter_state=first.filter_state,
    )
    second_stage = _filter_stage(second)
    assert second_stage.output_value == pytest.approx(0.05)
    assert second_stage.metadata["slew_path"] == "reverse-direction"
    assert second_stage.metadata["effective_reverse_slew_limit"] == pytest.approx(0.05)
    assert second_stage.metadata["slew_limit"] == pytest.approx(0.05)


def test_combat_filter_mode_transition_does_not_latch_or_rebuild_every_sample():
    workspace = _workspace_for_axes(
        filtering_by_id=_all_axis_filtering(center_alpha=0.20, edge_alpha=0.20, same_slew_limit=10.0, reverse_slew_limit=10.0),
        combat_by_id=_all_axis_combat(combat_center_alpha=1.0, combat_edge_alpha=1.0, combat_same_slew=10.0, combat_reverse_slew=10.0),
    )
    pipeline = WorkspaceSignalPipeline(workspace)
    state = pipeline.initial_state()

    inactive = pipeline.process(_raw(Roll=0.5), state=state, mode_state=ModeState())
    active = pipeline.process(_raw(Roll=1.0), state=inactive.state, mode_state=ModeState(combat_active=True))
    inactive_again = pipeline.process(_raw(Roll=0.0), state=active.state, mode_state=ModeState())

    assert _filter_stage(inactive.axis_results["Roll"]).output_value == pytest.approx(0.10)
    assert _filter_stage(active.axis_results["Roll"]).output_value == pytest.approx(1.0)
    assert _filter_stage(inactive_again.axis_results["Roll"]).metadata["combat_filter_active"] is False
    assert _filter_stage(inactive_again.axis_results["Roll"]).metadata["effective_center_alpha"] == pytest.approx(0.20)
    assert _filter_stage(inactive_again.axis_results["Roll"]).output_value == pytest.approx(0.80)

    status = simulation_fallback_status()
    orchestrator = RuntimeOrchestrator(
        workspace=workspace,
        runtime_status=status,
        config=RuntimeOrchestratorConfig(deterministic_simulation=True),
    )
    for buttons, roll in ((_buttons(), 0.5), (_buttons(5), 1.0), (_buttons(), 0.0)):
        frame = orchestrator.build_frame_from_runtime_snapshot(
            RuntimeSnapshot(
                raw_axis_values=_raw(Roll=roll),
                final_output_values={axis: 0.0 for axis in AXIS_DISPLAY_NAMES},
                button_states=buttons,
                hat_state="Centered",
                runtime_status=status,
                simulated=True,
            )
        )
        assert frame.runtime_orchestrator_rebuild_count == 1


def test_combat_filter_params_are_per_axis_and_do_not_leak():
    combat_by_id = _all_axis_combat(combat_center_alpha=0.40, combat_edge_alpha=0.40, combat_same_slew=10.0, combat_reverse_slew=10.0)
    combat_by_id["roll"] = _combat("Roll", combat_center_alpha=0.90, combat_edge_alpha=0.90)
    combat_by_id["pitch"] = _combat("Pitch", combat_center_alpha=0.30, combat_edge_alpha=0.30)
    combat_by_id["yaw"] = _combat("Yaw", combat_center_alpha=1.0, combat_edge_alpha=1.0, combat_same_slew=0.05)
    workspace = _workspace_for_axes(
        filtering_by_id=_all_axis_filtering(center_alpha=0.10, edge_alpha=0.10, same_slew_limit=10.0, reverse_slew_limit=10.0),
        combat_by_id=combat_by_id,
    )

    result = WorkspaceSignalPipeline(workspace).process(
        _raw(Roll=0.50, Pitch=0.50, Throttle=0.50, Yaw=1.0),
        mode_state=ModeState(combat_active=True),
    )

    roll_stage = _filter_stage(result.axis_results["Roll"])
    pitch_stage = _filter_stage(result.axis_results["Pitch"])
    yaw_stage = _filter_stage(result.axis_results["Yaw"])
    throttle_stage = _filter_stage(result.axis_results["Throttle"])
    assert roll_stage.metadata["effective_center_alpha"] == pytest.approx(0.90)
    assert pitch_stage.metadata["effective_center_alpha"] == pytest.approx(0.30)
    assert yaw_stage.metadata["effective_same_slew_limit"] == pytest.approx(0.05)
    assert yaw_stage.output_value == pytest.approx(0.05)
    assert throttle_stage.metadata["effective_center_alpha"] == pytest.approx(0.40)
    assert result.final_output_values["Roll"] != pytest.approx(result.final_output_values["Pitch"])


def test_invalid_combat_filter_params_fail_safe_without_nan_or_crash():
    filtering = _filtering(center_alpha=0.30, edge_alpha=0.70, same_slew_limit=0.40, reverse_slew_limit=0.25)
    combat = _combat(
        combat_center_alpha=float("nan"),
        combat_edge_alpha="not-a-number",
        combat_same_slew=None,
        combat_reverse_slew=float("inf"),
    )
    result = process_axis_stack(
        0.80,
        tuning=_linear_tuning(),
        filtering=filtering,
        combat=combat,
        mode_config=ModeConfig(),
        mode_state=ModeState(combat_active=True),
    )

    filtering_stage = _filter_stage(result)
    assert math.isfinite(result.final_output)
    assert filtering_stage.metadata["combat_filter_active"] is True
    assert filtering_stage.metadata["effective_center_alpha"] == pytest.approx(0.30)
    assert filtering_stage.metadata["effective_edge_alpha"] == pytest.approx(0.70)
    assert filtering_stage.metadata["effective_same_slew_limit"] == pytest.approx(0.40)
    assert filtering_stage.metadata["effective_reverse_slew_limit"] == pytest.approx(0.25)


def test_hat_pov_passthrough_remains_normalized():
    workspace = create_default_workspace()
    workspace = replace(workspace, mappings=replace(workspace.mappings, hat_routes=()))

    for state, expected in (
        ("Centered", "Centered"),
        ("Up", "Up"),
        ("Down", "Down"),
        ("Left", "Left"),
        ("Right", "Right"),
        ("sideways-ish", "Centered"),
    ):
        intent = build_workspace_virtual_output_intent(_raw(), workspace=workspace, hat_state=state)
        assert _hat_value(intent) == expected
        assert _output_button_names(intent) == ()


def test_hat_cardinal_directions_can_drive_mapped_output_buttons():
    workspace = create_default_workspace()
    mappings = replace(
        workspace.mappings,
        hat_routes=(HatMapping(hotas_hat=1, vjoy_pov=1, up_button=9, right_button=10, down_button=11, left_button=12),),
    )
    workspace = replace(workspace, mappings=mappings)

    expectations = {
        "Up": "Out9",
        "Right": "Out10",
        "Down": "Out11",
        "Left": "Out12",
    }
    for direction, button_name in expectations.items():
        intent = build_workspace_virtual_output_intent(_raw(), workspace=workspace, hat_state=direction)
        assert _hat_value(intent) == direction
        assert _output_button_names(intent) == (button_name,)


def test_hat_to_button_routes_or_with_normal_button_routes():
    workspace = create_default_workspace()
    mappings = replace(
        workspace.mappings,
        button_routes=(ButtonMapping(hotas_button=5, output_button=9),),
        hat_routes=(HatMapping(hotas_hat=1, vjoy_pov=1, up_button=9),),
    )
    workspace = replace(workspace, mappings=mappings)

    sequence = (
        (_buttons(), "Centered", False),
        (_buttons(5), "Centered", True),
        (_buttons(), "Up", True),
        (_buttons(5), "Up", True),
        (_buttons(5), "Centered", True),
        (_buttons(), "Centered", False),
    )
    for buttons, hat_state, expected in sequence:
        intent = build_workspace_virtual_output_intent(_raw(), workspace=workspace, button_states=buttons, hat_state=hat_state)
        assert _button_value(intent, "Out9") is expected


def test_hat_to_button_neutral_releases_mapped_outputs():
    workspace = create_default_workspace()
    workspace = replace(
        workspace,
        mappings=replace(workspace.mappings, hat_routes=(HatMapping(hotas_hat=1, vjoy_pov=1, up_button=9),)),
    )

    pressed = build_workspace_virtual_output_intent(_raw(), workspace=workspace, hat_state="Up")
    released = build_workspace_virtual_output_intent(_raw(), workspace=workspace, hat_state="Centered")

    assert _button_value(pressed, "Out9") is True
    assert _button_value(released, "Out9") is False
    assert _hat_value(released) == "Centered"


def test_hat_invalid_output_targets_are_skipped_safely():
    workspace = create_default_workspace()
    workspace = replace(
        workspace,
        mappings=replace(workspace.mappings, hat_routes=(HatMapping(hotas_hat=1, vjoy_pov=1, up_button=999, right_button=10),)),
    )

    invalid = build_workspace_virtual_output_intent(_raw(), workspace=workspace, hat_state="Up")
    valid = build_workspace_virtual_output_intent(_raw(), workspace=workspace, hat_state="Right")

    assert _output_button_names(invalid) == ()
    assert _output_button_names(valid) == ("Out10",)


def test_hat_diagonal_policy_is_covered_or_explicitly_reported():
    workspace = create_default_workspace()
    workspace = replace(
        workspace,
        mappings=replace(workspace.mappings, hat_routes=(HatMapping(hotas_hat=1, vjoy_pov=1, up_button=9, right_button=10),)),
    )

    intent = build_workspace_virtual_output_intent(_raw(), workspace=workspace, hat_state="UpRight")

    assert _hat_value(intent) == "UpRight"
    assert set(_output_button_names(intent)) == {"Out9", "Out10"}


def test_hat_to_button_output_intent_matches_fake_writer_payload():
    workspace = create_default_workspace()
    workspace = replace(
        workspace,
        mappings=replace(workspace.mappings, hat_routes=(HatMapping(hotas_hat=1, vjoy_pov=1, up_button=9),)),
    )
    intent = build_workspace_virtual_output_intent(_raw(), workspace=workspace, hat_state="Up")
    backend = FakeVirtualOutputBackend()

    result = backend.write_output_intent(intent)

    assert result.success is True
    assert backend.last_written_intent == intent
    assert _button_value(backend.last_written_intent, "Out9") is True
    assert _hat_value(backend.last_written_intent) == "Up"


def test_1c_runtime_authority_boundary_no_ui_calculation_dependency():
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
