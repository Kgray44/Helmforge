from __future__ import annotations

import os
from pathlib import Path

from shared_core.models.workspace import create_default_workspace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TUNING_ROUTES = (
    "tuning.base_tuning",
    "tuning.filtering",
    "tuning.combat_profile",
    "tuning.conditional_rules",
)


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _state(*, active_page_id: str = "base_tuning"):
    from shared_core.models.runtime import (
        InputDeviceDetection,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )
    from v3_app.services.app_state import AppState

    runtime_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.SIMULATED,
        input=InputDeviceDetection(),
        output=OutputBackendDetection(status=OutputStatus.VJOY_DETECTED, backend_name="vJoy"),
    )
    state = AppState.from_runtime_status(runtime_status, active_page_id=active_page_id)
    state.active_profile = "LCD-6 Fixture"
    state.status_message = "Workspace ready."
    return state


def _text_blob(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join(labels + buttons)


def test_lcd_6_tuning_model_exposes_axes_parameters_metadata_and_validation():
    from v3_app.liquid.models.tuning_command_model import (
        build_tuning_command_model,
        stage_tuning_parameter_edit,
    )

    workspace = create_default_workspace()
    model = build_tuning_command_model(
        route_key="tuning.base_tuning",
        workspace=workspace,
        selected_axis="Roll",
        state=_state(),
    )
    parameters = {parameter.parameter_id: parameter for parameter in model.parameters}

    assert model.axis_options == ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
    assert model.selected_axis == "Roll"
    assert model.route_key == "tuning.base_tuning"
    assert {"base.curve_mode", "base.curve_strength", "base.deadzone", "base.max_output"}.issubset(parameters)
    assert parameters["base.curve_mode"].control_kind == "dropdown"
    assert parameters["base.curve_mode"].options == ("s",)
    assert parameters["base.deadzone"].control_kind == "numeric"
    assert parameters["base.deadzone"].minimum == 0.0
    assert parameters["base.deadzone"].maximum == 0.5
    assert "Preview only" in model.preview_truth_label

    staged = stage_tuning_parameter_edit(workspace, "tuning.base_tuning", "Roll", "base.deadzone", "0.07")
    assert staged.valid is True
    assert staged.workspace.tuning.axes["roll"].deadzone == 0.07
    assert staged.workspace.state.saved is False
    assert "Draft tuning change" in staged.status_label
    assert "Output proof unchanged" in staged.message

    invalid_text = stage_tuning_parameter_edit(workspace, "tuning.base_tuning", "Roll", "base.deadzone", "letters")
    assert invalid_text.valid is False
    assert invalid_text.workspace == workspace
    assert invalid_text.validation_errors

    invalid_range = stage_tuning_parameter_edit(workspace, "tuning.base_tuning", "Roll", "base.deadzone", "9")
    assert invalid_range.valid is False
    assert invalid_range.workspace == workspace


def test_lcd_6_each_tuning_route_maps_to_real_liquid_page_not_placeholder():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    for route_key in TUNING_ROUTES:
        shell.switch_route(route_key)
        app.processEvents()
        page = shell.page_widgets[route_key].widget()
        text = _text_blob(page)

        assert page.objectName() == "liquidTuningCommandPage"
        assert page.property("routeKey") == route_key
        assert "Liquid Command Deck placeholder" not in text
        assert "Placeholder route" not in text
        assert page.findChild(QWidget, "liquidTuningHero") is not None
        assert page.findChild(QWidget, "liquidTuningAxisSelectorPanel") is not None
        assert page.findChild(QWidget, "liquidTuningAdvancedDetails") is not None
        assert page.findChild(QWidget, "liquidTuningLiveSnapshot") is not None
        assert page.findChild(QWidget, "liquidTuningGuidance") is not None


def test_lcd_6_axis_selector_contains_required_axes_and_updates_selected_axis():
    _app()

    from v3_app.liquid.pages.tuning_command_pages import TuningCommandPage

    page = TuningCommandPage(route_key="tuning.base_tuning", state=_state(), workspace=create_default_workspace())
    selector = page.findChild(object, "liquidTuningAxisSelector")

    assert tuple(selector.option_labels()) == ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
    assert page.property("selectedAxis") == "Roll"

    page.select_axis("Yaw")
    text = _text_blob(page)

    assert page.property("selectedAxis") == "Yaw"
    assert "Axis: Yaw" in text
    assert "Selected control\nYaw" in text or "Yaw" in text


def test_lcd_6_page_specific_controls_and_instrument_regions_exist():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.tuning_command_pages import TuningCommandPage

    expectations = {
        "tuning.base_tuning": (
            "How does this axis respond before filtering/modes/rules?",
            ("Curve Mode", "Curve Strength", "Deadzone", "Anti-Deadzone", "Hysteresis", "Output Scale", "Max Output"),
        ),
        "tuning.filtering": (
            "How much smoothing/slew behavior is applied to this axis?",
            ("Center Alpha", "Edge Alpha", "Same Slew Limit", "Reverse Slew Limit"),
        ),
        "tuning.combat_profile": (
            "How does this axis behave in combat/aiming mode?",
            ("Combat Curve", "Combat Scale", "Combat Center Alpha", "Combat Edge Alpha", "Combat Same Slew", "Combat Reverse Slew"),
        ),
    }

    for route_key, (question, labels) in expectations.items():
        page = TuningCommandPage(route_key=route_key, state=_state(), workspace=create_default_workspace())
        text = _text_blob(page)

        assert question in text
        assert page.findChild(QWidget, "liquidTuningResponseInstrument") is not None
        assert page.findChild(QWidget, "liquidTuningParameterInspector") is not None
        for label in labels:
            assert label in text


def test_lcd_6_dropdowns_numeric_validators_and_invalid_stage_behavior():
    _app()

    from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton
    from v3_app.liquid.pages.tuning_command_pages import TuningCommandPage

    page = TuningCommandPage(route_key="tuning.base_tuning", state=_state(), workspace=create_default_workspace())
    dropdown = page.findChild(QComboBox, "liquidTuningControl_base_curve_mode")
    numeric = page.findChild(QLineEdit, "liquidTuningControl_base_deadzone")
    stage_button = page.findChild(QPushButton, "liquidTuningStage_base_deadzone")

    assert dropdown is not None
    assert dropdown.property("componentRole") == "DropdownParameterControl"
    assert [dropdown.itemText(index) for index in range(dropdown.count())] == ["s"]
    assert numeric is not None
    assert numeric.validator() is not None
    assert numeric.property("minValue") == 0.0
    assert numeric.property("maxValue") == 0.5
    assert stage_button is not None

    numeric.setText("letters")
    result = page.stage_parameter_edit("base.deadzone", numeric.text())

    assert result.valid is False
    assert numeric.property("validationState") == "invalid"
    assert "not staged" in result.message


def test_lcd_6_shell_stages_supported_tuning_edit_without_runtime_truth_change():
    app = _app()

    from PySide6.QtWidgets import QLabel
    from v3_app.liquid.app_shell import LiquidCommandShell

    state = _state()
    original_runtime = state.runtime
    shell = LiquidCommandShell(state=state)
    shell.switch_route("tuning.base_tuning")
    app.processEvents()

    result = shell.stage_tuning_parameter_edit("tuning.base_tuning", "Roll", "base.deadzone", "0.08")
    app.processEvents()

    saved_chip = shell.findChild(QLabel, "liquidSavedChip")
    page = shell.page_widgets["tuning.base_tuning"].widget()
    text = _text_blob(page).casefold()

    assert result.valid is True
    assert shell.workspace.tuning.axes["roll"].deadzone == 0.08
    assert shell.state.saved is False
    assert shell.state.runtime == original_runtime
    assert saved_chip is not None and saved_chip.text() == "Unsaved"
    assert "draft tuning change" in text
    assert "output proof unchanged" in text
    assert "output verified" not in text


def test_lcd_6_filtering_and_combat_edits_stage_workspace_draft_only():
    from v3_app.liquid.models.tuning_command_model import stage_tuning_parameter_edit

    workspace = create_default_workspace()

    filtering = stage_tuning_parameter_edit(
        workspace,
        "tuning.filtering",
        "Yaw",
        "filtering.center_alpha",
        "0.31",
    )
    combat = stage_tuning_parameter_edit(
        workspace,
        "tuning.combat_profile",
        "Pitch",
        "combat.combat_scale",
        "0.72",
    )

    assert filtering.valid is True
    assert filtering.workspace.filtering.axes["yaw"].center_alpha == 0.31
    assert filtering.workspace.state.saved is False
    assert combat.valid is True
    assert combat.workspace.combat.axes["pitch"].combat_scale == 0.72
    assert combat.workspace.state.saved is False


def test_lcd_6_conditional_rules_page_is_real_read_only_visualization():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.tuning_command_pages import TuningCommandPage

    page = TuningCommandPage(route_key="tuning.conditional_rules", state=_state(), workspace=create_default_workspace())
    text = _text_blob(page)
    rows = [widget for widget in page.findChildren(QWidget) if widget.property("conditionalRuleFlowRow") is True]

    assert "What rules can change the response stack, and when do they trigger?" in text
    assert "Rule system status" in text
    assert "Enabled rules" in text
    assert "Disabled rules" in text
    assert "Read-only rule visualization" in text
    assert rows
    assert page.findChild(QWidget, "liquidTuningRuleMetrics") is not None
    assert page.findChild(QWidget, "liquidTuningRuleInspector") is not None
    assert page.findChild(QWidget, "liquidTuningRuleWarnings") is not None


def test_lcd_6_live_snapshot_guidance_and_advanced_are_truth_labeled_secondary():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.tuning_command_pages import TuningCommandPage

    page = TuningCommandPage(route_key="tuning.filtering", state=_state(), workspace=create_default_workspace())
    snapshot = page.findChild(QWidget, "liquidTuningLiveSnapshot")
    guidance = page.findChild(QWidget, "liquidTuningGuidance")
    advanced = page.findChild(QWidget, "liquidTuningAdvancedDetails")
    text = _text_blob(page)

    assert snapshot is not None
    assert "Current sample unavailable" in text
    assert "Preview only" in text
    assert guidance is not None
    for section in ("Current feel", "What this affects", "Suggested range", "Caution", "Selected axis note"):
        assert section in text
    assert advanced is not None
    assert advanced.property("advancedSecondary") is True
    assert advanced.property("visualWeight") == "subdued"


def test_lcd_6_preflight_mapping_and_hidden_route_coalescing_remain_intact(monkeypatch):
    app = _app()

    from shared_core.models.runtime import InputStatus, OutputStatus, RuntimeTruth
    from tests.test_lcd_4f_interactive_startup_freeze import _telemetry
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.pages.preflight_command_page import PreflightCommandPage

    render_count = {"count": 0}
    original_render = PreflightCommandPage._render

    def counted_render(self, *args, **kwargs):
        render_count["count"] += 1
        return original_render(self, *args, **kwargs)

    monkeypatch.setattr(PreflightCommandPage, "_render", counted_render)
    shell = LiquidCommandShell(state=_state(active_page_id="base_tuning"))
    shell.switch_route("tuning.base_tuning")
    initial_preflight_renders = render_count["count"]

    telemetry = _telemetry(
        truth=RuntimeTruth.DETECTED_UNVERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.VJOY_DETECTED,
        output_verified=False,
    )
    for _ in range(8):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()

    assert shell.current_route_key == "tuning.base_tuning"
    assert render_count["count"] == initial_preflight_renders

    shell.switch_route("preflight.command_readiness")
    assert shell.page_widgets["preflight.command_readiness"].widget().objectName() == "liquidPreflightCommandPage"
    shell.switch_route("mapping.hotas_map")
    assert shell.page_widgets["mapping.hotas_map"].widget().objectName() == "liquidMappingCommandPage"


def test_lcd_6_sources_preserve_runtime_boundaries_and_forbidden_claims():
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "tuning_command_pages.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "models" / "tuning_command_model.py",
        )
        if path.exists()
    )

    for forbidden in (
        "from v3_app.pages.base_tuning_page",
        "from v3_app.pages.filtering_page",
        "from v3_app.pages.combat_profile_page",
        "from v3_app.pages.conditional_rules_page",
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


def test_lcd_6_report_documents_tuning_scope_and_truth_boundaries():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-6-tuning-command-pages-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-6 Tuning Command Pages",
        "routes implemented",
        "tuning page architecture",
        "tuning presentation/edit model structure",
        "data surfaces used",
        "axis selector behavior",
        "Base Tuning page behavior",
        "Filtering page behavior",
        "Combat Profile page behavior",
        "Conditional Rules page behavior",
        "parameter metadata usage",
        "validation behavior",
        "draft/staged edit behavior",
        "live/current snapshot truth behavior",
        "guidance block behavior",
        "response preview/graph approach",
        "advanced details behavior",
        "output intent/preview differs from output proof",
        "Legacy fallback/reference is preserved",
        "limitations/deferred tuning features",
        "runtime truth preservation statement",
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
        "tuning edits are workspace/draft/preview edits only",
    ):
        assert required in text
