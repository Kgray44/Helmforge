from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

from shared_core.math.pipeline import WorkspaceSignalPipeline, WorkspaceSignalPipelineResult
from shared_core.math.stack import ModeState, StageResult
from shared_core.models.runtime import AXIS_NAMES, BUTTON_NAMES, RuntimeTruth
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.telemetry import BridgeTelemetrySnapshot
from v3_app.services.app_state import AppState


ANALYSIS_ROUTE_KEYS = (
    "analysis.effective_response_stack",
    "analysis.live_monitor",
)


@dataclass(frozen=True)
class AnalysisPipelineStageModel:
    stage_id: str
    stage_name: str
    value_text: str
    stage_summary: str
    source_label: str
    state_role: str
    warning_text: str = ""


@dataclass(frozen=True)
class AnalysisAxisMonitorModel:
    axis_name: str
    raw_value: float | None
    final_value: float | None
    raw_text: str
    final_text: str
    state_role: str


@dataclass(frozen=True)
class AnalysisButtonMonitorModel:
    label: str
    active: bool
    state_text: str
    state_role: str


@dataclass(frozen=True)
class AnalysisCommandModel:
    route_key: str
    page_title: str
    page_question: str
    selected_axis: str
    axis_options: tuple[str, ...]
    runtime_truth_label: str
    telemetry_label: str
    telemetry_role: str
    source_label: str
    freshness_label: str
    sample_truth_label: str
    output_proof_label: str
    output_proof_role: str
    pipeline_stages: tuple[AnalysisPipelineStageModel, ...]
    axis_monitors: tuple[AnalysisAxisMonitorModel, ...]
    buttons: tuple[AnalysisButtonMonitorModel, ...]
    hat_label: str
    hat_direction: str
    hat_role: str
    metrics: tuple[tuple[str, str, str, str], ...]
    warnings: tuple[str, ...]
    advanced_details: tuple[tuple[str, str], ...]
    truth_source_notes: tuple[str, ...]
    signature: tuple[object, ...]


def build_analysis_command_model(
    *,
    route_key: str,
    workspace: WorkspaceConfig | None = None,
    state: AppState | None = None,
    telemetry: BridgeTelemetrySnapshot | None = None,
    selected_axis: str = "Roll",
    pipeline: WorkspaceSignalPipeline | None = None,
) -> AnalysisCommandModel:
    route_key = _validate_route(route_key)
    workspace = workspace or create_default_workspace()
    selected_axis = _validated_axis(selected_axis)
    telemetry_state = _telemetry_state(state=state, telemetry=telemetry)
    raw_axes = _axis_values(telemetry, "raw_axes")
    final_axes = _axis_values(telemetry, "final_axes")
    pipeline_result = _pipeline_result(workspace, raw_axes, pipeline=pipeline)
    axis_monitors = _axis_monitors(raw_axes, final_axes, pipeline_result, telemetry_state.role)
    stages = _pipeline_stages(
        selected_axis=selected_axis,
        raw_axes=raw_axes,
        final_axes=final_axes,
        pipeline_result=pipeline_result,
        telemetry_role=telemetry_state.role,
    )
    buttons = _buttons(telemetry, telemetry_state.role)
    hat_direction, hat_label, hat_role = _hat(telemetry, telemetry_state.role)
    output_verified = _output_verified(state=state, telemetry=telemetry)
    output_proof_label = "Output proof verified" if output_verified else "Output proof missing"
    output_proof_role = "verified" if output_verified else "blocked"
    runtime_truth_label = _runtime_truth_label(state=state, telemetry=telemetry, output_verified=output_verified)
    metrics = _metrics(
        pipeline_stages=stages,
        axis_monitors=axis_monitors,
        buttons=buttons,
        telemetry_state=telemetry_state,
        output_proof_label=output_proof_label,
    )
    warnings = _warnings(telemetry=telemetry, telemetry_label=telemetry_state.label)
    advanced_details = _advanced_details(
        route_key=route_key,
        selected_axis=selected_axis,
        telemetry=telemetry,
        telemetry_state=telemetry_state,
        runtime_truth_label=runtime_truth_label,
        output_proof_label=output_proof_label,
        pipeline_stages=stages,
    )
    return AnalysisCommandModel(
        route_key=route_key,
        page_title=_page_title(route_key),
        page_question=_page_question(route_key),
        selected_axis=selected_axis,
        axis_options=tuple(AXIS_NAMES),
        runtime_truth_label=runtime_truth_label,
        telemetry_label=telemetry_state.label,
        telemetry_role=telemetry_state.role,
        source_label=telemetry_state.source_label,
        freshness_label=telemetry_state.freshness_label,
        sample_truth_label=telemetry_state.sample_truth_label,
        output_proof_label=output_proof_label,
        output_proof_role=output_proof_role,
        pipeline_stages=stages,
        axis_monitors=axis_monitors,
        buttons=buttons,
        hat_label=hat_label,
        hat_direction=hat_direction,
        hat_role=hat_role,
        metrics=metrics,
        warnings=warnings,
        advanced_details=advanced_details,
        truth_source_notes=(
            "Analysis pages read existing AppState, workspace, and passive Bridge telemetry snapshots.",
            "Output proof is separate from output intent.",
            "LCD-7 does not poll hardware, write vJoy, start Bridge, or perform output verification.",
        ),
        signature=(
            route_key,
            selected_axis,
            telemetry_state.label,
            runtime_truth_label,
            output_proof_label,
            tuple((axis.axis_name, axis.raw_text, axis.final_text) for axis in axis_monitors),
            tuple((button.label, button.active) for button in buttons),
            hat_label,
        ),
    )


@dataclass(frozen=True)
class _TelemetryState:
    label: str
    role: str
    source_label: str
    freshness_label: str
    sample_truth_label: str


def _validate_route(route_key: str) -> str:
    if route_key not in ANALYSIS_ROUTE_KEYS:
        raise KeyError(route_key)
    return route_key


def _validated_axis(axis_name: str) -> str:
    return axis_name if axis_name in AXIS_NAMES else "Roll"


def _telemetry_state(*, state: AppState | None, telemetry: BridgeTelemetrySnapshot | None) -> _TelemetryState:
    if telemetry is None:
        source = "Simulation mode / passive workspace" if _state_truth(state) is RuntimeTruth.SIMULATED else "Passive runtime snapshot"
        return _TelemetryState(
            label="Telemetry missing",
            role="simulation" if _state_truth(state) is RuntimeTruth.SIMULATED else "unavailable",
            source_label=source,
            freshness_label="No Bridge telemetry frame available.",
            sample_truth_label="Current sample unavailable",
        )
    runtime_frame = dict(telemetry.runtime_frame or {})
    stale = bool(runtime_frame.get("input_stale"))
    proof = str(runtime_frame.get("telemetry_proof") or "").strip().casefold()
    stale = stale or proof == "stale" or _age_seconds(telemetry.timestamp) > 5.0
    if stale:
        return _TelemetryState(
            label="Telemetry stale",
            role="waiting",
            source_label="Bridge telemetry",
            freshness_label=f"Stale value retained; {_age_seconds(telemetry.timestamp):.1f}s old.",
            sample_truth_label="Stale telemetry sample retained",
        )
    if telemetry.runtime_truth is RuntimeTruth.SIMULATED:
        return _TelemetryState(
            label="Simulation mode",
            role="simulation",
            source_label="Bridge telemetry / simulation mode",
            freshness_label=f"Passive snapshot {_age_seconds(telemetry.timestamp):.1f}s old.",
            sample_truth_label="Simulation mode; passive snapshot",
        )
    return _TelemetryState(
        label="Telemetry fresh",
        role="ready",
        source_label="Bridge telemetry",
        freshness_label=f"Passive snapshot {_age_seconds(telemetry.timestamp):.1f}s old.",
        sample_truth_label="Telemetry fresh",
    )


def _state_truth(state: AppState | None) -> RuntimeTruth:
    if state is None:
        return RuntimeTruth.SIMULATED
    return state.runtime.truth


def _age_seconds(timestamp: datetime | None) -> float:
    if timestamp is None:
        return 0.0
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds())


def _axis_values(telemetry: BridgeTelemetrySnapshot | None, field_name: str) -> dict[str, float] | None:
    if telemetry is None:
        return None
    snapshot = getattr(telemetry, field_name, None)
    values = getattr(snapshot, "values", None)
    if not isinstance(values, Mapping):
        return None
    result: dict[str, float] = {}
    for axis in AXIS_NAMES:
        if axis in values:
            result[axis] = float(values[axis])
    return result if result else None


def _pipeline_result(
    workspace: WorkspaceConfig,
    raw_axes: Mapping[str, float] | None,
    *,
    pipeline: WorkspaceSignalPipeline | None = None,
) -> WorkspaceSignalPipelineResult | None:
    if raw_axes is None:
        return None
    if any(axis not in raw_axes for axis in AXIS_NAMES):
        return None
    active_pipeline = pipeline or WorkspaceSignalPipeline(workspace)
    return active_pipeline.process(raw_axes, mode_state=ModeState(), state=active_pipeline.initial_state())


def _axis_monitors(
    raw_axes: Mapping[str, float] | None,
    final_axes: Mapping[str, float] | None,
    pipeline_result: WorkspaceSignalPipelineResult | None,
    state_role: str,
) -> tuple[AnalysisAxisMonitorModel, ...]:
    monitors: list[AnalysisAxisMonitorModel] = []
    for axis in AXIS_NAMES:
        raw_value = _value_from_mapping(raw_axes, axis)
        final_value = _value_from_mapping(final_axes, axis)
        final_text = _value_text(final_value)
        role = state_role if raw_value is not None or final_value is not None else "unavailable"
        if final_value is None and pipeline_result is not None:
            preview_value = pipeline_result.final_output_values.get(axis)
            final_text = f"{_value_text(preview_value)} preview"
        monitors.append(
            AnalysisAxisMonitorModel(
                axis_name=axis,
                raw_value=raw_value,
                final_value=final_value,
                raw_text=_value_text(raw_value),
                final_text=final_text,
                state_role=role,
            )
        )
    return tuple(monitors)


def _pipeline_stages(
    *,
    selected_axis: str,
    raw_axes: Mapping[str, float] | None,
    final_axes: Mapping[str, float] | None,
    pipeline_result: WorkspaceSignalPipelineResult | None,
    telemetry_role: str,
) -> tuple[AnalysisPipelineStageModel, ...]:
    if raw_axes is None:
        return _unavailable_pipeline("Current sample unavailable")
    if pipeline_result is None:
        return _unavailable_pipeline("Stage data unavailable from current passive snapshot")

    axis_result = pipeline_result.axis_results[selected_axis]
    by_name = {stage.stage_name: stage for stage in axis_result.stages}
    final_passive = _value_from_mapping(final_axes, selected_axis)
    return (
        _stage_model(
            "raw_input",
            "Raw Input",
            _value_from_mapping(raw_axes, selected_axis),
            "Passive raw input sample for the selected axis.",
            "Bridge telemetry",
            telemetry_role,
        ),
        _stage_model_from_stack(
            "base_tuning",
            "Base Tuning",
            by_name.get("Base Output Limits"),
            "Center conditioning, curve shape, and base output limits as workspace preview.",
            "Workspace preview from passive raw input",
            telemetry_role,
        ),
        _stage_model_from_stack(
            "filtering",
            "Filtering",
            by_name.get("Filtering"),
            "Smoothing and slew behavior as a bounded preview; not a runtime probe.",
            "Workspace preview from passive raw input",
            telemetry_role,
        ),
        _stage_model_from_stack(
            "modes_combat_profile",
            "Modes / Combat Profile",
            by_name.get("Mode Modifiers"),
            "Mode and combat profile contribution. Active mode telemetry is read-only when present.",
            "Workspace preview from passive raw input",
            telemetry_role,
        ),
        _stage_model_from_stack(
            "conditional_rules",
            "Conditional Rules",
            by_name.get("Rule Injections"),
            "Conditional rule stage summary from workspace rule evaluation.",
            "Workspace preview from passive raw input",
            telemetry_role,
        ),
        _stage_model(
            "final_output_intent",
            "Final Output Intent",
            final_passive if final_passive is not None else axis_result.final_output,
            "Output Intent after the visible response stack; this is not output proof.",
            "Bridge telemetry" if final_passive is not None else "Workspace preview from passive raw input",
            telemetry_role,
        ),
    )


def _unavailable_pipeline(reason: str) -> tuple[AnalysisPipelineStageModel, ...]:
    names = (
        ("raw_input", "Raw Input"),
        ("base_tuning", "Base Tuning"),
        ("filtering", "Filtering"),
        ("modes_combat_profile", "Modes / Combat Profile"),
        ("conditional_rules", "Conditional Rules"),
        ("final_output_intent", "Final Output Intent"),
    )
    return tuple(
        AnalysisPipelineStageModel(
            stage_id=stage_id,
            stage_name=name,
            value_text="unavailable",
            stage_summary=f"{reason}; LCD-7 does not invent stage values.",
            source_label="Passive snapshot unavailable",
            state_role="unavailable",
            warning_text="unavailable",
        )
        for stage_id, name in names
    )


def _stage_model_from_stack(
    stage_id: str,
    stage_name: str,
    stage: StageResult | None,
    summary: str,
    source_label: str,
    state_role: str,
) -> AnalysisPipelineStageModel:
    if stage is None:
        return AnalysisPipelineStageModel(
            stage_id=stage_id,
            stage_name=stage_name,
            value_text="unavailable",
            stage_summary="Stage data unavailable from current workspace pipeline preview.",
            source_label=source_label,
            state_role="unavailable",
            warning_text="unavailable",
        )
    return _stage_model(stage_id, stage_name, stage.output_value, summary, source_label, state_role)


def _stage_model(
    stage_id: str,
    stage_name: str,
    value: float | None,
    summary: str,
    source_label: str,
    state_role: str,
) -> AnalysisPipelineStageModel:
    role = state_role if value is not None else "unavailable"
    return AnalysisPipelineStageModel(
        stage_id=stage_id,
        stage_name=stage_name,
        value_text=_value_text(value),
        stage_summary=summary,
        source_label=source_label,
        state_role=role,
        warning_text="" if value is not None else "unavailable",
    )


def _buttons(
    telemetry: BridgeTelemetrySnapshot | None,
    telemetry_role: str,
) -> tuple[AnalysisButtonMonitorModel, ...]:
    source = getattr(getattr(telemetry, "controls", None), "buttons", None)
    source = source if isinstance(source, Mapping) else {}
    result: list[AnalysisButtonMonitorModel] = []
    for label in BUTTON_NAMES:
        available = label in source
        active = bool(source.get(label, False))
        result.append(
            AnalysisButtonMonitorModel(
                label=label,
                active=active,
                state_text="Active" if active else ("Inactive" if available else "Unavailable"),
                state_role=("info" if active else telemetry_role) if available else "unavailable",
            )
        )
    return tuple(result)


def _hat(telemetry: BridgeTelemetrySnapshot | None, telemetry_role: str) -> tuple[str, str, str]:
    hats = getattr(getattr(telemetry, "controls", None), "hats", None)
    hats = hats if isinstance(hats, Mapping) else {}
    value = str(hats.get("POV") or hats.get("Hat") or "")
    if not value:
        return "Neutral", "Hat / POV: Unavailable", "unavailable"
    normalized = value.strip().title()
    if normalized in {"Centered", "Center"}:
        normalized = "Neutral"
    if normalized not in {"Up", "Left", "Neutral", "Right", "Down"}:
        normalized = "Neutral"
    return normalized, f"Hat / POV: {value}", telemetry_role


def _metrics(
    *,
    pipeline_stages: tuple[AnalysisPipelineStageModel, ...],
    axis_monitors: tuple[AnalysisAxisMonitorModel, ...],
    buttons: tuple[AnalysisButtonMonitorModel, ...],
    telemetry_state: _TelemetryState,
    output_proof_label: str,
) -> tuple[tuple[str, str, str, str], ...]:
    active_buttons = sum(1 for button in buttons if button.active)
    available_axes = sum(1 for axis in axis_monitors if axis.raw_value is not None or axis.final_value is not None)
    unavailable_stages = sum(1 for stage in pipeline_stages if stage.state_role == "unavailable")
    return (
        ("Telemetry", telemetry_state.label, telemetry_state.freshness_label, telemetry_state.role),
        ("Axes", f"{available_axes}/6", "Passive raw/final visibility", "ready" if available_axes else "unavailable"),
        ("Active buttons", str(active_buttons), "Read-only button sample", "info" if active_buttons else "unavailable"),
        ("Stage gaps", str(unavailable_stages), "Unavailable stage values are not invented", "warning" if unavailable_stages else "info"),
        ("Output proof", output_proof_label.replace("Output proof ", ""), "Proof remains separate", "verified" if output_proof_label.endswith("verified") else "blocked"),
    )


def _warnings(*, telemetry: BridgeTelemetrySnapshot | None, telemetry_label: str) -> tuple[str, ...]:
    notes: list[str] = []
    if telemetry_label == "Telemetry stale":
        notes.append("Telemetry stale; retained values are not live.")
    if telemetry_label == "Telemetry missing":
        notes.append("Current sample unavailable.")
    if telemetry is not None:
        notes.extend(telemetry.warnings)
        notes.extend(telemetry.errors)
    return tuple(notes) or ("Read-only visualization; output intent is not proof.",)


def _advanced_details(
    *,
    route_key: str,
    selected_axis: str,
    telemetry: BridgeTelemetrySnapshot | None,
    telemetry_state: _TelemetryState,
    runtime_truth_label: str,
    output_proof_label: str,
    pipeline_stages: tuple[AnalysisPipelineStageModel, ...],
) -> tuple[tuple[str, str], ...]:
    runtime_frame = dict(telemetry.runtime_frame or {}) if telemetry is not None and telemetry.runtime_frame is not None else {}
    details = [
        ("Route key", route_key),
        ("Selected axis key", selected_axis),
        ("Telemetry source", telemetry_state.source_label),
        ("Telemetry freshness", telemetry_state.freshness_label),
        ("Runtime truth label", runtime_truth_label),
        ("Output proof state", output_proof_label),
        ("Output intent note", "Final output intent is not output proof."),
        ("Pipeline stage count", str(len(pipeline_stages))),
        ("Runtime frame ready state", str(runtime_frame.get("ready_state") or "unavailable")),
        ("Runtime frame output proof", str(runtime_frame.get("output_proof") or "unavailable")),
        ("Runtime frame telemetry proof", str(runtime_frame.get("telemetry_proof") or "unavailable")),
    ]
    if telemetry is not None:
        details.extend(
            (
                ("Bridge lifecycle state", telemetry.lifecycle_state.value),
                ("Active profile", telemetry.active_profile),
                ("Active modes", ", ".join(telemetry.active_modes.to_dict().get("active_mode_names", ())) or "none"),
                ("Rule summary", str(telemetry.rule_summary.to_dict())),
                ("Raw axis count", str(len(getattr(telemetry.raw_axes, "values", {})))),
                ("Final axis count", str(len(getattr(telemetry.final_axes, "values", {})))),
                ("Button count", str(len(getattr(telemetry.controls, "buttons", {})))),
                ("Hat state", ", ".join(f"{key}:{value}" for key, value in getattr(telemetry.controls, "hats", {}).items()) or "unavailable"),
            )
        )
    return tuple(details)


def _output_verified(*, state: AppState | None, telemetry: BridgeTelemetrySnapshot | None) -> bool:
    if telemetry is not None:
        return bool(telemetry.output_verified)
    return bool(state is not None and state.runtime.output_verified)


def _runtime_truth_label(
    *,
    state: AppState | None,
    telemetry: BridgeTelemetrySnapshot | None,
    output_verified: bool,
) -> str:
    truth = telemetry.runtime_truth if telemetry is not None else _state_truth(state)
    if truth is RuntimeTruth.LIVE_VERIFIED and output_verified:
        return "Live Verified"
    if truth is RuntimeTruth.DETECTED_UNVERIFIED:
        return "Detected Unverified"
    if truth in {RuntimeTruth.BLOCKED_MISSING_DEVICE, RuntimeTruth.BLOCKED_MISSING_DRIVER}:
        return "Runtime blocked"
    if truth is RuntimeTruth.ERROR:
        return "Hard error"
    return "Simulation mode"


def _value_from_mapping(values: Mapping[str, float] | None, key: str) -> float | None:
    if values is None or key not in values:
        return None
    return float(values[key])


def _value_text(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"{value:+.3f}"


def _page_title(route_key: str) -> str:
    return {
        "analysis.effective_response_stack": "Effective Response Stack",
        "analysis.live_monitor": "Live Monitor",
    }[route_key]


def _page_question(route_key: str) -> str:
    return {
        "analysis.effective_response_stack": "How does raw input become final output?",
        "analysis.live_monitor": "What is the HOTAS doing right now?",
    }[route_key]
