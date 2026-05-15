from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

import pyqtgraph as pg


class GraphPreview(QWidget):
    def __init__(self, *, object_name: str) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self._series_items: dict[str, pg.PlotDataItem] = {}
        self._series_cache: dict[str, tuple[tuple[tuple[float, float], ...], str]] = {}
        self._series_pen_key: dict[str, tuple[str, int, object | None]] = {}
        self._pen_cache: dict[tuple[str, int, object | None], object] = {}
        self._marker_item: pg.PlotDataItem | None = None
        self._marker_cache: tuple[float, float] | None = None
        self._named_marker_items: dict[str, pg.PlotDataItem] = {}
        self._named_marker_cache: dict[str, tuple[float, float]] = {}
        self._named_marker_color_cache: dict[str, str] = {}
        self.series_update_count = 0
        self.marker_update_count = 0
        self.item_create_count = 0
        self.stale_remove_count = 0
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

    @property
    def live_marker_items(self) -> dict[str, pg.PlotDataItem]:
        return self._named_marker_items

    def plot_series(self, series: tuple[tuple[str, tuple[tuple[float, float], ...], str], ...]) -> None:
        active_names: set[str] = set()
        for name, points, color in series:
            active_names.add(name)
            normalized_points = tuple((float(point[0]), float(point[1])) for point in points)
            pen_key = (str(color), 2, None)
            pen = self._pen_for(color=str(color), width=2)
            item = self._series_items.get(name)
            if item is None:
                x_values = [point[0] for point in normalized_points]
                y_values = [point[1] for point in normalized_points]
                self._series_items[name] = self.plot.plot(x_values, y_values, pen=pen, name=name)
                self._series_cache[name] = (normalized_points, str(color))
                self._series_pen_key[name] = pen_key
                self.item_create_count += 1
                self.series_update_count += 1
            else:
                cached = self._series_cache.get(name)
                if self._series_pen_key.get(name) != pen_key:
                    item.setPen(pen)
                    self._series_pen_key[name] = pen_key
                if cached != (normalized_points, str(color)):
                    x_values = [point[0] for point in normalized_points]
                    y_values = [point[1] for point in normalized_points]
                    item.setData(x_values, y_values)
                    self._series_cache[name] = (normalized_points, str(color))
                    self.series_update_count += 1
        for stale_name in tuple(set(self._series_items) - active_names):
            self.plot.removeItem(self._series_items.pop(stale_name))
            self._series_cache.pop(stale_name, None)
            self._series_pen_key.pop(stale_name, None)
            self.stale_remove_count += 1

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
                self._marker_cache = None
            return
        self.update_marker(marker)

    def update_marker(self, marker: tuple[float, float] | None) -> None:
        if marker is None:
            if self._marker_item is not None and self._marker_cache is not None:
                self._marker_item.setData([], [])
                self._marker_cache = None
                self.marker_update_count += 1
            return
        normalized = (float(marker[0]), float(marker[1]))
        if self._marker_cache == normalized:
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
            self.item_create_count += 1
        self._marker_item.setData([normalized[0]], [normalized[1]])
        self._marker_cache = normalized
        self.marker_update_count += 1

    def plot_series_with_markers(
        self,
        series: tuple[tuple[str, tuple[tuple[float, float], ...], str], ...],
        *,
        markers: dict[str, tuple[float, float]],
        marker_colors: dict[str, str] | None = None,
    ) -> None:
        self.plot_series(series)
        self.update_markers(markers, marker_colors=marker_colors)

    def update_markers(
        self,
        markers: dict[str, tuple[float, float]],
        *,
        marker_colors: dict[str, str] | None = None,
    ) -> None:
        marker_colors = marker_colors or {}
        for name, marker in markers.items():
            normalized = (float(marker[0]), float(marker[1]))
            color = marker_colors.get(name, "#b9ecff")
            item = self._named_marker_items.get(name)
            if item is None:
                item = self.plot.plot(
                    [],
                    [],
                    pen=None,
                    symbol="o",
                    symbolBrush=color,
                    symbolPen="#ffffff",
                    symbolSize=12,
                )
                self._named_marker_items[name] = item
                self.item_create_count += 1
            if self._named_marker_cache.get(name) != normalized or self._named_marker_color_cache.get(name) != color:
                item.setData([normalized[0]], [normalized[1]])
                self._named_marker_cache[name] = normalized
                self._named_marker_color_cache[name] = color
                self.marker_update_count += 1

        for stale_name in set(self._named_marker_items) - set(markers):
            if stale_name in self._named_marker_cache:
                self._named_marker_items[stale_name].setData([], [])
                self._named_marker_cache.pop(stale_name, None)
                self._named_marker_color_cache.pop(stale_name, None)
                self.marker_update_count += 1

    def _pen_for(self, *, color: str, width: int = 2, style=None):
        key = (color, int(width), style)
        pen = self._pen_cache.get(key)
        if pen is None:
            pen = pg.mkPen(color=color, width=width, style=style)
            self._pen_cache[key] = pen
        return pen
