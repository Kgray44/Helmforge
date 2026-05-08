from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HARNESS = PROJECT_ROOT / "scripts" / "run_phase19b_kraken.py"
REPORT = PROJECT_ROOT / "docs" / "HelmForge" / "phase-19b-integration-kraken-regression-sweep-report.md"

REQUIRED_SECTIONS = (
    "source_app_smoke",
    "packaged_app_smoke",
    "bridge_smoke",
    "runtime_setup_dry_run",
    "page_navigation_smoke",
    "help_docs_search_smoke",
    "perf_diagnostics_copy_smoke",
    "helm_overlay_smoke",
    "live_overlay_smoke",
    "flight_recorder_smoke",
    "packaging_metadata_smoke",
    "installer_metadata_smoke",
    "runtime_truth_boundary_smoke",
    "full_live_runtime_ready_gate_smoke",
    "safety_boundary_smoke",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase19b_kraken_harness_exists_and_lists_required_sections():
    assert HARNESS.exists()

    completed = subprocess.run(
        [sys.executable, str(HARNESS), "--list-sections"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr

    for section in REQUIRED_SECTIONS:
        assert section in completed.stdout


def test_phase19b_kraken_dry_run_writes_schema_artifacts(tmp_path):
    output_root = tmp_path / "kraken"
    completed = subprocess.run(
        [sys.executable, str(HARNESS), "--dry-run", "--output-root", str(output_root)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr

    artifact_dirs = [path for path in output_root.iterdir() if path.is_dir()]
    assert len(artifact_dirs) == 1
    artifact_dir = artifact_dirs[0]
    results_path = artifact_dir / "phase19b_kraken_results.json"
    rows_path = artifact_dir / "phase19b_kraken_rows.jsonl"
    summary_path = artifact_dir / "phase19b_kraken_summary.md"
    assert results_path.exists()
    assert rows_path.exists()
    assert summary_path.exists()

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "19B"
    assert payload["artifact_dir"] == str(artifact_dir)
    assert set(REQUIRED_SECTIONS) <= set(payload["sections"])
    assert {"pass", "fail", "skipped"} <= set(payload["counts"])

    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    assert set(REQUIRED_SECTIONS) <= {row["section"] for row in rows}
    assert all(row["status"] in {"pass", "fail", "skipped"} for row in rows)

    summary = summary_path.read_text(encoding="utf-8")
    for word in ("pass", "fail", "skipped", "packaged_app_smoke", "installer_metadata_smoke"):
        assert word in summary


def test_phase19b_harness_static_contract_mentions_safety_and_packaging_boundaries():
    source = _read(HARNESS)

    for required in (
        ".artifacts",
        "phase19b_kraken",
        "packaging/dist/HelmForge/HelmForge.exe --smoke-exit-ms 250",
        "no fake readiness",
        "no Bridge lifecycle management",
        "no driver/vJoy installer launch",
        "no cloud AI/LLM",
        "no auto-save",
        "Full Live Runtime Ready proof gate",
    ):
        assert required in source

    for forbidden in (
        "Start-Process",
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "keyboard.add_hotkey",
        "VideoWriter",
        "OpenAI(",
    ):
        assert forbidden not in source


def test_phase19b_report_documents_harness_results_and_next_phase():
    assert REPORT.exists()
    report = _read(REPORT)

    for required in (
        "Harness Design",
        "Sections Run",
        "Artifacts Written",
        "Pass / Fail / Skipped Summary",
        "Source App Smoke Result",
        "Packaged App Smoke Result",
        "Bridge Smoke Result",
        "Runtime Setup Dry-Run Result",
        "Page Navigation Smoke Result",
        "Help / Docs Smoke Result",
        "Perf / Diagnostics Smoke Result",
        "Packaging / Installer Metadata Smoke Result",
        "Full Live Runtime Ready Gate Result",
        "Safety Boundary Result",
        "Known Failures / Blockers",
        "Recommendation For Phase 19C",
    ):
        assert required in report

    for required in (
        "no fake readiness",
        "no Bridge lifecycle management",
        "no driver/vJoy installer launch",
        "packaged smoke",
        "ISCC.exe",
    ):
        assert required in report
