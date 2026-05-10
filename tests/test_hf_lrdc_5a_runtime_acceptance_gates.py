from __future__ import annotations

import json
import shutil
from pathlib import Path


def _telemetry(**overrides):
    payload = {
        "timestamp": "2026-05-10T12:00:00+00:00",
        "runtime_truth": "blocked_missing_device",
        "output_verified": False,
        "output_status": "vjoy_detected",
        "raw_axes": {"Roll": 0.1},
        "final_axes": {"Roll": 0.2},
        "bridge_timing": {
            "tick_count": 20,
            "last_tick_duration_ms": 2.5,
            "last_discovery_age_ms": 4500.0,
            "fast_loop_status": "healthy",
            "slow_lane_status": "idle",
        },
        "physical_input_fidelity": {
            "backend_name": "fake_physical_input_backend",
            "backend_kind": "fake",
            "sample_age_ms": 1.0,
            "read_duration_ms": 0.2,
            "mapping_status": "ok",
        },
        "physical_input_backend_choice": {
            "selected_backend_name": "fake_physical_input_backend",
            "selected_backend_kind": "fake",
            "fallback_used": False,
        },
        "telemetry_source": {
            "source": "Bridge Stream",
            "fresh": True,
            "stale": False,
        },
        "live_monitor": {
            "accepted_frame_cadence_hz": 58.0,
            "repeated_frame_count": 0,
            "duplicate_frames_accepted": False,
            "latest_bridge_frame_age_ms": 18.0,
        },
        "bridge_workspace": {
            "workspace_hash": "abc123",
            "workspace_revision": "abc123",
            "config_status": "loaded",
        },
        "ui_workspace_hash": "abc123",
        "runtime_frame": {
            "sequence": 10,
            "output_intent_ready": True,
            "full_live_runtime_ready": False,
            "blocked_reason": "blocked_unverified_output",
        },
        "output_loop_runtime": {
            "state": "disabled",
            "verification_status": "fake_verified",
            "verification_fake": True,
            "verification_real": False,
            "write_rate_hz": 30.0,
            "write_success_count": 0,
            "write_failure_count": 0,
            "write_skipped_count": 4,
            "write_skipped_rate_limited_count": 1,
            "safety_stop_reason": "None",
            "neutral_restore_status": "not_attempted",
            "loop_recreated_count": 0,
        },
    }
    payload.update(overrides)
    return payload


def _fake_bench_summary(**overrides):
    summary = {
        "pass": True,
        "mode": "fake",
        "fake_or_real_path": "fake",
        "input": {"sample_count": 12, "backend_kind": "fake"},
        "pipeline": {"final_output_changes_observed": 5, "pipeline_error_count": 0},
        "output": {
            "write_success_count": 0,
            "write_failure_count": 0,
            "write_skipped_count": 2,
            "write_skipped_rate_limited_count": 1,
            "verification_status": "fake_verified",
        },
        "telemetry": {
            "json_snapshot_frame_count": 12,
            "duplicate_or_repeated_frame_count": 0,
            "source_used": "Bridge JSON Snapshot",
        },
        "runtime_truth": {
            "full_live_runtime_ready": False,
            "real_output_verified": False,
            "fake_output_verified": True,
        },
        "warnings": ["fake backend proof is fake-path proof only"],
        "errors": [],
    }
    summary.update(overrides)
    return summary


def _manual_result(**overrides):
    result = {
        "overall_status": "passed",
        "mode": "manual",
        "bridge_source": "Bridge Stream",
        "steps": [
            {"step_id": "telemetry_readiness", "status": "passed"},
            {"step_id": "output_proof_status", "status": "blocked"},
        ],
    }
    result.update(overrides)
    return result


def test_hf_lrdc_5a_gate_model_counts_and_rc_readiness():
    from shared_core.runtime.runtime_acceptance import (
        AcceptanceGateStatus,
        AcceptanceProofKind,
        RuntimeAcceptanceGate,
        RuntimeAcceptanceReport,
    )

    report = RuntimeAcceptanceReport(
        source="unit",
        proof_kind=AcceptanceProofKind.FAKE,
        gates=[
            RuntimeAcceptanceGate("a", "A", AcceptanceGateStatus.PASSED, AcceptanceProofKind.FAKE),
            RuntimeAcceptanceGate("b", "B", AcceptanceGateStatus.WARNING, AcceptanceProofKind.FAKE),
            RuntimeAcceptanceGate(
                "c",
                "C",
                AcceptanceGateStatus.BLOCKED,
                AcceptanceProofKind.FAKE,
                blocked_reason="blocked",
            ),
        ],
    )

    result = report.result()
    assert result.passed_count == 1
    assert result.warning_count == 1
    assert result.blocked_count == 1
    assert result.ready_for_rc is False
    assert result.overall_status == "blocked"

    passed = RuntimeAcceptanceReport(
        source="unit",
        proof_kind=AcceptanceProofKind.FAKE,
        gates=[RuntimeAcceptanceGate("ok", "OK", AcceptanceGateStatus.PASSED, AcceptanceProofKind.FAKE)],
    )
    assert passed.result().ready_for_rc is True


def test_hf_lrdc_5a_fake_mode_acceptance_passes_without_real_claims():
    from shared_core.runtime.runtime_acceptance import RuntimeAcceptanceOptions, evaluate_runtime_acceptance

    report = evaluate_runtime_acceptance(
        RuntimeAcceptanceOptions(mode="fake"),
        telemetry=_telemetry(),
        bench_summary=_fake_bench_summary(),
        manual_validation=_manual_result(),
    )

    assert report.result().ready_for_rc is True
    assert report.proof_kind.value == "fake"
    assert report.full_live_runtime_ready is False
    assert report.fake_or_real_path == "fake"
    assert report.gate("full_live_runtime_ready").status.value == "passed"
    assert report.release_posture == "fake_path_pass_real_path_unproven"


def test_hf_lrdc_5a_real_mode_blocks_when_required_proof_is_missing():
    from shared_core.runtime.runtime_acceptance import RuntimeAcceptanceOptions, evaluate_runtime_acceptance

    report = evaluate_runtime_acceptance(
        RuntimeAcceptanceOptions(mode="real", require_hotas=True, require_vjoy=True, require_real_output=True),
        telemetry=_telemetry(),
        bench_summary=_fake_bench_summary(),
        manual_validation=_manual_result(),
    )

    assert report.result().ready_for_rc is False
    assert report.gate("physical_input_fidelity").status.value == "blocked"
    assert report.gate("vjoy_output_verification_truth").status.value == "blocked"
    assert report.gate("rc_freeze").status.value == "blocked"
    assert "real hardware proof" in report.gate("rc_freeze").blocked_reason


def test_hf_lrdc_5a_gate_checks_block_bad_evidence():
    from shared_core.runtime.runtime_acceptance import RuntimeAcceptanceOptions, evaluate_runtime_acceptance

    bad_telemetry = _telemetry(
        bridge_timing={},
        physical_input_fidelity={},
        bridge_workspace={"workspace_hash": "bridge"},
        ui_workspace_hash="ui",
        telemetry_source={"source": "Bridge Stream", "fresh": False, "stale": True},
        live_monitor={"accepted_frame_cadence_hz": 30.0, "repeated_frame_count": 4, "duplicate_frames_accepted": True},
        output_loop_runtime={"state": "safety_stopped", "safety_stop_reason": "write_failed"},
    )
    report = evaluate_runtime_acceptance(
        RuntimeAcceptanceOptions(mode="fake"),
        telemetry=bad_telemetry,
        bench_summary=_fake_bench_summary(**{"pass": False}),
    )

    assert report.gate("bridge_fast_loop_health").status.value == "blocked"
    assert report.gate("physical_input_fidelity").status.value == "blocked"
    assert report.gate("telemetry_source_truth").status.value == "blocked"
    assert report.gate("frame_dedupe_cadence").status.value == "blocked"
    assert report.gate("workspace_config_sync").status.value == "blocked"
    assert report.gate("output_cadence_safety").status.value == "blocked"
    assert report.gate("pipeline_output_intent").status.value == "passed"
    assert report.gate("vjoy_output_verification_truth").status.value != "passed"


def test_hf_lrdc_5a_export_writes_structured_artifacts(tmp_path):
    from shared_core.runtime.runtime_acceptance import RuntimeAcceptanceOptions, evaluate_runtime_acceptance, export_acceptance_report

    report = evaluate_runtime_acceptance(
        RuntimeAcceptanceOptions(mode="fake"),
        telemetry=_telemetry(),
        bench_summary=_fake_bench_summary(),
        manual_validation=_manual_result(),
    )
    artifacts = export_acceptance_report(report, tmp_path, evidence={"telemetry": _telemetry()})

    assert artifacts["summary_json"].exists()
    assert artifacts["summary_md"].exists()
    assert artifacts["gates_json"].exists()
    assert artifacts["evidence_json"].exists()
    summary = json.loads(artifacts["summary_json"].read_text(encoding="utf-8"))
    assert summary["ready_for_rc"] is True
    assert "Gate" in artifacts["summary_md"].read_text(encoding="utf-8")
    gates = json.loads(artifacts["gates_json"].read_text(encoding="utf-8"))
    assert any(gate["gate_id"] == "rc_freeze" for gate in gates)


def test_hf_lrdc_5a_cli_writes_artifacts_and_returns_status(tmp_path):
    from scripts.run_hf_lrdc_acceptance import build_parser, main

    parser = build_parser()
    args = parser.parse_args(["--mode", "fake", "--output", str(tmp_path)])
    assert args.mode == "fake"

    assert main(["--mode", "fake", "--output", str(tmp_path)]) == 0
    summaries = list(Path(tmp_path).glob("*/acceptance_summary.json"))
    assert summaries
    data = json.loads(summaries[0].read_text(encoding="utf-8"))
    assert data["proof_kind"] == "fake"
    assert data["ready_for_rc"] is True

    real_dir = tmp_path / "real"
    assert main(["--mode", "real", "--require-hotas", "--output", str(real_dir)]) == 1
    shutil.rmtree(Path(__file__).resolve().parents[1] / "scripts" / "__pycache__", ignore_errors=True)
