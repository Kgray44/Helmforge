from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel, QPushButton, QWidget

from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from v3_app.liquid.components import (
    LiquidAdvancedSection,
    LiquidDetailPanel,
    LiquidHeroPanel,
    LiquidInspectorPanel,
    LiquidPage,
)
from v3_app.liquid.flow_components import RouteFlowRow
from v3_app.liquid.glass import action_button, glass_panel
from v3_app.liquid.layout import grid_layout, horizontal_layout, vertical_layout
from v3_app.liquid.models.mapping_edit_model import (
    MappingEditModel,
    MappingEditResult,
    MappingEditableField,
    MappingRouteRecord,
    build_mapping_edit_model,
    stage_mapping_route_edit,
)
from v3_app.liquid.status_components import MetricTile, StatusChip, StatusLight, status_tone_for_role
from v3_app.services.app_state import AppState


StageEditCallback = Callable[[str, str, str], MappingEditResult]
RevertCallback = Callable[[], None]
RouteCallback = Callable[[str], None]
RouteSelectCallback = Callable[[str], None]


class MappingRouteDetailsPage(LiquidPage):
    def __init__(
        self,
        *,
        state: AppState | None = None,
        workspace: WorkspaceConfig | None = None,
        base_workspace: WorkspaceConfig | None = None,
        selected_route_id: str | None = None,
        on_stage_edit: StageEditCallback | None = None,
        on_revert: RevertCallback | None = None,
        on_route_requested: RouteCallback | None = None,
        on_route_selected: RouteSelectCallback | None = None,
        last_edit_result: MappingEditResult | None = None,
    ) -> None:
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._base_workspace = base_workspace or self._workspace
        self._selected_route_id = selected_route_id
        self._on_stage_edit = on_stage_edit
        self._on_revert = on_revert
        self._on_route_requested = on_route_requested
        self._on_route_selected = on_route_selected
        self._last_edit_result = last_edit_result
        self._model: MappingEditModel | None = None
        self._render_count = 0
        self._last_render_signature: tuple[object, ...] | None = None
        super().__init__(
            title="Route Details",
            subtitle="Focused workspace route editor.",
            helper_text="MAPPING / ROUTE DETAILS",
            object_name="liquidMappingRouteDetailsPage",
        )
        self.setProperty("componentRole", "MappingRouteDetailsPage")
        self.setProperty("liquidRole", "liquid_mapping_route_details_page")
        self.setProperty("routeKey", "mapping.route_details")
        self.setProperty("modeId", "mapping")
        self.setProperty("subpageId", "route_details")
        self._render()

    def stage_edit(self, route_id: str, field_id: str, value: str) -> MappingEditResult:
        if self._on_stage_edit is not None:
            return self._on_stage_edit(route_id, field_id, value)
        result = stage_mapping_route_edit(self._workspace, route_id, field_id, value)
        if result.valid:
            self._workspace = result.workspace
        self._last_edit_result = result
        self._render()
        return result

    def update_mapping_workspace(
        self,
        *,
        state: AppState | None = None,
        workspace: WorkspaceConfig | None = None,
        base_workspace: WorkspaceConfig | None = None,
        selected_route_id: str | None = None,
        last_edit_result: MappingEditResult | None = None,
    ) -> None:
        if state is not None:
            self._state = state
        if workspace is not None:
            self._workspace = workspace
        if base_workspace is not None:
            self._base_workspace = base_workspace
        if selected_route_id is not None:
            self._selected_route_id = selected_route_id
        self._last_edit_result = last_edit_result
        next_signature = _edit_render_signature(
            self._state,
            self._workspace,
            self._base_workspace,
            self._selected_route_id,
            self._last_edit_result,
        )
        if next_signature == self._last_render_signature:
            return
        self._render()

    def _render(self) -> None:
        model = build_mapping_edit_model(
            workspace=self._workspace,
            base_workspace=self._base_workspace,
            selected_route_id=self._selected_route_id,
        )
        self._model = model
        self._selected_route_id = model.selected_route.route_id
        self._render_count += 1
        self._last_render_signature = _edit_render_signature(
            self._state,
            self._workspace,
            self._base_workspace,
            self._selected_route_id,
            self._last_edit_result,
        )
        self.setProperty("mappingEditRenderCount", self._render_count)
        self.setProperty("selectedRouteId", self._selected_route_id)
        self.set_header(
            _edit_header(
                "Route Details",
                "Mapping / Route Details",
                "mapping.route_details",
                "How does this physical control route through workspace intent?",
            )
        )
        self.set_status_rail(_edit_status_rail(model, self._state))
        self.set_hero(_route_details_hero(model.selected_route, self._last_edit_result))
        self.set_inspector(_route_summary_panel(model.selected_route))
        self.set_detail(_route_editor_panel(model.selected_route, self.stage_edit, object_name="liquidMappingRouteEditor"))
        self.set_advanced(
            _route_guidance_panel(
                model,
                self._last_edit_result,
                on_revert=self._on_revert,
                on_route_requested=self._on_route_requested,
            )
        )


class MappingAdvancedRouteTablesPage(LiquidPage):
    def __init__(
        self,
        *,
        state: AppState | None = None,
        workspace: WorkspaceConfig | None = None,
        base_workspace: WorkspaceConfig | None = None,
        selected_route_id: str | None = None,
        on_stage_edit: StageEditCallback | None = None,
        on_revert: RevertCallback | None = None,
        on_route_requested: RouteCallback | None = None,
        on_route_selected: RouteSelectCallback | None = None,
        last_edit_result: MappingEditResult | None = None,
    ) -> None:
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._base_workspace = base_workspace or self._workspace
        self._selected_route_id = selected_route_id
        self._on_stage_edit = on_stage_edit
        self._on_revert = on_revert
        self._on_route_requested = on_route_requested
        self._on_route_selected = on_route_selected
        self._last_edit_result = last_edit_result
        self._model: MappingEditModel | None = None
        self._render_count = 0
        self._last_render_signature: tuple[object, ...] | None = None
        super().__init__(
            title="Advanced Route Tables",
            subtitle="Grouped workspace route table editor.",
            helper_text="MAPPING / ADVANCED TABLES",
            object_name="liquidMappingAdvancedRouteTablesPage",
        )
        self.setProperty("componentRole", "MappingAdvancedRouteTablesPage")
        self.setProperty("liquidRole", "liquid_mapping_advanced_route_tables_page")
        self.setProperty("routeKey", "mapping.advanced_route_tables")
        self.setProperty("modeId", "mapping")
        self.setProperty("subpageId", "advanced_route_tables")
        self._render()

    def stage_edit(self, route_id: str, field_id: str, value: str) -> MappingEditResult:
        if self._on_stage_edit is not None:
            return self._on_stage_edit(route_id, field_id, value)
        result = stage_mapping_route_edit(self._workspace, route_id, field_id, value)
        if result.valid:
            self._workspace = result.workspace
        self._selected_route_id = route_id
        self._last_edit_result = result
        self._render()
        return result

    def select_route(self, route_id: str) -> None:
        self._selected_route_id = route_id
        if self._on_route_selected is not None:
            self._on_route_selected(route_id)
        self._render()

    def update_mapping_workspace(
        self,
        *,
        state: AppState | None = None,
        workspace: WorkspaceConfig | None = None,
        base_workspace: WorkspaceConfig | None = None,
        selected_route_id: str | None = None,
        last_edit_result: MappingEditResult | None = None,
    ) -> None:
        if state is not None:
            self._state = state
        if workspace is not None:
            self._workspace = workspace
        if base_workspace is not None:
            self._base_workspace = base_workspace
        if selected_route_id is not None:
            self._selected_route_id = selected_route_id
        self._last_edit_result = last_edit_result
        next_signature = _edit_render_signature(
            self._state,
            self._workspace,
            self._base_workspace,
            self._selected_route_id,
            self._last_edit_result,
        )
        if next_signature == self._last_render_signature:
            return
        self._render()

    def _render(self) -> None:
        model = build_mapping_edit_model(
            workspace=self._workspace,
            base_workspace=self._base_workspace,
            selected_route_id=self._selected_route_id,
        )
        self._model = model
        self._selected_route_id = model.selected_route.route_id
        self._render_count += 1
        self._last_render_signature = _edit_render_signature(
            self._state,
            self._workspace,
            self._base_workspace,
            self._selected_route_id,
            self._last_edit_result,
        )
        self.setProperty("mappingEditRenderCount", self._render_count)
        self.setProperty("selectedRouteId", self._selected_route_id)
        self.set_header(
            _edit_header(
                "Advanced Route Tables",
                "Mapping / Advanced Route Tables",
                "mapping.advanced_route_tables",
                "What advanced route details are available for later editing?",
            )
        )
        self.set_status_rail(_edit_status_rail(model, self._state))
        self.set_hero(_advanced_tables_hero(model))
        self.set_inspector(_route_editor_panel(model.selected_route, self.stage_edit, object_name="liquidMappingSelectedRouteEditor"))
        self.set_detail(_grouped_route_tables(model, self.stage_edit, self.select_route))
        self.set_advanced(
            _route_guidance_panel(
                model,
                self._last_edit_result,
                on_revert=self._on_revert,
                on_route_requested=self._on_route_requested,
            )
        )


def create_mapping_route_details_page(**kwargs) -> MappingRouteDetailsPage:
    return MappingRouteDetailsPage(**kwargs)


def create_mapping_advanced_route_tables_page(**kwargs) -> MappingAdvancedRouteTablesPage:
    return MappingAdvancedRouteTablesPage(**kwargs)


def _edit_render_signature(
    state: AppState | None,
    workspace: WorkspaceConfig,
    base_workspace: WorkspaceConfig,
    selected_route_id: str | None,
    last_edit_result: MappingEditResult | None,
) -> tuple[object, ...]:
    model = build_mapping_edit_model(
        workspace=workspace,
        base_workspace=base_workspace,
        selected_route_id=selected_route_id,
    )
    route_signature = tuple(
        (
            record.route_id,
            record.logical_function,
            record.output_intent_target,
            record.enabled_state,
            record.status,
            record.changed,
            record.warning,
            tuple((field.field_id, field.value, field.editable) for field in record.editable_fields),
        )
        for record in model.route_records
    )
    last_edit_signature = (
        None
        if last_edit_result is None
        else (
            last_edit_result.valid,
            last_edit_result.route_id,
            last_edit_result.field_id,
            last_edit_result.staged_value,
            last_edit_result.message,
            last_edit_result.validation_errors,
        )
    )
    return (
        model.selected_route.route_id,
        model.changed_count,
        bool(state.saved) if state is not None else None,
        workspace.active_profile,
        workspace.source_path,
        workspace.state.saved,
        route_signature,
        last_edit_signature,
    )


def _edit_header(title: str, route_label: str, route_key: str, purpose: str) -> QFrame:
    header = glass_panel(f"liquidMappingEditHeader_{_object_slug(route_key)}", role="liquid_page_header")
    header.setProperty("componentRole", "MappingEditPageHeader")
    header.setProperty("liquidComponent", True)
    layout = horizontal_layout(header, margins=(14, 9, 14, 9), spacing=10)
    title_column = vertical_layout(spacing=3)
    kicker = QLabel("LIQUID COMMAND DECK")
    kicker.setObjectName("liquidComponentKicker")
    title_label = QLabel(title)
    title_label.setObjectName("liquidComponentTitle")
    subtitle = QLabel(purpose)
    subtitle.setObjectName("liquidComponentSubtitle")
    subtitle.setWordWrap(True)
    title_column.addWidget(kicker)
    title_column.addWidget(title_label)
    title_column.addWidget(subtitle)
    route_chip = StatusChip(route_label, state_role="info")
    route_chip.setProperty("routeChip", True)
    route_chip.setToolTip(route_key)
    layout.addLayout(title_column, 1)
    layout.addWidget(route_chip)
    layout.addWidget(StatusChip("Draft mapping change", state_role="unsaved"))
    layout.addWidget(StatusChip("Output proof unchanged", state_role="info"))
    return header


def _edit_status_rail(model: MappingEditModel, state: AppState | None) -> QFrame:
    rail = glass_panel("liquidMappingEditStatusRail", role="liquid_mapping_edit_status_rail")
    rail.setProperty("componentRole", "MappingEditStatusRail")
    rail.setProperty("liquidComponent", True)
    layout = horizontal_layout(rail, margins=(12, 7, 12, 7), spacing=8)
    saved = bool(state.saved) if state is not None else model.changed_count == 0
    layout.addWidget(StatusChip(model.draft_state_label, state_role="unsaved" if model.changed_count else "info"))
    layout.addWidget(StatusChip("Workspace route edit", state_role="info"))
    layout.addWidget(StatusChip("Output Intent only", state_role="info"))
    layout.addWidget(StatusChip("Saved" if saved else "Unsaved workspace", state_role="saved" if saved else "unsaved"))
    layout.addStretch(1)
    return rail


def _route_details_hero(record: MappingRouteRecord, last_result: MappingEditResult | None) -> LiquidHeroPanel:
    hero = LiquidHeroPanel(
        "Route Details",
        f"{record.physical_label}: edit supported workspace route fields as a staged draft.",
        object_name="liquidMappingRouteDetailsHero",
        kicker="FOCUSED ROUTE EDITOR",
        state_role=record.status_role,
        minimum_height=220,
    )
    hero.setProperty("mappingEditHero", True)
    _append_to_panel(
        hero,
        RouteFlowRow(
            source_label=record.physical_label,
            function_label=record.logical_function,
            target_label=record.output_intent_target,
            status_role=record.status_role,
            helper_text="Workspace draft route only. Output proof unchanged.",
            object_name="liquidMappingEditRouteFlow",
        ),
    )
    _append_to_panel(hero, _edit_result_banner(last_result, default_text="No staged route edit yet."))
    return hero


def _advanced_tables_hero(model: MappingEditModel) -> LiquidHeroPanel:
    hero = LiquidHeroPanel(
        "Advanced Route Tables",
        "Compact editable rows grouped by route type. Save workspace to persist staged draft changes.",
        object_name="liquidMappingAdvancedTablesHero",
        kicker="BULK ROUTE REVIEW",
        state_role="unsaved" if model.changed_count else "info",
        minimum_height=210,
    )
    hero.setProperty("mappingAdvancedTablesHero", True)
    metrics = glass_panel("liquidMappingAdvancedTablesMetrics", role="liquid_mapping_edit_metrics")
    metrics.setProperty("componentRole", "MappingAdvancedTablesMetrics")
    layout = grid_layout(metrics, margins=(0, 6, 0, 0), spacing=10)
    counts = _route_counts(model.route_records)
    for index, (label, value, caption, role) in enumerate(
        (
            ("Axis routes", str(counts["axis"]), "editable output/function intent", "info"),
            ("Button routes", str(counts["button"]), "editable output intent", "info"),
            ("Hat routes", str(counts["hat"]), "read-only complex route", "info"),
            ("Draft changes", str(model.changed_count), "workspace route edits", "unsaved" if model.changed_count else "info"),
        )
    ):
        layout.addWidget(MetricTile(label, value, caption, state_role=role), index // 2, index % 2)
    _append_to_panel(hero, metrics)
    return hero


def _route_summary_panel(record: MappingRouteRecord) -> LiquidInspectorPanel:
    panel = LiquidInspectorPanel(
        "Selected Route",
        "This inspector shows the route being edited. Selection does not write output.",
        object_name="liquidMappingRouteSummary",
        liquid_role="liquid_context_inspector_region",
        minimum_height=270,
    )
    panel.setProperty("mappingRouteSummary", True)
    for label, value, role in (
        ("Selected control", record.physical_label, record.status_role),
        ("Control type", record.control_type.title(), "info"),
        ("Physical control ID", record.physical_control_id, "info"),
        ("Raw channel", record.raw_channel, "info"),
        ("Logical function", record.logical_function, record.status_role),
        ("Output Intent", record.output_intent_target, "info"),
        ("Mapped status", record.status.title(), record.status_role),
        ("Runtime proof", "Read-only runtime proof; Output proof unchanged.", "simulation"),
    ):
        _append_to_panel(panel, _detail_row(label, value, role))
    if record.warning:
        _append_to_panel(panel, _detail_row("Warning", record.warning, "warning"))
    return panel


def _route_editor_panel(
    record: MappingRouteRecord,
    on_stage_edit: StageEditCallback,
    *,
    object_name: str,
) -> LiquidDetailPanel:
    panel = LiquidDetailPanel(
        "Route Editor",
        "Supported fields stage workspace route edits only.",
        object_name=object_name,
        liquid_role="liquid_detail_action_region",
        minimum_height=300,
    )
    panel.setProperty("mappingRouteEditor", True)
    panel.setProperty("selectedRouteId", record.route_id)
    _append_to_panel(panel, _editor_mode_banner(record))
    for field in record.editable_fields:
        _append_to_panel(panel, _field_editor_row(record, field, on_stage_edit))
    return panel


def _editor_mode_banner(record: MappingRouteRecord) -> QFrame:
    banner = glass_panel("liquidMappingEditorModeBanner", role="liquid_mapping_editor_banner")
    banner.setProperty("componentRole", "MappingEditorModeBanner")
    banner.setProperty("liquidComponent", True)
    layout = horizontal_layout(banner, margins=(12, 9, 12, 9), spacing=8)
    layout.addWidget(StatusLight(state_role=record.status_role))
    label = QLabel("Draft mapping change - workspace route edit")
    label.setObjectName("liquidMappingEditorModeLabel")
    label.setWordWrap(True)
    layout.addWidget(label, 1)
    layout.addWidget(StatusChip("Output proof unchanged", state_role="info"))
    return banner


def _field_editor_row(
    record: MappingRouteRecord,
    field: MappingEditableField,
    on_stage_edit: StageEditCallback,
) -> QFrame:
    row = glass_panel(f"liquidMappingField_{_object_slug(record.route_id)}_{field.field_id}", role="liquid_mapping_field_row")
    row.setProperty("componentRole", "MappingEditableFieldRow")
    row.setProperty("liquidComponent", True)
    row.setProperty("mappingEditableField", field.editable)
    row.setProperty("fieldId", field.field_id)
    row.setProperty("routeId", record.route_id)
    row.setProperty("readOnly", not field.editable)
    row.setProperty("statusRole", "unsaved" if field.editable else "unavailable")
    row.setProperty("toneRole", status_tone_for_role("unsaved" if field.editable else "unavailable"))
    layout = horizontal_layout(row, margins=(10, 8, 10, 8), spacing=8)
    label = QLabel(field.label)
    label.setObjectName("liquidMappingFieldLabel")
    label.setWordWrap(True)
    layout.addWidget(label, 1)
    if field.editable:
        control = QComboBox()
        control.setObjectName(f"liquidMappingFieldControl_{_object_slug(record.route_id)}_{field.field_id}")
        control.setProperty("mappingFieldControl", True)
        control.setProperty("fieldId", field.field_id)
        control.setProperty("routeId", record.route_id)
        control.addItems(field.options or (field.value,))
        if field.value in field.options:
            control.setCurrentText(field.value)
        stage = action_button(
            "Stage change",
            object_name=f"liquidMappingStageButton_{_object_slug(record.route_id)}_{field.field_id}",
            enabled=True,
        )
        stage.setProperty("mappingStageButton", True)
        stage.setProperty("routeId", record.route_id)
        stage.setProperty("fieldId", field.field_id)
        stage.setToolTip("Stage this workspace route edit. It does not change output proof.")
        stage.clicked.connect(lambda _checked=False, combo=control, route_id=record.route_id, field_id=field.field_id: on_stage_edit(route_id, field_id, combo.currentText()))
        layout.addWidget(control, 2)
        layout.addWidget(stage)
    else:
        value = QLabel(f"{field.value} - {field.read_only_reason}")
        value.setObjectName("liquidMappingFieldReadOnlyValue")
        value.setWordWrap(True)
        layout.addWidget(value, 2)
    return row


def _grouped_route_tables(
    model: MappingEditModel,
    on_stage_edit: StageEditCallback,
    on_select_route: RouteSelectCallback,
) -> LiquidDetailPanel:
    panel = LiquidDetailPanel(
        "Compact Editable Rows",
        "Compact editable rows grouped by Axes / Buttons / Hat; full data remains in the edit model.",
        object_name="liquidMappingEditableRouteGroups",
        liquid_role="liquid_detail_action_region",
        minimum_height=420,
    )
    panel.setProperty("mappingEditableRouteGroups", True)
    for group_id, title in (("axis", "Axis routes"), ("button", "Button routes"), ("hat", "Hat routes"), ("auxiliary", "Unmapped / warnings")):
        records = tuple(record for record in model.route_records if _group_for_record(record) == group_id)
        if not records:
            continue
        _append_to_panel(panel, _route_group(group_id, title, records, model.selected_route.route_id, on_stage_edit, on_select_route))
    return panel


def _route_group(
    group_id: str,
    title: str,
    records: tuple[MappingRouteRecord, ...],
    selected_route_id: str,
    on_stage_edit: StageEditCallback,
    on_select_route: RouteSelectCallback,
) -> QFrame:
    group = glass_panel(f"liquidMappingRouteGroup_{group_id}", role="liquid_mapping_route_group")
    group.setProperty("componentRole", "MappingRouteGroup")
    group.setProperty("liquidComponent", True)
    group.setProperty("mappingRouteGroup", True)
    group.setProperty("routeGroup", group_id)
    layout = vertical_layout(group, margins=(12, 10, 12, 10), spacing=7)
    heading = horizontal_layout(spacing=8)
    title_label = QLabel(title)
    title_label.setObjectName("liquidMappingRouteGroupTitle")
    heading.addWidget(title_label, 1)
    heading.addWidget(StatusChip(f"{len(records)} routes", state_role="info"))
    layout.addLayout(heading)
    for record in records:
        layout.addWidget(_compact_route_row(record, selected_route_id, on_stage_edit, on_select_route))
    return group


def _compact_route_row(
    record: MappingRouteRecord,
    selected_route_id: str,
    on_stage_edit: StageEditCallback,
    on_select_route: RouteSelectCallback,
) -> QFrame:
    row = glass_panel(f"liquidMappingEditableRow_{_object_slug(record.route_id)}", role="liquid_mapping_editable_row")
    row.setProperty("componentRole", "MappingEditableRouteRow")
    row.setProperty("liquidComponent", True)
    row.setProperty("mappingEditableRouteRow", True)
    row.setProperty("routeId", record.route_id)
    row.setProperty("selected", record.route_id == selected_route_id)
    row.setProperty("statusRole", record.status_role)
    row.setProperty("toneRole", status_tone_for_role(record.status_role))
    layout = grid_layout(row, margins=(10, 8, 10, 8), spacing=8)
    for index, (label, value) in enumerate(
        (
            ("Route", record.physical_label),
            ("Raw channel", record.raw_channel),
            ("Function", record.logical_function),
            ("Output Intent", record.output_intent_target),
            ("Status", record.status),
        )
    ):
        layout.addWidget(_compact_cell(label, value), 0, index)
    select = action_button("Select", object_name=f"liquidMappingSelectRoute_{_object_slug(record.route_id)}", enabled=True)
    select.setProperty("routeId", record.route_id)
    select.clicked.connect(lambda _checked=False, route_id=record.route_id: on_select_route(route_id))
    layout.addWidget(select, 0, 5)
    editable_target = next(
        (field for field in record.editable_fields if field.field_id == "output_intent_target" and field.editable),
        None,
    )
    if editable_target is not None:
        combo = QComboBox()
        combo.setObjectName(f"liquidMappingInlineOutput_{_object_slug(record.route_id)}")
        combo.setProperty("mappingFieldControl", True)
        combo.setProperty("fieldId", editable_target.field_id)
        combo.setProperty("routeId", record.route_id)
        combo.addItems(editable_target.options)
        if editable_target.value in editable_target.options:
            combo.setCurrentText(editable_target.value)
        stage = action_button("Stage", object_name=f"liquidMappingInlineStage_{_object_slug(record.route_id)}", enabled=True)
        stage.setProperty("mappingStageButton", True)
        stage.clicked.connect(lambda _checked=False, route_id=record.route_id, field_id=editable_target.field_id, combo=combo: on_stage_edit(route_id, field_id, combo.currentText()))
        layout.addWidget(combo, 1, 3)
        layout.addWidget(stage, 1, 4)
    else:
        read_only = QLabel("Read-only in LCD-5G")
        read_only.setObjectName("liquidMappingInlineReadOnly")
        layout.addWidget(read_only, 1, 3, 1, 2)
    return row


def _route_guidance_panel(
    model: MappingEditModel,
    last_result: MappingEditResult | None,
    *,
    on_revert: RevertCallback | None,
    on_route_requested: RouteCallback | None,
) -> LiquidAdvancedSection:
    panel = LiquidAdvancedSection(
        "Validation and Draft Notes",
        "Normal controls answer what can be changed; this section explains exact edit state.",
        object_name="liquidMappingEditAdvancedNotes",
        liquid_role="liquid_advanced_region",
        minimum_height=230,
    )
    panel.setProperty("advancedSecondary", True)
    panel.setProperty("visualWeight", "subdued")
    _append_to_panel(panel, _edit_result_banner(last_result, default_text=model.draft_state_label))
    for note in model.truth_source_notes:
        _append_to_panel(panel, _note_row(note))
    actions = glass_panel("liquidMappingEditAdvancedActions", role="liquid_mapping_edit_actions")
    actions.setProperty("pageActionCluster", True)
    actions_layout = horizontal_layout(actions, margins=(12, 9, 12, 9), spacing=8)
    actions_layout.addWidget(_copy_button("Copy route details", "liquidMappingCopyRouteDetailsButton", _selected_route_text(model.selected_route)))
    actions_layout.addWidget(_copy_button("Copy route table summary", "liquidMappingCopyRouteTableSummaryButton", _route_table_summary_text(model)))
    actions_layout.addWidget(_validate_button("Validate route", "liquidMappingValidateRouteButton", model.selected_route.route_id))
    actions_layout.addWidget(_validate_button("Validate all routes", "liquidMappingValidateAllRoutesButton", "all routes"))
    actions_layout.addWidget(_navigation_button("HOTAS Map", "mapping.hotas_map", on_route_requested))
    actions_layout.addWidget(_navigation_button("Advanced Route Tables", "mapping.advanced_route_tables", on_route_requested))
    add_route = action_button("Add route", object_name="liquidMappingAddRouteButton", enabled=False)
    add_route.setToolTip("Add route is deferred because route creation is not represented as a safe workspace operation in this Liquid phase.")
    add_route.setAccessibleDescription(add_route.toolTip())
    actions_layout.addWidget(add_route)
    revert_selected = action_button("Revert selected route edit", object_name="liquidMappingRevertSelectedRouteButton", enabled=on_revert is not None)
    revert_selected.setToolTip("Revert staged Mapping route edits to the original Liquid workspace draft." if on_revert is not None else "Revert selected route is unavailable without shell draft ownership.")
    revert_selected.setAccessibleDescription(revert_selected.toolTip())
    if on_revert is not None:
        revert_selected.clicked.connect(lambda _checked=False: on_revert())
    actions_layout.addWidget(revert_selected)
    revert = action_button("Revert staged route edits", object_name="liquidMappingRevertDraftButton", enabled=on_revert is not None)
    revert.setProperty("mappingRevertDraftButton", True)
    revert.setToolTip("Revert all staged Mapping route edits to the original Liquid workspace draft." if on_revert is not None else "Revert is unavailable without shell draft ownership.")
    revert.setAccessibleDescription(revert.toolTip())
    if on_revert is not None:
        revert.clicked.connect(lambda _checked=False: on_revert())
    actions_layout.addWidget(revert)
    actions_layout.addStretch(1)
    _append_to_panel(panel, actions)
    return panel


def _edit_result_banner(last_result: MappingEditResult | None, *, default_text: str) -> QFrame:
    role = "ready" if last_result is not None and last_result.valid else "warning" if last_result is not None else "info"
    banner = glass_panel("liquidMappingEditResultBanner", role="liquid_mapping_edit_result")
    banner.setProperty("componentRole", "MappingEditResultBanner")
    banner.setProperty("liquidComponent", True)
    banner.setProperty("statusRole", role)
    banner.setProperty("toneRole", status_tone_for_role(role))
    layout = horizontal_layout(banner, margins=(12, 9, 12, 9), spacing=8)
    layout.addWidget(StatusLight(state_role=role))
    text = QLabel(last_result.message if last_result is not None else default_text)
    text.setObjectName("liquidMappingEditResultText")
    text.setWordWrap(True)
    layout.addWidget(text, 1)
    if last_result is not None:
        layout.addWidget(StatusChip(last_result.status_label, state_role=role))
    return banner


def _note_row(text: str) -> QFrame:
    row = glass_panel(f"liquidMappingEditNote_{_object_slug(text)[:28]}", role="liquid_mapping_edit_note")
    layout = horizontal_layout(row, margins=(12, 8, 12, 8), spacing=8)
    layout.addWidget(StatusLight(state_role="info"))
    label = QLabel(text)
    label.setObjectName("liquidMappingEditNoteText")
    label.setWordWrap(True)
    layout.addWidget(label, 1)
    return row


def _detail_row(label_text: str, value_text: str, role: str) -> QFrame:
    row = glass_panel(f"liquidMappingEditDetail_{_object_slug(label_text)}", role="liquid_mapping_edit_detail")
    row.setProperty("componentRole", "MappingEditDetailRow")
    row.setProperty("liquidComponent", True)
    row.setProperty("statusRole", role)
    row.setProperty("toneRole", status_tone_for_role(role))
    layout = horizontal_layout(row, margins=(12, 8, 12, 8), spacing=8)
    label = QLabel(label_text)
    label.setObjectName("liquidMappingEditDetailLabel")
    value = QLabel(value_text)
    value.setObjectName("liquidMappingEditDetailValue")
    value.setWordWrap(True)
    layout.addWidget(label, 1)
    layout.addWidget(value, 2)
    return row


def _compact_cell(label_text: str, value_text: str) -> QFrame:
    cell = glass_panel(f"liquidMappingEditCell_{_object_slug(label_text)}", role="liquid_mapping_edit_cell")
    layout = vertical_layout(cell, margins=(6, 4, 6, 4), spacing=2)
    label = QLabel(label_text)
    label.setObjectName("liquidMappingEditCellLabel")
    value = QLabel(value_text)
    value.setObjectName("liquidMappingEditCellValue")
    value.setWordWrap(True)
    layout.addWidget(label)
    layout.addWidget(value)
    return cell


def _navigation_button(text: str, route_key: str, on_route_requested: RouteCallback | None) -> QPushButton:
    button = action_button(text, object_name=f"liquidMappingNavigate_{_object_slug(route_key)}", enabled=on_route_requested is not None)
    button.setProperty("routeTarget", route_key)
    button.setProperty("navigationOnly", True)
    button.setToolTip(f"Navigate to {route_key}. This does not edit workspace routes by itself.")
    if on_route_requested is not None:
        button.clicked.connect(lambda _checked=False, target=route_key: on_route_requested(target))
    return button


def _copy_button(text: str, object_name: str, payload: str) -> QPushButton:
    button = action_button(text, object_name=object_name, enabled=True)
    button.setProperty("copyOnly", True)
    button.setToolTip("Copy route information to the clipboard. This does not edit workspace or runtime state.")
    button.setStatusTip(button.toolTip())
    button.setAccessibleDescription(button.toolTip())
    button.clicked.connect(lambda _checked=False, data=payload: _copy_to_clipboard(data))
    return button


def _validate_button(text: str, object_name: str, target: str) -> QPushButton:
    button = action_button(text, object_name=object_name, enabled=True)
    button.setProperty("validationOnly", True)
    button.setToolTip(f"Validate {target}. This reports draft route state only and does not write output.")
    button.setStatusTip(button.toolTip())
    button.setAccessibleDescription(button.toolTip())
    return button


def _copy_to_clipboard(text: str) -> None:
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)


def _selected_route_text(record: MappingRouteRecord) -> str:
    return "\n".join(
        (
            f"Route: {record.route_id}",
            f"Physical control: {record.physical_label}",
            f"Raw channel: {record.raw_channel}",
            f"Logical function: {record.logical_function}",
            f"Output Intent: {record.output_intent_target}",
            f"Status: {record.status}",
            "Output proof unchanged by copy action.",
        )
    )


def _route_table_summary_text(model: MappingEditModel) -> str:
    counts = _route_counts(model.route_records)
    return "\n".join(
        (
            f"Axis routes: {counts['axis']}",
            f"Button routes: {counts['button']}",
            f"Hat routes: {counts['hat']}",
            f"Draft changes: {model.changed_count}",
            "Route edits are workspace/draft mapping edits only.",
        )
    )


def _route_counts(records: tuple[MappingRouteRecord, ...]) -> dict[str, int]:
    return {
        "axis": sum(1 for record in records if record.control_type == "axis"),
        "button": sum(1 for record in records if record.control_type == "button"),
        "hat": sum(1 for record in records if record.control_type == "hat"),
    }


def _group_for_record(record: MappingRouteRecord) -> str:
    if record.control_type in {"axis", "button", "hat"} and not record.warning:
        return record.control_type
    return "auxiliary"


def _append_to_panel(panel: QWidget, widget: QWidget) -> None:
    layout = panel.layout()
    if layout is None:
        return
    insert_at = max(0, layout.count() - 1)
    layout.insertWidget(insert_at, widget)


def _object_slug(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value).strip("_")
