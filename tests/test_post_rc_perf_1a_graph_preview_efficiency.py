from __future__ import annotations

import os


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_perf_1a_graph_preview_caches_pens_and_reuses_plot_items():
    from v3_app.pages.graph_widgets import GraphPreview

    _app()
    graph = GraphPreview(object_name="perfGraph")
    series = (("Raw", ((0.0, 0.0), (1.0, 1.0)), "#53b7ff"),)

    graph.plot_series(series)
    item_id = id(graph._series_items["Raw"])
    created = graph.item_create_count
    updates = graph.series_update_count

    graph.plot_series(series)

    assert id(graph._series_items["Raw"]) == item_id
    assert graph.item_create_count == created
    assert graph.series_update_count == updates
    assert len(graph._pen_cache) == 1

    changed = (("Raw", ((0.0, 0.0), (1.0, 0.5)), "#53b7ff"),)
    graph.plot_series(changed)
    assert graph.series_update_count == updates + 1


def test_perf_1a_graph_preview_marker_updates_do_not_replot_static_series():
    from v3_app.pages.graph_widgets import GraphPreview

    _app()
    graph = GraphPreview(object_name="perfGraphMarker")
    series = (("Effective", ((-1.0, -1.0), (1.0, 1.0)), "#53b7ff"),)
    graph.plot_series(series)
    series_updates = graph.series_update_count

    graph.update_marker((0.1, 0.2))
    first_marker_count = graph.marker_update_count
    graph.update_marker((0.1, 0.2))
    graph.update_marker((0.2, 0.3))

    assert graph.series_update_count == series_updates
    assert graph.marker_update_count == first_marker_count + 1
    assert graph.item_create_count == 2
