from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase18a_packaging_folder_and_docs_describe_foundation_only():
    packaging_root = PROJECT_ROOT / "packaging"
    assert (packaging_root / "README.md").exists()
    assert (packaging_root / "build_release.ps1").exists()
    assert (packaging_root / "pyinstaller" / "README.md").exists()
    assert (packaging_root / "inno" / "README.md").exists()

    packaging_readme = _read(packaging_root / "README.md")
    for required in (
        "Phase 18A",
        "one-folder build",
        "PyInstaller",
        "Inno Setup",
        "user data",
        "Smoke-test",
        "does not create an installer",
    ):
        assert required in packaging_readme

    assert "installer is complete" not in packaging_readme.casefold()
    assert "build verified" not in packaging_readme.casefold()


def test_phase18a_build_script_is_dry_run_safe_and_not_broadly_destructive():
    script = _read(PROJECT_ROOT / "packaging" / "build_release.ps1")

    assert "[switch]$DryRun" in script
    assert "[switch]$Clean" in script
    assert "helmforge = \"v3_app.main:main\"" in script
    assert "python -m PyInstaller" in script
    assert "Write-Phase18Log" in script
    assert "Resolve-RepoRoot" in script
    assert "packaging\\output" in script

    forbidden_fragments = (
        "Remove-Item -Recurse -Force $RepoRoot",
        "Remove-Item -Recurse -Force .",
        "Remove-Item -Recurse -Force $env:LOCALAPPDATA",
        "Remove-Item -Recurse -Force $env:APPDATA",
        "Start-Process",
        "makensis",
    )
    for forbidden in forbidden_fragments:
        assert forbidden.casefold() not in script.casefold()

    assert "Resolve-InnoCompiler" in script
    assert "[switch]$BuildInstaller" in script


def test_phase18a_user_data_and_resource_paths_are_packaging_safe(tmp_path, monkeypatch):
    from v3_app.services.app_paths import (
        APP_DISPLAY_NAME,
        APP_INTERNAL_NAME,
        get_assets_root,
        get_user_data_paths,
        resolve_resource_path,
        source_tree_root,
    )

    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.delenv("APPDATA", raising=False)

    paths = get_user_data_paths()
    assert APP_DISPLAY_NAME == "HelmForge"
    assert APP_INTERNAL_NAME == "HelmForge"
    assert paths.root == local_app_data / "HelmForge"
    assert paths.config == paths.root / "config"
    assert paths.profiles == paths.root / "profiles"
    assert paths.logs == paths.root / "logs"
    assert paths.recordings == paths.root / "recordings"
    assert paths.artifacts == paths.root / "artifacts"
    assert not paths.root.exists()

    source_root = source_tree_root()
    assert source_root == PROJECT_ROOT
    assert resolve_resource_path("README.md").exists()
    assert get_assets_root() == PROJECT_ROOT / "assets"


def test_phase18a_readme_report_and_help_docs_do_not_claim_completed_installer():
    from v3_app.services.help_docs import search_articles

    phase_ledger = _read(PROJECT_ROOT / "docs" / "HelmForge" / "phase-ledger.md")
    report = _read(PROJECT_ROOT / "docs" / "HelmForge" / "phase-18a-packaging-foundation-report.md")

    for text in (phase_ledger, report):
        assert "Phase 18A" in text
        assert "Packaging, Installer, Icons, and User Data Locations" in text
        assert "simulation mode" in text
        assert "does not implement a full installer" in text
        assert "Full Live Runtime Ready" in text

    readme = _read(PROJECT_ROOT / "README.md")
    assert "installer is complete" not in readme.casefold()
    assert "Phase 18A" not in readme
    assert "installer is complete" not in report.casefold()

    results = search_articles("packaging installer source")
    assert results
    article_text = "\n".join(results[0].article.paragraphs)
    assert "Phase 18A" in article_text
    assert "python -m v3_app.main" in article_text
    assert "does not create an installer" in article_text


def test_phase18a_imports_without_hotas_vjoy_or_runtime_authority():
    import bridge_app.main as bridge_main
    import v3_app.main as app_main
    from v3_app.services import app_paths

    assert app_main.APP_NAME == "HelmForge"
    assert bridge_main.main is not None
    assert app_paths.get_user_data_paths().root.name == "HelmForge"

    app_sources = "\n".join(
        _read(path)
        for path in (
            PROJECT_ROOT / "v3_app" / "main.py",
            PROJECT_ROOT / "v3_app" / "services" / "app_paths.py",
            PROJECT_ROOT / "packaging" / "build_release.ps1",
        )
    )
    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "keyboard.add_hotkey",
        "vJoy output active",
        "output_verified = True",
        "OpenAI(",
    ):
        assert forbidden not in app_sources
