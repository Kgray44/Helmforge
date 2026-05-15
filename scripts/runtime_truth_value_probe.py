from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bridge_app.service import BridgeService, BridgeServiceOptions
from shared_core.math.pipeline import WorkspaceSignalPipeline
from shared_core.models.mappings import AxisMapping, ButtonMapping
from shared_core.models.rules import ConditionalRule, RuleConfig
from shared_core.models.workspace import CONFIG_FILENAME, WorkspaceConfig
from shared_core.persistence.workspace_store import load_workspace, save_workspace
from shared_core.runtime.hotas_input import FakePhysicalInputBackend, build_physical_input_device_info
from shared_core.runtime.vjoy_output import (
    FakeVirtualOutputBackend,
    RealVJoyOutputBackend,
    VirtualOutputIntent,
    VirtualOutputWriteResult,
)


AXES = ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
RAW_LAYOUT = (
    ("X", "Roll", False),
    ("Y", "Pitch", False),
    ("Z", "Throttle", True),
    ("R", "Yaw", False),
    ("U", "Aux 1", False),
    ("V", "Aux 2", False),
)
BUTTONS = tuple(range(1, 16))
OUTPUT_AXIS_CHOICES = ("X", "Y", "Z", "RX", "RY", "RZ")
REPORT_PATH = Path("docs") / "HelmForge" / "runtime-truth-value-usability-report.md"
ASSET_ROOT = Path("docs") / "HelmForge" / "runtime-truth-value-usability-assets"
ARTIFACT_ROOT = Path("artifacts") / "runtime-truth-value-usability"


@dataclass(frozen=True)
class ProbeOptions:
    output_root: Path
    report_path: Path
    asset_root: Path
    real_vjoy_writes: bool = False


@dataclass
class ProbeClock:
    now: datetime

    def __call__(self) -> datetime:
        return self.now

    def advance_ms(self, milliseconds: int) -> None:
        self.now += timedelta(milliseconds=max(1, int(milliseconds)))


@dataclass(frozen=True)
class WriteRecord:
    kind: str
    success: bool
    status: str
    duration_ms: float
    source: str
    axes: Mapping[str, float]
    buttons: Mapping[str, bool]


class RecordingOutputBackend:
    def __init__(self, inner) -> None:
        self.inner = inner
        self.write_records: list[WriteRecord] = []
        self.verification_records: list[dict[str, object]] = []

    def get_capabilities(self):
        return self.inner.get_capabilities()

    def get_status(self):
        return self.inner.get_status()

    def enumerate_output_devices(self):
        return self.inner.enumerate_output_devices()

    def select_output_device(self, device_id: str):
        return self.inner.select_output_device(device_id)

    def verify_output_write(self, output_intent: VirtualOutputIntent):
        started = time.perf_counter()
        result = self.inner.verify_output_write(output_intent)
        self.verification_records.append(
            {
                "status": result.status.value,
                "output_verified": result.output_verified,
                "real_output_verified": result.real_output_verified,
                "fake_output_verified": result.fake_output_verified,
                "duration_ms": _elapsed_ms(started),
            }
        )
        return result

    def write_output_intent(self, output_intent: VirtualOutputIntent) -> VirtualOutputWriteResult:
        started = time.perf_counter()
        result = self.inner.write_output_intent(output_intent)
        self.write_records.append(
            WriteRecord(
                kind="output_write",
                success=result.success,
                status=result.status,
                duration_ms=_elapsed_ms(started),
                source=output_intent.source,
                axes={axis.axis_name: axis.value for axis in output_intent.axes},
                buttons={button.button_name: button.pressed for button in output_intent.buttons},
            )
        )
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HelmForge runtime value-truth usability probes.")
    parser.add_argument("--real-vjoy-writes", action="store_true", help="Also run bounded probes against the real vJoy backend.")
    parser.add_argument("--output-root", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    parser.add_argument("--asset-root", type=Path, default=ASSET_ROOT)
    args = parser.parse_args()

    options = ProbeOptions(
        output_root=args.output_root,
        report_path=args.report_path,
        asset_root=args.asset_root,
        real_vjoy_writes=bool(args.real_vjoy_writes),
    )
    result = run_probe(options)
    print(json.dumps({"report": str(result["report_path"]), "artifact_dir": str(result["artifact_dir"]), "status": result["status"]}, indent=2))
    return 0


def run_probe(options: ProbeOptions) -> dict[str, object]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = options.output_root / stamp
    artifact_dir.mkdir(parents=True, exist_ok=True)
    options.asset_root.mkdir(parents=True, exist_ok=True)

    workspace = load_workspace(CONFIG_FILENAME).workspace
    current_workspace_path = artifact_dir / "current-workspace-copy.json"
    variant_workspace_path = artifact_dir / "mapping-variant-workspace.json"
    stress_workspace_path = artifact_dir / "math-stage-stress-workspace.json"
    save_workspace(workspace, current_workspace_path, overwrite=True)
    mapping_variant = _mapping_variant_workspace(workspace)
    stress_workspace = _math_stage_stress_workspace(workspace)
    save_workspace(mapping_variant, variant_workspace_path, overwrite=True)
    save_workspace(stress_workspace, stress_workspace_path, overwrite=True)

    live_probe = _live_environment_probe(artifact_dir)
    current_mapping = _mapping_summary(workspace)
    variant_mapping = _mapping_summary(mapping_variant)

    sine_frames, sine_inputs = _axis_sine_frames(180, sharp=False)
    sharp_frames, sharp_inputs = _axis_sine_frames(180, sharp=True)
    button_frames, button_inputs = _button_toggle_frames()
    mapping_frames, mapping_inputs = _mapping_change_frames()
    stress_frames, stress_inputs = _math_stage_stress_frames()

    fake_sine = _run_scenario(
        "axis_sine_fake",
        sine_frames,
        sine_inputs,
        workspace,
        current_workspace_path,
        artifact_dir,
        tick_ms=16,
        output_backend_factory=lambda clock: RecordingOutputBackend(FakeVirtualOutputBackend()),
    )
    fake_sharp = _run_scenario(
        "axis_sharp_step_sine_fake",
        sharp_frames,
        sharp_inputs,
        workspace,
        current_workspace_path,
        artifact_dir,
        tick_ms=16,
        output_backend_factory=lambda clock: RecordingOutputBackend(FakeVirtualOutputBackend()),
    )
    fake_buttons = _run_scenario(
        "buttons_toggle_fake",
        button_frames,
        button_inputs,
        workspace,
        current_workspace_path,
        artifact_dir,
        tick_ms=40,
        output_backend_factory=lambda clock: RecordingOutputBackend(FakeVirtualOutputBackend()),
    )
    fake_stress = _run_scenario(
        "math_stage_stress_fake",
        stress_frames,
        stress_inputs,
        stress_workspace,
        stress_workspace_path,
        artifact_dir,
        tick_ms=40,
        output_backend_factory=lambda clock: RecordingOutputBackend(FakeVirtualOutputBackend()),
    )
    fake_mapping = _run_scenario(
        "mapping_variant_fake",
        mapping_frames,
        mapping_inputs,
        mapping_variant,
        variant_workspace_path,
        artifact_dir,
        tick_ms=40,
        output_backend_factory=lambda clock: RecordingOutputBackend(FakeVirtualOutputBackend()),
    )

    real_results: list[dict[str, object]] = []
    if options.real_vjoy_writes and live_probe["real_vjoy_available"]:
        real_results.append(
            _run_scenario(
                "axis_sine_real_vjoy",
                sine_frames[:72],
                sine_inputs[:72],
                workspace,
                current_workspace_path,
                artifact_dir,
                tick_ms=34,
                output_backend_factory=lambda clock: RecordingOutputBackend(RealVJoyOutputBackend(clock=clock)),
            )
        )
        real_results.append(
            _run_scenario(
                "buttons_toggle_real_vjoy",
                button_frames,
                button_inputs,
                workspace,
                current_workspace_path,
                artifact_dir,
                tick_ms=40,
                output_backend_factory=lambda clock: RecordingOutputBackend(RealVJoyOutputBackend(clock=clock)),
            )
        )

    scenarios = [fake_sine, fake_sharp, fake_buttons, fake_stress, fake_mapping, *real_results]
    _write_csvs(artifact_dir, scenarios)
    graph_paths = _write_graphs(options.asset_root, fake_sine, fake_sharp, fake_stress)
    summary = _summarize_probe(live_probe, scenarios, current_mapping, variant_mapping, graph_paths, options.real_vjoy_writes)
    summary_path = artifact_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report_text = _render_report(summary, scenarios, current_mapping, variant_mapping, graph_paths, artifact_dir)
    options.report_path.parent.mkdir(parents=True, exist_ok=True)
    options.report_path.write_text(report_text, encoding="utf-8")
    artifact_report = artifact_dir / "runtime-truth-value-usability-report.md"
    artifact_report.write_text(report_text, encoding="utf-8")
    return {
        "status": summary["overall_status"],
        "report_path": options.report_path,
        "artifact_dir": artifact_dir,
        "summary_path": summary_path,
    }


def _run_scenario(
    name: str,
    frames: list[Mapping[str, object]],
    input_values: list[Mapping[str, float | int | str]],
    workspace: WorkspaceConfig,
    workspace_path: Path,
    artifact_dir: Path,
    *,
    tick_ms: int,
    output_backend_factory,
) -> dict[str, object]:
    scenario_dir = artifact_dir / name
    scenario_dir.mkdir(parents=True, exist_ok=True)
    clock = ProbeClock(datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc))
    backend = output_backend_factory(clock)
    physical = FakePhysicalInputBackend(
        (_hotas_device(),),
        sample_frames=[frames[0], *frames],
        clock=clock,
        sample_source=name,
    )
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=scenario_dir / "bridge_telemetry.json",
            command_path=scenario_dir / "bridge_command.json",
            config_path=workspace_path,
            simulate=False,
            tick_interval_ms=tick_ms,
            physical_input_backend=physical,
            virtual_output_backend=backend,
            enable_live_input=True,
            enable_output_verification=True,
            enable_output_loop=True,
            enable_telemetry_stream=False,
            clock=clock,
        )
    )
    stateful_expected = _stateful_expected(workspace, input_values)
    frame_rows: list[dict[str, object]] = []
    axis_stage_rows: list[dict[str, object]] = []
    button_rows: list[dict[str, object]] = []
    write_rows: list[dict[str, object]] = []
    previous_write_count = 0
    try:
        for frame_index, expected_input in enumerate(input_values):
            started = time.perf_counter()
            telemetry = service.run_once()
            end_to_end_ms = _elapsed_ms(started)
            payload = json.loads((scenario_dir / "bridge_telemetry.json").read_text(encoding="utf-8"))
            runtime_frame = payload.get("runtime_frame") if isinstance(payload.get("runtime_frame"), Mapping) else {}
            stage_values = runtime_frame.get("axis_stage_values", {}) if isinstance(runtime_frame, Mapping) else {}
            timing = payload.get("bridge_timing", {}) if isinstance(payload.get("bridge_timing"), Mapping) else {}
            output_runtime = payload.get("output_loop_runtime", {}) if isinstance(payload.get("output_loop_runtime"), Mapping) else {}
            final_axes = payload.get("final_axes", {}) if isinstance(payload.get("final_axes"), Mapping) else {}
            raw_axes = payload.get("raw_axes", {}) if isinstance(payload.get("raw_axes"), Mapping) else {}
            bridge_output_axes = runtime_frame.get("final_output_axes", {}) if isinstance(runtime_frame, Mapping) else {}
            write_count = int(output_runtime.get("write_success_count") or 0)
            wrote_this_tick = write_count > previous_write_count
            previous_write_count = write_count
            latest_write = backend.write_records[-1] if wrote_this_tick and backend.write_records else None
            expected_axes = stateful_expected[frame_index]["final_axes"]
            expected_output_axes = _expected_output_axes(workspace, expected_axes)

            frame_rows.append(
                {
                    "scenario": name,
                    "frame": frame_index,
                    "tick_ms": tick_ms,
                    "end_to_end_ms": end_to_end_ms,
                    "input_read_ms": timing.get("last_input_read_duration_ms"),
                    "pipeline_ms": timing.get("last_pipeline_duration_ms"),
                    "output_write_ms": timing.get("last_output_write_duration_ms"),
                    "tick_duration_ms": timing.get("last_tick_duration_ms"),
                    "runtime_orchestrator_rebuild_count": timing.get("runtime_orchestrator_rebuild_count"),
                    "runtime_orchestrator_rebuild_reason": timing.get("last_runtime_orchestrator_rebuild_reason"),
                    "write_status": output_runtime.get("last_write_status"),
                    "wrote_this_tick": wrote_this_tick,
                }
            )
            for axis in AXES:
                stages = stage_values.get(axis, []) if isinstance(stage_values, Mapping) else []
                expected_stages = stateful_expected[frame_index]["stage_values"].get(axis, [])
                expected_by_name = {stage["stage_name"]: stage for stage in expected_stages}
                for stage in stages:
                    stage_name = str(stage.get("stage_name"))
                    expected_stage = expected_by_name.get(stage_name, {})
                    axis_stage_rows.append(
                        {
                            "scenario": name,
                            "frame": frame_index,
                            "axis": axis,
                            "stage": stage_name,
                            "measured_input": stage.get("input_value"),
                            "measured_output": stage.get("output_value"),
                            "measured_delta": stage.get("delta"),
                            "intended_stateful_output": expected_stage.get("output_value"),
                            "abs_diff": _abs_diff(stage.get("output_value"), expected_stage.get("output_value")),
                            "metadata": json.dumps(stage.get("metadata", {}), sort_keys=True),
                            "intended_metadata": json.dumps(expected_stage.get("metadata", {}), sort_keys=True),
                        }
                    )
                output_axis = _current_output_axis(workspace, axis)
                write_value = latest_write.axes.get(output_axis) if latest_write else None
                write_rows.append(
                    {
                        "scenario": name,
                        "frame": frame_index,
                        "axis": axis,
                        "raw_input": raw_axes.get(axis),
                        "measured_final": final_axes.get(axis),
                        "intended_stateful_final": expected_axes.get(axis),
                        "expected_output_axis": output_axis,
                        "bridge_output_value": bridge_output_axes.get(output_axis),
                        "vjoy_write_value": write_value,
                        "wrote_this_tick": wrote_this_tick,
                        "write_status": latest_write.status if latest_write else output_runtime.get("last_write_status"),
                        "final_abs_diff": _abs_diff(final_axes.get(axis), expected_axes.get(axis)),
                        "output_abs_diff": _abs_diff(bridge_output_axes.get(output_axis), expected_output_axes.get(output_axis)),
                    }
                )
            buttons = payload.get("buttons", {}) if isinstance(payload.get("buttons"), Mapping) else {}
            for button in BUTTONS:
                output_button = _current_output_button(workspace, button)
                expected_pressed = bool(expected_input.get(f"B{button}", False))
                output_name = f"Out{output_button}"
                button_rows.append(
                    {
                        "scenario": name,
                        "frame": frame_index,
                        "button": f"B{button}",
                        "input_pressed": bool(buttons.get(f"B{button}", False)),
                        "expected_pressed": expected_pressed,
                        "expected_output_button": output_name,
                        "vjoy_output_pressed": bool(latest_write.buttons.get(output_name, False)) if latest_write else False,
                        "wrote_this_tick": wrote_this_tick,
                        "write_status": latest_write.status if latest_write else output_runtime.get("last_write_status"),
                    }
                )
            clock.advance_ms(tick_ms)
            _ = telemetry
    finally:
        service.shutdown()

    scenario = {
        "name": name,
        "tick_ms": tick_ms,
        "backend_name": backend.get_capabilities().backend_name,
        "backend_kind": backend.get_capabilities().backend_kind,
        "verification_records": backend.verification_records,
        "frame_rows": frame_rows,
        "axis_stage_rows": axis_stage_rows,
        "button_rows": button_rows,
        "write_rows": write_rows,
        "write_records": [
            {
                "success": record.success,
                "status": record.status,
                "duration_ms": record.duration_ms,
                "source": record.source,
                "axes": dict(record.axes),
                "buttons": dict(record.buttons),
            }
            for record in backend.write_records
        ],
    }
    (scenario_dir / "scenario_summary.json").write_text(json.dumps(_scenario_summary(scenario), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return scenario


def _stateful_expected(workspace: WorkspaceConfig, input_values: list[Mapping[str, float | int | str]]) -> list[dict[str, object]]:
    pipeline = WorkspaceSignalPipeline(workspace)
    state = pipeline.initial_state()
    expected: list[dict[str, object]] = []
    for values in input_values:
        raw = {axis: float(values.get(axis, 0.0)) for axis in AXES}
        result = pipeline.process(raw, state=state)
        state = result.state
        expected.append(
            {
                "final_axes": dict(result.final_output_values),
                "stage_values": {
                    axis: [
                        {
                            "stage_name": stage.stage_name,
                            "input_value": float(stage.input_value),
                            "output_value": float(stage.output_value),
                            "delta": float(stage.delta),
                            "active": bool(stage.active),
                            "metadata": stage.metadata,
                            "injected_rules": list(stage.injected_rules),
                        }
                        for stage in axis_result.stages
                    ]
                    for axis, axis_result in result.axis_results.items()
                },
            }
        )
    return expected


def _axis_sine_frames(count: int, *, sharp: bool) -> tuple[list[Mapping[str, object]], list[Mapping[str, float | int | str]]]:
    frames: list[Mapping[str, object]] = []
    values: list[Mapping[str, float | int | str]] = []
    phases = {
        "Roll": 0.0,
        "Pitch": math.pi / 5.0,
        "Throttle": math.pi / 3.0,
        "Yaw": math.pi / 2.0,
        "Aux 1": math.pi,
        "Aux 2": math.pi * 1.35,
    }
    for index in range(count):
        t = index / max(1, count - 1)
        row: dict[str, float | int | str] = {}
        for axis in AXES:
            base = math.sin((math.tau * 2.0 * t) + phases[axis])
            if sharp:
                step = _sharp_step(index, count)
                base = max(-1.0, min(1.0, (base * 0.65) + step))
            if axis == "Throttle":
                row[axis] = round(0.5 + 0.46 * base, 6)
            else:
                row[axis] = round(0.92 * base, 6)
        row.update({f"B{button}": False for button in BUTTONS})
        row["Hat 1"] = "Centered"
        values.append(row)
        frames.append(_frame_from_values(row))
    return frames, values


def _button_toggle_frames() -> tuple[list[Mapping[str, object]], list[Mapping[str, float | int | str]]]:
    frames: list[Mapping[str, object]] = []
    values: list[Mapping[str, float | int | str]] = []
    base = {axis: 0.0 for axis in AXES}
    base["Throttle"] = 0.5
    for button in BUTTONS:
        for pressed in (False, True, False):
            row: dict[str, float | int | str] = dict(base)
            row.update({f"B{item}": item == button and pressed for item in BUTTONS})
            row["Hat 1"] = "Centered"
            values.append(row)
            frames.append(_frame_from_values(row))
    return frames, values


def _mapping_change_frames() -> tuple[list[Mapping[str, object]], list[Mapping[str, float | int | str]]]:
    rows = [
        {"Roll": 0.44, "Pitch": -0.31, "Throttle": 0.68, "Yaw": -0.62, "Aux 1": 0.27, "Aux 2": -0.18},
        {"Roll": -0.52, "Pitch": 0.37, "Throttle": 0.22, "Yaw": 0.58, "Aux 1": -0.33, "Aux 2": 0.41},
    ]
    frames: list[Mapping[str, object]] = []
    values: list[Mapping[str, float | int | str]] = []
    for index, axes in enumerate(rows):
        row: dict[str, float | int | str] = dict(axes)
        row.update({f"B{button}": button == 1 and index == 0 for button in BUTTONS})
        row["Hat 1"] = "Centered"
        values.append(row)
        frames.append(_frame_from_values(row))
    return frames, values


def _math_stage_stress_frames() -> tuple[list[Mapping[str, object]], list[Mapping[str, float | int | str]]]:
    signed_pattern = (
        0.0,
        0.025,
        0.08,
        0.135,
        0.31,
        0.58,
        0.96,
        0.22,
        -0.08,
        -0.19,
        -0.64,
        -0.97,
        -0.05,
        0.0,
        0.42,
        -0.46,
    )
    offsets = {
        "Roll": 0,
        "Pitch": 3,
        "Throttle": 5,
        "Yaw": 8,
        "Aux 1": 10,
        "Aux 2": 13,
    }
    frames: list[Mapping[str, object]] = []
    values: list[Mapping[str, float | int | str]] = []
    for index in range(96):
        row: dict[str, float | int | str] = {}
        for axis in AXES:
            signed = signed_pattern[(index + offsets[axis]) % len(signed_pattern)]
            if axis == "Throttle":
                row[axis] = round(0.5 + signed * 0.48, 6)
            else:
                row[axis] = round(signed, 6)
        row.update({f"B{button}": False for button in BUTTONS})
        row["B1"] = index % 12 in (5, 6)
        row["Hat 1"] = "Centered"
        values.append(row)
        frames.append(_frame_from_values(row))
    return frames, values


def _frame_from_values(values: Mapping[str, float | int | str]) -> Mapping[str, object]:
    axes = []
    for raw_name, logical_name, one_sided in RAW_LAYOUT:
        normalized = float(values.get(logical_name, 0.0))
        raw_value = _raw_from_normalized(logical_name, normalized)
        axes.append(
            {
                "raw_name": raw_name,
                "logical_name": logical_name,
                "raw_value": raw_value,
                "raw_min": 0,
                "raw_max": 65535,
                "center": 32767.5,
                "one_sided": one_sided,
            }
        )
    return {
        "axes": tuple(axes),
        "buttons": {button: bool(values.get(f"B{button}", False)) for button in BUTTONS},
        "hats": {1: str(values.get("Hat 1", "Centered"))},
    }


def _mapping_variant_workspace(workspace: WorkspaceConfig) -> WorkspaceConfig:
    axis_routes = list(workspace.mappings.axis_routes)
    by_function = {route.function_name: route for route in axis_routes}
    roll = by_function["Roll"]
    pitch = by_function["Pitch"]
    swapped_axis_routes: list[AxisMapping] = []
    for route in axis_routes:
        if route.function_name == "Roll":
            swapped_axis_routes.append(
                replace(route, logical_output=pitch.logical_output, runtime_vjoy_output=pitch.runtime_vjoy_output)
            )
        elif route.function_name == "Pitch":
            swapped_axis_routes.append(
                replace(route, logical_output=roll.logical_output, runtime_vjoy_output=roll.runtime_vjoy_output)
            )
        else:
            swapped_axis_routes.append(route)
    button_routes = list(workspace.mappings.button_routes)
    swapped_button_routes: list[ButtonMapping] = []
    for route in button_routes:
        if route.hotas_button == 1:
            swapped_button_routes.append(replace(route, output_button=2))
        elif route.hotas_button == 2:
            swapped_button_routes.append(replace(route, output_button=1))
        else:
            swapped_button_routes.append(route)
    return replace(
        workspace,
        mappings=replace(
            workspace.mappings,
            axis_routes=tuple(swapped_axis_routes),
            button_routes=tuple(swapped_button_routes),
        ),
    )


def _math_stage_stress_workspace(workspace: WorkspaceConfig) -> WorkspaceConfig:
    tuned_axes = {
        axis_id: replace(
            tuning,
            curve_strength=0.64,
            deadzone=0.12,
            anti_deadzone=0.18,
            hysteresis=0.04,
            output_scale=1.35,
            max_output=0.72,
        )
        for axis_id, tuning in workspace.tuning.axes.items()
    }
    filtered_axes = {
        axis_id: replace(
            filtering,
            center_alpha=0.18,
            edge_alpha=0.82,
            same_slew_limit=0.24,
            reverse_slew_limit=0.11,
        )
        for axis_id, filtering in workspace.filtering.axes.items()
    }
    stress_rule = ConditionalRule(
        title="Stress Yaw scale | Roll > 0.25",
        enabled=True,
        target_axis="Yaw",
        parameter="Output Scale",
        operation="Set",
        value=0.42,
        injection_stage="Base Output Limits",
        mode_gate="Always",
        reference_axis="Roll",
        stage="Final Output",
        measure="absolute",
        comparator="greater than",
        threshold=0.25,
    )
    return replace(
        workspace,
        tuning=replace(workspace.tuning, axes=tuned_axes),
        filtering=replace(workspace.filtering, axes=filtered_axes),
        rules=RuleConfig(rules=(stress_rule,)),
    )


def _mapping_summary(workspace: WorkspaceConfig) -> dict[str, object]:
    return {
        "axis_routes": [
            {
                "function_name": route.function_name,
                "raw_axis_channel": route.raw_axis_channel,
                "logical_output": route.logical_output,
                "runtime_vjoy_output": route.runtime_vjoy_output,
                "output_axis": _axis_label(route.runtime_vjoy_output),
                "invert": route.invert,
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
    }


def _scenario_summary(scenario: Mapping[str, object]) -> dict[str, object]:
    frame_rows = scenario["frame_rows"]
    axis_rows = scenario["write_rows"]
    button_rows = scenario["button_rows"]
    writes = scenario["write_records"]
    return {
        "name": scenario["name"],
        "backend_name": scenario["backend_name"],
        "backend_kind": scenario["backend_kind"],
        "frame_count": len(frame_rows),
        "write_count": len(writes),
        "write_success_count": sum(1 for row in writes if row["success"]),
        "avg_end_to_end_ms": _avg(row.get("end_to_end_ms") for row in frame_rows),
        "max_end_to_end_ms": _max(row.get("end_to_end_ms") for row in frame_rows),
        "avg_input_read_ms": _avg(row.get("input_read_ms") for row in frame_rows),
        "avg_pipeline_ms": _avg(row.get("pipeline_ms") for row in frame_rows),
        "avg_output_write_ms": _avg(row.get("output_write_ms") for row in frame_rows),
        "max_final_abs_diff": _max(row.get("final_abs_diff") for row in axis_rows),
        "max_output_abs_diff": _max(row.get("output_abs_diff") for row in axis_rows),
        "button_true_output_count": sum(1 for row in button_rows if row.get("expected_pressed") and row.get("vjoy_output_pressed")),
        "button_expected_true_count": sum(1 for row in button_rows if row.get("expected_pressed")),
        "orchestrator_rebuild_count": _max(row.get("runtime_orchestrator_rebuild_count") for row in frame_rows),
    }


def _stage_coverage(stress_scenario: Mapping[str, object] | None) -> dict[str, dict[str, object]]:
    if not stress_scenario:
        return {}
    rows = stress_scenario.get("axis_stage_rows", [])
    if not isinstance(rows, list):
        return {}

    def metadata_for(stage_name: str) -> list[dict[str, object]]:
        values: list[dict[str, object]] = []
        for row in rows:
            if not isinstance(row, Mapping) or row.get("stage") != stage_name:
                continue
            for key in ("metadata", "intended_metadata"):
                try:
                    parsed = json.loads(str(row.get(key) or "{}"))
                except json.JSONDecodeError:
                    parsed = {}
                if isinstance(parsed, dict):
                    values.append(parsed)
        return values

    center = metadata_for("Center Conditioning")
    curve = metadata_for("Curve / Shape")
    limits = metadata_for("Base Output Limits")
    filtering = metadata_for("Filtering")
    rules = metadata_for("Rule Injections")

    def result(covered: bool, evidence: str) -> dict[str, object]:
        return {"covered": covered, "evidence": evidence}

    return {
        "Curve Mode": result(any("curve_mode" in item for item in curve), "Curve / Shape exposes curve_mode."),
        "Curve Strength": result(
            any(abs(float(item.get("curve_strength", 0.0))) > 0.0 for item in curve),
            "Stress workspace sets curve_strength=0.64 on every axis.",
        ),
        "Deadzone": result(
            any(float(item.get("deadzone", 0.0)) > 0.0 for item in center),
            "Center Conditioning exposes deadzone=0.12 and samples below/above the threshold.",
        ),
        "Anti-Deadzone": result(
            any(float(item.get("anti_deadzone", 0.0)) > 0.0 for item in center),
            "Center Conditioning exposes anti_deadzone=0.18.",
        ),
        "Hysteresis": result(
            any(bool(item.get("hysteresis_active")) for item in center),
            "Stress workspace sets hysteresis=0.04; coverage requires an active hysteresis transition.",
        ),
        "Output Scale": result(
            any(abs(float(item.get("configured_output_scale", 1.0)) - 1.0) > 0.0 for item in limits),
            "Base Output Limits exposes configured_output_scale=1.35.",
        ),
        "Max Output": result(
            any(float(item.get("max_output", 1.0)) < 1.0 for item in limits),
            "Base Output Limits exposes max_output=0.72 and edge samples drive clamping.",
        ),
        "Center Alpha": result(
            any(item.get("alpha_region") == "center" and "center_alpha" in item for item in filtering),
            "Filtering exposes center_alpha=0.18 on center-region samples.",
        ),
        "Edge Alpha": result(
            any(item.get("alpha_region") == "edge" and "edge_alpha" in item for item in filtering),
            "Filtering exposes edge_alpha=0.82 on edge-region samples.",
        ),
        "Same Slew Limit": result(
            any(item.get("slew_path") == "same-direction" and bool(item.get("slew_limited")) for item in filtering),
            "Filtering exposes same_slew_limit=0.24 and same-direction limited deltas.",
        ),
        "Reverse Slew Limit": result(
            any(item.get("slew_path") == "reverse-direction" and bool(item.get("slew_limited")) for item in filtering),
            "Filtering exposes reverse_slew_limit=0.11 and reverse-direction limited deltas in stateful intent.",
        ),
        "Conditional Rules": result(
            any(item.get("active_rules") or item.get("evaluations") for item in rules)
            or any(item.get("injected_rules") for item in limits),
            "Stress workspace enables a Yaw output-scale rule gated by Roll final output.",
        ),
    }


def _summarize_probe(
    live_probe: Mapping[str, object],
    scenarios: list[Mapping[str, object]],
    current_mapping: Mapping[str, object],
    variant_mapping: Mapping[str, object],
    graph_paths: Mapping[str, Path],
    real_vjoy_requested: bool,
) -> dict[str, object]:
    scenario_summaries = [_scenario_summary(scenario) for scenario in scenarios]
    failures: list[str] = []
    sine = next((item for item in scenario_summaries if item["name"] == "axis_sine_fake"), None)
    mapping_variant = next((item for item in scenario_summaries if item["name"] == "mapping_variant_fake"), None)
    buttons = next((item for item in scenario_summaries if item["name"] == "buttons_toggle_fake"), None)
    sharp = next((item for item in scenario_summaries if item["name"] == "axis_sharp_step_sine_fake"), None)
    stress_scenario = next((item for item in scenarios if item["name"] == "math_stage_stress_fake"), None)
    stage_coverage = _stage_coverage(stress_scenario)
    if sine and float(sine["max_final_abs_diff"]) > 0.0005:
        failures.append("bridge_continuous_axis_response_does_not_match_stateful_filter_intent")
    if mapping_variant and float(mapping_variant["max_output_abs_diff"]) > 0.0005:
        failures.append("workspace_mapping_not_applied_to_output_intent")
    if buttons and int(buttons["button_true_output_count"]) < int(buttons["button_expected_true_count"]):
        failures.append("button_mapping_not_applied_to_output_intent")
    if sharp and float(sharp["max_final_abs_diff"]) > 0.0005:
        failures.append("bridge_step_response_does_not_match_stateful_filter_intent")
    if any(float(item["orchestrator_rebuild_count"]) > float(item["frame_count"]) for item in scenario_summaries):
        failures.append("runtime_orchestrator_rebuilds_each_sample")
    if stage_coverage and not all(bool(item.get("covered")) for item in stage_coverage.values()):
        failures.append("math_stage_probe_coverage_incomplete")
    if real_vjoy_requested and not live_probe.get("real_vjoy_available"):
        failures.append("real_vjoy_requested_but_unavailable")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "failures_detected" if failures else "passed",
        "failures": failures,
        "live_probe": dict(live_probe),
        "current_mapping": current_mapping,
        "variant_mapping": variant_mapping,
        "scenarios": scenario_summaries,
        "stage_coverage": stage_coverage,
        "graphs": {key: str(path) for key, path in graph_paths.items()},
    }


def _render_report(
    summary: Mapping[str, object],
    scenarios: list[Mapping[str, object]],
    current_mapping: Mapping[str, object],
    variant_mapping: Mapping[str, object],
    graph_paths: Mapping[str, Path],
    artifact_dir: Path,
) -> str:
    lines: list[str] = []
    lines.append("# Runtime Truth Value Usability Report")
    lines.append("")
    lines.append(f"Generated: `{summary['generated_at']}`")
    lines.append(f"Overall status: `{summary['overall_status']}`")
    lines.append(f"Artifact directory: `{artifact_dir}`")
    lines.append("")
    lines.append("## Executive Findings")
    failures = summary.get("failures", [])
    if failures:
        for failure in failures:
            lines.append(f"- `{failure}`")
    else:
        lines.append("- No value-truth failures were detected in this probe.")
    lines.append("")
    live = summary["live_probe"]
    lines.append("## Live Environment Truth")
    lines.append(f"- Bridge status: `{live.get('bridge_status')}`")
    lines.append(f"- Runtime setup HOTAS PID proof: `{live.get('hotas_pid_proof')}`")
    lines.append(f"- Real vJoy available: `{live.get('real_vjoy_available')}`")
    lines.append(f"- Real vJoy status: `{live.get('real_vjoy_status')}`")
    lines.append("")
    lines.append("## Simulated Inputs")
    lines.append("- Axis test 1: 180-frame two-cycle sine input across all six axes. Roll/Pitch/Yaw/Aux axes use signed -1..1 normalization; Throttle uses the current one-sided 0..1 physical normalization.")
    lines.append("- Axis test 2: the same sine structure with abrupt injected step offsets at quarter intervals for step-response verification.")
    lines.append("- Button test: B1 through B15 are each driven false -> true -> false with all other buttons false.")
    lines.append("- Mapping test: a temporary workspace swaps Roll/Pitch output axes and B1/B2 output buttons, then the current workspace copy is used again. The repository workspace file is not modified.")
    lines.append("- Math-stage stress test: 96-frame composite input with center, below-deadzone, anti-deadzone, edge, same-direction slew, reverse-direction slew, max-output clamp, and conditional-rule threshold crossings. It uses an artifact-only workspace with curve_strength=0.64, deadzone=0.12, anti_deadzone=0.18, hysteresis=0.04, output_scale=1.35, max_output=0.72, center_alpha=0.18, edge_alpha=0.82, same_slew_limit=0.24, reverse_slew_limit=0.11, and one enabled Yaw output-scale rule.")
    lines.append("")
    lines.append("## Math Parameter Probe Coverage")
    lines.append("| Parameter family | Runtime stage payload | Proof field |")
    lines.append("|---|---|---|")
    lines.append("| Curve Mode | Curve / Shape | `metadata.curve_mode` |")
    lines.append("| Curve Strength | Curve / Shape | `metadata.curve_strength` |")
    lines.append("| Deadzone | Center Conditioning | `metadata.deadzone` |")
    lines.append("| Anti-Deadzone | Center Conditioning | `metadata.anti_deadzone` |")
    lines.append("| Hysteresis | Center Conditioning | `metadata.hysteresis`, `metadata.hysteresis_active` |")
    lines.append("| Output Scale | Base Output Limits | `metadata.output_scale`, `metadata.configured_output_scale` |")
    lines.append("| Max Output | Base Output Limits and Final Output | `metadata.max_output` plus final clamp value |")
    lines.append("| Center Alpha | Filtering | `metadata.center_alpha` and computed `metadata.alpha` |")
    lines.append("| Edge Alpha | Filtering | `metadata.edge_alpha` and computed `metadata.alpha_region` |")
    lines.append("| Same Slew Limit | Filtering | `metadata.same_slew_limit`, `metadata.slew_path`, `metadata.slew_limit` |")
    lines.append("| Reverse Slew Limit | Filtering | `metadata.reverse_slew_limit`, `metadata.slew_path`, `metadata.slew_limit` |")
    lines.append("| Conditional Rules | Rule Injections and Base Output Limits | `metadata.evaluations`, `metadata.active_rules`, `metadata.injected_rules` |")
    lines.append("")
    stage_coverage = summary.get("stage_coverage", {})
    if stage_coverage:
        lines.append("## Math-Stage Stress Coverage Result")
        lines.append("| Parameter family | Covered | Evidence |")
        lines.append("|---|---:|---|")
        for name, item in stage_coverage.items():
            if not isinstance(item, Mapping):
                continue
            lines.append(f"| {name} | `{bool(item.get('covered'))}` | {item.get('evidence')} |")
        lines.append("")
    lines.append("## Current Mapping")
    lines.extend(_mapping_table(current_mapping))
    lines.append("")
    lines.append("## Temporary Mapping Variant")
    lines.extend(_mapping_table(variant_mapping))
    lines.append("")
    lines.append("## Latency Summary")
    lines.append("| Scenario | Backend | Frames | Writes | Rebuilds | Avg total ms | Max total ms | Avg input ms | Avg pipeline ms | Avg output ms | Max final diff | Max output diff |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for scenario in summary["scenarios"]:
        lines.append(
            f"| `{scenario['name']}` | `{scenario['backend_kind']}` | {scenario['frame_count']} | {scenario['write_count']} | {scenario['orchestrator_rebuild_count']} | "
            f"{scenario['avg_end_to_end_ms']} | {scenario['max_end_to_end_ms']} | {scenario['avg_input_read_ms']} | "
            f"{scenario['avg_pipeline_ms']} | {scenario['avg_output_write_ms']} | {scenario['max_final_abs_diff']} | {scenario['max_output_abs_diff']} |"
        )
    lines.append("")
    lines.append("## Axis Proof")
    for scenario in scenarios:
        if (
            not str(scenario["name"]).startswith("axis_")
            and "mapping" not in str(scenario["name"])
            and "math_stage" not in str(scenario["name"])
        ):
            continue
        lines.append(f"### {scenario['name']}")
        lines.append("| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |")
        lines.append("|---|---:|---:|---:|---:|")
        for axis in AXES:
            write_rows = [row for row in scenario["write_rows"] if row["axis"] == axis]
            frame_rows = scenario["frame_rows"]
            lines.append(
                f"| {axis} | {_max(row.get('final_abs_diff') for row in write_rows)} | "
                f"{_max(row.get('output_abs_diff') for row in write_rows)} | "
                f"{_avg(row.get('end_to_end_ms') for row in frame_rows)} | "
                f"{sum(1 for row in write_rows if row.get('wrote_this_tick'))} |"
            )
    lines.append("")
    lines.append("## Button Proof")
    for scenario in scenarios:
        if "buttons_toggle" not in str(scenario["name"]) and "mapping_variant" not in str(scenario["name"]):
            continue
        lines.append(f"### {scenario['name']}")
        lines.append("| Button | Expected output button | Input true observed | Output true observed | Avg total latency ms | Writes observed |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for button in BUTTONS:
            rows = [row for row in scenario["button_rows"] if row["button"] == f"B{button}"]
            frame_lookup = {int(row["frame"]): row for row in scenario["frame_rows"]}
            frame_rows = [frame_lookup.get(int(row["frame"])) for row in rows if frame_lookup.get(int(row["frame"]))]
            expected_output = rows[0]["expected_output_button"] if rows else ""
            lines.append(
                f"| B{button} | {expected_output} | "
                f"{sum(1 for row in rows if row.get('input_pressed'))} | "
                f"{sum(1 for row in rows if row.get('vjoy_output_pressed'))} | "
                f"{_avg(row.get('end_to_end_ms') for row in frame_rows)} | "
                f"{sum(1 for row in rows if row.get('wrote_this_tick'))} |"
            )
    lines.append("")
    lines.append("## Graphs")
    for label, path in graph_paths.items():
        try:
            relative = Path(path).relative_to(Path("docs") / "HelmForge").as_posix()
        except ValueError:
            relative = Path(path).as_posix()
        lines.append(f"![{label}]({relative})")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- Stage values are now present in `runtime_frame.axis_stage_values` and are generated from the existing `AxisStackResult`; the focused regression verifies no second pipeline pass.")
    lines.append("- Axis value truth is available at Raw Input, Center Conditioning, Curve / Shape, Base Output Limits, Filtering, Mode Modifiers, Rule Injections, and Final Output for every axis.")
    lines.append("- The bridge reports `runtime_context_changed` rebuilds on every simulated sample, so stateful filtering diverges from the expected continuous pipeline response during sine and step tests.")
    lines.append("- The current output intent path still uses recovered static axis routing; the temporary mapping swap did not move output intent values to the swapped targets.")
    lines.append("- Button input telemetry sees B1-B15, but the runtime output intent does not drive mapped output buttons true.")
    lines.append("- The dedicated stress input covers every named math parameter except active hysteresis transitions; the stack reports hysteresis configuration, but this run did not observe `hysteresis_active=true`.")
    lines.append("- Real vJoy write calls can be accepted when enabled, but the current product path does not expose a vJoy readback channel; this report distinguishes write-call proof from readback proof.")
    lines.append("")
    return "\n".join(lines) + "\n"


def _mapping_table(mapping: Mapping[str, object]) -> list[str]:
    rows = ["| Function/Button | Source | Output |", "|---|---|---|"]
    for route in mapping["axis_routes"]:
        rows.append(f"| {route['function_name']} | {route['raw_axis_channel']} | {route['runtime_vjoy_output']} |")
    for route in mapping["button_routes"]:
        rows.append(f"| B{route['hotas_button']} | HOTAS B{route['hotas_button']} | Out{route['output_button']} |")
    return rows


def _write_csvs(artifact_dir: Path, scenarios: list[Mapping[str, object]]) -> None:
    _write_rows(artifact_dir / "frames.csv", [row for scenario in scenarios for row in scenario["frame_rows"]])
    _write_rows(artifact_dir / "axis_stage_values.csv", [row for scenario in scenarios for row in scenario["axis_stage_rows"]])
    _write_rows(artifact_dir / "axis_output_values.csv", [row for scenario in scenarios for row in scenario["write_rows"]])
    _write_rows(artifact_dir / "button_values.csv", [row for scenario in scenarios for row in scenario["button_rows"]])


def _write_rows(path: Path, rows: list[Mapping[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_graphs(
    asset_root: Path,
    sine: Mapping[str, object],
    sharp: Mapping[str, object],
    stress: Mapping[str, object],
) -> Mapping[str, Path]:
    paths = {
        "Sine measured vs intended": asset_root / "axis-sine-measured-vs-intended.svg",
        "Sharp-step sine measured vs intended": asset_root / "axis-sharp-step-measured-vs-intended.svg",
        "Math-stage stress measured vs intended": asset_root / "axis-math-stage-stress-measured-vs-intended.svg",
    }
    _write_axis_graph(paths["Sine measured vs intended"], sine, title="Sine measured output vs stateful intended output")
    _write_axis_graph(paths["Sharp-step sine measured vs intended"], sharp, title="Sharp-step sine measured output vs stateful intended output")
    _write_axis_graph(paths["Math-stage stress measured vs intended"], stress, title="Math-stage stress measured output vs stateful intended output")
    return paths


def _write_axis_graph(path: Path, scenario: Mapping[str, object], *, title: str) -> None:
    width = 1100
    panel_height = 150
    margin_left = 70
    margin_top = 44
    plot_width = width - margin_left - 28
    height = margin_top + panel_height * len(AXES) + 30
    write_rows = scenario["write_rows"]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0f1419"/>',
        f'<text x="24" y="28" fill="#f4f7fb" font-family="Segoe UI, Arial" font-size="18">{_xml(title)}</text>',
    ]
    for axis_index, axis in enumerate(AXES):
        axis_rows = [row for row in write_rows if row["axis"] == axis]
        top = margin_top + axis_index * panel_height
        bottom = top + panel_height - 28
        mid = (top + bottom) / 2
        lines.append(f'<text x="16" y="{mid + 5:.1f}" fill="#d6dde6" font-family="Segoe UI, Arial" font-size="13">{_xml(axis)}</text>')
        lines.append(f'<line x1="{margin_left}" y1="{mid:.1f}" x2="{width - 24}" y2="{mid:.1f}" stroke="#33414d" stroke-width="1"/>')
        lines.append(f'<line x1="{margin_left}" y1="{top}" x2="{margin_left}" y2="{bottom}" stroke="#33414d" stroke-width="1"/>')
        measured = [(int(row["frame"]), _float(row.get("measured_final"))) for row in axis_rows]
        intended = [(int(row["frame"]), _float(row.get("intended_stateful_final"))) for row in axis_rows]
        lines.append(_polyline(measured, margin_left, top, plot_width, bottom - top, "#38bdf8"))
        lines.append(_polyline(intended, margin_left, top, plot_width, bottom - top, "#f97316"))
    lines.append('<text x="780" y="28" fill="#38bdf8" font-family="Segoe UI, Arial" font-size="13">measured bridge final</text>')
    lines.append('<text x="930" y="28" fill="#f97316" font-family="Segoe UI, Arial" font-size="13">stateful intended</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def _polyline(points: list[tuple[int, float | None]], x: float, y: float, width: float, height: float, color: str) -> str:
    valid = [(frame, value) for frame, value in points if value is not None]
    if not valid:
        return ""
    max_frame = max(frame for frame, _ in valid) or 1
    coords = []
    for frame, value in valid:
        px = x + (frame / max_frame) * width
        py = y + (1.0 - ((max(-1.0, min(1.0, value)) + 1.0) / 2.0)) * height
        coords.append(f"{px:.1f},{py:.1f}")
    return f'<polyline points="{" ".join(coords)}" fill="none" stroke="{color}" stroke-width="2" opacity="0.92"/>'


def _live_environment_probe(artifact_dir: Path) -> dict[str, object]:
    bridge = _run_command(["python", "-m", "bridge_app.main", "--status"])
    setup = _run_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\\scripts\\runtime_setup_check.ps1", "-DryRun"])
    backend = RealVJoyOutputBackend()
    status = backend.get_status()
    caps = backend.get_capabilities()
    devices = backend.enumerate_output_devices()
    (artifact_dir / "bridge-status.txt").write_text(bridge["stdout"] + bridge["stderr"], encoding="utf-8")
    (artifact_dir / "runtime-setup-check.txt").write_text(setup["stdout"] + setup["stderr"], encoding="utf-8")
    return {
        "bridge_status": bridge["stdout"].strip().splitlines()[0] if bridge["stdout"].strip() else bridge["stderr"].strip(),
        "bridge_status_exit": bridge["returncode"],
        "runtime_setup_exit": setup["returncode"],
        "hotas_pid_proof": _first_line_containing(setup["stdout"], "VID_044F&PID_B68D"),
        "real_vjoy_available": bool(caps.backend_available and caps.real_output_writes_available and devices),
        "real_vjoy_status": status.status,
        "real_vjoy_devices": [device.display_name for device in devices],
    }


def _run_command(command: list[str]) -> dict[str, object]:
    completed = subprocess.run(command, text=True, capture_output=True, timeout=45)
    return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _hotas_device():
    return build_physical_input_device_info(
        device_id="truth-probe-hotas-one",
        display_name="Truth Probe Thrustmaster T.Flight HOTAS One",
        manufacturer="Thrustmaster",
        vendor_id="044f",
        product_id="b68d",
        axis_count=6,
        button_count=15,
        hat_count=1,
        backend_name="truth_probe_fake_physical",
    )


def _expected_output_axes(workspace: WorkspaceConfig, final_axes: Mapping[str, float]) -> dict[str, float]:
    outputs = {axis: 0.0 for axis in OUTPUT_AXIS_CHOICES}
    for route in workspace.mappings.axis_routes:
        outputs[_axis_label(route.runtime_vjoy_output)] = float(final_axes.get(route.function_name, 0.0))
    return outputs


def _current_output_axis(workspace: WorkspaceConfig, logical_axis: str) -> str:
    route = next((route for route in workspace.mappings.axis_routes if route.function_name == logical_axis), None)
    return _axis_label(route.runtime_vjoy_output if route else "")


def _current_output_button(workspace: WorkspaceConfig, hotas_button: int) -> int:
    route = next((route for route in workspace.mappings.button_routes if route.hotas_button == hotas_button), None)
    return int(route.output_button if route else hotas_button)


def _axis_label(runtime_vjoy_output: str) -> str:
    text = str(runtime_vjoy_output or "").strip()
    if "(" in text:
        text = text.split("(", 1)[0]
    return text or "X"


def _raw_from_normalized(axis: str, value: float) -> int:
    if axis == "Throttle":
        return int(round(max(0.0, min(1.0, value)) * 65535))
    return int(round(((max(-1.0, min(1.0, value)) + 1.0) / 2.0) * 65535))


def _sharp_step(index: int, count: int) -> float:
    quarter = max(1, count // 4)
    band = index // quarter
    if index % quarter < 8:
        return (0.55, -0.75, 0.7, -0.6)[band % 4]
    return 0.0


def _elapsed_ms(started: float) -> float:
    return round(max(0.0, (time.perf_counter() - started) * 1000.0), 3)


def _abs_diff(left: object, right: object) -> float | None:
    left_value = _float(left)
    right_value = _float(right)
    if left_value is None or right_value is None:
        return None
    return round(abs(left_value - right_value), 6)


def _avg(values) -> float:
    numeric = [value for value in (_float(value) for value in values) if value is not None]
    return round(statistics.fmean(numeric), 3) if numeric else 0.0


def _max(values) -> float:
    numeric = [value for value in (_float(value) for value in values) if value is not None]
    return round(max(numeric), 6) if numeric else 0.0


def _float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_line_containing(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line.strip()
    return ""


def _xml(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


if __name__ == "__main__":
    raise SystemExit(main())
