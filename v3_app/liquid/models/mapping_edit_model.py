from __future__ import annotations

from dataclasses import dataclass, replace

from shared_core.models.mappings import AxisMapping, ButtonMapping, MappingConfig
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from v3_app.liquid.models.mapping_command_model import build_mapping_command_model


AXIS_FUNCTION_OPTIONS = ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
AXIS_OUTPUT_INTENT_OPTIONS = (
    "vJoy X(axis1)",
    "vJoy Y(axis2)",
    "vJoy Z(axis3)",
    "vJoy RX(axis4)",
    "vJoy RY(axis5)",
    "vJoy RZ(axis6)",
    "vJoy SL0(axis7)",
    "vJoy SL1(axis8)",
)
BUTTON_OUTPUT_INTENT_OPTIONS = tuple(f"Button {index}" for index in range(1, 21))

_AXIS_FUNCTION_BY_CONTROL_ID = {
    "axis_roll": "Roll",
    "axis_pitch": "Pitch",
    "axis_throttle": "Throttle",
    "axis_yaw": "Yaw",
    "axis_aux_1": "Aux 1",
    "axis_aux_2": "Aux 2",
}
_AXIS_CONTROL_ID_BY_FUNCTION = {value: key for key, value in _AXIS_FUNCTION_BY_CONTROL_ID.items()}


@dataclass(frozen=True)
class MappingEditableField:
    field_id: str
    label: str
    value: str
    editable: bool
    options: tuple[str, ...] = ()
    read_only_reason: str = ""


@dataclass(frozen=True)
class MappingRouteRecord:
    route_id: str
    route_key: str
    physical_control_id: str
    physical_label: str
    control_type: str
    raw_channel: str
    logical_function: str
    output_intent_target: str
    enabled_state: str
    status: str
    notes: str
    warning: str
    editable_fields: tuple[MappingEditableField, ...]
    changed: bool = False
    status_role: str = "info"


@dataclass(frozen=True)
class MappingEditModel:
    route_records: tuple[MappingRouteRecord, ...]
    selected_route: MappingRouteRecord
    changed_count: int
    draft_state_label: str
    truth_source_notes: tuple[str, ...]


@dataclass(frozen=True)
class MappingEditResult:
    valid: bool
    workspace: WorkspaceConfig
    route_id: str
    field_id: str
    staged_value: str
    status_label: str
    message: str
    validation_errors: tuple[str, ...] = ()


def build_mapping_edit_model(
    *,
    workspace: WorkspaceConfig | None = None,
    base_workspace: WorkspaceConfig | None = None,
    selected_route_id: str | None = None,
) -> MappingEditModel:
    workspace = workspace or create_default_workspace()
    base_workspace = base_workspace or workspace
    command_model = build_mapping_command_model(workspace=workspace)
    base_records = {
        record.route_id: record
        for record in _records_for_workspace(base_workspace)
    }
    records = tuple(
        _record_from_command_detail(
            detail,
            changed=_record_changed(detail.route_key, detail.output_intent_target, detail.function, base_records),
        )
        for detail in command_model.advanced_route_details
    )
    selected = _select_route(records, selected_route_id)
    changed_count = sum(1 for record in records if record.changed)
    draft_label = "Draft mapping change staged" if changed_count else "Draft unchanged"
    return MappingEditModel(
        route_records=records,
        selected_route=selected,
        changed_count=changed_count,
        draft_state_label=draft_label,
        truth_source_notes=(
            "Route edits are workspace/draft mapping edits only.",
            "Output Intent is route intent, not output proof.",
            "Output proof unchanged by Mapping edits.",
        ),
    )


def stage_mapping_route_edit(
    workspace: WorkspaceConfig,
    route_id: str,
    field_id: str,
    value: str,
) -> MappingEditResult:
    model = build_mapping_edit_model(workspace=workspace, selected_route_id=route_id)
    record = _record_by_id(model.route_records, route_id)
    if record is None:
        return _invalid(workspace, route_id, field_id, value, "Unknown route key; edit was not staged.")

    field = _field_by_id(record, field_id)
    if field is None:
        return _invalid(workspace, route_id, field_id, value, "Unknown editable field; edit was not staged.")
    if not field.editable:
        reason = field.read_only_reason or "This route field is read-only in LCD-5G."
        return _invalid(workspace, route_id, field_id, value, f"{reason} Edit was not staged.")

    validation_errors = _validate_field_edit(workspace, record, field, value)
    if validation_errors:
        return MappingEditResult(
            valid=False,
            workspace=workspace,
            route_id=route_id,
            field_id=field_id,
            staged_value=value,
            status_label="Route edit rejected",
            message=f"{validation_errors[0]} Edit was not staged.",
            validation_errors=tuple(validation_errors),
        )

    updated = _workspace_with_edit(workspace, record, field, value)
    if updated is None:
        return _invalid(workspace, route_id, field_id, value, "Unsupported route shape; edit was not staged.")
    return MappingEditResult(
        valid=True,
        workspace=_mark_workspace_dirty(updated),
        route_id=route_id,
        field_id=field_id,
        staged_value=value,
        status_label="Draft mapping change staged",
        message=(
            f"Draft mapping change staged for {record.physical_label}. "
            "Save workspace to persist. Output proof unchanged."
        ),
    )


def route_id_for_control_id(control_id: str) -> str:
    if control_id.startswith("axis_"):
        return f"axis:{control_id}"
    if control_id.startswith("button_b"):
        return f"button:{control_id}"
    if control_id == "hat_pov":
        return "hat:hat_pov"
    return control_id


def control_id_for_route_id(route_id: str) -> str:
    if ":" not in route_id:
        return route_id
    return route_id.split(":", 1)[1]


def _records_for_workspace(workspace: WorkspaceConfig) -> tuple[MappingRouteRecord, ...]:
    command_model = build_mapping_command_model(workspace=workspace)
    return tuple(
        _record_from_command_detail(detail, changed=False)
        for detail in command_model.advanced_route_details
    )


def _record_from_command_detail(detail, *, changed: bool) -> MappingRouteRecord:
    route_type, _, control_id = detail.route_key.partition(":")
    status = "unsupported" if detail.mapped_state == "mapped" and route_type == "hat" else detail.mapped_state
    warning = detail.notes if "warning:" in detail.notes.casefold() else ""
    return MappingRouteRecord(
        route_id=detail.route_key,
        route_key=detail.route_key,
        physical_control_id=control_id,
        physical_label=_physical_label(control_id),
        control_type=_control_type(route_type),
        raw_channel=detail.raw_channel,
        logical_function=detail.function,
        output_intent_target=detail.output_intent_target,
        enabled_state="Not represented in current workspace schema",
        status="draft changed" if changed else status,
        notes=detail.notes,
        warning=warning,
        editable_fields=_editable_fields_for_detail(route_type, detail),
        changed=changed,
        status_role="warning" if changed or warning else detail.role,
    )


def _editable_fields_for_detail(route_type: str, detail) -> tuple[MappingEditableField, ...]:
    common_read_only = (
        MappingEditableField(
            "raw_channel",
            "Raw channel",
            detail.raw_channel,
            editable=False,
            read_only_reason="Physical control assignment changes are deferred to a later Mapping phase.",
        ),
        MappingEditableField(
            "enabled",
            "Enabled state",
            "Not represented in current workspace schema",
            editable=False,
            read_only_reason="Enabled/disabled route flags are not represented in the current workspace schema.",
        ),
    )
    if route_type == "axis" and detail.mapped_state == "mapped":
        return (
            MappingEditableField(
                "logical_function",
                "Logical function",
                detail.function,
                editable=True,
                options=AXIS_FUNCTION_OPTIONS,
            ),
            MappingEditableField(
                "output_intent_target",
                "Output Intent target",
                detail.output_intent_target,
                editable=True,
                options=AXIS_OUTPUT_INTENT_OPTIONS,
            ),
            *common_read_only,
        )
    if route_type == "button" and detail.mapped_state == "mapped":
        return (
            MappingEditableField(
                "logical_function",
                "Logical function",
                detail.function,
                editable=False,
                read_only_reason="Button semantic labels are derived from physical button routes in LCD-5G.",
            ),
            MappingEditableField(
                "output_intent_target",
                "Output Intent target",
                detail.output_intent_target,
                editable=True,
                options=BUTTON_OUTPUT_INTENT_OPTIONS,
            ),
            *common_read_only,
        )
    return (
        MappingEditableField(
            "logical_function",
            "Logical function",
            detail.function,
            editable=False,
            read_only_reason="Route creation or complex hat editing is deferred to a later Mapping phase.",
        ),
        MappingEditableField(
            "output_intent_target",
            "Output Intent target",
            detail.output_intent_target,
            editable=False,
            read_only_reason="Route creation or complex hat editing is deferred to a later Mapping phase.",
        ),
        *common_read_only,
    )


def _record_changed(
    route_id: str,
    output_intent_target: str,
    function: str,
    base_records: dict[str, MappingRouteRecord],
) -> bool:
    base = base_records.get(route_id)
    if base is None:
        return True
    return base.output_intent_target != output_intent_target or base.logical_function != function


def _select_route(records: tuple[MappingRouteRecord, ...], selected_route_id: str | None) -> MappingRouteRecord:
    preferred = selected_route_id or "axis:axis_roll"
    for record in records:
        if record.route_id == preferred:
            return record
    for record in records:
        if record.route_id == "axis:axis_roll":
            return record
    return records[0]


def _record_by_id(records: tuple[MappingRouteRecord, ...], route_id: str) -> MappingRouteRecord | None:
    for record in records:
        if record.route_id == route_id:
            return record
    return None


def _field_by_id(record: MappingRouteRecord, field_id: str) -> MappingEditableField | None:
    for field in record.editable_fields:
        if field.field_id == field_id:
            return field
    return None


def _validate_field_edit(
    workspace: WorkspaceConfig,
    record: MappingRouteRecord,
    field: MappingEditableField,
    value: str,
) -> tuple[str, ...]:
    normalized = value.strip()
    if not normalized:
        return ("A required route value is empty.",)
    if field.options and normalized not in field.options:
        return (f"{field.label} {normalized!r} is not supported for this route.",)
    if record.control_type == "axis":
        return _validate_axis_edit(workspace, record, field, normalized)
    if record.control_type == "button":
        return _validate_button_edit(workspace, record, field, normalized)
    return ("This route type is read-only in LCD-5G.",)


def _validate_axis_edit(
    workspace: WorkspaceConfig,
    record: MappingRouteRecord,
    field: MappingEditableField,
    value: str,
) -> tuple[str, ...]:
    if field.field_id == "logical_function":
        for route in workspace.mappings.axis_routes:
            if _axis_route_id(route) != record.route_id and route.function_name == value:
                return (f"Logical function {value!r} is already assigned to another axis route.",)
        return ()
    if field.field_id == "output_intent_target":
        target = _strip_vjoy_prefix(value)
        for route in workspace.mappings.axis_routes:
            if _axis_route_id(route) != record.route_id and route.runtime_vjoy_output == target:
                return (f"Output Intent {value!r} is already assigned to another axis route.",)
        return ()
    return ("This axis field is read-only in LCD-5G.",)


def _validate_button_edit(
    workspace: WorkspaceConfig,
    record: MappingRouteRecord,
    field: MappingEditableField,
    value: str,
) -> tuple[str, ...]:
    if field.field_id != "output_intent_target":
        return ("This button field is read-only in LCD-5G.",)
    target = _button_output_number(value)
    if target is None:
        return (f"Output Intent {value!r} is not a supported button target.",)
    for route in workspace.mappings.button_routes:
        if _button_route_id(route) != record.route_id and route.output_button == target:
            return (f"Output Intent {value!r} is already assigned to another button route.",)
    return ()


def _workspace_with_edit(
    workspace: WorkspaceConfig,
    record: MappingRouteRecord,
    field: MappingEditableField,
    value: str,
) -> WorkspaceConfig | None:
    if record.control_type == "axis":
        mapping = _mapping_with_axis_edit(workspace.mappings, record, field, value)
    elif record.control_type == "button":
        mapping = _mapping_with_button_edit(workspace.mappings, record, field, value)
    else:
        mapping = None
    if mapping is None:
        return None
    return replace(workspace, mappings=mapping)


def _mapping_with_axis_edit(
    mapping: MappingConfig,
    record: MappingRouteRecord,
    field: MappingEditableField,
    value: str,
) -> MappingConfig | None:
    routes = list(mapping.axis_routes)
    for index, route in enumerate(routes):
        if _axis_route_id(route) != record.route_id:
            continue
        if field.field_id == "logical_function":
            routes[index] = replace(route, function_name=value)
        elif field.field_id == "output_intent_target":
            routes[index] = replace(route, runtime_vjoy_output=_strip_vjoy_prefix(value))
        else:
            return None
        return replace(mapping, axis_routes=tuple(routes))
    return None


def _mapping_with_button_edit(
    mapping: MappingConfig,
    record: MappingRouteRecord,
    field: MappingEditableField,
    value: str,
) -> MappingConfig | None:
    if field.field_id != "output_intent_target":
        return None
    target = _button_output_number(value)
    if target is None:
        return None
    routes = list(mapping.button_routes)
    for index, route in enumerate(routes):
        if _button_route_id(route) != record.route_id:
            continue
        routes[index] = replace(route, output_button=target)
        return replace(mapping, button_routes=tuple(routes))
    return None


def _mark_workspace_dirty(workspace: WorkspaceConfig) -> WorkspaceConfig:
    return replace(workspace, state=replace(workspace.state, dirty=True, saved=False))


def _invalid(
    workspace: WorkspaceConfig,
    route_id: str,
    field_id: str,
    value: str,
    message: str,
) -> MappingEditResult:
    return MappingEditResult(
        valid=False,
        workspace=workspace,
        route_id=route_id,
        field_id=field_id,
        staged_value=value,
        status_label="Route edit rejected",
        message=message,
        validation_errors=(message,),
    )


def _axis_route_id(route: AxisMapping) -> str:
    control_id = _AXIS_CONTROL_ID_BY_FUNCTION.get(route.function_name, _axis_control_id(route.function_name))
    return f"axis:{control_id}"


def _button_route_id(route: ButtonMapping) -> str:
    return f"button:button_b{route.hotas_button}"


def _axis_control_id(axis_name: str) -> str:
    return "axis_" + axis_name.casefold().replace(" ", "_").replace("/", "_")


def _strip_vjoy_prefix(value: str) -> str:
    return value.strip().removeprefix("vJoy ").strip()


def _button_output_number(value: str) -> int | None:
    text = value.strip()
    if text.casefold().startswith("button "):
        text = text.split(" ", 1)[1]
    try:
        number = int(text)
    except ValueError:
        return None
    return number if 1 <= number <= 20 else None


def _physical_label(control_id: str) -> str:
    return {
        "axis_roll": "Roll axis",
        "axis_pitch": "Pitch axis",
        "axis_throttle": "Throttle axis",
        "axis_yaw": "Yaw axis",
        "axis_aux_1": "Aux 1",
        "axis_aux_2": "Aux 2",
        "hat_pov": "Hat / POV",
    }.get(control_id, control_id.replace("button_b", "B").replace("_", " ").title())


def _control_type(route_type: str) -> str:
    return {
        "axis": "axis",
        "button": "button",
        "hat": "hat",
    }.get(route_type, "auxiliary")
