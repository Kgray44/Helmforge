from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QWidget

from v3_app.liquid.glass import glass_panel
from v3_app.liquid.layout import horizontal_layout, vertical_layout
from v3_app.liquid.motion import apply_panel_motion_hint


def _label(text: str, object_name: str, *, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    return label


def _component_name(component_role: str) -> str:
    return f"liquid{component_role}"


def _set_component_properties(
    widget: QWidget,
    *,
    component_role: str,
    liquid_role: str,
    state_role: str | None = None,
) -> None:
    widget.setProperty("componentRole", component_role)
    widget.setProperty("liquidRole", liquid_role)
    widget.setProperty("liquidComponent", True)
    if state_role is not None:
        widget.setProperty("statusRole", state_role)


def _replace_slot(slot: QFrame, widget: QWidget, *, motion_role: str = "panel", order: int = 0) -> None:
    layout = slot.layout()
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        child = item.widget()
        if child is not None:
            child.setParent(None)
    apply_panel_motion_hint(widget, role=motion_role, order=order)
    layout.addWidget(widget)


class LiquidPage(QFrame):
    def __init__(
        self,
        *,
        title: str,
        subtitle: str = "",
        helper_text: str = "",
        object_name: str = "liquidPage",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        _set_component_properties(self, component_role="LiquidPage", liquid_role="liquid_page")

        self._status_slot = glass_panel("liquidPageStatusSlot", role="liquid_page_slot")
        self._header_slot = glass_panel("liquidPageHeaderSlot", role="liquid_page_slot")
        self._hero_slot = glass_panel("liquidPageHeroSlot", role="liquid_page_slot")
        self._inspector_slot = glass_panel("liquidPageInspectorSlot", role="liquid_page_slot")
        self._detail_slot = glass_panel("liquidPageDetailSlot", role="liquid_page_slot")
        self._advanced_slot = glass_panel("liquidPageAdvancedSlot", role="liquid_page_slot")
        for slot in (
            self._status_slot,
            self._header_slot,
            self._hero_slot,
            self._inspector_slot,
            self._detail_slot,
            self._advanced_slot,
        ):
            vertical_layout(slot, margins=(0, 0, 0, 0), spacing=0)

        root = vertical_layout(self, margins=(4, 2, 4, 2), spacing=14)
        lower_row = horizontal_layout(spacing=14)
        lower_row.addWidget(self._inspector_slot, 1)
        lower_row.addWidget(self._detail_slot, 1)

        root.addWidget(self._status_slot)
        root.addWidget(self._header_slot)
        root.addWidget(self._hero_slot, 3)
        root.addLayout(lower_row, 2)
        root.addWidget(self._advanced_slot)

        self.set_header(LiquidPageHeader(title, subtitle, helper_text))

    def set_header(self, widget: QWidget) -> None:
        _replace_slot(self._header_slot, widget, motion_role="header", order=0)

    def set_hero(self, widget: QWidget) -> None:
        _replace_slot(self._hero_slot, widget, motion_role="hero", order=1)

    def set_inspector(self, widget: QWidget) -> None:
        _replace_slot(self._inspector_slot, widget, motion_role="inspector", order=2)

    def set_detail(self, widget: QWidget) -> None:
        _replace_slot(self._detail_slot, widget, motion_role="detail", order=3)

    def set_advanced(self, widget: QWidget) -> None:
        _replace_slot(self._advanced_slot, widget, motion_role="advanced", order=4)

    def set_status_rail(self, widget: QWidget) -> None:
        _replace_slot(self._status_slot, widget, motion_role="status", order=0)


class LiquidPageHeader(QFrame):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        kicker: str = "LIQUID COMMAND DECK",
        *,
        object_name: str = "liquidPageHeader",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_component_properties(self, component_role="LiquidPageHeader", liquid_role="liquid_page_header")
        layout = horizontal_layout(self, margins=(14, 10, 14, 10), spacing=12)
        kicker_label = _label(kicker, "liquidComponentKicker")
        title_label = _label(title, "liquidComponentTitle")
        subtitle_label = _label(subtitle, "liquidComponentSubtitle", wrap=True)
        layout.addWidget(kicker_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label, 1)


class _TitledPanel(QFrame):
    def __init__(
        self,
        title: str,
        body: str = "",
        *,
        component_role: str,
        liquid_role: str,
        object_name: str | None = None,
        kicker: str = "STATIC COMPONENT",
        helper_text: str = "",
        state_role: str | None = None,
        minimum_height: int = 118,
    ) -> None:
        super().__init__()
        self.setObjectName(object_name or _component_name(component_role))
        self.setMinimumHeight(minimum_height)
        self.setProperty("embeddedOnCommandSurface", True)
        _set_component_properties(
            self,
            component_role=component_role,
            liquid_role=liquid_role,
            state_role=state_role,
        )
        layout = vertical_layout(self, margins=(18, 16, 18, 16), spacing=8)
        layout.addWidget(_label(kicker, "liquidComponentKicker"))
        layout.addWidget(_label(title, "liquidComponentTitle", wrap=True))
        if body:
            layout.addWidget(_label(body, "liquidComponentBody", wrap=True))
        if helper_text:
            layout.addWidget(_label(helper_text, "liquidComponentHelper", wrap=True))
        layout.addStretch(1)


class LiquidHeroPanel(_TitledPanel):
    def __init__(self, title: str, body: str = "", **kwargs) -> None:
        super().__init__(
            title,
            body,
            component_role="LiquidHeroPanel",
            liquid_role=kwargs.pop("liquid_role", "liquid_hero_panel"),
            kicker=kwargs.pop("kicker", "PRIMARY INSTRUMENT"),
            minimum_height=kwargs.pop("minimum_height", 220),
            **kwargs,
        )


class LiquidInstrumentPanel(_TitledPanel):
    def __init__(self, title: str, body: str = "", **kwargs) -> None:
        super().__init__(
            title,
            body,
            component_role="LiquidInstrumentPanel",
            liquid_role=kwargs.pop("liquid_role", "liquid_instrument_panel"),
            kicker=kwargs.pop("kicker", "INSTRUMENT"),
            **kwargs,
        )


class LiquidInspectorPanel(_TitledPanel):
    def __init__(self, title: str, body: str = "", **kwargs) -> None:
        super().__init__(
            title,
            body,
            component_role="LiquidInspectorPanel",
            liquid_role=kwargs.pop("liquid_role", "liquid_inspector_panel"),
            kicker=kwargs.pop("kicker", "INSPECTOR"),
            **kwargs,
        )


class LiquidDetailPanel(_TitledPanel):
    def __init__(self, title: str, body: str = "", **kwargs) -> None:
        super().__init__(
            title,
            body,
            component_role="LiquidDetailPanel",
            liquid_role=kwargs.pop("liquid_role", "liquid_detail_panel"),
            kicker=kwargs.pop("kicker", "DETAIL"),
            **kwargs,
        )


class LiquidAdvancedSection(_TitledPanel):
    def __init__(self, title: str, body: str = "", **kwargs) -> None:
        super().__init__(
            title,
            body,
            component_role="LiquidAdvancedSection",
            liquid_role=kwargs.pop("liquid_role", "liquid_advanced_section"),
            kicker=kwargs.pop("kicker", "ADVANCED"),
            **kwargs,
        )


class LiquidCommandSurfaceSection(_TitledPanel):
    def __init__(self, title: str, body: str = "", **kwargs) -> None:
        super().__init__(
            title,
            body,
            component_role="LiquidCommandSurfaceSection",
            liquid_role="liquid_command_surface_section",
            **kwargs,
        )


class LiquidFloatingPanel(_TitledPanel):
    def __init__(self, title: str, body: str = "", **kwargs) -> None:
        super().__init__(
            title,
            body,
            component_role="LiquidFloatingPanel",
            liquid_role="liquid_floating_panel",
            **kwargs,
        )
        self.setProperty("floatingLayer", True)


class LiquidSplitPanel(QFrame):
    def __init__(
        self,
        *,
        left: QWidget | None = None,
        right: QWidget | None = None,
        object_name: str = "liquidSplitPanel",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_component_properties(self, component_role="LiquidSplitPanel", liquid_role="liquid_split_panel")
        layout = horizontal_layout(self, margins=(0, 0, 0, 0), spacing=14)
        if left is not None:
            layout.addWidget(left, 1)
        if right is not None:
            layout.addWidget(right, 1)


class LiquidStatusRail(QFrame):
    def __init__(
        self,
        *,
        items: Iterable[tuple[str, str]] = (),
        object_name: str = "liquidStatusRail",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        _set_component_properties(self, component_role="LiquidStatusRail", liquid_role="liquid_status_rail")
        layout = horizontal_layout(self, margins=(14, 10, 14, 10), spacing=8)
        for label, state_role in items:
            capsule = LiquidGlassCapsule(label, state_role=state_role)
            layout.addWidget(capsule)
        layout.addStretch(1)


class LiquidGlassCapsule(QLabel):
    def __init__(
        self,
        text: str,
        *,
        state_role: str = "info",
        object_name: str = "liquidGlassCapsule",
    ) -> None:
        super().__init__(text)
        self.setObjectName(object_name)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setProperty("uiRole", "liquidGlassCapsule")
        self.setProperty("componentRole", "LiquidGlassCapsule")
        self.setProperty("statusRole", state_role)
        self.setProperty("toneRole", _tone_for_role(state_role))
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)


def _tone_for_role(state_role: str) -> str:
    normalized = state_role.strip().casefold()
    if normalized in {"ready", "verified", "saved", "safe", "done"}:
        return "success"
    if normalized in {"waiting", "blocked", "attention", "unsaved", "warning"}:
        return "warning"
    if normalized in {"error", "unsafe", "failed"}:
        return "danger"
    if normalized in {"disabled", "unavailable"}:
        return "disabled"
    return "info"
