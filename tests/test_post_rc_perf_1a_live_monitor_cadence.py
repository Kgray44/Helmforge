from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone


NOW = datetime(2026, 5, 12, 12, 0, 0, tzinfo=timezone.utc)


class FakeMonotonic:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeDateClock:
    def __init__(self, value: datetime = NOW) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status():
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
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )


def _payload(*, sequence: int = 1, timestamp: datetime = NOW, roll: float = 0.25) -> dict[str, object]:
    return {
        "timestamp": timestamp.isoformat(),
        "lifecycle_state": "LiveUnverified",
        "runtime_truth": "detected_unverified",
        "input_status": "detected",
        "output_status": "vjoy_detected",
        "output_verified": False,
        "active_profile": "Current Workspace",
        "raw_axes": {"Roll": roll, "Pitch": 0.0, "Throttle": 0.0, "Yaw": 0.0, "Aux 1": 0.0, "Aux 2": 0.0},
        "final_axes": {"Roll": roll * 0.5, "Pitch": 0.0, "Throttle": 0.0, "Yaw": 0.0, "Aux 1": 0.0, "Aux 2": 0.0},
        "buttons": {f"B{index}": False for index in range(1, 16)},
        "hats": {"HOTAS Hat": "Centered", "Output Hat": "Centered"},
        "active_modes": {"active_mode_names": []},
        "rule_summary": {"active_count": 0, "blocked_count": 0, "disabled_count": 0},
        "runtime_frame": {
            "schema_version": "helmforge.runtime_frame.v1",
            "sequence": sequence,
            "frame_id": f"runtime-frame-{sequence}",
            "generated_at": timestamp.isoformat(),
            "output_verified": False,
            "full_live_runtime_ready": False,
            "ready_state": "blocked",
            "telemetry_proof": "fresh",
            "safety_proof": "ok",
            "fake_or_real_path": "real",
        },
        "bridge_timing": {"tick_count": sequence, "last_tick_duration_ms": 4.0},
    }


def _page(tmp_path, *, bridge_clock=None, telemetry_stream_enabled=False):
    from shared_core.models.workspace import create_default_workspace
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    telemetry_path = tmp_path / "telemetry.json"
    telemetry_path.write_text(json.dumps(_payload()), encoding="utf-8")
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        telemetry_path=telemetry_path,
        bridge_clock=bridge_clock or (lambda: NOW),
        telemetry_stream_enabled=telemetry_stream_enabled,
    )
    page._timer.stop()
    page.show()
    return page


def test_perf_1a_live_monitor_throttles_repeated_json_frames_and_render_lanes(tmp_path):
    from v3_app.services.live_ui_scheduler import MultiCadenceScheduler

    monotonic = FakeMonotonic()
    date_clock = FakeDateClock()
    page = _page(tmp_path, bridge_clock=date_clock)
    page._scheduler = MultiCadenceScheduler(clock=monotonic)
    page._scheduler.force_all()
    initial_history = len(page.history)

    for _ in range(100):
        page._tick()
        monotonic.advance(0.016)
        date_clock.advance(0.016)

    assert page.tick_count == 100
    assert page.json_read_count <= 10
    assert page.history_append_count <= initial_history + 1
    assert len(page.history) <= initial_history + 1
    assert page.graph_update_count < page.tick_count
    assert page.value_update_count < page.tick_count
    assert page.repeated_frame_skip_count > 0


def test_perf_1a_live_monitor_embedded_and_stream_sources_skip_high_rate_json(tmp_path):
    from v3_app.services.bridge_client import BridgeTelemetryClient, BridgeTelemetryReadResult, BridgeTelemetryStatus
    from v3_app.services.embedded_bridge_telemetry import clear_embedded_bridge_telemetry, record_embedded_bridge_telemetry
    from v3_app.services.live_ui_scheduler import MultiCadenceScheduler

    date_clock = FakeDateClock()
    monotonic = FakeMonotonic()
    page = _page(tmp_path, bridge_clock=date_clock)
    page._scheduler = MultiCadenceScheduler(clock=monotonic)

    telemetry = BridgeTelemetryClient(telemetry_path=tmp_path / "telemetry.json", clock=date_clock).read().telemetry
    clear_embedded_bridge_telemetry()
    record_embedded_bridge_telemetry(telemetry, recorded_at=date_clock())

    class FailingJsonClient:
        def read(self):
            raise AssertionError("fresh embedded telemetry should bypass JSON reads")

    page._bridge_client = FailingJsonClient()
    embedded = page._read_bridge_telemetry()
    assert embedded.source_label == "Embedded Bridge"
    assert page.json_read_count == 0

    clear_embedded_bridge_telemetry()
    stream_result = BridgeTelemetryReadResult(
        status=BridgeTelemetryStatus.CONNECTED,
        path=tmp_path / "stream",
        telemetry=telemetry,
        last_read_at=date_clock(),
        age_seconds=0.0,
        source_label="Bridge Stream",
    )

    class FakeStream:
        read_count = 0

        def read_latest(self):
            self.read_count += 1
            return replace(stream_result, source_label="Bridge Stream")

    page._bridge_stream_client = FakeStream()
    selected = page._read_bridge_telemetry()
    assert selected.source_label == "Bridge Stream"
    assert page.json_read_count == 0
