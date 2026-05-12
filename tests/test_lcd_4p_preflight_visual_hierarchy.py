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
        input=InputDeviceDetection(
            status=input_status,
            detected_device_names=("Thrustmaster T-Flight HOTAS One",)
            if input_status is InputStatus.DETECTED
            else (),
        ),
        output=OutputBackendDetection(
            status=output_status,
            backend_name="vJoy" if output_status is not OutputStatus.NOT_CHECKED else None,
            live_output_writes_verified=output_verified,
        ),
    )


def _state(runtime_status: RuntimePreflightStatus, *, active_page_id: str = "preflight", saved: bool = True):
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(runtime_status, active_page_id=active_page_id)
    state.active_profile = "LCD-4P Visual Fixture"
    state.source_config = "C:/Users/kkids/Documents/HOTAS-Control-Panel/configs/lcd_4p_extremely_long_workspace_config_name.json"
    state.saved = saved
    state.status_message = "Workspace ready."
    return state


def _texts(widget) -> list[str]:
    from PySide6.QtWidgets import QLabel, QPushButton

    return [label.text() for label in widget.findChildren(QLabel)] + [
        button.text() for button in widget.findChildren(QPushButton)
    ]


def _text_blob(widget) -> str:
    return "\n".join(_texts(widget))


def _has_ancestor(widget, ancestor) -> bool:
    current = widget.parentWidget()
    while current is not None:
        if current is ancestor:
            return True
        current = current.parentWidget()
    return False


def _preflight_page(shell):
    return shell.page_widgets["preflight.command_readiness"].widget()


def test_lcd_4p_preflight_page_has_dominant_go_no_go_hero_and_grouped_proofs():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.preflight_command_page import PreflightCommandPage

    runtime_status = _runtime_status()
    page = PreflightCommandPage(state=_state(runtime_status), runtime_status=runtime_status)
    page_text = _text_blob(page)

    hero = page.findChild(QWidget, "liquidPreflightHeroGoNoGo")
    proof_group = page.findChild(QWidget, "liquidPreflightHeroTruthChips")
    status_rail = page.findChild(QWidget, "liquidPreflightStatusRail")

    assert page.property("routeKey") == "preflight.command_readiness"
    assert hero is not None
    assert hero.property("preflightVisualRole") == "primary_go_no_go"
    assert hero.property("preflightHero") is True
    assert "Output proof missing" in page_text
    assert "Next: Confirm output proof exists." in page_text
    assert proof_group is not None
    assert proof_group.property("proofGroupLocation") == "hero"
    assert _has_ancestor(proof_group, hero)
    assert status_rail is not None
    assert status_rail.property("mergedIntoHero") is True


def test_lcd_4p_readiness_gates_are_scannable_without_losing_truth_distinctions():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.preflight_command_page import PreflightCommandPage

    runtime_status = _runtime_status()
    page = PreflightCommandPage(state=_state(runtime_status), runtime_status=runtime_status)

    for gate_label in ("Input", "Telemetry", "Workspace", "vJoy", "Output Proof", "Safety"):
        gates = [
            widget
            for widget in page.findChildren(QWidget)
            if widget.property("preflightGateLabel") == gate_label
        ]
        assert gates, gate_label
        assert gates[0].property("preflightGateVisual") == "compact_scan"

    assert page.findChild(QWidget, "liquidPreflightGate_vJoy").property("preflightGateState") == "ready"
    assert page.findChild(QWidget, "liquidPreflightGate_Output_Proof").property("preflightGateState") == "blocked"


def test_lcd_4p_system_details_and_checklist_use_grouped_action_structures():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.preflight_command_page import PreflightCommandPage

    runtime_status = _runtime_status()
    page = PreflightCommandPage(state=_state(runtime_status), runtime_status=runtime_status)

    details = page.findChild(QWidget, "liquidPreflightSystemDetails")
    checklist = page.findChild(QWidget, "liquidPreflightNextActions")
    groups = [widget for widget in details.findChildren(QWidget) if widget.property("systemDetailGroup") is True]
    action_rows = [widget for widget in checklist.findChildren(QWidget) if widget.property("preflightChecklistItem") is True]

    assert details is not None
    assert details.property("detailStructure") == "grouped_system_map"
    assert {group.property("systemGroupName") for group in groups} >= {
        "Input / Device",
        "Telemetry / Bridge",
        "Workspace / Config",
        "Output / vJoy",
        "Runtime / Safety",
    }
    assert checklist is not None
    assert checklist.property("checklistStructure") == "action_rows"
    assert len(action_rows) >= 8
    assert all(row.property("actionRowStyle") == "breathing" for row in action_rows)


def test_lcd_4p_advanced_diagnostics_are_secondary_and_footer_backplate_is_reduced():
    app = _app()

    from PySide6.QtWidgets import QScrollArea, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(_runtime_status()))
    shell.switch_route("preflight.command_readiness")
    shell.resize(1360, 800)
    shell.show()
    app.processEvents()

    page = _preflight_page(shell)
    advanced = page.findChild(QWidget, "liquidPreflightAdvancedDiagnostics")
    footer = shell.findChild(QWidget, "liquid_floating_footer_strip")
    clearance = shell.findChild(QWidget, "liquid_footer_clearance")
    scroll = shell.findChild(QScrollArea, "liquid_page_scroll_area")

    assert advanced is not None
    assert advanced.property("advancedSecondary") is True
    assert advanced.property("visualWeight") == "subdued"
    assert advanced.findChild(QWidget, "liquidPreflightAdvancedSummary") is not None
    assert footer is not None
    assert footer.property("floatingLayer") is True
    assert clearance is not None
    assert clearance.property("footerBackdrop") == "transparent_compact"
    assert 80 <= clearance.height() <= 92
    assert scroll is not None
    assert scroll.property("scrollbarStyle") == "liquid_subtle"


def test_lcd_4p_shell_top_bar_and_single_preflight_route_are_less_compressed():
    app = _app()

    from PySide6.QtWidgets import QLabel, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(_runtime_status()))
    shell.switch_route("preflight.command_readiness")
    shell.resize(1360, 800)
    shell.show()
    app.processEvents()

    source_chip = shell.findChild(QLabel, "liquidSourceChip")
    selector = shell.findChild(QWidget, "liquid_subpage_selector")
    command_cluster = shell.findChild(QWidget, "liquidTopCommandCluster")

    assert source_chip is not None
    assert source_chip.text() == "Source: Workspace Config"
    assert "lcd_4p_extremely_long_workspace_config_name.json" in source_chip.toolTip()
    assert source_chip.maximumWidth() <= 190
    assert selector is not None
    assert selector.property("singleRouteMode") is True
    assert selector.maximumHeight() <= 38
    assert "Preflight / Command Readiness" in _text_blob(selector)
    assert command_cluster is not None
    assert command_cluster.maximumWidth() <= 128


def test_lcd_4p_preflight_truth_and_lcd4f_render_coalescing_remain_intact(monkeypatch):
    app = _app()

    from PySide6.QtWidgets import QLabel
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.pages.preflight_command_page import PreflightCommandPage
    from tests.test_lcd_4f_interactive_startup_freeze import _telemetry

    runtime_status = _runtime_status(
        truth=RuntimeTruth.LIVE_VERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.OUTPUT_VERIFIED,
        output_verified=True,
    )
    render_count = {"count": 0}
    original_render = PreflightCommandPage._render

    def counted_render(self, *args, **kwargs):
        render_count["count"] += 1
        return original_render(self, *args, **kwargs)

    monkeypatch.setattr(PreflightCommandPage, "_render", counted_render)
    shell = LiquidCommandShell(state=_state(runtime_status))
    shell.switch_route("preflight.command_readiness")
    initial_render_count = render_count["count"]
    telemetry = _telemetry(
        truth=RuntimeTruth.LIVE_VERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.OUTPUT_VERIFIED,
        output_verified=True,
    )
    for _ in range(24):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()

    runtime_chip = shell.findChild(QLabel, "liquidRuntimeTruthChip")
    page_text = _text_blob(shell.page_host.currentWidget())

    assert runtime_chip is not None
    assert runtime_chip.text() == "Live Verified"
    assert "Ready for live output" in page_text
    assert "Output proof verified" in page_text
    assert "Output proof missing" not in page_text
    assert render_count["count"] <= initial_render_count + 1


def test_lcd_4p_sources_do_not_add_runtime_authority_effects_or_forbidden_claims():
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "v3_app" / "liquid").rglob("*.py")
    )

    for forbidden in (
        "QPropertyAnimation",
        "QGraphicsBlurEffect",
        "BridgeCommandClient",
        "EmbeddedBridgeRuntime",
        "build_runtime_preflight_status(",
        "save_workspace(",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
    ):
        assert forbidden.casefold() not in source_text.casefold()

    page = __import__(
        "v3_app.liquid.pages.preflight_command_page",
        fromlist=["PreflightCommandPage"],
    ).PreflightCommandPage(state=_state(_runtime_status()), runtime_status=_runtime_status())
    visible_text = _text_blob(page)

    for forbidden_claim in (
        "Live Output Active",
        "vJoy writing",
        "Bridge managed",
        "Recording Ready",
        "Capture active",
        "Auto-save",
    ):
        assert forbidden_claim.casefold() not in visible_text.casefold()


def test_lcd_4p_report_documents_visual_polish_scope_and_deferrals():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-4p-preflight-visual-hierarchy-polish-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-4P Preflight Visual Hierarchy and Layout Polish",
        "why LCD-4P was needed",
        "top command/status compression fix",
        "Preflight route strip/subpage selector weight fix",
        "page banding reduction",
        "hero hierarchy improvements",
        "readiness gate visual hierarchy improvements",
        "system details refinement",
        "checklist refinement",
        "advanced diagnostics secondary treatment",
        "footer background/scrim fix",
        "scrollbar/spacing/border hierarchy refinements",
        "truth consistency preservation",
        "LCD-4F freeze fix preservation",
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
