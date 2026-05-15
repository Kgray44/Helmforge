from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QWidget

from shared_core.models.runtime import (
    InputStatus,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
    simulation_fallback_status,
)
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from v3_app.liquid.components import (
    LiquidAdvancedSection,
    LiquidDetailPanel,
    LiquidHeroPanel,
    LiquidInspectorPanel,
    LiquidPage,
    LiquidPageHeader,
    LiquidStatusRail,
)
from v3_app.liquid.flow_components import ChecklistPanel, RouteFlowRow
from v3_app.liquid.glass import action_button, glass_panel, mark_action_feedback
from v3_app.liquid.layout import grid_layout, horizontal_layout, vertical_layout
from v3_app.liquid.motion import MotionSettings, apply_interactive_card_motion, apply_raw_diagnostic_motion, current_motion_settings
from v3_app.liquid.parameter_controls import GuidanceBlock
from v3_app.liquid.status_components import MetricTile, ReadinessGate, StatusChip, TelemetryFreshnessRail, TruthBadge
from v3_app.liquid.visible_motion import MotionProofPanel
from v3_app.services.app_state import AppState
from v3_app.services.help_docs import (
    HelpArticle,
    all_articles,
    parameter_reference_entries,
    topic_tree_by_category,
)
from v3_app.services.parameter_metadata import ParameterMetadata
from v3_app.services.perf_diagnostics import (
    DEFAULT_MANUAL_BRIDGE_COMMAND,
    DiagnosticsCollector,
    DiagnosticsSnapshot,
    PerfMetricSummary,
    build_diagnostics_snapshot,
    build_diagnostics_text,
    format_metric_summary,
)


RouteCallback = Callable[[str], None]

SUPPORT_ROUTE_KEYS = (
    "support.help_docs",
    "support.perf_diagnostics",
    "support.setup_runtime_check",
)
SETUP_DRY_RUN_COMMAND = r"powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun"


class SupportCommandPage(LiquidPage):
    def __init__(
        self,
        *,
        route_key: str,
        state: AppState | None = None,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        diagnostics_collector: DiagnosticsCollector | None = None,
        workspace_path: str | Path | None = None,
        on_route_requested: RouteCallback | None = None,
        motion_settings: MotionSettings | None = None,
    ) -> None:
        self.route_key = _validate_route(route_key)
        self._runtime_status = runtime_status or _runtime_status_from_state(state)
        self._state = state or AppState.from_runtime_status(self._runtime_status, active_page_id=_page_id(route_key))
        self._workspace = workspace or create_default_workspace()
        self._collector = diagnostics_collector or DiagnosticsCollector()
        self._workspace_path = Path(workspace_path or self._state.source_config)
        self._on_route_requested = on_route_requested
        self._motion_settings = motion_settings or current_motion_settings()
        self._diagnostics_snapshot = _build_static_diagnostics_snapshot(
            state=self._state,
            runtime_status=self._runtime_status,
            workspace_path=self._workspace_path,
            collector=self._collector,
        )

        super().__init__(
            title=_page_title(route_key),
            subtitle=_page_question(route_key),
            helper_text="Liquid Support",
            object_name="liquidSupportCommandPage",
        )
        self.setProperty("routeKey", route_key)
        self.setProperty("modeId", "support")
        self.setProperty("subpageId", route_key.split(".")[-1])
        self.setProperty("lcdPhase", "LCD-9")
        self.setProperty("legacyWrapped", False)
        self.setProperty("motionIntensity", self._motion_settings.intensity.value)
        self._render()

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        self.setProperty("motionIntensity", motion_settings.intensity.value)
        for panel in self.findChildren(MotionProofPanel):
            panel.set_motion_settings(motion_settings)

    def refresh_diagnostics(self) -> None:
        self._diagnostics_snapshot = _build_static_diagnostics_snapshot(
            state=self._state,
            runtime_status=self._runtime_status,
            workspace_path=self._workspace_path,
            collector=self._collector,
        )
        self.setProperty("supportDiagnosticsRefreshCount", int(self.property("supportDiagnosticsRefreshCount") or 0) + 1)
        status = self.findChild(QLabel, "liquidSupportDiagnosticsActionStatus")
        if status is not None:
            status.setText("Diagnostics refreshed on demand. No high-cadence diagnostics loop was started.")
        self._render()

    def clear_timings(self) -> None:
        self._collector.clear()
        self._diagnostics_snapshot = _build_static_diagnostics_snapshot(
            state=self._state,
            runtime_status=self._runtime_status,
            workspace_path=self._workspace_path,
            collector=self._collector,
        )
        status = self.findChild(QLabel, "liquidSupportDiagnosticsActionStatus")
        if status is not None:
            status.setText("Timing summaries and jank buckets cleared locally.")
        self._render()

    def prepare_copy_diagnostics(self) -> str:
        text = build_diagnostics_text(self._diagnostics_snapshot)
        self.setProperty("supportCopyDiagnosticsPrepared", True)
        target = self.findChild(QLabel, "liquidSupportDiagnosticsCopyText")
        if target is not None:
            target.setText(text)
        return text

    def _render(self) -> None:
        self.set_header(
            LiquidPageHeader(
                _page_title(self.route_key),
                _page_question(self.route_key),
                kicker="SUPPORT / " + _page_title(self.route_key).upper(),
                object_name="liquidSupportPageHeader",
            )
        )
        self.set_status_rail(_support_status_rail(self.route_key, self._runtime_status, self._diagnostics_snapshot))
        if self.route_key == "support.help_docs":
            self._render_help_docs()
        elif self.route_key == "support.perf_diagnostics":
            self._render_perf_diagnostics()
        else:
            self._render_setup_runtime_check()

    def _render_help_docs(self) -> None:
        self.set_hero(_help_hero(self._runtime_status))
        self.set_inspector(_help_topics_panel(self._on_route_requested))
        self.set_detail(_parameter_reference_panel())
        self.set_advanced(_help_advanced_panel())

    def _render_perf_diagnostics(self) -> None:
        snapshot = self._diagnostics_snapshot
        self.set_hero(_diagnostics_hero(snapshot, self._collector))
        self.set_inspector(_diagnostics_left_panel(snapshot))
        self.set_detail(_diagnostics_right_panel(self, snapshot))
        self.set_advanced(_diagnostics_advanced_panel(snapshot))

    def _render_setup_runtime_check(self) -> None:
        self.set_hero(_setup_hero(self._runtime_status))
        self.set_inspector(_setup_readiness_panel(self._runtime_status, self._diagnostics_snapshot))
        self.set_detail(_setup_checklist_panel(self._runtime_status))
        self.set_advanced(_setup_advanced_panel(self._runtime_status, self._diagnostics_snapshot))


def create_help_docs_page(**kwargs) -> SupportCommandPage:
    return SupportCommandPage(route_key="support.help_docs", **kwargs)


def create_perf_diagnostics_page(**kwargs) -> SupportCommandPage:
    return SupportCommandPage(route_key="support.perf_diagnostics", **kwargs)


def create_setup_runtime_check_page(**kwargs) -> SupportCommandPage:
    return SupportCommandPage(route_key="support.setup_runtime_check", **kwargs)


def _validate_route(route_key: str) -> str:
    if route_key not in SUPPORT_ROUTE_KEYS:
        raise KeyError(route_key)
    return route_key


def _page_id(route_key: str) -> str:
    return route_key.split(".")[-1]


def _page_title(route_key: str) -> str:
    return {
        "support.help_docs": "Help / Docs",
        "support.perf_diagnostics": "Perf / Diagnostics",
        "support.setup_runtime_check": "Setup / Runtime Check",
    }[route_key]


def _page_question(route_key: str) -> str:
    return {
        "support.help_docs": "How do I understand and use HelmForge?",
        "support.perf_diagnostics": "What is the system actually reporting?",
        "support.setup_runtime_check": "What do I need to install, connect, or check?",
    }[route_key]


def _runtime_status_from_state(state: AppState | None) -> RuntimePreflightStatus:
    if state is None:
        return simulation_fallback_status()
    return RuntimePreflightStatus(
        mode=RuntimeMode.FULL_LIVE if state.runtime.truth is RuntimeTruth.LIVE_VERIFIED else RuntimeMode.SIMULATED,
        truth=state.runtime.truth,
        input=simulation_fallback_status().input.__class__(status=state.runtime.input_status),
        output=simulation_fallback_status().output.__class__(
            status=state.runtime.output_status,
            backend_name=state.runtime.backend_name or "vJoy",
            live_output_writes_verified=state.runtime.output_verified,
        ),
    )


def _build_static_diagnostics_snapshot(
    *,
    state: AppState,
    runtime_status: RuntimePreflightStatus,
    workspace_path: Path,
    collector: DiagnosticsCollector,
) -> DiagnosticsSnapshot:
    return build_diagnostics_snapshot(
        state=state,
        runtime_status=runtime_status,
        workspace_path=workspace_path,
        telemetry_status="not_read",
        telemetry_age_seconds=None,
        process_hint="Unavailable - process presence is a hint only",
        bridge_lifecycle="Not refreshed from Support page",
        hotas_discovery_status=_hotas_status(runtime_status),
        last_command_status="Unavailable",
        last_command_request_id="Unavailable",
        collector=collector,
        runtime_frame=None,
    )


def _support_status_rail(
    route_key: str,
    runtime_status: RuntimePreflightStatus,
    snapshot: DiagnosticsSnapshot,
) -> LiquidStatusRail:
    rail = LiquidStatusRail(
        items=(
            ("Support", "info"),
            (_page_title(route_key), "info"),
            (_runtime_truth_text(runtime_status), _runtime_role(runtime_status)),
            ("Output proof missing" if not snapshot.output_verified else "Output proof present", "blocked" if not snapshot.output_verified else "verified"),
            ("Diagnostics on demand", "info"),
        ),
        object_name="liquidSupportStatusRail",
    )
    rail.setProperty("routeKey", route_key)
    return rail


def _help_hero(runtime_status: RuntimePreflightStatus) -> QWidget:
    hero = LiquidHeroPanel(
        "Help / Docs",
        "Learn pages, parameters, setup, runtime truth, and safe workflow in the Liquid Command Deck model.",
        object_name="liquidSupportHero",
        state_role=_runtime_role(runtime_status),
        minimum_height=360,
    )
    layout = hero.layout()
    if layout is None:
        return hero
    layout.addWidget(
        GuidanceBlock(
            current_feel="HelmForge is organized as operating modes: Preflight, Mapping, Tuning, Analysis, Recorder, and Support.",
            affects="Use Help for clean guidance, Diagnostics for raw truth, and Setup for safe checks.",
            suggested_range="Start in simulation, shape the workspace, inspect Output Intent, then verify runtime truth separately.",
            caution="Output Intent is not output proof.",
            selected_axis_note="Full Live Runtime Ready requires the full proof chain.",
            object_name="liquidSupportCommandDeckGuidance",
        )
    )
    for text in _truth_guardrails():
        layout.addWidget(TruthBadge(text, state_role="warning" if "not" in text.casefold() else "info"))
    return hero


def _help_topics_panel(on_route_requested: RouteCallback | None) -> QWidget:
    panel = LiquidInspectorPanel(
        "Topic Rail",
        "Start with the topic cards, then use parameter reference for exact tuning meanings.",
        object_name="liquidSupportHelpTopicsPanel",
        state_role="info",
    )
    layout = panel.layout()
    if layout is None:
        return panel
    rail = glass_panel("liquidSupportHelpTopicRail", role="support_topic_rail")
    rail.setProperty("componentRole", "SupportTopicRail")
    rail_layout = horizontal_layout(rail, margins=(0, 0, 0, 0), spacing=8)
    for topic in ("Getting Started", "Runtime Truth", "Mapping", "Tuning", "Analysis", "Recorder", "Troubleshooting"):
        rail_layout.addWidget(StatusChip(topic, state_role="info"))
    rail_layout.addStretch(1)
    layout.addWidget(rail)

    cards = (
        ("Preflight and readiness", "Can I safely use live output right now?", "preflight.command_readiness"),
        ("Mapping physical controls", "What does each physical control intend to do?", "mapping.hotas_map"),
        ("Tuning axis feel", "How do curve, deadzone, filters, and combat layers affect feel?", "tuning.base_tuning"),
        ("Effective Response Stack", "Inspect raw input through stages into Final Output Intent.", "analysis.effective_response_stack"),
        ("Live Monitor", "Watch passive axes, buttons, and hats without treating motion as output proof.", "analysis.live_monitor"),
        ("Flight Recorder limitations", "Metadata-only artifacts are not real recordings.", "recorder.flight_recorder"),
        ("Helm Assistant", "Draft recommendations stay workspace-local until explicitly applied and saved.", ""),
        ("Setup / vJoy / Bridge", "Setup checks explain blockers and manual dry-run commands.", "support.setup_runtime_check"),
        ("Performance diagnostics", "Inspect runtime truth, telemetry, timing, and jank buckets.", "support.perf_diagnostics"),
    )
    grid = grid_layout(margins=(0, 0, 0, 0), spacing=8)
    for index, (title, body, route_key) in enumerate(cards):
        grid.addWidget(_topic_card(title, body, route_key, on_route_requested), index // 2, index % 2)
    layout.addLayout(grid)
    return panel


def _topic_card(title: str, body: str, route_key: str, on_route_requested: RouteCallback | None) -> QFrame:
    card = glass_panel(f"liquidSupportTopicCard_{_key(title)}", role="support_topic_card")
    card.setProperty("supportTopicCard", True)
    card.setProperty("routeTarget", route_key)
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    apply_interactive_card_motion(card)
    layout = vertical_layout(card, margins=(12, 10, 12, 10), spacing=7)
    layout.addWidget(StatusChip(title, state_role="info"))
    layout.addWidget(_label(body, "liquidSupportTopicBody", wrap=True))
    if route_key:
        button = action_button(
            "Open route",
            object_name=f"liquidSupportTopicRouteButton_{_key(title)}",
            enabled=on_route_requested is not None,
            action_kind="navigation",
            route_target=route_key,
            disabled_reason="Route navigation is available inside the Liquid shell.",
        )
        if on_route_requested is not None:
            button.clicked.connect(lambda _checked=False, target=route_key: on_route_requested(target))
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
    return card


def _parameter_reference_panel() -> QWidget:
    panel = LiquidDetailPanel(
        "Parameter Help",
        "Existing parameter metadata is shown by category; no competing metadata system is introduced.",
        object_name="liquidSupportParameterReference",
        state_role="info",
        minimum_height=360,
    )
    panel.setProperty("parameterMetadataSource", "v3_app.services.parameter_metadata")
    layout = panel.layout()
    if layout is None:
        return panel
    entries = parameter_reference_entries()
    by_category: dict[str, list[ParameterMetadata]] = {}
    for entry in entries:
        by_category.setdefault(entry.category, []).append(entry)
    for category, category_entries in sorted(by_category.items()):
        category_frame = glass_panel(f"liquidSupportParameterCategory_{_key(category)}", role="support_parameter_category")
        category_layout = vertical_layout(category_frame, margins=(10, 8, 10, 8), spacing=6)
        category_layout.addWidget(StatusChip(category, state_role="info"))
        for entry in category_entries[:4]:
            category_layout.addWidget(_parameter_row(entry))
        layout.addWidget(category_frame)
    return panel


def _parameter_row(metadata: ParameterMetadata) -> QFrame:
    row = glass_panel(f"liquidSupportParameter_{_key(metadata.parameter_id)}", role="support_parameter_row")
    row.setProperty("metadataId", metadata.parameter_id)
    row_layout = vertical_layout(row, margins=(8, 6, 8, 6), spacing=4)
    row_layout.addWidget(_label(metadata.display_name, "liquidSupportParameterName", wrap=True))
    row_layout.addWidget(_label(metadata.short_description, "liquidSupportParameterDescription", wrap=True))
    row_layout.addWidget(_label(f"Range / options: {_format_range_or_options(metadata)}", "liquidSupportParameterRange", wrap=True))
    examples = _format_examples(metadata)
    if examples:
        row_layout.addWidget(_label(f"Examples: {examples}", "liquidSupportParameterExamples", wrap=True))
    if metadata.warning_text:
        row_layout.addWidget(StatusChip(metadata.warning_text, state_role="warning"))
    return row


def _help_advanced_panel() -> QWidget:
    panel = LiquidAdvancedSection(
        "Article Index / Truth Notes",
        "The full article library stays secondary here; use topic cards first.",
        object_name="liquidSupportAdvancedDetails",
        state_role="info",
    )
    layout = panel.layout()
    if layout is None:
        return panel
    topic_tree = topic_tree_by_category(all_articles(), sort_mode="By Importance")
    for category, articles in topic_tree.items():
        titles = ", ".join(article.title for article in articles[:5])
        layout.addWidget(_label(f"{category}: {titles}", "liquidSupportArticleIndexRow", wrap=True))
    layout.addWidget(_label("Legacy pages remain fallback/reference. This Liquid page is a new composition.", "liquidSupportLegacyBoundary", wrap=True))
    return panel


def _diagnostics_hero(snapshot: DiagnosticsSnapshot, collector: DiagnosticsCollector) -> QWidget:
    hero = LiquidHeroPanel(
        "Perf / Diagnostics",
        "Current diagnostic summary, runtime truth, telemetry source/freshness, output proof state, and jank summary.",
        object_name="liquidSupportHero",
        state_role="info",
        minimum_height=360,
    )
    layout = hero.layout()
    if layout is None:
        return hero
    metrics = (
        ("Runtime truth", snapshot.runtime_truth, "Existing runtime status.", _role_for_truth(snapshot.runtime_truth)),
        ("Telemetry status", snapshot.telemetry_status, "Support page has not started a telemetry loop.", "info"),
        ("Output proof", "present" if snapshot.output_verified else "missing", "Output Intent remains separate.", "verified" if snapshot.output_verified else "blocked"),
        ("Full Live Runtime Ready", str(snapshot.full_live_runtime_ready).lower(), "Existing proof chain only.", "verified" if snapshot.full_live_runtime_ready else "blocked"),
        ("Active page", snapshot.active_page, "Current AppState route id.", "info"),
        ("JSON read cadence", "5 Hz fallback", "PERF 1A fallback policy remains throttled.", "info"),
        ("Graph/update timing", _timing_line("graph_update", snapshot), "Visual lanes are separate from diagnostics.", "info"),
        ("Jank bucket summary", _jank_line("graph_update", collector), "over_16ms through over_250ms.", "warning"),
    )
    metric_grid = grid_layout(margins=(0, 0, 0, 0), spacing=8)
    for index, (label, value, caption, role) in enumerate(metrics):
        metric_grid.addWidget(MetricTile(label, value, caption, state_role=role), index // 4, index % 4)
    layout.addLayout(metric_grid)
    layout.addWidget(
        TelemetryFreshnessRail(
            "Diagnostics update on demand or low cadence only.",
            state_role="info",
            source_label="No high-rate diagnostics loop",
            object_name="liquidSupportDiagnosticsFreshnessRail",
        )
    )
    layout.addWidget(
        _label(
            "JSON read cadence remains 5 Hz fallback. Graph/update timing is visual/data-lane reporting, not a diagnostics refresh loop.",
            "liquidSupportDiagnosticsCadenceNote",
            wrap=True,
        )
    )
    return hero


def _diagnostics_left_panel(snapshot: DiagnosticsSnapshot) -> QWidget:
    panel = LiquidInspectorPanel(
        "Runtime / Telemetry / Input",
        "Grouped runtime truth and Bridge/input facts. Raw detail is intentional on this diagnostics page.",
        object_name="liquidSupportDiagnosticsLeftPanel",
        state_role="info",
        minimum_height=420,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    layout.addWidget(
        _diagnostic_section(
            "Runtime Truth",
            (
                ("Runtime mode", snapshot.runtime_mode),
                ("Runtime truth", snapshot.runtime_truth),
                ("Input status", snapshot.input_device_status),
                ("Output/vJoy status", snapshot.output_status_detail),
                ("Output proof", "present" if snapshot.output_verified else "missing"),
                ("Full Live Runtime Ready", str(snapshot.full_live_runtime_ready).lower()),
            ),
        )
    )
    layout.addWidget(
        _diagnostic_section(
            "Bridge / Telemetry",
            (
                ("Telemetry source", snapshot.telemetry_status),
                ("Telemetry age", _age_text(snapshot.telemetry_age_seconds)),
                ("Lifecycle state", snapshot.bridge_lifecycle),
                ("Stream status", "local stream preferred when available; stream connected is not output proof"),
                ("JSON fallback status", "available at 5 Hz fallback cadence"),
                ("Last command status", snapshot.last_command_status),
            ),
        )
    )
    layout.addWidget(
        _diagnostic_section(
            "Physical Input",
            (
                ("Physical backend", snapshot.physical_input_backend),
                ("Selected device", snapshot.selected_input_device),
                ("Input sampling", snapshot.input_sampling),
                ("Sample source", snapshot.physical_input_sample_source),
                ("Axis/button/hat counts", snapshot.physical_input_sample_counts),
                ("Warnings/errors", f"{snapshot.physical_input_sampling_warnings} / {snapshot.physical_input_sampling_errors}"),
            ),
        )
    )
    return panel


def _diagnostics_right_panel(page: SupportCommandPage, snapshot: DiagnosticsSnapshot) -> QWidget:
    panel = LiquidDetailPanel(
        "Output / Performance / Workspace",
        "Output proof, PERF 1A timing lanes, workspace state, and diagnostic actions.",
        object_name="liquidSupportDiagnosticsRightPanel",
        state_role="info",
        minimum_height=420,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    layout.addWidget(
        _diagnostic_section(
            "Virtual Output / vJoy",
            (
                ("Backend", snapshot.virtual_output_backend),
                ("Dependency status", snapshot.vjoy_dependency_status),
                ("Selected device", snapshot.selected_output_device),
                ("Output loop state", snapshot.output_loop_state),
                ("Output write status", snapshot.output_write_status),
                ("Verification source", snapshot.output_verification_source),
                ("Real/fake proof separation", f"real={snapshot.real_output_verified} fake={snapshot.fake_output_verified}"),
            ),
        )
    )
    layout.addWidget(
        _diagnostic_section(
            "Performance",
            (
                ("Timing summaries", _timing_summary_block(snapshot)),
                ("Lane-level timings from PERF 1A", _lane_timing_text(snapshot)),
                ("Jank buckets", _all_jank_text(page._collector)),
                ("Hidden page skips", _hidden_skip_summary(snapshot)),
                ("Graph/update cadence", "visual graph lane may paint separately; static graph rebuilds stay dirty-only"),
                ("Scheduler lane statuses", "JSON fallback 5 Hz; diagnostics low cadence; shell chrome dirty-gated"),
            ),
        )
    )
    layout.addWidget(
        _diagnostic_section(
            "Workspace / UI",
            (
                ("Workspace path", snapshot.workspace_path),
                ("Active profile", page._state.active_profile),
                ("Saved/unsaved", "saved" if page._state.saved else "unsaved"),
                ("Selected route/page", snapshot.active_page),
                ("Selected axis", snapshot.selected_axis),
            ),
        )
    )
    layout.addWidget(MotionProofPanel(motion_settings=page._motion_settings))
    layout.addWidget(_diagnostic_actions(page))
    return panel


def _diagnostics_advanced_panel(snapshot: DiagnosticsSnapshot) -> QWidget:
    panel = LiquidAdvancedSection(
        "Raw Diagnostic Detail",
        "Raw/internal values are intentionally secondary, grouped, and diagnostics-only.",
        object_name="liquidSupportAdvancedDetails",
        state_role="info",
        minimum_height=260,
    )
    apply_raw_diagnostic_motion(panel)
    layout = panel.layout()
    if layout is None:
        return panel
    for label, value in (
        ("Runtime frame", snapshot.runtime_frame_status),
        ("Runtime frame sequence", snapshot.runtime_frame_sequence),
        ("Runtime frame source", snapshot.runtime_frame_source),
        ("Runtime frame output proof", snapshot.runtime_frame_output_proof),
        ("Runtime frame Full Live Runtime Ready", str(snapshot.runtime_frame_full_live_runtime_ready).lower()),
        ("Ready state", snapshot.runtime_frame_ready_state),
        ("Blocked reason", snapshot.runtime_frame_blocked_reason or "None"),
        ("Telemetry proof", snapshot.runtime_frame_telemetry_proof),
        ("Safety proof", snapshot.runtime_frame_safety_proof),
        ("Fake/real path", snapshot.runtime_frame_fake_or_real_path),
        ("Manual Bridge command", DEFAULT_MANUAL_BRIDGE_COMMAND),
    ):
        layout.addWidget(_key_value_row(label, value))
    return panel


def _diagnostic_section(title: str, rows: Iterable[tuple[str, str]]) -> QFrame:
    section = glass_panel(f"liquidSupportDiagnosticSection_{_key(title)}", role="support_diagnostic_section")
    section.setProperty("supportDiagnosticSection", True)
    section.setProperty("diagnosticSection", title)
    section.setProperty("componentRole", "SupportDiagnosticSection")
    layout = vertical_layout(section, margins=(12, 10, 12, 10), spacing=7)
    layout.addWidget(StatusChip(title, state_role="info"))
    for label, value in rows:
        layout.addWidget(_key_value_row(label, value))
    return section


def _diagnostic_actions(page: SupportCommandPage) -> QFrame:
    actions = glass_panel("liquidSupportDiagnosticActions", role="support_diagnostic_actions")
    actions.setProperty("componentRole", "SupportDiagnosticActions")
    layout = vertical_layout(actions, margins=(0, 0, 0, 0), spacing=8)
    row = horizontal_layout(spacing=8)
    refresh = action_button("Refresh Diagnostics", object_name="liquidSupportRefreshDiagnosticsButton", action_kind="validate")
    refresh.clicked.connect(lambda _checked=False: page.refresh_diagnostics())
    clear = action_button("Clear Timings", object_name="liquidSupportClearTimingsButton", action_kind="reset")
    clear.clicked.connect(lambda _checked=False: page.clear_timings())
    copy = action_button("Copy Diagnostics", object_name="liquidSupportCopyDiagnosticsButton", action_kind="copy")
    copy.clicked.connect(lambda _checked=False: _mark_copy(page, copy))
    row.addWidget(refresh)
    row.addWidget(clear)
    row.addWidget(copy)
    row.addStretch(1)
    layout.addLayout(row)
    status = _label("Diagnostics are ready. Actions are observational and local to the UI.", "liquidSupportDiagnosticsActionStatus", wrap=True)
    layout.addWidget(status)
    copy_text = _label("", "liquidSupportDiagnosticsCopyText", wrap=True)
    copy_text.setProperty("copyDiagnosticsText", True)
    layout.addWidget(copy_text)
    return actions


def _mark_copy(page: SupportCommandPage, button: QPushButton) -> None:
    page.prepare_copy_diagnostics()
    mark_action_feedback(button, "Diagnostics text prepared locally.")


def _setup_hero(runtime_status: RuntimePreflightStatus) -> QWidget:
    blocker = _setup_blocker(runtime_status)
    hero = LiquidHeroPanel(
        "Setup / Runtime Check",
        "Setup readiness summary, current blocker, and next safe action.",
        object_name="liquidSupportHero",
        state_role=_runtime_role(runtime_status),
        minimum_height=360,
    )
    layout = hero.layout()
    if layout is None:
        return hero
    layout.addWidget(TruthBadge(_runtime_truth_text(runtime_status), state_role=_runtime_role(runtime_status), helper_text="Existing runtime status only."))
    layout.addWidget(TruthBadge(f"Current blocker: {blocker}", state_role="warning" if blocker != "No blocker reported" else "ready"))
    layout.addWidget(TruthBadge("Next recommended action: run the safe dry-run setup check from a terminal.", state_role="info"))
    layout.addWidget(_label("Setup checks are checks, not runtime activation.", "liquidSupportSetupTruthNote", wrap=True))
    layout.addWidget(
        RouteFlowRow(
            source_label="Physical input proof",
            function_label="Workspace pipeline proof",
            target_label="Output proof gate",
            status_role="blocked" if not runtime_status.live_output_writes_verified else "verified",
            helper_text="Each proof stays separate. vJoy detected, stream connected, JSON freshness, and physical input are not output proof.",
        )
    )
    return hero


def _setup_readiness_panel(runtime_status: RuntimePreflightStatus, snapshot: DiagnosticsSnapshot) -> QWidget:
    panel = LiquidInspectorPanel(
        "Readiness Gates",
        "Each gate reports current known truth. No gate starts services or activates output.",
        object_name="liquidSupportSetupReadinessPanel",
        state_role=_runtime_role(runtime_status),
        minimum_height=420,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    gates = (
        ("Thrustmaster/HOTAS input", _input_gate(runtime_status)),
        ("Bridge telemetry", ("Not refreshed", "waiting", "Manual Bridge telemetry remains observational.")),
        ("Workspace config", ("Unsaved draft" if not snapshot.workspace_path else "Path known", "info", snapshot.workspace_path)),
        ("vJoy dependency", _output_dependency_gate(runtime_status)),
        ("vJoy device", _output_device_gate(runtime_status)),
        ("Output proof", _output_proof_gate(runtime_status)),
        ("Safety gate", ("Check only", "info", "Full Live Runtime Ready remains governed by the existing proof chain.")),
    )
    for title, (state_text, role, detail) in gates:
        layout.addWidget(ReadinessGate(title, state_text=state_text, state_role=role, detail=detail))
    return panel


def _setup_checklist_panel(runtime_status: RuntimePreflightStatus) -> QWidget:
    panel = LiquidDetailPanel(
        "Safe Setup Checklist",
        "Use these checks to find missing pieces without changing runtime authority.",
        object_name="liquidSupportSetupChecklistPanel",
        state_role=_runtime_role(runtime_status),
        minimum_height=420,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    checklist = ChecklistPanel(
        "Setup checklist",
        items=(
            ("Connect HOTAS", _role_for_input(runtime_status.input.status), _input_reason(runtime_status)),
            ("Confirm Windows sees controller", _role_for_input(runtime_status.input.status), "Device discovery is a hint, not output proof."),
            ("Confirm Bridge telemetry", "waiting", "Manual Bridge telemetry can be checked separately."),
            ("Confirm workspace saved/applied", "info", "Workspace state is separate from runtime proof."),
            ("Confirm vJoy driver detected", _role_for_output(runtime_status.output.status), _output_reason(runtime_status)),
            ("Confirm vJoy device available", _role_for_output(runtime_status.output.status), "Device availability is not output proof."),
            ("Confirm output proof missing/verified", "blocked" if not runtime_status.live_output_writes_verified else "verified", "Proof remains separate from intent."),
            ("Run safe setup check", "info", "Dry-run command only."),
        ),
        object_name="liquidSupportSetupChecklist",
    )
    layout.addWidget(checklist)
    layout.addWidget(_label(SETUP_DRY_RUN_COMMAND, "liquidSupportSetupDryRunCommand", wrap=True))
    layout.addWidget(StatusChip("No installers launched from this Liquid page", state_role="info"))
    layout.addWidget(StatusChip("No Bridge lifecycle action is started here", state_role="info"))
    return panel


def _setup_advanced_panel(runtime_status: RuntimePreflightStatus, snapshot: DiagnosticsSnapshot) -> QWidget:
    panel = LiquidAdvancedSection(
        "Setup Details / Dry-Run Guidance",
        "Detailed setup facts and command guidance. The PowerShell script can be run outside the app.",
        object_name="liquidSupportAdvancedDetails",
        state_role="info",
        minimum_height=260,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    details = (
        ("Input device names", ", ".join(runtime_status.detected_device_names) or "None detected"),
        ("Input status", runtime_status.input.status.value),
        ("vJoy/backend status", runtime_status.output.status.value),
        ("vJoy/backend name", runtime_status.detected_output_backend_name or "vJoy"),
        ("Bridge command example", DEFAULT_MANUAL_BRIDGE_COMMAND),
        ("Runtime setup dry-run", SETUP_DRY_RUN_COMMAND),
        ("Telemetry path/source", snapshot.telemetry_status),
        ("Simulation fallback", "Preserved. Safe fallback remains available."),
    )
    for label, value in details:
        layout.addWidget(_key_value_row(label, value))
    for warning in runtime_status.warnings:
        layout.addWidget(StatusChip(warning, state_role="warning"))
    return panel


def _truth_guardrails() -> tuple[str, ...]:
    return (
        "Output Intent is not output proof.",
        "vJoy detected is not output verified.",
        "Stream connected is not output proof.",
        "Recorder metadata-only artifacts are not real recordings.",
        "Simulation mode is safe fallback.",
        "Full Live Runtime Ready requires the full proof chain.",
    )


def _key_value_row(label: str, value: object) -> QFrame:
    row = glass_panel(f"liquidSupportRow_{_key(label)}", role="support_key_value_row")
    row.setProperty("componentRole", "SupportKeyValueRow")
    layout = horizontal_layout(row, margins=(0, 0, 0, 0), spacing=8)
    key = _label(label, "liquidSupportRowLabel", wrap=True)
    val = _label(str(value), "liquidSupportRowValue", wrap=True)
    layout.addWidget(key, 1)
    layout.addWidget(val, 2)
    return row


def _label(text: object, object_name: str, *, wrap: bool = False) -> QLabel:
    label = QLabel(str(text))
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    return label


def _hotas_status(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.input.status is InputStatus.DETECTED:
        return "target_device_detected"
    if runtime_status.input.status is InputStatus.ERROR:
        return "input_error"
    return "no_supported_device"


def _runtime_truth_text(runtime_status: RuntimePreflightStatus) -> str:
    return runtime_status.truth.value.replace("_", " ")


def _runtime_role(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.truth is RuntimeTruth.LIVE_VERIFIED and runtime_status.live_output_writes_verified:
        return "verified"
    if runtime_status.truth in {RuntimeTruth.DETECTED_UNVERIFIED, RuntimeTruth.SIMULATED}:
        return "simulation"
    if runtime_status.truth is RuntimeTruth.ERROR:
        return "error"
    return "blocked"


def _role_for_truth(value: str) -> str:
    normalized = value.casefold()
    if "live_verified" in normalized:
        return "verified"
    if "error" in normalized:
        return "error"
    if "blocked" in normalized:
        return "blocked"
    return "simulation"


def _role_for_input(status: InputStatus) -> str:
    if status is InputStatus.DETECTED:
        return "ready"
    if status is InputStatus.ERROR:
        return "error"
    return "waiting"


def _role_for_output(status: OutputStatus) -> str:
    if status is OutputStatus.OUTPUT_VERIFIED:
        return "verified"
    if status is OutputStatus.VJOY_DETECTED:
        return "warning"
    if status is OutputStatus.OUTPUT_ERROR:
        return "error"
    return "waiting"


def _input_gate(runtime_status: RuntimePreflightStatus) -> tuple[str, str, str]:
    status = runtime_status.input.status
    return (
        status.value.replace("_", " "),
        _role_for_input(status),
        _input_reason(runtime_status),
    )


def _output_dependency_gate(runtime_status: RuntimePreflightStatus) -> tuple[str, str, str]:
    status = runtime_status.output.status
    if status in {OutputStatus.VJOY_DETECTED, OutputStatus.OUTPUT_VERIFIED}:
        return ("Detected", _role_for_output(status), "Detected is not proof of output.")
    return ("Missing or unchecked", _role_for_output(status), _output_reason(runtime_status))


def _output_device_gate(runtime_status: RuntimePreflightStatus) -> tuple[str, str, str]:
    status = runtime_status.output.status
    if status in {OutputStatus.VJOY_DETECTED, OutputStatus.OUTPUT_VERIFIED}:
        return ("Available hint", _role_for_output(status), runtime_status.detected_output_backend_name or "vJoy")
    return ("Unavailable", _role_for_output(status), _output_reason(runtime_status))


def _output_proof_gate(runtime_status: RuntimePreflightStatus) -> tuple[str, str, str]:
    if runtime_status.live_output_writes_verified:
        return ("Proof present", "verified", "Existing runtime proof reports output writes.")
    return ("Proof missing", "blocked", "Output intent, vJoy detection, stream, JSON, and physical input do not prove output.")


def _input_reason(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.detected_device_names:
        return ", ".join(runtime_status.detected_device_names)
    return "Target HOTAS input is missing or not checked; simulation fallback remains safe."


def _output_reason(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.detected_output_backend_name:
        return runtime_status.detected_output_backend_name
    if runtime_status.output.warnings:
        return "; ".join(runtime_status.output.warnings)
    return "vJoy/backend proof is missing or not checked."


def _setup_blocker(runtime_status: RuntimePreflightStatus) -> str:
    if runtime_status.input.status is not InputStatus.DETECTED:
        return "HOTAS input missing"
    if runtime_status.output.status is OutputStatus.VJOY_MISSING:
        return "vJoy dependency missing"
    if not runtime_status.live_output_writes_verified:
        return "Output proof missing"
    return "No blocker reported"


def _format_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _format_range_or_options(metadata: ParameterMetadata) -> str:
    if metadata.dropdown_options:
        return ", ".join(metadata.dropdown_options)
    if metadata.min_value is not None and metadata.max_value is not None:
        unit = f" {metadata.units}" if metadata.units else ""
        return f"{_format_value(metadata.min_value)} to {_format_value(metadata.max_value)}{unit}"
    return "Not constrained"


def _format_examples(metadata: ParameterMetadata) -> str:
    examples = []
    if metadata.low_or_min_example is not None:
        examples.append(f"{metadata.low_or_min_example.label}: {metadata.low_or_min_example.value} - {metadata.low_or_min_example.effect}")
    if metadata.high_or_max_example is not None:
        examples.append(f"{metadata.high_or_max_example.label}: {metadata.high_or_max_example.value} - {metadata.high_or_max_example.effect}")
    return " | ".join(examples)


def _age_text(value: float | None) -> str:
    if value is None:
        return "Unavailable"
    return f"{value:.1f}s"


def _timing_line(name: str, snapshot: DiagnosticsSnapshot) -> str:
    summary = snapshot.timing_summaries.get(name, PerfMetricSummary(name=name))
    return format_metric_summary(summary)


def _timing_summary_block(snapshot: DiagnosticsSnapshot) -> str:
    return "; ".join(
        _timing_line(name, snapshot)
        for name in ("page_switch", "heartbeat", "graph_update", "json_read", "diagnostics_update")
    )


def _lane_timing_text(snapshot: DiagnosticsSnapshot) -> str:
    return "; ".join(
        _timing_line(name, snapshot)
        for name in ("telemetry_read", "json_read", "stream_read", "embedded_read", "values_update", "graph_update", "shell_chrome_update")
    )


def _jank_line(name: str, collector: DiagnosticsCollector) -> str:
    buckets = collector.jank_buckets(name)
    return ", ".join(f"{key}={value}" for key, value in buckets.items())


def _all_jank_text(collector: DiagnosticsCollector) -> str:
    names = ("heartbeat", "graph_update", "json_read", "diagnostics_update", "shell_chrome_update")
    return "; ".join(f"{name}: {_jank_line(name, collector)}" for name in names)


def _hidden_skip_summary(snapshot: DiagnosticsSnapshot) -> str:
    return (
        f"Live Monitor hidden-page skips: {snapshot.hidden_page_skips.get('Live Monitor', 0)}; "
        f"Effective Response Stack hidden-page skips: {snapshot.hidden_page_skips.get('Effective Response Stack', 0)}; "
        f"Flight Recorder hidden-page skips: {snapshot.hidden_page_skips.get('Flight Recorder', 'not instrumented')}"
    )


def _key(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text)).strip("_")
