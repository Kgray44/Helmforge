from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from shared_core.models.axes import all_axis_definitions
from shared_core.models.combat import AxisCombatProfile
from shared_core.models.filtering import AxisFiltering
from shared_core.models.modes import ModeConfig
from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.models.tuning import AxisTuning
from shared_core.models.workspace import WorkspaceConfig


class HelmEvidenceSource(str, Enum):
    WORKSPACE_VALUES = "Workspace values"
    MODE_SETTINGS = "Mode settings"
    CONDITIONAL_RULES = "Conditional rules"
    RESPONSE_STACK_SNAPSHOT = "Response stack snapshot"
    BRIDGE_TELEMETRY = "Bridge telemetry"
    RUNTIME_DIAGNOSTICS = "Runtime diagnostics"
    DISCOVERY_ONLY_STATUS = "Discovery-only status"
    SIMULATED_DATA = "Simulated data"
    UNAVAILABLE = "Unavailable"


@dataclass(frozen=True)
class HelmAxisContext:
    axis: str
    tuning: AxisTuning
    filtering: AxisFiltering
    combat: AxisCombatProfile
    evidence_source: str = HelmEvidenceSource.WORKSPACE_VALUES.value


@dataclass(frozen=True)
class HelmModeContext:
    precision_hold_buttons: tuple[int, ...]
    combat_trigger_buttons: tuple[int, ...]
    combat_zoom_aim_buttons: tuple[int, ...]
    combat_extra_buttons: tuple[int, ...]
    stack_mode: str
    evidence_source: str = HelmEvidenceSource.MODE_SETTINGS.value


@dataclass(frozen=True)
class HelmRuleContext:
    total_count: int
    enabled_count: int
    disabled_count: int
    target_axes: tuple[str, ...]
    selected_axis_rules: tuple[str, ...]
    disabled_rule_summaries: tuple[str, ...]
    evidence_source: str = HelmEvidenceSource.CONDITIONAL_RULES.value


@dataclass(frozen=True)
class HelmStackContext:
    available: bool
    selected_axis: str
    raw_input: float | None = None
    final_output: float | None = None
    largest_stage_name: str = ""
    largest_stage_delta: float = 0.0
    active_stages: tuple[str, ...] = ()
    rule_injection_stages: tuple[str, ...] = ()
    stage_count: int = 0
    evidence_source: str = HelmEvidenceSource.UNAVAILABLE.value


@dataclass(frozen=True)
class HelmRuntimeContext:
    runtime_truth: str
    lifecycle_state: str
    output_verified: bool
    full_live_runtime_ready: bool
    device_discovery_status: str
    telemetry_status: str
    process_presence_hint: str
    evidence_source: str = HelmEvidenceSource.RUNTIME_DIAGNOSTICS.value


@dataclass(frozen=True)
class HelmContext:
    selected_axis: str
    axis_contexts: Mapping[str, HelmAxisContext]
    mode: HelmModeContext
    rules: HelmRuleContext
    stack: HelmStackContext
    runtime: HelmRuntimeContext
    evidence_labels: tuple[str, ...]


def build_helm_context(
    workspace: WorkspaceConfig,
    *,
    runtime_status: RuntimePreflightStatus | None = None,
    runtime_truth: str | None = None,
    output_verified: bool | None = None,
    selected_axis: str | None = None,
    stack_snapshot: object | None = None,
    runtime_diagnostics: object | None = None,
) -> HelmContext:
    axis_name = selected_axis or "workspace-wide"
    axis_contexts = _axis_contexts(workspace)
    mode = _mode_context(workspace.modes)
    rules = _rule_context(workspace, selected_axis=axis_name)
    stack = _stack_context(stack_snapshot, selected_axis=axis_name)
    runtime = _runtime_context(
        runtime_status=runtime_status,
        runtime_truth=runtime_truth,
        output_verified=output_verified,
        runtime_diagnostics=runtime_diagnostics,
    )
    labels = [
        HelmEvidenceSource.WORKSPACE_VALUES.value,
        HelmEvidenceSource.MODE_SETTINGS.value,
        HelmEvidenceSource.CONDITIONAL_RULES.value,
    ]
    if stack.available:
        labels.append(HelmEvidenceSource.RESPONSE_STACK_SNAPSHOT.value)
    labels.append(_runtime_evidence_label(runtime))
    return HelmContext(
        selected_axis=axis_name,
        axis_contexts=axis_contexts,
        mode=mode,
        rules=rules,
        stack=stack,
        runtime=runtime,
        evidence_labels=tuple(dict.fromkeys(labels)),
    )


def _axis_contexts(workspace: WorkspaceConfig) -> dict[str, HelmAxisContext]:
    contexts: dict[str, HelmAxisContext] = {}
    for axis in all_axis_definitions():
        axis_id = axis.axis_id.value
        contexts[axis.display_name] = HelmAxisContext(
            axis=axis.display_name,
            tuning=workspace.tuning.axes[axis_id],
            filtering=workspace.filtering.axes[axis_id],
            combat=workspace.combat.axes[axis_id],
        )
    return contexts


def _mode_context(mode_config: ModeConfig) -> HelmModeContext:
    return HelmModeContext(
        precision_hold_buttons=tuple(mode_config.precision_hold_buttons),
        combat_trigger_buttons=tuple(mode_config.combat_trigger_buttons),
        combat_zoom_aim_buttons=tuple(mode_config.combat_zoom_aim_buttons),
        combat_extra_buttons=tuple(mode_config.combat_extra_buttons),
        stack_mode=mode_config.precision_combat_stack_mode.value,
    )


def _rule_context(workspace: WorkspaceConfig, *, selected_axis: str) -> HelmRuleContext:
    rules = workspace.rules.rules
    target_axes = tuple(dict.fromkeys(rule.target_axis for rule in rules))
    selected = tuple(
        rule.title
        for rule in rules
        if selected_axis != "workspace-wide"
        and (rule.target_axis.casefold() == selected_axis.casefold() or rule.reference_axis.casefold() == selected_axis.casefold())
    )
    disabled_summaries = tuple(
        f"Disabled {rule.target_axis} rule targets {rule.parameter} at {rule.injection_stage}."
        for rule in rules
        if not rule.enabled
    )
    enabled_count = sum(1 for rule in rules if rule.enabled)
    return HelmRuleContext(
        total_count=len(rules),
        enabled_count=enabled_count,
        disabled_count=len(rules) - enabled_count,
        target_axes=target_axes,
        selected_axis_rules=selected,
        disabled_rule_summaries=disabled_summaries,
    )


def _stack_context(stack_snapshot: object | None, *, selected_axis: str) -> HelmStackContext:
    if stack_snapshot is None or selected_axis == "workspace-wide":
        return HelmStackContext(
            available=False,
            selected_axis=selected_axis,
            evidence_source=HelmEvidenceSource.UNAVAILABLE.value,
        )
    try:
        axis_results = getattr(stack_snapshot, "axis_results")
        axis_result = axis_results[selected_axis]
        stages = tuple(axis_result.stages)
        raw_values = getattr(stack_snapshot, "raw_axis_values", {})
        final_values = getattr(stack_snapshot, "final_output_values", {})
    except (AttributeError, KeyError, TypeError):
        return HelmStackContext(
            available=False,
            selected_axis=selected_axis,
            evidence_source=HelmEvidenceSource.UNAVAILABLE.value,
        )

    largest = max(stages, key=lambda stage: abs(float(stage.delta)), default=None)
    rule_stages = tuple(stage.stage_name for stage in stages if getattr(stage, "injected_rules", ()))
    return HelmStackContext(
        available=True,
        selected_axis=selected_axis,
        raw_input=float(_mapping_get(raw_values, selected_axis, 0.0)),
        final_output=float(_mapping_get(final_values, selected_axis, getattr(axis_result, "final_output", 0.0))),
        largest_stage_name="" if largest is None else str(largest.stage_name),
        largest_stage_delta=0.0 if largest is None else float(largest.delta),
        active_stages=tuple(str(stage.stage_name) for stage in stages if bool(stage.active)),
        rule_injection_stages=rule_stages,
        stage_count=len(stages),
        evidence_source=HelmEvidenceSource.RESPONSE_STACK_SNAPSHOT.value,
    )


def _runtime_context(
    *,
    runtime_status: RuntimePreflightStatus | None,
    runtime_truth: str | None,
    output_verified: bool | None,
    runtime_diagnostics: object | None,
) -> HelmRuntimeContext:
    diagnostics_truth = _attr(runtime_diagnostics, "runtime_truth")
    diagnostics_output = _attr(runtime_diagnostics, "output_verified")
    truth = str(diagnostics_truth or runtime_truth or _enum_value(_attr(runtime_status, "truth")) or "blocked_missing_device")
    verified = bool(diagnostics_output if diagnostics_output is not None else output_verified)
    if runtime_status is not None and output_verified is None and diagnostics_output is None:
        verified = bool(runtime_status.live_output_writes_verified)
    lifecycle = str(_attr(runtime_diagnostics, "lifecycle_state") or "Simulated")
    device_status = str(_attr(runtime_diagnostics, "device_discovery_status") or "no_supported_device")
    telemetry_status = str(_attr(runtime_diagnostics, "telemetry_label") or "Unavailable")
    process_hint = str(_attr(runtime_diagnostics, "process_hint_label") or "Unavailable")
    return HelmRuntimeContext(
        runtime_truth=truth,
        lifecycle_state=lifecycle,
        output_verified=verified,
        full_live_runtime_ready=truth == "live_verified" and verified,
        device_discovery_status=device_status,
        telemetry_status=telemetry_status,
        process_presence_hint=process_hint,
    )


def _runtime_evidence_label(runtime: HelmRuntimeContext) -> str:
    if runtime.telemetry_status not in {"Unavailable", "Missing", ""}:
        return HelmEvidenceSource.BRIDGE_TELEMETRY.value
    return HelmEvidenceSource.RUNTIME_DIAGNOSTICS.value


def _mapping_get(mapping: object, key: str, fallback: float) -> float:
    if isinstance(mapping, Mapping):
        return float(mapping.get(key, fallback))
    return fallback


def _attr(value: object, name: str) -> object | None:
    if value is None:
        return None
    return getattr(value, name, None)


def _enum_value(value: object) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)
