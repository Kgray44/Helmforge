from __future__ import annotations

from dataclasses import dataclass

from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from v3_app.services.app_state import AppState
from v3_app.services.hotas_diagram_model import HotasDiagramControl, build_hotas_diagram_model


@dataclass(frozen=True)
class MappingControlModel:
    control_id: str
    display_label: str
    control_type: str
    physical_group: str
    anchor_x: float
    anchor_y: float
    raw_input_channel: str
    physical_source_label: str
    logical_function: str
    output_intent_target: str
    current_value_state: str
    mapped_state: str
    status_role: str
    warning: str
    detail_text: str
    route_type: str


@dataclass(frozen=True)
class MappingRouteFlowModel:
    source_label: str
    function_label: str
    target_label: str
    status_role: str
    helper_text: str


@dataclass(frozen=True)
class MappingMetricModel:
    label: str
    value: str
    caption: str
    role: str


@dataclass(frozen=True)
class MappingAdvancedRouteDetailModel:
    route_key: str
    physical_control_id: str
    raw_channel: str
    function: str
    output_intent_target: str
    mapped_state: str
    notes: str
    role: str


@dataclass(frozen=True)
class MappingCommandModel:
    controls: tuple[MappingControlModel, ...]
    selected_control: MappingControlModel
    route_flows: tuple[MappingRouteFlowModel, ...]
    mapping_metrics: tuple[MappingMetricModel, ...]
    warnings: tuple[str, ...]
    advanced_route_details: tuple[MappingAdvancedRouteDetailModel, ...]
    truth_source_notes: tuple[str, ...]
    source_label: str
    runtime_truth_label: str


def build_mapping_command_model(
    *,
    workspace: WorkspaceConfig | None = None,
    state: AppState | None = None,
    selected_control_id: str | None = None,
) -> MappingCommandModel:
    workspace = workspace or create_default_workspace()
    source_label = _source_label(state, workspace)
    runtime_truth_label = state.runtime.header_truth_label if state is not None else "Simulated"
    diagram = build_hotas_diagram_model(workspace, source_label=source_label)
    controls = tuple(_control_from_diagram(control) for control in diagram.routed_controls)
    selected = _select_control(controls, selected_control_id)
    route_flows = (_route_flow_for_control(selected),)
    warnings = tuple(control.warning for control in controls if control.warning)
    return MappingCommandModel(
        controls=controls,
        selected_control=selected,
        route_flows=route_flows,
        mapping_metrics=_metrics_for_controls(controls),
        warnings=warnings,
        advanced_route_details=tuple(_advanced_detail(control) for control in controls),
        truth_source_notes=(
            "Mapping data is derived from the current workspace/config route model.",
            "Output intent is not output write proof.",
            "Read-only visualization: selecting controls updates the inspector only.",
        ),
        source_label=source_label,
        runtime_truth_label=runtime_truth_label,
    )


def _select_control(
    controls: tuple[MappingControlModel, ...],
    selected_control_id: str | None,
) -> MappingControlModel:
    preferred_ids = (selected_control_id, "axis_roll")
    for preferred_id in preferred_ids:
        if not preferred_id:
            continue
        for control in controls:
            if control.control_id == preferred_id:
                return control
    return controls[0]


def _control_from_diagram(control: HotasDiagramControl) -> MappingControlModel:
    output_target = _output_target(control)
    logical = _logical_function(control)
    mapped_state = "mapped" if control.status == "mapped" else "unmapped"
    return MappingControlModel(
        control_id=control.control_id,
        display_label=control.display_label,
        control_type=control.control_type,
        physical_group=_physical_group(control),
        anchor_x=control.anchor_x,
        anchor_y=control.anchor_y,
        raw_input_channel=control.raw_input_channel,
        physical_source_label=_physical_source_label(control),
        logical_function=logical,
        output_intent_target=output_target,
        current_value_state=control.current_value_state,
        mapped_state=mapped_state,
        status_role=_status_role(control),
        warning=control.warning or "",
        detail_text=control.help_text or "Workspace route preview only.",
        route_type=control.route_type,
    )


def _physical_group(control: HotasDiagramControl) -> str:
    if control.control_id.startswith("axis_throttle") or control.control_id.startswith("axis_aux"):
        return "throttle"
    if control.control_id.startswith("button_b"):
        try:
            index = int(control.control_id.removeprefix("button_b"))
        except ValueError:
            return "unknown"
        return "throttle" if index >= 9 else "stick"
    if control.control_type in {"axis", "hat"}:
        return "stick"
    return "unknown"


def _physical_source_label(control: HotasDiagramControl) -> str:
    return {
        "axis_roll": "Physical Stick X",
        "axis_pitch": "Physical Stick Y",
        "axis_throttle": "Throttle Lever",
        "axis_yaw": "Rudder Twist",
        "axis_aux_1": "Aux 1",
        "axis_aux_2": "Aux 2",
        "hat_pov": "Hat / POV",
    }.get(control.control_id, control.display_label)


def _logical_function(control: HotasDiagramControl) -> str:
    if control.control_id.startswith("axis_"):
        return control.mapped_function.split(" -> ", 1)[0]
    if control.control_id.startswith("button_b"):
        return f"{control.display_label} route" if control.status == "mapped" else "Unmapped"
    if control.control_id == "hat_pov":
        return "View Hat" if control.status == "mapped" else "Unmapped"
    return control.mapped_function


def _output_target(control: HotasDiagramControl) -> str:
    target = control.output_intent_target.removeprefix("Output intent: ").strip()
    if not target or target.casefold() in {"unmapped", "unavailable"}:
        return target or "unavailable"
    if control.control_type == "axis":
        return target if target.startswith("vJoy ") else f"vJoy {target}"
    return target


def _status_role(control: HotasDiagramControl) -> str:
    if control.warning:
        return "warning"
    if control.status == "mapped":
        return "ready"
    if control.status == "unmapped":
        return "warning"
    return "unavailable"


def _route_flow_for_control(control: MappingControlModel) -> MappingRouteFlowModel:
    return MappingRouteFlowModel(
        source_label=control.physical_source_label,
        function_label=control.logical_function,
        target_label=control.output_intent_target,
        status_role=control.status_role,
        helper_text=(
            f"{control.display_label}: {control.mapped_state}. "
            "Route preview only; Output Intent is not output write proof."
        ),
    )


def _metrics_for_controls(controls: tuple[MappingControlModel, ...]) -> tuple[MappingMetricModel, ...]:
    axes = [control for control in controls if control.control_type == "axis" and control.mapped_state == "mapped"]
    buttons = [control for control in controls if control.control_type == "button" and control.mapped_state == "mapped"]
    hats = [control for control in controls if control.control_type == "hat" and control.mapped_state == "mapped"]
    unmapped = [control for control in controls if control.mapped_state != "mapped"]
    warnings = [control for control in controls if control.warning]
    targets = {
        control.output_intent_target
        for control in controls
        if control.output_intent_target not in {"unmapped", "unavailable"}
    }
    return (
        MappingMetricModel("Axis Routes", str(len(axes)), "workspace mapping intent", "info"),
        MappingMetricModel("Button Routes", str(len(buttons)), "switch bindings", "info"),
        MappingMetricModel("Hat Routes", str(len(hats)), "POV route intent", "info"),
        MappingMetricModel("Unmapped Controls", str(len(unmapped)), "honest workspace gaps", "warning" if unmapped else "ready"),
        MappingMetricModel("Warnings", str(len(warnings)), "workspace/config route warnings", "warning" if warnings else "ready"),
        MappingMetricModel("Output Intent Targets", str(len(targets)), "intent targets, not proof", "info"),
    )


def _advanced_detail(control: MappingControlModel) -> MappingAdvancedRouteDetailModel:
    return MappingAdvancedRouteDetailModel(
        route_key=f"{control.route_type}:{control.control_id}",
        physical_control_id=control.control_id,
        raw_channel=control.raw_input_channel,
        function=control.logical_function,
        output_intent_target=control.output_intent_target,
        mapped_state=control.mapped_state,
        notes=control.warning or control.detail_text,
        role=control.status_role,
    )


def _source_label(state: AppState | None, workspace: WorkspaceConfig) -> str:
    if state is not None and state.source_config:
        return "Bridge Config" if "hotas_bridge_config" in state.source_config.casefold() else "Workspace Config"
    if workspace.source_path:
        return "Bridge Config" if "hotas_bridge_config" in workspace.source_path.casefold() else "Workspace Config"
    return "Workspace Config"
