from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from shared_core.models.axes import AXIS_DISPLAY_NAMES, axis_by_name
from shared_core.models.combat import AxisCombatProfile, CombatProfileConfig
from shared_core.models.filtering import AxisFiltering, FilteringConfig
from shared_core.models.rules import ConditionalRule
from shared_core.models.tuning import AxisTuning, TuningConfig
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.telemetry import BridgeTelemetrySnapshot
from v3_app.services.app_state import AppState
from v3_app.services.parameter_metadata import PARAMETER_HELP, ParameterValueType, validate_numeric_text


TUNING_ROUTE_KEYS = (
    "tuning.base_tuning",
    "tuning.filtering",
    "tuning.combat_profile",
    "tuning.conditional_rules",
)


@dataclass(frozen=True)
class TuningParameterModel:
    parameter_id: str
    field_name: str
    label: str
    value: Any
    value_text: str
    control_kind: str
    options: tuple[str, ...] = ()
    minimum: float | int | None = None
    maximum: float | int | None = None
    units: str = ""
    help_text: str = ""
    metadata_id: str = ""
    changed: bool = False
    read_only_reason: str = ""


@dataclass(frozen=True)
class TuningPreviewModel:
    selected_axis: str
    title: str
    summary: str
    raw_value: float
    output_intent_value: float
    source_truth_label: str
    state_role: str


@dataclass(frozen=True)
class TuningGraphLineModel:
    label: str
    points: tuple[tuple[float, float], ...]
    role: str


@dataclass(frozen=True)
class TuningGraphMarkerModel:
    label: str
    point: tuple[float, float]
    role: str


@dataclass(frozen=True)
class TuningGraphModel:
    graph_kind: str
    title: str
    selected_axis: str
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    lines: tuple[TuningGraphLineModel, ...]
    markers: tuple[TuningGraphMarkerModel, ...] = ()


@dataclass(frozen=True)
class TuningRuleFlow:
    rule_id: str
    title: str
    enabled: bool
    condition_label: str
    action_label: str
    status_role: str
    warning: str = ""


@dataclass(frozen=True)
class TuningCommandModel:
    route_key: str
    page_title: str
    page_question: str
    selected_axis: str
    selected_axis_key: str
    axis_options: tuple[str, ...]
    parameters: tuple[TuningParameterModel, ...]
    preview: TuningPreviewModel
    preview_graph: TuningGraphModel | None
    preview_truth_label: str
    guidance: dict[str, str]
    advanced_details: tuple[tuple[str, str], ...]
    rule_flows: tuple[TuningRuleFlow, ...] = ()
    metrics: tuple[tuple[str, str, str, str], ...] = ()
    warnings: tuple[str, ...] = ()
    draft_state_label: str = "Draft unchanged"
    truth_source_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class TuningEditResult:
    valid: bool
    workspace: WorkspaceConfig
    route_key: str
    axis_name: str
    parameter_id: str
    staged_value: str
    status_label: str
    message: str
    validation_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ParameterSpec:
    parameter_id: str
    field_name: str


_BASE_SPECS = (
    _ParameterSpec("base.curve_mode", "curve_mode"),
    _ParameterSpec("base.curve_strength", "curve_strength"),
    _ParameterSpec("base.deadzone", "deadzone"),
    _ParameterSpec("base.anti_deadzone", "anti_deadzone"),
    _ParameterSpec("base.hysteresis", "hysteresis"),
    _ParameterSpec("base.output_scale", "output_scale"),
    _ParameterSpec("base.max_output", "max_output"),
)
_FILTERING_SPECS = (
    _ParameterSpec("filtering.center_alpha", "center_alpha"),
    _ParameterSpec("filtering.edge_alpha", "edge_alpha"),
    _ParameterSpec("filtering.same_slew_limit", "same_slew_limit"),
    _ParameterSpec("filtering.reverse_slew_limit", "reverse_slew_limit"),
)
_COMBAT_SPECS = (
    _ParameterSpec("combat.combat_curve", "combat_curve"),
    _ParameterSpec("combat.combat_scale", "combat_scale"),
    _ParameterSpec("combat.combat_center_alpha", "combat_center_alpha"),
    _ParameterSpec("combat.combat_edge_alpha", "combat_edge_alpha"),
    _ParameterSpec("combat.combat_same_slew", "combat_same_slew"),
    _ParameterSpec("combat.combat_reverse_slew", "combat_reverse_slew"),
)


def build_tuning_command_model(
    *,
    route_key: str,
    workspace: WorkspaceConfig | None = None,
    selected_axis: str = "Roll",
    state: AppState | None = None,
    base_workspace: WorkspaceConfig | None = None,
    telemetry: BridgeTelemetrySnapshot | None = None,
) -> TuningCommandModel:
    workspace = workspace or create_default_workspace()
    base_workspace = base_workspace or workspace
    selected_axis = _validated_axis_name(selected_axis)
    axis_key = _axis_key(selected_axis)
    route_key = _validate_route(route_key)
    parameters = _parameters_for_route(route_key, workspace, base_workspace, axis_key)
    sample = _passive_axis_sample(telemetry, selected_axis)
    preview = _preview_for_route(route_key, workspace, selected_axis, state, sample)
    preview_graph = _graph_for_route(route_key, workspace, selected_axis, sample)
    rule_flows = _rule_flows(workspace) if route_key == "tuning.conditional_rules" else ()
    metrics = _metrics_for_route(route_key, workspace, parameters, rule_flows)
    warnings = _warnings_for_route(route_key, rule_flows)
    changed_count = sum(1 for parameter in parameters if parameter.changed)
    draft_label = (
        f"{changed_count} draft tuning change{'s' if changed_count != 1 else ''} staged"
        if changed_count
        else "Draft unchanged"
    )
    return TuningCommandModel(
        route_key=route_key,
        page_title=_page_title(route_key),
        page_question=_page_question(route_key),
        selected_axis=selected_axis,
        selected_axis_key=axis_key,
        axis_options=tuple(AXIS_DISPLAY_NAMES),
        parameters=parameters,
        preview=preview,
        preview_graph=preview_graph,
        preview_truth_label=preview.source_truth_label,
        guidance=_guidance_for_route(route_key, selected_axis),
        advanced_details=_advanced_details(route_key, workspace, selected_axis, parameters),
        rule_flows=rule_flows,
        metrics=metrics,
        warnings=warnings,
        draft_state_label=draft_label,
        truth_source_notes=(
            "Tuning pages read workspace tuning/filtering/combat/rule state only.",
            "Edits are workspace/draft tuning changes; output proof unchanged.",
            "Response preview is preview-only and does not prove live output.",
        ),
    )


def stage_tuning_parameter_edit(
    workspace: WorkspaceConfig,
    route_key: str,
    axis_name: str,
    parameter_id: str,
    value: str,
) -> TuningEditResult:
    route_key = _validate_route(route_key)
    axis_name = _validated_axis_name(axis_name)
    axis_key = _axis_key(axis_name)
    spec = _spec_for_parameter(route_key, parameter_id)
    if spec is None:
        return _invalid(
            workspace,
            route_key,
            axis_name,
            parameter_id,
            value,
            "Unsupported tuning parameter; edit was not staged.",
        )
    parsed = _parse_parameter_value(parameter_id, value)
    if not parsed.valid:
        return TuningEditResult(
            valid=False,
            workspace=workspace,
            route_key=route_key,
            axis_name=axis_name,
            parameter_id=parameter_id,
            staged_value=value,
            status_label="Tuning edit rejected",
            message=f"{parsed.message} Edit was not staged.",
            validation_errors=(parsed.message,),
        )
    updated = _workspace_with_tuning_edit(workspace, route_key, axis_key, spec.field_name, parsed.value)
    if updated is None:
        return _invalid(
            workspace,
            route_key,
            axis_name,
            parameter_id,
            value,
            "Unsupported tuning route shape; edit was not staged.",
        )
    return TuningEditResult(
        valid=True,
        workspace=_mark_workspace_dirty(updated),
        route_key=route_key,
        axis_name=axis_name,
        parameter_id=parameter_id,
        staged_value=str(parsed.value),
        status_label="Draft tuning change staged",
        message=(
            f"Draft tuning change staged for {axis_name}. "
            "Save workspace to persist. Output proof unchanged."
        ),
    )


@dataclass(frozen=True)
class _ParsedValue:
    valid: bool
    value: Any = None
    message: str = ""


def _parameters_for_route(
    route_key: str,
    workspace: WorkspaceConfig,
    base_workspace: WorkspaceConfig,
    axis_key: str,
) -> tuple[TuningParameterModel, ...]:
    specs = _specs_for_route(route_key)
    if not specs:
        return ()
    source = _axis_config_for_route(workspace, route_key, axis_key)
    base = _axis_config_for_route(base_workspace, route_key, axis_key)
    return tuple(_parameter_model(spec, source, base) for spec in specs)


def _parameter_model(spec: _ParameterSpec, source: object, base: object) -> TuningParameterModel:
    metadata = PARAMETER_HELP.get(spec.parameter_id)
    value = getattr(source, spec.field_name)
    base_value = getattr(base, spec.field_name, value)
    label = metadata.display_name if metadata else _label_from_id(spec.parameter_id)
    options = tuple(metadata.dropdown_options) if metadata else ()
    control_kind = "dropdown" if metadata and metadata.value_type is ParameterValueType.DROPDOWN else "numeric"
    if metadata and metadata.value_type not in {ParameterValueType.DROPDOWN, ParameterValueType.NUMBER, ParameterValueType.INTEGER}:
        control_kind = "readonly"
    return TuningParameterModel(
        parameter_id=spec.parameter_id,
        field_name=spec.field_name,
        label=label,
        value=value,
        value_text=_format_value(value),
        control_kind=control_kind,
        options=options,
        minimum=metadata.min_value if metadata else None,
        maximum=metadata.max_value if metadata else None,
        units=metadata.units or "" if metadata else "",
        help_text=_metadata_help(metadata),
        metadata_id=metadata.parameter_id if metadata else spec.parameter_id,
        changed=value != base_value,
        read_only_reason="" if control_kind != "readonly" else "This parameter type is read-only in LCD-6.",
    )


def _parse_parameter_value(parameter_id: str, value: str) -> _ParsedValue:
    metadata = PARAMETER_HELP.get(parameter_id)
    if metadata is None:
        return _ParsedValue(False, message=f"{parameter_id!r} has no parameter metadata.")
    text = value.strip()
    if metadata.value_type is ParameterValueType.DROPDOWN:
        if text not in metadata.dropdown_options:
            return _ParsedValue(False, message=f"{metadata.display_name} {text!r} is not supported.")
        return _ParsedValue(True, value=text)
    if metadata.is_numeric:
        validation = validate_numeric_text(metadata, text)
        if not validation.acceptable:
            return _ParsedValue(False, message=_numeric_validation_message(metadata.display_name, validation.error))
        return _ParsedValue(True, value=validation.value)
    return _ParsedValue(False, message=f"{metadata.display_name} is read-only in LCD-6.")


def _workspace_with_tuning_edit(
    workspace: WorkspaceConfig,
    route_key: str,
    axis_key: str,
    field_name: str,
    value: Any,
) -> WorkspaceConfig | None:
    if route_key == "tuning.base_tuning":
        axes = dict(workspace.tuning.axes)
        current = axes.get(axis_key)
        if current is None:
            return None
        axes[axis_key] = replace(current, **{field_name: value})
        return replace(workspace, tuning=replace(workspace.tuning, axes=axes))
    if route_key == "tuning.filtering":
        axes = dict(workspace.filtering.axes)
        current = axes.get(axis_key)
        if current is None:
            return None
        axes[axis_key] = replace(current, **{field_name: value})
        return replace(workspace, filtering=replace(workspace.filtering, axes=axes))
    if route_key == "tuning.combat_profile":
        axes = dict(workspace.combat.axes)
        current = axes.get(axis_key)
        if current is None:
            return None
        axes[axis_key] = replace(current, **{field_name: value})
        return replace(workspace, combat=replace(workspace.combat, axes=axes))
    return None


def _axis_config_for_route(workspace: WorkspaceConfig, route_key: str, axis_key: str) -> AxisTuning | AxisFiltering | AxisCombatProfile:
    if route_key == "tuning.base_tuning":
        return workspace.tuning.axes[axis_key]
    if route_key == "tuning.filtering":
        return workspace.filtering.axes[axis_key]
    if route_key == "tuning.combat_profile":
        return workspace.combat.axes[axis_key]
    raise KeyError(route_key)


def _preview_for_route(
    route_key: str,
    workspace: WorkspaceConfig,
    selected_axis: str,
    state: AppState | None,
    sample: tuple[float | None, float | None],
) -> TuningPreviewModel:
    axis_key = _axis_key(selected_axis)
    passive_raw, passive_final = sample
    raw_value = passive_raw if passive_raw is not None else 0.35
    if route_key == "tuning.base_tuning":
        config = workspace.tuning.axes[axis_key]
        adjusted = passive_final if passive_final is not None else _signed_base_preview(raw_value, config)
        title = "Response preview"
        summary = f"Axis: {selected_axis}. Curve {config.curve_mode.upper()} at {config.curve_strength:.2f}; deadzone {config.deadzone:.2f}."
    elif route_key == "tuning.filtering":
        config = workspace.filtering.axes[axis_key]
        adjusted = passive_final if passive_final is not None else max(-1.0, min(1.0, raw_value * config.center_alpha + raw_value * (1.0 - config.center_alpha) * 0.72))
        title = "Filtering response preview"
        summary = f"Axis: {selected_axis}. Center alpha {config.center_alpha:.2f}; reverse slew {config.reverse_slew_limit:.2f}."
    elif route_key == "tuning.combat_profile":
        config = workspace.combat.axes[axis_key]
        tuning = workspace.tuning.axes[axis_key]
        adjusted = passive_final if passive_final is not None else _combat_preview(raw_value, tuning, config)
        title = "Combat response preview"
        summary = f"Axis: {selected_axis}. Combat curve {config.combat_curve:.2f}; scale {config.combat_scale:.2f}."
    else:
        raw_value = 0.0
        adjusted = 0.0
        title = "Rule system status"
        summary = "Conditional rules are visualized from workspace state; editing is deferred in LCD-6."
    state_role = _state_role(state)
    source_truth = _source_truth_label(state, state_role, live=passive_raw is not None)
    return TuningPreviewModel(
        selected_axis=selected_axis,
        title=title,
        summary=summary,
        raw_value=raw_value,
        output_intent_value=adjusted,
        source_truth_label=source_truth,
        state_role=state_role,
    )


def _graph_for_route(
    route_key: str,
    workspace: WorkspaceConfig,
    selected_axis: str,
    sample: tuple[float | None, float | None] = (None, None),
) -> TuningGraphModel | None:
    axis_key = _axis_key(selected_axis)
    samples = tuple(round(-1.0 + index * 0.05, 4) for index in range(41))
    reference = TuningGraphLineModel("Default", tuple((x, x) for x in samples), "simulation")
    passive_raw, passive_final = sample
    if route_key == "tuning.base_tuning":
        tuning = workspace.tuning.axes[axis_key]
        current = TuningGraphLineModel(
            "Current tuning",
            tuple((x, _signed_base_preview(x, tuning)) for x in samples),
            "info",
        )
        return TuningGraphModel(
            graph_kind="response_curve",
            title=f"{selected_axis} base response curve",
            selected_axis=selected_axis,
            x_range=(-1.0, 1.0),
            y_range=(-1.0, 1.0),
            lines=(reference, current),
            markers=_base_markers(tuning, passive_raw, passive_final),
        )
    if route_key == "tuning.filtering":
        filtering = workspace.filtering.axes[axis_key]
        input_step = TuningGraphLineModel(
            "Input step",
            _filter_input_step_points(),
            "simulation",
        )
        filtered = TuningGraphLineModel(
            "Filtered output",
            _filter_step_points(filtering),
            "info",
        )
        return TuningGraphModel(
            graph_kind="step_response",
            title=f"{selected_axis} filtering step response",
            selected_axis=selected_axis,
            x_range=(0.0, 72.0),
            y_range=(-1.0, 1.0),
            lines=(input_step, filtered),
        )
    if route_key == "tuning.combat_profile":
        tuning = workspace.tuning.axes[axis_key]
        combat = workspace.combat.axes[axis_key]
        base = TuningGraphLineModel(
            "Base tuning",
            tuple((x, _signed_base_preview(x, tuning)) for x in samples),
            "info",
        )
        combat_line = TuningGraphLineModel(
            "Combat profile",
            tuple((x, _combat_preview(x, tuning, combat)) for x in samples),
            "warning",
        )
        return TuningGraphModel(
            graph_kind="combat_response",
            title=f"{selected_axis} combat response overlay",
            selected_axis=selected_axis,
            x_range=(-1.0, 1.0),
            y_range=(-1.0, 1.0),
            lines=(reference, base, combat_line),
            markers=_combat_markers(tuning, combat, passive_raw, passive_final),
        )
    return None


def _base_preview(raw_value: float, config: AxisTuning) -> float:
    magnitude = max(0.0, abs(raw_value) - config.deadzone)
    span = max(0.001, 1.0 - config.deadzone)
    normalized = magnitude / span
    curved = normalized * (1.0 - config.curve_strength) + (normalized**3) * config.curve_strength
    if curved > 0.0 and config.anti_deadzone:
        curved = config.anti_deadzone + curved * (1.0 - config.anti_deadzone)
    scaled = min(config.max_output, curved * config.output_scale)
    return max(0.0, min(1.0, scaled))


def _signed_base_preview(raw_value: float, config: AxisTuning) -> float:
    sign = -1.0 if raw_value < 0.0 else 1.0
    return sign * _base_preview(abs(raw_value), config)


def _combat_preview(raw_value: float, tuning: AxisTuning, combat: AxisCombatProfile) -> float:
    base = _signed_base_preview(raw_value, tuning)
    curve = abs(base) ** max(0.25, float(combat.combat_curve))
    scaled = max(0.0, min(1.0, curve * float(combat.combat_scale)))
    return (-1.0 if base < 0.0 else 1.0) * scaled


def _base_markers(
    tuning: AxisTuning,
    passive_raw: float | None,
    passive_final: float | None,
) -> tuple[TuningGraphMarkerModel, ...]:
    raw = _sample_value(passive_raw)
    output = _signed_base_preview(raw, tuning)
    return (
        TuningGraphMarkerModel("Current input", (raw, raw), "simulation"),
        TuningGraphMarkerModel("Output intent", (raw, output), "info"),
    )


def _combat_markers(
    tuning: AxisTuning,
    combat: AxisCombatProfile,
    passive_raw: float | None,
    passive_final: float | None,
) -> tuple[TuningGraphMarkerModel, ...]:
    raw = _sample_value(passive_raw)
    base = _signed_base_preview(raw, tuning)
    combat_value = _combat_preview(raw, tuning, combat)
    return (
        TuningGraphMarkerModel("Current input", (raw, raw), "simulation"),
        TuningGraphMarkerModel("Base tuning current", (raw, base), "info"),
        TuningGraphMarkerModel("Combat profile current", (raw, combat_value), "warning"),
    )


def _filter_step_target(step: int) -> float:
    if step < 8:
        return 0.0
    if step < 28:
        return 1.0
    if step < 48:
        return -1.0
    if step < 60:
        return 0.35
    return 0.0


def _filter_step_target_at(sample_step: float) -> float:
    return _filter_step_target(int(sample_step))


def _filter_input_step_points() -> tuple[tuple[float, float], ...]:
    return (
        (0.0, 0.0),
        (8.0, 0.0),
        (8.0, 1.0),
        (28.0, 1.0),
        (28.0, -1.0),
        (48.0, -1.0),
        (48.0, 0.35),
        (60.0, 0.35),
        (60.0, 0.0),
        (72.0, 0.0),
    )


def _filter_step_points(config: AxisFiltering) -> tuple[tuple[float, float], ...]:
    value = 0.0
    points: list[tuple[float, float]] = []
    samples_per_step = 10
    total_steps = 72
    for index in range(total_steps * samples_per_step + 1):
        step = index / samples_per_step
        target = _filter_step_target_at(step)
        alpha = config.center_alpha if abs(value) < 0.5 else config.edge_alpha
        next_value = value + (target - value) * max(0.0, min(1.0, alpha)) / samples_per_step
        limit = config.same_slew_limit if target * value >= 0 or abs(value) < 0.001 else config.reverse_slew_limit
        slew = max(0.0, limit) / samples_per_step
        if slew:
            delta = max(-slew, min(slew, next_value - value))
            value += delta
        else:
            value = next_value
        points.append((float(step), max(-1.0, min(1.0, value))))
    return tuple(points)


def _passive_axis_sample(
    telemetry: BridgeTelemetrySnapshot | None,
    selected_axis: str,
) -> tuple[float | None, float | None]:
    if telemetry is None:
        return (None, None)
    raw_values = getattr(getattr(telemetry, "raw_axes", None), "values", None)
    final_values = getattr(getattr(telemetry, "final_axes", None), "values", None)
    raw = raw_values.get(selected_axis) if isinstance(raw_values, Mapping) else None
    final = final_values.get(selected_axis) if isinstance(final_values, Mapping) else None
    return (raw, final)


def _sample_value(value: float | None) -> float:
    return max(-1.0, min(1.0, float(value if value is not None else 0.0)))


def _rule_flows(workspace: WorkspaceConfig) -> tuple[TuningRuleFlow, ...]:
    if not workspace.rules.rules:
        return (
            TuningRuleFlow(
                rule_id="rules:none",
                title="No conditional rules configured",
                enabled=False,
                condition_label="No workspace rule",
                action_label="No response change",
                status_role="unavailable",
                warning="Rule creation is deferred to a later phase.",
            ),
        )
    return tuple(_rule_flow(index, rule) for index, rule in enumerate(workspace.rules.rules, start=1))


def _rule_flow(index: int, rule: ConditionalRule) -> TuningRuleFlow:
    condition = f"{rule.reference_axis} {rule.stage} {rule.measure} {rule.comparator} {rule.threshold:g}"
    if rule.threshold_high is not None:
        condition += f" to {rule.threshold_high:g}"
    action = f"{rule.target_axis} {rule.parameter} {rule.operation} {rule.value:g} at {rule.injection_stage}"
    return TuningRuleFlow(
        rule_id=f"rules:{index}",
        title=rule.title,
        enabled=rule.enabled,
        condition_label=condition,
        action_label=action,
        status_role="ready" if rule.enabled else "unavailable",
        warning="" if rule.enabled else "Disabled rule; visualization only.",
    )


def _metrics_for_route(
    route_key: str,
    workspace: WorkspaceConfig,
    parameters: tuple[TuningParameterModel, ...],
    rule_flows: tuple[TuningRuleFlow, ...],
) -> tuple[tuple[str, str, str, str], ...]:
    if route_key == "tuning.conditional_rules":
        enabled = sum(1 for rule in workspace.rules.rules if rule.enabled)
        disabled = len(workspace.rules.rules) - enabled
        warnings = sum(1 for flow in rule_flows if flow.warning)
        return (
            ("Enabled rules", str(enabled), "Workspace rule state", "ready" if enabled else "unavailable"),
            ("Disabled rules", str(disabled), "Read-only rule visualization", "warning" if disabled else "info"),
            ("Warnings", str(warnings), "Conflicts or disabled notes", "warning" if warnings else "info"),
        )
    changed = sum(1 for parameter in parameters if parameter.changed)
    return (
        ("Editable fields", str(len(parameters)), "Workspace parameters", "info"),
        ("Draft changes", str(changed), "Staged tuning edits", "unsaved" if changed else "info"),
        ("Output proof", "unchanged", "Preview is not output proof", "simulation"),
    )


def _warnings_for_route(route_key: str, rule_flows: tuple[TuningRuleFlow, ...]) -> tuple[str, ...]:
    if route_key != "tuning.conditional_rules":
        return ("Preview only; output proof unchanged.",)
    warnings = tuple(flow.warning for flow in rule_flows if flow.warning)
    return warnings or ("No rule warnings in the workspace snapshot.",)


def _guidance_for_route(route_key: str, selected_axis: str) -> dict[str, str]:
    if route_key == "tuning.base_tuning":
        return {
            "current_feel": "Base response sets the first feel layer before filtering, modes, or rules.",
            "affects": "Deadzone, curve strength, scale, and output cap for the selected axis.",
            "suggested_range": "Keep deadzone low and curve strength moderate unless a sensor or sim needs more help.",
            "caution": "Preview output is Output Intent only; it does not verify vJoy writes.",
            "selected_axis_note": f"{selected_axis} is selected for workspace tuning edits.",
        }
    if route_key == "tuning.filtering":
        return {
            "current_feel": "Filtering changes how quickly the axis follows input near center and during reversals.",
            "affects": "Center alpha, edge alpha, and slew limits for the selected axis.",
            "suggested_range": "Lower center alpha for steadier fine motion; keep edge alpha higher for authority.",
            "caution": "No new filtering runtime behavior is started from this page.",
            "selected_axis_note": f"{selected_axis} filtering is staged as a workspace draft.",
        }
    if route_key == "tuning.combat_profile":
        return {
            "current_feel": "Combat profile values describe a calmer response layer for aiming or combat modes.",
            "affects": "Combat curve, authority scale, smoothing, and slew limits.",
            "suggested_range": "Use moderate curve and scale reductions; extreme values can feel delayed.",
            "caution": "Combat preview is not proof that a live combat mode is active.",
            "selected_axis_note": f"{selected_axis} combat profile values are shown from workspace state.",
        }
    return {
        "current_feel": "Rules can conditionally change response stack parameters when their condition is met.",
        "affects": "Target axis, parameter, operation, injection stage, and condition threshold.",
        "suggested_range": "Keep rules sparse and named so conflicts are easy to audit.",
        "caution": "LCD-6 shows read-only rule visualization unless safe rule editing is added later.",
        "selected_axis_note": f"{selected_axis} remains the selected Tuning axis; rule rows may target other axes.",
    }


def _advanced_details(
    route_key: str,
    workspace: WorkspaceConfig,
    selected_axis: str,
    parameters: tuple[TuningParameterModel, ...],
) -> tuple[tuple[str, str], ...]:
    details = [
        ("Route key", route_key),
        ("Selected axis", selected_axis),
        ("Selected axis key", _axis_key(selected_axis)),
        ("Workspace saved", "yes" if workspace.state.saved else "no"),
        ("Workspace dirty", "yes" if workspace.state.dirty else "no"),
        ("Preview source", "workspace values / preview only"),
        ("Output proof", "unchanged by tuning edits"),
    ]
    details.extend((parameter.parameter_id, parameter.value_text) for parameter in parameters)
    if route_key == "tuning.conditional_rules":
        details.append(("Rule count", str(len(workspace.rules.rules))))
    return tuple(details)


def _specs_for_route(route_key: str) -> tuple[_ParameterSpec, ...]:
    if route_key == "tuning.base_tuning":
        return _BASE_SPECS
    if route_key == "tuning.filtering":
        return _FILTERING_SPECS
    if route_key == "tuning.combat_profile":
        return _COMBAT_SPECS
    return ()


def _spec_for_parameter(route_key: str, parameter_id: str) -> _ParameterSpec | None:
    for spec in _specs_for_route(route_key):
        if spec.parameter_id == parameter_id:
            return spec
    return None


def _validate_route(route_key: str) -> str:
    if route_key not in TUNING_ROUTE_KEYS:
        raise KeyError(route_key)
    return route_key


def _validated_axis_name(axis_name: str) -> str:
    return axis_by_name(axis_name).display_name


def _axis_key(axis_name: str) -> str:
    return axis_by_name(axis_name).axis_id.value


def _mark_workspace_dirty(workspace: WorkspaceConfig) -> WorkspaceConfig:
    return replace(workspace, state=replace(workspace.state, dirty=True, saved=False))


def _invalid(
    workspace: WorkspaceConfig,
    route_key: str,
    axis_name: str,
    parameter_id: str,
    value: str,
    message: str,
) -> TuningEditResult:
    return TuningEditResult(
        valid=False,
        workspace=workspace,
        route_key=route_key,
        axis_name=axis_name,
        parameter_id=parameter_id,
        staged_value=value,
        status_label="Tuning edit rejected",
        message=message,
        validation_errors=(message,),
    )


def _page_title(route_key: str) -> str:
    return {
        "tuning.base_tuning": "Base Tuning",
        "tuning.filtering": "Filtering",
        "tuning.combat_profile": "Combat Profile",
        "tuning.conditional_rules": "Conditional Rules",
    }[route_key]


def _page_question(route_key: str) -> str:
    return {
        "tuning.base_tuning": "How does this axis respond before filtering/modes/rules?",
        "tuning.filtering": "How much smoothing/slew behavior is applied to this axis?",
        "tuning.combat_profile": "How does this axis behave in combat/aiming mode?",
        "tuning.conditional_rules": "What rules can change the response stack, and when do they trigger?",
    }[route_key]


def _source_truth_label(state: AppState | None, state_role: str, *, live: bool = False) -> str:
    if live:
        return "Passive live telemetry - Bridge telemetry sample; Output proof unchanged"
    if state is None:
        return "Preview only - Current sample unavailable"
    if state.runtime.truth.value == "simulated":
        return "Preview only - Simulation mode; Current sample unavailable"
    if state.runtime.truth.value == "live_verified":
        return "Preview only - passive runtime snapshot is Live Verified; Output proof unchanged"
    if state.runtime.truth.value == "detected_unverified":
        return "Preview only - detected runtime remains output-unverified"
    return f"Preview only - {state.runtime.header_truth_label}; Current sample unavailable"


def _state_role(state: AppState | None) -> str:
    if state is None:
        return "simulation"
    if state.runtime.truth.value == "live_verified" and state.runtime.output_verified:
        return "ready"
    if state.runtime.truth.value in {"simulated", "detected_unverified"}:
        return "simulation"
    if state.runtime.truth.value == "error":
        return "error"
    return "warning"


def _numeric_validation_message(label: str, error: str | None) -> str:
    return {
        "empty": f"{label} is required.",
        "not_numeric": f"{label} must be numeric.",
        "not_integer": f"{label} must be an integer.",
        "below_min": f"{label} is below the supported range.",
        "above_max": f"{label} is above the supported range.",
    }.get(error or "", f"{label} is invalid.")


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _metadata_help(metadata) -> str:
    if metadata is None:
        return "Parameter metadata is not available for this field."
    parts = [metadata.short_description]
    if metadata.value_range is not None:
        parts.append(f"Range: {_format_value(metadata.min_value)} to {_format_value(metadata.max_value)}")
    if metadata.dropdown_options:
        parts.append("Options: " + ", ".join(metadata.dropdown_options))
    if metadata.warning_text:
        parts.append(metadata.warning_text)
    return " ".join(part for part in parts if part)


def _label_from_id(parameter_id: str) -> str:
    return parameter_id.split(".", 1)[-1].replace("_", " ").title()
