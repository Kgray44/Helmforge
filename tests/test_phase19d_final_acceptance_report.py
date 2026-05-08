from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT = PROJECT_ROOT / "docs" / "HelmForge" / "final-acceptance-report.md"
README = PROJECT_ROOT / "README.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase19d_final_acceptance_report_exists_and_freezes_rc_classification():
    assert REPORT.exists()
    report = _read(REPORT)

    for required in (
        "# HelmForge Final Acceptance Report",
        "Product name: HelmForge",
        "Technical subtitle: HOTAS Control Panel V3",
        "Final status",
        "RC classification: RC Ready With Known Non-Blocking Gaps",
        "Prompt-Book Coverage Summary",
        "Phase 0-19 Summary",
        "Phase 19A Inventory Summary",
        "Phase 19B Kraken Summary",
        "Phase 19C Correction Summary",
        "Packaging Status",
        "Runtime Truth Status",
        "Known Gaps",
        "Release Blockers vs Non-Blocking Gaps",
        "Final Recommendation",
        "Next Actions",
        "Final Freeze Statement",
    ):
        assert required in report

    for assumption in (
        "missing `assets/app_icon.ico` is accepted as a non-blocking RC gap",
        "Inno compile skip due to missing `ISCC.exe` is accepted as a non-blocking RC gap",
        "installer install/uninstall execution is not required for this RC",
        "signed production metadata is not required for this RC",
        "live HOTAS/vJoy Full Live Runtime Ready proof is not required for this RC",
        "simulation-first packaged launch is acceptable for this RC",
    ):
        assert assumption in report


def test_phase19d_acceptance_table_and_final_evidence_are_present():
    report = _read(REPORT)

    assert "| Area | Acceptance status | Final note |" in report
    for area in (
        "App shell",
        "Runtime setup",
        "Mapping",
        "Modes / Base Tuning / Filtering / Combat / Profiles",
        "Conditional Rules",
        "Effective Response Stack",
        "Live Monitor",
        "Helm",
        "Live Overlay",
        "Flight Recorder",
        "Help / Docs",
        "Perf / Diagnostics",
        "Runtime truth / Full Live Runtime Ready gate",
        "Packaging one-folder build",
        "Installer metadata",
        "Safety boundaries",
        "Layout / performance",
        "Real hardware acceptance",
    ):
        assert area in report

    for status in ("Pass", "Partial", "Blocked", "Deferred Truthfully"):
        assert status in report

    for required in (
        "19 pass",
        "0 fail",
        "1 skipped",
        "packaged app smoke passed",
        "source app smoke passed",
        "Bridge smoke passed",
        "runtime setup dry-run passed",
        "git diff --check",
    ):
        assert required in report


def test_phase19d_report_records_runtime_and_packaging_truth_without_overclaiming():
    report = _read(REPORT)
    lower_report = report.casefold()

    for required in (
        "packaging/dist/HelmForge/",
        "packaging/dist/HelmForge/HelmForge.exe",
        "packaging/inno/helmforge.iss",
        "%LocalAppData%\\HelmForge",
        "%LocalAppData%\\Programs\\HelmForge",
        "assets/app_icon.ico is missing",
        "ISCC.exe",
        "installer compile skipped",
        "no installer binary is claimed",
        "packaged smoke is not runtime readiness",
        "Full Live Runtime Ready requires the Phase 16 proof gate",
        "no Bridge lifecycle management",
        "user data preserved on uninstall by default",
        "installer does not install drivers/vJoy",
    ):
        assert required in report

    for required in (
        "telemetry remains the truth surface",
        "command files are requests, not success proof",
        "process presence is a hint only",
        "physical input alone is not full readiness",
        "output intent is not output write proof",
        "vjoy detected does not equal output verified",
        "fake/mock output is not real output",
        "simulation mode remains available",
        "bridge lifecycle management is not implemented",
    ):
        assert required in lower_report

    for forbidden in (
        "installer binary exists",
        "Full Live Runtime Ready from packaging smoke",
        "driver/vJoy installer launch added",
        "Bridge lifecycle management added",
        "new runtime behavior added",
    ):
        assert forbidden.casefold() not in lower_report


def test_phase19d_readme_points_to_final_report_and_preserves_boundaries():
    assert README.exists()
    readme = _read(README)

    for required in (
        "Phase 19D final acceptance status",
        "RC Ready With Known Non-Blocking Gaps",
        "docs/HelmForge/final-acceptance-report.md",
        "packaging/dist/HelmForge/HelmForge.exe",
        "assets/app_icon.ico is missing",
        "packaged smoke is not runtime readiness",
        "Full Live Runtime Ready remains governed by the Phase 16 proof gate",
        "no Bridge lifecycle management",
    ):
        assert required in readme


def test_phase19d_report_identifies_next_actions_and_no_new_authority():
    report = _read(REPORT)

    for required in (
        "provide `assets/app_icon.ico`",
        "compile the Inno installer on a machine with `ISCC.exe`",
        "run installer install/uninstall QA",
        "perform live HOTAS/vJoy readiness proof if hardware acceptance is required",
        "No new runtime authority was added",
        "No new hardware/output/Bridge lifecycle behavior was added",
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
        "cloud AI added",
        "auto-save added",
    ):
        assert forbidden.casefold() not in report.casefold()
