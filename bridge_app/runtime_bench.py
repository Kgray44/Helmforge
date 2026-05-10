from __future__ import annotations

import csv
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

from bridge_app.service import BridgeService, BridgeServiceOptions
from shared_core.runtime.hotas_input import FakePhysicalInputBackend, build_physical_input_device_info
from shared_core.runtime.vjoy_output import FakeVirtualOutputBackend, VirtualOutputWriteResult


BENCH_ROOT = Path(".artifacts") / "hf-lrdc" / "runtime-bench"
AXIS_NAMES = ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
RAW_NAMES = ("X", "Y", "Z", "R", "U", "V")


@dataclass(frozen=True)
class RuntimeBenchOptions:
    mode: str = "fake"
    scenario: str = "axis_sweep_roll"
    duration_ms: int = 3000
    output_dir: Path = BENCH_ROOT
    require_hotas: bool = False
    require_vjoy: bool = False
    allow_real_output_writes: bool = False
    tick_interval_ms: int = 16


@dataclass(frozen=True)
class RuntimeBenchResult:
    artifact_dir: Path
    summary: dict[str, object]


class BenchClock:
    def __init__(self, start: datetime | None = None) -> None:
        self.now = start or datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, milliseconds: int) -> None:
        self.now += timedelta(milliseconds=max(1, int(milliseconds)))


class FailingAfterFakeOutputBackend(FakeVirtualOutputBackend):
    def __init__(self, *, fail_after_successes: int = 1) -> None:
        super().__init__()
        self._fail_after_successes = max(0, int(fail_after_successes))

    def write_output_intent(self, output_intent):
        if len(self.written_intents) >= self._fail_after_successes and output_intent.source != "neutral_restore":
            return VirtualOutputWriteResult(
                success=False,
                status="write_failed",
                message="Bench injected fake output failure. Not real vJoy.",
                backend_name=self.backend_name,
                output_intent=output_intent,
                errors=("bench injected write failure",),
            )
        return super().write_output_intent(output_intent)


def build_fake_scenario_frames(scenario: str, *, frame_count: int = 120) -> tuple[dict[str, object], ...]:
    count = max(2, int(frame_count))
    frames: list[dict[str, object]] = []
    for index in range(count):
        t = index / max(1, count - 1)
        values = {axis: 0.0 for axis in AXIS_NAMES}
        buttons = {button: False for button in range(1, 16)}
        hat = "Centered"
        if scenario in {"axis_sweep_roll", "fake_output_success", "fake_output_rate_limited", "fake_output_failure", "fake_output_unverified"}:
            values["Roll"] = _triangle(t)
        elif scenario == "axis_step_pitch":
            values["Pitch"] = _step_pitch(index, count)
        elif scenario == "throttle_ramp":
            values["Throttle"] = -1.0 + 2.0 * t
        elif scenario == "buttons_hat":
            buttons[1] = index % 6 == 1
            buttons[2] = index % 6 == 2
            buttons[15] = index % 6 == 3
            hat = ("Up", "Right", "Down", "Left", "Centered", "Centered")[index % 6]
        elif scenario == "multi_axis_mixed":
            values["Roll"] = math.sin(t * math.tau)
            values["Pitch"] = math.cos(t * math.tau)
            values["Throttle"] = -1.0 + 2.0 * t
            values["Yaw"] = _triangle((t * 2.0) % 1.0)
        else:
            values["Roll"] = _triangle(t)
        axes = []
        for raw_name, logical_name in zip(RAW_NAMES, AXIS_NAMES):
            normalized = round(max(-1.0, min(1.0, values[logical_name])), 4)
            axes.append(
                {
                    "raw_name": raw_name,
                    "logical_name": logical_name,
                    "raw_value": _raw_from_normalized(normalized),
                    "raw_min": 0,
                    "raw_max": 65535,
                    "normalized_value": normalized,
                }
            )
        frames.append({"axes": tuple(axes), "buttons": buttons, "hats": {1: hat}})
    return tuple(frames)


def run_runtime_bench(options: RuntimeBenchOptions) -> RuntimeBenchResult:
    artifact_dir = _artifact_dir(options)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if options.mode == "real":
        return _run_real_placeholder(options, artifact_dir)
    return _run_fake_bench(options, artifact_dir)


def _run_fake_bench(options: RuntimeBenchOptions, artifact_dir: Path) -> RuntimeBenchResult:
    duration_ms = max(1, int(options.duration_ms))
    tick_ms = max(1, int(options.tick_interval_ms))
    ticks = max(1, math.ceil(duration_ms / tick_ms))
    frames = build_fake_scenario_frames(options.scenario, frame_count=max(ticks + 4, 8))
    clock = BenchClock()
    telemetry_path = artifact_dir / "bridge_telemetry.json"
    command_path = artifact_dir / "bridge_command.json"
    physical_backend = FakePhysicalInputBackend(
        (_hotas_device(),),
        sample_frames=frames,
        clock=clock,
        sample_source="fake_bench",
    )
    output_backend = _output_backend_for_scenario(options.scenario)
    enable_output = options.scenario != "fake_output_unverified"
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=telemetry_path,
            command_path=command_path,
            simulate=False,
            tick_interval_ms=tick_ms,
            physical_input_backend=physical_backend,
            virtual_output_backend=output_backend,
            enable_live_input=True,
            enable_output_verification=enable_output,
            enable_output_loop=enable_output,
            enable_telemetry_stream=False,
            clock=clock,
        )
    )
    frame_rows: list[dict[str, object]] = []
    timing_rows: list[dict[str, object]] = []
    final_roll_values: list[float] = []
    frame_keys: set[object] = set()
    duplicate_count = 0
    try:
        for tick in range(ticks):
            telemetry = service.run_once()
            payload = json.loads(telemetry_path.read_text(encoding="utf-8"))
            runtime_frame = payload.get("runtime_frame") or {}
            sequence = runtime_frame.get("sequence", tick + 1) if isinstance(runtime_frame, Mapping) else tick + 1
            if sequence in frame_keys:
                duplicate_count += 1
            frame_keys.add(sequence)
            final_axes = payload.get("final_axes") if isinstance(payload.get("final_axes"), Mapping) else {}
            final_roll_values.append(float(final_axes.get("Roll", 0.0)))
            timing = payload.get("bridge_timing") if isinstance(payload.get("bridge_timing"), Mapping) else {}
            output = payload.get("output_loop_runtime") if isinstance(payload.get("output_loop_runtime"), Mapping) else {}
            frame_rows.append(
                {
                    "sequence": sequence,
                    "timestamp": payload.get("timestamp"),
                    "runtime_truth": payload.get("runtime_truth"),
                    "output_verified": payload.get("output_verified"),
                    "full_live_runtime_ready": bool(runtime_frame.get("full_live_runtime_ready", False)) if isinstance(runtime_frame, Mapping) else False,
                    "roll": final_axes.get("Roll", 0.0),
                    "pitch": final_axes.get("Pitch", 0.0),
                    "throttle": final_axes.get("Throttle", 0.0),
                    "tick_duration_ms": timing.get("last_tick_duration_ms"),
                    "pipeline_duration_ms": timing.get("last_pipeline_duration_ms"),
                    "input_read_duration_ms": timing.get("last_input_read_duration_ms"),
                    "output_status": output.get("last_write_status"),
                }
            )
            timing_rows.append(
                {
                    "sequence": sequence,
                    "tick_duration_ms": timing.get("last_tick_duration_ms", 0.0),
                    "pipeline_duration_ms": timing.get("last_pipeline_duration_ms", 0.0),
                    "input_read_duration_ms": timing.get("last_input_read_duration_ms", 0.0),
                    "output_write_duration_ms": timing.get("last_output_write_duration_ms", 0.0),
                    "telemetry_publish_duration_ms": timing.get("last_telemetry_publish_duration_ms", 0.0),
                }
            )
            clock.advance(tick_ms)
    finally:
        service.shutdown()

    latest_payload = json.loads(telemetry_path.read_text(encoding="utf-8"))
    output_runtime = latest_payload.get("output_loop_runtime") if isinstance(latest_payload.get("output_loop_runtime"), Mapping) else {}
    timing_stats = _timing_stats(timing_rows)
    summary = _summary_for_fake(
        options=options,
        frame_rows=frame_rows,
        timing_rows=timing_rows,
        final_roll_values=final_roll_values,
        latest_payload=latest_payload,
        output_runtime=output_runtime,
        duplicate_count=duplicate_count,
        timing_stats=timing_stats,
    )
    _write_artifacts(artifact_dir, summary, frame_rows, timing_rows)
    return RuntimeBenchResult(artifact_dir=artifact_dir, summary=summary)


def _run_real_placeholder(options: RuntimeBenchOptions, artifact_dir: Path) -> RuntimeBenchResult:
    summary = {
        "pass": not (options.require_hotas or options.require_vjoy),
        "mode": "real",
        "scenario": options.scenario,
        "duration_ms": options.duration_ms,
        "fake_or_real_path": "real",
        "input": {"backend_name": "real_hardware_not_exercised", "sample_count": 0, "estimated_input_sample_rate_hz": 0.0},
        "pipeline": {"average_pipeline_duration_ms": 0.0, "max_pipeline_duration_ms": 0.0, "pipeline_error_count": 0, "final_output_changes_observed": 0},
        "output": {"backend_name": "real_vjoy_not_exercised", "verification_status": "not_attempted", "write_success_count": 0, "write_failure_count": 0, "safety_stop_state": False, "neutral_restore_status": "not_attempted"},
        "telemetry": {"stream_connected": False, "stream_frame_count": 0, "json_snapshot_frame_count": 0, "duplicate_or_repeated_frame_count": 0, "source_used": "real bench placeholder"},
        "runtime_truth": {"runtime_truth": "blocked_real_bench_not_exercised", "full_live_runtime_ready": False, "real_output_verified": False},
        "warnings": ("real hardware validation remains bench-only unless HOTAS/vJoy are present and explicit flags allow checks",),
        "errors": ("required real hardware was not exercised",) if (options.require_hotas or options.require_vjoy) else (),
    }
    _write_artifacts(artifact_dir, summary, (), ())
    return RuntimeBenchResult(artifact_dir=artifact_dir, summary=summary)


def _summary_for_fake(
    *,
    options: RuntimeBenchOptions,
    frame_rows: list[dict[str, object]],
    timing_rows: list[dict[str, object]],
    final_roll_values: list[float],
    latest_payload: Mapping[str, object],
    output_runtime: Mapping[str, object],
    duplicate_count: int,
    timing_stats: dict[str, float],
) -> dict[str, object]:
    output_success = int(output_runtime.get("write_success_count") or 0)
    output_failures = int(output_runtime.get("write_failure_count") or 0)
    rate_limited = int(output_runtime.get("write_skipped_rate_limited_count") or 0)
    output_state = str(output_runtime.get("state") or "unavailable")
    changes = _change_count(final_roll_values)
    runtime_frame = latest_payload.get("runtime_frame") if isinstance(latest_payload.get("runtime_frame"), Mapping) else {}
    pass_status = bool(frame_rows and changes > 0 and latest_payload.get("output_verified") is not True)
    if options.scenario == "fake_output_success":
        pass_status = pass_status and output_success > 0 and output_failures == 0
    if options.scenario == "fake_output_rate_limited":
        pass_status = pass_status and rate_limited > 0
    if options.scenario == "fake_output_failure":
        pass_status = pass_status and output_failures > 0 and output_state == "safety_stopped"
    if options.scenario == "fake_output_unverified":
        pass_status = pass_status and output_success == 0
    return {
        "pass": pass_status,
        "mode": "fake",
        "scenario": options.scenario,
        "duration_ms": options.duration_ms,
        "fake_or_real_path": "fake",
        "input": {
            "backend_name": "fake_physical_input_backend",
            "backend_kind": "fake",
            "sample_count": len(frame_rows),
            "estimated_input_sample_rate_hz": round(len(frame_rows) / max(0.001, options.duration_ms / 1000.0), 3),
            "average_input_read_duration_ms": timing_stats["avg_input_read_duration_ms"],
            "max_input_read_duration_ms": timing_stats["max_input_read_duration_ms"],
            "sample_age_average_ms": 0.0,
        },
        "pipeline": {
            "average_pipeline_duration_ms": timing_stats["avg_pipeline_duration_ms"],
            "max_pipeline_duration_ms": timing_stats["max_pipeline_duration_ms"],
            "pipeline_error_count": 0,
            "final_output_changes_observed": changes,
        },
        "output": {
            "backend_name": output_runtime.get("backend_name", "Fake output backend"),
            "backend_kind": output_runtime.get("backend_kind", "fake"),
            "target_write_rate_hz": output_runtime.get("write_rate_hz"),
            "actual_write_rate_hz": output_runtime.get("actual_write_rate_hz"),
            "attempted_ticks": output_runtime.get("tick_count", 0),
            "write_success_count": output_success,
            "write_failure_count": output_failures,
            "write_skipped_count": output_runtime.get("write_skipped_count", 0),
            "write_skipped_rate_limited_count": rate_limited,
            "safety_stop_state": output_state == "safety_stopped",
            "neutral_restore_status": output_runtime.get("neutral_restore_status", "not_attempted"),
            "verification_status": output_runtime.get("verification_status", "not_attempted"),
        },
        "telemetry": {
            "stream_connected": False,
            "stream_frame_count": 0,
            "stream_accepted_frame_rate_hz": 0.0,
            "json_snapshot_frame_count": len(frame_rows),
            "duplicate_or_repeated_frame_count": duplicate_count,
            "telemetry_frame_age_average_ms": 0.0,
            "source_used": "Bridge JSON Snapshot",
        },
        "runtime_truth": {
            "runtime_truth": latest_payload.get("runtime_truth"),
            "full_live_runtime_ready": bool(runtime_frame.get("full_live_runtime_ready", False)) if isinstance(runtime_frame, Mapping) else False,
            "real_output_verified": bool(output_runtime.get("verification_real", False)),
            "fake_output_verified": bool(output_runtime.get("verification_fake", False)),
        },
        "warnings": ("fake backend proof is fake-path proof only",),
        "errors": (),
    }


def _write_artifacts(
    artifact_dir: Path,
    summary: Mapping[str, object],
    frame_rows,
    timing_rows,
) -> None:
    artifact_dir.joinpath("summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact_dir.joinpath("summary.md").write_text(_summary_markdown(summary), encoding="utf-8")
    with artifact_dir.joinpath("frames.jsonl").open("w", encoding="utf-8") as handle:
        for row in frame_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    fieldnames = ("sequence", "tick_duration_ms", "pipeline_duration_ms", "input_read_duration_ms", "output_write_duration_ms", "telemetry_publish_duration_ms")
    with artifact_dir.joinpath("timings.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in timing_rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _summary_markdown(summary: Mapping[str, object]) -> str:
    return (
        f"# HF-LRDC Runtime Bench Summary\n\n"
        f"- Mode: {summary.get('mode')}\n"
        f"- Scenario: {summary.get('scenario')}\n"
        f"- Pass: {summary.get('pass')}\n"
        f"- Path: {summary.get('fake_or_real_path')}\n"
        f"- Runtime truth: {summary.get('runtime_truth')}\n"
        f"- Warning: fake backend proof is fake-path proof only; output intent is not output write proof.\n"
    )


def _artifact_dir(options: RuntimeBenchOptions) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_scenario = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in options.scenario)
    return Path(options.output_dir) / f"{stamp}-{options.mode}-{safe_scenario}"


def _output_backend_for_scenario(scenario: str):
    if scenario == "fake_output_failure":
        return FailingAfterFakeOutputBackend(fail_after_successes=1)
    return FakeVirtualOutputBackend()


def _hotas_device():
    return build_physical_input_device_info(
        device_id="bench-hotas-one",
        display_name="Bench Fake Thrustmaster T.Flight HOTAS One",
        manufacturer="Thrustmaster",
        vendor_id="044f",
        product_id="b68d",
        axis_count=6,
        button_count=15,
        hat_count=1,
        backend_name="fake_physical_input_backend",
    )


def _timing_stats(rows: list[Mapping[str, object]]) -> dict[str, float]:
    return {
        "avg_input_read_duration_ms": _avg(rows, "input_read_duration_ms"),
        "max_input_read_duration_ms": _max(rows, "input_read_duration_ms"),
        "avg_pipeline_duration_ms": _avg(rows, "pipeline_duration_ms"),
        "max_pipeline_duration_ms": _max(rows, "pipeline_duration_ms"),
    }


def _avg(rows: list[Mapping[str, object]], key: str) -> float:
    values = [_float(row.get(key)) for row in rows]
    values = [value for value in values if value is not None]
    return round(sum(values) / len(values), 3) if values else 0.0


def _max(rows: list[Mapping[str, object]], key: str) -> float:
    values = [_float(row.get(key)) for row in rows]
    values = [value for value in values if value is not None]
    return round(max(values), 3) if values else 0.0


def _float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _change_count(values: list[float]) -> int:
    return sum(1 for left, right in zip(values, values[1:]) if abs(left - right) > 0.001)


def _triangle(t: float) -> float:
    if t <= 0.5:
        return -1.0 + 4.0 * t
    return 3.0 - 4.0 * t


def _step_pitch(index: int, count: int) -> float:
    quarter = max(1, count // 4)
    if index < quarter:
        return 0.0
    if index < quarter * 2:
        return 1.0
    if index < quarter * 3:
        return -1.0
    return 0.0


def _raw_from_normalized(value: float) -> int:
    return int(round((max(-1.0, min(1.0, value)) + 1.0) * 0.5 * 65535))
