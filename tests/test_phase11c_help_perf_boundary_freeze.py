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

    return HelmForgeShell(
        AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_phase11c_help_docs_cross_links_and_required_topics_are_finalized():
    from v3_app.services.help_docs import articles_by_category, get_article

    grouped = articles_by_category()
    expected_topics = {
        "Advanced Pages": ("Conditional Rules", "Effective Response Stack", "Helm"),
        "Analysis": ("Graphs and Previews", "Runtime Indicators"),
        "Core Pages": ("Base Tuning", "Combat Profile", "Filtering", "Modes", "Profiles", "Mapping"),
        "Diagnostics": ("Performance / Diagnostics",),
        "Getting Started": ("Quick Start", "Runtime Setup / vJoy Setup"),
        "Reference": ("Tuning Glossary",),
        "Workflow": ("Saving and Importing",),
    }
    for category, titles in expected_topics.items():
        assert tuple(article.title for article in grouped[category]) == titles

    expected_related = {
        "Runtime Setup / vJoy Setup": {"Runtime Indicators", "Performance / Diagnostics"},
        "Runtime Indicators": {"Runtime Setup / vJoy Setup", "Performance / Diagnostics"},
        "Helm": {"Saving and Importing", "Runtime Indicators"},
        "Effective Response Stack": {"Graphs and Previews"},
        "Conditional Rules": {"Effective Response Stack"},
        "Saving and Importing": {"Helm"},
        "Performance / Diagnostics": {"Runtime Setup / vJoy Setup", "Runtime Indicators"},
    }
    for title, related in expected_related.items():
        assert related <= set(get_article(title).related_topics)


def test_phase11c_runtime_perf_articles_use_consistent_boundary_language():
    from v3_app.services.help_docs import get_article

    runtime_setup = get_article("Runtime Setup / vJoy Setup").search_text
    indicators = get_article("Runtime Indicators").search_text
    perf = get_article("Performance / Diagnostics").search_text

    assert "vJoy detected does not equal output verified" in runtime_setup
    assert "Telemetry remains the truth surface" in indicators
    assert "Diagnostics are observational" in perf
    assert "timing metrics are app/UI diagnostics, not live hardware proof" in perf
    assert "hidden-page skip counters show skipped expensive updates where instrumented" in perf
    assert "Run Runtime Preflight is safe and does not verify output" in perf
    assert "Copy Diagnostics creates local diagnostic text" in perf
    assert "output_verified remains false until a future verification phase proves writes" in perf
    assert "Full Live Runtime Ready remains false until future phases prove both input and output" in perf


def test_phase11c_perf_page_boundary_copy_and_actions_remain_safe(tmp_path):
    from PySide6.QtWidgets import QPushButton

    shell = _shell(tmp_path)
    shell.switch_page("perf_diagnostics")
    page = shell.page_widgets["perf_diagnostics"].widget()
    text = _label_text(page)
    button_text = " ".join(button.text() for button in page.findChildren(QPushButton))

    for section in (
        "Runtime Truth",
        "Bridge / Telemetry",
        "Workspace / UI State",
        "Performance Timings",
        "Hidden Page Skips",
        "Commands / Preflight",
        "Diagnostic Actions",
    ):
        assert section in text

    assert "Telemetry remains the truth surface" in text
    assert "Process presence is a hint only" in text
    assert "HOTAS discovery is discovery-only" in text
    assert "vJoy detected does not mean output verified" in text
    assert "Output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text
    assert "Run Runtime Preflight is a safe check/request, not runtime activation" in text

    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Install Service",
        "Enable Auto Start",
        "VerifyOutput",
        "Verify Output",
    ):
        assert forbidden not in button_text


def test_phase11c_copy_diagnostics_text_contains_truth_and_manual_guidance(tmp_path):
    from v3_app.services.app_state import AppState
    from v3_app.services.perf_diagnostics import (
        DEFAULT_MANUAL_BRIDGE_COMMAND,
        DiagnosticsCollector,
        build_diagnostics_snapshot,
        build_diagnostics_text,
    )

    state = AppState.from_runtime_status(_status(), driver_detected=True)
    state.active_page_id = "perf_diagnostics"
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
        collector=DiagnosticsCollector(),
    )
    text = build_diagnostics_text(snapshot)

    assert "Runtime truth: blocked_missing_device" in text
    assert "Output verified: false" in text
    assert "Full Live Runtime Ready: false" in text
    assert "Bridge telemetry status: Missing" in text
    assert "Telemetry remains the truth surface." in text
    assert f"Manual Bridge launch: {DEFAULT_MANUAL_BRIDGE_COMMAND}" in text


def test_phase11c_no_phase12_or_runtime_authority_was_added(tmp_path):
    from PySide6.QtWidgets import QPushButton
    from v3_app.services.bridge_commands import BridgeCommandClient

    shell = _shell(tmp_path)
    shell.switch_page("help_docs")
    help_page = shell.page_widgets["help_docs"].widget()
    shell.switch_page("perf_diagnostics")
    perf_page = shell.page_widgets["perf_diagnostics"].widget()
    button_text = " ".join(button.text() for page in (help_page, perf_page) for button in page.findChildren(QPushButton))

    for forbidden_button in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Install Service",
        "Enable Auto Start",
        "VerifyOutput",
        "Verify Output",
    ):
        assert forbidden_button not in button_text

    for unsafe in ("StartBridge", "StopBridge", "RestartBridge", "VerifyOutput"):
        assert BridgeCommandClient(command_path=tmp_path / "command.json").write_command(unsafe).success is False

    assert not (PROJECT_ROOT / "v3_app" / "pages" / "live_overlay_page.py").exists()
    recorder_page = PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py"
    if recorder_page.exists():
        recorder_text = recorder_page.read_text(encoding="utf-8")
        assert "Capture backend missing" in recorder_text
        assert "Recording backend is not active in this phase" in recorder_text

    phase11_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "pages" / "help_docs_page.py",
            PROJECT_ROOT / "v3_app" / "pages" / "perf_diagnostics_page.py",
            PROJECT_ROOT / "v3_app" / "services" / "help_docs.py",
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
        assert token not in phase11_sources


def test_phase11c_documentation_records_completed_phase11_boundary():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-11c-help-perf-diagnostics-boundary-freeze-report.md"
    assert report.exists()

    phase11b_report = (PROJECT_ROOT / "docs" / "HelmForge" / "phase-11b-perf-diagnostics-page-report.md").read_text(encoding="utf-8")
    assert "`git diff --check` - passed" in phase11b_report
    assert "pending final diff hygiene pass" not in phase11b_report

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
        "Phase 11 is now complete",
        "next prompt-book phase is Phase 12 Live Overlay Foundation",
        "Phase 12 must preserve the Phase 9K runtime boundary and Phase 10E Helm boundary",
        "Phase 11C does not add runtime authority",
        "Live Overlay",
        "Flight Recorder",
        "real HOTAS polling",
        "vJoy writes",
        "output verification",
        "real runtime activation",
    ):
        assert phrase in docs
