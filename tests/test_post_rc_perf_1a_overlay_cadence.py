from __future__ import annotations

import os


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_perf_1a_overlay_default_fps_is_30_and_range_still_allows_high_caps():
    from v3_app.overlay.overlay_config import LiveOverlayConfig

    config = LiveOverlayConfig.defaults()
    assert config.fps_cap == 30
    assert LiveOverlayConfig.from_dict({**config.to_dict(), "fps_cap": 144}).fps_cap == 144


def test_perf_1a_overlay_renderer_setters_mark_dirty_without_duplicate_updates():
    from v3_app.overlay.overlay_config import LiveOverlayConfig
    from v3_app.overlay.overlay_renderer import OverlayRenderer
    from v3_app.overlay.telemetry_buffer import OverlayTelemetrySample
    from v3_app.overlay.trace_builder import OverlayTraceBuilderCache

    _app()
    config = LiveOverlayConfig.defaults()
    renderer = OverlayRenderer(config=config)
    cache = OverlayTraceBuilderCache()
    samples = (
        OverlayTelemetrySample(timestamp=1.0, axes={"Roll": 0.1}, source="Final output"),
        OverlayTelemetrySample(timestamp=2.0, axes={"Roll": 0.2}, source="Final output"),
    )
    trace = cache.build(config, samples)

    renderer.set_trace_set(trace)
    renderer.set_trace_set(trace)
    renderer.set_runtime_truth(runtime_truth="simulated", output_verified=False, full_live_runtime_ready=False, source="Final output")
    renderer.set_runtime_truth(runtime_truth="simulated", output_verified=False, full_live_runtime_ready=False, source="Final output")

    assert cache.build_count == 1
    assert renderer.trace_set_update_count == 1
    assert renderer.runtime_truth_update_count <= 1
    assert renderer.update_request_count == 0
    assert renderer.consume_dirty_for_paint() is True
    assert renderer.consume_dirty_for_paint() is False


def test_perf_1a_overlay_window_skips_timer_repaint_when_nothing_changed():
    from v3_app.overlay.live_overlay_window import LiveOverlayWindow
    from v3_app.overlay.overlay_config import LiveOverlayConfig

    _app()
    window = LiveOverlayWindow(
        config=LiveOverlayConfig.defaults(),
        runtime_truth="blocked_missing_device",
        output_verified=False,
        full_live_runtime_ready=False,
    )
    window.show_overlay()
    for _ in range(10):
        window._refresh_if_visible()

    assert window.overlay_timer_tick_count == 10
    assert window.overlay_update_count < window.overlay_timer_tick_count
    window.hide_overlay()
