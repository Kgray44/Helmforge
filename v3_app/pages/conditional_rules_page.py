from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from shared_core.math.pipeline import WorkspaceSignalPipeline
from shared_core.math.stack import ModeState
from shared_core.models.axes import AXIS_DISPLAY_NAMES
from shared_core.models.rules import ConditionalRule, RuleConfig, yaw_roll_example_rule
from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.runtime_bridge import RuntimeBridge
from shared_core.rules.evaluator import (
    RuleEvaluationResult,
    RuleStatus,
    rule_detail_sentence,
    rule_preview_sentence,
    status_counts,
)
from v3_app.pages.page_helpers import apply_parameter_metadata, parameter_label, truth_notice
from v3_app.services.app_state import AppState
from v3_app.ui.status_chips import action_button, status_chip


OnDirty = Callable[[str], None]
OnStatus = Callable[[str], None]
OnWorkspaceChanged = Callable[[WorkspaceConfig, str], None]

PARAMETER_OPTIONS = ("Output Scale",)
OPERATION_OPTIONS = ("Set", "Add", "Multiply")
INJECTION_STAGE_OPTIONS = ("Base Output Limits",)
MODE_GATE_OPTIONS = ("Always", "Precision", "Combat")
BUTTON_TEST_OPTIONS = ("Any", "All")
REFERENCE_STAGE_OPTIONS = ("Final Output", "Raw Input", "Center Conditioning", "Curve / Shape", "Base Output Limits", "Filtering", "Mode Modifiers")
MEASURE_OPTIONS = ("absolute", "signed", "raw")
COMPARATOR_OPTIONS = ("greater than", "less than", "equal", "approximately", "between", "range")
RULE_FIELD_METADATA_IDS = {
    "title": "rules.title",
    "target_axis": "rules.target_axis",
    "parameter": "rules.parameter",
    "operation": "rules.operation",
    "value": "rules.value",
    "injection_stage": "rules.injects_at",
    "mode_gate": "rules.mode_gate",
    "buttons": "rules.buttons",
    "button_test": "rules.button_test",
    "reference_axis": "rules.reference_axis",
    "stage": "rules.stage",
    "measure": "rules.measure",
    "comparator": "rules.comparator",
    "threshold": "rules.threshold",
    "threshold_high": "rules.threshold_high",
}


class ConditionalRulesPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        on_dirty: OnDirty | None = None,
        on_status: OnStatus | None = None,
        on_workspace_changed: OnWorkspaceChanged | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("conditionalRulesPage")
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._on_dirty = on_dirty
        self._on_status = on_status
        self._on_workspace_changed = on_workspace_changed
        self._selected_index = 0
        self._updating_detail = False
        self._rule_results: tuple[RuleEvaluationResult, ...] = ()
        self._chips: dict[str, QLabel] = {}
        self._table: QTableWidget | None = None
        self._detail_labels: dict[str, QLabel] = {}
        self._detail_fields: dict[str, QWidget] = {}
        self._toggle_button = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)

        root.addWidget(self._build_intro())
        root.addWidget(
            truth_notice(
                "Rule edits stay in the workspace draft. Rule status is deterministic local evaluation, not a claim that runtime output fired.",
                object_name="conditionalRulesTruthNotice",
            )
        )
        root.addWidget(self._build_chip_row())
        root.addWidget(self._build_action_row())

        split = QHBoxLayout()
        split.setSpacing(18)
        split.addWidget(self._build_rule_list_card(), 1, Qt.AlignmentFlag.AlignTop)
        right = QVBoxLayout()
        right.setSpacing(18)
        right.addWidget(self._build_detail_card(), 2)
        right.addWidget(self._build_logic_card(), 1)
        right_panel = QWidget()
        right_panel.setLayout(right)
        split.addWidget(right_panel, 1, Qt.AlignmentFlag.AlignTop)
        root.addLayout(split, 1)

        self._refresh_all(select_index=0)

    def _build_intro(self) -> QWidget:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        title = QLabel("Conditional Rules")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Build responsive modifier rules, track their live state, and see exactly where they inject into the response stack."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        runtime = QLabel(
            f"Runtime truth: {self._runtime_status.truth.value}. Output writes verified: "
            f"{str(self._runtime_status.live_output_writes_verified).lower()}."
        )
        runtime.setObjectName("pageBody")
        runtime.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(runtime)
        return block

    def _build_chip_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for key, tone in (
            ("total", "neutral"),
            ("active", "success"),
            ("blocked", "warning"),
            ("disabled", "danger"),
        ):
            chip = status_chip("0", tone=tone, object_name=f"rules{key.title()}Chip")
            self._chips[key] = chip
            layout.addWidget(chip)
        layout.addStretch(1)
        return row

    def _build_action_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        add = action_button("Add Rule", object_name="addRuleButton")
        edit = action_button("Edit Selected", object_name="editSelectedRuleButton")
        duplicate = action_button("Duplicate", object_name="duplicateRuleButton")
        toggle = action_button("Enable", object_name="toggleRuleEnabledButton")
        delete = action_button("Delete", object_name="deleteRuleButton")
        delete.setProperty("danger", True)
        add.clicked.connect(self._add_rule)
        edit.clicked.connect(self._focus_editor)
        duplicate.clicked.connect(self._duplicate_rule)
        toggle.clicked.connect(self._toggle_rule_enabled)
        delete.clicked.connect(self._delete_rule)
        self._toggle_button = toggle
        for button in (add, edit, duplicate, toggle, delete):
            layout.addWidget(button)
        layout.addStretch(1)
        return row

    def _build_rule_list_card(self) -> QFrame:
        card = self._card("conditionalRuleListCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)
        layout.addWidget(self._card_header("Rule List", "Rules stay persistent, and live state updates in place without rebuilding the workspace."))

        self._table = QTableWidget(0, 4)
        self._table.setObjectName("conditionalRuleList")
        self._table.setHorizontalHeaderLabels(("Rule", "Targets", "Parameter", "Live"))
        self._configure_table(self._table, minimum_height=420)
        self._table.currentCellChanged.connect(lambda row, _col, _prev_row, _prev_col: self._select_rule(row))
        layout.addWidget(self._table, 1)
        return card

    def _build_detail_card(self) -> QFrame:
        card = self._card("conditionalRuleDetailCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)
        layout.addWidget(self._card_header("Rule Detail", "The selected rule's scope, live state, and the exact condition it is waiting on."))

        badge = QLabel("Disabled")
        badge.setObjectName("ruleStatusBadge")
        badge.setProperty("uiRole", "statusChip")
        badge.setProperty("chipTone", "danger")
        title = QLabel("")
        title.setObjectName("ruleDetailTitle")
        title.setWordWrap(True)
        detail = QLabel("")
        detail.setObjectName("ruleDetailSentence")
        detail.setWordWrap(True)
        preview = QLabel("")
        preview.setObjectName("rulePreviewSentence")
        preview.setWordWrap(True)
        facts = QLabel("")
        facts.setObjectName("ruleDetailFacts")
        facts.setWordWrap(True)
        self._detail_labels.update({"badge": badge, "title": title, "detail": detail, "preview": preview, "facts": facts})

        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addWidget(facts)
        layout.addWidget(preview)
        layout.addWidget(self._build_editor_grid())
        return card

    def _build_logic_card(self) -> QFrame:
        card = self._card("ruleLogicCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(12)
        layout.addWidget(self._card_header("Rule Logic"))
        for text in (
            "Conditional rules are injected inline at the stage they affect. Use them for hover bands, roll-linked trims, or mode-specific filtering shifts.",
            "Select a rule to review its target axis, gating, reference signal, and injection stage in one place.",
        ):
            label = QLabel(text)
            label.setObjectName("cardBody")
            label.setWordWrap(True)
            layout.addWidget(label)
        return card

    def _build_editor_grid(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        for title, rows in (
            (
                "Action",
                (
                    ("Title", "title", "line"),
                    ("Target Axis", "target_axis", AXIS_DISPLAY_NAMES),
                    ("Parameter", "parameter", PARAMETER_OPTIONS),
                    ("Operation", "operation", OPERATION_OPTIONS),
                    ("Value", "value", "line"),
                    ("Injects At", "injection_stage", INJECTION_STAGE_OPTIONS),
                ),
            ),
            (
                "When",
                (
                    ("Mode Gate", "mode_gate", MODE_GATE_OPTIONS),
                    ("Buttons", "buttons", "line"),
                    ("Button Test", "button_test", BUTTON_TEST_OPTIONS),
                ),
            ),
            (
                "Condition",
                (
                    ("Reference Axis", "reference_axis", AXIS_DISPLAY_NAMES),
                    ("Stage", "stage", REFERENCE_STAGE_OPTIONS),
                    ("Measure", "measure", MEASURE_OPTIONS),
                    ("Comparator", "comparator", COMPARATOR_OPTIONS),
                    ("Threshold", "threshold", "line"),
                    ("Threshold High", "threshold_high", "line"),
                ),
            ),
        ):
            group = QFrame()
            group.setObjectName("ruleEditorGroup")
            group_layout = QGridLayout(group)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setHorizontalSpacing(12)
            group_layout.setVerticalSpacing(8)
            group_title = QLabel(title)
            group_title.setObjectName("sectionLabel")
            group_layout.addWidget(group_title, 0, 0, 1, 2)
            for row_index, (label, field, options) in enumerate(rows, start=1):
                metadata_id = RULE_FIELD_METADATA_IDS.get(field)
                key = parameter_label(label, metadata_id=metadata_id)
                group_layout.addWidget(key, row_index, 0)
                if options == "line":
                    widget = QLineEdit()
                    widget.setObjectName(f"rule{_field_object_name(field)}Field")
                    apply_parameter_metadata(widget, metadata_id)
                    widget.editingFinished.connect(lambda field_name=field: self._line_field_changed(field_name))
                else:
                    widget = QComboBox()
                    widget.setObjectName(f"rule{_field_object_name(field)}Field")
                    apply_parameter_metadata(widget, metadata_id)
                    widget.addItems(tuple(options))
                    widget.currentTextChanged.connect(
                        lambda value, field_name=field: self._combo_field_changed(field_name, value)
                    )
                self._detail_fields[field] = widget
                group_layout.addWidget(widget, row_index, 1)
            layout.addWidget(group)
        return panel

    def _refresh_all(self, *, select_index: int | None = None) -> None:
        self._rule_results = self._evaluate_rules()
        self._refresh_chips()
        self._populate_table()
        if select_index is not None:
            self._selected_index = max(0, min(select_index, len(self._workspace.rules.rules) - 1))
        self._refresh_detail()

    def _evaluate_rules(self) -> tuple[RuleEvaluationResult, ...]:
        if not self._workspace.rules.rules:
            return ()
        snapshot = RuntimeBridge(
            preflight_status=self._runtime_status,
            deterministic_simulation=True,
        ).snapshot()
        pipeline = WorkspaceSignalPipeline(self._workspace)
        return pipeline.process(snapshot.raw_axis_values, mode_state=ModeState()).rule_evaluations

    def _refresh_chips(self) -> None:
        counts = status_counts(self._rule_results)
        labels = {
            "total": f"{counts['total']} rules",
            "active": f"{counts['active']} active",
            "blocked": f"{counts['blocked']} blocked",
            "disabled": f"{counts['disabled']} disabled",
        }
        for key, text in labels.items():
            self._chips[key].setText(text)

    def _populate_table(self) -> None:
        if self._table is None:
            return
        self._table.blockSignals(True)
        self._table.setRowCount(len(self._workspace.rules.rules))
        for row, rule in enumerate(self._workspace.rules.rules):
            status = self._result_for(row).status.value if row < len(self._rule_results) else "Disabled"
            for column, value in enumerate((rule.title, rule.target_axis, rule.parameter, status)):
                item = QTableWidgetItem(value)
                self._table.setItem(row, column, item)
        if self._workspace.rules.rules:
            self._table.selectRow(self._selected_index)
        self._table.blockSignals(False)
        self._table.resizeColumnsToContents()

    def _refresh_detail(self) -> None:
        rule = self._selected_rule()
        self._updating_detail = True
        try:
            if rule is None:
                for label in self._detail_labels.values():
                    label.setText("No rule selected.")
                return

            result = self._result_for(self._selected_index)
            tone = _tone_for_status(result.status)
            self._detail_labels["badge"].setText(result.status.value)
            self._detail_labels["badge"].setProperty("chipTone", tone)
            self._detail_labels["badge"].style().unpolish(self._detail_labels["badge"])
            self._detail_labels["badge"].style().polish(self._detail_labels["badge"])
            self._detail_labels["title"].setText(rule.title)
            self._detail_labels["detail"].setText(rule_detail_sentence(rule))
            self._detail_labels["facts"].setText(
                f"Target Axis: {rule.target_axis} | Parameter: {rule.parameter} | Operation: {rule.operation} | "
                f"Value: {_format_number(rule.value)} | Injects At: {rule.injection_stage} | Mode Gate: {rule.mode_gate}"
            )
            status_note = f"{result.status.value}: {result.blocked_reason}" if result.blocked_reason else f"{result.status.value}: rule is turned {'on' if rule.enabled else 'off'}."
            self._detail_labels["preview"].setText(f"{status_note} {rule_preview_sentence(rule)}")
            _set_line(self._detail_fields["title"], rule.title)
            _set_combo(self._detail_fields["target_axis"], rule.target_axis)
            _set_combo(self._detail_fields["parameter"], rule.parameter)
            _set_combo(self._detail_fields["operation"], rule.operation)
            _set_line(self._detail_fields["value"], _format_number(rule.value))
            _set_combo(self._detail_fields["injection_stage"], rule.injection_stage)
            _set_combo(self._detail_fields["mode_gate"], rule.mode_gate)
            _set_line(self._detail_fields["buttons"], _format_buttons(rule.buttons))
            _set_combo(self._detail_fields["button_test"], rule.button_test)
            _set_combo(self._detail_fields["reference_axis"], rule.reference_axis)
            _set_combo(self._detail_fields["stage"], rule.stage)
            _set_combo(self._detail_fields["measure"], rule.measure)
            _set_combo(self._detail_fields["comparator"], rule.comparator)
            _set_line(self._detail_fields["threshold"], _format_number(rule.threshold))
            _set_line(self._detail_fields["threshold_high"], "" if rule.threshold_high is None else _format_number(rule.threshold_high))
            if self._toggle_button is not None:
                self._toggle_button.setText("Disable" if rule.enabled else "Enable")
        finally:
            self._updating_detail = False

    def _select_rule(self, row: int) -> None:
        if row < 0 or row >= len(self._workspace.rules.rules):
            return
        self._selected_index = row
        self._refresh_detail()

    def _selected_rule(self) -> ConditionalRule | None:
        if not self._workspace.rules.rules:
            return None
        if self._selected_index >= len(self._workspace.rules.rules):
            self._selected_index = len(self._workspace.rules.rules) - 1
        return self._workspace.rules.rules[self._selected_index]

    def _result_for(self, index: int) -> RuleEvaluationResult:
        return self._rule_results[index]

    def _line_field_changed(self, field: str) -> None:
        if self._updating_detail:
            return
        widget = self._detail_fields[field]
        value = widget.text()
        try:
            if field in {"value", "threshold"}:
                parsed = float(value)
            elif field == "threshold_high":
                parsed = None if value.strip() == "" else float(value)
            elif field == "buttons":
                parsed = _parse_buttons(value)
            else:
                parsed = value.strip()
        except ValueError:
            self._status_message(f"Rule {field.replace('_', ' ')} must be numeric before it can be staged.")
            return
        self._update_selected_rule(**{field: parsed})

    def _combo_field_changed(self, field: str, value: str) -> None:
        if self._updating_detail:
            return
        self._update_selected_rule(**{field: value})

    def _add_rule(self) -> None:
        rules = list(self._workspace.rules.rules)
        rules.append(_new_rule(len(rules) + 1))
        self._set_rule_config(
            RuleConfig(rules=tuple(rules)),
            "Added a disabled conditional rule draft.",
            select_index=len(rules) - 1,
        )

    def _focus_editor(self) -> None:
        title = self._detail_fields.get("title")
        if title is not None:
            title.setFocus()
        self._status_message("Edit the selected rule in the grouped Action, When, and Condition fields.")

    def _duplicate_rule(self) -> None:
        rule = self._selected_rule()
        if rule is None:
            self._status_message("Select a rule before duplicating it.")
            return
        rules = list(self._workspace.rules.rules)
        copied = replace(rule, title=_unique_copy_title(rule.title, rules), enabled=False)
        insert_at = self._selected_index + 1
        rules.insert(insert_at, copied)
        self._set_rule_config(
            RuleConfig(rules=tuple(rules)),
            f"Duplicated rule {rule.title}; copy is disabled.",
            select_index=insert_at,
        )

    def _toggle_rule_enabled(self) -> None:
        rule = self._selected_rule()
        if rule is None:
            self._status_message("Select a rule before toggling it.")
            return
        self._update_selected_rule(enabled=not rule.enabled)

    def _delete_rule(self) -> None:
        if not self._workspace.rules.rules:
            self._status_message("No rule is selected for deletion.")
            return
        rules = list(self._workspace.rules.rules)
        removed = rules.pop(self._selected_index)
        next_index = max(0, min(self._selected_index, len(rules) - 1))
        self._set_rule_config(
            RuleConfig(rules=tuple(rules)),
            f"Deleted conditional rule {removed.title}.",
            select_index=next_index,
        )

    def _update_selected_rule(self, **changes) -> None:
        rule = self._selected_rule()
        if rule is None:
            return
        rules = list(self._workspace.rules.rules)
        rules[self._selected_index] = replace(rule, **changes)
        self._set_rule_config(
            RuleConfig(rules=tuple(rules)),
            f"Conditional rule edit staged for {rules[self._selected_index].title}.",
            select_index=self._selected_index,
        )

    def _set_rule_config(self, rule_config: RuleConfig, message: str, *, select_index: int) -> None:
        self._workspace = replace(self._workspace, rules=rule_config)
        if self._on_workspace_changed is not None:
            self._on_workspace_changed(self._workspace, message)
        elif self._on_dirty is not None:
            self._on_dirty(message)
        self._refresh_all(select_index=select_index)

    def _status_message(self, message: str) -> None:
        if self._on_status is not None:
            self._on_status(message)

    def _configure_table(self, table: QTableWidget, *, minimum_height: int) -> None:
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(38)
        table.setAlternatingRowColors(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(minimum_height)

    @staticmethod
    def _card(object_name: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName(object_name)
        frame.setProperty("cardRole", "pageCard")
        frame.setFrameShape(QFrame.Shape.NoFrame)
        return frame

    @staticmethod
    def _card_header(title: str, body: str | None = None) -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        layout.addWidget(title_label)
        if body:
            body_label = QLabel(body)
            body_label.setObjectName("cardBody")
            body_label.setWordWrap(True)
            layout.addWidget(body_label)
        return header


def _new_rule(index: int) -> ConditionalRule:
    base = yaw_roll_example_rule()
    return replace(base, title=f"New Conditional Rule {index}", enabled=False, value=1.0, threshold=0.5)


def _tone_for_status(status: RuleStatus) -> str:
    if status is RuleStatus.ACTIVE:
        return "success"
    if status is RuleStatus.BLOCKED:
        return "warning"
    if status is RuleStatus.DISABLED:
        return "danger"
    return "neutral"


def _set_combo(widget: QWidget, value: str) -> None:
    combo = widget
    if not isinstance(combo, QComboBox):
        return
    if combo.findText(value) < 0:
        combo.addItem(value)
    combo.setCurrentText(value)


def _set_line(widget: QWidget, value: str) -> None:
    line = widget
    if isinstance(line, QLineEdit):
        line.setText(value)


def _field_object_name(field: str) -> str:
    return "".join(part.capitalize() for part in field.split("_"))


def _format_buttons(buttons: tuple[int, ...]) -> str:
    return ", ".join(str(button) for button in buttons)


def _parse_buttons(value: str) -> tuple[int, ...]:
    if not value.strip():
        return ()
    normalized = value.replace("B", "").replace("b", "").replace(";", ",")
    return tuple(int(part.strip()) for part in normalized.split(",") if part.strip())


def _format_number(value: float | int) -> str:
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


def _unique_copy_title(title: str, rules: list[ConditionalRule]) -> str:
    existing = {rule.title for rule in rules}
    candidate = f"{title} Copy"
    index = 2
    while candidate in existing:
        candidate = f"{title} Copy {index}"
        index += 1
    return candidate
