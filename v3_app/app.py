from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow

from v3_app.services.app_state import AppState
from v3_app.theme.qss import app_qss
from v3_app.theme.tokens import Layout
from v3_app.ui.shell import HelmForgeShell


def _icon_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "HOTAS Control Panel Forensic Spec Set"
        / "Recovered PNG Evidence"
        / "00 App Icons and Assets"
        / "v2-app-icon_detailed-hotas-throttle-joystick-final-icon.png"
    )


class HelmForgeMainWindow(QMainWindow):
    def __init__(self, *, title: str, state: AppState | None = None) -> None:
        super().__init__()
        self.setObjectName("helmforgeMainWindow")
        self.setWindowTitle(title)
        self.setMinimumSize(Layout.window_min_width, Layout.window_min_height)
        self.resize(Layout.window_width, Layout.window_height)
        icon_file = _icon_path()
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))
        self.shell = HelmForgeShell(state)
        self.setCentralWidget(self.shell)
        self.setStyleSheet(app_qss())


def build_window(*, title: str, state: AppState | None = None) -> HelmForgeMainWindow:
    return HelmForgeMainWindow(title=title, state=state)
