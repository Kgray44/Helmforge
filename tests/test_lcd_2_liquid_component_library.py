from __future__ import annotations

import os
from pathlib import Path

import pytest

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
    )


def _state():
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(_runtime_status())
    state.active_profile = "LCD-2 Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = False
    state.status_message = "LCD-2 component library loaded; actions remain placeholders."
    return state


def _texts(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join(labels + buttons)


def _component_roles(widget) -> set[str]:
    from PySide6.QtWidgets import QWidget

    return {
        child.property("componentRole")
        for child in widget.findChildren(QWidget)
        if child.property("componentRole")
    }


def test_lcd_2_layout_components_construct_offscreen_and_expose_regions():
    _app()

    from v3_app.liquid.components import (
        LiquidAdvancedSection,
        LiquidCommandSurfaceSection,
        LiquidDetailPanel,
        LiquidFloatingPanel,
        LiquidGlassCapsule,
        LiquidHeroPanel,
        LiquidInspectorPanel,
        LiquidInstrumentPanel,
        LiquidPage,
        LiquidPageHeader,
        LiquidSplitPanel,
        LiquidStatusRail,
    )

    page = LiquidPage(
        title="Mapping",
        subtitle="Physical controls to mapping intent.",
        helper_text="LCD-2 static composition only.",
        object_name="testLiquidPage",
    )
    page.set_header(LiquidPageHeader("Mapping", "Route intent", "LIQUID COMMAND DECK"))
    page.set_hero(LiquidHeroPanel("HOTAS Visual Map", "Read-only placeholder instrument."))
    page.set_inspector(LiquidInspectorPanel("Selected Control", "Inspector seam."))
    page.set_detail(LiquidDetailPanel("Route Details", "Detail/action seam."))
    page.set_advanced(LiquidAdvancedSection("Advanced Route Tables", "Secondary diagnostics seam."))
    page.set_status_rail(LiquidStatusRail(items=(("Workspace loaded", "info"), ("Output proof missing", "blocked"))))

    split = LiquidSplitPanel(left=LiquidInstrumentPanel("Axis Instrument"), right=LiquidInspectorPanel("Context"))
    section = LiquidCommandSurfaceSection("Command Surface Section")
    floating = LiquidFloatingPanel("Floating HUD")
    capsule = LiquidGlassCapsule("Output intent", state_role="info")

    assert page.objectName() == "testLiquidPage"
    assert page.property("componentRole") == "LiquidPage"
    assert page.property("liquidRole") == "liquid_page"
    assert split.property("componentRole") == "LiquidSplitPanel"
    assert section.property("componentRole") == "LiquidCommandSurfaceSection"
    assert floating.property("floatingLayer") is True
    assert capsule.property("statusRole") == "info"
    for role in (
        "LiquidPageHeader",
        "LiquidHeroPanel",
        "LiquidInspectorPanel",
        "LiquidDetailPanel",
        "LiquidAdvancedSection",
        "LiquidStatusRail",
    ):
        assert role in _component_roles(page)


def test_lcd_2_status_components_use_consistent_roles_without_ready_disabled_states():
    _app()

    from v3_app.liquid.status_components import (
        DraftStateIndicator,
        MetricTile,
        ReadinessGate,
        StatusChip,
        TelemetryFreshnessRail,
        TruthBadge,
        status_tone_for_role,
    )

    expected_tones = {
        "ready": "success",
        "verified": "success",
        "saved": "success",
        "safe": "success",
        "waiting": "warning",
        "blocked": "warning",
        "attention": "warning",
        "unsaved": "warning",
        "error": "danger",
        "unsafe": "danger",
        "failed": "danger",
        "info": "info",
        "simulation": "info",
        "live-neutral": "info",
        "disabled": "disabled",
        "unavailable": "disabled",
    }
    for role, tone in expected_tones.items():
        chip = StatusChip(f"{role} state", state_role=role)
        assert chip.property("statusRole") == role
        assert chip.property("toneRole") == tone
        assert status_tone_for_role(role) == tone

    unavailable = StatusChip("Capture backend unavailable", state_role="unavailable")
    assert unavailable.property("toneRole") == "disabled"
    assert "ready" not in unavailable.text().casefold()

    gate = ReadinessGate(
        "Output proof",
        state_text="Output proof missing",
        state_role="blocked",
        detail="No write proof is asserted by LCD-2 components.",
    )
    gate_text = _texts(gate)
    assert gate.property("componentRole") == "ReadinessGate"
    assert "Output proof missing" in gate_text
    assert "Output Verified".casefold() not in gate_text.casefold()
    assert "Full Live Runtime Ready".casefold() not in gate_text.casefold()

    widgets = (
        TruthBadge("Runtime blocked", state_role="blocked"),
        MetricTile("Axis routes", "6", "mapping intent", state_role="info"),
        DraftStateIndicator("Draft change staged", state_role="unsaved"),
        TelemetryFreshnessRail("Telemetry stale", state_role="waiting", source_label="Simulation mode"),
    )
    assert {widget.property("componentRole") for widget in widgets} == {
        "TruthBadge",
        "MetricTile",
        "DraftStateIndicator",
        "TelemetryFreshnessRail",
    }


def test_lcd_2_flow_components_preserve_output_intent_and_static_checklists():
    _app()

    from v3_app.liquid.flow_components import ChecklistPanel, RouteFlowRow, SignalPipelineStage

    flow = RouteFlowRow(
        source_label="Physical Stick X",
        function_label="Roll",
        target_label="vJoy X",
        status_role="waiting",
        helper_text="Output proof missing.",
    )
    stage = SignalPipelineStage(
        "Base Tuning",
        "Transforms raw input with workspace parameters.",
        selected_value="Roll selected",
        status_role="simulation",
        warning_text="Read-only visualization.",
    )
    checklist = ChecklistPanel(
        "Next Actions",
        items=(
            ("Workspace loaded", "done", "Static state only."),
            ("Confirm input sample", "waiting", "Telemetry missing."),
            ("Capture backend", "unavailable", "Capture backend unavailable."),
        ),
    )

    assert "Physical Stick X" in _texts(flow)
    assert "Output Intent: vJoy X" in _texts(flow)
    assert flow.property("statusRole") == "waiting"
    assert "Read-only visualization" in _texts(stage)
    assert "Capture backend unavailable" in _texts(checklist)
    assert checklist.property("componentRole") == "ChecklistPanel"


def test_lcd_2_parameter_and_inspector_components_are_metadata_ready_and_validating():
    _app()

    from v3_app.liquid.parameter_controls import (
        AXIS_SELECTOR_OPTIONS,
        AxisSelectorPills,
        DropdownParameterControl,
        GuidanceBlock,
        LiveSnapshotBlock,
        NumericParameterControl,
        ParameterLabelWithInfo,
        ParameterRow,
    )

    label = ParameterLabelWithInfo(
        "Curve Strength",
        help_text="Higher values soften center response.",
        metadata={"unit": "%", "description": "Metadata-backed help seam."},
    )
    numeric = NumericParameterControl(value=0.34, min_value=0.0, max_value=1.0, decimals=2)
    row = ParameterRow(
        label="Curve Strength",
        control=numeric,
        unit_text="ratio",
        status_note="Draft change staged",
        changed=True,
        help_text="Inspector metadata seam.",
    )
    dropdown = DropdownParameterControl(options=("Linear", "Expo"), selected="Expo")
    axes = AxisSelectorPills(selected_axis="Roll")
    guidance = GuidanceBlock(
        current_feel="Smooth center, crisp edge.",
        affects="Response curve shape.",
        suggested_range="0.20 to 0.60",
        caution="Do not infer live output from preview.",
        selected_axis_note="Roll selected.",
    )
    snapshot = LiveSnapshotBlock(
        selected_control="Roll",
        source_truth_label="Simulation mode",
        raw_value="0.00",
        output_intent_value="Output Intent: vJoy X",
        state_role="simulation",
    )

    assert label.toolTip()
    assert row.property("changed") is True
    assert numeric.numeric_value() == pytest.approx(0.34)
    numeric.setText("not-a-number")
    assert numeric.numeric_value() is None
    assert numeric.property("validationState") == "invalid"
    assert dropdown.selected_value() == "Expo"
    with pytest.raises(ValueError):
        dropdown.set_selected_value("Unsupported Mode")
    assert tuple(axes.option_labels()) == AXIS_SELECTOR_OPTIONS
    assert axes.selected_axis() == "Roll"
    for required in ("Current feel", "What this affects", "Suggested range", "Caution", "Selected axis note"):
        assert required in _texts(guidance)
    assert "Simulation mode" in _texts(snapshot)
    assert "Output Intent: vJoy X" in _texts(snapshot)


def test_lcd_2_static_instrument_placeholders_construct_without_live_claims():
    _app()

    from v3_app.liquid.instruments import (
        AxisBar,
        AxisBarPair,
        ButtonIlluminationGrid,
        CapabilityRail,
        ControlMarker,
        HatDirectionIndicator,
        MiniCurvePreview,
    )

    widgets = (
        AxisBar("Roll", value=0.25, state_role="simulation"),
        AxisBarPair("Roll", raw_value=0.20, output_intent_value=0.18, state_role="simulation"),
        ButtonIlluminationGrid(buttons=("A", "B", "C"), active_buttons=("B",), state_role="simulation"),
        HatDirectionIndicator(selected_direction="Neutral", state_role="unavailable"),
        ControlMarker("Stick X", "Mapping intent", state_role="info"),
        MiniCurvePreview("Curve preview", state_role="simulation"),
        CapabilityRail(
            capabilities=(
                ("Capture backend", "unavailable", "Capture backend unavailable"),
                ("Metadata", "info", "Metadata-only artifact"),
            )
        ),
    )

    assert {widget.property("componentRole") for widget in widgets} == {
        "AxisBar",
        "AxisBarPair",
        "ButtonIlluminationGrid",
        "HatDirectionIndicator",
        "ControlMarker",
        "MiniCurvePreview",
        "CapabilityRail",
    }
    text = "\n".join(_texts(widget) for widget in widgets)
    for forbidden in ("live output active", "recording ready", "HOTAS connected", "vJoy writing"):
        assert forbidden not in text.casefold()


def test_lcd_2_placeholder_pages_demonstrate_representative_components_truthfully():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    expected_roles = {
        "preflight": {"ReadinessGate", "StatusChip", "ChecklistPanel"},
        "mapping": {"RouteFlowRow", "MappingHotasVisualMap", "MetricTile"},
        "tuning": {"AxisSelectorPills", "ParameterRow", "GuidanceBlock"},
        "analysis": {"SignalPipelineStage", "LiveSnapshotBlock", "TelemetryFreshnessRail"},
        "recorder": {"TruthBadge", "CapabilityRail", "MetricTile"},
        "support": {"LiquidAdvancedSection", "GuidanceBlock", "MetricTile"},
    }

    for mode_id, roles in expected_roles.items():
        shell.switch_mode(mode_id)
        page = shell.page_host.currentWidget()
        page_text = _texts(page)
        if mode_id == "preflight":
            assert "Command Readiness" in page_text
            assert "Can I safely use live output right now?" in page_text
            assert "Liquid Command Deck placeholder" not in page_text
        elif mode_id == "mapping":
            assert "HOTAS Map" in page_text
            assert "What is each physical control doing?" in page_text
            assert "Liquid Command Deck placeholder" not in page_text
        elif mode_id == "tuning":
            assert "Base Tuning" in page_text
            assert "How does this axis respond and feel?" in page_text
            assert "Liquid Command Deck placeholder" not in page_text
        elif mode_id == "analysis":
            assert "Effective Response Stack" in page_text
            assert "How does raw input become final output?" in page_text
            assert "Liquid Command Deck placeholder" not in page_text
        elif mode_id == "recorder":
            assert "Flight Recorder" in page_text
            assert "What can I capture, buffer, and review?" in page_text
            assert "Liquid Command Deck placeholder" not in page_text
        else:
            assert "Liquid Command Deck placeholder" in page_text
        assert roles <= _component_roles(page)

        for forbidden in (
            "Live Output Active",
            "Full Live Runtime Ready",
            "Recording Ready",
            "HOTAS connected",
            "vJoy writing",
            "Bridge managed",
            "auto-save",
        ):
            assert forbidden.casefold() not in page_text.casefold()


def test_lcd_2_preserves_floating_shell_names_and_avoids_forbidden_architecture():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    for object_name in (
        "liquid_command_surface",
        "liquid_surface_glass_field",
        "liquid_floating_mode_dock",
        "liquid_floating_footer_strip",
        "liquid_page_host",
    ):
        assert shell.findChild(QWidget, object_name) is not None

    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "v3_app" / "liquid").rglob("*.py")
    )
    for forbidden in (
        "from v3_app.ui.shell import HelmForgeShell",
        "from v3_app.pages.mapping_page",
        "from v3_app.pages.preflight_page",
        "QPropertyAnimation",
        "QGraphicsBlurEffect",
        "QGraphicsOpacityEffect",
        "QTimer",
        "open_radial",
        "radial_menu",
        "EmbeddedBridgeRuntime",
        "BridgeCommandClient",
        "save_workspace(",
        "build_runtime_preflight_status(",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
    ):
        assert forbidden.casefold() not in source_text.casefold()


def test_lcd_2_report_documents_component_library_scope_and_deferrals():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-2-liquid-component-library-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-2 Liquid Component Library",
        "components added",
        "module structure",
        "floating command surface",
        "runtime truth wording",
        "metadata integration",
        "LCD-3",
        "LCD-4 through LCD-9",
        "LCD-10 through LCD-12",
        "no full page rebuilds were implemented",
        "no subpage navigation architecture was implemented",
        "no animations were added",
        "no radial menu behavior was added",
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
