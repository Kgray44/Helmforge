from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _shell(tmp_path):
    _app()

    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import build_initial_app_state
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell(
        state=build_initial_app_state(),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )
    shell.switch_page("help_docs")
    return shell


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def _tree_texts(tree) -> list[str]:
    values: list[str] = []
    for row in range(tree.topLevelItemCount()):
        parent = tree.topLevelItem(row)
        values.append(parent.text(0))
        for child_index in range(parent.childCount()):
            values.append(parent.child(child_index).text(0))
    return values


def _select_tree_topic(tree, title: str) -> None:
    for row in range(tree.topLevelItemCount()):
        parent = tree.topLevelItem(row)
        for child_index in range(parent.childCount()):
            child = parent.child(child_index)
            if child.text(0) == title:
                tree.setCurrentItem(child)
                return
    raise AssertionError(f"topic not found: {title}")


def test_post_rc_1d_service_exposes_structured_manual_and_metadata_reference():
    from v3_app.services.help_docs import (
        HELP_SORT_OPTIONS,
        HELP_TOPIC_TREE_ORDER,
        get_article,
        parameter_reference_entries,
        topic_tree_by_category,
    )
    from v3_app.services.parameter_metadata import PARAMETER_HELP

    for category in (
        "Getting Started",
        "Runtime Truth",
        "Mapping",
        "Flight Recorder",
        "Parameter Reference",
        "Troubleshooting",
    ):
        assert category in HELP_TOPIC_TREE_ORDER

    assert HELP_SORT_OPTIONS == (
        "By Category",
        "By Last Opened",
        "Alphabetical A-Z",
        "Alphabetical Z-A",
        "By Importance",
    )

    tree = topic_tree_by_category()
    assert "Mapping edit workflow" in [article.title for article in tree["Mapping"]]
    assert "One-frame capture proof" in [article.title for article in tree["Flight Recorder"]]

    mapping_workflow = get_article("Mapping edit workflow")
    assert mapping_workflow.open_page_id == "mapping"
    assert {
        "What this is",
        "What it does",
        "When to use it",
        "Key parameters",
        "Runtime truth notes",
        "Related topics",
    } <= {section.heading for section in mapping_workflow.sections}
    assert "Mapping edits are workspace/config draft only" in mapping_workflow.search_text
    assert "Save Workspace is required to persist" in mapping_workflow.search_text

    one_frame = get_article("One-frame capture proof")
    assert one_frame.open_page_id == "flight_recorder"
    assert "one-frame capture proof is not video recording" in one_frame.search_text
    assert "No continuous recorder capture yet" in one_frame.search_text

    references = parameter_reference_entries()
    assert PARAMETER_HELP.require("base.deadzone") in references
    assert any(metadata.parameter_id == "mapping.raw_axis" for metadata in references)


def test_post_rc_1d_help_page_uses_dark_tree_article_surface_and_sort_options(tmp_path):
    _app()

    from PySide6.QtWidgets import QComboBox, QFrame, QListWidget, QTreeWidget
    from v3_app.theme.qss import app_qss

    shell = _shell(tmp_path)
    page = shell.page_widgets["help_docs"].widget()
    tree = page.findChild(QTreeWidget, "helpDocsTopicTree")
    sort = page.findChild(QComboBox, "helpDocsSortDropdown")
    legacy = page.findChild(QListWidget, "helpDocsTopicList")
    article_surface = page.findChild(QFrame, "helpArticleSurface")

    assert tree is not None
    assert tree.topLevelItemCount() >= 10
    assert sort is not None
    assert [sort.itemText(index) for index in range(sort.count())] == [
        "By Category",
        "By Last Opened",
        "Alphabetical A-Z",
        "Alphabetical Z-A",
        "By Importance",
    ]
    assert legacy is not None
    assert legacy.count() > 0
    assert article_surface is not None
    assert article_surface.property("helpArticleSurface") is True

    first_category = tree.topLevelItem(0)
    assert first_category.data(0, Qt.ItemDataRole.UserRole) is None
    assert first_category.childCount() > 0
    assert first_category.child(0).data(0, Qt.ItemDataRole.UserRole)

    qss = app_qss()
    for selector in (
        "QTreeWidget#helpDocsTopicTree",
        "QFrame#helpArticleSurface",
        "QFrame#helpParameterReferenceBlock",
        "QLabel#helpArticleSectionTitle",
    ):
        assert selector in qss
    assert "#ffffff" not in qss[qss.find("QFrame#helpArticleSurface") : qss.find("QFrame#helpParameterReferenceBlock")]


def test_post_rc_1d_search_tree_preserves_categories_and_selects_structured_topics(tmp_path):
    _app()

    from PySide6.QtWidgets import QLineEdit, QTreeWidget

    shell = _shell(tmp_path)
    page = shell.page_widgets["help_docs"].widget()
    search = page.findChild(QLineEdit, "helpDocsSearchField")
    tree = page.findChild(QTreeWidget, "helpDocsTopicTree")

    search.setText("one-frame capture proof")
    texts = _tree_texts(tree)

    assert "Flight Recorder" in texts
    assert "One-frame capture proof" in texts
    assert "one-frame capture proof" not in [tree.topLevelItem(index).text(0).casefold() for index in range(tree.topLevelItemCount())]

    _select_tree_topic(tree, "One-frame capture proof")
    text = _label_text(page)
    assert "One-frame capture proof" in page.article_title.text()
    assert "What this is" in text
    assert "Runtime truth notes" in text
    assert "one-frame capture proof is not video recording" in text


def test_post_rc_1d_parameter_reference_renders_registry_blocks(tmp_path):
    _app()

    from PySide6.QtWidgets import QFrame, QTreeWidget

    shell = _shell(tmp_path)
    page = shell.page_widgets["help_docs"].widget()
    tree = page.findChild(QTreeWidget, "helpDocsTopicTree")

    _select_tree_topic(tree, "Parameter Reference")
    text = _label_text(page)
    blocks = page.findChildren(QFrame, "helpParameterReferenceBlock")
    block_ids = {block.property("metadataId") for block in blocks}

    assert "Parameter Reference" in page.article_title.text()
    assert "Deadzone" in text
    assert "workspace only" in text
    assert "Range" in text
    assert "Default" in text
    assert "base.deadzone" in block_ids
    assert "mapping.raw_axis" in block_ids


def test_post_rc_1d_page_navigation_buttons_route_inside_app(tmp_path):
    _app()

    from PySide6.QtWidgets import QPushButton, QTreeWidget

    shell = _shell(tmp_path)
    page = shell.page_widgets["help_docs"].widget()
    tree = page.findChild(QTreeWidget, "helpDocsTopicTree")

    _select_tree_topic(tree, "Mapping edit workflow")
    button = page.findChild(QPushButton, "helpOpenPageButton_mapping")
    assert button is not None
    assert button.text() == "Open Mapping"

    button.click()
    assert shell.active_page_id == "mapping"


def test_post_rc_1d_expanded_articles_cover_post_rc_truth_and_boundaries():
    from v3_app.services.help_docs import search_articles

    expectations = {
        "hotas diagram": "HOTAS diagram",
        "route inspector": "Mapping Route Inspector",
        "axis routing": "Axis routing",
        "button routing": "Button routing",
        "hat routing": "Hat routing",
        "recorder review export diagnostics": "Recorder review/export diagnostics",
        "real capture limitations": "Real capture limitations",
        "Full Live Runtime Ready gate": "Full Live Runtime Ready",
        "vJoy output verification": "vJoy/output verification",
    }
    for query, expected_title in expectations.items():
        results = search_articles(query)
        assert results, query
        assert any(result.article.title == expected_title for result in results), query


def test_post_rc_1d_report_and_runtime_boundary_are_present():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-1d-help-docs-full-overhaul-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")

    for required in (
        "Help / Docs UI changes",
        "topic tree model",
        "article model",
        "sort behavior",
        "metadata integration",
        "page navigation buttons",
        "runtime truth preservation",
        "No runtime authority",
    ):
        assert required in report_text

    source_paths = (
        PROJECT_ROOT / "v3_app" / "services" / "help_docs.py",
        PROJECT_ROOT / "v3_app" / "pages" / "help_docs_page.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "UpdateVJD",
        "SetAxis",
        "subprocess.Popen",
        "QProcess",
        "OpenAI(",
        "auto_save",
    ):
        assert forbidden not in sources
