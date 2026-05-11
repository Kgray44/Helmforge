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

    return AppState.from_runtime_status(_runtime_status())


def _workspace():
    from shared_core.models.workspace import create_default_workspace

    return create_default_workspace()


def _shell(tmp_path):
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        state=_state(),
        workspace=_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        runtime_status=_runtime_status(),
    )


def _page(shell, page_id: str):
    shell.switch_page(page_id)
    return shell.page_widgets[page_id].widget()


def _text(widget) -> str:
    from PySide6.QtWidgets import QFrame, QLabel, QPushButton

    return "\n".join(
        [label.text() for label in widget.findChildren(QLabel)]
        + [button.text() for button in widget.findChildren(QPushButton)]
    )


def test_post_rc_4b_major_pages_construct_offscreen(tmp_path):
    _app()
    shell = _shell(tmp_path)

    for page_id in (
        "mapping",
        "profiles",
        "modes",
        "base_tuning",
        "filtering",
        "combat_profile",
        "conditional_rules",
        "effective_response_stack",
        "live_monitor",
        "flight_recorder",
        "help_docs",
        "perf_diagnostics",
    ):
        page = _page(shell, page_id)

        assert page is not None
        assert page.objectName()


def test_post_rc_4b_mapping_polish_preserves_draft_only_workflow(tmp_path):
    _app()

    from PySide6.QtWidgets import QFrame, QLabel, QPushButton

    shell = _shell(tmp_path)
    page = _page(shell, "mapping")
    text = _text(page)

    assert page.findChild(QLabel, "mappingPolishTruthNotice") is not None
    assert page.findChild(QLabel, "mappingPolishTruthNotice").property("uiRole") == "truthNotice"
    assert page.findChild(QPushButton, "changeMappingButton") is not None
    assert "Selected Control" in text
    assert "Draft mapping only" in text
    assert "Change the target below" in text
    assert "draft" in text.lower()

    if (PROJECT_ROOT / "tests" / "test_post_rc_2d_advanced_mapping_editor.py").exists():
        for expected in ("Draft Review", "Undo", "Redo", "Preset", "Search"):
            assert expected in text


def test_post_rc_4b_flight_recorder_workflow_truth_is_coherent(tmp_path):
    _app()

    from PySide6.QtWidgets import QFrame, QLabel, QPushButton

    shell = _shell(tmp_path)
    page = _page(shell, "flight_recorder")
    text = _text(page)

    for object_name in (
        "recorderCaptureProofCard",
        "recorderFrameBufferCard",
        "recorderEncodingExportCard",
    ):
        assert page.findChild(QFrame, object_name) is not None

    assert page.findChild(QLabel, "recorderWorkflowTruthNotice") is not None

    assert page.findChild(QPushButton, "exportClipButton") is not None
    assert page.findChild(QPushButton, "previewClipButton") is not None
    assert "Intermediate artifacts are not playable clips" in text
    assert "Playable claim allowed" in text
    assert "Preview stays unavailable" in text
    assert "No global hotkey" in text or "global recorder hotkeys" in text

    if (PROJECT_ROOT / "tests" / "test_post_rc_3f_durable_frame_storage.py").exists():
        assert "Frame Storage" in text
        assert "Image sequence" in text
        assert "not encoded / not playable" in text.lower()


def test_post_rc_4b_help_docs_and_diagnostics_have_truth_anchors(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel, QTreeWidget

    shell = _shell(tmp_path)
    help_page = _page(shell, "help_docs")
    diagnostics_page = _page(shell, "perf_diagnostics")

    assert help_page.findChild(QTreeWidget, "helpDocsTopicTree") is not None
    assert help_page.findChild(QLabel, "helpDocsReadabilityNotice") is not None
    assert "Parameter Reference" in _text(help_page)
    assert "local" in _text(help_page).lower()

    diagnostics_notice = diagnostics_page.findChild(QLabel, "diagnosticsTruthLegend")
    assert diagnostics_notice is not None
    diagnostics_text = diagnostics_notice.text()
    assert "Hints" in diagnostics_text
    assert "proof" in diagnostics_text.lower()
    assert "Full Live Runtime Ready" in diagnostics_text


def test_post_rc_4b_dropdowns_selection_and_stack_polish_are_stable(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel, QComboBox, QTreeWidget

    shell = _shell(tmp_path)

    profiles = _page(shell, "profiles")
    profile_tree = profiles.findChild(QTreeWidget, "profileLibraryTree")
    assert profile_tree is not None
    assert profile_tree.currentItem() is not None
    assert profiles.findChild(QLabel, "profilesDraftPolishNotice") is not None

    modes = _page(shell, "modes")
    stack_mode = modes.findChild(QComboBox, "stackModeField")
    assert stack_mode is not None
    assert stack_mode.count() > 0
    assert modes.findChild(QLabel, "modesPolishTruthNotice") is not None

    rules = _page(shell, "conditional_rules")
    target_axis = rules.findChild(QComboBox, "ruleTargetAxisField")
    assert target_axis is not None
    assert target_axis.count() > 0
    assert rules.findChild(QLabel, "conditionalRulesTruthNotice") is not None

    stack = _page(shell, "effective_response_stack")
    assert stack.findChild(QLabel, "stackPolishTruthNotice") is not None
    assert "Output intent is not output write proof" in _text(stack)

    live_monitor = _page(shell, "live_monitor")
    assert live_monitor.findChild(QLabel, "liveMonitorTruthNotice") is not None
    assert "Telemetry remains the truth surface" in _text(live_monitor)


def test_post_rc_4b_qss_has_global_polish_selectors():
    qss = (PROJECT_ROOT / "v3_app" / "theme" / "qss.py").read_text(encoding="utf-8")

    for expected in (
        'QLabel[uiRole="truthNotice"]',
        'QFrame[uiRole="workflowCard"]',
        'QLabel[uiRole="sectionKicker"]',
        "QTableWidget::item:selected",
        'QPushButton[uiRole="actionButton"]:disabled',
    ):
        assert expected in qss


def test_post_rc_4b_report_exists_and_runtime_authority_is_not_added():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-4b-page-by-page-polish-report.md"
    assert report.exists()

    source_paths = (
        PROJECT_ROOT / "v3_app" / "pages" / "mapping_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "help_docs_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
        PROJECT_ROOT / "v3_app" / "theme" / "qss.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "keyboard.add_hotkey",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
        "subprocess.Popen",
        "CreateService",
        "SetWindowsHookEx",
    ):
        assert forbidden not in sources
