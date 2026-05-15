from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QVBoxLayout, QWidget

from v3_app.overlay.overlay_config import LiveOverlayConfig
from v3_app.overlay.overlay_renderer import OverlayRenderer
from v3_app.overlay.trace_builder import OverlayTraceSet


class LiveOverlayWindow(QWidget):
    """Detached app-owned window for the Live Overlay telemetry strip."""

    visibility_changed = Signal(bool)

    def __init__(
        self,
        *,
        config: LiveOverlayConfig,
        runtime_truth: str,
        output_verified: bool,
        full_live_runtime_ready: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(None)
        self.setObjectName("liveOverlayWindow")
        self._reference_widget = parent
        self.config = config
        self._always_on_top_status = "Enabled" if config.always_on_top else "Disabled"
        self._apply_window_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("HelmForge Live Overlay")
        self.setWindowOpacity(max(0.0, min(1.0, config.opacity)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.renderer = OverlayRenderer(config=config, parent=self)
        self.renderer.set_runtime_truth(
            runtime_truth=runtime_truth,
            output_verified=output_verified,
            full_live_runtime_ready=full_live_runtime_ready,
            source=config.source,
        )
        layout.addWidget(self.renderer)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setObjectName("liveOverlayRefreshTimer")
        self.refresh_timer.setInterval(_timer_interval(config.fps_cap))
        self.refresh_timer.timeout.connect(self._refresh_if_visible)
        self.overlay_timer_tick_count = 0
        self.overlay_update_count = 0
        self.overlay_skipped_update_count = 0

    def show_overlay(self) -> None:
        self.apply_bottom_strip_placement()
        self.show()
        if not self.refresh_timer.isActive():
            self.refresh_timer.start()
        self.visibility_changed.emit(True)

    def hide_overlay(self) -> None:
        self.refresh_timer.stop()
        self.hide()
        self.visibility_changed.emit(False)

    def is_overlay_active(self) -> bool:
        return self.isVisible()

    def apply_config(self, config: LiveOverlayConfig) -> None:
        was_visible = self.isVisible()
        self.config = config
        self.setWindowOpacity(max(0.0, min(1.0, config.opacity)))
        self._apply_window_flags()
        self.renderer.set_config(config)
        self.refresh_timer.setInterval(_timer_interval(config.fps_cap))
        if was_visible:
            self.apply_bottom_strip_placement()
            self.show()

    def set_trace_set(self, trace_set: OverlayTraceSet) -> None:
        self.renderer.set_trace_set(trace_set)

    def set_runtime_truth(self, *, runtime_truth: str, output_verified: bool, full_live_runtime_ready: bool) -> None:
        self.renderer.set_runtime_truth(
            runtime_truth=runtime_truth,
            output_verified=output_verified,
            full_live_runtime_ready=full_live_runtime_ready,
            source=self.config.source,
        )

    def hotkey_status_text(self) -> str:
        return "Registered" if self.config.hotkey_registered else "Not registered"

    def click_through_status_text(self) -> str:
        if self.config.click_through and self.config.click_through_supported == "true":
            return "Enabled"
        return "Not enabled - not verified"

    def always_on_top_status_text(self) -> str:
        return self._always_on_top_status

    def apply_bottom_strip_placement(self) -> None:
        screen = None
        if self._reference_widget is not None:
            handle = self._reference_widget.windowHandle()
            if handle is not None:
                screen = handle.screen()
        screen = screen or self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(900, 160)
            return
        geometry = screen.availableGeometry()
        margin = max(0, int(self.config.margin_px))
        width = int(geometry.width() * 0.72)
        height = max(120, min(260, int(geometry.height() * 0.18 * max(0.2, min(1.0, self.config.height)))))
        x = geometry.x() + (geometry.width() - width) // 2
        y = geometry.y() + geometry.height() - height - margin
        self.setGeometry(x, y, width, height)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.refresh_timer.stop()
        super().closeEvent(event)
        QTimer.singleShot(0, lambda: self.visibility_changed.emit(False))

    def _apply_window_flags(self) -> None:
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        if self.config.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            self._always_on_top_status = "Enabled"
        else:
            self._always_on_top_status = "Disabled"
        self.setWindowFlags(flags)

    def _refresh_if_visible(self) -> None:
        if not self.isVisible():
            self.refresh_timer.stop()
            return
        self.overlay_timer_tick_count += 1
        if self.renderer.consume_dirty_for_paint():
            self.overlay_update_count += 1
            self.renderer.request_overlay_update()
        else:
            self.overlay_skipped_update_count += 1


def _timer_interval(fps_cap: int) -> int:
    fps = max(1, int(fps_cap))
    return max(1, int(1000 / fps))
