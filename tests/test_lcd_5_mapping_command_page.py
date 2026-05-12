from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path

from shared_core.models.mappings import MappingConfig
from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)
from shared_core.models.workspace import create_default_workspace


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


def _state(runtime_status: RuntimePreflightStatus | None = None, *, active_page_id: str = "mapping"):
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(runtime_status or _runtime_status(), active_page_id=active_page_id)
    state.active_profile = "LCD-5 Mapping Fixture"
    state.source_config = "C:/Users/kkids/Documents/HOTAS-Control-Panel/configs/lcd_5_mapping_fixture.json"
    state.status_message = "Workspace ready."
    return state


def _texts(widget) -> list[str]:
    from PySide6.QtWidgets import QLabel, QPushButton

    return [label.text() for label in widget.findChildren(QLabel)] + [
        button.text() for button in widget.findChildren(QPushButton)
    ]


def _text_blob(widget) -> str:
    return "\n".join(_texts(widget))


def _mapping_page_from_shell(shell):
    return shell.page_widgets["mapping.hotas_map"].widget()


def test_lcd_5_mapping_model_derives_known_controls_and_intent_metrics():
    from v3_app.liquid.models.mapping_command_model import build_mapping_command_model

    model = build_mapping_command_model(workspace=create_default_workspace(), state=_state())
    controls = {control.control_id: control for control in model.controls}

    assert model.selected_control.control_id == "axis_roll"
    assert set(controls) >= {
        "axis_roll",
        "axis_pitch",
        "axis_throttle",
        "axis_yaw",
        "axis_aux_1",
        "axis_aux_2",
        "button_b1",
        "button_b15",
        "hat_pov",
    }
    assert controls["axis_roll"].display_label == "Roll axis"
    assert controls["axis_roll"].physical_group == "stick"
    assert controls["axis_roll"].output_intent_target == "vJoy X(axis1)"
    assert controls["button_b15"].output_intent_target == "Button 15"
    assert controls["hat_pov"].display_label == "Hat / POV"
    assert {metric.label for metric in model.mapping_metrics} >= {
        "Axis Routes",
        "Button Routes",
        "Hat Routes",
        "Unmapped Controls",
        "Warnings",
        "Output Intent Targets",
    }
    assert any("Output intent is not output write proof" in note for note in model.truth_source_notes)


def test_lcd_5_mapping_page_constructs_with_visual_hotas_map_and_all_markers():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.mapping_command_page import MappingCommandPage

    page = MappingCommandPage(state=_state(), workspace=create_default_workspace())
    page_text = _text_blob(page)

    hero = page.findChild(QWidget, "liquidMappingHotasHero")
    visual_map = page.findChild(QWidget, "liquidMappingHotasMap")

    assert page.property("routeKey") == "mapping.hotas_map"
    assert "Liquid Command Deck placeholder" not in page_text
    assert "What is each physical control doing?" in page_text
    assert hero is not None
    assert hero.property("mappingVisualRole") == "primary_hotas_map"
    assert visual_map is not None
    assert visual_map.property("hotasVisualMap") is True

    for control_id in (
        "axis_roll",
        "axis_pitch",
        "axis_throttle",
        "axis_yaw",
        "axis_aux_1",
        "axis_aux_2",
        "hat_pov",
        *(f"button_b{index}" for index in range(1, 16)),
    ):
        marker = page.findChild(QWidget, f"liquidMappingMarker_{control_id}")
        assert marker is not None, control_id
        assert marker.property("mappingMarker") is True


def test_lcd_5_selected_control_inspector_and_route_flow_update_without_mutation():
    _app()

    from v3_app.liquid.pages.mapping_command_page import MappingCommandPage

    workspace = create_default_workspace()
    page = MappingCommandPage(state=_state(), workspace=workspace)
    before_routes = workspace.mappings

    assert page.selected_control_id == "axis_roll"
    assert "Roll axis" in _text_blob(page.findChild(object, "liquidMappingInspector"))
    assert "Physical Stick X" in _text_blob(page.findChild(object, "liquidMappingRouteFlowPanel"))
    assert "Output Intent: vJoy X(axis1)" in _text_blob(page.findChild(object, "liquidMappingRouteFlowPanel"))

    page.select_control("button_b5")
    inspector_text = _text_blob(page.findChild(object, "liquidMappingInspector"))
    flow_text = _text_blob(page.findChild(object, "liquidMappingRouteFlowPanel"))

    assert page.selected_control_id == "button_b5"
    assert "B5" in inspector_text
    assert "Button 5" in flow_text
    assert "Output Intent: Button 5" in flow_text
    assert workspace.mappings == before_routes


def test_lcd_5_unmapped_controls_are_honest_and_do_not_imply_output_proof():
    _app()

    from v3_app.liquid.models.mapping_command_model import build_mapping_command_model
    from v3_app.liquid.pages.mapping_command_page import MappingCommandPage

    workspace = create_default_workspace()
    unmapped_workspace = replace(
        workspace,
        mappings=MappingConfig(
            axis_routes=workspace.mappings.axis_routes[:2],
            button_routes=workspace.mappings.button_routes[:3],
            hat_routes=(),
        ),
    )
    model = build_mapping_command_model(workspace=unmapped_workspace, state=_state())
    controls = {control.control_id: control for control in model.controls}

    assert controls["axis_throttle"].mapped_state == "unmapped"
    assert controls["axis_throttle"].output_intent_target == "unmapped"
    assert controls["button_b4"].mapped_state == "unmapped"
    assert controls["hat_pov"].mapped_state == "unmapped"

    page = MappingCommandPage(state=_state(), workspace=unmapped_workspace)
    page_text = _text_blob(page).casefold()

    assert "unmapped" in page_text
    assert "read-only visualization" in page_text
    assert "output intent" in page_text
    assert "output verified" not in page_text
    assert "vjoy writing" not in page_text
    assert "live output active" not in page_text
    assert "hotas connected" not in page_text


def test_lcd_5_route_registry_uses_real_mapping_page_and_preserves_preflight():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    shell.switch_route("mapping.hotas_map")
    shell.resize(1360, 800)
    shell.show()
    app.processEvents()

    mapping_page = _mapping_page_from_shell(shell)
    mapping_text = _text_blob(mapping_page)

    assert mapping_page.objectName() == "liquidMappingCommandPage"
    assert mapping_page.findChild(QWidget, "liquidMappingHotasMap") is not None
    assert "Liquid Command Deck placeholder" not in mapping_text

    shell.switch_route("preflight.command_readiness")
    app.processEvents()
    preflight = shell.page_widgets["preflight.command_readiness"].widget()
    assert preflight.objectName() == "liquidPreflightCommandPage"
    assert "Can I safely use live output right now?" in _text_blob(preflight)


def test_lcd_5_advanced_route_details_are_secondary_and_metrics_exist():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.models.mapping_command_model import build_mapping_command_model
    from v3_app.liquid.pages.mapping_command_page import MappingCommandPage

    workspace = create_default_workspace()
    model = build_mapping_command_model(state=_state(), workspace=workspace)
    page = MappingCommandPage(state=_state(), workspace=workspace)
    metrics = page.findChild(QWidget, "liquidMappingMetrics")
    advanced = page.findChild(QWidget, "liquidMappingAdvancedRouteDetails")
    detail_rows = [
        widget
        for widget in advanced.findChildren(QWidget)
        if widget.property("advancedRouteDetailRow") is True
    ]

    assert metrics is not None
    assert metrics.property("mappingMetrics") is True
    assert advanced is not None
    assert advanced.property("advancedSecondary") is True
    assert advanced.property("visualWeight") == "subdued"
    assert len(model.advanced_route_details) >= 22
    assert 1 <= len(detail_rows) <= 6
    assert advanced.findChild(QWidget, "liquidMappingAdvancedCounts") is not None


def test_lcd_5_lcd4f_hidden_preflight_coalescing_remains_intact(monkeypatch):
    app = _app()

    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.pages.preflight_command_page import PreflightCommandPage
    from tests.test_lcd_4f_interactive_startup_freeze import _telemetry

    render_count = {"count": 0}
    original_render = PreflightCommandPage._render

    def counted_render(self, *args, **kwargs):
        render_count["count"] += 1
        return original_render(self, *args, **kwargs)

    monkeypatch.setattr(PreflightCommandPage, "_render", counted_render)
    shell = LiquidCommandShell(state=_state(active_page_id="mapping"))
    shell.switch_route("mapping.hotas_map")
    initial_render_count = render_count["count"]

    telemetry = _telemetry(
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        output_verified=False,
    )
    for _ in range(20):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()

    assert shell.current_route_key == "mapping.hotas_map"
    assert render_count["count"] == initial_render_count


def test_lcd_5_mapping_runtime_chip_tracks_top_bar_without_rebuild_loop():
    app = _app()

    from PySide6.QtWidgets import QLabel
    from tests.test_lcd_4f_interactive_startup_freeze import _telemetry
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(active_page_id="mapping"))
    shell.switch_route("mapping.hotas_map")
    page = _mapping_page_from_shell(shell)
    initial_render_count = page.property("mappingRenderCount")

    telemetry = _telemetry(
        truth=RuntimeTruth.LIVE_VERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.OUTPUT_VERIFIED,
        output_verified=True,
    )
    for _ in range(8):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()

    runtime_chip = shell.findChild(QLabel, "liquidRuntimeTruthChip")
    assert runtime_chip.text() == "Live Verified"
    assert "Live Verified" in _text_blob(page)
    assert page.property("mappingRenderCount") <= initial_render_count + 1


def test_lcd_5_sources_do_not_wrap_legacy_page_or_add_forbidden_runtime_authority():
    source_paths = (
        PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "mapping_command_page.py",
        PROJECT_ROOT / "v3_app" / "liquid" / "models" / "mapping_command_model.py",
    )
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for forbidden in (
        "from v3_app.pages.mapping_page",
        "HotasDiagramWidget",
        "BridgeCommandClient",
        "EmbeddedBridgeRuntime",
        "build_runtime_preflight_status(",
        "verify_output_write",
        "write_output_intent",
        "QPropertyAnimation",
        "QGraphicsBlurEffect",
        "auto_save",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
    ):
        assert forbidden.casefold() not in source_text.casefold()


def test_lcd_5_report_documents_mapping_scope_and_deferrals():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-5-mapping-command-page-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-5 Mapping Command Page",
        "Mapping page architecture",
        "route replaced",
        "mapping presentation model structure",
        "data surfaces used",
        "HOTAS visual map approach",
        "selected control inspector behavior",
        "route flow behavior",
        "metrics behavior",
        "advanced route details behavior",
        "truth consistency with top bar/runtime state",
        "layout/overlap preservation statement",
        "Legacy fallback/reference is preserved",
        "prepares for later mapping/detail/editing phases",
        "explicit deferred items",
        "runtime truth preservation statement",
        "no Route Details page was rebuilt",
        "no Advanced Route Tables page was rebuilt",
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
