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
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        state=AppState.from_runtime_status(_runtime_status()),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        runtime_status=_runtime_status(),
    )


def test_post_rc_4c_main_shell_constructs_and_footer_stays_clean(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel

    shell = _shell(tmp_path)
    assert shell.objectName() == "helmforgeShell"
    assert shell.sidebar is not None
    assert shell.header is not None
    assert shell.footer is not None

    footer_text = "\n".join(label.text() for label in shell.footer.findChildren(QLabel))
    for forbidden in ("Page:", "Axis:", "Profile:", "Source:"):
        assert forbidden not in footer_text


def test_post_rc_4c_helm_launcher_default_is_not_pressed_or_active(tmp_path):
    _app()

    from PySide6.QtWidgets import QPushButton
    from v3_app.theme.qss import app_qss

    shell = _shell(tmp_path)
    helm = shell.findChild(QPushButton, "helmButton")

    assert helm is not None
    assert helm.property("uiRole") == "actionButton"
    assert helm.isCheckable() is False
    assert helm.isChecked() is False
    assert helm.isDown() is False
    assert "QPushButton#helmButton {\n        background:" not in app_qss()


def test_post_rc_4c_helm_opens_as_right_overlay_with_dim_scrim_not_sidebar(tmp_path):
    _app()

    from PySide6.QtWidgets import QWidget

    shell = _shell(tmp_path)
    shell.resize(1280, 820)
    overlay = shell.open_helm_overlay()
    scrim = shell.findChild(QWidget, "helmOverlayScrim")

    assert "helm" not in shell.page_widgets
    assert overlay.objectName() == "helmOverlay"
    assert overlay.property("overlayPlacement") == "right-glide"
    assert overlay.property("blurDeferred") is True
    assert overlay.width() < shell.width()
    assert overlay.x() >= shell.geometry().x()
    assert scrim is not None
    assert scrim.property("scrimMode") == "dimmed"
    assert scrim.property("uiRole") == "overlayScrim"


def test_post_rc_4c_helm_active_bulb_and_symptom_input_are_polished(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel, QPlainTextEdit

    shell = _shell(tmp_path)
    overlay = shell.open_helm_overlay()

    bulb = overlay.findChild(QLabel, "helmActiveBulb")
    symptom = overlay.findChild(QPlainTextEdit, "helmSymptomInput")

    assert bulb is not None
    assert bulb.property("polish") == "bulb"
    assert bulb.property("pulseStyle") == "static-qss"

    assert symptom is not None
    assert symptom.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth
    assert symptom.property("autoResize") is True
    assert symptom.minimumHeight() <= 100
    assert symptom.maximumHeight() >= 200
    symptom.setPlainText("Long symptom text " * 30)
    assert 92 <= symptom.height() <= 220


def test_post_rc_4c_helm_action_buttons_are_normal_and_apply_revert_has_footer_row(tmp_path):
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget

    shell = _shell(tmp_path)
    overlay = shell.open_helm_overlay()

    for object_name in ("helmAnalyzeButton", "helmReviewChangesButton", "helmCancelButton", "helmCloseButton"):
        button = overlay.findChild(QPushButton, object_name)
        assert button is not None
        assert button.isCheckable() is False
        assert button.isChecked() is False
        assert button.isDown() is False

    action_row = overlay.findChild(QWidget, "helmActionRow")
    assert action_row is not None
    assert action_row.property("uiRole") == "cardActionRow"
    assert action_row.findChild(QPushButton, "helmApplySelectedButton") is not None
    assert action_row.findChild(QPushButton, "helmRevertLastButton") is not None


def test_post_rc_4c_helm_cards_are_content_sized_and_named_for_qa(tmp_path):
    _app()

    from PySide6.QtWidgets import QFrame

    shell = _shell(tmp_path)
    overlay = shell.open_helm_overlay()

    for object_name in (
        "helmWhatsWrongCard",
        "helmRecommendationCard",
        "helmFindingCard",
        "helmApplyRevertCard",
    ):
        card = overlay.findChild(QFrame, object_name)
        assert card is not None, object_name
        assert card.property("helmCardContentSized") is True


def test_post_rc_4c_walkthrough_matrix_exists_and_is_honest():
    matrix = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-human-walkthrough-completion-matrix.md"
    assert matrix.exists()
    text = matrix.read_text(encoding="utf-8")

    for section in (
        "Global / Shell",
        "Helm",
        "Mapping",
        "Profiles",
        "Modes",
        "Base Tuning",
        "Filtering",
        "Combat Profile",
        "Conditional Rules",
        "Effective Response Stack",
        "Live Monitor",
        "Flight Recorder",
        "Help / Docs",
        "Perf / Diagnostics",
        "Bottom Bar",
    ):
        assert f"## {section}" in text

    for status in ("Fixed", "Partial", "Not Fixed", "Deferred", "Cannot Verify Without Visible QA"):
        assert status in text


def test_post_rc_4c_no_runtime_authority_was_introduced():
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "helm" / "helm_overlay.py",
            PROJECT_ROOT / "v3_app" / "theme" / "qss.py",
            PROJECT_ROOT / "v3_app" / "ui" / "header.py",
            PROJECT_ROOT / "v3_app" / "ui" / "footer.py",
            PROJECT_ROOT / "v3_app" / "ui" / "shell.py",
        )
    )

    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "keyboard.add_hotkey",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
        "UpdateVJD",
        "SetAxis",
        "SetBtn",
        "AcquireVJD",
        "CreateService",
        "SetWindowsHookEx",
        "QProcess",
        "subprocess.Popen",
    ):
        assert forbidden not in sources
