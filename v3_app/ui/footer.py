from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget

from v3_app.pages.placeholders import PageDefinition
from v3_app.services.app_state import AppState
from v3_app.ui.status_chips import action_button


class Footer(QWidget):
    def __init__(
        self,
        state: AppState,
        active_page: PageDefinition,
        *,
        on_import_profile: Callable[[], None] | None = None,
        on_revert: Callable[[], None] | None = None,
        on_save: Callable[[], None] | None = None,
    ) -> None:
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

        actions = QWidget()
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)
        import_button = action_button("Import Profile", object_name="importProfileButton")
        revert_button = action_button("Revert", object_name="revertButton")
        save_button = action_button("Save Workspace", object_name="saveWorkspaceButton")
        if on_import_profile is not None:
            import_button.clicked.connect(on_import_profile)
        if on_revert is not None:
            revert_button.clicked.connect(on_revert)
        if on_save is not None:
            save_button.clicked.connect(on_save)
        action_layout.addWidget(import_button)
        action_layout.addWidget(revert_button)
        action_layout.addWidget(save_button)

        layout.addWidget(self._message, 1)
        layout.addWidget(actions)
        self.update_state(state, active_page)

    def update_state(self, state: AppState, active_page: PageDefinition) -> None:
        self._state = state
        self._active_page = active_page
        self._message.setText(state.status_message)
