from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QMainWindow

from v3_app.services.app_state import AppState
from v3_app.services.embedded_bridge_runtime import EmbeddedBridgeRuntime
from v3_app.theme.cockpit_qss import cockpit_qss
from v3_app.theme.qss import app_qss
from v3_app.theme.tokens import Layout
from v3_app.ui.cockpit.shell import CockpitShell
from v3_app.ui.shell import HelmForgeShell

UI_SHELL_ENV = "HELMFORGE_UI_SHELL"
RESET_WINDOW_GEOMETRY_ENV = "HELMFORGE_RESET_WINDOW_GEOMETRY"
LEGACY_UI_SHELL = "legacy"
LIQUID_UI_SHELL = "liquid"
VALID_UI_SHELLS = (LEGACY_UI_SHELL, LIQUID_UI_SHELL)

UI_MODE_ENV_VAR = "HELMFORGE_UI_MODE"
LEGACY_UI_MODE = "legacy"
COCKPIT_UI_MODE = "cockpit"
SUPPORTED_UI_MODES = {LEGACY_UI_MODE, COCKPIT_UI_MODE}


def _icon_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "HOTAS Control Panel Forensic Spec Set"
        / "Recovered PNG Evidence"
        / "00 App Icons and Assets"
        / "v2-app-icon_detailed-hotas-throttle-joystick-final-icon.png"
    )


class HelmForgeMainWindow(QMainWindow):
    def __init__(
        self,
        *,
        title: str,
        state: AppState | None = None,
        ui_shell: str | None = None,
        ui_mode: str | None = None,
        reset_window_geometry: bool | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("helmforgeMainWindow")
        self.setWindowTitle(title)
        self.ui_shell = resolve_ui_shell(ui_shell)
        self.reset_window_geometry = resolve_reset_window_geometry(reset_window_geometry)
        self.ui_mode = resolve_ui_mode({UI_MODE_ENV_VAR: ui_mode} if ui_mode is not None else None)
        if self.ui_shell == LIQUID_UI_SHELL:
            self.ui_mode = LEGACY_UI_MODE
        self.setProperty("uiShell", self.ui_shell)
        self.setProperty("uiMode", self.ui_mode)
        self.setProperty("resetWindowGeometry", self.reset_window_geometry)
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
        available_geometry = _available_screen_geometry()
        if self.ui_shell == LIQUID_UI_SHELL:
            target_geometry = safe_initial_window_geometry(
                available_geometry,
                applied_default_size,
                preferred_top_left=None,
            )
            self.setGeometry(target_geometry)
        else:
            self.resize(applied_default_size)
            self.move(safe_window_top_left(available_geometry, applied_default_size))
        self.setProperty("safeWindowGeometryApplied", True)
        icon_file = _icon_path()
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))
        self.shell = _build_shell(self.ui_shell, self.ui_mode, state)
        self.embedded_bridge_runtime = None
        self._embedded_bridge_started = False
        if state is None:
            self.embedded_bridge_runtime = EmbeddedBridgeRuntime(on_telemetry=self.shell.apply_bridge_telemetry, parent=self)
        self.setCentralWidget(self.shell)
        self.setStyleSheet(app_qss() + (cockpit_qss() if self.ui_mode == COCKPIT_UI_MODE else ""))

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self.embedded_bridge_runtime is not None and not self._embedded_bridge_started:
            self.embedded_bridge_runtime.start()
            self._embedded_bridge_started = True

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.embedded_bridge_runtime is not None:
            self.embedded_bridge_runtime.stop()
        super().closeEvent(event)


def build_window(
    *,
    title: str,
    state: AppState | None = None,
    ui_shell: str | None = None,
    ui_mode: str | None = None,
    reset_window_geometry: bool | None = None,
) -> HelmForgeMainWindow:
    return HelmForgeMainWindow(
        title=title,
        state=state,
        ui_shell=ui_shell,
        ui_mode=ui_mode,
        reset_window_geometry=reset_window_geometry,
    )


def resolve_ui_shell(ui_shell: str | None = None) -> str:
    requested = (ui_shell or os.environ.get(UI_SHELL_ENV) or LEGACY_UI_SHELL).strip().casefold()
    if requested not in VALID_UI_SHELLS:
        valid = ", ".join(VALID_UI_SHELLS)
        raise ValueError(f"Unknown HelmForge UI shell {requested!r}; expected one of: {valid}.")
    return requested


def resolve_ui_mode(env: Mapping[str, str | None] | None = None) -> str:
    source = os.environ if env is None else env
    requested = str(source.get(UI_MODE_ENV_VAR) or LEGACY_UI_MODE).strip().casefold()
    return requested if requested in SUPPORTED_UI_MODES else LEGACY_UI_MODE


def resolve_reset_window_geometry(reset_window_geometry: bool | None = None) -> bool:
    if reset_window_geometry is not None:
        return bool(reset_window_geometry)
    requested = os.environ.get(RESET_WINDOW_GEOMETRY_ENV, "").strip().casefold()
    return requested in {"1", "true", "yes", "on", "reset"}


def window_sizes_for_shell(ui_shell: str, *, available_size: QSize | None = None) -> tuple[QSize, QSize]:
    if ui_shell == LIQUID_UI_SHELL:
        from v3_app.liquid.theme_tokens import LiquidLayout

        minimum = QSize(LiquidLayout.window_min_width, LiquidLayout.window_min_height)
        default = QSize(LiquidLayout.window_width, LiquidLayout.window_height)
        if available_size is None or available_size.width() <= 0 or available_size.height() <= 0:
            return minimum, default
        return _clamped_window_sizes(minimum=minimum, default=default, available_size=available_size)
    minimum = QSize(Layout.window_min_width, Layout.window_min_height)
    default = QSize(Layout.window_width, Layout.window_height)
    return minimum, default


def _available_screen_size() -> QSize | None:
    geometry = _available_screen_geometry()
    if geometry is None:
        return None
    return QSize(geometry.width(), geometry.height())


def _available_screen_geometry() -> QRect | None:
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return None
    return screen.availableGeometry()


def safe_initial_window_geometry(
    available_geometry: QRect | None,
    desired_size: QSize,
    *,
    preferred_top_left: QPoint | None = None,
    margin: int = 12,
) -> QRect:
    if available_geometry is None or available_geometry.width() <= 0 or available_geometry.height() <= 0:
        return QRect(QPoint(0, 0), desired_size)

    width = min(desired_size.width(), available_geometry.width())
    height = min(desired_size.height(), available_geometry.height())
    width = max(320, width) if available_geometry.width() >= 320 else available_geometry.width()
    height = max(240, height) if available_geometry.height() >= 240 else available_geometry.height()

    preferred_area = available_geometry.adjusted(margin, margin, -margin, -margin)
    if preferred_area.width() <= 0 or preferred_area.height() <= 0:
        preferred_area = QRect(available_geometry)
    horizontal_area = preferred_area if width <= preferred_area.width() else available_geometry
    vertical_area = preferred_area if height <= preferred_area.height() else available_geometry

    if preferred_top_left is None:
        x = horizontal_area.left() + max(0, (horizontal_area.width() - width) // 2)
        y = vertical_area.top() + max(0, (vertical_area.height() - height) // 2)
    else:
        x = preferred_top_left.x()
        y = preferred_top_left.y()

    max_x = horizontal_area.right() - width + 1
    max_y = vertical_area.bottom() - height + 1
    x = min(max(x, horizontal_area.left()), max_x)
    y = min(max(y, vertical_area.top()), max_y)
    return QRect(x, y, width, height)


def safe_window_top_left(
    available_geometry: QRect | None,
    window_size: QSize,
    *,
    preferred_top_left: QPoint | None = None,
    margin: int = 12,
) -> QPoint:
    if available_geometry is None or available_geometry.width() <= 0 or available_geometry.height() <= 0:
        return QPoint(0, 0)
    preferred_area = available_geometry.adjusted(margin, margin, -margin, -margin)
    if preferred_area.width() <= 0 or preferred_area.height() <= 0:
        preferred_area = QRect(available_geometry)
    horizontal_area = preferred_area if window_size.width() <= preferred_area.width() else available_geometry
    vertical_area = preferred_area if window_size.height() <= preferred_area.height() else available_geometry

    if preferred_top_left is None:
        x = horizontal_area.left() + max(0, (horizontal_area.width() - window_size.width()) // 2)
        y = vertical_area.top() + max(0, (vertical_area.height() - window_size.height()) // 2)
    else:
        x = preferred_top_left.x()
        y = preferred_top_left.y()

    x = _clamp_axis(x, horizontal_area.left(), horizontal_area.right() - window_size.width() + 1)
    y = _clamp_axis(y, vertical_area.top(), vertical_area.bottom() - window_size.height() + 1)
    return QPoint(x, y)


def _clamp_axis(value: int, minimum: int, maximum: int) -> int:
    if maximum < minimum:
        return minimum
    return min(max(value, minimum), maximum)


def clamp_window_to_available_screen(
    window: QMainWindow,
    *,
    preferred_top_left: QPoint | None = None,
) -> QRect:
    geometry = safe_initial_window_geometry(
        _available_screen_geometry(),
        window.size(),
        preferred_top_left=preferred_top_left,
    )
    window.setGeometry(geometry)
    window.setProperty("safeWindowGeometryApplied", True)
    return geometry


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


def _build_shell(ui_shell: str, ui_mode: str, state: AppState | None):
    if ui_shell == LIQUID_UI_SHELL:
        from v3_app.liquid.app_shell import LiquidCommandShell

        return LiquidCommandShell(state)
    if ui_mode == COCKPIT_UI_MODE:
        return CockpitShell(state)
    return HelmForgeShell(state)
