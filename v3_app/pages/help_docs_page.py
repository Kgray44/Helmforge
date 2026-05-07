from __future__ import annotations

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
    QVBoxLayout,
    QWidget,
)

from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.driver_setup import VJOY_SETUP_SOURCE_URL
from shared_core.runtime.setup_guidance import OFFICIAL_THRUSTMASTER_SUPPORT_PAGE
from v3_app.pages.page_helpers import card, card_header, card_layout, page_intro
from v3_app.services.app_state import AppState
from v3_app.services.help_docs import HelpArticle, all_articles, articles_by_category, get_article, search_articles
from v3_app.ui.status_chips import action_button, status_chip


class HelpDocsPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("helpDocsPage")
        self._state = state
        self._workspace = workspace
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._articles = all_articles()
        self._current_article = get_article("Quick Start")

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
        self.sort_dropdown.addItem("By Category")
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
        layout.addWidget(card_header("Topics", "Browse the built-in guide by category."))
        self.topic_list = QListWidget()
        self.topic_list.setObjectName("helpDocsTopicList")
        self.topic_list.setMinimumHeight(520)
        self.topic_list.currentItemChanged.connect(self._topic_selected)
        layout.addWidget(self.topic_list, 1)
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
        guide_body = QWidget()
        guide_body.setObjectName("helpArticleBodyPanel")
        self.article_body_layout = QVBoxLayout(guide_body)
        self.article_body_layout.setContentsMargins(0, 0, 0, 0)
        self.article_body_layout.setSpacing(12)
        self.guide_scroll.setWidget(guide_body)
        layout.addWidget(self.guide_scroll, 1)
        return frame

    def _populate_topics(self) -> None:
        query = self.search_field.text().strip() if hasattr(self, "search_field") else ""
        previous = self._current_article.title if self._current_article else "Quick Start"
        self.topic_list.blockSignals(True)
        self.topic_list.clear()

        if query:
            results = search_articles(query)
            articles = tuple(result.article for result in results)
            for article in articles:
                self._add_article_item(article, prefix=article.category)
        else:
            for category, articles in articles_by_category().items():
                header = QListWidgetItem(category)
                header.setData(Qt.ItemDataRole.UserRole, None)
                header.setFlags(Qt.ItemFlag.ItemIsEnabled)
                header.setForeground(Qt.GlobalColor.lightGray)
                self.topic_list.addItem(header)
                for article in articles:
                    self._add_article_item(article)

        selected_row = 0
        for row in range(self.topic_list.count()):
            item = self.topic_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == previous:
                selected_row = row
                break
        self.topic_list.blockSignals(False)
        if self.topic_list.count():
            self.topic_list.setCurrentRow(selected_row)
            item = self.topic_list.currentItem()
            if item is not None and item.data(Qt.ItemDataRole.UserRole):
                self._render_article(get_article(str(item.data(Qt.ItemDataRole.UserRole))))

    def _add_article_item(self, article: HelpArticle, *, prefix: str | None = None) -> None:
        text = article.title if prefix is None else f"{prefix} / {article.title}"
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, article.title)
        self.topic_list.addItem(item)

    def _topic_selected(self, item: QListWidgetItem | None, _previous: QListWidgetItem | None = None) -> None:
        if item is None:
            return
        title = item.data(Qt.ItemDataRole.UserRole)
        if not title:
            return
        self._render_article(get_article(str(title)))

    def _render_article(self, article: HelpArticle) -> None:
        self._current_article = article
        self.article_title.setText(article.title)
        self.article_category.setText(f"{article.category} guide")
        self.article_summary.setText(article.summary)
        _clear_layout(self.article_body_layout)
        for paragraph in article.paragraphs:
            label = QLabel(paragraph)
            label.setObjectName("helpArticleParagraph")
            label.setWordWrap(True)
            self.article_body_layout.addWidget(label)
        if article.related_topics:
            related = QLabel(f"Related topics: {', '.join(article.related_topics)}")
            related.setObjectName("sectionHint")
            related.setWordWrap(True)
            self.article_body_layout.addWidget(related)
        self.article_body_layout.addStretch(1)


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
