from __future__ import annotations

import json
import os
from datetime import datetime, timezone


NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)


def _telemetry(
    *,
    raw_axes: dict[str, float] | None = None,
    final_axes: dict[str, float] | None = None,
    buttons: dict[str, bool] | None = None,
    hats: dict[str, str] | None = None,
    bridge_hash: str = "abc123",
    ui_hash: str = "abc123",
    output_verified: bool = False,
    full_ready: bool = False,
    source_label: str = "Bridge Stream",
) -> dict[str, object]:
    raw = {"Roll": 0.0, "Pitch": 0.0, "Throttle": 0.0, "Yaw": 0.0, "Aux 1": 0.0, "Aux 2": 0.0}
    raw.update(raw_axes or {})
    final = dict(raw)
    final.update(final_axes or {})
    btns = {f"B{index}": False for index in range(1, 16)}
    btns.update(buttons or {})
    return {
        "source_label": source_label,
        "age_seconds": 0.03,
        "raw_axes": raw,
        "final_axes": final,
        "buttons": btns,
        "hats": hats or {"HOTAS Hat": "Centered"},
        "bridge_workspace": {"workspace_hash": bridge_hash},
        "ui_workspace_hash": ui_hash,
        "device_discovery": {"status": "supported_device_detected", "matched": True, "device_name": "T.Flight HOTAS One"},
        "physical_input_fidelity": {
            "backend_name": "windows_winmm_joystick",
            "backend_kind": "windows_winmm",
            "sample_age_ms": 5.0,
            "read_duration_ms": 0.4,
            "estimated_sample_rate_hz": 120.0,
            "mapping_status": "ok",
        },
        "physical_input_backend_choice": {"selected_backend_name": "windows_winmm_joystick"},
        "output_status": "vjoy_detected",
        "output_verified": output_verified,
        "output_loop_runtime": {
            "verification_status": "real_verified" if output_verified else "not_attempted",
            "verification_real": output_verified,
            "state": "running" if output_verified else "disabled",
            "write_success_count": 2 if output_verified else 0,
            "write_skipped_count": 0,
            "write_failure_count": 0,
            "neutral_restore_status": "not_attempted",
            "safety_stop_reason": "None",
        },
        "runtime_frame": {
            "full_live_runtime_ready": full_ready,
            "ready_state": "ready" if full_ready else "blocked",
            "blocked_reason": "" if full_ready else "blocked_unverified_output",
            "fake_or_real_path": "real",
            "proof_summary": "Full gate open." if full_ready else "Output proof incomplete.",
            "output_intent_ready": True,
            "final_output_axes": final,
        },
    }


def test_hf_lrdc_4b_session_creates_required_steps_and_summarizes_status():
    from shared_core.runtime.manual_bench_validation import ManualValidationStepStatus, create_manual_validation_session

    session = create_manual_validation_session()
    step_ids = [step.step_id for step in session.steps]

    for required in ("telemetry_readiness", "config_sync", "hotas_detection", "axis_roll", "axis_pitch", "axis_throttle", "axis_yaw", "axis_aux1", "axis_aux2", "button_b1", "button_b2", "button_b15", "hat_up", "hat_right", "hat_down", "hat_left", "hat_centered", "pipeline_output_intent", "output_proof_status", "final_readiness_truth"):
        assert required in step_ids

    session.start_step("telemetry_readiness")
    session.record_operator_note("telemetry_readiness", "operator sees fresh frames")
    session.mark_step("telemetry_readiness", ManualValidationStepStatus.PASSED, observed_signal="fresh")

    assert session.step("telemetry_readiness").operator_note == "operator sees fresh frames"
    assert session.summary()["passed_count"] == 1
    assert session.summary()["overall_status"] in {"in_progress", "failed"}


def test_hf_lrdc_4b_axis_evaluation_passes_target_axis_only_and_ignores_noise():
    from shared_core.runtime.manual_bench_validation import create_manual_validation_session

    session = create_manual_validation_session(axis_threshold=0.2)
    session.start_step("axis_roll")
    session.evaluate_current_step(_telemetry(raw_axes={"Roll": 0.0}))
    session.evaluate_current_step(_telemetry(raw_axes={"Roll": 0.55}))
    assert session.step("axis_roll").status.value == "passed"

    pitch = create_manual_validation_session(axis_threshold=0.2)
    pitch.start_step("axis_pitch")
    pitch.evaluate_current_step(_telemetry(raw_axes={"Roll": 0.8, "Pitch": 0.01}))
    pitch.evaluate_current_step(_telemetry(raw_axes={"Roll": -0.8, "Pitch": 0.03}))
    assert pitch.step("axis_pitch").status.value != "passed"

    noise = create_manual_validation_session(axis_threshold=0.2)
    noise.start_step("axis_yaw")
    noise.evaluate_current_step(_telemetry(raw_axes={"Yaw": 0.0}))
    noise.evaluate_current_step(_telemetry(raw_axes={"Yaw": 0.05}))
    assert noise.step("axis_yaw").status.value != "passed"


def test_hf_lrdc_4b_button_and_hat_evaluation_from_telemetry():
    from shared_core.runtime.manual_bench_validation import create_manual_validation_session

    button = create_manual_validation_session()
    button.start_step("button_b1")
    button.evaluate_current_step(_telemetry(buttons={"B1": False}))
    button.evaluate_current_step(_telemetry(buttons={"B1": True}))
    button.evaluate_current_step(_telemetry(buttons={"B1": False}))
    assert button.step("button_b1").status.value == "passed"

    hat = create_manual_validation_session()
    hat.start_step("hat_right")
    hat.evaluate_current_step(_telemetry(hats={"HOTAS Hat": "Right"}))
    assert hat.step("hat_right").status.value == "passed"

    missing = create_manual_validation_session()
    missing.start_step("hat_down")
    missing.evaluate_current_step({**_telemetry(), "hats": {}})
    assert missing.step("hat_down").status.value in {"observing", "blocked"}


def test_hf_lrdc_4b_config_telemetry_and_output_truth_rules():
    from shared_core.runtime.manual_bench_validation import create_manual_validation_session

    config = create_manual_validation_session()
    config.start_step("config_sync")
    config.evaluate_current_step(_telemetry(bridge_hash="same", ui_hash="same"))
    assert config.step("config_sync").status.value == "passed"

    mismatch = create_manual_validation_session()
    mismatch.start_step("config_sync")
    mismatch.evaluate_current_step(_telemetry(bridge_hash="bridge", ui_hash="ui"))
    assert mismatch.step("config_sync").status.value == "blocked"

    stale = create_manual_validation_session()
    stale.start_step("telemetry_readiness")
    stale.evaluate_current_step({**_telemetry(), "age_seconds": 9.0})
    assert stale.step("telemetry_readiness").status.value == "blocked"

    output = create_manual_validation_session()
    output.start_step("output_proof_status")
    output.evaluate_current_step(_telemetry(output_verified=False))
    assert output.step("output_proof_status").status.value == "blocked"
    assert "Output intent is not output write proof" in output.step("output_proof_status").failure_reason

    ready = create_manual_validation_session()
    ready.start_step("final_readiness_truth")
    ready.evaluate_current_step(_telemetry(output_verified=True, full_ready=True))
    assert ready.step("final_readiness_truth").status.value == "passed"


def test_hf_lrdc_4b_export_writes_json_and_markdown(tmp_path):
    from shared_core.runtime.manual_bench_validation import create_manual_validation_session, export_manual_validation_session

    session = create_manual_validation_session(session_id="test-session")
    session.start_step("telemetry_readiness")
    session.evaluate_current_step(_telemetry())

    result = export_manual_validation_session(session, tmp_path)

    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    data = json.loads(result["json_path"].read_text(encoding="utf-8"))
    assert data["session_id"] == "test-session"
    assert "Manual Bench Validation" in result["markdown_path"].read_text(encoding="utf-8")


def test_hf_lrdc_4b_live_monitor_card_constructs_and_starts_session(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QLabel
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.app_state import AppState
    from shared_core.models.runtime import RuntimeMode, RuntimePreflightStatus, RuntimeTruth, InputDeviceDetection, InputStatus, OutputBackendDetection, OutputStatus

    app = QApplication.instance() or QApplication([])
    _ = app
    runtime_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )
    page = LiveMonitorPage(
        state=AppState.from_runtime_status(runtime_status, driver_detected=True),
        runtime_status=runtime_status,
        telemetry_path=tmp_path / "missing.json",
    )

    assert page.findChild(QLabel, "manualBenchValidationTitle").text() == "Manual Bench Validation"
    page.start_manual_validation()
    assert page.manual_validation_session is not None
    assert "Bridge / telemetry readiness" in page.findChild(QLabel, "manualBenchCurrentStep").text()
    assert page.findChild(QLabel, "manualBenchEvidence").text()
