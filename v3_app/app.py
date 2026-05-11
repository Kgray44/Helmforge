from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QMainWindow

from v3_app.services.app_state import AppState
from v3_app.services.embedded_bridge_runtime import EmbeddedBridgeRuntime
from v3_app.theme.qss import app_qss
from v3_app.theme.tokens import Layout
from v3_app.ui.shell import HelmForgeShell

UI_SHELL_ENV = "HELMFORGE_UI_SHELL"
LEGACY_UI_SHELL = "legacy"
LIQUID_UI_SHELL = "liquid"
VALID_UI_SHELLS = (LEGACY_UI_SHELL, LIQUID_UI_SHELL)


def _icon_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "HOTAS Control Panel Forensic Spec Set"
        / "Recovered PNG Evidence"
        / "00 App Icons and Assets"
        / "v2-app-icon_detailed-hotas-throttle-joystick-final-icon.png"
    )


class HelmForgeMainWindow(QMainWindow):
    def __init__(self, *, title: str, state: AppState | None = None, ui_shell: str | None = None) -> None:
        super().__init__()
        self.setObjectName("helmforgeMainWindow")
        self.setWindowTitle(title)
        self.ui_shell = resolve_ui_shell(ui_shell)
        requested_minimum_size, requested_default_size = window_sizes_for_shell(self.ui_shell)
        applied_minimum_size, applied_default_size = window_sizes_for_shell(
            self.ui_shell,
            available_size=_available_screen_size(),
        )
        self.setProperty("requestedMinimumSize", requested_minimum_size)
        self.setProperty("requestedDefaultSize", requested_default_size)
        self.setProperty("appliedMinimumSize", applied_minimum_size)
        self.setProperty("appliedDefaultSize", applied_default_size)
        self.setMinimumSize(applied_minimum_size)
        self.resize(applied_default_size)
        icon_file = _icon_path()
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))
        self.shell = _build_shell(self.ui_shell, state)
        self.embedded_bridge_runtime = None
        self._embedded_bridge_started = False
        if state is None:
            self.embedded_bridge_runtime = EmbeddedBridgeRuntime(on_telemetry=self.shell.apply_bridge_telemetry, parent=self)
        self.setCentralWidget(self.shell)
        self.setStyleSheet(app_qss())

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self.embedded_bridge_runtime is not None and not self._embedded_bridge_started:
            self.embedded_bridge_runtime.start()
            self._embedded_bridge_started = True

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.embedded_bridge_runtime is not None:
            self.embedded_bridge_runtime.stop()
        super().closeEvent(event)


def build_window(*, title: str, state: AppState | None = None, ui_shell: str | None = None) -> HelmForgeMainWindow:
    return HelmForgeMainWindow(title=title, state=state, ui_shell=ui_shell)


def resolve_ui_shell(ui_shell: str | None = None) -> str:
    requested = (ui_shell or os.environ.get(UI_SHELL_ENV) or LEGACY_UI_SHELL).strip().casefold()
    if requested not in VALID_UI_SHELLS:
        valid = ", ".join(VALID_UI_SHELLS)
        raise ValueError(f"Unknown HelmForge UI shell {requested!r}; expected one of: {valid}.")
    return requested


def window_sizes_for_shell(ui_shell: str, *, available_size: QSize | None = None) -> tuple[QSize, QSize]:
    if ui_shell == LIQUID_UI_SHELL:
        from v3_app.liquid.theme_tokens import LiquidLayout

        minimum = QSize(LiquidLayout.window_min_width, LiquidLayout.window_min_height)
        default = QSize(LiquidLayout.window_width, LiquidLayout.window_height)
        if available_size is None or available_size.width() <= 0 or available_size.height() <= 0:
            return minimum, default
        return _clamped_window_sizes(minimum=minimum, default=default, available_size=available_size)
    else:
        minimum = QSize(Layout.window_min_width, Layout.window_min_height)
        default = QSize(Layout.window_width, Layout.window_height)
        return minimum, default


def _available_screen_size() -> QSize | None:
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return None
    geometry = screen.availableGeometry()
    return QSize(geometry.width(), geometry.height())


def _clamped_window_sizes(*, minimum: QSize, default: QSize, available_size: QSize) -> tuple[QSize, QSize]:
    width_margin = 40 if available_size.width() > 900 else 0
    height_margin = 40 if available_size.height() > 820 else 0
    available_width = max(640, available_size.width() - width_margin)
    available_height = max(480, available_size.height() - height_margin)
    minimum_width = min(minimum.width(), available_width)
    minimum_height = min(minimum.height(), available_height)
    default_width = min(default.width(), max(minimum_width, available_width))
    default_height = min(default.height(), max(minimum_height, available_height))
    return QSize(minimum_width, minimum_height), QSize(default_width, default_height)


def _build_shell(ui_shell: str, state: AppState | None):
    if ui_shell == LIQUID_UI_SHELL:
        from v3_app.liquid.app_shell import LiquidCommandShell

        return LiquidCommandShell(state)
    return HelmForgeShell(state)
