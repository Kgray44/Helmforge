from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status():
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )

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
    _app()
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        runtime_status=_runtime_status(),
    )


def _page(shell, page_id: str):
    shell.switch_page(page_id)
    return shell.page_widgets[page_id].widget()


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    return "\n".join(
        [label.text() for label in widget.findChildren(QLabel)]
        + [button.text() for button in widget.findChildren(QPushButton)]
    )


def test_post_rc_4e_live_monitor_exposes_compact_runtime_polish(tmp_path):
    from PySide6.QtWidgets import QComboBox, QFrame, QLabel

    page = _page(_shell(tmp_path), "live_monitor")

    axis = page.findChild(QComboBox, "liveMonitorAxisSelector")
    assert axis is not None
    assert axis.count() >= 6
    assert axis.currentText().strip()

    assert page.findChild(QFrame, "liveMonitorCompactState") is not None
    assert page.findChild(QFrame, "liveMonitorActionBlock") is not None
    assert page.findChild(QFrame, "liveMonitorAxisLevelsVertical") is not None
    assert page.findChild(QLabel, "liveMonitorHistorySecondsLabel").text() == "History window: 7 seconds"
    assert "UI cadence:" in page.findChild(QLabel, "liveMonitorGraphCadenceLabel").text()
    assert "Output intent is not output write proof" in _label_text(page)


def test_post_rc_4e_live_overlay_config_dialog_is_scrollable_styled_and_has_presets(tmp_path):
    from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton, QScrollArea

    page = _page(_shell(tmp_path), "live_monitor")
    dialog = page.create_live_overlay_config_dialog()

    assert dialog.objectName() == "liveOverlayConfigDialog"
    assert dialog.property("postRc4eStyled") is True
    assert dialog.isSizeGripEnabled() is True
    assert dialog.minimumHeight() <= 560
    assert dialog.minimumWidth() >= 760

    scroll = dialog.findChild(QScrollArea, "liveOverlayConfigScrollArea")
    preset = dialog.findChild(QComboBox, "liveOverlayPresetDropdown")
    name = dialog.findChild(QLineEdit, "liveOverlayPresetNameInput")
    save = dialog.findChild(QPushButton, "liveOverlaySavePresetButton")

    assert scroll is not None and scroll.widgetResizable()
    assert preset is not None
    assert [preset.itemText(index) for index in range(preset.count())] == [
        "Regular",
        "Compact",
        "High Contrast",
        "Telemetry Focus",
        "Minimal",
        "Custom",
    ]
    assert name is not None
    assert save is not None

    preset.setCurrentText("Compact")
    assert dialog.property("selectedPreset") == "Compact"
    dialog.findChild(QComboBox, "overlayFpsCapField")
    dialog.accept()
    assert page.overlay_config.preset == "Compact"


def test_post_rc_4e_flight_recorder_workflow_status_and_editable_supported_settings(tmp_path):
    from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame

    page = _page(_shell(tmp_path), "flight_recorder")

    workflow = page.findChild(QFrame, "recorderWorkflowMapCard")
    status = page.findChild(QFrame, "recorderStatusCard")
    sort = page.findChild(QComboBox, "recordingLibrarySortDropdown")
    cursor = page.findChild(QCheckBox, "recordCursorCheckbox")
    axis_include = page.findChild(QCheckBox, "recorderAxisInclude_Roll")

    assert workflow is not None
    assert status is not None
    assert status.property("scanFriendlyRows") is True
    assert sort is not None and sort.count() >= 4
    assert cursor is not None and cursor.isEnabled()
    assert axis_include is not None and axis_include.isEnabled()

    cursor.setChecked(not cursor.isChecked())
    assert page.settings.record_cursor == cursor.isChecked()
    axis_include.setChecked(False)
    assert page.settings.axes["Roll"].include is False

    text = _label_text(page).casefold()
    for phrase in (
        "intermediate artifacts are not playable clips",
        "image sequence truth",
        "encoded clip file",
        "playable claim allowed",
    ):
        assert phrase in text


def test_post_rc_4e_help_docs_and_perf_diagnostics_keep_readable_truth_surfaces(tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QComboBox, QFrame, QPushButton, QScrollArea, QTreeWidget

    shell = _shell(tmp_path)
    help_page = _page(shell, "help_docs")
    tree = help_page.findChild(QTreeWidget, "helpDocsTopicTree")
    assert tree is not None
    assert help_page.findChild(QComboBox, "helpDocsSortDropdown").count() >= 5
    assert help_page.findChild(QFrame, "helpArticleSurface").property("postRc4eReadable") is True
    assert help_page.findChild(QScrollArea, "helpDocsGuideScrollArea") is not None
    for row in range(tree.topLevelItemCount()):
        parent = tree.topLevelItem(row)
        for child_index in range(parent.childCount()):
            child = parent.child(child_index)
            if child.data(0, Qt.ItemDataRole.UserRole) == "Live Monitor":
                tree.setCurrentItem(child)
                break
    assert any(button.objectName().startswith("helpOpenPageButton_") for button in help_page.findChildren(QPushButton))

    perf_page = _page(shell, "perf_diagnostics")
    assert perf_page.findChild(QFrame, "diagnosticsHintProofReadinessLegend") is not None
    assert perf_page.findChild(QFrame, "perfTimingCard").property("expandedTimingDisplay") is True
    assert perf_page.findChild(QFrame, "perfBridgeTelemetryCard").property("cardSizing") == "content"
    text = _label_text(perf_page)
    assert "Hint" in text and "Proof" in text and "Readiness" in text
    assert "Full Live Runtime Ready" in text


def test_post_rc_4e_matrix_report_and_runtime_authority_boundaries():
    matrix = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-human-walkthrough-completion-matrix.md"
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-4e-runtime-recorder-docs-diagnostics-polish-report.md"
    assert matrix.exists()
    assert report.exists()

    text = matrix.read_text(encoding="utf-8")
    for section in (
        "Live Monitor",
        "Live Overlay",
        "Flight Recorder",
        "Help / Docs",
        "Perf / Diagnostics",
        "Final Walkthrough Acceptance Summary",
        "Recommended 5A manual visible QA checks",
    ):
        assert f"## {section}" in text
    for status in ("Fixed", "Partial", "Deferred", "Cannot Verify Without Visible QA"):
        assert status in text

    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "help_docs_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
            PROJECT_ROOT / "v3_app" / "overlay" / "config_dialog.py",
            PROJECT_ROOT / "v3_app" / "overlay" / "overlay_config.py",
        )
    )
    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "RegisterHotKey",
        "keyboard.add_hotkey",
        "UpdateVJD",
        "SetAxis",
        "SetBtn",
        "AcquireVJD",
        "VideoWriter",
        "SetWindowsHookEx",
        "DirectX hook",
        "Vulkan hook",
        "OpenGL hook",
        "pystray",
        "OpenAI(",
        "anthropic",
        "auto_save",
    ):
        assert forbidden not in sources
