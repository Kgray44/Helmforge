from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase18b_build_script_runs_real_onedir_path_without_installer_authority():
    script = _read(PROJECT_ROOT / "packaging" / "build_release.ps1")

    for required in (
        "[switch]$DryRun",
        "[switch]$Clean",
        "Build mode",
        "--onedir",
        "--windowed",
        "--name",
        "HelmForge",
        "--distpath",
        "$DistRoot",
        "--workpath",
        "$BuildRoot",
        "--specpath",
        "$OutputRoot",
        "--hidden-import",
        "bridge_app.main",
        "--exclude-module",
        "pytest",
        "packaging\\dist\\HelmForge\\HelmForge.exe --smoke-exit-ms 250",
        "No installer was created",
        "[switch]$BuildInstaller",
        "Resolve-InnoCompiler",
    ):
        assert required in script

    for forbidden in (
        "Start-Process",
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "LaunchInstallers",
        "Enable Auto Start",
        "Install Service",
    ):
        assert forbidden.casefold() not in script.casefold()

    assert "Inno Setup compiler" in script
    assert "No installer was created" in script


def test_phase18b_packaging_docs_document_output_and_smoke_without_installer_claim():
    packaging_readme = _read(PROJECT_ROOT / "packaging" / "README.md")
    pyinstaller_readme = _read(PROJECT_ROOT / "packaging" / "pyinstaller" / "README.md")
    readme = _read(PROJECT_ROOT / "README.md")

    for text in (packaging_readme, pyinstaller_readme, readme):
        assert "Phase 18B" in text
        assert "one-folder" in text
        assert "packaging/dist/HelmForge/HelmForge.exe" in text
        assert "--smoke-exit-ms 250" in text
        assert "does not create an installer" in text
        assert "simulation mode" in text
        assert "Full Live Runtime Ready" in text
        assert "installer is complete" not in text.casefold()

    for text in (packaging_readme, pyinstaller_readme):
        assert "StartBridge" not in text
        assert "StopBridge" not in text
        assert "RestartBridge" not in text


def test_phase18b_resource_helper_supports_source_and_frozen_roots(tmp_path):
    from v3_app.services.app_paths import get_resource_root, resolve_resource_path, source_tree_root

    frozen_root = tmp_path / "frozen"
    frozen_root.mkdir()
    (frozen_root / "marker.txt").write_text("packaged", encoding="utf-8")

    assert source_tree_root() == PROJECT_ROOT
    assert get_resource_root(pyinstaller_root=frozen_root) == frozen_root
    assert resolve_resource_path("marker.txt", pyinstaller_root=frozen_root) == frozen_root / "marker.txt"
    assert resolve_resource_path("README.md").exists()


def test_phase18b_report_records_build_smoke_and_remaining_installer_gap():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-18b-pyinstaller-one-folder-build-report.md"
    assert report.exists()
    text = _read(report)

    for required in (
        "Phase 18B",
        "Build Command",
        "Output Path",
        "Packaged Executable Path",
        "Packaged Smoke Result",
        "Missing HOTAS/vJoy Behavior",
        "Resource Path Notes",
        "Icon Status",
        "Known Packaging Gaps",
        "What Remains For Phase 18C",
        "No final installer release",
    ):
        assert required in text


def test_phase18b_build_config_does_not_bundle_forensic_docs_or_local_runtime_authority():
    script = _read(PROJECT_ROOT / "packaging" / "build_release.ps1")
    packaging_docs = "\n".join(
        _read(path)
        for path in (
            PROJECT_ROOT / "packaging" / "README.md",
            PROJECT_ROOT / "packaging" / "pyinstaller" / "README.md",
            PROJECT_ROOT / "docs" / "HelmForge" / "phase-18b-pyinstaller-one-folder-build-report.md",
        )
    )

    for forbidden in (
        "HOTAS Control Panel Forensic Spec Set",
        "--add-data .git",
        "--add-data tests",
        "--add-data .pytest_cache",
        "--add-data .venv",
        "--add-data recordings",
        "driver installer launch",
        "service install",
        "login auto-start",
        "tray manager",
        "recorder capture",
        "graphics API hooking",
        "OpenAI(",
    ):
        assert forbidden.casefold() not in script.casefold()

    assert "forensic documents are not bundled" in packaging_docs.casefold()
    assert "no final installer release" in packaging_docs.casefold()
