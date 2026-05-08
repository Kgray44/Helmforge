from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase18d_packaging_docs_freeze_phase18_and_handoff_to_phase19():
    packaging_readme = _read(PROJECT_ROOT / "packaging" / "README.md")
    root_readme = _read(PROJECT_ROOT / "README.md")
    report = _read(PROJECT_ROOT / "docs" / "HelmForge" / "phase-18d-final-packaging-qa-report.md")

    for text in (packaging_readme, root_readme, report):
        assert "Phase 18D" in text
        assert "Phase 18 is now complete" in text
        assert "Phase 19: Final Integration Kraken / Full Acceptance Sweep" in text
        assert "one-folder build" in text
        assert "packaging/dist/HelmForge/HelmForge.exe" in text
        assert "packaging/inno/helmforge.iss" in text
        assert "Full Live Runtime Ready" in text
        assert "does not add runtime authority" in text
        assert "signed production installer" not in text.casefold()


def test_phase18d_build_and_installer_metadata_remain_safe_and_explicit():
    build_script = _read(PROJECT_ROOT / "packaging" / "build_release.ps1")
    inno_script = _read(PROJECT_ROOT / "packaging" / "inno" / "helmforge.iss")

    for required in (
        "[switch]$DryRun",
        "[switch]$Clean",
        "[switch]$BuildInstaller",
        "[switch]$SkipInstaller",
        "[string]$InnoPath",
        "Resolve-InnoCompiler",
        "PyInstaller one-folder build",
        "packaging\\dist\\HelmForge\\HelmForge.exe --smoke-exit-ms 250",
        "packaging\\inno\\helmforge.iss",
        "Inno Setup compiler was not found",
    ):
        assert required in build_script

    for forbidden in (
        "Start-Process",
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Enable Auto Start",
        "Install Service",
        "Remove-Item -LiteralPath $RepoRoot",
        "Remove-Item -LiteralPath $env:LOCALAPPDATA",
        "Remove-Item -LiteralPath $env:APPDATA",
    ):
        assert forbidden.casefold() not in build_script.casefold()

    assert "DefaultDirName={localappdata}\\Programs\\HelmForge" in inno_script
    assert 'Name: "{group}\\HelmForge"; Filename: "{app}\\HelmForge.exe"' in inno_script
    assert 'Name: "{autodesktop}\\HelmForge"; Filename: "{app}\\HelmForge.exe"; Tasks: desktopicon' in inno_script
    assert "UninstallDisplayName={#AppDisplayName}" in inno_script
    assert "{localappdata}\\HelmForge\\*" not in inno_script
    assert "[Registry]" not in inno_script
    assert "[RunOnce]" not in inno_script
    assert "{commonstartup}" not in inno_script.casefold()
    assert "vJoySetup" not in inno_script
    assert "StartBridge" not in inno_script


def test_phase18d_resource_user_data_and_icon_truth_are_documented():
    from v3_app.services.app_paths import get_user_data_paths, resolve_resource_path

    report = _read(PROJECT_ROOT / "docs" / "HelmForge" / "phase-18d-final-packaging-qa-report.md")
    packaging_readme = _read(PROJECT_ROOT / "packaging" / "README.md")

    paths = get_user_data_paths({"LOCALAPPDATA": r"C:\Users\Example\AppData\Local"})
    assert paths.root == Path(r"C:\Users\Example\AppData\Local\HelmForge")
    assert paths.config == paths.root / "config"
    assert paths.profiles == paths.root / "profiles"
    assert paths.logs == paths.root / "logs"
    assert paths.recordings == paths.root / "recordings"
    assert paths.artifacts == paths.root / "artifacts"
    assert resolve_resource_path("README.md").exists()

    for text in (report, packaging_readme):
        assert "%LocalAppData%\\Programs\\HelmForge" in text
        assert "%LocalAppData%\\HelmForge" in text
        assert "user data is preserved" in text
        assert "assets/app_icon.ico is missing" in text
        assert "icon conversion remains deferred" in text
        assert "ISCC.exe" in text


def test_phase18d_report_contains_phase19_readiness_checklist_and_runtime_boundaries():
    report = _read(PROJECT_ROOT / "docs" / "HelmForge" / "phase-18d-final-packaging-qa-report.md")

    for heading in (
        "Phase 18A Summary",
        "Phase 18B Summary",
        "Phase 18C Summary",
        "Phase 18D QA Summary",
        "Build Script Status",
        "One-Folder Build Status",
        "Packaged Smoke Result",
        "Installer Script Status",
        "Installer Compile Result",
        "Icon Status",
        "User Data Separation Status",
        "Resource Path Status",
        "Runtime Truth Preservation",
        "Known Remaining Packaging Issues",
        "Phase 19 Readiness Checklist",
    ):
        assert heading in report

    for checklist_item in (
        "App shell",
        "Mapping",
        "Base Tuning",
        "Filtering",
        "Conditional Rules",
        "Effective Response Stack",
        "Live Monitor",
        "Helm",
        "Live Overlay",
        "Flight Recorder",
        "Help / Docs",
        "Perf / Diagnostics",
        "Full Live Runtime Ready gate",
        "Packaging",
        "Installer if available",
    ):
        assert checklist_item in report

    for forbidden in (
        "automatic Bridge launch was added",
        "driver installer launch was added",
        "vJoy output behavior changed",
        "cloud AI behavior was added",
        "auto-save was added",
    ):
        assert forbidden.casefold() not in report.casefold()
