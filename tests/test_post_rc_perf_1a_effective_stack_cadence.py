from __future__ import annotations

import os


class FakeMonotonic:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


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


def test_perf_1a_effective_stack_reuses_pipeline_and_skips_repeated_compute(monkeypatch):
    from shared_core.math.pipeline import WorkspaceSignalPipeline as RealPipeline
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages import effective_response_stack_page as module
    from v3_app.pages.effective_response_stack_page import EffectiveResponseStackPage
    from v3_app.services.app_state import AppState
    from v3_app.services.live_ui_scheduler import MultiCadenceScheduler

    _app()
    counts = {"init": 0, "process": 0}

    class CountingPipeline(RealPipeline):
        def __init__(self, workspace):
            counts["init"] += 1
            super().__init__(workspace)

        def process(self, *args, **kwargs):
            counts["process"] += 1
            return super().process(*args, **kwargs)

    monkeypatch.setattr(module, "WorkspaceSignalPipeline", CountingPipeline)
    monotonic = FakeMonotonic()
    page = EffectiveResponseStackPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_status(),
    )
    page._timer.stop()
    page.show()
    page._scheduler = MultiCadenceScheduler(clock=monotonic)
    page._scheduler.force_all()
    init_count = counts["init"]

    for _ in range(100):
        page._tick()
        monotonic.advance(0.016)

    assert page.tick_count == 100
    assert counts["init"] == init_count
    assert page.pipeline_compute_count < page.tick_count
    assert page.full_render_count < page.tick_count
    assert page.static_graph_rebuild_count < page.tick_count
    assert page.marker_update_count >= page.static_graph_rebuild_count


def test_perf_1a_stage_cards_dirty_update_without_repolishing_unchanged_state():
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.effective_response_stack_page import EffectiveResponseStackPage
    from v3_app.services.app_state import AppState

    _app()
    page = EffectiveResponseStackPage(
        state=AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_status(),
    )
    page._timer.stop()
    card = page.stage_widgets["Raw Input"]
    before = card.repolish_count

    page.refresh_snapshot(raw_axis_values=dict(page._current_raw_values))
    after_first = card.repolish_count
    page.refresh_snapshot(raw_axis_values=dict(page._current_raw_values))

    assert card.update_count >= 1
    assert card.repolish_count == after_first
    assert card.repolish_count >= before
