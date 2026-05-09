from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
        messages=("Simulation mode selected because live output is not verified.",),
    )


def _shell(tmp_path):
    _app()
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell(
        AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )
    shell.switch_page("perf_diagnostics")
    return shell


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_phase11b_timing_service_records_summarizes_clears_and_counts_skips():
    from v3_app.services.perf_diagnostics import DiagnosticsCollector, format_metric_summary

    collector = DiagnosticsCollector()
    collector.record_timing("heartbeat", 10.0)
    collector.record_timing("heartbeat", 30.0)
    collector.record_timing("graph", 12.5)
    collector.record_hidden_skip("Live Monitor")
    collector.record_hidden_skip("Live Monitor")

    heartbeat = collector.summary("heartbeat")
    graph = collector.summary("graph")

    assert heartbeat.count == 2
    assert heartbeat.average_ms == 20.0
    assert heartbeat.max_ms == 30.0
    assert graph.count == 1
    assert format_metric_summary(heartbeat) == "count 2 | avg 20.0 ms | max 30.0 ms"
    assert collector.hidden_skip_counts()["Live Monitor"] == 2

    collector.clear()

    assert collector.summary("heartbeat").count == 0
    assert collector.hidden_skip_counts() == {}


def test_phase11b_copy_diagnostics_text_is_pure_and_truthful(tmp_path):
    from v3_app.services.app_state import AppState
    from v3_app.services.perf_diagnostics import (
        DEFAULT_MANUAL_BRIDGE_COMMAND,
        DiagnosticsCollector,
        build_diagnostics_snapshot,
        build_diagnostics_text,
    )

    state = AppState.from_runtime_status(_status(), driver_detected=True)
    state.active_page_id = "perf_diagnostics"
    state.selected_axis = "Yaw"
    state.source_config = str(tmp_path / "hotas_bridge_config_v3.json")
    collector = DiagnosticsCollector()
    collector.record_timing("page_switch", 9.5)
    collector.record_hidden_skip("Live Monitor")

    snapshot = build_diagnostics_snapshot(
        state=state,
        runtime_status=_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        telemetry_status="Missing",
        telemetry_age_seconds=None,
        process_hint="Unavailable",
        bridge_lifecycle="Simulated",
        hotas_discovery_status="no_supported_device",
        last_command_status="none",
        last_command_request_id="none",
        collector=collector,
    )
    text = build_diagnostics_text(snapshot)

    assert "HelmForge - HOTAS Control Panel V3" in text
    assert "Active page: perf_diagnostics" in text
    assert "Runtime truth: blocked_missing_device" in text
    assert "Bridge lifecycle: Simulated" in text
    assert "Bridge telemetry status: Missing" in text
    assert "HOTAS discovery: no_supported_device" in text
    assert "Output/vJoy status: vjoy_detected" in text
    assert "Output verified: false" in text
    assert "Full Live Runtime Ready: false" in text
    assert "Process hint: Unavailable" in text
    assert "Selected axis: Yaw" in text
    assert "page_switch: count 1 | avg 9.5 ms | max 9.5 ms" in text
    assert "Live Monitor hidden-page skips: 1" in text
    assert f"Manual Bridge launch: {DEFAULT_MANUAL_BRIDGE_COMMAND}" in text


def test_phase11b_perf_diagnostics_page_constructs_with_required_cards_and_truth(tmp_path):
    from PySide6.QtWidgets import QCheckBox, QPushButton

    shell = _shell(tmp_path)
    page = shell.page_widgets["perf_diagnostics"].widget()
    text = _label_text(page)

    assert "Perf / Diagnostics" in text
    for card in (
        "Runtime Truth",
        "Bridge / Telemetry",
        "Workspace / UI State",
        "Performance Timings",
        "Hidden Page Skips",
        "Commands / Preflight",
        "Diagnostic Actions",
    ):
        assert card in text

    for label in (
        "Active page",
        "Runtime truth",
        "Bridge lifecycle",
        "Bridge telemetry status",
        "Telemetry age",
        "Process hint",
        "HOTAS discovery",
        "Input device status",
        "Output/vJoy status",
        "Output verified",
        "Full Live Runtime Ready",
        "Selected axis",
        "Workspace/source file",
        "Last command status",
        "Last command request_id",
        "Runtime setup/preflight status",
        "Hidden page skips",
        "Page build/switch timings",
        "Heartbeat/update timing",
        "Graph draw/update timing",
        "Startup timing",
        "Diagnostics collection state",
    ):
        assert label in text

    assert "Runtime truth\nblocked_missing_device" in text
    assert "Bridge lifecycle" in text
    assert "vJoy detected; output writes unverified" in text
    assert "Output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text
    assert "Process presence is a hint only" in text
    assert "Telemetry remains the truth surface" in text
    assert "python -m bridge_app.main --run-for-ms 250" in text
    assert page.findChild(QCheckBox, "collectLiveTimingsToggle") is not None
    for button in ("Clear timings", "Run Runtime Preflight", "Copy Diagnostics"):
        assert button in {candidate.text() for candidate in page.findChildren(QPushButton)}


def test_phase11b_preflight_and_actions_are_safe_and_do_not_claim_runtime_ready(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton

    shell = _shell(tmp_path)
    page = shell.page_widgets["perf_diagnostics"].widget()

    page.findChild(QPushButton, "runRuntimePreflightButton").click()
    text = _label_text(page)
    assert "Runtime preflight check refreshed. This check does not verify output writes." in text
    assert "Output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text

    page.findChild(QPushButton, "copyDiagnosticsButton").click()
    copy_text = page.findChild(QLabel, "diagnosticsCopyText").text()
    assert "Runtime truth:" in copy_text
    assert "Output verified: false" in copy_text
    assert "Full Live Runtime Ready: false" in copy_text
    assert "Manual Bridge launch: python -m bridge_app.main --run-for-ms 250" in copy_text
    assert "Copy Diagnostics text prepared; clipboard integration is not required for Phase 11B." in _label_text(page)


def test_phase11b_clear_timings_and_collect_toggle_update_diagnostics_state(tmp_path):
    from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton

    shell = _shell(tmp_path)
    page = shell.page_widgets["perf_diagnostics"].widget()
    page._collector.record_timing("heartbeat", 22.0)
    page._collector.record_hidden_skip("Live Monitor")
    page.refresh_diagnostics()
    assert "heartbeat: count 1 | avg 22.0 ms | max 22.0 ms" in _label_text(page)
    assert "Live Monitor hidden-page skips: 1" in _label_text(page)

    toggle = page.findChild(QCheckBox, "collectLiveTimingsToggle")
    toggle.setChecked(False)
    assert "Diagnostics collection state\nPaused" in _label_text(page)

    page.findChild(QPushButton, "clearTimingsButton").click()
    assert "Timings and hidden-page skip counters cleared." in page.findChild(QLabel, "diagnosticsActionStatus").text()
    assert "heartbeat: unavailable" in _label_text(page)
    assert "Live Monitor hidden-page skips: Unavailable" in _label_text(page)


def test_phase11b_no_forbidden_controls_or_runtime_authority_imports_are_added(tmp_path):
    from PySide6.QtWidgets import QPushButton

    shell = _shell(tmp_path)
    page = shell.page_widgets["perf_diagnostics"].widget()
    button_text = " ".join(button.text() for button in page.findChildren(QPushButton))
    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "VerifyOutput",
        "Verify Output",
        "Install Service",
        "Enable Auto Start",
    ):
        assert forbidden not in button_text

    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
            PROJECT_ROOT / "v3_app" / "services" / "perf_diagnostics.py",
        )
    )
    for token in (
        "UpdateVJD",
        "SetAxis",
        "SetBtn",
        "AcquireVJD",
        "subprocess.Popen",
        "QProcess",
        "startDetached",
        "Start-Process",
        "win32serviceutil",
        "schtasks",
        "pystray",
        "openai",
        "anthropic",
        "auto_save",
    ):
        assert token not in sources


def test_phase11b_documentation_records_observational_diagnostics_scope():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-11b-perf-diagnostics-page-report.md"
    assert report.exists()
    docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "docs" / "HelmForge" / "bridge-ui-architecture.md",
            PROJECT_ROOT / "docs" / "HelmForge" / "bridge-service-design.md",
            report,
        )
    )
    for phrase in (
        "Phase 11B implements Perf / Diagnostics page only",
        "diagnostics are observational and do not add runtime authority",
        "Run Runtime Preflight remains safe and does not prove output verification",
        "timing metrics are UI/app diagnostics, not live hardware proof",
        "process presence remains a hint",
        "telemetry remains the truth surface",
    ):
        assert phrase in docs
