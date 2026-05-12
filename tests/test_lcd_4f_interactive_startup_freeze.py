from __future__ import annotations

import os
import time
from datetime import datetime, timezone
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
from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState
from shared_core.runtime.telemetry import (
    AxisTelemetrySnapshot,
    BridgeTelemetrySnapshot,
    ButtonHatTelemetrySnapshot,
    ModeStateTelemetrySnapshot,
    OutputVerificationState,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
        mode=RuntimeMode.FULL_LIVE
        if truth is RuntimeTruth.LIVE_VERIFIED and output_verified
        else RuntimeMode.SIMULATED,
        truth=truth,
        input=InputDeviceDetection(status=input_status),
        output=OutputBackendDetection(
            status=output_status,
            backend_name="vJoy" if output_status is not OutputStatus.NOT_CHECKED else None,
            live_output_writes_verified=output_verified,
        ),
    )


def _state(runtime_status: RuntimePreflightStatus, *, active_page_id: str = "mapping"):
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(runtime_status, active_page_id=active_page_id)
    state.active_profile = "LCD-4F Stability Fixture"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = True
    return state


def _telemetry(
    *,
    truth: RuntimeTruth = RuntimeTruth.DETECTED_UNVERIFIED,
    input_status: InputStatus = InputStatus.DETECTED,
    output_status: OutputStatus = OutputStatus.VJOY_DETECTED,
    output_verified: bool = False,
) -> BridgeTelemetrySnapshot:
    return BridgeTelemetrySnapshot(
        runtime_truth=truth,
        lifecycle_state=BridgeLifecycleState.LIVE_VERIFIED
        if truth is RuntimeTruth.LIVE_VERIFIED and output_verified
        else BridgeLifecycleState.LIVE_UNVERIFIED,
        input_status=input_status,
        output_status=output_status,
        raw_axes=AxisTelemetrySnapshot({"roll": 0.0, "pitch": 0.0}),
        final_axes=AxisTelemetrySnapshot({"roll": 0.0, "pitch": 0.0}),
        controls=ButtonHatTelemetrySnapshot(),
        active_modes=ModeStateTelemetrySnapshot(),
        timestamp=datetime.now(timezone.utc),
        active_profile="LCD-4F Stability Fixture",
        output_verification=OutputVerificationState(
            verified=output_verified,
            backend_name="vJoy" if output_status is not OutputStatus.NOT_CHECKED else None,
        ),
        runtime_frame={
            "runtime_truth": truth.value,
            "telemetry_proof": "fresh",
            "output_proof": "verified" if output_verified else "missing",
            "safety_proof": "ready" if output_verified else "blocked",
            "full_live_runtime_ready": bool(truth is RuntimeTruth.LIVE_VERIFIED and output_verified),
            "ready_state": "ready" if output_verified else "blocked",
        },
    )


def _preflight_page(shell):
    preflight_scroll = shell.page_widgets["preflight.command_readiness"]
    return preflight_scroll.widget()


def test_lcd_4f_hidden_preflight_route_does_not_rebuild_on_telemetry_burst(monkeypatch):
    app = _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.pages.preflight_command_page import PreflightCommandPage

    render_count = {"count": 0}
    original_render = PreflightCommandPage._render

    def counted_render(self, *args, **kwargs):
        render_count["count"] += 1
        return original_render(self, *args, **kwargs)

    monkeypatch.setattr(PreflightCommandPage, "_render", counted_render)
    shell = LiquidCommandShell(state=_state(_runtime_status(), active_page_id="mapping"))
    assert shell.current_route_key == "mapping.hotas_map"
    preflight_page = _preflight_page(shell)
    initial_render_count = render_count["count"]

    telemetry = _telemetry()
    for _ in range(40):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()

    assert shell.current_route_key == "mapping.hotas_map"
    assert _preflight_page(shell) is preflight_page
    assert render_count["count"] == initial_render_count


def test_lcd_4f_active_preflight_route_coalesces_equivalent_telemetry_frames(monkeypatch):
    app = _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.pages.preflight_command_page import PreflightCommandPage

    render_count = {"count": 0}
    original_render = PreflightCommandPage._render

    def counted_render(self, *args, **kwargs):
        render_count["count"] += 1
        return original_render(self, *args, **kwargs)

    monkeypatch.setattr(PreflightCommandPage, "_render", counted_render)
    shell = LiquidCommandShell(state=_state(_runtime_status(), active_page_id="preflight"))
    shell.switch_route("preflight.command_readiness")
    preflight_page = _preflight_page(shell)
    initial_render_count = render_count["count"]

    telemetry = _telemetry()
    started = time.perf_counter()
    for _ in range(40):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()
    elapsed = time.perf_counter() - started

    assert shell.current_route_key == "preflight.command_readiness"
    assert _preflight_page(shell) is preflight_page
    assert render_count["count"] <= initial_render_count + 1
    assert elapsed < 2.0


def test_lcd_4f_liquid_event_loop_stays_responsive_with_preflight_active():
    app = _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(_runtime_status(), active_page_id="preflight"))
    shell.switch_route("preflight.command_readiness")
    telemetry = _telemetry()

    deadline = time.perf_counter() + 0.6
    iterations = 0
    while time.perf_counter() < deadline:
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()
        iterations += 1

    assert iterations > 1
    assert shell.current_route_key == "preflight.command_readiness"
    assert shell.page_host.currentWidget() is shell.page_widgets["preflight.command_readiness"]


def test_lcd_4f_preflight_construction_uses_passive_sources_only():
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "preflight_command_page.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "models" / "preflight_readiness_model.py",
        )
    )

    for forbidden in (
        "build_runtime_preflight_status(",
        "BridgeCommandClient",
        "EmbeddedBridgeRuntime",
        "subprocess",
        ".sleep(",
        "QTimer(",
    ):
        assert forbidden.casefold() not in source_text.casefold()


def test_lcd_4f_report_documents_root_cause_fix_and_scope_boundaries():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-4f-interactive-freeze-triage-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-4F Interactive Startup Freeze Triage and Fix",
        "Freeze Symptoms",
        "Suspected Root Cause",
        "Actual Root Cause Found",
        "Files Changed",
        "Fix Applied",
        "Why Smokes Missed It",
        "Regression Test Added",
        "Runtime Truth Preservation",
        "does not change runtime authority",
        "No Mapping page was rebuilt",
        "No Tuning page was rebuilt",
        "No Analysis or Live Monitor page was rebuilt",
        "No Recorder, Helm, Support, or Diagnostics page was rebuilt",
        "No radial menu behavior was added",
        "No animations were added",
        "No page transitions were added",
        "No real blur or distortion was added",
        "No hardware polling behavior was changed",
        "No vJoy/output behavior was changed",
        "No output verification behavior was changed",
        "No Bridge lifecycle management was added",
        "No recorder capture/encoding was added",
        "No cloud AI/LLM behavior was added",
        "No auto-save was added",
    ):
        assert required in text
