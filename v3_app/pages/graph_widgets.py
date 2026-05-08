from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

import pyqtgraph as pg


class GraphPreview(QWidget):
    def __init__(self, *, object_name: str) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self._series_items: dict[str, pg.PlotDataItem] = {}
        self._marker_item: pg.PlotDataItem | None = None
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
        self.plot.setMouseEnabled(x=False, y=False)
        layout.addWidget(self.plot)

    def plot_series(self, series: tuple[tuple[str, tuple[tuple[float, float], ...], str], ...]) -> None:
        active_names: set[str] = set()
        for name, points, color in series:
            active_names.add(name)
            x_values = [point[0] for point in points]
            y_values = [point[1] for point in points]
            pen = pg.mkPen(color=color, width=2)
            item = self._series_items.get(name)
            if item is None:
                self._series_items[name] = self.plot.plot(x_values, y_values, pen=pen, name=name)
            else:
                item.setPen(pen)
                item.setData(x_values, y_values)
        for stale_name in tuple(set(self._series_items) - active_names):
            self.plot.removeItem(self._series_items.pop(stale_name))

    def plot_series_with_marker(
        self,
        series: tuple[tuple[str, tuple[tuple[float, float], ...], str], ...],
        *,
        marker: tuple[float, float] | None = None,
    ) -> None:
        self.plot_series(series)
        if marker is None:
            if self._marker_item is not None:
                self._marker_item.setData([], [])
            return
        if self._marker_item is None:
            self._marker_item = self.plot.plot(
                [],
                [],
                pen=None,
                symbol="o",
                symbolBrush="#b9ecff",
                symbolPen="#ffffff",
                symbolSize=11,
            )
        self._marker_item.setData([marker[0]], [marker[1]])
