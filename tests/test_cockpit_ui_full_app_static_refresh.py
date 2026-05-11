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
from shared_core.models.workspace import create_default_workspace


PAGE_IDS = (
    "preflight",
    "mapping",
    "profiles",
    "modes",
    "base_tuning",
    "filtering",
    "combat_profile",
    "conditional_rules",
    "effective_response_stack",
    "live_monitor",
    "flight_recorder",
    "help_docs",
    "perf_diagnostics",
)

PAGE_TITLES = (
    "Preflight",
    "Mapping",
    "Profiles",
    "Modes",
    "Base Tuning",
    "Filtering",
    "Combat Profile",
    "Conditional Rules",
    "Effective Response Stack",
    "Live Monitor",
    "Flight Recorder",
    "Help / Docs",
    "Perf / Diagnostics",
)


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status(
    *,
    truth: RuntimeTruth = RuntimeTruth.BLOCKED_MISSING_DEVICE,
    input_status: InputStatus = InputStatus.MISSING,
    output_status: OutputStatus = OutputStatus.VJOY_DETECTED,
    output_verified: bool = False,
) -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=truth,
        input=InputDeviceDetection(status=input_status),
        output=OutputBackendDetection(
            status=output_status,
            backend_name="vJoy" if output_status is not OutputStatus.VJOY_MISSING else None,
            live_output_writes_verified=output_verified,
        ),
        warnings=("No HOTAS input has been verified for live use.",),
        errors=(),
    )


def _state(runtime_status: RuntimePreflightStatus | None = None):
    from v3_app.services.app_state import AppState

    return AppState.from_runtime_status(runtime_status or _runtime_status(), active_page_id="preflight")


def _cockpit_shell(runtime_status: RuntimePreflightStatus | None = None):
    _app()
    from v3_app.ui.cockpit.shell import CockpitShell

    status = runtime_status or _runtime_status()
    return CockpitShell(state=_state(status), workspace=create_default_workspace(), runtime_status=status)


def _visible_text(widget, *, include_advanced: bool = False) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    widgets = widget.findChildren(QLabel) + widget.findChildren(QPushButton)
    parts: list[str] = []
    for child in widgets:
        if not include_advanced and _inside_advanced_or_diagnostics(child):
            continue
        text = child.text().strip()
        if text:
            parts.append(text)
    return " ".join(parts)


def _inside_advanced_or_diagnostics(widget) -> bool:
    parent = widget
    while parent is not None:
        object_name = parent.objectName()
        if parent.property("cockpitAdvancedPanel") is True:
            return True
        if object_name in {"cockpitPage_perf_diagnostics", "page_perf_diagnostics"}:
            return True
        parent = parent.parentWidget()
    return False


def test_cockpit_ui_mode_resolution_and_legacy_fallback_are_explicit(monkeypatch):
    _app()

    from v3_app.app import build_window, resolve_ui_mode
    from v3_app.ui.cockpit.shell import CockpitShell
    from v3_app.ui.shell import HelmForgeShell

    assert resolve_ui_mode({}) == "cockpit"
    assert resolve_ui_mode({"HELMFORGE_UI_MODE": "cockpit"}) == "cockpit"
    assert resolve_ui_mode({"HELMFORGE_UI_MODE": "legacy"}) == "legacy"
    assert resolve_ui_mode({"HELMFORGE_UI_MODE": "unexpected"}) == "legacy"

    monkeypatch.setenv("HELMFORGE_UI_MODE", "legacy")
    legacy = build_window(title="Legacy", state=_state())
    assert isinstance(legacy.shell, HelmForgeShell)
    assert not isinstance(legacy.shell, CockpitShell)

    monkeypatch.setenv("HELMFORGE_UI_MODE", "cockpit")
    cockpit = build_window(title="Cockpit", state=_state())
    assert isinstance(cockpit.shell, CockpitShell)
    assert cockpit.shell.property("uiMode") == "cockpit"


def test_cockpit_component_construction_offscreen():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.ui.cockpit.components import (
        AdvancedPanel,
        ChecklistPanel,
        CockpitActionStrip,
        CockpitStatusBanner,
        DataGridCard,
        FlowRow,
        MetricTile,
        ReadinessRail,
        SystemTile,
    )
    from v3_app.ui.cockpit.page_frame import CockpitPage

    legacy = QWidget()
    widgets = [
        CockpitStatusBanner("Runtime checks", "HOTAS not connected", "Connect the device before live output.", tone="warning"),
        ReadinessRail((("Input", "waiting", "warning"), ("Telemetry", "ready", "success"))),
        SystemTile("Device / Driver", "Waiting", "No supported HOTAS is connected.", facts=("Driver installed", "Workspace ready")),
        MetricTile("Axis routes", "4", "configured", tone="success"),
        FlowRow("Physical input", "Logical function", "Output intent"),
        ChecklistPanel("Warnings / Actions", (("waiting", "Connect HOTAS"), ("ok", "Workspace loaded"))),
        DataGridCard("Routing Details", "Detailed tables remain available."),
        AdvancedPanel("Advanced Technical Details", "Raw runtime fields live here.", legacy),
        CockpitActionStrip((QPushButton("Save Workspace"), QPushButton("Apply Workspace"))),
        CockpitPage(title="Preflight", mission="Verify readiness.", banner=None, rail=None, body=QWidget()),
    ]

    for widget in widgets:
        widget.ensurePolished()
        assert widget.objectName()


def test_cockpit_shell_contains_all_existing_pages_and_static_strips():
    shell = _cockpit_shell()

    from PySide6.QtWidgets import QWidget

    assert shell.property("uiMode") == "cockpit"
    assert set(shell.page_widgets) == set(PAGE_IDS)
    assert shell.findChild(QWidget, "appSidebar") is not None
    assert shell.findChild(QWidget, "appHeader") is not None
    assert shell.findChild(QWidget, "appFooter") is not None
    assert shell.findChild(QWidget, "statusCluster") is not None
    assert shell.findChild(QWidget, "assistantCluster") is not None
    assert "HOTAS Not Connected" in _visible_text(shell.header, include_advanced=True)
    assert "Blocked Missing Device" not in _visible_text(shell.header, include_advanced=True)

    navigation_text = _visible_text(shell, include_advanced=True)
    for title in PAGE_TITLES:
        assert title in navigation_text


def test_each_cockpit_page_constructs_with_frame_identity_and_nonblank_content():
    shell = _cockpit_shell()

    for page_id, title in zip(PAGE_IDS, PAGE_TITLES, strict=True):
        shell.switch_page(page_id)
        page = shell.page_widgets[page_id].widget()
        text = _visible_text(page, include_advanced=True)

        assert page.objectName() == f"cockpitPage_{page_id}"
        assert page.property("cockpitPageFrame") is True
        assert page.findChild(type(page), f"cockpitPage_{page_id}") is None
        assert title in text
        assert len(text) > 120
        assert page.findChild(object, "cockpitPageTitle") is not None
        assert page.findChild(object, "cockpitPageMission") is not None
        assert page.findChildren(object, "cockpitStatusBanner") or page.findChildren(object, "cockpitSystemTile")


def test_preflight_cockpit_dashboard_sections_are_present_and_static():
    shell = _cockpit_shell()
    shell.switch_page("preflight")
    page = shell.page_widgets["preflight"].widget()
    text = _visible_text(page, include_advanced=True)

    assert page.findChild(object, "cockpitPreflightHero") is not None
    assert page.findChild(object, "cockpitReadinessRail") is not None
    for gate in ("Input", "Telemetry", "Workspace", "vJoy", "Output Proof", "Safety"):
        assert gate in text
    for section in (
        "Device / Driver",
        "Bridge / Telemetry",
        "vJoy / Output",
        "Workspace / Config",
        "Input Data",
        "Pipeline / Safety",
    ):
        assert section in text
    assert page.findChildren(object, "cockpitMetricTile")
    assert "Warnings / Actions" in text
    advanced = page.findChild(object, "cockpitAdvancedTechnicalDetails")
    assert advanced is not None
    assert advanced.property("cockpitAdvancedPanel") is True


def test_mapping_cockpit_route_overview_and_details_are_present_without_prototype_copy():
    shell = _cockpit_shell()
    shell.switch_page("mapping")
    page = shell.page_widgets["mapping"].widget()
    text = _visible_text(page, include_advanced=False)

    assert page.findChild(object, "cockpitMappingRouteOverview") is not None
    assert page.findChild(object, "cockpitMappingFlowSummary") is not None
    assert page.findChild(object, "cockpitHotasDiagramPanel") is not None
    assert page.findChild(object, "cockpitMappingDetailsPanel") is not None
    for label in ("Axis routes", "Button routes", "Hat routes", "Conflicts", "Unmapped", "Workspace"):
        assert label in text
    for forbidden in ("Post-RC", "not merged"):
        assert forbidden not in text


def test_cockpit_normal_ui_wording_hides_raw_internal_strings_outside_advanced_and_diagnostics():
    shell = _cockpit_shell()
    forbidden = (
        "Post-RC",
        "not merged",
        "blocked_missing_device",
        "no_supported_device",
        "live_verified",
        "output_verified",
        "hotas_bridge_config_v3.json",
        "source of truth",
        "telemetry json",
        "config route",
        "raw dump",
        "debug dump",
    )

    for page_id in PAGE_IDS:
        shell.switch_page(page_id)
        page = shell.page_widgets[page_id].widget()
        text = _visible_text(page, include_advanced=False)
        for raw in forbidden:
            assert raw.lower() not in text.lower(), f"{raw!r} leaked on {page_id}"


def test_cockpit_navigation_all_pages_and_static_actions_do_not_raise():
    shell = _cockpit_shell()

    for page_id in PAGE_IDS:
        shell.switch_page(page_id)
        assert shell.active_page_id == page_id
        assert shell.page_widgets[page_id].widget() is not None

    shell.import_profile_placeholder()
    shell.revert_workspace()
    shell.save_workspace()
    assert "Saved" in _visible_text(shell, include_advanced=True)


def test_cockpit_runtime_safety_static_ui_modules_do_not_import_or_use_forbidden_runtime_paths():
    project_root = Path(__file__).resolve().parents[1]
    scanned_paths = [
        project_root / "v3_app" / "ui" / "cockpit",
        project_root / "v3_app" / "theme" / "cockpit_tokens.py",
        project_root / "v3_app" / "theme" / "cockpit_qss.py",
    ]
    joined = "\n".join(
        path.read_text(encoding="utf-8")
        for root in scanned_paths
        for path in ([root] if root.is_file() else root.rglob("*.py"))
    )

    forbidden = (
        "QGraphicsBlurEffect",
        "QGraphicsOpacityEffect",
        "QPropertyAnimation",
        "setGraphicsEffect",
        "pyvjoy",
        "hardware polling",
        "BridgeCommandClient",
        "EmbeddedBridgeRuntime",
        "live_output_writes_verified =",
        "auto_save",
    )
    for token in forbidden:
        assert token not in joined


def test_cockpit_docs_record_default_mode_legacy_preservation_and_static_first_rule():
    project_root = Path(__file__).resolve().parents[1]
    refresh = project_root / "docs" / "HelmForge" / "cockpit-ui-v2-full-app-static-refresh.md"
    inventory = project_root / "docs" / "HelmForge" / "cockpit-ui-v2-page-inventory.md"

    refresh_text = refresh.read_text(encoding="utf-8")
    inventory_text = inventory.read_text(encoding="utf-8")

    assert "HELMFORGE_UI_MODE=legacy" in refresh_text
    assert "HELMFORGE_UI_MODE=cockpit" in refresh_text
    assert "Default/unset mode: Cockpit" in refresh_text
    assert "No animations, drawers, blur effects, opacity effects, or graphics effects" in refresh_text
    for title in PAGE_TITLES:
        assert f"| {title} |" in inventory_text
