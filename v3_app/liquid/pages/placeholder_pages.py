from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtWidgets import QLabel, QSizePolicy

from v3_app.liquid.components import (
    LiquidAdvancedSection,
    LiquidDetailPanel,
    LiquidHeroPanel,
    LiquidInspectorPanel,
)
from v3_app.liquid.flow_components import ChecklistPanel, RouteFlowRow, SignalPipelineStage
from v3_app.liquid.glass import glass_panel
from v3_app.liquid.instruments import AxisBarPair, CapabilityRail, ControlMarker, MiniCurvePreview
from v3_app.liquid.layout import horizontal_layout, vertical_layout
from v3_app.liquid.models.nav_model import (
    LiquidNavigationModel,
    LiquidRoute,
    build_liquid_navigation_model,
)
from v3_app.liquid.parameter_controls import (
    AxisSelectorPills,
    GuidanceBlock,
    LiveSnapshotBlock,
    NumericParameterControl,
    ParameterRow,
)
from v3_app.liquid.pages.mapping_command_page import create_mapping_command_page
from v3_app.liquid.pages.mapping_edit_pages import (
    create_mapping_advanced_route_tables_page,
    create_mapping_route_details_page,
)
from v3_app.liquid.pages.preflight_command_page import create_preflight_command_page
from v3_app.liquid.pages.tuning_command_pages import (
    create_base_tuning_command_page,
    create_combat_profile_command_page,
    create_conditional_rules_command_page,
    create_filtering_command_page,
)
from v3_app.liquid.pages.analysis_command_pages import (
    create_effective_response_stack_page,
    create_live_monitor_page,
)
from v3_app.liquid.pages.recorder_command_pages import (
    create_capture_backend_truth_page,
    create_clip_library_page,
    create_flight_recorder_page,
)
from v3_app.liquid.status_components import MetricTile, ReadinessGate, StatusChip, TelemetryFreshnessRail, TruthBadge


@dataclass(frozen=True)
class LiquidPlaceholderPageDefinition:
    mode_id: str
    subpage_id: str
    route_key: str
    title: str
    subpage_title: str
    purpose: str
    hero_title: str
    context_title: str
    detail_title: str
    advanced_title: str
    placeholder_notice: str


_PLACEHOLDER_NOTICE = (
    "Liquid Command Deck placeholder route. Placeholder / static shell foundation; "
    "future page rebuild content will replace this route in a later LCD page phase."
)


def _route_definitions(
    model: LiquidNavigationModel,
) -> tuple[LiquidPlaceholderPageDefinition, ...]:
    return tuple(_definition_from_route(route) for route in model.routes)


def _definition_from_route(route: LiquidRoute) -> LiquidPlaceholderPageDefinition:
    return LiquidPlaceholderPageDefinition(
        mode_id=route.mode_id,
        subpage_id=route.subpage_id,
        route_key=route.route_key,
        title=route.mode_display_name,
        subpage_title=route.subpage_display_name,
        purpose=route.purpose,
        hero_title=_hero_title(route),
        context_title=_context_title(route),
        detail_title=_detail_title(route),
        advanced_title=_advanced_title(route),
        placeholder_notice=_PLACEHOLDER_NOTICE,
    )


def _make_factory(definition: LiquidPlaceholderPageDefinition) -> Callable[[], object]:
    return lambda definition=definition: create_liquid_placeholder_page(definition)


def create_liquid_placeholder_page(definition: LiquidPlaceholderPageDefinition):
    route_slot = definition.mode_id
    page = glass_panel(f"liquidPlaceholderPage_{definition.route_key.replace('.', '_')}", role="placeholderPage")
    page.setProperty("routeKey", definition.route_key)
    page.setProperty("modeId", definition.mode_id)
    page.setProperty("subpageId", definition.subpage_id)
    page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    root = vertical_layout(page, margins=(4, 2, 4, 22), spacing=12)

    status_rail = glass_panel(f"liquidModeStatusRail_{route_slot}", role="liquid_status_cluster")
    status_rail.setProperty("routeKey", definition.route_key)
    status_rail.setProperty("liquidRole", "liquid_status_cluster")
    status_rail.setProperty("componentRole", "LiquidPlaceholderHeader")
    status_layout = vertical_layout(status_rail, margins=(14, 10, 14, 10), spacing=7)

    title_region = glass_panel(
        f"liquidPlaceholderHeaderTitleRegion_{route_slot}",
        role="liquid_placeholder_header_title_region",
    )
    title_layout = horizontal_layout(title_region, margins=(0, 0, 0, 0), spacing=10)
    kicker = QLabel("LIQUID COMMAND DECK")
    kicker.setObjectName("liquidPlaceholderKicker")
    title = QLabel(definition.title)
    title.setObjectName("liquidPlaceholderTitle")
    subpage = QLabel(definition.subpage_title)
    subpage.setObjectName("liquidPlaceholderSubpageTitle")
    subpage.setWordWrap(True)
    subpage.setMinimumWidth(0)
    title.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
    title_layout.addWidget(kicker)
    title_layout.addWidget(title)
    title_layout.addWidget(subpage, 1)

    subtitle_region = glass_panel(
        f"liquidPlaceholderHeaderSubtitleRegion_{route_slot}",
        role="liquid_placeholder_header_subtitle_region",
    )
    subtitle_layout = horizontal_layout(subtitle_region, margins=(0, 0, 0, 0), spacing=0)
    purpose = QLabel(definition.purpose)
    purpose.setObjectName("liquidPlaceholderPurpose")
    purpose.setWordWrap(True)
    subtitle_layout.addWidget(purpose)

    status_layout.addWidget(title_region)
    status_layout.addWidget(subtitle_region)

    chip_region = glass_panel(
        f"liquidPlaceholderHeaderChipRegion_{route_slot}",
        role="liquid_placeholder_header_chip_region",
    )
    chip_layout = horizontal_layout(chip_region, margins=(0, 0, 0, 0), spacing=8)
    route_chip = StatusChip(_route_chip_label(definition), state_role="info")
    route_chip.setProperty("routeKey", definition.route_key)
    route_chip.setToolTip(definition.route_key)
    route_chip.setStatusTip(f"Placeholder route key: {definition.route_key}")
    route_chip.setAccessibleName(_route_chip_label(definition))
    route_chip.setAccessibleDescription(f"Route key: {definition.route_key}")
    chip_layout.addWidget(route_chip)
    chip_layout.addWidget(StatusChip("Page rebuild pending", state_role="info"))
    chip_layout.addWidget(StatusChip("Read-only preview", state_role="simulation"))
    chip_layout.addStretch(1)
    status_layout.addWidget(chip_region)

    notice = QLabel(definition.placeholder_notice)
    notice.setObjectName("liquidPlaceholderNotice")
    notice.setWordWrap(True)

    hero = LiquidHeroPanel(
        definition.hero_title,
        f"Static LCD-3 route host for {definition.subpage_title}.",
        object_name=f"liquidHeroRegion_{route_slot}",
        liquid_role="liquid_hero_region",
    )
    hero.setProperty("embeddedOnCommandSurface", True)
    hero.setMinimumHeight(204)
    _add_to_panel(hero, _hero_demo(definition))
    _add_to_panel(hero, notice)

    lower_row = horizontal_layout(spacing=14)
    context_panel = LiquidInspectorPanel(
        definition.context_title,
        "Route-aware context placeholder. Real page data is deferred.",
        object_name=f"liquidContextInspectorRegion_{route_slot}",
        liquid_role="liquid_context_inspector_region",
    )
    _add_to_panel(context_panel, _context_demo(definition))
    detail_panel = LiquidDetailPanel(
        definition.detail_title,
        "Route-aware detail placeholder; no actions are wired in LCD-3.",
        object_name=f"liquidDetailActionRegion_{route_slot}",
        liquid_role="liquid_detail_action_region",
    )
    _add_to_panel(detail_panel, _detail_demo(definition))
    lower_row.addWidget(context_panel, 1)
    lower_row.addWidget(detail_panel, 1)

    advanced = LiquidAdvancedSection(
        definition.advanced_title,
        "Advanced and diagnostic content remains secondary until its page phase.",
        object_name=f"liquidAdvancedRegion_{route_slot}",
        liquid_role="liquid_advanced_region",
    )
    _add_to_panel(advanced, _advanced_demo(definition))
    _add_to_panel(advanced, _route_key_note(definition))

    root.addWidget(status_rail)
    root.addWidget(hero, 3)
    root.addLayout(lower_row, 2)
    root.addWidget(advanced)
    return page


def _route_chip_label(definition: LiquidPlaceholderPageDefinition) -> str:
    words = definition.subpage_title.replace("/", " ").split()
    if not words:
        return "Route surface"
    label = " ".join(word if word.isupper() else word.lower() for word in words)
    return f"{label[0].upper()}{label[1:]} route"


def _route_key_note(definition: LiquidPlaceholderPageDefinition) -> QLabel:
    note = QLabel(f"Placeholder route key: {definition.route_key}")
    note.setObjectName("liquidRouteKeyAdvancedNote")
    note.setWordWrap(True)
    note.setToolTip(definition.route_key)
    note.setAccessibleName("Placeholder route key")
    note.setAccessibleDescription(definition.route_key)
    return note


def _add_to_panel(panel, widget) -> None:
    layout = panel.layout()
    if layout is None:
        return
    insert_at = max(0, layout.count() - 1)
    layout.insertWidget(insert_at, widget)


def _hero_title(route: LiquidRoute) -> str:
    return {
        "preflight.command_readiness": "Go / No-Go Readiness",
        "mapping.hotas_map": "HOTAS Visual Map",
        "mapping.route_details": "Route Details Flow",
        "mapping.advanced_route_tables": "Advanced Route Tables",
        "tuning.base_tuning": "Response Instrument",
        "tuning.filtering": "Filtering Response Instrument",
        "tuning.combat_profile": "Combat Response Instrument",
        "tuning.conditional_rules": "Conditional Rule Flow",
        "analysis.effective_response_stack": "Signal / Live Monitor Instrument",
        "analysis.live_monitor": "Live Monitor Instrument",
        "recorder.flight_recorder": "Capture Capability Deck",
        "recorder.clip_library": "Clip Library / Artifacts",
        "recorder.capture_backend_truth": "Capture Backend Truth",
        "support.help_docs": "Diagnostics / Help Console",
        "support.perf_diagnostics": "Perf / Diagnostics Console",
        "support.setup_runtime_check": "Setup / Runtime Check",
    }[route.route_key]


def _context_title(route: LiquidRoute) -> str:
    return {
        "preflight": "Readiness Context",
        "mapping": "Route Context",
        "tuning": "Axis Context",
        "analysis": "Signal Context",
        "recorder": "Artifact Context",
        "support": "Support Context",
    }[route.mode_id]


def _detail_title(route: LiquidRoute) -> str:
    return {
        "preflight": "Setup Actions",
        "mapping": "Mapping Details",
        "tuning": "Tuning Details",
        "analysis": "Analysis Details",
        "recorder": "Review Details",
        "support": "Guidance Details",
    }[route.mode_id]


def _advanced_title(route: LiquidRoute) -> str:
    return {
        "preflight": "Deferred Proof Gates",
        "mapping": "Future Layer Controls",
        "tuning": "Future Response Stack",
        "analysis": "Deferred Diagnostics",
        "recorder": "Unavailable Capture Path",
        "support": "Advanced Support Queue",
    }[route.mode_id]


def _hero_demo(definition: LiquidPlaceholderPageDefinition):
    route_key = definition.route_key
    if route_key == "preflight.command_readiness":
        return ReadinessGate(
            "Command readiness",
            state_text="Demo gate: Runtime blocked",
            state_role="blocked",
            detail="Static component sample; not the current top-bar runtime truth.",
        )
    if route_key == "mapping.hotas_map":
        return ControlMarker("Stick X", "Mapping intent: Roll", state_role="info")
    if route_key == "mapping.route_details":
        return RouteFlowRow(
            source_label="Physical Stick X",
            function_label="Roll",
            target_label="vJoy X",
            status_role="waiting",
            helper_text="Static route placeholder; Output Intent wording is used until proof exists.",
        )
    if route_key == "mapping.advanced_route_tables":
        return MetricTile("Route tables", "Static", "Advanced route table rebuild is deferred.", state_role="info")
    if route_key == "tuning.base_tuning":
        return MiniCurvePreview("Response preview", state_role="simulation")
    if route_key == "tuning.filtering":
        return AxisBarPair("Filter response", raw_value=0.46, output_intent_value=0.40, state_role="simulation")
    if route_key == "tuning.combat_profile":
        return MiniCurvePreview("Combat profile preview", state_role="simulation")
    if route_key == "tuning.conditional_rules":
        return SignalPipelineStage(
            "Condition",
            "Static condition to action route placeholder.",
            selected_value="Rule seam",
            status_role="simulation",
        )
    if route_key == "analysis.effective_response_stack":
        return SignalPipelineStage(
            "Raw Input",
            "Static stage placeholder for the future response stack.",
            selected_value="Roll selected",
            status_role="simulation",
            warning_text="Read-only visualization.",
        )
    if route_key == "analysis.live_monitor":
        return AxisBarPair("Roll signal", raw_value=0.35, output_intent_value=0.31, state_role="simulation")
    if route_key == "recorder.flight_recorder":
        return TruthBadge(
            "Example state: Capture backend unavailable",
            state_role="unavailable",
            helper_text="Metadata-only artifact surfaces remain read-only in LCD-3.",
        )
    if route_key == "recorder.clip_library":
        return MetricTile("Artifacts", "Metadata-only", "Clip rebuild is deferred.", state_role="info")
    if route_key == "recorder.capture_backend_truth":
        return CapabilityRail(
            capabilities=(
                ("Capture backend", "unavailable", "Example state: Capture backend unavailable"),
                ("Artifact mode", "info", "Metadata-only artifact"),
            )
        )
    if route_key == "support.perf_diagnostics":
        return MetricTile("Diagnostics", "Placeholder", "Raw diagnostics remain deferred.", state_role="info")
    if route_key == "support.setup_runtime_check":
        return ChecklistPanel(
            "Setup check placeholder",
            items=(
                ("Workspace loaded", "done", "Static placeholder state."),
                ("Telemetry proof", "waiting", "Example state: Telemetry missing."),
                ("Output proof", "blocked", "Example state: Output proof missing."),
            ),
        )
    return MetricTile("Docs topics", "Static", "Help and diagnostics stay secondary.", state_role="info")


def _context_demo(definition: LiquidPlaceholderPageDefinition):
    if definition.mode_id == "preflight":
        return StatusChip("Static component sample: Simulation mode", state_role="simulation")
    if definition.mode_id == "mapping":
        return MetricTile("Axis routes", "6", "workspace mapping intent", state_role="info")
    if definition.mode_id == "tuning":
        return AxisSelectorPills(selected_axis="Roll")
    if definition.mode_id == "analysis":
        return TelemetryFreshnessRail(
            "Example state: Telemetry stale",
            state_role="waiting",
            source_label="Static component sample",
        )
    if definition.mode_id == "recorder":
        return MetricTile(
            "Capture",
            "Unavailable",
            "Example state: Capture backend unavailable",
            state_role="unavailable",
        )
    return MetricTile("Diagnostics", "Read-only", "Runtime actions are not wired in LCD-3.", state_role="info")


def _detail_demo(definition: LiquidPlaceholderPageDefinition):
    if definition.mode_id == "preflight":
        return ChecklistPanel(
            "Readiness checklist",
            items=(
                ("Workspace loaded", "done", "Static placeholder state."),
                ("Telemetry sample", "waiting", "Example state: Telemetry missing."),
                ("Output proof", "blocked", "Example state: Output proof missing."),
            ),
        )
    if definition.mode_id == "mapping":
        return RouteFlowRow(
            source_label="Physical Stick X",
            function_label="Roll",
            target_label="vJoy X",
            status_role="waiting",
            helper_text="Static component sample; Output Intent wording is used until proof exists.",
        )
    if definition.mode_id == "tuning":
        return ParameterRow(
            label="Curve Strength",
            control=NumericParameterControl(value=0.34, min_value=0.0, max_value=1.0, decimals=2),
            unit_text="ratio",
            status_note="Draft change staged",
            changed=True,
            help_text="Metadata-ready placeholder.",
        )
    if definition.mode_id == "analysis":
        return AxisBarPair("Response sample", raw_value=0.25, output_intent_value=0.22, state_role="simulation")
    if definition.mode_id == "recorder":
        return CapabilityRail(
            capabilities=(
                ("Capture backend", "unavailable", "Example state: Capture backend unavailable"),
                ("Artifact mode", "info", "Metadata-only artifact"),
            )
        )
    return GuidanceBlock(
        current_feel="Support content is static.",
        affects="Future diagnostics and help page composition.",
        suggested_range="Use advanced details only when needed.",
        caution="No runtime action is launched from LCD-3.",
        selected_axis_note="Not axis-specific.",
    )


def _advanced_demo(definition: LiquidPlaceholderPageDefinition):
    if definition.mode_id == "tuning":
        return GuidanceBlock(
            current_feel="Smooth center placeholder.",
            affects="Future tuning page guidance.",
            suggested_range="0.20 to 0.60",
            caution="Preview does not prove live output.",
            selected_axis_note="Roll selected.",
        )
    if definition.mode_id == "analysis":
        return LiveSnapshotBlock(
            selected_control="Roll",
            source_truth_label="Static component sample: Simulation mode",
            raw_value="0.00",
            output_intent_value="Output Intent: vJoy X",
            state_role="simulation",
        )
    if definition.mode_id == "recorder":
        return StatusChip("Static component sample: Metadata-only artifact", state_role="info")
    if definition.mode_id == "support":
        return GuidanceBlock(
            current_feel="Diagnostics are secondary.",
            affects="Future support and setup guidance.",
            suggested_range="Keep raw details grouped.",
            caution="Do not imply Bridge lifecycle ownership.",
            selected_axis_note="Not axis-specific.",
        )
    return StatusChip("Read-only visualization", state_role="info")


_NAV_MODEL = build_liquid_navigation_model()
LIQUID_ROUTE_PLACEHOLDER_PAGES = _route_definitions(_NAV_MODEL)
_PAGE_BY_ROUTE = {page.route_key: page for page in LIQUID_ROUTE_PLACEHOLDER_PAGES}
LIQUID_PLACEHOLDER_PAGES = tuple(
    _PAGE_BY_ROUTE[_NAV_MODEL.route_for(mode.mode_id, mode.default_subpage_id).route_key]
    for mode in _NAV_MODEL.modes
)
_PAGE_BY_MODE = {page.mode_id: page for page in LIQUID_PLACEHOLDER_PAGES}
LIQUID_ROUTE_PAGE_FACTORIES = {
    definition.route_key: _make_factory(definition) for definition in LIQUID_ROUTE_PLACEHOLDER_PAGES
}
LIQUID_ROUTE_PAGE_FACTORIES["mapping.hotas_map"] = create_mapping_command_page
LIQUID_ROUTE_PAGE_FACTORIES["mapping.route_details"] = create_mapping_route_details_page
LIQUID_ROUTE_PAGE_FACTORIES["mapping.advanced_route_tables"] = create_mapping_advanced_route_tables_page
LIQUID_ROUTE_PAGE_FACTORIES["preflight.command_readiness"] = create_preflight_command_page
LIQUID_ROUTE_PAGE_FACTORIES["tuning.base_tuning"] = create_base_tuning_command_page
LIQUID_ROUTE_PAGE_FACTORIES["tuning.filtering"] = create_filtering_command_page
LIQUID_ROUTE_PAGE_FACTORIES["tuning.combat_profile"] = create_combat_profile_command_page
LIQUID_ROUTE_PAGE_FACTORIES["tuning.conditional_rules"] = create_conditional_rules_command_page
LIQUID_ROUTE_PAGE_FACTORIES["analysis.effective_response_stack"] = create_effective_response_stack_page
LIQUID_ROUTE_PAGE_FACTORIES["analysis.live_monitor"] = create_live_monitor_page
LIQUID_ROUTE_PAGE_FACTORIES["recorder.flight_recorder"] = create_flight_recorder_page
LIQUID_ROUTE_PAGE_FACTORIES["recorder.clip_library"] = create_clip_library_page
LIQUID_ROUTE_PAGE_FACTORIES["recorder.capture_backend_truth"] = create_capture_backend_truth_page


def placeholder_definition_by_mode_id(mode_id: str) -> LiquidPlaceholderPageDefinition:
    try:
        return _PAGE_BY_MODE[mode_id]
    except KeyError as exc:
        raise KeyError(mode_id) from exc


def placeholder_definition_by_route_key(route_key: str) -> LiquidPlaceholderPageDefinition:
    try:
        return _PAGE_BY_ROUTE[route_key]
    except KeyError as exc:
        raise KeyError(route_key) from exc
