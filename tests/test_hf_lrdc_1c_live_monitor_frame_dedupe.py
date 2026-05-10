from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone


NOW = datetime(2026, 5, 9, 12, 0, 0, tzinfo=timezone.utc)


def _payload(
    *,
    sequence: int | None = 1,
    frame_id: str = "runtime-frame-1",
    generated_at: datetime | None = NOW,
    timestamp: datetime = NOW,
    tick_count: int = 1,
    roll: float = 0.1,
) -> dict[str, object]:
    runtime_frame = {
        "schema_version": "helmforge.runtime_frame.v1",
        "frame_id": frame_id,
        "sequence": sequence,
        "generated_at": generated_at.isoformat() if generated_at else None,
        "input_source": "physical",
        "input_status": "active",
        "input_device": "Thrustmaster T.Flight HOTAS One",
        "pipeline_status": "physical_input_ready_output_unverified",
        "final_output_axes": {"Roll": roll},
        "output_intent_ready": True,
        "output_backend": "Real vJoy",
        "output_verification_status": "not_attempted",
        "output_loop_state": "disabled",
        "last_output_write_status": "Not active",
        "output_verified": False,
        "full_live_runtime_ready": False,
        "runtime_truth": "blocked_unverified_output",
        "blocked_reason": "blocked_unverified_output",
        "ready_state": "blocked",
        "telemetry_proof": "fresh",
        "safety_proof": "ok",
        "fake_or_real_path": "real",
        "evaluated_at": timestamp.isoformat(),
        "proof_summary": "Output intent is not output write proof.",
    }
    return {
        "timestamp": timestamp.isoformat(),
        "lifecycle_state": "LiveUnverified",
        "runtime_truth": "detected_unverified",
        "input_status": "detected",
        "output_status": "vjoy_detected",
        "output_verified": False,
        "active_profile": "Current Workspace",
        "raw_axes": {"Roll": roll, "Pitch": 0, "Throttle": 0, "Yaw": 0, "Aux 1": 0, "Aux 2": 0},
        "final_axes": {"Roll": roll, "Pitch": 0, "Throttle": 0, "Yaw": 0, "Aux 1": 0, "Aux 2": 0},
        "buttons": {f"B{index}": False for index in range(1, 16)},
        "hats": {"HOTAS Hat": "Centered", "Output Hat": "Centered"},
        "active_modes": {"active_mode_names": []},
        "rule_summary": {"active_count": 0, "blocked_count": 0, "disabled_count": 0},
        "runtime_frame": runtime_frame,
        "bridge_timing": {
            "tick_count": tick_count,
            "last_tick_duration_ms": 4.2,
            "last_input_read_duration_ms": 0.3,
            "last_pipeline_duration_ms": 0.8,
            "last_output_write_duration_ms": 0.0,
            "last_telemetry_publish_duration_ms": 0.4,
        },
        "physical_input_fidelity": {
            "backend_name": "windows_winmm_joystick",
            "backend_kind": "windows_winmm",
            "sequence": 12,
            "sample_age_ms": 5.0,
            "read_duration_ms": 0.3,
            "estimated_sample_rate_hz": 120.0,
            "mapping_status": "ok",
        },
        "physical_input_backend_choice": {
            "selected_backend_name": "windows_winmm_joystick",
            "selected_backend_kind": "windows_winmm",
            "fallback_used": True,
        },
    }


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status():
    from shared_core.models.runtime import InputDeviceDetection, InputStatus, OutputBackendDetection, OutputStatus, RuntimeMode, RuntimePreflightStatus, RuntimeTruth

    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )


def test_hf_lrdc_1c_frame_identity_prefers_strongest_available_fields():
    from v3_app.pages.live_monitor_data import extract_bridge_frame_identity
    from v3_app.services.bridge_client import BridgeTelemetryClient

    path = __import__("tempfile").NamedTemporaryFile(delete=False).name
    from pathlib import Path

    telemetry_path = Path(path)
    _write(telemetry_path, _payload(sequence=7, frame_id="frame-a", tick_count=99))
    telemetry = BridgeTelemetryClient(telemetry_path=telemetry_path, clock=lambda: NOW).read().telemetry
    assert extract_bridge_frame_identity(telemetry).identity_key == "sequence:7"

    _write(telemetry_path, _payload(sequence=None, frame_id="frame-b", tick_count=99))
    telemetry = BridgeTelemetryClient(telemetry_path=telemetry_path, clock=lambda: NOW).read().telemetry
    assert extract_bridge_frame_identity(telemetry).identity_key == "frame_id:frame-b"

    generated = NOW + timedelta(milliseconds=20)
    _write(telemetry_path, _payload(sequence=None, frame_id="", generated_at=generated, tick_count=99))
    telemetry = BridgeTelemetryClient(telemetry_path=telemetry_path, clock=lambda: NOW).read().telemetry
    assert extract_bridge_frame_identity(telemetry).identity_key == f"generated_at:{generated.isoformat()}"

    _write(telemetry_path, _payload(sequence=None, frame_id="", generated_at=None, timestamp=generated, tick_count=99))
    telemetry = BridgeTelemetryClient(telemetry_path=telemetry_path, clock=lambda: generated).read().telemetry
    assert extract_bridge_frame_identity(telemetry).identity_key == f"timestamp:{generated.isoformat()}"


def test_hf_lrdc_1c_tracker_dedupes_repeats_and_estimates_accepted_cadence():
    from v3_app.pages.live_monitor_data import LiveTelemetryFrameTracker, extract_bridge_frame_identity
    from v3_app.services.bridge_client import BridgeTelemetryClient

    telemetry_path = __import__("pathlib").Path(__import__("tempfile").NamedTemporaryFile(delete=False).name)
    tracker = LiveTelemetryFrameTracker()

    _write(telemetry_path, _payload(sequence=1, timestamp=NOW))
    first = BridgeTelemetryClient(telemetry_path=telemetry_path, clock=lambda: NOW).read().telemetry
    first_result = tracker.observe(extract_bridge_frame_identity(first), received_at=NOW)
    assert first_result.is_new_frame is True

    repeat_result = tracker.observe(extract_bridge_frame_identity(first), received_at=NOW + timedelta(milliseconds=8))
    assert repeat_result.is_new_frame is False
    assert repeat_result.repeated_frame_count == 1
    assert repeat_result.accepted_cadence_hz is None

    _write(telemetry_path, _payload(sequence=2, timestamp=NOW + timedelta(milliseconds=20)))
    second = BridgeTelemetryClient(telemetry_path=telemetry_path, clock=lambda: NOW + timedelta(milliseconds=20)).read().telemetry
    second_result = tracker.observe(extract_bridge_frame_identity(second), received_at=NOW + timedelta(milliseconds=20))
    assert second_result.is_new_frame is True
    assert round(second_result.accepted_cadence_hz or 0) == 50


def test_hf_lrdc_1c_live_monitor_appends_only_new_bridge_frames_and_keeps_labels_current(tmp_path):
    from PySide6.QtWidgets import QLabel
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    telemetry_path = tmp_path / "telemetry.json"
    _write(telemetry_path, _payload(sequence=1, roll=0.2))
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        runtime_status=_runtime_status(),
        telemetry_path=telemetry_path,
        bridge_clock=lambda: NOW,
    )
    first_len = len(page.history)

    page.refresh_snapshot(force_new=True)
    repeated_len = len(page.history)
    assert repeated_len == first_len
    assert page.repeated_bridge_frame_count >= 1

    _write(telemetry_path, _payload(sequence=2, timestamp=NOW + timedelta(milliseconds=20), roll=0.7))
    page.refresh_snapshot(force_new=True)

    assert len(page.history) == repeated_len + 1
    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))
    assert "Bridge frame:" in labels_text
    assert "Repeated frames skipped:" in labels_text
    assert "tick 4.2 ms" in labels_text
    assert "Physical input: windows_winmm_joystick" in labels_text
    assert "mapping ok" in labels_text
    assert "Full Live Runtime Ready true" not in labels_text
    assert "Output Verified" not in labels_text


def test_hf_lrdc_1c_generated_at_change_appends_when_sequence_missing(tmp_path):
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    telemetry_path = tmp_path / "telemetry.json"
    _write(telemetry_path, _payload(sequence=None, frame_id="", generated_at=NOW))
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        runtime_status=_runtime_status(),
        telemetry_path=telemetry_path,
        bridge_clock=lambda: NOW,
    )
    before = len(page.history)

    _write(telemetry_path, _payload(sequence=None, frame_id="", generated_at=NOW + timedelta(milliseconds=16), timestamp=NOW + timedelta(milliseconds=16)))
    page.refresh_snapshot(force_new=True)

    assert len(page.history) == before + 1


def test_hf_lrdc_1c_stale_bridge_uses_simulation_fallback_without_output_overclaim(tmp_path):
    from PySide6.QtWidgets import QLabel
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState

    _app()
    telemetry_path = tmp_path / "telemetry.json"
    _write(telemetry_path, _payload(sequence=1, timestamp=NOW))
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        runtime_status=_runtime_status(),
        telemetry_path=telemetry_path,
        bridge_clock=lambda: NOW + timedelta(seconds=10),
        bridge_stale_after_seconds=1.0,
    )

    labels_text = " ".join(label.text() for label in page.findChildren(QLabel))
    assert "Bridge Stale" in labels_text or "Stale" in labels_text
    assert "Simulation Fallback" in labels_text
    assert "Full Live Runtime Ready true" not in labels_text
