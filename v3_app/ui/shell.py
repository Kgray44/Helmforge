from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from v3_app.pages.placeholders import PAGE_DEFINITIONS, create_placeholder_page, page_definition_by_id
from v3_app.services.app_state import AppState, build_initial_app_state
from v3_app.ui.footer import Footer
from v3_app.ui.header import Header
from v3_app.ui.sidebar import Sidebar


class HelmForgeShell(QWidget):
    def __init__(self, state: AppState | None = None) -> None:
        super().__init__()
        self.setObjectName("helmforgeShell")
        self.state = state or build_initial_app_state()
        self.active_page_id = self.state.active_page_id
        self.page_widgets: dict[str, QScrollArea] = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        self.sidebar = Sidebar(PAGE_DEFINITIONS, self.state, self.switch_page)
        self.header = Header(self.state)
        self.stack = QStackedWidget()
        self.stack.setObjectName("pageStack")
        self.footer = Footer(self.state, page_definition_by_id(self.active_page_id))

        main = QWidget()
        main.setObjectName("contentViewport")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        main_layout.addWidget(self.header)
        main_layout.addWidget(self.stack, 1)
        main_layout.addWidget(self.footer)

        root.addWidget(self.sidebar)
        root.addWidget(main, 1)

        self._build_pages()
        self.switch_page(self.active_page_id, record_timing=False)

    def _build_pages(self) -> None:
        for page in PAGE_DEFINITIONS:
            scroll = QScrollArea()
            scroll.setObjectName("pageScrollArea")
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            content = create_placeholder_page(page, runtime_label=self.state.runtime.runtime_card_label)
            scroll.setWidget(content)
            self.stack.addWidget(scroll)
            self.page_widgets[page.page_id] = scroll

    def switch_page(self, page_id: str, *, record_timing: bool = True) -> None:
        if page_id not in self.page_widgets:
            raise KeyError(page_id)

        start = time.perf_counter()
        self.active_page_id = page_id
        self.state.active_page_id = page_id
        self.stack.setCurrentWidget(self.page_widgets[page_id])
        self.sidebar.update_active(page_id)
        self.footer.update_state(self.state, page_definition_by_id(page_id))
        if record_timing:
            self.state.page_switch_timings_ms[page_id] = (time.perf_counter() - start) * 1000.0
