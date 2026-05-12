from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel, QPushButton, QSizePolicy, QTreeWidget, QTreeWidgetItem, QWidget

from shared_core.models.runtime import RuntimeMode, RuntimePreflightStatus, RuntimeTruth
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.telemetry import BridgeTelemetrySnapshot
from v3_app.liquid.components import (
    LiquidAdvancedSection,
    LiquidDetailPanel,
    LiquidHeroPanel,
    LiquidInspectorPanel,
    LiquidPage,
    LiquidPageHeader,
)
from v3_app.liquid.flow_components import RouteFlowRow, SignalPipelineStage
from v3_app.liquid.glass import action_button, glass_panel, mark_action_feedback, refresh_style
from v3_app.liquid.instruments import AxisBarPair, CapabilityRail, ResponseCurveGraph
from v3_app.liquid.layout import horizontal_layout, vertical_layout
from v3_app.liquid.models.tuning_command_model import (
    TuningCommandModel,
    TuningEditResult,
    TuningParameterModel,
    build_tuning_command_model,
    stage_tuning_parameter_edit,
)
from v3_app.liquid.parameter_controls import (
    AxisSelectorPills,
    DropdownParameterControl,
    GuidanceBlock,
    LiveSnapshotBlock,
    NumericParameterControl,
    ParameterLabelWithInfo,
)
from v3_app.liquid.status_components import DraftStateIndicator, MetricTile, StatusChip, TruthBadge
from v3_app.services.app_state import AppState


StageEditCallback = Callable[[str, str, str, str], TuningEditResult]
AxisSelectedCallback = Callable[[str, str], None]
RouteCallback = Callable[[str], None]
RevertCallback = Callable[[], None]


@dataclass(frozen=True)
class TuningPreset:
    preset_id: str
    name: str
    category: str
    purpose: str
    base_tuning: str
    filtering: str
    combat_profile: str
    rules: str


BUILT_IN_TUNING_PRESETS: tuple[TuningPreset, ...] = (
    TuningPreset(
        preset_id="balanced_default",
        name="Balanced Default",
        category="Built-in Presets",
        purpose="Conservative general-purpose tuning for everyday flying and vehicle control.",
        base_tuning="Linear response with a modest center deadzone and no aggressive scaling.",
        filtering="Light smoothing with no heavy lag.",
        combat_profile="Neutral combat response; faster modes are reviewed before staging.",
        rules="No automatic rule injection.",
    ),
    TuningPreset(
        preset_id="precision_aim",
        name="Precision Aim",
        category="Built-in Presets",
        purpose="Softer center and finer small movement control for careful aiming.",
        base_tuning="Gentle center response with reduced near-zero sensitivity.",
        filtering="Light-to-moderate smoothing for micro-corrections.",
        combat_profile="Precision-biased curve preview; no live combat mutation.",
        rules="Rules remain workspace-owned.",
    ),
    TuningPreset(
        preset_id="smooth_flight",
        name="Smooth Flight",
        category="Built-in Presets",
        purpose="Stronger smoothing and gentle response for stable flight.",
        base_tuning="Soft response ramp with conservative output intent.",
        filtering="Higher smoothing and slew damping preview.",
        combat_profile="Gentle profile, not a combat boost.",
        rules="No automatic rule injection.",
    ),
    TuningPreset(
        preset_id="combat_response",
        name="Combat Response",
        category="Built-in Presets",
        purpose="Faster response / combat-oriented profile while preserving output proof boundaries.",
        base_tuning="Quicker magnitude growth outside the center.",
        filtering="Lower smoothing to preserve rapid reversals.",
        combat_profile="Combat curve preview keeps sign and center crossing sane.",
        rules="Mode and rule changes remain draft-only if supported later.",
    ),
)


class TuningCommandPage(LiquidPage):
    def __init__(
        self,
        *,
        route_key: str,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        base_workspace: WorkspaceConfig | None = None,
        selected_axis: str = "Roll",
        telemetry: BridgeTelemetrySnapshot | None = None,
        on_axis_selected: AxisSelectedCallback | None = None,
        on_stage_edit: StageEditCallback | None = None,
        on_route_requested: RouteCallback | None = None,
        on_revert: RevertCallback | None = None,
        last_edit_result: TuningEditResult | None = None,
    ) -> None:
        self.route_key = route_key
        self.state = state
        self.workspace = workspace or create_default_workspace()
        self.base_workspace = base_workspace or self.workspace
        self.selected_axis = selected_axis
        self.telemetry = telemetry
        self._on_axis_selected = on_axis_selected
        self._on_stage_edit = on_stage_edit
        self._on_route_requested = on_route_requested
        self._on_revert = on_revert
        self._last_edit_result = last_edit_result
        self._render_signature: tuple[object, ...] | None = None
        self._render_structure_signature: tuple[object, ...] | None = None
        self._current_model: TuningCommandModel | None = None
        self._parameter_controls: dict[str, QWidget] = {}
        self.render_count = 0
        super().__init__(
            title=_title_for_route(route_key),
            subtitle=_question_for_route(route_key),
            object_name="liquidTuningCommandPage",
        )
        self.setProperty("routeKey", route_key)
        self.setProperty("modeId", "tuning")
        self.setProperty("selectedAxis", selected_axis)
        self.setProperty("lcdPhase", "LCD-6")
        self.setProperty("tuningRenderCount", self.render_count)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._render(force=True)

    def select_axis(self, axis_name: str) -> None:
        if axis_name == self.selected_axis:
            return
        self.selected_axis = axis_name
        self.setProperty("selectedAxis", axis_name)
        if self._on_axis_selected is not None:
            self._on_axis_selected(self.route_key, axis_name)
        self._render(force=True)

    def stage_parameter_edit(self, parameter_id: str, value_text: str | None = None) -> TuningEditResult:
        if value_text is None:
            control = self._parameter_controls.get(parameter_id)
            value_text = _control_value(control)
        if self._on_stage_edit is not None:
            result = self._on_stage_edit(self.route_key, self.selected_axis, parameter_id, value_text or "")
        else:
            result = stage_tuning_parameter_edit(
                self.workspace,
                self.route_key,
                self.selected_axis,
                parameter_id,
                value_text or "",
            )
            if result.valid:
                self.workspace = result.workspace
        self._last_edit_result = result
        self._mark_parameter_control_validation(parameter_id, valid=result.valid)
        if result.valid:
            self._render(force=True)
        return result

    def update_tuning_workspace(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig,
        base_workspace: WorkspaceConfig,
        selected_axis: str,
        last_edit_result: TuningEditResult | None,
        telemetry: BridgeTelemetrySnapshot | None = None,
    ) -> None:
        self.state = state
        self.workspace = workspace
        self.base_workspace = base_workspace
        self.selected_axis = selected_axis
        self.telemetry = telemetry
        self._last_edit_result = last_edit_result
        self.setProperty("selectedAxis", selected_axis)
        next_model = build_tuning_command_model(
            route_key=self.route_key,
            workspace=self.workspace,
            base_workspace=self.base_workspace,
            selected_axis=self.selected_axis,
            state=self.state,
            telemetry=self.telemetry,
        )
        if self._can_update_live_preview_in_place(next_model):
            self._update_live_preview_in_place(next_model)
            return
        self._render(force=False)

    def _render(self, *, force: bool = False) -> None:
        model = build_tuning_command_model(
            route_key=self.route_key,
            workspace=self.workspace,
            base_workspace=self.base_workspace,
            selected_axis=self.selected_axis,
            state=self.state,
            telemetry=self.telemetry,
        )
        signature = _model_signature(model, self._last_edit_result)
        if not force and signature == self._render_signature:
            return
        self._render_signature = signature
        self._render_structure_signature = _model_structure_signature(model, self._last_edit_result)
        self._current_model = model
        self._parameter_controls = {}
        self.render_count += 1
        self.setProperty("tuningRenderCount", self.render_count)

        self.set_header(_build_header(model))
        self.set_status_rail(_build_status_rail(self, model, self._last_edit_result))
        self.set_hero(_build_hero(self, model))
        if self.route_key == "tuning.conditional_rules":
            self.set_inspector(_build_rule_inspector(self, model))
            self.set_detail(_build_rule_details(model))
        else:
            self.set_inspector(_build_axis_context(self, model))
            self.set_detail(_build_parameter_inspector(self, model, self._last_edit_result))
        self.set_advanced(_build_advanced(model))

    def _mark_parameter_control_validation(self, parameter_id: str, *, valid: bool) -> None:
        control = self._parameter_controls.get(parameter_id)
        if control is not None:
            control.setProperty("validationState", "valid" if valid else "invalid")
            refresh_style(control)

    def _can_update_live_preview_in_place(self, model: TuningCommandModel) -> bool:
        if self._current_model is None or model.preview_graph is None:
            return False
        if self.route_key not in {"tuning.base_tuning", "tuning.filtering", "tuning.combat_profile"}:
            return False
        if _model_structure_signature(model, self._last_edit_result) != self._render_structure_signature:
            return False
        return self.findChild(QWidget, "liquidTuningResponseGraph") is not None

    def _update_live_preview_in_place(self, model: TuningCommandModel) -> None:
        self._current_model = model
        self._render_signature = _model_signature(model, self._last_edit_result)
        graph = self.findChild(ResponseCurveGraph, "liquidTuningResponseGraph")
        if graph is not None and model.preview_graph is not None:
            graph.update_model(
                title=model.preview_graph.title,
                graph_kind=model.preview_graph.graph_kind,
                lines=tuple((line.label, line.points, line.role) for line in model.preview_graph.lines),
                markers=tuple((marker.label, marker.point, marker.role) for marker in model.preview_graph.markers),
                selected_axis=model.preview_graph.selected_axis,
                x_range=model.preview_graph.x_range,
                y_range=model.preview_graph.y_range,
                state_role=model.preview.state_role,
            )
        instrument = self.findChild(AxisBarPair, "liquidTuningResponseInstrument")
        if instrument is not None:
            instrument.update_values(
                raw_value=model.preview.raw_value,
                output_intent_value=model.preview.output_intent_value,
            )
        snapshot = self.findChild(LiveSnapshotBlock, "liquidTuningLiveSnapshot")
        if snapshot is not None:
            snapshot.update_values(
                selected_control=model.selected_axis,
                source_truth_label=model.preview.source_truth_label,
                raw_value=f"{model.preview.raw_value:.2f}"
                + ("" if "Passive live telemetry" in model.preview.source_truth_label else " (Current sample unavailable)"),
                output_intent_value=f"Output Intent preview {model.preview.output_intent_value:.2f}",
                state_role=model.preview.state_role,
            )


def create_base_tuning_command_page(**kwargs) -> TuningCommandPage:
    _ensure_defaults(kwargs)
    return TuningCommandPage(route_key="tuning.base_tuning", **kwargs)


def create_filtering_command_page(**kwargs) -> TuningCommandPage:
    _ensure_defaults(kwargs)
    return TuningCommandPage(route_key="tuning.filtering", **kwargs)


def create_combat_profile_command_page(**kwargs) -> TuningCommandPage:
    _ensure_defaults(kwargs)
    return TuningCommandPage(route_key="tuning.combat_profile", **kwargs)


def create_conditional_rules_command_page(**kwargs) -> TuningCommandPage:
    _ensure_defaults(kwargs)
    return TuningCommandPage(route_key="tuning.conditional_rules", **kwargs)


def create_profiles_library_command_page(**kwargs) -> LiquidPage:
    _ensure_defaults(kwargs)
    return TuningProfilesLibraryPage(**kwargs)


class TuningProfilesLibraryPage(LiquidPage):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        base_workspace: WorkspaceConfig | None = None,
        on_route_requested: RouteCallback | None = None,
        **_kwargs,
    ) -> None:
        self.state = state
        self.workspace = workspace or create_default_workspace()
        self.base_workspace = base_workspace or self.workspace
        self._on_route_requested = on_route_requested
        self.render_count = 0
        self._render_signature: tuple[object, ...] | None = None
        self._selected_preset_id = "current_workspace"
        super().__init__(
            title="Profiles Library",
            subtitle="Workspace tuning profile review and safe profile utilities.",
            object_name="liquidTuningProfilesLibraryPage",
        )
        self.setProperty("routeKey", "tuning.profiles_library")
        self.setProperty("modeId", "tuning")
        self.setProperty("profilesLibraryPage", True)
        self.setProperty("profilesLibraryRenderCount", self.render_count)
        self._render()

    def select_profile_preset(self, preset_id: str) -> None:
        if preset_id == self._selected_preset_id:
            return
        if preset_id not in _profile_preset_ids():
            return
        self._selected_preset_id = preset_id
        self.setProperty("selectedPresetId", preset_id)
        self._render()

    def update_tuning_workspace(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig,
        base_workspace: WorkspaceConfig,
        **_kwargs,
    ) -> None:
        self.state = state
        self.workspace = workspace
        self.base_workspace = base_workspace
        self._render()

    def _render(self) -> None:
        signature = _profiles_render_signature(self.state, self.workspace, self._selected_preset_id)
        if signature == self._render_signature:
            return
        self._render_signature = signature
        self.render_count += 1
        self.setProperty("profilesLibraryRenderCount", self.render_count)
        active_profile = self.workspace.active_profile
        self.set_header(
            LiquidPageHeader(
                "Profiles Library",
                "Which workspace tuning profiles are available and what can I safely do with them?",
                kicker="TUNING COMMAND",
                object_name="liquidTuningProfilesHeader",
            )
        )
        self.set_status_rail(_profiles_status_rail(active_profile, self.workspace))
        selected_preset = _preset_by_id(self._selected_preset_id, self.workspace)
        self.set_hero(_profiles_hero(active_profile, self.workspace, selected_preset))
        self.set_inspector(_profiles_preset_browser(self, self.workspace, selected_preset))
        self.set_detail(_profiles_actions_panel(self.workspace, self._on_route_requested, selected_preset))
        self.set_advanced(_profiles_advanced(self.workspace))


def _profiles_status_rail(active_profile: str, workspace: WorkspaceConfig) -> QFrame:
    rail = glass_panel("liquidTuningProfilesStatusRail", role="liquid_tuning_profiles_status")
    rail.setProperty("profilesLibraryStatusRail", True)
    layout = horizontal_layout(rail, margins=(12, 8, 12, 8), spacing=8)
    layout.addWidget(StatusChip(f"Active profile: {active_profile}", state_role="info"))
    layout.addWidget(StatusChip("Workspace draft only", state_role="simulation"))
    layout.addWidget(StatusChip(f"Rules: {len(workspace.rules.rules)}", state_role="info"))
    layout.addStretch(1)
    return rail


def _profiles_render_signature(state: AppState, workspace: WorkspaceConfig, selected_preset_id: str = "current_workspace") -> tuple[object, ...]:
    return (
        selected_preset_id,
        workspace.active_profile,
        state.saved,
        len(workspace.tuning.axes),
        len(workspace.filtering.axes),
        len(workspace.combat.axes),
        len(workspace.rules.rules),
        len(workspace.mappings.axis_routes),
        len(workspace.mappings.button_routes),
        len(workspace.mappings.hat_routes),
    )


def _profile_preset_ids() -> set[str]:
    return {"current_workspace", "import_pending", *(preset.preset_id for preset in BUILT_IN_TUNING_PRESETS)}


def _preset_by_id(preset_id: str, workspace: WorkspaceConfig) -> TuningPreset:
    if preset_id == "current_workspace":
        return TuningPreset(
            preset_id="current_workspace",
            name="Current Workspace",
            category="Active Workspace",
            purpose=f"Current active workspace profile: {workspace.active_profile}.",
            base_tuning=f"{len(workspace.tuning.axes)} base tuning axis records.",
            filtering=f"{len(workspace.filtering.axes)} filtering axis records.",
            combat_profile=f"{len(workspace.combat.axes)} combat profile axis records.",
            rules=f"{len(workspace.rules.rules)} conditional rules.",
        )
    if preset_id == "import_pending":
        return TuningPreset(
            preset_id="import_pending",
            name="Empty / import pending",
            category="Imported Profiles",
            purpose="No imported profile is available from the current safe workspace surfaces.",
            base_tuning="Import support is deferred.",
            filtering="Import support is deferred.",
            combat_profile="Import support is deferred.",
            rules="Imported rule preview unavailable.",
        )
    for preset in BUILT_IN_TUNING_PRESETS:
        if preset.preset_id == preset_id:
            return preset
    return _preset_by_id("current_workspace", workspace)


def _profiles_preset_tree(page: TuningProfilesLibraryPage, selected_preset_id: str) -> QTreeWidget:
    tree = QTreeWidget()
    tree.setObjectName("liquidTuningProfilesPresetTree")
    tree.setProperty("profilesPresetTree", True)
    tree.setHeaderHidden(True)
    tree.setMinimumHeight(260)
    tree.setColumnCount(1)
    selected_item: QTreeWidgetItem | None = None

    def add_child(parent: QTreeWidgetItem, preset_id: str, label: str) -> QTreeWidgetItem:
        nonlocal selected_item
        item = QTreeWidgetItem(parent, [label])
        item.setData(0, Qt.ItemDataRole.UserRole, preset_id)
        if preset_id == selected_preset_id:
            selected_item = item
        return item

    active = QTreeWidgetItem(tree, ["Active Workspace"])
    active.setExpanded(True)
    add_child(active, "current_workspace", "Current Workspace")

    built_in = QTreeWidgetItem(tree, ["Built-in Presets"])
    built_in.setExpanded(True)
    for preset in BUILT_IN_TUNING_PRESETS:
        add_child(built_in, preset.preset_id, preset.name)

    imported = QTreeWidgetItem(tree, ["Imported Profiles"])
    imported.setExpanded(True)
    add_child(imported, "import_pending", "Empty / import pending")

    if selected_item is not None:
        tree.setCurrentItem(selected_item)

    def on_selection_changed() -> None:
        current = tree.currentItem()
        if current is None:
            return
        preset_id = current.data(0, Qt.ItemDataRole.UserRole)
        if preset_id:
            page.select_profile_preset(str(preset_id))

    tree.itemSelectionChanged.connect(on_selection_changed)
    return tree


def _profiles_preset_preview(preset: TuningPreset, workspace: WorkspaceConfig) -> QFrame:
    preview = glass_panel("liquidTuningProfilesPresetPreview", role="liquid_tuning_profiles_preset_preview")
    preview.setProperty("componentRole", "TuningPresetPreview")
    preview.setProperty("selectedPresetId", preset.preset_id)
    preview.setProperty("selectedPresetName", preset.name)
    layout = vertical_layout(preview, margins=(12, 10, 12, 10), spacing=7)
    layout.addWidget(StatusChip(f"{preset.category}: {preset.name}", state_role="simulation" if preset.preset_id != "current_workspace" else "info"))
    for label, value in (
        ("Purpose", preset.purpose),
        ("Base tuning", preset.base_tuning),
        ("Filtering", preset.filtering),
        ("Combat profile", preset.combat_profile),
        ("Rules", preset.rules),
        ("Workspace", f"Active profile {workspace.active_profile}; output proof unchanged."),
    ):
        row = horizontal_layout(spacing=8)
        row.addWidget(QLabel(label), 1)
        value_label = QLabel(value)
        value_label.setWordWrap(True)
        row.addWidget(value_label, 2)
        layout.addLayout(row)
    return preview


def _profiles_hero(active_profile: str, workspace: WorkspaceConfig, selected_preset: TuningPreset) -> LiquidHeroPanel:
    hero = LiquidHeroPanel(
        "Profiles Library",
        "Tree-style preset selector and tuning/profile utilities. Selecting a preset previews it only.",
        object_name="liquidTuningProfilesHero",
        state_role="info",
        minimum_height=260,
    )
    hero.setProperty("profilesLibraryHero", True)
    _add_to_panel(hero, MetricTile("Active profile", active_profile, "Current workspace profile name", state_role="info"))
    _add_to_panel(hero, MetricTile("Axes tuned", str(len(workspace.tuning.axes)), "Base tuning axis records", state_role="info"))
    _add_to_panel(hero, MetricTile("Rules", str(len(workspace.rules.rules)), "Conditional rules in workspace", state_role="info"))
    _add_to_panel(hero, MetricTile("Selected preset", selected_preset.name, selected_preset.purpose, state_role="simulation"))
    return hero


def _profiles_preset_browser(page: TuningProfilesLibraryPage, workspace: WorkspaceConfig, selected_preset: TuningPreset) -> LiquidInspectorPanel:
    panel = LiquidInspectorPanel(
        "Preset Browser",
        "Folder-style profile selection. Choosing a preset updates the preview; it does not auto-apply.",
        object_name="liquidTuningProfilesSummary",
    )
    panel.setProperty("profilesSummaryPanel", True)
    _add_to_panel(panel, _profiles_preset_tree(page, selected_preset.preset_id))
    _add_to_panel(panel, _profiles_preset_preview(selected_preset, workspace))
    return panel


def _profiles_actions_panel(workspace: WorkspaceConfig, on_route_requested: RouteCallback | None, selected_preset: TuningPreset) -> LiquidDetailPanel:
    panel = LiquidDetailPanel(
        "Profile Commands",
        "Only safe copy/navigation actions are enabled until profile mutation semantics are represented.",
        object_name="liquidTuningProfilesActions",
    )
    panel.setProperty("pageActionCluster", True)
    actions = glass_panel("liquidTuningProfilesActionCluster", role="liquid_tuning_profiles_actions")
    layout = horizontal_layout(actions, margins=(12, 9, 12, 9), spacing=8)
    layout.addWidget(_copy_button("Copy profile summary", "liquidTuningProfilesCopySummaryButton", _profiles_summary_text(workspace)))
    layout.addWidget(_copy_button("Copy preset summary", "liquidTuningProfilesCopyPresetButton", _preset_summary_text(selected_preset, workspace)))
    apply_reason = "Disabled: applying presets to the workspace draft is not represented by the current safe profile semantics."
    apply_button = action_button(
        "Apply preset to draft",
        object_name="liquidTuningProfilesApplyPresetButton",
        enabled=False,
        action_kind="disabled_deferred",
        disabled_reason=apply_reason,
    )
    apply_button.setProperty("draftOnly", False)
    apply_button.setToolTip(apply_reason)
    apply_button.setStatusTip(apply_reason)
    apply_button.setAccessibleDescription(apply_reason)
    layout.addWidget(apply_button)
    for label, route_key in (
        ("Open Base Tuning", "tuning.base_tuning"),
        ("Open Filtering", "tuning.filtering"),
        ("Open Combat Profile", "tuning.combat_profile"),
        ("Open Conditional Rules", "tuning.conditional_rules"),
    ):
        layout.addWidget(_route_button(label, route_key, on_route_requested))
    for text, reason, name in (
        ("Import profile", "Disabled: profile import is not represented as a safe Liquid workspace operation.", "liquidTuningProfilesImportButton"),
        ("Export profile", "Disabled: dedicated profile export is not represented by the current workspace services.", "liquidTuningProfilesExportButton"),
        ("Duplicate / rename / delete", "Disabled: profile library mutation is deferred until workspace profile semantics are explicit.", "liquidTuningProfilesMutateButton"),
        ("Save profile", "Disabled: profile persistence stays with the global Save Workspace action.", "liquidTuningProfilesSaveButton"),
    ):
        disabled = action_button(text, object_name=name, enabled=False, action_kind="disabled_deferred", disabled_reason=reason)
        disabled.setToolTip(reason)
        disabled.setAccessibleDescription(reason)
        layout.addWidget(disabled)
    layout.addStretch(1)
    _add_to_panel(panel, actions)
    return panel


def _profiles_advanced(workspace: WorkspaceConfig) -> LiquidAdvancedSection:
    advanced = LiquidAdvancedSection(
        "Profile Details",
        "Secondary workspace profile facts.",
        object_name="liquidTuningProfilesAdvanced",
    )
    advanced.setProperty("advancedSecondary", True)
    details = QLabel(_profiles_summary_text(workspace))
    details.setWordWrap(True)
    _add_to_panel(advanced, details)
    return advanced


def _profiles_summary_text(workspace: WorkspaceConfig) -> str:
    return "\n".join(
        (
            f"Active profile: {workspace.active_profile}",
            f"Base tuning axes: {len(workspace.tuning.axes)}",
            f"Filtering axes: {len(workspace.filtering.axes)}",
            f"Combat profile axes: {len(workspace.combat.axes)}",
            f"Conditional rules: {len(workspace.rules.rules)}",
            "Profile copy/navigation action only; runtime truth unchanged.",
        )
    )


def _preset_summary_text(preset: TuningPreset, workspace: WorkspaceConfig) -> str:
    return "\n".join(
        (
            f"Preset: {preset.name}",
            f"Category: {preset.category}",
            f"Purpose: {preset.purpose}",
            f"Base tuning: {preset.base_tuning}",
            f"Filtering: {preset.filtering}",
            f"Combat profile: {preset.combat_profile}",
            f"Rules: {preset.rules}",
            f"Workspace active profile: {workspace.active_profile}",
            "Selecting or copying a preset does not apply it, save it, write vJoy, or prove output.",
        )
    )


def _build_header(model: TuningCommandModel) -> LiquidPageHeader:
    header = LiquidPageHeader(
        model.page_title,
        model.page_question,
        kicker="TUNING COMMAND",
        object_name="liquidTuningHeader",
    )
    header.setProperty("routeKey", model.route_key)
    header.setProperty("tuningHeader", True)
    return header


def _build_status_rail(page: TuningCommandPage, model: TuningCommandModel, last_edit_result: TuningEditResult | None) -> QFrame:
    rail = glass_panel("liquidTuningStatusRail", role="liquid_tuning_status_rail")
    rail.setProperty("tuningStatusRail", True)
    layout = horizontal_layout(rail, margins=(12, 8, 12, 8), spacing=8)
    selector = AxisSelectorPills(
        selected_axis=model.selected_axis,
        options=model.axis_options,
        object_name="liquidTuningTopAxisSelector",
    )
    selector.setProperty("topLevelAxisSelector", True)
    selector.selectionChanged.connect(page.select_axis)
    layout.addWidget(selector)
    layout.addWidget(StatusChip(f"Axis: {model.selected_axis}", state_role="info"))
    nav_purpose = _navigation_purpose(model.route_key)
    if nav_purpose != model.page_question:
        layout.addWidget(StatusChip(nav_purpose, state_role="info"))
    layout.addWidget(StatusChip(model.draft_state_label, state_role="unsaved" if "staged" in model.draft_state_label else "info"))
    layout.addWidget(StatusChip("Preview only", state_role="simulation"))
    layout.addWidget(StatusChip("Output proof unchanged", state_role="simulation"))
    if last_edit_result is not None:
        layout.addWidget(StatusChip(last_edit_result.status_label, state_role="unsaved" if last_edit_result.valid else "warning"))
    layout.addStretch(1)
    return rail


def _build_hero(page: TuningCommandPage, model: TuningCommandModel) -> LiquidHeroPanel:
    hero = LiquidHeroPanel(
        model.preview.title,
        model.preview.summary,
        object_name="liquidTuningHero",
        liquid_role="liquid_tuning_response_hero",
        state_role=model.preview.state_role,
        minimum_height=520,
    )
    hero.setProperty("tuningResponseHero", True)
    hero.setProperty("primaryVisualRole", "response-preview")
    hero.setProperty("dominantInstrument", True)
    if model.route_key == "tuning.conditional_rules":
        _add_to_panel(hero, _rule_status_summary(model))
    if model.preview_graph is not None:
        _add_to_panel(
            hero,
            ResponseCurveGraph(
                title=model.preview_graph.title,
                graph_kind=model.preview_graph.graph_kind,
                lines=tuple((line.label, line.points, line.role) for line in model.preview_graph.lines),
                markers=tuple((marker.label, marker.point, marker.role) for marker in model.preview_graph.markers),
                selected_axis=model.preview_graph.selected_axis,
                x_range=model.preview_graph.x_range,
                y_range=model.preview_graph.y_range,
                state_role=model.preview.state_role,
                object_name="liquidTuningResponseGraph",
            ),
        )
    _add_to_panel(
        hero,
        AxisBarPair(
            "Passive response instrument",
            raw_value=model.preview.raw_value,
            output_intent_value=model.preview.output_intent_value,
            state_role=model.preview.state_role,
            object_name="liquidTuningResponseInstrument",
        ),
    )
    _add_to_panel(
        hero,
        TruthBadge(
            model.preview.source_truth_label,
            state_role=model.preview.state_role,
            helper_text="Response preview and Output Intent are not output verification.",
            object_name="liquidTuningPreviewTruthBadge",
        ),
    )
    if model.metrics:
        _add_to_panel(
            hero,
            CapabilityRail(
                capabilities=_capability_metrics(model.metrics[:3]),
                object_name="liquidTuningHeroMetrics",
            ),
        )
    _add_to_panel(hero, _build_tuning_action_cluster(page, model))
    return hero


def _rule_status_summary(model: TuningCommandModel) -> QFrame:
    summary = glass_panel("liquidTuningRuleStatusHero", role="liquid_tuning_rule_status_hero")
    summary.setProperty("componentRole", "ConditionalRuleStatusHero")
    summary.setProperty("liquidComponent", True)
    layout = horizontal_layout(summary, margins=(12, 9, 12, 9), spacing=8)
    layout.addWidget(StatusChip(f"Axis context: {model.selected_axis}", state_role="info"))
    for label, value, caption, role in model.metrics:
        layout.addWidget(MetricTile(label, value, caption, state_role=role), 1)
    layout.addStretch(1)
    return summary


def _build_tuning_action_cluster(page: TuningCommandPage, model: TuningCommandModel) -> QFrame:
    object_name = "liquidTuningRuleActionCluster" if model.route_key == "tuning.conditional_rules" else "liquidTuningCommandActions"
    actions = glass_panel(object_name, role="liquid_tuning_command_actions")
    actions.setProperty("componentRole", "TuningCommandActions")
    actions.setProperty("liquidComponent", True)
    actions.setProperty("pageActionCluster", True)
    layout = horizontal_layout(actions, margins=(0, 6, 0, 4), spacing=8)
    if model.route_key == "tuning.conditional_rules":
        for text, name in (
            ("Add rule", "liquidTuningAddRuleButton"),
            ("Edit selected rule", "liquidTuningEditRuleButton"),
            ("Enable / disable rule", "liquidTuningEnableRuleButton"),
        ):
            disabled = action_button(
                text,
                object_name=name,
                enabled=False,
                action_kind="disabled_deferred",
                disabled_reason="Disabled: conditional rule mutation is deferred because no safe Liquid rule-edit workspace seam exists.",
            )
            disabled.setToolTip("Conditional rule mutation is deferred because no safe Liquid rule-edit workspace seam exists in LCD-7R.")
            disabled.setAccessibleDescription(disabled.toolTip())
            layout.addWidget(disabled)
        layout.addWidget(_copy_button("Copy rule summary", "liquidTuningCopyRuleSummaryButton", _tuning_summary_text(model)))
        layout.addWidget(_validate_button("Validate rules", "liquidTuningValidateRulesButton"))
    else:
        layout.addWidget(_copy_button("Copy tuning parameters", "liquidTuningCopyParametersButton", _tuning_summary_text(model)))
        layout.addWidget(_copy_button("Copy curve preview values", "liquidTuningCopyPreviewButton", _graph_summary_text(model)))
        reset = action_button(
            "Reset selected axis",
            object_name="liquidTuningResetAxisButton",
            enabled=False,
            action_kind="disabled_deferred",
            disabled_reason="Disabled: axis reset is deferred because this phase does not add a route-level default restore operation.",
        )
        reset.setToolTip("Axis reset is deferred because this phase does not add a route-level default restore operation.")
        reset.setAccessibleDescription(reset.toolTip())
        layout.addWidget(reset)
        revert = action_button(
            "Revert selected axis tuning",
            object_name="liquidTuningRevertAxisButton",
            enabled=page._on_revert is not None,
            action_kind="revert",
            disabled_reason="Disabled: revert is unavailable without shell draft ownership." if page._on_revert is None else "",
        )
        revert.setToolTip("Revert staged tuning edits to the original Liquid workspace draft." if page._on_revert else "Revert is unavailable without shell draft ownership.")
        revert.setAccessibleDescription(revert.toolTip())
        if page._on_revert is not None:
            revert.clicked.connect(lambda _checked=False: page._on_revert())
        layout.addWidget(revert)
        for label, route_key in _tuning_navigation_targets(model.route_key):
            layout.addWidget(_route_button(label, route_key, page._on_route_requested))
    layout.addStretch(1)
    return actions


def _build_axis_context(page: TuningCommandPage, model: TuningCommandModel) -> LiquidInspectorPanel:
    panel = LiquidInspectorPanel(
        "Axis Context",
        "Select an axis, inspect the passive snapshot, and stage workspace tuning edits.",
        object_name="liquidTuningAxisSelectorPanel",
        liquid_role="liquid_tuning_axis_context",
    )
    panel.setProperty("tuningAxisContext", True)
    selector = AxisSelectorPills(
        selected_axis=model.selected_axis,
        options=model.axis_options,
        object_name="liquidTuningAxisSelector",
    )
    selector.selectionChanged.connect(page.select_axis)
    _add_to_panel(panel, selector)
    _add_to_panel(
        panel,
        LiveSnapshotBlock(
            selected_control=model.selected_axis,
            source_truth_label=model.preview.source_truth_label,
            raw_value=f"{model.preview.raw_value:.2f}" + ("" if "Passive live telemetry" in model.preview.source_truth_label else " (Current sample unavailable)"),
            output_intent_value=f"Output Intent preview {model.preview.output_intent_value:.2f}",
            state_role=model.preview.state_role,
            object_name="liquidTuningLiveSnapshot",
        ),
    )
    _add_to_panel(
        panel,
        GuidanceBlock(
            current_feel=model.guidance["current_feel"],
            affects=model.guidance["affects"],
            suggested_range=model.guidance["suggested_range"],
            caution=model.guidance["caution"],
            selected_axis_note=model.guidance["selected_axis_note"],
            object_name="liquidTuningGuidance",
        ),
    )
    return panel


def _build_parameter_inspector(
    page: TuningCommandPage,
    model: TuningCommandModel,
    last_edit_result: TuningEditResult | None,
) -> LiquidDetailPanel:
    panel = LiquidDetailPanel(
        "Parameter Inspector",
        "Metadata-backed controls stage workspace tuning changes only.",
        object_name="liquidTuningParameterInspector",
        liquid_role="liquid_tuning_parameter_inspector",
    )
    panel.setProperty("tuningParameterInspector", True)
    if last_edit_result is not None:
        _add_to_panel(
            panel,
            DraftStateIndicator(
                last_edit_result.message,
                state_role="unsaved" if last_edit_result.valid else "warning",
                object_name="liquidTuningLastEditResult",
            ),
        )
    for parameter in model.parameters:
        _add_to_panel(panel, _parameter_row(page, parameter))
    return panel


def _parameter_row(page: TuningCommandPage, parameter: TuningParameterModel) -> QFrame:
    row = glass_panel(
        f"liquidTuningRow_{_safe_id(parameter.parameter_id)}",
        role="liquid_tuning_parameter_row",
    )
    row.setProperty("tuningParameterRow", True)
    row.setProperty("componentRole", "ParameterRow")
    row.setProperty("liquidComponent", True)
    row.setProperty("parameterId", parameter.parameter_id)
    row.setProperty("changed", parameter.changed)
    layout = horizontal_layout(row, margins=(12, 9, 12, 9), spacing=10)
    label = ParameterLabelWithInfo(
        parameter.label,
        help_text=parameter.help_text,
        metadata={
            "description": parameter.help_text,
            "unit": parameter.units,
        },
        object_name=f"liquidTuningLabel_{_safe_id(parameter.parameter_id)}",
    )
    layout.addWidget(label, 1)
    control: QWidget
    if parameter.control_kind == "dropdown":
        control = DropdownParameterControl(
            options=parameter.options,
            selected=parameter.value_text,
            object_name=f"liquidTuningControl_{_safe_id(parameter.parameter_id)}",
        )
    elif parameter.control_kind == "numeric":
        control = NumericParameterControl(
            value=float(parameter.value),
            min_value=parameter.minimum,
            max_value=parameter.maximum,
            decimals=3,
            object_name=f"liquidTuningControl_{_safe_id(parameter.parameter_id)}",
        )
        control.setProperty("minValue", parameter.minimum)
        control.setProperty("maxValue", parameter.maximum)
    else:
        control = QLabel(parameter.read_only_reason or parameter.value_text)
        control.setObjectName(f"liquidTuningControl_{_safe_id(parameter.parameter_id)}")
        control.setProperty("componentRole", "ReadOnlyTuningParameter")
    control.setProperty("parameterId", parameter.parameter_id)
    page._parameter_controls[parameter.parameter_id] = control
    layout.addWidget(control, 1)
    if parameter.units:
        layout.addWidget(QLabel(parameter.units))
    stage = action_button(
        "Stage tuning change",
        object_name=f"liquidTuningStage_{_safe_id(parameter.parameter_id)}",
        enabled=parameter.control_kind != "readonly",
        action_kind="stage_draft" if parameter.control_kind != "readonly" else "disabled_deferred",
        disabled_reason=(parameter.read_only_reason or "Disabled: this tuning field is read-only.") if parameter.control_kind == "readonly" else "",
    )
    stage.setProperty("tuningStageButton", True)
    stage.setProperty("parameterId", parameter.parameter_id)
    stage.clicked.connect(lambda checked=False, pid=parameter.parameter_id: page.stage_parameter_edit(pid))
    layout.addWidget(stage)
    if parameter.changed:
        layout.addWidget(StatusChip("Draft tuning change", state_role="unsaved"))
    return row


def _build_rule_inspector(page: TuningCommandPage, model: TuningCommandModel) -> LiquidInspectorPanel:
    panel = LiquidInspectorPanel(
        "Rule System Status",
        "Read-only rule visualization. Safe rule editing is deferred beyond LCD-6.",
        object_name="liquidTuningRuleInspector",
        liquid_role="liquid_tuning_rule_inspector",
    )
    panel.setProperty("tuningRuleInspector", True)
    axis_context = glass_panel("liquidTuningAxisSelectorPanel", role="liquid_tuning_axis_context")
    axis_layout = vertical_layout(axis_context, margins=(12, 10, 12, 10), spacing=9)
    selector = AxisSelectorPills(
        selected_axis=model.selected_axis,
        options=model.axis_options,
        object_name="liquidTuningAxisSelector",
    )
    selector.selectionChanged.connect(page.select_axis)
    axis_layout.addWidget(selector)
    axis_layout.addWidget(
        LiveSnapshotBlock(
            selected_control=model.selected_axis,
            source_truth_label=model.preview.source_truth_label,
            raw_value=f"{model.preview.raw_value:.2f}" if "Passive live telemetry" in model.preview.source_truth_label else "Current sample unavailable",
            output_intent_value="Rule preview only",
            state_role=model.preview.state_role,
            object_name="liquidTuningLiveSnapshot",
        )
    )
    _add_to_panel(panel, axis_context)
    _add_to_panel(panel, _selected_rule_inspector(model))
    _add_to_panel(
        panel,
        GuidanceBlock(
            current_feel=model.guidance["current_feel"],
            affects=model.guidance["affects"],
            suggested_range=model.guidance["suggested_range"],
            caution=model.guidance["caution"],
            selected_axis_note=model.guidance["selected_axis_note"],
            object_name="liquidTuningGuidance",
        ),
    )
    metrics = CapabilityRail(capabilities=_capability_metrics(model.metrics), object_name="liquidTuningRuleMetrics")
    metrics.setToolTip("Enabled rules / Disabled rules / Warnings")
    summary = QLabel("Enabled rules / Disabled rules / Warnings")
    summary.setObjectName("liquidTuningRuleMetricSummary")
    _add_to_panel(panel, summary)
    _add_to_panel(panel, metrics)
    warnings = glass_panel("liquidTuningRuleWarnings", role="liquid_tuning_rule_warnings")
    warning_layout = vertical_layout(warnings, margins=(12, 10, 12, 10), spacing=7)
    warning_layout.addWidget(QLabel("Conflict/warning checklist"))
    for warning in model.warnings:
        warning_layout.addWidget(StatusChip(warning, state_role="warning" if "disabled" in warning.casefold() else "info"))
    _add_to_panel(panel, warnings)
    _add_to_panel(panel, _rule_validation_panel(model))
    return panel


def _selected_rule_inspector(model: TuningCommandModel) -> QFrame:
    inspector = glass_panel("liquidTuningSelectedRuleInspector", role="liquid_tuning_selected_rule_inspector")
    inspector.setProperty("componentRole", "ConditionalRuleInspector")
    inspector.setProperty("liquidComponent", True)
    layout = vertical_layout(inspector, margins=(12, 10, 12, 10), spacing=7)
    flow = model.rule_flows[0] if model.rule_flows else None
    title = QLabel("Selected rule inspector")
    title.setObjectName("liquidTuningRuleInspectorTitle")
    layout.addWidget(title)
    if flow is None:
        layout.addWidget(QLabel("No workspace rule selected."))
        return inspector
    for label, value in (
        ("Rule", flow.title),
        ("Condition", flow.condition_label),
        ("Action", flow.action_label),
        ("State", "enabled" if flow.enabled else "disabled"),
    ):
        row = horizontal_layout(spacing=8)
        row.addWidget(QLabel(label), 1)
        value_label = QLabel(value)
        value_label.setWordWrap(True)
        row.addWidget(value_label, 2)
        layout.addLayout(row)
    return inspector


def _rule_validation_panel(model: TuningCommandModel) -> QFrame:
    panel = glass_panel("liquidTuningRuleValidationPanel", role="liquid_tuning_rule_validation")
    panel.setProperty("componentRole", "ConditionalRuleValidationPanel")
    panel.setProperty("liquidComponent", True)
    layout = vertical_layout(panel, margins=(12, 10, 12, 10), spacing=7)
    layout.addWidget(QLabel("Validation / conflict status"))
    for warning in model.warnings:
        layout.addWidget(StatusChip(warning, state_role="warning" if "disabled" in warning.casefold() else "info"))
    layout.addWidget(StatusChip("Runtime proof unchanged", state_role="simulation"))
    return panel


def _build_rule_details(model: TuningCommandModel) -> LiquidDetailPanel:
    panel = LiquidDetailPanel(
        "Condition / Action Flow",
        "Rules are shown as workspace intent, not runtime application proof.",
        object_name="liquidTuningParameterInspector",
        liquid_role="liquid_tuning_rule_details",
    )
    panel.setProperty("tuningParameterInspector", True)
    rule_list = glass_panel("liquidTuningRuleList", role="liquid_tuning_rule_list")
    rule_list.setProperty("componentRole", "ConditionalRuleList")
    rule_list.setProperty("liquidComponent", True)
    rule_layout = vertical_layout(rule_list, margins=(0, 0, 0, 0), spacing=7)
    for flow in model.rule_flows:
        row = SignalPipelineStage(
            flow.title,
            f"Condition: {flow.condition_label}\nAction: {flow.action_label}",
            selected_value="enabled" if flow.enabled else "disabled",
            status_role=flow.status_role,
            warning_text=flow.warning,
            object_name=f"liquidTuningRuleFlow_{_safe_id(flow.rule_id)}",
        )
        row.setProperty("conditionalRuleFlowRow", True)
        rule_layout.addWidget(row)
    rule_layout.addWidget(
        RouteFlowRow(
            source_label="Condition",
            function_label="Response rule",
            target_label="Output Intent preview only",
            status_role="simulation",
            helper_text="Read-only rule visualization; no workspace rule edit is staged on this page.",
            object_name="liquidTuningRuleIntentFlow",
        ),
    )
    _add_to_panel(panel, rule_list)
    return panel


def _build_advanced(model: TuningCommandModel) -> LiquidAdvancedSection:
    advanced = LiquidAdvancedSection(
        "Advanced Details",
        "Raw tuning IDs and draft status stay secondary to the response instrument.",
        object_name="liquidTuningAdvancedDetails",
        liquid_role="liquid_tuning_advanced_details",
    )
    advanced.setProperty("advancedSecondary", True)
    advanced.setProperty("visualWeight", "subdued")
    details = glass_panel("liquidTuningAdvancedGrid", role="liquid_tuning_advanced_grid")
    layout = vertical_layout(details, margins=(12, 10, 12, 10), spacing=6)
    for label, value in model.advanced_details:
        row = horizontal_layout(spacing=8)
        left = QLabel(label)
        left.setObjectName("liquidTuningAdvancedLabel")
        right = QLabel(value)
        right.setObjectName("liquidTuningAdvancedValue")
        right.setWordWrap(True)
        row.addWidget(left, 1)
        row.addWidget(right, 2)
        layout.addLayout(row)
    for note in model.truth_source_notes:
        layout.addWidget(TruthBadge(note, state_role="simulation"))
    _add_to_panel(advanced, details)
    return advanced


def _add_to_panel(panel: QWidget, widget: QWidget) -> None:
    layout = panel.layout()
    if layout is None:
        return
    insert_at = max(0, layout.count() - 1)
    layout.insertWidget(insert_at, widget)


def _model_signature(model: TuningCommandModel, last_edit_result: TuningEditResult | None) -> tuple[object, ...]:
    return (
        model.route_key,
        model.selected_axis,
        model.preview.source_truth_label,
        model.preview.raw_value,
        model.preview.output_intent_value,
        model.draft_state_label,
        tuple((marker.label, marker.point) for marker in model.preview_graph.markers) if model.preview_graph else (),
        tuple((parameter.parameter_id, parameter.value_text, parameter.changed) for parameter in model.parameters),
        tuple((flow.rule_id, flow.enabled, flow.action_label, flow.condition_label) for flow in model.rule_flows),
        last_edit_result.message if last_edit_result else "",
    )


def _model_structure_signature(model: TuningCommandModel, last_edit_result: TuningEditResult | None) -> tuple[object, ...]:
    return (
        model.route_key,
        model.selected_axis,
        model.draft_state_label,
        tuple((parameter.parameter_id, parameter.value_text, parameter.changed) for parameter in model.parameters),
        tuple((flow.rule_id, flow.enabled, flow.action_label, flow.condition_label) for flow in model.rule_flows),
        last_edit_result.message if last_edit_result else "",
    )


def _ensure_defaults(kwargs: dict) -> None:
    kwargs.setdefault("workspace", create_default_workspace())
    kwargs.setdefault("state", _default_state())


def _default_state() -> AppState:
    return AppState.from_runtime_status(
        RuntimePreflightStatus(
            mode=RuntimeMode.SIMULATED,
            truth=RuntimeTruth.SIMULATED,
        )
    )


def _capability_metrics(metrics: tuple[tuple[str, str, str, str], ...]) -> tuple[tuple[str, str, str], ...]:
    return tuple((label, role, f"{value} - {caption}") for label, value, caption, role in metrics)


def _control_value(control: QWidget | None) -> str:
    if control is None:
        return ""
    if isinstance(control, NumericParameterControl):
        return control.text()
    if isinstance(control, DropdownParameterControl) or isinstance(control, QComboBox):
        return control.currentText()
    if isinstance(control, QLabel):
        return control.text()
    return ""


def _title_for_route(route_key: str) -> str:
    return _title_for_route.cache.get(route_key, "Tuning")


_title_for_route.cache = {
    "tuning.base_tuning": "Base Tuning",
    "tuning.filtering": "Filtering",
    "tuning.combat_profile": "Combat Profile",
    "tuning.conditional_rules": "Conditional Rules",
}


def _question_for_route(route_key: str) -> str:
    return {
        "tuning.base_tuning": "How does this axis respond before filtering/modes/rules?",
        "tuning.filtering": "How much smoothing/slew behavior is applied to this axis?",
        "tuning.combat_profile": "How does this axis behave in combat/aiming mode?",
        "tuning.conditional_rules": "What rules can change the response stack, and when do they trigger?",
    }.get(route_key, "How does this axis respond and feel?")


def _navigation_purpose(route_key: str) -> str:
    return {
        "tuning.base_tuning": "How does this axis respond and feel?",
        "tuning.filtering": "How should noisy input be smoothed?",
        "tuning.combat_profile": "How should combat response differ from baseline tuning?",
        "tuning.conditional_rules": "Which rules can change the response stack, and when do they trigger?",
    }.get(route_key, _question_for_route(route_key))


def _copy_button(text: str, object_name: str, payload: str) -> QPushButton:
    button = action_button(text, object_name=object_name, enabled=True, action_kind="copy")
    button.setProperty("copyOnly", True)
    button.setToolTip("Copy Tuning information to the clipboard. This does not change runtime state.")
    button.setStatusTip(button.toolTip())
    button.setAccessibleDescription(button.toolTip())
    button.clicked.connect(lambda _checked=False, data=payload, target=button: _copy_to_clipboard(data, target))
    return button


def _route_button(text: str, route_key: str, on_route_requested: RouteCallback | None) -> QPushButton:
    reason = f"Navigate to {route_key}. This does not stage or apply tuning changes."
    if on_route_requested is None:
        reason = f"Disabled: {reason} Navigation callback unavailable in this context."
    button = action_button(
        text,
        object_name=f"liquidTuningOpen_{_safe_id(route_key)}",
        enabled=on_route_requested is not None,
        action_kind="navigation",
        disabled_reason=reason if on_route_requested is None else "",
        route_target=route_key,
    )
    button.setProperty("routeTarget", route_key)
    button.setProperty("navigationOnly", True)
    button.setToolTip(reason)
    button.setStatusTip(reason)
    button.setAccessibleDescription(reason)
    if on_route_requested is not None:
        button.clicked.connect(lambda _checked=False, target=route_key: on_route_requested(target))
    return button


def _validate_button(text: str, object_name: str) -> QPushButton:
    button = action_button(text, object_name=object_name, enabled=True, action_kind="validate")
    button.setProperty("validationOnly", True)
    button.setToolTip("Validate displayed workspace rule state only. This does not mutate runtime state.")
    button.setStatusTip(button.toolTip())
    button.setAccessibleDescription(button.toolTip())
    button.clicked.connect(lambda _checked=False, target_button=button: mark_action_feedback(target_button, "Validated displayed rule state; runtime unchanged."))
    return button


def _copy_to_clipboard(text: str, button: QPushButton | None = None) -> None:
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)
        if button is not None:
            mark_action_feedback(button, "Copied tuning information to clipboard.")
    elif button is not None:
        mark_action_feedback(button, "Clipboard unavailable; nothing was copied.")


def _tuning_summary_text(model: TuningCommandModel) -> str:
    lines = [f"Route: {model.route_key}", f"Selected axis: {model.selected_axis}", model.draft_state_label]
    lines.extend(f"{parameter.label}: {parameter.value_text}" for parameter in model.parameters)
    lines.extend(f"{flow.title}: {flow.condition_label} -> {flow.action_label}" for flow in model.rule_flows)
    lines.append("Output proof unchanged by copy action.")
    return "\n".join(lines)


def _graph_summary_text(model: TuningCommandModel) -> str:
    if model.preview_graph is None:
        return f"{model.page_title}: graph unavailable for {model.selected_axis}."
    lines = [f"{model.preview_graph.title} ({model.preview_graph.graph_kind})"]
    for line in model.preview_graph.lines:
        preview = ", ".join(f"{x:g}:{y:g}" for x, y in line.points[:: max(1, len(line.points) // 8)])
        lines.append(f"{line.label}: {preview}")
    lines.append("Preview only; output proof unchanged.")
    return "\n".join(lines)


def _tuning_navigation_targets(route_key: str) -> tuple[tuple[str, str], ...]:
    if route_key == "tuning.base_tuning":
        return (("Open Filtering", "tuning.filtering"), ("Open Combat Profile", "tuning.combat_profile"), ("Open Profiles Library", "tuning.profiles_library"))
    if route_key == "tuning.filtering":
        return (("Open Base Tuning", "tuning.base_tuning"), ("Open Combat Profile", "tuning.combat_profile"), ("Open Profiles Library", "tuning.profiles_library"))
    if route_key == "tuning.combat_profile":
        return (("Open Base Tuning", "tuning.base_tuning"), ("Open Filtering", "tuning.filtering"), ("Open Profiles Library", "tuning.profiles_library"))
    return ()


def _safe_id(text: str) -> str:
    return text.replace(".", "_").replace(":", "_").replace(" ", "_").lower()
