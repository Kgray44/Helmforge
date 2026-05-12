from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QPoint

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


def _runtime_status(
    *,
    truth: RuntimeTruth,
    input_status: InputStatus,
    output_status: OutputStatus,
    output_verified: bool,
    mode: RuntimeMode | None = None,
    backend_name: str | None = "vJoy",
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=mode
        or (
            RuntimeMode.FULL_LIVE
            if truth is RuntimeTruth.LIVE_VERIFIED and output_verified
            else RuntimeMode.SIMULATED
        ),
        truth=truth,
        input=InputDeviceDetection(
            status=input_status,
            detected_device_names=("Thrustmaster T-Flight HOTAS One",)
            if input_status is InputStatus.DETECTED
            else (),
        ),
        output=OutputBackendDetection(
            status=output_status,
            backend_name=backend_name,
            live_output_writes_verified=output_verified,
        ),
        warnings=warnings,
        errors=errors,
    )


def _state(runtime_status: RuntimePreflightStatus, *, saved: bool = True):
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(runtime_status, active_page_id="preflight")
    state.active_profile = "LCD-4 Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = saved
    state.status_message = "LCD-4 Preflight command page fixture."
    return state


def _texts(widget) -> list[str]:
    from PySide6.QtWidgets import QLabel, QPushButton

    return [label.text() for label in widget.findChildren(QLabel)] + [
        button.text() for button in widget.findChildren(QPushButton)
    ]


def _text_blob(widget) -> str:
    return "\n".join(_texts(widget))


def _rect_in_shell(widget, shell):
    top_left = widget.mapTo(shell, QPoint(0, 0))
    return widget.geometry().translated(top_left - widget.geometry().topLeft())


def _gate_by_label(model, label: str):
    for gate in model.readiness_gates:
        if gate.label == label:
            return gate
    raise AssertionError(f"Missing readiness gate: {label}")


def test_lcd_4_readiness_model_keeps_vjoy_detection_distinct_from_output_proof():
    from v3_app.liquid.models.preflight_readiness_model import build_preflight_readiness_model

    runtime_status = _runtime_status(
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        output_verified=False,
    )

    model = build_preflight_readiness_model(state=_state(runtime_status), runtime_status=runtime_status)

    assert model.overall_state == "blocked"
    assert model.overall_label == "Output proof missing"
    assert "vJoy is detected" in _gate_by_label(model, "vJoy").reason
    assert _gate_by_label(model, "vJoy").state == "ready"
    assert _gate_by_label(model, "Output Proof").state == "blocked"
    assert "Output proof missing" in _gate_by_label(model, "Output Proof").reason
    assert model.output_proof_label == "Output proof missing"
    assert model.overall_label != "Ready for live output"


def test_lcd_4_missing_hotas_and_simulation_are_truthful_non_ready_states():
    from v3_app.liquid.models.preflight_readiness_model import build_preflight_readiness_model

    missing_status = _runtime_status(
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input_status=InputStatus.MISSING,
        output_status=OutputStatus.VJOY_DETECTED,
        output_verified=False,
    )
    simulation_status = _runtime_status(
        truth=RuntimeTruth.SIMULATED,
        input_status=InputStatus.NOT_CHECKED,
        output_status=OutputStatus.NOT_CHECKED,
        output_verified=False,
        backend_name=None,
    )

    missing = build_preflight_readiness_model(state=_state(missing_status), runtime_status=missing_status)
    simulation = build_preflight_readiness_model(
        state=_state(simulation_status),
        runtime_status=simulation_status,
    )

    assert missing.overall_label == "HOTAS not connected"
    assert _gate_by_label(missing, "Input").state == "blocked"
    assert "Ready for live output" not in missing.overall_label

    assert simulation.overall_label == "Simulation mode"
    assert simulation.overall_state == "simulation"
    assert _gate_by_label(simulation, "Safety").state == "simulation"
    assert "Simulation mode" in simulation.short_explanation


def test_lcd_4_live_verified_fixture_aligns_hero_gates_and_top_bar_truth():
    from v3_app.liquid.models.preflight_readiness_model import build_preflight_readiness_model

    runtime_status = _runtime_status(
        truth=RuntimeTruth.LIVE_VERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.OUTPUT_VERIFIED,
        output_verified=True,
    )
    state = _state(runtime_status)

    model = build_preflight_readiness_model(state=state, runtime_status=runtime_status)

    assert state.runtime.header_truth_label == "Live Verified"
    assert model.overall_state == "ready"
    assert model.overall_label == "Ready for live output"
    assert model.runtime_truth_label == "Live Verified"
    assert model.output_proof_label == "Output proof verified"
    assert _gate_by_label(model, "Input").state == "ready"
    assert _gate_by_label(model, "Output Proof").state == "verified"
    assert _gate_by_label(model, "Safety").state == "safe"


def test_lcd_4_preflight_page_constructs_real_liquid_composition_offscreen():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.preflight_command_page import PreflightCommandPage

    runtime_status = _runtime_status(
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        output_verified=False,
    )
    page = PreflightCommandPage(state=_state(runtime_status), runtime_status=runtime_status)
    page_text = _text_blob(page)

    assert page.objectName() == "liquidPreflightCommandPage"
    assert page.property("routeKey") == "preflight.command_readiness"
    assert page.property("componentRole") == "PreflightCommandPage"
    assert page.findChild(QWidget, "liquidPreflightHeroGoNoGo") is not None
    assert page.findChild(QWidget, "liquidPreflightReadinessGates") is not None
    assert page.findChild(QWidget, "liquidPreflightSystemDetails") is not None
    assert page.findChild(QWidget, "liquidPreflightNextActions") is not None
    advanced = page.findChild(QWidget, "liquidPreflightAdvancedDiagnostics")
    assert advanced is not None
    assert advanced.property("advancedSecondary") is True

    for gate_label in ("Input", "Telemetry", "Workspace", "vJoy", "Output Proof", "Safety"):
        gate = [
            widget
            for widget in page.findChildren(QWidget)
            if widget.property("preflightGateLabel") == gate_label
        ]
        assert gate, gate_label

    assert "Can I safely use live output right now?" in page_text
    assert "Output proof missing" in page_text
    assert "Confirm output proof exists" in page_text
    assert "Legacy" not in page_text
    assert page.findChild(QWidget, "runtimeSetupGuideButton") is None


def test_lcd_4_route_registry_replaces_only_preflight_command_readiness():
    _app()

    from v3_app.liquid.pages.placeholder_pages import LIQUID_ROUTE_PAGE_FACTORIES

    preflight_page = LIQUID_ROUTE_PAGE_FACTORIES["preflight.command_readiness"]()
    mapping_page = LIQUID_ROUTE_PAGE_FACTORIES["mapping.hotas_map"]()

    assert preflight_page.objectName() == "liquidPreflightCommandPage"
    assert "Can I safely use live output right now?" in _text_blob(preflight_page)
    assert "Liquid Command Deck placeholder route" not in _text_blob(preflight_page)

    assert mapping_page.objectName() == "liquidPlaceholderPage_mapping_hotas_map"
    assert "Liquid Command Deck placeholder route" in _text_blob(mapping_page)


def test_lcd_4_shell_top_bar_and_preflight_page_do_not_contradict_live_verified_truth():
    _app()

    from PySide6.QtWidgets import QLabel
    from v3_app.liquid.app_shell import LiquidCommandShell

    runtime_status = _runtime_status(
        truth=RuntimeTruth.LIVE_VERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.OUTPUT_VERIFIED,
        output_verified=True,
    )
    shell = LiquidCommandShell(state=_state(runtime_status))
    shell.switch_route("preflight.command_readiness")
    page_text = _text_blob(shell.page_host.currentWidget())
    runtime_chip = shell.findChild(QLabel, "liquidRuntimeTruthChip")

    assert runtime_chip is not None
    assert runtime_chip.text() == "Live Verified"
    assert "Ready for live output" in page_text
    assert "Live Verified" in page_text
    assert "Output proof verified" in page_text
    assert "Output proof missing" not in page_text


def test_lcd_4_shell_top_bar_and_preflight_page_do_not_contradict_blocked_truth():
    _app()

    from PySide6.QtWidgets import QLabel
    from v3_app.liquid.app_shell import LiquidCommandShell

    runtime_status = _runtime_status(
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        output_verified=False,
    )
    shell = LiquidCommandShell(state=_state(runtime_status, saved=False))
    shell.switch_route("preflight.command_readiness")
    page_text = _text_blob(shell.page_host.currentWidget())
    runtime_chip = shell.findChild(QLabel, "liquidRuntimeTruthChip")

    assert runtime_chip is not None
    assert runtime_chip.text() == "Detected Unverified"
    assert "Output proof missing" in page_text
    assert "vJoy detected" in page_text
    assert "Ready for live output" not in page_text
    assert "Output proof verified" not in page_text


def test_lcd_4_preflight_page_preserves_footer_clearance_at_default_liquid_size():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    runtime_status = _runtime_status(
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input_status=InputStatus.MISSING,
        output_status=OutputStatus.VJOY_DETECTED,
        output_verified=False,
    )
    shell = LiquidCommandShell(state=_state(runtime_status))
    shell.switch_route("preflight.command_readiness")
    shell.resize(1360, 800)
    shell.show()
    app.processEvents()

    footer = shell.findChild(QWidget, "liquid_floating_footer_strip")
    page_host = shell.findChild(QWidget, "liquid_page_host")
    clearance = shell.findChild(QWidget, "liquid_footer_clearance")

    assert footer is not None
    assert page_host is not None
    assert clearance is not None
    assert clearance.property("footerClearance") is True
    assert _rect_in_shell(page_host, shell).bottom() <= _rect_in_shell(footer, shell).top() + 4


def test_lcd_4_liquid_sources_do_not_introduce_runtime_authority_or_forbidden_claims():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    runtime_status = _runtime_status(
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input_status=InputStatus.MISSING,
        output_status=OutputStatus.VJOY_DETECTED,
        output_verified=False,
    )
    shell = LiquidCommandShell(state=_state(runtime_status))
    visible_text = _text_blob(shell)
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "v3_app" / "liquid").rglob("*.py")
    )

    for forbidden in (
        "from v3_app.ui.shell import HelmForgeShell",
        "from v3_app.pages.preflight_page",
        "build_runtime_preflight_status(",
        "BridgeCommandClient",
        "EmbeddedBridgeRuntime",
        "save_workspace(",
        "QPropertyAnimation",
        "QGraphicsBlurEffect",
        "QGraphicsOpacityEffect",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
    ):
        assert forbidden.casefold() not in source_text.casefold()

    for forbidden_claim in (
        "Live Output Active",
        "vJoy writing",
        "Bridge managed",
        "Recording Ready",
        "Capture active",
        "Auto-save",
    ):
        assert forbidden_claim.casefold() not in visible_text.casefold()


def test_lcd_4_report_documents_scope_truth_and_deferrals():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-4-preflight-command-page-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-4 Preflight Command Page",
        "Preflight page architecture",
        "route replaced",
        "readiness model",
        "actual truth data surfaces used",
        "hero go/no-go behavior",
        "readiness gates",
        "system details",
        "checklist behavior",
        "advanced diagnostics",
        "truth consistency with top bar",
        "layout/overlap preservation",
        "Legacy fallback/reference is preserved",
        "LCD-5 through LCD-12",
        "runtime truth preservation",
        "no Mapping page was rebuilt",
        "no Tuning page was rebuilt",
        "no Analysis/Live Monitor page was rebuilt",
        "no Recorder/Helm page was rebuilt",
        "no Support/Diagnostics page was rebuilt",
        "no radial menu behavior was added",
        "no animations were added",
        "no page transitions were added",
        "no real blur/distortion was added",
        "no runtime authority was changed",
        "no hardware polling was changed",
        "no vJoy/output behavior was changed",
        "no output verification behavior was changed",
        "no Bridge lifecycle management was added",
        "no recorder capture/encoding was added",
        "no cloud AI/LLM behavior was added",
        "no auto-save was added",
    ):
        assert required in text
