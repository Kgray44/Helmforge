from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from v3_app.pages.placeholders import PageDefinition
from v3_app.services.app_state import AppState
from v3_app.theme.tokens import Layout


SIDEBAR_GROUPS = (
    ("SETUP", "Runtime readiness, routing, profiles, and live mode control.", ("preflight", "mapping", "profiles", "modes")),
    ("TUNING", "Base shaping, filtering, combat, and rule logic.", ("base_tuning", "filtering", "combat_profile", "conditional_rules")),
    ("ANALYSIS", "Effective stack view, live telemetry, and capture.", ("effective_response_stack", "live_monitor", "flight_recorder")),
    ("SUPPORT", "Built-in reference and diagnostics.", ("help_docs", "perf_diagnostics")),
)


def _icon_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "HOTAS Control Panel Forensic Spec Set"
        / "Recovered PNG Evidence"
        / "00 App Icons and Assets"
        / "v2-app-icon_detailed-hotas-throttle-joystick-final-icon.png"
    )


class Sidebar(QWidget):
    def __init__(
        self,
        pages: tuple[PageDefinition, ...],
        state: AppState,
        on_page_selected: Callable[[str], None],
    ) -> None:
        super().__init__()
        self.setObjectName("appSidebar")
        self.setFixedWidth(Layout.sidebar_width)
        self._state = state
        self._on_page_selected = on_page_selected
        self._pages = {page.page_id: page for page in pages}
        self.nav_buttons: dict[str, QPushButton] = {}
        self.nav_accents: dict[str, QLabel] = {}
        self._runtime_state_label: QLabel | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        layout.addWidget(self._build_brand())
        for group_title, hint, page_ids in SIDEBAR_GROUPS:
            layout.addSpacing(3)
            section = QLabel(group_title)
            section.setObjectName("sectionLabel")
            section.setToolTip(hint)
            layout.addWidget(section)
            for page_id in page_ids:
                layout.addWidget(self._build_nav_row(page_id))

        layout.addStretch(1)
        layout.addWidget(self._build_runtime_card())
        self.update_active(state.active_page_id)

    def _build_brand(self) -> QWidget:
        brand = QWidget()
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 2)
        brand_layout.setSpacing(4)

        icon = QLabel()
        icon_file = _icon_path()
        if icon_file.exists():
            pixmap = QPixmap(str(icon_file))
            icon.setPixmap(pixmap.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            brand_layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignLeft)

        title = QLabel("HelmForge")
        title.setObjectName("brandTitle")
        subtitle = QLabel("HOTAS Control Panel V3")
        subtitle.setObjectName("brandSubtitle")
        workspace = QLabel("Control workspace")
        workspace.setObjectName("brandSubtitle")
        brand_layout.addWidget(title)
        brand_layout.addWidget(subtitle)
        workspace.setVisible(False)
        return brand

    def _build_nav_row(self, page_id: str) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        accent = QLabel()
        accent.setObjectName("activeAccent")
        accent.setFixedWidth(4)
        accent.setMinimumHeight(28)
        accent.setVisible(False)

        button = QPushButton(self._pages[page_id].title)
        button.setObjectName(f"nav_{page_id}")
        button.setProperty("navItem", True)
        button.setProperty("active", False)
        button.setMinimumHeight(28)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.clicked.connect(lambda checked=False, pid=page_id: self._on_page_selected(pid))

        row_layout.addWidget(accent)
        row_layout.addWidget(button, 1)
        self.nav_buttons[page_id] = button
        self.nav_accents[page_id] = accent
        return row

    def _build_runtime_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("runtimeCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)
        label = QLabel("Runtime")
        label.setObjectName("sectionHint")
        state = QLabel(self._state.runtime.runtime_card_label)
        state.setObjectName("runtimeState")
        state.setProperty("chipTone", self._state.runtime.tone)
        self._runtime_state_label = state
        layout.addWidget(label)
        layout.addWidget(state)
        return card

    def update_active(self, page_id: str) -> None:
        for nav_id, button in self.nav_buttons.items():
            active = nav_id == page_id
            button.setProperty("active", active)
            self.nav_accents[nav_id].setVisible(active)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def update_runtime(self, state: AppState) -> None:
        self._state = state
        if self._runtime_state_label is not None:
            self._runtime_state_label.setText(state.runtime.runtime_card_label)
            self._runtime_state_label.setProperty("chipTone", state.runtime.tone)
            self._runtime_state_label.style().unpolish(self._runtime_state_label)
            self._runtime_state_label.style().polish(self._runtime_state_label)
            self._runtime_state_label.update()
