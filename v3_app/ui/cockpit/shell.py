from __future__ import annotations

from PySide6.QtWidgets import QLabel, QScrollArea

from shared_core.models.runtime import RuntimeTruth
from v3_app.pages.placeholders import PageDefinition
from v3_app.ui.cockpit.pages import build_cockpit_page
from v3_app.ui.shell import HelmForgeShell
from v3_app.services.ui_dirty import repolish_if_changed, set_label_text_if_changed


class CockpitShell(HelmForgeShell):
    """Static Cockpit presentation layer that preserves the Legacy page classes."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setProperty("uiMode", "cockpit")
        self.sidebar.setProperty("uiMode", "cockpit")
        self.header.setProperty("uiMode", "cockpit")
        self.footer.setProperty("uiMode", "cockpit")
        self.content_viewport.setProperty("uiMode", "cockpit")
        self.stack.setProperty("uiMode", "cockpit")
        for scroll in self.page_widgets.values():
            self._mark_scroll(scroll)
        self._polish_cockpit_runtime_copy()

    def _create_page_content(self, page_id: str, page: PageDefinition):
        legacy_page = super()._create_page_content(page_id, page)
        return build_cockpit_page(
            page_id=page_id,
            page=page,
            legacy_page=legacy_page,
            state=self.state,
            runtime_status=self.runtime_status,
            workspace=self.workspace,
        )

    def _build_pages(self) -> None:
        super()._build_pages()
        for scroll in self.page_widgets.values():
            self._mark_scroll(scroll)

    def apply_bridge_telemetry(self, telemetry) -> None:
        super().apply_bridge_telemetry(telemetry)
        self._polish_cockpit_runtime_copy()

    def mark_workspace_dirty(self, message: str) -> None:
        super().mark_workspace_dirty(message)
        self._polish_cockpit_runtime_copy()

    def apply_workspace(self) -> None:
        super().apply_workspace()
        self._polish_cockpit_runtime_copy()

    def save_workspace(self) -> None:
        super().save_workspace()
        self._polish_cockpit_runtime_copy()

    def revert_workspace(self) -> None:
        super().revert_workspace()
        self._polish_cockpit_runtime_copy()

    def _polish_cockpit_runtime_copy(self) -> None:
        label = _cockpit_runtime_label(self.runtime_status)
        for object_name in ("runtimeTruthChip", "runtimeState"):
            widget = self.findChild(QLabel, object_name)
            if widget is not None:
                changed = set_label_text_if_changed(widget, label)
                repolish_if_changed(widget, changed)
                if changed:
                    widget.update()

    @staticmethod
    def _mark_scroll(scroll: QScrollArea) -> None:
        scroll.setProperty("uiMode", "cockpit")
        scroll.viewport().setProperty("uiMode", "cockpit")


def _cockpit_runtime_label(runtime_status) -> str:
    if runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and runtime_status.live_output_writes_verified:
        return "Live Checks Passed"
    if runtime_status.truth is RuntimeTruth.DETECTED_UNVERIFIED:
        return "Output Unverified"
    if runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DEVICE:
        return "HOTAS Not Connected"
    if runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DRIVER:
        return "Driver or vJoy Missing"
    if runtime_status.truth is RuntimeTruth.ERROR:
        return "Runtime Error"
    return "Simulation Mode"
