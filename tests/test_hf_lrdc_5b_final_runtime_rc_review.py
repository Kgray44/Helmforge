from __future__ import annotations

from pathlib import Path


REPORT = Path("docs/HelmForge/hf-lrdc-5b-final-live-runtime-rc-review-report.md")


def _report_text() -> str:
    return REPORT.read_text(encoding="utf-8")


def test_hf_lrdc_5b_final_report_exists_and_has_required_sections():
    text = _report_text()

    for heading in (
        "## Executive Summary",
        "## Phase Completion Checklist",
        "## Runtime Chain Verification",
        "## Artifact Summary",
        "## Gate Summary",
        "## Fake vs Real Proof Boundary",
        "## Known Limitations",
        "## Final Decision",
        "## Runtime Truth Preservation",
    ):
        assert heading in text


def test_hf_lrdc_5b_release_posture_is_valid_and_not_real_ready():
    text = _report_text()
    valid_postures = {
        "rc_freeze_ready",
        "fake_path_pass_real_path_unproven",
        "blocked_missing_hardware_proof",
        "blocked_output_verification",
        "blocked_telemetry_transport",
        "blocked_runtime_truth",
        "blocked_tests",
        "blocked_unknown",
    }

    assert any(f"release_posture: {posture}" in text for posture in valid_postures)
    assert "proof_kind: fake" in text
    assert "real_path_acceptance: blocked_missing_hardware_proof" in text
    assert "Full Live Runtime Ready: false" in text


def test_hf_lrdc_5b_documents_telemetry_blocks_and_source_priority():
    text = _report_text()

    for block in (
        "runtime_frame",
        "bridge_timing",
        "physical_input_fidelity",
        "physical_input_backend_choice",
        "bridge_workspace",
        "output_loop_runtime",
        "telemetry_stream",
        "last_command",
        "device_discovery",
        "warnings/errors",
    ):
        assert block in text
    assert "Bridge Stream > Bridge JSON Snapshot > Simulation Fallback" in text


def test_hf_lrdc_5b_truth_language_forbids_bad_equivalences():
    text = _report_text()

    forbidden = (
        "stream connected = output verified",
        "vJoy detected = output verified",
        "physical input = vJoy writes",
        "config match = live output",
        "manual pass = Full Live Runtime Ready",
    )
    for phrase in forbidden:
        assert phrase not in text

    required_truth = (
        "Fake-path acceptance does not equal real Full Live Runtime Ready",
        "Output intent is not output write proof",
        "vJoy detected is not output verification",
        "Manual operator confirmation does not override runtime proof gates",
    )
    for phrase in required_truth:
        assert phrase in text
