from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase18c_inno_script_defines_app_shortcuts_uninstall_and_user_data_policy():
    script_path = PROJECT_ROOT / "packaging" / "inno" / "helmforge.iss"
    assert script_path.exists()
    script = _read(script_path)

    for required in (
        '#define AppName "HelmForge"',
        '#define AppDisplayName "HelmForge - HOTAS Control Panel V3"',
        "AppVersion={#AppVersion}",
        "AppPublisher={#AppPublisher}",
        "DefaultDirName={localappdata}\\Programs\\HelmForge",
        "PrivilegesRequired=lowest",
        "UninstallDisplayName={#AppDisplayName}",
        "UninstallDisplayIcon={app}\\HelmForge.exe",
        'Name: "{group}\\HelmForge"; Filename: "{app}\\HelmForge.exe"',
        'Name: "{autodesktop}\\HelmForge"; Filename: "{app}\\HelmForge.exe"; Tasks: desktopicon',
        'Name: "desktopicon"',
        'Name: "launchafterinstall"',
        "User data under {localappdata}\\HelmForge is preserved",
    ):
        assert required in script

    for forbidden in (
        "vJoySetup",
        "driver installer",
        "InstallService",
        "ServiceInstall",
        "runascurrentuser",
        "runasoriginaluser",
        "Startup",
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "{localappdata}\\HelmForge\\*",
    ):
        assert forbidden.casefold() not in script.casefold()


def test_phase18c_build_script_supports_optional_installer_without_requiring_inno():
    script = _read(PROJECT_ROOT / "packaging" / "build_release.ps1")

    for required in (
        "[switch]$BuildInstaller",
        "[switch]$SkipInstaller",
        "[string]$InnoPath",
        "Resolve-InnoCompiler",
        "ISCC.exe",
        "packaging\\inno\\helmforge.iss",
        "packaging\\installer",
        "/DAppVersion=$AppVersion",
        "-BuildInstaller was requested",
        "No installer was created",
    ):
        assert required in script

    assert "PyInstaller one-folder build" in script
    assert "if ($BuildInstaller)" in script
    assert "throw \"Inno Setup compiler was not found" in script


def test_phase18c_icon_wiring_is_truthful_for_missing_or_present_ico():
    icon = PROJECT_ROOT / "assets" / "app_icon.ico"
    build_script = _read(PROJECT_ROOT / "packaging" / "build_release.ps1")
    inno_script = _read(PROJECT_ROOT / "packaging" / "inno" / "helmforge.iss")
    report = _read(PROJECT_ROOT / "docs" / "HelmForge" / "phase-18c-icons-installer-shortcuts-report.md")

    assert "AppIconPath" in build_script
    assert "--icon" in build_script
    assert "#if FileExists(AppIcon)" in inno_script
    assert "SetupIconFile={#AppIcon}" in inno_script

    if icon.exists():
        assert "PyInstaller icon wiring: complete" in report
    else:
        assert "PyInstaller icon wiring: deferred because assets/app_icon.ico is missing" in report
        assert "Icon conversion remains required" in report


def test_phase18c_docs_report_and_readme_explain_installer_without_signed_release_claim():
    packaging_readme = _read(PROJECT_ROOT / "packaging" / "README.md")
    inno_readme = _read(PROJECT_ROOT / "packaging" / "inno" / "README.md")
    phase_ledger = _read(PROJECT_ROOT / "docs" / "HelmForge" / "phase-ledger.md")
    report = _read(PROJECT_ROOT / "docs" / "HelmForge" / "phase-18c-icons-installer-shortcuts-report.md")

    for text in (packaging_readme, inno_readme, phase_ledger, report):
        assert "Phase 18C" in text
        assert "Start Menu shortcut" in text
        assert "optional Desktop shortcut" in text
        assert "uninstall" in text.casefold()
        assert "does not install drivers" in text
        assert "does not manage Bridge lifecycle" in text
        assert "user data is preserved" in text
        assert "signed production installer" not in text.casefold()
    root_readme = _read(PROJECT_ROOT / "README.md")
    assert "Phase 18C" not in root_readme

    for required in (
        "Icon Asset Status",
        "PyInstaller Icon Wiring Status",
        "Inno Script Path",
        "Installer Tasks",
        "Shortcut Behavior",
        "Uninstall Behavior",
        "Installer Build Result",
        "Packaged Smoke Result",
        "Remaining Phase 18D Work",
    ):
        assert required in report


def test_phase18c_version_metadata_is_central_and_used_by_packaging():
    from v3_app.version import APP_VERSION, APP_VERSION_TAG

    assert APP_VERSION == "0.1.0-dev"
    assert APP_VERSION_TAG == f"v{APP_VERSION}"

    build_script = _read(PROJECT_ROOT / "packaging" / "build_release.ps1")
    report = _read(PROJECT_ROOT / "docs" / "HelmForge" / "phase-18c-icons-installer-shortcuts-report.md")
    assert "v3_app.version" in build_script
    assert APP_VERSION in report
