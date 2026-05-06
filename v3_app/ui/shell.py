from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from shared_core.models.workspace import CONFIG_FILENAME, WorkspaceConfig, create_default_workspace
from shared_core.persistence.workspace_store import WorkspaceJsonError, load_workspace, save_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from v3_app.pages.base_tuning_page import BaseTuningPage
from v3_app.pages.combat_profile_page import CombatProfilePage
from v3_app.pages.conditional_rules_page import ConditionalRulesPage
from v3_app.pages.effective_response_stack_page import EffectiveResponseStackPage
from v3_app.pages.filtering_page import FilteringPage
from v3_app.pages.mapping_page import MappingPage
from v3_app.pages.modes_page import ModesPage
from v3_app.pages.placeholders import PAGE_DEFINITIONS, create_placeholder_page, page_definition_by_id
from v3_app.pages.profiles_page import ProfilesPage
from v3_app.services.app_state import AppState, build_initial_app_state
from v3_app.ui.footer import Footer
from v3_app.ui.header import Header
from v3_app.ui.sidebar import Sidebar


class HelmForgeShell(QWidget):
    def __init__(
        self,
        state: AppState | None = None,
        *,
        workspace: WorkspaceConfig | None = None,
        workspace_path: str | Path | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("helmforgeShell")
        self.state = state or build_initial_app_state()
        self.workspace_path = Path(workspace_path or CONFIG_FILENAME)
        self.workspace = workspace or self._load_initial_workspace()
        self._last_saved_workspace = self.workspace
        self.state.source_config = str(self.workspace_path)
        self.runtime_status = build_runtime_preflight_status()
        self.active_page_id = self.state.active_page_id
        self.page_widgets: dict[str, QScrollArea] = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        self.sidebar = Sidebar(PAGE_DEFINITIONS, self.state, self.switch_page)
        self.header = Header(self.state)
        self.stack = QStackedWidget()
        self.stack.setObjectName("pageStack")
        self.footer = Footer(
            self.state,
            page_definition_by_id(self.active_page_id),
            on_import_profile=self.import_profile_placeholder,
            on_revert=self.revert_workspace,
            on_save=self.save_workspace,
        )

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

    def _load_initial_workspace(self) -> WorkspaceConfig:
        if self.workspace_path.exists():
            try:
                return load_workspace(self.workspace_path).workspace
            except WorkspaceJsonError as exc:
                self.state.status_message = f"Workspace load failed; using default draft. {exc}"
                self.state.saved = False
        return create_default_workspace()

    def _build_pages(self) -> None:
        for page in PAGE_DEFINITIONS:
            scroll = QScrollArea()
            scroll.setObjectName("pageScrollArea")
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            content = self._create_page_content(page.page_id, page)
            scroll.setWidget(content)
            self.stack.addWidget(scroll)
            self.page_widgets[page.page_id] = scroll

    def _rebuild_pages(self) -> None:
        while self.stack.count():
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()
        self.page_widgets = {}
        self._build_pages()
        self.switch_page(self.active_page_id, record_timing=False)

    def _create_page_content(self, page_id: str, page) -> QWidget:
        common = {
            "state": self.state,
            "workspace": self.workspace,
            "runtime_status": self.runtime_status,
        }
        if page_id == "mapping":
            return MappingPage(
                **common,
                on_dirty=self.mark_workspace_dirty,
                on_status=self.set_status_message,
                on_workspace_changed=self.update_workspace_draft,
            )
        if page_id == "modes":
            return ModesPage(**common, on_dirty=self.mark_workspace_dirty)
        if page_id == "base_tuning":
            return BaseTuningPage(**common, on_dirty=self.mark_workspace_dirty)
        if page_id == "filtering":
            return FilteringPage(**common, on_dirty=self.mark_workspace_dirty)
        if page_id == "combat_profile":
            return CombatProfilePage(**common, on_dirty=self.mark_workspace_dirty)
        if page_id == "profiles":
            return ProfilesPage(**common, on_status=self.set_status_message)
        if page_id == "conditional_rules":
            return ConditionalRulesPage(
                **common,
                on_dirty=self.mark_workspace_dirty,
                on_status=self.set_status_message,
                on_workspace_changed=self.update_workspace_draft,
            )
        if page_id == "effective_response_stack":
            return EffectiveResponseStackPage(**common)
        return create_placeholder_page(page, runtime_label=self.state.runtime.runtime_card_label)

    def mark_workspace_dirty(self, message: str) -> None:
        self.state.saved = False
        self.state.status_message = message
        self.header.update_state(self.state)
        self.footer.update_state(self.state, page_definition_by_id(self.active_page_id))

    def update_workspace_draft(self, workspace: WorkspaceConfig, message: str) -> None:
        self.workspace = workspace
        self.mark_workspace_dirty(message)

    def set_status_message(self, message: str) -> None:
        self.state.status_message = message
        self.footer.update_state(self.state, page_definition_by_id(self.active_page_id))

    def import_profile_placeholder(self) -> None:
        self.set_status_message("Import Profile is reserved for a later import phase; no workspace file was changed.")

    def save_workspace(self) -> None:
        try:
            save_workspace(self.workspace, self.workspace_path, overwrite=True)
        except Exception as exc:
            self.state.saved = False
            self.set_status_message(f"Workspace save failed: {exc}")
            self.header.update_state(self.state)
            return
        self._last_saved_workspace = self.workspace
        self.state.saved = True
        self.state.status_message = f"Saved workspace draft to {self.workspace_path}."
        self.header.update_state(self.state)
        self.footer.update_state(self.state, page_definition_by_id(self.active_page_id))

    def revert_workspace(self) -> None:
        if self.workspace_path.exists():
            try:
                self.workspace = load_workspace(self.workspace_path).workspace
            except WorkspaceJsonError as exc:
                self.set_status_message(f"Workspace revert failed: {exc}")
                return
        else:
            self.workspace = self._last_saved_workspace
        self._last_saved_workspace = self.workspace
        self.state.saved = True
        self.state.status_message = "Reverted the workspace to the last saved or imported state."
        self.header.update_state(self.state)
        self.footer.update_state(self.state, page_definition_by_id(self.active_page_id))
        self._rebuild_pages()

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
