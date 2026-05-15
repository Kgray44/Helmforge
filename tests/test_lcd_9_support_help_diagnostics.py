from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from shared_core.models.runtime import (
    AXIS_NAMES,
    BUTTON_NAMES,
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)
from shared_core.models.workspace import create_default_workspace
from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState
from shared_core.runtime.telemetry import (
    AxisTelemetrySnapshot,
    BridgeTelemetrySnapshot,
    ButtonHatTelemetrySnapshot,
    ModeStateTelemetrySnapshot,
    OutputVerificationState,
    RuleStateSummary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUPPORT_ROUTES = (
    "support.help_docs",
    "support.perf_diagnostics",
    "support.setup_runtime_check",
)


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status(
    *,
    truth: RuntimeTruth = RuntimeTruth.DETECTED_UNVERIFIED,
    input_status: InputStatus = InputStatus.DETECTED,
    output_status: OutputStatus = OutputStatus.VJOY_DETECTED,
    output_verified: bool = False,
) -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.FULL_LIVE if truth is RuntimeTruth.LIVE_VERIFIED else RuntimeMode.SIMULATED,
        truth=truth,
        input=InputDeviceDetection(
            status=input_status,
            detected_device_names=("Thrustmaster T-Flight HOTAS One",) if input_status is InputStatus.DETECTED else (),
        ),
        output=OutputBackendDetection(
            status=output_status,
            backend_name="vJoy",
            live_output_writes_verified=output_verified,
        ),
    )


def _state(*, active_page_id: str = "help_docs"):
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(
        _runtime_status(),
        active_page_id=active_page_id,
        driver_detected=True,
    )
    state.active_profile = "LCD-9 Fixture"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = False
    state.selected_axis = "Roll"
    state.status_message = "LCD-9 Support fixture."
    return state


def _telemetry(*, roll: float = 0.2) -> BridgeTelemetrySnapshot:
    raw = {axis: 0.0 for axis in AXIS_NAMES}
    raw["Roll"] = roll
    final = {axis: value * 0.5 for axis, value in raw.items()}
    return BridgeTelemetrySnapshot(
        runtime_truth=RuntimeTruth.DETECTED_UNVERIFIED,
        lifecycle_state=BridgeLifecycleState.SIMULATED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        raw_axes=AxisTelemetrySnapshot(raw),
        final_axes=AxisTelemetrySnapshot(final),
        controls=ButtonHatTelemetrySnapshot(buttons={button: False for button in BUTTON_NAMES}, hats={"POV": "Centered"}),
        active_modes=ModeStateTelemetrySnapshot(),
        timestamp=datetime.now(timezone.utc),
        active_profile="LCD-9 Fixture",
        rule_summary=RuleStateSummary(),
        output_verification=OutputVerificationState(verified=False, backend_name="vJoy", message="missing"),
        runtime_frame={
            "telemetry_proof": "fresh",
            "input_stale": False,
            "full_live_runtime_ready": False,
            "output_verified": False,
            "output_proof": "missing",
            "ready_state": "blocked",
        },
    )


def _text_blob(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join(labels + buttons)


def test_lcd_9_support_pages_construct_offscreen_from_liquid_factories():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.support_command_pages import (
        create_help_docs_page,
        create_perf_diagnostics_page,
        create_setup_runtime_check_page,
    )

    factories = (
        ("support.help_docs", create_help_docs_page, "Help / Docs"),
        ("support.perf_diagnostics", create_perf_diagnostics_page, "Perf / Diagnostics"),
        ("support.setup_runtime_check", create_setup_runtime_check_page, "Setup / Runtime Check"),
    )
    for route_key, factory, title in factories:
        page = factory(state=_state(), workspace=create_default_workspace(), runtime_status=_runtime_status())
        text = _text_blob(page)

        assert page.objectName() == "liquidSupportCommandPage"
        assert page.property("routeKey") == route_key
        assert page.property("modeId") == "support"
        assert page.property("lcdPhase") == "LCD-9"
        assert title in text
        assert page.findChild(QWidget, "liquidSupportStatusRail") is not None
        assert page.findChild(QWidget, "liquidSupportAdvancedDetails") is not None
        assert "Liquid Command Deck placeholder" not in text
        assert "Placeholder route" not in text


def test_lcd_9_support_routes_are_wired_into_liquid_shell_not_placeholders():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    for route_key in SUPPORT_ROUTES:
        shell.switch_route(route_key)
        app.processEvents()
        page = shell.page_widgets[route_key].widget()
        text = _text_blob(page)

        assert page.objectName() == "liquidSupportCommandPage"
        assert page.property("routeKey") == route_key
        assert page.findChild(QWidget, "liquidSupportHero") is not None
        assert "Liquid Command Deck placeholder" not in text
        assert "Placeholder route" not in text


def test_lcd_9_help_docs_expose_topics_truth_explanations_and_parameter_metadata():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.support_command_pages import create_help_docs_page

    page = create_help_docs_page(state=_state(), workspace=create_default_workspace(), runtime_status=_runtime_status())
    text = _text_blob(page)
    topic_cards = [widget for widget in page.findChildren(QWidget) if widget.property("supportTopicCard") is True]

    assert len(topic_cards) >= 9
    for required in (
        "Getting Started",
        "Runtime Truth",
        "Mapping",
        "Tuning",
        "Analysis",
        "Recorder",
        "Troubleshooting",
        "Preflight and readiness",
        "Live Monitor",
        "Setup / vJoy / Bridge",
    ):
        assert required in text
    for truth_text in (
        "Output Intent is not output proof.",
        "vJoy detected is not output verified.",
        "Stream connected is not output proof.",
        "Recorder metadata-only artifacts are not real recordings.",
        "Simulation mode is safe fallback.",
        "Full Live Runtime Ready requires the full proof chain.",
    ):
        assert truth_text in text
    assert page.findChild(QWidget, "liquidSupportParameterReference") is not None
    assert "Curve Strength" in text
    assert "Deadzone" in text


def test_lcd_9_perf_diagnostics_groups_runtime_telemetry_output_perf_and_workspace_truth():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.pages.support_command_pages import create_perf_diagnostics_page
    from v3_app.services.perf_diagnostics import DiagnosticsCollector

    collector = DiagnosticsCollector()
    collector.record_timing("graph_update", 17.5)
    collector.record_timing("json_read", 41.0)
    collector.record_timing("diagnostics_update", 4.0)
    collector.record_hidden_skip("Live Monitor")

    page = create_perf_diagnostics_page(
        state=_state(active_page_id="perf_diagnostics"),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(),
        diagnostics_collector=collector,
    )
    text = _text_blob(page)
    sections = {
        widget.property("diagnosticSection")
        for widget in page.findChildren(QWidget)
        if widget.property("supportDiagnosticSection") is True
    }

    assert {
        "Runtime Truth",
        "Bridge / Telemetry",
        "Physical Input",
        "Virtual Output / vJoy",
        "Performance",
        "Workspace / UI",
    }.issubset(sections)
    for required in (
        "Full Live Runtime Ready",
        "Output proof",
        "Telemetry source",
        "JSON read cadence",
        "Graph/update timing",
        "over_16ms",
        "over_33ms",
        "over_50ms",
        "over_100ms",
        "over_250ms",
        "Live Monitor hidden-page skips",
    ):
        assert required in text
    assert page.findChild(QPushButton, "liquidSupportRefreshDiagnosticsButton") is not None
    assert page.findChild(QPushButton, "liquidSupportClearTimingsButton") is not None
    assert page.findChild(QPushButton, "liquidSupportCopyDiagnosticsButton") is not None


def test_lcd_9_setup_runtime_check_is_safe_dry_run_guidance_not_activation():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.pages.support_command_pages import create_setup_runtime_check_page

    page = create_setup_runtime_check_page(
        state=_state(active_page_id="setup_runtime_check"),
        workspace=create_default_workspace(),
        runtime_status=_runtime_status(input_status=InputStatus.MISSING),
    )
    text = _text_blob(page)
    gates = [widget for widget in page.findChildren(QWidget) if widget.property("componentRole") == "ReadinessGate"]

    assert len(gates) >= 7
    assert page.findChild(QWidget, "liquidSupportSetupChecklist") is not None
    for required in (
        "Connect HOTAS",
        "Confirm Windows sees controller",
        "Confirm Bridge telemetry",
        "Confirm workspace saved/applied",
        "Confirm vJoy driver detected",
        "Confirm vJoy device available",
        "Confirm output proof missing/verified",
        "Run safe setup check",
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\runtime_setup_check.ps1 -DryRun",
        "Setup checks are checks, not runtime activation.",
    ):
        assert required in text
    assert page.findChild(QPushButton, "liquidSupportLaunchInstallerButton") is None
    assert page.findChild(QPushButton, "liquidSupportStartBridgeButton") is None
    assert "Output verified" not in text


def test_lcd_9_support_source_reuses_services_without_wrapping_legacy_or_unsafe_runtime_actions():
    source = (PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "support_command_pages.py").read_text(encoding="utf-8")

    for required in (
        "from v3_app.services.help_docs import",
        "from v3_app.services.perf_diagnostics import",
        "parameter_reference_entries",
        "build_diagnostics_snapshot",
    ):
        assert required in source
    for forbidden in (
        "from v3_app.pages.help_docs_page",
        "from v3_app.pages.perf_diagnostics_page",
        "HelpDocsPage",
        "PerfDiagnosticsPage",
        "QDesktopServices",
        "LaunchInstallers",
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "verify_output_write",
        "write_output",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
    ):
        assert forbidden.casefold() not in source.casefold()


def test_lcd_9_live_monitor_visual_lane_targets_60fps_without_full_render_or_duplicate_samples():
    _app()

    from v3_app.liquid.pages.analysis_command_pages import (
        LIQUID_LIVE_MONITOR_VISUAL_INTERVAL_MS,
        LIQUID_LIVE_MONITOR_VISUAL_TARGET_FPS,
        AnalysisCommandPage,
    )

    page = AnalysisCommandPage(
        route_key="analysis.live_monitor",
        state=_state(active_page_id="live_monitor"),
        workspace=create_default_workspace(),
        telemetry=_telemetry(roll=0.2),
    )
    page.set_live_monitor_active(True)
    page._stop_live_display_timer()
    full_render_count = page.full_render_count
    model_build_count = page.model_build_count
    accepted_sample_count = page.accepted_sample_count

    assert LIQUID_LIVE_MONITOR_VISUAL_TARGET_FPS == 60
    assert 15 <= LIQUID_LIVE_MONITOR_VISUAL_INTERVAL_MS <= 17
    assert page.property("liveMonitorVisualTargetFps") == 60
    assert page.property("liveMonitorVisualRenderOnly") is True

    for _ in range(12):
        assert page.advance_live_monitor_visual_frame() is True

    assert page.property("liveMonitorVisualFrameTickCount") == 12
    assert page.full_render_count == full_render_count
    assert page.model_build_count == model_build_count
    assert page.accepted_sample_count == accepted_sample_count
    assert page.property("liveMonitorDuplicateSampleSkipCount") == 0

    page.update_analysis_snapshot(telemetry=_telemetry(roll=0.45))

    assert page.accepted_sample_count == accepted_sample_count + 1
    assert page.full_render_count == full_render_count
    assert page.model_build_count == model_build_count + 1
