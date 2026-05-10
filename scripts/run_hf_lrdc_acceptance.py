from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge_app.runtime_bench import RuntimeBenchOptions, run_runtime_bench
from shared_core.runtime.runtime_acceptance import (
    RuntimeAcceptanceOptions,
    evaluate_runtime_acceptance,
    export_acceptance_report,
    load_json_mapping,
)


DEFAULT_OUTPUT = Path(".artifacts") / "hf-lrdc" / "acceptance"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run HF-LRDC runtime acceptance gates.")
    parser.add_argument("--mode", choices=("fake", "real"), default="fake")
    parser.add_argument("--require-hotas", action="store_true")
    parser.add_argument("--require-vjoy", action="store_true")
    parser.add_argument("--require-real-output", action="store_true")
    parser.add_argument("--require-manual-validation", action="store_true")
    parser.add_argument("--bench-artifact", type=Path)
    parser.add_argument("--manual-validation-artifact", type=Path)
    parser.add_argument("--telemetry-json", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    telemetry = load_json_mapping(args.telemetry_json)
    bench_summary = load_json_mapping(args.bench_artifact)
    manual = load_json_mapping(args.manual_validation_artifact)
    if args.mode == "fake" and not bench_summary:
        bench = run_runtime_bench(
            RuntimeBenchOptions(
                mode="fake",
                scenario="axis_sweep_roll",
                duration_ms=160,
                output_dir=Path(args.output) / "_bench",
            )
        )
        bench_summary = dict(bench.summary)
        if not telemetry:
            telemetry = _telemetry_from_fake_bench(bench_summary)
    options = RuntimeAcceptanceOptions(
        mode=args.mode,
        require_hotas=bool(args.require_hotas),
        require_vjoy=bool(args.require_vjoy),
        require_real_output=bool(args.require_real_output),
        require_manual_validation=bool(args.require_manual_validation),
        source="hf_lrdc_acceptance_cli",
    )
    report = evaluate_runtime_acceptance(
        options,
        telemetry=telemetry,
        bench_summary=bench_summary,
        manual_validation=manual,
    )
    artifacts = export_acceptance_report(
        report,
        Path(args.output),
        evidence={"telemetry": telemetry, "bench_summary": bench_summary, "manual_validation": manual},
    )
    result = report.result()
    blocked = [gate for gate in report.gates if gate.required and gate.status.value == "blocked"]
    print(f"overall_status={result.overall_status}")
    print(f"ready_for_rc={result.ready_for_rc}")
    print(f"proof_kind={report.proof_kind.value}")
    print(f"blocked_gate_count={result.blocked_count}")
    print(f"warning_count={result.warning_count}")
    print(f"artifact_path={artifacts['artifact_dir']}")
    if blocked:
        print("top_blocked_reasons=" + " | ".join((gate.blocked_reason or gate.title) for gate in blocked[:3]))
    return 0 if result.ready_for_rc else 1


def _telemetry_from_fake_bench(summary: Mapping[str, object]) -> dict[str, object]:
    output = _mapping(summary.get("output"))
    input_summary = _mapping(summary.get("input"))
    runtime_truth = _mapping(summary.get("runtime_truth"))
    telemetry = _mapping(summary.get("telemetry"))
    pipeline = _mapping(summary.get("pipeline"))
    return {
        "timestamp": "generated_from_fake_bench",
        "runtime_truth": "fake_path_acceptance_only",
        "output_verified": False,
        "output_status": "fake_output_backend",
        "raw_axes": {"Roll": 0.25},
        "final_axes": {"Roll": 0.25},
        "bridge_timing": {
            "tick_count": input_summary.get("sample_count", 1),
            "last_tick_duration_ms": 1.0,
            "last_discovery_age_ms": 2500.0,
            "fast_loop_status": "healthy",
            "slow_lane_status": "idle",
        },
        "physical_input_fidelity": {
            "backend_name": input_summary.get("backend_name", "fake_physical_input_backend"),
            "backend_kind": input_summary.get("backend_kind", "fake"),
            "sample_age_ms": input_summary.get("sample_age_average_ms", 0.0),
            "read_duration_ms": input_summary.get("average_input_read_duration_ms", 0.0),
            "mapping_status": "ok",
        },
        "physical_input_backend_choice": {
            "selected_backend_name": input_summary.get("backend_name", "fake_physical_input_backend"),
            "selected_backend_kind": input_summary.get("backend_kind", "fake"),
        },
        "telemetry_source": {
            "source": telemetry.get("source_used", "Bridge JSON Snapshot"),
            "fresh": True,
            "stale": False,
        },
        "live_monitor": {
            "accepted_frame_cadence_hz": telemetry.get("stream_accepted_frame_rate_hz", 0.0),
            "repeated_frame_count": telemetry.get("duplicate_or_repeated_frame_count", 0),
            "duplicate_frames_accepted": False,
            "latest_bridge_frame_age_ms": telemetry.get("telemetry_frame_age_average_ms", 0.0),
        },
        "bridge_workspace": {
            "workspace_hash": "fake-bench-workspace",
            "workspace_revision": "fake-bench-workspace",
            "config_status": "loaded",
        },
        "ui_workspace_hash": "fake-bench-workspace",
        "runtime_frame": {
            "sequence": input_summary.get("sample_count", 1),
            "output_intent_ready": bool(pipeline.get("final_output_changes_observed", 0)),
            "full_live_runtime_ready": bool(runtime_truth.get("full_live_runtime_ready", False)),
            "blocked_reason": "fake_path_real_runtime_not_proven",
            "fake_or_real_path": "fake",
        },
        "output_loop_runtime": {
            "state": "disabled",
            "verification_status": output.get("verification_status", "fake_verified"),
            "verification_fake": bool(runtime_truth.get("fake_output_verified", True)),
            "verification_real": bool(runtime_truth.get("real_output_verified", False)),
            "write_rate_hz": output.get("target_write_rate_hz", 30.0),
            "write_success_count": output.get("write_success_count", 0),
            "write_failure_count": output.get("write_failure_count", 0),
            "write_skipped_count": output.get("write_skipped_count", 0),
            "write_skipped_rate_limited_count": output.get("write_skipped_rate_limited_count", 0),
            "safety_stop_reason": "None",
            "neutral_restore_status": output.get("neutral_restore_status", "not_attempted"),
            "loop_recreated_count": 0,
        },
    }


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


if __name__ == "__main__":
    raise SystemExit(main())
