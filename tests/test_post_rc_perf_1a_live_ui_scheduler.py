from __future__ import annotations


def test_perf_1a_cadence_gate_is_deterministic_under_injected_time():
    from v3_app.services.live_ui_scheduler import CadenceGate

    gate = CadenceGate(rate_hz=5.0)

    assert gate.due(10.0) is True
    gate.mark(10.0)
    assert gate.due(10.19) is False
    assert gate.due(10.20) is True

    gate.mark(10.20)
    gate.force()
    assert gate.due(10.21) is True
    gate.mark(10.21)
    gate.reset()
    assert gate.due(10.22) is True


def test_perf_1a_scheduler_centralizes_named_live_ui_lanes():
    from v3_app.services.live_ui_scheduler import DEFAULT_LIVE_UI_CADENCES, MultiCadenceScheduler

    scheduler = MultiCadenceScheduler(clock=lambda: 0.0)

    assert DEFAULT_LIVE_UI_CADENCES["telemetry_json"].rate_hz == 5.0
    assert DEFAULT_LIVE_UI_CADENCES["shell_chrome"].rate_hz == 10.0
    assert DEFAULT_LIVE_UI_CADENCES["overlay_paint"].rate_hz == 30.0
    assert DEFAULT_LIVE_UI_CADENCES["effective_stack_compute"].rate_hz <= 20.0
    assert 24.0 <= DEFAULT_LIVE_UI_CADENCES["graphs"].rate_hz <= 30.0


def test_perf_1a_dirty_cache_timing_series_and_jank_buckets_are_bounded():
    from v3_app.services.live_ui_scheduler import BoundedTimingSeries, DirtyValueCache, JankBucketCounter

    cache = DirtyValueCache()
    assert cache.changed("axis", ("Roll", 0.1)) is True
    assert cache.changed("axis", ("Roll", 0.1)) is False
    assert cache.changed("axis", ("Roll", 0.2)) is True

    timings = BoundedTimingSeries(max_samples=3)
    for value in (1.0, 2.0, 3.0, 100.0):
        timings.append(value)
    summary = timings.summary("graph_update")
    assert summary.count == 3
    assert summary.last_ms == 100.0
    assert summary.max_ms == 100.0

    buckets = JankBucketCounter()
    for value in (12.0, 17.0, 35.0, 52.0, 150.0, 300.0):
        buckets.observe(value)

    assert buckets.snapshot()["over_16ms"] == 5
    assert buckets.snapshot()["over_33ms"] == 4
    assert buckets.snapshot()["over_50ms"] == 3
    assert buckets.snapshot()["over_100ms"] == 2
    assert buckets.snapshot()["over_250ms"] == 1


def test_perf_1a_diagnostics_collector_keeps_bounded_lane_history():
    from v3_app.services.perf_diagnostics import DiagnosticsCollector

    collector = DiagnosticsCollector(max_timing_samples=5)
    for index in range(20):
        collector.record_timing("graph_update", float(index))

    summary = collector.summary("graph_update")

    assert summary.count == 5
    assert summary.last_ms == 19.0
    assert summary.max_ms == 19.0
    assert collector.jank_buckets("graph_update")["over_16ms"] == 3
