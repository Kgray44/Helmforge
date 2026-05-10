from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _status():
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
    )


def _shell(tmp_path):
    _app()
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell(
        AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )
    shell.switch_page("help_docs")
    return shell


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_phase11a_help_content_has_required_categories_topics_and_articles():
    from v3_app.services.help_docs import HELP_CATEGORY_ORDER, articles_by_category, get_article

    expected = {
        "Advanced Pages": ("Conditional Rules", "Effective Response Stack", "Helm"),
        "Analysis": ("Graphs and Previews", "Runtime Indicators"),
        "Core Pages": ("Base Tuning", "Combat Profile", "Filtering", "Modes", "Profiles", "Mapping"),
        "Diagnostics": ("Performance / Diagnostics",),
        "Getting Started": ("Quick Start", "Runtime Setup / vJoy Setup"),
        "Reference": ("Tuning Glossary",),
        "Workflow": ("Saving and Importing",),
    }

    grouped = articles_by_category()
    assert tuple(expected) == HELP_CATEGORY_ORDER
    for category, titles in expected.items():
        assert category in grouped
        assert tuple(article.title for article in grouped[category]) == titles
        for title in titles:
            article = get_article(title)
            assert article.title == title
            assert article.category == category
            assert article.summary
            assert len(article.body) > 240


def test_phase11a_runtime_setup_article_preserves_runtime_truth_boundaries():
    from v3_app.services.help_docs import get_article

    article = get_article("Runtime Setup / vJoy Setup")
    text = article.search_text

    assert "Simulation mode works without physical HOTAS hardware" in text
    assert "Simulation mode also works without output verification" in text
    assert "Bridge telemetry is the runtime truth surface" in text
    assert "manual Bridge launch" in text
    assert "python -m bridge_app.main --run-for-ms 250" in text
    assert "The UI does not start, stop, restart, spawn, install, or manage the Bridge" in text
    assert "physical HOTAS discovery is discovery-only" in text
    assert "vJoy detected does not equal output verified" in text
    assert "output_verified remains false until guarded verification proves writes" in text
    assert "Full Live Runtime Ready remains false until the Phase 16 gate proves fresh input" in text
    assert "blocked_missing_device" in text
    assert "stale, missing, or invalid telemetry falls back safely" in text
    assert "Run Preflight and Bridge commands are safe requests, not proof of runtime success" in text
    assert "command acknowledgement requires matching request_id" in text
    for forbidden_claim in (
        "live HOTAS polling is active",
        "vJoy writes are active",
        "Full Live Runtime Ready is available",
        "the UI can launch the Bridge",
    ):
        assert forbidden_claim not in text


def test_phase11a_helm_runtime_indicators_saving_and_glossary_articles_are_specific():
    from v3_app.services.help_docs import get_article

    helm = get_article("Helm").search_text
    assert "top-right ASSISTANT cluster" in helm
    assert "overlay/modal" in helm
    assert "deterministic and local" in helm
    assert "does not use cloud AI or LLM behavior" in helm
    assert "Apply Selected Changes modifies only the in-memory workspace draft" in helm
    assert "Save Workspace remains the only persistence action" in helm
    assert "does not mutate conditional rules in v1" in helm
    assert "does not perform live hardware analysis" in helm

    indicators = get_article("Runtime Indicators").search_text
    for term in (
        "Telemetry",
        "Bridge lifecycle",
        "Runtime truth",
        "Output verified",
        "Full Live Runtime Ready",
        "HOTAS discovery",
        "Process hint",
        "Command acknowledgement",
        "Stale telemetry",
        "Missing telemetry",
        "Invalid telemetry",
        "Simulation fallback",
    ):
        assert term in indicators

    saving = get_article("Saving and Importing").search_text
    assert "current workspace draft" in saving
    assert "dirty/unsaved state" in saving
    assert "Helm changes remain in memory until saved" in saving
    assert "command requests do not save the workspace" in saving
    assert "runtime telemetry does not modify workspace settings" in saving

    glossary = get_article("Tuning Glossary").search_text
    for term in (
        "Curve strength",
        "Deadzone",
        "Anti-deadzone",
        "Hysteresis",
        "Output scale",
        "Max output",
        "Center alpha",
        "Edge alpha",
        "Same slew limit",
        "Reverse slew limit",
        "Combat scale",
        "Precision mode",
        "Combat mode",
        "Stack mode",
        "Conditional rule",
        "Response stack",
        "Output verification",
    ):
        assert term in glossary


def test_phase11a_search_is_local_deterministic_and_finds_runtime_and_helm():
    from v3_app.services.help_docs import search_articles

    helm_results = search_articles("Helm overlay local in-memory")
    runtime_results = search_articles("vJoy output verified runtime setup")

    assert helm_results[0].article.title == "Helm"
    assert runtime_results[0].article.title == "Runtime Setup / vJoy Setup"
    assert any(result.article.title == "Runtime Indicators" for result in search_articles("stale telemetry"))


def test_phase11a_help_docs_page_constructs_with_controls_categories_and_default_article(tmp_path):
    from PySide6.QtWidgets import QComboBox, QLineEdit, QListWidget

    shell = _shell(tmp_path)
    page = shell.page_widgets["help_docs"].widget()

    text = _label_text(page)
    search = page.findChild(QLineEdit, "helpDocsSearchField")
    sort = page.findChild(QComboBox, "helpDocsSortDropdown")
    topics = page.findChild(QListWidget, "helpDocsTopicList")

    assert "Help / Docs" in text
    assert "Search the built-in guide, browse by category, and keep the details you use most close at hand." in text
    assert search is not None
    assert search.placeholderText() == "Search features, pages, or tuning terms"
    assert sort is not None
    assert sort.currentText() == "By Category"
    assert "By Category" in [sort.itemText(index) for index in range(sort.count())]
    assert topics is not None
    topic_text = "\n".join(topics.item(index).text() for index in range(topics.count()))
    for expected in (
        "Getting Started",
        "Quick Start",
        "Runtime Setup / vJoy Setup",
        "Advanced Pages",
        "Conditional Rules",
        "Effective Response Stack",
        "Helm",
        "Performance / Diagnostics",
        "Tuning Glossary",
    ):
        assert expected in topic_text
    assert "Quick Start" in text


def test_phase11a_search_filters_topic_list_and_selection_updates_guide_content(tmp_path):
    from PySide6.QtWidgets import QLabel, QLineEdit, QListWidget

    shell = _shell(tmp_path)
    page = shell.page_widgets["help_docs"].widget()
    search = page.findChild(QLineEdit, "helpDocsSearchField")
    topics = page.findChild(QListWidget, "helpDocsTopicList")

    search.setText("vJoy runtime setup")
    filtered = [topics.item(index).text() for index in range(topics.count())]
    assert any("Runtime Setup / vJoy Setup" in item for item in filtered)
    assert all("Runtime Setup / vJoy Setup" in item or "Runtime Indicators" in item for item in filtered)

    runtime_item = next(topics.item(index) for index in range(topics.count()) if "Runtime Setup / vJoy Setup" in topics.item(index).text())
    topics.setCurrentItem(runtime_item)
    text = _label_text(page)
    assert "Runtime Setup / vJoy Setup" in page.findChild(QLabel, "helpArticleTitle").text()
    assert "Simulation mode works without physical HOTAS hardware" in text
    assert "vJoy detected does not equal output verified" in text

    search.setText("Helm overlay")
    helm_item = next(topics.item(index) for index in range(topics.count()) if "Helm" in topics.item(index).text())
    topics.setCurrentItem(helm_item)
    text = _label_text(page)
    assert "Helm" in page.findChild(QLabel, "helpArticleTitle").text()
    assert "Helm launches from the top-right ASSISTANT cluster" in text
    assert "Apply Selected Changes modifies only the in-memory workspace draft" in text


def test_phase11a_no_runtime_authority_controls_or_imports_are_added(tmp_path):
    from PySide6.QtWidgets import QPushButton

    shell = _shell(tmp_path)
    page = shell.page_widgets["help_docs"].widget()
    button_text = " ".join(button.text() for button in page.findChildren(QPushButton))
    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "VerifyOutput",
        "Verify Output",
        "Install Service",
        "Enable Auto Start",
    ):
        assert forbidden not in button_text

    source_paths = tuple((PROJECT_ROOT / "v3_app" / "pages").glob("*.py")) + tuple(
        (PROJECT_ROOT / "v3_app" / "services").glob("*.py")
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
    for token in (
        "UpdateVJD",
        "SetAxis",
        "SetBtn",
        "AcquireVJD",
        "subprocess.Popen",
        "QProcess",
        "startDetached",
        "Start-Process",
        "win32serviceutil",
        "schtasks",
        "pystray",
        "openai",
        "anthropic",
        "auto_save",
    ):
        assert token not in sources


def test_phase11a_documentation_records_help_docs_scope_and_phase11b_deferral():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-11a-help-docs-foundation-report.md"
    assert report.exists()
    docs = "\n".join(
        path.read_text(encoding="utf-8")
            for path in (
                PROJECT_ROOT / "docs" / "HelmForge" / "phase-ledger.md",
                PROJECT_ROOT / "docs" / "HelmForge" / "bridge-ui-architecture.md",
                report,
            )
    )
    for phrase in (
        "Phase 11A implements Help / Docs foundation only",
        "Perf / Diagnostics page work is deferred to Phase 11B",
        "Runtime Setup / vJoy Setup article is local built-in documentation",
        "Help / Docs does not add runtime authority",
        "Help / Docs does not use cloud AI or LLM behavior",
    ):
        assert phrase in docs
