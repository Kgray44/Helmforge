from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow

from v3_app.services.app_state import AppState
from v3_app.services.embedded_bridge_runtime import EmbeddedBridgeRuntime
from v3_app.theme.cockpit_qss import cockpit_qss
from v3_app.theme.qss import app_qss
from v3_app.theme.tokens import Layout
from v3_app.ui.cockpit.shell import CockpitShell
from v3_app.ui.shell import HelmForgeShell


UI_MODE_ENV_VAR = "HELMFORGE_UI_MODE"
SUPPORTED_UI_MODES = {"legacy", "cockpit"}


def _icon_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "HOTAS Control Panel Forensic Spec Set"
        / "Recovered PNG Evidence"
        / "00 App Icons and Assets"
        / "v2-app-icon_detailed-hotas-throttle-joystick-final-icon.png"
    )


class HelmForgeMainWindow(QMainWindow):
    def __init__(self, *, title: str, state: AppState | None = None, ui_mode: str | None = None) -> None:
        super().__init__()
        self.setObjectName("helmforgeMainWindow")
        self.ui_mode = resolve_ui_mode({UI_MODE_ENV_VAR: ui_mode} if ui_mode is not None else None)
        self.setProperty("uiMode", self.ui_mode)
        self.setWindowTitle(title)
        self.setMinimumSize(Layout.window_min_width, Layout.window_min_height)
        self.resize(Layout.window_width, Layout.window_height)
        icon_file = _icon_path()
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))
        self.shell = CockpitShell(state) if self.ui_mode == "cockpit" else HelmForgeShell(state)
        self.embedded_bridge_runtime = None
        self._embedded_bridge_started = False
        if state is None:
            self.embedded_bridge_runtime = EmbeddedBridgeRuntime(on_telemetry=self.shell.apply_bridge_telemetry, parent=self)
        self.setCentralWidget(self.shell)
        self.setStyleSheet(app_qss() + (cockpit_qss() if self.ui_mode == "cockpit" else ""))

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self.embedded_bridge_runtime is not None and not self._embedded_bridge_started:
            self.embedded_bridge_runtime.start()
            self._embedded_bridge_started = True

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.embedded_bridge_runtime is not None:
            self.embedded_bridge_runtime.stop()
        super().closeEvent(event)


def resolve_ui_mode(env: Mapping[str, str | None] | None = None) -> str:
    source = os.environ if env is None else env
    requested = str(source.get(UI_MODE_ENV_VAR) or "cockpit").strip().casefold()
    return requested if requested in SUPPORTED_UI_MODES else "legacy"


def build_window(*, title: str, state: AppState | None = None, ui_mode: str | None = None) -> HelmForgeMainWindow:
    return HelmForgeMainWindow(title=title, state=state, ui_mode=ui_mode)
