from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from PySide6.QtWidgets import QFrame, QGridLayout, QVBoxLayout, QWidget

from shared_core.models.runtime import InputStatus, OutputStatus, RuntimePreflightStatus, RuntimeTruth
from shared_core.models.workspace import WorkspaceConfig
from v3_app.pages.placeholders import PageDefinition
from v3_app.services.app_state import AppState
from v3_app.ui.cockpit.components import (
    AdvancedPanel,
    ChecklistPanel,
    CockpitStatusBanner,
    DataGridCard,
    FlowRow,
    MetricTile,
    ReadinessRail,
    SystemTile,
)
from v3_app.ui.cockpit.page_frame import CockpitPage


def build_cockpit_page(
    *,
    page_id: str,
    page: PageDefinition,
    legacy_page: QWidget,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    workspace: WorkspaceConfig,
) -> CockpitPage:
    legacy_page.setProperty("cockpitLegacyWrapped", True)
    if page_id == "preflight":
        return _preflight_page(page, legacy_page, state, runtime_status, workspace)
    if page_id == "mapping":
        return _mapping_page(page, legacy_page, state, runtime_status, workspace)
    return _standard_page(page_id, page, legacy_page, state, runtime_status, workspace)


def _preflight_page(
    page: PageDefinition,
    legacy_page: QWidget,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    workspace: WorkspaceConfig,
) -> CockpitPage:
    banner = CockpitStatusBanner(
        "Preflight Command Check",
        _runtime_headline(runtime_status),
        _runtime_explanation(runtime_status),
        next_action=_runtime_next_action(runtime_status),
        tone=_runtime_tone(runtime_status),
        object_name="cockpitPreflightHero",
    )
    rail = ReadinessRail(_readiness_items(runtime_status), object_name="cockpitReadinessRail")

    body = _body_container("cockpitPreflightBody")
    layout = body.layout()
    assert isinstance(layout, QVBoxLayout)

    metric_grid = _grid_section("cockpitPreflightInputMetrics")
    counts = _mapping_counts(workspace)
    _add_metrics(
        metric_grid,
        (
            MetricTile("Axis routes", str(counts["axis"]), "input channels", tone="info"),
            MetricTile("Button routes", str(counts["button"]), "switch bindings", tone="info"),
            MetricTile("Hat routes", str(counts["hat"]), "POV routes", tone="info"),
            MetricTile("Detected devices", str(len(runtime_status.detected_device_names)), "reported by preflight", tone=_input_tone(runtime_status)),
        ),
    )
    layout.addWidget(metric_grid)

    systems = _grid_section("cockpitPreflightSystemGrid")
    tiles = (
        SystemTile(
            "Device / Driver",
            _input_status_text(runtime_status),
            "Physical HOTAS detection and driver readiness stay read-only in the UI.",
            facts=(
                f"Target: {runtime_status.target_hardware.primary_device_name}",
                f"Driver: {'Ready' if state.runtime.driver_detected else 'Check required'}",
            ),
            tone=_input_tone(runtime_status),
        ),
        SystemTile(
            "Bridge / Telemetry",
            "Telemetry waiting" if runtime_status.truth is not RuntimeTruth.LIVE_VERIFIED else "Telemetry verified",
            "The Bridge remains the owner of runtime checks; Cockpit mode only displays the reported state.",
            facts=("Live source shown when telemetry arrives", "No new polling added"),
            tone=_runtime_tone(runtime_status),
        ),
        SystemTile(
            "vJoy / Output",
            _output_status_text(runtime_status),
            "Output readiness is shown without changing write-loop or verification semantics.",
            facts=(
                f"Backend: {runtime_status.detected_output_backend_name or 'Not selected'}",
                f"Output proof: {_verified_text(runtime_status.live_output_writes_verified)}",
            ),
            tone=_output_tone(runtime_status),
        ),
        SystemTile(
            "Workspace / Config",
            "Workspace loaded",
            "The current workspace draft is available to the UI and remains under the existing save/apply contract.",
            facts=(f"Profile: {_active_profile_name(workspace)}", f"Saved state: {'Saved' if state.saved else 'Unsaved changes'}"),
            tone="success" if state.saved else "warning",
        ),
        SystemTile(
            "Input Data",
            "Routes staged",
            "Axis, button, and hat routes are visible for operator review before live use.",
            facts=(f"{counts['axis']} axes", f"{counts['button']} buttons", f"{counts['hat']} hats"),
            tone="info",
        ),
        SystemTile(
            "Pipeline / Safety",
            "Safety gated",
            "Full live readiness still requires input, telemetry, workspace, output proof, and safety checks.",
            facts=("No output claim is made from UI launch", "Advanced details stay isolated below"),
            tone=_runtime_tone(runtime_status),
        ),
    )
    _add_tiles(systems, tiles)
    layout.addWidget(systems)

    checklist_rows = _preflight_checklist(runtime_status, state)
    layout.addWidget(ChecklistPanel("Warnings / Actions", checklist_rows))
    layout.addWidget(
        AdvancedPanel(
            "Advanced Technical Details",
            "Detailed Legacy preflight controls and raw runtime fields remain static and always visible here.",
            legacy_page,
            object_name="cockpitAdvancedTechnicalDetails",
        )
    )

    return CockpitPage(
        title=page.title,
        mission="Verify the cockpit stack before live use: input, telemetry, workspace, output proof, and safety.",
        banner=banner,
        rail=rail,
        body=body,
        object_name="cockpitPage_preflight",
    )


def _mapping_page(
    page: PageDefinition,
    legacy_page: QWidget,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    workspace: WorkspaceConfig,
) -> CockpitPage:
    counts = _mapping_counts(workspace)
    conflicts = _mapping_conflicts(workspace)
    unmapped = _unmapped_count(workspace)
    banner = CockpitStatusBanner(
        "Route Control",
        "Mapping workspace ready" if conflicts == 0 else "Mapping conflicts need review",
        "Routes stay in the workspace draft until Apply Workspace and Save Workspace are used.",
        next_action="Review conflicts before live output." if conflicts else "Inspect or edit routes below.",
        tone="success" if conflicts == 0 else "warning",
    )
    rail = ReadinessRail(
        (
            ("Axis", f"{counts['axis']} routes", "success"),
            ("Buttons", f"{counts['button']} routes", "success"),
            ("Hats", f"{counts['hat']} routes", "success"),
            ("Conflicts", str(conflicts), "success" if conflicts == 0 else "warning"),
            ("Unmapped", str(unmapped), "success" if unmapped == 0 else "warning"),
            ("Workspace", "Draft safe", "info" if not state.saved else "success"),
        )
    )

    body = _body_container("cockpitMappingBody")
    layout = body.layout()
    assert isinstance(layout, QVBoxLayout)

    overview = _grid_section("cockpitMappingRouteOverview")
    _add_metrics(
        overview,
        (
            MetricTile("Axis routes", str(counts["axis"]), "flight channels", tone="info"),
            MetricTile("Button routes", str(counts["button"]), "button intents", tone="info"),
            MetricTile("Hat routes", str(counts["hat"]), "POV mappings", tone="info"),
            MetricTile("Conflicts", str(conflicts), "duplicate outputs", tone="success" if conflicts == 0 else "warning"),
            MetricTile("Unmapped", str(unmapped), "needs review", tone="success" if unmapped == 0 else "warning"),
            MetricTile("Workspace", _active_profile_name(workspace), "active profile", tone="success"),
        ),
    )
    layout.addWidget(overview)

    flow_panel = DataGridCard(
        "Live Route Summary",
        "Representative physical input to logical function to output intent routes.",
        object_name="cockpitMappingFlowSummary",
    )
    flow_layout = flow_panel.layout()
    assert isinstance(flow_layout, QVBoxLayout)
    for route in workspace.mappings.axis_routes[:4]:
        flow_layout.addWidget(FlowRow(route.raw_axis_channel, route.function_name, route.runtime_vjoy_output or "Draft mapping"))
    if not workspace.mappings.axis_routes:
        flow_layout.addWidget(FlowRow("Physical input", "Logical function", "Draft mapping"))
    layout.addWidget(flow_panel)

    layout.addWidget(
        SystemTile(
            "HOTAS Diagram",
            "Interactive diagram available",
            "The existing stable diagram and editor stay in the detailed mapping panel below for this static pass.",
            facts=("Diagram state reviewed", "Route tables ready", "Editor stays in the workspace draft"),
            tone="info",
            object_name="cockpitHotasDiagramPanel",
        )
    )
    layout.addWidget(
        AdvancedPanel(
            "Routing Tables and Details",
            "The stable Mapping editor, diagram, tables, and route inspector are reused here with Cockpit styling.",
            legacy_page,
            object_name="cockpitMappingDetailsPanel",
        )
    )

    return CockpitPage(
        title=page.title,
        mission="Operate physical input to logical function to output intent routing without changing the mapping model.",
        banner=banner,
        rail=rail,
        body=body,
        object_name="cockpitPage_mapping",
    )


def _standard_page(
    page_id: str,
    page: PageDefinition,
    legacy_page: QWidget,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    workspace: WorkspaceConfig,
) -> CockpitPage:
    spec = _page_spec(page_id, state, runtime_status, workspace)
    banner = CockpitStatusBanner(
        spec["banner_title"],
        spec["state"],
        spec["explanation"],
        next_action=spec["next_action"],
        tone=spec["tone"],
    )
    rail = ReadinessRail(tuple(spec["rail"]))
    body = _body_container(f"cockpit{_pascal(page_id)}Body")
    layout = body.layout()
    assert isinstance(layout, QVBoxLayout)

    overview = _grid_section(f"cockpit{_pascal(page_id)}Overview")
    _add_metrics(overview, tuple(spec["metrics"]))
    layout.addWidget(overview)
    for widget in spec["sections"]:
        layout.addWidget(widget)

    if page_id == "perf_diagnostics":
        layout.addWidget(
            DataGridCard(
                "Diagnostic Workbench",
                "Raw runtime, environment, and Bridge diagnostic values are allowed on this page and remain read-only unless an existing command is used.",
                content=legacy_page,
                object_name="cockpitDiagnosticsDetailsPanel",
            )
        )
    else:
        layout.addWidget(
            AdvancedPanel(
                spec["details_title"],
                spec["details_body"],
                legacy_page,
                object_name=f"cockpit{_pascal(page_id)}DetailsPanel",
            )
        )

    return CockpitPage(
        title=page.title,
        mission=spec["mission"],
        banner=banner,
        rail=rail,
        body=body,
        object_name=f"cockpitPage_{page_id}",
    )


def _page_spec(
    page_id: str,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    workspace: WorkspaceConfig,
) -> dict[str, object]:
    counts = _mapping_counts(workspace)
    active_profile = _active_profile_name(workspace)
    rule_count = len(workspace.rules.rules)
    enabled_rules = sum(1 for rule in workspace.rules.rules if rule.enabled)
    selected_axis = state.selected_axis
    axis_key = selected_axis.casefold().replace(" ", "_")
    tuning = workspace.tuning.axes.get(axis_key)
    filtering = workspace.filtering.axes.get(axis_key)
    combat = workspace.combat.axes.get(axis_key)

    base = {
        "mission": "Review this workspace through the Cockpit frame while preserving the existing controls below.",
        "banner_title": "Cockpit Workspace",
        "state": "Workspace ready",
        "explanation": "The existing page is reused under a static Cockpit status hierarchy.",
        "next_action": "Use the detailed controls below when edits are needed.",
        "tone": "info",
        "rail": _readiness_items(runtime_status),
        "metrics": (
            MetricTile("Axis routes", str(counts["axis"]), "available", tone="info"),
            MetricTile("Button routes", str(counts["button"]), "available", tone="info"),
            MetricTile("Profile", active_profile, "workspace", tone="success"),
        ),
        "sections": (),
        "details_title": "Detailed Controls",
        "details_body": "Existing page controls remain available in this static Cockpit pass.",
    }

    specs: dict[str, dict[str, object]] = {
        "profiles": {
            "mission": "Manage workspace profiles with clear active, saved, import, and export posture.",
            "banner_title": "Profile Bay",
            "state": f"{active_profile} active",
            "explanation": "Profile data and save/apply state are preserved from the existing workspace.",
            "metrics": (
                MetricTile("Profiles", str(len(workspace.profiles.profiles)), "available", tone="info"),
                MetricTile("Active profile", active_profile, "selected", tone="success"),
                MetricTile("Workspace", "Saved" if state.saved else "Unsaved", "draft state", tone="success" if state.saved else "warning"),
            ),
            "sections": (
                SystemTile("Profile Library", "Static list", "Profile cards and actions below use the existing profile workflow.", facts=("Import and save actions stay in the footer", "No auto-save added"), tone="info"),
            ),
            "details_title": "Profile Library and Actions",
        },
        "modes": {
            "mission": "Review precision, combat, zoom, and mode stacking relationships.",
            "banner_title": "Mode Control",
            "state": "Mode stack available",
            "explanation": "Button bindings and stack mode are shown without changing mode evaluation.",
            "metrics": (
                MetricTile("Precision holds", str(len(workspace.modes.precision_hold_buttons)), "bindings", tone="info"),
                MetricTile("Combat triggers", str(len(workspace.modes.combat_trigger_buttons)), "bindings", tone="info"),
                MetricTile("Stack mode", workspace.modes.precision_combat_stack_mode.value.title(), "relationship", tone="success"),
            ),
            "sections": (
                FlowRow("Precision", "Combat stack", workspace.modes.precision_combat_stack_mode.value.title()),
                SystemTile("Mode Bindings", "Review ready", "Binding summaries are kept as chips and detailed controls below.", facts=("Precision / Combat", "Zoom / Extra modes"), tone="info"),
            ),
            "details_title": "Mode Details",
        },
        "base_tuning": {
            "mission": "Shape the selected axis response while keeping tuning math unchanged.",
            "banner_title": "Base Response Instrument",
            "state": f"{selected_axis} selected",
            "explanation": "Curve, deadzone, scale, and output limit controls remain the existing workspace values.",
            "metrics": (
                MetricTile("Curve", f"{getattr(tuning, 'curve_strength', 0.0):.2f}", "strength", tone="info"),
                MetricTile("Deadzone", f"{getattr(tuning, 'deadzone', 0.0):.2f}", "center", tone="info"),
                MetricTile("Output scale", f"{getattr(tuning, 'output_scale', 1.0):.2f}", "authority", tone="success"),
            ),
            "sections": (
                SystemTile("Response Preview", "Instrument panel", "Existing graph and parameter controls are styled as cockpit panels below.", facts=(f"Axis: {selected_axis}", "Math unchanged"), tone="info"),
                ChecklistPanel("Advisory", (("ok", "Review curve before applying workspace."), ("waiting", "Live output still depends on runtime readiness."))),
            ),
            "details_title": "Base Tuning Controls",
        },
        "filtering": {
            "mission": "Tune smoothing and slew response while preserving filtering math.",
            "banner_title": "Filter Instrument",
            "state": f"{selected_axis} selected",
            "explanation": "Center, edge, same-direction, and reverse-direction controls remain configuration-only.",
            "metrics": (
                MetricTile("Center alpha", f"{getattr(filtering, 'center_alpha', 0.0):.2f}", "smoothing", tone="info"),
                MetricTile("Edge alpha", f"{getattr(filtering, 'edge_alpha', 0.0):.2f}", "smoothing", tone="info"),
                MetricTile("Reverse slew", f"{getattr(filtering, 'reverse_slew_limit', 0.0):.2f}", "limit", tone="warning"),
            ),
            "sections": (
                SystemTile("Filter Preview", "Instrument panel", "The existing preview and controls are restyled below.", facts=(f"Axis: {selected_axis}", "No math changes"), tone="info"),
                ChecklistPanel("Advisory", (("ok", "Use filtering to smooth input without hiding runtime state."),)),
            ),
            "details_title": "Filtering Controls",
        },
        "combat_profile": {
            "mission": "Review combat-focused response shaping without changing combat profile math.",
            "banner_title": "Combat Response",
            "state": f"{selected_axis} selected",
            "explanation": "Combat curve, scale, and trigger context are surfaced as cockpit metrics.",
            "metrics": (
                MetricTile("Combat curve", f"{getattr(combat, 'combat_curve', 0.0):.2f}", "curve", tone="info"),
                MetricTile("Combat scale", f"{getattr(combat, 'combat_scale', 0.0):.2f}", "authority", tone="success"),
                MetricTile("Trigger buttons", str(len(workspace.modes.combat_trigger_buttons)), "bindings", tone="warning"),
            ),
            "sections": (
                SystemTile("Combat Context", "Configuration only", "Mode and trigger data come from the workspace and do not activate live output.", facts=("No game injection", "No backend rewrite"), tone="info"),
            ),
            "details_title": "Combat Profile Controls",
        },
        "conditional_rules": {
            "mission": "Inspect conditional rule readiness, counts, and condition to action flow.",
            "banner_title": "Rule System",
            "state": f"{enabled_rules} enabled of {rule_count}",
            "explanation": "Rule evaluation logic is unchanged; this pass only reorganizes presentation.",
            "metrics": (
                MetricTile("Rules", str(rule_count), "total", tone="info"),
                MetricTile("Enabled", str(enabled_rules), "active candidates", tone="success" if enabled_rules else "warning"),
                MetricTile("Disabled", str(rule_count - enabled_rules), "parked", tone="warning"),
            ),
            "sections": tuple(_rule_flow_rows(workspace)),
            "details_title": "Rule List and Editor",
        },
        "effective_response_stack": {
            "mission": "Follow the selected axis from raw input through final output intent.",
            "banner_title": "Response Pipeline",
            "state": f"{selected_axis} pipeline staged",
            "explanation": "Stage order and calculations remain owned by the shared response stack.",
            "metrics": (
                MetricTile("Selected axis", selected_axis, "pipeline", tone="info"),
                MetricTile("Stages", "6", "raw to final", tone="success"),
                MetricTile("Rules", str(enabled_rules), "enabled", tone="warning" if enabled_rules == 0 else "success"),
            ),
            "sections": (
                FlowRow("Raw Input", "Base Tuning", "Filtering"),
                FlowRow("Modes", "Rules", "Final Output"),
                SystemTile("Pipeline Preview", "Instrument panel", "Existing stack cards and graph panels are kept below with Cockpit styling.", facts=("No stack calculation changes",), tone="info"),
            ),
            "details_title": "Effective Stack Details",
        },
        "live_monitor": {
            "mission": "Watch telemetry, axis levels, buttons, hats, and output intent with truthful stale or missing states.",
            "banner_title": "Live Monitor",
            "state": _runtime_headline(runtime_status),
            "explanation": "Telemetry semantics remain unchanged; the page only receives the existing frame data.",
            "metrics": (
                MetricTile("Axes", str(counts["axis"]), "monitored", tone="info"),
                MetricTile("Buttons", str(counts["button"]), "monitored", tone="info"),
                MetricTile("Runtime", _runtime_headline(runtime_status), "reported", tone=_runtime_tone(runtime_status)),
            ),
            "sections": (
                SystemTile("Telemetry Source", _input_status_text(runtime_status), "Raw and final comparisons remain in the existing monitor below.", facts=("Stale data is shown as waiting", "No polling changes"), tone=_runtime_tone(runtime_status)),
            ),
            "details_title": "Live Monitor Instruments",
        },
        "flight_recorder": {
            "mission": "Review recorder capability, settings, clip library, and metadata-only capture truth.",
            "banner_title": "Recorder Bay",
            "state": "Recorder shell ready",
            "explanation": "Recorder backend behavior, capture capability, and metadata-only truth labels are preserved.",
            "metrics": (
                MetricTile("Capture mode", "Metadata", "truth labeled", tone="warning"),
                MetricTile("Library", "Available", "clip review", tone="info"),
                MetricTile("Runtime", _runtime_headline(runtime_status), "reported", tone=_runtime_tone(runtime_status)),
            ),
            "sections": (
                SystemTile("Recording Capability", "Truth labeled", "No real capture is claimed when the backend is unavailable.", facts=("No encoding changes", "No capture behavior changes"), tone="warning"),
            ),
            "details_title": "Recorder Controls and Library",
        },
        "help_docs": {
            "mission": "Browse built-in guidance, topic navigation, and parameter reference in a cockpit document surface.",
            "banner_title": "Support Library",
            "state": "Guide available",
            "explanation": "Existing help topics are reorganized visually without writing a new manual.",
            "metrics": (
                MetricTile("Topics", "Built in", "searchable", tone="info"),
                MetricTile("Navigation", "Ready", "topic tree", tone="success"),
                MetricTile("Helm", "Available", "assistant entry", tone="info"),
            ),
            "sections": (
                SystemTile("Topic Tiles", "Organized", "Search, article navigation, and page links stay on the existing Help / Docs page.", facts=("No docs rewrite in UI code",), tone="info"),
            ),
            "details_title": "Help / Docs Browser",
        },
        "perf_diagnostics": {
            "mission": "Inspect environment, runtime, Bridge, device, and diagnostics details intentionally.",
            "banner_title": "Diagnostics",
            "state": "Diagnostics available",
            "explanation": "Raw values are allowed here because this is the dedicated diagnostic workspace.",
            "metrics": (
                MetricTile("Pages", "13", "registered", tone="success"),
                MetricTile("Runtime", _runtime_headline(runtime_status), "reported", tone=_runtime_tone(runtime_status)),
                MetricTile("Workspace", "Loaded", "diagnostic context", tone="info"),
            ),
            "sections": (
                SystemTile("Environment / Runtime", "Read-only", "Diagnostics remain grouped and do not change runtime authority.", facts=("Bridge/device details stay diagnostic",), tone="info"),
            ),
            "details_title": "Diagnostic Workbench",
        },
    }
    override = specs.get(page_id, {})
    merged = {**base, **override}
    merged.setdefault("next_action", base["next_action"])
    merged.setdefault("tone", base["tone"])
    merged.setdefault("rail", base["rail"])
    merged.setdefault("details_body", base["details_body"])
    return merged


def _body_container(object_name: str) -> QWidget:
    body = QWidget()
    body.setObjectName(object_name)
    layout = QVBoxLayout(body)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(14)
    return body


def _grid_section(object_name: str) -> QFrame:
    frame = QFrame()
    frame.setObjectName(object_name)
    frame.setProperty("cockpitComponent", "gridSection")
    layout = QGridLayout(frame)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(12)
    layout.setVerticalSpacing(12)
    return frame


def _add_metrics(frame: QFrame, metrics: Iterable[MetricTile]) -> None:
    layout = frame.layout()
    assert isinstance(layout, QGridLayout)
    for index, metric in enumerate(metrics):
        layout.addWidget(metric, index // 3, index % 3)


def _add_tiles(frame: QFrame, tiles: Iterable[SystemTile]) -> None:
    layout = frame.layout()
    assert isinstance(layout, QGridLayout)
    for index, tile in enumerate(tiles):
        layout.addWidget(tile, index // 2, index % 2)


def _readiness_items(runtime_status: RuntimePreflightStatus) -> tuple[tuple[str, str, str], ...]:
    return (
        ("Input", _input_status_text(runtime_status), _input_tone(runtime_status)),
        ("Telemetry", "Live verified" if runtime_status.truth is RuntimeTruth.LIVE_VERIFIED else "Waiting", _runtime_tone(runtime_status)),
        ("Workspace", "Loaded", "success"),
        ("vJoy", _output_status_text(runtime_status), _output_tone(runtime_status)),
        ("Output Proof", _verified_text(runtime_status.live_output_writes_verified), "success" if runtime_status.live_output_writes_verified else "warning"),
        ("Safety", "Gated", "success" if runtime_status.truth is RuntimeTruth.LIVE_VERIFIED else "warning"),
    )


def _mapping_counts(workspace: WorkspaceConfig) -> Counter[str]:
    return Counter(
        {
            "axis": len(workspace.mappings.axis_routes),
            "button": len(workspace.mappings.button_routes),
            "hat": len(workspace.mappings.hat_routes),
        }
    )


def _mapping_conflicts(workspace: WorkspaceConfig) -> int:
    outputs = [route.runtime_vjoy_output for route in workspace.mappings.axis_routes if route.runtime_vjoy_output]
    buttons = [route.output_button for route in workspace.mappings.button_routes if route.output_button > 0]
    return sum(count - 1 for count in Counter(outputs).values() if count > 1) + sum(
        count - 1 for count in Counter(buttons).values() if count > 1
    )


def _unmapped_count(workspace: WorkspaceConfig) -> int:
    return sum(1 for route in workspace.mappings.axis_routes if not route.runtime_vjoy_output) + sum(
        1 for route in workspace.mappings.button_routes if route.output_button <= 0
    )


def _preflight_checklist(runtime_status: RuntimePreflightStatus, state: AppState) -> tuple[tuple[str, str], ...]:
    rows = [
        ("ok" if state.saved else "waiting", "Save or apply any workspace draft before live use."),
        ("ok" if runtime_status.output.status is not OutputStatus.VJOY_MISSING else "waiting", "Verify the virtual output backend before live output."),
        ("ok" if runtime_status.live_output_writes_verified else "waiting", "Output proof must come from the existing runtime verification path."),
    ]
    if runtime_status.input.status is InputStatus.MISSING:
        rows.insert(0, ("waiting", "Connect the supported HOTAS before live checks can pass."))
    elif runtime_status.input.status is InputStatus.ERROR:
        rows.insert(0, ("error", "Resolve the input device error before continuing."))
    else:
        rows.insert(0, ("ok", "HOTAS input detection is available."))
    return tuple(rows)


def _rule_flow_rows(workspace: WorkspaceConfig) -> Iterable[FlowRow]:
    for rule in workspace.rules.rules[:3]:
        condition = f"{rule.reference_axis} {rule.comparator} {rule.threshold:.2f}"
        action = f"{rule.target_axis} {rule.parameter}"
        state = "Enabled" if rule.enabled else "Disabled"
        yield FlowRow(condition, state, action)
    if not workspace.rules.rules:
        yield FlowRow("Condition", "Rule state", "Action")


def _runtime_headline(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and runtime_status.live_output_writes_verified:
        return "Live checks passed"
    if runtime_status.truth is RuntimeTruth.DETECTED_UNVERIFIED:
        return "Output waiting for proof"
    if runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DEVICE:
        return "HOTAS not connected"
    if runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DRIVER:
        return "Driver or output backend missing"
    if runtime_status.truth is RuntimeTruth.ERROR:
        return "Runtime error"
    return "Simulation mode"


def _runtime_explanation(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and runtime_status.live_output_writes_verified:
        return "Input, telemetry, and output proof have all been reported ready by the runtime."
    if runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DEVICE:
        return "The cockpit can be configured, but live checks wait for the supported HOTAS."
    if runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DRIVER:
        return "The workspace can be edited while driver or output setup is completed."
    if runtime_status.truth is RuntimeTruth.DETECTED_UNVERIFIED:
        return "Input is detected, but output proof has not been verified by the runtime."
    if runtime_status.truth is RuntimeTruth.ERROR:
        return "A runtime error is being reported; diagnostics can show the raw details."
    return "The app is operating in a simulation-safe presentation state."


def _runtime_next_action(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DEVICE:
        return "Next action: connect the supported HOTAS and run Preflight Check."
    if runtime_status.truth is RuntimeTruth.BLOCKED_MISSING_DRIVER:
        return "Next action: complete driver and virtual output setup."
    if runtime_status.truth is RuntimeTruth.DETECTED_UNVERIFIED:
        return "Next action: verify output through the existing runtime path."
    if runtime_status.truth is RuntimeTruth.ERROR:
        return "Next action: open diagnostics for raw runtime details."
    return "Next action: review the workspace, then apply and save when ready."


def _runtime_tone(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and runtime_status.live_output_writes_verified:
        return "success"
    if runtime_status.truth in {RuntimeTruth.DETECTED_UNVERIFIED, RuntimeTruth.SIMULATED}:
        return "warning"
    if runtime_status.truth is RuntimeTruth.ERROR:
        return "danger"
    return "warning"


def _input_status_text(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.input.status is InputStatus.DETECTED:
        return "HOTAS detected"
    if runtime_status.input.status is InputStatus.ERROR:
        return "Input error"
    if runtime_status.input.status is InputStatus.NOT_CHECKED:
        return "Input not checked"
    return "HOTAS not connected"


def _output_status_text(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.output.status is OutputStatus.OUTPUT_VERIFIED:
        return "Output verified"
    if runtime_status.output.status is OutputStatus.VJOY_DETECTED:
        return "vJoy detected"
    if runtime_status.output.status is OutputStatus.VJOY_MISSING:
        return "vJoy missing"
    if runtime_status.output.status is OutputStatus.OUTPUT_ERROR:
        return "Output error"
    return "Output not checked"


def _input_tone(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.input.status is InputStatus.DETECTED:
        return "success"
    if runtime_status.input.status is InputStatus.ERROR:
        return "danger"
    return "warning"


def _output_tone(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.output.status is OutputStatus.OUTPUT_VERIFIED or runtime_status.live_output_writes_verified:
        return "success"
    if runtime_status.output.status is OutputStatus.OUTPUT_ERROR:
        return "danger"
    return "warning"


def _verified_text(value: bool) -> str:
    return "Verified" if value else "Not verified"


def _active_profile_name(workspace: WorkspaceConfig) -> str:
    for profile in workspace.profiles.profiles:
        if profile.profile_id == workspace.profiles.active_profile_id:
            return profile.name
    return workspace.active_profile.replace("-", " ").title()


def _pascal(page_id: str) -> str:
    return "".join(part.title() for part in page_id.split("_"))
