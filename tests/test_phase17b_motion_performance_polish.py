from __future__ import annotations

import os
from pathlib import Path

from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status() -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
        messages=("Simulation fallback remains available; live output is not verified.",),
    )


def _state():
    from v3_app.services.app_state import AppState

    return AppState.from_runtime_status(_runtime_status(), driver_detected=True)


def _workspace():
    from shared_core.models.workspace import create_default_workspace

    return create_default_workspace()


def _shell(tmp_path):
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        _state(),
        workspace=_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )


def _widget_text(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join((*labels, *buttons))


def test_phase17b_shell_reuses_heavy_pages_and_shared_perf_collector(tmp_path):
    _app()

    shell = _shell(tmp_path)
    heavy_pages = (
        "live_monitor",
        "effective_response_stack",
        "flight_recorder",
        "help_docs",
        "perf_diagnostics",
    )

    first_scroll_ids: dict[str, int] = {}
    first_content_ids: dict[str, int] = {}
    for page_id in heavy_pages:
        shell.switch_page(page_id)
        first_scroll_ids[page_id] = id(shell.page_widgets[page_id])
        first_content_ids[page_id] = id(shell.page_widgets[page_id].widget())

    for page_id in heavy_pages:
        shell.switch_page(page_id)
        assert id(shell.page_widgets[page_id]) == first_scroll_ids[page_id]
        assert id(shell.page_widgets[page_id].widget()) == first_content_ids[page_id]

    assert shell.diagnostics_collector.summary("page_switch").count >= len(heavy_pages)


def test_phase17b_graph_preview_updates_plot_items_in_place():
    _app()

    from v3_app.pages.graph_widgets import GraphPreview

    graph = GraphPreview(object_name="phase17bGraphPreview")
    graph.plot_series_with_marker(
        (
            ("Raw", ((0.0, 0.0), (1.0, 0.5)), "#53b7ff"),
            ("Final", ((0.0, 0.0), (1.0, 0.25)), "#76d39b"),
        ),
        marker=(1.0, 0.5),
    )
    first_items = dict(graph._series_items)
    first_marker = graph._marker_item
    first_count = len(graph.plot.listDataItems())

    graph.plot_series_with_marker(
        (
            ("Raw", ((0.0, 0.1), (1.0, 0.6), (2.0, 0.4)), "#53b7ff"),
            ("Final", ((0.0, 0.0), (1.0, 0.2), (2.0, 0.1)), "#76d39b"),
        ),
        marker=(2.0, 0.1),
    )

    assert graph._series_items == first_items
    assert graph._marker_item is first_marker
    assert len(graph.plot.listDataItems()) == first_count


def test_phase17b_hidden_live_and_stack_ticks_skip_heavy_refresh_and_count():
    _app()

    from v3_app.pages.effective_response_stack_page import EffectiveResponseStackPage
    from v3_app.pages.live_monitor_page import LiveMonitorPage
    from v3_app.services.perf_diagnostics import DiagnosticsCollector

    collector = DiagnosticsCollector()
    live = LiveMonitorPage(
        state=_state(),
        workspace=_workspace(),
        runtime_status=_runtime_status(),
        diagnostics_collector=collector,
    )
    live.hide()
    sample_index = live._sample_index
    live._tick()

    stack = EffectiveResponseStackPage(
        state=_state(),
        workspace=_workspace(),
        runtime_status=_runtime_status(),
        diagnostics_collector=collector,
    )
    stack.hide()
    stage_ids = {name: id(widget) for name, widget in stack.stage_widgets.items()}
    stack._tick()

    hidden = collector.hidden_skip_counts()
    assert live._sample_index == sample_index
    assert hidden["Live Monitor"] == 1
    assert hidden["Effective Response Stack"] == 1
    assert {name: id(widget) for name, widget in stack.stage_widgets.items()} == stage_ids


def test_phase17b_overlay_helm_help_recorder_and_perf_interactions(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel
    from v3_app.overlay.live_overlay_window import LiveOverlayWindow
    from v3_app.overlay.overlay_config import LiveOverlayConfig
    from v3_app.pages.flight_recorder_page import FlightRecorderPage
    from v3_app.pages.help_docs_page import HelpDocsPage
    from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
    from v3_app.services.perf_diagnostics import DiagnosticsCollector

    overlay = LiveOverlayWindow(
        config=LiveOverlayConfig.defaults(),
        runtime_truth="blocked_missing_device",
        output_verified=False,
        full_live_runtime_ready=False,
    )
    overlay.show_overlay()
    assert overlay.refresh_timer.isActive()
    overlay.hide_overlay()
    assert not overlay.refresh_timer.isActive()

    shell = _shell(tmp_path)
    helm = shell.open_helm_overlay()
    assert "Apply Selected Changes" in _widget_text(helm)
    helm.close()
    assert not helm.isVisible()

    help_page = HelpDocsPage(state=_state(), workspace=_workspace(), runtime_status=_runtime_status())
    for query in ("Runtime Setup", "Helm", "Live Overlay", "Flight Recorder", ""):
        help_page.search_field.setText(query)
        assert help_page.topic_list.count() > 0
        assert help_page.article_title.text()

    recorder = FlightRecorderPage(state=_state(), workspace=_workspace(), runtime_status=_runtime_status())
    recorder.refresh_library()
    recorder_text = _widget_text(recorder)
    assert "Metadata-only preview" in recorder_text
    assert "No video captured" in recorder_text
    assert "No encoding performed" in recorder_text
    assert "Recording started" not in recorder_text

    collector = DiagnosticsCollector()
    collector.record_timing("heartbeat", 11.0)
    collector.record_timing("graph", 7.0)
    collector.record_hidden_skip("Live Monitor")
    perf = PerfDiagnosticsPage(
        state=_state(),
        workspace=_workspace(),
        runtime_status=_runtime_status(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        diagnostics_collector=collector,
    )
    perf_text = _widget_text(perf)
    copy_text = perf.prepare_copy_diagnostics()
    assert "Heartbeat/update timing" in perf_text
    assert "Graph draw/update timing" in perf_text
    assert perf._rows["Live Monitor hidden-page skips"].text() == "Live Monitor hidden-page skips: 1"
    assert "Live Monitor hidden-page skips: 1" in copy_text
    perf.clear_timings()
    assert "heartbeat: unavailable" in _widget_text(perf)
    assert perf._rows["Live Monitor hidden-page skips"].text() == "Live Monitor hidden-page skips: Unavailable"
    assert perf.findChild(QLabel, "diagnosticsActionStatus").text() == "Timings and hidden-page skip counters cleared."


def test_phase17b_boundary_scan_no_new_runtime_or_capture_authority(tmp_path):
    _app()

    shell = _shell(tmp_path)
    text = _widget_text(shell)
    assert "Full Live Runtime Ready\ntrue" not in text
    assert "Full Live Runtime Ready true" not in text
    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Start Bridge",
        "Stop Bridge",
        "Restart Bridge",
        "Install Service",
        "Enable Auto Start",
    ):
        assert forbidden not in text

    source_paths = (
        PROJECT_ROOT / "v3_app" / "ui" / "shell.py",
        PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "effective_response_stack_page.py",
        PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py",
        PROJECT_ROOT / "v3_app" / "overlay" / "live_overlay_window.py",
        PROJECT_ROOT / "v3_app" / "services" / "perf_diagnostics.py",
    )
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
    for forbidden in (
        "keyboard.add_hotkey",
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "mss",
        "dxcam",
        "VideoWriter",
        "ffmpeg",
        "OpenAI(",
    ):
        assert forbidden not in sources


def test_phase17b_docs_explain_motion_performance_without_runtime_authority():
    from v3_app.services.help_docs import get_article

    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-17b-motion-performance-polish-report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    assert "Phase 17B" in report_text
    assert "Hidden-Page Skip Behavior" in report_text
    assert "Runtime Truth Preservation" in report_text
    assert "Recommendation For Phase 17C" in report_text

    phase_ledger = (PROJECT_ROOT / "docs" / "HelmForge" / "phase-ledger.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "HelmForge" / "bridge-ui-architecture.md").read_text(encoding="utf-8")
    runtime_setup = "\n".join(get_article("Runtime Setup / vJoy Setup").paragraphs)
    perf_docs = "\n".join(get_article("Performance / Diagnostics").paragraphs)
    for text in (phase_ledger, architecture, runtime_setup, perf_docs):
        assert "Phase 17B" in text
        assert "hardware polling" in text or "app diagnostics" in text or "app/UI diagnostics" in text
        assert "vJoy writes" in text or "not hardware or output proof" in text
