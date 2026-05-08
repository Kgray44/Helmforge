from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from v3_app.pages.page_helpers import (
    OnDirty,
    add_card_to_grid,
    card,
    card_header,
    card_layout,
    field_row,
    format_buttons,
    page_intro,
    runtime_truth_rows,
    value_grid,
)
from v3_app.services.app_state import AppState


class ModesPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        on_dirty: OnDirty | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("modesPage")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)

        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._on_dirty = on_dirty
        self._modes = self._workspace.modes

        root.addWidget(
            page_intro(
                "Modes",
                "Configure precision and combat activation without diving into raw tuning values.",
                "Keep trigger lists, zoom gating, and the current live mode state in one clear workspace.",
            )
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        add_card_to_grid(grid, self._build_precision_card(), 0, 0)
        add_card_to_grid(grid, self._build_combat_card(), 0, 1)
        add_card_to_grid(grid, self._build_live_state_card(), 1, 0)
        add_card_to_grid(grid, self._build_notes_card(), 1, 1)
        root.addLayout(grid)
        root.addStretch(1)

    def _build_precision_card(self) -> QWidget:
        frame = card("precisionModeCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Precision Mode", "Buttons that enable precision scaling."))
        grid = QGridLayout()
        dirty = "Modes precision button edit staged in the current workspace draft."
        field_row(
            grid,
            0,
            "Precision Hold Buttons",
            format_buttons(self._modes.precision_hold_buttons),
            object_name="precisionHoldButtonsField",
            on_dirty=self._on_dirty,
            dirty_message=dirty,
        )
        layout.addLayout(grid)
        layout.addStretch(1)
        layout.addWidget(_muted("Precision uses button hold detection. Configured."))
        return frame

    def _build_combat_card(self) -> QWidget:
        frame = card("combatModeCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Combat Mode", "Buttons that drive combat/zoom behavior."))
        grid = QGridLayout()
        dirty = "Modes combat button edit staged in the current workspace draft."
        field_row(grid, 0, "Combat Trigger Buttons", format_buttons(self._modes.combat_trigger_buttons), object_name="combatTriggerButtonsField", on_dirty=self._on_dirty, dirty_message=dirty)
        field_row(grid, 1, "Combat Zoom/Aim Buttons", format_buttons(self._modes.combat_zoom_aim_buttons), object_name="combatZoomButtonsField", on_dirty=self._on_dirty, dirty_message=dirty)
        field_row(grid, 2, "Combat Extra Buttons", format_buttons(self._modes.combat_extra_buttons), object_name="combatExtraButtonsField", on_dirty=self._on_dirty, dirty_message=dirty)
        field_row(grid, 3, "Stack Mode", self._modes.precision_combat_stack_mode.value, object_name="stackModeField", on_dirty=self._on_dirty, dirty_message=dirty)
        layout.addLayout(grid)
        layout.addWidget(_muted("Combat Trigger Buttons: Not configured. Combat Extra Buttons: Not configured."))
        layout.addWidget(_muted("Zoom buttons currently do activate combat behavior in the runtime layer."))
        return frame

    def _build_live_state_card(self) -> QWidget:
        frame = card("liveModeStateCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Live Mode State", "Current runtime mode evaluation from bridge telemetry."))
        state_label = QLabel("Normal")
        state_label.setObjectName("snapshotValue")
        layout.addWidget(state_label)
        layout.addLayout(
            value_grid(
                (
                    ("Precision", "off"),
                    ("Combat", "off"),
                    ("Trigger", "off"),
                    ("Zoom", "off"),
                    ("Extra", "off"),
                    ("Stack", self._modes.precision_combat_stack_mode.value),
                    *runtime_truth_rows(self._runtime_status),
                )
            )
        )
        return frame

    def _build_notes_card(self) -> QWidget:
        frame = card("modeNotesCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Mode Notes", "Quick reading for the current configuration."))
        note = QLabel(
            "Precision engages with button 0. Combat can open from no trigger buttons, while zoom uses button 5. "
            "Extra combat gating is driven by no extra buttons. When Precision and Combat overlap, their scaling currently multiply together."
        )
        note.setObjectName("routeSummaryValue")
        note.setWordWrap(True)
        layout.addStretch(1)
        layout.addWidget(note)
        return frame


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("cardBody")
    label.setWordWrap(True)
    return label
