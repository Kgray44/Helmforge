from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from v3_app.overlay.overlay_config import LiveOverlayConfig
from v3_app.overlay.trace_builder import OverlayTraceSet


class OverlayRenderer(QWidget):
    """Lightweight Qt renderer for the app-owned Live Overlay strip."""

    def __init__(self, *, config: LiveOverlayConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("liveOverlayRenderer")
        self.setMinimumSize(420, 120)
        self.config = config
        self._trace_set = OverlayTraceSet(source=config.source, history_seconds=config.history_seconds, series=())
        self._runtime_truth = "blocked_missing_device"
        self._output_verified = False
        self._full_live_runtime_ready = False
        self._source = config.source

    def set_config(self, config: LiveOverlayConfig) -> None:
        self.config = config
        self._source = self._trace_set.source or config.source
        self.update()

    def set_trace_set(self, trace_set: OverlayTraceSet) -> None:
        self._trace_set = trace_set
        self._source = trace_set.source or self.config.source
        self.update()

    def set_runtime_truth(
        self,
        *,
        runtime_truth: str,
        output_verified: bool,
        full_live_runtime_ready: bool,
        source: str | None = None,
    ) -> None:
        self._runtime_truth = runtime_truth
        self._output_verified = bool(output_verified)
        self._full_live_runtime_ready = bool(full_live_runtime_ready)
        if source:
            self._source = source
        self.update()

    def included_axes(self) -> tuple[str, ...]:
        return tuple(series.axis for series in self._trace_set.series)

    def axis_colors(self) -> dict[str, str]:
        return {series.axis: series.color for series in self._trace_set.series}

    def status_text(self) -> str:
        has_points = any(series.points for series in self._trace_set.series)
        prefix = (
            f"Rendering {len(self._trace_set.series)} overlay axes."
            if has_points
            else "Waiting for overlay telemetry samples."
        )
        return (
            f"{prefix} Runtime truth: {self._runtime_truth}. "
            f"Output verified: {str(self._output_verified).lower()}. "
            f"Full Live Runtime Ready: {str(self._full_live_runtime_ready).lower()}. "
            f"Source: {self._source}."
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._paint_background(painter)
        content = self.rect().adjusted(14, 12, -14, -12)
        self._paint_grid(painter, content)

        if not any(series.points for series in self._trace_set.series):
            self._paint_idle_text(painter, content)
            painter.end()
            return

        graph_rect = QRectF(content)
        if self.config.show_legend:
            graph_rect.adjust(0, 22, 0, 0)
        if self.config.show_live_values:
            graph_rect.adjust(0, 0, 0, -22)
        self._paint_traces(painter, graph_rect)
        if self.config.show_legend:
            self._paint_legend(painter, content)
        if self.config.show_live_values:
            self._paint_live_values(painter, content)
        painter.end()
        super().paintEvent(event)

    def _paint_background(self, painter: QPainter) -> None:
        alpha = int(max(0.0, min(1.0, self.config.background)) * 215)
        painter.fillRect(self.rect(), QColor(8, 12, 18, alpha))

    def _paint_grid(self, painter: QPainter, rect) -> None:
        grid_color = QColor(145, 166, 190, 38)
        painter.setPen(QPen(grid_color, 1))
        center_y = rect.top() + rect.height() / 2.0
        painter.drawLine(QPointF(rect.left(), center_y), QPointF(rect.right(), center_y))
        painter.drawRect(QRectF(rect))

    def _paint_idle_text(self, painter: QPainter, rect) -> None:
        painter.setPen(QColor("#B9C4D0"))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(QRectF(rect), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.status_text())

    def _paint_traces(self, painter: QPainter, rect: QRectF) -> None:
        if rect.width() <= 4 or rect.height() <= 4:
            return
        history = max(0.5, float(self._trace_set.history_seconds or self.config.history_seconds))
        half_height = rect.height() / 2.0
        center_y = rect.top() + half_height
        for series in self._trace_set.series:
            if len(series.points) < 2:
                continue
            color = QColor(series.color)
            color.setAlpha(225)
            painter.setPen(QPen(color, max(1.0, float(self.config.line_thickness))))
            points = [
                QPointF(
                    rect.left() + max(0.0, min(1.0, (timestamp + history) / history)) * rect.width(),
                    center_y - max(-1.0, min(1.0, value)) * (half_height - 6),
                )
                for timestamp, value in series.points
            ]
            for start, end in zip(points, points[1:]):
                painter.drawLine(start, end)

    def _paint_legend(self, painter: QPainter, rect) -> None:
        x = rect.left()
        painter.setFont(QFont())
        for series in self._trace_set.series:
            color = QColor(series.color)
            painter.setPen(QPen(color, 2))
            painter.drawLine(QPointF(x, rect.top() + 6), QPointF(x + 18, rect.top() + 6))
            painter.setPen(QColor("#D6DEE8"))
            painter.drawText(QPointF(x + 24, rect.top() + 10), series.axis)
            x += 92

    def _paint_live_values(self, painter: QPainter, rect) -> None:
        values: list[str] = []
        for series in self._trace_set.series:
            if series.points:
                values.append(f"{series.axis} {series.points[-1][1]:+.2f}")
        painter.setPen(QColor("#B9C4D0"))
        painter.drawText(QRectF(rect), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, "  ".join(values))
