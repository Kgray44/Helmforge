from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from shared_core.models.profiles import ProfileType
from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.models.workspace import CONFIG_FILENAME, WorkspaceConfig, create_default_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from v3_app.pages.page_helpers import (
    OnStatus,
    card,
    card_header,
    card_layout,
    format_buttons,
    page_intro,
    runtime_truth_rows,
    truth_notice,
    value_grid,
)
from v3_app.services.app_state import AppState
from v3_app.ui.status_chips import action_button, status_chip


class ProfilesPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        on_status: OnStatus | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("profilesPage")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)

        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._on_status = on_status

        intro_row = QHBoxLayout()
        intro_row.addWidget(
            page_intro(
                "Profiles",
                "Keep built-in presets and personal profiles in one library. The selected profile becomes the live workspace for the rest of V3.",
            ),
            1,
        )
        intro_actions = QHBoxLayout()
        save_new = action_button("Save Current As New", object_name="saveCurrentAsNewButton")
        import_json = action_button("Import JSON", object_name="importJsonButton")
        for button in (save_new, import_json):
            button.clicked.connect(lambda _checked=False, label=button.text(): self._status(f"{label} is reserved for a later profile persistence phase."))
            intro_actions.addWidget(button)
        intro_row.addLayout(intro_actions)
        root.addLayout(intro_row)

        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        status_row.addWidget(status_chip("Active Profile", tone="success"))
        active_note = QLabel("Current Workspace is currently active across Modes, Base Tuning, Filtering, Combat Profile, Rules, and Stack.")
        active_note.setObjectName("cardBody")
        status_row.addWidget(active_note, 1)
        root.addLayout(status_row)
        root.addWidget(
            truth_notice(
                "Profile selection is a workspace draft decision. Save Workspace remains the explicit persistence step; "
                "no profile is runtime-activated outside this local configuration surface.",
                object_name="profilesDraftPolishNotice",
            )
        )

        main = QHBoxLayout()
        main.setSpacing(18)
        main.addWidget(self._build_library_card(), 1)

        detail = QVBoxLayout()
        detail.setSpacing(18)
        detail.addWidget(self._build_detail_card())
        mid = QHBoxLayout()
        mid.setSpacing(18)
        mid.addWidget(self._build_setup_summary_card(), 1)
        mid.addWidget(self._build_profile_feel_card(), 1)
        detail.addLayout(mid)
        detail.addWidget(self._build_actions_card())
        main.addLayout(detail, 2)
        root.addLayout(main)

    def _build_library_card(self) -> QWidget:
        frame = card("profileLibraryCard")
        layout = card_layout(frame)
        layout.addWidget(
            card_header(
                "Profile Library",
                "Choose a built-in preset or a personal profile. Selecting one makes it the active workspace immediately.",
            )
        )
        tree = QTreeWidget()
        tree.setObjectName("profileLibraryTree")
        tree.setColumnCount(3)
        tree.setHeaderLabels(("Profile", "Type", "State"))
        built_in_root = QTreeWidgetItem(("Built-In Presets", "", ""))
        personal_root = QTreeWidgetItem(("Personal Profiles", "", ""))
        selected_item: QTreeWidgetItem | None = None
        for profile in self._workspace.profiles.profiles:
            if profile.profile_type is ProfileType.BUILT_IN:
                item = QTreeWidgetItem((profile.name, "Preset", "Ready"))
                built_in_root.addChild(item)
                if selected_item is None:
                    selected_item = item
            else:
                state = "Active" if profile.active else "Ready"
                item = QTreeWidgetItem((profile.name, "Personal", state))
                personal_root.addChild(item)
                if profile.active:
                    selected_item = item
        tree.addTopLevelItem(built_in_root)
        tree.addTopLevelItem(personal_root)
        tree.expandAll()
        if selected_item is not None:
            tree.setCurrentItem(selected_item)
        tree.setColumnWidth(0, 230)
        tree.setColumnWidth(1, 90)
        tree.setMinimumHeight(420)
        layout.addWidget(tree)

        actions = QHBoxLayout()
        for text, name in (("Duplicate", "duplicateProfileButton"), ("Export JSON", "exportProfileButton")):
            button = action_button(text, object_name=name)
            button.clicked.connect(lambda _checked=False, label=text: self._status(f"{label} is reserved for a later profile persistence phase."))
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)
        return frame

    def _build_detail_card(self) -> QWidget:
        frame = card("profileDetailCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Profile Detail", "Review what the selected profile does before you tune deeper pages."))
        title = QLabel("Current Workspace")
        title.setObjectName("snapshotValue")
        layout.addWidget(title)
        source = QLabel(f"Loaded from the current V3 workspace copy: {CONFIG_FILENAME}.")
        source.setObjectName("cardBody")
        source.setWordWrap(True)
        layout.addWidget(source)
        chips = QHBoxLayout()
        chips.addWidget(status_chip("Personal", tone="success"))
        chips.addWidget(status_chip("Active", tone="success"))
        chips.addWidget(status_chip(CONFIG_FILENAME, tone="neutral"))
        chips.addStretch(1)
        layout.addLayout(chips)
        note = QLabel(
            "Selecting a profile makes it the active workspace immediately. Edits in the rest of the app update this personal profile draft until saved."
        )
        note.setObjectName("cardBody")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addLayout(value_grid(runtime_truth_rows(self._runtime_status)))
        return frame

    def _build_setup_summary_card(self) -> QWidget:
        frame = card("profileSetupSummaryCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Setup Summary", "Quick view of what this profile is wired to."))
        enabled_rules = sum(1 for rule in self._workspace.rules.rules if rule.enabled)
        layout.addLayout(
            value_grid(
                (
                    ("Mapped Axes", str(len(self._workspace.mappings.axis_routes))),
                    ("Precision", f"button {format_buttons(self._workspace.modes.precision_hold_buttons)}"),
                    ("Combat Trigger", format_buttons(self._workspace.modes.combat_trigger_buttons)),
                    ("Zoom Gate", f"button {format_buttons(self._workspace.modes.combat_zoom_aim_buttons)}"),
                    ("Extra Gate", format_buttons(self._workspace.modes.combat_extra_buttons)),
                    ("Stack Mode", self._workspace.modes.precision_combat_stack_mode.value),
                    ("Enabled Rules", str(enabled_rules)),
                )
            )
        )
        return frame

    def _build_profile_feel_card(self) -> QWidget:
        frame = card("profileFeelCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Profile Feel", "High-level reading of the main flight axes in this profile."))
        text = QLabel(
            "Roll: stable center response, fast same-direction response. Combat: stable center response, trimmed overall authority.\n"
            "Pitch: stable center response. Combat: soft near center.\n"
            "Yaw: soft near center, stable center response. Combat: soft near center, strong edge ramp."
        )
        text.setObjectName("cardBody")
        text.setWordWrap(True)
        layout.addWidget(text)
        return frame

    def _build_actions_card(self) -> QWidget:
        frame = card("profileActionsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Profile Actions", "Use presets as a starting point, duplicate variants, and manage your personal library here."))
        actions = QHBoxLayout()
        for text, name in (
            ("Use This Profile", "useProfileButton"),
            ("Rename", "renameProfileButton"),
            ("Delete", "deleteProfileButton"),
        ):
            button = action_button(text, object_name=name)
            button.clicked.connect(lambda _checked=False, label=text: self._status(f"{label} is reserved for a later profile editing phase."))
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)
        note = QLabel(
            "This personal profile is active right now. Any changes you make elsewhere in V3 update it inside the current workspace draft."
        )
        note.setObjectName("cardBody")
        note.setWordWrap(True)
        layout.addWidget(note)
        return frame

    def _status(self, message: str) -> None:
        if self._on_status is not None:
            self._on_status(message)
