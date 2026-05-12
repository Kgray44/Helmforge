from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from shared_core.models.runtime import (
    AXIS_NAMES,
    BUTTON_NAMES,
    InputStatus,
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
ANALYSIS_ROUTES = ("analysis.effective_response_stack", "analysis.live_monitor")


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _state(*, active_page_id: str = "effective_response_stack", truth: RuntimeTruth = RuntimeTruth.SIMULATED):
    from shared_core.models.runtime import InputDeviceDetection, OutputBackendDetection
    from v3_app.services.app_state import AppState

    output_verified = truth is RuntimeTruth.LIVE_VERIFIED
    runtime_status = RuntimePreflightStatus(
        mode=RuntimeMode.FULL_LIVE if output_verified else RuntimeMode.SIMULATED,
        truth=truth,
        input=InputDeviceDetection(status=InputStatus.DETECTED),
        output=OutputBackendDetection(
            status=OutputStatus.OUTPUT_VERIFIED if output_verified else OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=output_verified,
        ),
    )
    state = AppState.from_runtime_status(runtime_status, active_page_id=active_page_id)
    state.active_profile = "LCD-7 Fixture"
    state.status_message = "Workspace ready."
    return state


def _telemetry(
    *,
    truth: RuntimeTruth = RuntimeTruth.SIMULATED,
    output_verified: bool = False,
    stale: bool = False,
    missing_values: bool = False,
) -> BridgeTelemetrySnapshot:
    timestamp = datetime.now(timezone.utc) - (timedelta(seconds=12) if stale else timedelta(milliseconds=100))
    raw_axes = {} if missing_values else {axis: (index - 2) / 5 for index, axis in enumerate(AXIS_NAMES)}
    final_axes = {} if missing_values else {axis: value * 0.8 for axis, value in raw_axes.items()}
    runtime_frame = {
        "telemetry_proof": "stale" if stale else "fresh",
        "input_stale": stale,
        "ready_state": "verified" if output_verified else "blocked",
        "output_proof": "verified" if output_verified else "missing",
        "source_label": "Bridge telemetry",
    }
    return BridgeTelemetrySnapshot(
        runtime_truth=truth,
        lifecycle_state=BridgeLifecycleState.LIVE_VERIFIED if output_verified else BridgeLifecycleState.SIMULATED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.OUTPUT_VERIFIED if output_verified else OutputStatus.VJOY_DETECTED,
        raw_axes=AxisTelemetrySnapshot(raw_axes),
        final_axes=AxisTelemetrySnapshot(final_axes),
        controls=ButtonHatTelemetrySnapshot(
            buttons={button: index in {0, 3, 14} for index, button in enumerate(BUTTON_NAMES)},
            hats={"POV": "Up"},
        ),
        active_modes=ModeStateTelemetrySnapshot(combat_active=True, active_mode_names=("Combat",)),
        timestamp=timestamp,
        active_profile="LCD-7 Fixture",
        rule_summary=RuleStateSummary(active_count=1, blocked_count=0, disabled_count=1),
        output_verification=OutputVerificationState(
            verified=output_verified,
            backend_name="vJoy",
            message="Verified by existing runtime proof." if output_verified else "Output proof missing.",
        ),
        runtime_frame=runtime_frame,
    )


def _text_blob(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join(labels + buttons)


def test_lcd_7_analysis_model_builds_pipeline_and_live_monitor_from_passive_snapshot():
    from v3_app.liquid.models.analysis_command_model import build_analysis_command_model

    model = build_analysis_command_model(
        route_key="analysis.effective_response_stack",
        workspace=create_default_workspace(),
        state=_state(),
        telemetry=_telemetry(),
        selected_axis="Roll",
    )
    stage_names = [stage.stage_name for stage in model.pipeline_stages]

    assert model.axis_options == ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
    assert model.selected_axis == "Roll"
    assert stage_names == [
        "Raw Input",
        "Base Tuning",
        "Filtering",
        "Modes / Combat Profile",
        "Conditional Rules",
        "Final Output Intent",
    ]
    assert model.output_proof_label == "Output proof missing"
    assert any(stage.stage_name == "Final Output Intent" and "Output Intent" in stage.stage_summary for stage in model.pipeline_stages)
    assert {axis.axis_name for axis in model.axis_monitors} == set(AXIS_NAMES)
    assert {button.label for button in model.buttons} == set(BUTTON_NAMES)
    assert model.hat_label == "Hat / POV: Up"
    assert "Output proof is separate from output intent." in model.truth_source_notes


def test_lcd_7_analysis_routes_map_to_real_pages_not_placeholders():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    for route_key in ANALYSIS_ROUTES:
        shell.switch_route(route_key)
        app.processEvents()
        page = shell.page_widgets[route_key].widget()
        text = _text_blob(page)

        assert page.objectName() == "liquidAnalysisCommandPage"
        assert page.property("routeKey") == route_key
        assert "Liquid Command Deck placeholder" not in text
        assert "Placeholder route" not in text
        assert page.findChild(QWidget, "liquidAnalysisAdvancedDetails") is not None
        assert page.findChild(QWidget, "liquidAnalysisFreshnessRail") is not None


def test_lcd_7_effective_response_stack_page_contains_pipeline_axis_selector_and_truth_labels():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    page = AnalysisCommandPage(
        route_key="analysis.effective_response_stack",
        state=_state(),
        workspace=create_default_workspace(),
        telemetry=_telemetry(),
    )
    text = _text_blob(page)
    stages = [widget for widget in page.findChildren(QWidget) if widget.property("analysisPipelineStage") is True]

    assert page.findChild(QWidget, "liquidAnalysisPipelineHero") is not None
    assert page.findChild(QWidget, "liquidAnalysisAxisSelector") is not None
    assert len(stages) >= 6
    for label in ("Raw Input", "Base Tuning", "Filtering", "Modes / Combat Profile", "Conditional Rules", "Final Output Intent"):
        assert label in text
    assert "Output Intent" in text
    assert "Output proof missing" in text
    assert "output verified" not in text.casefold()

    page.select_axis("Yaw")
    assert page.property("selectedAxis") == "Yaw"
    assert "Axis: Yaw" in _text_blob(page)


def test_lcd_7_live_monitor_page_contains_axis_button_hat_instruments_and_freshness():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    page = AnalysisCommandPage(
        route_key="analysis.live_monitor",
        state=_state(active_page_id="live_monitor"),
        workspace=create_default_workspace(),
        telemetry=_telemetry(),
    )
    text = _text_blob(page)

    assert page.findChild(QWidget, "liquidAnalysisLiveMonitorHero") is not None
    assert page.findChild(QWidget, "liquidAnalysisAxisInstrumentPanel") is not None
    assert page.findChild(QWidget, "liquidAnalysisButtonGrid") is not None
    assert page.findChild(QWidget, "liquidAnalysisHatIndicator") is not None
    assert page.findChild(QWidget, "liquidAnalysisFreshnessRail") is not None
    for axis in AXIS_NAMES:
        assert axis in text
    assert "B1" in text
    assert "B15" in text
    assert "Hat / POV: Up" in text
    assert "Telemetry fresh" in text


def test_lcd_7_stale_missing_and_simulation_truth_are_explicit():
    from v3_app.liquid.models.analysis_command_model import build_analysis_command_model

    missing = build_analysis_command_model(
        route_key="analysis.live_monitor",
        workspace=create_default_workspace(),
        state=_state(),
        telemetry=None,
    )
    stale = build_analysis_command_model(
        route_key="analysis.live_monitor",
        workspace=create_default_workspace(),
        state=_state(),
        telemetry=_telemetry(stale=True),
    )
    unavailable = build_analysis_command_model(
        route_key="analysis.effective_response_stack",
        workspace=create_default_workspace(),
        state=_state(),
        telemetry=_telemetry(missing_values=True),
    )

    assert missing.telemetry_label == "Telemetry missing"
    assert missing.sample_truth_label == "Current sample unavailable"
    assert "Simulation mode" in missing.source_label
    assert stale.telemetry_label == "Telemetry stale"
    assert "stale" in stale.sample_truth_label.casefold()
    assert any("unavailable" in stage.value_text.casefold() for stage in unavailable.pipeline_stages)


def test_lcd_7_live_verified_fixture_keeps_output_intent_and_output_proof_separate():
    from v3_app.liquid.models.analysis_command_model import build_analysis_command_model

    model = build_analysis_command_model(
        route_key="analysis.effective_response_stack",
        workspace=create_default_workspace(),
        state=_state(truth=RuntimeTruth.LIVE_VERIFIED),
        telemetry=_telemetry(truth=RuntimeTruth.LIVE_VERIFIED, output_verified=True),
    )

    assert model.runtime_truth_label == "Live Verified"
    assert model.output_proof_label == "Output proof verified"
    assert any(stage.stage_name == "Final Output Intent" for stage in model.pipeline_stages)
    assert all(stage.stage_name != "Output Proof" for stage in model.pipeline_stages)
    assert model.output_proof_role == "verified"


def test_lcd_7_shell_updates_visible_analysis_only_and_keeps_hidden_pages_coalesced(monkeypatch):
    app = _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.pages.analysis_command_pages import AnalysisCommandPage

    render_count = {"count": 0}
    original_render = AnalysisCommandPage._render

    def counted_render(self, *args, **kwargs):
        render_count["count"] += 1
        return original_render(self, *args, **kwargs)

    monkeypatch.setattr(AnalysisCommandPage, "_render", counted_render)
    shell = LiquidCommandShell(state=_state(active_page_id="base_tuning"))
    shell.switch_route("tuning.base_tuning")
    hidden_renders = render_count["count"]
    telemetry = _telemetry()

    for _ in range(8):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()

    assert render_count["count"] == hidden_renders

    shell.switch_route("analysis.live_monitor")
    visible_start = render_count["count"]
    for _ in range(8):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()

    assert shell.current_route_key == "analysis.live_monitor"
    assert render_count["count"] <= visible_start + 2


def test_lcd_7_existing_preflight_mapping_and_tuning_routes_still_work():
    app = _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    expected = {
        "preflight.command_readiness": "liquidPreflightCommandPage",
        "mapping.hotas_map": "liquidMappingCommandPage",
        "tuning.base_tuning": "liquidTuningCommandPage",
    }
    for route_key, object_name in expected.items():
        shell.switch_route(route_key)
        app.processEvents()
        assert shell.page_widgets[route_key].widget().objectName() == object_name


def test_lcd_7_sources_preserve_runtime_boundaries_and_forbidden_claims():
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "analysis_command_pages.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "models" / "analysis_command_model.py",
        )
        if path.exists()
    )

    for forbidden in (
        "from v3_app.pages.live_monitor_page",
        "from v3_app.pages.effective_response_stack_page",
        "BridgeTelemetryClient",
        "BridgeCommandClient",
        "EmbeddedBridgeRuntime",
        "build_runtime_preflight_status(",
        "PhysicalInputBackend",
        "VirtualOutputWriteLoop",
        "verify_output_write",
        "write_output",
        "QPropertyAnimation",
        "QGraphicsBlurEffect",
        "QTimer",
        "auto_save",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
    ):
        assert forbidden.casefold() not in source_text.casefold()


def test_lcd_7_report_documents_analysis_scope_and_truth_boundaries():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-7-analysis-command-pages-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-7 Analysis Command Pages",
        "routes implemented",
        "Analysis page architecture",
        "Effective Response Stack page behavior",
        "Live Monitor page behavior",
        "analysis/live monitor presentation model structure",
        "data surfaces used",
        "passive telemetry behavior",
        "stale/missing/simulation truth behavior",
        "pipeline stage behavior",
        "axis/button/hat instrument behavior",
        "advanced raw details behavior",
        "output intent differs from output proof",
        "hidden-route rebuild protection",
        "Legacy fallback/reference is preserved",
        "limitations/deferred live motion features",
        "runtime truth preservation statement",
        "no Recorder/Helm page was rebuilt",
        "no Support/Diagnostics page was rebuilt",
        "no radial menu behavior was added",
        "no animations were added",
        "no page transitions were added",
        "no live data easing was added",
        "no real blur/distortion was added",
        "no runtime authority was changed",
        "no hardware polling was changed",
        "no vJoy/output behavior was changed",
        "no output verification behavior was changed",
        "no Bridge lifecycle management was added",
        "no recorder capture/encoding was added",
        "no cloud AI/LLM behavior was added",
        "no auto-save was added",
        "analysis pages are passive/read-only visualizations of existing state",
    ):
        assert required in text
