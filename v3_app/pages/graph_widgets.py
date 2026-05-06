from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

import pyqtgraph as pg


class GraphPreview(QWidget):
    def __init__(self, *, object_name: str) -> None:
        super().__init__()
        self.setObjectName(object_name)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plot = pg.PlotWidget()
        self.plot.setBackground("#07111d")
        self.plot.showGrid(x=True, y=True, alpha=0.18)
        self.plot.getAxis("bottom").setPen("#28496a")
        self.plot.getAxis("left").setPen("#28496a")
        self.plot.getAxis("bottom").setTextPen("#a8c3dc")
        self.plot.getAxis("left").setTextPen("#a8c3dc")
        self.plot.setMinimumHeight(330)
        layout.addWidget(self.plot)

    def plot_series(self, series: tuple[tuple[str, tuple[tuple[float, float], ...], str], ...]) -> None:
        self.plot.clear()
        for name, points, color in series:
            x_values = [point[0] for point in points]
            y_values = [point[1] for point in points]
            pen = pg.mkPen(color=color, width=2)
            self.plot.plot(x_values, y_values, pen=pen, name=name)

    def plot_series_with_marker(
        self,
        series: tuple[tuple[str, tuple[tuple[float, float], ...], str], ...],
        *,
        marker: tuple[float, float] | None = None,
    ) -> None:
        self.plot_series(series)
        if marker is None:
            return
        self.plot.plot(
            [marker[0]],
            [marker[1]],
            pen=None,
            symbol="o",
            symbolBrush="#b9ecff",
            symbolPen="#ffffff",
            symbolSize=11,
        )
