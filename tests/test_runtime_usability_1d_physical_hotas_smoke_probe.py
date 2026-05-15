from __future__ import annotations

import json
from pathlib import Path

from scripts.runtime_physical_hotas_smoke_probe import (
    LiveProgressReporter,
    ProbeSample,
    StepResult,
    build_game_readiness_checklist,
    build_mapping_variant_workspace,
    build_summary_payload,
    run_axis_step,
    run_button_step,
    run_hat_step,
    runtime_authority_violations,
)
from shared_core.models.workspace import create_default_workspace
from shared_core.runtime.vjoy_output import build_workspace_virtual_output_intent


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _sample(
    timestamp: float,
    *,
    raw_axes: dict[str, float] | None = None,
    final_axes: dict[str, float] | None = None,
    output_axes: dict[str, float] | None = None,
    buttons: dict[str, bool] | None = None,
    output_buttons: dict[str, bool] | None = None,
    hat_state: str = "Centered",
    output_hats: dict[str, str] | None = None,
    write_axes: dict[str, float] | None = None,
    write_buttons: dict[str, bool] | None = None,
) -> ProbeSample:
    return ProbeSample(
        timestamp=timestamp,
        raw_axes={"Roll": 0.0, "Pitch": 0.0, "Throttle": 0.0, "Yaw": 0.0, "Aux 1": 0.0, "Aux 2": 0.0} | (raw_axes or {}),
        final_axes={"Roll": 0.0, "Pitch": 0.0, "Throttle": 0.0, "Yaw": 0.0, "Aux 1": 0.0, "Aux 2": 0.0} | (final_axes or {}),
        output_axes={"X": 0.0, "Y": 0.0, "Z": 0.0, "RX": 0.0, "RY": 0.0, "RZ": 0.0} | (output_axes or {}),
        buttons={f"B{index}": False for index in range(1, 16)} | (buttons or {}),
        output_buttons={f"Out{index}": False for index in range(1, 21)} | (output_buttons or {}),
        hat_state=hat_state,
        output_hats={"POV1": hat_state} | (output_hats or {}),
        write_axes={"X": 0.0, "Y": 0.0, "Z": 0.0, "RX": 0.0, "RY": 0.0, "RZ": 0.0} | (write_axes or output_axes or {}),
        write_buttons={f"Out{index}": False for index in range(1, 21)} | (write_buttons or output_buttons or {}),
        stage_values={},
        active_modes=(),
        active_rules=(),
        rebuild_count=1,
        input_source="physical",
    )


def test_axis_step_detects_change_then_collects_settle_window():
    samples = [
        _sample(0.0),
        _sample(0.5, raw_axes={"Roll": 0.10}, final_axes={"Roll": 0.10}, output_axes={"X": 0.10}, write_axes={"X": 0.10}),
        _sample(1.0, raw_axes={"Roll": 0.18}, final_axes={"Roll": 0.18}, output_axes={"X": 0.18}, write_axes={"X": 0.18}),
        _sample(2.7, raw_axes={"Roll": 0.22}, final_axes={"Roll": 0.22}, output_axes={"X": 0.22}, write_axes={"X": 0.22}),
    ]

    result = run_axis_step(samples, axis_name="Roll", output_axis="X", threshold=0.08, timeout_sec=60.0, settle_sec=2.0)

    assert result.status == "passed"
    assert result.baseline_value == 0.0
    assert result.changed_value == 0.10
    assert result.final_value == 0.22
    assert result.output_target == "X"
    assert result.output_value == 0.22
    assert result.writer_value == 0.22
    assert result.settle_sample_count == 3


def test_axis_step_times_out_after_60_seconds_without_change():
    samples = [_sample(0.0), _sample(30.0), _sample(60.0)]

    result = run_axis_step(samples, axis_name="Roll", output_axis="X", threshold=0.08, timeout_sec=60.0, settle_sec=2.0)

    assert result.status == "timeout"
    assert result.timeout is True
    assert result.detected is False
    assert "not observed within 60.0 seconds" in result.message


def test_live_progress_reporter_writes_current_step_and_completed_result(tmp_path):
    reporter = LiveProgressReporter(tmp_path)

    reporter.start_step(
        step_type="axis",
        name="Aux 2",
        instruction="Move Aux 2 now, if present.",
        index=6,
        total=6,
    )

    current = json.loads((tmp_path / "current-step.json").read_text(encoding="utf-8"))
    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert current["name"] == "Aux 2"
    assert current["status"] == "waiting"
    assert progress["status"] == "running"
    assert progress["current_step"]["instruction"] == "Move Aux 2 now, if present."

    result = StepResult("axis", "Aux 2", "timeout", "Aux 2 was not observed.", timeout=True)
    reporter.finish_step(result)
    reporter.finish_probe({"overall_status": "failed"})

    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    log_text = (tmp_path / "progress.log").read_text(encoding="utf-8")
    assert progress["status"] == "failed"
    assert progress["current_step"] is None
    assert progress["completed_steps"][0]["name"] == "Aux 2"
    assert '"event": "step_started"' in log_text
    assert '"event": "step_finished"' in log_text


def test_button_step_detects_press_and_release():
    samples = [
        _sample(0.0),
        _sample(1.0, buttons={"B1": True}, output_buttons={"Out1": True}, write_buttons={"Out1": True}),
        _sample(3.2, buttons={"B1": True}, output_buttons={"Out1": True}, write_buttons={"Out1": True}),
        _sample(3.5),
    ]

    result = run_button_step(samples, button_name="B1", output_button="Out1", timeout_sec=60.0, settle_sec=2.0)

    assert result.status == "passed"
    assert result.press_observed is True
    assert result.release_observed is True
    assert result.output_true_observed is True
    assert result.output_false_observed is True
    assert result.writer_true_observed is True
    assert result.writer_false_observed is True


def test_button_step_reports_release_timeout():
    samples = [
        _sample(0.0),
        _sample(1.0, buttons={"B2": True}, output_buttons={"Out2": True}, write_buttons={"Out2": True}),
        _sample(63.5, buttons={"B2": True}, output_buttons={"Out2": True}, write_buttons={"Out2": True}),
    ]

    result = run_button_step(samples, button_name="B2", output_button="Out2", timeout_sec=60.0, settle_sec=2.0)

    assert result.status == "timeout"
    assert result.press_observed is True
    assert result.release_observed is False
    assert "release was not observed" in result.message


def test_hat_step_detects_cardinal_direction_and_neutral():
    up = [
        _sample(0.0),
        _sample(0.5, hat_state="Up", output_hats={"POV1": "Up"}, output_buttons={"Out9": True}, write_buttons={"Out9": True}),
        _sample(2.7, hat_state="Up", output_hats={"POV1": "Up"}, output_buttons={"Out9": True}, write_buttons={"Out9": True}),
    ]
    neutral = [
        _sample(0.0, hat_state="Up", output_hats={"POV1": "Up"}, output_buttons={"Out9": True}),
        _sample(0.4, hat_state="Centered", output_hats={"POV1": "Centered"}),
        _sample(2.5, hat_state="Centered", output_hats={"POV1": "Centered"}),
    ]

    up_result = run_hat_step(up, expected_hat="Up", mapped_buttons=("Out9",), timeout_sec=60.0, settle_sec=2.0)
    neutral_result = run_hat_step(neutral, expected_hat="Centered", mapped_buttons=(), timeout_sec=60.0, settle_sec=2.0)

    assert up_result.status == "passed"
    assert up_result.output_hat == "Up"
    assert up_result.mapped_buttons_true == ("Out9",)
    assert neutral_result.status == "passed"
    assert neutral_result.output_hat == "Centered"
    assert neutral_result.mapped_buttons_true == ()


def test_hat_diagonal_policy_reports_or_decomposes_correctly():
    samples = [
        _sample(0.0),
        _sample(0.3, hat_state="UpRight", output_hats={"POV1": "UpRight"}, output_buttons={"Out9": True, "Out10": True}),
        _sample(2.6, hat_state="UpRight", output_hats={"POV1": "UpRight"}, output_buttons={"Out9": True, "Out10": True}),
    ]

    result = run_hat_step(samples, expected_hat="UpRight", mapped_buttons=("Out9", "Out10"), timeout_sec=60.0, settle_sec=2.0)

    assert result.status == "passed"
    assert result.diagonal_policy == "decompose_to_cardinal_buttons"
    assert set(result.mapped_buttons_true) == {"Out9", "Out10"}


def test_physical_pov_direction_words_drive_runtime_hat_output_and_buttons():
    workspace = create_default_workspace()

    north = build_workspace_virtual_output_intent(_sample(0.0).final_axes, workspace=workspace, hat_state="North")
    east = build_workspace_virtual_output_intent(_sample(0.0).final_axes, workspace=workspace, hat_state="East")

    assert next(hat.value for hat in north.hats if hat.hat_name == "POV1") == "Up"
    assert next(button.pressed for button in north.buttons if button.button_name == "Out7") is True
    assert next(hat.value for hat in east.hats if hat.hat_name == "POV1") == "Right"
    assert next(button.pressed for button in east.buttons if button.button_name == "Out18") is True


def test_mapping_variant_routes_physical_roll_to_swapped_output_target_in_simulated_probe():
    workspace = build_mapping_variant_workspace(create_default_workspace())
    roll_route = next(route for route in workspace.mappings.axis_routes if route.function_name == "Roll")
    samples = [
        _sample(0.0),
        _sample(0.4, raw_axes={"Roll": 0.2}, final_axes={"Roll": 0.2}, output_axes={"Y": 0.2}, write_axes={"Y": 0.2}),
        _sample(2.5, raw_axes={"Roll": 0.3}, final_axes={"Roll": 0.3}, output_axes={"Y": 0.3}, write_axes={"Y": 0.3}),
    ]

    result = run_axis_step(samples, axis_name="Roll", output_axis="Y", threshold=0.08, timeout_sec=60.0, settle_sec=2.0)

    assert roll_route.runtime_vjoy_output == "Y(axis2)"
    assert result.status == "passed"
    assert result.output_target == "Y"
    assert result.output_value == 0.3


def test_probe_report_separates_physical_proof_vjoy_write_call_and_readback():
    payload = build_summary_payload(
        physical_detected=True,
        hotas_vid_pid="VID_044F&PID_B68D",
        vjoy_detected=True,
        vjoy_write_call_status="passed",
        step_results=[],
        artifact_dir=Path("artifacts/runtime-physical-hotas-smoke/example"),
    )

    assert payload["hardware"]["physical_hotas_proof"] == "detected"
    assert payload["hardware"]["vjoy_write_call_proof"] == "passed"
    assert payload["hardware"]["vjoy_readback"] == "not_implemented"
    assert payload["truth_boundaries"]["game_level_verification"] == "manual_checklist_only"


def test_probe_does_not_import_ui_pages_as_runtime_calculation_authority():
    assert runtime_authority_violations(PROJECT_ROOT) == []


def test_game_readiness_checklist_marks_device_filtering_out_of_scope():
    checklist = build_game_readiness_checklist(
        physical_detected=True,
        vjoy_detected=True,
        vjoy_write_calls_accepted=True,
        game_level_verified=False,
    )

    assert "Direct physical HOTAS hiding/filtering is intentionally out of scope for Runtime Usability 1D." in checklist
    assert "bind controls from vJoy Device 1" in checklist
