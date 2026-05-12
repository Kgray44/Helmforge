from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QButtonGroup, QFrame, QLabel, QPushButton, QSizePolicy

from v3_app.liquid.glass import refresh_style
from v3_app.liquid.layout import horizontal_layout, vertical_layout
from v3_app.liquid.models.nav_model import (
    DEFAULT_LIQUID_NAVIGATION_MODEL,
    LiquidMode,
    LiquidNavigationModel,
)
from v3_app.liquid.theme_tokens import LiquidLayout


LiquidModeDefinition = LiquidMode
LIQUID_MODES = DEFAULT_LIQUID_NAVIGATION_MODEL.modes
LIQUID_MODE_IDS = DEFAULT_LIQUID_NAVIGATION_MODEL.mode_ids
REQUIRED_LIQUID_MODES = tuple(mode.display_name for mode in LIQUID_MODES)


class LiquidModeDock(QFrame):
    def __init__(
        self,
        *,
        active_mode_id: str,
        on_mode_selected: Callable[[str], None],
        model: LiquidNavigationModel = DEFAULT_LIQUID_NAVIGATION_MODEL,
    ) -> None:
        super().__init__()
        self.setObjectName("liquid_floating_mode_dock")
        self.setProperty("liquidRole", "liquid_floating_mode_dock")
        self.setProperty("floatingLayer", True)
        self.setFixedWidth(LiquidLayout.mode_dock_width)
        self.setMaximumWidth(LiquidLayout.mode_dock_width)
        self._model = model
        self._on_mode_selected = on_mode_selected
        self._buttons: dict[str, QPushButton] = {}
        self._active_mode_id = active_mode_id
        self._hover_label: QLabel | None = None
        self._active_label: QLabel | None = None

        layout = vertical_layout(
            self,
            margins=(10, 10, 10, 10),
            spacing=8,
        )
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        anchor = QFrame()
        anchor.setObjectName("liquid_radial_anchor_orb")
        anchor.setProperty("liquidRole", "liquid_radial_anchor_orb")
        anchor.setProperty("futureOnly", True)
        anchor.setToolTip("Future quick switch anchor; radial navigation is planned for a later phase.")
        anchor.setAccessibleName("Future radial quick switch anchor")
        anchor.setFixedSize(48, 48)
        anchor_layout = vertical_layout(anchor, margins=(0, 0, 0, 0), spacing=0)
        anchor_label = QLabel("HF")
        anchor_label.setObjectName("liquidOrbText")
        anchor_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        anchor_layout.addWidget(anchor_label)
        layout.addWidget(anchor, 0, Qt.AlignmentFlag.AlignHCenter)

        self._hover_label = QLabel()
        self._hover_label.setObjectName("liquidDockHoverLabel")
        self._hover_label.setProperty("liquidRole", "liquid_dock_hover_label")
        self._hover_label.setProperty("customHoverLabel", True)
        self._hover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hover_label.setWordWrap(True)
        self._hover_label.setMinimumWidth(68)
        self._hover_label.setText(mode_definition_by_id(active_mode_id).display_name)
        layout.addWidget(self._hover_label)

        for mode in self._model.modes:
            button = QPushButton(mode.glyph)
            button.setObjectName(f"liquidMode_{mode.mode_id}")
            button.setProperty("uiRole", "liquidModeDockButton")
            button.setProperty("modeId", mode.mode_id)
            button.setProperty("dockDensity", "floating_glyph")
            button.setProperty("hoverLabel", mode.display_name)
            button.setAccessibleName(mode.accessibility_text)
            button.setToolTip(mode.tooltip)
            button.setStatusTip(mode.short_description)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumWidth(56)
            button.setMaximumWidth(58)
            button.setMinimumHeight(LiquidLayout.mode_button_height)
            button.setMaximumHeight(LiquidLayout.mode_button_height)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            button.installEventFilter(self)
            button.clicked.connect(lambda checked=False, mode_id=mode.mode_id: self._on_mode_selected(mode_id))
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
            self._buttons[mode.mode_id] = button
        layout.addStretch(1)

        self._active_label = QLabel()
        self._active_label.setObjectName("liquidDockActiveLabel")
        self._active_label.setProperty("liquidRole", "liquid_dock_active_label")
        self._active_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._active_label.setWordWrap(True)
        self._active_label.setMinimumWidth(68)
        layout.addWidget(self._active_label)
        self.update_active(active_mode_id)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if isinstance(watched, QPushButton) and watched.property("uiRole") == "liquidModeDockButton":
            if event.type() == QEvent.Type.Enter:
                self._set_hover_label(str(watched.property("hoverLabel") or watched.accessibleName()))
            elif event.type() == QEvent.Type.Leave:
                self._set_hover_label(mode_definition_by_id(self._active_mode_id).display_name)
        return super().eventFilter(watched, event)

    def update_active(self, active_mode_id: str) -> None:
        self._active_mode_id = active_mode_id
        active_label = mode_definition_by_id(active_mode_id).display_name
        for mode_id, button in self._buttons.items():
            active = mode_id == active_mode_id
            button.setChecked(active)
            button.setProperty("active", active)
            refresh_style(button)
            if active and self._active_label is not None:
                self._active_label.setText(active_label)
        self._set_hover_label(active_label)

    def _set_hover_label(self, text: str) -> None:
        if self._hover_label is not None:
            self._hover_label.setText(text)


class LiquidSubpageSelector(QFrame):
    def __init__(
        self,
        *,
        model: LiquidNavigationModel,
        active_mode_id: str,
        active_subpage_id: str,
        on_subpage_selected: Callable[[str], None],
    ) -> None:
        super().__init__()
        self.setObjectName("liquid_subpage_selector")
        self.setProperty("liquidRole", "liquid_subpage_selector")
        self.setProperty("selectorStyle", "segmented_route_strip")
        self.setProperty("floatingLayer", True)
        self._model = model
        self._on_subpage_selected = on_subpage_selected
        self._buttons: dict[str, QPushButton] = {}
        self._active_mode_id = ""
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._layout = horizontal_layout(self, margins=(12, 8, 12, 8), spacing=8)
        self.update_for_route(active_mode_id, active_subpage_id)

    def update_for_route(self, active_mode_id: str, active_subpage_id: str) -> None:
        if self._active_mode_id == active_mode_id and self._buttons:
            self.update_active(active_subpage_id)
            return
        self._active_mode_id = active_mode_id
        self._clear()
        mode = self._model.mode_by_id(active_mode_id)
        single_route = len(mode.subpages) == 1
        self.setProperty("singleRouteMode", single_route)
        self.setMaximumHeight(36 if single_route else 46)
        if single_route:
            self._layout.setContentsMargins(8, 4, 8, 4)
        else:
            self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(6 if single_route else 8)
        label_text = (
            f"{mode.display_name} / {mode.subpages[0].display_name}"
            if single_route
            else f"{mode.display_name} routes"
        )
        label = QLabel(label_text)
        label.setObjectName("liquidSubpageSelectorModeLabel")
        label.setProperty("liquidRole", "liquid_subpage_selector_label")
        label.setAccessibleName(label_text)
        self._layout.addWidget(label)
        for subpage in mode.subpages:
            button = QPushButton(subpage.display_name)
            button.setObjectName(f"liquidSubpage_{subpage.route_key.replace('.', '_')}")
            button.setProperty("uiRole", "liquidSubpageSelectorButton")
            button.setProperty("selectorDensity", "single_route_chip" if single_route else "compact_segmented")
            button.setProperty("subpageId", subpage.subpage_id)
            button.setProperty("routeKey", subpage.route_key)
            button.setProperty("modeId", mode.mode_id)
            button.setAccessibleName(f"{mode.display_name} / {subpage.display_name}")
            button.setToolTip(subpage.tooltip)
            button.setStatusTip(subpage.purpose)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if single_route:
                button.setMaximumHeight(26)
            button.clicked.connect(lambda checked=False, subpage_id=subpage.subpage_id: self._on_subpage_selected(subpage_id))
            self._group.addButton(button)
            self._buttons[subpage.subpage_id] = button
            self._layout.addWidget(button)
        self._layout.addStretch(1)
        self.update_active(active_subpage_id)

    def update_active(self, active_subpage_id: str) -> None:
        for subpage_id, button in self._buttons.items():
            active = subpage_id == active_subpage_id
            button.setChecked(active)
            button.setProperty("active", active)
            refresh_style(button)

    def _clear(self) -> None:
        self._buttons.clear()
        for button in self._group.buttons():
            self._group.removeButton(button)
        while self._layout.count():
            item = self._layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.setParent(None)


def mode_definition_by_id(mode_id: str) -> LiquidModeDefinition:
    return DEFAULT_LIQUID_NAVIGATION_MODEL.mode_by_id(mode_id)
