from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.driver_setup import VJOY_SETUP_SOURCE_URL
from shared_core.runtime.setup_guidance import OFFICIAL_THRUSTMASTER_SUPPORT_PAGE
from v3_app.pages.page_helpers import card, card_header, card_layout, page_intro, truth_notice
from v3_app.services.app_state import AppState
from v3_app.services.help_docs import (
    HELP_SORT_OPTIONS,
    HelpArticle,
    all_articles,
    articles_by_category,
    get_article,
    parameter_reference_entries,
    search_articles,
    topic_category_for,
    topic_tree_by_category,
)
from v3_app.services.parameter_metadata import ParameterMetadata
from v3_app.ui.status_chips import action_button, status_chip


OpenPageCallback = Callable[[str], None]
OpenHelmCallback = Callable[[], None]

PAGE_BUTTON_LABELS = {
    "mapping": "Open Mapping",
    "base_tuning": "Open Base Tuning",
    "filtering": "Open Filtering",
    "combat_profile": "Open Combat Profile",
    "modes": "Open Modes",
    "conditional_rules": "Open Conditional Rules",
    "effective_response_stack": "Open Effective Response Stack",
    "live_monitor": "Open Live Monitor",
    "flight_recorder": "Open Flight Recorder",
    "perf_diagnostics": "Open Perf / Diagnostics",
    "helm": "Open Helm",
}


class HelpDocsPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        on_open_page: OpenPageCallback | None = None,
        on_open_helm: OpenHelmCallback | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("helpDocsPage")
        self._state = state
        self._workspace = workspace
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._articles = all_articles()
        self._current_article = get_article("Quick Start")
        self._on_open_page = on_open_page
        self._on_open_helm = on_open_helm
        self._last_opened: dict[str, int] = {}
        self._open_counter = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)
        root.addWidget(
            page_intro(
                "Help / Docs",
                "Search the built-in guide, browse by category, and keep the details you use most close at hand.",
                "Local documentation only. These guides explain current boundaries without performing runtime actions.",
            )
        )
        root.addWidget(
            truth_notice(
                "Documentation is local. Parameter Reference and page navigation explain current boundaries; "
                "they do not start services, verify output, or contact cloud systems.",
                object_name="helpDocsReadabilityNotice",
            )
        )
        root.addWidget(self._build_controls_card())

        split = QHBoxLayout()
        split.setSpacing(18)
        split.addWidget(self._build_topics_card(), 1)
        split.addWidget(self._build_article_card(), 2)
        root.addLayout(split, 1)
        root.addStretch(1)

        self._populate_topics()
        self._render_article(self._current_article)

    def _build_controls_card(self) -> QFrame:
        frame = card("helpDocsControlsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Guide Controls", "Search locally across titles, categories, keywords, and article text."))
        row = QHBoxLayout()
        row.setSpacing(10)

        search_label = QLabel("Search")
        search_label.setObjectName("formLabel")
        self.search_field = QLineEdit()
        self.search_field.setObjectName("helpDocsSearchField")
        self.search_field.setPlaceholderText("Search features, pages, or tuning terms")
        self.search_field.textChanged.connect(self._populate_topics)

        sort_label = QLabel("Sort")
        sort_label.setObjectName("formLabel")
        self.sort_dropdown = QComboBox()
        self.sort_dropdown.setObjectName("helpDocsSortDropdown")
        self.sort_dropdown.addItems(HELP_SORT_OPTIONS)
        self.sort_dropdown.currentTextChanged.connect(self._populate_topics)

        row.addWidget(search_label)
        row.addWidget(self.search_field, 1)
        row.addWidget(sort_label)
        row.addWidget(self.sort_dropdown)
        row.addWidget(status_chip("Local Docs", tone="success", object_name="helpDocsLocalChip"))
        row.addWidget(
            status_chip(
                f"Output verified: {str(self._runtime_status.live_output_writes_verified).lower()}",
                tone="warning",
                object_name="helpDocsOutputTruthChip",
            )
        )
        layout.addLayout(row)

        source_row = QHBoxLayout()
        source_row.setSpacing(10)
        source_note = QLabel("Setup source links are manual references; opening them is a user action.")
        source_note.setObjectName("sectionHint")
        source_note.setWordWrap(True)
        support_button = QPushButton("Open Official Thrustmaster Support Page")
        support_button.setObjectName("supportButton")
        support_button.setProperty("uiRole", "actionButton")
        support_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(OFFICIAL_THRUSTMASTER_SUPPORT_PAGE)))
        vjoy_button = action_button("Open vJoy Setup Source", object_name="vjoyButton")
        vjoy_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(VJOY_SETUP_SOURCE_URL)))
        source_row.addWidget(source_note, 1)
        source_row.addWidget(support_button)
        source_row.addWidget(vjoy_button)
        layout.addLayout(source_row)
        return frame

    def _build_topics_card(self) -> QFrame:
        frame = card("helpDocsTopicsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Topics", "Browse the built-in manual by collapsible category."))
        self.topic_tree = QTreeWidget()
        self.topic_tree.setObjectName("helpDocsTopicTree")
        self.topic_tree.setMinimumHeight(520)
        self.topic_tree.setHeaderHidden(True)
        self.topic_tree.currentItemChanged.connect(self._tree_topic_selected)
        layout.addWidget(self.topic_tree, 1)

        self.topic_list = QListWidget()
        self.topic_list.setObjectName("helpDocsTopicList")
        self.topic_list.hide()
        self.topic_list.currentItemChanged.connect(self._legacy_topic_selected)
        layout.addWidget(self.topic_list)
        return frame

    def _build_article_card(self) -> QFrame:
        frame = card("helpDocsGuideCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Guide", "Selected article and related reference."))

        self.article_title = QLabel("")
        self.article_title.setObjectName("helpArticleTitle")
        self.article_title.setWordWrap(True)
        self.article_category = QLabel("")
        self.article_category.setObjectName("helpArticleCategory")
        self.article_category.setWordWrap(True)
        self.article_summary = QLabel("")
        self.article_summary.setObjectName("helpArticleSummary")
        self.article_summary.setWordWrap(True)

        layout.addWidget(self.article_title)
        layout.addWidget(self.article_category)
        layout.addWidget(self.article_summary)

        self.guide_scroll = QScrollArea()
        self.guide_scroll.setObjectName("helpDocsGuideScrollArea")
        self.guide_scroll.setWidgetResizable(True)
        self.guide_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.guide_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.article_surface = QFrame()
        self.article_surface.setObjectName("helpArticleSurface")
        self.article_surface.setProperty("helpArticleSurface", True)
        self.article_surface.setProperty("postRc4eReadable", True)
        self.article_body_layout = QVBoxLayout(self.article_surface)
        self.article_body_layout.setContentsMargins(18, 16, 18, 18)
        self.article_body_layout.setSpacing(14)
        self.guide_scroll.setWidget(self.article_surface)
        layout.addWidget(self.guide_scroll, 1)
        return frame

    def _populate_topics(self) -> None:
        query = self.search_field.text().strip() if hasattr(self, "search_field") else ""
        sort_mode = self.sort_dropdown.currentText() if hasattr(self, "sort_dropdown") else "By Category"
        previous = self._current_article.title if self._current_article else "Quick Start"
        articles = tuple(result.article for result in search_articles(query)) if query else self._articles
        grouped = topic_tree_by_category(articles, sort_mode=sort_mode, last_opened=self._last_opened)

        self.topic_tree.blockSignals(True)
        self.topic_tree.clear()
        for category, category_articles in grouped.items():
            parent = QTreeWidgetItem((category,))
            parent.setData(0, Qt.ItemDataRole.UserRole, None)
            parent.setFlags(Qt.ItemFlag.ItemIsEnabled)
            parent.setExpanded(True)
            parent.setFirstColumnSpanned(True)
            self.topic_tree.addTopLevelItem(parent)
            for article in category_articles:
                child = QTreeWidgetItem((article.title,))
                child.setData(0, Qt.ItemDataRole.UserRole, article.title)
                child.setToolTip(0, article.summary)
                parent.addChild(child)
        self.topic_tree.blockSignals(False)

        self._populate_legacy_topic_list(articles, query=query)
        self._select_topic(previous)

    def _populate_legacy_topic_list(self, articles: tuple[HelpArticle, ...], *, query: str) -> None:
        previous = self._current_article.title if self._current_article else "Quick Start"
        self.topic_list.blockSignals(True)
        self.topic_list.clear()
        if query:
            for article in articles:
                self._add_legacy_article_item(article, prefix=article.category)
        else:
            for category, category_articles in articles_by_category().items():
                header = QListWidgetItem(category)
                header.setData(Qt.ItemDataRole.UserRole, None)
                header.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.topic_list.addItem(header)
                for article in category_articles:
                    self._add_legacy_article_item(article)
        self.topic_list.blockSignals(False)
        for row in range(self.topic_list.count()):
            item = self.topic_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == previous:
                self.topic_list.setCurrentRow(row)
                break

    def _add_legacy_article_item(self, article: HelpArticle, *, prefix: str | None = None) -> None:
        text = article.title if prefix is None else f"{prefix} / {article.title}"
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, article.title)
        self.topic_list.addItem(item)

    def _select_topic(self, title: str) -> None:
        fallback: QTreeWidgetItem | None = None
        for row in range(self.topic_tree.topLevelItemCount()):
            parent = self.topic_tree.topLevelItem(row)
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                if fallback is None:
                    fallback = child
                if child.data(0, Qt.ItemDataRole.UserRole) == title:
                    self.topic_tree.setCurrentItem(child)
                    self._render_article(get_article(title))
                    return
        if fallback is not None:
            self.topic_tree.setCurrentItem(fallback)
            article_title = str(fallback.data(0, Qt.ItemDataRole.UserRole))
            self._render_article(get_article(article_title))

    def _tree_topic_selected(self, item: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None = None) -> None:
        if item is None:
            return
        title = item.data(0, Qt.ItemDataRole.UserRole)
        if not title:
            return
        self._render_article(get_article(str(title)))

    def _legacy_topic_selected(self, item: QListWidgetItem | None, _previous: QListWidgetItem | None = None) -> None:
        if item is None:
            return
        title = item.data(Qt.ItemDataRole.UserRole)
        if not title:
            return
        self._render_article(get_article(str(title)))

    def _render_article(self, article: HelpArticle) -> None:
        self._current_article = article
        self._open_counter += 1
        self._last_opened[article.title] = self._open_counter
        self.article_title.setText(article.title)
        self.article_category.setText(f"{topic_category_for(article)} guide")
        self.article_summary.setText(article.summary)
        _clear_layout(self.article_body_layout)

        if article.sections:
            for section in article.sections:
                self._add_section(section.heading, section.body)
        else:
            self._add_section("What this is", article.paragraphs)

        self._add_parameter_blocks(article)
        if article.related_topics:
            related = QLabel(f"Related topics: {', '.join(article.related_topics)}")
            related.setObjectName("helpArticleRelated")
            related.setWordWrap(True)
            self.article_body_layout.addWidget(related)
        self._add_open_button(article)
        self.article_body_layout.addStretch(1)

    def _add_section(self, heading: str, paragraphs: tuple[str, ...]) -> None:
        section = QFrame()
        section.setObjectName("helpArticleSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel(heading)
        title.setObjectName("helpArticleSectionTitle")
        title.setWordWrap(True)
        layout.addWidget(title)
        for paragraph in paragraphs:
            label = QLabel(paragraph)
            label.setObjectName("helpArticleParagraph")
            label.setWordWrap(True)
            layout.addWidget(label)
        self.article_body_layout.addWidget(section)

    def _add_parameter_blocks(self, article: HelpArticle) -> None:
        if article.title == "Parameter Reference":
            metadata_entries = parameter_reference_entries()
        else:
            metadata_entries = tuple(
                metadata
                for metadata_id in article.parameter_ids
                if (metadata := _metadata_or_none(metadata_id)) is not None
            )
        if not metadata_entries:
            return

        heading = QLabel("Parameter reference")
        heading.setObjectName("helpArticleSectionTitle")
        heading.setWordWrap(True)
        self.article_body_layout.addWidget(heading)
        for metadata in metadata_entries:
            self.article_body_layout.addWidget(_parameter_block(metadata))

    def _add_open_button(self, article: HelpArticle) -> None:
        if not article.open_page_id:
            return
        button = action_button(PAGE_BUTTON_LABELS.get(article.open_page_id, f"Open {article.open_page_id}"))
        button.setObjectName(f"helpOpenPageButton_{article.open_page_id}")
        button.setProperty("pageId", article.open_page_id)
        button.clicked.connect(lambda _checked=False, page_id=article.open_page_id: self._open_target(page_id))
        self.article_body_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)

    def _open_target(self, page_id: str) -> None:
        if page_id == "helm":
            if self._on_open_helm is not None:
                self._on_open_helm()
            return
        if self._on_open_page is not None:
            self._on_open_page(page_id)


def _metadata_or_none(metadata_id: str) -> ParameterMetadata | None:
    from v3_app.services.parameter_metadata import PARAMETER_HELP

    return PARAMETER_HELP.get(metadata_id)


def _parameter_block(metadata: ParameterMetadata) -> QFrame:
    block = QFrame()
    block.setObjectName("helpParameterReferenceBlock")
    block.setProperty("metadataId", metadata.parameter_id)
    layout = QGridLayout(block)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setHorizontalSpacing(14)
    layout.setVerticalSpacing(7)

    title = QLabel(metadata.display_name)
    title.setObjectName("helpParameterName")
    title.setWordWrap(True)
    layout.addWidget(title, 0, 0, 1, 2)

    rows = (
        ("ID", metadata.parameter_id),
        ("Page", metadata.category),
        ("Scope", metadata.support_scope.value.replace("_", " ")),
        ("Type", metadata.value_type.value),
        ("Default", _format_value(metadata.default_value)),
        ("Range", _format_range_or_options(metadata)),
        ("Examples", _format_examples(metadata)),
    )
    for row, (label_text, value_text) in enumerate(rows, start=1):
        label = QLabel(label_text)
        label.setObjectName("tableMutedText")
        value = QLabel(value_text)
        value.setObjectName("helpParameterValue")
        value.setWordWrap(True)
        layout.addWidget(label, row, 0)
        layout.addWidget(value, row, 1)
    if metadata.warning_text:
        warning = QLabel(metadata.warning_text)
        warning.setObjectName("helpParameterWarning")
        warning.setWordWrap(True)
        layout.addWidget(warning, len(rows) + 1, 0, 1, 2)
    return block


def _format_value(value: object) -> str:
    if value is None:
        return "Not specified"
    return str(value)


def _format_range_or_options(metadata: ParameterMetadata) -> str:
    if metadata.value_range is not None:
        units = f" {metadata.units}" if metadata.units else ""
        text = f"{metadata.min_value} to {metadata.max_value}{units}"
        if metadata.recommended_range is not None:
            text += f" (recommended {metadata.recommended_range.recommended_minimum} to {metadata.recommended_range.recommended_maximum}{units})"
        return text
    if metadata.dropdown_options:
        return ", ".join(metadata.dropdown_options)
    return "Not applicable"


def _format_examples(metadata: ParameterMetadata) -> str:
    examples = []
    if metadata.low_or_min_example is not None:
        examples.append(f"{metadata.low_or_min_example.value}: {metadata.low_or_min_example.effect}")
    if metadata.high_or_max_example is not None:
        examples.append(f"{metadata.high_or_max_example.value}: {metadata.high_or_max_example.effect}")
    return " | ".join(examples) if examples else "No examples recorded"


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
