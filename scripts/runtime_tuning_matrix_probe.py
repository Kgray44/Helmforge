from __future__ import annotations

import argparse
import ast
import json
import math
import random
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared_core.math.filtering import FilterState, step_filter
from shared_core.math.pipeline import WorkspaceSignalPipeline
from shared_core.math.stack import EXPECTED_STAGE_NAMES, ModeState, process_axis_stack
from shared_core.models.axes import AXIS_DISPLAY_NAMES, all_axis_definitions
from shared_core.models.combat import AxisCombatProfile
from shared_core.models.filtering import AxisFiltering
from shared_core.models.mappings import AxisMapping, ButtonMapping, HatMapping, MappingConfig
from shared_core.models.modes import ModeConfig, StackMode
from shared_core.models.rules import ConditionalRule, RuleConfig, yaw_roll_example_rule
from shared_core.models.runtime import RuntimeSnapshot, simulation_fallback_status
from shared_core.models.tuning import AxisTuning
from shared_core.models.workspace import create_default_workspace
from shared_core.rules.evaluator import (
    SUPPORTED_COMPARATORS,
    SUPPORTED_INJECTION_STAGES,
    SUPPORTED_MEASURES,
    SUPPORTED_MODE_GATES,
    SUPPORTED_OPERATIONS,
    SUPPORTED_PARAMETERS,
    RuleEvaluationContext,
    RuleStatus,
    evaluate_rule,
)
from shared_core.runtime.runtime_orchestrator import RuntimeOrchestrator, RuntimeOrchestratorConfig
from shared_core.runtime.vjoy_output import (
    FakeVirtualOutputBackend,
    RealVJoyOutputBackend,
    VirtualOutputIntent,
    build_workspace_virtual_output_intent,
)


ARTIFACT_ROOT = Path("artifacts") / "runtime-tuning-matrix"
REPORT_PATH = Path("docs") / "HelmForge" / "runtime-usability-1b-full-tuning-matrix-report.md"
VJOY_AXES = ("X", "Y", "Z", "RX", "RY", "RZ")
BUTTONS = tuple(range(1, 16))
SUPPORTED_CURVE_MODES = ("s",)
FUZZ_SEEDS = (1337, 44044, 8675309)
FUZZ_CASES_PER_SEED = 84
NUMERIC_PARAMETER_GROUPS = {
    "tuning": (
        "curve_strength",
        "deadzone",
        "anti_deadzone",
        "hysteresis",
        "output_scale",
        "max_output",
        "precision_scale",
    ),
    "filtering": ("center_alpha", "edge_alpha", "same_slew_limit", "reverse_slew_limit"),
    "combat": (
        "combat_curve",
        "combat_scale",
        "combat_center_alpha",
        "combat_edge_alpha",
        "combat_same_slew",
        "combat_reverse_slew",
    ),
}
BOUNDARY_VALUES = (-1.0, 0.0, 0.001, 0.25, 0.5, 0.75, 0.999, 1.0, 1.5, None, float("nan"), float("inf"), "bad", "")


@dataclass(frozen=True)
class ProbeCase:
    section: str
    name: str
    passed: bool
    details: Mapping[str, Any]


def _linear_tuning(axis: str = "Roll", **overrides: object) -> AxisTuning:
    return AxisTuning(
        axis=axis,
        curve_mode=str(overrides.pop("curve_mode", "s")),
        curve_strength=overrides.pop("curve_strength", 0.0),  # type: ignore[arg-type]
        deadzone=overrides.pop("deadzone", 0.0),  # type: ignore[arg-type]
        anti_deadzone=overrides.pop("anti_deadzone", 0.0),  # type: ignore[arg-type]
        hysteresis=overrides.pop("hysteresis", 0.0),  # type: ignore[arg-type]
        output_scale=overrides.pop("output_scale", 1.0),  # type: ignore[arg-type]
        max_output=overrides.pop("max_output", 1.0),  # type: ignore[arg-type]
        precision_scale=overrides.pop("precision_scale", 1.0),  # type: ignore[arg-type]
        invert=bool(overrides.pop("invert", False)),
    )


def _identity_filtering(axis: str = "Roll", **overrides: object) -> AxisFiltering:
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


def _all_axis_tuning(**kwargs: object) -> dict[str, AxisTuning]:
    return {axis.axis_id.value: _linear_tuning(axis.display_name, **kwargs) for axis in all_axis_definitions()}


def _all_axis_filtering(**kwargs: object) -> dict[str, AxisFiltering]:
    return {axis.axis_id.value: _identity_filtering(axis.display_name, **kwargs) for axis in all_axis_definitions()}


def _all_axis_combat(**kwargs: object) -> dict[str, AxisCombatProfile]:
    return {axis.axis_id.value: _combat(axis.display_name, **kwargs) for axis in all_axis_definitions()}


def _raw(**overrides: float) -> dict[str, float]:
    values = {axis: 0.0 for axis in AXIS_DISPLAY_NAMES}
    values.update({axis: float(value) for axis, value in overrides.items()})
    return values


def _buttons(*pressed: int) -> dict[str, bool]:
    active = set(pressed)
    return {f"B{index}": index in active for index in BUTTONS}


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


def _axis_value(intent: VirtualOutputIntent, axis_name: str) -> float:
    return next(axis.value for axis in intent.axes if axis.axis_name == axis_name)


def _button_value(intent: VirtualOutputIntent, button_name: str) -> bool:
    return next(button.pressed for button in intent.buttons if button.button_name == button_name)


def _hat_value(intent: VirtualOutputIntent, hat_name: str = "POV1") -> str:
    return next(hat.value for hat in intent.hats if hat.hat_name == hat_name)


def _pressed_button_names(intent: VirtualOutputIntent) -> tuple[str, ...]:
    return tuple(button.button_name for button in intent.buttons if button.pressed)


def _filter_stage(axis_result):
    return axis_result.stage_by_name("Filtering")


def _record(results: list[ProbeCase], section: str, name: str, passed: bool, **details: Any) -> None:
    results.append(ProbeCase(section=section, name=name, passed=passed, details=_jsonable(details)))


def _jsonable(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _finite_outputs(result) -> bool:
    return all(math.isfinite(value) and -1.0 <= value <= 1.0 for value in result.final_output_values.values())


def _run_authority_boundary(results: list[ProbeCase]) -> None:
    forbidden_prefixes = ("v3_app.pages", "v3_app.liquid", "v3_app.widgets", "PySide6")
    scanned_roots = (
        PROJECT_ROOT / "shared_core" / "math",
        PROJECT_ROOT / "shared_core" / "runtime",
        PROJECT_ROOT / "shared_core" / "rules",
        PROJECT_ROOT / "bridge_app",
    )
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
    _record(results, "runtime_authority_boundary", "shared_runtime_no_ui_imports", not violations, violations=violations)


def _parameter_inventory() -> dict[str, Any]:
    workspace = create_default_workspace()
    return {
        "curve_modes_supported": list(SUPPORTED_CURVE_MODES),
        "numeric_parameters": {group: list(parameters) for group, parameters in NUMERIC_PARAMETER_GROUPS.items()},
        "rule_supported_parameters": list(SUPPORTED_PARAMETERS),
        "rule_supported_operations": list(SUPPORTED_OPERATIONS),
        "rule_supported_injection_stages": list(SUPPORTED_INJECTION_STAGES),
        "rule_supported_measures": list(SUPPORTED_MEASURES),
        "rule_supported_mode_gates": list(SUPPORTED_MODE_GATES),
        "rule_supported_comparators": list(SUPPORTED_COMPARATORS),
        "axis_routes": [
            {
                "function_name": route.function_name,
                "raw_axis_channel": route.raw_axis_channel,
                "runtime_vjoy_output": route.runtime_vjoy_output,
            }
            for route in workspace.mappings.axis_routes
        ],
        "button_routes": [
            {"hotas_button": route.hotas_button, "output_button": route.output_button}
            for route in workspace.mappings.button_routes
        ],
        "hat_routes": [
            {
                "hotas_hat": route.hotas_hat,
                "vjoy_pov": route.vjoy_pov,
                "up_button": route.up_button,
                "right_button": route.right_button,
                "down_button": route.down_button,
                "left_button": route.left_button,
            }
            for route in workspace.mappings.hat_routes
        ],
        "known_gaps": {
            "vjoy_readback": "No vJoy readback channel exists; accepted write calls are not readback proof.",
        },
    }


def _run_curve_matrix(results: list[ProbeCase]) -> int:
    count = 0
    inputs = (-1.0, -0.75, -0.5, -0.25, -0.05, 0.0, 0.05, 0.25, 0.5, 0.75, 1.0)
    for mode in SUPPORTED_CURVE_MODES:
        for axis in AXIS_DISPLAY_NAMES:
            outputs: list[float] = []
            for value in inputs:
                result = process_axis_stack(
                    value,
                    tuning=_linear_tuning(axis, curve_mode=mode, curve_strength=0.5),
                    filtering=_identity_filtering(axis),
                    combat=_combat(axis),
                    mode_config=ModeConfig(),
                    mode_state=ModeState(),
                )
                outputs.append(result.final_output)
                stage = result.stage_by_name("Curve / Shape")
                passed = math.isfinite(result.final_output) and -1.0 <= result.final_output <= 1.0 and stage.metadata["curve_mode"] == mode
                _record(results, "curve_mode_matrix", f"{axis}_{mode}_{value}", passed, output=result.final_output)
                count += 1
            _record(
                results,
                "curve_mode_matrix_summary",
                f"{axis}_{mode}_monotonic",
                outputs == sorted(outputs),
                min_output=min(outputs),
                max_output=max(outputs),
            )
    unsupported = process_axis_stack(
        0.5,
        tuning=_linear_tuning(curve_mode="unsupported", curve_strength=0.5),
        filtering=_identity_filtering(),
        combat=_combat(),
        mode_config=ModeConfig(),
        mode_state=ModeState(),
    )
    metadata = unsupported.stage_by_name("Curve / Shape").metadata
    _record(
        results,
        "curve_mode_matrix",
        "unsupported_curve_mode_safe_default",
        metadata.get("curve_mode") == "s" and metadata.get("curve_mode_supported") is False,
        metadata=metadata,
    )
    count += 1
    return count


def _run_numeric_boundaries(results: list[ProbeCase]) -> int:
    count = 0
    for group, parameters in NUMERIC_PARAMETER_GROUPS.items():
        for parameter in parameters:
            for value in BOUNDARY_VALUES:
                try:
                    kwargs = {parameter: value}
                    if group == "tuning":
                        result = process_axis_stack(
                            0.7,
                            tuning=_linear_tuning(**kwargs),
                            filtering=_identity_filtering(),
                            combat=_combat(),
                            mode_config=ModeConfig(),
                            mode_state=ModeState(precision_active=True),
                        )
                    elif group == "filtering":
                        result = process_axis_stack(
                            0.7,
                            tuning=_linear_tuning(),
                            filtering=_identity_filtering(**kwargs),
                            combat=_combat(),
                            mode_config=ModeConfig(),
                            mode_state=ModeState(),
                        )
                    else:
                        result = process_axis_stack(
                            0.7,
                            tuning=_linear_tuning(),
                            filtering=_identity_filtering(),
                            combat=_combat(**kwargs),
                            mode_config=ModeConfig(),
                            mode_state=ModeState(combat_active=True),
                        )
                    passed = math.isfinite(result.final_output) and -1.0 <= result.final_output <= 1.0
                    _record(results, "numeric_boundary_matrix", f"{parameter}_{value!r}", passed, parameter=parameter, value=value, output=result.final_output)
                except Exception as exc:  # pragma: no cover - artifact evidence path
                    _record(results, "numeric_boundary_matrix", f"{parameter}_{value!r}", False, parameter=parameter, value=value, error=str(exc))
                count += 1
    return count


def _run_combat_filter_matrix(results: list[ProbeCase]) -> int:
    count = 0
    base_filtering = _identity_filtering(center_alpha=0.20, edge_alpha=0.20, same_slew_limit=10.0, reverse_slew_limit=10.0)
    combat_filtering = _combat(combat_center_alpha=1.0, combat_edge_alpha=1.0, combat_same_slew=0.01, combat_reverse_slew=0.01)
    inactive = process_axis_stack(
        0.40,
        tuning=_linear_tuning(),
        filtering=base_filtering,
        combat=combat_filtering,
        mode_config=ModeConfig(),
        mode_state=ModeState(),
    )
    inactive_stage = _filter_stage(inactive)
    _record(
        results,
        "combat_filter_matrix",
        "inactive_uses_base_filtering",
        math.isclose(inactive_stage.output_value, 0.08, abs_tol=1e-9)
        and inactive_stage.metadata.get("combat_filter_active") is False
        and math.isclose(float(inactive_stage.metadata.get("effective_center_alpha", -1.0)), 0.20, abs_tol=1e-9),
        metadata=inactive_stage.metadata,
        observed=inactive_stage.output_value,
        expected=0.08,
    )
    count += 1

    active_center = process_axis_stack(
        0.25,
        tuning=_linear_tuning(),
        filtering=_identity_filtering(center_alpha=0.05, edge_alpha=0.05, same_slew_limit=10.0, reverse_slew_limit=10.0),
        combat=_combat(combat_center_alpha=0.80, combat_edge_alpha=0.80, combat_same_slew=10.0, combat_reverse_slew=10.0),
        mode_config=ModeConfig(),
        mode_state=ModeState(combat_active=True),
    )
    center_stage = _filter_stage(active_center)
    _record(
        results,
        "combat_filter_matrix",
        "active_center_alpha_override",
        math.isclose(center_stage.output_value, 0.20, abs_tol=1e-9)
        and center_stage.metadata.get("combat_filter_active") is True
        and math.isclose(float(center_stage.metadata.get("effective_center_alpha", -1.0)), 0.80, abs_tol=1e-9),
        metadata=center_stage.metadata,
        observed=center_stage.output_value,
        expected=0.20,
    )
    count += 1

    active_edge = process_axis_stack(
        0.75,
        tuning=_linear_tuning(),
        filtering=_identity_filtering(center_alpha=0.05, edge_alpha=0.05, same_slew_limit=10.0, reverse_slew_limit=10.0),
        combat=_combat(combat_center_alpha=0.20, combat_edge_alpha=1.0, combat_same_slew=10.0, combat_reverse_slew=10.0),
        mode_config=ModeConfig(),
        mode_state=ModeState(combat_active=True),
    )
    edge_stage = _filter_stage(active_edge)
    expected_alpha = 0.20 + (1.0 - 0.20) * 0.75
    _record(
        results,
        "combat_filter_matrix",
        "active_edge_alpha_override",
        math.isclose(float(edge_stage.metadata.get("alpha", -1.0)), expected_alpha, abs_tol=1e-9)
        and math.isclose(edge_stage.output_value, 0.75 * expected_alpha, abs_tol=1e-9),
        metadata=edge_stage.metadata,
        observed=edge_stage.output_value,
        expected=0.75 * expected_alpha,
    )
    count += 1

    slew_filtering = _identity_filtering(center_alpha=1.0, edge_alpha=1.0, same_slew_limit=10.0, reverse_slew_limit=10.0)
    slew_combat = _combat(combat_center_alpha=1.0, combat_edge_alpha=1.0, combat_same_slew=0.10, combat_reverse_slew=0.05)
    same = process_axis_stack(
        1.0,
        tuning=_linear_tuning(),
        filtering=slew_filtering,
        combat=slew_combat,
        mode_config=ModeConfig(),
        mode_state=ModeState(combat_active=True),
    )
    same_stage = _filter_stage(same)
    _record(
        results,
        "combat_filter_matrix",
        "active_same_slew_override",
        math.isclose(same_stage.output_value, 0.10, abs_tol=1e-9)
        and math.isclose(float(same_stage.metadata.get("effective_same_slew_limit", -1.0)), 0.10, abs_tol=1e-9),
        metadata=same_stage.metadata,
        observed=same_stage.output_value,
        expected=0.10,
    )
    count += 1

    reverse = process_axis_stack(
        -1.0,
        tuning=_linear_tuning(),
        filtering=slew_filtering,
        combat=slew_combat,
        mode_config=ModeConfig(),
        mode_state=ModeState(combat_active=True),
        previous_filter_state=same.filter_state,
    )
    reverse_stage = _filter_stage(reverse)
    _record(
        results,
        "combat_filter_matrix",
        "active_reverse_slew_override",
        math.isclose(reverse_stage.output_value, 0.05, abs_tol=1e-9)
        and reverse_stage.metadata.get("slew_path") == "reverse-direction"
        and math.isclose(float(reverse_stage.metadata.get("effective_reverse_slew_limit", -1.0)), 0.05, abs_tol=1e-9),
        metadata=reverse_stage.metadata,
        observed=reverse_stage.output_value,
        expected=0.05,
    )
    count += 1

    transition_workspace = _workspace_for_axes(
        tuning_by_id=_all_axis_tuning(),
        filtering_by_id=_all_axis_filtering(center_alpha=0.20, edge_alpha=0.20, same_slew_limit=10.0, reverse_slew_limit=10.0),
        combat_by_id=_all_axis_combat(combat_center_alpha=1.0, combat_edge_alpha=1.0, combat_same_slew=10.0, combat_reverse_slew=10.0),
    )
    pipeline = WorkspaceSignalPipeline(transition_workspace)
    state = pipeline.initial_state()
    transition_outputs: list[float] = []
    transition_active: list[bool] = []
    for raw_roll, active in ((0.5, False), (1.0, True), (0.0, False)):
        output = pipeline.process(_raw(Roll=raw_roll), state=state, mode_state=ModeState(combat_active=active))
        state = output.state
        stage = _filter_stage(output.axis_results["Roll"])
        transition_outputs.append(stage.output_value)
        transition_active.append(bool(stage.metadata.get("combat_filter_active")))
    _record(
        results,
        "combat_filter_matrix",
        "inactive_active_inactive_transition",
        transition_active == [False, True, False]
        and all(math.isclose(observed, expected, abs_tol=1e-9) for observed, expected in zip(transition_outputs, (0.10, 1.0, 0.80))),
        observed=transition_outputs,
        expected=[0.10, 1.0, 0.80],
        active=transition_active,
    )
    count += 1

    combat_by_id = _all_axis_combat(combat_center_alpha=0.40, combat_edge_alpha=0.40, combat_same_slew=10.0, combat_reverse_slew=10.0)
    combat_by_id["roll"] = _combat("Roll", combat_center_alpha=0.90, combat_edge_alpha=0.90)
    combat_by_id["pitch"] = _combat("Pitch", combat_center_alpha=0.30, combat_edge_alpha=0.30)
    combat_by_id["yaw"] = _combat("Yaw", combat_center_alpha=1.0, combat_edge_alpha=1.0, combat_same_slew=0.05)
    independent = WorkspaceSignalPipeline(
        _workspace_for_axes(
            tuning_by_id=_all_axis_tuning(),
            filtering_by_id=_all_axis_filtering(center_alpha=0.10, edge_alpha=0.10, same_slew_limit=10.0, reverse_slew_limit=10.0),
            combat_by_id=combat_by_id,
        )
    ).process(_raw(Roll=0.50, Pitch=0.50, Throttle=0.50, Yaw=1.0), mode_state=ModeState(combat_active=True))
    roll_meta = _filter_stage(independent.axis_results["Roll"]).metadata
    pitch_meta = _filter_stage(independent.axis_results["Pitch"]).metadata
    yaw_stage = _filter_stage(independent.axis_results["Yaw"])
    _record(
        results,
        "combat_filter_matrix",
        "per_axis_combat_filter_independence",
        math.isclose(float(roll_meta.get("effective_center_alpha", -1.0)), 0.90, abs_tol=1e-9)
        and math.isclose(float(pitch_meta.get("effective_center_alpha", -1.0)), 0.30, abs_tol=1e-9)
        and math.isclose(float(yaw_stage.metadata.get("effective_same_slew_limit", -1.0)), 0.05, abs_tol=1e-9)
        and math.isclose(yaw_stage.output_value, 0.05, abs_tol=1e-9),
        roll_metadata=roll_meta,
        pitch_metadata=pitch_meta,
        yaw_metadata=yaw_stage.metadata,
    )
    count += 1

    invalid = process_axis_stack(
        0.80,
        tuning=_linear_tuning(),
        filtering=_identity_filtering(center_alpha=0.30, edge_alpha=0.70, same_slew_limit=0.40, reverse_slew_limit=0.25),
        combat=_combat(combat_center_alpha=float("nan"), combat_edge_alpha="bad", combat_same_slew=None, combat_reverse_slew=float("inf")),
        mode_config=ModeConfig(),
        mode_state=ModeState(combat_active=True),
    )
    invalid_stage = _filter_stage(invalid)
    _record(
        results,
        "combat_filter_matrix",
        "invalid_combat_filter_values_fail_safe",
        math.isfinite(invalid.final_output)
        and math.isclose(float(invalid_stage.metadata.get("effective_center_alpha", -1.0)), 0.30, abs_tol=1e-9)
        and math.isclose(float(invalid_stage.metadata.get("effective_edge_alpha", -1.0)), 0.70, abs_tol=1e-9)
        and math.isclose(float(invalid_stage.metadata.get("effective_same_slew_limit", -1.0)), 0.40, abs_tol=1e-9),
        metadata=invalid_stage.metadata,
        output=invalid.final_output,
    )
    count += 1
    return count


def _run_mapping_matrix(results: list[ProbeCase]) -> int:
    final_axes = {"Roll": 0.11, "Pitch": 0.22, "Throttle": 0.33, "Yaw": 0.44, "Aux 1": 0.55, "Aux 2": 0.66}
    workspace = create_default_workspace()
    cases: list[tuple[str, object, list[float]]] = [
        ("default", workspace, [0.11, 0.22, 0.33, 0.44, 0.55, 0.66]),
        (
            "roll_pitch_swap_yaw_aux_swap",
            replace(
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
            ),
            [0.22, 0.11, 0.33, 0.55, 0.44, 0.66],
        ),
        (
            "throttle_to_rz",
            replace(workspace, mappings=replace(workspace.mappings, axis_routes=(AxisMapping("Throttle", "Axis 3", "RZ", "RZ(axis6)"),))),
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.33],
        ),
        ("roll_unmapped", replace(workspace, mappings=replace(workspace.mappings, axis_routes=workspace.mappings.axis_routes[1:])), [0.0, 0.22, 0.33, 0.44, 0.55, 0.66]),
        (
            "duplicate_x_last_wins",
            replace(workspace, mappings=replace(workspace.mappings, axis_routes=(AxisMapping("Roll", "Axis 1", "X", "X(axis1)"), AxisMapping("Pitch", "Axis 2", "X", "X(axis1)")))),
            [0.22, 0.0, 0.0, 0.0, 0.0, 0.0],
        ),
        ("invalid_target_skipped", replace(workspace, mappings=replace(workspace.mappings, axis_routes=(AxisMapping("Roll", "Axis 1", "NOPE", "NOPE"),))), [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    ]
    for name, case_workspace, expected in cases:
        intent = build_workspace_virtual_output_intent(final_axes, workspace=case_workspace)
        observed = [_axis_value(intent, axis) for axis in VJOY_AXES]
        passed = all(math.isclose(observed[index], expected[index], abs_tol=1e-9) for index in range(len(expected)))
        _record(results, "axis_mapping_matrix", name, passed, observed=observed, expected=expected)
    return len(cases)


def _run_button_hat_matrix(results: list[ProbeCase]) -> tuple[int, int]:
    workspace = create_default_workspace()
    final_axes = {axis: 0.0 for axis in AXIS_DISPLAY_NAMES}
    button_count = 0
    for button in BUTTONS:
        press = build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons(button))
        hold = build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons(button))
        release = build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons())
        passed = (
            _button_value(press, f"Out{button}") is True
            and _button_value(hold, f"Out{button}") is True
            and _button_value(release, f"Out{button}") is False
            and [item.button_name for item in press.buttons if item.pressed] == [f"Out{button}"]
        )
        _record(results, "button_behavior_matrix", f"B{button}_press_hold_release", passed)
        button_count += 3
    rapid = [
        build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons()),
        build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons(3)),
        build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons()),
    ]
    _record(results, "button_behavior_matrix", "rapid_tap_B3", [_button_value(intent, "Out3") for intent in rapid] == [False, True, False])
    button_count += 3
    simultaneous = build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons(1, 2, 3))
    _record(results, "button_behavior_matrix", "three_buttons_simultaneous", [item.button_name for item in simultaneous.buttons if item.pressed] == ["Out1", "Out2", "Out3"])
    button_count += 1
    all_true = build_workspace_virtual_output_intent(final_axes, workspace=workspace, button_states=_buttons(*BUTTONS))
    _record(results, "button_behavior_matrix", "all_buttons_true", len([item for item in all_true.buttons if item.pressed]) == 15)
    button_count += 1
    swapped = replace(workspace, mappings=replace(workspace.mappings, button_routes=(ButtonMapping(1, 2), ButtonMapping(2, 1), *workspace.mappings.button_routes[2:])))
    swapped_intent = build_workspace_virtual_output_intent(final_axes, workspace=swapped, button_states=_buttons(1))
    _record(results, "button_mapping_matrix", "B1_B2_swap", _button_value(swapped_intent, "Out2") is True and _button_value(swapped_intent, "Out1") is False)
    button_count += 1
    duplicate = replace(workspace, mappings=replace(workspace.mappings, button_routes=(ButtonMapping(1, 1), ButtonMapping(2, 1))))
    duplicate_intent = build_workspace_virtual_output_intent(final_axes, workspace=duplicate, button_states=_buttons(1))
    _record(results, "button_mapping_matrix", "duplicate_output_or_semantics", _button_value(duplicate_intent, "Out1") is True)
    button_count += 1

    hat_states = ("Centered", "Up", "UpRight", "Right", "DownRight", "Down", "DownLeft", "Left", "UpLeft", "sideways-ish")
    for state in hat_states:
        intent = build_workspace_virtual_output_intent(final_axes, workspace=workspace, hat_state=state)
        expected = "Centered" if state == "sideways-ish" else state
        _record(results, "hat_pov_matrix", state, _hat_value(intent) == expected, observed=_hat_value(intent), expected=expected)
    return button_count, len(hat_states)


def _run_hat_button_mapping_matrix(results: list[ProbeCase]) -> int:
    final_axes = {axis: 0.0 for axis in AXIS_DISPLAY_NAMES}
    workspace = create_default_workspace()
    count = 0

    no_mapping = replace(workspace, mappings=replace(workspace.mappings, hat_routes=()))
    for state, expected in (
        ("Centered", "Centered"),
        ("Up", "Up"),
        ("Down", "Down"),
        ("Left", "Left"),
        ("Right", "Right"),
        ("sideways-ish", "Centered"),
    ):
        intent = build_workspace_virtual_output_intent(final_axes, workspace=no_mapping, hat_state=state)
        _record(
            results,
            "hat_button_mapping_matrix",
            f"pov_passthrough_{state}",
            _hat_value(intent) == expected and _pressed_button_names(intent) == (),
            observed_hat=_hat_value(intent),
            expected_hat=expected,
            pressed_buttons=_pressed_button_names(intent),
        )
        count += 1

    mapped = replace(
        workspace,
        mappings=replace(
            workspace.mappings,
            hat_routes=(HatMapping(hotas_hat=1, vjoy_pov=1, up_button=9, right_button=10, down_button=11, left_button=12),),
        ),
    )
    for state, expected_button in (("Up", "Out9"), ("Right", "Out10"), ("Down", "Out11"), ("Left", "Out12")):
        intent = build_workspace_virtual_output_intent(final_axes, workspace=mapped, hat_state=state)
        _record(
            results,
            "hat_button_mapping_matrix",
            f"cardinal_{state}_to_{expected_button}",
            _pressed_button_names(intent) == (expected_button,),
            observed=_pressed_button_names(intent),
            expected=[expected_button],
            pov=_hat_value(intent),
        )
        count += 1

    released = build_workspace_virtual_output_intent(final_axes, workspace=mapped, hat_state="Centered")
    _record(
        results,
        "hat_button_mapping_matrix",
        "neutral_releases_hat_buttons",
        _pressed_button_names(released) == () and _hat_value(released) == "Centered",
        observed=_pressed_button_names(released),
    )
    count += 1

    duplicate = replace(
        workspace,
        mappings=replace(
            workspace.mappings,
            button_routes=(ButtonMapping(hotas_button=5, output_button=9),),
            hat_routes=(HatMapping(hotas_hat=1, vjoy_pov=1, up_button=9),),
        ),
    )
    or_sequence = [
        _button_value(build_workspace_virtual_output_intent(final_axes, workspace=duplicate, button_states=_buttons(), hat_state="Centered"), "Out9"),
        _button_value(build_workspace_virtual_output_intent(final_axes, workspace=duplicate, button_states=_buttons(5), hat_state="Centered"), "Out9"),
        _button_value(build_workspace_virtual_output_intent(final_axes, workspace=duplicate, button_states=_buttons(), hat_state="Up"), "Out9"),
        _button_value(build_workspace_virtual_output_intent(final_axes, workspace=duplicate, button_states=_buttons(5), hat_state="Up"), "Out9"),
        _button_value(build_workspace_virtual_output_intent(final_axes, workspace=duplicate, button_states=_buttons(5), hat_state="Centered"), "Out9"),
        _button_value(build_workspace_virtual_output_intent(final_axes, workspace=duplicate, button_states=_buttons(), hat_state="Centered"), "Out9"),
    ]
    _record(
        results,
        "hat_button_mapping_matrix",
        "hat_and_button_duplicate_or_semantics",
        or_sequence == [False, True, True, True, True, False],
        observed=or_sequence,
        expected=[False, True, True, True, True, False],
    )
    count += 1

    invalid = replace(
        workspace,
        mappings=replace(workspace.mappings, hat_routes=(HatMapping(hotas_hat=1, vjoy_pov=1, up_button=999, right_button=10),)),
    )
    invalid_up = build_workspace_virtual_output_intent(final_axes, workspace=invalid, hat_state="Up")
    valid_right = build_workspace_virtual_output_intent(final_axes, workspace=invalid, hat_state="Right")
    _record(
        results,
        "hat_button_mapping_matrix",
        "invalid_hat_button_target_skipped",
        _pressed_button_names(invalid_up) == () and _pressed_button_names(valid_right) == ("Out10",),
        invalid_observed=_pressed_button_names(invalid_up),
        valid_observed=_pressed_button_names(valid_right),
    )
    count += 1

    diagonal = replace(
        workspace,
        mappings=replace(workspace.mappings, hat_routes=(HatMapping(hotas_hat=1, vjoy_pov=1, up_button=9, right_button=10),)),
    )
    diagonal_intent = build_workspace_virtual_output_intent(final_axes, workspace=diagonal, hat_state="UpRight")
    _record(
        results,
        "hat_button_mapping_matrix",
        "diagonal_decomposes_to_cardinal_buttons",
        set(_pressed_button_names(diagonal_intent)) == {"Out9", "Out10"} and _hat_value(diagonal_intent) == "UpRight",
        observed=_pressed_button_names(diagonal_intent),
        expected=["Out9", "Out10"],
        pov=_hat_value(diagonal_intent),
    )
    count += 1

    writer = FakeVirtualOutputBackend()
    writer_intent = build_workspace_virtual_output_intent(final_axes, workspace=diagonal, hat_state="UpRight")
    write_result = writer.write_output_intent(writer_intent)
    _record(
        results,
        "hat_button_mapping_matrix",
        "fake_writer_payload_matches_hat_button_intent",
        write_result.success and writer.last_written_intent == writer_intent and set(_pressed_button_names(writer.last_written_intent)) == {"Out9", "Out10"},
        observed=_pressed_button_names(writer.last_written_intent) if writer.last_written_intent is not None else [],
    )
    count += 1
    return count


def _run_mode_matrix(results: list[ProbeCase]) -> int:
    modes = ModeConfig(precision_hold_buttons=(1,), combat_zoom_aim_buttons=(5,), precision_combat_stack_mode=StackMode.MULTIPLY)
    workspace = _workspace_for_axes(
        tuning_by_id=_all_axis_tuning(precision_scale=0.5),
        filtering_by_id=_all_axis_filtering(),
        combat_by_id=_all_axis_combat(combat_curve=0.0, combat_scale=0.5),
        modes=modes,
    )
    cases = (
        ("inactive", _buttons(), 0.8, False, False),
        ("precision_active", _buttons(1), 0.4, True, False),
        ("combat_active", _buttons(5), 0.4, False, True),
        ("precision_and_combat_active", _buttons(1, 5), 0.2, True, True),
    )
    for name, buttons, expected, precision_active, combat_active in cases:
        frame = _runtime_frame(workspace, _raw(Roll=0.8), buttons=buttons)
        mode_metadata = frame.pipeline.axis_stage_values["Roll"][5]["metadata"]
        passed = (
            math.isclose(frame.pipeline.final_output_values["Roll"], expected, abs_tol=1e-9)
            and mode_metadata["precision_active"] is precision_active
            and mode_metadata["combat_active"] is combat_active
        )
        _record(results, "mode_modifier_matrix", name, passed, observed=frame.pipeline.final_output_values["Roll"], expected=expected, metadata=mode_metadata)
    return len(cases)


def _run_rule_matrix(results: list[ProbeCase]) -> int:
    count = 0
    context = RuleEvaluationContext(values_by_stage={"Final Output": {"Roll": 0.5, "Yaw": 0.25}})
    comparator_thresholds = {
        "greater than": (0.4, None, True),
        "less than": (0.4, None, False),
        "equal": (0.5, None, True),
        "approximately": (0.5, None, True),
        "between": (0.4, 0.6, True),
        "range": (0.4, 0.6, True),
    }
    for comparator, (threshold, threshold_high, expected) in comparator_thresholds.items():
        result = evaluate_rule(replace(yaw_roll_example_rule(), enabled=True, comparator=comparator, threshold=threshold, threshold_high=threshold_high), context)
        _record(results, "conditional_rule_matrix", f"comparator_{comparator}", result.applies is expected, status=result.status.value)
        count += 1
    for operation, expected_scale in (("Set", 0.5), ("Add", 1.5), ("Multiply", 0.5)):
        workspace = _workspace_for_axes(
            tuning_by_id=_all_axis_tuning(),
            filtering_by_id=_all_axis_filtering(),
            combat_by_id=_all_axis_combat(),
            rules=(replace(yaw_roll_example_rule(), enabled=True, target_axis="Yaw", operation=operation, value=0.5),),
        )
        result = WorkspaceSignalPipeline(workspace).process(_raw(Roll=0.8, Yaw=0.8))
        observed = result.axis_results["Yaw"].stage_by_name("Base Output Limits").metadata["output_scale"]
        _record(results, "conditional_rule_matrix", f"operation_{operation}", math.isclose(observed, expected_scale, abs_tol=1e-9), observed=observed, expected=expected_scale)
        count += 1
    invalid_cases = (
        ("invalid_target_axis", replace(yaw_roll_example_rule(), enabled=True, target_axis="Nope")),
        ("invalid_reference_axis", replace(yaw_roll_example_rule(), enabled=True, reference_axis="Nope")),
        ("invalid_parameter", replace(yaw_roll_example_rule(), enabled=True, parameter="Max Output")),
        ("invalid_comparator", replace(yaw_roll_example_rule(), enabled=True, comparator="outside")),
        ("missing_threshold_high", replace(yaw_roll_example_rule(), enabled=True, comparator="between", threshold_high=None)),
    )
    for name, rule in invalid_cases:
        result = evaluate_rule(rule, context)
        _record(results, "conditional_rule_matrix", name, result.status is RuleStatus.BLOCKED, status=result.status.value, reason=result.blocked_reason)
        count += 1
    gated = replace(yaw_roll_example_rule(), enabled=True, mode_gate="Combat", buttons=(5,), target_axis="Yaw", value=0.25)
    gated_workspace = _workspace_for_axes(
        tuning_by_id=_all_axis_tuning(),
        filtering_by_id=_all_axis_filtering(),
        combat_by_id=_all_axis_combat(),
        rules=(gated,),
    )
    inactive = WorkspaceSignalPipeline(gated_workspace).process(_raw(Roll=0.8, Yaw=0.8), mode_state=ModeState(combat_active=True), active_buttons=())
    active = WorkspaceSignalPipeline(gated_workspace).process(_raw(Roll=0.8, Yaw=0.8), mode_state=ModeState(combat_active=True), active_buttons=(5,))
    _record(results, "conditional_rule_matrix", "mode_button_gated_inactive", inactive.rule_evaluations[0].status is RuleStatus.INACTIVE, status=inactive.rule_evaluations[0].status.value)
    _record(results, "conditional_rule_matrix", "mode_button_gated_active", active.rule_evaluations[0].status is RuleStatus.ACTIVE, status=active.rule_evaluations[0].status.value)
    return count + 2


def _run_stage_consistency(results: list[ProbeCase]) -> int:
    workspace = create_default_workspace()
    frame = _runtime_frame(workspace, _raw(Roll=0.6, Pitch=-0.4, Throttle=0.5, Yaw=0.2, **{"Aux 1": -0.2, "Aux 2": 0.1}), buttons=_buttons(1, 4))
    count = 0
    for axis_name, stages in frame.pipeline.axis_stage_values.items():
        passed = tuple(stage["stage_name"] for stage in stages) == EXPECTED_STAGE_NAMES
        passed = passed and all(math.isfinite(stage["input_value"]) and math.isfinite(stage["output_value"]) and math.isfinite(stage["delta"]) for stage in stages)
        passed = passed and math.isclose(stages[-1]["output_value"], frame.pipeline.final_output_values[axis_name], abs_tol=1e-9)
        _record(results, "stage_telemetry_consistency", axis_name, passed)
        count += 1
    backend = FakeVirtualOutputBackend()
    write = backend.write_output_intent(frame.output_intent)
    _record(results, "writer_payload_consistency", "fake_writer_matches_intent", write.success and backend.last_written_intent == frame.output_intent)
    return count


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


def _run_pairwise(results: list[ProbeCase]) -> int:
    cases = _pairwise_cases()
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
        pipeline = WorkspaceSignalPipeline(workspace)
        state = pipeline.initial_state()
        passed = True
        for raw_roll in (0.0, 0.3, 0.8, -0.4):
            output = pipeline.process(_raw(Roll=raw_roll, Yaw=0.7), state=state, mode_state=ModeState(precision_active=bool(case["mode"])))
            state = output.state
            passed = passed and _finite_outputs(output)
        _record(results, "pairwise_interaction_matrix", str(case["pair"]), passed)
    return len(cases)


def _run_fuzz(results: list[ProbeCase]) -> int:
    count = 0
    for seed in FUZZ_SEEDS:
        rng = random.Random(seed)
        for index in range(FUZZ_CASES_PER_SEED):
            routes = list(create_default_workspace().mappings.axis_routes)
            rng.shuffle(routes)
            vjoy_targets = list(VJOY_AXES)
            rng.shuffle(vjoy_targets)
            remapped_routes = tuple(
                replace(route, logical_output=vjoy_targets[position], runtime_vjoy_output=f"{vjoy_targets[position]}(axis{position + 1})")
                for position, route in enumerate(routes)
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
                buttons=_buttons(*(button for button in BUTTONS if rng.random() < 0.2)),
                hat_state=rng.choice(("Centered", "Up", "Down", "Left", "Right")),
            )
            passed = frame.runtime_orchestrator_rebuild_count == 1
            passed = passed and all(math.isfinite(value) and -1.0 <= value <= 1.0 for value in frame.pipeline.final_output_values.values())
            passed = passed and all(math.isfinite(axis.value) and -1.0 <= axis.value <= 1.0 for axis in frame.output_intent.axes)
            backend = FakeVirtualOutputBackend()
            backend.write_output_intent(frame.output_intent)
            passed = passed and backend.last_written_intent == frame.output_intent
            _record(results, "seeded_fuzz_property", f"seed_{seed}_case_{index}", passed)
            count += 1
    return count


def _run_real_vjoy_subset(results: list[ProbeCase], enabled: bool) -> dict[str, Any]:
    backend = RealVJoyOutputBackend()
    caps = backend.get_capabilities()
    devices = backend.enumerate_output_devices()
    summary = {
        "requested": enabled,
        "available": bool(caps.backend_available and caps.real_output_writes_available and devices),
        "devices": [device.display_name for device in devices],
        "write_attempts": 0,
        "write_successes": 0,
        "readback_verified": False,
    }
    if not enabled or not summary["available"]:
        _record(results, "real_vjoy_optional", "real_vjoy_subset", True, **summary, status="skipped")
        return summary
    intents = [
        build_workspace_virtual_output_intent({"Roll": 0.2, "Pitch": -0.2, "Throttle": 0.5, "Yaw": 0.1, "Aux 1": 0.0, "Aux 2": 0.0}, workspace=create_default_workspace(), button_states=_buttons()),
        build_workspace_virtual_output_intent({axis: 0.0 for axis in AXIS_DISPLAY_NAMES}, workspace=create_default_workspace(), button_states=_buttons(1, 2, 3)),
        build_workspace_virtual_output_intent({axis: 0.0 for axis in AXIS_DISPLAY_NAMES}, workspace=create_default_workspace(), hat_state="Up"),
    ]
    for intent in intents:
        result = backend.write_output_intent(intent)
        summary["write_attempts"] += 1
        if result.success:
            summary["write_successes"] += 1
    _record(results, "real_vjoy_optional", "real_vjoy_subset", summary["write_attempts"] == summary["write_successes"], **summary, status="write_call_proof_only")
    return summary


def _live_probe() -> dict[str, Any]:
    bridge = subprocess.run(
        [sys.executable, "-m", "bridge_app.main", "--status"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    setup = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\\scripts\\runtime_setup_check.ps1", "-DryRun"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "bridge_status_exit": bridge.returncode,
        "bridge_status": bridge.stdout.strip().splitlines()[0] if bridge.stdout.strip() else bridge.stderr.strip(),
        "runtime_setup_exit": setup.returncode,
        "hotas_pid_proof": "\n".join(line for line in setup.stdout.splitlines() if "VID_044F&PID_B68D" in line),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_table(path: Path, title: str, rows: list[tuple[str, str, str]]) -> None:
    lines = [f"# {title}", "", "| Item | Status | Evidence |", "|---|---|---|"]
    for item, status, evidence in rows:
        lines.append(f"| {item} | {status} | {evidence} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _coverage_summary(results: list[ProbeCase], counts: Mapping[str, int], inventory: Mapping[str, Any]) -> dict[str, Any]:
    failures = [case for case in results if not case.passed]
    return {
        "overall_status": "failed" if failures else "passed",
        "failures": len(failures),
        "setting_families": {
            "base_tuning": "covered",
            "filtering": "covered",
            "combat_curve_scale": "covered",
            "combat_filter_parameters": "covered",
            "modes": "covered",
            "conditional_rules": "covered",
            "axis_mapping": "covered",
            "button_mapping": "covered",
            "hat_pov": "pov_passthrough_and_hat_button_mapping_covered",
        },
        "generated_case_counts": dict(counts),
        "inventory_gaps": dict(inventory["known_gaps"]),
    }


def _render_report(
    *,
    generated_at: str,
    artifact_dir: Path,
    counts: Mapping[str, int],
    coverage: Mapping[str, Any],
    inventory: Mapping[str, Any],
    live: Mapping[str, Any],
    real_vjoy: Mapping[str, Any],
    failures: list[ProbeCase],
) -> str:
    lines: list[str] = []
    lines.append("# Runtime Usability 1B Full Tuning Matrix Report")
    lines.append("")
    lines.append(f"Generated: `{generated_at}`")
    lines.append(f"Artifact directory: `{artifact_dir}`")
    lines.append(f"Overall status: `{coverage['overall_status']}`")
    lines.append("")
    lines.append("## Executive Result")
    if failures:
        lines.append(f"- Matrix status: failed with {len(failures)} failures. Failures are listed in `failures.json`.")
    else:
        lines.append("- Matrix status: passed. No deterministic runtime matrix failures were detected.")
    lines.append("- Physical HOTAS proof: deferred/unplugged; this phase intentionally uses simulated/fake input.")
    lines.append(f"- Bridge status: `{live.get('bridge_status')}`")
    lines.append(f"- vJoy optional write-call requested: `{real_vjoy.get('requested')}`")
    lines.append(f"- vJoy optional write-call available: `{real_vjoy.get('available')}`")
    lines.append("- vJoy readback status: not implemented; accepted write calls are not readback proof.")
    lines.append("")
    lines.append("## Runtime Authority Boundary")
    lines.append("- UI pages/widgets are not used as runtime calculation authority.")
    lines.append("- Bridge/shared_core owns runtime math, rule evaluation, output intent, and writer payload construction.")
    lines.append("- v3_app telemetry parsing may display Bridge values, but this probe does not use UI pages as expected-value calculators.")
    lines.append("")
    lines.append("## Parameter Inventory")
    lines.append(f"- Curve modes tested: `{', '.join(inventory['curve_modes_supported'])}`")
    lines.append(f"- Numeric tuning parameters: `{', '.join(inventory['numeric_parameters']['tuning'])}`")
    lines.append(f"- Numeric filtering parameters: `{', '.join(inventory['numeric_parameters']['filtering'])}`")
    lines.append(f"- Numeric combat parameters inventoried: `{', '.join(inventory['numeric_parameters']['combat'])}`")
    lines.append(f"- Conditional rule comparators: `{', '.join(inventory['rule_supported_comparators'])}`")
    lines.append(f"- Conditional rule operations: `{', '.join(inventory['rule_supported_operations'])}`")
    lines.append(f"- Conditional rule injection targets currently supported: `{', '.join(inventory['rule_supported_parameters'])}` at `{', '.join(inventory['rule_supported_injection_stages'])}`")
    lines.append("")
    lines.append("## Generated Counts")
    lines.append("| Area | Cases |")
    lines.append("|---|---:|")
    for key, value in counts.items():
        lines.append(f"| `{key}` | {value} |")
    lines.append("")
    lines.append("## Coverage Summary")
    lines.append("| Family | Status |")
    lines.append("|---|---|")
    for key, value in coverage["setting_families"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.append("")
    lines.append("## Known Gaps / Deferred Items")
    for key, value in inventory["known_gaps"].items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("## Evidence Tables")
    lines.append("- `parameter-inventory.json`")
    lines.append("- `coverage-summary.json`")
    lines.append("- `matrix-results.json`")
    lines.append("- `generated-case-counts.json`")
    lines.append("- `known-gaps.json`")
    lines.append("- `tuning-boundary-table.md`")
    lines.append("- `rule-matrix-table.md`")
    lines.append("- `mode-matrix-table.md`")
    lines.append("- `combat-filter-table.md`")
    lines.append("- `hat-button-mapping-table.md`")
    lines.append("")
    lines.append("## Runtime Truth Preservation Statement")
    lines.append("- Missing HOTAS does not fail this phase; physical sampling proof remains deferred.")
    lines.append("- Real vJoy write-call proof, when requested and available, remains separate from readback proof.")
    lines.append("- Full Live Runtime Ready and Bridge lifecycle semantics were not loosened.")
    lines.append("- No UI redesign, Live Monitor performance work, animations, Flight Recorder work, game injection, graphics hooking, cloud AI/LLM behavior, or auto-save behavior was added by this probe.")
    lines.append("")
    return "\n".join(lines)


def run_probe(*, real_vjoy_writes: bool) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = ARTIFACT_ROOT / generated_at
    artifact_dir.mkdir(parents=True, exist_ok=True)

    results: list[ProbeCase] = []
    counts: dict[str, int] = {}
    live = _live_probe()
    inventory = _parameter_inventory()

    _run_authority_boundary(results)
    counts["runtime_authority_boundary"] = 1
    counts["curve_mode_cases"] = _run_curve_matrix(results)
    counts["numeric_boundary_cases"] = _run_numeric_boundaries(results)
    counts["combat_filter_cases"] = _run_combat_filter_matrix(results)
    counts["axis_mapping_cases"] = _run_mapping_matrix(results)
    button_count, hat_count = _run_button_hat_matrix(results)
    counts["button_behavior_cases"] = button_count
    counts["hat_pov_cases"] = hat_count
    counts["hat_button_mapping_cases"] = _run_hat_button_mapping_matrix(results)
    counts["mode_cases"] = _run_mode_matrix(results)
    counts["conditional_rule_cases"] = _run_rule_matrix(results)
    counts["stage_telemetry_cases"] = _run_stage_consistency(results)
    counts["pairwise_cases"] = _run_pairwise(results)
    counts["seeded_fuzz_property_cases"] = _run_fuzz(results)
    real_vjoy = _run_real_vjoy_subset(results, real_vjoy_writes)
    counts["real_vjoy_optional_cases"] = int(real_vjoy.get("write_attempts", 0))

    failures = [case for case in results if not case.passed]
    coverage = _coverage_summary(results, counts, inventory)

    result_payload = [
        {"section": case.section, "name": case.name, "passed": case.passed, "details": dict(case.details)}
        for case in results
    ]
    _write_json(artifact_dir / "summary.json", {
        "generated_at": generated_at,
        "overall_status": coverage["overall_status"],
        "artifact_dir": str(artifact_dir),
        "failure_count": len(failures),
        "generated_case_counts": counts,
        "hardware": {
            "physical_hotas_proof": "deferred_unplugged" if not live.get("hotas_pid_proof") else live.get("hotas_pid_proof"),
            "bridge_status": live.get("bridge_status"),
            "vjoy_write_call": real_vjoy,
            "vjoy_readback": "not_implemented",
        },
    })
    _write_json(artifact_dir / "matrix-results.json", result_payload)
    _write_json(
        artifact_dir / "failures.json",
        [
            {"section": case.section, "name": case.name, "passed": case.passed, "details": dict(case.details)}
            for case in failures
        ],
    )
    _write_json(artifact_dir / "generated-case-counts.json", counts)
    _write_json(artifact_dir / "coverage-summary.json", coverage)
    _write_json(artifact_dir / "parameter-inventory.json", inventory)
    _write_json(artifact_dir / "known-gaps.json", inventory["known_gaps"])

    _write_table(
        artifact_dir / "tuning-boundary-table.md",
        "Runtime Tuning Boundary Matrix",
        [(parameter, "covered", f"{len(BOUNDARY_VALUES)} boundary values") for group in NUMERIC_PARAMETER_GROUPS.values() for parameter in group],
    )
    _write_table(
        artifact_dir / "rule-matrix-table.md",
        "Conditional Rule Matrix",
        [
            ("Comparators", "covered", ", ".join(SUPPORTED_COMPARATORS)),
            ("Operations", "covered", ", ".join(SUPPORTED_OPERATIONS)),
            ("Injection Parameters", "partial", ", ".join(SUPPORTED_PARAMETERS)),
            ("Invalid Rules", "covered", "invalid target/reference/parameter/comparator/missing range high"),
            ("Mode/Button Gates", "covered", "Combat + B5 active/inactive"),
        ],
    )
    _write_table(
        artifact_dir / "mode-matrix-table.md",
        "Mode Modifier Matrix",
        [
            ("Inactive", "covered", "no scale applied"),
            ("Precision", "covered", "precision_hold_buttons activate precision_scale"),
            ("Combat", "covered", "combat buttons activate combat curve/scale"),
            ("Precision + Combat", "covered", "multiply stack mode applies both"),
        ],
    )
    _write_table(
        artifact_dir / "combat-filter-table.md",
        "Combat Filter Runtime Matrix",
        [
            ("Inactive base filtering", "covered", "combat filter parameters have no effect while combat is inactive"),
            ("Combat alpha override", "covered", "combat_center_alpha and combat_edge_alpha become effective filter values"),
            ("Combat slew override", "covered", "combat_same_slew and combat_reverse_slew limit same/reverse motion"),
            ("Mode transition", "covered", "inactive -> active -> inactive preserves previous output state"),
            ("Per-axis independence", "covered", "each axis reports its own effective combat filter values"),
            ("Invalid combat values", "covered", "invalid combat filter values fall back to base finite values"),
        ],
    )
    _write_table(
        artifact_dir / "hat-button-mapping-table.md",
        "Hat To Button Runtime Matrix",
        [
            ("POV passthrough", "covered", "normalized POV1 output remains emitted"),
            ("Cardinal mappings", "covered", "Up/Right/Down/Left drive configured output buttons"),
            ("Neutral release", "covered", "Centered releases hat-derived output buttons"),
            ("OR semantics", "covered", "hat routes OR with normal button routes"),
            ("Invalid targets", "covered", "invalid hat button targets are skipped safely"),
            ("Diagonal policy", "covered", "diagonal POV values decompose into cardinal button routes"),
            ("Writer payload", "covered", "fake writer payload matches output intent"),
        ],
    )

    report = _render_report(
        generated_at=generated_at,
        artifact_dir=artifact_dir,
        counts=counts,
        coverage=coverage,
        inventory=inventory,
        live=live,
        real_vjoy=real_vjoy,
        failures=failures,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    return {
        "status": coverage["overall_status"],
        "report": str(REPORT_PATH),
        "artifact_dir": str(artifact_dir),
        "failures": len(failures),
        "generated_case_counts": counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic HelmForge runtime tuning matrix proof.")
    parser.add_argument("--real-vjoy-writes", action="store_true", help="Attempt bounded simulated real-vJoy write calls if vJoy is available.")
    args = parser.parse_args()
    summary = run_probe(real_vjoy_writes=args.real_vjoy_writes)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
