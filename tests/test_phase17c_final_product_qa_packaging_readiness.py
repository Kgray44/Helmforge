from __future__ import annotations

import os
from pathlib import Path

from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status() -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
        messages=("Simulation fallback remains available; live output is not verified.",),
    )


def _state():
    from v3_app.services.app_state import AppState

    return AppState.from_runtime_status(_runtime_status(), driver_detected=True)


def _workspace():
    from shared_core.models.workspace import create_default_workspace

    return create_default_workspace()


def _shell(tmp_path):
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        _state(),
        workspace=_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )


def _widget_text(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join((*labels, *buttons))


def test_phase17c_all_pages_and_key_dialogs_still_construct_for_final_qa(tmp_path):
    _app()

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QScrollArea
    from v3_app.overlay.config_dialog import LiveOverlayConfigDialog
    from v3_app.overlay.live_overlay_window import LiveOverlayWindow
    from v3_app.overlay.overlay_config import LiveOverlayConfig
    from v3_app.pages.placeholders import PAGE_DEFINITIONS

    shell = _shell(tmp_path)
    for width, height in ((1280, 720), (1440, 900), (1920, 1080)):
        shell.resize(width, height)
        for page in PAGE_DEFINITIONS:
            shell.switch_page(page.page_id)
            scroll = shell.page_widgets[page.page_id]
            assert isinstance(scroll, QScrollArea)
            assert scroll.widgetResizable()
            assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            assert scroll.widget() is not None
            assert page.title in _widget_text(scroll.widget())

    first_ids = {page.page_id: id(shell.page_widgets[page.page_id].widget()) for page in PAGE_DEFINITIONS}
    for page in PAGE_DEFINITIONS:
        shell.switch_page(page.page_id)
        assert id(shell.page_widgets[page.page_id].widget()) == first_ids[page.page_id]

    helm = shell.open_helm_overlay()
    assert "Apply Selected Changes" in _widget_text(helm)
    helm.close()

    dialog = LiveOverlayConfigDialog(config=LiveOverlayConfig.defaults(), on_apply=lambda _config: None)
    assert dialog.minimumWidth() >= 760
    assert 500 <= dialog.minimumHeight() <= 560

    overlay = LiveOverlayWindow(
        config=LiveOverlayConfig.defaults(),
        runtime_truth="blocked_missing_device",
        output_verified=False,
        full_live_runtime_ready=False,
    )
    overlay.show_overlay()
    assert overlay.refresh_timer.isActive()
    overlay.hide_overlay()
    assert not overlay.refresh_timer.isActive()


def test_phase17c_runtime_truth_copy_remains_blocked_and_diagnostics_are_complete(tmp_path):
    _app()

    from PySide6.QtWidgets import QPushButton

    shell = _shell(tmp_path)
    app_text = _widget_text(shell)
    assert "Full Live Runtime Ready\ntrue" not in app_text
    assert "Full Live Runtime Ready true" not in app_text
    assert "connected and ready" not in app_text.casefold()

    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Start Bridge",
        "Stop Bridge",
        "Restart Bridge",
        "Install Service",
        "Enable Auto Start",
    ):
        assert forbidden not in app_text

    shell.switch_page("perf_diagnostics")
    perf = shell.page_widgets["perf_diagnostics"].widget()
    perf_text = _widget_text(perf)
    copy_text = perf.prepare_copy_diagnostics()
    for required in (
        "Full Live Runtime Ready gate",
        "Ready state",
        "Blocked reason",
        "Input proof",
        "Output proof",
        "Telemetry proof",
        "Safety proof",
        "Proof summary",
    ):
        assert required in perf_text
        assert required in copy_text

    button_text = " ".join(button.text() for button in shell.findChildren(QPushButton))
    for forbidden in ("Install Service", "Enable Auto Start", "Install App", "Build Installer"):
        assert forbidden not in button_text


def test_phase17c_help_docs_and_readme_report_phase18_readiness_without_packaging_claims():
    from v3_app.services.help_docs import search_articles

    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-17c-final-product-qa-packaging-readiness-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    for required in (
        "Phase 18 Packaging Readiness Census",
        "User Data Path Readiness Notes",
        "Icon Readiness Notes",
        "Recommendation For Phase 18",
        "Phase 17 is now complete",
    ):
        assert required in report_text

    phase_ledger = (PROJECT_ROOT / "docs" / "HelmForge" / "phase-ledger.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "HelmForge" / "bridge-ui-architecture.md").read_text(encoding="utf-8")
    for text in (phase_ledger, architecture):
        assert "Phase 17C" in text
        assert "Phase 18: Packaging, Installer, Icons, and User Data Locations" in text
        assert "does not implement packaging" in text
        assert "simulation mode" in text

    results = search_articles("packaging installer source")
    assert results
    article_text = "\n".join(results[0].article.paragraphs)
    assert "Phase 18" in article_text
    assert "installer is not implemented" in article_text
    assert "python -m v3_app.main" in article_text


def test_phase17c_packaging_census_truth_and_no_packaging_behavior_added():
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'helmforge = "v3_app.main:main"' in pyproject
    assert 'helmforge-bridge = "bridge_app.main:main"' in pyproject
    assert '"PySide6"' in pyproject
    assert '"pyqtgraph"' in pyproject

    icon_candidates = tuple((PROJECT_ROOT / "HOTAS Control Panel Forensic Spec Set").rglob("*icon*.png"))
    assert icon_candidates
    assert not tuple(PROJECT_ROOT.rglob("*.ico"))
    packaging_root = PROJECT_ROOT / "packaging"
    if packaging_root.exists():
        assert (packaging_root / "README.md").exists()
        assert (packaging_root / "build_release.ps1").exists()
        if (packaging_root / "dist").exists():
            assert (packaging_root / "dist").is_dir()
        if (packaging_root / "output").exists():
            assert (packaging_root / "output").is_dir()
    else:
        assert not packaging_root.exists()
    assert not (PROJECT_ROOT / "installer").exists()
    spec_files = tuple(PROJECT_ROOT.rglob("*.spec"))
    for spec_file in spec_files:
        assert packaging_root in spec_file.parents
        assert "output" in spec_file.parts or "build" in spec_file.parts

    script_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "scripts").glob("*"))
    for forbidden in ("pyinstaller", "Inno Setup", "ISCC", "makensis", "wix"):
        assert forbidden.casefold() not in script_sources.casefold()

    app_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "main.py",
            PROJECT_ROOT / "v3_app" / "ui" / "shell.py",
            PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py",
            PROJECT_ROOT / "v3_app" / "services" / "help_docs.py",
        )
    )
    for forbidden in (
        "keyboard.add_hotkey",
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "mss",
        "dxcam",
        "VideoWriter",
        "ffmpeg",
        "OpenAI(",
    ):
        assert forbidden not in app_sources
