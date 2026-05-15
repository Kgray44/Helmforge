from __future__ import annotations

import os

from shared_core.models.runtime import AXIS_NAMES


class FakeMonotonic:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class CountingSource:
    total_reads = 0

    def __init__(self, runtime_bridge, bridge_client=None, *, clock=None) -> None:
        self.last_source_label = "Counting source"
        self.last_runtime_truth = runtime_bridge.runtime_status.truth.value
        self.last_output_verified = runtime_bridge.runtime_status.live_output_writes_verified

    def raw_axes(self) -> dict[str, float]:
        type(self).total_reads += 1
        return {axis: 0.15 for axis in AXIS_NAMES}


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _status():
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )

    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )


def _page(page_cls):
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import AppState

    _app()
    page = page_cls(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_status(),
    )
    page._timer.stop()
    page.show()
    return page


def test_perf_1a_tuning_pages_do_not_read_live_source_at_60hz(monkeypatch):
    from v3_app.pages import base_tuning_page, combat_profile_page, filtering_page
    from v3_app.services.live_ui_scheduler import MultiCadenceScheduler

    for module in (base_tuning_page, filtering_page, combat_profile_page):
        monkeypatch.setattr(module, "LiveAxisSampleSource", CountingSource)

    pages = [
        _page(base_tuning_page.BaseTuningPage),
        _page(filtering_page.FilteringPage),
        _page(combat_profile_page.CombatProfilePage),
    ]
    for page in pages:
        clock = FakeMonotonic()
        page._live_scheduler = MultiCadenceScheduler(clock=clock)
        page._live_scheduler.force_all()
        for _ in range(100):
            page._tick()
            clock.advance(0.016)

        assert page.tick_count == 100
        assert page.live_source_read_count < page.tick_count
        assert page.marker_update_count < page.tick_count
        assert page.static_graph_rebuild_count < page.tick_count


def test_perf_1a_tuning_static_graph_rebuilds_only_on_axis_or_setting_changes(monkeypatch):
    from v3_app.pages import base_tuning_page

    monkeypatch.setattr(base_tuning_page, "LiveAxisSampleSource", CountingSource)
    page = _page(base_tuning_page.BaseTuningPage)
    before = page.static_graph_rebuild_count

    for _ in range(10):
        page._tick()

    assert page.static_graph_rebuild_count == before
    page.set_selected_axis("Yaw")
    assert page.static_graph_rebuild_count == before + 1
