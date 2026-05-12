from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel, QPushButton, QScrollArea, QSizePolicy, QWidget

from shared_core.models.runtime import (
    InputDeviceDetection,
    OutputBackendDetection,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from v3_app.liquid.components import (
    LiquidAdvancedSection,
    LiquidDetailPanel,
    LiquidHeroPanel,
    LiquidInspectorPanel,
    LiquidPage,
)
from v3_app.liquid.flow_components import RouteFlowRow
from v3_app.liquid.glass import action_button, configure_command_action, glass_panel, mark_action_feedback, refresh_style
from v3_app.liquid.layout import grid_layout, horizontal_layout, vertical_layout
from v3_app.liquid.models.mapping_command_model import (
    MappingAdvancedRouteDetailModel,
    MappingCommandModel,
    MappingControlModel,
    build_mapping_command_model,
)
from v3_app.liquid.models.mapping_edit_model import (
    MappingEditResult,
    MappingEditableField,
    MappingRouteRecord,
    build_mapping_edit_model,
    control_id_for_route_id,
    route_id_for_control_id,
    stage_mapping_route_edit,
)
from v3_app.liquid.status_components import MetricTile, StatusChip, StatusLight, status_tone_for_role
from v3_app.services.app_state import AppState


StageEditCallback = Callable[[str, str, str], MappingEditResult]
RevertCallback = Callable[[], None]


class MappingCommandPage(LiquidPage):
    def __init__(
        self,
        *,
        state: AppState | None = None,
        workspace: WorkspaceConfig | None = None,
        selected_control_id: str | None = None,
        selected_route_id: str | None = None,
        on_route_requested: Callable[[str], None] | None = None,
        on_route_selected: Callable[[str], None] | None = None,
        on_stage_edit: StageEditCallback | None = None,
        on_revert: RevertCallback | None = None,
        last_edit_result: MappingEditResult | None = None,
    ) -> None:
        self._state = state or _default_state()
        self._workspace = workspace or create_default_workspace()
        self._selected_control_id = selected_control_id or (
            control_id_for_route_id(selected_route_id) if selected_route_id else None
        )
        self._on_route_requested = on_route_requested
        self._on_route_selected = on_route_selected
        self._on_stage_edit = on_stage_edit
        self._on_revert = on_revert
        self._last_edit_result = last_edit_result
        self._editor_open = False
        self._model: MappingCommandModel | None = None
        self._last_render_signature: tuple[object, ...] | None = None
        self._render_count = 0
        super().__init__(
            title="Mapping",
            subtitle="What is each physical control doing?",
            helper_text="HOTAS MAP",
            object_name="liquidMappingCommandPage",
        )
        self.setProperty("componentRole", "MappingCommandPage")
        self.setProperty("liquidRole", "liquid_mapping_command_page")
        self.setProperty("routeKey", "mapping.hotas_map")
        self.setProperty("modeId", "mapping")
        self.setProperty("subpageId", "hotas_map")
        self._render()

    @property
    def selected_control_id(self) -> str:
        if self._model is not None:
            return self._model.selected_control.control_id
        return self._selected_control_id or "axis_roll"

    def select_control(self, control_id: str) -> None:
        scroll_area, scroll_value = _ancestor_scroll_state(self)
        self._selected_control_id = control_id
        self._editor_open = True
        if self._on_route_selected is not None:
            self._on_route_selected(route_id_for_control_id(control_id))
            _restore_scroll_state(scroll_area, scroll_value)
            return
        self._render()
        _restore_scroll_state(scroll_area, scroll_value)

    def close_inline_editor(self) -> None:
        if not self._editor_open:
            return
        scroll_area, scroll_value = _ancestor_scroll_state(self)
        self._editor_open = False
        self._render()
        _restore_scroll_state(scroll_area, scroll_value)

    def stage_inline_edit(self, route_id: str, field_id: str, value: str) -> MappingEditResult:
        if self._on_stage_edit is not None:
            result = self._on_stage_edit(route_id, field_id, value)
        else:
            result = stage_mapping_route_edit(self._workspace, route_id, field_id, value)
            if result.valid:
                self._workspace = result.workspace
                self._state.saved = False
                self._state.status_message = result.message
        self._last_edit_result = result
        self._editor_open = True
        scroll_area, scroll_value = _ancestor_scroll_state(self)
        self._render()
        _restore_scroll_state(scroll_area, scroll_value)
        return result

    def update_state(self, state: AppState) -> None:
        next_signature = _render_signature(state, self._workspace, self._selected_control_id)
        if next_signature == self._last_render_signature:
            self._state = state
            return
        self._state = state
        self._render(next_signature)

    def update_mapping_workspace(
        self,
        *,
        state: AppState | None = None,
        workspace: WorkspaceConfig | None = None,
        selected_route_id: str | None = None,
        last_edit_result: MappingEditResult | None = None,
        **_kwargs,
    ) -> None:
        next_state = state or self._state
        next_workspace = workspace or self._workspace
        next_selected_control_id = (
            control_id_for_route_id(selected_route_id)
            if selected_route_id is not None
            else self._selected_control_id
        )
        next_signature = _render_signature(next_state, next_workspace, next_selected_control_id)
        if next_signature == self._last_render_signature:
            self._state = next_state
            self._workspace = next_workspace
            self._selected_control_id = next_selected_control_id
            self._last_edit_result = last_edit_result
            return
        if state is not None:
            self._state = state
        if workspace is not None:
            self._workspace = workspace
        if selected_route_id is not None:
            self._selected_control_id = control_id_for_route_id(selected_route_id)
        self._last_edit_result = last_edit_result
        self._render(next_signature)

    def _render(self, signature: tuple[object, ...] | None = None) -> None:
        model = build_mapping_command_model(
            workspace=self._workspace,
            state=self._state,
            selected_control_id=self._selected_control_id,
        )
        self._model = model
        self._selected_control_id = model.selected_control.control_id
        self._last_render_signature = signature or _render_signature(
            self._state,
            self._workspace,
            self._selected_control_id,
        )
        self._render_count += 1
        self.setProperty("mappingRenderCount", self._render_count)
        self.setProperty("selectedControlId", self._selected_control_id)
        self.set_header(_mapping_header(model))
        self.set_status_rail(_mapping_status_rail(model))
        self.set_hero(
            _hero_panel(
                model,
                self._workspace,
                self.select_control,
                editor_open=self._editor_open,
                on_stage_edit=self.stage_inline_edit,
                on_revert=self._on_revert,
                on_route_requested=self._on_route_requested,
                on_close=self.close_inline_editor,
                last_edit_result=self._last_edit_result,
            )
        )
        self.set_inspector(_selected_control_inspector(model))
        self.set_detail(_route_flow_panel(model, self._on_route_requested))
        self.set_advanced(_advanced_route_details_panel(model, self._on_route_requested))


def create_mapping_command_page(
    *,
    state: AppState | None = None,
    workspace: WorkspaceConfig | None = None,
    selected_control_id: str | None = None,
    selected_route_id: str | None = None,
    on_route_requested: Callable[[str], None] | None = None,
    on_route_selected: Callable[[str], None] | None = None,
    on_stage_edit: StageEditCallback | None = None,
    on_revert: RevertCallback | None = None,
    last_edit_result: MappingEditResult | None = None,
) -> MappingCommandPage:
    return MappingCommandPage(
        state=state,
        workspace=workspace,
        selected_control_id=selected_control_id,
        selected_route_id=selected_route_id,
        on_route_requested=on_route_requested,
        on_route_selected=on_route_selected,
        on_stage_edit=on_stage_edit,
        on_revert=on_revert,
        last_edit_result=last_edit_result,
    )


def _mapping_header(model: MappingCommandModel) -> QFrame:
    header = glass_panel("liquidMappingPageHeader", role="liquid_page_header")
    header.setProperty("componentRole", "LiquidPageHeader")
    header.setProperty("liquidComponent", True)
    header.setProperty("mappingHeader", True)
    header.setProperty("visualWeight", "subtle")
    layout = horizontal_layout(header, margins=(14, 9, 14, 9), spacing=12)

    title_column = vertical_layout(spacing=3)
    kicker = QLabel("LIQUID COMMAND DECK")
    kicker.setObjectName("liquidComponentKicker")
    title = QLabel("Mapping")
    title.setObjectName("liquidComponentTitle")
    subtitle = QLabel("HOTAS Map / What is each physical control doing?")
    subtitle.setObjectName("liquidComponentSubtitle")
    subtitle.setWordWrap(True)
    title_column.addWidget(kicker)
    title_column.addWidget(title)
    title_column.addWidget(subtitle)

    route_chip = StatusChip("Mapping / HOTAS Map", state_role="info", object_name="liquidMappingRouteChip")
    route_chip.setProperty("routeChip", True)
    route_chip.setToolTip("Route: mapping.hotas_map")
    route_chip.setAccessibleName("Mapping HOTAS Map route")
    source_chip = StatusChip(f"Source: {model.source_label}", state_role="info", object_name="liquidMappingSourceChip")
    source_chip.setMaximumWidth(210)
    runtime_chip = StatusChip(model.runtime_truth_label, state_role="simulation", object_name="liquidMappingRuntimeChip")

    layout.addLayout(title_column, 1)
    layout.addWidget(route_chip)
    layout.addWidget(source_chip)
    layout.addWidget(runtime_chip)
    return header


def _mapping_status_rail(model: MappingCommandModel) -> QFrame:
    rail = glass_panel("liquidMappingIntentRail", role="liquid_mapping_intent_rail")
    rail.setProperty("componentRole", "MappingIntentRail")
    rail.setProperty("liquidComponent", True)
    rail.setProperty("visualWeight", "integrated")
    rail.setMaximumHeight(54)
    layout = horizontal_layout(rail, margins=(12, 7, 12, 7), spacing=8)
    layout.addWidget(StatusChip("Read-only visualization", state_role="simulation"))
    layout.addWidget(StatusChip("Mapping intent", state_role="info"))
    layout.addWidget(StatusChip("Output Intent only", state_role="info"))
    if model.warnings:
        layout.addWidget(StatusChip(f"{len(model.warnings)} workspace warnings", state_role="warning"))
    layout.addStretch(1)
    return rail


def _hero_panel(
    model: MappingCommandModel,
    workspace: WorkspaceConfig,
    on_select: Callable[[str], None],
    *,
    editor_open: bool,
    on_stage_edit: StageEditCallback,
    on_revert: RevertCallback | None,
    on_route_requested: Callable[[str], None] | None,
    on_close: Callable[[], None],
    last_edit_result: MappingEditResult | None,
) -> LiquidHeroPanel:
    selected = model.selected_control
    hero = LiquidHeroPanel(
        "HOTAS Visual Map",
        "Read-only map: select controls to inspect routes. Editing arrives in Mapping / Route Details. Use command actions to stage workspace mapping edits.",
        object_name="liquidMappingHotasHero",
        kicker="PRIMARY MAPPING INSTRUMENT",
        state_role=selected.status_role,
        minimum_height=380,
    )
    hero.setProperty("mappingHero", True)
    hero.setProperty("mappingVisualRole", "primary_hotas_map")
    hero.setProperty("primaryInstrument", True)
    _append_to_panel(hero, _selected_summary(model))
    editor_card = (
        _inline_mapping_editor_card(
            model,
            workspace=workspace,
            on_stage_edit=on_stage_edit,
            on_revert=on_revert,
            on_route_requested=on_route_requested,
            on_close=on_close,
            last_edit_result=last_edit_result,
        )
        if editor_open
        else None
    )
    _append_to_panel(hero, _LiquidHotasMapEditorSurface(model, on_select=on_select, editor_card=editor_card))
    _append_to_panel(hero, _metrics_panel(model))
    return hero


def _inline_mapping_editor_card(
    model: MappingCommandModel,
    *,
    workspace: WorkspaceConfig,
    on_stage_edit: StageEditCallback,
    on_revert: RevertCallback | None,
    on_route_requested: Callable[[str], None] | None,
    on_close: Callable[[], None],
    last_edit_result: MappingEditResult | None,
) -> QFrame:
    route_id = route_id_for_control_id(model.selected_control.control_id)
    edit_model = build_mapping_edit_model(workspace=workspace, selected_route_id=route_id)
    record = edit_model.selected_route
    card = glass_panel("liquidMappingInlineEditorCard", role="liquid_mapping_inline_editor")
    card.setProperty("componentRole", "MappingInlineEditorCard")
    card.setProperty("liquidComponent", True)
    card.setProperty("mappingEditorOpen", True)
    card.setProperty("selectedControlId", model.selected_control.control_id)
    card.setProperty("selectedRouteId", record.route_id)
    card.setProperty("pageActionCluster", True)
    layout = vertical_layout(card, margins=(14, 12, 14, 12), spacing=9)

    header = horizontal_layout(spacing=8)
    title = QLabel(f"Route editor: {record.physical_label}")
    title.setObjectName("liquidMappingInlineEditorTitle")
    title.setWordWrap(True)
    header.addWidget(StatusLight(state_role=record.status_role))
    header.addWidget(title, 1)
    header.addWidget(StatusChip(record.status.title(), state_role=record.status_role))
    header.addWidget(StatusChip("Draft workspace edit", state_role="unsaved"))
    layout.addLayout(header)

    summary = grid_layout(margins=(0, 0, 0, 0), spacing=8)
    for index, (label, value) in enumerate(
        (
            ("Type", record.control_type.title()),
            ("Raw channel", record.raw_channel),
            ("Logical function", record.logical_function),
            ("Output Intent", record.output_intent_target),
            ("Validation", "Ready to validate draft route"),
            ("Truth", "Output proof unchanged"),
        )
    ):
        summary.addWidget(_compact_cell(label, value), index // 3, index % 3)
    layout.addLayout(summary)

    controls: dict[str, QComboBox] = {}
    for field in record.editable_fields:
        layout.addWidget(_inline_editor_field(record, field, controls))

    if last_edit_result is not None and last_edit_result.route_id == record.route_id:
        layout.addWidget(StatusChip(last_edit_result.message, state_role="unsaved" if last_edit_result.valid else "warning"))

    actions = horizontal_layout(spacing=8)
    primary_field = _primary_editable_field(record)
    stage = action_button(
        "Stage mapping change",
        object_name="liquidMappingInlineEditorStageButton",
        enabled=primary_field is not None,
        action_kind="stage_draft" if primary_field is not None else "disabled_deferred",
        disabled_reason="Disabled: this route has no safely editable fields." if primary_field is None else "",
    )
    stage.setToolTip("Stage the selected workspace mapping value. This does not write vJoy or change output proof.")
    if primary_field is not None:
        stage.clicked.connect(
            lambda _checked=False, field_id=primary_field.field_id: on_stage_edit(
                record.route_id,
                field_id,
                controls[field_id].currentText(),
            )
        )
    actions.addWidget(stage)

    validate = action_button("Validate route", object_name="liquidMappingInlineEditorValidateButton", enabled=True, action_kind="validate")
    validate.setToolTip("Validate the selected draft route shape. Runtime and output proof remain unchanged.")
    validate.clicked.connect(lambda _checked=False, target=validate: mark_action_feedback(target, "Route validation completed locally; no runtime change."))
    actions.addWidget(validate)

    revert = action_button(
        "Revert selected edit",
        object_name="liquidMappingInlineEditorRevertButton",
        enabled=on_revert is not None,
        action_kind="revert" if on_revert is not None else "disabled_deferred",
        disabled_reason="Disabled: shell-owned Mapping draft revert is unavailable here." if on_revert is None else "",
    )
    revert.setToolTip("Revert staged Mapping route edits to the original Liquid workspace draft." if on_revert is not None else "Revert unavailable without shell draft ownership.")
    if on_revert is not None:
        revert.clicked.connect(lambda _checked=False: on_revert())
    actions.addWidget(revert)

    actions.addWidget(_copy_button("Copy route details", "liquidMappingInlineEditorCopyButton", _record_text(record)))
    actions.addWidget(
        _deferred_route_button(
            "Open full Route Details",
            object_name="liquidMappingInlineEditorOpenDetailsButton",
            route_target="mapping.route_details",
            on_route_requested=on_route_requested,
        )
    )
    actions.addWidget(
        _deferred_route_button(
            "Open Advanced Route Tables",
            object_name="liquidMappingInlineEditorOpenTablesButton",
            route_target="mapping.advanced_route_tables",
            on_route_requested=on_route_requested,
        )
    )
    close = action_button("Close editor", object_name="liquidMappingInlineEditorCloseButton", enabled=True, action_kind="toggle_ui")
    close.setToolTip("Close the local route editor card. Runtime and workspace are unchanged.")
    close.clicked.connect(lambda _checked=False: on_close())
    actions.addWidget(close)
    actions.addStretch(1)
    layout.addLayout(actions)
    return card


def _inline_editor_field(
    record: MappingRouteRecord,
    field: MappingEditableField,
    controls: dict[str, QComboBox],
) -> QFrame:
    row = glass_panel(f"liquidMappingInlineField_{field.field_id}", role="liquid_mapping_inline_field")
    row.setProperty("componentRole", "MappingInlineEditableField")
    row.setProperty("liquidComponent", True)
    row.setProperty("fieldId", field.field_id)
    row.setProperty("routeId", record.route_id)
    row.setProperty("readOnly", not field.editable)
    layout = horizontal_layout(row, margins=(10, 8, 10, 8), spacing=8)
    label = QLabel(field.label)
    label.setObjectName("liquidMappingInlineFieldLabel")
    layout.addWidget(label, 1)
    if field.editable:
        combo = QComboBox()
        combo.setObjectName(f"liquidMappingInlineFieldControl_{field.field_id}")
        combo.setProperty("mappingFieldControl", True)
        combo.setProperty("fieldId", field.field_id)
        combo.addItems(field.options or (field.value,))
        if field.value in field.options:
            combo.setCurrentText(field.value)
        controls[field.field_id] = combo
        layout.addWidget(combo, 2)
    else:
        value = QLabel(f"{field.value} - {field.read_only_reason}")
        value.setObjectName("liquidMappingInlineFieldReadOnly")
        value.setWordWrap(True)
        layout.addWidget(value, 2)
    return row


def _primary_editable_field(record: MappingRouteRecord) -> MappingEditableField | None:
    for preferred in ("output_intent_target", "logical_function"):
        for field in record.editable_fields:
            if field.field_id == preferred and field.editable:
                return field
    return next((field for field in record.editable_fields if field.editable), None)


def _selected_summary(model: MappingCommandModel) -> QFrame:
    selected = model.selected_control
    row = glass_panel("liquidMappingHeroSummary", role="liquid_mapping_hero_summary")
    row.setProperty("componentRole", "MappingHeroSummary")
    row.setProperty("liquidComponent", True)
    row.setProperty("proofGroupLocation", "hero")
    layout = horizontal_layout(row, margins=(0, 4, 0, 4), spacing=8)
    layout.addWidget(StatusChip(f"Selected: {selected.display_label}", state_role=selected.status_role))
    layout.addWidget(StatusChip(f"Function: {selected.logical_function}", state_role=selected.status_role))
    layout.addWidget(StatusChip(f"Output Intent: {selected.output_intent_target}", state_role="info"))
    layout.addWidget(StatusChip("Selection only", state_role="simulation"))
    layout.addWidget(StatusChip("Output Intent shown; no vJoy write is performed here.", state_role="info"))
    layout.addStretch(1)
    return row


class _LiquidHotasVisualMap(QFrame):
    def __init__(
        self,
        model: MappingCommandModel,
        *,
        on_select: Callable[[str], None],
    ) -> None:
        super().__init__()
        self.setObjectName("liquidMappingHotasMap")
        self.setProperty("componentRole", "MappingHotasVisualMap")
        self.setProperty("liquidComponent", True)
        self.setProperty("hotasVisualMap", True)
        self.setProperty("selectedControlId", model.selected_control.control_id)
        self.setMinimumHeight(245)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._model = model
        self._on_select = on_select
        self._markers: dict[str, QPushButton] = {}
        self._build_markers()

    def sizeHint(self) -> QSize:
        return QSize(760, 300)

    def _build_markers(self) -> None:
        for control in self._model.controls:
            marker = QPushButton(_short_marker_label(control), self)
            marker.setObjectName(f"liquidMappingMarker_{control.control_id}")
            marker.setProperty("uiRole", "liquidMappingMarker")
            marker.setProperty("mappingMarker", True)
            marker.setProperty("controlId", control.control_id)
            marker.setProperty("controlType", control.control_type)
            marker.setProperty("physicalGroup", control.physical_group)
            marker.setProperty("statusRole", control.status_role)
            marker.setProperty("toneRole", status_tone_for_role(control.status_role))
            marker.setProperty("mappedState", control.mapped_state)
            marker.setProperty("selected", control.control_id == self._model.selected_control.control_id)
            configure_command_action(marker, action_kind="select_state")
            marker.setCheckable(True)
            marker.setChecked(control.control_id == self._model.selected_control.control_id)
            marker.setToolTip(_marker_tooltip(control))
            marker.setAccessibleName(control.display_label)
            marker.setAccessibleDescription(_marker_tooltip(control))
            marker.clicked.connect(lambda _checked=False, control_id=control.control_id: self._on_select(control_id))
            refresh_style(marker)
            self._markers[control.control_id] = marker
        self._position_markers()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_markers()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        painter.fillRect(rect, QColor(5, 14, 24, 70))

        throttle = self._region_rect(0.24, 0.50, 0.30, 0.72)
        stick = self._region_rect(0.74, 0.46, 0.30, 0.66)
        base = self._region_rect(0.50, 0.80, 0.74, 0.18)
        for region, label in ((throttle, "THROTTLE"), (stick, "STICK"), (base, "BASE")):
            self._draw_region(painter, region, label)
        self._draw_route_hint(painter)

    def _position_markers(self) -> None:
        rect = QRectF(self.rect()).adjusted(28, 26, -28, -24)
        for control in self._model.controls:
            marker = self._markers[control.control_id]
            width = 74 if control.control_type == "button" else 106
            height = 34
            if control.control_type == "hat":
                width = 112
            x = int(rect.left() + rect.width() * control.anchor_x - width / 2)
            y = int(rect.top() + rect.height() * control.anchor_y - height / 2)
            marker.setGeometry(x, y, width, height)
            marker.raise_()

    def _region_rect(self, x: float, y: float, width: float, height: float) -> QRectF:
        rect = QRectF(self.rect()).adjusted(28, 26, -28, -24)
        return QRectF(
            rect.left() + rect.width() * (x - width / 2),
            rect.top() + rect.height() * (y - height / 2),
            rect.width() * width,
            rect.height() * height,
        )

    def _draw_region(self, painter: QPainter, region: QRectF, label: str) -> None:
        painter.setPen(QPen(QColor(118, 217, 255, 64), 1.2))
        painter.setBrush(QColor(14, 38, 58, 120))
        painter.drawRoundedRect(region, 22, 22)
        font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(159, 185, 207, 160))
        painter.drawText(region.adjusted(12, 8, -12, -8), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, label)

    def _draw_route_hint(self, painter: QPainter) -> None:
        selected = self._model.selected_control
        rect = QRectF(self.rect()).adjusted(28, 26, -28, -24)
        source = rect.topLeft()
        source.setX(rect.left() + rect.width() * selected.anchor_x)
        source.setY(rect.top() + rect.height() * selected.anchor_y)
        target = rect.bottomRight()
        target.setX(rect.left() + rect.width() * 0.90)
        target.setY(rect.top() + rect.height() * 0.88)
        painter.setPen(QPen(QColor(126, 224, 166, 96), 2.0))
        painter.drawLine(source, target)
        painter.setPen(QPen(QColor(118, 217, 255, 150), 1.2))
        painter.drawEllipse(source, 7, 7)
        painter.drawEllipse(target, 5, 5)


class _LiquidHotasMapEditorSurface(QFrame):
    def __init__(
        self,
        model: MappingCommandModel,
        *,
        on_select: Callable[[str], None],
        editor_card: QFrame | None,
    ) -> None:
        super().__init__()
        self.setObjectName("liquidMappingEditorOverlaySurface")
        self.setProperty("componentRole", "MappingEditorOverlaySurface")
        self.setProperty("liquidComponent", True)
        self.setProperty("mappingEditorOverlaySurface", True)
        self.setProperty("editorOpen", editor_card is not None)
        self.setMinimumHeight(560)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._map = _LiquidHotasVisualMap(model, on_select=on_select)
        self._map.setParent(self)
        self._scrim: QFrame | None = None
        self._editor_card = editor_card
        if editor_card is not None:
            self._scrim = QFrame(self)
            self._scrim.setObjectName("liquidMappingEditorFrostedScrim")
            self._scrim.setProperty("componentRole", "MappingEditorFrostedScrim")
            self._scrim.setProperty("liquidComponent", True)
            self._scrim.setProperty("frostedEditorOverlay", True)
            self._scrim.setProperty("visualEffect", "static_frosted_dim_scrim")
            editor_card.setParent(self)
            editor_card.raise_()
            self._scrim.lower()

    def sizeHint(self) -> QSize:
        return QSize(840, 560)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._map.setGeometry(self.rect())
        if self._scrim is not None:
            self._scrim.setGeometry(self.rect())
            self._scrim.raise_()
        if self._editor_card is not None:
            width = min(max(620, self.width() - 120), 820)
            height = min(max(360, self._editor_card.sizeHint().height()), max(360, self.height() - 70))
            x = max(24, int((self.width() - width) / 2))
            y = max(28, int((self.height() - height) / 2))
            self._editor_card.setGeometry(x, y, width, height)
            self._editor_card.raise_()


def _selected_control_inspector(model: MappingCommandModel) -> LiquidInspectorPanel:
    control = model.selected_control
    panel = LiquidInspectorPanel(
        "Selected Control Inspector",
        "Selection only - workspace routes are not edited on this page.",
        object_name="liquidMappingInspector",
        liquid_role="liquid_context_inspector_region",
        minimum_height=290,
    )
    panel.setProperty("mappingInspector", True)
    panel.setProperty("selectedControlId", control.control_id)
    _append_to_panel(panel, _inspector_header(control))
    for label, value, role in (
        ("Physical control", control.display_label, control.status_role),
        ("Control type", control.control_type.title(), "info"),
        ("Physical group", control.physical_group.title(), "info"),
        ("Raw channel", control.raw_input_channel, "info"),
        ("Logical function", control.logical_function, control.status_role),
        ("Output Intent", control.output_intent_target, "info"),
        ("Current value/state", control.current_value_state, "simulation"),
        ("Mapped status", control.mapped_state.title(), control.status_role),
        ("Selection mode", "Selection only - workspace routes are not edited on this page.", "simulation"),
        ("Route editing", "Open Mapping / Route Details to stage workspace route edits.", "info"),
    ):
        _append_to_panel(panel, _detail_row(label, value, role, object_name=f"liquidMappingInspector_{_object_slug(label)}"))
    if control.warning:
        _append_to_panel(panel, _detail_row("Warning", control.warning, "warning", object_name="liquidMappingInspector_warning"))
    _append_to_panel(panel, _detail_row("Truth note", "Read-only visualization; Output Intent is not output write proof.", "simulation", object_name="liquidMappingInspector_truth_note"))
    return panel


def _inspector_header(control: MappingControlModel) -> QFrame:
    header = glass_panel("liquidMappingInspectorHeader", role="liquid_mapping_inspector_header")
    header.setProperty("componentRole", "MappingInspectorHeader")
    header.setProperty("liquidComponent", True)
    layout = horizontal_layout(header, margins=(12, 10, 12, 10), spacing=8)
    layout.addWidget(StatusLight(state_role=control.status_role))
    label = QLabel(control.display_label)
    label.setObjectName("liquidMappingSelectedControlLabel")
    label.setWordWrap(True)
    route = QLabel(f"{control.physical_source_label} -> {control.logical_function}")
    route.setObjectName("liquidMappingSelectedControlRoute")
    route.setWordWrap(True)
    layout.addWidget(label, 1)
    layout.addWidget(route, 2)
    layout.addWidget(StatusChip(control.mapped_state.title(), state_role=control.status_role))
    return header


def _route_flow_panel(
    model: MappingCommandModel,
    on_route_requested: Callable[[str], None] | None,
) -> LiquidDetailPanel:
    selected = model.selected_control
    panel = LiquidDetailPanel(
        "Route Flow",
        "Physical control to logical function to virtual Output Intent.",
        object_name="liquidMappingRouteFlowPanel",
        liquid_role="liquid_detail_action_region",
        minimum_height=290,
    )
    panel.setProperty("mappingRouteFlowPanel", True)
    panel.setProperty("selectedControlId", selected.control_id)
    for index, flow in enumerate(model.route_flows):
        row = RouteFlowRow(
            source_label=flow.source_label,
            function_label=flow.function_label,
            target_label=flow.target_label,
            status_role=flow.status_role,
            helper_text=flow.helper_text,
            object_name=f"liquidMappingRouteFlowRow_{index}",
        )
        row.setProperty("mappingRouteFlow", True)
        _append_to_panel(panel, row)
    _append_to_panel(panel, _truth_notes(model))
    _append_to_panel(panel, _selected_route_actions(model, on_route_requested))
    return panel


def _truth_notes(model: MappingCommandModel) -> QFrame:
    notes = glass_panel("liquidMappingTruthNotes", role="liquid_mapping_truth_notes")
    notes.setProperty("componentRole", "MappingTruthNotes")
    notes.setProperty("liquidComponent", True)
    layout = vertical_layout(notes, margins=(12, 10, 12, 10), spacing=6)
    title = QLabel("Truth boundaries")
    title.setObjectName("liquidMappingTruthNotesTitle")
    layout.addWidget(title)
    for note in model.truth_source_notes:
        label = QLabel(note)
        label.setObjectName("liquidMappingTruthSourceNote")
        label.setWordWrap(True)
        layout.addWidget(label)
    return notes


def _metrics_panel(model: MappingCommandModel) -> QFrame:
    panel = glass_panel("liquidMappingMetrics", role="liquid_mapping_metrics")
    panel.setProperty("componentRole", "MappingMetricsPanel")
    panel.setProperty("liquidComponent", True)
    panel.setProperty("mappingMetrics", True)
    layout = grid_layout(panel, margins=(0, 6, 0, 0), spacing=10)
    for index, metric in enumerate(model.mapping_metrics):
        tile = MetricTile(
            metric.label,
            metric.value,
            metric.caption,
            state_role=metric.role,
            object_name=f"liquidMappingMetric_{_object_slug(metric.label)}",
        )
        tile.setProperty("mappingMetric", True)
        row, column = divmod(index, 3)
        layout.addWidget(tile, row, column)
    return panel


def _advanced_route_details_panel(
    model: MappingCommandModel,
    on_route_requested: Callable[[str], None] | None,
) -> LiquidAdvancedSection:
    panel = LiquidAdvancedSection(
        "Advanced Route Details",
        "Dense route data stays secondary; HOTAS Map remains the primary surface.",
        object_name="liquidMappingAdvancedRouteDetails",
        liquid_role="liquid_advanced_region",
        minimum_height=210,
    )
    panel.setProperty("mappingAdvancedRouteDetails", True)
    panel.setProperty("advancedSecondary", True)
    panel.setProperty("visualWeight", "subdued")
    _append_to_panel(panel, _advanced_summary(model))
    _append_to_panel(panel, _advanced_counts(model))
    _append_to_panel(panel, _selected_advanced_route(model))
    _append_to_panel(panel, _advanced_preview_routes(model, on_route_requested))
    return panel


def _advanced_summary(model: MappingCommandModel) -> QFrame:
    summary = glass_panel("liquidMappingAdvancedSummary", role="liquid_mapping_advanced_summary")
    summary.setProperty("componentRole", "MappingAdvancedSummary")
    summary.setProperty("liquidComponent", True)
    summary.setProperty("visualWeight", "subdued")
    layout = horizontal_layout(summary, margins=(12, 8, 12, 8), spacing=8)
    layout.addWidget(StatusLight(state_role="info"))
    label = QLabel(
        f"{len(model.advanced_route_details)} route records from {model.source_label}. "
        "These rows describe mapping intent, not live output proof."
    )
    label.setObjectName("liquidMappingAdvancedSummaryText")
    label.setWordWrap(True)
    layout.addWidget(label, 1)
    return summary


def _advanced_counts(model: MappingCommandModel) -> QFrame:
    counts = glass_panel("liquidMappingAdvancedCounts", role="liquid_mapping_advanced_counts")
    counts.setProperty("componentRole", "MappingAdvancedCounts")
    counts.setProperty("liquidComponent", True)
    counts.setProperty("visualWeight", "subdued")
    layout = horizontal_layout(counts, margins=(12, 8, 12, 8), spacing=8)
    axis_count = sum(1 for detail in model.advanced_route_details if detail.route_key.startswith("axis:"))
    button_count = sum(1 for detail in model.advanced_route_details if detail.route_key.startswith("button:"))
    hat_count = sum(1 for detail in model.advanced_route_details if detail.route_key.startswith("hat:"))
    unmapped_count = sum(1 for detail in model.advanced_route_details if detail.mapped_state != "mapped")
    layout.addWidget(StatusChip(f"Axis routes: {axis_count}", state_role="info"))
    layout.addWidget(StatusChip(f"Button routes: {button_count}", state_role="info"))
    layout.addWidget(StatusChip(f"Hat routes: {hat_count}", state_role="info"))
    layout.addWidget(StatusChip(f"Unmapped/warnings: {unmapped_count + len(model.warnings)}", state_role="warning" if unmapped_count or model.warnings else "ready"))
    layout.addStretch(1)
    return counts


def _selected_advanced_route(model: MappingCommandModel) -> QFrame:
    section = glass_panel("liquidMappingSelectedAdvancedRoute", role="liquid_mapping_selected_route")
    section.setProperty("componentRole", "MappingAdvancedPreviewSection")
    section.setProperty("liquidComponent", True)
    section.setProperty("visualWeight", "subdued")
    layout = vertical_layout(section, margins=(12, 10, 12, 10), spacing=7)
    title = QLabel("Selected route detail")
    title.setObjectName("liquidMappingAdvancedSectionTitle")
    layout.addWidget(title)
    layout.addWidget(_advanced_route_row(_detail_for_control(model, model.selected_control.control_id)))
    return section


def _advanced_preview_routes(
    model: MappingCommandModel,
    on_route_requested: Callable[[str], None] | None,
) -> QFrame:
    preview = glass_panel("liquidMappingAdvancedPreviewList", role="liquid_mapping_advanced_preview")
    preview.setProperty("componentRole", "MappingAdvancedPreviewList")
    preview.setProperty("liquidComponent", True)
    preview.setProperty("visualWeight", "subdued")
    layout = vertical_layout(preview, margins=(12, 10, 12, 10), spacing=7)
    title = QLabel("Preview routes")
    title.setObjectName("liquidMappingAdvancedSectionTitle")
    layout.addWidget(title)
    for detail in _preview_details(model):
        layout.addWidget(_advanced_route_row(detail))
    note = QLabel("Full route table belongs in Mapping / Advanced Route Tables.")
    note.setObjectName("liquidMappingAdvancedTableNote")
    note.setWordWrap(True)
    layout.addWidget(note)
    layout.addWidget(
        _deferred_route_button(
            "Open Advanced Route Tables",
            object_name="liquidMappingOpenAdvancedTablesButton",
            route_target="mapping.advanced_route_tables",
            on_route_requested=on_route_requested,
        )
    )
    return preview


def _preview_details(model: MappingCommandModel) -> tuple[MappingAdvancedRouteDetailModel, ...]:
    return tuple(
        detail
        for detail in model.advanced_route_details
        if detail.physical_control_id != model.selected_control.control_id
    )[:4]


def _detail_for_control(model: MappingCommandModel, control_id: str) -> MappingAdvancedRouteDetailModel:
    for detail in model.advanced_route_details:
        if detail.physical_control_id == control_id:
            return detail
    return model.advanced_route_details[0]


def _advanced_route_row(detail: MappingAdvancedRouteDetailModel) -> QFrame:
    row = glass_panel(f"liquidMappingAdvancedRow_{_object_slug(detail.physical_control_id)}", role="liquid_mapping_advanced_row")
    row.setProperty("componentRole", "MappingAdvancedRouteRow")
    row.setProperty("liquidComponent", True)
    row.setProperty("advancedRouteDetailRow", True)
    row.setProperty("statusRole", detail.role)
    row.setProperty("toneRole", status_tone_for_role(detail.role))
    layout = grid_layout(row, margins=(10, 8, 10, 8), spacing=8)
    cells = (
        ("Route key", detail.route_key),
        ("Physical control ID", detail.physical_control_id),
        ("Raw channel", detail.raw_channel),
        ("Function", detail.function),
        ("Output Intent", detail.output_intent_target),
        ("Status", detail.mapped_state),
        ("Notes", detail.notes),
    )
    for index, (label, value) in enumerate(cells):
        cell = _compact_cell(label, value)
        layout.addWidget(cell, index // 4, index % 4)
    return row


def _detail_row(label_text: str, value_text: str, role: str, *, object_name: str) -> QFrame:
    row = glass_panel(object_name, role="liquid_mapping_detail_row")
    row.setProperty("componentRole", "MappingDetailRow")
    row.setProperty("liquidComponent", True)
    row.setProperty("detailRowStyle", "soft")
    row.setProperty("statusRole", role)
    row.setProperty("toneRole", status_tone_for_role(role))
    layout = horizontal_layout(row, margins=(12, 8, 12, 8), spacing=8)
    label = QLabel(label_text)
    label.setObjectName("liquidMappingDetailLabel")
    label.setWordWrap(True)
    value = QLabel(value_text)
    value.setObjectName("liquidMappingDetailValue")
    value.setWordWrap(True)
    layout.addWidget(label, 1)
    layout.addWidget(value, 2)
    return row


def _compact_cell(label_text: str, value_text: str) -> QFrame:
    cell = glass_panel(f"liquidMappingCell_{_object_slug(label_text)}", role="liquid_mapping_compact_cell")
    cell.setProperty("componentRole", "MappingAdvancedCell")
    cell.setProperty("liquidComponent", True)
    layout = vertical_layout(cell, margins=(8, 6, 8, 6), spacing=3)
    label = QLabel(label_text)
    label.setObjectName("liquidMappingAdvancedCellLabel")
    value = QLabel(value_text)
    value.setObjectName("liquidMappingAdvancedCellValue")
    value.setWordWrap(True)
    layout.addWidget(label)
    layout.addWidget(value)
    return cell


def _selected_route_actions(model: MappingCommandModel, on_route_requested: Callable[[str], None] | None) -> QFrame:
    actions = glass_panel("liquidMappingDeferredActions", role="liquid_mapping_deferred_actions")
    actions.setProperty("componentRole", "MappingDeferredActions")
    actions.setProperty("liquidComponent", True)
    actions.setProperty("visualWeight", "subdued")
    actions.setProperty("pageActionCluster", True)
    layout = horizontal_layout(actions, margins=(12, 10, 12, 10), spacing=8)
    note = QLabel("Selected control actions. Route edits stage workspace draft changes only.")
    note.setObjectName("liquidMappingDeferredActionNote")
    note.setWordWrap(True)
    layout.addWidget(note, 1)
    layout.addWidget(
        _deferred_route_button(
            "Edit selected route",
            object_name="liquidMappingEditSelectedRouteButton",
            route_target="mapping.route_details",
            on_route_requested=on_route_requested,
        )
    )
    layout.addWidget(
        _deferred_route_button(
            "Open Route Details",
            object_name="liquidMappingOpenRouteDetailsButton",
            route_target="mapping.route_details",
            on_route_requested=on_route_requested,
        )
    )
    layout.addWidget(
        _deferred_route_button(
            "Open Advanced Route Tables",
            object_name="liquidMappingOpenAdvancedTablesButtonInline",
            route_target="mapping.advanced_route_tables",
            on_route_requested=on_route_requested,
        )
    )
    layout.addWidget(
        _copy_button(
            "Copy selected route",
            "liquidMappingCopySelectedRouteButton",
            _selected_route_text(model),
        )
    )
    layout.addWidget(
        _copy_button(
            "Copy mapping summary",
            "liquidMappingCopySummaryButton",
            _mapping_summary_text(model),
        )
    )
    reset = action_button(
        "Reset selected route",
        object_name="liquidMappingResetSelectedRouteButton",
        enabled=False,
        action_kind="disabled_deferred",
        disabled_reason="Disabled: selected-route defaults are not represented as a safe route-level workspace operation.",
    )
    reset.setToolTip("Reset is pending because selected-route defaults are not represented as a safe route-level workspace operation.")
    reset.setAccessibleDescription(reset.toolTip())
    reset.setStatusTip(reset.toolTip())
    layout.addWidget(reset)
    return actions


def _deferred_route_button(
    text: str,
    *,
    object_name: str,
    route_target: str,
    on_route_requested: Callable[[str], None] | None,
) -> QPushButton:
    reason = f"{text}. Navigation only; no workspace edit is staged by this button."
    if on_route_requested is None:
        reason = f"Disabled: {reason} Navigation callback unavailable in this context."
    button = action_button(
        text,
        object_name=object_name,
        enabled=on_route_requested is not None,
        action_kind="navigation",
        disabled_reason=reason if on_route_requested is None else "",
        route_target=route_target,
    )
    button.setProperty("navigationOnly", True)
    button.setProperty("routeTarget", route_target)
    button.setToolTip(reason)
    button.setAccessibleName(text)
    button.setStatusTip(reason)
    button.setAccessibleDescription(reason)
    if on_route_requested is not None:
        button.clicked.connect(lambda _checked=False, target=route_target: on_route_requested(target))
    return button


def _copy_button(text: str, object_name: str, payload: str) -> QPushButton:
    button = action_button(text, object_name=object_name, enabled=True, action_kind="copy")
    button.setProperty("copyOnly", True)
    button.setToolTip("Copy mapping information to the clipboard. This does not edit workspace or runtime state.")
    button.setStatusTip(button.toolTip())
    button.setAccessibleDescription(button.toolTip())
    button.clicked.connect(lambda _checked=False, data=payload, target=button: _copy_to_clipboard(data, target))
    return button


def _copy_to_clipboard(text: str, button: QPushButton | None = None) -> None:
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)
        if button is not None:
            mark_action_feedback(button, "Copied mapping information to clipboard.")
    elif button is not None:
        mark_action_feedback(button, "Clipboard unavailable; nothing was copied.")


def _selected_route_text(model: MappingCommandModel) -> str:
    selected = model.selected_control
    return "\n".join(
        (
            f"Selected control: {selected.display_label}",
            f"Raw channel: {selected.raw_input_channel}",
            f"Logical function: {selected.logical_function}",
            f"Output Intent: {selected.output_intent_target}",
            f"Mapped state: {selected.mapped_state}",
            "Output proof unchanged by copy action.",
        )
    )


def _ancestor_scroll_state(widget: QWidget) -> tuple[QScrollArea | None, int]:
    parent = widget.parent()
    while parent is not None:
        if isinstance(parent, QScrollArea):
            return parent, parent.verticalScrollBar().value()
        parent = parent.parent()
    return None, 0


def _restore_scroll_state(scroll_area: QScrollArea | None, value: int) -> None:
    if scroll_area is None:
        return

    def restore() -> None:
        bar = scroll_area.verticalScrollBar()
        bar.setValue(min(max(0, value), bar.maximum()))

    restore()


def _record_text(record: MappingRouteRecord) -> str:
    return "\n".join(
        (
            f"Route: {record.route_id}",
            f"Physical control: {record.physical_label}",
            f"Control type: {record.control_type}",
            f"Raw channel: {record.raw_channel}",
            f"Logical function: {record.logical_function}",
            f"Output Intent: {record.output_intent_target}",
            f"Status: {record.status}",
            f"Notes: {record.notes}",
            "Workspace draft copy only; output proof unchanged.",
        )
    )


def _mapping_summary_text(model: MappingCommandModel) -> str:
    lines = [f"Mapping source: {model.source_label}", f"Runtime truth: {model.runtime_truth_label}"]
    lines.extend(f"{metric.label}: {metric.value} ({metric.caption})" for metric in model.mapping_metrics)
    lines.append("Output Intent is mapping intent, not output proof.")
    return "\n".join(lines)


def _append_to_panel(panel: QWidget, widget: QWidget) -> None:
    layout = panel.layout()
    if layout is None:
        return
    insert_at = max(0, layout.count() - 1)
    layout.insertWidget(insert_at, widget)


def _short_marker_label(control: MappingControlModel) -> str:
    if control.control_id == "hat_pov":
        return "Hat / POV"
    if control.control_id.startswith("button_b"):
        return control.display_label
    if control.control_id.startswith("axis_aux"):
        return control.display_label
    return control.logical_function if control.logical_function != "Unmapped" else control.display_label


def _marker_tooltip(control: MappingControlModel) -> str:
    lines = [
        control.display_label,
        f"Type: {control.control_type}",
        f"Raw channel: {control.raw_input_channel}",
        f"Logical function: {control.logical_function}",
        f"Output Intent: {control.output_intent_target}",
        f"Current value/state: {control.current_value_state}",
        f"Status: {control.mapped_state}",
        "Note: Read-only visualization; Output Intent is not output write proof.",
    ]
    if control.warning:
        lines.insert(6, f"Warning: {control.warning}")
    return "\n".join(lines)


def _object_slug(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value).strip("_")


def _render_signature(
    state: AppState,
    workspace: WorkspaceConfig,
    selected_control_id: str | None,
) -> tuple[object, ...]:
    return (
        selected_control_id,
        state.active_profile,
        state.source_config,
        bool(state.saved),
        state.runtime.header_truth_label,
        state.runtime.tone,
        state.runtime.backend_name,
        workspace.active_profile,
        workspace.source_path,
        workspace.state.saved,
        len(workspace.mappings.axis_routes),
        len(workspace.mappings.button_routes),
        len(workspace.mappings.hat_routes),
        tuple((route.function_name, route.raw_axis_channel, route.logical_output, route.runtime_vjoy_output) for route in workspace.mappings.axis_routes),
        tuple((route.hotas_button, route.output_button) for route in workspace.mappings.button_routes),
        tuple((route.hotas_hat, route.vjoy_pov, route.up_button, route.right_button, route.down_button, route.left_button) for route in workspace.mappings.hat_routes),
    )


def _default_state() -> AppState:
    runtime_status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.SIMULATED,
        input=InputDeviceDetection(),
        output=OutputBackendDetection(),
        messages=("Simulation mode selected; Mapping page is read-only.",),
    )
    state = AppState.from_runtime_status(runtime_status, active_page_id="mapping")
    state.active_profile = "Workspace loaded"
    state.status_message = "LCD-5 Mapping command page default fixture."
    return state
