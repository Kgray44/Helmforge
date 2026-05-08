from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from shared_core.models.mappings import AxisMapping, ButtonMapping, HatMapping
from shared_core.models.runtime import AXIS_NAMES, BUTTON_NAMES, HAT_CENTERED
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace


@dataclass(frozen=True)
class HotasDiagramControl:
    control_id: str
    display_label: str
    control_type: str
    anchor_x: float
    anchor_y: float
    region_width: float | None = None
    region_height: float | None = None
    raw_input_channel: str = "unavailable"
    mapped_function: str = "unmapped"
    output_intent_target: str = "Output intent: unavailable"
    current_value_state: str = "unavailable"
    help_text: str = ""
    status: str = "unavailable"
    warning: str | None = None
    route_type: str = "reference"
    table_object_name: str | None = None
    route_row: int | None = None
    editable: bool = False


@dataclass(frozen=True)
class HotasDiagramSelection:
    control_id: str
    route_type: str
    table_object_name: str
    route_row: int
    is_selectable: bool = True


@dataclass(frozen=True)
class HotasRouteWarning:
    code: str
    severity: str
    control_id: str
    route_type: str
    message: str


@dataclass(frozen=True)
class HotasRouteInspector:
    selected_control_id: str
    selected_label: str
    selected_physical_input: str
    mapped_virtual_output: str
    route_type: str
    mode_profile_context: str
    source_of_truth: str
    editable_in_current_ui: str
    conflict_status: str
    no_live_output_verification_notice: str
    warnings: tuple[HotasRouteWarning, ...] = ()


@dataclass(frozen=True)
class HotasDiagramModel:
    controls: tuple[HotasDiagramControl, ...]
    source_label: str = "Simulation/fallback"
    truth_note: str = (
        "Read-only visual/diagnostic diagram. Output intent is not output write proof."
    )

    @property
    def routed_controls(self) -> tuple[HotasDiagramControl, ...]:
        return tuple(
            control
            for control in self.controls
            if control.control_type in {"axis", "button", "hat"}
        )


_PHYSICAL_REFERENCE_CONTROLS: tuple[HotasDiagramControl, ...] = (
    HotasDiagramControl(
        control_id="region_throttle",
        display_label="Throttle side",
        control_type="throttle",
        anchor_x=0.24,
        anchor_y=0.50,
        region_width=0.28,
        region_height=0.72,
        raw_input_channel="layout reference",
        mapped_function="Physical throttle controls",
        output_intent_target="Output intent: none (physical reference)",
        current_value_state="reference only",
        help_text="Schematic region for the throttle half of the HOTAS.",
        status="reference",
    ),
    HotasDiagramControl(
        control_id="region_stick",
        display_label="Stick side",
        control_type="stick",
        anchor_x=0.74,
        anchor_y=0.46,
        region_width=0.28,
        region_height=0.66,
        raw_input_channel="layout reference",
        mapped_function="Physical stick controls",
        output_intent_target="Output intent: none (physical reference)",
        current_value_state="reference only",
        help_text="Schematic region for the stick half of the HOTAS.",
        status="reference",
    ),
    HotasDiagramControl(
        control_id="region_base",
        display_label="Base",
        control_type="base",
        anchor_x=0.50,
        anchor_y=0.80,
        region_width=0.72,
        region_height=0.18,
        raw_input_channel="layout reference",
        mapped_function="Shared HOTAS base",
        output_intent_target="Output intent: none (physical reference)",
        current_value_state="reference only",
        help_text="Schematic base reference for button and aux placement.",
        status="reference",
    ),
)


_AXIS_LAYOUT = {
    "Roll": ("axis_roll", "Roll axis", 0.66, 0.42),
    "Pitch": ("axis_pitch", "Pitch axis", 0.78, 0.34),
    "Throttle": ("axis_throttle", "Throttle axis", 0.24, 0.34),
    "Yaw": ("axis_yaw", "Yaw axis", 0.76, 0.58),
    "Aux 1": ("axis_aux_1", "Aux 1", 0.31, 0.70),
    "Aux 2": ("axis_aux_2", "Aux 2", 0.42, 0.70),
}

_BUTTON_LAYOUT = {
    1: (0.66, 0.23),
    2: (0.76, 0.23),
    3: (0.84, 0.32),
    4: (0.61, 0.32),
    5: (0.58, 0.49),
    6: (0.86, 0.49),
    7: (0.63, 0.68),
    8: (0.78, 0.68),
    9: (0.17, 0.23),
    10: (0.30, 0.23),
    11: (0.16, 0.55),
    12: (0.30, 0.55),
    13: (0.45, 0.79),
    14: (0.53, 0.79),
    15: (0.61, 0.79),
}


def build_hotas_diagram_model(
    workspace: WorkspaceConfig | None = None,
    *,
    raw_axis_values: Mapping[str, float] | None = None,
    button_states: Mapping[str, bool] | None = None,
    hat_state: str | None = None,
    source_label: str = "Simulation/fallback",
) -> HotasDiagramModel:
    workspace = workspace or create_default_workspace()
    axis_routes = {
        route.function_name: (row, route)
        for row, route in enumerate(workspace.mappings.axis_routes)
    }
    button_routes = {
        route.hotas_button: (row, route)
        for row, route in enumerate(workspace.mappings.button_routes)
    }
    hat_routes = {
        route.hotas_hat: (row, route)
        for row, route in enumerate(workspace.mappings.hat_routes)
    }

    controls: list[HotasDiagramControl] = list(_PHYSICAL_REFERENCE_CONTROLS)
    controls.extend(
        _axis_control(
            axis_name,
            axis_routes.get(axis_name),
            raw_axis_values=raw_axis_values,
            source_label=source_label,
        )
        for axis_name in AXIS_NAMES
    )
    controls.extend(
        _button_control(
            button_name,
            button_routes.get(index),
            button_states=button_states,
            source_label=source_label,
        )
        for index, button_name in enumerate(BUTTON_NAMES, start=1)
    )
    controls.append(
        _hat_control(
            hat_routes.get(1),
            hat_state=hat_state,
            source_label=source_label,
        )
    )

    return HotasDiagramModel(controls=tuple(controls), source_label=source_label)


def select_hotas_diagram_route(
    model: HotasDiagramModel,
    control_id: str,
) -> HotasDiagramSelection | None:
    for control in model.routed_controls:
        if control.control_id != control_id:
            continue
        if control.table_object_name is None or control.route_row is None:
            return None
        return HotasDiagramSelection(
            control_id=control.control_id,
            route_type=control.route_type,
            table_object_name=control.table_object_name,
            route_row=control.route_row,
        )
    return None


def build_workspace_route_warnings(workspace: WorkspaceConfig) -> tuple[HotasRouteWarning, ...]:
    warnings: list[HotasRouteWarning] = []
    warnings.extend(_duplicate_axis_output_warnings(workspace))
    warnings.extend(_duplicate_button_output_warnings(workspace))
    warnings.extend(_missing_or_invalid_axis_warnings(workspace))
    warnings.extend(_missing_or_invalid_button_warnings(workspace))
    warnings.extend(_missing_or_invalid_hat_warnings(workspace))
    return tuple(warnings)


def build_route_inspector(
    control: HotasDiagramControl,
    *,
    workspace: WorkspaceConfig,
    active_profile: str,
    source_label: str,
    runtime_truth_label: str,
    telemetry_status: str,
    warnings: tuple[HotasRouteWarning, ...] | None = None,
) -> HotasRouteInspector:
    route_warnings = warnings if warnings is not None else build_workspace_route_warnings(workspace)
    control_warnings = tuple(
        warning for warning in route_warnings if warning.control_id == control.control_id
    )
    output_target = control.output_intent_target.removeprefix("Output intent: ").strip()
    conflict_status = (
        "No workspace conflicts detected"
        if not control_warnings
        else "; ".join(warning.message for warning in control_warnings)
    )
    editable = (
        "Editable in Mapping table"
        if control.editable and control.table_object_name is not None
        else "Read-only reference"
    )
    return HotasRouteInspector(
        selected_control_id=control.control_id,
        selected_label=control.display_label,
        selected_physical_input=control.raw_input_channel,
        mapped_virtual_output=output_target,
        route_type=control.route_type,
        mode_profile_context=f"Profile: {active_profile}",
        source_of_truth=(
            f"workspace/config route with {source_label} display values; "
            f"{telemetry_status}; runtime truth: {runtime_truth_label}"
        ),
        editable_in_current_ui=editable,
        conflict_status=conflict_status,
        no_live_output_verification_notice=(
            "No live output verification: Output intent does not prove live output."
        ),
        warnings=control_warnings,
    )


def format_hotas_control_tooltip(control: HotasDiagramControl) -> str:
    lines = [
        control.display_label,
        f"Type: {control.control_type}",
        f"Raw channel: {control.raw_input_channel}",
        f"Mapped function: {control.mapped_function}",
        control.output_intent_target,
        f"Current value/state: {control.current_value_state}",
        f"Status: {control.status}",
        "Note: Read-only visual/diagnostic only. Output intent is not output write proof.",
    ]
    if control.warning:
        lines.insert(6, f"Warning: {control.warning}")
    if control.help_text:
        lines.insert(6, f"Help: {control.help_text}")
    return "\n".join(lines)


def _axis_control(
    axis_name: str,
    route_info: tuple[int, AxisMapping] | None,
    *,
    raw_axis_values: Mapping[str, float] | None,
    source_label: str,
) -> HotasDiagramControl:
    control_id, display_label, anchor_x, anchor_y = _AXIS_LAYOUT[axis_name]
    route = route_info[1] if route_info is not None else None
    row = route_info[0] if route_info is not None else None
    if route is None:
        return HotasDiagramControl(
            control_id=control_id,
            display_label=display_label,
            control_type="axis",
            anchor_x=anchor_x,
            anchor_y=anchor_y,
            region_width=0.13,
            region_height=0.12,
            raw_input_channel="unavailable",
            mapped_function=f"{axis_name} -> unmapped",
            output_intent_target="Output intent: unmapped",
            current_value_state="unavailable",
            help_text=f"{display_label} has no workspace route.",
            status="unmapped",
            warning="No axis route is available in the workspace.",
            route_type="axis",
        )

    current = route.live_raw_value
    if raw_axis_values is not None and axis_name in raw_axis_values:
        current = raw_axis_values[axis_name]
    return HotasDiagramControl(
        control_id=control_id,
        display_label=display_label,
        control_type="axis",
        anchor_x=anchor_x,
        anchor_y=anchor_y,
        region_width=0.13,
        region_height=0.12,
        raw_input_channel=route.raw_axis_channel,
        mapped_function=f"{route.function_name} -> {route.logical_output}",
        output_intent_target=f"Output intent: {route.runtime_vjoy_output}",
        current_value_state=_signed(current),
        help_text=f"Uses {source_label} value when no fresh physical sample is present.",
        status="mapped",
        route_type="axis",
        table_object_name="axisRoutingTable",
        route_row=row,
        editable=True,
    )


def _button_control(
    button_name: str,
    route_info: tuple[int, ButtonMapping] | None,
    *,
    button_states: Mapping[str, bool] | None,
    source_label: str,
) -> HotasDiagramControl:
    button_index = int(button_name.removeprefix("B"))
    anchor_x, anchor_y = _BUTTON_LAYOUT[button_index]
    route = route_info[1] if route_info is not None else None
    row = route_info[0] if route_info is not None else None
    pressed = bool(button_states.get(button_name, route.raw_state if route else False)) if button_states is not None else bool(route.raw_state if route else False)

    if route is None:
        return HotasDiagramControl(
            control_id=f"button_b{button_index}",
            display_label=button_name,
            control_type="button",
            anchor_x=anchor_x,
            anchor_y=anchor_y,
            region_width=0.075,
            region_height=0.08,
            raw_input_channel=button_name,
            mapped_function="Unmapped",
            output_intent_target="Output intent: unmapped",
            current_value_state="Pressed" if pressed else "Idle",
            help_text=f"{button_name} has no workspace button route.",
            status="unmapped",
            warning="No button route is available in the workspace.",
            route_type="button",
        )

    return HotasDiagramControl(
        control_id=f"button_b{button_index}",
        display_label=button_name,
        control_type="button",
        anchor_x=anchor_x,
        anchor_y=anchor_y,
        region_width=0.075,
        region_height=0.08,
        raw_input_channel=f"B{route.hotas_button}",
        mapped_function=f"Virtual button {route.output_button}",
        output_intent_target=f"Output intent: Button {route.output_button}",
        current_value_state="Pressed" if pressed else "Idle",
        help_text=f"Uses {source_label} state when no fresh physical sample is present.",
        status="mapped",
        route_type="button",
        table_object_name="buttonRoutingTable",
        route_row=row,
        editable=True,
    )


def _hat_control(
    route_info: tuple[int, HatMapping] | None,
    *,
    hat_state: str | None,
    source_label: str,
) -> HotasDiagramControl:
    route = route_info[1] if route_info is not None else None
    row = route_info[0] if route_info is not None else None
    current = hat_state or route.live_hat_state if route is not None else HAT_CENTERED
    if route is None:
        return HotasDiagramControl(
            control_id="hat_pov",
            display_label="Hat / POV",
            control_type="hat",
            anchor_x=0.72,
            anchor_y=0.16,
            region_width=0.12,
            region_height=0.10,
            raw_input_channel="Hat unavailable",
            mapped_function="Unmapped",
            output_intent_target="Output intent: unmapped",
            current_value_state=current,
            help_text="No workspace hat route is available.",
            status="unmapped",
            warning="No hat route is available in the workspace.",
            route_type="hat",
        )

    return HotasDiagramControl(
        control_id="hat_pov",
        display_label="Hat / POV",
        control_type="hat",
        anchor_x=0.72,
        anchor_y=0.16,
        region_width=0.12,
        region_height=0.10,
        raw_input_channel=f"Hat {route.hotas_hat}",
        mapped_function=f"POV {route.vjoy_pov}",
        output_intent_target=f"Output intent: POV {route.vjoy_pov}{_hat_button_suffix(route)}",
        current_value_state=f"{current} ({source_label})",
        help_text="Hat direction is displayed as visual intent only.",
        status="mapped",
        route_type="hat",
        table_object_name="hatRoutingTable",
        route_row=row,
        editable=True,
    )


def _duplicate_axis_output_warnings(workspace: WorkspaceConfig) -> tuple[HotasRouteWarning, ...]:
    by_output: dict[str, list[AxisMapping]] = {}
    for route in workspace.mappings.axis_routes:
        target = route.runtime_vjoy_output.strip()
        if target:
            by_output.setdefault(target, []).append(route)

    warnings: list[HotasRouteWarning] = []
    for target, routes in by_output.items():
        if len(routes) < 2:
            continue
        labels = ", ".join(route.function_name for route in routes)
        for route in routes:
            warnings.append(
                HotasRouteWarning(
                    code="duplicate_output_intent",
                    severity="warning",
                    control_id=_axis_control_id(route.function_name),
                    route_type="axis",
                    message=(
                        f"workspace/config warning: {labels} share output intent {target}."
                    ),
                )
            )
    return tuple(warnings)


def _duplicate_button_output_warnings(workspace: WorkspaceConfig) -> tuple[HotasRouteWarning, ...]:
    by_output: dict[int, list[ButtonMapping]] = {}
    for route in workspace.mappings.button_routes:
        if route.output_button > 0:
            by_output.setdefault(route.output_button, []).append(route)

    warnings: list[HotasRouteWarning] = []
    for target, routes in by_output.items():
        if len(routes) < 2:
            continue
        labels = ", ".join(f"B{route.hotas_button}" for route in routes)
        for route in routes:
            warnings.append(
                HotasRouteWarning(
                    code="duplicate_output_intent",
                    severity="warning",
                    control_id=f"button_b{route.hotas_button}",
                    route_type="button",
                    message=(
                        f"workspace/config warning: {labels} share output intent Button {target}."
                    ),
                )
            )
    return tuple(warnings)


def _missing_or_invalid_axis_warnings(workspace: WorkspaceConfig) -> tuple[HotasRouteWarning, ...]:
    warnings: list[HotasRouteWarning] = []
    by_name = {route.function_name: route for route in workspace.mappings.axis_routes}
    for axis_name in AXIS_NAMES:
        route = by_name.get(axis_name)
        control_id = _axis_control_id(axis_name)
        if route is None:
            warnings.append(
                HotasRouteWarning(
                    code="unmapped_important_control",
                    severity="warning",
                    control_id=control_id,
                    route_type="axis",
                    message=f"workspace/config warning: {axis_name} has no mapping route.",
                )
            )
            continue
        if not route.runtime_vjoy_output.strip():
            warnings.append(
                HotasRouteWarning(
                    code="missing_output_target",
                    severity="warning",
                    control_id=control_id,
                    route_type="axis",
                    message=f"workspace/config warning: {axis_name} has no output intent target.",
                )
            )
        if not route.raw_axis_channel.startswith("Axis "):
            warnings.append(
                HotasRouteWarning(
                    code="invalid_route_shape",
                    severity="warning",
                    control_id=control_id,
                    route_type="axis",
                    message=f"workspace/config warning: {axis_name} raw input shape is not supported.",
                )
            )
    for route in workspace.mappings.axis_routes:
        if route.function_name not in AXIS_NAMES:
            warnings.append(
                HotasRouteWarning(
                    code="unsupported_route_type",
                    severity="warning",
                    control_id=_axis_control_id(route.function_name),
                    route_type="axis",
                    message=(
                        f"workspace/config warning: {route.function_name} is outside the supported diagram controls."
                    ),
                )
            )
    return tuple(warnings)


def _missing_or_invalid_button_warnings(workspace: WorkspaceConfig) -> tuple[HotasRouteWarning, ...]:
    warnings: list[HotasRouteWarning] = []
    by_button = {route.hotas_button: route for route in workspace.mappings.button_routes}
    for index in range(1, 16):
        if index not in by_button:
            warnings.append(
                HotasRouteWarning(
                    code="unmapped_important_control",
                    severity="warning",
                    control_id=f"button_b{index}",
                    route_type="button",
                    message=f"workspace/config warning: B{index} has no button route.",
                )
            )
    for route in workspace.mappings.button_routes:
        if not 1 <= route.hotas_button <= 15 or not 1 <= route.output_button <= 20:
            warnings.append(
                HotasRouteWarning(
                    code="invalid_route_shape",
                    severity="warning",
                    control_id=f"button_b{route.hotas_button}",
                    route_type="button",
                    message=(
                        f"workspace/config warning: B{route.hotas_button} route shape is outside supported button ranges."
                    ),
                )
            )
    return tuple(warnings)


def _missing_or_invalid_hat_warnings(workspace: WorkspaceConfig) -> tuple[HotasRouteWarning, ...]:
    warnings: list[HotasRouteWarning] = []
    if not workspace.mappings.hat_routes:
        return (
            HotasRouteWarning(
                code="unmapped_important_control",
                severity="warning",
                control_id="hat_pov",
                route_type="hat",
                message="workspace/config warning: Hat / POV has no route.",
            ),
        )
    for route in workspace.mappings.hat_routes:
        if route.hotas_hat < 1 or route.vjoy_pov < 1:
            warnings.append(
                HotasRouteWarning(
                    code="invalid_route_shape",
                    severity="warning",
                    control_id="hat_pov",
                    route_type="hat",
                    message="workspace/config warning: Hat / POV route shape is outside supported ranges.",
                )
            )
    return tuple(warnings)


def _axis_control_id(axis_name: str) -> str:
    if axis_name in _AXIS_LAYOUT:
        return _AXIS_LAYOUT[axis_name][0]
    return "axis_" + axis_name.casefold().replace(" ", "_").replace("/", "_")


def _hat_button_suffix(route: HatMapping) -> str:
    pairs = (
        ("Up", route.up_button),
        ("Right", route.right_button),
        ("Down", route.down_button),
        ("Left", route.left_button),
    )
    mapped = [f"{label} {button}" for label, button in pairs if button is not None]
    if not mapped:
        return ""
    return " + " + ", ".join(mapped)


def _signed(value: float) -> str:
    return f"{value:+.2f}"
