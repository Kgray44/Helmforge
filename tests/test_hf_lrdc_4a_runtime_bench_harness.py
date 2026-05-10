from __future__ import annotations

import json
import shutil
from pathlib import Path


def test_hf_lrdc_4a_fake_scenarios_generate_expected_activity():
    from bridge_app.runtime_bench import build_fake_scenario_frames

    sweep = build_fake_scenario_frames("axis_sweep_roll", frame_count=9)
    assert sweep[0]["axes"][0]["logical_name"] == "Roll"
    assert min(frame["axes"][0]["normalized_value"] for frame in sweep) <= -0.9
    assert max(frame["axes"][0]["normalized_value"] for frame in sweep) >= 0.9

    pitch = build_fake_scenario_frames("axis_step_pitch", frame_count=8)
    pitch_values = {frame["axes"][1]["normalized_value"] for frame in pitch}
    assert {0.0, 1.0, -1.0}.issubset(pitch_values)

    throttle = build_fake_scenario_frames("throttle_ramp", frame_count=8)
    throttle_values = [frame["axes"][2]["normalized_value"] for frame in throttle]
    assert throttle_values[0] < throttle_values[-1]

    buttons_hat = build_fake_scenario_frames("buttons_hat", frame_count=6)
    assert any(frame["buttons"][1] for frame in buttons_hat)
    assert any(frame["buttons"][2] for frame in buttons_hat)
    assert any(frame["buttons"][15] for frame in buttons_hat)
    assert {"Up", "Right", "Down", "Left", "Centered"}.issubset({next(iter(frame["hats"].values())) for frame in buttons_hat})

    mixed = build_fake_scenario_frames("multi_axis_mixed", frame_count=8)
    changed_axes = {
        axis_index
        for axis_index in range(4)
        if len({frame["axes"][axis_index]["normalized_value"] for frame in mixed}) > 1
    }
    assert changed_axes == {0, 1, 2, 3}


def test_hf_lrdc_4a_fake_bench_writes_artifacts_and_sections(tmp_path):
    from bridge_app.runtime_bench import RuntimeBenchOptions, run_runtime_bench

    result = run_runtime_bench(
        RuntimeBenchOptions(mode="fake", scenario="axis_sweep_roll", duration_ms=160, output_dir=tmp_path)
    )

    assert result.summary["pass"] is True
    assert result.summary["fake_or_real_path"] == "fake"
    assert result.summary["input"]["sample_count"] > 0
    assert result.summary["pipeline"]["final_output_changes_observed"] > 0
    assert result.summary["telemetry"]["json_snapshot_frame_count"] > 0
    assert result.summary["runtime_truth"]["full_live_runtime_ready"] is False
    assert result.artifact_dir.joinpath("summary.md").exists()
    assert result.artifact_dir.joinpath("summary.json").exists()
    assert result.artifact_dir.joinpath("frames.jsonl").exists()
    assert result.artifact_dir.joinpath("timings.csv").exists()


def test_hf_lrdc_4a_fake_output_success_rate_limit_failure_and_unverified(tmp_path):
    from bridge_app.runtime_bench import RuntimeBenchOptions, run_runtime_bench

    success = run_runtime_bench(
        RuntimeBenchOptions(mode="fake", scenario="fake_output_success", duration_ms=180, output_dir=tmp_path / "success")
    ).summary
    assert success["output"]["write_success_count"] > 0
    assert success["output"]["safety_stop_state"] is False
    assert success["runtime_truth"]["real_output_verified"] is False

    limited = run_runtime_bench(
        RuntimeBenchOptions(mode="fake", scenario="fake_output_rate_limited", duration_ms=180, output_dir=tmp_path / "limited")
    ).summary
    assert limited["output"]["write_skipped_rate_limited_count"] > 0
    assert limited["output"]["write_success_count"] < limited["output"]["attempted_ticks"]

    failed = run_runtime_bench(
        RuntimeBenchOptions(mode="fake", scenario="fake_output_failure", duration_ms=180, output_dir=tmp_path / "failed")
    ).summary
    assert failed["output"]["write_failure_count"] > 0
    assert failed["output"]["safety_stop_state"] is True
    assert failed["output"]["neutral_restore_status"] in {"not_attempted", "failed", "restored"}

    unverified = run_runtime_bench(
        RuntimeBenchOptions(mode="fake", scenario="fake_output_unverified", duration_ms=180, output_dir=tmp_path / "unverified")
    ).summary
    assert unverified["output"]["write_success_count"] == 0
    assert unverified["output"]["verification_status"] in {"not_attempted", "fake_verified"}
    assert unverified["runtime_truth"]["full_live_runtime_ready"] is False


def test_hf_lrdc_4a_real_mode_missing_hardware_is_honest_not_ci_failure(tmp_path):
    from bridge_app.runtime_bench import RuntimeBenchOptions, run_runtime_bench

    result = run_runtime_bench(
        RuntimeBenchOptions(mode="real", scenario="manual_watch", duration_ms=120, output_dir=tmp_path, require_hotas=False)
    )

    assert result.summary["fake_or_real_path"] == "real"
    assert result.summary["runtime_truth"]["full_live_runtime_ready"] is False
    assert "real hardware validation remains bench-only" in " ".join(result.summary["warnings"])


def test_hf_lrdc_4a_cli_parses_and_short_fake_smoke_writes_summary(tmp_path):
    from scripts.run_hf_lrdc_runtime_bench import build_parser, main

    args = build_parser().parse_args(
        ["--mode", "fake", "--scenario", "axis_sweep_roll", "--duration-ms", "100", "--output", str(tmp_path)]
    )
    assert args.mode == "fake"
    assert args.scenario == "axis_sweep_roll"
    assert args.duration_ms == 100

    assert main(["--mode", "fake", "--scenario", "axis_sweep_roll", "--duration-ms", "100", "--output", str(tmp_path)]) == 0
    summaries = list(Path(tmp_path).glob("*/summary.json"))
    assert summaries
    data = json.loads(summaries[0].read_text(encoding="utf-8"))
    assert data["scenario"] == "axis_sweep_roll"
    assert data["pass"] is True
    shutil.rmtree(Path(__file__).resolve().parents[1] / "scripts" / "__pycache__", ignore_errors=True)


def test_hf_lrdc_4a_frame_log_tracks_sequences_and_duplicate_truth(tmp_path):
    from bridge_app.runtime_bench import RuntimeBenchOptions, run_runtime_bench

    result = run_runtime_bench(
        RuntimeBenchOptions(mode="fake", scenario="multi_axis_mixed", duration_ms=160, output_dir=tmp_path)
    )

    frames = result.artifact_dir.joinpath("frames.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert frames
    first = json.loads(frames[0])
    assert "sequence" in first
    assert "tick_duration_ms" in first
    assert result.summary["telemetry"]["duplicate_or_repeated_frame_count"] == 0
