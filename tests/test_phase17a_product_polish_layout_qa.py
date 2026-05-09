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


def _shell(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        AppState.from_runtime_status(_runtime_status()),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )


def _widget_text(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton, QScrollArea

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join((*labels, *buttons))


def test_phase17a_all_main_pages_construct_navigate_and_keep_scrollable_layouts(tmp_path):
    _app()

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QScrollArea
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
            assert scroll.viewport().objectName() == "pageScrollViewport"
            assert scroll.widget() is not None
            assert page.title in _widget_text(scroll.widget())


def test_phase17a_status_chips_actions_helm_and_overlay_dialog_are_visually_distinct(tmp_path):
    _app()

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QPushButton, QScrollArea
    from v3_app.overlay.config_dialog import LiveOverlayConfigDialog
    from v3_app.overlay.overlay_config import LiveOverlayConfig
    from v3_app.ui.status_chips import action_button, status_chip

    chip = status_chip("Output verified: false")
    action = action_button("Run Runtime Preflight")
    assert isinstance(chip, QLabel)
    assert not isinstance(chip, QPushButton)
    assert chip.property("interactive") is False
    assert chip.cursor().shape() == Qt.CursorShape.ArrowCursor
    assert isinstance(action, QPushButton)
    assert action.cursor().shape() == Qt.CursorShape.PointingHandCursor

    shell = _shell(tmp_path)
    overlay = shell.open_helm_overlay()
    assert overlay.objectName() == "helmOverlay"
    assert overlay.findChild(QScrollArea, "helmOverlayScrollArea") is not None
    overlay.close()

    dialog = LiveOverlayConfigDialog(config=LiveOverlayConfig.defaults(), on_apply=lambda _config: None)
    assert dialog.objectName() == "liveOverlayConfigDialog"
    assert dialog.minimumWidth() >= 760
    assert 500 <= dialog.minimumHeight() <= 560


def test_phase17a_runtime_copy_and_forbidden_controls_remain_frozen(tmp_path):
    _app()

    from v3_app.pages.placeholders import PAGE_DEFINITIONS

    shell = _shell(tmp_path)
    app_text = _widget_text(shell)
    page_copy = "\n".join(f"{page.title}\n{page.subtitle}\n{page.shell_note}" for page in PAGE_DEFINITIONS)

    assert "final vJoy output" not in page_copy
    assert "Full Live Runtime Ready\ntrue" not in app_text
    assert "Full Live Runtime Ready true" not in app_text
    assert "connected and ready" not in app_text.casefold()
    assert "vJoy active" not in app_text

    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Start Bridge",
        "Stop Bridge",
        "Restart Bridge",
        "Install Service",
        "Enable Auto Start",
        "Install vJoy",
    ):
        assert forbidden not in app_text


def test_phase17a_recorder_help_and_diagnostics_truth_surfaces(tmp_path):
    _app()

    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.app_state import AppState
    from v3_app.services.help_docs import search_articles

    state = AppState.from_runtime_status(_runtime_status())
    recorder = FlightRecorderPage(
        state=state,
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
    )
    recorder_text = _widget_text(recorder)
    assert "Metadata-only preview" in recorder_text
    assert "No video captured" in recorder_text
    assert "No encoding performed" in recorder_text
    assert "Hotkey not registered" in recorder_text

    perf = PerfDiagnosticsPage(
        state=state,
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )
    perf_text = _widget_text(perf)
    copy_text = perf.prepare_copy_diagnostics()
    for required in (
        "Full Live Runtime Ready gate",
        "Ready state",
        "Telemetry proof",
        "Safety proof",
        "Fake/real path",
        "Proof summary",
    ):
        assert required in perf_text
        assert required in copy_text

    for query in ("Runtime Setup", "Helm", "Live Overlay", "Flight Recorder"):
        assert search_articles(query), query


def test_phase17a_docs_report_and_boundary_scans_are_present():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-17a-product-polish-layout-qa-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    assert "Phase 17A" in report_text
    assert "Runtime truth preservation" in report_text
    assert "Recommendation for Phase 17B" in report_text

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "HelmForge" / "bridge-ui-architecture.md").read_text(encoding="utf-8")
    assert "Phase 17A" in readme
    assert "Product Polish, Layout QA, and Motion" in readme
    assert "Phase 17A" in architecture

    source_paths = (
        PROJECT_ROOT / "v3_app" / "ui" / "shell.py",
        PROJECT_ROOT / "v3_app" / "ui" / "status_chips.py",
        PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py",
        PROJECT_ROOT / "v3_app" / "services" / "help_docs.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
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
        assert forbidden not in sources
