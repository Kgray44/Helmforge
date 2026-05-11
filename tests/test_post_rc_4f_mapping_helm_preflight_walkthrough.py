from __future__ import annotations

import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status(*, live: bool = False):
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )

    if live:
        return RuntimePreflightStatus(
            mode=RuntimeMode.FULL_LIVE,
            truth=RuntimeTruth.LIVE_VERIFIED,
            input=InputDeviceDetection(status=InputStatus.DETECTED),
            output=OutputBackendDetection(
                status=OutputStatus.OUTPUT_VERIFIED,
                backend_name="vJoy",
                live_output_writes_verified=True,
            ),
        )
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


def _shell(tmp_path, *, runtime_status=None):
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    status = runtime_status or _runtime_status()
    return HelmForgeShell(
        state=AppState.from_runtime_status(status),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
        runtime_status=status,
        bridge_command_path=tmp_path / "bridge_command.json",
    )


def _live_verified_telemetry():
    from shared_core.models.runtime import InputStatus, OutputStatus, RuntimeTruth
    from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState
    from shared_core.runtime.telemetry import (
        AxisTelemetrySnapshot,
        BridgeTelemetrySnapshot,
        ButtonHatTelemetrySnapshot,
        ModeStateTelemetrySnapshot,
        OutputVerificationState,
    )

    return BridgeTelemetrySnapshot(
        runtime_truth=RuntimeTruth.LIVE_VERIFIED,
        lifecycle_state=BridgeLifecycleState.LIVE_VERIFIED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.OUTPUT_VERIFIED,
        raw_axes=AxisTelemetrySnapshot({}),
        final_axes=AxisTelemetrySnapshot({}),
        controls=ButtonHatTelemetrySnapshot(),
        active_modes=ModeStateTelemetrySnapshot(),
        output_verification=OutputVerificationState(verified=True, backend_name="vJoy"),
        active_profile="current-workspace",
    )


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    return "\n".join(
        [label.text() for label in widget.findChildren(QLabel)]
        + [button.text() for button in widget.findChildren(QPushButton)]
    )


def _visible_label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    texts: list[str] = []
    for child in [*widget.findChildren(QLabel), *widget.findChildren(QPushButton)]:
        if not child.isVisible():
            continue
        name = child.objectName().casefold()
        parent = child.parentWidget()
        while parent is not None:
            name += " " + parent.objectName().casefold()
            parent = parent.parentWidget()
        if "advanced" in name or "diagnostic" in name or "perf" in name:
            continue
        texts.append(child.text())
    return "\n".join(texts)


def test_post_rc_4f_global_runtime_and_footer_workspace_state_are_truthful(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel

    shell = _shell(tmp_path)
    sidebar_runtime = shell.sidebar.findChild(QLabel, "runtimeState")
    footer_state = shell.footer.findChild(QLabel, "footerWorkspaceStateChip")

    assert sidebar_runtime is not None
    assert footer_state is not None
    assert footer_state.text() == "Saved"

    shell.mark_workspace_dirty("Mapping edit staged.")
    assert footer_state.text() == "Unsaved changes"
    assert footer_state.property("chipTone") == "warning"

    shell.apply_bridge_telemetry(_live_verified_telemetry())
    assert sidebar_runtime.text() == "Live Verified"
    assert sidebar_runtime.property("chipTone") == "success"


def test_post_rc_4f_apply_workspace_reloads_bridge_without_saving_main_file(tmp_path):
    _app()

    from dataclasses import replace
    from PySide6.QtWidgets import QPushButton
    from shared_core.persistence.workspace_identity import compute_workspace_hash

    shell = _shell(tmp_path)
    workspace_path = tmp_path / "hotas_bridge_config_v3.json"
    updated = replace(shell.workspace, active_profile="combat-test-draft")
    shell.update_workspace_draft(updated, "Profile changed for live trial.")

    apply_button = shell.footer.findChild(QPushButton, "applyWorkspaceButton")
    assert apply_button is not None
    apply_button.click()
    _app().processEvents()

    assert not workspace_path.exists()
    command = json.loads((tmp_path / "bridge_command.json").read_text(encoding="utf-8"))
    assert command["command"] == "ReloadConfig"
    assert command["config_path"] != str(workspace_path)
    assert command["expected_workspace_hash"] == compute_workspace_hash(updated)
    assert command["expected_workspace_revision"] == compute_workspace_hash(updated)[:12]
    assert shell.state.saved is False
    assert "Applied workspace draft" in shell.state.status_message


def test_post_rc_4f_preflight_is_first_setup_page_and_not_embedded_in_mapping(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel, QFrame
    from v3_app.ui.sidebar import SIDEBAR_GROUPS

    shell = _shell(tmp_path)

    assert SIDEBAR_GROUPS[0][2][0] == "preflight"
    assert "preflight" in shell.page_widgets

    shell.switch_page("preflight")
    preflight = shell.page_widgets["preflight"].widget()
    text = _label_text(preflight)
    assert "Run Preflight Check" in text
    for section_name in (
        "preflightReadinessSection",
        "preflightDeviceDriverSection",
        "preflightVjoyOutputSection",
        "preflightBridgeTelemetrySection",
        "preflightWorkspaceConfigSection",
        "preflightInputDataSection",
        "preflightSafetyGatesSection",
        "preflightWarningsActionsSection",
        "preflightAdvancedDetailsSection",
    ):
        assert preflight.findChild(QFrame, section_name) is not None
    assert len(preflight.findChildren(QLabel, "preflightDatumValue")) >= 30

    mapping = shell.page_widgets["mapping"].widget()
    assert mapping.findChild(QFrame, "runtimePreflightCard") is None


def test_post_rc_4f_mapping_status_tables_and_remap_card_match_finished_design(tmp_path):
    _app()

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QFrame, QTableWidget

    shell = _shell(tmp_path, runtime_status=_runtime_status(live=True))
    shell.show()
    _app().processEvents()
    mapping = shell.page_widgets["mapping"].widget()

    text = _label_text(mapping)
    assert "current-workspace" in text
    assert "Live Verified" in text
    assert "vJoy Verified" in text

    overview = mapping.findChild(QFrame, "routingOverviewCard")
    summary = mapping.findChild(QFrame, "liveRouteSummaryCard")
    assert overview is not None
    assert summary is not None
    assert len(overview.findChildren(QLabel, "routeCountBadge")) >= 3
    assert len(summary.findChildren(QFrame, "routeFlowRow")) >= 6
    assert "Raw axis 1 -> X -> X(axis1)" not in _visible_label_text(summary)

    axis_table = mapping.findChild(QTableWidget, "axisRoutingTable")
    button_table = mapping.findChild(QTableWidget, "buttonRoutingTable")
    assert axis_table is not None
    assert button_table is not None
    assert axis_table.columnCount() == 5
    assert button_table.columnCount() == 2
    assert axis_table.verticalHeader().defaultSectionSize() >= 48
    assert button_table.verticalHeader().defaultSectionSize() >= 48

    headers = [
        axis_table.horizontalHeaderItem(index).text()
        for index in range(axis_table.columnCount())
    ] + [
        button_table.horizontalHeaderItem(index).text()
        for index in range(button_table.columnCount())
    ]
    assert "Live Raw" not in headers
    assert "Final Intent" not in headers
    assert "Raw" not in headers
    assert "Output" not in headers
    assert not axis_table.findChildren(QComboBox)
    assert not button_table.findChildren(QComboBox)
    assert not axis_table.findChildren(QCheckBox)

    marker = mapping.findChild(QLabel, "hotasMarker_axis_roll")
    assert marker is not None
    QTest.mouseClick(marker, Qt.MouseButton.LeftButton)
    _app().processEvents()

    remap_card = mapping.findChild(QFrame, "routeRemapCard")
    assert remap_card is not None
    assert remap_card.isVisible()
    assert remap_card.parentWidget() is mapping
    assert remap_card.property("uiRole") == "diagramRemapOverlay"
    assert remap_card.property("overlayMode") == "floating-over-page"
    assert mapping.property("diagramBackdropBlurred") is True
    assert remap_card.findChild(QLabel, "routeEditorPhysicalValue").text() == "Axis 1"
    assert "Route Inspector" not in _visible_label_text(remap_card)
    assert "Source of truth" not in _visible_label_text(remap_card)


def test_post_rc_4f_hotas_diagram_markers_survive_resize_filter_and_click(tmp_path):
    _app()

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel, QFrame
    from v3_app.services.hotas_diagram_model import build_hotas_diagram_model
    from v3_app.widgets.hotas_diagram import HotasDiagramWidget

    shell = _shell(tmp_path)
    shell.show()
    _app().processEvents()
    mapping = shell.page_widgets["mapping"].widget()
    diagram = mapping.findChild(HotasDiagramWidget, "hotasDiagramWidget")
    assert diagram is not None
    model = build_hotas_diagram_model(shell.workspace)
    assert len([control for control in model.routed_controls if control.route_type == "axis"]) == 6
    assert len([control for control in model.routed_controls if control.route_type == "button"]) == 15
    assert len([control for control in model.routed_controls if control.route_type == "hat"]) == 1
    diagram.resize(980, 460)
    _app().processEvents()

    markers = diagram.findChildren(QLabel)
    marker_names = {marker.objectName() for marker in markers}
    assert len(markers) >= 22
    assert "hotasMarker_axis_roll" in marker_names
    assert "hotasMarker_button_b15" in marker_names
    assert "hotasMarker_hat_pov" in marker_names

    for marker in markers:
        geometry = marker.geometry()
        assert geometry.width() > 0
        assert geometry.height() > 0
        assert diagram.rect().contains(geometry.topLeft())
        assert diagram.rect().contains(geometry.bottomRight())

    diagram.set_filter("Buttons")
    _app().processEvents()
    assert any(marker.property("filteredOut") is False for marker in markers)
    diagram.set_filter("All")
    _app().processEvents()
    assert all(marker.property("filteredOut") is False for marker in markers)

    marker = diagram.findChild(QLabel, "hotasMarker_button_b5")
    assert marker is not None
    QTest.mouseClick(marker, Qt.MouseButton.LeftButton)
    _app().processEvents()
    remap = mapping.findChild(QFrame, "routeRemapCard")
    assert remap is not None
    assert remap.isVisible()


def test_post_rc_4f_helm_is_in_app_pane_with_live_pulse_and_responsive_columns(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel, QFrame, QScrollArea

    shell = _shell(tmp_path)
    shell.resize(1280, 820)
    overlay = shell.open_helm_overlay()

    assert overlay.parentWidget() is shell
    assert overlay.property("paneMode") == "in-app-slide"
    assert overlay.property("blurDeferred") is False
    assert overlay.property("slideAnimation") == "right-pane"
    assert overlay.property("helmResponsiveLayout") == "single-column"
    scrolls = overlay.findChildren(QScrollArea)
    assert len(scrolls) == 1
    assert scrolls[0].horizontalScrollBarPolicy().name == "ScrollBarAlwaysOff"

    bulb = overlay.findChild(QLabel, "helmActiveBulb")
    assert bulb is not None
    assert bulb.property("pulseStyle") == "qt-pulse"
    assert bulb.property("polish") == "led-bulb"

    overlay.symptom_input.setPlainText("Can't hold aim steady")
    overlay.analyze()
    _app().processEvents()
    assert "live_verified" not in _visible_label_text(overlay)
    assert "no_supported_device" not in _visible_label_text(overlay)
    assert overlay.findChild(QLabel, "helmApplyStatus") is not None

    wide_shell = _shell(tmp_path / "wide")
    wide_shell.resize(1800, 1000)
    wide_shell.show()
    wide_overlay = wide_shell.open_helm_overlay()
    wide_overlay.symptom_input.setPlainText("Can't hold aim steady")
    wide_overlay.analyze()
    _app().processEvents()
    assert wide_overlay.property("helmResponsiveLayout") == "two-column-wide"
    diff_card = wide_overlay.findChild(QFrame, "helmRecommendationCard")
    apply_card = wide_overlay.findChild(QFrame, "helmApplyRevertCard")
    assert diff_card is not None
    assert apply_card is not None
    assert diff_card.geometry().right() <= wide_overlay.findChild(QScrollArea, "helmOverlayScrollArea").viewport().width()
    assert apply_card.isVisible()


def test_post_rc_4f_preflight_audit_report_has_required_detailed_columns():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "post-rc-4f-preflight-data-audit.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    for column in (
        "UI Label",
        "Dashboard Section",
        "Current UI Value",
        "Source of Truth",
        "Code Location",
        "User Meaning",
        "Classification",
        "Simple fix available in this pass?",
        "Fix applied in this pass",
        "Follow-up needed",
    ):
        assert column in text
    assert text.count("|") >= 300


def test_post_rc_4f_main_ui_visible_strings_are_polished(tmp_path):
    _app()

    from PySide6.QtWidgets import QLabel

    shell = _shell(tmp_path, runtime_status=_runtime_status(live=True))
    mapping = shell.page_widgets["mapping"].widget()
    preflight = shell.page_widgets["preflight"].widget()
    overlay = shell.open_helm_overlay()
    overlay.symptom_input.setPlainText("Can't hold aim steady")
    overlay.analyze()
    _app().processEvents()

    visible_text = "\n".join(
        (
            _visible_label_text(mapping),
            _visible_label_text(preflight),
            _visible_label_text(overlay),
            shell.footer.findChild(QLabel, "footerDetail").text(),
        )
    )
    for forbidden in (
        "Post-RC",
        "not merged",
        "telemetry json",
        "hotas_bridge_config_v3.json",
        "blocked_missing_device",
        "no_supported_device",
        "output_verified",
        "live_verified",
        "source of truth",
        "config route",
        "raw dump",
        "workspace/config",
        "Output intent only",
        "Bridge telemetry unavailable",
    ):
        assert forbidden not in visible_text


def test_post_rc_4f_no_runtime_authority_was_added():
    sources = "\n".join(
        (PROJECT_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "v3_app/pages/mapping_page.py",
            "v3_app/pages/preflight_page.py",
            "v3_app/helm/helm_overlay.py",
            "v3_app/widgets/hotas_diagram.py",
        )
    )
    for forbidden in (
        "StartBridge(",
        "StopBridge(",
        "RestartBridge(",
        "PhysicalInputSampler",
        "read_current_state(",
        "auto_save",
        "autosave",
        "VideoWriter",
    ):
        assert forbidden not in sources
