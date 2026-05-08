from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT = PROJECT_ROOT / "docs" / "HelmForge" / "phase-19c-final-corrections-report.md"
ARTIFACT_ROOT = PROJECT_ROOT / ".artifacts" / "phase19b_kraken"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _referenced_artifact_dir(report_text: str) -> Path:
    match = re.search(r"\.artifacts/phase19b_kraken/[0-9TZ-]+", report_text)
    assert match, "Phase 19C report should name the reviewed Kraken artifact path."
    return PROJECT_ROOT / Path(match.group(0))


def test_phase19c_report_exists_and_summarizes_phase19b_artifacts():
    assert REPORT.exists()
    report = _read(REPORT)

    for required in (
        "Phase 19B Result Summary",
        "Kraken Artifact Path Reviewed",
        "Failures Found",
        "Skipped Items",
        "Known Blockers",
        "Corrections Made",
        "Corrections Intentionally Not Made",
        "Remaining Release Blockers",
        "Recommendation For Phase 19D",
        "RC Ready With Known Non-Blocking Gaps",
    ):
        assert required in report

    assert "19 pass" in report
    assert "0 fail" in report
    assert "1 skipped" in report
    assert "No failures were found" in report
    assert "installer compile" in report
    assert "ISCC.exe is unavailable" in report


def test_phase19c_report_and_artifact_schema_record_known_truths():
    report = _read(REPORT)
    artifact_dir = _referenced_artifact_dir(report)
    results_path = artifact_dir / "phase19b_kraken_results.json"
    summary_path = artifact_dir / "phase19b_kraken_summary.md"
    rows_path = artifact_dir / "phase19b_kraken_rows.jsonl"
    assert results_path.exists()
    assert summary_path.exists()
    assert rows_path.exists()

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert payload["counts"] == {"pass": 19, "fail": 0, "skipped": 1}
    assert "packaged_app_smoke" in payload["sections"]
    assert "runtime_truth_boundary_smoke" in payload["sections"]
    assert "full_live_runtime_ready_gate_smoke" in payload["sections"]
    assert "safety_boundary_smoke" in payload["sections"]

    rows = payload["rows"]
    skipped = [row for row in rows if row["status"] == "skipped"]
    assert len(skipped) == 1
    assert skipped[0]["section"] == "installer_metadata_smoke"
    assert skipped[0]["check"] == "installer_compile"
    assert "ISCC.exe unavailable" in skipped[0]["message"]

    packaged_rows = [row for row in rows if row["section"] == "packaged_app_smoke"]
    assert any(row["status"] == "pass" and row["check"] == "packaged_smoke_launch" for row in packaged_rows)


def test_phase19c_docs_do_not_overclaim_installer_icon_or_runtime_readiness():
    report = _read(REPORT)
    root_readme = _read(PROJECT_ROOT / "README.md")
    packaging_readme = _read(PROJECT_ROOT / "packaging" / "README.md")
    phase19b = _read(PROJECT_ROOT / "docs" / "HelmForge" / "phase-19b-integration-kraken-regression-sweep-report.md")

    combined = "\n".join((report, root_readme, packaging_readme, phase19b))
    assert "assets/app_icon.ico is missing" in combined
    assert "icon embedding remains a known packaging blocker" in report
    assert "No installer binary is claimed" in report
    assert "Real hardware Full Live Runtime Ready proof is not claimed" in report
    assert "packaging smoke is not runtime readiness" in report
    assert "Phase 19D" in report

    for forbidden in (
        "signed production installer exists",
        "final installer binary exists",
        "Full Live Runtime Ready from packaging smoke",
        "Release Candidate Ready without gaps",
    ):
        assert forbidden.casefold() not in combined.casefold()


def test_phase19c_no_runtime_authority_or_bridge_lifecycle_added():
    report = _read(REPORT)
    harness = _read(PROJECT_ROOT / "scripts" / "run_phase19b_kraken.py")
    source_text = "\n".join((report, harness))

    for required in (
        "no new runtime behavior",
        "no Bridge lifecycle management",
        "no driver/vJoy installer launch",
        "no cloud AI/LLM",
        "no auto-save",
    ):
        assert required in report

    for forbidden in (
        "StartBridge control added",
        "StopBridge control added",
        "RestartBridge control added",
        "driver installer launch added",
        "new hardware polling added",
        "vJoy output behavior changed",
        "recorder capture added",
        "OpenAI(",
    ):
        assert forbidden.casefold() not in source_text.casefold()
