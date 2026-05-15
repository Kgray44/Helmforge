from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

import pytest


AXES = ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
BUTTONS = tuple(range(1, 16))
RAW_LAYOUT = (
    ("X", "Roll", False),
    ("Y", "Pitch", False),
    ("Z", "Throttle", True),
    ("R", "Yaw", False),
    ("U", "Aux 1", False),
    ("V", "Aux 2", False),
)


class ProbeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance_ms(self, milliseconds: int) -> None:
        self.now += timedelta(milliseconds=milliseconds)


def test_runtime_usability_1a_stable_samples_do_not_rebuild_or_reset_pipeline_state(tmp_path):
    from shared_core.math.pipeline import WorkspaceSignalPipeline
    from shared_core.models.workspace import create_default_workspace

    workspace = create_default_workspace()
    clock = ProbeClock()
    inputs = [
        _axis_values(roll=0.62, pitch=-0.28),
        _axis_values(roll=0.74, pitch=-0.12),
        _axis_values(roll=0.36, pitch=0.18),
        _axis_values(roll=-0.44, pitch=0.31),
    ]
    service = _service(tmp_path, workspace=workspace, inputs=inputs, clock=clock, tick_ms=40)

    expected_pipeline = WorkspaceSignalPipeline(workspace)
    expected_state = expected_pipeline.initial_state()
    frames = []
    try:
        for values in inputs:
            telemetry = service.run_once(publish_telemetry=False)
            expected = expected_pipeline.process(dict(telemetry.raw_axes.values), state=expected_state)
            expected_state = expected.state
            frames.append(telemetry.runtime_frame)
            for axis in AXES:
                assert telemetry.final_axes.values[axis] == pytest.approx(expected.final_output_values[axis], abs=1e-5)
            clock.advance_ms(40)
    finally:
        service.shutdown()

    assert service.timing.runtime_orchestrator_rebuild_count == 1
    assert frames[-1]["runtime_orchestrator_rebuild_count"] == 1
    assert frames[-1]["runtime_orchestrator_rebuild_reason"] == "startup"


def test_runtime_usability_1a_workspace_config_change_triggers_one_controlled_state_reset(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from shared_core.persistence.workspace_store import save_workspace

    workspace = create_default_workspace()
    config_path = tmp_path / "hotas_bridge_config_v3.json"
    save_workspace(workspace, config_path, overwrite=True)
    clock = ProbeClock()
    service = _service(
        tmp_path,
        workspace=workspace,
        config_path=config_path,
        inputs=[_axis_values(roll=0.5), _axis_values(roll=0.6), _axis_values(roll=0.7)],
        clock=clock,
        tick_ms=40,
    )

    try:
        service.run_once(publish_telemetry=False)
        assert service.timing.runtime_orchestrator_rebuild_count == 1

        swapped = _swapped_roll_pitch_workspace(workspace)
        save_workspace(swapped, config_path, overwrite=True)
        service.reload_config(config_path)
        telemetry = service.run_once(publish_telemetry=False)
    finally:
        service.shutdown()

    assert service.timing.runtime_orchestrator_rebuild_count == 2
    assert telemetry.runtime_frame["runtime_orchestrator_rebuild_reason"] == "workspace_config_changed"


def test_runtime_usability_1a_default_and_swapped_axis_mapping_drive_output_intent():
    from shared_core.models.workspace import create_default_workspace
    from shared_core.runtime.runtime_orchestrator import RuntimeFrameSource, RuntimeOrchestrator, RuntimeOrchestratorConfig

    workspace = create_default_workspace()
    swapped = _swapped_roll_pitch_workspace(workspace)
    raw = _raw_axes(_axis_values(roll=0.42, pitch=-0.37, throttle=0.68, yaw=-0.52, aux1=0.27, aux2=-0.14))

    default_frame = RuntimeOrchestrator(
        workspace=workspace,
        config=RuntimeOrchestratorConfig(preferred_input_source=RuntimeFrameSource.SIMULATION),
    ).build_frame_from_runtime_snapshot(_runtime_snapshot(raw))
    swapped_frame = RuntimeOrchestrator(
        workspace=swapped,
        config=RuntimeOrchestratorConfig(preferred_input_source=RuntimeFrameSource.SIMULATION),
    ).build_frame_from_runtime_snapshot(_runtime_snapshot(raw))

    assert default_frame.output_intent.axis_value("X") == pytest.approx(default_frame.pipeline.final_output_values["Roll"])
    assert default_frame.output_intent.axis_value("Y") == pytest.approx(default_frame.pipeline.final_output_values["Pitch"])
    assert swapped_frame.output_intent.axis_value("Y") == pytest.approx(swapped_frame.pipeline.final_output_values["Roll"])
    assert swapped_frame.output_intent.axis_value("X") == pytest.approx(swapped_frame.pipeline.final_output_values["Pitch"])
    assert swapped_frame.output_intent.axis_value("Z") == pytest.approx(swapped_frame.pipeline.final_output_values["Throttle"])
    assert swapped_frame.pipeline.final_output_values["Roll"] != pytest.approx(swapped_frame.output_intent.axis_value("X"))


def test_runtime_usability_1a_button_mapping_drives_intent_press_and_release():
    from shared_core.models.workspace import create_default_workspace
    from shared_core.runtime.runtime_orchestrator import RuntimeOrchestrator

    workspace = create_default_workspace()
    swapped = _swapped_roll_pitch_workspace(workspace)

    for button in BUTTONS:
        pressed = RuntimeOrchestrator(workspace=workspace).build_frame_from_runtime_snapshot(
            _runtime_snapshot(_raw_axes(_axis_values()), buttons={button: True})
        )
        released = RuntimeOrchestrator(workspace=workspace).build_frame_from_runtime_snapshot(
            _runtime_snapshot(_raw_axes(_axis_values()), buttons={button: False})
        )
        assert _button_value(pressed.output_intent, f"Out{button}") is True
        assert _button_value(released.output_intent, f"Out{button}") is False
        assert all(_button_value(pressed.output_intent, f"Out{other}") is False for other in BUTTONS if other != button)

    b1_swapped = RuntimeOrchestrator(workspace=swapped).build_frame_from_runtime_snapshot(
        _runtime_snapshot(_raw_axes(_axis_values()), buttons={1: True})
    )
    b2_swapped = RuntimeOrchestrator(workspace=swapped).build_frame_from_runtime_snapshot(
        _runtime_snapshot(_raw_axes(_axis_values()), buttons={2: True})
    )
    assert _button_value(b1_swapped.output_intent, "Out2") is True
    assert _button_value(b1_swapped.output_intent, "Out1") is False
    assert _button_value(b2_swapped.output_intent, "Out1") is True
    assert _button_value(b2_swapped.output_intent, "Out2") is False


def test_runtime_usability_1a_fake_writer_records_mapped_axes_and_buttons(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from shared_core.persistence.workspace_store import save_workspace
    from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend

    workspace = _swapped_roll_pitch_workspace(create_default_workspace())
    config_path = tmp_path / "mapping-variant-workspace.json"
    save_workspace(workspace, config_path, overwrite=True)
    clock = ProbeClock()
    backend = FakeVirtualOutputBackend()
    inputs = [_axis_values(roll=0.5, pitch=-0.25, b1=True), _axis_values(roll=0.5, pitch=-0.25, b1=False)]
    service = _service(tmp_path, workspace=workspace, config_path=config_path, inputs=inputs, clock=clock, backend=backend, tick_ms=40)

    try:
        first = service.run_once(publish_telemetry=False)
        clock.advance_ms(40)
        second = service.run_once(publish_telemetry=False)
    finally:
        service.shutdown()

    writes = [intent for intent in backend.written_intents if intent.source.startswith("runtime_orchestrator")]
    first_write = writes[0]
    second_write = writes[1]
    assert first_write.axis_value("Y") == pytest.approx(first.runtime_frame["final_pipeline_axes"]["Roll"], abs=1e-6)
    assert first_write.axis_value("X") == pytest.approx(first.runtime_frame["final_pipeline_axes"]["Pitch"], abs=1e-6)
    assert _button_value(first_write, "Out2") is True
    assert _button_value(first_write, "Out1") is False
    assert _button_value(second_write, "Out2") is False
    assert second.runtime_frame["final_output_axes"]["Y"] == pytest.approx(second.runtime_frame["final_pipeline_axes"]["Roll"], abs=1e-6)


def test_runtime_usability_1a_stage_telemetry_comes_from_single_pipeline_pass(tmp_path, monkeypatch):
    import shared_core.runtime.runtime_orchestrator as runtime_orchestrator
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.math.pipeline import WorkspaceSignalPipeline
    from shared_core.math.stack import EXPECTED_STAGE_NAMES

    process_calls = 0

    class CountingPipeline(WorkspaceSignalPipeline):
        def process(self, *args, **kwargs):
            nonlocal process_calls
            process_calls += 1
            return super().process(*args, **kwargs)

    monkeypatch.setattr(runtime_orchestrator, "WorkspaceSignalPipeline", CountingPipeline)
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "telemetry.json",
            command_path=tmp_path / "command.json",
            simulate=True,
            enable_telemetry_stream=False,
        )
    )

    try:
        telemetry = service.run_once(publish_telemetry=False)
    finally:
        service.shutdown()

    roll_stages = telemetry.runtime_frame["axis_stage_values"]["Roll"]
    assert process_calls == 1
    assert [stage["stage_name"] for stage in roll_stages] == list(EXPECTED_STAGE_NAMES)
    assert roll_stages[-1]["output_value"] == pytest.approx(telemetry.final_axes.values["Roll"], abs=1e-6)


def _service(
    tmp_path: Path,
    *,
    workspace,
    inputs: list[Mapping[str, object]],
    clock: ProbeClock,
    config_path: Path | None = None,
    backend=None,
    tick_ms: int = 40,
):
    from bridge_app.service import BridgeService, BridgeServiceOptions
    from shared_core.persistence.workspace_store import save_workspace
    from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend

    path = config_path or tmp_path / "hotas_bridge_config_v3.json"
    if not path.exists():
        save_workspace(workspace, path, overwrite=True)
    frames = [_frame_from_values(inputs[0]), *(_frame_from_values(values) for values in inputs)]
    return BridgeService(
        BridgeServiceOptions(
            telemetry_path=tmp_path / "bridge_telemetry.json",
            command_path=tmp_path / "bridge_command.json",
            config_path=path,
            simulate=False,
            tick_interval_ms=tick_ms,
            discovery_refresh_interval_seconds=60.0,
            physical_input_backend=_fake_physical_backend(frames, clock),
            virtual_output_backend=backend or FakeVirtualOutputBackend(),
            enable_live_input=True,
            enable_output_verification=True,
            enable_output_loop=True,
            enable_telemetry_stream=False,
            clock=clock,
        )
    )


def _fake_physical_backend(frames: list[Mapping[str, object]], clock: ProbeClock):
    from shared_core.runtime.hotas_input import FakePhysicalInputBackend, build_physical_input_device_info

    return FakePhysicalInputBackend(
        (
            build_physical_input_device_info(
                device_id="truth-probe-hotas-one",
                display_name="Truth Probe Thrustmaster T.Flight HOTAS One",
                manufacturer="Thrustmaster",
                vendor_id="044f",
                product_id="b68d",
                axis_count=6,
                button_count=15,
                hat_count=1,
                backend_name="truth_probe_fake_physical",
            ),
        ),
        sample_frames=frames,
        clock=clock,
        sample_source="runtime_usability_1a",
    )


def _axis_values(
    *,
    roll: float = 0.0,
    pitch: float = 0.0,
    throttle: float = 0.5,
    yaw: float = 0.0,
    aux1: float = 0.0,
    aux2: float = 0.0,
    b1: bool = False,
) -> dict[str, object]:
    values: dict[str, object] = {
        "Roll": roll,
        "Pitch": pitch,
        "Throttle": throttle,
        "Yaw": yaw,
        "Aux 1": aux1,
        "Aux 2": aux2,
        **{f"B{button}": False for button in BUTTONS},
        "Hat 1": "Centered",
    }
    values["B1"] = b1
    return values


def _raw_axes(values: Mapping[str, object]) -> dict[str, float]:
    return {axis: float(values.get(axis, 0.0)) for axis in AXES}


def _frame_from_values(values: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "axes": tuple(
            {
                "raw_name": raw_name,
                "logical_name": logical_name,
                "raw_value": _raw_from_normalized(logical_name, float(values.get(logical_name, 0.0))),
                "raw_min": 0,
                "raw_max": 65535,
                "center": 32767.5,
                "one_sided": one_sided,
            }
            for raw_name, logical_name, one_sided in RAW_LAYOUT
        ),
        "buttons": {button: bool(values.get(f"B{button}", False)) for button in BUTTONS},
        "hats": {1: str(values.get("Hat 1", "Centered"))},
    }


def _runtime_snapshot(raw_axes: Mapping[str, float], *, buttons: Mapping[int, bool] | None = None):
    from shared_core.models.runtime import RuntimeSnapshot, simulation_fallback_status

    button_states = {f"B{button}": bool((buttons or {}).get(button, False)) for button in BUTTONS}
    return RuntimeSnapshot(
        raw_axis_values=dict(raw_axes),
        final_output_values=dict(raw_axes),
        button_states=button_states,
        hat_state="Centered",
        runtime_status=simulation_fallback_status(),
        simulated=True,
    )


def _swapped_roll_pitch_workspace(workspace):
    swapped_axes = []
    roll = next(route for route in workspace.mappings.axis_routes if route.function_name == "Roll")
    pitch = next(route for route in workspace.mappings.axis_routes if route.function_name == "Pitch")
    for route in workspace.mappings.axis_routes:
        if route.function_name == "Roll":
            swapped_axes.append(replace(route, logical_output=pitch.logical_output, runtime_vjoy_output=pitch.runtime_vjoy_output))
        elif route.function_name == "Pitch":
            swapped_axes.append(replace(route, logical_output=roll.logical_output, runtime_vjoy_output=roll.runtime_vjoy_output))
        else:
            swapped_axes.append(route)
    swapped_buttons = []
    for route in workspace.mappings.button_routes:
        if route.hotas_button == 1:
            swapped_buttons.append(replace(route, output_button=2))
        elif route.hotas_button == 2:
            swapped_buttons.append(replace(route, output_button=1))
        else:
            swapped_buttons.append(route)
    return replace(
        workspace,
        mappings=replace(
            workspace.mappings,
            axis_routes=tuple(swapped_axes),
            button_routes=tuple(swapped_buttons),
        ),
    )


def _button_value(intent, button_name: str) -> bool:
    return next((button.pressed for button in intent.buttons if button.button_name == button_name), False)


def _raw_from_normalized(axis: str, value: float) -> int:
    if axis == "Throttle":
        return int(round(max(0.0, min(1.0, value)) * 65535))
    return int(round(((max(-1.0, min(1.0, value)) + 1.0) / 2.0) * 65535))
