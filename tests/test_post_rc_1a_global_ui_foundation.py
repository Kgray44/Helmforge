from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _shell(tmp_path):
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import build_initial_app_state
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        state=build_initial_app_state(),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )


def test_post_rc_1a_main_window_has_shorter_default_and_resizes_both_directions():
    _app()

    from v3_app.main import build_main_window
    from v3_app.theme.tokens import Layout

    window = build_main_window()

    assert Layout.window_height <= 860
    assert window.size().width() == Layout.window_width
    assert window.size().height() == Layout.window_height
    assert 1100 <= window.minimumWidth() <= Layout.window_width
    assert 650 <= window.minimumHeight() <= Layout.window_height
    assert window.maximumWidth() > Layout.window_width
    assert window.maximumHeight() > Layout.window_height

    window.resize(Layout.window_width + 120, Layout.window_height + 80)
    assert window.width() >= Layout.window_width + 120
    assert window.height() >= Layout.window_height + 80


def test_post_rc_1a_shell_uses_carded_sidebar_status_assistant_and_page_boundary(tmp_path):
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.theme.qss import app_qss

    shell = _shell(tmp_path)
    qss = app_qss()

    assert shell.findChild(QWidget, "appSidebar") is not None
    assert shell.findChild(QWidget, "statusCluster") is not None
    assert shell.findChild(QWidget, "assistantCluster") is not None

    for selector in (
        "QWidget#appSidebar",
        "QWidget#statusCluster",
        "QWidget#assistantCluster",
        "QScrollArea#pageScrollArea",
    ):
        assert selector in qss

    assert "QScrollArea#pageScrollArea" in qss
    assert "pageScrollArea {\n        background:" in qss
    assert "border: 1px solid" in qss


def test_post_rc_1a_buttons_have_distinct_states_and_helm_is_not_active_by_default(tmp_path):
    _app()

    from PySide6.QtWidgets import QPushButton
    from v3_app.theme.qss import app_qss

    shell = _shell(tmp_path)
    helm = shell.findChild(QPushButton, "helmButton")
    assert helm is not None
    assert helm.property("uiRole") == "actionButton"
    assert not helm.isCheckable()
    assert not helm.isChecked()

    qss = app_qss()
    for rule in (
        "QPushButton:hover",
        "QPushButton:pressed",
        "QPushButton:checked",
        "QPushButton:disabled",
        "QToolButton:hover",
        "QToolButton:pressed",
        "QToolButton:checked",
        "QToolButton:disabled",
    ):
        assert rule in qss

    assert "QPushButton#helmButton {\n        background:" not in qss


def test_post_rc_1a_dropdowns_have_items_visible_text_and_popup_theme(tmp_path):
    _app()

    from PySide6.QtWidgets import QComboBox
    from v3_app.theme.qss import app_qss

    shell = _shell(tmp_path)
    for page_id in ("effective_response_stack", "live_monitor", "help_docs", "flight_recorder"):
        shell.switch_page(page_id)

    for object_name in (
        "stackAxisSelector",
        "liveMonitorAxisSelector",
        "helpDocsSortDropdown",
        "recordingLibrarySortDropdown",
    ):
        combo = shell.findChild(QComboBox, object_name)
        assert combo is not None, object_name
        assert combo.count() > 0
        assert combo.currentText().strip()
        assert all(combo.itemText(index).strip() for index in range(combo.count()))

    qss = app_qss()
    for required in (
        "QComboBox QAbstractItemView",
        "QComboBox QAbstractItemView::item",
        "QComboBox QAbstractItemView::item:selected",
        "QComboBox:disabled",
    ):
        assert required in qss


def test_post_rc_1a_bottom_bar_removes_page_axis_profile_source_details(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel, QPushButton

    shell = _shell(tmp_path)
    shell.switch_page("flight_recorder")
    footer = shell.footer
    footer_text = "\n".join(label.text() for label in footer.findChildren(QLabel))
    footer_buttons = {button.text() for button in footer.findChildren(QPushButton)}

    for forbidden in ("Page:", "Axis:", "Profile:", "Source:"):
        assert forbidden not in footer_text

    assert footer_buttons >= {"Import Profile", "Revert", "Save Workspace"}


def test_post_rc_1a_card_grid_helper_top_aligns_content_sized_cards():
    _app()

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QGridLayout, QWidget
    from v3_app.pages.page_helpers import add_card_to_grid, card

    container = QWidget()
    grid = QGridLayout(container)
    short_card = card("shortCard")
    tall_card = card("tallCard")

    add_card_to_grid(grid, short_card, 0, 0)
    add_card_to_grid(grid, tall_card, 0, 1)

    assert short_card.property("cardSizing") == "content"
    assert tall_card.property("cardSizing") == "content"
    assert grid.itemAtPosition(0, 0).alignment() & Qt.AlignmentFlag.AlignTop
    assert grid.itemAtPosition(0, 1).alignment() & Qt.AlignmentFlag.AlignTop


def test_post_rc_1a_no_forbidden_runtime_controls_or_authority(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel, QPushButton

    shell = _shell(tmp_path)
    app_text = "\n".join(
        [label.text() for label in shell.findChildren(QLabel)]
        + [button.text() for button in shell.findChildren(QPushButton)]
    )

    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Install Service",
        "Enable Auto Start",
        "Install vJoy",
    ):
        assert forbidden not in app_text

    source_paths = (
        PROJECT_ROOT / "v3_app" / "ui" / "shell.py",
        PROJECT_ROOT / "v3_app" / "theme" / "qss.py",
        PROJECT_ROOT / "v3_app" / "ui" / "footer.py",
        PROJECT_ROOT / "v3_app" / "ui" / "header.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "keyboard.add_hotkey",
        "VideoWriter",
        "OpenAI(",
    ):
        assert forbidden not in sources


def test_post_rc_1a_report_documents_walkthrough_scope():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-1a-global-ui-foundation-report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "Post-RC 1A",
        "user walkthrough issues addressed",
        "global style/layout changes",
        "dropdown/button fixes",
        "bottom bar change",
        "remaining known page-specific issues",
        "Recommendation for Post-RC 1B",
        "no runtime behavior",
    ):
        assert required in text
