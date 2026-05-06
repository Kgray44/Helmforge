import json

import pytest

from shared_core.models.axes import AxisId, all_axis_definitions, axis_by_name
from shared_core.models.mappings import DEFAULT_BATTLEFIELD_ROUTING_NOTE
from shared_core.models.modes import StackMode
from shared_core.models.profiles import BUILT_IN_PROFILE_NAMES, CURRENT_WORKSPACE_PROFILE_NAME
from shared_core.models.rules import default_conditional_rules
from shared_core.models.workspace import (
    CONFIG_FILENAME,
    LEGACY_V2_CONFIG_FILENAME,
    SCHEMA_VERSION,
    create_default_workspace,
)
from shared_core.persistence.workspace_store import (
    WorkspaceJsonError,
    load_workspace,
    save_workspace,
)


def test_default_workspace_creates_all_six_recovered_axes():
    workspace = create_default_workspace()

    assert [axis.display_name for axis in all_axis_definitions()] == [
        "Roll",
        "Pitch",
        "Throttle",
        "Yaw",
        "Aux 1",
        "Aux 2",
    ]
    assert tuple(workspace.tuning.axes) == tuple(axis.value for axis in AxisId)
    assert axis_by_name("aux 1").axis_id is AxisId.AUX_1
    assert workspace.product_name == "HelmForge"
    assert workspace.technical_subtitle == "HOTAS Control Panel V3"
    assert workspace.target_hardware.primary_device_name == "Thrustmaster T-Flight HOTAS One"


def test_recovered_mapping_defaults_are_present():
    workspace = create_default_workspace()
    routes = {route.function_name: route for route in workspace.mappings.axis_routes}

    assert routes["Roll"].raw_axis_channel == "Axis 1"
    assert routes["Roll"].logical_output == "X"
    assert routes["Roll"].runtime_vjoy_output == "X(axis1)"
    assert routes["Pitch"].runtime_vjoy_output == "Y(axis2)"
    assert routes["Throttle"].runtime_vjoy_output == "Z(axis3)"
    assert routes["Yaw"].raw_axis_channel == "Axis 6"
    assert routes["Yaw"].logical_output == "RZ"
    assert routes["Yaw"].runtime_vjoy_output == "RX(axis4)"
    assert routes["Aux 1"].logical_output == "SL0"
    assert routes["Aux 1"].runtime_vjoy_output == "RY(axis5)"
    assert routes["Aux 2"].logical_output == "RX"
    assert routes["Aux 2"].runtime_vjoy_output == "RZ(axis6)"
    assert len(workspace.mappings.button_routes) == 15
    assert workspace.mappings.button_routes[0].hotas_button == 1
    assert workspace.mappings.button_routes[-1].output_button == 15
    assert len(workspace.mappings.hat_routes) == 1
    assert workspace.mappings.hat_routes[0].up_button == 7
    assert "Battlefield-safe runtime routing" in DEFAULT_BATTLEFIELD_ROUTING_NOTE


def test_mode_defaults_are_present():
    modes = create_default_workspace().modes

    assert modes.precision_hold_buttons == (0,)
    assert modes.combat_trigger_buttons == ()
    assert modes.combat_zoom_aim_buttons == (5,)
    assert modes.combat_extra_buttons == ()
    assert modes.precision_combat_stack_mode is StackMode.MULTIPLY


def test_default_profiles_include_recovered_names_and_current_workspace():
    profiles = create_default_workspace().profiles
    names = [profile.name for profile in profiles.profiles]

    assert BUILT_IN_PROFILE_NAMES == (
        "Balanced Flight",
        "Precision Tracking",
        "Aggressive Combat",
        "Smooth Cinematic",
    )
    assert all(name in names for name in BUILT_IN_PROFILE_NAMES)
    assert CURRENT_WORKSPACE_PROFILE_NAME in names
    assert profiles.active_profile_id == "current-workspace"


def test_conditional_example_rule_can_be_represented():
    rule = default_conditional_rules()[0]

    assert rule.title == "Yaw 0.75 | Roll > 0.35"
    assert rule.enabled is False
    assert rule.target_axis == "Yaw"
    assert rule.parameter == "Output Scale"
    assert rule.operation == "Set"
    assert rule.value == 0.75
    assert rule.injection_stage == "Base Output Limits"
    assert rule.mode_gate == "Always"
    assert rule.reference_axis == "Roll"
    assert rule.stage == "Final Output"
    assert rule.measure == "absolute"
    assert rule.comparator == "greater than"
    assert rule.threshold == 0.35


def test_workspace_json_round_trips_and_preserves_sections(tmp_path):
    path = tmp_path / CONFIG_FILENAME
    workspace = create_default_workspace()

    save_workspace(workspace, path)
    result = load_workspace(path)
    loaded = result.workspace

    assert result.status == "loaded"
    assert loaded.schema_version == SCHEMA_VERSION
    assert loaded.source_path == CONFIG_FILENAME
    assert loaded.legacy_source_note == f"Recovered V2 used {LEGACY_V2_CONFIG_FILENAME}."
    assert loaded.mappings.axis_routes[3].function_name == "Yaw"
    assert loaded.modes.precision_combat_stack_mode is StackMode.MULTIPLY
    assert loaded.rules.rules[0].title == "Yaw 0.75 | Roll > 0.35"
    assert loaded.profiles.active_profile_id == "current-workspace"


def test_save_workspace_refuses_silent_destructive_overwrite(tmp_path):
    path = tmp_path / CONFIG_FILENAME
    workspace = create_default_workspace()

    save_workspace(workspace, path)

    with pytest.raises(FileExistsError):
        save_workspace(workspace, path)


def test_missing_workspace_file_returns_safe_default(tmp_path):
    result = load_workspace(tmp_path / CONFIG_FILENAME)

    assert result.status == "missing_default"
    assert result.workspace.source_path == CONFIG_FILENAME
    assert result.error is None


def test_corrupt_json_reports_useful_error_without_destroying_data(tmp_path):
    path = tmp_path / CONFIG_FILENAME
    path.write_text("{ nope", encoding="utf-8")

    with pytest.raises(WorkspaceJsonError) as exc_info:
        load_workspace(path)

    assert "Invalid workspace JSON" in str(exc_info.value)
    assert path.read_text(encoding="utf-8") == "{ nope"


def test_serialized_workspace_uses_v3_config_name_and_schema(tmp_path):
    path = tmp_path / CONFIG_FILENAME
    save_workspace(create_default_workspace(), path)

    data = json.loads(path.read_text(encoding="utf-8"))

    assert CONFIG_FILENAME == "hotas_bridge_config_v3.json"
    assert LEGACY_V2_CONFIG_FILENAME == "hotas_bridge_config_v2.json"
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["source_path"] == CONFIG_FILENAME
