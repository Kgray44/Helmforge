from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from shared_core.models.workspace import create_default_workspace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECORDER_ROUTES = (
    "recorder.flight_recorder",
    "recorder.clip_library",
    "recorder.capture_backend_truth",
)


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _state(*, active_page_id: str = "flight_recorder"):
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )
    from v3_app.services.app_state import AppState

    runtime_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
    )
    state = AppState.from_runtime_status(runtime_status, active_page_id=active_page_id)
    state.active_profile = "LCD-8 Fixture"
    state.status_message = "Workspace ready."
    return state


def _workspace_with_helm_findings():
    workspace = create_default_workspace()
    combat_axes = dict(workspace.combat.axes)
    tuning_axes = dict(workspace.tuning.axes)
    filtering_axes = dict(workspace.filtering.axes)
    combat_axes["yaw"] = replace(
        combat_axes["yaw"],
        combat_center_alpha=0.52,
        combat_reverse_slew=0.06,
        combat_same_slew=0.06,
        combat_scale=0.68,
    )
    combat_axes["pitch"] = replace(combat_axes["pitch"], combat_center_alpha=0.56, combat_scale=0.84)
    tuning_axes["yaw"] = replace(tuning_axes["yaw"], deadzone=0.08, curve_strength=0.62)
    filtering_axes["yaw"] = replace(filtering_axes["yaw"], center_alpha=0.22, reverse_slew_limit=0.42)
    return replace(
        workspace,
        combat=replace(workspace.combat, axes=combat_axes),
        tuning=replace(workspace.tuning, axes=tuning_axes),
        filtering=replace(workspace.filtering, axes=filtering_axes),
    )


def _text_blob(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join(labels + buttons)


def test_lcd_8_recorder_model_reports_capability_truth_without_capture_or_encoding(tmp_path):
    from v3_app.liquid.models.recorder_command_model import build_recorder_command_model
    from v3_app.recorder.capture_backend import MissingCaptureBackend
    from v3_app.recorder.recorder_settings import FlightRecorderSettings

    settings = FlightRecorderSettings.from_dict(
        {**FlightRecorderSettings.defaults().to_dict(), "destination_folder": str(tmp_path)}
    )
    model = build_recorder_command_model(
        route_key="recorder.flight_recorder",
        settings=settings,
        capture_backend=MissingCaptureBackend(),
    )
    labels = " ".join(capability.label for capability in model.capabilities)

    assert model.real_capture_supported is False
    assert model.encoding_available is False
    assert model.hindsight_video_available is False
    assert model.frame_capture_available is False
    assert "Capture backend unavailable" in labels
    assert "Frame capture unavailable" in labels
    assert "Encoding unavailable" in labels
    assert "Hindsight video unavailable" in labels
    assert "Metadata-only artifact review" in labels
    assert any(action.action_id == "record_now" and not action.enabled for action in model.actions)
    assert any(action.action_id == "save_last_clip" and not action.enabled for action in model.actions)
    assert "Output proof unchanged" in model.truth_source_notes


def test_lcd_8_recorder_routes_map_to_real_liquid_pages_not_placeholders():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    for route_key in RECORDER_ROUTES:
        shell.switch_route(route_key)
        app.processEvents()
        page = shell.page_widgets[route_key].widget()
        text = _text_blob(page)

        assert page.objectName() == "liquidRecorderCommandPage"
        assert page.property("routeKey") == route_key
        assert "Liquid Command Deck placeholder" not in text
        assert "Placeholder route" not in text
        assert page.findChild(QWidget, "liquidRecorderStatusHero") is not None
        assert page.findChild(QWidget, "liquidRecorderAdvancedDetails") is not None


def test_lcd_8_flight_recorder_page_disables_unavailable_capture_actions():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.pages.recorder_command_pages import RecorderCommandPage

    page = RecorderCommandPage(route_key="recorder.flight_recorder", state=_state())
    text = _text_blob(page)
    record_now = page.findChild(QPushButton, "liquidRecorderRecordNowButton")
    save_last = page.findChild(QPushButton, "liquidRecorderSaveLastClipButton")

    assert page.findChild(QWidget, "liquidRecorderCapabilityRail") is not None
    assert record_now is not None and record_now.isEnabled() is False
    assert save_last is not None and save_last.isEnabled() is False
    assert "Real recording unavailable" in text
    assert "Metadata-only artifacts available" in text
    assert "Capture backend unavailable" in text
    assert "Encoding unavailable" in text
    assert "Hindsight video unavailable" in text
    for forbidden in ("Recording ready", "Recording active", "Video export ready", "Hindsight buffer ready"):
        assert forbidden not in text


def test_lcd_8_capture_backend_truth_lists_backend_fields_and_no_injection_no_hooking():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.pages.recorder_command_pages import RecorderCommandPage

    page = RecorderCommandPage(route_key="recorder.capture_backend_truth", state=_state())
    text = _text_blob(page)

    assert page.findChild(QWidget, "liquidRecorderBackendTruthPanel") is not None
    assert "Backend name" in text
    assert "Dependency unavailable" in text
    assert "Screen capture unavailable" in text
    assert "Frame capture unavailable" in text
    assert "Display enumeration unavailable" in text
    assert "No game injection" in text
    assert "No graphics hooking" in text
    assert "Encoding unavailable" in text


def test_lcd_8_clip_library_page_shows_metadata_artifacts_without_playback_or_export_claims(tmp_path):
    _app()

    from v3_app.liquid.pages.recorder_command_pages import RecorderCommandPage
    from v3_app.recorder.capture_backend import SimulatedCaptureBackend
    from v3_app.recorder.recorder_controller import FlightRecorderController
    from v3_app.recorder.recorder_settings import FlightRecorderSettings

    settings = FlightRecorderSettings.from_dict(
        {**FlightRecorderSettings.defaults().to_dict(), "destination_folder": str(tmp_path)}
    )
    controller = FlightRecorderController(settings=settings, capture_backend=SimulatedCaptureBackend())
    controller.append_telemetry_sample(timestamp=10.0, axes={"Yaw": 0.3}, source="Final output")
    result = controller.save_last_clip(now=11.0, created_at="2026-05-12T12:00:00Z")
    assert result.artifact is not None

    page = RecorderCommandPage(route_key="recorder.clip_library", state=_state(), settings=settings)
    text = _text_blob(page)

    assert "Clip metadata" in text
    assert "Metadata-only artifact" in text
    assert "Playback unavailable" in text
    assert "Export unavailable" in text
    assert "Real recording unavailable" in text
    assert "playable clip" not in text.casefold()


def test_lcd_8_helm_model_structures_findings_and_stages_draft_without_runtime_truth_change():
    from v3_app.liquid.models.helm_command_model import (
        build_helm_command_model,
        stage_selected_helm_changes,
        revert_helm_changes,
    )

    workspace = _workspace_with_helm_findings()
    state = _state()
    original_runtime = state.runtime
    model = build_helm_command_model(
        workspace=workspace,
        state=state,
        symptom_text="Combat mode feels sluggish",
        selected_axis="Yaw",
    )

    assert model.findings
    assert model.proposed_changes
    assert model.apply_available is True
    assert all("Output proof unchanged" in change.truth_note for change in model.proposed_changes)

    staged = stage_selected_helm_changes(workspace, model.result, selected_change_ids=(model.proposed_changes[0].change_id,))
    assert staged.valid is True
    assert staged.workspace is not workspace
    assert staged.workspace.state.saved is False
    assert "Draft Helm change" in staged.status_label
    assert "Output proof unchanged" in staged.message
    assert state.runtime == original_runtime

    reverted = revert_helm_changes(staged.workspace, staged.applied_diffs)
    assert reverted.workspace == workspace
    assert reverted.valid is True


def test_lcd_8_helm_deck_constructs_and_shell_button_toggles_without_cloud_ai():
    app = _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(), workspace=_workspace_with_helm_findings())
    deck = shell.findChild(QWidget, "liquidHelmAssistantDeck")
    helm_button = shell.findChild(QPushButton, "liquidHelmButton")

    assert deck is not None
    assert deck.property("helmSurface") is True
    assert helm_button is not None and helm_button.isEnabled() is True
    assert "cloud" not in _text_blob(deck).casefold()

    assert deck.isVisible() is False
    helm_button.click()
    app.processEvents()
    assert deck.isVisible() is True
    text = _text_blob(deck)
    assert "Helm Assistant" in text
    assert "Evidence source" in text
    assert "Apply selected changes to workspace draft" in text
    assert "Output proof unchanged" in text


def test_lcd_8_helm_apply_and_revert_use_existing_workspace_draft_semantics():
    app = _app()

    from PySide6.QtWidgets import QPushButton
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(), workspace=_workspace_with_helm_findings())
    original_runtime = shell.state.runtime
    original_value = shell.workspace.combat.axes["yaw"].combat_center_alpha
    apply_button = shell.findChild(QPushButton, "liquidHelmApplySelectedButton")

    assert apply_button is not None and apply_button.isEnabled() is True
    apply_button.click()
    app.processEvents()

    assert shell.workspace.combat.axes["yaw"].combat_center_alpha != original_value
    assert shell.state.saved is False
    assert shell.state.runtime == original_runtime
    assert "Helm staged" in shell.state.status_message

    revert_button = shell.findChild(QPushButton, "liquidHelmRevertLastButton")
    assert revert_button is not None and revert_button.isEnabled() is True
    revert_button.click()
    app.processEvents()

    assert shell.workspace.combat.axes["yaw"].combat_center_alpha == original_value
    assert shell.state.runtime == original_runtime
    assert "reverted" in shell.state.status_message.casefold()


def test_lcd_8_hidden_recorder_pages_do_not_rebuild_on_telemetry_bursts(monkeypatch):
    app = _app()

    from tests.test_lcd_4f_interactive_startup_freeze import _telemetry
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.pages.recorder_command_pages import RecorderCommandPage

    render_count = {"count": 0}
    original_render = RecorderCommandPage._render

    def counted_render(self, *args, **kwargs):
        render_count["count"] += 1
        return original_render(self, *args, **kwargs)

    monkeypatch.setattr(RecorderCommandPage, "_render", counted_render)
    shell = LiquidCommandShell(state=_state(active_page_id="live_monitor"))
    shell.switch_route("analysis.live_monitor")
    initial_renders = render_count["count"]
    telemetry = _telemetry()

    for _ in range(8):
        shell.apply_bridge_telemetry(telemetry)
        app.processEvents()

    assert shell.current_route_key == "analysis.live_monitor"
    assert render_count["count"] == initial_renders


def test_lcd_8_prior_routes_still_work():
    app = _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state())
    expected = {
        "preflight.command_readiness": "liquidPreflightCommandPage",
        "mapping.hotas_map": "liquidMappingCommandPage",
        "tuning.base_tuning": "liquidTuningCommandPage",
        "analysis.live_monitor": "liquidAnalysisCommandPage",
    }
    for route_key, object_name in expected.items():
        shell.switch_route(route_key)
        app.processEvents()
        assert shell.page_widgets[route_key].widget().objectName() == object_name


def test_lcd_8_sources_preserve_runtime_boundaries_and_forbidden_claims():
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "recorder_command_pages.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "pages" / "helm_command_deck.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "models" / "recorder_command_model.py",
            PROJECT_ROOT / "v3_app" / "liquid" / "models" / "helm_command_model.py",
        )
        if path.exists()
    )

    for forbidden in (
        "from v3_app.pages.flight_recorder_page",
        "from v3_app.helm.helm_overlay",
        "QPropertyAnimation",
        "QGraphicsBlurEffect",
        "BridgeCommandClient",
        "EmbeddedBridgeRuntime",
        "verify_output_write",
        "write_output",
        "start_recording",
        "record_now(",
        "save_last_clip(",
        "capture_frame(",
        "capture_one_frame(",
        "encode(",
        "VideoWriter",
        "ffmpeg",
        "ImageGrab",
        "mss",
        "dxcam",
        "RegisterHotKey",
        "OpenAI(",
        "anthropic",
        "auto_save",
        "StartBridge",
        "StopBridge",
        "RestartBridge",
    ):
        assert forbidden.casefold() not in source_text.casefold()

    for forbidden_claim in (
        "Recording ready",
        "Recording active",
        "Video export ready",
        "Hindsight buffer ready",
        "capture backend ready",
        "encoding ready",
        "live output active",
    ):
        assert forbidden_claim.casefold() not in source_text.casefold()


def test_lcd_8_report_documents_recorder_helm_scope_and_truth_boundaries():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-8-recorder-helm-command-pages-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-8 Recorder and Helm Command Pages",
        "routes implemented",
        "Recorder page architecture",
        "Flight Recorder page behavior",
        "Capture Backend Truth page behavior",
        "Clip Library / Artifacts page behavior",
        "Recorder presentation model structure",
        "data surfaces used",
        "backend capability truth behavior",
        "metadata-only vs real recording truth behavior",
        "disabled/unavailable recorder action behavior",
        "Helm assistant deck/surface architecture",
        "Helm data/logic surfaces used",
        "Helm recommendation/finding/proposed-change behavior",
        "Helm apply/revert semantics",
        "Recorder/Helm truth differs from runtime output proof",
        "hidden-route rebuild protection",
        "Legacy fallback/reference is preserved",
        "limitations/deferred recorder/Helm features",
        "runtime truth preservation statement",
        "no Support/Diagnostics page was rebuilt",
        "no radial menu behavior was added",
        "no animations were added",
        "no page transitions were added",
        "no recorder timeline animation was added",
        "no Helm slide-in animation was added",
        "no real blur/distortion was added",
        "no runtime authority was changed",
        "no hardware polling was changed",
        "no vJoy/output behavior was changed",
        "no output verification behavior was changed",
        "no Bridge lifecycle management was added",
        "no real recorder capture/encoding was added",
        "no game injection was added",
        "no graphics API hooking was added",
        "no cloud AI/LLM behavior was added",
        "no auto-save was added",
        "Recorder pages are truth surfaces over existing recorder/backend state",
        "Helm changes are recommendations/staged draft changes only using existing safe semantics",
    ):
        assert required in text
