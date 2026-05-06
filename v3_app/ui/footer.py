from __future__ import annotations

from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget

from v3_app.pages.placeholders import PageDefinition
from v3_app.services.app_state import AppState
from v3_app.ui.status_chips import action_button


class Footer(QWidget):
    def __init__(self, state: AppState, active_page: PageDefinition) -> None:
        super().__init__()
        self.setObjectName("appFooter")
        self._state = state
        self._active_page = active_page

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(18)

        self._message = QLabel(state.status_message)
        self._message.setObjectName("footerDetail")
        self._message.setWordWrap(True)

        self._page_detail = QLabel()
        self._page_detail.setObjectName("footerPageDetail")

        actions = QWidget()
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)
        action_layout.addWidget(action_button("Import Profile", object_name="importProfileButton"))
        action_layout.addWidget(action_button("Revert", object_name="revertButton"))
        action_layout.addWidget(action_button("Save Workspace", object_name="saveWorkspaceButton"))

        layout.addWidget(self._message, 1)
        layout.addWidget(self._page_detail, 2)
        layout.addWidget(actions)
        self.update_state(state, active_page)

    def update_state(self, state: AppState, active_page: PageDefinition) -> None:
        self._state = state
        self._active_page = active_page
        self._message.setText(state.status_message)
        self._page_detail.setText(
            f"Page: {active_page.title} | Axis: {state.selected_axis} | "
            f"Profile: {state.active_profile} | Source: Workspace copy: {state.source_config}"
        )
